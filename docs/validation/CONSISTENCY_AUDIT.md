# CARS — Cross-device / cross-file consistency audit
_2026-07-24. Reconciles every identity + policy source: engine `REGISTRY`/`BINDINGS`/`CRITICALITY`/seeds (Dell#2 code), runtime
`rulebook.json`+`a2_policy.json` (Dell#2, authoritative), dashboard `ROLE`/`CRIT` (Dell#1), Snort `cars.rules` (Dell#1), seams (Dell#1)._

## 1. Identity cross-reference matrix (per IP, across every source)
Legend: R=engine REGISTRY role, D=dashboard ROLE, ACL=criticality (engine==dashboard), G=GUARD binding, AL=in runtime allowlist, DPI=has Snort rule.
| IP | R (engine) | D (dash) | ACL | G bind | AL (runtime) | DPI target | consistent? |
|----|-----------|----------|-----|--------|--------------|-----------|-------------|
| 192.168.2.10 PLC1 | plc | plc | CRITICAL | dpid1:1 | dst ×5 | S7+SUSPECT+S7CommPlus | ✅ |
| 192.168.2.9 HMI1 | hmi | hmi | HIGH | dpid1:2 | src→.2.10 | SUSPECT | ✅ |
| 192.168.3.10 PLC2 | plc | plc | HIGH | (NAT, none) | dst←.3.66 | S7 | ✅ |
| 192.168.3.9 HMI2 | hmi | hmi | MEDIUM | (NAT, none) | – | SUSPECT | ✅ |
| 192.168.2.30 Historian | historian | historian | MEDIUM | dpid3:3 | – | – | ✅ |
| 192.168.2.20 Modbus PLC | plc | **MISSING** | LOW | – | dst | Modbus ×8 | ⚠ F1 |
| 192.168.2.31 Operator | supervisory | **MISSING** | (LOW dflt) | – | src ×2 | – | ⚠ F1 |
| 192.168.2.55 EWS | ews | ews | (LOW dflt) | – | src→.2.10 | – | ✅ |
| 192.168.2.45 Remediation | remediation | remediation | (LOW dflt) | – | src→.2.10 | – | ✅ |
| 192.168.2.77 Insider(Kali) | supervisory | **MISSING** | (LOW dflt) | – | **src ×2** | – | ⚠ F1,F4 |
| 192.168.2.66 Attacker | unknown | unknown | (LOW dflt) | – | – | – | ✅ |
| 192.168.2.1 OT-FW/gateway | gateway | gateway | (LOW dflt) | – | – | – | ✅ |
| 192.168.3.66 Cell-2 eng | supervisory | **MISSING** | (LOW dflt) | – | src→.3.10 | – | ⚠ F1 |
| 192.168.3.1 Cell-2 GW | **(not in engine)** | cell2gw | – | – | – | – | ⚠ F1 (display-only) |
| 192.168.3.99 Honeypot | (not registered) | – | – | – | – | – | ok (deception decoy) |

## 2. Policy-file reconciliation
- **Runtime `rulebook.json` (29 rows) vs code `RULEBOOK` seed (27 rows):** runtime has **2 extra rows** — `remediation→plc CONTROL OPERATIONAL` and `remediation→plc any OPERATIONAL` (authorise the .2.45 agent) — that the **code seed lacks**. Runtime also has `ews→plc/hmi SENSITIVE` (matches code v0.7, Option A ✅).
- **Runtime `a2_policy.json` (8 allow) vs code `ALLOWLIST` seed (4):** runtime has **4 extra conduits** the code seed lacks: `.2.77→.2.10:102`, `.2.77→.2.20:502`, `.2.55→.2.10:102`, `.2.45→.2.10:102`. `default_deny` matches (`null→.2.20`, `dpid1→.2.10`).
- **CRITICALITY:** engine `CRITICALITY` == dashboard `CRIT` (6 assets identical) ✅.
- **GUARD BINDINGS:** protected set `{.2.9, .2.10, .2.30}` — the real endpoints on their access ports; Cell-2 clones + sources correctly unbound ✅.
- **Snort DPI targets** `{.2.10, .2.9, .3.10, .3.9, .2.20}` ⊆ engine PLC/HMI assets ✅ (HMIs get only SUSPECT-SYN, no op-DPI — S7CommPlus honest boundary G3 ✅). *(Note: the `CARS-SUSPECT TCP PLC1` SYN rule is why the IT/gateway attacker produced a `TCP => BLOCK` in C.4 — resolved.)*

## 3. Findings
| # | Sev | Finding | Fix | Status |
|---|-----|---------|-----|--------|
| **F1** | MED | **Dashboard `ROLE` map drifted from engine `REGISTRY`.** Missing `.2.20`(plc), `.2.31`(supervisory), `.2.77`(supervisory), `.3.66`(supervisory) → dashboard labelled them `unknown`/attacker glyph, mis-representing the Modbus PLC + operator as hostile. | Synced master `ROLE` + `TYPEOF` (added `supervisory:'sup'`) + `hlabel` to the registry; `.3.1` kept as modelled NAT node. | **FIXED in master** (deploy+restart+cache-bust pending) |
| **F2** | MED (resilience) | **Code seeds drifted from authoritative runtime JSON.** A cold re-seed would (a) classify the remediation agent's restores `FORBIDDEN` (agent breaks) and (b) drop the `.2.45/.2.55/.2.77` allowlist conduits. | Added +2 remediation `RULEBOOK` rows (index 2-3, before dangerous-ops block) + 4 `ALLOWLIST` conduits. **Verified: seed==runtime (29 rules, 8 conduits).** | **FIXED in master** (redeploy engine pending) |
| **F3** | LOW | **6 dead `scada` rulebook rows** — no IP has role `scada`, never match. | Kept as harmless future-proofing (a `scada`-role asset can be added later). | Accepted |
| **F4** | INFO (intentional) | **`.2.77` (Kali insider) allowlisted** to `.2.10:102` + `.2.20:502` — deliberate *test conduit* (VD-1) so A3+criticality can be exercised on the insider. | Documented as test-only in the seed comment; remove for a "production" snapshot. | Accepted (test) |
| **F5** | INFO | `.2.20` LOW but absent from dashboard `ROLE`. | Subsumed by F1. | **FIXED (F1)** |
| **N1** | MED (audit gap) | **Snort's active config is `/etc/snort/cars.conf`** (systemd ExecStart `-c /etc/snort/cars.conf`), NOT `snort.conf` (the uploaded `snort.conf` is the stock Debian default and is not what runs). **RESOLVED (cars.conf read):** it is a minimal custom config — `var HOME_NET 192.168.2.0/24`, `var EXTERNAL_NET any`, `include /etc/snort/cars.rules`. Note (a) HOME_NET is the **OT subnet .2.0/24** (tighter than stock `any`), harmless since every `cars.rules` rule uses explicit dst IPs (incl. the .3.x Cell-2 rules) not `$HOME_NET`; (b) **`cars.rules` is included from `/etc/snort/cars.rules`** (root of /etc/snort), so that is the deploy target — NOT `/etc/snort/rules/`. | Confirmed correct; deploy `cars.rules` to `/etc/snort/cars.rules`. | **CLOSED** |
| **N2** | LOW (coverage) | **Cell-2 S7 DPI asymmetry.** Cell-1 (.2.10) has both S7 control-start `0x28` (sid 1000043) and stop `0x29`; Cell-2 (.3.10) had only stop `0x29` (sids 1000045-47) — a control-start on PLC2 would be missed. | Added `sid:1000048` `CARS-S7-DIAG-control` for `.3.10:102`. | **FIXED in master `cars.rules`** (deploy+reload pending) |
| **N3** | LOW (config) | **Duplicate `192.168.2.66`** on ovsgw: `att0` (base-ns) AND `atkns/atk` both carried `.2.66`. NOT vestigial — `att0` is used by `mttm.py` (base-ns because it needs the controller API `10.10.10.1:8080`, which `atkns` can't reach per C.8); `atkns/.2.66` is the canonical attacker for ~10 forensic/validate scripts. Both UP → standing ARP ambiguity (att0 showed 24k dropped RX). | **FIXED (Option A):** `att0` renumbered to `.2.67` (persistent in `cars-seams.service` + live) and `mttm.py SRC=.2.67`; `atkns` keeps the canonical `.2.66`. MTTM still measures an unlisted attacker→PLC1 (latency-equivalent; SUSPECT rules are dst-keyed). | **FIXED** |

## 4. What is already consistent (the reassuring half)
Criticality (engine==dashboard), GUARD bindings, DPI targets ⊆ registry, the runtime rulebook (Option A + remediation auth), the default-deny scoping (`.2.10` on dpid1 only for the NAT path), and the seam IPs (`att0`.2.66 / `sup0`.2.30 / `ins2`.3.66 + netns opns/atkns/remns/hpotns/mbns) all line up with their intended roles.

## 5. Recommended reconciliation actions (in order)
1. ~~**F2 — align code seeds to runtime**~~ **DONE** (seed==runtime verified: 29 rules, 8 conduits).
2. ~~**F1 — sync dashboard `ROLE`/`TYPEOF`**~~ **DONE** (added `.2.20/.2.31/.2.77/.3.66` + `supervisory` glyph).
3. ~~**N2 — Cell-2 0x28 DPI**~~ **DONE** (sid 1000048 added to master `cars.rules`).
4. **F4/F3 — policy intent:** keep `.2.77` allowlisted (test) or remove (production snapshot); `scada` rows kept as future-proofing.
5. **N1/N3 — need user:** upload `/etc/snort/cars.conf`; decide the `.2.66` `att0`/`atkns` duplicate.

After deploying the master edits, one line is true: *every identity, role, criticality, binding, conduit, and DPI target is consistent across all three devices* — with two open items (cars.conf upload, .2.66 dedup) that don't affect running behaviour.

## 6. Deep-audit results — file-by-file (deployed vs E:\ master)
Every uploaded deployed artifact was diffed against its master:
| File | Device | Result |
|------|--------|--------|
| `cars_engine.py` | Dell#2 | Functionally **identical** to master (maint-window fix present); only comment/whitespace drift. Master now also carries the F2 seed rows. |
| `cars_dashboard.py` (plain) | — | **Stale backup** — lacks steadiness fix, REMEDIATE mode, and criticality badge. **Non-authoritative.** |
| `cars_dashboard-31045dcf.py` | Dell#1 | **Byte-identical to master** → confirms the criticality **badge + steadiness fix ARE deployed** ✅. This is the running copy. |
| `snort_bridge.py` | Dell#1 | Functionally identical (comment drift only) ✅ |
| `cars_remediation.py` | Dell#1 (remns) | Functionally identical (ASCII vs em-dash punctuation only) ✅ |
| `mb_server.py` | Dell#1 (mbns) | Functionally identical; register map `hr[8]=4242` "safety-critical" demo register present ✅ |
| `cars.rules` | Dell#1 | Full DPI ruleset confirmed (SUSPECT ×8, Modbus ×8, S7 classic ×4, S7CommPlus ×1, Cell-2 S7 ×3). N2 gap fixed in master. |

**Service wiring confirmed (Dell#1):** the **CC-76 fix is correctly deployed** — `cars-bridge` drop-in `After=/PartOf=cars-snort.service` + `Restart=on-failure`, and `cars-snort` drop-in `Wants=cars-bridge.service`. So a Snort restart now cascades a bridge restart (bridge no longer silently dies). `cars-bridge.service` base: `Requires=cars-snort.service`, `ExecStart=python3 -u snort_bridge.py`.

**Seam→identity map (Dell#1 ovsgw, from live `ip`):** `opns/opr`=.2.31, `atkns/atk`=.2.66, `remns/rem0`=.2.45, `hpotns/hpot`=.3.99, `mbns/mbplc`=.2.20, base `sup0`=.2.30, base `att0`=.2.66 (**dup — N3**), base `ins2`=.3.66, `vmnet2`=Kali insider (.2.77). All match the registry (post-F1).

**Cell-2 setup location RESOLVED:** `cars-cell2.service` (oneshot) runs **`/usr/local/sbin/cars-cell2.sh`** on Dell#3 — this is why `ls ~/*.sh` found nothing there. NAT confirmed: DNAT `.3.10→.2.10` (PREROUTING -i eth0), MASQUERADE -o `cell2gw`(.2.1). `.2.1` is shared by `cell2gw` (Dell#3) and the OT-FW/gateway (GNS3, Dell#1) — both "gateway", acceptable (N4, info-only).
