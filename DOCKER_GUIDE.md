# Docker Guide for rsID Retrieval

## Building the Docker Image

Build the Docker image from the repository root:

```bash
docker build -t rsid-retrieval .
```

## Basic Usage

### Regular Mode (CES1)

Run regular CES1 processing:

```bash
docker run --rm -v ${PWD}:/data rsid-retrieval \
  --input_vcf /data/your_file.vcf \
  --output_dir /data/results \
  --type CES1P1-CES1 \
  --email your.email@example.com
```

### Sandbox Mode

Override the entry point to use sandbox mode:

```bash
docker run --rm -v ${PWD}:/data \
  --entrypoint python rsid-retrieval \
  /app/sandbox_cli.py \
  --input_vcf /data/your_file.vcf \
  --output_dir /data/results \
  --chromosome "16" \
  --equation "x + 55758218" \
  --format "RefSeq" \
  --email your.email@example.com
```

## Volume Mounting

The `/data` directory in the container is the working directory. Mount your local directory:

**Linux/Mac:**
```bash
-v $(pwd):/data
```

**Windows (PowerShell):**
```bash
-v ${PWD}:/data
```

**Windows (Command Prompt):**
```bash
-v %cd%:/data
```

## Examples

### Example 1: Basic CES1 Processing

```bash
docker run --rm \
  -v ${PWD}:/data \
  rsid-retrieval \
  --input_vcf /data/sample.vcf \
  --output_dir /data/ces1_results \
  --type CES1P1-CES1 \
  --email researcher@university.edu
```

### Example 2: Sandbox with Custom Equation

```bash
docker run --rm \
  -v ${PWD}:/data \
  --entrypoint python \
  rsid-retrieval /app/sandbox_cli.py \
  --input_vcf /data/chr1.vcf \
  --output_dir /data/chr1_results \
  --chromosome "1" \
  --equation "x + 1000000" \
  --format "RefSeq" \
  --email researcher@university.edu
```

### Example 3: Test Equation Before Processing

```bash
docker run --rm \
  --entrypoint python \
  rsid-retrieval /app/sandbox_cli.py \
  --test-equation \
  --equation "x + 55758218" \
  --test-positions "100,1000,10000"
```

### Example 4: Get Help

```bash
# Regular mode help
docker run --rm rsid-retrieval --help

# Sandbox mode help
docker run --rm \
  --entrypoint python \
  rsid-retrieval /app/sandbox_cli.py --help
```

## Running Tests in Docker

Run the test suite inside the container:

```bash
docker run --rm \
  --entrypoint python \
  rsid-retrieval /app/run_tests.py
```

## Advanced Usage

### Interactive Shell

Access the container interactively:

```bash
docker run --rm -it \
  -v ${PWD}:/data \
  --entrypoint /bin/bash \
  rsid-retrieval
```

Inside the container:
```bash
# Run regular processing
python /app/cli.py --help

# Run sandbox processing
python /app/sandbox_cli.py --help

# Run tests
python /app/run_tests.py
```

### Custom Python Script

Run your own Python script that uses the tool's modules:

```bash
docker run --rm \
  -v ${PWD}:/data \
  --entrypoint python \
  rsid-retrieval /data/your_script.py
```

## Docker Compose (Optional)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  rsid-retrieval:
    build: .
    image: rsid-retrieval
    volumes:
      - ./data:/data
    environment:
      - ENTREZ_EMAIL=your.email@example.com
    command: >
      --input_vcf /data/input.vcf
      --output_dir /data/results
      --type CES1P1-CES1
      --email ${ENTREZ_EMAIL}
```

Run with:
```bash
docker-compose run rsid-retrieval
```

## Troubleshooting

### Permission Issues

If you encounter permission issues with output files:

```bash
# Run with current user ID
docker run --rm \
  -v ${PWD}:/data \
  --user $(id -u):$(id -g) \
  rsid-retrieval [options]
```

### File Not Found

Ensure file paths inside the container start with `/data/`:
- Correct: `--input_vcf /data/file.vcf`
- Incorrect: `--input_vcf file.vcf`

### Memory Issues

For large VCF files, increase Docker memory:

```bash
docker run --rm \
  --memory=4g \
  -v ${PWD}:/data \
  rsid-retrieval [options]
```

## Notes

- GUI modes are not available in Docker (CLI only)
- The container uses `requirements_no_pyqt.txt` (no GUI dependencies)
- UTF-8 encoding is set by default for cross-platform compatibility
- The working directory inside the container is `/data`
- Application files are in `/app`

## Building for Different Platforms

Build for multiple architectures:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t rsid-retrieval .
```

## Image Size Optimization

The image uses `python:3.12-slim` for a smaller footprint while maintaining functionality. Current size should be approximately 200-300 MB.
