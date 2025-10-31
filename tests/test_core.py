"""
Smoke tests for rsID Retrieval tool.
These tests verify core functionality before and after cleanup.
"""
import unittest
import os
import sys
import tempfile
import shutil

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vcf_processor import validate_vcf_file
from core.sandbox import SandboxProcessor


class TestVCFValidation(unittest.TestCase):
    """Test VCF file validation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.valid_vcf = os.path.join(self.fixtures_dir, 'test_sample.vcf')
    
    def test_valid_vcf_file(self):
        """Test that valid VCF file passes validation."""
        is_valid, message = validate_vcf_file(self.valid_vcf)
        self.assertTrue(is_valid, f"Valid VCF should pass validation: {message}")
        self.assertEqual(message, "VCF file is valid")
    
    def test_nonexistent_file(self):
        """Test that nonexistent file fails validation."""
        is_valid, message = validate_vcf_file("nonexistent.vcf")
        self.assertFalse(is_valid)
        self.assertIn("does not exist", message)
    
    def test_invalid_extension(self):
        """Test that non-VCF file fails validation."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_file.close()
        
        try:
            is_valid, message = validate_vcf_file(temp_file.name)
            self.assertFalse(is_valid)
            self.assertIn(".vcf extension", message)
        finally:
            os.unlink(temp_file.name)
    
    def test_empty_file(self):
        """Test that empty VCF file fails validation."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.vcf', delete=False, mode='w')
        temp_file.close()
        
        try:
            is_valid, message = validate_vcf_file(temp_file.name)
            self.assertFalse(is_valid)
            self.assertIn("empty", message.lower())
        finally:
            os.unlink(temp_file.name)


class TestSandboxProcessor(unittest.TestCase):
    """Test sandbox mode functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Use a dummy email for testing (won't actually call API in these tests)
        self.processor = SandboxProcessor("test@example.com")
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_equation_validation_simple(self):
        """Test validation of simple equation."""
        is_valid, message, results = self.processor.validate_equation("x + 1000000")
        self.assertTrue(is_valid, f"Simple equation should be valid: {message}")
        self.assertEqual(message, "Equation is valid")
        self.assertEqual(len(results), 4)  # Default test positions
    
    def test_equation_validation_complex(self):
        """Test validation of complex equation."""
        is_valid, message, results = self.processor.validate_equation("x * 2 + 500")
        self.assertTrue(is_valid, f"Complex equation should be valid: {message}")
        self.assertEqual(len(results), 4)
    
    def test_equation_validation_empty(self):
        """Test validation of empty equation."""
        is_valid, message, results = self.processor.validate_equation("")
        self.assertFalse(is_valid)
        self.assertIn("empty", message.lower())
    
    def test_equation_validation_invalid_syntax(self):
        """Test validation of equation with invalid syntax."""
        is_valid, message, results = self.processor.validate_equation("x +")
        self.assertFalse(is_valid)
        self.assertIn("syntax", message.lower())
    
    def test_equation_validation_wrong_variable(self):
        """Test validation of equation with wrong variable."""
        is_valid, message, results = self.processor.validate_equation("y + 1000")
        self.assertFalse(is_valid)
    
    def test_equation_validation_negative_result(self):
        """Test validation of equation producing negative result."""
        is_valid, message, results = self.processor.validate_equation("x - 10000000")
        self.assertFalse(is_valid)
        self.assertIn("negative", message.lower())
    
    def test_chromosome_format_refseq(self):
        """Test chromosome formatting to RefSeq."""
        # Test numeric input
        result = self.processor._format_chromosome("16", "RefSeq")
        self.assertEqual(result, "NC_000016.10")
        
        # Test UCSC input
        result = self.processor._format_chromosome("chr16", "RefSeq")
        self.assertEqual(result, "NC_000016.10")
        
        # Test RefSeq input (should normalize)
        result = self.processor._format_chromosome("NC_000016.10", "RefSeq")
        self.assertEqual(result, "NC_000016.10")
    
    def test_chromosome_format_ucsc(self):
        """Test chromosome formatting to UCSC."""
        result = self.processor._format_chromosome("16", "UCSC")
        self.assertEqual(result, "chr16")
        
        result = self.processor._format_chromosome("NC_000016.10", "UCSC")
        self.assertEqual(result, "chr16")
    
    def test_chromosome_format_ensembl(self):
        """Test chromosome formatting to Ensembl."""
        result = self.processor._format_chromosome("chr16", "Ensembl")
        self.assertEqual(result, "16")
        
        result = self.processor._format_chromosome("NC_000016.10", "Ensembl")
        self.assertEqual(result, "16")
    
    def test_chromosome_format_numeric(self):
        """Test chromosome formatting to numeric."""
        result = self.processor._format_chromosome("chr16", "numeric")
        self.assertEqual(result, "16")
        
        result = self.processor._format_chromosome("NC_000016.10", "numeric")
        self.assertEqual(result, "16")
    
    def test_chromosome_format_sex_chromosomes(self):
        """Test formatting of sex chromosomes."""
        # X chromosome
        result = self.processor._format_chromosome("X", "RefSeq")
        self.assertEqual(result, "NC_0000X.10")
        
        result = self.processor._format_chromosome("chrX", "UCSC")
        self.assertEqual(result, "chrX")
        
        # Y chromosome
        result = self.processor._format_chromosome("Y", "RefSeq")
        self.assertEqual(result, "NC_0000Y.10")


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflows."""
    
    def setUp(self):
        """Set up test environment."""
        self.fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        self.valid_vcf = os.path.join(self.fixtures_dir, 'test_sample.vcf')
        self.temp_dir = tempfile.mkdtemp()
        self.processor = SandboxProcessor("test@example.com")
    
    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_sandbox_modification_basic(self):
        """Test basic sandbox VCF modification without API calls."""
        output_vcf = os.path.join(self.temp_dir, 'modified.vcf')
        
        result = self.processor.apply_custom_modification(
            input_vcf=self.valid_vcf,
            output_vcf=output_vcf,
            chromosome_id="16",
            equation_str="x + 1000",
            chromosome_format="RefSeq"
        )
        
        self.assertTrue(result['success'], f"Modification should succeed: {result.get('error', '')}")
        self.assertTrue(os.path.exists(output_vcf), "Output VCF should be created")
        
        # Verify statistics
        stats = result['statistics']
        self.assertIn('total_variants', stats)
        self.assertIn('chromosome_format', stats)
        self.assertIn('16 -> NC_000016.10', stats['chromosome_format'])
    
    def test_sandbox_modification_format_conversion(self):
        """Test format conversion during modification."""
        output_vcf = os.path.join(self.temp_dir, 'converted.vcf')
        
        result = self.processor.apply_custom_modification(
            input_vcf=self.valid_vcf,
            output_vcf=output_vcf,
            chromosome_id="chr16",
            equation_str="x",
            chromosome_format="UCSC"
        )
        
        self.assertTrue(result['success'])
        
        # Read output and verify chromosome format
        with open(output_vcf, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('chr16', content, "Output should use UCSC format")
    
    def test_sandbox_modification_invalid_vcf(self):
        """Test that invalid VCF is rejected."""
        nonexistent = "nonexistent.vcf"
        output_vcf = os.path.join(self.temp_dir, 'output.vcf')
        
        result = self.processor.apply_custom_modification(
            input_vcf=nonexistent,
            output_vcf=output_vcf,
            chromosome_id="16",
            equation_str="x + 1000",
            chromosome_format="RefSeq"
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_sandbox_modification_invalid_equation(self):
        """Test that invalid equation is rejected."""
        output_vcf = os.path.join(self.temp_dir, 'output.vcf')
        
        result = self.processor.apply_custom_modification(
            input_vcf=self.valid_vcf,
            output_vcf=output_vcf,
            chromosome_id="16",
            equation_str="invalid equation",
            chromosome_format="RefSeq"
        )
        
        self.assertFalse(result['success'])
        self.assertIn('equation', result['error'].lower())


def run_tests():
    """Run all tests and return results."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVCFValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestSandboxProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    print("=" * 70)
    print("Running rsID Retrieval Smoke Tests")
    print("=" * 70)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 70)
    print("Test Summary:")
    print(f"  Tests Run: {result.testsRun}")
    print(f"  Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print("=" * 70)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
