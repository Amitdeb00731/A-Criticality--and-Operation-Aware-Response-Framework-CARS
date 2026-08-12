#!/usr/bin/env python3
# cars_remediation.py  —  P1/Rung B: CARS PROCESS-STATE MAINTENANCE via last-good substitution (the explicit novelty).
# Detects sensor tampering by PROCESS ANOMALY (a value the bang-bang law physically cannot produce) and restores last-good
# to the PLC, so the loop keeps a correct reading DURING/AFTER the attack = "block (network) AND maintain (process)".
#
# ── #25 RETROFIT (2026-07-29, CC-90): TOPOLOGY-WIDE. One codebase, per-PLC profile selected by argv/env, so the SAME agent
#    protects Tank1 (Cell-1, .2.10) AND Tank2 (Cell-2, .3.10). Two detection SOURCES because the two PLCs differ in capacity:
#      • plc1  source=s7   — direct persistent S7 read+write (.2.10 has spare S7 connection resources). DEFAULT, unchanged.
#      • plc2  source=mqtt — reads the level from the collector's existing MQTT telemetry (cars/cell2/plc2/level), so it
#        needs NO persistent S7 slot on the 1212C (which has no spare while Node-RED polls it), and opens a BRIEF S7
#        connection only to WRITE last-good on tamper. Broker is localhost-only (pen-test P0-3), so the telemetry an OT
#        attacker sees cannot be poisoned -> MQTT-sourced detection is sound here.
#    + auto-reconnect on the s7 path (fixes the "doesn't auto-reconnect after Node-RED starves its slot" zombie).
#
# RUN  PLC1 (unchanged): sudo systemctl restart cars-remediation           # service: ip netns exec remns ... (defaults plc1)
# RUN  PLC2 (new):       sudo nohup python3 ~/cars_remediation.py plc2 &    # base-ns; routes .3.10 via ins2; needs mosquitto_sub
import snap7, time, struct, json, os, sys, subprocess

PROFILES = {
    # Tank1 / PLC1 (Cell-1), pump ON 30 / OFF 70. DEFAULT — identical to the pre-retrofit single-PLC agent.
    "plc1": dict(host="192.168.2.10", band_lo=28.0, band_hi=72.0, drop=15.0, floor=25.0, seed=50.0, source="s7",
                 feed="/tmp/cars_remediation.jsonl", status="/tmp/cars_remediation_status.json", tag="PLC1"),
    # Tank2 / PLC2 (Cell-2), pump ON 20 / OFF 55. TRANSIENT S7 (connect->read->[write]->disconnect each cycle): never holds
    # a 2nd persistent slot against the Node-RED collector, and every read is a "first read on a fresh connection" — the one
    # the 1212C serviced reliably (sustained 2nd-slot reads were what timed out). Authoritative (reads the real PLC), no
    # dependency on the collector's MQTT publish (which is currently not emitting per-tank topics). mqtt_* kept for fallback.
    "plc2": dict(host="192.168.3.10", band_lo=18.0, band_hi=57.0, drop=12.0, floor=15.0, seed=37.0, source="s7t",
                 poll=1.0, mqtt_host="127.0.0.1", mqtt_topic="cars/cell2/plc2/level",
                 feed="/tmp/cars_remediation_plc2.jsonl", status="/tmp/cars_remediation_plc2_status.json", tag="PLC2"),
}
SEL = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CARS_PLC", "plc1")).lower()
if SEL not in PROFILES:
    sys.exit("[REM] unknown PLC profile %r (expected one of %s)" % (SEL, ", ".join(PROFILES)))
P = PROFILES[SEL]
HOST = P["host"]; DB = 7; OFFSET = 0
FEED = P["feed"]; STATUS = P["status"]
BAND_LO, BAND_HI = P["band_lo"], P["band_hi"]
DROP = P["drop"]; FLOOR = P["floor"]; SEED = P["seed"]; TAG = P["tag"]; SOURCE = P["source"]
POLL = 0.3

def feed(ev, **kw):
    kw["event"] = ev; kw["ts"] = time.time(); kw["plc"] = TAG
    try:
        with open(FEED, "a") as f: f.write(json.dumps(kw) + "\n")
        os.chmod(FEED, 0o644)
    except Exception: pass
def status(**kw):
    kw["ts"] = time.time(); kw["plc"] = TAG
    try:
        with open(STATUS, "w") as f: json.dump(kw, f)
        os.chmod(STATUS, 0o644)
    except Exception: pass
def log(msg): print(msg, flush=True)   # flush so journald/foreground shows lines immediately
def s7_read(c):   return struct.unpack('>f', bytes(c.db_read(DB, OFFSET, 4)))[0]
def s7_write(c, v): c.db_write(DB, OFFSET, bytearray(struct.pack('>f', v)))

def tampered(lvl, prev):
    return (lvl < FLOOR) or (lvl < prev - DROP)

