"""
Graphical user interface for rsID retrieval.
"""
import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QPushButton, QLineEdit, 
    QLabel, QComboBox, QWidget, QMessageBox, QTextEdit, QProgressBar
)
from PyQt6.QtCore import QThread, pyqtSignal
from core.pipeline import RSIDProcessor


CONFIG_FILE = "config.json"


def load_config():
    """Load configuration from file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}


def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        json.dump(config, file)


class ProcessingThread(QThread):
    """
    Thread for running VCF processing in the background.
    """
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(dict)
    
    def __init__(self, processor, input_vcf, output_dir, modification_type, pos_modifier):
        super().__init__()
        self.processor = processor
        self.input_vcf = input_vcf
        self.output_dir = output_dir
        self.modification_type = modification_type
        self.pos_modifier = pos_modifier
    
    def run(self):
        """Run the processing in background thread."""
        try:
            result = self.processor.process_vcf(
                input_vcf=self.input_vcf,
                output_dir=self.output_dir,
                modification_type=self.modification_type,
                pos_modifier=self.pos_modifier,
                progress_callback=self.progress_updated.emit
            )
            self.processing_finished.emit(result)
        except Exception as e:
            self.processing_finished.emit({
                'success': False,
                'errors': [str(e)],
                'files': {}
            })


class MainWindow(QMainWindow):
    """
    Main GUI window for rsID retrieval application.
    """
    
    def __init__(self):
        super().__init__()
        self.processor = None
        self.processing_thread = None
        self.init_ui()
        self.load_email()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("rsID Retrieval")
        self.setGeometry(100, 100, 600, 600)
        
        layout = QVBoxLayout()
        
        # Input VCF file selection
        self.input_vcf_label = QLabel("Input VCF File:")
        layout.addWidget(self.input_vcf_label)
        self.input_vcf_edit = QLineEdit()
        layout.addWidget(self.input_vcf_edit)
        self.input_vcf_button = QPushButton("Browse")
        self.input_vcf_button.clicked.connect(self.browse_input_vcf)
        layout.addWidget(self.input_vcf_button)

        # Output directory selection
        self.output_dir_label = QLabel("Output Directory:")
        layout.addWidget(self.output_dir_label)
        self.output_dir_edit = QLineEdit()
        layout.addWidget(self.output_dir_edit)
        self.output_dir_button = QPushButton("Browse")
        self.output_dir_button.clicked.connect(self.browse_output_dir)
        layout.addWidget(self.output_dir_button)

        # Email input
        self.email_label = QLabel("Email:")
        layout.addWidget(self.email_label)
        self.email_edit = QLineEdit()
        layout.addWidget(self.email_edit)

        # Modification type selection
        self.type_label = QLabel("Modification Type:")
        layout.addWidget(self.type_label)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["CES1P1-CES1", "CES1A2-CES1"])
        layout.addWidget(self.type_combo)

        # Position modifier
        self.pos_modifier_label = QLabel("Position Modifier (for CES1P1-CES1):")
        layout.addWidget(self.pos_modifier_label)
        self.pos_modifier_edit = QLineEdit()
        self.pos_modifier_edit.setText("55758218")
        layout.addWidget(self.pos_modifier_edit)

        # Run button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.run_processing)
        layout.addWidget(self.run_button)

        # Command display
        self.command_label = QLabel("Command:")
        layout.addWidget(self.command_label)
        self.command_display = QTextEdit()
        self.command_display.setReadOnly(True)
        layout.addWidget(self.command_display)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Set up the main widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_email(self):
        """Load email from configuration."""
        config = load_config()
        email = config.get("email", "")
        self.email_edit.setText(email)

    def save_email(self):
        """Save email to configuration."""
        email = self.email_edit.text()
        config = load_config()
        config["email"] = email
        save_config(config)

    def browse_input_vcf(self):
        """Browse for input VCF file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open VCF File", "", "VCF Files (*.vcf);;All Files (*)")
        if file_name:
            self.input_vcf_edit.setText(file_name)

    def browse_output_dir(self):
        """Browse for output directory."""
        dir_name = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_name:
            self.output_dir_edit.setText(dir_name)

    def run_processing(self):
        """Start the VCF processing."""
        # Save email configuration
        self.save_email()
        
        # Get input values
        input_vcf = self.input_vcf_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        email = self.email_edit.text().strip()
        modification_type = self.type_combo.currentText()
        
        # Basic validation
        if not input_vcf or not output_dir or not email:
            QMessageBox.warning(self, "Input Error", "Please fill in all required fields.")
            return
        
        # Validate position modifier
        try:
            pos_modifier = int(self.pos_modifier_edit.text())
            if pos_modifier <= 0:
                QMessageBox.warning(self, "Input Error", "Position modifier must be a positive integer.")
                return
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Position modifier must be a valid integer.")
            return
        
        # Initialize processor
        try:
            self.processor = RSIDProcessor(email)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize processor: {str(e)}")
            return
        
        # Validate inputs using processor
        errors = self.processor.validate_inputs(input_vcf, output_dir, modification_type, pos_modifier)
        if errors:
            error_msg = "\n".join(f"• {error}" for error in errors)
            QMessageBox.critical(self, "Validation Error", f"Input validation failed:\n\n{error_msg}")
            return
        
        # Build command string for display
        base_name = os.path.splitext(os.path.basename(input_vcf))[0]
        results_subdir = os.path.join(output_dir, f"{base_name}_results")
        command = f"python cli.py --input_vcf \"{input_vcf}\" --output_dir \"{results_subdir}\" --type {modification_type} --email \"{email}\""
        if modification_type == "CES1P1-CES1":
            command += f" --pos_modifier {pos_modifier}"
        self.command_display.setText(command)
        
        # Disable UI during processing
        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Start processing in background thread
        self.processing_thread = ProcessingThread(
            self.processor, input_vcf, output_dir, modification_type, pos_modifier
        )
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        self.processing_thread.start()

    def update_progress(self, value):
        """Update progress bar."""
        self.progress_bar.setValue(value)

    def processing_complete(self, result):
        """Handle processing completion."""
        # Re-enable UI
        self.run_button.setEnabled(True)
        
        if result['success']:
            # Show success message
            summary = result.get('summary', {})
            message = f"VCF processing completed successfully!\n\n"
            message += f"Results saved to: {os.path.dirname(list(result['files'].values())[0])}\n\n"
            
            if summary:
                message += f"Summary:\n"
                message += f"• Total variants: {summary.get('total_variants', 'N/A')}\n"
                message += f"• With rsID: {summary.get('with_rsid', 'N/A')}\n"
                message += f"• Without rsID: {summary.get('without_rsid', 'N/A')}\n"
                message += f"• High quality (QUAL≥20): {summary.get('reliable_variants', 'N/A')}\n"
            
            QMessageBox.information(self, "Success", message)
        else:
            # Show error message
            error_msg = "Processing failed with the following errors:\n\n"
            error_msg += "\n".join(f"• {error}" for error in result.get('errors', ['Unknown error']))
            
            if 'messages' in result and result['messages']:
                error_msg += f"\n\nCompleted steps:\n"
                error_msg += "\n".join(f"✓ {msg}" for msg in result['messages'])
            
            QMessageBox.critical(self, "Processing Failed", error_msg)


def main():
    """Main GUI entry point."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
