#!/usr/bin/env python3
"""Split a VCF into separate files per chromosome (1..21).

Usage:
  python scripts/split_vcf_by_chromosome.py --input_vcf <input.vcf> --output_dir <outdir>

Features:
 - Preserves all header lines (lines starting with '#') in each output file
 - Normalizes chromosome identifiers like 'chr1', '1', 'NC_000016.10' -> '16'
 - Writes only chromosomes 1 through 21 by default (configurable)
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional


def normalize_chrom(chrom: str) -> Optional[str]:
    """Normalize chromosome string to a numeric string for autosomes 1-21.

    Returns the chromosome number as a string if between 1 and 21, otherwise None.
    Examples handled: 'chr1' -> '1', '1' -> '1', 'NC_000016.10' -> '16'
    """
    if not chrom:
        return None
    chrom = chrom.strip()
    # Remove common prefix
    if chrom.lower().startswith('chr'):
        chrom = chrom[3:]

    # RefSeq pattern like NC_000016.10 -> extract digits
    if chrom.upper().startswith('NC_'):
        nums = re.findall(r"(\d+)", chrom)
        if nums:
            # usually the last group contains the chromosome number or 000016
            # choose the last and strip leading zeros
            val = nums[-1].lstrip('0') or '0'
            try:
                n = int(val)
            except ValueError:
                return None
            if 1 <= n <= 21:
                return str(n)
            return None

    # Mitochondrial or sex chromosomes -> ignore for 1..21
    if chrom.upper() in ('X', 'Y', 'M', 'MT'):
        return None

    # If it's numeric (possibly with leading zeros)
    m = re.match(r"^0*(\d+)$", chrom)
    if m:
        try:
            n = int(m.group(1))
        except ValueError:
            return None
        if 1 <= n <= 21:
            return str(n)
        return None

    # Fallback: try to extract any number
    nums = re.findall(r"(\d+)", chrom)
    if nums:
        val = nums[-1].lstrip('0') or '0'
        try:
            n = int(val)
        except ValueError:
            return None
        if 1 <= n <= 21:
            return str(n)

    return None


def split_vcf(input_vcf: Path, output_dir: Path, chromosomes: Iterable[int] = range(1, 22)) -> List[Path]:
    """Split input VCF into per-chromosome files for given chromosome numbers.

    Returns list of output file paths created.
    """
    input_vcf = Path(input_vcf)
    output_dir = Path(output_dir)
    if not input_vcf.exists():
        raise FileNotFoundError(f"Input VCF not found: {input_vcf}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare output file handles
    chrom_set = {str(c) for c in chromosomes}
    out_handles = {}
    out_paths = {}

    headers: List[str] = []

    with input_vcf.open('r', encoding='utf-8') as fh:
        for line in fh:
            if line.startswith('#'):
                headers.append(line)
                continue
            # data line
            parts = line.rstrip('\n').split('\t')
            if not parts:
                continue
            chrom_raw = parts[0]
            chrom = normalize_chrom(chrom_raw)
            if chrom is None or chrom not in chrom_set:
                continue
            # open file handle if needed
            if chrom not in out_handles:
                out_path = output_dir / f"{input_vcf.stem}_chr{chrom}.vcf"
                out_paths[chrom] = out_path
                out_handles[chrom] = out_path.open('w', encoding='utf-8')
                # write headers
                for h in headers:
                    out_handles[chrom].write(h)
            out_handles[chrom].write(line)

    # Close handles
    for h in out_handles.values():
        h.close()

    return list(out_paths.values())


def parse_chromosomes_option(option: Optional[str]) -> List[int]:
    """Parse chromosomes option like '1-21' or '1,2,5' into list of ints."""
    if not option:
        return list(range(1, 22))
    option = option.strip()
    if '-' in option:
        a, b = option.split('-', 1)
        return list(range(int(a), int(b) + 1))
    parts = [p.strip() for p in option.split(',') if p.strip()]
    return [int(p) for p in parts]


def main():
    parser = argparse.ArgumentParser(description="Split VCF by chromosome (1..21)")
    parser.add_argument('--input_vcf', required=True, help='Path to input VCF')
    parser.add_argument('--output_dir', required=True, help='Directory for per-chromosome VCFs')
    parser.add_argument('--chromosomes', required=False, help='Chromosomes to extract (e.g. "1-21" or "1,2,3")')
    args = parser.parse_args()

    input_vcf = Path(args.input_vcf)
    output_dir = Path(args.output_dir)
    chromosomes = parse_chromosomes_option(args.chromosomes)

    created = split_vcf(input_vcf, output_dir, chromosomes)
    if created:
        print(f"Created {len(created)} files:")
        for p in created:
            print(f" - {p}")
    else:
        print("No chromosome files were created. Check input VCF and chromosome identifiers.")


if __name__ == '__main__':
    main()
