"""
Quick test to verify the modular architecture works correctly.
"""
from core.vcf_processor import validate_vcf_file
from core.entrez_api import setup_entrez, test_entrez_connection
from core.pipeline import RSIDProcessor

def test_basic_functionality():
    """Test basic functionality of the modular system."""
    print("Testing modular architecture...")
    
    # Test 1: VCF validation with non-existent file
    print("1. Testing VCF validation...")
    is_valid, error_msg = validate_vcf_file("nonexistent.vcf")
    print(f"   Non-existent file validation: {'PASS' if not is_valid else 'FAIL'}")
    print(f"   Error message: {error_msg}")
    
    # Test 2: Entrez setup
    print("\n2. Testing Entrez setup...")
    try:
        setup_entrez("test@example.com")
        print("   Entrez setup: PASS")
    except Exception as e:
        print(f"   Entrez setup: FAIL - {e}")
    
    # Test 3: Processor initialization
    print("\n3. Testing processor initialization...")
    try:
        processor = RSIDProcessor("test@example.com")
        print("   Processor initialization: PASS")
        
        # Test input validation
        errors = processor.validate_inputs(
            input_vcf="nonexistent.vcf",
            output_dir="/tmp/test",
            modification_type="CES1P1-CES1",
            pos_modifier=55758218
        )
        print(f"   Input validation (should find errors): {'PASS' if errors else 'FAIL'}")
        print(f"   Found {len(errors)} validation errors")
        
    except Exception as e:
        print(f"   Processor initialization: FAIL - {e}")
    
    print("\nModular architecture test complete!")

if __name__ == "__main__":
    test_basic_functionality()
