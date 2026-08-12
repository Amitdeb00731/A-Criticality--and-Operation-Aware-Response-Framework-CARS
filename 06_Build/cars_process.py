#!/usr/bin/env python3
# cars_process.py — soft co-simulation of a water-tank bang-bang control loop (Cardenas-group style),
# driving the REAL Q0.3 relay on PLC1 over S7, from the AUTHORIZED controller identity .2.40 (role=controller).
# Control law (eq.1): pump=1 if level<=LOW, 0 if level>=HIGH.  Dynamics (eq.2): level += fill/-drain.
# Reasserts Q0.3 EVERY cycle so any attacker flip is corrected; reads it back and reports a health metric
# (readback-vs-intent mismatches = attacker interference that momentarily reached the relay).
#   sudo ip netns exec ctlns python3 /home/msclab/cars_process.py     (Dell#1)
import snap7, time, sys
try:
    from snap7.type import Area; PA = Area.PA
except Exception:
    PA = 0x82
HOST = "192.168.2.10"; LOW = 30.0; HIGH = 70.0; FILL = 6.0; DRAIN = 5.0; DT = 0.5   # DT=0.5s -> 2 ops/s (under A5 flood=5)
def main():
    c = snap7.client.Client(); c.connect(HOST, 0, 1)
    if not c.get_connected():
        print("[CTL] connect FAILED (is .2.40 authorized + allowlisted?)"); sys.exit(1)
    print("[CTL] process controller ONLINE (.2.40) — bang-bang tank level, actuator = Q0.3 relay")
    level = 50.0; pump = False; last = False; cyc = 0; n = 0; bad = 0
    try:
        while True:
            if   level <= LOW:  pump = True
            elif level >= HIGH: pump = False
            level += FILL if pump else -DRAIN
            level = max(0.0, min(100.0, level))
            c.write_area(PA, 0, 0, bytearray([0x08 if pump else 0x00]))     # actuate + reassert
            got = c.read_area(PA, 0, 0, 1)[0] & 0x08                        # read the real relay back
            n += 1
            if (got != 0) != pump: bad += 1                                # relay != controller intent = interference
            if pump != last: cyc += 1; last = pump
            print("[CTL] level=%5.1f  pump=%-3s  cycles=%d  relay=%-3s  interference=%d/%d"
                  % (level, "ON" if pump else "off", cyc, "ON" if got else "off", bad, n))
            time.sleep(DT)
    except KeyboardInterrupt:
        c.write_area(PA, 0, 0, bytearray([0x00])); c.disconnect()
        print("\n[CTL] stopped. pump off. actuations=%d  interference-events=%d" % (n, bad))
if __name__ == "__main__":
    main()
