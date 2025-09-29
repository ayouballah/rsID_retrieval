import sys
import os
import pandas as pd
import argparse
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QLineEdit, 
    QLabel, QComboBox, QWidget, QMessageBox, QTextEdit, QProgressBar
)
import time
from Bio import Entrez
from tqdm import tqdm
import json
import shutil
import concurrent.futures
import threading

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file)

def modify_vcf_ces1p1_ces1(input_vcf, output_vcf, pos_modifier=55758218):
    with open(input_vcf, 'r') as file:
        lines = file.readlines()
        header_lines = [line for line in lines if line.startswith('##')]
        column_header_line = lines[len(header_lines)]
        column_headers = column_header_line.strip().split('\t')
        data_lines = lines[len(header_lines) + 1:]

    data = [line.strip().split('\t') for line in data_lines]
    df = pd.DataFrame(data, columns=column_headers)
    df['POS'] = df['POS'].astype(int) + pos_modifier

    with open(output_vcf, 'w') as file:
        file.writelines(header_lines)
        file.write(column_header_line)
        for _, row in df.iterrows():
            file.write('\t'.join(row.astype(str)) + '\n')

    print(f"VCF file modified successfully. Output saved to {output_vcf}")

def modify_vcf_ces1a2_ces1(input_vcf, output_vcf):
    """
    Modify the POS field in a VCF file based on specific criteria.

    This function reads an input VCF file, adjusts the POS (position) values according to a predefined
    lambda function, and writes the modified data to an output VCF file. The modification involves
    adding a positional modifier if the original POS is less than 2358 or subtracting from a base
    value if the POS is greater than 32634. Positions that do not meet these criteria remain unchanged.

    Parameters:
        input_vcf (str): Path to the input VCF file to be modified.
        output_vcf (str): Path where the modified VCF file will be saved.

    Returns:
        None
    """
    # Position modification constants for CES1A2-CES1 mapping
    LOW_POS_THRESHOLD = 2358
    HIGH_POS_THRESHOLD = 32634
    BASE_OFFSET = 55758218
    HIGH_OFFSET_BASE = 55834270
    HIGH_OFFSET_SUBTRACT = 72745
    
    with open(input_vcf, 'r') as file:
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

    with open(output_vcf, 'w') as file:
        file.writelines(header_lines)
        file.write(column_header_line)
        for _, row in df.iterrows():
            file.write('\t'.join(row.astype(str)) + '\n')

    print(f"VCF file modified successfully. Output saved to {output_vcf}")

def clean_vcf(input_vcf, output_vcf): 
    """
    Clean a VCF file by selecting specific columns and ensuring proper chromosome format.

    This function reads an input VCF file, retains only the columns CHROM, POS, ID, REF, ALT, QUAL,
    and SAMPLE, ensures the CHROM field uses the correct RefSeq format for the API, and writes 
    the cleaned data to an output VCF file.

    Parameters:
        input_vcf (str): Path to the input VCF file to be cleaned.
        output_vcf (str): Path where the cleaned VCF file will be saved.

    Returns:
        None
    """
    try:
        # Read the VCF file preserving header information
        with open(input_vcf, 'r') as file:
            lines = file.readlines()
            header_lines = [line for line in lines if line.startswith('##')]
        
        # Read data section
        vcf = pd.read_csv(input_vcf, comment='#', sep='\t', header=None, dtype=str)
        vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
        
        # Select required columns
        vcf_cleaned = vcf[['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']].copy()
        
        # Ensure proper chromosome format for NCBI API
        # The API requires RefSeq accession format (NC_000016.10) for chromosome 16
        vcf_cleaned['CHROM'] = 'NC_000016.10'  # Use the current RefSeq accession for chr16
        
        # Write the cleaned VCF with proper headers
        with open(output_vcf, 'w') as outfile:
            # Write VCF format header
            outfile.write("##fileformat=VCFv4.2\n")
            outfile.write("##contig=<ID=NC_000016.10,length=90354753>\n")
            outfile.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tSAMPLE\n")
            
            # Write data
            vcf_cleaned.to_csv(outfile, sep='\t', index=False, header=False)
        
        print(f"Cleaned VCF file saved to {output_vcf}")
        print(f"Format: Chromosome set to NC_000016.10 for API compatibility")
        
    except Exception as e:
        print(f"Error cleaning VCF file: {e}")
        # Fallback to original method if new method fails
        try:
            vcf = pd.read_csv(input_vcf, comment='#', sep='\t', header=None, dtype=str)
            vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
            vcf_cleaned = vcf[['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']]
            vcf_cleaned['CHROM'] = 'NC_000016.10'
            vcf_cleaned.to_csv(output_vcf, sep='\t', index=False, header=False)
            print(f"Cleaned VCF file saved to {output_vcf} (fallback method)")
        except Exception as e2:
            print(f"Both cleaning methods failed: {e2}")

