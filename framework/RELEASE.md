# Cutting a release (and getting a DOI)

The version is set to **0.1.0** (`pyproject.toml`, `cars/__init__.py`). These steps need
GitHub and Zenodo access, so they are done by the maintainer, not from this workspace.

## 1. Pre-release checks

```bash
cd framework
ruff check cars                       # lint clean
PYTHONPATH=. pytest tests/ -q          # config parity + emulation core green
python -m build                        # optional: build the wheel/sdist (pip install build)
docker build -f Dockerfile -t cars-controller:0.1.0 ..    # controller image builds
```

Confirm `CHANGELOG.md` covers 0.1.0 and `README.md` is current.

## 2. Tag and release on GitHub

```bash
git add -A
git commit -m "CARS framework v0.1.0: config-driven engine, emulation, CI, docs, Docker"
git tag -a v0.1.0 -m "CARS framework v0.1.0"
git push origin main --tags
```

Then create a GitHub Release from tag `v0.1.0` (paste the CHANGELOG 0.1.0 notes).

## 3. Mint a DOI on Zenodo

1. Sign in to <https://zenodo.org> with GitHub, and under **Settings → GitHub** flip the
   switch **on** for this repository. (Do this *before* the release; Zenodo only archives
   releases created after the switch is enabled.)
2. `.zenodo.json` at the repo root supplies the metadata (title, authors, licence, keywords),
   so the archive is correct automatically.
3. Publishing the GitHub Release triggers Zenodo to archive it and mint a DOI (a versioned
   DOI plus a concept DOI for "all versions").

## 4. After the DOI is minted

- Add the DOI to `CITATION.cff` (a `doi:` field) and a DOI badge to `README.md`.
- Add an **Availability** line to the dissertation pointing at the repo and the DOI, e.g.:
  *"CARS is available as an open-source framework at <repo>, archived at <DOI>."*

That gives the thesis a citable software artefact and lets others install, reproduce and
build on the pipeline.
