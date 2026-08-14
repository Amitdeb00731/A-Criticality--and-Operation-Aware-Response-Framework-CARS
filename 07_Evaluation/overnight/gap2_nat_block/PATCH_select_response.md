# Gap 2 patch — conduit-BLOCK, not source-ISOLATE, at a shared/NAT identity

**Problem.** Pivot A (the IT attacker) is source-NATed onto the single gateway
identity `192.168.2.1`. Because the destination PLC is CRITICAL, the engine
escalates straight to **ISOLATE source** (`select_response`, FORBIDDEN branch,
`dcw>=3`). That installs `nw_src=192.168.2.1 actions=drop` — which quarantines
*every* host behind the NAT for 75 s, i.e. all legitimate north-south IT/OT
traffic (historian pulls, remote monitoring, logistics). A self-inflicted DoS.

**Fix.** A NAT-collapsed / shared identity must be cut at the **conduit** level
(BLOCK = `nw_src=.1, nw_dst=PLC` drop), not the source level, so only the
PLC-bound flow from the gateway is severed and the other gateway traffic keeps
flowing. True single hosts (Pivot B, `192.168.2.77`) still get the fine-grained
source ISOLATE. Minimal change, keyed on the resolved role.

## Change 1 — add a constant near the other response constants (~line 60)

```python
SHARED_ROLES = {"gateway"}   # Gap-2: NAT/collapse points -> cut the conduit, never the whole source
```

## Change 2 — `select_response()` FORBIDDEN branch (~lines 399-403)

Replace:

```python
        # FORBIDDEN: one command can harm -> block now; isolate the source on persistence.
        if flood:
            return "ISOLATE"
        if dcw >= 3: return "ISOLATE"                             # CRITICAL asset: isolate the source immediately
        return "BLOCK" if src_count < esc else "ISOLATE"
```

with:

```python
        # FORBIDDEN: one command can harm -> block now; isolate the source on persistence.
        # Gap-2: a SHARED / NAT-collapsed identity (e.g. the IT gateway) must NOT be
        # source-isolated -- that quarantines every host behind the NAT (a self-inflicted
        # DoS on all north-south traffic). For such an identity cut only the offending
        # conduit (BLOCK = src+dst drop); a true single host still gets the source ISOLATE.
        shared = s_role in SHARED_ROLES
        if flood:
            return "BLOCK" if shared else "ISOLATE"
        if dcw >= 3:
            return "BLOCK" if shared else "ISOLATE"               # CRITICAL asset
        if shared:
            return "BLOCK"
        return "BLOCK" if src_count < esc else "ISOLATE"
```

## Expected behaviour after the patch

| Attacker | Seen as | Response before | Response after | Collateral |
|----------|---------|-----------------|----------------|------------|
| Pivot A (IT, NATed) | `192.168.2.1` (gateway) | ISOLATE source `.1` (all gateway traffic cut 75 s) | **BLOCK conduit `.1 -> PLC`** (only the PLC-bound flow cut) | legit IT/OT gateway traffic survives |
| Pivot B (on-segment) | `192.168.2.77` (unknown) | ISOLATE source `.77` | ISOLATE source `.77` (unchanged) | none — true host, correct |

The attacker still lands **zero writes** on the PLC in both cases (the conduit to
`:102` is forbidden and dropped); the only change is that Pivot A no longer takes
the whole enterprise conduit down with it.

Note: the honest residual is that a single BLOCK cannot distinguish the rogue IT
host from the legitimate IT hosts sharing the NAT for *that same PLC conduit*, so
a legitimate IT->PLC conduit (if one existed) would also be cut. On this testbed
no legitimate IT host has an allowlisted PLC conduit, so the BLOCK is collateral-
free; true per-host attribution across a NAT still needs the OT firewall to pass
the real source (future work).
