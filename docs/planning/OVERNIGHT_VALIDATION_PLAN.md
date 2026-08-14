# CARS overnight validation plan — answering the supervisor's 14 points

Purpose: turn each of the supervisor's fourteen points into (a) a defensible design rationale grounded in the deployed code, and (b) a concrete experiment to run on the live testbed overnight (12–14 h) that captures the data to justify every number. Each item ends with what it changes in the dissertation.

Ground truth (read from `06_Build/`): `BLOCK_TIMEOUT = 30`; reactive `hard_timeout = 30 + 15*w` with weights CRITICAL/HIGH/MEDIUM/LOW = 3/2/1/0 (so 75/60/45/30 s); `FLOOD_RATE = 5.0` ops/s; `FLOOD_EXEMPT = {192.168.2.55}`; `ESCALATE = 3`, `esc = max(1, ESCALATE - dcw)`; reactive cookie `0x00ca`, allowlist cookie `0x00a2`; bridge `COOLDOWN = 3`, `RATEWIN = 3.0`, `tail -F -s 0.05`; flow-audit `--watch 10`.

All runs write to a timestamped results directory `~/overnight_YYYYMMDD/` on Dell 1, and each battery is reversible and returns the rig to green (`armstate` ARMED, services active, `flow-audit ok:1`, `0xca` 0) before the next.

---

## Two design principles the supervisor is really probing

The numbers are not tuned to flatter the result; they follow two rules that must be stated in the report:

1. **Bounded and reversible.** Every reactive action self-expires, so a wrong decision costs a known, small amount of time, never a permanent cut. This is why timeouts are seconds, not minutes, and why they self-heal.
2. **Criticality-proportional.** The higher the consequence of the protected asset, the sooner CARS escalates and the longer it holds, because the cost of a missed attack rises with criticality while the cost of a brief over-block does not.

Every number below is a point on one of those two axes, and the overnight tests measure the physical and network behaviour that sets where the knee should sit.

---

## Battery A — Justifying the numbers (points 1, 2, 13, 14)

### A1. Why 24 scored cases, not 25 or 26 (point 1)
**Rationale.** The case set is not a sample of size 24; it is the *closure* of the decision space over the branches the engine can take. The decision path is `classify(role, op) -> tier`, then criticality elevation (`SENSITIVE -> FORBIDDEN` on a CRITICAL asset), then `select_response(tier, rate, dcw)`. The scored set enumerates one case per meaningful branch across four bands: legit-benign (the false-positive test, one per permitted conduit), attack (one per forbidden role/op/target combination, the true-positive test), and flood (the volumetric overlay). Grey cases sit outside the binary score because they test grading, not a legitimate-or-attack decision. So 24 is "every branch exercised once", and adding a 25th identical-branch case would add no coverage.
**Experiment.** Emit the branch-coverage table: for each scored case, record which `classify`/elevation/`select_response` branch it exercises, and show the 24 cover the reachable branches with none duplicated and none missing. Script: extend `cars_eval.py` to print the branch id per case.
**Report change:** replace "twenty-four scored cases" with a one-paragraph coverage argument and a small branch-coverage table; cross-reference the vast test (A/G below) for statistical accuracy.

### A2. Why the reactive timeout is 30 + 15w (75/60/45/30 s) (points 2, 13-quarantine)
**Rationale.** Base 30 s is chosen to outlast an automated reconnect/re-attack train: a default TCP SYN retransmit sequence (roughly 1+2+4+8+16 s) spans about 31 s, so a 30 s quarantine survives a full reconnect attempt rather than releasing the attacker mid-retry. It is also short enough that a mis-fire on a legitimate source self-heals in well under a minute (reversibility). The `+15w` term makes the hold criticality-proportional: each weight step adds 15 s, giving the clean 30/45/60/75 ladder (base to 2.5× base) across the four tiers, so a CRITICAL asset holds an attacker 2.5× longer than a LOW test asset.
**Experiment (overnight).** (i) *Reconnect-survival:* from the attacker, run an automated S7 reconnect loop against an isolated conduit; log the SYN-retry timestamps and confirm the 30 s base outlasts the retry train, and that the block renews if the attack is still live at expiry. (ii) *Reversibility:* isolate a legitimate source by a forced mis-fire, measure exact time-to-recovery, confirm it equals the tier timeout and the conduit returns to ALLOW with no manual step. (iii) *Sensitivity sweep:* temporarily set the base to 20 and 45 s and repeat (i) to show 30 sits above the reconnect train (20 releases mid-retry; 45 adds no benefit). Capture per-tier the installed `hard_timeout` from `dump-flows` and the observed self-heal time.
**Report change:** a "why these durations" subsection in the design chapter, with the reconnect-train figure and the per-tier self-heal measurements.