# Global rate limiter for Entrez API calls - balanced for speed and reliability
_rate_limiter = threading.Semaphore(4)  # Reduced from 5 to 4 to avoid 429 errors
_last_request_time = threading.local()

def fetch_rsid_entrez(chromosome, position):
    """
    Fetch rsID(s) from NCBI Entrez for a given chromosome and position.
    Thread-safe version with rate limiting.

    This function queries the NCBI Entrez SNP database to retrieve rsID(s) associated with the
    specified chromosome and position. It constructs a search query, performs the search, and
    returns a comma-separated string of rsIDs if found. If no rsIDs are found or an error occurs,
    the function returns None.

    Parameters:
        chromosome (str): The chromosome identifier (for us is specifically "16").
        position (int): The genomic position on the chromosome.

    Returns:
        str or None: A comma-separated string of rsIDs if found, otherwise None.
    """
    # Handle different chromosome formats
    if chromosome.startswith("NC_"):
        # Extract chromosome number from RefSeq format (e.g., NC_000016.10 -> 16)
        chrom_num = chromosome.replace("NC_0000", "").split(".")[0]
    else:
        chrom_num = str(chromosome)
    
    query = f"{chrom_num}[CHR] AND {position}[POS]"
    
    # Rate limiting - optimized for speed while avoiding 429 errors
    with _rate_limiter:
        try:
            # Balanced timing to maximize throughput without rate limiting
            if hasattr(_last_request_time, 'value'):
                time_since_last = time.time() - _last_request_time.value
                if time_since_last < 0.3:  # Slightly increased from 0.25 to 0.3 for stability
                    time.sleep(0.3 - time_since_last)
            
            _last_request_time.value = time.time()
            
            # Ensure email is set for Entrez
            if not Entrez.email:
                return None
                
            handle = Entrez.esearch(db="snp", term=query, retmax=20)  # Increased from 10 to 20 results
            record = Entrez.read(handle)
            handle.close()

            if record["IdList"]:
                rsids = [f"rs{rsid}" for rsid in record["IdList"]]
                result = ','.join(rsids)
                return result
            else:
                return None
                
        except Exception as e:
            return None

def fetch_rsid_batch(batch_data):
    """
    Process a batch of variants for rsID lookup.
    
    Parameters:
        batch_data: tuple of (batch_index, variants_list)
        
    Returns:
        tuple: (batch_index, results_list)
    """
    batch_idx, variants = batch_data
    results = []
    
    for variant_idx, (chromosome, position, current_id) in variants:
        if current_id == "." or current_id == "NORSID":
            rsid = fetch_rsid_entrez(chromosome, position)
            results.append((variant_idx, rsid if rsid else "NORSID"))
        else:
            results.append((variant_idx, current_id))  # Keep existing rsID
    
    return batch_idx, results



