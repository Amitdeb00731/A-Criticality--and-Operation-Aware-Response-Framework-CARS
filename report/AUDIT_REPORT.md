# CARS Dissertation — Independent Audit (peer-review style)

Audited: current LaTeX source in `report/`, a clean 84-page rebuild compiled from it,
the raw lab data in `07_Evaluation/overnight/results/`, and REPORT_PLAN.md.
Date of audit: 14 August 2026.

---

## 1. Headline verdict

The **written report is in strong shape**: every headline number traces to captured
data, citations are clean and resolve, all figures and appendix listings are present,
and the prose is honest about its boundaries. Two things must be actioned before
submission — one is blocking, one is a policy call:

- **BLOCKING (build):** the `main.pdf` that was circulated is a stale skeleton, not
  the report. Rebuild required (see §2). Resolved here by producing a correct 84-page
  build.
- **MAJOR (word budget):** the body is ~17–18k words against the plan's 6,000–10,000
  band. Needs a supervisor decision and probably trimming (see §7).

Everything else is minor.

---

## 2. Blocking finding — the compiled PDF (RESOLVED, but you must rebuild locally)

The circulated `main.pdf` (43 pages) contains literal placeholders:
- Ch4 Critical Evaluation: "[To be written: accuracy and false-positive evaluation…]"
- Ch5 Conclusion: "[To be written…]"
- Appendix A: "[To be written…]"
- Bibliography still carrying `VERIFY:` working notes.
No `7.6 ms`, no §4.8, no event-driven monitor, ~6.4k words.

**Cause:** `dissertation.cls` requires `algorithm2e` (with `[algochapter]`), which is
missing on the build machine. `latexmk` therefore fails on the current source and
keeps serving the last skeleton that *did* compile. `algorithm2e` is required by the
class but never used in the document.

**Fix on your machine:** `tlmgr install algorithm2e relsize` (or install
`texlive-science`), then `latexmk -pdf main.tex`. Confirm the result is ~84 pages with
real Ch4/5/appendix. A correct build (`CARS_dissertation_REBUILT.pdf`) was produced in
this session for reference; it neutralised the unused `algorithm2e` line only to prove
the source is complete — you should install the package rather than edit the class.

---

## 3. REPORT_PLAN compliance, rule by rule

- **R1 (no unverified/invented claim):** PASS. Headline numbers re-derived from raw
  files (§4). No placeholders or TODOs anywhere in the body/appendix.
- **R2 (no AI tells / em-dashes / British spelling):** PASS. No em/en dashes, none of
  the flagged tell-words, British spelling throughout.
- **R5 (genuine citations):** PASS. 16 bib entries, every `\cite` resolves, no
  undefined citations; the only "VERIFY" strings are provenance comments in the .bib.
- **R8/R11 (vital proof in body, rest signposted):** PASS. Body carries the vital
  proof; appendix is comprehensive with correct `\ref`/`Appendix~\ref` signposts.
- **R9/R10 (verify/rerun on device):** PASS for the evaluated results; all fresh-run
  numbers reconcile to the captured files.
- **Word budget (plan §3):** FAIL against the 6–10k band (~17–18k). Supervisor call.
- **Template/front matter:** Abstract, Supporting Technologies, Notation, Ethics
  (§4.13) and Threats (§4.12) all present. Orphaned `ethics.tex` stub is dead code.

---

## 4. Fact & number verification (checked against raw data, all PASS)

| Claim in report | Raw source | Result |
|---|---|---|
| MTTM median 7.6, mean 11.2, sd 11.8, p95 38.4, p99 67.9, min 5.5, max 72.9 ms | `b2/mttm_values.txt` (n=100) | exact (p95/p99 = numpy linear percentiles) |
| Accuracy 2,078 cases: 2,040 TP, 38 TN, 0 FP, 0 FN; 51 sources | `vast/vast.csv` | exact (2,040/40 = 51 sources) |
| Wilson 95% CI [0.9982, 1.0000] | 2078/2078 | correct |
| Flow-integrity: persistent 30/30 @ 8.5 s; transient 5/30 | `flowint/*.csv` | exact |
| Event-driven monitor: 30/30 @ median 0.27 s | `gap4_flowmonitor/…csv` | exact (270.9 ms) |
| Process transparency: disarmed 51.5/sd 12.8, armed 50.7/sd 13.2 | `e2/interleaved.csv` | exact |
| Criticality ladder 75/60/45/30 s = 30+15w | engine `cars_engine.py` | exact |
| Gap 2: gateway→BLOCK conduit, .77→ISOLATE source | live probe | exact |
| Accuracy table 24 scored = 13 TP + 11 TN (+3 grey) | table rows | consistent |

---

## 5. Figures & tables

- All 44 `\includegraphics` targets exist in `figures/` and resolve (the
  `{fig0X…drawio}.png` form is correct).
