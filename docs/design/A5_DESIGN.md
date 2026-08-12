# A5 — Rate / Behavioral Intelligence (flood-aware, graded, safety-capped)

_Added 2026-07-19 (CC-66). Under Rule 0: states exactly what it adds, where it helps, and where it is redundant._

## 1. Motivation
Pre-A5, CARS decided on three axes: the operation (A3 operation-aware DPI), the actor (role/criticality/conduit), and
persistence (per-source/per-conduit offense count). It was **time-blind**: ten writes over an hour and ten writes in one
second escalated identically, and a flood of individually-**legal** reads was `ALLOW` every time. A source can deny
service to a PLC with entirely legal operations (comms/CPU saturation) — CARS could not see it. A5 adds the missing axis:
the **rate** of an operation.

## 2. Mechanism
**Sensor side (snort_bridge v4).** The controller cannot observe the true packet rate — the bridge dedups its POSTs on a
`COOLDOWN=3s` per `(src,dst,op)` key. So the bridge itself keeps a sliding window `RATE_WINDOW=3s` of every alert per key
and sends the current `rate` (ops/s) in each `/respond` payload. During a 20/s storm it POSTs once per 3s but carries
`rate≈17–20`; at normal cadence `rate<1`.

**Brain side (cars_engine).** `respond()` reads `rate`, sets `flood = rate >= FLOOD_RATE` (5/s), and passes it to
`select_response`, which grades:

| tier | normal | **flood** |
|---|---|---|
| CRITICAL (HMI↔PLC loop) | REFUSE | **REFUSE** (safety cap holds — never throttle the loop) |
| OPERATIONAL (permitted, e.g. read) | ALLOW | **THROTTLE (meter) → BLOCK** on persistence |
| SENSITIVE (ews→plc) | THROTTLE→BLOCK | **BLOCK** (cut now, don't rate-limit) |
| FORBIDDEN (untrusted→PLC) | BLOCK→ISOLATE | **ISOLATE** immediately |

The decision line is tagged `[FLOOD N ops/s]`, and the response is bounded/reversible like every A1 response (meter/flow
`hard_timeout=30s`, self-heals when the flood stops).

## 3. What it proves (measured, CC-66)
On the **same legal S7 read** from `.2.31` at ~17/s (`cars_rate_demo.sh`, dashboard CSV corroborated):

```
READ => ALLOW                       (normal rate)
READ => [FLOOD 17 ops/s] THROTTLE   (graded step 1)
READ => [FLOOD 17 ops/s] THROTTLE
READ => [FLOOD 17 ops/s] BLOCK      (graded step 2, sustained)
READ => ALLOW                       (flood stopped -> self-healed)
```

Controller decide+enforce 0.4–0.7 ms. Graded **and** reversible, with no lasting penalty once the abuse stops.

## 4. Honest scope (where A5 is redundant)
A5's value is **volumetric abuse of _permitted_ operations**. For **forbidden** ops it is largely redundant: a forbidden
op is cut on the **first packet** by the reactive layer (A1/A3), so its rate never accumulates at the sensor to trip the
threshold — the write-flood in the DoS demo (CC-65) is `ISOLATE`d immediately, `[FLOOD]` or not. So the honest claim is
**not** "flood detection catches everything" — it is: _CARS adds a temporal axis that catches volumetric DoS built from
legal operations, which the operation/criticality axes cannot see, while forbidden bursts remain covered by the existing
first-packet enforcement._

## 5. Parameters (tunable)
`RATE_WINDOW=3.0s`, `FLOOD_RATE=5.0 ops/s`, `THROTTLE_RATE=20 pps` meter, `ESCALATE=3` (THROTTLE→BLOCK), `BLOCK_TIMEOUT=30s`
(self-heal). `FLOOD_RATE` sits above normal operator cadence and well below a 15–20/s storm; the legitimate HMI loop is
CRITICAL→REFUSE regardless of rate, so it is never affected.
