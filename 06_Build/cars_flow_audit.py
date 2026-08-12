#!/usr/bin/env python3
# cars_flow_audit.py  —  #28 / New candidate A: FLOW-INTEGRITY (policy) CHECKER.
#
# WHY (grounded in the literature): Melis et al. (Bologna, "A Policy Checker Approach for Secure Industrial SDN") verify SDN
# forwarding integrity to catch bogus injected flow-rules, removals, loops and black-holes "notoriously difficult to detect via
# normal network scans". Gardiner et al. (Bristol, "Controller-in-the-Middle") show a compromised controller can silently
# inject/remove flow-rules and break a process. A stateless firewall/IPS cannot self-verify its own forwarding state; CARS can.
# This checker is that defensive pair: it holds a TRUSTED BASELINE of the immutable security policy and alarms on any drift.
#
# MODEL (classify, don't pre-filter - so nothing evades by using an unexpected cookie):
#   IMMUTABLE POLICY  = table 0 (GUARD, all rules) + table 1 cookie 0xa2 (A2 stateful allowlist/default-deny/ct pipeline).
#                       Baselined at a trusted start; MISSING (removed) or CHANGED (action rewritten) => DRIFT.
#   LEGIT DYNAMIC     = table 1, cookie 0x0, priority 100-110 (CARS reactive isolate/block) — the ONLY allowed live additions.
#   EVERYTHING ELSE in table 0/1 that is not in the baseline and not a legit reactive rule => EXTRA (bogus injection) => DRIFT.
#   (table 2 L2-learn is intentionally never inspected — it changes every packet.)
#
# USAGE:
#   Baseline (right after a trusted controller start):  sudo python3 cars_flow_audit.py --baseline --bridges ovs1,ovsgw
#   One-shot check (exit 0=clean, 2=DRIFT):            sudo python3 cars_flow_audit.py --check    --bridges ovs1,ovsgw
#   Daemon (periodic; drift -> feed + controller audit): sudo python3 cars_flow_audit.py --watch 10 --bridges ovs1,ovsgw
import subprocess, re, json, sys, time, argparse, os, urllib.request

BASELINE = "/home/msclab/cars/flow_baseline.json"
FEED     = "/tmp/cars_flowaudit.jsonl"          # drift events (operator/dashboard can tail)
STATUS   = "/tmp/cars_flowaudit_status.json"    # live one-line state
CARS_API = "http://10.10.10.1:8080"             # optional: surface drift into the controller decision log
OFCTL    = ["ovs-ofctl", "-O", "OpenFlow13"]

VOLATILE = re.compile(r'\b(duration|n_packets|n_bytes|idle_age|hard_age|idle_timeout|hard_timeout)=[^,]*,?\s*')

def dump(bridge, table):
    r = subprocess.run(OFCTL + ["dump-flows", bridge, "table=%d" % table], capture_output=True, text=True)
    return r.stdout.splitlines()

def parse(line):
    """-> (table, priority:int, cookie, match, actions), volatile fields stripped; or None."""
    line = line.strip()
    if not line or "actions=" not in line:
        return None
    left, actions = line.split(" actions=", 1)
    m_ck = re.search(r'cookie=(0x[0-9a-fA-F]+)', left)
    m_tb = re.search(r'table=(\d+)', left)
    m_pr = re.search(r'priority=(\d+)', left)
    cookie = (m_ck.group(1) if m_ck else "0x0").lower()
    table  = m_tb.group(1) if m_tb else "?"
    prio   = int(m_pr.group(1)) if m_pr else 0
    idx = left.find("priority=")
    match = left[idx:] if idx >= 0 else left.split(", ")[-1]
    match = VOLATILE.sub("", match).strip().rstrip(",")
    return (table, prio, cookie, match, VOLATILE.sub("", actions).strip())

def key_of(br, s):
    return "%s|t%s|p%s|c%s|%s" % (br, s[0], s[1], s[2], s[3])   # identity = bridge,table,priority,cookie,match (NOT actions)

def is_reactive(s):  # CARS reactive isolate/block/throttle/deflect — identified by the DISTINCT reactive cookie 0xca (CC-95).
    return s[2] == "0xca"
# NOTE: baseline captures ALL non-reactive table0/table1 rules at a trusted start (GUARD cookie0x0, A2 cookie0xa2, static
# prio-0 miss). Anything that is not cookie-0xca appearing later = bogus injection => flagged. This CLOSES the earlier
# blind spot: a bogus rule hiding at cookie0x0/prio100-110 is no longer mistaken for reactive and is caught as EXTRA.

