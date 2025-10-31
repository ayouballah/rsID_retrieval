"""
Sandbox CLI interface for flexible VCF processing.
"""
import sys
import argparse
from core.sandbox import SandboxProcessor


def main():
    """
    Sandbox CLI entry point.
    """
    parser = argparse.ArgumentParser(description="Sandbox mode for flexible VCF processing with custom chromosomes and equations.")
    parser.add_argument("--input_vcf", type=str, help="Path to the input VCF file")
    parser.add_argument("--output_dir", type=str, help="Path to save the processed VCF files")
    parser.add_argument("--email", type=str, help="Email required by Entrez API")
    parser.add_argument("--chromosome", type=str, help="Target chromosome ID (e.g., '16', 'X', 'chrX')")
    parser.add_argument("--equation", type=str, required=True, help="Position modification equation using 'x' as position variable (e.g., 'x + 1000000')")
    parser.add_argument("--format", type=str, choices=["RefSeq", "UCSC", "Ensembl", "numeric"], 
                       default="RefSeq", help="Output chromosome format (default: RefSeq)")
    parser.add_argument("--test-equation", action="store_true", help="Test equation with sample positions and exit")
    parser.add_argument("--test-positions", type=str, help="Comma-separated positions for equation testing (e.g., '100,1000,10000')")

    args = parser.parse_args()

    try:
        # Test equation mode
        if args.test_equation:
            print("Testing equation syntax and behavior...")
            
            test_positions = None
            if args.test_positions:
                try:
                    test_positions = [int(x.strip()) for x in args.test_positions.split(',')]
                except ValueError:
                    print("Error: Invalid test positions format. Use comma-separated integers.")
                    sys.exit(1)
            
            # For test mode, we can test equations without Entrez setup
            class EquationTester:
                def validate_equation(self, equation_str, test_positions=None):
                    if not equation_str.strip():
                        return False, "Equation cannot be empty", []
                    
                    if test_positions is None:
                        test_positions = [100, 1000, 10000, 100000]
                    
                    test_results = []
                    
                    try:
                        for pos in test_positions:
                            x = pos
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
            
            temp_processor = EquationTester()
            is_valid, error_msg, test_results = temp_processor.validate_equation(args.equation, test_positions)
            
            if is_valid:
                print(f"✓ Equation '{args.equation}' is valid!")
                print("\nTest results:")
                for original, modified in test_results:
                    print(f"  {original} -> {modified}")
            else:
                print(f"✗ Equation error: {error_msg}")
                sys.exit(1)
            
            return
        
        # Check required arguments for processing mode
        if not all([args.input_vcf, args.output_dir, args.email, args.chromosome]):
            print("Error: Missing required arguments for processing mode.")
            print("Required: --input_vcf, --output_dir, --email, --chromosome")
            sys.exit(1)
        
        print(f"Starting sandbox processing...")
        print(f"Input VCF: {args.input_vcf}")
        print(f"Target chromosome: {args.chromosome}")
        print(f"Position equation: {args.equation}")
        print(f"Output format: {args.format}")
        
        # Initialize sandbox processor
        processor = SandboxProcessor(args.email)
        
        # Test equation first
        is_valid, error_msg, test_results = processor.validate_equation(args.equation)
        if not is_valid:
            print(f"✗ Equation error: {error_msg}")
            sys.exit(1)
        
        print("✓ Equation validated successfully")
        print("Equation test results:")
        for original, modified in test_results[:3]:  # Show first 3 results
            print(f"  {original} -> {modified}")
        
        # Run sandbox pipeline
        result = processor.run_sandbox_pipeline(
            input_vcf=args.input_vcf,
            output_dir=args.output_dir,
            chromosome_id=args.chromosome,
            equation_str=args.equation,
            chromosome_format=args.format,
            progress_callback=None  # CLI mode - progress shown by tqdm
        )
        
        if result['success']:
            print("\n" + "="*60)
            print("SANDBOX PROCESSING COMPLETED SUCCESSFULLY")
            print("="*60)
            
            for message in result['messages']:
                print(f"✓ {message}")
            
            print(f"\nSandbox Configuration:")
            stats = result['sandbox_stats']
            print(f"  - Original positions: {stats['original_range']}")
            print(f"  - Modified positions: {stats['modified_range']}")
            print(f"  - Total variants: {stats['total_variants']}")
            print(f"  - Chromosome mapping: {stats['chromosome_format']}")
            
            print(f"\nFiles created:")
            for file_type, file_path in result['files'].items():
                print(f"  - {file_type}: {file_path}")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"\nAnnotation Summary:")
                print(f"  - Total variants: {summary['total_variants']}")
                print(f"  - With rsID: {summary['with_rsid']}")
                print(f"  - Without rsID: {summary['without_rsid']}")
                print(f"  - High quality (QUAL≥20): {summary['reliable_variants']}")
                
        else:
            print("\n" + "="*60)
            print("SANDBOX PROCESSING FAILED")
            print("="*60)
            
            if 'error' in result:
                print(f"✗ Error: {result['error']}")
            
            if 'messages' in result:
                print(f"\nCompleted steps:")
                for message in result['messages']:
                    print(f"✓ {message}")
            
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
