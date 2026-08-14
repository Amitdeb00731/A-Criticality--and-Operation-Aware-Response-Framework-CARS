#!/usr/bin/env python3
# Gap 2 patcher -- applies the conduit-BLOCK-at-shared-identity change to
# cars_engine.py safely. Run on Dell 2 in the directory that holds cars_engine.py:
#     python3 patch_gap2.py /path/to/cars_engine.py
# Backs up to <file>.bak.gap2, applies both edits, and py_compile-checks the result.
import re, sys, shutil, py_compile

f = sys.argv[1] if len(sys.argv) > 1 else "cars_engine.py"
s = open(f).read()
assert "def select_response" in s, "not the engine file?"

if "SHARED_ROLES" in s:
    print("SHARED_ROLES already present -- skipping constant insert")
else:
    anchor = 'RESPONSES = ("ALLOW", "MONITOR", "THROTTLE", "DEFLECT", "ISOLATE", "BLOCK", "REFUSE")'
    assert anchor in s, "RESPONSES anchor not found"
    s = s.replace(anchor,
        anchor + '\nSHARED_ROLES = {"gateway"}   # Gap-2: NAT/collapse points -> conduit BLOCK, never whole-source ISOLATE',
        1)

pat = re.compile(
    r'        if flood:\n'
    r'            return "ISOLATE"\n'
    r'        if dcw >= 3: return "ISOLATE"[^\n]*\n'
    r'        return "BLOCK" if src_count < esc else "ISOLATE"')
new = (
    '        # Gap-2: a SHARED / NAT-collapsed identity (the IT gateway) must NOT be\n'
    '        # source-isolated -- that quarantines every host behind the NAT. Cut only\n'
    '        # the offending conduit (BLOCK); a true single host still gets ISOLATE.\n'
    '        shared = s_role in SHARED_ROLES\n'
    '        if flood:\n'
    '            return "BLOCK" if shared else "ISOLATE"\n'
    '        if dcw >= 3:\n'
    '            return "BLOCK" if shared else "ISOLATE"               # CRITICAL asset\n'
    '        if shared:\n'
    '            return "BLOCK"\n'
    '        return "BLOCK" if src_count < esc else "ISOLATE"')
s2, n = pat.subn(new, s)
assert n == 1, "FORBIDDEN branch not matched exactly (n=%d) -- do not proceed, tell Claude" % n

shutil.copy(f, f + ".bak.gap2")
open(f, "w").write(s2)
py_compile.compile(f, doraise=True)
print("[gap2] patched OK; backup at %s.bak.gap2" % f)
print("[gap2] restart the controller, then green-check.")
