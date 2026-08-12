# CARS — Asset-Criticality Framework (two-place: decision + response)
_2026-07-24. Design lock. Introduces per-asset criticality that participates in BOTH the decision and the response, grounded in
established methodologies (not an invented scheme), bounded by two safety invariants so strictness never becomes a self-inflicted outage._

## 1. The gap this closes
CARS is "criticality-aware", but until now criticality lived only on the **operation** (CONTROL vs READ) and the **role** (plc vs hmi).
Every PLC was treated identically. A supervisor observation: assets differ in importance — PLC1 (a safety-critical primary process)
warrants a stricter, faster, stickier response than PLC2 (a downstream buffer). This framework adds the missing axis: **per-asset
consequence-based criticality**, applied to both what CARS decides and how it responds.

## 2. How criticality is DERIVED (recognised methods, three lenses)
The Asset Criticality Level (ACL) of a protected asset is the **max** across three established lenses:
1. **INL Consequence-driven Cyber-informed Engineering (CCE)** — *primary driver.* Consequence-prioritisation: what is the worst
   physical/operational impact if this asset fails/is compromised? (safety hazard > production loss > moderate > minor).
2. **CISA OT Asset Inventory Guidance (2025) — criticality-based + function-based classification** — the recognised tiering schema
   (Critical/High/Medium/Low) and function taxonomy (control / monitoring / supervisory / …). The tank process maps to CISA's
   **Water/Wastewater** conceptual taxonomy.
3. **Attack-path centrality (the "path-usage" idea)** — a quantitative modifier: an asset that is a dependency chokepoint / pivot
   (high betweenness, many dependents) is bumped up (e.g., the historian as a pivot into OT).

_ACL is a property of the **protected (destination) asset** — the thing CARS defends. It is orthogonal to source **trust/role**._

## 3. ACL scale
| Level | weight `cw` | CCE consequence meaning |
|---|---|---|
| **CRITICAL** | 3 | failure = safety/mission hazard (e.g., overflow) |
| **HIGH** | 2 | major operational / production impact |
| **MEDIUM** | 1 | moderate impact |
| **LOW** | 0 | minor / support / test asset |

## 4. Assignment for the testbed (auditable)
| Asset | IP | CISA function | Consequence (CCE) | centrality | **ACL** |
|---|---|---|---|---|---|
| PLC1 (primary tank) | 192.168.2.10 | control | overflow / safety hazard | primary path | **CRITICAL** |
| PLC2 (downstream buffer) | 192.168.3.10 | control | production loss, no safety hazard | secondary | **HIGH** |
| HMI1 (critical-tank view) | 192.168.2.9 | monitoring | loss of operator visibility on critical process | — | **HIGH** |
| HMI2 | 192.168.3.9 | monitoring | loss of visibility (secondary) | — | **MEDIUM** |
| Historian/SCADA | 192.168.2.30 | supervisory | data loss + **pivot chokepoint** | pivot bump | **MEDIUM** |
| Modbus sim | 192.168.2.20 | control (test) | test asset | — | **LOW** |
| _anything unlisted_ | — | — | — | — | **LOW** (safe default → behaves as today) |

## 5. Two safety invariants (criticality NEVER overrides these)
Because in ICS **over-blocking a critical asset's legitimate traffic is itself the outage**, strictness is bounded by:
- **I1 — Safety cap:** the `hmi↔plc` control loop stays `CRITICAL → REFUSE` (never enforced). Blocking it = the incident.
- **I2 — Proven-legit visibility:** explicitly **allowlisted conduits** and **trusted monitoring READs** stay permitted. Blocking the
  historian's read of the critical tank = self-inflicted loss of visibility. (Note: I2 preserves the *conduit and reads*; it does NOT
  grant WRITE authority — see §6.)

## 6. Criticality in the DECISION (surgical tier-elevation)
After the operation-based `classify()` returns a tier, criticality **raises** it in the grey zone, bounded by I1/I2:
- **On a CRITICAL asset, a trusted actuating WRITE (`SENSITIVE`) is elevated to `FORBIDDEN`** — *nothing but the closed control loop
  and an authorised maintenance window may write to the safety-critical process.* A supervisory/historian/EWS write to PLC1, only
  `SENSITIVE` before, is now `FORBIDDEN` → blocked/isolated.
