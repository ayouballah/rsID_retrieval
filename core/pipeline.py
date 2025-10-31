"""
Main processing pipeline for rsID retrieval.
"""
import os
from .vcf_processor import (
    validate_vcf_file, modify_vcf_ces1p1_ces1, modify_vcf_ces1a2_ces1, 
    clean_vcf, filter_rsids_vcf, filter_significant_rsids, generate_summary_report
)
from .entrez_api import setup_entrez, annotate_vcf_with_entrez


class RSIDProcessor:
    """
    Main processor class for rsID retrieval workflow.
    """
    
    def __init__(self, email):
        """
        Initialize the processor with an email for Entrez API.
        """
        self.email = email
        setup_entrez(email)
    
    def validate_inputs(self, input_vcf, output_dir, modification_type, pos_modifier=None):
        """
        Validate all inputs before processing.
        """
        errors = []
        
        # Validate email
        if not self.email or '@' not in self.email:
            errors.append("Valid email address required for Entrez API")
        
        # Validate VCF file
        is_valid, error_msg = validate_vcf_file(input_vcf)
        if not is_valid:
            errors.append(f"Invalid VCF file: {error_msg}")
        
        # Validate output directory
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory: {str(e)}")
        
        # Validate modification type
        if modification_type not in ["CES1P1-CES1", "CES1A2-CES1"]:
            errors.append("Invalid modification type. Must be 'CES1P1-CES1' or 'CES1A2-CES1'")
        
        # Validate position modifier for CES1P1-CES1
        if modification_type == "CES1P1-CES1" and (pos_modifier is None or pos_modifier <= 0):
            errors.append("Position modifier must be a positive integer for CES1P1-CES1")
        
        return errors
    
    def process_vcf(self, input_vcf, output_dir, modification_type, pos_modifier=55758218, progress_callback=None):
        """
        Complete VCF processing pipeline.
        
        Parameters:
            input_vcf (str): Path to input VCF file
            output_dir (str): Output directory path
            modification_type (str): Type of modification ('CES1P1-CES1' or 'CES1A2-CES1')
            pos_modifier (int): Position modifier value (for CES1P1-CES1)
            progress_callback (callable): Optional progress callback function
            
        Returns:
            dict: Processing results and file paths
        """
        # Validate inputs
        errors = self.validate_inputs(input_vcf, output_dir, modification_type, pos_modifier)
        if errors:
            return {
                'success': False,
                'errors': errors,
                'files': {}
            }
        
        # Setup file paths
        base_name = os.path.splitext(os.path.basename(input_vcf))[0]
        results_subdir = os.path.join(output_dir, f"{base_name}_results")
        os.makedirs(results_subdir, exist_ok=True)
        
        files = {
            'final_output_vcf': os.path.join(results_subdir, f"{base_name}_final_annotation.vcf"),
            'filtered_rsids_vcf': os.path.join(results_subdir, f"{base_name}_filtered_rsids.vcf"),
            'no_rsids_vcf': os.path.join(results_subdir, f"{base_name}_no_rsids.vcf"),
            'significant_rsids_vcf': os.path.join(results_subdir, f"{base_name}_significant_rsids.vcf"),
            'summary_report': os.path.join(results_subdir, f"summary_report_for_{base_name}.txt")
        }
        
        try:
            messages = []
            
            # Step 1: Modify VCF based on the selected type
            if modification_type == "CES1P1-CES1":
                msg = modify_vcf_ces1p1_ces1(input_vcf, files['no_rsids_vcf'], pos_modifier)
            elif modification_type == "CES1A2-CES1":
                msg = modify_vcf_ces1a2_ces1(input_vcf, files['no_rsids_vcf'])
            messages.append(msg)
            
            if progress_callback:
                progress_callback(10)
            
            # Step 2: Clean the modified VCF
            msg = clean_vcf(files['no_rsids_vcf'], files['no_rsids_vcf'])
            messages.append(msg)
            
            if progress_callback:
                progress_callback(20)
            
            # Step 3: Annotate VCF with rsIDs using Entrez API
            result = annotate_vcf_with_entrez(files['no_rsids_vcf'], files['final_output_vcf'], progress_callback)
            messages.append(result['message'])
            
            if progress_callback:
                progress_callback(70)
            
            # Step 4: Filter to include only rsIDs
            msg = filter_rsids_vcf(files['final_output_vcf'], files['filtered_rsids_vcf'])
            messages.append(msg)
            
            if progress_callback:
                progress_callback(80)
            
            # Step 5: Filter significant rsIDs
            msg = filter_significant_rsids(files['filtered_rsids_vcf'], files['significant_rsids_vcf'])
            messages.append(msg)
            
            if progress_callback:
                progress_callback(90)
            
            # Step 6: Generate summary report
            summary_data = generate_summary_report(files['final_output_vcf'], files['summary_report'])
            messages.append(f"Summary report generated successfully")
            
            if progress_callback:
                progress_callback(100)
            
            return {
                'success': True,
                'messages': messages,
                'files': files,
                'summary': summary_data,
                'annotation_result': result
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [str(e)],
                'files': files,
                'messages': messages if 'messages' in locals() else []
            }
