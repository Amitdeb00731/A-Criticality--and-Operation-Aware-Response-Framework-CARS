# Two quick rig checks to settle reviewer points #1 and #3

Run on Dell 1 (CARS armed, green). Both are read-only. Upload the output and the
two caveats in the report can be tightened from "explained/untested" to "measured".

## Check #1 — is the Snort bridge event-driven (inotify), not a 50 ms poll?

This confirms the corrected §4.6 explanation: the 7.6 ms median implies the bridge
picks up each alert as it is written, not on a timed cycle.

```
# the tail child that follows the alert file
TP=$(pgrep -f "tail -F.*alert")
echo "tail pid: $TP"
# does it hold an inotify watch? (a line here = event-driven, not polling)
sudo ls -l /proc/$TP/fd | grep -i inotify
sudo grep -l inotify /proc/$TP/fdinfo/* 2>/dev/null && echo "INOTIFY: event-driven confirmed" || echo "no inotify -> falling back to 50ms poll"
# optional, definitive: watch the syscalls for 3 s while an alert is written
# sudo timeout 3 strace -p $TP -e inotify_add_watch,read 2>&1 | head
```
Expected: an `inotify` fd is present, confirming sub-millisecond pickup (so the tail
is scheduling/HTTP jitter under load, not a 50 ms boundary).

## Check #3 — connection-tracker TCP depth (sequence validation)

Shows whether OVS `ct` validates TCP window/sequence (strict) or only the 5-tuple
state (liberal). Strict = a spoofed out-of-window ACK into an established flow is
marked INVALID.

```
# 0 = strict window/seq tracking (INVALID on out-of-window); 1 = liberal (5-tuple only)
cat /proc/sys/net/netfilter/nf_conntrack_tcp_be_liberal
cat /proc/sys/net/netfilter/nf_conntrack_tcp_loose
```
Expected on a default kernel: `be_liberal = 0` (strict) and `tcp_loose = 1`.

Optional live probe (only if you want the measured result, not the setting): from an
on-segment host, replay a correctly-5-tuple ACK with an out-of-window sequence into an
established HMI->PLC flow and confirm `ct_state=+inv` (dropped) rather than `+est`
(admitted). This is the one case §4.11 currently flags as not specifically tested.

## After running
Paste the outputs; I will fold them into the §4.6 latency note (inotify confirmed)
and the §4.11 conntrack caveat (window-tracking setting, and the seq-probe outcome if
run), replacing "not specifically tested" with the measured behaviour.
