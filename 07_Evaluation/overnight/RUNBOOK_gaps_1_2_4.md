# Runbook — closing Gaps 1, 2, 4 on the live testbed

Off-rig work is done and validated (this sandbox can't reach the Dell/PLC/Factory
IO rig). Each item below is ready to run on Dell 1 with CARS armed and green;
each returns the rig to green. Upload the named result files and I fold them into
Chapter 4.

Green-check first: `07_Evaluation/overnight/green_check.sh`.

---

## Gap 1 — reaction window under alert load  (partly done off-rig)

**Done (off-rig, faithful to the deployed engine):** the controller decision +
audit-log stage was benchmarked against the *real* extracted `classify` /
`select_response` code (fidelity 9/9 vs the report matrix).
`gap1_alert_stress/RESULT.txt`:
- decision compute: median **4.3 us**, p99 **11 us** (~200k/s compute ceiling);
- decision + audit write: **~16-18k alerts/s** sustained, single core;
- identical-alert floods are capped by `COOLDOWN=3s` dedup to <=1 POST/key/3s;
- diverse floods: added queue wait ~0 ms at 1k/s, ~0.08 ms at 10k/s, knee ~16k/s,
  unstable >~18k/s.

**To close on the rig (end-to-end curve):**
```
cd 07_Evaluation/overnight/gap1_alert_stress && bash live_flood.sh
```
Produces `results/gap1_live/curve.csv` (probe MTTM vs background alerts/s on real
hardware). Upload it. Expected: MTTM flat through 1k-10k/s, rising only as the
single-threaded controller nears saturation — the live confirmation of the bench.

---

## Gap 2 — conduit BLOCK instead of source ISOLATE at a NAT identity

**Patch (validated off-rig):** `gap2_nat_block/PATCH_select_response.md`. Off-rig
check confirmed Pivot A (gateway `.1`) -> **BLOCK conduit**, Pivot B (`.77`) ->
**ISOLATE source** (unchanged).

**To close on the rig:**
1. Apply the two edits in `PATCH_select_response.md` to `06_Build/cars_engine.py`;
   restart the controller; green-check.
2. Re-fire Pivot A (IT attacker, NATed to `.1`) at the CRITICAL PLC, and confirm:
   - audit reads `... => BLOCK conduit` (not `ISOLATE source`);
   - `dump-flows ovsgw` shows `cookie=0xca ... nw_src=192.168.2.1,nw_dst=192.168.2.10 actions=drop` (conduit, not bare `nw_src`);
   - a concurrent legit gateway flow to a *non-PLC* host still passes (the DoS is gone);
   - the attacker still lands **zero** writes on the PLC.
3. Re-fire Pivot B and confirm it is still source-ISOLATEd.
Capture the two audit slices + the two `dump-flows` to `results/gap2_nat_block/`.

---

## Gap 4 — event-driven flow-integrity monitor (closes the 10 s blind spot)

**Module:** `gap4_flowmonitor/cars_flowmonitor.py` — subscribes to OVS's Nicira
flow-monitor (`ovs-ofctl monitor <br> watch:`), so any injected/modified rule is
checked against the trusted baseline the instant it is installed and posted to the
existing `/cars/flowaudit` drift feed. Works on the deployed OF1.3 + OVS stack
(no OF1.4 bump). The 10 s poller stays as a slow backstop.

**To close on the rig:**
1. Capture the trusted baseline (allowlist `0xa2` rules) to
   `/home/msclab/cars/flow_baseline.json` while green.
2. Start the monitor:
   ```
   sudo python3 gap4_flowmonitor/cars_flowmonitor.py --bridges ovs1,ovsgw \
        --baseline /home/msclab/cars/flow_baseline.json \
        --api http://127.0.0.1:8080/cars/flowaudit
   ```
3. Re-run the **same** transient test as `results/flowint/transient.csv` (2 s
   inject-then-delete a bogus rule), 30 trials, but now record the monitor's
   detection latency per trial. Expected: detection on **30/30** within
   milliseconds (vs 5/30 for the 10 s poll), with the drift line in the decision
   log carrying `event-driven`.
4. Repeat the persistent case (should also be instant).
Capture to `results/gap4_flowmonitor/transient_eventdriven.csv` + a decision-log
slice.

---

### After the runs
Upload: `gap1_live/curve.csv`, `gap2_nat_block/` (audits+flows),
`gap4_flowmonitor/transient_eventdriven.csv`. I then update §4.6 (load curve),
§4.7 (NAT BLOCK), §4.10 + Appendix Gap C/D (event-driven flow-integrity), and the
future-work/conclusion accordingly.
