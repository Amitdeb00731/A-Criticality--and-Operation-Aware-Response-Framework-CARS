# Test and evaluation harness inventory (recalled from 06_Build source, 4 Aug 2026)

Grounded recall of every test/eval script and how each is run, read from `06_Build/` source (not memory), so Chapter 4 reruns exactly what we ran before (hard rules 9, 10).

Common facts (from the script headers):
- All harnesses run on **Dell 1** (has OVS for heal, the token, and control-plane reach).
- Controller API: `http://10.10.10.1:8080` (Dell 2 over the 10.10.10.x control net). Token: `~/cars/api_token` (= `/home/msclab/cars/api_token`).
- The scripts live in the repo `06_Build/`. They are NOT currently on the Dells; deploy the one we need to Dell 1 (e.g. `~/` or `~/cars/`) before running. The engine (`cars_engine.py`) runs on Dell 2.
- Several attack clients expect deployed paths: `/home/msclab/s7_write.py`, `/home/msclab/cars_evidence_logger.py`.

## 4.2 Accuracy / decision matrix
- **cars_eval.py** — 27 labelled cases via `/cars/respond` (the deployed decision path: classify -> criticality elevation -> select_response). Disarms via `/cars/defense {on:false}` for a decision-only pass, scores TN/TP/FP/FN, re-arms. Prints a TALLY + Accuracy/FP-rate/FN-rate; writes **`/tmp/cars_eval_matrix.csv`**. Run: `python3 cars_eval.py` on Dell 1. (Grey rows shown, not scored.)

## 4.3 Criticality-graded response
- **cars_criticality_proof.sh** — fires controlled scenarios via `/cars/respond` and tabulates `{tier, crit-tier, elevated, action(+timeout)}`. Decision-side DISARMED (pure decision); response-proportionality ARMED from the harmless attacker `.2.66`, healed after each. Run: `sudo bash cars_criticality_proof.sh` on Dell 1.

## 4.4 Wire-level campaign, armed vs unprotected
- **cars_campaign_lib.sh** — shared capture library sourced by phase scripts: `arm/disarm`, `snap` (cross-layer state), `flowdump` (audit every flow), `capstart/capstop` (3-point pcaps). Output under `/tmp/grand_campaign`.
- **cars_wire_campaign.sh** — ARMED wire/packet campaign: attacks control-plane, flows, conntrack state and the process; captures pcaps at 3 wire points + timestamp-aligned state from every layer (audit, flows, conntrack, guard, flow-audit, remediation/PLC). Reversible + process-safe. Output `/tmp/campaign`.
- **cars_wire_campaign_disarmed.sh** — the DISARMED control (baseline): disarms enforcement + stops remediation, reruns the vectors (V4 sustained to show persistence), then re-arms + restarts remediation to prove recovery. Usage: `sudo bash cars_wire_campaign_disarmed.sh <TOKEN>`.
- **cars_e2e.sh** — deep end-to-end: drives the full response spectrum through the real autonomous chain, four independent proof layers per scenario (WIRE via tshark, SNORT alert delta, CARS audit decision, OVS flow n_packets moved) + OUTCOME.
- **cars_packet_proof.sh** — wire-level op-awareness: two synchronised captures, MIRROR (`snort0`, what DPI sees) and PLC1 port (`enx9c69d331d874`, what reaches PLC1); READ(allow)+WRITE(control) ARMED then WRITE DISARMED; pcaps for Wireshark.
- **cars_ics_attack.sh** — operation-awareness trial: I1 discrimination (identical 5-tuple `.31->.20:502`, READ allowed vs WRITE throttled), I2 write-escalation (SENSITIVE throttle -> BLOCK), I3 ICS-MTTM.
- **cars_ics_battery.sh** — full ICS op spectrum from the same operator `.31` at Modbus `.20`: READ->ALLOW, WRITE->throttle, CONTROL/DIAG/PROGRAM/ILLEGAL->BLOCK; conduit restored between ops.
- **cars_stateful_test.sh** — isolated conntrack proof on a throwaway bridge + netns (`10.9.9.0/24`, no live PLCs): allowlisted client incl. return traffic passes (ct +est), attacker +new to a protected dst dropped.
- **cars_validate_all.sh** — consolidated both-cells end-to-end (general A2/DEFLECT/GUARD/self-heal + ICS Modbus 5 classes + S7 both PLCs + agendas + hot-reload/maintenance/arm-disarm), one PASS/FAIL.
- **kali_evil.sh** — DISARMED worst-case devastation battery on the live tank (sensor chaos via `s7_write.py --dbspoof --db 7 --offset 0`, etc.); runtime carnage only, never touches program/firmware.
- **cars_s7_demo.sh** — physical relay attack demo (Q0.3): disarmed the relay clicks, armed it is silent; same attacker/PLC/op, only variable is armed.
- **cars_rate_demo.sh** — rate/flood: ACT1 normal ALLOW, ACT2 read-flood THROTTLE->BLOCK, ACT3 write-flood ISOLATE.
- **cars_showcase.sh / cars_showcase_plc2.sh** — live showcase runs (ACT1-4), PLC1 and PLC2.

