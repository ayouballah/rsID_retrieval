"""
Core VCF processing and validation functions for rsID retrieval.
"""
import os
import pandas as pd
import time
import threading
from Bio import Entrez
import shutil
import concurrent.futures
from tqdm import tqdm


def validate_vcf_file(vcf_path):
    """
    Validate VCF file format and structure.
    Returns (is_valid, error_message).
    """
    if not os.path.exists(vcf_path):
        return False, f"File does not exist: {vcf_path}"
    
    if not vcf_path.lower().endswith('.vcf'):
        return False, "File must have .vcf extension"
    
    try:
        with open(vcf_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        if not lines:
            return False, "VCF file is empty"
        
        # Find header lines and column header
        header_lines = [line for line in lines if line.startswith('##')]
        
        # Find the column header line (starts with #CHROM)
        column_header_line = None
        for i, line in enumerate(lines):
            if line.startswith('#CHROM'):
                column_header_line = line
                break
        
        if not column_header_line:
            return False, "VCF file missing column header line (#CHROM)"
        
        # Validate minimum required columns
        columns = column_header_line.strip().split('\t')
        required_columns = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER']
        
        for req_col in required_columns:
            if req_col not in columns:
                return False, f"Missing required column: {req_col}"
        
        # Check if there's at least one data line
        data_start_idx = len(header_lines) + 1
        if len(lines) <= data_start_idx:
            return False, "VCF file has no data rows"
        
        # Validate first few data lines for basic format
        for i in range(min(3, len(lines) - data_start_idx)):
            data_line = lines[data_start_idx + i].strip()
            if data_line:  # Skip empty lines
                data_parts = data_line.split('\t')
                if len(data_parts) < len(required_columns):
                    return False, f"Data row {i+1} has insufficient columns ({len(data_parts)} < {len(required_columns)})"
                
                # Validate POS is numeric
                try:
                    int(data_parts[1])  # POS column
                except ValueError:
                    return False, f"Data row {i+1}: POS column must be numeric, got '{data_parts[1]}'"
        
        return True, "VCF file is valid"
        
    except Exception as e:
        return False, f"Error reading VCF file: {str(e)}"


def modify_vcf_ces1p1_ces1(input_vcf, output_vcf, pos_modifier=55758218):
    """
    Modify VCF by adding a position modifier to all positions.
    """
    # Validate input VCF file
    is_valid, error_msg = validate_vcf_file(input_vcf)
    if not is_valid:
        raise ValueError(f"Invalid input VCF file: {error_msg}")
    
    with open(input_vcf, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        header_lines = [line for line in lines if line.startswith('##')]
        column_header_line = lines[len(header_lines)]
        column_headers = column_header_line.strip().split('\t')
        data_lines = lines[len(header_lines) + 1:]

    data = [line.strip().split('\t') for line in data_lines]
    df = pd.DataFrame(data, columns=column_headers)
    df['POS'] = df['POS'].astype(int) + pos_modifier

    with open(output_vcf, 'w', encoding='utf-8') as file:
        file.writelines(header_lines)
        file.write(column_header_line)
        for _, row in df.iterrows():
            file.write('\t'.join(row.astype(str)) + '\n')

    return f"VCF file modified successfully. Output saved to {output_vcf}"


def modify_vcf_ces1a2_ces1(input_vcf, output_vcf):
    """
    Modify the POS field in a VCF file based on specific criteria.
    """
    # Validate input VCF file
    is_valid, error_msg = validate_vcf_file(input_vcf)
    if not is_valid:
        raise ValueError(f"Invalid input VCF file: {error_msg}")
    
    # Position modification constants for CES1A2-CES1 mapping
    LOW_POS_THRESHOLD = 2358
    HIGH_POS_THRESHOLD = 32634
    BASE_OFFSET = 55758218
    HIGH_OFFSET_BASE = 55834270
    HIGH_OFFSET_SUBTRACT = 72745
    
    with open(input_vcf, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        header_lines = [line for line in lines if line.startswith('##')]
        column_header_line = lines[len(header_lines)]
        column_headers = column_header_line.strip().split('\t')
        data_lines = lines[len(header_lines) + 1:]

    data = [line.strip().split('\t') for line in data_lines]
    df = pd.DataFrame(data, columns=column_headers)
    df['POS'] = df['POS'].astype(int)
    df['POS'] = df['POS'].apply(
        lambda x: BASE_OFFSET + x if x < LOW_POS_THRESHOLD 
        else HIGH_OFFSET_BASE - (HIGH_OFFSET_SUBTRACT - x) if x > HIGH_POS_THRESHOLD 
        else x
    )

    with open(output_vcf, 'w', encoding='utf-8') as file:
        file.writelines(header_lines)
        file.write(column_header_line)
        for _, row in df.iterrows():
            file.write('\t'.join(row.astype(str)) + '\n')

    return f"VCF file modified successfully. Output saved to {output_vcf}"


def clean_vcf(input_vcf, output_vcf):
    """
    Clean a VCF file by selecting specific columns and ensuring proper chromosome format.
    """
    try:
        # Read the VCF file preserving header information
        with open(input_vcf, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            header_lines = [line for line in lines if line.startswith('##')]
        
        # Read data section
        vcf = pd.read_csv(input_vcf, comment='#', sep='\t', header=None, dtype=str)
        vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
        
        # Select required columns
        vcf_cleaned = vcf[['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']].copy()
        
        # Ensure proper chromosome format for NCBI API
        vcf_cleaned['CHROM'] = 'NC_000016.10'  # Use the current RefSeq accession for chr16
        
        # Write the cleaned VCF with proper headers
        with open(output_vcf, 'w', encoding='utf-8') as outfile:
            # Write VCF format header
            outfile.write("##fileformat=VCFv4.2\n")
            outfile.write("##contig=<ID=NC_000016.10,length=90354753>\n")
            outfile.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tSAMPLE\n")
            
            # Write data
            vcf_cleaned.to_csv(outfile, sep='\t', index=False, header=False)
        
        return f"Cleaned VCF file saved to {output_vcf}"
        
    except Exception as e:
        # Fallback to original method if new method fails
        try:
            vcf = pd.read_csv(input_vcf, comment='#', sep='\t', header=None, dtype=str)
            vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
            vcf_cleaned = vcf[['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']]
            vcf_cleaned['CHROM'] = 'NC_000016.10'
            vcf_cleaned.to_csv(output_vcf, sep='\t', index=False, header=False)
            return f"Cleaned VCF file saved to {output_vcf} (fallback method)"
        except Exception as e2:
            raise Exception(f"Both cleaning methods failed: {e2}")


def filter_rsids_vcf(final_output_vcf, filtered_rsids_vcf):
    """
    Filters the final annotated VCF to include only entries with rsIDs.
    """
    vcf = pd.read_csv(final_output_vcf, comment='#', sep='\t', header=None, dtype=str)
    vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']
    
    # Filter entries where ID starts with 'rs'
    filtered_vcf = vcf[vcf['ID'].str.startswith('rs')]
    
    # Write clean VCF without extra columns
    with open(filtered_rsids_vcf, 'w', encoding='utf-8') as output:
        for _, row in filtered_vcf.iterrows():
            line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                       str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
            output.write('\t'.join(line_data) + '\n')
    
    return f"Found {len(filtered_vcf)} variants with rsIDs out of {len(vcf)} total variants"


def filter_significant_rsids(filtered_rsids_vcf, significant_rsids_vcf, qual_threshold=20.0):
    """
    Filters the filtered rsIDs VCF to include only entries with QUAL >= qual_threshold.
    """
    vcf = pd.read_csv(filtered_rsids_vcf, comment='#', sep='\t', header=None, dtype=str)
    vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']
    
    # Convert QUAL to float for comparison
    vcf['QUAL'] = vcf['QUAL'].astype(float)
    
    # Filter based on QUAL score
    significant_vcf = vcf[vcf['QUAL'] >= qual_threshold]
    
    # Write clean VCF without extra columns
    with open(significant_rsids_vcf, 'w', encoding='utf-8') as output:
        for _, row in significant_vcf.iterrows():
            line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                       str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
            output.write('\t'.join(line_data) + '\n')
    
    return f"Found {len(significant_vcf)} high-quality variants out of {len(vcf)} variants with rsIDs"


def generate_summary_report(final_output_vcf, summary_report_path):
    """
    Generates a summary report based on the final annotated VCF file.
    """
    vcf = pd.read_csv(final_output_vcf, comment='#', sep='\t', header=None, dtype=str)
    base_name = os.path.splitext(os.path.basename(final_output_vcf))[0].replace("_final_annotation", "")

    total_variants = vcf.shape[0]
    
    # rsID is in the 3rd column (index 2)
    with_rsid = vcf[vcf[2].str.startswith('rs')].shape[0]
    without_rsid = total_variants - with_rsid
    
    # Quality is in the 6th column (index 5)
    reliable_variants = vcf[(vcf[2].str.startswith('rs')) & (vcf[5].astype(float) >= 20)].shape[0]

    # Write the summary to the report file
    with open(summary_report_path, 'w', encoding='utf-8') as report_file:
        report_file.write(f"Summary Report for {base_name}\n")
        report_file.write(f"Total variants analyzed: {total_variants}\n")
        report_file.write(f"Variants with an rsID: {with_rsid}\n")
        report_file.write(f"Variants without an rsID: {without_rsid}\n")
        report_file.write(f"Reliable variants (QUAL equal or higher than 20): {reliable_variants}\n")

    return {
        'base_name': base_name,
        'total_variants': total_variants,
        'with_rsid': with_rsid,
        'without_rsid': without_rsid,
        'reliable_variants': reliable_variants
    }
