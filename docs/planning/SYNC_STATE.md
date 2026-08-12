# CARS — SYNC STATE (master ↔ deployed truth) · keep current every session

_Purpose: durable record so context survives conversation compaction. Update this whenever a file is changed or deployed._
_Last updated: 2026-08-01 (session: accuracy eval, deception demo, GRAND validation campaign — implementation FINALISED)._

## SESSION 2026-08-01 — implementation FINALISED; validation complete (see DECISION_LOG CC-99, CC-99b, CC-100)
**★ STATUS: TECHNICAL IMPLEMENTATION IS COMPLETE. Everything is built, deployed, and validated. From next session we WRITE THE REPORT
from scratch, re-running each showcase/test/eval cleanly per report section and capturing evidence as we go. Nothing done so far was
captured as report evidence — it was all system validation to confirm everything is in place. Do NOT treat today's `/tmp/grand_campaign`
artifacts or the uploaded CSVs as final report evidence; they proved readiness. The report gets its own fresh, traceable runs.**
- **Accuracy / false-positive evaluation (CC-99):** `06_Build/cars_eval.py` — 27-case decision matrix via `/cars/respond`, grounded in
  deployed REGISTRY+RULEBOOK. Result **TP=13 TN=11 FP=0 FN=0, 100% accuracy, 0% FP**. Report `EVALUATION_REPORT.md` + `cars_eval_matrix.csv`.
- **Deception demo (CC-99b):** sensor-spoof FDI overflow — tank driven ~195% while PLC/HMI read empty; 70/70 spoof writes judged ISOLATE
  (detection identical disarmed). Appendix in `EVALUATION_REPORT.md`, `cars_deception_decisionlog.csv`.
- **GRAND validation campaign (CC-100):** 7 phases wire-level, armed vs unprotected, full cross-layer audit. `GRAND_VALIDATION_REPORT.md`,
  harness `06_Build/cars_campaign_lib.sh`. Recon / spoofing / state / control-plane / op-aware / process-devastation / response-ladder —
  all validated. 3-state method (flat-net bypass `cookie 0xb1` vs disarmed vs armed). Key learnings baked in: proactive default-deny is
  NOT arm-gated (outsider blocked even disarmed); reaction-window (~1s) leaks only inert packets; layered defence; 0 FP throughout.
- **Deliverables now in repo:** `EVALUATION_REPORT.md`, `GRAND_VALIDATION_REPORT.md`, `WIRE_VALIDATION_REPORT.md`, `DECISION_LOG.md`
  (through CC-100), plus harnesses `cars_eval.py`, `cars_campaign_lib.sh` in `06_Build/`.
- **PACKUP 2026-08-01:** CARS left ARMED; Factory IO tank running (scene Start; buttons work); all Phase-7 reactive flows auto-expired;
  flow-audit `ok:1`; remediation left STOPPED (Factory IO uses the live loop for maintain); `.2.31`/`.2.66`/`.2.67`/`.2.77` isolates all
  self-expired. Testbed clean + safe to power down. `/tmp/grand_campaign` bundle clears on reboot (validation only — fine to discard).
- **NEXT SESSION — REPORT WRITING (from scratch):** build the dissertation section by section; for each section, RE-RUN the relevant
  testbed setup / implementation demo / CARS showcase / test / evaluation FRESH and capture the evidence for that section. Redo everything
  needed as we go. The system is final and stable; the task now is authored narrative + clean captured proofs mapped to each chapter.
- **★ TODO (Amit, priority for next session): DEDICATED CRITICALITY SHOWCASE — not yet run as its own test.** Criticality was validated
  PIECEWISE (decision-side elevation SENSITIVE→FORBIDDEN on CRITICAL, and response-side duration scaling 75/60/30s seen in CC-99 grey rows
  + campaign P1/P7), but NOT as a single clean sweep. Build one test that fires the SAME attack (e.g. a SENSITIVE WRITE, and/or a flood) at
  a CRITICAL (.2.10), HIGH (.2.9), MEDIUM (.2.30), LOW (.2.20) asset in turn — tier is the ONLY variable — producing a 4-row table where
  decision + response + block-duration graduate monotonically (75/60/45/30s). NOTE: MEDIUM tier (.2.30/.3.9, 45s rung) never exercised
  explicitly yet — this closes that gap. This becomes the named subsection proving the "criticality-aware" thesis claim.
