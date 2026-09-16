"""Generate Fig 2.1 (host-graph construction) and Fig 2.2 (node-to-edge
projection) for docs/report. Run: python make_figures.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import os

OUT = r"C:\Users\trex2\Potential-Gold\Zero-Day\docs\report\figures"
os.makedirs(OUT, exist_ok=True)

INK = "#1a1a1a"
ACCENT = "#0b5394"
LIGHT = "#e8eef4"
GREY = "#5a5a5a"


def box(ax, xy, w, h, text, fontsize=8, fill="white", edge=INK, style=None):
    b = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02",
                       facecolor=fill, edgecolor=edge, linewidth=1.2)
    ax.add_patch(b)
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=INK, style=style or "normal",
            wrap=True)


def arrow(ax, a, b):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12,
                                linewidth=1.2, color=INK, shrinkA=2, shrinkB=4))


def fig21():
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    # stage boxes
    box(ax, (0.2, 2.0), 1.8, 1.2, "Flows\n(CSV rows)", fontsize=8, fill=LIGHT)
    arrow(ax, (2.0, 2.6), (2.5, 2.6))
    box(ax, (2.5, 2.0), 1.8, 1.2, "60 s / 300 s\ntime windows", fontsize=8,
        fill=LIGHT)
    arrow(ax, (4.3, 2.6), (4.8, 2.6))
    # graph sketch panel
    ax.add_patch(FancyBboxPatch((4.8, 0.6), 2.4, 3.2,
                                boxstyle="round,pad=0.02", facecolor="white",
                                edgecolor=INK, linewidth=1.2))
    ax.text(6.0, 3.55, "host graph", ha="center", fontsize=8, color=GREY)
    # scanner fan-out: one node -> many
    pos = {"s": (5.4, 2.2), "a": (6.4, 3.1), "b": (6.6, 2.5),
           "c": (6.6, 1.9), "d": (6.4, 1.3)}
    for a, b in [("s", "a"), ("s", "b"), ("s", "c"), ("s", "d")]:
        ax.annotate("", xy=pos[b], xytext=pos[a],
                    arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.2))
    for k, (x, y) in pos.items():
        ax.add_patch(Circle((x, y), 0.13, facecolor=ACCENT if k == "s"
                            else "white", edgecolor=ACCENT, linewidth=1.4))
    ax.text(5.4, 1.85, "scan", ha="center", fontsize=7, color=ACCENT)
    arrow(ax, (7.2, 2.6), (7.7, 2.6))
    box(ax, (7.7, 2.0), 2.1, 1.2, "GraphSAGE AE\n+ LogScaler", fontsize=8,
        fill=LIGHT)
    # labels under arrows
    ax.text(2.25, 2.35, "cut", ha="center", fontsize=7, color=GREY)
    ax.text(4.55, 2.35, "build", ha="center", fontsize=7, color=GREY)
    ax.text(7.45, 2.35, "score", ha="center", fontsize=7, color=GREY)
    ax.text(6.0, 0.85, "nodes = hosts, edges = flows", ha="center",
            fontsize=7, color=GREY)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig21_host_graph.png", dpi=150)
    plt.close(fig)


def fig22():
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    box(ax, (0.2, 2.9), 2.2, 1.2, "source-host\nanomaly score", fontsize=8,
        fill=LIGHT)
    box(ax, (0.2, 1.2), 2.2, 1.2, "edge reconstruction\nerror", fontsize=8,
        fill=LIGHT)
    arrow(ax, (2.4, 3.5), (3.4, 2.6))
    arrow(ax, (2.4, 1.8), (3.4, 2.6))
    box(ax, (3.4, 1.9), 2.4, 1.4, "rank_mean fusion\n(rank jointly)", fontsize=8,
        fill=LIGHT, edge=ACCENT)
    arrow(ax, (5.8, 2.6), (6.4, 2.6))
    # alert list
    ax.add_patch(FancyBboxPatch((6.4, 0.8), 3.4, 3.4,
                                boxstyle="round,pad=0.02", facecolor="white",
                                edgecolor=INK, linewidth=1.2))
    ax.text(8.1, 3.95, "ScoredAlert queue", ha="center", fontsize=8,
            color=GREY)
    rows = ["1. 10.0.0.5 → 10.0.0.9   0.99",
            "2. 10.0.0.5 → 10.0.0.12 0.97",
            "3. 10.0.0.2 → 10.0.0.9   0.61",
            "…"]
    for i, r in enumerate(rows):
        ax.text(8.1, 3.45 - i * 0.45, r, ha="center", fontsize=7.5,
                color=ACCENT if i == 0 else INK,
                fontweight="bold" if i == 0 else "normal")
    ax.text(8.1, 1.15, "src_ip, dst_ip, score, rank", ha="center",
            fontsize=7, color=GREY)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig22_edge_projection.png", dpi=150)
    plt.close(fig)


fig21()
fig22()
print("wrote", sorted(os.listdir(OUT)))
