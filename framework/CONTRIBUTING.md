# Contributing

CARS is a research prototype from an MSc dissertation, opened as a framework so others can adopt, reproduce and extend it. Contributions are welcome; please keep the honesty discipline of the original work — no claim without evidence, and limitations stated plainly.

## Development setup

```bash
cd framework
pip install -e '.[dev]'          # pytest + ruff
pip install python-snap7 'pymodbus>=3.5,<3.9'   # for the emulation-core tests
```

## Before you open a PR

```bash
ruff check cars                  # lint the package (config in pyproject.toml)
PYTHONPATH=. pytest tests/ -q     # config parity + headless emulation core
```

CI (`.github/workflows/ci.yml`) runs the same on every push touching the framework or the engine.

## Ground rules

- **The engine's default behaviour must not change.** The `CARS_SITE` overlay is opt-in and guarded; `tests/test_config_parity.py` proves the shipped config reproduces the built-in policy exactly. Keep that test green.
- **Config, not code.** New policy (assets, roles, conduits, rulebook, criticality) belongs in `site.yaml` and the loader, not hardcoded.
- **Honesty.** If a component is not tested, say so. The emulation substitutes software PLCs for the physical CPUs; do not present it as a hardware or safety validation.
- **Offensive tooling** is for research and authorised testing only (`SECURITY.md`).

## Roadmap

The phase plan is in `../docs/planning/CARS_FRAMEWORK_PLAN.md`. Good first areas: wiring the remaining engine tuning constants into `site.yaml`, a fully-automated Mininet demo (Python API rather than the interactive CLI), and a Dockerised controller.
