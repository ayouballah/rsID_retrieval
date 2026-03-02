#!/usr/bin/env python3
"""Compare rsID overlap between a ClinVar VCF and a genomic mapping VCF.

rsIDs are read from the ID column (column 3) of both files and matched
per (chromosome, position, REF, ALT) variant. A variant where at least one
rsID appears in both files is counted as an overlap. Multi-allelic sites are
compared independently per allele. Variants exclusive to one file are
recorded separately in the JSON output.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import matplotlib.pyplot as plt


# Variant key type: (chrom, pos, ref, alt)
VKey = Tuple[str, str, str, str]


def parse_original_vcf(
    path: Path,
) -> Tuple[Dict[VKey, Set[str]], Dict[VKey, List[str]], List[str], Set[VKey]]:
    """Parse ClinVar VCF reading rsIDs directly from the ID column (column 3).

    Returns:
        rsid_map: mapping from (chrom, pos, ref, alt) -> set of rsIDs
        line_map: mapping from (chrom, pos, ref, alt) -> list of raw VCF lines
        headers: list of header lines to reuse when writing filtered VCFs
        all_variants: set of every (chrom, pos, ref, alt) seen (including NORSID)
    """

    rsid_map: Dict[VKey, Set[str]] = defaultdict(set)
    line_map: Dict[VKey, List[str]] = defaultdict(list)
    headers: List[str] = []
    all_variants: Set[VKey] = set()

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line:
                continue
            if line.startswith("#"):
                headers.append(line)
                continue
            parts = line.rstrip().split("\t")
            if len(parts) < 5:
                continue
            chrom, pos, id_field, ref, alt = parts[0], parts[1], parts[2], parts[3], parts[4]
            key: VKey = (chrom, pos, ref, alt)
            all_variants.add(key)

            rs_ids: List[str] = []

            # Try ID column first (e.g. rsID_retrieval annotated output or
            # cleaned VCFs that carry rsIDs in col 3)
            if id_field not in {".", "", "NORSID"}:
                rs_ids = [
                    token.strip()
                    for token in id_field.split(",")
                    if token.strip() and token.strip() not in {".", "NORSID"}
                    and token.strip().lower().startswith("rs")
                ]

            # Fallback: extract RS=<number> from INFO field (raw ClinVar VCF format)
            if not rs_ids and len(parts) >= 8:
                info = parts[7]
                for m in re.finditer(r'(?:^|;)RS=(\d+)', info):
                    rs_ids.append(f"rs{m.group(1)}")

            if rs_ids:
                rsid_map[key].update(rs_ids)
                line_map[key].append(line.rstrip("\n"))
    return rsid_map, line_map, headers, all_variants


def parse_annotated_vcf(path: Path) -> Tuple[Dict[VKey, Set[str]], Set[VKey]]:
    """Parse genomic mapping VCF reading rsIDs from the ID column (column 3).

    Returns:
        mapping: (chrom, pos, ref, alt) -> set of rsIDs
        all_variants: set of every (chrom, pos, ref, alt) seen (including NORSID)
    """
    mapping: Dict[VKey, Set[str]] = defaultdict(set)
    all_variants: Set[VKey] = set()

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            parts = line.rstrip().split("\t")
            if len(parts) < 5:
                continue
            chrom, pos, rs_field, ref, alt = parts[0], parts[1], parts[2], parts[3], parts[4]
            key: VKey = (chrom, pos, ref, alt)
            all_variants.add(key)

            rs_ids: List[str] = []

            # Try ID column first
            if rs_field not in {".", "", "NORSID"}:
                rs_ids = [
                    token.strip()
                    for token in rs_field.split(",")
                    if token.strip() and token.strip() not in {".", "NORSID"}
                    and token.strip().lower().startswith("rs")
                ]

            # Fallback: extract RS=<number> from INFO field (raw ClinVar VCF format)
            if not rs_ids and len(parts) >= 8:
                info = parts[7]
                for m in re.finditer(r'(?:^|;)RS=(\d+)', info):
                    rs_ids.append(f"rs{m.group(1)}")

            if rs_ids:
                mapping[key].update(rs_ids)
    return mapping, all_variants


def build_overlap(
    original: Dict[VKey, Set[str]],
    annotated: Dict[VKey, Set[str]],
    orig_all_variants: Set[VKey],
    annot_all_variants: Set[VKey],
) -> Tuple[Dict[str, object], Set[VKey]]:
    rsid_variants = set(original.keys()) | set(annotated.keys())

    overlap: Dict[VKey, str] = {}       # variant -> first matching rsID
    clinvar_only: Dict[VKey, List[str]] = {}
    genomic_only: Dict[VKey, List[str]] = {}
    original_only_variants: Set[VKey] = set()

    for key in rsid_variants:
        orig_set = original.get(key, set())
        ann_set = annotated.get(key, set())
        common = orig_set & ann_set
        if common:
            overlap[key] = sorted(common)[0]
        elif orig_set:
            clinvar_only[key] = sorted(orig_set)
            original_only_variants.add(key)
        elif ann_set:
            genomic_only[key] = sorted(ann_set)

    # Variants where BOTH tools found no rsID — agreement on absence
    orig_norsid = orig_all_variants - set(original.keys())
    annot_norsid = annot_all_variants - set(annotated.keys())
    mutual_norsid = orig_norsid & annot_norsid

    def _vkey(item):
        (chrom, pos, ref, alt), _ = item
        try:
            return (chrom, int(pos), ref, alt)
        except ValueError:
            return (chrom, pos, ref, alt)

    summary = {
        "count_overlap_variants": len(overlap) + len(mutual_norsid),
        "count_rsid_overlap_variants": len(overlap),
        "count_mutual_norsid_variants": len(mutual_norsid),
        "count_clinvar_only_variants": len(clinvar_only),
        "count_genomic_only_variants": len(genomic_only),
        "overlap": {
            f"{c}:{p}:{r}>{a}": rsid
            for (c, p, r, a), rsid in sorted(overlap.items(), key=_vkey)
        },
        "clinvar_only": {
            f"{c}:{p}:{r}>{a}": rsids
            for (c, p, r, a), rsids in sorted(clinvar_only.items(), key=_vkey)
        },
        "genomic_only": {
            f"{c}:{p}:{r}>{a}": rsids
            for (c, p, r, a), rsids in sorted(genomic_only.items(), key=_vkey)
        },
    }
    return summary, original_only_variants


def write_original_only_vcf(
    headers: Iterable[str],
    line_map: Dict[VKey, List[str]],
    target_variants: Set[VKey],
    output_path: Path,
) -> int:
    """Write a filtered ClinVar VCF containing only variants exclusive to ClinVar."""

    if not target_variants:
        return 0

    with output_path.open("w", encoding="utf-8") as handle:
        for line in headers:
            handle.write(line if line.endswith("\n") else f"{line}\n")

        total_lines = 0
        def _sort_key(k: VKey):
            try:
                return (k[0], int(k[1]), k[2], k[3])
            except ValueError:
                return k
        for key in sorted(target_variants, key=_sort_key):
            for record in line_map.get(key, []):
                handle.write(f"{record}\n")
                total_lines += 1
    return total_lines


def render_venn(
    summary: Dict[str, object],
    output_path: Path,
    left_label: str = "SNPnexus v5 output",
    right_label: str = "rsID_retrieval output",
) -> None:
    # Left = original/reference source (genomic_only = unique to left)
    # Right = rsID_retrieval (clinvar_only = unique to right)
    left = summary["count_genomic_only_variants"]
    right = summary["count_clinvar_only_variants"]
    overlap = summary["count_overlap_variants"]  # rsID overlap + mutual NORSID

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_facecolor("#f8fafc")
    fig.patch.set_facecolor("#f8fafc")
    plt.axis("off")

    left_circle = plt.Circle((0.4, 0.5), 0.3, color="#6366f1", alpha=0.35)
    right_circle = plt.Circle((0.6, 0.5), 0.3, color="#f97316", alpha=0.35)

    ax.add_patch(left_circle)
    ax.add_patch(right_circle)

    ax.text(0.18, 0.88, left_label, fontsize=13, weight="bold", color="#312e81", ha="center")
    ax.text(0.82, 0.88, right_label, fontsize=13, weight="bold", color="#7c2d12", ha="center")

    ax.text(0.28, 0.5, f"{left:,}\nUnique\nVariants", fontsize=16, ha="center", va="center", color="#312e81")
    ax.text(0.72, 0.5, f"{right:,}\nUnique\nVariants", fontsize=16, ha="center", va="center", color="#7c2d12")
    ax.text(
        0.5,
        0.5,
        f"{overlap:,}\nMatching\nVariants",
        fontsize=17,
        ha="center",
        va="center",
        color="#111827",
        weight="bold",
    )

    mutual_norsid = summary.get("count_mutual_norsid_variants", 0)
    rsid_overlap = summary.get("count_rsid_overlap_variants", overlap)
    caption = (
        f"Overlap includes {rsid_overlap:,} variants with matching rsID "
        f"and {mutual_norsid:,} variants where both tools found no rsID (mutual NORSID)."
    )
    ax.text(0.5, 0.08, caption, fontsize=10.5, color="#4b5563", ha="center", wrap=True)

    fig.savefig(output_path, dpi=320, bbox_inches="tight")
    plt.close(fig)



def main() -> None:
    parser = argparse.ArgumentParser(description="Compare rsID overlap between ClinVar sources")
    parser.add_argument("--original", required=True, help="Path to original ClinVar VCF with RS entries")
    parser.add_argument("--annotated", required=True, help="Path to annotated VCF produced by pipeline")
    parser.add_argument("--output-dir", default="benchmark_speed_results", help="Directory for outputs")
    parser.add_argument("--left-label", default="ClinVar Original", help="Label for the left (original) circle in the Venn diagram")
    parser.add_argument("--right-label", default="rsID_retrieval Output", help="Label for the right (annotated) circle in the Venn diagram")
    args = parser.parse_args()

    original_path = Path(args.original)
    annotated_path = Path(args.annotated)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Parsing ClinVar VCF: {original_path}")
    original_map, line_map, headers, orig_all_variants = parse_original_vcf(original_path)
    print(f"   Loaded {sum(len(v) for v in original_map.values())} rsIDs from ClinVar ({len(orig_all_variants):,} total variants)")

    print(f"Parsing genomic mapping VCF: {annotated_path}")
    annotated_map, annot_all_variants = parse_annotated_vcf(annotated_path)
    print(f"   Loaded {sum(len(v) for v in annotated_map.values())} rsIDs from genomic mapping ({len(annot_all_variants):,} total variants)")

    print("Computing rsID overlap...")
    summary, original_only_variants = build_overlap(original_map, annotated_map, orig_all_variants, annot_all_variants)
    print(f"   Overlap: {summary['count_overlap_variants']:,} variants total")
    print(f"     ├─ rsID match:     {summary['count_rsid_overlap_variants']:,}")
    print(f"     └─ mutual NORSID:  {summary['count_mutual_norsid_variants']:,}")
    print(f"   ClinVar-only: {summary['count_clinvar_only_variants']:,} | Genomic-only: {summary['count_genomic_only_variants']:,}")

    vcf_output_path = output_dir / "clinvar_original_only.vcf"
    print("Writing ClinVar-only VCF slice...")
    vcf_entries = write_original_only_vcf(headers, line_map, original_only_variants, vcf_output_path)
    summary["clinvar_only_vcf"] = {
        "path": str(vcf_output_path),
        "variant_records": vcf_entries,
    }

    summary_path = output_dir / "rsid_overlap_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"✓ Summary saved to {summary_path}")

    venn_path = output_dir / "rsid_overlap_venn.png"
    render_venn(summary, venn_path, left_label=args.left_label, right_label=args.right_label)
    print(f"✓ Venn diagram saved to {venn_path}")


if __name__ == "__main__":
    main()