def annotate_vcf_with_entrez(input_vcf_path, final_output_vcf_path, progress_callback):
    """
    Annotate VCF using NCBI Entrez API with parallel processing.
    
    Parameters:
        input_vcf_path (str): Path to the input VCF file to be annotated.
        final_output_vcf_path (str): Path where the annotated VCF file will be saved.
        progress_callback (callable): A function to update the progress bar (expects an integer).
    
    Returns:
        None
    """
    print("Annotating VCF using NCBI Entrez API (parallel processing)...")
    
    try:
        # Copy the input VCF to output as starting point
        shutil.copy2(input_vcf_path, final_output_vcf_path)
        
        # Process all entries with Entrez API
        with open(input_vcf_path, 'r') as file:
            lines = file.readlines()
            header_lines = [line for line in lines if line.startswith('#')]
            data_lines = [line.strip() for line in lines if not line.startswith('#') and line.strip()]
        
        # Parse the data lines properly
        vcf_data = []
        for line in data_lines:
            parts = line.split('\t')
            # Ensure we have exactly 7 columns (CHROM, POS, ID, REF, ALT, QUAL, SAMPLE)
            if len(parts) >= 7:
                vcf_data.append(parts[:7])  # Take only first 7 columns
            elif len(parts) >= 6:
                vcf_data.append(parts + [''])  # Add empty SAMPLE if missing
            else:
                continue  # Skip malformed lines
        
        if not vcf_data:
            print("No valid variant data found in VCF file")
            return
            
        vcf = pd.DataFrame(vcf_data, columns=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "SAMPLE"])
        total_rows = vcf.shape[0]
        annotated_count = 0
        
        # Check if we're in GUI mode or CLI mode
        is_cli_mode = progress_callback is None or (hasattr(progress_callback, '__name__') and progress_callback.__name__ == '<lambda>')
        
        # Prepare batches for parallel processing (optimized batch size for speed)
        batch_size = 2  # Smaller batches = more parallelism
        batches = []
        
        for i in range(0, total_rows, batch_size):
            batch_variants = []
            for j in range(i, min(i + batch_size, total_rows)):
                row = vcf.iloc[j]
                batch_variants.append((j, (row['CHROM'], row['POS'], row['ID'])))
            batches.append((i // batch_size, batch_variants))
        
        if is_cli_mode:
            # Use tqdm for command line interface showing variants instead of batches
            progress_bar = tqdm(total=total_rows, desc="Annotating variants", 
                              unit="variant", bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} variants [{elapsed}<{remaining}, {rate_fmt}]',
                              leave=True)
        
        # Process batches in parallel with optimized worker count (balanced)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all batches for processing
            future_to_batch = {executor.submit(fetch_rsid_batch, batch): batch[0] 
                             for batch in batches}
            
            completed_batches = 0
            batch_results = {}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_idx, results = future.result()
                    batch_results[batch_idx] = results
                    completed_batches += 1
                    
                    # Count newly annotated variants in this batch
                    for variant_idx, rsid in results:
                        if rsid.startswith('rs') and vcf.iloc[variant_idx]['ID'] in ['.', 'NORSID']:
                            annotated_count += 1
                    
                    if is_cli_mode:
                        # Update progress by the number of variants in this batch
                        variants_in_batch = len(results)
                        progress_bar.set_postfix(annotated=annotated_count)
                        progress_bar.update(variants_in_batch)
                    elif progress_callback:
                        progress_callback(int(completed_batches / len(batches) * 100))
                        
                except Exception as e:
                    print(f"Batch {batch_idx} failed: {e}")
                    # Create dummy results for failed batch
                    batch_results[batch_idx] = [(i, "NORSID") for i in range(batch_idx * batch_size, 
                                                                            min((batch_idx + 1) * batch_size, total_rows))]
        
        # Close progress bar for CLI mode
        if is_cli_mode:
            progress_bar.close()
        
        # Apply results back to DataFrame
        for batch_idx in sorted(batch_results.keys()):
            for variant_idx, rsid in batch_results[batch_idx]:
                vcf.at[variant_idx, 'ID'] = rsid
        
        # Write the annotated VCF
        with open(input_vcf_path, 'r') as original:
            lines = original.readlines()
            header_lines = [line for line in lines if line.startswith('#')]
        
        with open(final_output_vcf_path, 'w') as output:
            output.writelines(header_lines)
            # Write data without extra columns, ensuring proper formatting
            for _, row in vcf.iterrows():
                # Only write the essential 7 columns: CHROM, POS, ID, REF, ALT, QUAL, SAMPLE
                line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                           str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
                output.write('\t'.join(line_data) + '\n')
        
        print(f"Parallel Entrez annotation complete. {annotated_count}/{total_rows} variants annotated.")
        print(f"Annotated VCF saved to {final_output_vcf_path}")
        
    except Exception as e:
        print(f"An error occurred during parallel Entrez annotation: {e}")
        # Fallback to sequential processing
        print("Falling back to sequential processing...")
        annotate_vcf_with_entrez_sequential(input_vcf_path, final_output_vcf_path, progress_callback)

def annotate_vcf_with_entrez_sequential(input_vcf_path, final_output_vcf_path, progress_callback):
    """
    Sequential fallback method for VCF annotation using NCBI Entrez API.
    Used when parallel processing fails.
    """
    print("Using sequential Entrez annotation (fallback)...")
    
    try:
        # Process all entries with Entrez API sequentially
        with open(input_vcf_path, 'r') as file:
            lines = file.readlines()
            header_lines = [line for line in lines if line.startswith('#')]
            data_lines = [line.strip() for line in lines if not line.startswith('#') and line.strip()]
        
        # Parse the data lines properly
        vcf_data = []
        for line in data_lines:
            parts = line.split('\t')
            if len(parts) >= 7:
                vcf_data.append(parts[:7])
            elif len(parts) >= 6:
                vcf_data.append(parts + [''])
            else:
                continue
        
        if not vcf_data:
            print("No valid variant data found in VCF file")
            return
            
        vcf = pd.DataFrame(vcf_data, columns=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "SAMPLE"])
        total_rows = vcf.shape[0]
        annotated_count = 0
        
        is_cli_mode = progress_callback is None or (hasattr(progress_callback, '__name__') and progress_callback.__name__ == '<lambda>')
        
        if is_cli_mode:
            progress_bar = tqdm(total=total_rows, desc="Sequential annotation", 
                              unit="variant", ascii=True, leave=False)
        
        for idx in range(total_rows):
            row = vcf.iloc[idx]
            if row['ID'] == "." or row['ID'] == "NORSID":
                rsid = fetch_rsid_entrez(row['CHROM'], row['POS'])
                
                if not rsid:
                    rsid = "NORSID"
                
                vcf.at[idx, 'ID'] = rsid
                if rsid != "NORSID":
                    annotated_count += 1
                
                time.sleep(0.1)  # Rate limiting
            
            if is_cli_mode:
                progress_bar.set_postfix(annotated=annotated_count)
                progress_bar.update(1)
            elif not is_cli_mode and (idx % 10 == 0 or idx == total_rows - 1):
                progress_callback(int((idx + 1) / total_rows * 100))
        
        if is_cli_mode:
            progress_bar.close()
        
        # Write the annotated VCF
        with open(input_vcf_path, 'r') as original:
            lines = original.readlines()
            header_lines = [line for line in lines if line.startswith('#')]
        
        with open(final_output_vcf_path, 'w') as output:
            output.writelines(header_lines)
            for _, row in vcf.iterrows():
                line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                           str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
                output.write('\t'.join(line_data) + '\n')
        
        print(f"Sequential annotation complete. {annotated_count}/{total_rows} variants annotated.")
        print(f"Annotated VCF saved to {final_output_vcf_path}")
        
    except Exception as e:
        print(f"Sequential annotation also failed: {e}")


