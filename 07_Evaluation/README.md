# Evaluation harnesses

The scripts here reproduce the evaluation of Chapter 4 on the hardware testbed (or, for
the decision-only parts, against the deployed engine). This directory keeps the
**harness scripts** and the **specific result files the report cites**; the bulk raw
output (full pcaps and large dumps) is not shipped — re-run the harnesses to regenerate it.

- `cars2_mttm.py` — reaction-window (mean-time-to-mitigate) timing on a single clock.
- `overnight/vast_accuracy.py` — accuracy-at-scale over the 2,078-case labelled corpus.
- `overnight/b1_analyze.py` — normal-traffic baseline analysis.
- `overnight/night/night_analyze.py` — the long-run / stress-campaign plots.
- `overnight/gap4_flowmonitor/cars_flowmonitor.py` — the event-driven flow-integrity monitor.
- `overnight/results/` — the curated result files referenced by the report's figures
  (`vast/vast.csv`, `e2/interleaved.csv`, `jitter/timeline.csv`, `critbeh/judgements.csv`,
  `flowint/{persistent,transient}.csv`, `gap1_live/curve.csv`, `gap4_flowmonitor/…`).

See `../REPRODUCE.md` for which harness reproduces which claim, and `../06_Build/` for the
wire-campaign and criticality-proof shell harnesses.
