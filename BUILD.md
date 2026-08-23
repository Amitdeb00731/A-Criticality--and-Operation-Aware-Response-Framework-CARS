# Building CARS

## The framework (Python package)

```bash
cd framework
pip install -e .                       # core: config loader + CLI
pip install -e '.[controller,emulation]'   # + os-ken, requests, python-snap7, pymodbus
cars config validate examples/site.testbed.yaml
```

Requires Python 3.9+. Lint and tests:

```bash
ruff check cars
PYTHONPATH=. pytest tests/ -q
```

## The controller Docker image

Build from the repository root (needs `framework/` and `06_Build/cars_engine.py`):

```bash
docker build -f framework/Dockerfile -t cars-controller:0.1.0 .
# or with compose (from framework/):
cd framework && docker compose up --build
```

The image is the controller only: it listens on `:6653` for OpenFlow and `:8080` for the control API. Point your Open vSwitch bridges (real fabric or the Mininet emulation on the host) at it. Override the policy by mounting your own `site.yaml` and setting `CARS_SITE`.

## The dissertation (LaTeX)

```bash
cd report
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

Requires a full TeX Live: the class `dissertation.cls` uses `algorithm2e`, `listings`, and the University of Bristol thesis template. `main.pdf` is not committed; it regenerates from source. Always run **bibtex** so the citations resolve.

## Release

Cutting a tagged release and minting a Zenodo DOI is documented in `framework/RELEASE.md`.