def filter_rsids_vcf(final_output_vcf, filtered_rsids_vcf):
    """
    Filters the final annotated VCF to include only entries with rsIDs.
    """
    try:
        print("Filtering VCF to include only variants with rsIDs...")
        vcf = pd.read_csv(final_output_vcf, comment='#', sep='\t', header=None, dtype=str)
        vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']
        
        # Filter entries where ID starts with 'rs'
        filtered_vcf = vcf[vcf['ID'].str.startswith('rs')]
        
        # Write clean VCF without extra columns
        with open(filtered_rsids_vcf, 'w') as output:
            for _, row in filtered_vcf.iterrows():
                line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                           str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
                output.write('\t'.join(line_data) + '\n')
        
        print(f"Filtered rsIDs VCF saved to {filtered_rsids_vcf}")
        print(f"Found {len(filtered_vcf)} variants with rsIDs out of {len(vcf)} total variants")
    except Exception as e:
        print(f"An error occurred while filtering rsIDs: {e}")

def filter_significant_rsids(filtered_rsids_vcf, significant_rsids_vcf, qual_threshold=20.0):
    """
    Filters the filtered rsIDs VCF to include only entries with QUAL >= qual_threshold.
    """
    try:
        print(f"Filtering rsIDs VCF for variants with QUAL >= {qual_threshold}...")
        vcf = pd.read_csv(filtered_rsids_vcf, comment='#', sep='\t', header=None, dtype=str)
        vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']
        
        # Convert QUAL to float for comparison
        vcf['QUAL'] = vcf['QUAL'].astype(float)
        
        # Filter based on QUAL score
        significant_vcf = vcf[vcf['QUAL'] >= qual_threshold]
        
        # Write clean VCF without extra columns
        with open(significant_rsids_vcf, 'w') as output:
            for _, row in significant_vcf.iterrows():
                line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                           str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
                output.write('\t'.join(line_data) + '\n')
        
        print(f"Significant rsIDs VCF saved to {significant_rsids_vcf}")
        print(f"Found {len(significant_vcf)} high-quality variants out of {len(vcf)} variants with rsIDs")
    except Exception as e:
        print(f"An error occurred while filtering significant rsIDs: {e}")

