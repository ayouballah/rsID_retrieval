"""
Unified GUI for rsID retrieval with regular and sandbox modes.
"""
import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QLabel, QComboBox, QWidget, QMessageBox, QTextEdit, QProgressBar, QTabWidget,
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from core.pipeline import RSIDProcessor
from core.sandbox import SandboxProcessor


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


class RegularProcessingThread(QThread):
    """Thread for regular VCF processing."""
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    
    def __init__(self, processor, input_vcf, output_dir, modification_type, pos_modifier):
        super().__init__()
        self.processor = processor
        self.input_vcf = input_vcf
        self.output_dir = output_dir
        self.modification_type = modification_type
        self.pos_modifier = pos_modifier
    
    def run(self):
        """Run the regular processing in background thread."""
        try:
            self.status_updated.emit("Starting regular VCF processing...")
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


class SandboxProcessingThread(QThread):
    """Thread for sandbox VCF processing."""
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(dict)
    status_updated = pyqtSignal(str)
    
    def __init__(self, processor, input_vcf, output_dir, chromosome_id, equation_str, chromosome_format):
        super().__init__()
        self.processor = processor
        self.input_vcf = input_vcf
        self.output_dir = output_dir
        self.chromosome_id = chromosome_id
        self.equation_str = equation_str
        self.chromosome_format = chromosome_format
    
    def run(self):
        """Run the sandbox processing in background thread."""
        try:
            self.status_updated.emit("Starting sandbox VCF processing...")
            result = self.processor.run_sandbox_pipeline(
                input_vcf=self.input_vcf,
                output_dir=self.output_dir,
                chromosome_id=self.chromosome_id,
                equation_str=self.equation_str,
                chromosome_format=self.chromosome_format,
                progress_callback=self.progress_updated.emit
            )
            self.processing_finished.emit(result)
        except Exception as e:
            self.processing_finished.emit({
                'success': False,
                'error': str(e),
                'files': {}
            })


