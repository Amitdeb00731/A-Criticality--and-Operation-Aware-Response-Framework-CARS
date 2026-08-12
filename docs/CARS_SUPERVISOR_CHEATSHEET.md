# CARS — Master Cheat Sheet (supervisor walkthrough)
**Project CARS** — a **C**riticality- and operation-**A**ware SDN **R**esponse **S**ystem for ICS. Reactive **and** proactive intrusion
response on a real Siemens S7-1200 testbed, that **blocks the attacker at the network AND maintains the physical process** — safety-capped
so the control loop is never severed. This sheet explains every device, wire, script, and decision, down to the packet and the line of code.
_Deployed state as of 2026-07-24. Core sources: `cars_engine.py` (brain), `snort_bridge.py` (sensor), `cars.rules` / `cars_ics_dpi_rules.txt` (DPI), `cars_remediation.py` (process agent), `cars_dashboard.py` (view)._

---

## 1) Devices & roles — who is what (Q1)
| Device | Role | Key address | What it *is* |
|---|---|---|---|
| **Dell #2** | **CARS controller (the "brain")** | control `10.10.10.1` | Runs `os-ken` (SDN controller, a Ryu fork) executing `cars_engine.py`. OpenFlow 1.3 on `:6653`, REST Event API on `:8080`. Makes every decision. |
| **Dell #1** | **Switch + sensor + services host** | control `10.10.10.2`, OT foot `192.168.2.30` | Runs **two** OVS bridges — `ovs1` (dpid 1, Cell-1 access) and `ovsgw` (dpid 3, aggregation/gateway) — plus **Snort** (DPI), `snort_bridge.py`, the **dashboard**, the **remediation agent**, the Modbus sim, the honeypot, the GNS3 IT-attacker chain, and the attack "seams". |
| **Dell #3** | **Pure switch (Cell-2)** | control `10.10.10.3` | Runs OVS bridge `ovs2` (dpid 2) for the second teaching box; reached from Cell-1 via NAT. |
| **Box 1 (real)** | **PLC1 + HMI1** | PLC `192.168.2.10`, HMI `192.168.2.9` | Siemens **S7-1200 1212C** running the live water-tank control program; **KTP700** HMI panel. Wired into Dell #1. |
| **Box 2 (real)** | **PLC2 + HMI2** | clone `192.168.2.10`/`.9`, seen from Cell-1 as `192.168.3.10`/`.9` via NAT | Identical S7-1200 + HMI. Wired into Dell #3. |
| **MikroTik hAP** | **dumb L2 mgmt switch** | — | Carries only the `10.10.10.0/24` **control plane** (out-of-band OpenFlow). Textbook SDN separation. |
| **Asus laptop** | **EWS (engineering workstation)** | OT `192.168.2.55` | TIA Portal box; authorised engineering identity `ews`. |
| **Kali VM** | **insider attacker** | OT `192.168.2.77` | Real attacker vantage inside the OT segment. |
| **GNS3 chain** | **IT-side kill chain** | IT `10.0.40.0/24` → SNAT `192.168.2.1` | VyOS Enterprise-FW → DMZ → OT-FW → into the fabric — the external attack path. |

**Logical identities the brain knows** (`cars_engine.py` `REGISTRY`, lines 19-30, plus deployed additions `.2.45`=remediation, `.2.55`=ews, `.2.77`=supervisory): `plc, hmi, historian, supervisory, ews, remediation, gateway, unknown`. **Anything not in the registry = `unknown` = untrusted** (`role_of()`, line 73).

---

