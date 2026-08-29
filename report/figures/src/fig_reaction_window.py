#!/usr/bin/env python3
"""Figure: anatomy of the 7.6 ms reaction window (Section 4.6).
Honest split: only the controller decision (0.026 ms) and the total window
(median 7.6 ms) are separately measured; the ~7.57 ms remainder is the aggregate
detection-and-transport plumbing, not timed per stage. Renders fig_reaction_window.png."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

TEAL_F, TEAL_E, TEAL_T = "#E1F5EE", "#0F6E56", "#04342C"   # measured decision
GRY_F,  GRY_E,  GRY_T  = "#F1EFE8", "#5F5E5A", "#2C2C2A"   # plumbing / neutral

fig, ax = plt.subplots(figsize=(9.2, 4.7))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

def box(x, w, y, h, fill, edge, title, sub, tcol, tsize=11, ssize=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.4",
                                fc=fill, ec=edge, lw=1.2))
    cx = x + w/2
    ax.text(cx, y + h*0.62, title, ha="center", va="center", fontsize=tsize, color=tcol, weight="medium")
    if sub:
        ax.text(cx, y + h*0.26, sub, ha="center", va="center", fontsize=ssize, color=tcol)

def arrow(x1, x2, y):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=GRY_E, lw=1.3))

# --- Row A: stage flow ---
yA, hA = 70, 15
box(6,  20, yA, hA, GRY_F, GRY_E, "Snort DPI", "reads mirror", GRY_T)
box(30, 20, yA, hA, GRY_F, GRY_E, "Bridge", "tail + POST", GRY_T)
box(54, 20, yA, hA, TEAL_F, TEAL_E, "Controller", "0.026 ms", TEAL_T)
box(78, 20, yA, hA, GRY_F, GRY_E, "Install", "rule live", GRY_T)
for x1, x2 in [(26,30),(50,54),(74,78)]:
    arrow(x1, x2, yA + hA/2)
ax.text(16, 90, "t = 0\nattack frame on wire", ha="center", va="center", fontsize=8.5, color=GRY_E)
ax.text(88, 90, "t $\\approx$ 7.6 ms\ndrop rule installed", ha="center", va="center", fontsize=8.5, color=GRY_E)

# --- Row B: proportional bar ---
yB, hB = 44, 10
ax.add_patch(Rectangle((6, yB), 91.4, hB, fc=GRY_F, ec=GRY_E, lw=1.0))
ax.text(51.7, yB + hB/2, "detection + transport plumbing    $\\approx$ 7.57 ms   (99.7%)",
        ha="center", va="center", fontsize=9.5, color=GRY_T)
ax.add_patch(Rectangle((97.4, yB), 0.6, hB, fc=TEAL_E, ec=TEAL_E, lw=0.8))
ax.annotate("decision\n0.026 ms  (0.3%)", xy=(97.7, yB+hB), xytext=(88, 64),
            ha="center", va="center", fontsize=8.5, color=TEAL_T,
            arrowprops=dict(arrowstyle="-", color=TEAL_E, lw=0.8))
ax.text(6, yB-3.5, "0 ms", ha="left", va="top", fontsize=8.5, color=GRY_E)
ax.text(97.4, yB-3.5, "7.6 ms (median)", ha="right", va="top", fontsize=8.5, color=GRY_E)

# --- Row C: the decision, expanded ---
ax.text(6, 33, "the 0.026 ms, expanded", ha="left", va="center", fontsize=8.5, color=GRY_E)
ax.add_patch(FancyBboxPatch((6, 13), 89, 15, boxstyle="round,pad=0.2,rounding_size=1.2",
                            fc="none", ec=GRY_E, lw=0.7, linestyle=(0,(4,3))))
labels = ["classify", "elevate tier", "select response", "send flow-mod"]
xs = [8, 30.5, 53, 75.5]; w = 19.5
for x, lab in zip(xs, labels):
    ax.add_patch(FancyBboxPatch((x, 16.5), w, 9, boxstyle="round,pad=0.2,rounding_size=1.0",
                                fc=TEAL_F, ec=TEAL_E, lw=1.0))
    ax.text(x + w/2, 21, lab, ha="center", va="center", fontsize=9, color=TEAL_T)
for x1, x2 in [(27.5,30.5),(50,53),(72.5,75.5)]:
    arrow(x1, x2, 21)

fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
fig.savefig("fig_reaction_window.png", dpi=200, bbox_inches="tight", facecolor="white")
print("wrote fig_reaction_window.png")
