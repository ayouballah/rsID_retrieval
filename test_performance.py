#!/usr/bin/env python3
"""
Test script to verify parallel annotation performance.
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rsID_retrieval import fetch_rsid_entrez
from Bio import Entrez

def test_performance():
    """Test performance of rsID lookup"""
    print("Testing performance with multiple positions...")
    
    # Set email for Entrez
    Entrez.email = "test@example.com"
    
    # Test positions
    test_positions = [
        "55759367", "55798764", "55806531", "55806600", 
        "55832104", "55832425", "55832466", "55833130"
    ]
    
    start_time = time.time()
    successful_lookups = 0
    
    for pos in test_positions:
        rsid = fetch_rsid_entrez("NC_000016.10", pos)
        if rsid and rsid != "NORSID":
            successful_lookups += 1
            print(f"Position {pos}: {rsid[:50]}...")
        else:
            print(f"Position {pos}: No rsID found")
    
    total_time = time.time() - start_time
    print(f"\nPerformance Summary:")
    print(f"Total positions tested: {len(test_positions)}")
    print(f"Successful lookups: {successful_lookups}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per lookup: {total_time/len(test_positions):.2f} seconds")

if __name__ == "__main__":
    test_performance()