class UnifiedMainWindow(QMainWindow):
    """
    Unified GUI window with tabs for regular and sandbox processing.
    """
    
    def __init__(self):
        super().__init__()
        self.regular_processor = None
        self.sandbox_processor = None
        self.processing_thread = None
        self.init_ui()
        self.load_email()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("rsID Retrieval - Unified Interface")
        self.setGeometry(100, 100, 900, 800)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Regular processing tab
        regular_tab = self.create_regular_tab()
        self.tab_widget.addTab(regular_tab, "🧬 Regular Processing (CES1)")
        
        # Sandbox processing tab
        sandbox_tab = self.create_sandbox_tab()
        self.tab_widget.addTab(sandbox_tab, "🧪 Sandbox Mode (Universal)")
        
        main_layout.addWidget(self.tab_widget)
        
        # Shared components at the bottom
        self.create_shared_components(main_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def create_regular_tab(self):
        """Create the regular processing tab."""
        regular_widget = QWidget()
        layout = QVBoxLayout()
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()
        
        # Input VCF
        input_layout = QHBoxLayout()
        self.regular_input_vcf_edit = QLineEdit()
        regular_input_browse = QPushButton("Browse")
        regular_input_browse.clicked.connect(lambda: self.browse_input_vcf(self.regular_input_vcf_edit))
        input_layout.addWidget(self.regular_input_vcf_edit)
        input_layout.addWidget(regular_input_browse)
        file_layout.addRow("Input VCF File:", input_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        self.regular_output_dir_edit = QLineEdit()
        regular_output_browse = QPushButton("Browse")
        regular_output_browse.clicked.connect(lambda: self.browse_output_dir(self.regular_output_dir_edit))
        output_layout.addWidget(self.regular_output_dir_edit)
        output_layout.addWidget(regular_output_browse)
        file_layout.addRow("Output Directory:", output_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # CES1 configuration group
        ces1_group = QGroupBox("CES1 Configuration")
        ces1_layout = QFormLayout()
        
        # Modification type
        self.regular_type_combo = QComboBox()
        self.regular_type_combo.addItems(["CES1P1-CES1", "CES1A2-CES1"])
        ces1_layout.addRow("Modification Type:", self.regular_type_combo)
        
        # Position modifier
        self.regular_pos_modifier_edit = QLineEdit()
        self.regular_pos_modifier_edit.setText("55758218")
        ces1_layout.addRow("Position Modifier (CES1P1-CES1):", self.regular_pos_modifier_edit)
        
        ces1_group.setLayout(ces1_layout)
        layout.addWidget(ces1_group)
        
        # Run button for regular processing
        self.regular_run_button = QPushButton("Run Regular Processing")
        self.regular_run_button.clicked.connect(self.run_regular_processing)
        layout.addWidget(self.regular_run_button)
        
        regular_widget.setLayout(layout)
        return regular_widget
    
    def create_sandbox_tab(self):
        """Create the sandbox processing tab."""
        sandbox_widget = QWidget()
        layout = QVBoxLayout()
        
        # Create sub-tabs for sandbox
        sandbox_tabs = QTabWidget()
        
        # Configuration sub-tab
        config_tab = self.create_sandbox_config_tab()
        sandbox_tabs.addTab(config_tab, "Configuration")
        
        # Testing sub-tab
        test_tab = self.create_sandbox_test_tab()
        sandbox_tabs.addTab(test_tab, "Equation Testing")
        
        layout.addWidget(sandbox_tabs)
        
        # Run button for sandbox processing
        self.sandbox_run_button = QPushButton("Run Sandbox Processing")
        self.sandbox_run_button.clicked.connect(self.run_sandbox_processing)
        layout.addWidget(self.sandbox_run_button)
        
        sandbox_widget.setLayout(layout)
        return sandbox_widget
    
    def create_sandbox_config_tab(self):
        """Create sandbox configuration sub-tab."""
        config_widget = QWidget()
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()
        
        input_layout = QHBoxLayout()
        self.sandbox_input_vcf_edit = QLineEdit()
        sandbox_input_browse = QPushButton("Browse")
        sandbox_input_browse.clicked.connect(lambda: self.browse_input_vcf(self.sandbox_input_vcf_edit))
        input_layout.addWidget(self.sandbox_input_vcf_edit)
        input_layout.addWidget(sandbox_input_browse)
        file_layout.addRow("Input VCF File:", input_layout)
        
        output_layout = QHBoxLayout()
        self.sandbox_output_dir_edit = QLineEdit()
        sandbox_output_browse = QPushButton("Browse")
        sandbox_output_browse.clicked.connect(lambda: self.browse_output_dir(self.sandbox_output_dir_edit))
        output_layout.addWidget(self.sandbox_output_dir_edit)
        output_layout.addWidget(sandbox_output_browse)
        file_layout.addRow("Output Directory:", output_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Chromosome configuration
        chrom_group = QGroupBox("Chromosome Configuration")
        chrom_layout = QFormLayout()
        
        self.sandbox_chromosome_edit = QLineEdit()
        self.sandbox_chromosome_edit.setPlaceholderText("e.g., 16, X, chr1, NC_000001.11")
        chrom_layout.addRow("Target Chromosome:", self.sandbox_chromosome_edit)
        
        self.sandbox_format_combo = QComboBox()
        self.sandbox_format_combo.addItems(["RefSeq", "UCSC", "Ensembl", "numeric"])
        # Add tooltips for each format option
        self.sandbox_format_combo.setItemData(0, "RefSeq: NC_000016.10 (NCBI reference sequences, best for NCBI APIs)", Qt.ItemDataRole.ToolTipRole)
        self.sandbox_format_combo.setItemData(1, "UCSC: chr16 (UCSC genome browser format, widely used)", Qt.ItemDataRole.ToolTipRole)
        self.sandbox_format_combo.setItemData(2, "Ensembl: 16 (Ensembl database format, European bioinformatics)", Qt.ItemDataRole.ToolTipRole)
        self.sandbox_format_combo.setItemData(3, "numeric: 16 (Simple numeric format, minimal)", Qt.ItemDataRole.ToolTipRole)
        chrom_layout.addRow("Output Format:", self.sandbox_format_combo)
        
        # Format explanation
        self.format_explanation = QLabel()
        self.format_explanation.setWordWrap(True)
        self.format_explanation.setStyleSheet("QLabel { color: #555; font-size: 10px; background-color: #f9f9f9; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }")
        self.update_format_explanation()  # Set initial explanation
        
        # Connect format change to explanation update
        self.sandbox_format_combo.currentTextChanged.connect(self.update_format_explanation)
        
        chrom_layout.addRow("", self.format_explanation)
        
        chrom_group.setLayout(chrom_layout)
        layout.addWidget(chrom_group)
        
        # Equation configuration
        equation_group = QGroupBox("Position Modification Equation")
        equation_layout = QVBoxLayout()
        
        self.sandbox_equation_edit = QLineEdit()
        self.sandbox_equation_edit.setPlaceholderText("e.g., x + 1000000, x * 2, x + 55758218")
        equation_layout.addWidget(QLabel("Equation (use 'x' for position):"))
        equation_layout.addWidget(self.sandbox_equation_edit)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        
        ces1_button = QPushButton("CES1 (+55758218)")
        ces1_button.clicked.connect(lambda: self.sandbox_equation_edit.setText("x + 55758218"))
        preset_layout.addWidget(ces1_button)
        
        offset_button = QPushButton("Offset (+1M)")
        offset_button.clicked.connect(lambda: self.sandbox_equation_edit.setText("x + 1000000"))
        preset_layout.addWidget(offset_button)
        
        scale_button = QPushButton("Scale (x2)")
        scale_button.clicked.connect(lambda: self.sandbox_equation_edit.setText("x * 2"))
        preset_layout.addWidget(scale_button)
        
        equation_layout.addLayout(preset_layout)
        equation_group.setLayout(equation_layout)
        layout.addWidget(equation_group)
        
        config_widget.setLayout(layout)
        return config_widget
    
    def create_sandbox_test_tab(self):
        """Create sandbox equation testing sub-tab."""
        test_widget = QWidget()
        layout = QVBoxLayout()
        
        # Test input
        test_input_group = QGroupBox("Test Equation")
        test_input_layout = QVBoxLayout()
        
        self.sandbox_test_positions_edit = QLineEdit()
        self.sandbox_test_positions_edit.setText("100, 1000, 10000, 100000")
        test_input_layout.addWidget(QLabel("Test Positions (comma-separated):"))
        test_input_layout.addWidget(self.sandbox_test_positions_edit)
        
        self.sandbox_test_button = QPushButton("Test Equation")
        self.sandbox_test_button.clicked.connect(self.test_sandbox_equation)
        test_input_layout.addWidget(self.sandbox_test_button)
        
        test_input_group.setLayout(test_input_layout)
        layout.addWidget(test_input_group)
        
        # Test results
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout()
        
        self.sandbox_test_table = QTableWidget()
        self.sandbox_test_table.setColumnCount(2)
        self.sandbox_test_table.setHorizontalHeaderLabels(["Original Position", "Modified Position"])
        results_layout.addWidget(self.sandbox_test_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        test_widget.setLayout(layout)
        return test_widget
    
    def create_shared_components(self, main_layout):
        """Create shared components used by both tabs."""
        # Email configuration (shared)
        email_group = QGroupBox("Entrez API Configuration (Required)")
        email_layout = QFormLayout()
        
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("your.email@example.com")
        email_layout.addRow("Email:", self.email_edit)
        
        email_group.setLayout(email_layout)
        main_layout.addWidget(email_group)
        
        # Status and progress (shared)
        status_group = QGroupBox("Processing Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Results display (shared)
        results_group = QGroupBox("Processing Results")
        results_layout = QVBoxLayout()
        
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setMaximumHeight(200)
        results_layout.addWidget(self.results_display)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        # Control buttons (shared)
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("🗑️ Clear All")
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)
        
        self.cancel_button = QPushButton("❌ Cancel Processing")
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
    
    def load_email(self):
        """Load email from configuration."""
        config = load_config()
        email = config.get("email", "")
        self.email_edit.setText(email)
    
    def save_email(self):
        """Save email to configuration."""
        email = self.email_edit.text().strip()
        config = load_config()
        config["email"] = email
        save_config(config)
    
    def update_format_explanation(self):
        """Update the chromosome format explanation based on selected format."""
        format_type = self.sandbox_format_combo.currentText()
        
        explanations = {
            "RefSeq": """
<b>RefSeq Format</b> (Recommended)<br>
📋 <b>Output Example:</b> NC_000016.10<br>
🔍 <b>NCBI Query:</b> Uses "16" internally (fully compatible)<br>
🎯 <b>Best for:</b> NCBI tools, dbSNP, official references<br>
✅ <b>This tool:</b> Native format, maximum compatibility
            """,
            "UCSC": """
<b>UCSC Format</b><br>
📋 <b>Output Example:</b> chr16<br>
🔍 <b>NCBI Query:</b> Uses "16" internally (fully compatible)<br>
🎯 <b>Best for:</b> UCSC Browser, IGV, genome visualization<br>
✅ <b>This tool:</b> Perfect for downstream browser analysis
            """,
            "Ensembl": """
<b>Ensembl Format</b><br>
📋 <b>Output Example:</b> 16<br>
🔍 <b>NCBI Query:</b> Uses "16" internally (fully compatible)<br>
🎯 <b>Best for:</b> Ensembl database, European bioinformatics<br>
✅ <b>This tool:</b> Clean format for international workflows
            """,
            "numeric": """
<b>Numeric Format</b><br>
📋 <b>Output Example:</b> 16<br>
🔍 <b>NCBI Query:</b> Uses "16" internally (fully compatible)<br>
🎯 <b>Best for:</b> Custom pipelines, minimal formatting needs<br>
✅ <b>This tool:</b> Simplest format for basic processing
            """
        }
        
        explanation_text = explanations.get(format_type, "Select a format to see details")
        
        # Add universal compatibility note
        compatibility_note = """
<hr style="margin: 8px 0; border: 1px solid #ddd;">
<b style="color: #2e8b57;">🔧 Universal NCBI Compatibility</b><br>
<span style="font-size: 9px; color: #666;">All formats query NCBI identically - only output appearance changes</span>
        """
        
        full_explanation = explanation_text + compatibility_note
        self.format_explanation.setText(full_explanation)
    
    def browse_input_vcf(self, line_edit):
        """Browse for input VCF file."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open VCF File", "", "VCF Files (*.vcf);;All Files (*)")
        if file_name:
            line_edit.setText(file_name)
    
    def browse_output_dir(self, line_edit):
        """Browse for output directory."""
        dir_name = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_name:
            line_edit.setText(dir_name)
    
    def test_sandbox_equation(self):
        """Test sandbox equation with sample positions."""
        equation = self.sandbox_equation_edit.text().strip()
        if not equation:
            QMessageBox.warning(self, "Input Error", "Please enter an equation to test.")
            return
        
        # Get test positions
        test_positions_text = self.sandbox_test_positions_edit.text().strip()
        try:
            test_positions = [int(x.strip()) for x in test_positions_text.split(',') if x.strip()]
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid test positions. Use comma-separated integers.")
            return
        
        # Get email
        email = self.email_edit.text().strip()
        if not email or '@' not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return
        
        try:
            # Test equation without full processor setup
            processor = SandboxProcessor(email)
            is_valid, error_msg, test_results = processor.validate_equation(equation, test_positions)
            
            if is_valid:
                # Display results in table
                self.sandbox_test_table.setRowCount(len(test_results))
                for i, (original, modified) in enumerate(test_results):
                    self.sandbox_test_table.setItem(i, 0, QTableWidgetItem(str(original)))
                    self.sandbox_test_table.setItem(i, 1, QTableWidgetItem(str(modified)))
                
                self.sandbox_test_table.resizeColumnsToContents()
                QMessageBox.information(self, "Success", f"✓ Equation '{equation}' is valid!")
            else:
                QMessageBox.critical(self, "Equation Error", f"✗ Equation error:\n{error_msg}")
                
        except Exception as e:
            QMessageBox.critical(self, "Test Error", f"Failed to test equation:\n{str(e)}")
    
    def run_regular_processing(self):
        """Start regular VCF processing."""
        # Save email
        self.save_email()
        
        # Get inputs
        input_vcf = self.regular_input_vcf_edit.text().strip()
        output_dir = self.regular_output_dir_edit.text().strip()
        email = self.email_edit.text().strip()
        modification_type = self.regular_type_combo.currentText()
        
        # Validate inputs
        if not all([input_vcf, output_dir, email]):
            QMessageBox.warning(self, "Input Error", "Please fill in all required fields.")
            return
        
        if '@' not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return
        
        try:
            pos_modifier = int(self.regular_pos_modifier_edit.text())
            if pos_modifier <= 0:
                QMessageBox.warning(self, "Input Error", "Position modifier must be positive.")
                return
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Position modifier must be a valid integer.")
            return
        
        # Initialize processor
        try:
            self.regular_processor = RSIDProcessor(email)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize processor:\n{str(e)}")
            return
        
        # Validate using processor
        errors = self.regular_processor.validate_inputs(input_vcf, output_dir, modification_type, pos_modifier)
        if errors:
            error_msg = "\n".join(f"• {error}" for error in errors)
            QMessageBox.critical(self, "Validation Error", f"Input validation failed:\n\n{error_msg}")
            return
        
        # Start processing
        self.start_processing("regular")
        self.processing_thread = RegularProcessingThread(
            self.regular_processor, input_vcf, output_dir, modification_type, pos_modifier
        )
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.status_updated.connect(self.update_status)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        self.processing_thread.start()
    
    def run_sandbox_processing(self):
        """Start sandbox VCF processing."""
        # Save email
        self.save_email()
        
        # Get inputs
        input_vcf = self.sandbox_input_vcf_edit.text().strip()
        output_dir = self.sandbox_output_dir_edit.text().strip()
        email = self.email_edit.text().strip()
        chromosome_id = self.sandbox_chromosome_edit.text().strip()
        equation_str = self.sandbox_equation_edit.text().strip()
        chromosome_format = self.sandbox_format_combo.currentText()
        
        # Validate inputs
        if not all([input_vcf, output_dir, email, chromosome_id, equation_str]):
            QMessageBox.warning(self, "Input Error", "Please fill in all required fields.")
            return
        
        if '@' not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return
        
        # Initialize processor
        try:
            self.sandbox_processor = SandboxProcessor(email)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize processor:\n{str(e)}")
            return
        
        # Test equation
        is_valid, error_msg, _ = self.sandbox_processor.validate_equation(equation_str)
        if not is_valid:
            QMessageBox.critical(self, "Equation Error", f"Invalid equation:\n{error_msg}")
            return
        
        # Start processing
        self.start_processing("sandbox")
        self.processing_thread = SandboxProcessingThread(
            self.sandbox_processor, input_vcf, output_dir, chromosome_id, equation_str, chromosome_format
        )
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.status_updated.connect(self.update_status)
        self.processing_thread.processing_finished.connect(self.processing_complete)
        self.processing_thread.start()
    
    def start_processing(self, mode):
        """Prepare UI for processing."""
        self.regular_run_button.setEnabled(False)
        self.sandbox_run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.results_display.clear()
        self.status_label.setText(f"Starting {mode} processing...")
    
    def update_progress(self, value):
        """Update progress bar."""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """Update status label."""
        self.status_label.setText(message)
    
    def processing_complete(self, result):
        """Handle processing completion."""
        # Re-enable UI
        self.regular_run_button.setEnabled(True)
        self.sandbox_run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        if result.get('success', False):
            # Show success results
            self.status_label.setText("✅ Processing completed successfully!")
            
            results_text = "PROCESSING COMPLETED SUCCESSFULLY\n\n"
            
            # Add messages
            if 'messages' in result:
                results_text += "Steps completed:\n"
                for message in result['messages']:
                    results_text += f"✓ {message}\n"
                results_text += "\n"
            
            # Add summary
            if 'summary' in result:
                summary = result['summary']
                results_text += f"Summary:\n"
                results_text += f"• Total variants: {summary.get('total_variants', 'N/A')}\n"
                results_text += f"• With rsID: {summary.get('with_rsid', 'N/A')}\n"
                results_text += f"• Without rsID: {summary.get('without_rsid', 'N/A')}\n"
                results_text += f"• High quality (QUAL≥20): {summary.get('reliable_variants', 'N/A')}\n\n"
            
            # Add sandbox stats
            if 'sandbox_stats' in result:
                stats = result['sandbox_stats']
                results_text += f"Sandbox Configuration:\n"
                results_text += f"• Original positions: {stats['original_range']}\n"
                results_text += f"• Modified positions: {stats['modified_range']}\n"
                results_text += f"• Chromosome mapping: {stats['chromosome_format']}\n\n"
            
            # Add file paths
            if 'files' in result and result['files']:
                results_text += f"Output files:\n"
                for file_type, file_path in result['files'].items():
                    results_text += f"• {file_type}: {os.path.basename(file_path)}\n"
                results_text += f"\nResults directory: {os.path.dirname(list(result['files'].values())[0])}"
            
            self.results_display.setText(results_text)
            
            # Show success dialog
            QMessageBox.information(self, "Success", "Processing completed successfully! Check the Results tab for details.")
            
        else:
            # Show error results
            self.status_label.setText("❌ Processing failed!")
            
            error_text = "PROCESSING FAILED\n\n"
            
            # Add errors
            errors = result.get('errors', []) if 'errors' in result else [result.get('error', 'Unknown error')]
            error_text += "Errors:\n"
            for error in errors:
                error_text += f"✗ {error}\n"
            
            # Add completed steps if any
            if 'messages' in result and result['messages']:
                error_text += f"\nCompleted steps:\n"
                for message in result['messages']:
                    error_text += f"✓ {message}\n"
            
            self.results_display.setText(error_text)
            
            # Show error dialog
            primary_error = errors[0] if errors else "Unknown error"
            QMessageBox.critical(self, "Processing Failed", f"Processing failed:\n\n{primary_error}")
    
    def cancel_processing(self):
        """Cancel ongoing processing."""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
            
            self.regular_run_button.setEnabled(True)
            self.sandbox_run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.status_label.setText("❌ Processing cancelled by user")
            self.results_display.append("\n--- Processing cancelled by user ---")
    
    def clear_all(self):
        """Clear all input fields and results."""
        # Regular tab
        self.regular_input_vcf_edit.clear()
        self.regular_output_dir_edit.clear()
        self.regular_pos_modifier_edit.setText("55758218")
        self.regular_type_combo.setCurrentIndex(0)
        
        # Sandbox tab
        self.sandbox_input_vcf_edit.clear()
        self.sandbox_output_dir_edit.clear()
        self.sandbox_chromosome_edit.clear()
        self.sandbox_equation_edit.clear()
        self.sandbox_format_combo.setCurrentText("RefSeq")
        self.sandbox_test_positions_edit.setText("100, 1000, 10000, 100000")
        self.sandbox_test_table.setRowCount(0)
        
        # Shared components
        self.email_edit.clear()
        self.results_display.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")


def main():
    """Main unified GUI entry point."""
    app = QApplication(sys.argv)
    window = UnifiedMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()