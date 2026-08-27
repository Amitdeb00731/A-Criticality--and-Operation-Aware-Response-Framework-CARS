#!/usr/bin/env python3
"""
Figure 4.13 generator: framework flow-table behaviour under a distinct-source
isolate flood. Two panels, each series drawn as its own labelled curve with a
legend and its own axis. Nothing is invented; every point is read from the two
captured CSVs. Memory is plotted in full, so the plot itself shows the daemon
reaching 393 MB at the 94k peak and lingering to 425 MB through the drain.

Inputs  (repo-relative):
  07_Evaluation/overnight/results/flowtable_ramp_20k.csv     (left, graceful)
  07_Evaluation/overnight/results/flowtable_ceiling_94k.csv  (right, saturation)
Output:
  report/figures/stat_flowtable.png
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RES = os.path.join(REPO, "07_Evaluation", "overnight", "results")
OUT = os.path.join(HERE, "..", "stat_flowtable.png")

BLUE, ORANGE, GREEN, GREY = "#1f5fa8", "#e07b1a", "#2e8b57", "#555555"

ramp = pd.read_csv(os.path.join(RES, "flowtable_ramp_20k.csv"))
ceil = pd.read_csv(os.path.join(RES, "flowtable_ceiling_94k.csv"))

plt.rcParams.update({"font.size": 11, "axes.titlesize": 12,
                     "legend.fontsize": 9, "figure.dpi": 150})
fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.5, 5.2))

# ---------------------------------------------------------------- LEFT panel
# graceful regime: flows track sources 1:1, install latency flat at ~2 ms.
axL.set_title("Graceful regime: single injector (~400 flows/s)")
l1, = axL.plot(ramp["t_s"], ramp["reactive_flows"], color=BLUE, lw=2.4,
               label="reactive flows on gateway")
axL.set_xlabel("time (s)")
axL.set_ylabel("reactive flows on gateway", color=BLUE)
axL.tick_params(axis="y", labelcolor=BLUE)
axL.set_ylim(0, 22000)
axL.set_xlim(0, 132)
axL.grid(True, alpha=0.25)

axLb = axL.twinx()
inst = ramp.dropna(subset=["install_med_ms"])          # install only during ramp
l2, = axLb.plot(inst["t_s"], inst["install_med_ms"], color=ORANGE, lw=2.0,
                ls="--", marker="o", ms=3, label="install latency (per rule)")
axLb.set_ylabel("install latency (ms)", color=ORANGE)
axLb.tick_params(axis="y", labelcolor=ORANGE)
axLb.set_ylim(0, 30)                                    # shared scale with right panel

axL.annotate("flows track sources 1:1;\nprocess undisturbed",
             xy=(30, 12000), xytext=(6, 18200), color=GREY,
             fontsize=9, arrowprops=dict(arrowstyle="->", color=GREY, lw=1))
axL.annotate("self-heal drain\n(hard_timeout expiry)",
             xy=(110, 5300), xytext=(78, 9500), color=GREEN,
             fontsize=9, arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2))
axL.legend([l1, l2], [l1.get_label(), l2.get_label()], loc="upper right",
           framealpha=0.9)

# ---------------------------------------------------------------- RIGHT panel
# saturation: flows, install latency and daemon memory, each its own curve.
axR.set_title("Saturation: 24 injectors (~2000 flows/s)")
# plot install/flows only while installs are happening (inject rate > 0); the
# zero rows after t=75 s mean 'injection stopped', not '0 ms latency'.
inj = ceil[ceil["inject_rate_s"] > 0]

r1, = axR.plot(ceil["t_s"], ceil["reactive_flows"], color=BLUE, lw=2.4,
               label="reactive flows on gateway")
axR.set_xlabel("time (s)")
axR.set_ylabel("reactive flows on gateway", color=BLUE)
axR.tick_params(axis="y", labelcolor=BLUE)
axR.set_ylim(0, 122000)          # headroom so annotations clear every curve
axR.set_xlim(0, 100)
axR.grid(True, alpha=0.25)

axRb = axR.twinx()
r2, = axRb.plot(inj["t_s"], inj["install_med_ms"], color=ORANGE, lw=2.0,
                ls="--", marker="o", ms=3, label="install latency (per rule)")
axRb.set_ylabel("install latency (ms)", color=ORANGE)
axRb.tick_params(axis="y", labelcolor=ORANGE)
axRb.set_ylim(0, 30)

axRc = axR.twinx()                                      # third axis: memory
axRc.spines["right"].set_position(("outward", 54))
r3, = axRc.plot(ceil["t_s"], ceil["vswitchd_mb"], color=GREEN, lw=1.8,
                ls=":", marker="s", ms=3, label="ovs-vswitchd memory")
axRc.set_ylabel("ovs-vswitchd memory (MB)", color=GREEN)
axRc.tick_params(axis="y", labelcolor=GREEN)
# widen the memory axis so the green curve sits in a lower band, visually
# separated from the blue flows curve (data unchanged; axis range only)
axRc.set_ylim(250, 560)

# mark the 94k saturation peak (t=75.3); the memory curve reads 393 MB there
axR.set_title("Saturation: 24 injectors (~2000 flows/s)", pad=16)
bbox = dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9)
# saturation label lifted into the top headroom, clear of every curve
axR.annotate("~94k flows: control plane saturates,\n"
             "channel to fail-secure, S7 loop stalls",
             xy=(75.3, 94118), xytext=(47, 113000), color="#8a1f1f",
             fontsize=8.5, ha="left", va="center", bbox=bbox,
             arrowprops=dict(arrowstyle="->", color="#8a1f1f", lw=1.2))
axR.annotate("self-heal drain\n94k to 0 in ~23 s",
             xy=(91, 30000), xytext=(80, 52000), color=GREEN,
             fontsize=9, bbox=bbox,
             arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2))
# memory: 393 MB at the flow peak, lingering to 425 MB through the drain
axRc.annotate("memory 393 MB at peak,\nlingers to 425 MB", xy=(75.3, 393.0),
              xytext=(43, 296), color=GREEN, fontsize=8.5, ha="left", bbox=bbox,
              arrowprops=dict(arrowstyle="->", color=GREEN, lw=1))

lines = [r1, r2, r3]
axR.legend(lines, [l.get_label() for l in lines], loc="upper left",
           framealpha=0.9)

fig.tight_layout()
fig.savefig(os.path.abspath(OUT), bbox_inches="tight")
print("wrote", os.path.abspath(OUT))
print("peak flows:", int(ceil["reactive_flows"].max()),
      "| mem@peak:", float(ceil.loc[ceil["reactive_flows"].idxmax(), "vswitchd_mb"]),
      "| mem max:", float(ceil["vswitchd_mb"].max()),
      "| install max:", float(inj["install_med_ms"].max()))
