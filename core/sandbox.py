"""
Sandbox mode for flexible VCF processing with custom chromosomes and equations.
"""
import os
import pandas as pd
from core.vcf_processor import validate_vcf_file
from core.entrez_api import setup_entrez, annotate_vcf_with_entrez
from core.vcf_processor import clean_vcf, filter_rsids_vcf, filter_significant_rsids, generate_summary_report


class SandboxProcessor:
    """
    Flexible processor for custom chromosome and equation modifications.
    """
    
    def __init__(self, email):
        """Initialize sandbox processor with email for Entrez API."""
        self.email = email
        setup_entrez(email)
        
    def validate_equation(self, equation_str, test_positions=None):
        """
        Validate custom equation syntax and test with sample positions.
        
        Parameters:
            equation_str (str): Python equation string (e.g., "x + 1000000")
            test_positions (list): List of test positions to validate equation
            
        Returns:
            tuple: (is_valid, error_message, test_results)
        """
        if not equation_str.strip():
            return False, "Equation cannot be empty", []
        
        # Test positions for validation
        if test_positions is None:
            test_positions = [100, 1000, 10000, 100000]
        
        test_results = []
        
        try:
            # Test equation with sample positions
            for pos in test_positions:
                x = pos  # Variable name expected in equation
                try:
                    result = eval(equation_str)
                    if not isinstance(result, (int, float)):
                        return False, f"Equation must return numeric value, got {type(result)}", []
                    if result < 0:
                        return False, f"Equation produced negative position {result} for input {pos}", []
                    test_results.append((pos, int(result)))
                except Exception as e:
                    return False, f"Equation error at position {pos}: {str(e)}", []
            
            return True, "Equation is valid", test_results
            
        except Exception as e:
            return False, f"Invalid equation syntax: {str(e)}", []
    
    def apply_custom_modification(self, input_vcf, output_vcf, chromosome_id, equation_str, chromosome_format="RefSeq"):
        """
        Apply custom chromosome and position modifications to VCF.
        
        Parameters:
            input_vcf (str): Path to input VCF file
            output_vcf (str): Path to output VCF file
            chromosome_id (str): Target chromosome ID (e.g., "16", "NC_000016.10", "chrX")
            equation_str (str): Python equation for position modification (use 'x' for position)
            chromosome_format (str): Output format ("RefSeq", "UCSC", "Ensembl", "numeric")
            
        Returns:
            dict: Results including statistics and validation info
        """
        # Validate inputs
        is_valid, error_msg = validate_vcf_file(input_vcf)
        if not is_valid:
            return {"success": False, "error": f"Invalid VCF file: {error_msg}"}
        
        # Validate equation
        eq_valid, eq_error, test_results = self.validate_equation(equation_str)
        if not eq_valid:
            return {"success": False, "error": f"Invalid equation: {eq_error}"}
        
        try:
            # Read VCF file
            with open(input_vcf, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                header_lines = [line for line in lines if line.startswith('##')]
                column_header_line = lines[len(header_lines)]
                column_headers = column_header_line.strip().split('\t')
                data_lines = lines[len(header_lines) + 1:]

            # Parse data
            data = [line.strip().split('\t') for line in data_lines if line.strip()]
            df = pd.DataFrame(data, columns=column_headers)
            
            if df.empty:
                return {"success": False, "error": "No data rows found in VCF file"}
            
            original_positions = df['POS'].astype(int).tolist()
            
            # Apply custom equation to positions
            modified_positions = []
            for pos in original_positions:
                x = pos  # Variable for equation
                try:
                    new_pos = int(eval(equation_str))
                    modified_positions.append(new_pos)
                except Exception as e:
                    return {"success": False, "error": f"Equation failed for position {pos}: {str(e)}"}
            
            # Update positions
            df['POS'] = modified_positions
            
            # Update chromosome format
            formatted_chrom = self._format_chromosome(chromosome_id, chromosome_format)
            df['#CHROM'] = formatted_chrom
            
            # Write modified VCF
            with open(output_vcf, 'w', encoding='utf-8') as file:
                file.writelines(header_lines)
                file.write(column_header_line)
                for _, row in df.iterrows():
                    file.write('\t'.join(row.astype(str)) + '\n')
            
            # Generate statistics
            stats = {
                "original_range": f"{min(original_positions)} - {max(original_positions)}",
                "modified_range": f"{min(modified_positions)} - {max(modified_positions)}",
                "total_variants": len(df),
                "chromosome_format": f"{chromosome_id} -> {formatted_chrom}",
                "equation_test_results": test_results
            }
            
            return {
                "success": True,
                "message": f"Custom modification applied successfully",
                "statistics": stats
            }
            
        except Exception as e:
            return {"success": False, "error": f"Processing failed: {str(e)}"}
    
    def _format_chromosome(self, chrom_id, format_type):
        """
        Format chromosome ID according to specified format.
        
        Parameters:
            chrom_id (str): Input chromosome identifier
            format_type (str): Output format type
            
        Returns:
            str: Formatted chromosome identifier
        """
        # Extract numeric part if present
        numeric_chrom = chrom_id.replace("chr", "").replace("NC_0000", "").split(".")[0]
        
        if format_type == "RefSeq":
            if numeric_chrom.isdigit():
                return f"NC_{int(numeric_chrom):06d}.10"  # e.g., NC_000016.10
            else:
                return f"NC_0000{numeric_chrom}.10"  # For X, Y, MT
        elif format_type == "UCSC":
            return f"chr{numeric_chrom}"  # e.g., chr16
        elif format_type == "Ensembl":
            return numeric_chrom  # e.g., 16
        elif format_type == "numeric":
            return numeric_chrom  # e.g., 16
        else:
            return chrom_id  # Return as-is for unknown formats
    
    def run_sandbox_pipeline(self, input_vcf, output_dir, chromosome_id, equation_str, 
                           chromosome_format="RefSeq", progress_callback=None):
        """
        Run complete sandbox processing pipeline.
        
        Parameters:
            input_vcf (str): Path to input VCF file
            output_dir (str): Output directory
            chromosome_id (str): Target chromosome ID
            equation_str (str): Position modification equation
            chromosome_format (str): Chromosome format
            progress_callback (callable): Progress callback function
            
        Returns:
            dict: Complete processing results
        """
        try:
            # Setup file paths
            base_name = os.path.splitext(os.path.basename(input_vcf))[0]
            results_subdir = os.path.join(output_dir, f"{base_name}_sandbox_results")
            os.makedirs(results_subdir, exist_ok=True)
            
            files = {
                'modified_vcf': os.path.join(results_subdir, f"{base_name}_custom_modified.vcf"),
                'cleaned_vcf': os.path.join(results_subdir, f"{base_name}_cleaned.vcf"),
                'annotated_vcf': os.path.join(results_subdir, f"{base_name}_annotated.vcf"),
                'filtered_rsids_vcf': os.path.join(results_subdir, f"{base_name}_with_rsids.vcf"),
                'significant_rsids_vcf': os.path.join(results_subdir, f"{base_name}_significant.vcf"),
                'summary_report': os.path.join(results_subdir, f"sandbox_report_{base_name}.txt")
            }
            
            messages = []
            
            if progress_callback:
                progress_callback(10)
            
            # Step 1: Apply custom modifications
            result = self.apply_custom_modification(
                input_vcf, files['modified_vcf'], chromosome_id, equation_str, chromosome_format
            )
            
            if not result['success']:
                return result
            
            messages.append(f"Applied custom modification: {equation_str}")
            messages.append(f"Chromosome format: {result['statistics']['chromosome_format']}")
            
            if progress_callback:
                progress_callback(25)
            
            # Step 2: Clean VCF
            clean_msg = clean_vcf(files['modified_vcf'], files['cleaned_vcf'])
            messages.append(clean_msg)
            
            if progress_callback:
                progress_callback(35)
            
            # Step 3: Annotate with rsIDs
            annotation_result = annotate_vcf_with_entrez(
                files['cleaned_vcf'], files['annotated_vcf'], progress_callback
            )
            messages.append(annotation_result['message'])
            
            if progress_callback:
                progress_callback(75)
            
            # Step 4: Filter rsIDs
            rsid_msg = filter_rsids_vcf(files['annotated_vcf'], files['filtered_rsids_vcf'])
            messages.append(rsid_msg)
            
            if progress_callback:
                progress_callback(85)
            
            # Step 5: Filter significant rsIDs
            sig_msg = filter_significant_rsids(files['filtered_rsids_vcf'], files['significant_rsids_vcf'])
            messages.append(sig_msg)
            
            if progress_callback:
                progress_callback(95)
            
            # Step 6: Generate summary report
            summary_data = generate_summary_report(files['annotated_vcf'], files['summary_report'])
            
            # Add sandbox-specific information to summary
            with open(files['summary_report'], 'a', encoding='utf-8') as f:
                f.write(f"\n--- Sandbox Configuration ---\n")
                f.write(f"Input chromosome: {chromosome_id}\n")
                f.write(f"Output format: {chromosome_format}\n")
                f.write(f"Position equation: {equation_str}\n")
                f.write(f"Original position range: {result['statistics']['original_range']}\n")
                f.write(f"Modified position range: {result['statistics']['modified_range']}\n")
                f.write(f"Equation test results:\n")
                for orig, modified in result['statistics']['equation_test_results']:
                    f.write(f"  {orig} -> {modified}\n")
            
            messages.append("Sandbox summary report generated")
            
            if progress_callback:
                progress_callback(100)
            
            return {
                'success': True,
                'messages': messages,
                'files': files,
                'sandbox_stats': result['statistics'],
                'summary': summary_data,
                'annotation_result': annotation_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Sandbox pipeline failed: {str(e)}",
                'files': files if 'files' in locals() else {}
            }
