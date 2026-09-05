"""Figure: Opus 4.5 push-back (judge CONDITIONAL) and refusal (judge REFUSE) rates on the retraining ticket
by intervention (reasoning off), one bar each per ticket with 95% Wilson intervals. Reads the judged files directly. Writes results/figures/interventions.{png,svg}.

    uv run --with matplotlib python fig_interventions.py
"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RES = Path("/home/mhieuuu/Github/safety-refusals/results")

def count(cond):
    rows = [json.loads(l) for l in (RES / f"{cond}.judged.jsonl").read_text().splitlines() if l.strip()]
    oc = [r.get("judge", {}).get("outcome") for r in rows]
    return oc.count("CONDITIONAL"), oc.count("REFUSE"), len(rows)

def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)

cells = [  # label, condition id
    ("Baseline ticket", "R_absent_off"),
    ("Details specified\n(reliability-weighted evidence,\nbalanced outcomes)", "V1_off"),
    ("Details removed\n(mechanism left vague)", "V2_off"),
    ("General research task\n(tool-call calibration)", "V7_off"),
]
data = [(lab, cond, *count(cond)) for lab, cond in cells]
for lab, cond, c, r, n in data:
    print(f"{cond:14s} push-back {c:2d}/{n:<3d} CI {'-'.join(f'{100*v:.0f}' for v in wilson(c, n))}   "
          f"refusal {r:2d}/{n:<3d} CI {'-'.join(f'{100*v:.0f}' for v in wilson(r, n))}")

# reference palette: slot 1 blue, text tokens, light surface, recessive grid
BLUE, ORANGE = "#2a78d6", "#eb6834"  # reference palette slots 1 and 2 (validated adjacent pair)
INK, INK2, SURF, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=200)
fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
ys = [3 * i for i in range(len(data))][::-1]
series = [("Push-back (concerns raised, help conditional)", BLUE, +0.5, lambda d: d[2]),
          ("Refusal (declines outright)", ORANGE, -0.5, lambda d: d[3])]
for y, d in zip(ys, data):
    n = d[4]
    for name, col, off, get in series:
        k = get(d); yy = y + off
        p = 100 * k / n; lo, hi = (100 * v for v in wilson(k, n))
        ax.barh(yy, p, height=0.86, color=col, linewidth=0, zorder=3)
        ax.plot([lo, hi], [yy, yy], color=INK2, linewidth=1.2, zorder=4)
        for x in (lo, hi):
            ax.plot([x, x], [yy - 0.2, yy + 0.2], color=INK2, linewidth=1.2, zorder=4)
        ax.text(hi + 1.8, yy, f"{k}/{n}  ({p:.0f}%)", va="center", ha="left", color=INK, fontsize=9, zorder=5)
ax.set_yticks(ys); ax.set_yticklabels([d[0] for d in data], color=INK, fontsize=9.5)
ax.set_ylim(min(ys) - 1.6, max(ys) + 1.6)
ax.set_xlim(0, 126); ax.set_xticks(range(0, 101, 25))
ax.set_xticklabels([f"{v}%" for v in range(0, 101, 25)], color=INK2, fontsize=9)
ax.set_xlabel("Share of samples, 95% Wilson interval", color=INK2, fontsize=9.5)
ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0); ax.set_axisbelow(True)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(GRID); ax.tick_params(axis="both", length=0)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=col, label=name) for name, col, _, _ in series], loc="lower right",
          frameon=False, fontsize=9, labelcolor=INK2, handlelength=1.2, handleheight=0.8)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.text(0.02, 0.97, "Opus 4.5 push-back and refusal on the Haiku retraining ticket, by intervention",
         ha="left", va="top", color=INK, fontsize=11)
for ext in ("png", "svg"):
    fig.savefig(RES / "figures" / f"interventions.{ext}", facecolor=SURF)
print("wrote", RES / "figures" / "interventions.png")
