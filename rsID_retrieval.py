import sys
import pandas as pd
import argparse
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QLineEdit, 
    QLabel, QComboBox, QWidget, QMessageBox, QCheckBox, QTextEdit,QProgressBar
)
import os
import time
from Bio import Entrez
from tqdm import tqdm
import json

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
    with open(input_vcf, 'r') as file:
        lines = file.readlines()
        header_lines = [line for line in lines if line.startswith('##')]
        column_header_line = lines[len(header_lines)]
        column_headers = column_header_line.strip().split('\t')
        data_lines = lines[len(header_lines) + 1:]

    data = [line.strip().split('\t') for line in data_lines]
    df = pd.DataFrame(data, columns=column_headers)
    df['POS'] = df['POS'].astype(int)
    df['POS'] = df['POS'].apply(lambda x: 55758218 + x if x < 2358 else 55834270 - (72745 - x) if x > 32634 else x) # the potions are specific to the lab, you  might consider changing them 

    with open(output_vcf, 'w') as file:
        file.writelines(header_lines)
        file.write(column_header_line)
        for _, row in df.iterrows():
            file.write('\t'.join(row.astype(str)) + '\n')

    print(f"VCF file modified successfully. Output saved to {output_vcf}")

def clean_vcf(input_vcf, output_vcf): 
    vcf = pd.read_csv(input_vcf, comment='#', sep='\t', header=None, dtype=str)
    vcf.columns = ['CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO', 'FORMAT', 'SAMPLE']
    vcf_cleaned = vcf[['CHROM', 'POS','ID', 'REF', 'ALT','QUAL','SAMPLE']]
    vcf_cleaned['CHROM'] = 'NC_000016.10'# please change this if you're looking at another chromosome we are looking at chromosome number 16
    vcf_cleaned.to_csv(output_vcf, sep='\t', index=False, header=False)
    print(f"Cleaned VCF file saved to {output_vcf}")

def fetch_rsid_entrez(chromosome, position):
    chromosome = chromosome.replace("NC_0000", "").split(".")[0]# entrez uses 16 as for a query so please change it as you see fit  
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

def process_norsid_entries(annotated_vcf_path, final_output_vcf_path, progress_callback):
    try:
        vcf = pd.read_csv(annotated_vcf_path, sep='\t', comment='#', header=None, dtype=str, 
                          names=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT", "SAMPLE"])
        
        total_rows = vcf.shape[0]
        for idx, row in tqdm(vcf.iterrows(), total=total_rows, desc="Processing NORSID entries"):
            if row['ID'] == "NORSID" or".":# a fail mechanism just incase the first Api stops responding properly 
                rsid = fetch_rsid_entrez(row['CHROM'], row['POS'])
                if rsid:
                    vcf.at[idx, 'ID'] = rsid
                time.sleep(0.0001)  # Delay to avoid NCBI rate limits
            
            # Only update progress bar every few steps for smoother transitions
            if idx % 10 == 0 or idx == total_rows - 1:
                progress_callback(int((idx + 1) / total_rows * 100))
        
        vcf.to_csv(final_output_vcf_path, sep='\t', index=False, header=False)
        print(f"Final VCF with all annotations saved to {final_output_vcf_path}")
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

        self.setWindowTitle("rsID_retrieval")
        self.setGeometry(100, 100, 600, 400)
        
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

        self.save_temp_checkbox = QCheckBox("Save Temporary Files")
        layout.addWidget(self.save_temp_checkbox)

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
        save_temp_files = self.save_temp_checkbox.isChecked()

        if not input_vcf or not output_dir:
            QMessageBox.warning(self, "Input Error", "Please specify both input VCF file and output directory.")
            return

        base_name = os.path.splitext(os.path.basename(input_vcf))[0]
        modified_vcf = os.path.join(output_dir, f"{base_name}_annotated_modified.vcf")
        cleaned_vcf = os.path.join(output_dir, f"{base_name}_annotated_cleaned.vcf")
        final_output_vcf = os.path.join(output_dir, f"{base_name}_final_annotation.vcf")

        email = self.email_edit.text()

        command = f"python test3.py --input_vcf \"{input_vcf}\" --output_dir \"{output_dir}\" --type {modification_type} --email \"{email}\""
        if modification_type == "CES1P1-CES1":
            command += f" --pos_modifier {pos_modifier}"
        if save_temp_files:
            command += " --save_temp_files"

        self.command_display.setText(command)
        try:
            if modification_type == "CES1P1-CES1":
                modify_vcf_ces1p1_ces1(input_vcf, modified_vcf, pos_modifier)
            elif modification_type == "CES1A2-CES1":
                modify_vcf_ces1a2_ces1(input_vcf, modified_vcf)

            clean_vcf(modified_vcf, cleaned_vcf)
            annotate_vcf_with_ncbi(cleaned_vcf, final_output_vcf, self.update_progress)

            if not save_temp_files:
                os.remove(modified_vcf)
                os.remove(cleaned_vcf)

            QMessageBox.information(self, "Success", "VCF file processed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify, clean, and annotate a VCF file.")
    parser.add_argument("--input_vcf", type=str, help="Path to the input VCF file")
    parser.add_argument("--output_dir", type=str, help="Path to save the final annotated VCF file")
    parser.add_argument("--email", type=str, help="email required by Entrez to initialize the search process")
    parser.add_argument("--type", type=str, choices=["CES1P1-CES1", "CES1A2-CES1"], help="Type of position modification")
    parser.add_argument("--pos_modifier", type=int, default=55758218, help="Value to add to each POS entry (only for CES1P1-CES1)")
    parser.add_argument("--save_temp_files", action='store_true', help="Save temporary files")

    args = parser.parse_args()

    if len(sys.argv) > 1:
        if args.input_vcf and args.output_dir and args.type:
            input_vcf = args.input_vcf
            output_dir = args.output_dir
            modification_type = args.type
            pos_modifier = args.pos_modifier
            save_temp_files = args.save_temp_files
            base_name = os.path.splitext(os.path.basename(input_vcf))[0]
            modified_vcf = os.path.join(output_dir,f"{base_name}modified.vcf")
            cleaned_vcf = os.path.join(output_dir,f"{base_name}cleaned.vcf")
            final_output_vcf = os.path.join(output_dir,f"{base_name}_final_annotation.vcf")# quick fix around TODO: make base name a global variable instead of defining it in multiple places   

            if modification_type == "CES1P1-CES1":
                modify_vcf_ces1p1_ces1(input_vcf, modified_vcf, pos_modifier)
            elif modification_type == "CES1A2-CES1":
                modify_vcf_ces1a2_ces1(input_vcf, modified_vcf)

            clean_vcf(modified_vcf, cleaned_vcf)
            def dummy_progress_callback(value):
                pass
            annotate_vcf_with_ncbi(cleaned_vcf, final_output_vcf,dummy_progress_callback)

            if not save_temp_files:
                os.remove(modified_vcf)
                os.remove(cleaned_vcf)

            print("VCF file processed successfully.")
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