- **READs (`OPERATIONAL`) are never elevated** (I2 — monitoring must survive). **The loop (`CRITICAL/REFUSE`) is never elevated** (I1).
- **Maintenance window still governs**: inside an authorised window the elevation is suspended (the write is permitted-with-monitoring),
  and recognised dangerous eng ops (CONTROL/DIAG/PROGRAM) are waived as before.
- HIGH/MEDIUM/LOW assets: **no** tier elevation (classification unchanged); criticality shows only in the response.

_This closes the concrete air-gap: a **trusted-but-not-loop** source (compromised supervisory, historian, mis-scoped EWS) writing to
the critical PLC used to be merely `SENSITIVE` (throttle-then-block); it is now `FORBIDDEN` on the critical asset._

## 7. Criticality in the RESPONSE (proportional aggression)
With `cw` of the destination asset (`select_response` + enforcement):
| Knob | Rule | Effect |
|---|---|---|
| Escalation speed | `esc = max(1, ESCALATE − cw)` | CRITICAL → ISOLATE after 1 offence; LOW → after 3 (today) |
| Response floor | CRITICAL: FORBIDDEN→**ISOLATE now**, SENSITIVE→**BLOCK now** | harsher first response on high-consequence assets |
| Flood | CRITICAL + OPERATIONAL-flood → **BLOCK** (not THROTTLE) | DoS on the critical tank is cut, not just rate-limited |
| Block duration | `hard_timeout = 30 + cw·15` s | CRITICAL 75 · HIGH 60 · MED 45 · LOW 30 — protection is stickier |
| Triage priority *(optional v2)* | reactive flow priority `100 + cw` | critical-asset blocks resist displacement |
| Safety cap | **unchanged** | REFUSE loop invariant untouched |

## 8. Integration points (in `cars_engine.py`)
- `CRITICALITY = {ip: level}`, `CW = {level: weight}`, helpers `crit_of(ip)` (default LOW), `cw_of(ip)`.
- `respond()`: after `classify()`, apply §6 elevation (bounded by the maintenance window), then pass `cw` to `select_response()` and a
  criticality-scaled `hard_timeout` to enforcement; surface `[CRIT:<acl>]` (+`,elevated`) in the audit line and JSON.
- `select_response(..., dcw)`: apply §7 escalation/floor/flood rules.
- `block/throttle/isolate/deflect_conduit(..., timeout)`: accept the scaled timeout.
- (optional) `GET /cars/criticality`; dashboard node badge + decision-log column.

## 9. Why it is bulletproof
- **Deterministic & auditable** — a lookup table + simple arithmetic; every decision traceable to the ACL. No heuristics/ML.
- **Backward-compatible** — unset asset ⇒ LOW ⇒ identical to today; the existing `cars_validate_all.sh` suite still passes.
- **Grounded** — every ACL cites CCE/CISA/centrality; nothing arbitrary in the viva.
- **Bounded strictness** — it can only *tighten* on high-consequence assets and is floored by I1/I2, so it never causes the self-inflicted
  outage that unbounded strictness would. This boundedness is what makes it *true* criticality judgement, not brittle deny-all.

## 10. Validation (proportionality demo)
Fire the **same** trusted actuating WRITE, and the same forbidden op, at **PLC1 (CRITICAL)** vs **PLC2 (HIGH)** vs **Modbus (LOW)**:
- trusted WRITE: PLC1 → **FORBIDDEN → ISOLATE**, 75 s; PLC2 → SENSITIVE → BLOCK-after-1, 60 s; Modbus → SENSITIVE graded, 30 s.
- forbidden CONTROL: PLC1 → **ISOLATE now**, 75 s; PLC2 → BLOCK→ISOLATE, 60 s; Modbus → BLOCK graded, 30 s.
Same attack, response provably proportionate to consequence — one table + audit lines — plus a no-regression run of the existing suite.

## Sources
- INL CCE — https://inl.gov/national-security/cce/ ; concept paper — https://inl.gov/content/uploads/2023/07/DOE_OSTI_CCEconcept-Paper.pdf
- MITRE Crown Jewels Analysis (ICS) — https://www.mitre.org/sites/default/files/2023-01/PR-22-2824-Crown-Jewels-for-Industrial-Control-Systems.pdf
- CISA OT Asset Inventory Guidance (2025) — https://www.cisa.gov/resources-tools/resources/foundations-ot-cybersecurity-asset-inventory-guidance-owners-and-operators
- Attack-path/centrality criticality — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11252175
