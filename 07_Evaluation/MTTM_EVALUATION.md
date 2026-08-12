# MTTM Evaluation — Reactive Mitigation Latency (insider path)
_2026-07-13 · 20 trials · single-clock (Dell#1, no cross-machine skew) · att0 (192.168.2.66) -> PLC1 (192.168.2.10), ICMP._

## Method
Each trial: `restore` (clear block) -> T0 = attack start (`ping -i 0.1 -I att0 192.168.2.10`) -> poll `/cars/status` until the conduit block appears -> T_block. **MTTM = T_block - T0**, all timed on Dell#1's clock. 20 trials, ~4 s apart (bridge cooldown = 3 s). CARS's own latency measured inside `respond()` on the controller (`cars_ms`).

## Results (three measurement iterations — a methodology story)
| Iteration | mean | median | std | min | max |
|---|---|---|---|---|---|
| Baseline (bridge `tail -F`, 1 s default poll) | 1.111 s | 1.248 s | 0.478 s | 0.206 s | 2.025 s |
| Bridge poll tightened (`tail -s 0.05`) | 0.933 s | 1.075 s | 0.557 s | **0.048 s** | 1.693 s |
| Final (+ CARS self-timing) | 1.132 s | 1.127 s | 0.673 s | 0.139 s | 2.802 s |

**CARS decide+enforce (controller-side, n=21): mean = 0.613 ms** (range 0.378–0.904 ms).

## Finding
- **CARS's own reactive latency is sub-millisecond (~0.61 ms)** — classify + install the drop on all switches.
- **End-to-end MTTM (~1.13 s) is ~99.95% detector latency:** `0.613 ms / 1132 ms ≈ 0.05%` is CARS. The residual ~1 s variance is **Snort's libpcap read-buffer / alert-flush**, NOT the bridge — proven because tightening the bridge poll dropped the *min* to 48 ms but not the mean (the gate is upstream, in the IDS).
- **Best-case end-to-end = 139 ms**, confirming the loop completes quickly when the sensor buffer aligns.

## Implication (the thesis point)
The reactive SDN response layer imposes **negligible overhead** on mitigation; end-to-end MTTM is **bounded by the IDS**, which is independent of and tunable/replaceable outside the controller. This cleanly separates the *contribution* (a fast, safe, criticality-aware reactive SDN response — sub-ms) from the *sensor* (off-the-shelf Snort).

## Threats to validity / next
- External (VPCS/GNS3) path measured only manually (blocked after ~1 packet); scripted multi-trial run is future work (drive VPCS console via telnet).
- Snort tuning (DAQ/pcap read-timeout, unbuffered alert output) could lower the end-to-end for a "CARS + tuned sensor" figure.
- Raw data: `~/mttm_results.csv` (Dell#1).

---
## Cell-2 MTTM (NAT path) — 2026-07-15, n=20 (identical harness to AG2, target .3.10)
mean **0.707 s** · median 0.715 s · std **0.025 s** · min 0.604 s · max 0.723 s.
CARS decide+enforce (per-decision): **0.38–0.71 ms** (sub-ms, same as Cell-1).

**Findings:**
- **NAT-transparent detection:** Cell-2 is not slower than the Cell-1 insider path (mean 0.707 s vs ~1.13 s) and far tighter (std 0.025 s). Snort detects at the **ovsgw SPAN mirror, upstream of the Dell#3 NAT**, so the transit/translation adds no detection latency — the sensor is correctly placed before the address rewrite.
- **Sensor-bound, not CARS-bound:** the ~0.7 s is the Snort detect→alert→bridge pipeline; CARS's own classify+enforce stays sub-millisecond. Confirms the AG2 conclusion on a second, physically distinct cell.
- **Determinism:** std 0.025 s → highly repeatable reactive behaviour (visible live as the dashboard block-line cycling on all 20 trials).
Raw: ~/cars2_mttm_results.csv (Dell#1) · harness 07_Evaluation/cars2_mttm.py.

---
## Snort DAQ tuning — pcap -> afpacket (2026-07-15, n=20, Cell-2 path, same harness)
| DAQ | mean | median | std | min | max |
|---|---|---|---|---|---|
| pcap (default) | 0.707 s | 0.715 s | 0.025 s | 0.604 s | 0.723 s |
| **afpacket** | **0.026 s** | 0.026 s | **0.000 s** | 0.025 s | 0.027 s |

**~27x faster.** Root cause: the default pcap DAQ batches packets until its read-timeout expires,
holding each sparse ICMP before Snort processes it — this produced the flat ~0.7 s floor. afpacket
delivers packets promptly. CARS decide+enforce unchanged (0.38-0.46 ms). Of the residual 26 ms,
CARS is <0.5 ms and ~20 ms is the harness's own /cars/status poll granularity — so the true
sensor->enforce path is tighter still. Applies to BOTH cells (single sensor).

**PERSIST:** always launch Snort with the afpacket DAQ:
`sudo snort -q -A fast --daq afpacket -c /etc/snort/cars.conf -i snort0 -l /var/log/snort`
(Update COLD_START / RESUME_CELL2 Snort line accordingly.)

---
## Three-vector comparison — all attack paths, afpacket sensor (2026-07-15)
| Attack vector | Src as seen by CARS | Detection point | Mitigation | CARS decide+enforce |
|---|---|---|---|---|
| Insider (on-plane) | 192.168.2.66 -> .2.10 | ovsgw SPAN mirror | ~26 ms (same sensor) | sub-ms |
| Cell-2 (NAT transit) | 192.168.3.66 -> .3.10 | ovsgw SPAN mirror | **0.026 s measured (n=20)** | 0.38-0.46 ms |
| External kill-chain (VPCS) | 192.168.2.1 -> .2.10 (OT-FW SNAT) | ovsgw SPAN mirror | **blocked after 1 packet** (seq1 only) | 0.33-0.84 ms |

**Key result:** all three vectors are detected at the *same* co-located ovsgw mirror, downstream of
the OT-FW where all traffic converges, so the detect->enforce latency is identical (~26 ms, afpacket)
regardless of where the attacker sits. The external path's kill-chain hops add only sub-ms
propagation, not detection delay. CARS decide+enforce stays sub-millisecond across all vectors.
External attacker correctly renders as OT-FW(NAT)->PLC1 on the console (NAT coarseness, per CC-19).

---
## FINAL — insider re-measured on afpacket + sensor now persistent (2026-07-15)
Insider (att0 .2.66 -> .2.10), afpacket, n=20: **mean 0.025 s** · median 0.025 · std 0.000 · min 0.025 · max 0.026. Replaces the old pcap 1.13 s.

**All three vectors, directly measured on afpacket:**
| Vector | MTTM (measured) |
|---|---|
| Insider (on-plane) | **0.025 s** (n=20) |
| Cell-2 (NAT transit) | **0.026 s** (n=20) |
| External kill-chain (VPCS) | blocked after 1 packet (co-located mirror, ~0.026 s) |

Uniform ~25-26 ms across every attacker location => co-located ovsgw-mirror detection is
location-independent; CARS decide+enforce stays sub-ms throughout.

**Sensor persistence:** `cars-snort.service` (afpacket) + `cars-bridge.service` on Dell#1, with
`Conflicts=snort.service` + `disable snort.service` so the distro Snort can never grab snort0 and
silently revert to slow pcap. Combined with `cars-cell2.service` (Dell#3) and the OVS-DB port
persistence, the full data path survives reboot; only the os-ken controller (Dell#2) remains a
manual start.
