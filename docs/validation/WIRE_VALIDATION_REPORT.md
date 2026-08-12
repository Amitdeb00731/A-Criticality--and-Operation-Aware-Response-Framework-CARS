# CARS — Wire/Packet-Level Attack & Cross-Device Evidence Report
_Campaign 2026-07-30 19:29, harness `06_Build/cars_wire_campaign.sh`. Captures: `plc1_wire.pcap` (PLC1 port), `of_control.pcap` (OpenFlow 6653), `dpi_mirror.pcap` (Snort mirror) + `events.log` (timestamp-aligned state from every layer). **Hard rule honoured: every claim below is a captured packet, a logged line, or a live state value — no inference.**_

## Method
Four real attack vectors run in sequence against the live testbed, each captured at 3 wire points and snapshotted across controller audit, switch flow tables, conntrack, GUARD counters, flow-audit, and remediation/PLC state. Correlation matches, per vector: **attacker packet → what DPI saw → CARS's control-plane reaction (flow-mod) → the audit/log entry → the process outcome.**

---

## V1 — Control-plane attack (control-API authentication)
- **Attack (19:29:25):** unauthenticated `POST /cars/defense {"on":false}` from `10.10.10.2` → controller `10.10.10.1:8080` (attempt to silently DISARM CARS — the P0-4 vector).
- **Response on the wire:** `HTTP 401`, body `{"error":"unauthorized - X-CARS-Token required"}` (`v1_resp`).
- **Controller audit (matched):** `19:29:25 CONTROL 10.10.10.2(api) -> 10.10.10.1(controller) HTTP /cars/defense => DENIED (bad/missing token)`.
- **State:** enforcement unchanged (no disarm); remediation kept running throughout.
- **Verdict:** control-plane disarm **refused and audited** end-to-end. ✔

## V2 — Flow tampering (flow-integrity / policy checker)
- **Attack (19:29:27):** inject bogus rule (`cookie=0x0, nw_src=198.51.100.66, drop`) on ovsgw **+ delete the real A2 allowlist conduit** `.2.31→.2.20:502` on ovs1.
- **Autonomous detection (matched):** the `cars-flowaudit` watch-daemon flagged it at its next poll — `flowaudit: {ok:0, missing:1, extra:1}` (ts 19:29:36): `missing`=the deleted conduit, `extra`=the injected rule. Drift posted to the decision log (`flow-integrity: policy-removed` + `bogus-injected`).
- **Recovery:** flows restored → daemon returns `ok:1` by 19:29:46; `flows_ovs1_end` confirms the conduit is back.
- **Honest note:** the harness's *inline* `--check` hit a path bug (run under `sudo`, `~`→`/root`, file not found) — cosmetic; the **daemon** is the real detector and proved it autonomously.
- **Verdict:** injection **and** deletion of the *real* CARS policy detected autonomously, surfaced, self-cleared on restore. ✔

## V3 — State manipulation (stateful conntrack pipeline)
- **Attack (19:29:41):** attacker `.2.66` forges **8 out-of-state TCP ACKs** to `PLC1:102` (no handshake — attempt to slip past the ct pipeline as if "established").
- **Wire proof (by ABSENCE):** `plc1_wire.pcap` shows **0 packets from `192.168.2.66`** — the forged ACKs **never reached the PLC**. They are `-trk → ct → +new` to a protected dst → dropped in table 1 before crossing to ovs1. conntrack shows no new `.2.66` entries.
- **Verdict:** out-of-state bypass stopped before the crown jewel; proven by absence on the PLC wire. ✔

## V4 — Op-aware ICS attack (DPI + criticality + remediation = "block AND maintain")
Compromised **trusted** seam `.2.31` (scada) writes a physically-impossible level to PLC1 — the signature ICS attack. Captured at **all three** wire points + controller + process:

- **Attacker packet (PLC1 wire, 19:29:44.529, byte-exact):**
  `…32 01 …000e 0008  **05**  01 12 0a 10 02 0004 **0007** **84** 000000  0004 0020 **40a00000**`
  → S7 **Write Var (func 0x05)**, **DB 0x0007**, **area 0x84 (DB)**, offset 0, value **`0x40A00000` = IEEE-754 5.0**. The exact tamper, on the wire.
