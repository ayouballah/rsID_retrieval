#!/usr/bin/env python3
"""Speed benchmark for rsID_retrieval.

This script runs the sandbox CLI against a curated set of VCF files and builds a
publication-ready HTML report that highlights runtime and annotation statistics.
It can also operate in report-only mode, consuming prior JSON results.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

try:  # Optional dependency for publication-style plot
    import matplotlib  # type: ignore

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
except ImportError:  # pragma: no cover - graceful fallback
    plt = None  # type: ignore

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("⚠ tqdm not installed. Install with: pip install tqdm")

# Benchmark configuration -----------------------------------------------------
VCF_CONFIGS: List[Dict[str, str]] = [
    {
        "name": "GIAB_subset_A",
        "path": r"C:\Users\ayoub\Documents\GitHub\rsID_retrieval\data\public_vcfs\HG001_subset_A.vcf",
        "chromosome": "1",
        "equation": "x",
        "format": "numeric",
        "description": "GIAB HG001 subset A (1000 variants)",
    },
    {
        "name": "GIAB_subset_D",
        "path": r"C:\Users\ayoub\Documents\GitHub\rsID_retrieval\data\public_vcfs\HG001_subset_D.vcf",
        "chromosome": "1",
        "equation": "x",
        "format": "numeric",
        "description": "GIAB HG001 subset D (5000 variants)",
    },
    {
        "name": "ClinVar_chr20_full",
        "path": r"C:\Users\ayoub\Documents\GitHub\rsID_retrieval\data\public_vcfs\clinvar_chr20_cleaned.vcf",
        "chromosome": "20",
        "equation": "x",
        "format": "numeric",
        "description": "ClinVar chromosome 20 full dataset (cleaned)",
    },
]

OUTPUT_DIR = Path("benchmark_optimized_results")
EMAIL = "ayoubellah4@gmail.com"

# Utility helpers -------------------------------------------------------------

def count_vcf_variants(vcf_path: str) -> int:
    """Count total variant records in a VCF file."""
    count = 0
    with open(vcf_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("#"):
                count += 1
    return count


def count_annotated_variants(vcf_path: Path) -> int:
    """Count variants that received an rsID annotation."""
    count = 0
    try:
        with open(vcf_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("#"):
                    continue
                fields = line.rstrip().split("\t")
                if len(fields) > 2 and fields[2] not in {".", "", "NORSID"}:
                    count += 1
    except FileNotFoundError:
        pass
    return count


def count_unannotated_variants(vcf_path: Path) -> int:
    """Count variants that did NOT receive an rsID annotation (NORSID)."""
    count = 0
    try:
        with open(vcf_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("#"):
                    continue
                fields = line.rstrip().split("\t")
                if len(fields) > 2 and fields[2] in {".", "", "NORSID"}:
                    count += 1
    except FileNotFoundError:
        pass
    return count


def load_results_from_json(json_path: Path) -> List[Dict[str, object]]:
    """Load benchmark results from a JSON file."""

    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {json_path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON structure in {json_path}: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of results in {json_path}")

    return payload

# Visualization ---------------------------------------------------------------

def generate_publication_chart(results: List[Dict[str, object]], output_dir: Path) -> Optional[Path]:
    """Render figure summarising the benchmark."""

    if plt is None:
        print("⚠ Matplotlib is not available. Skipping figure.")
        return None

    successful = [r for r in results if r.get("success")]
    if not successful:
        print("⚠ No successful runs available for figure.")
        return None

    ordered = sorted(successful, key=lambda r: r.get("total_variants", 0))
    dataset_labels = [f"Set {idx + 1}" for idx, _ in enumerate(ordered)]
    durations = [r.get("duration_seconds", 0.0) for r in ordered]
    annotation_rates = [r.get("annotation_rate", 0.0) for r in ordered]
    time_per_variant = [r.get("time_per_variant", 0.0) for r in ordered]
    variant_counts = [r.get("total_variants", 0) for r in ordered]

    plt.style.use("seaborn-v0_8")
    plt.rcParams.update(
        {
            "axes.titleweight": "bold",
            "axes.labelsize": 12,
            "axes.titlesize": 14,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 10,
        }
    )

    fig = plt.figure(figsize=(12.2, 7.5), dpi=170)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(
        nrows=2,
        ncols=2,
        height_ratios=[1.05, 1],
        width_ratios=[1, 1],
        hspace=0.55,
        wspace=0.42,
    )

    palette = {
        "runtime": "#2563eb",
        "variants": "#f97316",
        "rate": "#16a34a",
        "efficiency": "#7c3aed",
        "baseline": "#94a3b8",
    }

    ax_runtime = fig.add_subplot(gs[0, 0])
    ax_rate = fig.add_subplot(gs[0, 1])
    ax_efficiency = fig.add_subplot(gs[1, 0])
    ax_variants = fig.add_subplot(gs[1, 1])

    axes = (ax_runtime, ax_rate, ax_efficiency, ax_variants)
    for ax in axes:
        ax.set_facecolor("#f8fafc")
        ax.grid(axis="y", linestyle="--", linewidth=0.8, color="#e2e8f0", alpha=0.8)
        for spine in ax.spines.values():
            spine.set_visible(False)

    y_pos = list(range(len(dataset_labels)))
    ax_runtime.barh(y_pos, durations, color=palette["runtime"], alpha=0.9, height=0.55)
    ax_runtime.set_yticks(y_pos)
    runtime_labels = [f"{label} • {count:,} variants" for label, count in zip(dataset_labels, variant_counts)]
    ax_runtime.set_yticklabels(runtime_labels)
    ax_runtime.invert_yaxis()
    ax_runtime.set_xlabel("Processing Time (s)")
    ax_runtime.set_title("Runtime by Dataset")

    ax_runtime.set_xlim(0, max(durations) * 1.2)

    avg_duration = sum(durations) / len(durations)
    ax_runtime.axvline(avg_duration, color=palette["baseline"], linestyle="--", linewidth=1.2)
    runtime_label_idx = 1 if len(durations) >= 2 else 0
    runtime_label_x = min(avg_duration + max(durations) * 0.04, ax_runtime.get_xlim()[1] * 0.98)
    ax_runtime.text(
        runtime_label_x,
        runtime_label_idx,
        "Average",
        color=palette["baseline"],
        fontsize=9,
        ha="left",
        va="center",
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.35},
    )

    for y, value in zip(y_pos, durations):
        text_pos = value + max(durations) * 0.03
        ax_runtime.text(text_pos, y, f"{value:.1f}s", va="center", fontsize=10, color="#0f172a")

    ax_rate.plot(
        dataset_labels,
        annotation_rates,
        color=palette["rate"],
        marker="o",
        markersize=7,
        linewidth=2.4,
    )
    ax_rate.fill_between(dataset_labels, annotation_rates, color=palette["rate"], alpha=0.12)
    ax_rate.set_ylim(0, 105)
    ax_rate.set_ylabel("rsID Recovery (%)")
    ax_rate.set_title("rsID Recovery Rate")
    ax_rate.grid(axis="x", linestyle=":", color="#e2e8f0")

    avg_rate = sum(annotation_rates) / len(annotation_rates)
    ax_rate.axhline(avg_rate, color=palette["baseline"], linestyle="--", linewidth=1.2)
    ax_rate.text(
        len(dataset_labels) - 1,
        avg_rate + 2,
        "Average",
        color=palette["baseline"],
        fontsize=9,
        ha="right",
    )

    ax_efficiency.bar(dataset_labels, time_per_variant, color=palette["efficiency"], alpha=0.9, width=0.55)
    ax_efficiency.set_ylabel("Seconds per Variant")
    ax_efficiency.set_title("Per-Variant Processing Time")
    ax_efficiency.set_ylim(0, max(time_per_variant) * 1.35)

    avg_eff = sum(time_per_variant) / len(time_per_variant)
    ax_efficiency.axhline(avg_eff, color=palette["baseline"], linestyle="--", linewidth=1.2)
    if len(time_per_variant) >= 2:
        eff_label_x = 0.5
        eff_label_y = (time_per_variant[0] + time_per_variant[1]) / 2
    else:
        eff_label_x = len(dataset_labels) - 0.3
        eff_label_y = avg_eff
    ax_efficiency.text(
        eff_label_x,
        eff_label_y,
        "Average",
        color=palette["baseline"],
        fontsize=9,
        ha="center",
        va="center",
        clip_on=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 0.35},
    )

    for idx, value in enumerate(time_per_variant):
        ax_efficiency.text(idx, value + max(time_per_variant) * 0.07, f"{value:.3f}s", ha="center", fontsize=10, color="#0f172a")

    ax_variants.bar(dataset_labels, variant_counts, color=palette["variants"], alpha=0.85, width=0.55)
    ax_variants.set_ylabel("Variant Count")
    ax_variants.set_title("Variants Processed")
    ax_variants.set_ylim(0, max(variant_counts) * 1.25)

    for idx, value in enumerate(variant_counts):
        ax_variants.text(idx, value + max(variant_counts) * 0.05, f"{value:,}", ha="center", fontsize=10, color="#0f172a")

    ax_variants.grid(axis="x", linestyle=":", color="#e2e8f0")

    fig.suptitle("rsID_retrieval Speed Benchmark", fontsize=17, fontweight="bold")
    fig.subplots_adjust(top=0.9, bottom=0.11, left=0.08, right=0.96)

    chart_path = output_dir / "speed_benchmark_publication.png"
    fig.savefig(chart_path, dpi=320, bbox_inches="tight")
    plt.close(fig)

    print(f"✓ Publication-quality figure saved: {chart_path}")
    return chart_path


def generate_html_report(results: List[Dict[str, object]], output_path: Path) -> None:
    """Build a single-page HTML report with embedded publication-style visualisation."""

    successful = [r for r in results if r.get("success")]
    ordered = sorted(successful, key=lambda r: r.get("total_variants", 0))
    durations = [r.get("duration_seconds", 0.0) for r in ordered]
    variant_counts = [r.get("total_variants", 0) for r in ordered]
    annotation_rates = [r.get("annotation_rate", 0.0) for r in ordered]
    time_per_variant = [r.get("time_per_variant", 0.0) for r in ordered]

    total_variants_all = sum(r.get("total_variants", 0) for r in results)
    annotated_total = sum(r.get("annotated_variants", 0) for r in successful)

    chart_path = generate_publication_chart(results, OUTPUT_DIR)
    embedded_chart = ""
    download_button = ""
    if chart_path and chart_path.exists():
        encoded_chart = base64.b64encode(chart_path.read_bytes()).decode("utf-8")
        embedded_chart = (
            '<img src="data:image/png;base64,'
            f"{encoded_chart}"
            '" alt="Benchmark summary" '
            'style="width:100%; max-width:980px; border-radius:14px; '
            'box-shadow:0 30px 70px rgba(15,23,42,0.20);" />'
        )
        download_button = (
            f'<a class="download-button" href="{chart_path.name}" download>'
            '⬇ Export high-res PNG</a>'
        )

    table_rows: List[str] = []
    for r in results:
        status_icon = "✓" if r.get("success") else "✗"
        status_color = "#10b981" if r.get("success") else "#ef4444"
        unannotated = r.get('unannotated_variants', 0)
        table_rows.append(
            "                        <tr>\n"
            f"                            <td>{r.get('total_variants', 0):,}</td>\n"
            f"                            <td>{r.get('annotated_variants', 0):,}</td>\n"
            f"                            <td style=\"color: #ef4444;\">{unannotated:,}</td>\n"
            f"                            <td>{r.get('annotation_rate', 0):.1f}%</td>\n"
            f"                            <td><strong>{r.get('duration_seconds', 0):.2f}s</strong></td>\n"
            f"                            <td>{r.get('time_per_variant', 0):.3f}s</td>\n"
            f"                            <td style=\"color: {status_color}; font-weight: bold;\">{status_icon}</td>\n"
            "                        </tr>\n"
        )

    total_runtime = sum(durations)
    mean_annotation = sum(annotation_rates) / len(annotation_rates) if annotation_rates else 0.0

    insight_items: List[str] = []
    if ordered:
        fastest_idx = durations.index(min(durations))
        highest_rate_idx = annotation_rates.index(max(annotation_rates))
        best_eff_idx = time_per_variant.index(min(time_per_variant))
        
        # Calculate NORSID counts for each dataset
        unannotated_counts = [r.get("unannotated_variants", 0) for r in ordered]
        total_unannotated = sum(unannotated_counts)

        def describe(idx: int) -> str:
            return f"Set {idx + 1} ({variant_counts[idx]:,} variants)"

        insight_items.append(
            f"<li><span class=\"tag\">Fastest Runtime</span>{describe(fastest_idx)} completed in {durations[fastest_idx]:.1f}s.</li>"
        )
        insight_items.append(
            f"<li><span class=\"tag\">Highest rsID Recovery</span>{describe(highest_rate_idx)} achieved {annotation_rates[highest_rate_idx]:.1f}% rsID recovery.</li>"
        )
        insight_items.append(
            f"<li><span class=\"tag\">Most Efficient</span>{describe(best_eff_idx)} processed at {time_per_variant[best_eff_idx]:.3f}s per variant.</li>"
        )
        insight_items.append(
            f"<li><span class=\"tag\" style=\"background:#fef2f2; color:#dc2626;\">NORSID Total</span>Across all datasets, {total_unannotated:,} variants could not be annotated with rsIDs.</li>"
        )

    methodology_text = (
        "Runs executed via sandbox_cli.py with dataset-specific chromosome remapping and position equations. "
        "All outputs were generated on Windows using the curated OneDrive VCF inputs and the rsID_retrieval sandbox pipeline."
    )

    html_content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>rsID_retrieval Speed Benchmark</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(145deg, #f1f5ff 0%, #f8fafc 100%);
            padding: 2.75rem;
            color: #1f2937;
            line-height: 1.7;
        }}
        .container {{
            max-width: 1140px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 2.6rem;
            border-radius: 1.25rem;
            margin-bottom: 2.6rem;
            box-shadow: 0 30px 65px rgba(15, 23, 42, 0.12);
            border: 1px solid #e2e8f0;
        }}
        h1 {{
            font-size: 2.35rem;
            letter-spacing: 0.02em;
            margin-bottom: 0.75rem;
        }}
        .subtitle {{
            color: #4b5563;
            font-size: 1.05rem;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.4rem;
            margin-bottom: 2.4rem;
        }}
        .stat-card {{
            background: white;
            padding: 1.8rem;
            border-radius: 1.1rem;
            box-shadow: 0 24px 50px rgba(15, 23, 42, 0.1);
            border: 1px solid #e2e8f0;
        }}
        .stat-value {{
            font-size: 2.05rem;
            font-weight: 600;
            color: #2563eb;
            margin-bottom: 0.55rem;
        }}
        .stat-label {{
            color: #4b5563;
            letter-spacing: 0.02em;
            font-size: 0.95rem;
        }}
        .section-card {{
            background: white;
            padding: 2.3rem;
            border-radius: 1.2rem;
            margin-bottom: 2.6rem;
            box-shadow: 0 22px 55px rgba(15, 23, 42, 0.12);
            border: 1px solid #e2e8f0;
        }}
        .chart-wrapper {{
            text-align: center;
        }}
        .chart-title {{
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.88rem;
            color: #6b7280;
            margin-bottom: 1.5rem;
        }}
        .chart-caption {{
            font-size: 0.98rem;
            color: #374151;
            margin-top: 1.8rem;
            max-width: 860px;
            margin-left: auto;
            margin-right: auto;
        }}
        .download-button {{
            display: inline-block;
            margin-top: 1rem;
            padding: 0.65rem 1.6rem;
            background: #111827;
            color: #f8fafc;
            border-radius: 999px;
            text-decoration: none;
            font-size: 0.92rem;
            letter-spacing: 0.02em;
            box-shadow: 0 15px 35px rgba(15, 23, 42, 0.25);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .download-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 20px 45px rgba(15, 23, 42, 0.3);
        }}
        .insights-list {{
            list-style: none;
            margin-top: 1.6rem;
            display: grid;
            gap: 0.9rem;
        }}
        .insights-list li {{
            font-size: 0.98rem;
            color: #1f2937;
            background: #f8fafc;
            padding: 0.85rem 1.1rem;
            border-radius: 0.9rem;
            border: 1px solid #e2e8f0;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
        }}
        .tag {{
            display: inline-block;
            margin-right: 0.6rem;
            padding: 0.1rem 0.55rem;
            border-radius: 999px;
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            background: #2563eb1a;
            color: #2563eb;
            border: 1px solid #bfdbfe;
        }}
        .table-card {{
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.98rem;
        }}
        th, td {{
            padding: 0.95rem 1.1rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.75rem;
            color: #6b7280;
        }}
        tbody tr:hover {{
            background-color: #f9fafb;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            margin-top: 2.6rem;
            font-size: 0.88rem;
        }}
    </style>
</head>
<body>
    <div class=\"container\">
        <div class=\"header\">
            <h1>rsID_retrieval Speed Benchmark</h1>
            <p class=\"subtitle\">Performance comparison across curated VCF cohorts</p>
            <p class=\"subtitle\" style=\"margin-top: 0.4rem;\">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class=\"stats-grid\">
            <div class=\"stat-card\">
                <div class=\"stat-value\">{len(results)}</div>
                <div class=\"stat-label\">VCF Files Tested</div>
            </div>
            <div class=\"stat-card\">
                <div class=\"stat-value\">{total_variants_all:,}</div>
                <div class=\"stat-label\">Total Variants Processed</div>
            </div>
            <div class=\"stat-card\">
                <div class=\"stat-value\">{total_runtime:.1f}s</div>
                <div class=\"stat-label\">Aggregate Runtime (successful)</div>
            </div>
            <div class=\"stat-card\">
                <div class=\"stat-value\">{annotated_total:,}</div>
                <div class=\"stat-label\">Variants Annotated with rsID</div>
            </div>
            <div class=\"stat-card\">
                <div class=\"stat-value\">{mean_annotation:.1f}%</div>
                    <div class="stat-label">Mean rsID Recovery</div>
            </div>
        </div>

        <div class=\"section-card chart-wrapper\">
            <h2 class=\"chart-title\">Benchmark Overview</h2>
            {embedded_chart or '<p style="color:#ef4444;">No chart image available.</p>'}
            <p class=\"chart-caption\">
                Runtime (upper panel) and annotation efficiency (lower panel) for rsID_retrieval in sandbox mode. rsID recovery rate and time-per-variant share aligned axes to emphasise trade-offs across datasets.
            </p>
            {download_button}
        </div>

        {'<div class="section-card"><h2 class="chart-title" style="text-transform:none; letter-spacing:0.02em; font-size:1.1rem; color:#1f2937;">Key Highlights</h2><ul class="insights-list">' + ''.join(insight_items) + '</ul></div>' if insight_items else ''}

        <div class=\"section-card\">
            <h2 class=\"chart-title\" style=\"text-transform:none; letter-spacing:0.04em; font-size:1.05rem; color:#1f2937;\">Detailed Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Total Variants</th>
                        <th>Annotated</th>
                        <th>NORSID</th>
                        <th>Rate</th>
                        <th>Duration</th>
                        <th>Time/Variant</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
{''.join(table_rows)}
                </tbody>
            </table>
        </div>

        <div class=\"section-card\">
            <h2 class=\"chart-title\" style=\"text-transform:none; letter-spacing:0.04em; font-size:1.05rem; color:#1f2937;\">Methodology Notes</h2>
            <p style=\"font-size:0.96rem; color:#374151; margin-top:1.4rem;\">{methodology_text}</p>
        </div>

        <div class=\"footer\">
            <p>rsID_retrieval Benchmark Suite &mdash; Sandbox Mode</p>
        </div>
    </div>
</body>
</html>"""

    output_path.write_text(html_content, encoding="utf-8")
    print(f"\n✓ HTML report generated: {output_path}")