- **REMEDIATION SCOPE — DECIDED (CC-101): clean-scope-and-document.** Remediation last-good-restore = validated on the in-PLC SIM only
  (wire CC-88/96). On the live Factory IO loop it is NOT run/tested (it fights the live sensor; blinded by sensor-spoof). Live "maintain"
  = physical control-loop self-recovery after CARS isolates the attacker (shown Phase 6 + re-arm recoveries). Dissertation framing drafted
  in CC-101 (novelty intact, boundary defended, live sensor-aware remediation = future work). Keep `cars-remediation` STOPPED for Factory IO.
- **BRING-UP checklist (unchanged):** power PLC teaching boxes ON first; green-light seam ofports (rem0ovs=14, opr=10, mbplc=7);
  re-baseline flow checker + `systemctl restart cars-flowaudit`; recreate `/tmp/rd2.py` (clears on reboot — the `%IB10` reader with
  `c.disconnect()`); STOP `cars-remediation` for the live Factory IO loop (frees a PLC1 S7 slot); recovery after any PLC download =
  Start CPU → Factory IO Stop/Play → press scene Start.

## SESSION 2026-07-31 — Factory IO operator control + LIVE attack campaign (see DECISION_LOG CC-98d, CC-98e)
**DONE + PROVEN this session:**
- **Factory IO SCENE SWITCHES working (CC-98d):** Start latches `Running %M0.0` → fills; Stop halts; Reset flickers lamp — all live-proven. Two faults fixed: (1) buttons were on onboard `%I0.0–0.3` (1212C refreshes those from unwired terminals each scan → wiped Factory IO's writes) → remapped Factory IO **Bool Inputs offset 0→10** (`%I10.x`), PLC tags repointed; (2) scene **Stop is normally-closed** (`%I10.2` rests at 1) → OB30 changed `"StopBtn"`→`NOT "StopBtn"` (fail-safe: FIO disconnect → stop). `/tmp/rd2.py` on Dell#1 extended to read `%IB10`. **HMI panel buttons still deferred** (panel Transfer/Settings locked in Start Center; `HMI_Start/Stop %M0.1/0.2` already wired, activate when HMI project downloads).
- **Flowaudit noise fixed + policy KEPT:** the `.2.55→.2.9:102` conduit (CC-98c) was flagged EXTRA every poll (stale baseline post-`/cars/reload`). Verified it was the only drift (missing=0, changed=0), **re-baselined** (`--baseline` + `systemctl restart cars-flowaudit`) → `ok:1`. **CC-98 policy change KEPT** — necessary, narrowly-scoped (only READ/WRITE/CONTROL=OPERATIONAL; PROGRAM/DIAG/ILLEGAL stay FORBIDDEN), anti-spoofed. CARS re-armed; Factory IO cycles clean under enforcement (`.2.55 … OPERATIONAL ALLOW`, 0 isolate).
- **LIVE ATTACK CAMPAIGN (CC-98e) — two vectors, armed vs disarmed, reader=`remns/.2.45`:**
  - **`.2.31` compromised insider** (opns) forces fill valve: ARMED = **0 writes landed**, isolated <1s (`S7 CONTROL FORBIDDEN→ISOLATE [CRIT:CRITICAL]` ENFORCED, `0xca`=1 both bridges), tank steady. DISARMED = **207 writes @26/s**, actuators seized (Fill→100/Disch→0), CARS decides ISOLATE but **MONITOR** (detection identical, arming is the difference). Level did NOT overflow — PLC bang-bang **high-level interlock** caps at >70 (defense-in-depth); contrast is **control authority** not level number. Full overflow needs sensor-spoof (`%ID100=0`) — deferred (visual/screenshot).
  - **`.2.77` external outsider** (Kali VM, vmnet2→ovsgw p12, unregistered): isolated at **TCP connect** (default-deny, no grace), `0xca`=1 both bridges, **Kali side: 6/6 TCP:102 connects BLOCKED, 0 landed**, tank untouched. `guard{.2.77}={}` correct (unregistered ≠ GUARD-protected). Repeated audit lines = DPI re-observing retries, not a leak.
  - **Evidence:** live audit + 3 decision CSVs (`cars_decisions_1785533492405/875168/534167717.csv`) + isolate-flow dumps + remns tank reads + Kali stdout.
- **PACKUP 2026-07-31:** CARS left **ARMED** (`enforce_enabled:true`); tank running (scene Start); `.2.31`/`.2.77` isolates auto-expire at 75s. Flow-audit re-baselined to trusted policy (`ok:1`). Master `cars_engine.py` unchanged this session (only rulebook/allowlist from CC-98 already deployed); OB30 (Stop NC) + Factory IO offset-10 are on the Win Dell TIA/FIO project.

**NEXT SESSION AGENDA (2026-08-01) — the Monday validation pass:**
1. **Accuracy / false-positive evaluation (the main deliverable):** build the evaluation matrix — every (src→dst→op→tier) combination across the topology, expected decision vs measured decision, tally TP/FP/TN/FN. Run the full legit-traffic mix (all A2 conduits + Factory IO HIL) confirming **0 false positives**, plus all attack scenarios confirming detection. This is the dissertation evaluation-chapter evidence.
2. **(Optional) sensor-spoof overflow visual:** `.2.31`/Kali writes `%ID100=0` to blind the interlock → real 3D tank overflows → Factory IO screenshot (numeric reads show spoofed value = the deception story). Armed = blocked, disarmed = overflow.
3. **Deferred (not blocking):** HMI panel buttons (panel transfer locked); pin Win-Dell port-12 ofport for `.2.55` binding durability; Kali `.2.77` recovery at true final teardown; SDN Phase 2/3 (#21 QoS, #22 micro-seg), #29 MoTaR deception (design/isolated only).
**BRING-UP checklist (unchanged):** power PLC teaching boxes ON first; green-light seam ofports (rem0ovs=14, opr=10, mbplc=7); re-baseline flow checker + `systemctl restart cars-flowaudit`; recovery after any PLC download = **Start CPU → Factory IO Stop/Play → press scene Start**.

## SESSION 2026-07-30 — bring-up + full robustness validation (see DECISION_LOG CC-94, CC-95)
- **Bring-up green-light** passed; **ofport-drift regression fixed** (CC-94): `rem0ovs` drifted 14→13 (Kali took 14) → remns ARPs dropped as spoof + remediation offline. Runtime-pinned + baked `ofport_request=14` into `cars-remns.sh`. Also: PLC1 teaching box was off (operator powered on). **Bring-up checklist: green-light the seam ofports (rem0ovs=14, opr=10, mbplc=7) + re-baseline flow checker + `systemctl restart cars-flowaudit`.**
- **#28 SEALED**: `/cars/flowaudit` endpoint live, fixed checker deployed, `cars-flowaudit.service` running.
- **Stateful attack-path re-seal** PASS: op-aware READ⇒ALLOW / WRITE⇒ISOLATE[CRIT:CRITICAL,elevated], Kali⇒isolate, reactive isolate installs prio110 over ct rules, loop unbroken.
- **ROBUSTNESS BATTERY (CC-95) COMPLETE + tight:** flow-integrity checker validated LIVE (inject/remove/rewrite/black-hole on real A2) + isolated (loop/black-hole); **HARDENED** with distinct `REACTIVE_COOKIE=0x00CA` (closed the reactive-envelope evasion, proven caught); controller-compromise sim (C2 independence PASS; C3 full-compromise + C1 poll-window = documented boundaries); stateful pipeline robustness 4/4 (no out-of-state bypass, no ct-exhaustion).
- **DEPLOY-ORDER LESSONS baked in:** (1) `ofport_request` pin the seam ports; (2) after ANY checker code change OR re-baseline, `systemctl restart cars-flowaudit` (else the running daemon uses stale code/baseline and false-alarms — observed live).
- **MASTER↔DEPLOYED (2026-07-30):** `cars_engine.py` master==deployed (guard bindings+visibility, flowaudit endpoint, REACTIVE_COOKIE all deployed+restarted). `cars_flow_audit.py` deployed (is_reactive→0xca). `cars-remns.sh` pinned. `cars-flowaudit.service` installed. Robust-test harnesses in `06_Build/` (isolated, not deployed — run on demand).
- **WIRE-LEVEL VALIDATION (CC-96) + DISARMED BASELINE done:** full armed-vs-disarmed attack campaign captured at 3 wire points + cross-device state. Report: `WIRE_VALIDATION_REPORT.md`. Result: armed = attacker cut on the wire + process maintained; disarmed = 16/16 writes land, level pinned 5.0→12, then clean recovery on re-arm. Detection identical both modes; enforcement is the difference.
- **PACKUP 2026-07-30 (end of session):** tests were self-restoring — disarmed run RE-ARMED CARS (`enforce_enabled:true`) + restarted remediation at its end; V2 tamper restored; isolates auto-expired. Testbed left process-safe + CARS armed. Temp campaign dirs (`/tmp/campaign*`) clear on reboot.
- **NEXT BRING-UP checklist:** (1) power PLC teaching boxes ON first; (2) green-light seam ofports (rem0ovs=14, opr=10, mbplc=7); (3) re-baseline flow checker (`--baseline`) + `systemctl restart cars-flowaudit`; (4) recover Kali `.2.77` if doing final wrap-up (else leave OT-only attacker).
- **NEXT WORK:** Factory IO (step 4) — the live demo/validation vehicle. Everything it builds on is now robustness- + wire-validated. Need at bring-up: CARS hosts + ovsgw uplink ports (how Win Dell appears), Win Dell IP (ipconfig), Factory IO scene list.

_Prior: 2026-07-29 (session: retrofits + flow-integrity checker)._

## SESSION 2026-07-29 — gaps closed + new candidate A (see DECISION_LOG CC-90..93)
**DONE + PROVEN this session:**
- **#25 remediation topology-wide:** PLC1 agent was a ZOMBIE (dead S7 conn, no reconnect) → fixed with auto-reconnect, revived live. Agent now config-driven (`cars_remediation.py` profiles plc1/plc2). **Tank2 process-maintenance BOUNDED** by PLC2's 1212C S7 connection limit (proven 3 ways) → documented, NOT hacked (CC-91). Tank2 still gets CARS network-block (Cell-2 IS gated via ovsgw/ins2 — refines old G6). Option A (TIA connection-resource bump) is the clean path if full symmetry wanted later.
- **#26 GUARD anti-spoof → trusted seams:** added BINDINGS for scada .2.31 (ovsgw p10), remediation .2.45 (p14), modbus .2.20 (p7). **PROVEN live:** legit path unbroken (n_packets=114), spoofed .2.45 from wrong port dropped 0→5, guard API confirms (CC-92). Deployed to Dell#2 engine + restarted.
- **#30 spoof VISIBILITY:** guard drops were silent → added `_guard_seen()` emitting a decision-log event on drop-counter climb. **PROVEN:** spoofed .2.31 x4 + .2.45 x5 → two `FORBIDDEN/SPOOFED/REFUSE` rows in /cars/audit AND dashboard CSV (CC-92b). Deployed + restarted.
- **#28 flow-integrity checker (new candidate A):** `06_Build/cars_flow_audit.py` + `cars_flowaudit_test.sh`. Isolated 6/6; **LIVE detection proven** (caught injected 0xbad rule on ovsgw). Baseline logic fixed (all non-reactive, no prio-0 false positive). (CC-93)

**NEXT SESSION — finish #28 (small), then continue week plan:**
1. Deploy `/cars/flowaudit` endpoint on Dell#2 (patch STAGED in master `cars_engine.py`, NOT yet deployed) + restart controller.
2. Re-baseline with the fixed checker: `sudo python3 cars_flow_audit.py --baseline --bridges ovs1,ovsgw` → `--check` must read CLEAN (prio-0 false positive fixed).
3. Inject harmless bogus rule → confirm drift line lands in decision log + dashboard (this session it posted into the void — endpoint wasn't deployed).
4. Install `cars-flowaudit.service` watch-daemon (like remediation).
5. Then continue WEEK_PLAN: SDN Phase 2 (QoS #21), Phase 3 (micro-seg #22); backlog #30-done, #17 token rotation, #29 deception design.

**FACTORY IO — INTEGRATED + RUNNING ARMED (2026-07-31, CC-98).** Level Control scene on Win Dell (EWS .2.55) drives PLC1's real loop; runs clean under ARMED CARS. Mapping: level `%ID100`(0–5), fill `%QD100`, discharge `%QD104`; OB30 scales ×20 → `DB7.Level` 0–100, bang-bang 30/70. `.2.55` authorised (rulebook ews→plc READ/WRITE/CONTROL=OPERATIONAL before dangerous block; FLOOD_EXEMPT; GUARD anti-spoof binding port12/b4:e9:b8:a4:ce:46). Remediation STOPPED for Factory IO (fights the live sensor; control-loop provides maintain). NEXT: attack demo (compromised .2.31 forces `%Q` fill valve → overflow → CARS isolate → recover; armed vs disarmed). Pin port-12 ofport for durability; re-baseline flow-audit after policy change.

**FACTORY IO LIVE-DEMO (original plan):** deploy a Factory IO process on the **Windows Dell** (same box as TIA Portal) as the live validation/demo vehicle for CARS. Win Dell is **connected to Dell#1**, so its S7 traffic to the PLC traverses the CARS OVS fabric = CARS-governed (the make-or-break condition is satisfied). Driver = Factory IO S7-1200 (PUT/GET, maps %I/%Q). **Primary target = PLC1/Cell-1** (full DPI/criticality/remediation coverage). NOTE: **PLC2/Cell-2 ALSO runs a closed-loop process** (Tank2 bang-bang band 20-55) — a two-cell demo is possible later. Win Dell is most likely the **EWS `.2.55`** identity (role exists in model, no netns because it's this real machine) — CONFIRM its exact OVS port + IP tomorrow. To resolve tomorrow: (1) scene (pre-installed vs custom on-theme level/tank), (2) PLC1 S7 connection-slot budget (HMI+collector+remediation+FactoryIO vs 1212C limit — may pause collector during demo), (3) allowlist the Factory-IO↔PLC conduit so its fast poll isn't flood-flagged (FLOOD_RATE=5), (4) PUT/GET enable + %I/%Q program mapping so legit input-writes stay clean while attacker %Q-forcing stays DPI-caught.

**⚠ TESTBED-DOWN RECOVERY (standing instruction from Amit):** Kali `.2.77` was made an OT-only untrusted insider + UNREGISTERED from the engine REGISTRY for the pen-test. Amit said to **recover the previous setting before putting the testbed down** (re-add .2.77 to supervisory/registry with labels + restore its prior homing). NOT done this session — do at next bring-up or now if still reachable.

**MASTER↔DEPLOYED drift after this session:** `cars_engine.py` master has TWO changes vs deployed: (a) GUARD BINDINGS + `_guard_seen` visibility = DEPLOYED ✅; (b) `/cars/flowaudit` endpoint = **STAGED, NOT deployed**. `cars_remediation.py` master (multi-PLC + reconnect) deployed to Dell#1 ✅ (PLC1 service runs it; PLC2 instance was manual, now down with testbed).

_Last updated (pre-2026-07-29): 2026-07-24 (deep audit CC-78)._

## DEEP AUDIT 2026-07-24 (CC-78) — deployed vs master reconciled
All deployed artifacts diffed against masters. **Deployed engine/bridge/remediation/mb_server/dashboard are functionally identical to masters** (comment/whitespace only). Confirmed: **criticality badge IS deployed** (`cars_dashboard-31045dcf.py` == master); CC-76 bridge↔snort drop-ins deployed; Cell-2 setup = `/usr/local/sbin/cars-cell2.sh` (Dell#3). Master edits this session — **ALL DEPLOYED + VERIFIED on hardware 2026-07-24 21:2x via cars_deploy_verify.sh:**
- `cars_engine.py` (Dell#2): F2 seed fix (+2 remediation RULEBOOK rows, +4 ALLOWLIST conduits). **DEPLOYED; seed==runtime verified live (29/8); controller healthy (PLC1=CRITICAL). Not restarted (runtime unaffected).** master==deployed.
- `cars_dashboard.py` (Dell#1): F1 ROLE/TYPEOF/hlabel sync (+.2.20/.2.31/.2.77/.3.66, +supervisory glyph). **DEPLOYED + process relaunched (nohup pid 225442 — no systemd unit); running :8090 confirmed serving the new ROLE map.** master==deployed.
- `cars.rules` (Dell#1 `/etc/snort/cars.rules`): N2 Cell-2 0x28 sid 1000048. **DEPLOYED; snort -T clean; cars-snort+cars-bridge restarted together (CC-76).** master==deployed.
- **N1 CLOSED:** `cars.conf` received — `HOME_NET 192.168.2.0/24`, `EXTERNAL_NET any`, `include /etc/snort/cars.rules` (rules path confirmed = /etc/snort/cars.rules, NOT /rules/).
- Deploy tool: `06_Build/cars_deploy_verify.sh` (backup-first, snort -T pre-swap, rollback-on-fail; needed `sudo cp` fix for the /etc write).
- **N3 CLOSED (Option A):** `att0` (MTTM base-ns vantage) renumbered `.2.66`→**`.2.67`** in `cars-seams.service` (Dell#1, `/etc/systemd/system/`) + live + `mttm.py SRC=.2.67`; `atkns/atk` keeps canonical `.2.66`. No more duplicate on ovsgw. (`cars-seams.service` + `mttm.py` are Dell#1-only, not in E:\; backups in `~/cars_backup/`.)
- STILL OPEN (optional, deferred by user): `cars-dashboard.service` (dashboard runs nohup, no auto-restart) — user prefers to hand-edit the py when needed.

## ⚠️ KNOWN DIVERGENCE (discovered 2026-07-23)
The **deployed** files on the Dells are NOT always byte-identical to the E:\ masters. Confirmed drift:
- **cars_dashboard.py**: the DEPLOYED copy on Dell#1 (`~/cars_dashboard.py`) is a **newer build** than the E:\ master —
  it has a live **topology feed in `poll()`** and a **separate `logPoll()`** function (line ~284) that runs the Decision-Log
  `accumulate()`. The E:\ master ran `accumulate()` inline at the end of `poll()`. → anchors in that region differ.
  **Deployed is authoritative** (it's what runs). Reconcile the master by ingesting the full deployed file when convenient.
- **cars_remediation.py**: deployed copy had drifted from the master's first lines → on 2026-07-23 it was **overwritten
  wholesale** with the current master (full-file heredoc, backup at `~/cars_remediation.py.bak`). Now in sync.

**Rule going forward:** before shipping an anchor-based patcher, confirm anchors against the deployed file
(`grep -n`), because master≠deployed. Prefer full-file overwrite for small files; anchored patchers only for big ones,
and always compile-guarded + abort-safe (build in memory, `py_compile`, write only on success).

## Node-RED historian-collector (CC-80, 2026-07-24) — LIVE
- Master flow: `06_Build/cars_nodered_flow.json` (import into Node-RED editor :1880). S7 PLC1 (DB7.REAL0=level, Q0.0=pump) -> MQTT `cars/cell1/plc1/*` -> InfluxDB (`cars`/`plc`) -> /ui.
- Infra: Mosquitto `127.0.0.1:1883` (apt+systemd, Dell#1). InfluxDB docker (org=cars, bucket=plc, token=cars-token-change-me [ROTATE later]). Collector identity = `.2.30` (historian, via sup0).
- CARS: a2_policy.json runtime allow=10 (+.2.30->.2.10:102, +.2.30->.2.20:502); engine ALLOWLIST seed=10 (seed==runtime). PROVEN: `.2.30 -> .2.10 S7 READ => ALLOW [CRIT:CRITICAL]`.
- OPEN: Modbus node deferred (Node-18 vs contrib-modbus@5.60 needs Node>=22); confirm InfluxDB landing + /ui; two node-red instances (:1880 plain / :1882 industrial) to consolidate.

## D2 two-tank (CC-81, 2026-07-25) — LIVE
- PLC2 (S7-1200 1212C, Cell-2 `.3.10`/NAT, HIGH) now runs the same in-PLC tank sim as PLC1 (DB7 "Sim", cyclic OB 100ms, pump `Q0.3`), tweaked to band 20..55 (fill+0.4/drain-0.6). Programmed via direct TB2-switch link then rewired to Dell#3.
- Node-RED add: `06_Build/cars_nodered_cell2_add.json` → `cars/cell2/plc2/{level,pump}`; subscribe broadened `cars/#`; cell1 pump bit fixed `Q0.0`→`Q0.3`. CARS unchanged (`.3.66→.3.10:102` already allowlisted; reads ALLOW [CRIT:HIGH]).
- PLC1 tank truth: **in-PLC SCL sim, NOT a physical sensor** (DB7 "Sim", pump Q0.3, 1212C). HMI1's real screen is in a different project than `CARS_Tank_test.ap18`.

## PEN-TEST posture (CC-82, 2026-07-25) — TEMPORARY; revert after
- **`.2.77` fully untrusted:** REGISTRY line commented (unregistered→unknown) + 2 ALLOWLIST seed conduits commented in `cars_engine.py` (master + deployed Dell#2); runtime `a2_policy.json` `allow=8` (.2.77 conduits removed, hot-reloaded); dashboard ROLE `.2.77`→`unknown`. **To revert:** uncomment the 3 engine lines (25/59/60) + re-add the 2 a2_policy conduits + reload-a2 + set dashboard back to supervisory, restart controller.
- **Node-RED STOPPED** (`snap stop node-red`) — paused for clean pen-test log + to free PLC1 S7 slot for remediation. Restart: `snap start node-red`.
- **Remediation** restarted, live on Tank 1 only (Cell-1 hardcoded). Tank 2 has NO remediation (finding).
- **CARS** was DISARMED (defense off) for the raw-footprint baseline scan at end of session — **RE-ARM before leaving** (`POST /cars/defense {"on":true}`).
- Playbook + findings: `PEN_TEST_PLAYBOOK.md`. Scan outputs on Kali: `~/pentest_recon_*`, `~/pentest_full_scan_*`.
- **Kali confined to OT for honest insider test:** `nmcli device disconnect eth0` (VMware NAT/mgmt) + `eth2` (IT 10.0.40.66); only eth1=`.2.77` left. **REVERT before shutdown:** `nmcli device connect eth0 && nmcli device connect eth2`. While confined, toggle CARS from Dell#1/#2 (Kali can't reach 10.10.10.1). Kali is triple-homed: eth1=.2.77 OT, eth2=10.0.40.66 IT, eth0=NAT/mgmt.
- **P0-4 finding:** control API (`10.10.10.1:8080`) is unauthenticated + control actions unlogged → silent disarm possible from any host with a control-plane path (the Kali reached it via eth0 NAT = test-VM artifact, not an OT/IT breach). FIX for writeup: authenticate API (token/mTLS) + audit-log arm/disarm/restore/reload.

## CONTROL-API AUTH (CC-85, 2026-07-27) — IN EFFECT
- Control POSTs (`/cars/defense,maintenance,reload,reload-a2,block,unblock,restore`) now require header **`X-CARS-Token`**; token at **`~/cars/api_token`** on Dell#2 (0600). Current token: `a1299b2294293267641198cd28bb62db` (rotate anytime by editing the file + restart, or `CARS_API_TOKEN` env).
- **All operator control curls + validation scripts must add** `-H "X-CARS-Token: $TOKEN"`. Read GETs + `/cars/respond` (bridge) unchanged.
- For scripts on Dell#1: place the token at `~/cars/api_token` there too (or `export CARS_API_TOKEN=...`).

## SDN PHASE 1 — STATEFUL conntrack policy (CC-89) — LIVE on the fabric
- `cars_engine.py`: `STATEFUL=True` (master==deployed Dell#2). Table 1 now ct()-based (`-trk→ct`, `+est→allow`, `+new&allowlisted→commit`, `+new&protected→drop`, `+new→commit`). Fail-safe: any install error → classic path. Rollback = `sed 's/^STATEFUL = True/STATEFUL = False/' ~/cars/cars_engine.py` + restart (and drop `.2.9` from a2_policy default_deny).
- Runtime a2_policy default_deny = 4 (`.2.20`, `.2.10`, `.2.9`×2). `.2.9` shield ONLY safe with STATEFUL=True.
- PROVEN: HMI `.2.9:102` filtered to confined insider + HMI panel LIVE + loop unbroken (collector/remediation flowing, ct +est n=15101). Isolated proof `06_Build/cars_stateful_test.sh` (3/3). API pre-validated in venv.
- **BULLETPROOF GAP (do first next session):** re-run full no-regression under STATEFUL=True — confirm reactive ISOLATE/BLOCK + A3 op-awareness + criticality response + remediation all still fire under the ct pipeline. Happy-path proven; attack-path not yet re-verified live under stateful.

## HARD RULE (standing): every capability WHOLE-topology / every-device — industry relevance, not a thesis demo. Binding retroactively + on all future work. (See DECISION_LOG hard-rule note.)

## NEXT AGENDAS (priority order — RETROFITS FIRST per the hard rule: make existing capabilities whole before adding new)
0a. **Retrofit remediation to ALL PLCs** (#25): PLC2/Tank2 currently has NO remediation - biggest whole-topology gap. Multi-PLC/config-driven; prove Tank2 spoof->block+restore.
0b. **Retrofit GUARD anti-spoof to all devices** (#26): bind Modbus .2.20 + trusted seams .2.31/.2.45/.2.55/.3.66; verify a spoofed .2.45/.2.31 is dropped.
1. **Seal Phase 1: DONE** (2026-07-27 - enforcement path verified under STATEFUL, zero regression; CC-89).
2. **SDN Phase 2** (#21): control-loop QoS/metering (guarantee loop latency under DoS) + isolated fast-failover prototype (topology is single-uplink → real failover needs a redundant link).
3. **SDN Phase 3** (#22): dynamic micro-segmentation (time-bounded conduits as data-plane flows).
4. **SDN Phase 4** (#23): cross-flow global analytics (lateral-movement/scan campaign detection).
5. **SDN Phase 5** (#24): P4/BMv2 line-rate op-enforcement — ISOLATED Mininet only (never live tanks).
6. Backlog: Modbus re-add Node-18 (#14); `/ui` polish + rotate `cars-token-change-me` (#17); cosmetic registry tidy (.3.66 criticality, deployed name strings); remaining pen-test phases (IT eth2, supervisory).

## Deploy map (where each master runs)
| Master (E:\...\06_Build\) | Runs on | Deployed path | In sync? |
|---|---|---|---|
| cars_engine.py | Dell#2 | ~/cars/cars_engine.py | **YES - v0.7 (asset criticality), reconciled + redeployed 07-24 (CC-77). master==deployed.** Runtime rulebook.json: ews->plc/hmi = SENSITIVE (Option A). NOTE: REGISTRY/CRITICALITY are in code; RULEBOOK/ALLOWLIST authoritative = rulebook.json/a2_policy.json (runtime), not the code seeds. |
| snort_bridge.py | Dell#1 | ~/ (v4) | **YES (audit CC-78: deployed==master, comment drift only)** |
| cars.rules | Dell#1 | /etc/snort/rules/cars.rules | **master edited (N2 sid 1000048) — DEPLOY+reload pending** |
| cars.conf (active Snort cfg) | Dell#1 | /etc/snort/cars.conf | **NOT in E:\ — user to upload (N1)** |
| s7_write.py | Dell#1 + Kali | ~/ | yes (incl. --dbspoof) |
| cars_remediation.py | Dell#1 (remns netns) | ~/cars_remediation.py | **yes (overwritten 07-23)** |
| cars-remns.sh + cars-remediation.service | Dell#1 | ~/ + /etc/systemd/system/ | pending user confirm |
| cars_dashboard.py | Dell#1 | ~/cars_dashboard.py | **badge deployed (==-31045dcf); master edited 07-24 (F1 ROLE sync) — DEPLOY+restart+cache-bust pending** |

## Remediation-feed integration (this session's change)
Goal: show the "block AND maintain" story in one place. Agent writes a live status + event feed to `/tmp`, dashboard
reads them locally (no OT→control-plane break) and shows a **Process-remediation card** + interleaves restores into the
**Decision Log** as purple `RESTORE`/`MAINT` rows.
- **Agent** (`cars_remediation.py`): added `feed()`→`/tmp/cars_remediation.jsonl` (ONLINE, RESTORED) and
  `status()`→`/tmp/cars_remediation_status.json` (live level/last-good/restores). ✅ deployed (full overwrite).
- **Dashboard** (`cars_dashboard.py`): 10 edits — `.rRESTORE`/`.opRESTORE` styles; remed card in sidebar; `RESTORE` in
  RK2 + filter dropdowns; `remediation` added to poll fetch + `rem=res[8]`; **P6 retargeted to deployed** (insert
  card-render + log-injection before `poll()` closes); backend `remediation_feed()` + `/api/remediation` route.
  → apply with **`patch_dash.py`** (E:\...\06_Build\patch_dash.py) — tailored to the DEPLOYED build, compile-guarded,
  abort-safe, idempotent (`if new in s: continue`). **Status: emitted + validated; user to run on Dell#1.**

## To fully reconcile the dashboard master (TODO)
Ingest the deployed file so the master matches reality:
`Dell#1: cat ~/cars_dashboard.py`  → paste back → save as the E:\ master (then re-derive future patches from it).
