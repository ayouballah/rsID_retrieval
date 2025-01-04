import sys
import os
import pandas as pd
import argparse
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QLineEdit, 
    QLabel, QComboBox, QWidget, QMessageBox, QCheckBox, QTextEdit, QProgressBar
)
import time
from Bio import Entrez
from tqdm import tqdm
import json
import shutil

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
    with open(input_vcf, 'r') as file:
        lines = file.readlines()
        header_lines = [line for line in lines if line.startswith('##')]
        column_header_line = lines[len(header_lines)]
        column_headers = column_header_line.strip().split('\t')
        data_lines = lines[len(header_lines) + 1:]

    data = [line.strip().split('\t') for line in data_lines]
    df = pd.DataFrame(data, columns=column_headers)
    df['POS'] = df['POS'].astype(int)
    df['POS'] = df['POS'].apply(lambda x: 55758218 + x if x < 2358 else 55834270 - (72745 - x) if x > 32634 else x)  # Modify as needed for your own application 
    #TODO : remove magic numbers ✨  

    with open(output_vcf, 'w') as file:
        file.writelines(header_lines)
        file.write(column_header_line)
        for _, row in df.iterrows():
            file.write('\t'.join(row.astype(str)) + '\n')

    print(f"VCF file modified successfully. Output saved to {output_vcf}")

