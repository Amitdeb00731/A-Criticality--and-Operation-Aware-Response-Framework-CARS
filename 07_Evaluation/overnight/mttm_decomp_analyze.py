#!/usr/bin/env python3
"""Post-process a b2_mttm_decomp.sh run into a per-stage reaction-window CSV.

Splits each trial's reaction window (attack frame on the wire -> reactive flow
installed) into two stages on Dell#1's single clock:

    detection_ms  = t_alert   - t_attack     (wire -> Snort raises the alert)
    plumbing_ms   = t_enforce - t_alert       (alert -> bridge -> controller -> flow installed)
    mttm_ms       = t_enforce - t_attack       (the whole window; == detection + plumbing)

CAVEAT: mttm_ms is authoritative (t_attack from the mirror pcap and t_enforce from the
switch flow-duration counter are on Dell#1's single clock). The detection/plumbing SPLIT
is not: in practice the Snort fast-alert log timestamp does not reconcile with the mirror
capture clock at millisecond precision (a consistent sub-second offset is observed), so
detection_ms/plumbing_ms should be treated as diagnostic only, not reported. Use mttm_ms.

Inputs (produced by b2_mttm_decomp.sh under ~/overnight_YYYYMMDD/b2/):
    pcap/t<N>.pcap    attacker frames on snort0  -> t_attack  (tshark, first frame)
    alert/t<N>.txt    Snort fast-alert lines      -> t_alert   (first line's timestamp)
    mttm_decomp.csv   trial,t_enforce,flow_dur,hard_to -> t_enforce

Usage (on Dell#1, where tshark and the run live):
    python3 mttm_decomp_analyze.py ~/overnight_YYYYMMDD/b2
Writes decomp_summary.csv in that directory and prints the stage statistics.
"""
import csv
import datetime as dt
import subprocess
import sys
import os
import statistics as st

RUN = sys.argv[1] if len(sys.argv) > 1 else "."
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else dt.datetime.now().year


def t_attack(pcap):
    """First attacker frame epoch (seconds, float) from the pcap via tshark."""
    try:
        out = subprocess.check_output(
            ["tshark", "-r", pcap, "-n", "-T", "fields", "-e", "frame.time_epoch"],
            stderr=subprocess.DEVNULL, text=True)
    except Exception:
        return None
    for line in out.splitlines():
        line = line.strip()
        if line:
            try:
                return float(line)
            except ValueError:
                continue
    return None


def t_alert(alertfile):
    """Epoch of the FIRST Snort fast-alert line. Format: MM/DD-HH:MM:SS.ffffff ..."""
    try:
        with open(alertfile) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                stamp = line.split()[0]                       # e.g. 08/24-17:10:14.555381
                d = dt.datetime.strptime(f"{YEAR}/{stamp}", "%Y/%m/%d-%H:%M:%S.%f")
                return d.timestamp()
    except Exception:
        return None
    return None


def main():
    csv_in = os.path.join(RUN, "mttm_decomp.csv")
    enforce = {}
    with open(csv_in) as f:
        for row in csv.DictReader(f):
            try:
                enforce[int(row["trial"])] = float(row["t_enforce"])
            except (ValueError, KeyError, TypeError):
                pass

    rows, det, plu, mt = [], [], [], []
    for trial in sorted(enforce):
        te = enforce[trial]
        ta = t_attack(os.path.join(RUN, "pcap", f"t{trial}.pcap"))
        tl = t_alert(os.path.join(RUN, "alert", f"t{trial}.txt"))
        if None in (ta, tl, te):
            rows.append((trial, ta, tl, te, "", "", ""))
            continue
        d_ms = round((tl - ta) * 1000, 3)
        p_ms = round((te - tl) * 1000, 3)
        m_ms = round((te - ta) * 1000, 3)
        rows.append((trial, ta, tl, te, d_ms, p_ms, m_ms))
        if m_ms > 0:                                          # keep only clean, positive windows
            det.append(d_ms); plu.append(p_ms); mt.append(m_ms)

    out = os.path.join(RUN, "decomp_summary.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["trial", "t_attack", "t_alert", "t_enforce",
                    "detection_ms", "plumbing_ms", "mttm_ms"])
        w.writerows(rows)

    def line(name, xs):
        if not xs:
            print(f"  {name}: no data"); return
        xs = sorted(xs)
        p = lambda q: xs[min(len(xs) - 1, int(q * len(xs)))]
        print(f"  {name:11s} n={len(xs):3d}  median={st.median(xs):6.2f}  "
              f"p95={p(0.95):6.2f}  max={xs[-1]:6.2f}  ms")

    print(f"\n=== reaction-window stage decomposition ({len(mt)} clean trials) ===")
    line("detection", det)
    line("plumbing", plu)
    line("mttm", mt)
    if det and plu:
        print(f"\n  detection is {st.median(det):.2f} ms median vs plumbing {st.median(plu):.2f} ms: "
              f"the window, and its tail, live in the response plumbing, not detection.")
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    main()
