#!/usr/bin/env python3
"""
Quick throwaway script to remove rsIDs from VCF files.
Replaces all rsIDs in the ID column with '.' (missing value).
"""

import argparse
import sys


def remove_rsids_from_vcf(input_vcf, output_vcf):
    """
    Remove all rsIDs from VCF file by replacing them with '.'
    Preserves headers and all other data.
    """
    processed_variants = 0
    rsids_removed = 0
    
    with open(input_vcf, 'r', encoding='utf-8') as infile:
        with open(output_vcf, 'w', encoding='utf-8') as outfile:
            for line in infile:
                # Keep all header lines unchanged
                if line.startswith('#'):
                    outfile.write(line)
                    continue
                
                # Process data lines
                parts = line.strip().split('\t')
                if len(parts) < 3:
                    # Malformed line, keep as is
                    outfile.write(line)
                    continue
                
                processed_variants += 1
                
                # Check if ID column (index 2) has any ID (not just rsIDs)
                id_field = parts[2]
                if id_field != '.':
                    # Remove ANY ID - replace with '.'
                    parts[2] = '.'
                    rsids_removed += 1
                
                # Write modified line
                outfile.write('\t'.join(parts) + '\n')
    
    print(f"✓ Processed {processed_variants} variants")
    print(f"✓ Removed rsIDs from {rsids_removed} variants")
    print(f"✓ Output saved to: {output_vcf}")


def main():
    parser = argparse.ArgumentParser(
        description='Remove rsIDs from VCF file (replace with ".")'
    )
    parser.add_argument('--input', required=True, help='Input VCF file')
    parser.add_argument('--output', required=True, help='Output VCF file')
    
    args = parser.parse_args()
    
    try:
        remove_rsids_from_vcf(args.input, args.output)
    except FileNotFoundError:
        print(f"✗ Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