### A3. Why the flow-integrity poll is 10 s (point 13)
**Rationale.** The poll is a trade-off between drift-detection latency and the cost of dumping every switch's tables. Ten seconds bounds the worst-case time to catch a *persistent* injection at one poll, while `dump-flows` on three small bridges every 10 s is negligible load. A shorter poll narrows the window but never closes it (a sub-poll transient still slips, as already shown), so 10 s is the knee, not a floor.
**Experiment (overnight).** Measure the `dump-flows` cost (CPU time and duration) at poll intervals 2/5/10/30 s over an hour each; plot cost vs interval and mark 10 s. Re-run the transient-vs-persistent injection at each interval to show the detection-latency/overhead trade-off. (Already have the 2 s-transient-missed / persistent-caught result; this generalises it.)
**Report change:** justify 10 s with the cost-vs-latency curve; fold into the deployment-limits paragraph and the flow-integrity design.

### A4. Why COOLDOWN = 3 s and RATEWIN = 3 s (point 14)
**Rationale.** `COOLDOWN` de-duplicates: at most one POST per `(src,dst,op)` per 3 s, so a sustained attack cannot storm the controller with thousands of identical events (which would itself widen the reaction window — the very bottleneck noted as future work). `RATEWIN` estimates ops/s over the same 3 s so the `FLOOD_RATE = 5` test is taken over a stable window rather than an instantaneous burst. Three seconds smooths burstiness and dedups while staying short enough to re-POST and renew the block if the attack persists past self-heal.
**Experiment (overnight).** Under a sustained 50 ops/s attack, count controller POSTs and decision-log events with `COOLDOWN` at 0/1/3/5 s over ten minutes each; show the alert volume (and controller CPU) collapse at 3 s while the response still fires within one window and renews on persistence. Confirm the estimated ops/s tracks the true send rate across `RATEWIN` values.
**Report change:** a short justification of the bridge constants, tied to the controller-bottleneck limitation.

---

## Battery B — Normal traffic baseline and MTTM under load (points 3, 4, 5)

This is the heart of the supervisor's concern: the MTTM was measured, but the *background it was measured against* was never characterised, and the distribution was never explained.

