"""
Comprehensive test suite for the sandbox functionality.
"""
import os
import tempfile
from core.sandbox import SandboxProcessor


def test_equation_validation():
    """Test equation validation functionality."""
    print("Testing equation validation...")
    
    processor = SandboxProcessor("test@example.com")
    
    # Test valid equations
    valid_equations = [
        "x + 1000000",
        "x * 2", 
        "(x * 1.5) + 500000",
        "x + 55758218",
        "x - 1000 if x > 1000 else x"
    ]
    
    for equation in valid_equations:
        is_valid, error_msg, test_results = processor.validate_equation(equation)
        print(f"  ✓ '{equation}': {'PASS' if is_valid else 'FAIL'}")
        if not is_valid:
            print(f"    Error: {error_msg}")
    
    # Test invalid equations
    invalid_equations = [
        "",  # Empty
        "x +",  # Incomplete
        "y + 1000",  # Wrong variable
        "import os",  # Dangerous code
        "x / 0"  # Division by zero
    ]
    
    for equation in invalid_equations:
        is_valid, error_msg, test_results = processor.validate_equation(equation)
        print(f"  ✓ '{equation}': {'PASS' if not is_valid else 'FAIL'} (should be invalid)")


def test_chromosome_formatting():
    """Test chromosome format conversion."""
    print("\nTesting chromosome formatting...")
    
    processor = SandboxProcessor("test@example.com")
    
    test_cases = [
        ("16", "RefSeq", "NC_000016.10"),
        ("16", "UCSC", "chr16"),
        ("16", "Ensembl", "16"), 
        ("16", "numeric", "16"),
        ("X", "RefSeq", "NC_0000X.10"),
        ("chr1", "RefSeq", "NC_000001.10"),
    ]
    
    for input_chrom, format_type, expected in test_cases:
        result = processor._format_chromosome(input_chrom, format_type)
        status = "PASS" if result == expected else "FAIL"
        print(f"  ✓ {input_chrom} → {format_type}: {result} ({status})")


def create_test_vcf():
    """Create a minimal test VCF file."""
    vcf_content = """##fileformat=VCFv4.2
##contig=<ID=1,length=249250621>
#CHROM	POS	ID	REF	ALT	QUAL	FILTER
1	100	.	A	T	30	PASS
1	200	.	C	G	40	PASS
1	300	.	T	A	50	PASS
"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False)
    temp_file.write(vcf_content)
    temp_file.close()
    return temp_file.name


def test_vcf_modification():
    """Test VCF modification functionality."""
    print("\nTesting VCF modification...")
    
    # Create test VCF
    test_vcf = create_test_vcf()
    output_vcf = tempfile.NamedTemporaryFile(suffix='.vcf', delete=False).name
    
    try:
        processor = SandboxProcessor("test@example.com")
        
        # Test modification
        result = processor.apply_custom_modification(
            input_vcf=test_vcf,
            output_vcf=output_vcf,
            chromosome_id="16",
            equation_str="x + 1000000",
            chromosome_format="RefSeq"
        )
        
        if result['success']:
            print("  ✓ VCF modification: PASS")
            print(f"    Statistics: {result['statistics']}")
        else:
            print(f"  ✗ VCF modification: FAIL - {result['error']}")
        
    finally:
        # Clean up
        if os.path.exists(test_vcf):
            os.unlink(test_vcf)
        if os.path.exists(output_vcf):
            os.unlink(output_vcf)


def main():
    """Run all sandbox tests."""
    print("="*50)
    print("SANDBOX FUNCTIONALITY TESTS")
    print("="*50)
    
    test_equation_validation()
    test_chromosome_formatting()
    test_vcf_modification()
    
    print("\n" + "="*50)
    print("SANDBOX TESTS COMPLETED")
    print("="*50)


if __name__ == "__main__":
    main()