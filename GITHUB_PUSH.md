# Publishing this repository to GitHub

The repository is already a git repo, reconciled to the final state and committed
locally. Follow these steps to publish it and make the report's links resolve.

Replace `USERNAME` with your GitHub username throughout. The suggested repo name is
`Reactive_SDN_ICS` (keep it consistent with the report links).

## 1. Point the report at your repository (one line)

Set the URL the report links to. Edit `report/main.tex`, line with `\repourl`:

```latex
\newcommand{\repourl}{https://github.com/USERNAME/Reactive_SDN_ICS}
```

Change `USERNAME` (and the repo name if you use a different one) to your real URL.
This single line drives every "Code and data availability" link and the file-map
table in the appendix. Then rebuild the report so the links bake in
(`latexmk -pdf main.tex`).

## 2. Create the GitHub repository and push

### Option A — GitHub CLI (fastest)

```bash
cd /path/to/Reactive_SDN_ICS
gh auth login                       # once, if not already authenticated
gh repo create Reactive_SDN_ICS --private --source=. --remote=origin --push
```

`--private` is recommended until after your submission/marking; switch to `--public`
later with `gh repo edit --visibility public` if you wish.

### Option B — manual (create on github.com first)

1. On github.com: New repository, name it `Reactive_SDN_ICS`, do **not** add a
   README/.gitignore/licence (the repo already has them).
2. Then:

```bash
cd /path/to/Reactive_SDN_ICS
git remote add origin https://github.com/USERNAME/Reactive_SDN_ICS.git
git branch -M main
git push -u origin main
```

If you set `\repourl` in step 1 after committing, commit that change too:

```bash
git add report/main.tex && git commit -m "Set repository URL for report links" && git push
```

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