def generate_summary_report(final_output_vcf, summary_report_path):
    """
    Generates a summary report based on the final annotated VCF file.
    
    Parameters:
    - final_output_vcf (str): Path to the final annotated VCF file.
    - summary_report_path (str): Path to save the summary report.
    """
    try:
        vcf = pd.read_csv(final_output_vcf, comment='#', sep='\t', header=None, dtype=str)
        base_name = os.path.splitext(os.path.basename(final_output_vcf))[0].replace("_final_annotation", "")
    
        total_variants = vcf.shape[0]
        
        # rsID is in the 3rd column (index 2)
        with_rsid = vcf[vcf[2].str.startswith('rs')].shape[0]
        without_rsid = total_variants - with_rsid
        
        # Quality is in the 6th column (index 5)
        reliable_variants = vcf[(vcf[2].str.startswith('rs')) & (vcf[5].astype(float) >= 20)].shape[0]
    
        # Write the summary to the report file
        with open(summary_report_path, 'w') as report_file:
            report_file.write(f"Summary Report for {base_name}\n")
            report_file.write(f"Total variants analyzed: {total_variants}\n")
            report_file.write(f"Variants with an rsID: {with_rsid}\n")
            report_file.write(f"Variants without an rsID: {without_rsid}\n")
            report_file.write(f"Reliable variants (QUAL equal or higher than 20): {reliable_variants}\n")
    
        print(f"Summary report saved to {summary_report_path}")
    except Exception as e:
        print(f"An error occurred while generating summary report: {e}")