### B1. Characterise the normal OT traffic (point 4)
Run the testbed in its normal armed steady state (no attack) for a long window (2–4 h overnight) and capture, per conduit: packets/s and ops/s, the cyclic HMI/PLC control-loop rate, the historian poll rate, and the Factory IO HIL exchange rate (the `.55` exempt high-rate flow). Artefacts: per-conduit rate time series (`tcpdump` counters + the bridge's own ops/s log), a summary table of baseline load, and a traffic-mix pie. This is the "normal load" the report currently lacks.

### B2. Decompose the reaction window (point 3)
Explain the *shape* of Figure 4.9 by breaking the 12.6 ms into its fixed stages with timestamps on one clock: mirror-to-Snort, Snort detect, bridge read+POST, engine decide, `flow_mod` install-to-first-drop. Instrument each stage (the engine already logs `cars_ms`; add a timestamp at Snort alert write and at bridge POST). Over 200+ trials, show the distribution is *clustered* because it is the sum of near-constant software stages, and the tail appears only when detection lands on a poll/cooldown boundary. This is why it is not a broad continuous 5–50 ms spread: it is a tight mode plus a boundary-driven tail, not random network jitter.

### B3. MTTM as a function of background load (points 3, 4)
Re-run the MTTM harness (100 trials) at three background levels: baseline (B1), 2×, and 5× normal load (extra historian polls and benign reads, never touching the attacker conduit). Plot the MTTM distribution per load level. Expected and to be shown with data: the median barely moves while the upper percentiles and the boundary tail grow with load, because the fixed pipeline dominates until queueing at the file-tail/HTTP bridge starts to bite. This directly answers "how is MTTM affected by normal traffic load" with measured curves, and grounds the controller-bottleneck limitation in data rather than assertion.

### B4. Separate trial traffic from regular traffic (point 5)
Make the methodology explicit and measured: the trial (attack) traffic is a distinct, labelled conduit from a dedicated attacker identity, fired in single, timed shots; the regular traffic is the characterised B1 background. Capture both at the three wire points during a trial so the report can show, side by side, the steady background and the single attack frame whose mitigation is being timed. This removes the ambiguity the supervisor flagged: the MTTM is the time from the *trial* frame to its enforcement, measured against, and not contaminated by, the *regular* load.

**Report change:** a new evaluation subsection "Normal load and how it shapes the reaction window", with the baseline traffic table, the stage-decomposition of the window, the MTTM-vs-load curves, and an explicit trial-vs-background methodology note. Figure 4.9 gets a companion figure and an honest explanation of its shape.

---

## Battery C — Criticality under attack, across all levels (point 6)
Fire the *same* attack (an S7 CONTROL write, then a flood) from the same attacker against one asset of each criticality: CRITICAL (PLC1 .2.10), HIGH (PLC2 .3.10 or HMI1 .2.9), MEDIUM (historian/HMI2), LOW (Modbus sim .2.20). For each, capture the tier, the selected response, the installed timeout, the MTTM, and the physical/network outcome. Produce a single comparison matrix and a bar chart of response severity and hold-time versus criticality, showing the ladder escalating sooner and holding longer as consequence rises (`esc = max(1, 3-dcw)` and `30+15w`). Repeat each 10× for stable numbers.
**Report change:** upgrade the criticality-sweep section from a decision-only table to an *under-attack* comparison with measured response, hold-time and process outcome per tier.

---

## Battery D — Return to normal after mitigation (point 7)
For each response type (THROTTLE, BLOCK, ISOLATE, DEFLECT) run attack → mitigation → recovery and capture the full return path with timestamps: the reactive `0xca` rule appearing, its `duration`/`hard_timeout` counting down, the rule self-expiring, `flow-audit` returning `ok:1` without re-baselining, the remediation agent restoring the last-good process value, and the conduit returning to ALLOW. Record the total time-to-normal per response and per criticality, over 10 cycles each. Show that recovery is automatic and byte-exact (no operator action, no residual rule).
**Report change:** a "recovery and self-healing" subsection with a timeline figure (attack → isolate → expiry → green) and the measured time-to-normal table.

---

## Battery E — Risk of CARS on the process (point 9, VITAL; overlaps 8)
The central OT question: does arming CARS ever harm the very process it protects? Run a long (8–12 h overnight) armed-versus-disarmed comparison with the process cycling normally and no attack, and measure whether enforcement or the control-plane machinery perturbs legitimate operation:
- Per-second tank-level series armed vs disarmed: is the control band held identically (no added oscillation)?
- Legitimate-conduit added latency: round-trip time on the HMI↔PLC and historian↔PLC conduits, armed vs disarmed, distribution not just mean.
- Legitimate packet loss under enforcement: count any legit packet dropped while reactive rules are active elsewhere (must be zero — the false-positive-on-the-wire test at scale).
- Switch/controller overhead: CPU and forwarding latency added by the three-table pipeline versus a plain L2 switch.
This is the evidence that the defence is safe to arm on a live process, which is the whole thesis. Capture everything to per-second logs.
**Report change:** a dedicated "Does the defence disturb the process?" evaluation, the strongest possible support for the deployability claim, with armed-vs-disarmed process and latency distributions.

---

## Battery F — Flow install / modify / withdraw lifecycle, fully recorded (point 10)
Continuously record the data-plane rule lifecycle across a scripted sequence that triggers each response and each self-heal. Capture: a periodic `ovs-ofctl dump-flows` snapshot series (0.5 s cadence) around each event, and, where available, an OpenFlow flow-monitor subscription; for every reactive rule, log the install timestamp, cookie, table, priority, match (`nw_src`/conduit), actions, and `hard_timeout`, then the modify (renew) and the withdraw (expiry or explicit delete). Produce a per-event ledger: rule installed at T, matched N packets, withdrawn at T+timeout. Include the `OFPT_FLOW_MOD` decode (already have one) for a representative install.
**Report change:** an appendix "flow lifecycle ledger" plus a body figure of one full install-to-withdraw timeline; substantiates "installs, modifies and withdraws flows" with recorded evidence.

---

## Battery G — Vast detection-accuracy test (point 11)
Move accuracy from coverage-complete (the 24) to statistically strong. Generate a large labelled corpus by sweeping role × operation × target-criticality × rate and adding realistic noise and replayed benign traffic (target several thousand cases), drive each through the deployed `/cars/respond` path, score TP/TN/FP/FN, and report accuracy and the false-positive rate with confidence intervals. Include adversarial-but-legit edge cases (maintenance-window writes, exempt high-rate I/O) to stress the false-positive boundary. Run over several hours.
**Report change:** report both results honestly: the 24-case branch-coverage result and the large-N statistical result, so the headline accuracy is backed by scale, not just enumeration.

---

## Battery H — Controller compromise and strict flow-integrity evaluation (point 12)
An adversarial suite against the control plane, run many times for statistics: (i) inject a bogus rule; (ii) delete a real allowlist conduit; (iii) modify an existing rule's action; each at persistent and sub-poll-transient durations, and at several rates. For each trial record: detection (caught within one poll or missed), the drift verdict (`missing`/`extra`/`changed` counts), the time-to-detect, and whether the restore is byte-exact. Also exercise the authenticated-disarm path (unauthenticated `POST /cars/defense` must stay refused). Aggregate detection rate and detection latency over, say, 100 trials, and characterise the residual (sub-poll transient) quantitatively.
**Report change:** upgrade the control-plane-compromise result from a single demonstration to a measured detection-rate and detection-latency evaluation, with the transient blind spot quantified.

---

## Battery I — Discovery / reconnection jitter on normal traffic (point 8)
Because CARS passes normal traffic, test whether the control-plane machinery adds noise to it: force controller↔switch reconnections and a Snort restart while the legitimate process runs, and measure jitter and loss on the live control-loop and historian conduits during discovery and repair. Capture the RTT time series across the reconnection events; quantify any added jitter and whether any legitimate packet is lost when the controller re-discovers topology or Snort re-attaches. Confirm the installed proactive rules keep forwarding during a controller outage (data-plane persistence), and measure the transient at reattach.
**Report change:** a paragraph (and RTT-during-reconnect figure) in the deployment-limits / process-risk section quantifying the reconnection jitter, tied to point 9.

---

## Suggested overnight running order (12–14 h)
1. B1 baseline traffic characterisation (2 h, unattended) — needed by B3/E.
2. E process-risk armed-vs-disarmed (runs in parallel with B1 as the same steady-state capture, extended to 8–12 h with periodic scripted attacks interleaved).
3. B2/B3 MTTM decomposition and MTTM-vs-load (1–2 h).
4. C criticality-under-attack sweep (1 h).
5. F flow-lifecycle capture (folded into C and H events).
6. D recovery cycles (1 h).
7. H flow-integrity adversarial suite, 100 trials (1–2 h).
8. G vast accuracy corpus (2–3 h, unattended).
9. A2/A3/A4 sensitivity sweeps (1 h).
Return to green after each; keep every raw capture under `~/overnight_YYYYMMDD/<battery>/`.

## What I need to build next
Per battery: a small capture harness plus an orchestrator that sequences them, timestamps everything, and returns the rig to green between runs. I will build these as reviewed, reversible scripts (read-mostly; the only writes are the existing attack tools and temporary policy toggles), and we run them interactively the way we have been, capturing outputs as we go.
