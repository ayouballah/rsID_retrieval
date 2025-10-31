# Sandbox Mode - Universal rsID Retrieval

The Sandbox Mode transforms your CES1-specific tool into a universal genomics platform that works with any chromosome and custom position transformations.

## Overview

Sandbox Mode provides:

- **Universal Application**: Works with any chromosome (1-22, X, Y, MT)
- **Flexible Equations**: Custom position transformation equations  
- **Multi-format Support**: RefSeq, UCSC, Ensembl chromosome formats
- **Validation**: Safe equation testing before processing
- **Transparency**: Clear visualization of position transformations

## Quick Start

### GUI Mode (Recommended for beginners)
```bash
python main.py --sandbox --gui
# or
python sandbox_gui.py
```

### CLI Mode (For automation)
```bash
python sandbox_cli.py \
  --input_vcf your_file.vcf \
  --output_dir ./results \
  --email your@email.com \
  --chromosome "1" \
  --equation "x + 1000000" \
  --format "RefSeq"
```

## Equation System

Use `x` as the position variable in your equations:

### Simple Examples
```bash
# Add constant offset
x + 1000000

# Scale positions  
x * 2

# CES1 gene mapping
x + 55758218

# Complex transformation
(x * 1.2) + 750000
```

### Advanced Examples
```bash
# Conditional logic
x + 1000000 if x < 50000 else x + 2000000

# Mathematical functions
int(x * 1.5) + 500000

# Range-based mapping
x + 100000 if x < 1000000 else x - 100000
```

## Equation Validation

Always test your equations before processing:

```bash
# Test with default positions
python sandbox_cli.py --test-equation --equation "x + 55758218"

# Test with custom positions
python sandbox_cli.py \
  --test-equation \
  --equation "(x * 1.5) + 500000" \
  --test-positions "100,1000,10000,100000"
```

Output:
```
Equation '(x * 1.5) + 500000' is valid.

Test results:
  100 → 650000
  1000 → 2000000
  10000 → 15500000
  100000 → 650000000
```

## Chromosome Format Support

### Input (Flexible - Auto-detected)
- Numeric: `1`, `16`, `22`, `23` 
- UCSC: `chr1`, `chr16`, `chrX`, `chrY`
- RefSeq: `NC_000001.11`, `NC_000016.10`
- Mixed: Any combination works

### Output (Standardized)
- RefSeq (default): `NC_000016.10` - Best for NCBI APIs
- UCSC: `chr16` - Common in genome browsers  
- Ensembl: `16` - Ensembl database format
- Numeric: `16` - Simple numeric

## Complete Workflow Examples

### Example 1: Human Chromosome 1 Analysis
```bash
python sandbox_cli.py \
  --input_vcf chr1_variants.vcf \
  --output_dir ./chr1_analysis \
  --email researcher@university.edu \
  --chromosome "1" \
  --equation "x + 2000000" \
  --format "RefSeq"
```

### Example 2: X-Chromosome Study
```bash
python sandbox_cli.py \
  --input_vcf x_chromosome.vcf \
  --output_dir ./x_analysis \
  --email researcher@university.edu \
  --chromosome "X" \
  --equation "x * 1.1" \
  --format "UCSC"
```

### Example 3: Complex Gene Region Mapping
```bash
python sandbox_cli.py \
  --input_vcf gene_region.vcf \
  --output_dir ./gene_mapping \
  --email researcher@university.edu \
  --chromosome "16" \
  --equation "x + 55758218 if x < 100000 else x + 55758218 + 50000" \
  --format "RefSeq"
```

## GUI Features

The Sandbox GUI provides:

- File Browser: Easy VCF and directory selection
- Equation Builder: Interactive equation testing
- Real-time Testing: See position transformations instantly  
- Progress Tracking: Live processing updates
- Results Display: Comprehensive statistics and logs
- Preset Equations: Quick access to common transformations

## Performance and Safety

- Input Validation: Comprehensive VCF file checking
- Safe Equations: Sandboxed equation evaluation  
- Parallel Processing: Same high-performance engine
- Statistics: Detailed transformation tracking
- Fallback: Automatic error recovery

## Output Files

Each run creates a organized results directory:

```
your_file_sandbox_results/
├── your_file_custom_modified.vcf    # Applied transformations
├── your_file_cleaned.vcf            # Cleaned for API
├── your_file_annotated.vcf          # With rsIDs  
├── your_file_with_rsids.vcf         # Only variants with rsIDs
├── your_file_significant.vcf        # High quality (QUAL≥20)
└── sandbox_report_your_file.txt     # Comprehensive report
```

## Use Cases

### Research Applications
- Cross-species studies: Map between genome builds
- Comparative genomics: Analyze orthologous regions
- Population genetics: Study different populations
- Clinical research: Validate variants across references

### Data Integration
- Format conversion: Between genome browsers
- Coordinate lifting: Between assembly versions  
- Multi-platform: Combine data from different sources
- Quality control: Standardize variant datasets

## Integration Examples

### Batch Processing
```bash
for vcf in *.vcf; do
  python sandbox_cli.py \
    --input_vcf "$vcf" \
    --output_dir "./batch_results" \
    --email researcher@university.edu \
    --chromosome "auto_detect" \
    --equation "x + offset_for_${vcf}" \
    --format "RefSeq"
done
```

### Python Integration
```python
from core.sandbox import SandboxProcessor

# Process multiple files
processor = SandboxProcessor("your@email.com")

for vcf_file, chromosome, equation in datasets:
    result = processor.run_sandbox_pipeline(
        input_vcf=vcf_file,
        output_dir="./results",
        chromosome_id=chromosome,
        equation_str=equation,
        chromosome_format="RefSeq"
    )
    print(f"Processed {vcf_file}: {result['summary']}")
```

## Troubleshooting

### Common Issues

**Equation Errors**
```bash
# Test first
python sandbox_cli.py --test-equation --equation "your_equation"
```

**Invalid VCF**
```
Error: Invalid VCF file: Missing required column: #CHROM
```
Check VCF format, ensure proper headers

**No rsIDs Found**
```
Found 0 variants with rsIDs out of 100 total variants
```
Check chromosome format and position accuracy

### Getting Help
```bash
python sandbox_cli.py --help           # CLI help
python sandbox_gui.py                  # GUI mode
python test_sandbox.py                 # Run tests
```

## From CES1-Specific to Universal

The tool has evolved from CES1 gene analysis to a universal genomics platform that works with any chromosome and transformation.