# ── SOURCE = s7 : direct persistent read+write with auto-reconnect (PLC1) ──────────────────────────────────────────────
def run_s7():
    c = None; last_good = SEED; prev = SEED; restores = 0
    while True:
        try:
            if c is None:
                c = snap7.client.Client(); c.connect(HOST, 0, 1)
                log("[REM:%s] ONLINE via S7 (%s) - watching Tank.Level; restore last-good on tamper" % (TAG, HOST))
                feed("ONLINE", host=HOST, source="s7")
            lvl = s7_read(c)
            if tampered(lvl, prev):
                seen = lvl; s7_write(c, last_good); restores += 1
                log("[REM:%s] TAMPER (Level=%.1f, prev %.1f) -> RESTORED last-good %.1f   [restores %d]"
                    % (TAG, seen, prev, last_good, restores))
                feed("RESTORED", level=round(seen, 1), prev=round(prev, 1), last_good=round(last_good, 1), restores=restores)
                lvl = last_good
            elif BAND_LO <= lvl <= BAND_HI:
                last_good = lvl
            status(online=1, level=round(lvl, 1), last_good=round(last_good, 1), restores=restores)
            prev = lvl
        except Exception as e:
            log("[REM:%s] read/write error: %s -> reconnecting" % (TAG, e))
            status(online=0, last_good=round(last_good, 1), restores=restores)
            try:
                if c is not None: c.disconnect()
            except Exception: pass
            c = None; time.sleep(1.0); continue
        time.sleep(POLL)

# ── SOURCE = mqtt : detect from telemetry, restore with a BRIEF S7 write (PLC2, S7-slot-free detection) ─────────────────
def transient_write(val):
    c = snap7.client.Client()
    c.connect(HOST, 0, 1)
    try:
        s7_write(c, val)
    finally:
        try: c.disconnect()
        except Exception: pass

def run_mqtt():
    MQTT_HOST = P["mqtt_host"]; TOPIC = P["mqtt_topic"]
    last_good = SEED; prev = SEED; restores = 0
    while True:  # respawn the subscriber if it ever dies
        proc = subprocess.Popen(["mosquitto_sub", "-h", MQTT_HOST, "-t", TOPIC],
                                stdout=subprocess.PIPE, text=True, bufsize=1)
        log("[REM:%s] ONLINE via MQTT %s (restore-writes to %s) - transient-write on tamper" % (TAG, TOPIC, HOST))
        feed("ONLINE", host=HOST, source="mqtt", topic=TOPIC)
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line: continue
                try: lvl = float(line)
                except ValueError: continue
                if tampered(lvl, prev):
                    seen = lvl
                    try:
                        transient_write(last_good); restores += 1
                        log("[REM:%s] TAMPER (Level=%.1f, prev %.1f) -> RESTORED last-good %.1f   [restores %d]"
                            % (TAG, seen, prev, last_good, restores))
                        feed("RESTORED", level=round(seen, 1), prev=round(prev, 1),
                             last_good=round(last_good, 1), restores=restores)
                    except Exception as e:
                        log("[REM:%s] restore write FAILED: %s (will retry next tamper reading)" % (TAG, e))
                        feed("RESTORE_FAIL", level=round(seen, 1), error=str(e))
                    lvl = last_good
                elif BAND_LO <= lvl <= BAND_HI:
                    last_good = lvl
                status(online=1, level=round(lvl, 1), last_good=round(last_good, 1), restores=restores, source="mqtt")
                prev = lvl
        except Exception as e:
            log("[REM:%s] telemetry stream error: %s -> respawning subscriber" % (TAG, e))
        finally:
            try: proc.terminate()
            except Exception: pass
        status(online=0, last_good=round(last_good, 1), restores=restores, source="mqtt")
        time.sleep(1.0)

# ── SOURCE = s7t : TRANSIENT S7 read+write each cycle (PLC2 — never holds a 2nd persistent slot) ────────────────────────
def run_s7_transient():
    POLL_T = P.get("poll", 1.0)
    last_good = SEED; prev = SEED; restores = 0; consec_fail = 0; announced = False
    while True:
        c = None
        try:
            c = snap7.client.Client(); c.connect(HOST, 0, 1)
            lvl = s7_read(c)
            if not announced:
                log("[REM:%s] ONLINE via transient S7 (%s) - fresh connect+read each cycle; restore last-good on tamper" % (TAG, HOST))
                feed("ONLINE", host=HOST, source="s7t"); announced = True
            consec_fail = 0
            if tampered(lvl, prev):
                seen = lvl; s7_write(c, last_good); restores += 1
                log("[REM:%s] TAMPER (Level=%.1f, prev %.1f) -> RESTORED last-good %.1f   [restores %d]"
                    % (TAG, seen, prev, last_good, restores))
                feed("RESTORED", level=round(seen, 1), prev=round(prev, 1), last_good=round(last_good, 1), restores=restores)
                lvl = last_good
            elif BAND_LO <= lvl <= BAND_HI:
                last_good = lvl
            status(online=1, level=round(lvl, 1), last_good=round(last_good, 1), restores=restores, source="s7t")
            prev = lvl
        except Exception as e:
            consec_fail += 1
            if consec_fail == 1 or consec_fail % 15 == 0:
                log("[REM:%s] transient read miss: %s (x%d, will retry)" % (TAG, e, consec_fail))
            if consec_fail >= 3:
                status(online=0, last_good=round(last_good, 1), restores=restores, source="s7t")
        finally:
            try:
                if c is not None: c.disconnect()
            except Exception: pass
        time.sleep(POLL_T)

def main():
    if SOURCE == "mqtt":       run_mqtt()
    elif SOURCE == "s7t":      run_s7_transient()
    else:                      run_s7()
if __name__ == "__main__":
    main()