# Benchmark execution ---------------------------------------------------------

def run_single_benchmark(config: Dict[str, str]) -> Optional[Dict[str, object]]:
    """Execute sandbox_cli for a single VCF configuration."""

    vcf_path = config["path"]
    if not Path(vcf_path).exists():
        print(f"ERROR: VCF file not found: {vcf_path}")
        return None

    variant_count = count_vcf_variants(vcf_path)

    print("\n" + "=" * 70)
    print(f"Benchmarking: {config['name']}")
    print("=" * 70)
    print(f"File: {Path(vcf_path).name}")
    print(f"Variants: {variant_count}")
    print(f"Chromosome: {config['chromosome']}")
    print(f"Equation: {config['equation']}")
    print(f"Format: {config['format']}")
    print(f"Description: {config['description']}")
    print(f"Estimated time: {variant_count * 0.3:.1f}-{variant_count * 1.0:.1f} seconds")

    output_dir = OUTPUT_DIR / f"{config['name']}_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "sandbox_cli.py",
        "--input_vcf",
        vcf_path,
        "--output_dir",
        str(output_dir),
        "--email",
        EMAIL,
        "--chromosome",
        config["chromosome"],
        "--equation",
        config["equation"],
        "--format",
        config["format"],
    ]

    print(f"\nStarting benchmark at {datetime.now().strftime('%H:%M:%S')}...")
    start_time = time.time()

    try:
        import os as _os
        env = _os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1,
            universal_newlines=True,
            env=env,
        )

        captured_lines: List[str] = []
        pbar = None
        if HAS_TQDM:
            pbar = tqdm(
                total=variant_count,
                desc=f"Processing {config['name']}",
                unit="variant",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
            )

        for line in process.stdout:
            captured_lines.append(line)
            if pbar:
                match = re.search(r"(\d+)\s*/\s*(\d+)", line)
                if match:
                    try:
                        current = int(match.group(1))
                    except ValueError:
                        current = pbar.n
                    else:
                        pbar.n = current
                        pbar.refresh()
            if any(keyword in line.lower() for keyword in ["error", "warning", "completed", "starting"]):
                if pbar:
                    pbar.write(line.rstrip())
                else:
                    print(line.rstrip())

        process.wait()
        elapsed = time.time() - start_time

        if pbar:
            pbar.close()

        success = process.returncode == 0

        if not success:
            print(f"\n⚠ Command failed with return code {process.returncode}")
            if captured_lines:
                joined = ''.join(captured_lines)
                print(joined if len(joined) < 2000 else joined[-2000:])

        results_subdir = output_dir / f"{Path(vcf_path).stem}_sandbox_results"
        annotated_file = results_subdir / f"{Path(vcf_path).stem}_annotated.vcf"
        annotated_count = count_annotated_variants(annotated_file)
        unannotated_count = count_unannotated_variants(annotated_file)

        print(f"Completed in {elapsed:.2f} seconds")
        print(f"Status: {'✓ Success' if success else '✗ Failed'}")
        if variant_count:
            percent = annotated_count / variant_count * 100
        else:
            percent = 0.0
        print(f"Annotated variants: {annotated_count}/{variant_count} ({percent:.1f}%)")
        print(f"Unannotated (NORSID): {unannotated_count}/{variant_count}")

        result: Dict[str, object] = {
            "name": config["name"],
            "file": Path(vcf_path).name,
            "description": config["description"],
            "chromosome": config["chromosome"],
            "equation": config["equation"],
            "format": config["format"],
            "total_variants": variant_count,
            "annotated_variants": annotated_count,
            "unannotated_variants": unannotated_count,
            "annotation_rate": round(percent, 2) if variant_count else 0.0,
            "duration_seconds": round(elapsed, 2),
            "time_per_variant": round(elapsed / variant_count, 3) if variant_count else 0.0,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        return result

    except Exception as exc:  # pragma: no cover - defensive guard
        elapsed = time.time() - start_time
        print(f"ERROR: {exc}")
        return {
            "name": config["name"],
            "file": Path(vcf_path).name,
            "error": str(exc),
            "duration_seconds": round(elapsed, 2),
            "success": False,
            "timestamp": datetime.now().isoformat(),
        }

# Entry point -----------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="rsID_retrieval speed benchmark")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip execution and regenerate HTML from an existing JSON file.",
    )
    parser.add_argument(
        "--input-json",
        type=str,
        help="Optional path to a benchmark JSON file (used with --report-only).",
    )
    parser.add_argument(
        "--only",
        type=str,
        metavar="DATASET_NAME",
        help="Run only the named dataset (e.g. GIAB_subset_D), merge into the latest JSON, and regenerate figures.",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("rsID_retrieval Speed Benchmark")
    print("=" * 70)
    print(f"Configured VCF files: {len(VCF_CONFIGS)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    OUTPUT_DIR.mkdir(exist_ok=True)

    results: List[Dict[str, object]] = []

    if args.only:
        # Find the config matching the requested dataset name
        matching = [c for c in VCF_CONFIGS if c["name"] == args.only]
        if not matching:
            available = ", ".join(c["name"] for c in VCF_CONFIGS)
            print(f"ERROR: Dataset '{args.only}' not found. Available: {available}")
            return
        config = matching[0]

        # Load the most recent existing JSON to merge into
        existing_results: List[Dict[str, object]] = []
        json_candidates = sorted(
            OUTPUT_DIR.glob("speed_benchmark_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if json_candidates:
            existing_results = load_results_from_json(json_candidates[0])
            print(f"Loaded existing results from: {json_candidates[0]}")

        # Run only the requested dataset
        outcome = run_single_benchmark(config)
        if outcome:
            # Replace or append the entry for this dataset
            existing_results = [r for r in existing_results if r.get("name") != args.only]
            existing_results.append(outcome)

        results = existing_results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = OUTPUT_DIR / f"speed_benchmark_{timestamp}.json"
        json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\n✓ Updated JSON results saved: {json_path}")

        html_path = OUTPUT_DIR / "speed_benchmark_report.html"
        generate_html_report(results, html_path)

        print("\n" + "=" * 70)
        print("✓ Figures and report updated!")
        print("=" * 70)
        print(f"\nView results: {html_path.absolute()}")
        return

    if args.report_only:
        if args.input_json:
            json_path = Path(args.input_json)
        else:
            json_candidates = sorted(
                OUTPUT_DIR.glob("speed_benchmark_*.json"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if not json_candidates:
                raise FileNotFoundError(
                    "No benchmark JSON files found. Run the benchmark first or provide --input-json."
                )
            json_path = json_candidates[0]

        print(f"\nLoading existing results from: {json_path}")
        results = load_results_from_json(json_path)
    else:
        for config in VCF_CONFIGS:
            outcome = run_single_benchmark(config)
            if outcome:
                results.append(outcome)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = OUTPUT_DIR / f"speed_benchmark_{timestamp}.json"
        json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\n✓ JSON results saved: {json_path}")

    if not results:
        print("No results available to report. Exiting.")
        return

    html_path = OUTPUT_DIR / "speed_benchmark_report.html"
    generate_html_report(results, html_path)

    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"Total files: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        total_time = sum(r.get("duration_seconds", 0.0) for r in successful)
        total_variants = sum(r.get("total_variants", 0) for r in successful)
        total_annotated = sum(r.get("annotated_variants", 0) for r in successful)
        avg_time_file = total_time / len(successful)
        avg_time_variant = total_time / total_variants if total_variants else 0.0

        print(f"\nTotal processing time: {total_time:.2f} seconds")
        print(f"Total variants processed: {total_variants:,}")
        if total_variants:
            print(f"Total variants annotated: {total_annotated:,} ({total_annotated / total_variants * 100:.1f}%)")
        print(f"Average time per file: {avg_time_file:.2f} seconds")
        print(f"Average time per variant: {avg_time_variant:.3f} seconds")

    print("\n" + "=" * 70)
    print("✓ Benchmark complete!")
    print("=" * 70)
    print(f"\nView results: {html_path.absolute()}")


if __name__ == "__main__":
    main()