- Data charts verified against data: `chart_mttm.png` (7.6/38.4/67.9 markers, 100
  trials), `chart_critsweep.png` (75/60/45/30 vs w=3..0). Correct labels and numbers.
- Accuracy table (Table 4.1) and confusion table internally consistent.
- **To check on the correct rebuild (couldn't be done on the stale PDF):** float
  placement/overflow of the wide listings and the decision matrix, that every figure
  renders (not just exists), caption/label pairing, and that no table breaks a margin.

---

## 6. Appendix & cross-references

- All 10 `\lstinputlisting` external files present under `appendix_listings/`.
- New Gap C (event-driven) and Gap 2 (conduit BLOCK) listings added and labelled
  uniquely (`lst:ev_poll_fix`, `lst:ev_natblock`); Appendix `appx:availability`
  present and signposted from §4.8 and §4.10.
- No missing cross-references (0 `??` in the rebuild).

---

## 7. Issues by severity

**Major**
1. Word budget ~2x over the plan's 6–10k band. Decide with supervisor; if trimming,
   the densest candidates are the two-pivot narrative (§4.7), the load discussion
   (§4.6), and some threats-to-validity prose, which can be condensed without losing
   evidence.

**Minor / cosmetic**
2. Transparency sample count: appendix intro says "7,060 samples" but the online-only
   split is 3,528 + 3,530 = 7,058. Reconcile the wording (7,060 rows captured, 7,058
   online).
3. Title-page date is fixed to "3 August 2026" (the stable-baseline date). Confirm the
   real submission date before handing in.
4. Delete the orphaned `ethics.tex` stub (dead; Ethics is §4.13).
5. A `LaTeX Font Warning: OMS/cmtt/m/n undefined` in the build — cosmetic; add
   `\usepackage{textcomp}` if you want it gone.

---

## 8. Peer-reviewer gap list (the work, not just the report)

These are the questions an external examiner will press. Most are already stated as
limitations in §4.12; listed here so nothing is a surprise in the viva.

1. **Single testbed, single policy.** 100% accuracy and 0% FP are properties of *this*
   rulebook over *this* decision space plus one live campaign, not a statistical claim
   for arbitrary industrial traffic. Stated honestly, but it is the central external
   critique.
2. **HIL, not a real plant.** Every result is on a Factory IO tank; the transparency
   and block-and-maintain findings are strong for the testbed, not a universal
   guarantee. Stated.
3. **Reaction window is a detect-then-respond property.** 7.6 ms here; on a fast
   process one second (sustained-flood cut) is ample for damage. The proactive layer
   carries the truly-fast cases. Stated.
4. **Trusted-insider-in-envelope is unsolved.** The guardian alarms, it does not
   prevent; a slow, plausible manipulation still evades it. This is the hardest ICS
   problem and remains open by design. Stated.
5. **NAT attribution.** Even after the Gap 2 refinement, CARS cannot separate a rogue
   IT host from its neighbours behind a NAT on the same conduit; true attribution
   needs the boundary firewall. Stated.
6. **Control-plane security.** OpenFlow runs in plaintext on an isolated management
   plane; TLS is unimplemented and its latency unmeasured. The event-driven monitor
   now closes the transient-injection window, but a genuine controller *crash*
   transparency figure is still not proven (fail-secure switches only bound it).
7. **State-exhaustion and bridge scaling.** Not tested against a spoofed-source
   conntrack-exhaustion flood; the file+HTTP detection bridge is characterised
   (~16–18k alerts/s single-core, bench) but a heavy distributed flood would still
   bottleneck it. Enabling Snort reassembly also adds IDS state (bounded at max_tcp
   8192, passive mirror). Stated.
8. **DPI evasion / encrypted protocols.** Operation-awareness depends on a readable
   payload; overlapping-segment/timing evasions and S7CommPlus/OPC-UA-secure would
   blind the reactive tier (proactive tier still holds). Stated.
9. **No head-to-head baseline.** The comparison with related work is qualitative; no
   competing reactive-SDN system was run on the same testbed for a quantitative
   contrast. A reviewer may ask for this.
10. **Half-open sockets / connection-pool exhaustion on the S7-1200.** Identified
    analytically (silent drop leaves the PLC socket half-open), not stress-tested; TCP
    reset on quarantine is the proposed remedy.

---

## 9. Punch list (do before submission)

- [ ] Install `algorithm2e`, rebuild `main.tex`, confirm 84-page real PDF.
- [ ] Supervisor decision on word count; trim if required.
- [ ] Reconcile the 7,060 vs 7,058 transparency sample wording.
- [ ] Set the correct submission date on the title page.
- [ ] Delete `ethics.tex`.
- [ ] On the correct PDF: eyeball every figure renders, captions pair, no table/listing
      overflows the margin, and the wide decision matrix and code listings sit well.
- [ ] Optional: add `\usepackage{textcomp}` to clear the font warning.