def clean_vcf(input_vcf, output_vcf): 
    """
    Clean a VCF file by selecting specific columns and modifying the chromosome identifier.

    This function reads an input VCF file, retains only the columns CHROM, POS, ID, REF, ALT, QUAL,
    and SAMPLE, modifies the CHROM field to a specified value, and writes the cleaned data to an
    output VCF file.

    Parameters:
        input_vcf (str): Path to the input VCF file to be cleaned.
        output_vcf (str): Path where the cleaned VCF file will be saved.

    Returns:
        None
    """
    vcf = pd.read_csv(input_vcf, comment='#', sep='\t', header=None, dtype=str)
    vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
    vcf_cleaned = vcf[['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'SAMPLE']]
    vcf_cleaned['CHROM'] = 'NC_000016.10'  # Modify if needed
    vcf_cleaned.to_csv(output_vcf, sep='\t', index=False, header=False)
    print(f"Cleaned VCF file saved to {output_vcf}")

def fetch_rsid_entrez(chromosome, position):
    """
    Fetch rsID(s) from NCBI Entrez for a given chromosome and position.

    This function queries the NCBI Entrez SNP database to retrieve rsID(s) associated with the
    specified chromosome and position. It constructs a search query, performs the search, and
    returns a comma-separated string of rsIDs if found. If no rsIDs are found or an error occurs,
    the function returns None.

    Parameters:
        chromosome (str): The chromosome identifier (for us is specifically "16").TODO make it depentant using regular expression
        position (int): The genomic position on the chromosome.

    Returns:
        str or None: A comma-separated string of rsIDs if found, otherwise None.
    """
    chromosome = chromosome.replace("NC_0000", "").split(".")[0]  # Modify if needed  
    query = f"{chromosome}[CHR] AND {position}[POS]"
    
    try:
        handle = Entrez.esearch(db="snp", term=query)
        record = Entrez.read(handle)
        handle.close()

        if record["IdList"]:
            rsids = [f"rs{rsid}" for rsid in record["IdList"]]
            return ','.join(rsids)  
        else:
            return None
    except Exception as e:
        print(f"An error occurred while fetching rsID: {e}")
        return None

def process_norsid_entries(annotated_vcf_path, output_vcf_path, progress_callback):
    """
    Annotate a VCF file with rsIDs using the NCBI Entrez API.

    This function uploads the input VCF file to the NCBI Entrez API to retrieve rsID annotations.
    Upon successful annotation, it saves the annotated VCF to the specified output path and
    further processes any entries with missing rsIDs.

    Parameters:
        input_vcf_path (str): Path to the input VCF file to be annotated.
        final_output_vcf_path (str): Path where the annotated VCF file will be saved.
        progress_callback (callable): A function to update the progress bar (expects an integer).

    Returns:
        None
    """
    processed_norsid_vcf = output_vcf_path.replace("_final_annotation.vcf", "_norsid_processed.vcf")
    try:
        vcf = pd.read_csv(annotated_vcf_path, sep='\t', comment='#', header=None, dtype=str, 
                          names=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", "SAMPLE"])
        
        total_rows = vcf.shape[0]
        for idx, row in tqdm(vcf.iterrows(), total=total_rows, desc="Processing NORSID entries"):
            if row['ID'] == "NORSID" or row['ID'] == ".":  # A fallback mechanism if the first API fails
                rsid = fetch_rsid_entrez(row['CHROM'], row['POS'])
                
                if isinstance(rsid, list) or isinstance(rsid, tuple):  # If rsid is a sequence, use the first element
                    rsid = rsid[0] if rsid else "NORSID"
                elif not rsid:  # If no rsid is found, assign NORSID
                    rsid = "NORSID"
                
                vcf.at[idx, 'ID'] = rsid
                time.sleep(0.0001)  # Delay to avoid NCBI rate limits
            
            if idx % 10 == 0 or idx == total_rows - 1:
                progress_callback(int((idx + 1) / total_rows * 100))  # Update progress bar
        
        vcf.to_csv(processed_norsid_vcf, sep='\t', index=False, header=False)
        shutil.move(processed_norsid_vcf, output_vcf_path)  # Rename to final output
        print(f"Final VCF with all annotations saved to {output_vcf_path}")
    except Exception as e:
        print(f"An error occurred during processing NORSID entries: {e}")

def annotate_vcf_with_ncbi(input_vcf_path, final_output_vcf_path, progress_callback):
    url = "https://api.ncbi.nlm.nih.gov/variation/v0/vcf/file/set_rsids"
    
    try:
        with open(input_vcf_path, 'rb') as vcf_file:
            files = {'vcf_file': vcf_file}
            response = requests.post(url, files=files)
            
            if response.status_code == 200:
                with open(final_output_vcf_path, 'wb') as output_file:
                    output_file.write(response.content)
                print(f"Annotated VCF file saved to {final_output_vcf_path}")
                process_norsid_entries(final_output_vcf_path, final_output_vcf_path, progress_callback)
            else:
                print(f"Error: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"An error occurred during annotation: {e}")

def filter_rsids_vcf(final_output_vcf, filtered_rsids_vcf):
    """
    Filters the final annotated VCF to include only entries with rsIDs.
    """
    try:
        vcf = pd.read_csv(final_output_vcf, comment='#', sep='\t', header=None, dtype=str)
        vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
        
        # Filter entries where ID starts with 'rs'
        filtered_vcf = vcf[vcf['ID'].str.startswith('rs')]
        filtered_vcf.to_csv(filtered_rsids_vcf, sep='\t', index=False, header=False)
        print(f"Filtered rsIDs VCF saved to {filtered_rsids_vcf}")
    except Exception as e:
        print(f"An error occurred while filtering rsIDs: {e}")

def filter_significant_rsids(filtered_rsids_vcf, significant_rsids_vcf, qual_threshold=20.0):
    """
    Filters the filtered rsIDs VCF to include only entries with QUAL >= qual_threshold.
    """
    try:
        vcf = pd.read_csv(filtered_rsids_vcf, comment='#', sep='\t', header=None, dtype={'QUAL': float})
        vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
        
        # Filter based on QUAL score
        significant_vcf = vcf[vcf['QUAL'] >= qual_threshold]
        
        # Save the filtered VCF
        significant_vcf.to_csv(significant_rsids_vcf, sep='\t', index=False, header=False)
        print(f"Significant rsIDs VCF saved to {significant_rsids_vcf}")
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
    
        total_reads = vcf.shape[0]
        
        # rsID is in the 3rd column (index 2)
        with_rsid = vcf[vcf[2].str.startswith('rs')].shape[0]
        without_rsid = total_reads - with_rsid
        
        # Quality is in the 6th column (index 5)
        reliable_reads = vcf[(vcf[2].str.startswith('rs')) & (vcf[5].astype(float) >= 20)].shape[0]
    
        # Write the summary to the report file
        with open(summary_report_path, 'w') as report_file:
            report_file.write(f"Summary Report for {base_name}\n")
            report_file.write(f"Total reads analyzed: {total_reads}\n")
            report_file.write(f"Reads with an rsID: {with_rsid}\n")
            report_file.write(f"Reads without an rsID: {without_rsid}\n")
            report_file.write(f"Reliable reads (QUAL equal or higher than 20): {reliable_reads}\n")
    
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

            # Annotate VCF with all rsIDs
            annotate_vcf_with_ncbi(no_rsids_vcf, final_output_vcf, self.update_progress)

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

                # Clean the modified VCF
                clean_vcf(no_rsids_vcf, no_rsids_vcf)  # Saving over itself as it's already cleaned

                # Annotate VCF with all rsIDs
                annotate_vcf_with_ncbi(no_rsids_vcf, final_output_vcf, lambda x: None)  # No progress in CLI

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