# Publishing this repository to GitHub

The repository is a git repo, reconciled to the final state and committed locally, and
the report's links are already set to your repository:
`https://github.com/Amitdeb00731/A-Criticality--and-Operation-Aware-Response-Framework-CARS`.
Your GitHub repo already exists and is public, so you only need to add the remote and
push.

## Push (your repo already exists on GitHub)

```bash
cd /path/to/Reactive_SDN_ICS
git remote add origin https://github.com/Amitdeb00731/A-Criticality--and-Operation-Aware-Response-Framework-CARS.git
git push -u origin main
```

If GitHub rejects the push because the repo was created with a README or licence
(non-fast-forward), merge those in once, then push:

```bash
git pull origin main --allow-unrelated-histories --no-edit
git push -u origin main
```

Or, if you don't need GitHub's auto-created files, overwrite them:

```bash
git push -u origin main --force
```

Authentication: if prompted, use a GitHub personal access token as the password, or
`gh auth login` first if you have the GitHub CLI.

## 3. What is and isn't tracked

Excluded by `.gitignore` (regenerable or too heavy): LaTeX build artefacts,
`report/main.pdf`, the 23 MB Snort journal, two unused high-resolution figure
originals, raw overnight pcaps, and `__pycache__`. Tracked tree is ~45 MB.

If you want the **final built PDF in the repo** (some prefer this for a dissertation),
build it cleanly (after `tlmgr install algorithm2e relsize`) and force-add it:

```bash
git add -f report/main.pdf && git commit -m "Add built dissertation PDF" && git push
```

## 4. Build note (important)

`dissertation.cls` requires `algorithm2e` (unused in the document but loaded by the
class). If it is missing, `latexmk` fails and silently keeps the last PDF. Install it
before building: `tlmgr install algorithm2e relsize` (or your distro's
`texlive-science`). A correct build is 84–85 pages.
