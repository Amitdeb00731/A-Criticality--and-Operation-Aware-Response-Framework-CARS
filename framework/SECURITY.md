# Security policy and posture

CARS is a **research prototype** from an MSc dissertation. It demonstrates a criticality- and operation-aware reactive defence on a lab testbed. It is **not hardened for production** and must not be relied on as the sole protection for a live industrial process.

## Known hardening gaps (carried openly from the dissertation)

These are documented honestly in the report's Threats-to-Validity chapter and are tracked as future work, not hidden:

- **Unauthenticated detection feed.** The `/cars/respond` endpoint is intentionally outside the control-API token gate so the sensor bridge stays lightweight. A host that can reach it could forge an alert and drive a reactive isolation. Mitigation: an authenticated / HMAC-signed feed. Keep the reporting interface on an isolated management plane.
- **Plaintext control channel.** OpenFlow runs over `tcp:6653` without TLS. Mitigation: run OpenFlow over TLS; keep the control plane on a separate management network.
- **Silent-drop socket exhaustion.** An isolate installs a silent drop, leaving a half-open S7 session on the PLC; on small CPUs (e.g. S7-1200, six dynamic connection resources) repeated isolation can exhaust the pool. Mitigation: emit a TCP reset toward the PLC on quarantine, or rate-limit isolations.
- **Gateway-scoped sensing.** DPI covers only gateway-crossing traffic; a purely intra-cell attack is not operation-aware (the proactive default-deny still applies). Mitigation: per-cell sensing.
- **First-packet residual on a trusted conduit.** The first packet of an atomic operation on an already-allowlisted conduit can land before the reactive drop installs. Mitigation: push more coverage into the proactive layer; TCP reset on quarantine.

## Offensive tooling

This repository ships attack clients (`s7_write.py`, `mb_attack.py`, `cars_fdi_overflow.py`, and others) **for research and authorised testing only**. Use them exclusively against systems you own or are explicitly authorised to test. The authors accept no liability for misuse.

## Reporting a vulnerability

Open a private security advisory on the GitHub repository, or contact the author. Please do not file public issues for security-sensitive findings.
