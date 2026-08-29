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
ax.text(6, 33, "0.026 ms expanded", ha="left", va="center", fontsize=8.5, color=GRY_E)
# dashed container = the timed window
ax.add_patch(FancyBboxPatch((4, 14), 95, 16, boxstyle="round,pad=0.2,rounding_size=1.2",
                            fc="none", ec=GRY_E, lw=0.7, linestyle=(0,(4,3))))
steps = [("1 classify", "role × op → tier"), ("2 elevate", "SENSITIVE → FORBID"),
         ("3 rate/state", "rate → flood flag"), ("4 select", "tier → response"),
         ("5 timeout", "weight → 30+15w s"), ("6 enforce", "rule → switch")]
w, gap, x0 = 13.2, 2.5, 6.0
xs = [x0 + i*(w+gap) for i in range(6)]
for x, (t, s) in zip(xs, steps):
    ax.add_patch(FancyBboxPatch((x, 16), w, 12, boxstyle="round,pad=0.2,rounding_size=1.0",
                                fc=TEAL_F, ec=TEAL_E, lw=1.0))
    ax.text(x + w/2, 25, t, ha="center", va="center", fontsize=8, color=TEAL_T, weight="medium")
    ax.text(x + w/2, 19, s, ha="center", va="center", fontsize=6.6, color=TEAL_T)
for i in range(5):
    arrow(xs[i] + w, xs[i+1], 22)
# audit + console log: OUTSIDE the timed window
ax.add_patch(FancyBboxPatch((70, 1), 29, 10, boxstyle="round,pad=0.2,rounding_size=1.0",
                            fc=GRY_F, ec=GRY_E, lw=0.9))
ax.text(84.5, 7.3, "audit + console log", ha="center", va="center", fontsize=7.5, color=GRY_T, weight="medium")
ax.text(84.5, 3.6, "after the timer", ha="center", va="center", fontsize=6.6, color=GRY_E)
ax.annotate("", xy=(85.5, 11), xytext=(91.1, 16), arrowprops=dict(arrowstyle="-|>", color=GRY_E, lw=1.2))

fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
fig.savefig("fig_reaction_window.png", dpi=200, bbox_inches="tight", facecolor="white")
print("wrote fig_reaction_window.png")
