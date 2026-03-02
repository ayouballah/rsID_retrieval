#!/usr/bin/env python3
"""Generate a single summary figure that consolidates benchmark results,
rsID recovery rates, a comparison table, per-variant timings and two Venn
diagrams produced by compare_rsid_overlap.py.

This is a throwaway utility: it discovers the latest benchmark JSON results
in a results directory and any rsid overlap outputs nearby, then renders a
publication-style PNG.

Usage:
  python generate_summary_figure.py --bench-dir benchmark_optimized_results

If no venn images are found the script will still produce the figure with
placeholders.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


def find_latest_json(folder: Path) -> Optional[Path]:
    files = sorted(folder.glob("speed_benchmark_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def find_overlap_summaries(folder: Path) -> List[Path]:
    # look for rsid_overlap_summary.json recursively
    return list(folder.rglob("rsid_overlap_summary.json"))


def load_results(json_path: Path):
    with open(json_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_venn_image(summary_json: Path) -> Optional[Path]:
    png = summary_json.parent / "rsid_overlap_venn.png"
    if png.exists():
        return png
    # fallback
    return None


def render_comparison_table(ax):
    """Render a clean, well-spaced comparison table."""
    headers = ["Feature", "RSID_Ret.", "SNPnexus", "VEP", "ANNOVAR"]
    
    # Shorter labels to prevent text overflow
    rows = [
        ["Real-time queries", "✓", "✗", "✗", "✗"],
        ["Latest build", "✓", "Ver-dep", "Ver-dep", "Ver-dep"],
        ["Merged/depr. IDs", "✓", "✗", "✗", "✗"],
        ["Coord. offset", "✓", "✗", "✗", "✗"],
        ["Variant limit", "None", "10K", "None", "None"],
        ["Local DB req.", "✗", "✗", "✓", "✓"],
        ["Install complex.", "Low", "Web", "High", "High"],
        ["Funct. annot.", "✗", "✓", "✓", "✓"],
        ["Speed", "~2/s", "Fast", "Fast", "Fast"],
    ]

    ax.axis("off")

    # Table boundaries - start directly at the top (no empty space above header)
    left = 0.02
    top = 0.98
    width = 0.96
    height = 0.90

    table_left = left
    table_right = left + width
    table_top = top
    table_bottom = top - height

    ncols = len(headers)
    nrows = len(rows) + 1

    # Column widths: slightly wider first column
    col_widths = [0.27] + [0.73 / (ncols - 1)] * (ncols - 1)

    # Header background
    header_h = 0.08
    ax.add_patch(plt.Rectangle((table_left, table_top - header_h), width, header_h, 
                                transform=ax.transAxes, color="#e8f0fe", zorder=1))

    # Draw headers
    x = table_left
    for ci, cw in enumerate(col_widths):
        ha = "left" if ci == 0 else "center"
        txt_x = x + 0.015 if ci == 0 else x + cw * width / 2
        ax.text(txt_x, table_top - header_h / 2, headers[ci], transform=ax.transAxes, 
                ha=ha, va="center", fontsize=10, fontweight="bold")
        x += cw * width

    # Draw rows - start immediately after header (no empty row)
    row_h = (height - header_h) / len(rows)
    for ri in range(len(rows)):
        y = table_top - header_h - ri * row_h
        
        # Alternating row colors for better readability
        if ri % 2 == 0:
            ax.add_patch(plt.Rectangle((table_left, y - row_h), width, row_h, 
                                      transform=ax.transAxes, color="#f8f9fa", zorder=0))
        
        # Horizontal separator
        ax.plot([table_left, table_right], [y - row_h, y - row_h], transform=ax.transAxes, 
                color="#dee2e6", linewidth=0.5, zorder=2)
        
        x = table_left
        for ci, cw in enumerate(col_widths):
            cell_text = rows[ri][ci]
            ha = "left" if ci == 0 else "center"
            txt_x = x + 0.015 if ci == 0 else x + cw * width / 2
            txt_y = y - row_h * 0.5  # center text in row
            
            if cell_text in ("✓", "✗"):
                cx = x + cw * width * 0.5
                cy = txt_y
                if cell_text == "✓":
                    # Checkmark
                    ax.plot([cx - 0.008, cx - 0.002], [cy - 0.003, cy - 0.008], 
                           transform=ax.transAxes, color="#16a34a", linewidth=2.0, solid_capstyle='round')
                    ax.plot([cx - 0.002, cx + 0.008], [cy - 0.008, cy + 0.007], 
                           transform=ax.transAxes, color="#16a34a", linewidth=2.0, solid_capstyle='round')
                else:
                    # X mark
                    ax.plot([cx - 0.007, cx + 0.007], [cy - 0.007, cy + 0.007], 
                           transform=ax.transAxes, color="#dc2626", linewidth=2.0, solid_capstyle='round')
                    ax.plot([cx - 0.007, cx + 0.007], [cy + 0.007, cy - 0.007], 
                           transform=ax.transAxes, color="#dc2626", linewidth=2.0, solid_capstyle='round')
            else:
                ax.text(txt_x, txt_y, cell_text, transform=ax.transAxes, 
                       ha=ha, va="center", fontsize=9)
            x += cw * width

    # Outer border
    border_color = "#adb5bd"
    ax.plot([table_left, table_right, table_right, table_left, table_left], 
            [table_top, table_top, table_bottom, table_bottom, table_top], 
            transform=ax.transAxes, color=border_color, linewidth=1.2, zorder=3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate consolidated benchmark summary figure")
    parser.add_argument("--bench-dir", type=Path, default=Path("benchmark_optimized_results"))
    parser.add_argument("--out", type=Path, default=Path("benchmark_optimized_results/speed_benchmark_summary.png"))
    args = parser.parse_args()

    bench_dir = args.bench_dir
    latest = find_latest_json(bench_dir)
    if not latest:
        raise SystemExit(f"No benchmark JSON files found in {bench_dir}")

    results = load_results(latest)

    # Prepare arrays
    labels = [r.get("name") for r in results]
    durations = [r.get("duration_seconds", 0.0) for r in results]
    rates = [r.get("annotation_rate", 0.0) for r in results]
    t_per_var = [r.get("time_per_variant", 0.0) for r in results]
    totals = [r.get("total_variants", 0) for r in results]

    # find up to two venn images
    overlap_jsons = find_overlap_summaries(bench_dir)
    venn_paths: List[Optional[Path]] = []
    for sj in overlap_jsons[:2]:
        png = load_venn_image(sj)
        venn_paths.append(png)

    plt.style.use("seaborn-v0_8")
    plt.rcParams.update(
        {
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.titlesize": 13,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 9,
        }
    )

    palette = {
        "runtime": "#2563eb",
        "variants": "#f97316",
        "rate": "#16a34a",
        "efficiency": "#7c3aed",
        "baseline": "#94a3b8",
    }

    # Standard scientific figure: wider than tall, reasonable aspect ratio
    fig = plt.figure(figsize=(20, 10), dpi=150)
    
    # Simple 2x3 grid with equal spacing
    gs = gridspec.GridSpec(
        2, 3,
        figure=fig,
        height_ratios=[1.0, 1.0],
        width_ratios=[1.1, 1.1, 1.1],  # Equal width for all columns
        hspace=0.30,
        wspace=0.25,
    )

    # Top row: A (Runtime) | B (Rate) | C (Per-variant)
    ax_runtime = fig.add_subplot(gs[0, 0])
    ax_rate = fig.add_subplot(gs[0, 1])
    ax_tpv = fig.add_subplot(gs[0, 2])

    # Bottom row: D (Table) | E (Venn1) | F (Venn2)
    ax_table = fig.add_subplot(gs[1, 0])
    ax_venn1 = fig.add_subplot(gs[1, 1])
    ax_venn2 = fig.add_subplot(gs[1, 2])

    # Sort results by total_variants
    ordered_idx = sorted(range(len(labels)), key=lambda i: totals[i])
    ordered_labels = [labels[i] for i in ordered_idx]
    ordered_durations = [durations[i] for i in ordered_idx]
    ordered_rates = [rates[i] for i in ordered_idx]
    ordered_tpv = [t_per_var[i] for i in ordered_idx]
    ordered_totals = [totals[i] for i in ordered_idx]

    dataset_display = [f"Set {i + 1}" for i in range(len(ordered_labels))]

    # A - Runtime horizontal bar
    y_pos = list(range(len(ordered_labels)))
    ax_runtime.barh(y_pos, ordered_durations, color=palette["runtime"], alpha=0.90, height=0.65)
    ax_runtime.set_yticks(y_pos)
    runtime_labels = [f"{d}\n• {cnt:,} variants" for d, cnt in zip(dataset_display, ordered_totals)]
    ax_runtime.set_yticklabels(runtime_labels, fontsize=9)
    ax_runtime.invert_yaxis()
    ax_runtime.set_xlabel("Processing Time (s)", fontsize=11)
    ax_runtime.set_title("Runtime by Dataset", fontsize=13, pad=10)
    ax_runtime.set_xlim(0, max(ordered_durations) * 1.12)
    ax_runtime.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)

    avg_duration = sum(ordered_durations) / max(1, len(ordered_durations))
    ax_runtime.axvline(avg_duration, color=palette["baseline"], linestyle="--", linewidth=1.2, alpha=0.7)
    # Place "Avg" label next to Set 2 (y position = 1 after invert)
    ax_runtime.text(avg_duration + max(ordered_durations) * 0.01, 1, "Avg", 
                   color=palette["baseline"], fontsize=9, va="center", ha="left")

    for y, val in zip(y_pos, ordered_durations):
        ax_runtime.text(val + max(ordered_durations) * 0.01, y, f"{val:.1f}s", 
                       va="center", fontsize=9, fontweight='bold')

    # B - rsID Recovery Rate
    ax_rate.plot(dataset_display, ordered_rates, color=palette["rate"], marker="o", 
                markersize=8, linewidth=2.5, markeredgewidth=0)
    ax_rate.fill_between(range(len(dataset_display)), ordered_rates, 
                         color=palette["rate"], alpha=0.15)
    ax_rate.set_ylim(0, 105)
    ax_rate.set_ylabel("rsID Recovery (%)", fontsize=11)
    ax_rate.set_title("rsID Recovery Rate", fontsize=13, pad=10)
    ax_rate.set_xticks(range(len(dataset_display)))
    ax_rate.set_xticklabels(dataset_display)
    ax_rate.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    
    avg_rate = sum(ordered_rates) / max(1, len(ordered_rates))
    ax_rate.axhline(avg_rate, color=palette["baseline"], linestyle="--", linewidth=1.2, alpha=0.7)
    ax_rate.text(0.98, avg_rate, " Avg", transform=ax_rate.get_yaxis_transform(), 
                ha="left", va="center", color=palette["baseline"], fontsize=9)

    # C - Comparison table
    render_comparison_table(ax_table)
    ax_table.set_title("Tool comparison", fontsize=13, pad=10)

    # D - Per-variant processing time
    bars = ax_tpv.bar(dataset_display, ordered_tpv, color=palette["efficiency"], 
                     alpha=0.85, width=0.6)
    ax_tpv.set_ylabel("Seconds per variant", fontsize=11)
    ax_tpv.set_title("Per-variant processing time", fontsize=13, pad=10)
    ax_tpv.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    
    avg_tpv = sum(ordered_tpv) / max(1, len(ordered_tpv))
    ax_tpv.axhline(avg_tpv, color=palette["baseline"], linestyle="--", linewidth=1.2, alpha=0.7)
    ax_tpv.text(0.98, avg_tpv, " Avg", transform=ax_tpv.get_yaxis_transform(), 
               ha="left", va="center", color=palette["baseline"], fontsize=9)
    
    try:
        max_tpv = max(ordered_tpv)
        ax_tpv.set_ylim(0, max_tpv * 1.25 if max_tpv > 0 else 1)
    except Exception:
        pass

    # Handle Venn diagrams
    # E: ClinVar original rsIDs vs rsID_retrieval output
    venn_e = Path(r"C:\Users\ayoub\Documents\GitHub\rsID_retrieval\benchmark_speed_results\rsid_overlap_venn.png")
    # F: SNPnexus v5 vs rsID_retrieval output (newly generated)
    venn_f = bench_dir / "rsid_overlap_venn.png"
    # Fallback: scan for any venn in bench_dir if explicit not found
    if not venn_f.exists() and venn_paths:
        venn_f = venn_paths[0] or venn_f

    venn_slots = [
        venn_e if venn_e.exists() else None,
        venn_f if venn_f.exists() else None,
    ]

    # E & F - Venn diagrams (stretch horizontally to fill the subplot)
    venn_titles = [
        "Comparing ClinVar entries to rsID_retrieval output",
        "Comparing SNP-nexus output to rsID_retrieval's"
    ]
    for ax, vp, vtitle in zip([ax_venn1, ax_venn2], venn_slots, venn_titles):
        ax.axis("off")
        if vp is not None and vp.exists():
            try:
                img = plt.imread(vp)
                # Stretch wider to fill axis better
                ax.imshow(img, aspect='auto', extent=[-0.15, 1.15, -0.05, 1.05])
                ax.set_xlim(-0.15, 1.15)
                ax.set_ylim(-0.05, 1.05)
                ax.set_title(vtitle, fontsize=11, pad=8)
            except Exception as e:
                ax.text(0.5, 0.5, f"(unable to load image:\n{str(e)[:30]}...)", 
                       ha="center", va="center", transform=ax.transAxes, fontsize=9)
        else:
            ax.text(0.5, 0.5, "(no venn image found)", 
                   ha="center", va="center", transform=ax.transAxes, fontsize=10, color='gray')

    # Add subplot labels A-F
    all_axes = [ax_runtime, ax_rate, ax_tpv, ax_table, ax_venn1, ax_venn2]
    for i, ax in enumerate(all_axes):
        letter = chr(65 + i)
        ax.text(-0.10, 1.08, letter, transform=ax.transAxes, 
               fontsize=16, fontweight="bold", va='top')

    title = f"rsID_retrieval Summary — Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    fig.suptitle(title, fontsize=15, weight="bold", y=0.98)

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")  # Reduced DPI for reasonable file size
    plt.close(fig)
    print(f"Saved summary figure to: {out}")


if __name__ == "__main__":
    main()
