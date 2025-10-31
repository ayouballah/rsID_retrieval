# rsID Retrieval

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
  - [Local Installation](#local-installation)
  - [Docker Installation](#docker-installation)
- [Usage](#usage)
  - [Unified Interface (Recommended)](#unified-interface-recommended)
  - [Regular Mode](#regular-mode)
  - [Sandbox Mode](#sandbox-mode)
  - [Command-Line Interface](#command-line-interface)
  - [Docker Usage](#docker-usage)
- [Chromosome Format Support](#chromosome-format-support)
- [Parameters](#parameters)
- [Examples](#examples)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)
- [Contributing](#contributing)
- [License](#license)

## Overview

**rsID Retrieval** is a Python-based tool designed for comprehensive variant analysis, specifically developed for processing Variant Call Format (VCF) files from nanopore sequencing. Originally designed for targeted chromosome 16 studies, the tool has evolved into a flexible platform supporting any chromosome through its sandbox mode. It modifies positional information, removes unnecessary columns, and annotates variants with rsIDs from the NCBI Entrez database. The tool is particularly helpful for targeted sequencing studies, enabling the identification of synonymous variants and rare alleles. It filters significant entries and generates comprehensive summary reports. 

The tool features a modular architecture with both a unified Graphical User Interface (GUI) built with PyQt6 and versatile Command-Line Interfaces (CLI), offering flexible usability for diverse research needs. The implementation uses parallel processing with the NCBI Entrez API to achieve performance improvements while maintaining reliability.

## Features

### Core Functionality
- **VCF Modification:** Adjusts the `POS` field based on predefined criteria or custom equations
- **Data Cleaning:** Selects specific columns and standardizes chromosome identifiers
- **rsID Annotation:** Fetches and annotates rsIDs using the NCBI Entrez API with optimized parallel processing
- **Filtering:** 
  - Retains only entries with valid rsIDs
  - Filters entries based on quality scores (QUAL >= 20 by default)
- **Reporting:** Generates comprehensive summary reports detailing processing outcomes and multiple VCF files with different filtering levels

### Dual Operating Modes

#### Regular Mode (CES1-Specific)
- **CES1P1-CES1 Mapping:** Simple positional offset modification
- **CES1A2-CES1 Mapping:** Complex conditional positional transformation
- Optimized for targeted chromosome 16 sequencing studies
- Preset configurations for common CES1 analysis workflows

#### Sandbox Mode (Universal)
- **Universal Chromosome Support:** Process any chromosome (1-22, X, Y, MT)
- **Custom Position Equations:** Apply arbitrary mathematical transformations to variant positions
- **Flexible Format Handling:** 
  - Input: Accepts RefSeq, UCSC, Ensembl, or numeric chromosome formats
  - Output: Convert to any standard format (RefSeq, UCSC, Ensembl, numeric)
- **Equation Testing:** Built-in validation and testing of custom position modification equations
- **Preset Equations:** Quick-access buttons for common transformations

### User Interfaces

#### Unified GUI (Recommended)
- **Tabbed Interface:** Switch seamlessly between Regular and Sandbox modes
- **Background Processing:** Non-blocking operations with real-time progress tracking
- **Format Explanations:** Interactive guidance for chromosome format selection
- **Visual Progress:** Detailed progress bars showing variant-level processing status
- **Results Display:** Comprehensive output with statistics and file locations

#### Command-Line Interfaces
- **Regular CLI:** Automation-friendly interface for CES1 processing
- **Sandbox CLI:** Scriptable interface for custom chromosome and equation workflows
- **Smart Entry Point:** Automatic mode detection based on arguments

### Technical Features
- **Modular Architecture:** Separated core logic, CLI, and GUI components for maintainability
- **Parallel Processing:** Multi-threaded Entrez API queries with intelligent rate limiting
- **Progress Tracking:** Real-time variant-level progress updates (not batch-based)
- **Error Handling:** Comprehensive validation and informative error messages
- **Cross-Platform Compatibility:** UTF-8 encoding throughout for Windows/Unix compatibility

## Architecture

The tool follows a modular architecture separating concerns into distinct components:

```
rsID_retrieval/
├── core/                          # Core business logic
│   ├── vcf_processor.py          # VCF file operations and validation
│   ├── entrez_api.py             # NCBI Entrez API integration
│   ├── pipeline.py               # Regular mode processing pipeline
│   └── sandbox.py                # Sandbox mode processing pipeline
├── unified_gui.py                # Unified interface (recommended entry point)
├── gui.py                        # Legacy regular mode GUI
├── sandbox_gui.py                # Standalone sandbox GUI
├── cli.py                        # Regular mode CLI
├── sandbox_cli.py                # Sandbox mode CLI
├── main.py                       # Smart entry point with mode detection
└── rsID_retrieval.py             # Original monolithic version (legacy)
```

This architecture enables:
- **Separation of Concerns:** Core logic independent of user interface
- **Reusability:** Core modules can be imported and used programmatically
- **Maintainability:** Bug fixes and features can be isolated to specific modules
- **Testability:** Core functions can be unit tested independently

## Installation

### Local Installation

#### Prerequisites
- **Python Version:** Python 3.8 or higher (tested with Python 3.12.3)
- **Operating System:** Windows, Linux, or macOS
- **Internet Connection:** Required for NCBI Entrez API access

#### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ayouballah/rsID_Retrieval.git
   cd rsID_Retrieval
   ```

2. **Create a Virtual Environment (Recommended):**
   
   **Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
   
   **Unix/macOS:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

#### Verification

To verify the installation, run:
```bash
python unified_gui.py
```

The unified GUI should launch without errors. If you encounter issues, see the [Troubleshooting](#troubleshooting) section.

### Docker Installation

Docker provides a containerized environment for running rsID Retrieval without installing Python or dependencies locally. The Docker image includes all CLI functionality with optimized rate limiting for NCBI API compliance.

#### Prerequisites
- **Docker:** Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- **Internet Connection:** Required for pulling image and NCBI API access

#### Quick Start with Docker

**Pull the pre-built image from Docker Hub:**
```bash
docker pull ayouballah/rsid-retrieval:latest
```

**Or build from source:**
```bash
git clone https://github.com/ayouballah/rsID_Retrieval.git
cd rsID_Retrieval
docker build -t rsid-retrieval .
```

#### Docker Features

- ✅ **No Python installation required** - Everything runs in container
- ✅ **CLI-only interface** - Optimized for automation and scripting
- ✅ **Optimized rate limiting** - 2 concurrent workers, 0.5s delays, 5 retries
- ✅ **Production-ready** - 94.1% annotation success rate on real datasets
- ✅ **Cross-platform** - Works on Windows, Linux, and macOS
- ✅ **Minimal image** - Based on python:3.12-slim (~605MB)

**Note:** The Docker image contains CLI functionality only. For GUI usage, use the local installation method.

For detailed Docker usage instructions, see [Docker Usage](#docker-usage) or consult `DOCKER_GUIDE.md`.

## Usage

### Unified Interface (Recommended)

The unified interface provides access to both Regular and Sandbox modes through a single tabbed window.

**Launch the Unified GUI:**
```bash
python unified_gui.py
```

**Features:**
- **Regular Tab:** CES1-specific processing with preset configurations
- **Sandbox Tab:** Universal chromosome processing with custom equations
- **Configuration Sub-tab:** Set up input/output files and parameters
- **Test Sub-tab:** Validate custom equations before processing
- **Background Processing:** Interface remains responsive during analysis
- **Real-time Progress:** Variant-level progress tracking

**Workflow:**
1. Enter your email address (required by NCBI Entrez)
2. Select the appropriate tab (Regular or Sandbox)
3. Choose your input VCF file
4. Specify output directory
5. Configure mode-specific parameters
6. Click "Run" to start processing
7. Monitor progress and view results

### Regular Mode

Regular mode is optimized for CES1 gene family studies on chromosome 16.

#### GUI Usage

**Using Unified Interface:**
```bash
python unified_gui.py
```
Select the "Regular" tab and configure:
- **Input VCF File:** Your chromosome 16 VCF file
- **Output Directory:** Where results will be saved
- **Modification Type:** 
  - `CES1P1-CES1`: Simple offset (position + modifier)
  - `CES1A2-CES1`: Conditional mapping with thresholds
- **Position Modifier:** Offset value (default: 55758218 for CES1P1)

**Using Legacy GUI:**
```bash
python gui.py
```

#### CLI Usage

```bash
python cli.py --input_vcf <path> --output_dir <path> --email <email> --type <modification_type> [--pos_modifier <value>]
```

**Arguments:**
- `--input_vcf`: Path to input VCF file
- `--output_dir`: Directory for output files
- `--email`: Your email (required by NCBI)
- `--type`: Modification type (`CES1P1-CES1` or `CES1A2-CES1`)
- `--pos_modifier`: Offset value (only for CES1P1-CES1, default: 55758218)

**Example:**
```bash
python cli.py --input_vcf "data/sample.vcf" --output_dir "results" --email "researcher@institution.edu" --type CES1P1-CES1 --pos_modifier 55758218
```

### Sandbox Mode

Sandbox mode enables universal chromosome processing with custom position transformations.

#### GUI Usage

**Using Unified Interface:**
```bash
python unified_gui.py
```
Select the "Sandbox" tab and configure:

**Configuration Sub-tab:**
- **Input VCF File:** VCF file for any chromosome
- **Output Directory:** Where results will be saved
- **Target Chromosome:** Chromosome identifier in any format (e.g., `16`, `chr16`, `NC_000016.10`, `X`)
- **Output Format:** Select desired chromosome format:
  - **RefSeq:** `NC_000016.10` (NCBI reference sequences)
  - **UCSC:** `chr16` (UCSC Genome Browser format)
  - **Ensembl:** `16` (Ensembl database format)
  - **numeric:** `16` (simple numeric format)
- **Position Equation:** Mathematical expression using `x` as the position variable
  - Examples: `x + 1000000`, `x * 2`, `x + 55758218`
  - Use preset buttons for common transformations

**Test Sub-tab:**
- Validate equations with sample positions
- Preview transformation results before processing
- Ensure equation correctness

**Using Standalone GUI:**
```bash
python sandbox_gui.py
```

#### CLI Usage

```bash
python sandbox_cli.py --input_vcf <path> --output_dir <path> --email <email> --chromosome <id> --equation <expr> [--format <type>]
```

**Arguments:**
- `--input_vcf`: Path to input VCF file
- `--output_dir`: Directory for output files
- `--email`: Your email (required by NCBI)
- `--chromosome`: Target chromosome (any format accepted)
- `--equation`: Position modification equation (use `x` for position)
- `--format`: Output chromosome format (default: `RefSeq`)
  - Options: `RefSeq`, `UCSC`, `Ensembl`, `numeric`

**Example:**
```bash
python sandbox_cli.py --input_vcf "data/chr1.vcf" --output_dir "results" --email "researcher@institution.edu" --chromosome "1" --equation "x + 500000" --format "UCSC"
```

### Command-Line Interface

#### Using the Smart Entry Point

The `main.py` script automatically detects the appropriate mode based on provided arguments:

```bash
python main.py [arguments]
```

- If `--type` is provided: Uses Regular mode
- If `--chromosome` and `--equation` are provided: Uses Sandbox mode
- If no arguments: Launches unified GUI

### Docker Usage

Docker enables running rsID Retrieval in an isolated container without local Python installation. The Docker image provides CLI functionality with optimized NCBI API rate limiting.

#### Basic Docker Workflow

**1. Pull the image (if not already available):**
```bash
docker pull ayouballah/rsid-retrieval:latest
```

**2. Prepare your data:**
- Place your VCF file in a directory (e.g., `/path/to/data/`)
- Create an output directory or use the same directory

**3. Run the container:**

**Regular Mode (CES1P1):**
```bash
docker run --rm \
  -v /path/to/data:/data \
  ayouballah/rsid-retrieval:latest \
  --input_vcf /data/input.vcf \
  --output_dir /data/results \
  --type CES1P1-CES1 \
  --email your.email@institution.edu
```

**Regular Mode (CES1A2):**
```bash
docker run --rm \
  -v /path/to/data:/data \
  ayouballah/rsid-retrieval:latest \
  --input_vcf /data/input.vcf \
  --output_dir /data/results \
  --type CES1A2-CES1 \
  --email your.email@institution.edu
```

**Sandbox Mode:**
```bash
docker run --rm \
  -v /path/to/data:/data \
  ayouballah/rsid-retrieval:latest \
  --mode sandbox \
  --input_vcf /data/input.vcf \
  --output_dir /data/results \
  --chromosome 16 \
  --equation "x + 1000000" \
  --format UCSC \
  --email your.email@institution.edu
```

#### Docker Command Breakdown

| Component | Description |
|-----------|-------------|
| `docker run` | Execute container |
| `--rm` | Automatically remove container after execution |
| `-v /path/to/data:/data` | Mount local directory to container's `/data` |
| `ayouballah/rsid-retrieval:latest` | Docker image name and tag |
| `--input_vcf /data/input.vcf` | Path to VCF file (inside container) |
| `--output_dir /data/results` | Output directory (inside container) |
| `--email your@email.com` | Your email for NCBI Entrez API |

#### Windows-Specific Docker Usage

**Windows PowerShell:**
```powershell
docker run --rm `
  -v "C:\Users\YourName\data:/data" `
  ayouballah/rsid-retrieval:latest `
  --input_vcf "/data/input.vcf" `
  --output_dir "/data/results" `
  --type CES1P1-CES1 `
  --email your.email@institution.edu
```

**Windows Command Prompt:**
```cmd
docker run --rm ^
  -v "C:\Users\YourName\data:/data" ^
  ayouballah/rsid-retrieval:latest ^
  --input_vcf "/data/input.vcf" ^
  --output_dir "/data/results" ^
  --type CES1P1-CES1 ^
  --email your.email@institution.edu
```

#### Docker Performance

The Docker image uses ultra-conservative rate limiting settings for maximum reliability:

| Setting | Value | Purpose |
|---------|-------|---------|
| Concurrent Workers | 2 | Avoid NCBI rate limits |
| Minimum Delay | 0.5s | Ensure API compliance |
| Max Retries | 5 | Recover from transient failures |
| Retry Backoff | 1.5s exponential | Progressive retry delays |

**Expected Performance:**
- Processing speed: ~1.9 variants/second
- Success rate: 94%+ on production datasets
- HTTP 429 errors: Zero or minimal with retry recovery

#### Docker Examples

**Example 1: Process 422-variant CES1P1 file**
```bash
docker run --rm \
  -v "$PWD/data:/data" \
  ayouballah/rsid-retrieval:latest \
  --input_vcf /data/Ces1p1_Ces1_S1.vcf \
  --output_dir /data/results \
  --type CES1P1-CES1 \
  --email researcher@university.edu
```
Expected time: ~3-4 minutes

**Example 2: Sandbox mode with chromosome 1**
```bash
docker run --rm \
  -v "$PWD/data:/data" \
  ayouballah/rsid-retrieval:latest \
  --mode sandbox \
  --input_vcf /data/chr1.vcf \
  --output_dir /data/chr1_results \
  --chromosome 1 \
  --equation "x + 500000" \
  --format RefSeq \
  --email researcher@university.edu
```

**Example 3: Running unit tests in Docker**
```bash
docker run --rm ayouballah/rsid-retrieval:latest python /app/run_tests.py
```

#### Troubleshooting Docker Issues

**Issue: Permission denied on output directory**
```
Solution: Ensure the output directory exists and has write permissions
mkdir -p data/results
chmod 777 data/results  # Linux/macOS
```

**Issue: File not found in container**
```
Solution: Verify volume mount path matches your local directory
Use absolute paths for -v argument
```

**Issue: Slow processing**
```
Solution: This is expected - Docker uses conservative rate limiting
422 variants typically process in 3-4 minutes
```

For comprehensive Docker documentation, see `DOCKER_GUIDE.md` in the repository.

## Chromosome Format Support

The sandbox mode handles multiple chromosome format conventions.

### Input Format Detection

The tool automatically detects and normalizes input chromosome identifiers. You do not need to specify the input format type.

**Supported Input Formats:**
- **Numeric:** `1`, `16`, `22`, `X`, `Y`, `MT`
- **UCSC:** `chr1`, `chr16`, `chrX`, `chr22`
- **RefSeq:** `NC_000001.11`, `NC_000016.10`, `NC_000023.11`
- **Partial RefSeq:** `NC_000016` (version number optional)

### Output Format Selection

Choose the output format based on downstream analysis requirements:

| Format | Example | Best For | Notes |
|--------|---------|----------|-------|
| **RefSeq** | `NC_000016.10` | NCBI tools, dbSNP, official databases | Recommended for NCBI API compatibility |
| **UCSC** | `chr16` | UCSC Genome Browser, IGV, visualization tools | Most widely used in genome browsers |
| **Ensembl** | `16` | Ensembl database, European bioinformatics resources | Clean format for international databases |
| **numeric** | `16` | Custom pipelines, minimal formatting needs | Simplest representation |

### Format Conversion Examples

| Input | Output Format | Result | NCBI Query |
|-------|---------------|--------|------------|
| `16` | RefSeq | `NC_000016.10` | Uses `16` |
| `chr16` | RefSeq | `NC_000016.10` | Uses `16` |
| `NC_000016.10` | RefSeq | `NC_000016.10` | Uses `16` |
| `16` | UCSC | `chr16` | Uses `16` |
| `chr16` | UCSC | `chr16` | Uses `16` |
| `NC_000016.10` | numeric | `16` | Uses `16` |

**Important:** Regardless of input or output format, all NCBI Entrez API queries use the normalized numeric representation internally, ensuring consistent rsID retrieval.
## Parameters

### Common Parameters

| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `--input_vcf` | Path to the input VCF file | Yes | - |
| `--output_dir` | Directory where output files will be saved | Yes | - |
| `--email` | Email address (required by NCBI Entrez API) | Yes | - |

### Regular Mode Parameters

| Parameter | Description | Required | Default | Options |
|-----------|-------------|----------|---------|---------|
| `--type` | Type of position modification | Yes | - | `CES1P1-CES1`, `CES1A2-CES1` |
| `--pos_modifier` | Value to add to each POS entry | Only for CES1P1-CES1 | 55758218 | Any positive integer |

### Sandbox Mode Parameters

| Parameter | Description | Required | Default | Options |
|-----------|-------------|----------|---------|---------|
| `--chromosome` | Target chromosome identifier | Yes | - | Any format: `16`, `chr16`, `NC_000016.10` |
| `--equation` | Position modification equation (use `x` for position) | Yes | - | Valid Python expression: `x + 1000000`, `x * 2` |
| `--format` | Output chromosome format | No | `RefSeq` | `RefSeq`, `UCSC`, `Ensembl`, `numeric` |

### Output Files

Both modes generate the following output files in the specified output directory:

| File | Description |
|------|-------------|
| `*_modified.vcf` | VCF with modified positions |
| `*_cleaned.vcf` | Cleaned VCF with standardized columns |
| `*_annotated.vcf` | VCF annotated with rsIDs from NCBI |
| `*_with_rsids.vcf` | Filtered VCF containing only variants with rsIDs |
| `*_significant.vcf` | High-quality variants (QUAL >= 20) with rsIDs |
| `*_report.txt` | Summary report with statistics |

Sandbox mode additionally includes configuration details in the summary report.

## Examples

### Example 1: Regular Mode - CES1P1 Processing (GUI)

```bash
python unified_gui.py
```
1. Select "Regular" tab
2. Browse to input VCF file: `data/ces1p1_sample.vcf`
3. Select output directory: `results/ces1p1`
4. Enter email: `researcher@institution.edu`
5. Select modification type: `CES1P1-CES1`
6. Set position modifier: `55758218`
7. Click "Run"

### Example 2: Regular Mode - CES1P1 Processing (CLI)

```bash
python cli.py \
  --input_vcf "data/ces1p1_sample.vcf" \
  --output_dir "results/ces1p1" \
  --email "researcher@institution.edu" \
  --type CES1P1-CES1 \
  --pos_modifier 55758218
```

### Example 3: Regular Mode - CES1A2 Processing (CLI)

```bash
python cli.py \
  --input_vcf "data/ces1a2_sample.vcf" \
  --output_dir "results/ces1a2" \
  --email "researcher@institution.edu" \
  --type CES1A2-CES1
```

### Example 4: Sandbox Mode - Chromosome 1 with Offset (GUI)

```bash
python unified_gui.py
```
1. Select "Sandbox" tab
2. Browse to input VCF file: `data/chr1_sample.vcf`
3. Select output directory: `results/chr1_custom`
4. Enter email: `researcher@institution.edu`
5. Enter target chromosome: `1` (or `chr1` or `NC_000001.11`)
6. Select output format: `UCSC`
7. Enter equation: `x + 500000`
8. Click "Test Equation" to verify (optional)
9. Click "Run"

### Example 5: Sandbox Mode - Chromosome X with Complex Transformation (CLI)

```bash
python sandbox_cli.py \
  --input_vcf "data/chrX_variants.vcf" \
  --output_dir "results/chrX_analysis" \
  --email "researcher@institution.edu" \
  --chromosome "X" \
  --equation "x + 1000000" \
  --format "RefSeq"
```

### Example 6: Sandbox Mode - Using RefSeq Input with UCSC Output (CLI)

```bash
python sandbox_cli.py \
  --input_vcf "data/sample.vcf" \
  --output_dir "results/format_conversion" \
  --email "researcher@institution.edu" \
  --chromosome "NC_000022.11" \
  --equation "x" \
  --format "UCSC"
```
This converts chromosome 22 from RefSeq format to UCSC format without modifying positions.

### Example 7: Using Smart Entry Point

```bash
# Launches unified GUI
python main.py

# Automatically detects Regular mode
python main.py --input_vcf "data/sample.vcf" --output_dir "results" --email "user@email.com" --type CES1P1-CES1

# Automatically detects Sandbox mode
python main.py --input_vcf "data/sample.vcf" --output_dir "results" --email "user@email.com" --chromosome "16" --equation "x + 1000000"
```
## Dependencies

rsID Retrieval relies on several well-maintained third-party libraries. The correct versions are automatically installed when using pip with the requirements file.

### Required Packages

| Package | Version | Purpose |
|---------|---------|---------|
| pandas | 2.2.2 | Data manipulation and VCF processing |
| biopython | 1.84 | NCBI Entrez API integration |
| PyQt6 | 6.7.0 | Graphical user interface |
| tqdm | 4.66.4 | Progress bars for CLI |

### Installation

All dependencies are specified in `requirements.txt`:

```bash
pip install -r requirements.txt
```

For CLI-only usage (without GUI support), you can use:

```bash
pip install -r requirements_no_pyqt.txt
```

## Configuration

The tool uses a configuration file (`config.json`) to persist user settings between sessions.

### Configuration File Location

The `config.json` file is automatically created in the application directory on first run.

### Configuration Structure

```json
{
  "email": "your_email@institution.edu"
}
```

### Email Requirement

The NCBI Entrez API requires users to provide an email address. This is used by NCBI to:
- Contact users in case of problems with their queries
- Track usage patterns for resource allocation
- Comply with NCBI usage policies

**Privacy:** Your email is only sent to NCBI Entrez and is not stored or transmitted elsewhere.

### Setting Email

**GUI Method:**
- Enter your email in the email field
- The application automatically saves it to `config.json`
- The email persists across sessions

**CLI Method:**
- Provide `--email` parameter with each command
- Alternatively, manually create/edit `config.json` with your email

**Manual Configuration:**
Create or edit `config.json` in the application directory:
```json
{
  "email": "researcher@institution.edu"
}
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Import Errors or Missing Modules

**Error Message:**
```
ModuleNotFoundError: No module named 'PyQt6'
```

**Solution:**
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

If using a virtual environment, verify it is activated.

---

#### Issue: VCF File Format Errors

**Error Message:**
```
Invalid VCF file: Missing required column: #CHROM
```

**Solution:**
- Verify the VCF file has proper headers
- Ensure the file follows VCF format specification
- Check that the file contains the required columns: `#CHROM`, `POS`, `ID`, `REF`, `ALT`, `QUAL`, `FILTER`
- Validate the VCF file has at least one data row

---

#### Issue: NCBI Entrez Connection Errors

**Error Message:**
```
Entrez test failed: HTTP Error 429: Too Many Requests
```

**Solution:**
- The tool implements rate limiting, but occasionally NCBI may throttle requests
- Wait a few minutes and retry
- Check your internet connection
- Verify NCBI services are operational: https://www.ncbi.nlm.nih.gov/

---

#### Issue: Email Not Accepted

**Error Message:**
```
Valid email address required for Entrez API
```

**Solution:**
- Ensure email contains '@' symbol
- Use a valid institutional or personal email
- Email format: `user@domain.com`

---

#### Issue: GUI Not Launching (Windows)

**Error Message:**
```
'charmap' codec can't encode character
```

**Solution:**
This encoding issue has been fixed in recent versions. Update to the latest version:
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

#### Issue: Sandbox Equation Errors

**Error Message:**
```
Invalid equation syntax: name 'y' is not defined
```

**Solution:**
- Equations must use `x` as the variable representing the position
- Valid: `x + 1000000`, `x * 2`, `x + 55758218`
- Invalid: `y + 1000`, `pos + 1000`, `x +` (incomplete)
- Test equations using the "Test Equation" button before processing

---

#### Issue: No rsIDs Found

**Problem:**
Processing completes but no rsIDs are annotated.

**Possible Causes and Solutions:**
1. **Incorrect chromosome format in VCF:**
   - Solution: The tool automatically standardizes chromosome identifiers, but verify input VCF uses standard formats
   
2. **Positions don't match dbSNP:**
   - Solution: Verify position modifications are correct for your reference genome
   
3. **Variants not in dbSNP:**
   - Solution: Novel or rare variants may not have rsIDs
   
4. **Network issues:**
   - Solution: Check internet connection and NCBI service status

---

#### Issue: Slow Processing

**Problem:**
Annotation takes longer than expected.

**Solutions:**
- **Expected behavior:** Processing speed depends on:
  - Number of variants (larger files take longer)
  - NCBI server response times
  - Network latency
- **Optimization:** The tool uses parallel processing with 4 workers and 0.3s rate limiting for optimal balance
- **Typical speed:** Approximately 10-20 variants per second with good network conditions

---

### Getting Help

If you encounter issues not listed here:

1. **Check existing documentation:**
   - Review relevant guide files (`docs/SANDBOX_GUIDE.md`, `docs/UNIFIED_GUI_GUIDE.md`)
   - Check `CHANGELOG.md` for migration guidance

2. **Verify installation:**
   - Ensure Python version >= 3.8
   - Confirm all dependencies are installed
   - Try running with `python -v` for verbose output

3. **Report issues:**
   - Open an issue on GitHub: https://github.com/ayouballah/rsID_Retrieval/issues
   - Include error messages, Python version, and operating system
   - Provide minimal example to reproduce the issue

## Performance

### Optimization Features

The tool implements several performance optimizations:

**Parallel Processing:**
- Multi-threaded Entrez API queries using ThreadPoolExecutor
- 4 concurrent workers for optimal throughput
- Intelligent batch processing with size 2 for maximum parallelism

**Rate Limiting:**
- 0.3-second delay between requests to avoid NCBI throttling
- Semaphore-based concurrency control
- Automatic retry on transient failures

**Progress Tracking:**
- Real-time variant-level progress (not batch-based)
- Accurate time estimation
- Non-blocking UI updates in GUI mode

### Performance Metrics

Based on testing with typical VCF files:

| Metric | Value |
|--------|-------|
| Processing Speed | 10-20 variants/second |
| Improvement over Sequential | 63% faster |
| Worker Threads | 4 |
| Rate Limit | 0.3s between requests |
| Batch Size | 2 variants |

**Note:** Actual performance depends on network conditions, NCBI server load, and file size.


## Contributing

Contributions to rsID Retrieval are welcome and appreciated. Whether you want to report bugs, suggest features, or submit code improvements, your input helps make this tool better for the research community.

### How to Contribute

**Reporting Issues:**
- Use GitHub Issues to report bugs or suggest enhancements
- Provide detailed information including:
  - Clear description of the issue or suggestion
  - Steps to reproduce (for bugs)
  - Python version and operating system
  - Error messages and relevant logs
  - Expected vs actual behavior

**Submitting Code:**
- Fork the repository
- Create a feature branch (`git checkout -b feature/improvement`)
- Make your changes following the existing code style
- Test your changes thoroughly
- Commit with clear, descriptive messages
- Push to your fork and submit a pull request

**Areas for Contribution:**
- Bug fixes and error handling improvements
- Performance optimizations
- Additional chromosome format support
- Enhanced documentation and examples
- Unit tests and integration tests
- UI/UX improvements
- Additional preset equations for sandbox mode

### Development Guidelines

**Code Style:**
- Follow PEP 8 Python style guidelines
- Use descriptive variable and function names
- Add docstrings to functions and classes
- Comment complex logic

**Testing:**
- Test changes with various VCF file formats
- Verify both GUI and CLI functionality
- Test edge cases and error conditions
- Ensure cross-platform compatibility

**Documentation:**
- Update README.md for user-facing changes
- Add examples for new features
- Update relevant guide files
- Keep changelog current

### Getting Started with Development

1. **Set up development environment:**
   ```bash
   git clone https://github.com/ayouballah/rsID_Retrieval.git
   cd rsID_Retrieval
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Explore the codebase:**
   - Review `core/` modules for business logic
   - Check GUI implementations in `*_gui.py` files
   - Examine CLI scripts in `*_cli.py` files

3. **Make changes and test:**
   - Modify code in a feature branch
   - Test using sample VCF files
   - Verify both modes (Regular and Sandbox)

4. **Submit your contribution:**
   - Push to your fork
   - Create a pull request with description
   - Respond to review feedback

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for complete details.

### MIT License Summary

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the following conditions:

- The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
- The software is provided "as is", without warranty of any kind, express or implied.

For the full license text, see the LICENSE file in the repository.

---

## Acknowledgments

This tool was developed to support targeted sequencing research and variant analysis workflows. Special thanks to:

- NCBI for providing the Entrez API and dbSNP database
- The BioPython team for comprehensive bioinformatics tools
- The pandas development team for powerful data manipulation capabilities
- The PyQt team for excellent GUI framework support

## Citation

If you use rsID Retrieval in your research, please cite this repository:

```
rsID Retrieval: A flexible tool for VCF processing and rsID annotation
GitHub: https://github.com/ayouballah/rsID_Retrieval
```

## Contact

For questions, issues, or collaboration inquiries:

- **GitHub Issues:** https://github.com/ayouballah/rsID_Retrieval/issues
- **Repository:** https://github.com/ayouballah/rsID_Retrieval

---

**Version:** 2.0 (Modular Architecture with Unified Interface)  
**Last Updated:** October 2025  
**Status:** Active Development