## 4.5 Reaction window / latency
- **cars_mttm.sh** — MTTM = `t_enforce - t_attack` on Dell 1's single clock: `t_attack` = first attacker frame in the mirror pcap (tshark, us), `t_enforce` = poll_time - flow.duration (flow age = install time, skew-free). ICMP flood = harmless L3 floor. Run: `sudo bash cars_mttm.sh [N]`.
- **07_Evaluation/cars2_mttm.py** — MTTM (to review before use).
- ICS-layer MTTM via `cars_ics_attack.sh` I3.

## Process evidence / the tank-level curve (4.4 devastation)
- **cars_evidence_logger.py** — RAW per-second logger: samples tank Level (`DB7.0` Real) + relay `Q0.3` + agent restores, timestamped to CSV, reads the PLC directly (independent of the remediation agent, so it works agent-off). Run: `sudo ip netns exec opns /usr/bin/python3 /home/msclab/cars_evidence_logger.py <tag> <secs>` -> `/tmp/cars_evidence_<tag>.csv`. **Use this for the armed/disarmed before-after curve** (not a hand-rolled reader).

## Attack clients
- **s7_write.py** — S7comm output-write attack (PA area, Q0.0..Q0.7): `--flap` toggles the relay (audible); `--dbspoof --db 7 --offset 0 --spoofval N --secs S --hz H` spoofs the sensor value. Leaves outputs OFF on exit.
- **mb_attack.py** — raw Modbus/TCP function-code attack (coil/write/illegal), proto-id at byte 2, FC at byte 7 (what the Snort DPI anchors on).
- **s7_probe.py, mb_client.py, mb_server.py** — supporting probe/clients.

## Dashboard (appendix, extra work)
- **cars_dashboard.py** — the CARS intelligence dashboard (document in Appendix; capture live screenshots).

## Supporting / forensics (review only if a section needs them)
cars_a2_forensics.sh, cars_a3_forensics.sh, cars_a3_validate.sh, cars_crosscheck.sh, cars_deploy_verify.sh, cars_forensics.sh, cars_dos_flicker.sh, cars_flowaudit_test.sh, cars_flowaudit_robust_test.sh, cars_stress.sh, cars_verifyC.sh, cars_process.py, l2_switch.py, patch_agent.py, patch_critbadge.py, patch_dash.py.

## Reports these produced (already on disk, for reconciliation only, not substitution)
EVALUATION_REPORT.md, GRAND_VALIDATION_REPORT.md, WIRE_VALIDATION_REPORT.md, VALIDATION_DAY2_REPORT.md, VALIDATION_DAY_RESULTS.md, 07_Evaluation/MTTM_EVALUATION.md, 07_Evaluation/DEMO_RESULTS.md, 07_Evaluation/RESPONSE_SPECTRUM.md, CRITICALITY_FRAMEWORK.md, and the CSVs cars_eval_matrix.csv / cars_deception_decisionlog.csv.