## 2) How they're wired — three physical planes (Q2, Q8)
1. **OT data plane — `192.168.2.0/24`** (and Cell-2's NAT front `192.168.3.0/24`): PLC↔HMI S7comm on TCP **:102**, Modbus on **:502**. Carried on the OVS switches via **USB-Ethernet dongles** (e.g. PLC1 on `enx9c69d331d874` → Dell #1). Box 1 and Box 2 are **two separate L2 segments reusing the same clone IPs** — not interconnected (that isolation is deliberate).
2. **SDN control plane — `10.10.10.0/24`** (wired through the hAP): the OVS switches talk OpenFlow to the controller (`tcp:10.10.10.1:6653`). Out-of-band, sub-millisecond, DHCP-proof static IPs. **The attacker never sees this plane.**
3. **Internet/lab — `192.168.88.0/24` (WiFi):** package installs only; never in the OT or control path.

**Switch fabric:** `ovs1`(dpid1) ⇄ `ovsgw`(dpid3) are patched (`UPLINKS = {1:[3], 3:[1], 2:[]}`, line 70). `ovsgw` also mirrors OT traffic to **Snort**, hosts the **GNS3 seam `it0`**, the **netns attack/service seams**, and the **NAT to Cell-2** (`ovs2`, dpid2, Dell #3). So a Cell-1→PLC2 attack crosses `ovsgw`'s mirror and is inspected/blocked at the Cell-1 edge before it reaches Dell #3.

**Anti-spoof anchor — `BINDINGS`** (lines 63-69): each protected IP has exactly ONE legitimate `(dpid, port, MAC, IP)` origin, e.g. `PLC1 = (dpid1, port1, e0:dc:a0:63:98:09, 192.168.2.10)`. This is what makes identity physically enforceable (see §6 GUARD).

---

## 3) What runs on each device + why every file exists (Q3, Q4)
**Dell #2 — the brain (one process):**
- `cars_engine.py` — the entire controller: registry, rulebook, the 3-table OpenFlow pipeline, the decision engine, enforcement, self-heal, discovery, and the `:8080` REST API. Started via `osken-manager ~/cars/cars_engine.py` in tmux.
- `rulebook.json`, `a2_policy.json` — externalised policy (hot-reloadable), seeded from the code defaults on first run (`load_rulebook()` line 111, `load_a2()` line 132).
- `cars_audit.log` — every decision, appended by `_audit()` (line 371).

**Dell #1 — switch + sensing + services (systemd units, never `pkill`):**
| Runs | File / unit | Purpose |
|---|---|---|
| Snort IDS | `cars-snort.service` + `cars.rules` (`cars_ics_dpi_rules.txt`) | Deep-packet inspection of mirrored OT traffic; writes ICS-op alerts to `/var/log/snort/alert`. |
| Sensor→brain bridge | `cars-bridge.service` → `snort_bridge.py` | Tails the Snort alert file, extracts protocol+op+**rate**, POSTs to `/cars/respond`. |
| Modbus sim | `cars-modbus.service` → `mb_server.py` (`mbns`, `.2.20`) | A soft PLC so Modbus attacks have a safe target. |
| Honeypot | `cars-hpot.service` (`hpotns`, `.3.99`) | The DEFLECT decoy. |
| Cell-2 seam | `cars-ins2.service` (`ins2`, `.3.66`) | Cell-1→PLC2 attack vantage via NAT. |
| Attack/host seams | `cars-seams` / netns | `opns` (.2.31 operator), `atkns` (.2.66 attacker), `sup0` (.2.30 historian). |
| **Remediation agent** | `cars-remediation.service` + `cars-remns.sh` → `cars_remediation.py` (`remns`, `.2.45`) | The process-state guardian (see §8). |
| Dashboard | `cars_dashboard.py` (`:8090`) | Live topology + decision log + process-remediation feed. |
| GNS3 | native | The IT→OT kill-chain periphery off seam `it0`. |
| Attack tooling | `s7_write.py`, `mb_attack.py`, `mb_client.py` | S7/Modbus attack + benign clients used by the test harnesses. |
| Harnesses | `cars_validate_all.sh`, `cars_mttm.sh`, `cars_rate_demo.sh`, `cars_dos_flicker.sh`, `kali_evil.sh`, `cars_evidence_logger.py` | Reproducible validation + measurement. |

**Dell #3 — pure switch:** OVS `ovs2` (dpid2) + the Cell-2 NAT. No CARS logic (kept a bare switch).

**The PLCs themselves** run the **live process** in ladder/SCL: a cyclic OB (100 ms) implementing bang-bang tank control — `IF Level<=30 THEN Pump:=TRUE; IF Level>=70 THEN Pump:=FALSE; Pump_Out(%Q0.3):=Pump`, with `Sim.Level` in **DB7 offset 0 (Real)**. The clicking relay is **Q0.3**. This is the physical process CARS defends.

---

## 4) Controller working principle — the decision pipeline (Q5)
Every packet and every decision flows through this chain. **The switch never decides; it only enforces flows the brain installs.**

**A. Data-plane pipeline — 3 OpenFlow tables** (built in `features_handler()`, line 550):
- **Table 0 = GUARD** (`install_guard()`, line 492): anti-spoof. Legit `(port,MAC,IP)` binding → pass (P200); uplink transit → pass (P150); **a protected IP arriving without its binding = spoof → DROP** (P100); ARP with a protected IP from the wrong sender = ARP-poison → DROP (P100); everything else → pass.
- **Table 1 = POLICY**: the **A2 proactive baseline** (`install_allowlist()`, line 519) — allowlisted conduit → pass (P60), PLC-bound IP not allowlisted → **pre-dropped before it ever lands** (P55, default-deny). **Reactive responses** land here too at **P100-P110** (block/throttle/deflect/isolate), overriding the baseline. Default P0 → go to Table 2.
- **Table 2 = SWITCH**: ordinary L2 learning (`packet_in_handler()`, line 582); table-miss → controller.

**B. Detect → decide → enforce (the reactive path):**
1. OT traffic is mirrored to **Snort**, which byte-matches ICS operations (§5) and writes an alert.
2. `snort_bridge.py` tails the alert, parses `proto/src/dst/op` and computes **ops/sec** over a 3 s window, and POSTs `{src,dst,proto,op,rate,dpid}` to **`/cars/respond`**.
3. `respond()` (line 333) runs the decision: `classify()` → tier; `select_response()` → action; `enforce_response()` → OpenFlow. It timestamps the whole thing (`time.perf_counter()`) — that's the **0.024–0.114 ms** decision-compute figure.
4. The chosen action installs a flow (block/throttle/deflect/isolate) on **every** switch, with `hard_timeout=30` and `SEND_FLOW_REM` so it **auto-heals** when the attack stops.

**C. Human/console controls (REST `:8080`, `_app()` line 192):** `GET /cars/status|audit|hosts|guard|allowlist|rules`; `POST /cars/defense {on}` (arm/disarm), `POST /cars/maintenance {minutes}` (window), `POST /cars/reload|reload-a2` (hot-reload policy), `POST /cars/respond|block|restore`.

---

## 5) How it identifies everything — the rules (Q6)
CARS layers **four independent signals** before deciding:

**(i) WHO — identity by registry + physical binding.** `role_of(ip)` maps IP→role (`REGISTRY`). GUARD (Table 0) proves the IP is genuinely coming from its one legitimate MAC+port, so an attacker can't just borrow a trusted IP.

**(ii) WHAT — operation, at the byte level (Snort DPI, `cars.rules`).** Not 5-tuple — the actual ICS command:
- **Classic S7comm (0x32):** match TPKT `03 00` @ 0, S7 header `32 01` @ **offset 7**, then the **function byte @ offset 17**: `05`=Write-Var → **CONTROL** (sid 1000041); `29`=STOP / `28`=start → **DIAG** (sids 1000042/43); `04`=Read → **READ** (1000044). Same rules mirror onto Cell-2 `.3.10` (sids 1000045-47).
- **Modbus (TCP :502):** proto-id `00 00` @ offset 2, **function code @ offset 7**: FC5/15 coil = **CONTROL**; FC8 (`08`) = **DIAG** (1000025); FC43 (`2B`) = **PROGRAM** (1000026); **FC byte > 43 = ILLEGAL** (`byte_test:1,>,43,7`, 1000027).
- **S7CommPlus (0x72):** the legit HMI↔PLC loop uses this; it is **not function-code-parsed** (honest boundary G3), so the 0x32 rules never false-fire on the real control loop.
The alert message is named `CARS-<PROTO>-<OP>` so `snort_bridge.py` (line 21) maps it straight to an op label.

**(iii) HOW FAST — behavioural rate (A5).** `snort_bridge.py` counts every alert for a `(src,dst,op)` over `RATEWIN=3s` → ops/sec; the brain flags `flood` when `rate ≥ FLOOD_RATE (5.0)` (`respond()` line 349). This catches a **volumetric DoS made of individually-legal reads**.

**(iv) HOW CRITICAL — the declarative rulebook (`RULEBOOK`, lines 79-108, first-match-wins).** `classify()` (line 149) walks the table top-down; the first row matching `(src_role|ip|any, dst_role|ip|any, op|any)` sets the **tier**:
- `hmi↔plc any` → **CRITICAL** (the control loop — a safety invariant)
- `any→plc CONTROL/DIAG/PROGRAM/ILLEGAL` → **FORBIDDEN** (dangerous ops, even from a trusted source)
- `ews→plc` → SENSITIVE; `supervisory/historian→plc WRITE` → SENSITIVE; their reads → OPERATIONAL
- deployed additions: `remediation→plc CONTROL` → **OPERATIONAL** (the authorised restore path)
- final catch-alls → **FORBIDDEN** (default-deny).

Then **tier → action** (`select_response()`, line 288): **CRITICAL→REFUSE** (never touch the loop, even under flood); OPERATIONAL→ALLOW, but **OPERATIONAL+flood→THROTTLE then BLOCK**; SENSITIVE→THROTTLE→BLOCK (or BLOCK immediately if flooding); **FORBIDDEN→BLOCK, escalating to ISOLATE** on persistence, or **ISOLATE immediately if flooding**. Persistence is tracked per-conduit and per-source (`conduit_state`, `source_state`).

**Response ladder (decoupled from the decision):** `ALLOW · MONITOR · THROTTLE · DEFLECT · ISOLATE · BLOCK · REFUSE` (line 39).

---

## 6) Role of the OVS switches (Q7)
The OVS switches are **dumb, fast enforcers** running OpenFlow 1.3 with **`fail_mode=secure`** (this is why controller-off = fail-secure, not fail-open). Each does exactly three things via its tables:
- **`ovs1` (dpid 1):** Cell-1 access — real PLC1/HMI1 hang off it; runs GUARD + POLICY + SWITCH.
- **`ovsgw` (dpid 3):** the aggregation/gateway — **mirrors OT traffic to Snort**, hosts the netns seams + honeypot + GNS3 `it0`, and **NATs to Cell-2**. Most reactive drops for attackers live here.
- **`ovs2` (dpid 2):** Cell-2 access on Dell #3 — real PLC2/HMI2.
Because `block_conduit()` (line 385) installs the drop on **every connected switch** (`for d,dp in self.datapaths`), a block reaches the target's actual cell even across the NAT. GUARD drop-counts are polled every 3 s and surfaced (`_poll_stats` line 654, `_flow_stats` line 662, `/cars/guard`).

---

## 7) Wire-level walkthrough — one malicious S7 write, end to end
This is the packet's journey and the exact code that acts on it:
1. **Attacker** (`.2.77` or `.2.31`) opens TCP to **`192.168.2.10:102`** and sends an S7 Write-Var PDU. On the wire: `03 00 …` (TPKT) `… 32 01 …` (S7 job) with **`05` at TCP-payload offset 17** (Write-Var) and `82` (output area) at 27.
2. **GUARD (Table 0)** lets it through *if* the source is a real bound host (it's a real endpoint, so not a spoof) — GUARD stops IP theft, not authorised-endpoint misuse (that's the next layer's job).
3. **Snort** sees the mirrored packet, matches **sid 1000041** (`content:"|05|"; offset:17; depth:1`) → writes alert `CARS-S7-CONTROL-write`.
4. **`snort_bridge.py`** parses `op=CONTROL`, `proto=S7`, computes rate, and `POST`s to `/cars/respond`.
5. **`respond()`** → `classify()` walks `RULEBOOK`: `any→plc CONTROL` matches row → **FORBIDDEN**. `select_response()` → **BLOCK** (or **ISOLATE** if it's a burst/persistent).
6. **`block_conduit()`** sends an `OFPFlowMod` to **every switch**: `table_id=1, priority=100, match=(eth_type=0x0800, ipv4_src=attacker, ipv4_dst=192.168.2.10), instructions=[] (drop), hard_timeout=30, flags=SEND_FLOW_REM`. The attacker's very next packet is dropped in silicon → the client throws **`S7TimeoutError`** (you saw exactly this).
7. **First-packet reality (honest):** the very first packet reaches the PLC before the flow is installed (~**12 ms MTTM**, measured, stdev 0.9 ms). Enforcement bounds the *attack*, not the first datagram.
8. **Self-heal:** when the attack stops, the `hard_timeout` expires, OVS sends `FlowRemoved`, `_flow_removed()` (line 471) clears state and **forgives the offense count** so a returning attacker re-escalates from the bottom rung. Verified clean: after tests, `conduit_blocks/mac_blocks` are empty and only allowlist ALLOW flows remain.

For a **sensor false-data** attack (`--dbspoof`, DB7 write), the same block fires **and** the remediation agent restores the reading — that's the "block AND maintain" novelty (§8).

---

## 8) The remediation agent — how it works & how smart it is (Q10)
`cars_remediation.py` runs in the `remns` netns as identity `.2.45` (authorised: rulebook `remediation→plc CONTROL = OPERATIONAL`, allowlisted `.2.45→.2.10:102`). Every **0.3 s** it reads `Tank.Level` (DB7.0, Real via snap7) and detects tampering **by process anomaly**, not by signature: a value **below the control floor (25)** or an **implausible one-poll drop (>15)** — physics the bang-bang law cannot produce. On tamper it **writes back the last-good value** (`wr(c, last_good)`), so the loop keeps a correct reading during/after attack. It **tracks last-good** only while the level is in the healthy band (28-72).
**Why it's clever:** it is **audit-independent** — the OT netns *cannot* reach the control plane (`10.10.10.1`), so it can't be told what to do; it infers tampering from the physics alone, and keeps protecting **even if the whole controller is down** (proven in the fail-secure test). It writes a live feed (`/tmp/cars_remediation_status.json` + `.jsonl`) that the dashboard reads locally and interleaves into the decision log as purple `REMEDIATE` rows. This is the Cárdenas-group virtual-sensor idea, integrated with a network block and a safety cap, **on real hardware** — a combination no single reference system claims.

---

## 9) How intelligent is the brain, overall (Q10)
CARS's "intelligence" is **six independent layers composed under a safety discipline**, and every layer is auditable:
1. **Identity** (registry + physical MAC/port binding) — knows *who*, and can't be spoofed.
2. **Operation-awareness** (byte-level DPI) — knows *what command*, not just a port.
3. **Behavioural rate** (A5) — knows *how fast*, so a flood of legal reads is still caught.
4. **Criticality grading** (first-match rulebook) — proportionate: read≠write≠stop≠program.
5. **Persistence/escalation** — a stray packet is blocked; a *campaign* gets the source quarantined; everything **auto-heals and forgives**.
6. **Safety cap** — the `hmi↔plc` loop is **REFUSE**: CARS will alert but **never enforce against the control loop**, even under flood. This is the property most reactive-IR systems lack.
Plus **proactive default-deny** (works even IDS-down), **deception** (DEFLECT to a honeypot), and **process-state maintenance** (the remediation agent). All of this decides in **~0.1 ms** and mitigates in **~12 ms**, on real Siemens hardware. The design is deliberately **transparent** — the whole policy is a readable table (`RULEBOOK`), not a black-box model.

---

## 10) Current state of the system (Q9)
- **Armed and healthy:** defense `enforce_enabled=true`, GUARD + ARP-guard on, all 3 switches up, no active blocks, decision-compute sub-ms.
- **Live process running:** PLC1 tank oscillating 30-70, relay cycling, remediation agent active.
- **Validated (Campaign 2, `VALIDATION_DAY2_REPORT.md`):** 1501 decisions, **1381 ALLOW (92%)**, all 66 enforcement actions hit **only attackers** (zero legit flows blocked), **MTTM 12.2±0.9 ms**, passed across armed/disarmed/maintenance/controller-off/recover, plus a raw-unprotected "devastation" baseline and two bonus findings (the S7-1200 firmware **rejects** classic CPU-stop; the PLC self-drops excess concurrent S7 sessions).
- **Novelty proven & visible:** block-and-maintain demonstrated on hardware and shown live in one unified decision log.

---

## 11) Likely supervisor questions → one-line answers (with the receipt)
- *"How does it know a write from a read?"* → Snort byte-matches the S7 function code at TCP-payload **offset 17** (`05`=write, `04`=read; `cars.rules` sid 1000041/44).
- *"What stops IP spoofing?"* → Table-0 GUARD: a protected IP not from its bound MAC+port is dropped (`install_guard()` P100).
- *"What if the controller dies?"* → OVS `fail_mode=secure`: last policy holds, unlisted stays denied, agent keeps healing; enforcement resumes on restart (proven).
- *"Won't it break the plant with a false positive?"* → The control loop is **REFUSE** (never enforced); 1381/1501 decisions were ALLOW, 0 legit flows blocked.
- *"Where's the novelty?"* → Network **block** + process **maintenance** + **safety cap**, on **real hardware** — combined, none of the reference works do all three.
- *"How fast?"* → decide ~0.1 ms, mitigate ~12 ms (measured, n=15, stdev 0.9 ms).
- *"Is policy hard-coded?"* → No — `rulebook.json` + `a2_policy.json`, hot-reloadable with no restart (`/cars/reload`, `/cars/reload-a2`).

## 12) Honest boundaries (state them proactively — it's a strength)
- **G1** a *compromised authorised endpoint* can issue authorised ops (identity is honoured — that's why the agent + safety cap matter).
- **G3** S7CommPlus (0x72) is session-marked, not function-parsed (the legit HMI loop rides it).
- **G5** IT-side attackers collapse to one NAT identity (`.2.1`) at the OT edge.
- **G6** single controller (Dell#2) and Cell-2 internal traffic isn't mirrored (only Cell-1→PLC2 crossing `ovsgw` is).
- **First-packet reality:** first datagram lands before the block (~12 ms); CARS bounds the attack, not the first packet.

---

# APPENDIX A — The full controller decision tables (verbatim from `cars_engine.py`)

## A.0 How the controller gives its judgement (the `respond()` pipeline, line 333)
**Input** (from the sensor `snort_bridge.py`, one JSON POST to `/cars/respond`): `{src, dst, proto, op, rate, dpid}`.

| # | Step | Code | What happens |
|---|------|------|--------------|
| 1 | **Identify** | `role_of(src)`, `role_of(dst)` (line 73) | IP → role via REGISTRY (unknown if unlisted). |
| 2 | **Classify (decide tier)** | `classify()` line 149 | Walk RULEBOOK top→bottom, **first match wins** → `tier ∈ {CRITICAL, FORBIDDEN, SENSITIVE, OPERATIONAL}`. |
| 3 | **Maintenance waiver** | line 338 | If `tier=FORBIDDEN` AND `op∈{CONTROL,DIAG,PROGRAM}` AND window open → tier becomes `OPERATIONAL` (permitted-with-monitoring). `ILLEGAL` is **never** waived. |
| 4 | **Rate check** | line 349 | `flood = (rate ≥ FLOOD_RATE=5.0)`. |
| 5 | **Persistence** | lines 341-352 | Bump `conduit_state[(src,dst)].count` and `source_state[src].count` (unless the action is ALLOW/MONITOR). |
| 6 | **Select response (decide action)** | `select_response()` line 288 | Map `(tier, flood, count)` → one of the ladder actions (table A.5). |
| 7 | **Enforce or monitor** | line 353 | If armed → `enforce_response()` installs the OpenFlow flow; if disarmed → log `"DEFENSE DISARMED - would <action> (monitor only)"`. |
| 8 | **Annotate** | lines 357-360 | Prefix `MAINTENANCE-AUTHORISED` / `[FLOOD N ops/s]` on the audit line as applicable. |
| 9 | **Measure + audit** | lines 361-368 | Record decide+enforce latency (`perf_counter`, the ~0.1 ms figure), append the audit line, return the decision JSON. |

**One sentence:** *the controller identifies the source, reads the operation, grades it against a first-match rulebook into a criticality tier, overlays rate and persistence, then picks a proportionate, safety-capped, self-healing response — and either enforces it as an OpenFlow flow or (if disarmed) just logs what it would have done.*

## A.1 REGISTRY — identity map (`REGISTRY`, lines 19-30 + deployed additions)
| OT IP | role | cell | name / note |
|-------|------|------|-------------|
| 192.168.2.10 | plc | 1 | PLC1 (real S7-1200) |
| 192.168.2.9 | hmi | 1 | HMI1 (KTP700) |
| 192.168.3.10 | plc | 2 | PLC2 via Dell#3 NAT |
| 192.168.3.9 | hmi | 2 | HMI2 via NAT |
| 192.168.2.20 | plc | – | PLC-MB (Modbus sim) |
| 192.168.2.30 | historian | – | Supervisory foot (`sup0`) |
| 192.168.2.31 | supervisory | – | Operator / eng station (`opns`) |
| 192.168.2.66 | unknown | – | Attacker seam (`atkns`) |
| 192.168.3.66 | supervisory | – | Cell-2 eng station → PLC2 (`ins2`) |
| 192.168.2.1 | gateway | – | OT-FW / IT-DMZ boundary (NAT collapse point) |
| 192.168.2.45 | remediation | – | **Remediation agent (deployed add)** |
| 192.168.2.55 | ews | – | **Engineering workstation / TIA (deployed add)** |
| 192.168.2.77 | supervisory | – | **Kali insider (deployed add)** |
| *anything else* | **unknown** | – | untrusted by default |

## A.2 RULEBOOK — the decision policy (`RULEBOOK`, lines 79-108; **ordered, first-match-wins**)
| # | src (role/ip/any) | dst | op | → TIER | meaning |
|---|------|-----|----|--------|---------|
| — | **remediation** | plc | CONTROL/any | **OPERATIONAL** | *deployed insert, above row 1-group* — authorised restore write |
| 1 | hmi | plc | any | **CRITICAL** | control loop = safety invariant |
| 2 | plc | hmi | any | **CRITICAL** | control loop (reverse) |
| 3 | any | plc | CONTROL | **FORBIDDEN** | coil/output actuation — dangerous even from trusted |
| 4 | any | hmi | CONTROL | FORBIDDEN | |
| 5 | any | plc | DIAG | FORBIDDEN | stop/restart comms (FC8 / S7 0x29) |
| 6 | any | hmi | DIAG | FORBIDDEN | |
| 7 | any | plc | PROGRAM | FORBIDDEN | program/config download (FC43) |
| 8 | any | hmi | PROGRAM | FORBIDDEN | |
| 9 | any | plc | ILLEGAL | FORBIDDEN | malformed / out-of-range FC |
| 10 | any | hmi | ILLEGAL | FORBIDDEN | |
| 11 | ews | plc | any | SENSITIVE | maintenance identity — elevated |
| 12 | ews | hmi | any | SENSITIVE | |
| 13 | supervisory | plc | WRITE | SENSITIVE | a trusted WRITE still actuates → escalate |
| 14 | historian | plc | WRITE | SENSITIVE | |
| 15 | scada | plc | WRITE | SENSITIVE | |
| 16-18 | supervisory/historian/scada | hmi | WRITE | SENSITIVE | |
| 19 | supervisory | plc | any | OPERATIONAL | trusted read/monitor → permit |
| 20 | historian | plc | any | OPERATIONAL | |
| 21 | scada | plc | any | OPERATIONAL | |
| 22-24 | supervisory/historian/scada | hmi | any | OPERATIONAL | |
| 25 | any | plc | any | **FORBIDDEN** | anything else → a PLC |
| 26 | any | hmi | any | **FORBIDDEN** | anything else → an HMI |
| 27 | any | any | any | **FORBIDDEN** | global default-deny |

Match rule (`classify()` line 152): a row matches when `src∈{any, role, exact-ip}` AND `dst∈{any, role, exact-ip}` AND `op∈{any, exact-op}`. Edit the policy by editing `rulebook.json` — no code change, hot-reloadable.

## A.2b Field decoder — what every field / address / token actually is (covers all A-sections)

**A.1 REGISTRY fields.** The **key** is an **OT-plane IPv4 address** — `192.168.2.0/24` is Cell-1; `192.168.3.0/24` is Cell-2's **NAT front** (the same physical PLC2, re-addressed so Cell-1 can reach it). The **value `role`** is the trust class the entire policy keys on. Quick read of the addresses: `.2.10/.2.9` = real PLC1/HMI1; `.3.10/.3.9` = PLC2/HMI2 via NAT; `.2.20` = the soft Modbus PLC; `.2.30` = supervisory foot, `.2.31` = operator/eng; `.2.45` = remediation agent; `.2.55` = EWS; `.2.66` = attacker seam; `.2.77` = Kali insider; `.2.1` = the NAT collapse point where **all** IT-side attackers appear as one identity.

**A.2 RULEBOOK fields.** Four columns: **`src`** and **`dst`** each match by **role name** (from A.1), an **exact IP**, or **`any`**; **`op`** is the DPI **operation label** (`READ / WRITE / CONTROL / DIAG / PROGRAM / ILLEGAL / S7 / any`); the result is the **`tier`** (criticality). Order matters — the first row whose three columns all match wins and stops the search.

**A.3–A.5 & A.7 OpenFlow fields — the match ("if" part of a flow):**
| Token in the dump | What it actually is |
|---|---|
| `in_port=N` | the **physical switch port** the frame entered (e.g. `ovs1` port 1 = the cable to PLC1) — anchors a packet to *where* it came in |
| `eth_type=0x0800 / 0x0806 / 0x88cc` | the frame is **IPv4 / ARP / LLDP** |
| `eth_src` / `eth_dst` | source / destination **MAC address** (layer-2 hardware address) |
| `ipv4_src` / `ipv4_dst` | source / destination **IP address** (layer-3) |
| `arp_spa` | ARP **Sender Protocol Address** = the **IP the ARP is claiming to own** |
| `arp_sha` | ARP **Sender Hardware Address** = the **MAC behind that claim** (GUARD checks spa + sha + in_port together) |
| `ip_proto=6` | the L4 protocol = **TCP** (17=UDP, 1=ICMP) |
| `tcp_dst=102 / 502` | destination TCP port = the **service**: **102 = S7comm (PLC), 502 = Modbus** |
| `cookie=0xa2` | a **tag** stamped on A2 proactive flows so a hot-reload deletes only those (never reactive flows) |
| `priority=N` | **match precedence** — higher wins (reactive P100 beats allowlist P60 beats default-deny P55) |
| `hard_timeout=30` | the flow **self-deletes 30 s** after install (self-heal) |

**A.3–A.5 & A.7 — the action ("then" part):** `resubmit(,N)` / goto_table:N = **continue at table N**; `drop` (empty instruction) = **discard silently**; `output:N` = **send out port N**; `FLOOD` = out **all ports except ingress**; `CONTROLLER` = **punt up to the brain** (table-miss / learning); `set_field:X->field` = **rewrite a header** (DEFLECT rewrites eth_dst/ipv4_dst to the honeypot); `meter:1` = pass through **meter #1** (rate-limit, drop above 20 pps) = THROTTLE.

**A.3 BINDINGS fields (the anti-spoof anchor).** Each row is `(dpid, port, MAC, IP)` = the **one legitimate physical origin** of a protected IP. Example: `(1, 1, e0:dc:a0:63:98:09, 192.168.2.10)` reads *"PLC1's IP may appear ONLY from switch 1, port 1, with that exact MAC."* Any other `(port, MAC)` presenting that IP = spoof → dropped in Table 0.

**A.6 decision-engine fields.** `offense` / `count` = how many times this **conduit** (`conduit_state[(src,dst)]`) or **source** (`source_state[src]`) has already been caught — the persistence memory; `flood` = the sensor-measured **ops/sec ≥ FLOOD_RATE (5)**; `ESCALATE=3` = the count at which BLOCK→ISOLATE and THROTTLE→BLOCK.

**A.8 self-heal fields.** `hard_timeout` = the auto-expiry clock on every reactive flow; `SEND_FLOW_REM` = the switch→brain "this flow just expired" notice; on receiving it the brain zeroes the offense count so a returning attacker restarts at the bottom rung.

**A.9 discovery fields.** `dpid` = datapath id = the **switch number** (1=ovs1, 2=ovs2, 3=ovsgw); `port_no` = the OpenFlow **port index**; an `EventLink` carries `src.dpid/src.port ↔ dst.dpid/dst.port` (the fabric patch link between switches).

## A.3 Table 0 = GUARD (anti-spoof, `install_guard()` line 492)
| Prio | Match | Action | Purpose |
|------|-------|--------|---------|
| 200 | in_port=P, eth_src=MAC, ipv4_src=IP (per BINDING) | → Table 1 | legit bound host passes |
| 200 | in_port=P, arp_spa=IP, arp_sha=MAC | → Table 1 | legit ARP passes |
| 150 | in_port = uplink/patch | → Table 1 | transit port (already guarded at its access switch) |
| 100 | eth_type=IP, ipv4_src = protected IP | **DROP** | protected IP not from its binding = **IP spoof** |
| 100 | eth_type=ARP, arp_spa = protected IP | **DROP** | protected IP announced by wrong sender = **ARP poison** |
| 50 | eth_type=IP (any other) | → Table 1 | ordinary IP passes |
| 0 | * | → Table 1 | ARP/LLDP/non-IP passes |

## A.4 Table 1 = POLICY (proactive baseline + reactive responses)
| Prio | Match | Action | Installed by | Layer |
|------|-------|--------|--------------|-------|
| 110 | ipv4_src = X | **DROP (all dst)** | `isolate_source()` line 418 | reactive — quarantine source |
| 105 | ipv4_src=A, ipv4_dst=T | rewrite → honeypot, → T2 | `deflect_conduit()` line 434 | reactive — deception |
| 100 | ipv4_src=A, ipv4_dst=T | **DROP** (block) *or* meter#1 + → T2 (throttle) | `block/throttle_conduit()` 385/407 | reactive — block / rate-limit |
| 60 | ipv4_src=s, ipv4_dst=d, ip_proto, tcp_dst | → Table 2 (ALLOW) | `install_allowlist()` line 519 (cookie 0x00A2) | proactive A2 — allow known-good |
| 55 | ipv4_dst = protected (per-switch scoped) | **DROP** | `install_allowlist()` | proactive A2 — **default-deny** |
| 0 | * | → Table 2 | `features_handler()` line 561 | default = ALLOW → learning |

Reactive flows (P100-110) **pre-empt** the proactive baseline (P55-60); all reactive flows carry `hard_timeout=30 + SEND_FLOW_REM` (self-heal).

## A.5 Table 2 = SWITCH (L2 learning, `packet_in_handler()` line 582)
| Prio | Match | Action | Purpose |
|------|-------|--------|---------|
| 2 | eth_dst = ff:ff:ff:ff:ff:ff | FLOOD | broadcast/ARP re-resolves even if controller is down (HP4) |
| 1 | in_port, eth_dst, eth_src (learned) | output learned port | normal L2 forwarding |
| 0 | * (table-miss) | → CONTROLLER | learn the source, install the flow |

## A.6 Decision engine — tier × behaviour → action (`select_response()` line 288, `ESCALATE=3`)
| TIER | normal rate | **flood** (rate ≥ 5/s) |
|------|-------------|------------------------|
| **CRITICAL** (hmi↔plc loop) | **REFUSE** (never enforce) | **REFUSE** (safety cap holds even under flood) |
| **OPERATIONAL** (trusted read/monitor) | **ALLOW** | **THROTTLE** if offense<3, then **BLOCK** |
| **SENSITIVE** (ews→plc, trusted WRITE) | **THROTTLE** if offense<3, then **BLOCK** | **BLOCK** (cut now, don't rate-limit) |
| **FORBIDDEN** (dangerous / untrusted → PLC) | **BLOCK** if src-offense<3, then **ISOLATE** | **ISOLATE** (burst = active attack → quarantine source) |

## A.7 Enforcement — action → the exact flow installed (`enforce_response()` line 310)
| Action | Primitive | Flow (table / prio / match / instruction) | Scope | Timeout |
|--------|-----------|-------------------------------------------|-------|---------|
| ALLOW / MONITOR | — | none — audit only | — | — |
| THROTTLE | `throttle_conduit` | T1 P100, ipv4 src+dst, **meter#1 (20 pps drop) + goto T2** | all switches | 30 s, SEND_FLOW_REM |
| BLOCK | `block_conduit` | T1 P100, ipv4 src+dst, **empty instr = DROP** | all switches | 30 s, SEND_FLOW_REM |
| DEFLECT | `deflect_conduit` | T1 P105 fwd: setfield eth/ip→honeypot; reverse: setfield ip_src→target, output attacker port | all switches | 30 s, SEND_FLOW_REM |
| ISOLATE | `isolate_source` | T1 **P110, ipv4_src only (any dst) = DROP** | all switches | 30 s, SEND_FLOW_REM |
| REFUSE | — | **none — mirror/alert only (safety invariant)** | — | — |

## A.8 Self-heal (`_flow_removed()` line 471)
| Mechanism | Where | Effect |
|-----------|-------|--------|
| `hard_timeout = BLOCK_TIMEOUT (30 s)` | on every reactive flow | flow auto-expires 30 s after install if not renewed |
| continued detection | bridge keeps POSTing | re-installs the flow → resets the 30 s timer (block persists while attack persists) |
| `OFPFF_SEND_FLOW_REM` | flag on the flow | switch notifies the controller when the flow expires |
| `_flow_removed` on `HARD_TIMEOUT` | line 480 | clears `conduit_blocks`, **resets offense count to 0 (forgive)** so a returning attacker re-escalates from the bottom rung; ISOLATE heal also clears `source_state` |
| `POST /cars/restore` | API line 273 | manual immediate un-isolate/unblock |

## A.9 Discovery (event-driven, no static topology)
| OpenFlow event | Handler (line) | What the controller learns / does |
|----------------|----------------|-----------------------------------|
| SwitchFeatures (connect) | `features_handler` (550) | wipe old flows, build T0/T1/T2 pipeline, install GUARD + A2, request port descs |
| PacketIn (table-2 miss) | `packet_in_handler` (582) | learn host IP/MAC/dpid/port; install L2 flow; forward |
| PortDescStatsReply | `_port_desc` (628) | initial up/down state of every port |
| PortStatus | `_port_status` (636) | live port link up/down changes |
| LinkAdd / LinkDelete | `_link_add/_del` (643/648) | fabric links (via LLDP topology) |
| FlowStatsReply (poll 3 s) | `_flow_stats` (662) | GUARD spoof-drop packet counts → `/cars/guard` |
| StateChange → DEAD | `_sw_dead` (618) | switch down → purge its hosts/ports/macs (no phantoms) |

## A.10 The packet's journey — how it's matched and where it ends up (every scenario)
**The fixed path of every frame:** ingress port → **Table 0 (GUARD)** → **Table 1 (POLICY)** → **Table 2 (SWITCH / L2-learn)** → egress port. Within each table the **highest-priority matching flow wins**, and its action either forwards (`resubmit`/`output`/`FLOOD`), discards (`drop`), or punts (`CONTROLLER`). **In parallel**, `ovsgw` mirrors a copy to **Snort**; if it is an ICS operation, Snort → `snort_bridge.py` → the brain, and the brain may install a **new Table-1 flow** that changes what the **next** packet of that conversation hits. So a conversation's *first* packet is judged by the *existing* tables; the *response* shapes everything after.

Traces below use `T0/T1/T2` = the three tables; **bold** = the winning flow.

**① Legit control loop — HMI `.2.9` → PLC `.2.10:102` (S7CommPlus 0x72).**
Enters `ovs1` on the HMI's bound port. **T0:** matches its **P200 binding** (`in_port`+`eth_src`+`ipv4_src` all correct) → goto T1. **T1:** matches **P60 allowlist** (`.2.9→.2.10:102`) → goto T2. **T2:** learned flow → `output` PLC's port. **Delivered.** Mirror→Snort: it's `0x72`, *not* function-parsed, so no CONTROL/READ alert; if the brain sees it at all → `hmi→plc` = **CRITICAL → REFUSE** (alert only, **never** enforced). *The control loop is sacred and untouchable.*

**② Legit monitoring read — operator `.2.31` → PLC `.2.10:102` (S7 read `0x04`).**
**T0:** `.2.31` is not a *protected* IP, so P200 doesn't apply; **P50 (any other IP) → goto T1**. **T1:** matches **P60 allowlist** (`.2.31→.2.10:102`) → goto T2 → **delivered.** Mirror→Snort: **sid 1000044** (`0x04`) → `op=READ` → brain `classify()` = `supervisory→plc any` = **OPERATIONAL → ALLOW (monitor only)**. **No flow installed**, read succeeds. *Authorised + benign = pass, and it's logged.*

**③ Insider command injection — `.2.31`/`.2.77` → PLC `.2.10:102` (S7 write `0x05`).**
**T0:** passes (real endpoint, IP not spoofed). **T1:** the TCP conduit is allowlisted (**P60**), so the **first** packet reaches the PLC (first-packet reality). Mirror→Snort: **sid 1000041** (`0x05 @ offset 17`) → `op=CONTROL` → brain = `any→plc CONTROL` = **FORBIDDEN → BLOCK**: `block_conduit()` installs **T1 P100 drop** (`ipv4_src=attacker, ipv4_dst=.2.10`, `hard_timeout=30`) on **all** switches. The attacker's **next** packets hit that P100 drop → `S7TimeoutError`. Persist/burst → **ISOLATE** (P110, drop *all* of the source's traffic). **Self-heals** 30 s after the attack stops. *Authorised conduit, unauthorised operation = blocked-and-quarantined; the loop keeps running.*

**④ IP spoofing — attacker forges source IP `.2.10` (a protected IP) from the wrong port/MAC.**
**T0 GUARD:** `ipv4_src=.2.10` arrives NOT matching its binding (wrong `in_port`/`eth_src`) → matches **P100 spoof-drop → dropped at ingress**, before T1, before it can impersonate the PLC. The `/cars/guard` counter ticks. *Never reaches the policy table, the brain, or any host.*

**⑤ ARP poisoning — attacker sends gratuitous ARP claiming to own `.2.10`.**
**T0 GUARD:** `eth_type=ARP, arp_spa=.2.10` from the wrong sender → matches **P100 ARP-guard drop → dropped.** Neighbours' ARP caches are never poisoned; the man-in-the-middle setup fails at layer 2.

**⑥ Unlisted attacker to a default-deny asset — `.2.66` → Modbus `.2.20:502`.**
**T0:** `.2.66` not protected → **P50 → goto T1**. **T1:** no allowlist row for `.2.66→.2.20`; matches **P55 default-deny** (`ipv4_dst=.2.20`) → **drop**. The TCP SYN never completes → *"TCP connect FAILED (blocked)"*. *Proactive: pre-dropped before it lands — no IDS, no alert, no decision needed.* (Contrast ③, where the conduit *is* allowlisted so detection is reactive.)

**⑦ Volumetric DoS with a LEGAL op — `.2.31` reads at ~20/s.**
Each read individually matches **P60 allow** → delivered. But Snort alerts every read; `snort_bridge.py` measures **rate ≈ 17/s ≥ FLOOD_RATE** and tags it; brain = `OPERATIONAL + flood` → **THROTTLE** (installs meter #1 at P100 — rate-limit to 20 pps, not a hard drop) → **BLOCK** if sustained. Stop the flood → **self-heals to ALLOW**. *Decides on rate, not just type; and the critical loop is exempt even here.*

**⑧ Sensor false-data injection — `.2.77` → PLC DB7 write (S7 `0x05`).**
Network path = exactly ③ (**BLOCK → ISOLATE**, attacker cut after one packet). **In parallel and independently**, the **remediation agent** (`.2.45`, authorised: `remediation→plc CONTROL = OPERATIONAL`, allowlisted `.2.45→.2.10:102`) reads DB7 every 0.3 s, sees the tampered value below the control floor, and **writes back the last-good value** → the process reading is maintained. *This is "block (network) AND maintain (process)".*

**⑨ Return / reply traffic — PLC `.2.10` → operator `.2.31` (the S7 response).**
`ipv4_dst=.2.31` is **not** a PLC, so the P55 default-deny (which matches `ipv4_dst=PLC`) doesn't apply, and the reactive block (which matches `ipv4_src=attacker → ipv4_dst=PLC`) is directional and doesn't match the reverse. **P0 → goto T2 → delivered.** *CARS blocks the attack direction, never the return path — so legitimate request/response is never half-broken.*

**⑩ Controller DOWN (fail-secure) — any packet while the brain is offline.**
No packet-ins are processed, but every **already-installed** flow persists (OVS `fail_mode=secure`). A legit allowlisted conduit still forwards (its **P60** flow is present); an unlisted attacker is still dropped (**P55**); an active block/isolate stays in force until its timeout. The only gap: a **listed** source's *new* dangerous op isn't reactively blocked (no brain to decide) — but the agent still heals the process. Controller returns → pipeline rebuilt, enforcement resumes. *Fail-secure, not fail-open.*

**⑪ Broadcast / ARP (normal operation).**
**T0:** `P0 → goto T1`; **T1:** `P0 → goto T2`; **T2:** matches the **P2 broadcast flow → FLOOD**. This is why ARP re-resolves and the network keeps working even during a controller outage.

**Summary of "where does it end up":** spoof/ARP-poison die in **T0**; unlisted-to-protected dies in **T1 (P55)**; authorised-benign and the control loop pass **T1→T2** and are delivered; authorised-but-dangerous is delivered once then the conduit is dropped/quarantined by a **reactive T1 flow**; floods are metered then dropped; replies always pass. Every enforced drop carries a 30 s self-heal, and the `hmi↔plc` loop is never enforced against under any circumstance.

---

# APPENDIX B — Live command cheat sheet (prove it on the laptops)
_Bridge names: `ovs1` (dpid1, Dell#1), `ovsgw` (dpid3, Dell#1), `ovs2` (dpid2, Dell#3). Controller API: `http://10.10.10.1:8080`. Paths on the boxes: controller `~/cars/`, Snort `/etc/snort/`, alert `/var/log/snort/alert`._

## B.0 ⭐ Watch the whole loop fire live (the money demo — 4 terminals, then 1 attack)
Open four panes, then fire one command and watch detection → decision → enforcement → self-heal cascade across them:
```bash
# T1 (Dell#1) — the SENSOR sees the packet (DPI byte-match fires):
tail -f /var/log/snort/alert
# T2 (Dell#1) — the BRIDGE reports it to the brain (op + rate -> /cars/respond):
journalctl -u cars-bridge -f
# T3 (Dell#2) — the BRAIN's judgement (tier => response), one line per decision:
tail -f ~/cars/cars_audit.log
# T4 (Dell#1) — the ENFORCEMENT flow appears on the switch, then AUTO-EXPIRES ~30s later:
watch -n1 "sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -E 'priority=1(00|05|10)'"
```
Then fire ONE malicious write (Dell#1 operator seam, or Kali `.2.77`):
```bash
sudo ip netns exec opns python3 ~/s7_write.py --host 192.168.2.10 --val 0 --count 1
```
You will see, in order: **T1** `CARS-S7-CONTROL-write` alert → **T2** `REPORT … op=CONTROL … | CARS: …` → **T3** `FORBIDDEN 192.168.2.31(supervisory) -> 192.168.2.10(plc) S7 CONTROL => BLOCK/ISOLATE` → **T4** a `priority=100 … actions=drop` flow appears and disappears ~30 s later (self-heal). That single cascade *is* the system.

## B.1 Dell#2 — the brain: policy, judgement, controls
```bash
curl -s http://10.10.10.1:8080/cars/status   | python3 -m json.tool   # switches up, guard on, decision-ms, active blocks
curl -s http://10.10.10.1:8080/cars/rules     | python3 -m json.tool   # the RULEBOOK (live, ordered, first-match)
curl -s http://10.10.10.1:8080/cars/allowlist | python3 -m json.tool   # the A2 allowlist + default-deny (live)
curl -s http://10.10.10.1:8080/cars/defense                            # armed? {"enforce_enabled": true}
curl -s http://10.10.10.1:8080/cars/maintenance                        # maintenance window state
grep -A14 "REGISTRY = {" ~/cars/cars_engine.py                         # identity map (IP -> role) at the source
sed -n '79,108p' ~/cars/cars_engine.py                                 # the rulebook in code (matches /cars/rules)
cat ~/cars/rulebook.json                                               # the hot-reloadable policy file
cat ~/cars/a2_policy.json                                              # the hot-reloadable proactive allow/deny
tail -n 40 ~/cars/cars_audit.log                                       # recent decisions
```

## B.2 Dell#1 — the LIVE ground rules on the switch (the OpenFlow tables)
```bash
sudo ovs-vsctl get-fail-mode ovs1                                      # -> secure  (why controller-off = fail-secure)
sudo ovs-vsctl get-controller ovs1                                     # -> tcp:10.10.10.1:6653  (out-of-band brain)
# Table 0 = GUARD (anti-spoof): P200 legit bindings, P100 spoof/ARP DROP
sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=0
# Table 1 = POLICY: P60 allowlist (cookie 0xa2), P55 default-deny, P100+ reactive blocks
sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1
# Table 2 = SWITCH: learned L2 flows + broadcast flood
sudo ovs-ofctl -O OpenFlow13 dump-flows ovs1 table=2
sudo ovs-ofctl -O OpenFlow13 dump-meters ovsgw                         # the THROTTLE meter (id 1, 20 pps drop)
sudo ovs-vsctl list mirror                                             # the span that feeds Snort
curl -s http://10.10.10.1:8080/cars/guard | python3 -m json.tool       # per-IP spoof-drop counters (from Table 0)
```
Reading Table 1: `priority=60 … actions=resubmit(,2)` = allowlisted conduit; `priority=55 … actions=drop` = default-deny; `priority=100/110 … actions=drop` = a live reactive block/isolate (with `hard_timeout=30`).

## B.3 Dell#1 — the sensor: DPI rules + what it detected
```bash
grep "CARS-" /etc/snort/cars.rules                                     # the ICS DPI rules (S7 0x32 @off17, Modbus FC @off7)
systemctl status cars-snort --no-pager | head -5                      # Snort running on the mirror
tail -n 20 /var/log/snort/alert                                        # recent raw DPI alerts
systemctl status cars-bridge --no-pager | head -5                     # the sensor->brain bridge
journalctl -u cars-bridge -n 20 --no-pager                            # recent REPORT lines (op + ops/s -> /cars/respond)
```
Point to `sid:1000041 … content:"|05|"; offset:17` — that one line is "how it tells a write from a read."

## B.4 Dell#1 — services + attack/host seams
```bash
systemctl is-active cars-bridge cars-snort cars-modbus cars-hpot cars-ins2 cars-remediation
ip netns list                                                          # opns(.2.31) atkns(.2.66) remns(.2.45) mbns(.2.20) hpotns
curl -s -o /dev/null -w "dashboard %{http_code}\n" http://localhost:8090/   # live dashboard on :8090
```

## B.5 Dell#1 — the process guardian + the live plant
```bash
systemctl status cars-remediation --no-pager | head -5                # the process-state agent
cat /tmp/cars_remediation_status.json                                 # live: level, last_good, restores
journalctl -u cars-remediation -n 10 --no-pager                       # recent [REM] TAMPER->RESTORED events
# read the real tank + relay directly (needs the snap7-capable python):
sudo ip netns exec opns /usr/bin/python3 -c "import snap7,struct;c=snap7.client.Client();c.connect('192.168.2.10',0,1);print('Level',round(struct.unpack('>f',bytes(c.db_read(7,0,4)))[0],1),'| Q0.3',(c.ab_read(0,1)[0]>>3)&1);c.disconnect()"
```

## B.6 Dell#3 — the Cell-2 switch
```bash
sudo ovs-vsctl get-fail-mode ovs2 ; sudo ovs-vsctl get-controller ovs2
sudo ovs-ofctl -O OpenFlow13 dump-flows ovs2 table=0    # GUARD on Cell-2
sudo ovs-ofctl -O OpenFlow13 dump-flows ovs2 table=1    # POLICY on Cell-2
```

## B.7 The live controls (arm / disarm / maintenance / hot-reload policy)
```bash
curl -s -X POST http://10.10.10.1:8080/cars/defense -H 'Content-Type: application/json' -d '{"on":false}'   # DISARM (monitor-only)
curl -s -X POST http://10.10.10.1:8080/cars/defense -H 'Content-Type: application/json' -d '{"on":true}'    # RE-ARM
curl -s -X POST http://10.10.10.1:8080/cars/maintenance -H 'Content-Type: application/json' -d '{"minutes":10}'  # open window
curl -s -X POST http://10.10.10.1:8080/cars/reload                                                          # hot-reload rulebook.json
curl -s -X POST http://10.10.10.1:8080/cars/reload-a2                                                        # hot-reload a2_policy.json
```
Edit `~/cars/rulebook.json` or `a2_policy.json`, POST the matching reload, and the new policy is live **with no controller restart** — a strong "the policy is data, not code" point.

---

# APPENDIX C — Connective tissue, perimeter & honest caveats (the rest of the body)
_The organs a sharp reviewer asks about: how the sensor taps the wire, the control channel, the NAT, the perimeter, what the "process" really is, the supervisory layer, what breaks what, and who guards the guard. Where an exact config value is deployment-specific, the verify-command is given rather than a guessed number._

## C.0 Verification status (directly checked on hardware, 2026-07-24 — CC-76)
| Item | Status | Proof |
|---|---|---|
| **C.1** sensor tap | ✅ verified | OVS mirror `m0` (`select_all:true`) → `snort0`; Snort sniffs `-i snort0`. (`HOME_NET=any` — fine, rules are dst-IP-specific.) |
| **C.2** control channel + 2 bridges | ✅ verified | `ovs1`+`ovsgw` → `tcp:10.10.10.1:6653`; `ovs2` on Dell#3; 2 live OF sockets |
| **C.3** Cell-2 NAT | ✅ verified (Dell#3) | `DNAT -d 192.168.3.10 --to 192.168.2.10` + `MASQUERADE -o cell2gw` |
| **C.4** IT→OT kill chain | ✅ verified | IT `10.0.40.66` → Ent-FW → DMZ → OT-FW **SNAT → `.2.1`**. *Proactive:* default-deny dropped it at `ovs1` — couldn't even ping the PLC (topology shows `.2.1→PLC1`). *Reactive (allowlisted through):* `192.168.2.1(gateway) → .2.10 TCP => BLOCK (all switches)` — `gateway→plc` is FORBIDDEN outright, cut on connection. **G5 collapse proven live.** |
| **C.5** simulated process | ✅ verified | DB7 read/write + real relay observed all session |
| **C.6** historian/SCADA | ✅ **LIVE** | InfluxDB :8086=200, Grafana :3000=302, FUXA :1881=200 |
| **C.7** degradation | ✅ verified + **finding** | proactive A2 holds with sensor down; reactive restores when bridge returns. **CC-76: `cars-bridge` is coupled to `cars-snort` — stopping Snort cascades to the bridge and starting Snort alone does NOT revive it, silently blinding reactive detection.** Fix: `systemctl restart cars-snort cars-bridge` together; harden the unit (`PartOf=cars-snort.service`, `Restart=always`). |
| **C.8** control-plane isolation | ✅ verified | OT seam → `:8080` API **UNREACHABLE**; control plane → reachable |

## C.1 The sensor tap — how Snort actually sees the traffic (the nerve ending)
DPI can only inspect what it's shown. OT traffic reaches **Snort** by an **OVS port mirror (SPAN)** configured on **`ovsgw`**: selected OT ports/VLAN are copied to a **mirror output port** that Snort sniffs in **IDS mode** (`snort -i <mirror-if> -A fast -c /etc/snort/snort.conf`), writing to `/var/log/snort/alert`. `snort.conf` sets `HOME_NET` to the OT range and **`include $RULE_PATH/cars.rules`** (the file in Appendix B.3). Verify the tap and the config:
```bash
sudo ovs-vsctl list mirror ; sudo ovs-vsctl list bridge ovsgw | grep -i mirror   # what is mirrored where
grep -E "HOME_NET|cars.rules|ipvar|include" /etc/snort/snort.conf                 # scope + rule inclusion
ps -ef | grep "[s]nort" ; systemctl status cars-snort --no-pager | head -3        # which interface Snort sniffs
```
**Consequence (design point):** the mirror lives at the **Cell-1 aggregation edge (`ovsgw`)**, so a Cell-1→PLC2 attack that *crosses* `ovsgw` is inspected, but **Cell-2-internal** traffic on `ovs2` is **not mirrored** → boundary **G6**. This is *why* detection is edge-based, and it's stated honestly, not hidden.

## C.2 The command channel + the two bridges on Dell#1 (the spinal cord)
The brain talks to the muscles over **OpenFlow 1.3 on TCP `:6653`**, carried on the **out-of-band control plane `10.10.10.0/24`** (the wired MikroTik hAP), never on the OT plane. Dell#1 runs **two** OVS bridges — **`ovs1` (dpid 1, Cell-1 access)** and **`ovsgw` (dpid 3, aggregation/mirror/seams/NAT)** — joined by a **patch/uplink** (`UPLINKS={1:[3],3:[1]}`); Dell#3 runs **`ovs2` (dpid 2)**. All three point at `tcp:10.10.10.1:6653`. Because the channel is out-of-band, an OT-plane attacker cannot see or reach it. Verify:
```bash
sudo ovs-vsctl get-controller ovs1 ovsgw            # both -> tcp:10.10.10.1:6653
sudo ovs-ofctl -O OpenFlow13 show ovsgw | grep -iE "patch|peer"   # the ovs1<->ovsgw fabric link
ss -tnp | grep 6653                                 # live OpenFlow sessions (on Dell#2: 3 switches connected)
```

## C.3 Cell-2 reachability & NAT (why PLC2 is `.3.10`, and the identity collapse)
Both teaching boxes reuse the **same clone IP `192.168.2.10`** on **separate L2 segments**. To let Cell-1 reach PLC2 without an IP clash, PLC2 is fronted at **`192.168.3.10`**: the Cell-2 gateway path **DNATs `.3.10` → the real `.2.10`** on Dell#3, and **MASQUERADEs** the return so the real source is hidden (the `cars_engine.py` `DEFAULT_DENY` note, lines 55-57, documents exactly this — it's why the real-PLC deny is scoped to `ovs1`/dpid1 only, so the NAT path isn't severed). The Cell-2 eng station is `.3.66`. Verify:
```bash
sudo iptables -t nat -L -n -v        # on the Cell-2 NAT host (DNAT .3.10->.2.10, MASQUERADE)
```
**Honest consequence:** because the return is MASQUERADEd, and IT-side attackers are SNAT'd (C.4), multiple real sources can **collapse to one identity** at the OT edge → boundary **G5**. CARS judges what it can see; the NAT is the limit.

## C.4 The IT→OT kill chain (the skin / external attack surface)
The external attack path is a virtual **GNS3** periphery on Dell#1 (kept off the CARS core): **IT `10.0.40.0/24`** → **Enterprise-FW (VyOS)** → **DMZ `172.16.35.0/24`** → **OT-FW (VyOS, SNAT)** → OVS **internal seam `it0`** (no host IP) → into `ovsgw` → OT. Verified end-to-end routed (TTL 30→29→28). Every IT attacker **SNATs to `192.168.2.1`** at the OT-FW, so from CARS's view the whole enterprise is the single identity `gateway .2.1` (the pragmatic real-world truth: you defend the conduit, not the far-side host — **G5**). The insider vantage (**Kali `.2.77`**) sits *inside* the OT segment and is the harder, more honest adversary.

## C.5 What the "process" really is (state this plainly — it's still legitimate)
- **Real:** the **control logic runs on the real S7-1200** (a cyclic OB every 100 ms) and the **pump output `Q0.3` is a real electromechanical relay** (the clicking you hear; the wear you saw).
- **Simulated:** the tank **`Level` is a software value in `DB7` that the OB integrates** (`Level += FillRate` when the pump is on, `-= DrainRate` when off), with bang-bang thresholds 30/70. **There is no physical tank or analog level sensor.**
So it's a **PLC-resident process simulation driving real I/O** — the attack surface (S7 writes to DB7 / forcing Q0.3) and the physics (pump latch, overflow logic) are genuine and run on the real CPU; only the water is virtual. That's an honest, defensible demo — and it's exactly why the sensor-false-data attack is meaningful (it corrupts the real DB the real loop acts on).

## C.6 The supervisory / historian layer (the operator organ)
Present on Dell#1's OT foot **`.2.30`** (OVS internal port `ot0`): **InfluxDB 2.7** (`:8086`, historian store), **Grafana 11.1** (`:3000`, dashboards), **FUXA** (`:1881`, web SCADA/HMI with S7 + Modbus drivers). CARS treats these as ordinary assets under role **`historian`/`supervisory`** (so their traffic is policed like everything else). **Verified live 2026-07-24** (Influx 200 / Grafana 302 / FUXA 200). Live PLC tags are gated on PUT/GET on the PLC, but the stack itself is up. It exists so a reviewer sees the Purdue supervisory tier; it is peripheral to CARS's *enforcement*, which is the thesis.

## C.7 Failure & degradation matrix (what breaks what — the resilience answer)
| Component down | Detection | Enforcement still holding | Process | Net effect |
|---|---|---|---|---|
| **Controller (brain)** | reactive decisions pause | **YES** — OVS `fail_mode=secure`: GUARD (T0) + A2 allow/deny (T1 P55/60) + active blocks persist | agent still heals | **fail-secure** (proven, VC-4); listed source's *new* dangerous op not reactively blocked until it returns |
| **Snort (sensor)** | **blind** to ICS-op attacks | **YES** — proactive A2 default-deny + GUARD are pre-installed flows, independent of Snort | unaffected | unlisted still dropped, spoof still dropped, allowlist still flows; lose reactive op-blocking from *listed* sources. **CC-76 (FIXED 2026-07-24): `cars-bridge` was coupled to `cars-snort` so bouncing Snort silently dropped the bridge and didn't revive it. Hardened with a systemd drop-in (`Wants`+`PartOf`+`Restart=on-failure`) so the bridge now cycles with Snort.** |
| **`snort_bridge.py`** | alerts pile up unposted | YES (as above) | unaffected | same as Snort-down; on restart it tails from `-n0` and resumes |
| **Remediation agent** | n/a | network block unaffected | **no auto-heal** | under *armed*, attacker still cut after ~1 packet (minimal harm); under *disarmed*, no process healing |
| **An OVS switch** | that segment dark | its cell isolated | that PLC unreachable | hard local outage; on restart, clean-slate rebuild + controller re-pushes pipeline |
| **hAP / control net** | packet-ins stop | frozen at last flows (fail-secure) | agent still heals | equivalent to controller-down |
| **Single controller (SPOF)** | — | — | — | **G6** — resilient/redundant control plane is explicit future work |

## C.8 Security of CARS itself (who guards the guard — say this before they ask)
- The **Event API `:8080` is unauthenticated**, and **OpenFlow `:6653` is plaintext (no TLS)**. This is **safe only because the control plane `10.10.10.0/24` is physically out-of-band** on the hAP and **not routable from the OT plane** — an OT-side attacker cannot reach `10.10.10.1` to `curl` the API or inject flow-mods. Confirm the isolation: from an OT seam, `curl` to `10.10.10.1:8080` should **fail/time out**.
- **It's a designed trust boundary, not an oversight:** the assumption is *"the management network is protected."* Hardening (API token/mTLS, OpenFlow-TLS, mgmt-plane ACLs) is named future work — stating it shows you know the threat model of your own controller.
- **Blast radius if the brain is subverted:** it can install/withdraw flows on all switches — hence the **safety cap** (`hmi↔plc = REFUSE`) is a *code invariant*, and the **remediation agent is deliberately audit-independent** (can't be ordered around from the control plane), so a compromised brain still can't sever the loop or stop the process guardian.

## C.9 Cold-start & clock (operational reality)
- **Boot order:** hAP → teaching boxes → the three Dells. **Auto-restores** on boot: OVS bridges/ports, the `ot0`/`it0` seams (`ot0-ip.service`), nmcli static control-plane IPs, Docker (`unless-stopped`), and the `cars-*` systemd units on Dell#1. **Manual:** start the controller on Dell#2 (`cd ~/cars && source venv/bin/activate && osken-manager ~/cars/cars_engine.py`, in tmux) and GNS3. `fail_mode=secure` means the switches **keep enforcing** across a controller restart. Full SOP: **`06_Build/COLD_START.md`**.
- **Clock sync:** the cross-source evidence (Kali attack ↔ controller audit ↔ agent feed agreeing to the second) assumes the Dells + Kali share time. The controller audit uses local `strftime`; the agent uses Unix `time.time()`. For citable evidence keep them NTP-synced (or note the reference clock); tonight they aligned to the second, which is the corroboration you saw.

**Net:** with Appendix C, the sheet now covers brain (A), muscle (A.7/§7), skeleton (§2/C.2), **nerves (C.1/C.2)**, **skin (C.4)**, the **supervisory organ (C.6)**, the **honest process reality (C.5)**, **resilience (C.7)**, and **self-security (C.8)** — the full body, warts documented.

