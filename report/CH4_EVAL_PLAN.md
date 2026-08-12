# Chapter 4 (Critical Evaluation) — evidence map and writing plan

Governing discipline (unchanged): REPORT_PLAN hard rules 1 to 9. Every number, table cell, curve and claim in this chapter traces to a named artefact captured from the live system. No invented value, no simulated curve, no rounded-up figure. Where the expected value comes from the deployed logic and the measured value from a live interface, both are shown and the source named. If an artefact is missing, we capture it before writing that paragraph (rule 9), we do not estimate.

Headline claim to prove (grounded, from `cars_eval_matrix.csv`): decision accuracy 24/24 on the scored cases, false-positive rate 0/11, false-negative rate 0/13, plus 3 grey criticality-graded cases shown for grading. Corroborated at the wire level by the campaign.

## Section map and the artefact that backs each

4.1 Method and metrics
- Content: the role x operation x criticality space; ground-truth labelling; TN/TP/FP/FN definitions; the disarmed decision pass through `/cars/respond` (pure decisions) plus armed wire corroboration.
- Evidence: `EVALUATION_REPORT.md` (method, verbatim discipline note), harness `06_Build/cars_eval.py`.  STATUS: HAVE.

4.2 Decision accuracy and false positives (Table 4.1 + confusion summary)
- Content: the 27-case matrix; 11 TN, 13 TP, 0 FP, 0 FN, 3 grey; the 0% false-positive claim as the operator-trust result.
- Evidence: `cars_eval_matrix.csv` (27 rows: src,dst,op,rate,label,tier,response,verdict,note); `EVALUATION_REPORT.md`.  STATUS: HAVE.
- Deliverable: Table 4.1 (built from the CSV); a small confusion summary (TN/TP/FP/FN counts). Full 27-row table to the appendix if too long inline.

4.3 Criticality sweep (Table + bar chart of response and block duration)
- Content: same offence swept across CRITICAL/HIGH/MEDIUM/LOW; block/isolate duration 75/60/45/30 s = 30 + 15w; faster escalation at higher weight.
- Evidence: `CRITICALITY_FRAMEWORK.md`; harness `06_Build/cars_criticality_proof.sh`; `/cars/criticality` (already captured, fig:criticality).  STATUS: NEED the sweep RUN output (run `cars_criticality_proof.sh`, capture the per-tier response + measured duration). Do not plot 75/60/45/30 as a bare model curve without the run confirming it.

4.4 Wire-level campaign, armed versus unprotected (7 phases)
- Content per phase: recon; spoofing (ARP/IP/MAC/identity); state manipulation (out-of-state, conntrack); control-plane + flow tamper; op-aware ICS (op class x criticality); process devastation on the live tank; the response ladder (all 7 rungs).
- Evidence: `GRAND_VALIDATION_REPORT.md`, `WIRE_VALIDATION_REPORT.md`, `VALIDATION_DAY2_REPORT.md`, `VALIDATION_DAY_RESULTS.md`; pcaps `armed_plc1.pcap`, `disarmed_plc1.pcap`, `armed_mirror.pcap`, `dpi_mirror.pcap`, `of_control.pcap`, `plc1_wire.pcap`; `scan_ARMED.txt`, `scan_DISARMED.txt`.  STATUS: HAVE.
- Note: response-ladder coverage in the matrix is ALLOW/THROTTLE/ISOLATE/BLOCK/REFUSE; MONITOR and DEFLECT are evidenced by the campaign flow captures (`flows.zip`: MONITOR_*, DEFLECT_* — but those are the STALE July set; recapture MONITOR/DEFLECT flows fresh if we show them).

4.5 Reaction window and latency
- Content: decide-and-enforce time; the flood-versus-isolate reaction-window boundary (the honest latency finding).
- Evidence: decision-time mean from `/cars/status` (cars_ms_avg 0.026, n large) and verified_config (0.024 ms, n=1258); `MTTM_EVALUATION.md` (mean-time-to-mitigate); the reactive-rule install. Per-decision timing: check `cars_decisions_1785588865862.csv` for a ms column before claiming a distribution.  STATUS: HAVE aggregate; CONFIRM per-decision timing source.

4.6 Comparison against the literature
- Content: CARS versus the reactive-SDN and policy-checking alternatives already cited.
- Evidence: existing references (etxezarreta2023survey, gardiner2021controller, melis2018policychecker, samanis2025phd, etc.).  STATUS: HAVE.

Threats to Validity (own section): single testbed; simulated vs physical process; reaction-window latency; the documented boundaries (L2 discovery, safety-invariant loop, compromised endpoint acting in-role, full controller compromise). Evidence: the boundaries already stated in Ch3 threat model + verified_config.  STATUS: HAVE.

Ethics (own section): isolated air-gapped testbed; no production infrastructure; defensive intent; responsible-disclosure posture.  STATUS: HAVE.

## Planned figures/charts and their data source
- Table 4.1 accuracy matrix + confusion summary  <- cars_eval_matrix.csv  (HAVE; Claude builds)
- Criticality sweep table + block-duration bar chart  <- cars_criticality_proof.sh run  (NEED run)
- Attack-chain diagram per phase (draw.io)  <- validation reports  (HAVE; Claude draws)
- Traffic-flow armed vs unprotected (draw.io + annotation)  <- pcaps  (HAVE; Claude draws)
- Before/after tank-level curve  <- per-second DB7 series  (**GAP — capture fresh armed+disarmed, or present devastation qualitatively via the deception evidence; do NOT invent the curve**)
- GUARD anti-spoof bar chart (spoofed sent vs dropped per identity)  <- scan/campaign counts + /cars/guard  (CONFIRM the per-identity counts exist)
- Reaction-window timeline (flood vs isolate)  <- MTTM_EVALUATION.md  (HAVE)
- Whole-campaign summary table  <- GRAND_VALIDATION_REPORT.md  (HAVE)
- Evidence screenshots: tank overflow + HMI empty (deception); dashboard decision log; S7 write frame hex from plc1_wire.pcap (Wireshark)  <- pcaps + Amit screenshots  (HAVE pcaps; the overflow/HMI photo may need one screenshot)

## To capture or confirm tomorrow at the rig (before writing the dependent paragraph)
1. Criticality sweep run: `bash 06_Build/cars_criticality_proof.sh` (or the deployed path) -> per-tier response + measured block duration. Backs 4.3.
2. Per-second tank-level series, armed and disarmed, saved to file -> the before/after curve (4.4 process devastation). Decide now if in scope; if not, present devastation via the deception screenshot + MTTM, and state the curve is out of scope.
3. Item 15 (from LAB_VERIFY): one live reactive rule showing cookie 0x00ca + criticality-scaled timeout. Backs 3.6 and 4.4 enforcement.
4. Confirm per-decision timing column in `cars_decisions_*.csv` (for 4.5); if absent, report the aggregate mean only.
5. If MONITOR/DEFLECT flows are shown in 4.4, recapture them fresh (the July `flows.zip` set is stale).

## Order of writing (evidence-first, each paragraph after its artefact is in hand)
4.1 method -> 4.2 matrix (build Table 4.1 from CSV first) -> 4.3 criticality sweep (after the run) -> 4.4 campaign phase by phase (from the reports + pcaps) -> 4.5 latency/reaction window -> 4.6 comparison -> Threats to Validity -> Ethics. Compliance check after each section (em/en dashes, tell-words, British spelling, refs, word count), same as Chapter 3.
