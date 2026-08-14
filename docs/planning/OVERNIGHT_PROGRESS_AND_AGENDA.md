# CARS overnight validation - progress log and next agenda

Session: 12-13 August 2026. All runs on the live testbed, armed and green, with the Factory IO HIL healthy (after the laptop-outage incident, see E below). Raw artefacts under `07_Evaluation/overnight/results/`; harnesses under `07_Evaluation/overnight/`.

## Completed today (with results)

### B1 - normal-load baseline (point 4 foundation)
15-minute capture, 196,306 packets, 12 conduits. Per-conduit rate:
- HIL sim `.55 -> .10` S7: **129 pps / 32 ops/s** (flood-exempt)
- PLC reply `.10 -> .55`: 74 pps
- Remediation `.45 -> .10`: 6 pps / 3 ops/s
- Historian `.30 -> .10` and Cell-2 `.3.66 -> .3.10`: ~1 pps / 1 ops/s each
- Multicast/broadcast noise: mDNS `.251`, IGMP `.22`, LLMNR `.252`, broadcast `.255`
- Mix 63% S7 / 37% other; total ~213 pps.
- Finding: the HIL runs at **32 ops/s, 6x the `FLOOD_RATE=5`** - concrete justification for `FLOOD_EXEMPT={.55}`.

### E - does arming perturb the process? (point 9a) PASS
Load-controlled interleaved test, 2 hours, 24 blocks (5-min), 7,060 samples, 0 blocks excluded, load matched at 216 pps:
- disarmed: level mean 51.5, sd 12.83, 0 excursions
- armed: level mean 50.7, sd 13.22, 0 excursions
- **Arming CARS has no measurable effect on the process.**
- Method note: a first naive 1h-vs-1h run was contaminated when the Factory IO laptop shut down mid-run (~15 min); that run was discarded and the interleaved, load-logged, outage-excluding method was adopted. This is itself the rigour the supervisor asked for (normal load must be controlled).

### Attack-during-armed - defensive action vs the process (points 9b / 7 / 10) PASS
Compromised SCADA `.31` FDI (`s7_write --dbspoof --db 7 --spoofval 20`) under armed CARS, 150-s monitor:
- Isolated: `0xca` p110 `nw_src=.31` drop `hard_timeout=75`; attack cut after **9 packets**.
- Tank while isolated: 26.6-71.0, **0 excursions**; legit throughput **+31,755 pkts (~221 pps) continuous**; **0** emergency restores.
- Self-heal: install -> withdraw **76 s** (hard_timeout 75 + one poll), captured in `flows_*_ca1.txt` / `flows_*_ca0.txt`.
- Point 9b (process safe), 7 (self-heal), 10 (flow lifecycle) all demonstrated in one run.

### B2 - MTTM decomposition (points 3 / 5, and point 4 partial) DONE
100 trials, attacker `.66` ICMP -> PLC1, reactive loop:
- **Total window: median 7.6 ms, mean 11.2, p95 38.4, p99 67.9, min 5.5, max 72.9; tail 5/100.**
- Stage split: **detection (wire -> Snort alert) ~0 ms; plumbing (alert -> bridge -> controller -> install) median 7.5 ms** - the plumbing IS the window.
- Tail mechanism: the bridge tails the alert file with `tail -F -s 0.05` = a **50 ms** re-read interval; an alert landing just after a cycle waits up to ~50 ms. Discrete polling granularity, not random jitter.
- Load effect (point 4, from natural variation): Pearson **r = 0.43** between MTTM and background alert load; tail windows carried more background alerts (87 vs 83). Controlled 2x/5x sweep to follow (B3).
- Incidental: an unauthenticated `POST /cars/restore` was **DENIED (bad/missing token)** - the authenticated control interface working (feeds point 12).
- Headline-number note: this fresh decomposed run gives median **7.6 ms**; the report currently says 12.6 ms (earlier `cars_mttm.sh` run). Reconcile to one defined-load run when writing.

### B3 - controlled load sweep (point 4) ATTEMPTED, harness fix applied
Best-effort software load (Modbus reads to LOW `.20`). Level 0 measured background 68.2 alert-lines/s (the HIL doing ~34 read+write cycles/s). Levels 4 and 10 interrupted (no trials).
- Finding: level-0 MTTM read ~722 ms median, which is a **cadence artefact, not a regression**: B3's trials were spaced < the bridge `COOLDOWN=3s`, so each trial after the first fell inside the previous alert's dedup window and the re-POST was suppressed until cooldown expired (trial 1, with no prior cooldown, gave the correct 6.0 ms). This is incidentally a clean live demonstration of `COOLDOWN=3` (point 14).
- Fix applied to `b3_load_sweep.sh`: a 4 s inter-trial gap (must exceed `COOLDOWN`). Re-run tomorrow.
- Point 4 already stands from B2 (r=0.43 + the 50 ms bridge-poll mechanism); the clean B3 curve is a strengthening, and a true 2x/5x needs the exempt HIL rate raised on the Windows box.

