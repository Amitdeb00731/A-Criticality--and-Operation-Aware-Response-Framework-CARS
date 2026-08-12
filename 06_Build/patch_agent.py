import os, py_compile
P = os.path.expanduser('~/cars_remediation.py')
s = open(P, encoding='utf-8').read()
PAIRS = [
  ('import snap7, time, struct\nHOST = "192.168.2.10"; DB = 7; OFFSET = 0',
   'import snap7, time, struct, json, os\nHOST = "192.168.2.10"; DB = 7; OFFSET = 0\nFEED = "/tmp/cars_remediation.jsonl"       # append-only event log (ONLINE, RESTORED) \u2014 dashboard tails this\nSTATUS = "/tmp/cars_remediation_status.json"  # live one-line state (level, last-good, restores) \u2014 dashboard reads this\ndef feed(ev, **kw):\n    kw["event"] = ev; kw["ts"] = time.time()\n    try:\n        with open(FEED, "a") as f: f.write(json.dumps(kw) + "\\n")\n        os.chmod(FEED, 0o644)\n    except Exception: pass\ndef status(**kw):\n    kw["ts"] = time.time()\n    try:\n        with open(STATUS, "w") as f: json.dump(kw, f)\n        os.chmod(STATUS, 0o644)\n    except Exception: pass'),
  ('    print("[REM] state-maintenance agent ONLINE (.2.45) - watching Tank.Level; restore last-good on tamper")\n    last_good = 50.0; prev = 50.0; restores = 0',
   '    print("[REM] state-maintenance agent ONLINE (.2.45) - watching Tank.Level; restore last-good on tamper")\n    feed("ONLINE", host=HOST)\n    last_good = 50.0; prev = 50.0; restores = 0'),
  ('            if tamper:\n                wr(c, last_good); restores += 1\n                print("[REM] TAMPER (Level=%.1f, prev %.1f) -> RESTORED last-good %.1f   [restores %d]"\n                      % (lvl, prev, last_good, restores))\n                lvl = last_good\n            elif BAND_LO <= lvl <= BAND_HI:\n                last_good = lvl        # learn a trustworthy last-good while healthy\n            prev = lvl',
   '            if tamper:\n                seen = lvl\n                wr(c, last_good); restores += 1\n                print("[REM] TAMPER (Level=%.1f, prev %.1f) -> RESTORED last-good %.1f   [restores %d]"\n                      % (seen, prev, last_good, restores))\n                feed("RESTORED", level=round(seen, 1), prev=round(prev, 1),\n                     last_good=round(last_good, 1), restores=restores)\n                lvl = last_good\n            elif BAND_LO <= lvl <= BAND_HI:\n                last_good = lvl        # learn a trustworthy last-good while healthy\n            status(online=1, level=round(lvl, 1), last_good=round(last_good, 1), restores=restores)\n            prev = lvl'),
]
for old, new in PAIRS:
    if new in s: continue
    n = s.count(old)
    assert n == 1, 'anchor: %r (%d)'%(old[:40],n)
    s = s.replace(old,new,1)
open('/tmp/_ac.py','w',encoding='utf-8').write(s)
py_compile.compile('/tmp/_ac.py',doraise=True)
open(P,'w',encoding='utf-8').write(s)
print('agent patched OK ->',P)
