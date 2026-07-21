"""
visualize_stats.py — Visual statistics for the SHAP anomaly detection pipeline.

Generates a dashboard of plots from a CSV of network flows:
  1. Anomaly score distribution histogram
  2. Risk score distribution
  3. Attack type classification breakdown (pie chart)
  4. SHAP feature importance (mean |SHAP| bar chart)
  5. Top-N contributing features (horizontal bar)
  6. SHAP waterfall for worst anomalous flow
  7. Feature importance heatmap across flagged flows
  8. Feature category importance breakdown

Usage:
    python detection/visualize_stats.py <csv_path> [--threshold 0.5] [--top-n 20] [--out-dir detection/plots]
"""

import argparse
import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from detection.shap_explainer import (
    SHAPExplainer, FEATURE_NAMES, load_background,
    load_attack_mapper, guess_attack_type,
)

COLORS = {
    "primary": "#2196F3",
    "danger": "#F44336",
    "warning": "#FF9800",
    "success": "#4CAF50",
    "bg": "#1a1a2e",
    "card": "#16213e",
    "text": "#e0e0e0",
    "grid": "#333355",
}

CATEGORY_COLORS = {
    "timing": "#2196F3",
    "volume": "#FF9800",
    "packet_size": "#F44336",
    "header": "#9C27B0",
    "flags": "#4CAF50",
    "ratio": "#00BCD4",
    "window": "#FFEB3B",
    "burst": "#E91E63",
    "segment": "#795548",
    "payload": "#607D8B",
    "subflow": "#3F51B5",
}


def load_csv_data(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    drop_cols = [
        "Label", "Flow ID", "Source IP", "Destination IP", "Timestamp",
        "src_ip", "dst_ip", "src_port", "dst_port", "protocol", "timestamp",
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    df = df.replace([float("inf"), float("-inf")], float("nan"))
    df = df.dropna(axis=1)
    df = df.select_dtypes(include=[float, int])
    if df.shape[1] != 76:
        raise ValueError(f"Expected 76 features, got {df.shape[1]}")
    scaler = MinMaxScaler()
    data = scaler.fit_transform(df)
    return data, df.columns.tolist()


def setup_style():
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": COLORS["card"],
        "axes.edgecolor": COLORS["grid"],
        "axes.labelcolor": COLORS["text"],
        "xtick.color": COLORS["text"],
        "ytick.color": COLORS["text"],
        "text.color": COLORS["text"],
        "grid.color": COLORS["grid"],
        "grid.alpha": 0.3,
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
    })