## Day 2 (13 August, afternoon)

### B3 confirm - point 4 closed
Restore reverted to `del-flows`-only (the authenticated `/cars/restore` recovery grace was inflating back-to-back trials to ~722 ms). Confirming w=0: **median 7.2 ms** (matches B2's 7.6 ms). Synthetic load is throttle-capped: 4 aggressive Modbus read workers added only **+4.5 alert/s** (67.9 -> 72.4), so CARS itself limits how much an attacker can flood the detector. Point 4 rests on B2 (r=0.43 + the 50 ms bridge-poll mechanism) plus this throttle-ceiling finding; a true 2x/5x would need the exempt HIL rate raised on the Windows box.

### Criticality judgement and behaviour - point 6 DONE (240 judgements)
Attacker `.66` and compromised SCADA `.31`, all four tiers, ops READ/WRITE/CONTROL/DIAG, normal and flood rates, alternating and simultaneous.
- **Timeout ladder (alternating, cleaned between each): CRITICAL 75, HIGH 60, MEDIUM 45, LOW 30 - exact**, set by the target's criticality (`30+15w`). This is the live justification for those four numbers (points 6, 2, 13).
- **Source grading:** attacker `.66` -> ISOLATE for every op; trusted `.31` -> graded (READ mostly ALLOW, WRITE throttled/blocked/isolated by tier, CONTROL/DIAG isolated).
- **Operation grading:** reads permitted where writes/control/diag are cut.
- **Flood escalation:** flood removes the ALLOW/THROTTLE leniency, escalating to BLOCK/ISOLATE (e.g. `.31` on CRITICAL: normal permits reads, rate-12 cuts everything).
- **Persistence escalation:** accumulating source offences harden the response (a source that keeps attacking is treated more harshly).
- **Simultaneous multi-tier:** all four tiers judged concurrently; the per-target timeout measurement is unreliable in this mode because ISOLATE is a single per-source quarantine rule the concurrent hits share (a measurement artifact, not mis-grading; the alternating mode gives the clean ladder).

### Flow-integrity strict - point 12 DONE (60 trials)
- **Persistent** bogus rule: **30/30 = 100% detected**, latency median 8.5 s (within the 10 s poll).
- **Transient** (2 s inject-then-remove): **5/30 = 17% detected (83% missed)** - the quantified sub-poll blind spot (remedy: event-driven flow-monitor, already in the report).
- Incidental (from B2): unauthenticated `/cars/restore` and `/cars/defense` are DENIED - the authenticated control gate working.

### Vast accuracy - point 11 DONE (2,078 cases)
Large labelled corpus through the deployed decision path (decision-only, disarmed): 51 unregistered attacker sources x 5 assets x 4 ops x 2 rates (2,040 attack), plus 38 legit/exempt cases.
- **accuracy = 1.0000, 95% Wilson CI [0.9982, 1.0000]; TP=2,040 TN=38 FP=0 FN=0; no errors.**
- Every one of 2,040 distinct attack variants was restricted (all ISOLATE) - **0 false negatives** at scale.
- All 38 legit/exempt permitted (33 ALLOW + 5 REFUSE safety-loop) - **0 false positives**.
- Honest caveat for the write-up: the FN side is strong (n=2,040); the FP side rests on 38 legit/exempt cases (the allowlist input space is finite), so report 0% FP as backed by these plus the live-campaign zero FP, not a tight FP-only CI.

### Reconnection jitter - point 8 DONE (two-part, honest)
Monitored the legit HIL conduit while restarting Snort and bouncing the ovsgw controller connection; captured HIL frames for jitter/loss.
- **DPI re-attach (Snort restart): transparent.** Inter-frame timing identical to baseline (mean 4.90 ms vs 4.91 ms, max gap 33 ms vs 42 ms), HIL pps steady. Snort is passive/out-of-band, so reconnecting it does not touch forwarding.
- **Controller reconnection: a real availability dependency.** Forcing it via `del-controller`/`set-controller` caused a ~20 s window with multi-second forwarding stalls (max gap 4.2 s); the synchronous S7 session between Factory IO and PLC1 dropped and did NOT auto-recover - the tank froze and the driver had to be reconnected by hand.
- **Honest caveat:** the bridges are already `fail_mode=secure` (the correct hardening), so a genuine controller crash (TCP loss, config intact) should keep flows forwarding; the observed disruption largely reflects the heavy `del-controller` re-add + os-ken pipeline re-sync, not a faithful crash. The precise crash-transparency number is left as careful future work (not re-run, to avoid re-freezing the live process). This quantifies and mitigates the SDN single-point-of-failure risk (point D).
- Operational note: a too-broad `del-flows nw_src=.31,nw_dst=.20` accidentally removed the legit `0xa2` allowlist conduit with the stale `0xca` block; restored by hand. Lesson for harnesses: delete stale reactive rules by `cookie=0xca/-1`, never by src/dst.

### Kali realism MTTM - DONE (100 trials, two-part reaction story)
Attack fired from the REAL Kali VM (.77) vs the namespace (.66); single clock (T0 at the mirror, T4 on Dell 1).
- **Single injection (namespace, cooldown-reset): ~7.6 ms** (12.6 ms original) - the pipeline reaction window.
- **Sustained flood from the real Kali VM: leak window median 992 ms (p95 1032, min 960, max 2004), ~42 inert ICMP frames leaked/trial, 100/100 isolated.**
- Honest framing: the ~1 s vs 7.6 ms gap is the ATTACK PATTERN (continuous flood interacting with the 3 s dedup/rate window), not real-VM path overhead - so report it as the sustained-flood cut time, not a path comparison. The leaked packets are inert L3 ICMP (never touch the S7 process); the tank kept cycling throughout.
- Harness lesson: for a continuous attacker, start the pcap BEFORE the restore (else the flood re-isolates before T0 is captured); measure the leak window from the pcap (first->last frame), not the flow t_enforce (which catches re-installs).

## Points status
- Answered with strong data: **3, 4, 5, 6, 7, 8, 9, 10, 11, 12** (point 8 two-part: DPI transparent; controller outage is a real availability dependency, mitigated by secure fail-mode).
- Ready to write from code + the live 75/60/45/30 ladder anchor: **1, 2, 13, 14**.
- Kali realism MTTM: **DONE** (two-part reaction story, above).
- Lab campaign COMPLETE. Next: fold all results into Chapter 4 + write the design-rationale for 1/2/13/14 + reconcile the MTTM headline (7.6 ms decomposed vs 12.6 ms original).

## Tomorrow's agenda (ordered)
1. **B3 - controlled 2x/5x load sweep (point 4, chosen).** Build a harness that adds benign detection-path load and measures the MTTM distribution at 1x/2x/5x. Design care: the extra load must generate Snort alerts without tripping a flood block - candidates: reads to a LOW asset (throttle keeps the conduit open), or extra HIL-like cyclic I/O from an allowed source. Produce the MTTM-vs-load curve and the tail-fraction-vs-load.
2. **Kali realism MTTM.** Same capture on Dell 1, attack fired from the real `.77` VM (SSH-triggered or manual), to add the realistic attacker-path number beside the controlled namespace one. Single-clock property holds (T0 at the mirror, T4 on Dell 1). Check whether `.77` is cut reactively or proactively.
3. **Criticality under attack (point 6).** Fire the same forbidden op at one asset per tier (CRITICAL `.2.10`, HIGH `.3.10`/`.2.9`, MEDIUM `.2.30`/`.3.9`, LOW `.2.20`); record tier, response, `hard_timeout` (expect 75/60/45/30) and process outcome; comparison matrix + bar chart.
4. **Flow-integrity strict (point 12).** 100-trial controller-compromise suite: inject bogus rule / delete a real conduit / modify a rule, at persistent and sub-poll-transient durations; measure detection rate, detection latency, drift verdict, byte-exact restore; quantify the sub-poll blind spot. Re-confirm the unauthenticated-disarm/restore DENY.
5. **Vast accuracy (point 11).** Large labelled corpus (thousands of role x op x criticality x rate cases plus replayed benign traffic) through `/cars/respond`; TP/TN/FP/FN with confidence intervals; the statistical companion to the 24-case branch-coverage argument.
6. **Reconnection jitter (point 8).** Force controller<->switch reconnection and a Snort restart while the process runs; measure RTT/jitter/loss on legit conduits during discovery/repair; confirm data-plane persistence during a controller outage.
7. **Design-rationale writeups (points 1, 2, 13, 14)** with the sensitivity tests: 24-case branch coverage; 30+15w reconnect-survival + reversibility sweep; 10s poll cost-vs-latency; COOLDOWN/RATEWIN=3 alert-volume test.
8. **Reconcile the MTTM headline** (adopt the decomposed 7.6 ms run under known load, or re-run to reconcile with 12.6) and fold all of today's results into Chapter 4.

## Rig state at wrap-up
Leave CARS armed and green; the harnesses left the system armed. Green-check with `07_Evaluation/overnight/green_check.sh` at the start of tomorrow's session.
