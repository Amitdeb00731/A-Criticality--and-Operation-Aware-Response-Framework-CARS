# CARS — Final 2-Week Roadmap (depth + novelty + parallel framing)

_2026-07-23. Decision: NOT breadth. One deep novel capability + depth on the process + rigorous measurement, with the
write-up framing started NOW in parallel. **Hard feature-freeze ~day 8–9**, then all-in on measurement + the report.
Guiding principle: the dissertation risk is FRAMING/NOVELTY, not features (per GAP_AND_NOVELTY.md). Every technical item
below must feed a specific claim or figure in the report — if it doesn't, cut it._

## The one-sentence contribution we are building toward
"A **safety-capped, criticality-aware, reactive+proactive SDN intrusion-response** system for ICS that, on **real Siemens
hardware**, both **bounds the attacker at the network** (block/isolate/deflect, bounded + reversible, never cutting the
control loop) **and maintains process correctness during the attack** (process-aware last-good/estimated actuation) —
combining network-level response (cf. SDN-IR literature) with process-level maintenance (cf. Cárdenas group), neither of
which alone does both on hardware."

## TRACK 1 — Technical depth (needs the lab)
- **P1 — NOVELTY: process-aware "block AND maintain" response.** On detecting sensor/DB tampering (S7 write to the `Tank`
  DB), CARS not only blocks the malicious source but keeps the loop correct by holding/estimating the value (last-good or a
  1-line model estimate). This is the *new capability* that distinguishes CARS from every reference paper. Deliver a clean
  disarmed-vs-armed contrast on the real process (attack → without: overflow; with: process held correct).
- **P2 — DEPTH: the plant.** Pair TB2 (PLC2 + HMI2) → two-tank process; add HMI1/HMI2 visual (operator screen); run the
  sensor false-data-injection attack (the Cárdenas signature) on real hardware. (Handoff Section D1–D3.)
- **P3 — RIGOR: measurement.** Quantify what exists — MTTM distribution under multi-source load, controller decide+enforce
  latency, zero-collateral proof, a filled **MITRE ATT&CK for ICS coverage table**, controller-DoS fail-secure resilience.
  Plus the CC-68 follow-ups: tune A5 `FLOOD_RATE` for bursty EWS/HMI; optional S7CommPlus download-request DPI rule.

## TRACK 2 — Framing / write-up prep (NO lab needed — start immediately, run in parallel)
- **F1 — Related-work novelty comparison (the #1 write-up gap).** Position CARS against the closest 3–5 systems with a
  capability matrix + a precise delta statement. Start from Etxezarreta (survey) + the 2 Cárdenas papers already mapped;
  add 2–3 more SDN-IR-for-ICS systems. → `RELATED_WORK_and_NOVELTY.md`.
- **F2 — Evaluation-chapter skeleton + figures.** Turn the CC-log + validation results into the results chapter: the
  response-spectrum, MTTM, stress, MITRE-coverage, no-harm, EWS results as tables/figures with captions.
- **F3 — Wording + threat-model precision.** "provably"→"empirically/demonstrably"; state the threat model, the decision-vs-
  enforcement distinction, simulator-vs-real scope, and own G1/G3/G5/G6/S7CommPlus as bounded assumptions.

## Rough schedule (adjust freely)
- **Week 1:** P1 (the novel capability) + P2 (plant/HMI) in the lab; **F1** in parallel (I can draft most of it now).
- **Week 2 (to ~day 8–9):** P3 measurement runs; finish F1; build **F2** skeleton. **Feature-freeze day 8–9.**
- **Remainder:** figures/tables, F3 wording, hand the results chapter into the report draft.

## Explicitly OUT (breadth traps — do NOT add half-baked):
MTD, game-theoretic/ML adaptive response, stateful-P4 data plane, multi-controller HA, formal proof. Name each as
future work; a shallow version becomes an examiner target. Owning G1/G3/G5/G6 is stronger than half-fixing them.
