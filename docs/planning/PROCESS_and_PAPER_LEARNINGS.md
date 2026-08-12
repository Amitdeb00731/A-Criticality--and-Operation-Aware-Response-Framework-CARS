# Live Process on the PLCs + Learnings from the Cárdenas-group Papers

_2026-07-22. Two papers (same group): Murillo Piedrahita, Gaur, Giraldo, Cárdenas, Rueda — "Leveraging SDN for Incident
Response in ICS" (IEEE S&P Focus 2018) and "Virtual incident response functions in control systems" (Computer Networks 135,
2018). Purpose: (1) implement a live PLC-controlled process modelled on their water plant, (2) run the still-open tests
against it, (3) capture their impactful approaches for the write-up (they are prime related-work for the novelty comparison)._

## 1. What the papers do
- **Process:** SWaT-based water treatment — 3 PLCs. PLC101 → Tank_101 level (valve MV101 + pump P101), PLC301 → Tank_301
  level (P301), PLC201 → water pH (chemical dosing pump P201). Tanks connected by a pipe (cross-PLC coupling: P101 is on
  PLC101 but needs LIT301).
- **Control law (bang-bang / ON/OFF):** `MV101/P = 1 if LIT < lowL ; 0 if LIT > highL`. Tank dynamics (discrete integrator):
  `LIT(k+1) = LIT(k) + (V/A)·(u_in − u_out)`.
- **Testbed:** **simulated** — Mininet + a physical-process co-simulation (EtherNet/IP), SCADA + Historian. Open-source.
- **Attacks:** (a) **sensor false-data injection** — pin LIT101 to 0.3 so PLC101 never starts P101 → **Tank_101 overflows**;
  (b) **controller attack** — wrong control actions to actuators.
- **Response (their contribution):** SDN + NFV **virtual incident-response functions** that *take over* a compromised loop —
  a **state estimator / virtual sensor** replaces spoofed readings with model estimates; a **virtual PLC** runs open-loop
  control; **honeypot redirection** diverts the attacker. Response is **process-physics-aware**, not just network-level.

## 2. Impactful approaches (and how they map to CARS — novelty comparison + future work)
| Their mechanism | CARS today | Delta / opportunity |
|---|---|---|
| **State estimation / virtual sensor** (replace spoofed sensor data with model estimates) | none — CARS is network-level | **Future work for CARS**: a process-level response that, on detecting sensor/DB tampering, feeds estimated values. Big. |
| **Virtual PLC / open-loop takeover** (NFV) | none | Future work; needs a process model + NFV. |
| **Honeypot redirection** | **DEFLECT** → honeypot (have it) | CARS has the network redirect; the paper's honeypot also *emulates the process* (higher-interaction). Our G7 already notes this. |
| **Safety-capped, never-cut-the-loop** | **CARS core (REFUSE on CRITICAL)** | **The papers do NOT have this** — their response can take over/alter the loop. CARS's safety discipline is the distinguishing contribution. |
| **Proactive default-deny (works IDS-down)** | **CARS A2** | Papers are reactive-only (IDS-driven). |
| **Real ICS hardware** | **CARS: real Siemens S7-1200 ×2** | Papers are **simulated (Mininet)**. CARS on real hardware is a strength. |

**Honest novelty framing:** the Cárdenas group's contribution is *process-physics-aware* response (keep the process correct
via estimation) in **simulation**; CARS's contribution is *safety-capped, reactive+proactive network* response on **real
hardware** that provably never breaks the loop. **Complementary, not competing** — a combined system would block the
attacker at the network (CARS) AND maintain the process via estimation (their virtual functions). This is exactly the kind
of related-work delta the GAP doc said the dissertation needs; these two papers are two of the "closest 3–5".

## 3. Live process to implement on OUR real PLCs (mirrors their tank/bang-bang control)
Map their 2-tank level control onto our 2 real S7-1200s; the **Q0.3 relay = the pump/valve actuator** (audible + visible),
the tank level is simulated inside the PLC (a REAL in a DB = the "LIT" sensor, externally readable/spoofable like theirs).

