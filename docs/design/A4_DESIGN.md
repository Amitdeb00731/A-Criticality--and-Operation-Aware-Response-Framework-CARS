# A4 — Declarative, hot-reloadable rulebook. Design + record.
Done 2026-07-18 (CC-42). The capstone: the whole A1-A3 DECISION policy in one auditable table, changeable without code.

## Decisions (Rule-0 justified)
- **Scope = decision rulebook (replace `classify()`).** The decision logic (role->tier + A3 write-escalation) was the
  part scattered in code; A2's allowlist is already declarative. Replacing `classify()` completes the declarative policy
  without conflating proactive (A2 pre-installed flows) and reactive (on-detection) mechanisms. `select_response`,
  per-source offense, and enforcement stay intact — the rulebook only feeds the tier.
- **Match = first-match-wins (ordered).** ACL/firewall model: predictable, auditable, specific-over-general with a
  catch-all default — the right choice for a safety policy you must be able to reason about.
- **Behaviour-preserving refactor.** The rulebook must equal the old `classify()` exactly (proven: 400 combos, 0
  mismatches) before adding anything.

## Rulebook
`RULEBOOK = [(src, dst, op, tier), ...]`, evaluated top-down, first match wins.
- `src`/`dst` match by **role** (plc/hmi/supervisory/...), **exact IP**, or **"any"**.
- `op` matches "READ"/"WRITE"/"S7"/... or "any".
- Result = tier (CRITICAL/OPERATIONAL/SENSITIVE/FORBIDDEN); the existing `select_response` + escalation turn tier->response.
Order: CRITICAL control loop -> EWS elevated -> trusted WRITE (SENSITIVE) -> trusted read (OPERATIONAL) -> catch-all
FORBIDDEN to any PLC/HMI -> default-deny.

## Hot-reload (config-driven)
- `RULEBOOK_FILE = ~/cars/rulebook.json`. `load_rulebook()` seeds the file from the built-in defaults on first run,
  loads it at startup, and updates `RULEBOOK` in place (so `classify()` sees changes immediately).
- `GET /cars/rules` inspects the live table; `POST /cars/reload` re-reads the file (no restart).
- **Proven:** JSON edit permitting `.2.66->.2.20` + reload flips FORBIDDEN->OPERATIONAL live; revert + reload restores it.
  A bad/parse-error file keeps the previous rules (fail-safe).

## Honest boundary
A4 makes the **reactive decision** config-driven. The **A2 proactive allowlist** (`ALLOWLIST`/`DEFAULT_DENY_DSTS`) is a
separate declarative table applied at switch-connect; changing it needs a restart to reinstall the data-plane flows.
Hot-reloading A2's flows (re-derive + diff on `/cars/reload`) is a clean future extension. A4 does not touch enforcement.

## Future (A4+)
Extend rule fields already supported by the schema: exact-IP rules, per-function-code conditions, rate/timeout columns,
and context (maintenance window / process state) — all as table rows, no code. The schema is the seed of a full
`(src, dst, proto, fcode, action, rate, timeout, condition)` policy.