def plot_anomaly_distribution(scores, threshold, out_dir):
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.linspace(0, 1, 50)
    ax.hist(scores, bins=bins, color=COLORS["primary"], alpha=0.7, edgecolor="white", linewidth=0.3)
    ax.axvline(threshold, color=COLORS["danger"], linewidth=2, linestyle="--", label=f"Threshold = {threshold}")
    flagged = (scores > threshold).sum()
    total = len(scores)
    ax.set_title(f"Anomaly Score Distribution  ({flagged}/{total} flagged, {100*flagged/total:.1f}%)")
    ax.set_xlabel("Anomaly Score (MSE)")
    ax.set_ylabel("Flow Count")
    ax.legend()
    ax.grid(True, axis="y")
    plt.tight_layout()
    path = os.path.join(out_dir, "01_anomaly_distribution.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_risk_distribution(risk_scores, out_dir):
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = np.arange(0, 105, 5)
    colors = []
    for b in bins[:-1]:
        if b < 30:
            colors.append(COLORS["success"])
        elif b < 70:
            colors.append(COLORS["warning"])
        else:
            colors.append(COLORS["danger"])
    ax.hist(risk_scores, bins=bins, color=COLORS["primary"], alpha=0.7, edgecolor="white", linewidth=0.3)
    ax.axvspan(0, 30, alpha=0.08, color=COLORS["success"], label="Low Risk")
    ax.axvspan(30, 70, alpha=0.08, color=COLORS["warning"], label="Medium Risk")
    ax.axvspan(70, 100, alpha=0.08, color=COLORS["danger"], label="High Risk")
    ax.set_title("Risk Score Distribution")
    ax.set_xlabel("Risk Score (0-100)")
    ax.set_ylabel("Flow Count")
    ax.legend()
    ax.grid(True, axis="y")
    plt.tight_layout()
    path = os.path.join(out_dir, "02_risk_distribution.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_attack_breakdown(attack_types, out_dir):
    counts = {}
    for a in attack_types:
        counts[a] = counts.get(a, 0) + 1
    labels = list(counts.keys())
    values = list(counts.values())
    cmap = plt.cm.Set3
    pie_colors = [cmap(i / max(len(labels), 1)) for i in range(len(labels))]
    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, autopct="%1.1f%%",
        colors=pie_colors, startangle=140, pctdistance=0.8,
        textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax.set_title("Attack Type Classification Breakdown")
    plt.tight_layout()
    path = os.path.join(out_dir, "03_attack_breakdown.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_shap_bar(shap_matrix, out_dir, top_n=20):
    mean_abs = np.mean(np.abs(shap_matrix), axis=0)
    top_idx = np.argsort(mean_abs)[::-1][:top_n]
    names = [FEATURE_NAMES[i] for i in top_idx]
    vals = mean_abs[top_idx]
    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(range(len(names)), vals, color=COLORS["primary"], alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(f"Top {top_n} Features by Mean |SHAP Value|")
    ax.set_xlabel("Mean |SHAP|")
    ax.grid(True, axis="x")
    for bar, val in zip(bars, vals):
        ax.text(bar.get_width() + max(vals) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.4f}", va="center", fontsize=8, color=COLORS["text"])
    plt.tight_layout()
    path = os.path.join(out_dir, "04_shap_feature_importance.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_top_features_horizontal(top_features_list, out_dir, top_n=15):
    feat_totals = {}
    feat_counts = {}
    for flow_tops in top_features_list:
        for feat in flow_tops:
            name = feat["feature"]
            feat_totals[name] = feat_totals.get(name, 0) + abs(feat["shap_value"])
            feat_counts[name] = feat_counts.get(name, 0) + 1
    merged = sorted(feat_totals.keys(), key=lambda k: feat_totals[k], reverse=True)[:top_n]
    vals = [feat_totals[k] for k in merged]
    counts = [feat_counts[k] for k in merged]
    fig, ax = plt.subplots(figsize=(10, 7))
    colors_bar = [COLORS["danger"] if c > len(top_features_list) * 0.3 else COLORS["primary"] for c in counts]
    bars = ax.barh(range(len(merged)), vals, color=colors_bar, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.set_yticks(range(len(merged)))
    ax.set_yticklabels(merged, fontsize=9)
    ax.invert_yaxis()
    ax.set_title(f"Top {top_n} Most Frequently Anomalous Features")
    ax.set_xlabel("Cumulative |SHAP|")
    ax.grid(True, axis="x")
    for bar, val, c in zip(bars, vals, counts):
        ax.text(bar.get_width() + max(vals) * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f} (n={c})", va="center", fontsize=8, color=COLORS["text"])
    plt.tight_layout()
    path = os.path.join(out_dir, "05_top_anomalous_features.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_shap_waterfall(sv, feature_vector, out_dir, idx=0):
    ranked = np.argsort(np.abs(sv))[::-1][:15]
    names = [FEATURE_NAMES[i] for i in ranked]
    vals = [sv[i] for i in ranked]
    inputs = [feature_vector[i] for i in ranked]
    colors_bar = [COLORS["danger"] if v > 0 else COLORS["success"] for v in vals]
    fig, ax = plt.subplots(figsize=(10, 7))
    y_pos = range(len(names))
    ax.barh(y_pos, vals, color=colors_bar, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{n} ({inputs[i]:.3f})" for i, n in enumerate(names)], fontsize=8)
    ax.invert_yaxis()
    ax.axvline(0, color=COLORS["text"], linewidth=0.8, linestyle="-")
    ax.set_title(f"SHAP Waterfall — Flow #{idx} (Top 15 Features)")
    ax.set_xlabel("SHAP Value (increases / decreases anomaly)")
    ax.grid(True, axis="x")
    plt.tight_layout()
    path = os.path.join(out_dir, f"06_shap_waterfall_flow{idx}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_feature_heatmap(shap_matrix, flagged_indices, out_dir, top_n=25):
    mean_abs = np.mean(np.abs(shap_matrix), axis=0)
    top_feat_idx = np.argsort(mean_abs)[::-1][:top_n]
    subset = shap_matrix[:, top_feat_idx]
    names = [FEATURE_NAMES[i] for i in top_feat_idx]
    fig, ax = plt.subplots(figsize=(14, max(6, len(flagged_indices) * 0.4 + 2)))
    im = ax.imshow(subset, aspect="auto", cmap="RdBu_r", vmin=-np.max(np.abs(subset)), vmax=np.max(np.abs(subset)))
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(flagged_indices)))
    ax.set_yticklabels([f"Flow #{i}" for i in flagged_indices], fontsize=8)
    ax.set_title(f"SHAP Values Heatmap — Top {top_n} Features Across Flagged Flows")
    fig.colorbar(im, ax=ax, label="SHAP Value", shrink=0.8)
    plt.tight_layout()
    path = os.path.join(out_dir, "07_shap_heatmap.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_category_breakdown(shap_matrix, out_dir):
    mapper = load_attack_mapper()
    cat_to_feats = {}
    if mapper:
        for fname, cat in mapper.get("feature_to_category", {}).items():
            cat_to_feats.setdefault(cat, []).append(fname)
    mean_abs = np.mean(np.abs(shap_matrix), axis=0)
    cat_shap = {}
    for cat, feats in cat_to_feats.items():
        indices = [FEATURE_NAMES.index(f) for f in feats if f in FEATURE_NAMES]
        if indices:
            cat_shap[cat] = float(np.mean(mean_abs[indices]))
    if not cat_shap:
        print("  Skipping category breakdown (no mapper data)")
        return
    cats = sorted(cat_shap.keys(), key=lambda k: cat_shap[k], reverse=True)
    vals = [cat_shap[c] for c in cats]
    bar_colors = [CATEGORY_COLORS.get(c, "#888888") for c in cats]
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(cats)), vals, color=bar_colors, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=30, ha="right", fontsize=10)
    ax.set_title("Mean |SHAP| by Feature Category")
    ax.set_ylabel("Mean |SHAP|")
    ax.grid(True, axis="y")
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.01,
                f"{val:.4f}", ha="center", fontsize=9, color=COLORS["text"])
    plt.tight_layout()
    path = os.path.join(out_dir, "08_category_breakdown.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_score_scatter(scores, shap_matrix, flagged_idx, flagged_scores, out_dir):
    mean_abs = np.mean(np.abs(shap_matrix), axis=1)
    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(flagged_scores, mean_abs, c=flagged_scores, cmap="RdYlGn_r", alpha=0.6, s=20, edgecolors="white", linewidth=0.3)
    ax.set_xlabel("Anomaly Score")
    ax.set_ylabel("Mean |SHAP| per Flow")
    ax.set_title(f"Anomaly Score vs SHAP Intensity (colored by score)")
    fig.colorbar(scatter, ax=ax, label="Anomaly Score")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "09_score_vs_shap_intensity.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_summary_dashboard(scores, risk_scores, attack_types, flagged_count, total, out_dir):
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor(COLORS["bg"])
    gs = gridspec.GridSpec(2, 3, hspace=0.35, wspace=0.3)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[0, 2])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2])
    for ax in [ax1, ax2, ax3, ax4, ax5, ax6]:
        ax.set_facecolor(COLORS["card"])
        ax.tick_params(colors=COLORS["text"])
        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])
    ax1.hist(scores, bins=40, color=COLORS["primary"], alpha=0.7, edgecolor="white", linewidth=0.3)
    ax1.axvline(0.5, color=COLORS["danger"], linewidth=2, linestyle="--")
    ax1.set_title("Anomaly Scores")
    ax1.set_xlabel("Score")
    ax1.set_ylabel("Count")
    ax2.hist(risk_scores, bins=20, color=COLORS["warning"], alpha=0.7, edgecolor="white", linewidth=0.3)
    ax2.set_title("Risk Scores")
    ax2.set_xlabel("Risk (0-100)")
    ax3.bar(["Normal", "Anomaly"], [total - flagged_count, flagged_count],
            color=[COLORS["success"], COLORS["danger"]], alpha=0.8, edgecolor="white", linewidth=0.3)
    ax3.set_title("Classification")
    ax3.set_ylabel("Count")
    counts = {}
    for a in attack_types:
        counts[a] = counts.get(a, 0) + 1
    top3 = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
    if top3:
        labels, vals = zip(*top3)
        ax4.barh(range(len(labels)), vals, color=COLORS["primary"], alpha=0.8, edgecolor="white", linewidth=0.3)
        ax4.set_yticks(range(len(labels)))
        ax4.set_yticklabels(labels, fontsize=8)
        ax4.invert_yaxis()
    ax4.set_title("Top Attack Types")
    ax5.text(0.5, 0.5, f"{total}\nTotal Flows\n\n{flagged_count}\nFlagged\n\n{100*flagged_count/total:.1f}%\nAnomaly Rate",
             ha="center", va="center", fontsize=16, color=COLORS["text"],
             transform=ax5.transAxes, bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS["card"], edgecolor=COLORS["grid"]))
    ax5.set_xlim(0, 1)
    ax5.set_ylim(0, 1)
    ax5.axis("off")
    ax5.set_title("Summary Stats")
    ax6.text(0.5, 0.5, "Zero-Day Detection\nPipeline Dashboard\n\nSHAP + Autoencoder",
             ha="center", va="center", fontsize=14, color=COLORS["text"],
             transform=ax6.transAxes, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS["card"], edgecolor=COLORS["grid"]))
    ax6.set_xlim(0, 1)
    ax6.set_ylim(0, 1)
    ax6.axis("off")
    fig.suptitle("Anomaly Detection Dashboard", fontsize=18, fontweight="bold", color=COLORS["text"], y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    path = os.path.join(out_dir, "00_dashboard_summary.png")
    fig.savefig(path, dpi=150, facecolor=COLORS["bg"])
    plt.close(fig)
    print(f"  Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Visual statistics for SHAP anomaly detection")
    parser.add_argument("csv", help="CSV of network flows")
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--n-background", type=int, default=200)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--out-dir", type=str, default="detection/plots")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    setup_style()

    print(f"Loading data from {args.csv}...")
    data, col_names = load_csv_data(args.csv)
    total = len(data)
    print(f"  Loaded {total} flows x {data.shape[1]} features")

    print("Loading SHAP explainer...")
    bg = load_background(args.csv, n=args.n_background)
    explainer = SHAPExplainer(background=bg)

    print("Computing anomaly scores...")
    scores = explainer.anomaly_score(data)
    risk_scores = np.clip((scores * 100).astype(int), 0, 100)
    flagged_mask = scores > args.threshold
    flagged_idx = np.where(flagged_mask)[0]
    flagged_count = len(flagged_idx)
    print(f"  Flagged: {flagged_count}/{total} ({100*flagged_count/total:.1f}%)")

    print("Computing SHAP values for flagged flows...")
    if flagged_count > 0:
        flagged_data = data[flagged_idx]
        shap_matrix = explainer.shap_values(flagged_data)
        if shap_matrix.ndim == 3:
            shap_matrix = shap_matrix[0]
    else:
        print("  No flagged flows — using top score instead")
        worst = np.argmax(scores)
        shap_matrix = explainer.shap_values(data[worst:worst+1])
        if shap_matrix.ndim == 3:
            shap_matrix = shap_matrix[0]
        flagged_idx = np.array([worst])
        flagged_count = 1

    print("Classifying attack types...")
    attack_types = []
    top_features_per_flow = []
    for i, fidx in enumerate(flagged_idx):
        sv = shap_matrix[i] if shap_matrix.ndim == 2 else shap_matrix
        atype, _, _ = guess_attack_type(sv, FEATURE_NAMES, top_k=5)
        attack_types.append(atype)
        ranked = np.argsort(np.abs(sv))[::-1][:10]
        flow_tops = [{"feature": FEATURE_NAMES[j], "shap_value": float(sv[j]), "input_value": float(data[fidx, j])} for j in ranked]
        top_features_per_flow.append(flow_tops)

    print("\nGenerating plots...")
    plot_anomaly_distribution(scores, args.threshold, args.out_dir)
    plot_risk_distribution(risk_scores, args.out_dir)
    plot_attack_breakdown(attack_types, args.out_dir)
    plot_shap_bar(shap_matrix, args.out_dir, top_n=args.top_n)
    plot_top_features_horizontal(top_features_per_flow, args.out_dir, top_n=15)
    plot_shap_waterfall(shap_matrix[0], data[flagged_idx[0]], args.out_dir, idx=flagged_idx[0])
    plot_feature_heatmap(shap_matrix, flagged_idx, args.out_dir, top_n=min(25, flagged_count))
    plot_category_breakdown(shap_matrix, args.out_dir)
    flagged_scores = scores[flagged_idx]
    plot_score_scatter(scores, shap_matrix, flagged_idx, flagged_scores, args.out_dir)
    plot_summary_dashboard(scores, risk_scores, attack_types, flagged_count, total, args.out_dir)

    print(f"\nAll plots saved to {args.out_dir}/")
    print(f"Total: {len(os.listdir(args.out_dir))} PNG files generated")


if __name__ == "__main__":
    main()