**SCL (TIA Portal), one cyclic-interrupt OB (e.g. OB30 @ 100 ms) per PLC — TB1 = Tank_101 (TB2 = Tank_301 identical):**
```pascal
// --- Tank level bang-bang control (Cárdenas eq.1) + dynamics (eq.2) ---
IF  "DB".Level <= "DB".LowL  THEN "DB".Pump := TRUE;   // fill/pump ON when low
ELSIF "DB".Level >= "DB".HighL THEN "DB".Pump := FALSE; // stop when high
END_IF;
IF "DB".Pump THEN "DB".Level := "DB".Level + "DB".FillRate;   // eq.2 integrator
ELSE             "DB".Level := "DB".Level - "DB".DrainRate;
END_IF;
IF "DB".Level > 100.0 THEN "DB".Level := 100.0; END_IF;
IF "DB".Level < 0.0   THEN "DB".Level := 0.0;   END_IF;
%Q0.3 := "DB".Pump;   // drive the physical relay = the pump
```
Suggested tags: `Level:REAL`, `LowL:=30.0`, `HighL:=70.0`, `FillRate:=2.0`, `DrainRate:=1.5`, `Pump:BOOL`. Result: the level
oscillates in [30,70] and **Q0.3 cycles ON/OFF** = the pump cycling = a live, audible closed-loop process on real hardware.
Put `Level` in a DB so the HMI can read it (S7CommPlus monitoring) and an attacker can attempt to spoof it (sensor attack).

**Two attack surfaces (both map to the papers):**
- **Output hijack** (controller attack): external S7 write-var to `%Q0.3` (PA). Note: the PLC program re-asserts Q0.3 each
  scan, so a single write is transient — a *storm* is needed to hold it. CARS ISOLATEs the storm → program keeps control.
- **Sensor/level spoof** (their headline attack): external S7 write to the `Level` DB → control logic drives the pump wrong
  → over/underflow. CARS blocks writes to the PLC from an untrusted/dangerous conduit → level stays in bounds.

## 4. Still-open tests, run AGAINST this live process
- **No-harm / process integrity (capstone):** a monitor reads `%Q0.3` (or `Level`) continuously and counts pump cycles /
  checks the level stays in [Low,High]. Fire the multi-source barrage; **pass = the pump keeps cycling and level stays in
  band throughout** (CARS blocks all interference; the PLC's own loop is never disrupted). This is the direct "no harm" proof.
- **Multi-source DDoS + load (R9):** IT (`.2.1` via chain) + insider (`.2.77`) + netns (`.2.66`) hammer both PLCs at once;
  measure controller decide+enforce latency, zero legit-operator timeouts, zero collateral, loop counter never drops.
- **Sensor false-data injection (mirrors the paper's LIT101 attack):** attacker writes a false `Level` to the DB → CARS
  blocks the write → the real control law keeps the tank in band. (If we allow it through to show the *un*protected case:
  tank over/underflows — the paper's overflow result — then re-enable CARS to show protection.)
- **Cleverly-crafted / evasion (R13):** single one-shot / fragmented DPI-evading write (tests G3) — honest reactive-miss +
  A2 backstop.
- **R14 CRITICAL-loop boundary (G1):** documented — a fully-compromised HMI over the CRITICAL conduit is REFUSE (not enforced).

## 5. Implementation choice
- **Option A (recommended, most impactful):** program the SCL loop into the real S7-1200s via TIA Portal (Asus). A genuine
  closed-loop process on real hardware — a step **beyond** the papers' Mininet simulation.
- **Option B (fast):** a soft co-simulation on Dell#1 (Python models the tank dynamics, drives the real Q0.3 via snap7, holds
  `Level` in a shared store) — matches the papers' simulation approach; quicker but the control law lives in software, not the PLC.
