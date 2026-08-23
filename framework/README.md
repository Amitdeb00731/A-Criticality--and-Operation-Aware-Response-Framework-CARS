# CARS framework (`cars-ids`)

A criticality- and operation-aware SDN intrusion-response framework for industrial control systems. This directory packages the research prototype in `../06_Build` as an installable, config-driven framework so it can be adopted on another network, or tried end to end in emulation with no hardware.

> **Status: early (v0.1.0.dev0).** Config extraction and packaging are in progress; the live controller and the emulation demo are being wired to the validated engine. See `../docs/planning/CARS_FRAMEWORK_PLAN.md` for the phase plan. This is a research prototype, not a production or safety-certified system — read `LIMITATIONS.md` and `SECURITY.md`.

## The idea

The design philosophy mirrors the dissertation's Chapter 3: separate the **portable core** (the decision engine — classify, criticality elevation, response selection, GUARD, the three-table pipeline) from the **site-specific instantiation** (addresses, roles, conduits, rulebook, criticality). You adopt CARS by writing a `site.yaml` for your network, not by editing code.

## What works today

```bash
pip install pyyaml
python -m cars.config.loader examples/site.testbed.yaml
# or, once installed:  pip install -e .  &&  cars config validate examples/site.testbed.yaml
```

`examples/site.testbed.yaml` is the dissertation testbed's policy, extracted verbatim from the validated engine, and doubles as the schema reference. `cars config validate` loads and checks it and prints the criticality-scaled timeouts (75/60/45/30 s).

### Config-driven engine (opt-in)

The controller (`../06_Build/cars_engine.py`) now reads a site config when you point it at one, and is otherwise unchanged:

```bash
# config mode: overlay policy from a site.yaml
CARS_SITE=/path/to/site.yaml  osken-manager cars_engine.py
# default mode: no env var -> built-in constants, behaviour identical to before
osken-manager cars_engine.py
```

The overlay is fully guarded (any failure falls back to the built-in defaults and logs a warning), and `framework/tests/test_config_parity.py` proves `site.testbed.yaml` reproduces the built-in policy exactly — so config mode on the testbed is byte-equivalent to the validated defaults. Run the parity test and a short testbed smoke test before relying on config mode:

```bash
cd framework && PYTHONPATH=. python -m pytest tests/test_config_parity.py -q
```

## Documentation

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — install, validate a policy, run the emulation, run the tests.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the pipeline, the decision, and the component-to-code map (with the Chapter 3 diagrams).
- [`emulation/README.md`](emulation/README.md) — the no-hardware demo.
- [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY.md`](SECURITY.md), [`LIMITATIONS.md`](LIMITATIONS.md).

## Roadmap (each phase ships independently)

1. **Config extraction** — policy in `site.yaml` + loader, engine reads it (opt-in overlay); parity-tested. ✅
2. **Package + CLI** — installable `cars-ids`, `cars config validate`. ✅ (`cars run` on a live fabric: next)
3. **Emulation for anyone** — software S7/Modbus PLCs + tank co-sim (verified) and a Mininet fabric so a full defended attack runs with no hardware. ✅ (core tested; fabric runs on a Linux host)
4. **Docs + CI** — quickstart, architecture, contributing; CI runs lint + config-parity + the headless emulation core. ✅
5. **Release** — Docker Compose, tagged release, Zenodo DOI. *(next)*

## Layout

```
framework/
├── cars/                 installable package
│   ├── config/           site.yaml loader (+ schema validation)
│   ├── engine/           decision core (to be wired from 06_Build/cars_engine.py)
│   ├── adapters/         detection (Snort) + southbound (OpenFlow 1.3 / os-ken)
│   ├── api/              /cars/respond feed + authenticated control endpoints
│   └── cli.py            cars config | run | demo
├── emulation/            Mininet topology + software PLCs (snap7, pymodbus) + tank model
├── examples/             site.testbed.yaml (and your own site configs)
├── pyproject.toml
├── README.md   SECURITY.md   LIMITATIONS.md
```

## Licence

MIT (`../LICENSE`). Maximum reuse; attribution appreciated (`../CITATION.cff`).