def is_infra(s):  # os-ken topology/discovery internals (LLDP 0x88cc, or any controller-punt) — NOT CARS security policy.
    return ("CONTROLLER" in s[4]) or ("0x88cc" in s[3])   # excluded so the checker watches only GUARD + A2, not os-ken infra.

def collect(bridges):
    sigs = {}
    for br in bridges:
        for tbl in (0, 1):
            for ln in dump(br, tbl):
                s = parse(ln)
                if s and not is_infra(s):
                    sigs[key_of(br, s)] = s
    return sigs

def feed(ev, **kw):
    kw["event"] = ev; kw["ts"] = time.time()
    try:
        with open(FEED, "a") as f: f.write(json.dumps(kw) + "\n")
        os.chmod(FEED, 0o644)
    except Exception: pass

def status(**kw):
    kw["ts"] = time.time()
    try:
        with open(STATUS, "w") as f: json.dump(kw, f)
        os.chmod(STATUS, 0o644)
    except Exception: pass

def post_audit(kind, detail):
    """Best-effort: surface drift into the controller decision log (schema-shaped like the guard alert)."""
    try:
        body = json.dumps({"src": "0.0.0.0", "src_role": "flowaudit", "dst": "0.0.0.0", "dst_role": "policy",
                           "proto": "OF", "op": "DRIFT", "tier": "FORBIDDEN", "response": "REFUSE",
                           "decision": "flow-integrity",
                           "action": "REFUSED (flow-integrity:%s) - %s" % (kind, detail)}).encode()
        req = urllib.request.Request(CARS_API + "/cars/flowaudit", data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        pass   # optional endpoint; feed file + stdout are the primary channel

def check(base, live):
    missing = {k: base[k] for k in base if k not in live}                                  # removed (black-hole risk)
    changed = {k: (base[k], live[k]) for k in base if k in live and base[k][4] != live[k][4]}  # action rewritten
    extra = {k: s for k, s in live.items() if not is_reactive(s) and k not in base}        # bogus injected (any non-reactive)
    return missing, extra, changed

def report(missing, extra, changed, emit=False):
    if not (missing or extra or changed):
        print("[FLOW-AUDIT] CLEAN - live policy matches trusted baseline (reactive isolates ignored)")
        status(ok=1, missing=0, extra=0, changed=0)
        return 0
    print("[FLOW-AUDIT] *** DRIFT DETECTED *** missing=%d extra=%d changed=%d" % (len(missing), len(extra), len(changed)))
    for k in missing: print("  [MISSING - policy rule removed] %s => %s" % (k, missing[k][4]))
    for k in extra:   print("  [EXTRA   - bogus rule injected] %s => %s" % (k, extra[k][4]))
    for k, (b, l) in changed.items(): print("  [CHANGED - action modified    ] %s : %s -> %s" % (k, b[4], l[4]))
    if emit:
        for k in missing: feed("MISSING", key=k, was=missing[k][4]); post_audit("policy-removed", k)
        for k in extra:   feed("EXTRA",   key=k, now=extra[k][4]);   post_audit("bogus-injected", k)
        for k, (b, l) in changed.items(): feed("CHANGED", key=k, was=b[4], now=l[4]); post_audit("action-modified", k)
    status(ok=0, missing=len(missing), extra=len(extra), changed=len(changed))
    return 2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bridges", default="ovs1,ovsgw")
    ap.add_argument("--baseline", action="store_true", help="capture trusted baseline and exit")
    ap.add_argument("--check", action="store_true", help="one-shot diff vs baseline")
    ap.add_argument("--watch", type=int, default=0, help="daemon: check every N seconds")
    ap.add_argument("--baseline-file", default=BASELINE)
    a = ap.parse_args()
    bridges = [b for b in a.bridges.split(",") if b]

    if a.baseline:
        live = collect(bridges)
        pol = {k: s for k, s in live.items() if not is_reactive(s)}
        json.dump({"bridges": bridges, "captured": time.time(), "flows": pol},
                  open(a.baseline_file, "w"), indent=2)
        print("[FLOW-AUDIT] baseline captured: %d static-policy flows across %s -> %s" % (len(pol), bridges, a.baseline_file))
        return 0

    if not os.path.exists(a.baseline_file):
        sys.exit("[FLOW-AUDIT] no baseline at %s - run --baseline first (after a trusted controller start)" % a.baseline_file)
    base = {k: tuple(v) for k, v in json.load(open(a.baseline_file))["flows"].items()}

    if a.watch:
        print("[FLOW-AUDIT] watching every %ds (bridges=%s)" % (a.watch, bridges))
        while True:
            report(*check(base, collect(bridges)), emit=True)
            time.sleep(a.watch)
    else:
        return report(*check(base, collect(bridges)), emit=a.check)

if __name__ == "__main__":
    sys.exit(main())
