# Changelog

All notable changes to the CARS framework are recorded here. Format loosely follows
Keep a Changelog; versions follow SemVer.

## [0.1.0] — 2026-08

First framework release. Packages the dissertation prototype (`06_Build/`) as an
installable, config-driven framework with a no-hardware emulation.

### Added
- **Config-driven engine.** `cars_engine.py` reads a `site.yaml` when `CARS_SITE`
  is set (opt-in, guarded); default behaviour is unchanged. `framework/cars/config/`
  loader + schema; `examples/site.testbed.yaml` is the testbed policy, extracted
  verbatim and proven equivalent by `tests/test_config_parity.py`.
- **Installable package** `cars-ids` with a CLI (`cars config validate`, `cars demo`).
- **Emulation for anyone** (`framework/emulation/`): a python-snap7 S7 PLC server,
  a pymodbus Modbus server and a tank co-simulation, plus a Mininet two-cell fabric,
  so a full defended attack runs with no hardware. The S7 process core is covered by
  a headless integration test (`tests/test_emulation_core.py`).
- **CI** (`.github/workflows/ci.yml`): lint, config parity, and the emulation core.
- **Docs**: architecture (with the Chapter 3 diagrams), quickstart, contributing,
  security and limitations.
- **Docker**: a controller image and Compose file.

### Notes
- Research prototype; not production- or safety-certified. See `framework/SECURITY.md`
  and `framework/LIMITATIONS.md`.
- Attack clients ship for research and authorised testing only.
