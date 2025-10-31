"""
NCBI Entrez API integration for rsID retrieval.
"""
import time
import threading
import logging
from Bio import Entrez
import concurrent.futures
import pandas as pd
import shutil
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# Global rate limiter for Entrez API calls - very conservative to avoid 429 errors
_rate_limiter = threading.Semaphore(1)  # Reduced to 1 for maximum compliance with NCBI rate limits
_last_request_time = threading.local()


def setup_entrez(email):
    """
    Setup Entrez with the provided email.
    """
    if not email or '@' not in email:
        raise ValueError("Valid email address required for Entrez API")
    Entrez.email = email


def test_entrez_connection():
    """
    Test Entrez API connection.
    """
    if not Entrez.email:
        raise ValueError("Entrez email not set. Call setup_entrez() first.")
    
    try:
        handle = Entrez.esearch(db="snp", term="16[CHR] AND 123456[POS]")
        record = Entrez.read(handle)
        handle.close()
        return True, f"Entrez test successful: {record}"
    except Exception as e:
        return False, f"Entrez test failed: {e}"


def fetch_rsid_entrez(chromosome, position, max_retries=5):
    """
    Fetch rsID(s) from NCBI Entrez for a given chromosome and position.
    Thread-safe version with rate limiting and retry logic.
    
    Parameters:
        chromosome: Chromosome identifier
        position: Genomic position
        max_retries: Maximum number of retry attempts for transient failures (default: 5)
    """
    # Handle different chromosome formats
    if chromosome.startswith("NC_"):
        # Extract chromosome number from RefSeq format (e.g., NC_000016.10 -> 16)
        chrom_num = chromosome.replace("NC_0000", "").split(".")[0]
    else:
        chrom_num = str(chromosome)
    
    query = f"{chrom_num}[CHR] AND {position}[POS]"
    
    # Rate limiting - conservative approach to avoid 429 errors
    with _rate_limiter:
        for attempt in range(max_retries):
            try:
                # Very conservative timing to respect NCBI rate limits
                if hasattr(_last_request_time, 'value'):
                    time_since_last = time.time() - _last_request_time.value
                    if time_since_last < 0.5:  # Increased to 0.5s (2 requests/sec max)
                        time.sleep(0.5 - time_since_last)
                
                _last_request_time.value = time.time()
                
                # Ensure email is set for Entrez
                if not Entrez.email:
                    logger.error("Entrez email not set")
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
                if attempt < max_retries - 1:
                    # Log retry attempt with longer exponential backoff (1.5s, 3s, 4.5s, 6s, 7.5s)
                    backoff_time = 1.5 * (attempt + 1)
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for chr{chrom_num}:{position} - {str(e)[:50]}")
                    time.sleep(backoff_time)
                    continue
                else:
                    # Final failure - log it
                    logger.error(f"Failed to fetch rsID for chr{chrom_num}:{position} after {max_retries} attempts: {str(e)[:100]}")
                    return None
        
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


def annotate_vcf_with_entrez(input_vcf_path, final_output_vcf_path, progress_callback=None):
    """
    Annotate VCF using NCBI Entrez API with parallel processing.
    
    Parameters:
        input_vcf_path (str): Path to the input VCF file to be annotated.
        final_output_vcf_path (str): Path where the annotated VCF file will be saved.
        progress_callback (callable, optional): A function to update progress (expects an integer 0-100).
    
    Returns:
        dict: Summary of annotation results
    """
    try:
        # Copy the input VCF to output as starting point
        shutil.copy2(input_vcf_path, final_output_vcf_path)
        
        # Process all entries with Entrez API
        with open(input_vcf_path, 'r', encoding='utf-8') as file:
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
            raise ValueError("No valid variant data found in VCF file")
            
        vcf = pd.DataFrame(vcf_data, columns=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "SAMPLE"])
        total_rows = vcf.shape[0]
        annotated_count = 0
        
        # Check if we're in CLI mode or GUI mode
        is_cli_mode = progress_callback is None
        
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
            bar_format = '{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} variants [{elapsed}<{remaining}, {rate_fmt}]'
            progress_bar = tqdm(total=total_rows, desc="Annotating variants", 
                              unit="variant", bar_format=bar_format,
                              leave=True)
        
        # Process batches in parallel with minimal worker count for maximum rate limit compliance
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
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
                    # Log batch failure
                    logger.error(f"Batch {batch_idx} failed: {str(e)[:100]}")
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
        with open(input_vcf_path, 'r', encoding='utf-8') as original:
            lines = original.readlines()
            header_lines = [line for line in lines if line.startswith('#')]
        
        with open(final_output_vcf_path, 'w', encoding='utf-8') as output:
            output.writelines(header_lines)
            # Write data without extra columns, ensuring proper formatting
            for _, row in vcf.iterrows():
                # Only write the essential 7 columns: CHROM, POS, ID, REF, ALT, QUAL, SAMPLE
                line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                           str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
                output.write('\t'.join(line_data) + '\n')
        
        return {
            'total_variants': total_rows,
            'annotated_count': annotated_count,
            'success': True,
            'message': f"Parallel Entrez annotation complete. {annotated_count}/{total_rows} variants annotated."
        }
        
    except Exception as e:
        # Fallback to sequential processing
        return annotate_vcf_with_entrez_sequential(input_vcf_path, final_output_vcf_path, progress_callback)


def annotate_vcf_with_entrez_sequential(input_vcf_path, final_output_vcf_path, progress_callback=None):
    """
    Sequential fallback method for VCF annotation using NCBI Entrez API.
    Used when parallel processing fails.
    """
    try:
        # Process all entries with Entrez API sequentially
        with open(input_vcf_path, 'r', encoding='utf-8') as file:
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
            raise ValueError("No valid variant data found in VCF file")
            
        vcf = pd.DataFrame(vcf_data, columns=["CHROM", "POS", "ID", "REF", "ALT", "QUAL", "SAMPLE"])
        total_rows = vcf.shape[0]
        annotated_count = 0
        
        is_cli_mode = progress_callback is None
        
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
                
                time.sleep(0.5)  # Rate limiting
            
            if is_cli_mode:
                progress_bar.set_postfix(annotated=annotated_count)
                progress_bar.update(1)
            elif progress_callback and (idx % 10 == 0 or idx == total_rows - 1):
                progress_callback(int((idx + 1) / total_rows * 100))
        
        if is_cli_mode:
            progress_bar.close()
        
        # Write the annotated VCF
        with open(input_vcf_path, 'r', encoding='utf-8') as original:
            lines = original.readlines()
            header_lines = [line for line in lines if line.startswith('#')]
        
        with open(final_output_vcf_path, 'w', encoding='utf-8') as output:
            output.writelines(header_lines)
            for _, row in vcf.iterrows():
                line_data = [str(row['CHROM']), str(row['POS']), str(row['ID']), 
                           str(row['REF']), str(row['ALT']), str(row['QUAL']), str(row['SAMPLE'])]
                output.write('\t'.join(line_data) + '\n')
        
        return {
            'total_variants': total_rows,
            'annotated_count': annotated_count,
            'success': True,
            'message': f"Sequential annotation complete. {annotated_count}/{total_rows} variants annotated."
        }
        
    except Exception as e:
        return {
            'total_variants': 0,
            'annotated_count': 0,
            'success': False,
            'message': f"Sequential annotation failed: {e}"
        }
