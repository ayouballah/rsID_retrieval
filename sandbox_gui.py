"""
Sandbox GUI for flexible VCF processing with custom chromosomes and equations.
"""
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QLabel, QComboBox, QWidget, QMessageBox, QTextEdit, QProgressBar, 
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal
from core.sandbox import SandboxProcessor


class SandboxProcessingThread(QThread):
    """
    Thread for running sandbox processing in the background.
    """
    progress_updated = pyqtSignal(int)
    processing_finished = pyqtSignal(dict)
    
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


class SandboxWindow(QMainWindow):
    """
    Sandbox GUI window for flexible VCF processing.
    """
    
    def __init__(self):
        super().__init__()
        self.processor = None
        self.processing_thread = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("rsID Retrieval - Sandbox Mode")
        self.setGeometry(100, 100, 800, 700)
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Configuration tab
        config_tab = self.create_config_tab()
        tab_widget.addTab(config_tab, "Configuration")
        
        # Equation testing tab
        test_tab = self.create_test_tab()
        tab_widget.addTab(test_tab, "Equation Testing")
        
        # Results tab
        results_tab = self.create_results_tab()
        tab_widget.addTab(results_tab, "Results")
        
        main_layout.addWidget(tab_widget)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.test_equation_button = QPushButton("Test Equation")
        self.test_equation_button.clicked.connect(self.test_equation)
        button_layout.addWidget(self.test_equation_button)
        
        self.run_button = QPushButton("Run Sandbox Processing")
        self.run_button.clicked.connect(self.run_processing)
        button_layout.addWidget(self.run_button)
        
        self.clear_button = QPushButton("Clear All")
        self.clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(button_layout)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def create_config_tab(self):
        """Create configuration tab."""
        config_widget = QWidget()
        layout = QVBoxLayout()
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()
        
        # Input VCF
        input_layout = QHBoxLayout()
        self.input_vcf_edit = QLineEdit()
        input_browse_button = QPushButton("Browse")
        input_browse_button.clicked.connect(self.browse_input_vcf)
        input_layout.addWidget(self.input_vcf_edit)
        input_layout.addWidget(input_browse_button)
        file_layout.addRow("Input VCF File:", input_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        output_browse_button = QPushButton("Browse")
        output_browse_button.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(output_browse_button)
        file_layout.addRow("Output Directory:", output_layout)
        
        # Email
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("your.email@example.com")
        file_layout.addRow("Email (for Entrez API):", self.email_edit)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Chromosome configuration group
        chrom_group = QGroupBox("Chromosome Configuration")
        chrom_layout = QFormLayout()
        
        self.chromosome_edit = QLineEdit()
        self.chromosome_edit.setPlaceholderText("e.g., 16, X, chr1, NC_000001.11")
        chrom_layout.addRow("Target Chromosome:", self.chromosome_edit)
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["RefSeq", "UCSC", "Ensembl", "numeric"])
        self.format_combo.setCurrentText("RefSeq")
        chrom_layout.addRow("Output Format:", self.format_combo)
        
        chrom_group.setLayout(chrom_layout)
        layout.addWidget(chrom_group)
        
        # Equation group
        equation_group = QGroupBox("Position Modification Equation")
        equation_layout = QVBoxLayout()
        
        self.equation_edit = QLineEdit()
        self.equation_edit.setPlaceholderText("e.g., x + 1000000, x * 2, x + 55758218")
        equation_layout.addWidget(QLabel("Equation (use 'x' for position):"))
        equation_layout.addWidget(self.equation_edit)
        
        # Preset equations
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Presets:"))
        
        ces1_button = QPushButton("CES1 (+55758218)")
        ces1_button.clicked.connect(lambda: self.equation_edit.setText("x + 55758218"))
        preset_layout.addWidget(ces1_button)
        
        offset_button = QPushButton("Simple Offset (+1M)")
        offset_button.clicked.connect(lambda: self.equation_edit.setText("x + 1000000"))
        preset_layout.addWidget(offset_button)
        
        scale_button = QPushButton("Scale (x2)")
        scale_button.clicked.connect(lambda: self.equation_edit.setText("x * 2"))
        preset_layout.addWidget(scale_button)
        
        equation_layout.addLayout(preset_layout)
        equation_group.setLayout(equation_layout)
        layout.addWidget(equation_group)
        
        config_widget.setLayout(layout)
        return config_widget
    
    def create_test_tab(self):
        """Create equation testing tab."""
        test_widget = QWidget()
        layout = QVBoxLayout()
        
        # Test positions input
        test_input_group = QGroupBox("Test Positions")
        test_input_layout = QVBoxLayout()
        
        self.test_positions_edit = QLineEdit()
        self.test_positions_edit.setText("100, 1000, 10000, 100000, 1000000")
        self.test_positions_edit.setPlaceholderText("Comma-separated positions (e.g., 100, 1000, 10000)")
        test_input_layout.addWidget(QLabel("Positions to test:"))
        test_input_layout.addWidget(self.test_positions_edit)
        
        test_input_group.setLayout(test_input_layout)
        layout.addWidget(test_input_group)
        
        # Test results table
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout()
        
        self.test_results_table = QTableWidget()
        self.test_results_table.setColumnCount(2)
        self.test_results_table.setHorizontalHeaderLabels(["Original Position", "Modified Position"])
        results_layout.addWidget(self.test_results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        test_widget.setLayout(layout)
        return test_widget
    
    def create_results_tab(self):
        """Create results display tab."""
        results_widget = QWidget()
        layout = QVBoxLayout()
        
        # Processing log
        log_group = QGroupBox("Processing Log")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Statistics display
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setMaximumHeight(150)
        stats_layout.addWidget(self.stats_display)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        results_widget.setLayout(layout)
        return results_widget
    
    def browse_input_vcf(self):
        """Browse for input VCF file."""
        from PyQt6.QtWidgets import QFileDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Open VCF File", "", "VCF Files (*.vcf);;All Files (*)")
        if file_name:
            self.input_vcf_edit.setText(file_name)
    
    def browse_output_dir(self):
        """Browse for output directory."""
        from PyQt6.QtWidgets import QFileDialog
        dir_name = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_name:
            self.output_dir_edit.setText(dir_name)
    
    def test_equation(self):
        """Test the equation with sample positions."""
        equation = self.equation_edit.text().strip()
        if not equation:
            QMessageBox.warning(self, "Input Error", "Please enter an equation to test.")
            return
        
        # Get test positions
        test_positions_text = self.test_positions_edit.text().strip()
        try:
            test_positions = [int(x.strip()) for x in test_positions_text.split(',') if x.strip()]
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid test positions format. Use comma-separated integers.")
            return
        
        if not test_positions:
            QMessageBox.warning(self, "Input Error", "Please enter at least one test position.")
            return
        
        # Initialize processor
        email = self.email_edit.text().strip()
        if not email or '@' not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return
        
        try:
            processor = SandboxProcessor(email)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize processor: {str(e)}")
            return
        
        # Test equation
        is_valid, error_msg, test_results = processor.validate_equation(equation, test_positions)
        
        if is_valid:
            # Display results in table
            self.test_results_table.setRowCount(len(test_results))
            for i, (original, modified) in enumerate(test_results):
                self.test_results_table.setItem(i, 0, QTableWidgetItem(str(original)))
                self.test_results_table.setItem(i, 1, QTableWidgetItem(str(modified)))
            
            self.test_results_table.resizeColumnsToContents()
            QMessageBox.information(self, "Success", f"Equation '{equation}' is valid!\n\nCheck the Test Results table for details.")
        else:
            QMessageBox.critical(self, "Equation Error", f"Equation error:\n{error_msg}")
    
    def run_processing(self):
        """Start the sandbox processing."""
        # Get input values
        input_vcf = self.input_vcf_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        email = self.email_edit.text().strip()
        chromosome_id = self.chromosome_edit.text().strip()
        equation_str = self.equation_edit.text().strip()
        chromosome_format = self.format_combo.currentText()
        
        # Basic validation
        if not all([input_vcf, output_dir, email, chromosome_id, equation_str]):
            QMessageBox.warning(self, "Input Error", "Please fill in all required fields.")
            return
        
        if '@' not in email:
            QMessageBox.warning(self, "Input Error", "Please enter a valid email address.")
            return
        
        # Initialize processor
        try:
            self.processor = SandboxProcessor(email)
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize processor: {str(e)}")
            return
        
        # Test equation
        is_valid, error_msg, _ = self.processor.validate_equation(equation_str)
        if not is_valid:
            QMessageBox.critical(self, "Equation Error", f"Invalid equation:\n{error_msg}")
            return
        
        # Clear previous results
        self.log_display.clear()
        self.stats_display.clear()
        
        # Disable UI during processing
        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Start processing in background thread
        self.processing_thread = SandboxProcessingThread(
            self.processor, input_vcf, output_dir, chromosome_id, equation_str, chromosome_format
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
            # Display messages in log
            log_text = "Processing completed successfully!\n\n"
            for message in result.get('messages', []):
                log_text += f"✓ {message}\n"
            self.log_display.setText(log_text)
            
            # Display statistics
            if 'sandbox_stats' in result:
                stats = result['sandbox_stats']
                stats_text = f"Sandbox Configuration:\n"
                stats_text += f"• Original positions: {stats['original_range']}\n"
                stats_text += f"• Modified positions: {stats['modified_range']}\n"
                stats_text += f"• Total variants: {stats['total_variants']}\n"
                stats_text += f"• Chromosome mapping: {stats['chromosome_format']}\n\n"
                
                if 'summary' in result:
                    summary = result['summary']
                    stats_text += f"Annotation Results:\n"
                    stats_text += f"• Total variants: {summary['total_variants']}\n"
                    stats_text += f"• With rsID: {summary['with_rsid']}\n"
                    stats_text += f"• Without rsID: {summary['without_rsid']}\n"
                    stats_text += f"• High quality (QUAL≥20): {summary['reliable_variants']}\n"
                
                self.stats_display.setText(stats_text)
            
            # Show success message
            QMessageBox.information(self, "Success", 
                f"Sandbox processing completed successfully!\n\n"
                f"Results saved to: {os.path.dirname(list(result['files'].values())[0])}")
            
        else:
            # Display error
            error_msg = f"Processing failed:\n{result.get('error', 'Unknown error')}\n\n"
            if 'messages' in result and result['messages']:
                error_msg += "Completed steps:\n"
                for message in result['messages']:
                    error_msg += f"✓ {message}\n"
            
            self.log_display.setText(error_msg)
            QMessageBox.critical(self, "Processing Failed", result.get('error', 'Unknown error'))
    
    def clear_all(self):
        """Clear all input fields and results."""
        self.input_vcf_edit.clear()
        self.output_dir_edit.clear()
        self.email_edit.clear()
        self.chromosome_edit.clear()
        self.equation_edit.clear()
        self.test_positions_edit.setText("100, 1000, 10000, 100000, 1000000")
        self.test_results_table.setRowCount(0)
        self.log_display.clear()
        self.stats_display.clear()
        self.progress_bar.setValue(0)
        self.format_combo.setCurrentText("RefSeq")


def main():
    """Main sandbox GUI entry point."""
    app = QApplication(sys.argv)
    window = SandboxWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
