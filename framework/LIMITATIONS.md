# Limitations

CARS is a functional research prototype validated on a single hardware testbed with one hardware-in-the-loop process. Its results and its guarantees are bounded accordingly. These limits are stated in full in the dissertation's Threats-to-Validity chapter; the essentials are repeated here so an adopter starts with clear eyes.

## Scope of validation

- **Single testbed, one process.** The 100% decision accuracy and 0% false-positive figures are statements about this system, its rulebook, and the tested decision space plus the live campaign — not a statistical guarantee for arbitrary industrial traffic.
- **Hardware-in-the-loop.** The PLC, the S7 traffic, the control logic and the enforcement are real; the water is simulated in Factory IO, so overflow is a faithful process consequence, not a physical spill.

## What the reactive layer cannot bound

- **Reaction window vs. fast processes.** Mitigation is a few milliseconds on this slow tank, but a fast process (high-speed manufacturing, protection loops) can be harmed inside that window. The proactive layer (identity binding, allowlist, default-deny) has no reaction window and does the heavy lifting there.
- **First-packet leakage on a trusted conduit.** An unregistered source is stopped at the handshake, but a compromised, already-allowlisted host lands its first packets by design. For a discrete atomic command (e.g. an S7 STOP) that first packet is enough.
- **Encrypted protocols.** Operation-awareness needs a readable payload. S7CommPlus, OPC UA with security, or CIP Security blind the DPI tier; the proactive stateful layer still holds.
- **Trusted insider within its envelope.** A genuinely trusted party acting slowly within its physical envelope is the residual a network layer must not automate against; a read-only process guardian narrows but does not close it.

## Deployment gaps

See `SECURITY.md` for the hardening gaps (unauthenticated `/cars/respond`, plaintext control channel, silent-drop socket exhaustion, gateway-scoped sensing) and their mitigations.

## Emulation fidelity

The emulation path substitutes **software PLC servers** (snap7, pymodbus) for the physical Siemens CPUs. It runs genuine S7comm/Modbus, Snort DPI, OVS and the real controller, so it faithfully demonstrates the decision-and-enforcement pipeline — but it is not a substitute for validating against real hardware and real process-safety behaviour.
