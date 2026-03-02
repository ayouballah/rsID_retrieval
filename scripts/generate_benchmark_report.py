#!/usr/bin/env python3
"""Generate an interactive HTML benchmark report from benchmark_metrics.json."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from typing import Dict, List, Tuple


def ordered_unique(items: List[str]) -> List[str]:
    """Return items preserving the first occurrence order."""
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def build_datasets(metrics: List[dict]) -> Tuple[List[str], List[str], Dict[str, List[float]], Dict[str, List[float]], Dict[Tuple[str, str], dict]]:
    samples = ordered_unique([m["sample"] for m in metrics])
    tools = ordered_unique([m["tool"] for m in metrics])
    sample_index = {sample: idx for idx, sample in enumerate(samples)}

    duration_values: Dict[str, List[float]] = {tool: [None] * len(samples) for tool in tools}
    correctness_values: Dict[str, List[float]] = {tool: [None] * len(samples) for tool in tools}
    metric_lookup: Dict[Tuple[str, str], dict] = {}

    for entry in metrics:
        sample = entry["sample"]
        tool = entry["tool"]
        idx = sample_index[sample]
        metric_lookup[(sample, tool)] = entry
        duration = entry.get("duration_seconds")
        if duration is not None:
            duration_values[tool][idx] = round(duration, 3)
        total = entry.get("total_variants", 0)
        annotated = entry.get("annotated_variants", 0)
        if total:
            correctness_values[tool][idx] = round((annotated / total) * 100.0, 2)
        else:
            correctness_values[tool][idx] = None

    return samples, tools, duration_values, correctness_values, metric_lookup


def build_chart_datasets(tools: List[str], values: Dict[str, List[float]]) -> List[dict]:
    palette = [
        "#2563eb",  # blue
        "#16a34a",  # green
        "#d97706",  # orange
        "#dc2626",  # red
        "#7c3aed",  # purple
        "#0f766e",  # teal
        "#ca8a04",  # amber
        "#6366f1",  # indigo
    ]
    datasets = []
    for idx, tool in enumerate(tools):
        color = palette[idx % len(palette)]
        datasets.append(
            {
                "label": tool,
                "data": values[tool],
                "backgroundColor": color,
                "borderColor": color,
                "borderWidth": 1,
            }
        )
    return datasets


def build_status_table(samples: List[str], tools: List[str], metrics: Dict[Tuple[str, str], dict]) -> str:
    rows = []
    for sample in samples:
        for tool in tools:
            entry = metrics.get((sample, tool))
            status = entry.get("status") if entry else "n/a"
            duration = entry.get("duration_seconds") if entry else None
            total = entry.get("total_variants") if entry else None
            annotated = entry.get("annotated_variants") if entry else None
            percent = (annotated / total * 100.0) if entry and total else None
            rows.append(
                f"<tr><td>{sample}</td><td>{tool}</td><td>{status}</td><td>{'' if duration is None else round(duration, 3)}</td>"
                f"<td>{'' if annotated is None else annotated}</td><td>{'' if total is None else total}</td>"
                f"<td>{'' if percent is None else round(percent, 2)}</td></tr>"
            )
    return "\n".join(rows)


def render_html(samples: List[str], tools: List[str], duration_values: Dict[str, List[float]], correctness_values: Dict[str, List[float]], table_rows: str) -> str:
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration_datasets = build_chart_datasets(tools, duration_values)
    correctness_datasets = build_chart_datasets(tools, correctness_values)

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>rsID_retrieval Benchmark Report</title>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 2rem; color: #0f172a; background-color: #f8fafc; }}
    h1 {{ margin-bottom: 0.25rem; }}
    h2 {{ margin-top: 2rem; margin-bottom: 1rem; }}
    .card {{ background: #fff; padding: 1.5rem; border-radius: 0.75rem; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.1); margin-bottom: 2rem; }}
    canvas {{ max-width: 100%; height: 360px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
    th, td {{ border-bottom: 1px solid #e2e8f0; padding: 0.65rem; text-align: left; }}
    th {{ background-color: #1d4ed8; color: white; position: sticky; top: 0; }}
    tbody tr:hover {{ background-color: #eff6ff; }}
    .meta {{ color: #475569; font-size: 0.9rem; margin-bottom: 1.5rem; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>rsID_retrieval Benchmark Report</h1>
    <p class=\"meta\">Generated: {generated_at}</p>
    <p class=\"meta\">Samples analysed: {len(samples)} &nbsp;|&nbsp; Tools compared: {len(tools)}</p>
  </div>

  <div class=\"card\">
    <h2>Execution Time by Tool</h2>
    <canvas id=\"durationChart\"></canvas>
  </div>

  <div class=\"card\">
    <h2>Annotation Correctness (% of variants with annotations)</h2>
    <canvas id=\"correctnessChart\"></canvas>
  </div>

  <div class=\"card\">
    <h2>Detailed Metrics</h2>
    <div style=\"overflow-x: auto;\">
      <table>
        <thead>
          <tr><th>Sample</th><th>Tool</th><th>Status</th><th>Duration (s)</th><th>Annotated</th><th>Total</th><th>% Annotated</th></tr>
        </thead>
        <tbody>
          {table_rows}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    const samples = {json.dumps(samples)};
    const durationDatasets = {json.dumps(duration_datasets)};
    const correctnessDatasets = {json.dumps(correctness_datasets)};

    const durationConfig = {{
      type: 'bar',
      data: {{ labels: samples, datasets: durationDatasets }},
      options: {{
        responsive: true,
        scales: {{
          x: {{ stacked: false }},
          y: {{ stacked: false, title: {{ display: true, text: 'Seconds' }}, beginAtZero: true }}
        }},
        plugins: {{
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const value = context.parsed.y;
                return `${{context.dataset.label}}: ${{value == null ? 'n/a' : value.toFixed(3)}} s`;
              }}
            }}
          }}
        }}
      }}
    }};

    const correctnessConfig = {{
      type: 'bar',
      data: {{ labels: samples, datasets: correctnessDatasets }},
      options: {{
        responsive: true,
        scales: {{
          x: {{ stacked: false }},
          y: {{ stacked: false, title: {{ display: true, text: 'Annotated Variants (%)' }}, beginAtZero: true, suggestedMax: 100 }}
        }},
        plugins: {{
          tooltip: {{
            callbacks: {{
              label: function(context) {{
                const value = context.parsed.y;
                return `${{context.dataset.label}}: ${{value == null ? 'n/a' : value.toFixed(2)}} %`;
              }}
            }}
          }}
        }}
      }}
    }};

    new Chart(document.getElementById('durationChart'), durationConfig);
    new Chart(document.getElementById('correctnessChart'), correctnessConfig);
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML report from benchmark metrics.")
    parser.add_argument("--metrics", default=os.path.join("benchmark_results", "benchmark_metrics.json"), help="Path to benchmark metrics JSON file.")
    parser.add_argument("--output", default=os.path.join("benchmark_results", "benchmark_report.html"), help="Output HTML file path.")
    args = parser.parse_args()

    if not os.path.exists(args.metrics):
        raise FileNotFoundError(f"Metrics file not found: {args.metrics}")

    with open(args.metrics, "r", encoding="utf-8") as fh:
        metrics = json.load(fh)

    if not metrics:
        raise ValueError("Metrics file is empty. Run the benchmark first.")

    samples, tools, duration_values, correctness_values, metric_lookup = build_datasets(metrics)
    table_rows = build_status_table(samples, tools, metric_lookup)
    html = render_html(samples, tools, duration_values, correctness_values, table_rows)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"Benchmark report written to {args.output}")


if __name__ == "__main__":
    main()
