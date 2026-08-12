# Statistical / mathematical validation plan (strengthen beyond the functional prototype)

Goal: move the accuracy and latency claims from "functional prototype, 24 cases" toward a defensible statistical (and, over the finite domain, near-exhaustive) result. Do tomorrow if time allows, after the cross-layer captures. Honest target: not a universal proof, but (a) exhaustive coverage of the testbed's decision domain rather than a hand-picked sample, (b) confidence intervals on the error rates, (c) a characterised latency distribution with an analytic worst-case bound. This addresses the two named weaknesses: the tiny scored sample (24) and the 1 s worst-case reaction window.

## 1. Exhaustive decision-space enumeration (attacks the sample-size weakness)
The decision function is deterministic and total: `classify()` is first-match over a fixed RULEBOOK, with a default-deny catch-all, then the criticality elevation, then `select_response()`. Its input domain on the testbed is finite and small: {registered source roles} x {real destination assets, each with a fixed criticality} x {operation classes READ/WRITE/CONTROL/DIAG/PROGRAM/ILLEGAL/TCP} x {a couple of rate bands}. That full Cartesian product is on the order of a few hundred cases, so it can be enumerated in full, not sampled.
- Method: extend `cars_eval.py` into `cars_eval_full.py` (or a loop) that iterates every (src in REGISTRY) x (dst in assets) x (op in ops) x (rate in {0, flood}) and posts each to `/cars/respond`; derive the EXPECTED verdict directly from the deployed RULEBOOK + criticality logic (the policy is the ground truth); compare measured vs expected for every case.
- Result to report: N (the full domain size, hundreds), the confusion counts, and that coverage is 100% of the domain (every reachable (role, op, criticality) combination), not a subset. This is a proof-by-enumeration of the decision logic over the testbed's domain, subject only to the domain being this testbed's roles/assets.
- Run disarmed (decision-only) so nothing is enforced; re-arm after.

## 2. Confidence intervals on the error rates (statistical rigour)
- From the exhaustive run and from the aggregated live decisions (the campaign decision logs, thousands of rows), compute the false-positive and false-negative rates with a binomial confidence interval (Clopper-Pearson or Wilson), not a bare percentage.
- Report the standard result for zero observed errors: 0 / N gives, by the rule of three, a 95% upper bound of about 3/N on the true rate (e.g. 0/500 -> <= ~0.6% at 95%). State the FP-rate upper bound explicitly; this is the honest statistical form of "0% false positives".
- Aggregate the live-traffic decisions across all campaign phases as an independent, larger sample and give its interval too.

## 3. Latency distribution and worst-case bound (attacks the 1 s window)
- Re-run the MTTM harness for a larger n (>= 100 trials, ideally a few hundred) to characterise the distribution rather than 15 points.
- Report p50, p90, p95, p99, the mean, the standard deviation, and a confidence interval on the median; plot the CDF / histogram.
- Give the analytic bound: the reaction window <= detection-poll interval + (Snort detect + bridge + decide + install), so the worst case is bounded by the Snort/bridge poll period plus a small constant. State that period, and show the tail (the ~1 s cases) is exactly one poll interval; then note the concrete levers to shrink it (shorter poll, event-driven bridge instead of tail-polling) and that a fast process would require them.

## Placement in the dissertation
- A short "Statistical validation" subsection in Chapter 4 (after 4.2 or 4.5): the exhaustive-N accuracy with its confidence interval, and the latency distribution with percentiles and the analytic bound.
- Appendix: the full enumerated matrix (the hundreds of cases), the CI computation, the latency percentile table and CDF.
- Reframe carefully and honestly: this strengthens the claim from "24 hand-picked cases" to "exhaustive over the testbed's decision domain, with confidence intervals and a bounded worst-case latency", while the Threats-to-Validity limits (single testbed, one rulebook, simulated process, reactive window for a fast process) still stand. It is a stronger validation, not a universal proof.

## Captures/runs needed (fresh, rule 10)
1. `cars_eval_full.py` (extend cars_eval.py to the full domain) -> the exhaustive matrix CSV.
2. `cars_mttm.sh 200` (or loop to >= 100 trials) -> the latency sample for the distribution.
3. Compute the CIs and percentiles offline from the CSVs (Python/scipy) and build the table + CDF figure.
