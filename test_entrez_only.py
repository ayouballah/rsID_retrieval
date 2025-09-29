#!/usr/bin/env python3
"""
Essential test script to verify Entrez annotation functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rsID_retrieval import fetch_rsid_entrez
from Bio import Entrez

def test_entrez_function():
    """Test individual Entrez function"""
    print("Testing Entrez lookup functionality...")
    
    # Set email for Entrez
    Entrez.email = "test@example.com"
    
    # Test known positions
    test_positions = [
        ("NC_000016.10", "55759367"),
        ("NC_000016.10", "55798764"),
        ("NC_000016.10", "55831706")
    ]
    
    for chrom, pos in test_positions:
        rsid = fetch_rsid_entrez(chrom, pos)
        status = "✓ Found" if rsid and rsid != "NORSID" else "✗ Not found"
        print(f"Position {pos}: {rsid} [{status}]")
    
    print("Entrez test completed.")

if __name__ == "__main__":
    test_entrez_function()
    
    print("\nTest files created. You can now test with:")
    print("python rsID_retrieval.py --input_vcf test_input.vcf --output_dir test_output --type CES1P1-CES1 --email your_email@example.com")
