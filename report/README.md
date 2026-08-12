# CARS MSc dissertation (LaTeX)

Master file: `main.tex`. One `.tex` file per section, imported with `\input`.

## Build
- VS Code: install the **LaTeX Workshop** extension and a TeX distribution
  (TeX Live full, or MiKTeX). Open this `report/` folder and build `main.tex`.
- Command line: `pdflatex main` then `bibtex main` then `pdflatex main` twice.

## Layout
- `main.tex` .............. master (title metadata, structure, bibliography)
- `dissertation.cls` ...... University of Bristol MSc thesis class (unmodified)
- `references.bib` ........ bibliography (source-verified; complete TODO-VERIFY fields at first cite)
- `logo_uob_color.eps` .... title-page logo (used by the class)
- `figures/` .............. figures (created as we add them)
- Front matter: `abstract.tex`, `supporting-technologies.tex`, `notation.tex`, `ethics.tex`, `acknowledgements.tex`
- Body: `01_introduction.tex` (drafted), `02_background.tex`, `03_execution.tex`, `04_evaluation.tex`, `05_conclusion.tex`
- `appendix.tex`

Written to the rules in `../REPORT_PLAN.md`.