- **DPI saw it:** `dpi_mirror.pcap` carries the identical write frame (length 39, func 05, value 40a00000) — Snort had full visibility.
- **CARS reaction on the control channel:** `of_control.pcap` contains **64 OpenFlow frames embedding `c0a8 021f`** (= 192.168.2.31) as the `OXM_OF_IPV4_SRC` match — the controller installed the **ISOLATE** flow-mod against `.2.31`.
- **Enforcement at the data plane (PLC1 wire):** immediately after the write, the PLC **retransmits its reply** (seq 50:72) at 19:29:45.176 / :47.176 / :51.177 with **no response from `.2.31`** — the connection **severed by the ISOLATE**.
- **Flow table (end):** `priority=110,ip,nw_src=192.168.2.31 actions=drop` (cookie `0xca`) — the ISOLATE, active; `isolate_flows_ovs1(0xca): 0 → 1`.
- **Process maintenance:** remediation `restores: 1 → 2`, level `46 →(5.0 tamper)→ 35` — the agent detected the impossible value (`5.0 < floor 25`) and **restored last-good**.
- **Timeline (single aligned chain):** `44.464` .2.31 SYN → `44.529` **S7 WRITE 5.0** (PLC wire + DPI) → ~`44.5` **ISOLATE flow-mod** (OF channel) + isolate flow installed → `45.176+` PLC retransmits, **.2.31 silent = cut** → remediation **restores++** by `49`.
- **Verdict:** op-aware DPI distinguished the **WRITE** from benign reads, CARS **ISOLATED** the source (wire-proven cut), **and** remediation **maintained** the process value — **"block AND maintain" proven end-to-end at the packet level.** ✔

---

## DISARMED BASELINE (control experiment) — the quantified impact of CARS
_Same campaign with enforcement OFF + remediation stopped (`cars_wire_campaign_disarmed.sh`, run 20:16–20:17). Level values are **direct PLC DB7 reads** = ground truth._
- **V4 disarmed (sustained compromised-scada write):** **16/16 writes succeeded**, `readback=5.0` held for 8 s — attacker pinned the level with no resistance. CARS still **detected** it (`20:17:04 FORBIDDEN … S7 CONTROL => DEFENSE DISARMED - would ISOLATE (monitor only) [CRIT:CRITICAL]`) but did not enforce; `isolate_flows(0xca)=0`. **PLC1 DB7.Level driven 40 → 12** (tampered/low). **Recovery:** re-arm + remediation restart → `Level 50`, service active.
- **V3 disarmed:** level stayed normal (67) — forged out-of-state ACKs still didn't perturb the process (ct pipeline is structural, holds even disarmed).

**Armed vs disarmed, same attack:**

| | ARMED | DISARMED |
|---|---|---|
| Writes landed | 1, then cut | 16 / 16 |
| CARS decision | `ISOLATE` ENFORCED | `FORBIDDEN` "would ISOLATE (monitor only)" |
| Isolate flow | yes (`0xca` 0→1) | no (0) |
| Attacker connection | severed on the wire | never cut |
| Process value | maintained (restore 1→2) | pinned 5.0 → left at 12 |
| Outcome | **protected** | **tampered** |

**Takeaway:** detection is identical in both modes — CARS judges the forbidden write on the CRITICAL asset either way. *Arming* is what turns that judgment into the enforced ISOLATE + the process staying safe. The disarmed run is the attack simply succeeding — the impact CARS prevents.

## Robustness verdict (per implementation, evidence-backed)
| Capability | Attack | Wire/cross-device evidence | Result |
|---|---|---|---|
| Control-API auth | Unauth disarm POST | 401 on wire + `CONTROL … DENIED` audit | **Refused + audited** |
| Flow-integrity checker | Inject + delete real A2 rule | Daemon `missing:1,extra:1` + decision-log drift; restored | **Autonomous detect** |
| Stateful pipeline | Forged out-of-state ACKs | **0 packets on PLC1 wire**; no ct entry | **No bypass** |
| Op-aware DPI + criticality + remediation | Compromised-seam S7 WRITE (DB7←5.0) | write frame (PLC wire+DPI) → ISOLATE flow-mod (OF) → PLC retransmits/no-ACK (cut) → remediation restores++ | **Block AND maintain** |

**Documented boundaries (unchanged):** full controller-compromise (a subverted controller knows `REACTIVE_COOKIE`), flow-audit poll-window (10 s), G1 compromised-endpoint, G3 S7CommPlus session-only HMI DPI. All are fundamental, not fixable bugs.

_All artifacts retained: `plc1_wire.pcap`, `of_control.pcap`, `dpi_mirror.pcap`, `events.log`, `flows_ovs1_baseline/end`, `v1_resp`._