def test_entrez():
    Entrez.email = "your_email@example.com"  # Replace with your email
    try:
        handle = Entrez.esearch(db="snp", term="16[CHR] AND 123456[POS]")
        record = Entrez.read(handle)
        handle.close()
        print(f"Entrez test successful: {record}")
    except Exception as e:
        print(f"An error occurred during Entrez test: {e}")



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("rsID Retrieval")
        self.setGeometry(100, 100, 600, 600)
        
        layout = QVBoxLayout()
        
        self.input_vcf_label = QLabel("Input VCF File:")
        layout.addWidget(self.input_vcf_label)
        self.input_vcf_edit = QLineEdit()
        layout.addWidget(self.input_vcf_edit)
        self.input_vcf_button = QPushButton("Browse")
        self.input_vcf_button.clicked.connect(self.browse_input_vcf)
        layout.addWidget(self.input_vcf_button)

        self.output_dir_label = QLabel("Output Directory:")
        layout.addWidget(self.output_dir_label)
        self.output_dir_edit = QLineEdit()
        layout.addWidget(self.output_dir_edit)
        self.output_dir_button = QPushButton("Browse")
        self.output_dir_button.clicked.connect(self.browse_output_dir)
        layout.addWidget(self.output_dir_button)

        self.email_label = QLabel("Email:")
        layout.addWidget(self.email_label)
        self.email_edit = QLineEdit()
        layout.addWidget(self.email_edit)

        self.type_label = QLabel("Modification Type:")
        layout.addWidget(self.type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["CES1P1-CES1", "CES1A2-CES1"])
        layout.addWidget(self.type_combo)

        self.pos_modifier_label = QLabel("Position Modifier (for CES1P1-CES1):")
        layout.addWidget(self.pos_modifier_label)
        self.pos_modifier_edit = QLineEdit()
        self.pos_modifier_edit.setText("55758218")
        layout.addWidget(self.pos_modifier_edit)

        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_modification)
        layout.addWidget(self.run_button)

        self.command_label = QLabel("Command:")
        layout.addWidget(self.command_label)
        self.command_display = QTextEdit()
        self.command_display.setReadOnly(True)
        layout.addWidget(self.command_display)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.load_email()

    def load_email(self):
        config = load_config()
        email = config.get("email", "")
        self.email_edit.setText(email)
        Entrez.email = email

    def save_email(self):
        email = self.email_edit.text()
        config = load_config()
        config["email"] = email
        save_config(config)
        Entrez.email = email

    def browse_input_vcf(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open VCF File", "", "VCF Files (*.vcf);;All Files (*)")
        if file_name:
            self.input_vcf_edit.setText(file_name)

    def browse_output_dir(self):
        dir_name = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_name:
            self.output_dir_edit.setText(dir_name)

    def run_modification(self):
        self.save_email()
        input_vcf = self.input_vcf_edit.text()
        output_dir = self.output_dir_edit.text()
        modification_type = self.type_combo.currentText()
        pos_modifier = int(self.pos_modifier_edit.text())

        if not input_vcf or not output_dir:
            QMessageBox.warning(self, "Input Error", "Please specify both input VCF file and output directory.")
            return

        base_name = os.path.splitext(os.path.basename(input_vcf))[0]
        results_subdir = os.path.join(output_dir, f"{base_name}_results")
        os.makedirs(results_subdir, exist_ok=True)

        # Define all output file paths within the results subdirectory
        final_output_vcf = os.path.join(results_subdir, f"{base_name}_final_annotation.vcf")
        filtered_rsids_vcf = os.path.join(results_subdir, f"{base_name}_filtered_rsids.vcf")
        no_rsids_vcf = os.path.join(results_subdir, f"{base_name}_no_rsids.vcf")
        significant_rsids_vcf = os.path.join(results_subdir, f"{base_name}_significant_rsids.vcf")
        summary_report = os.path.join(results_subdir, f"summary_report_for_{base_name}.txt")

        email = self.email_edit.text()

        # Build the command string for display
        command = f"python rsID_retrieval.py --input_vcf \"{input_vcf}\" --output_dir \"{results_subdir}\" --type {modification_type} --email \"{email}\""
        if modification_type == "CES1P1-CES1":
            command += f" --pos_modifier {pos_modifier}"

        self.command_display.setText(command)
        try:
            # Modify VCF based on the selected type
            if modification_type == "CES1P1-CES1":
                modify_vcf_ces1p1_ces1(input_vcf, no_rsids_vcf, pos_modifier)
            elif modification_type == "CES1A2-CES1":
                modify_vcf_ces1a2_ces1(input_vcf, no_rsids_vcf)

            # Clean the modified VCF
            clean_vcf(no_rsids_vcf, no_rsids_vcf)  # Saving over itself as it's already cleaned

            # Annotate VCF with all rsIDs using Entrez API
            annotate_vcf_with_entrez(no_rsids_vcf, final_output_vcf, self.update_progress)

            # Filter to include only rsIDs
            filter_rsids_vcf(final_output_vcf, filtered_rsids_vcf)

            # Filter significant rsIDs
            filter_significant_rsids(filtered_rsids_vcf, significant_rsids_vcf)

            # Generate summary report
            generate_summary_report(final_output_vcf, summary_report)

            QMessageBox.information(self, "Success", f"VCF files processed successfully. Summary report saved to {summary_report}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify, clean, and annotate a VCF file.")
    parser.add_argument("--input_vcf", type=str, help="Path to the input VCF file")
    parser.add_argument("--output_dir", type=str, help="Path to save the final annotated VCF files")
    parser.add_argument("--email", type=str, help="Email required by Entrez to initialize the search process")
    parser.add_argument("--type", type=str, choices=["CES1P1-CES1", "CES1A2-CES1"], help="Type of position modification")
    parser.add_argument("--pos_modifier", type=int, default=55758218, help="Value to add to each POS entry (only for CES1P1-CES1)")

    args = parser.parse_args()

    if len(sys.argv) > 1:
        if args.input_vcf and args.output_dir and args.type and args.email:
            input_vcf = args.input_vcf
            output_dir = args.output_dir
            modification_type = args.type
            pos_modifier = args.pos_modifier
            email = args.email
            base_name = os.path.splitext(os.path.basename(input_vcf))[0]
            results_subdir = os.path.join(output_dir, f"{base_name}_results")
            os.makedirs(results_subdir, exist_ok=True)

            # Define all output file paths within the results subdirectory
            final_output_vcf = os.path.join(results_subdir, f"{base_name}_final_annotation.vcf")
            filtered_rsids_vcf = os.path.join(results_subdir, f"{base_name}_filtered_rsids.vcf")
            no_rsids_vcf = os.path.join(results_subdir, f"{base_name}_no_rsids.vcf")
            significant_rsids_vcf = os.path.join(results_subdir, f"{base_name}_significant_rsids.vcf")
            summary_report_path = os.path.join(results_subdir, f"summary_report_for_{base_name}.txt")

            try:
                # Modify VCF based on the selected type
                if modification_type == "CES1P1-CES1":
                    modify_vcf_ces1p1_ces1(input_vcf, no_rsids_vcf, pos_modifier)
                elif modification_type == "CES1A2-CES1":
                    modify_vcf_ces1a2_ces1(input_vcf, no_rsids_vcf)

                # Set Entrez email before any API operations
                Entrez.email = email

                # Clean the modified VCF
                clean_vcf(no_rsids_vcf, no_rsids_vcf)  # Saving over itself as it's already cleaned

                # Annotate VCF with all rsIDs using Entrez API
                print(f"Starting parallel annotation of {final_output_vcf}...")
                annotate_vcf_with_entrez(no_rsids_vcf, final_output_vcf, None)  # Use None for CLI mode

                # Filter to include only rsIDs
                filter_rsids_vcf(final_output_vcf, filtered_rsids_vcf)

                # Filter significant rsIDs
                filter_significant_rsids(filtered_rsids_vcf, significant_rsids_vcf)

                # Generate summary report
                generate_summary_report(final_output_vcf, summary_report_path)

                print("VCF files processed successfully.")
                print(f"Summary report saved to {summary_report_path}")
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print("Error: Missing required arguments for command-line mode.")
            parser.print_help()
    else:
        # Test Entrez functionality
        test_entrez()

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())