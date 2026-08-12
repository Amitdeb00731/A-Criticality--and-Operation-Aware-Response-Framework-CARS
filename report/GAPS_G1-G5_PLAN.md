# Second gap set (G1-G5): evaluation, treatment, runbooks, writeup plan

Decision (agreed): **frame G1, G3, G4** (verified real, but out-of-scope or risky to fix this late); **test G2 and G5 fresh** in the lab, then write up all five. Governing rules: verify on device (R9), fresh capture before writing (R10), no em/en dashes and British spelling (R2), signpost detail to the appendix (R11), honest bounds and negative results (R7), do not break the established system.

## Per-gap verdict and treatment (all verified on-device)
- **G1 - plaintext OpenFlow (`tcp:10.10.10.1:6653`, no TLS).** Real. Bounded: the control channel is on an isolated wired management plane `10.10.10.0/24` (MikroTik hAP, VLAN 1), which none of the modelled attackers (Kali `.2.77` on OT, the IT attacker north) can reach; MITM needs a management-plane foothold. **Frame** (Threats + Future Work): TLS OpenFlow and its latency overhead are the production remedy and unmeasured. Do not convert (breaking risk; does not change the data-plane claims).
- **G2 - 10 s flow-audit poll.** Real: a sub-10 s inject-exploit-delete evades `cars_flow_audit.py --watch 10`. **Test** (transient vs persistent), then **frame**: any poll has a window; the remedy is event-driven monitoring (OVS `flow-monitor` / OpenFlow multipart), and tightening `--watch` reduces but never removes it.
- **G3 - state exhaustion (conntrack/table flooding).** Real, untested. Partial mitigation exists: GUARD drops spoofed *protected* identities at Table 0 (no conntrack entry), but random non-protected spoofed sources still reach `ct()`. **Frame, do NOT test** - a real state-exhaustion flood could crash the live fabric and the running process (violates don't-break-the-system). Remedies: OVS conntrack limits/zones, meters, SYN protection = future work.
- **G4 - file-based IDS bridge.** Real but narrower than first stated: `snort_bridge.py` uses `tail -F -s 0.05` (50 ms follow, not a whole-file re-parse) with a `COOLDOWN=3 s` per-`(src,dst,op)` dedup, so same-key floods do not multiply POSTs. Under a heavy *multi-key* flood the tail+HTTP path would still queue, and the 12.6 ms median was single-source. **Frame**: production remedy is in-memory IPC (Snort unix-socket output / a socket / Redis). Do not re-architect.
- **G5 - silent drops and DEFLECT.** Silent `actions=drop` is real but bounded: CARS drops only the attacker/quarantined source, never the legitimate loop (0% FP, REFUSE safety cap), so the freeze risk is confined to the compromised host; a TCP RST on quarantine would be a graceful maturity improvement (unevaluated). DEFLECT is shown at the flow level (`tab:crosslayer`) but honeypot **engagement** was not evaluated. **Test** the DEFLECT engagement + the silent-drop contrast; **frame** the RST-on-quarantine and a full deception evaluation as future work.

## Tomorrow, lab: two safe, reversible tests

### Test G2 - transient rule injection evades the 10 s poller (Dell #1)
```bash
echo "baseline: $(cat /tmp/cars_flowaudit_status.json)"
sudo ovs-ofctl -O OpenFlow13 add-flow ovsgw "cookie=0x0,table=1,priority=6,ip,nw_src=198.51.100.66,actions=drop"
sleep 3
sudo ovs-ofctl -O OpenFlow13 --strict del-flows ovsgw "cookie=0x0,table=1,priority=6,ip,nw_src=198.51.100.66"
echo ">>> transient injected+deleted in ~3s; watch 21s (expect ok:1 throughout = MISSED)"
for i in 1 2 3; do sleep 7; echo "t+$((i*7))s: $(cat /tmp/cars_flowaudit_status.json)"; done
# persistent contrast (auditor catches within one poll):
sudo ovs-ofctl -O OpenFlow13 add-flow ovsgw "cookie=0x0,table=1,priority=6,ip,nw_src=198.51.100.66,actions=drop"
for i in 1 2; do sleep 7; echo "t+$((i*7))s: $(cat /tmp/cars_flowaudit_status.json)"; done   # expect ok:0, extra:1
sudo ovs-ofctl -O OpenFlow13 --strict del-flows ovsgw "cookie=0x0,table=1,priority=6,ip,nw_src=198.51.100.66"
sleep 12; echo "restored: $(cat /tmp/cars_flowaudit_status.json)"
```
Expected: transient never flips the auditor (`ok:1` throughout); persistent flips to `ok:0, extra:1` within one poll, then clears. Safe: priority 6, TEST-NET src, cookie 0x0 -> harmless and flagged as extra; reversible.

### Test G5 - DEFLECT engages the honeypot; silent-drop contrast (Dell #1)
```bash
ip netns list | grep -E 'atk|hpot'
sudo ip netns exec atkns ping -c2 -W2 192.168.2.10; echo "(expect 100% loss = silent drop / hang)"
sudo ip netns exec hpotns timeout 25 tcpdump -i any -nn > /tmp/hpot_cap.txt 2>/dev/null &
curl -s -XPOST http://10.10.10.1:8080/cars/respond -H 'Content-Type: application/json' \
  -d '{"src":"192.168.2.66","dst":"192.168.2.10","proto":"IP","dpid":3,"force":"DEFLECT"}'; echo
sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep 'priority=105'
sudo ip netns exec atkns ping -c3 192.168.2.10; echo "(expect replies now = decoy engaged)"
sleep 2; echo "== honeypot saw redirected traffic =="; sudo grep -E '192\.168' /tmp/hpot_cap.txt | head
curl -s -XPOST http://10.10.10.1:8080/cars/restore -H "X-CARS-Token: $(cat ~/cars/api_token)" -d '{"src":"192.168.2.66","dst":"192.168.2.10","dpid":3}' >/dev/null
for sw in ovs1 ovsgw; do sudo ovs-ofctl -O OpenFlow13 del-flows $sw "cookie=0xca/-1,table=1,priority=105" 2>/dev/null; done
echo "deflect cleared: $(sudo ovs-ofctl -O OpenFlow13 dump-flows ovsgw table=1 | grep -c 'priority=105')"
```
Expected: `.66 -> .10` silently dropped (100% loss) until DEFLECT is forced; then the attacker gets replies and the honeypot capture shows `.66 -> .3.99` (engaged). Safe: DEFLECT on the `.66` attacker seam to an isolated decoy; reversible; never touches the legit loop. Green-light after (armed, services active, `0xca`=0, flow-audit ok:1).

## Writeup plan (after the tests)
- **Threats to Validity:** add G1 (plaintext control, bounded by management-plane isolation), G3 (state exhaustion, untested, partial GUARD mitigation, remedies), G4 (file-based bridge latency under heavy load), and the silent-drop/RST part of G5.
- **Chapter 4:** G2 as a flow-integrity negative result (the transient window) beside the flow-tamper/self-check material; G5 DEFLECT engagement folded into the response-ladder / cross-layer DEFLECT row with the honeypot capture.
- **Future Work (Ch5):** TLS OpenFlow + overhead; event-driven flow monitoring; DDoS/state-exhaustion resilience; in-memory IDS IPC; RST-on-quarantine and a full deception evaluation.
- **Appendix:** short listing/note for the transient-injection test and the DEFLECT engagement capture.
