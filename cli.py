"""
Command-line interface for rsID retrieval.
"""
import sys
import argparse
from core.pipeline import RSIDProcessor
from core.entrez_api import test_entrez_connection


def main():
    """
    Main CLI entry point.
    """
    parser = argparse.ArgumentParser(description="Modify, clean, and annotate a VCF file.")
    parser.add_argument("--input_vcf", type=str, help="Path to the input VCF file")
    parser.add_argument("--output_dir", type=str, help="Path to save the final annotated VCF files")
    parser.add_argument("--email", type=str, help="Email required by Entrez to initialize the search process")
    parser.add_argument("--type", type=str, choices=["CES1P1-CES1", "CES1A2-CES1"], help="Type of position modification")
    parser.add_argument("--pos_modifier", type=int, default=55758218, help="Value to add to each POS entry (only for CES1P1-CES1)")

    args = parser.parse_args()

    if len(sys.argv) == 1:
        # No arguments provided, show help
        parser.print_help()
        return

    if not all([args.input_vcf, args.output_dir, args.type, args.email]):
        print("Error: Missing required arguments for command-line mode.")
        parser.print_help()
        return

    try:
        # Initialize processor
        processor = RSIDProcessor(args.email)
        
        # Test Entrez connection
        print("Testing Entrez API connection...")
        success, message = test_entrez_connection()
        if not success:
            print(f"Warning: {message}")
        else:
            print("Entrez API connection successful.")
        
        print(f"Starting processing of {args.input_vcf}...")
        
        # Process VCF
        result = processor.process_vcf(
            input_vcf=args.input_vcf,
            output_dir=args.output_dir,
            modification_type=args.type,
            pos_modifier=args.pos_modifier,
            progress_callback=None  # CLI mode - progress shown by tqdm
        )
        
        if result['success']:
            print("\n" + "="*50)
            print("PROCESSING COMPLETED SUCCESSFULLY")
            print("="*50)
            
            for message in result['messages']:
                print(f"✓ {message}")
            
            print(f"\nFiles created:")
            for file_type, file_path in result['files'].items():
                print(f"  - {file_type}: {file_path}")
            
            if 'summary' in result:
                summary = result['summary']
                print(f"\nSummary:")
                print(f"  - Total variants: {summary['total_variants']}")
                print(f"  - With rsID: {summary['with_rsid']}")
                print(f"  - Without rsID: {summary['without_rsid']}")
                print(f"  - High quality (QUAL≥20): {summary['reliable_variants']}")
                
        else:
            print("\n" + "="*50)
            print("PROCESSING FAILED")
            print("="*50)
            
            for error in result['errors']:
                print(f"✗ Error: {error}")
                
            if 'messages' in result:
                print(f"\nCompleted steps:")
                for message in result['messages']:
                    print(f"✓ {message}")
            
            sys.exit(1)
            
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
