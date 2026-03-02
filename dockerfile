# Use the official Python base image with a specific Python version
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ARG PYTHONPATH=""
ENV PYTHONPATH=/app:${PYTHONPATH}

# Install necessary system packages including bioinformatics tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        bcftools \
        samtools \
        tabix \
        default-jre-headless \
        wget \
        curl \
        unzip \
        git \
        && rm -rf /var/lib/apt/lists/*

# Install SnpSift (part of snpEff) - clone from GitHub
# The repo includes pre-built JARs, no compilation needed
RUN cd /opt && \
    git clone https://github.com/pcingola/SnpEff.git snpeff && \
    cd snpeff && \
    chmod +x scripts/*.sh && \
    ls -la *.jar || echo "Note: JAR files may be in subdirectory"

ENV PATH="/opt/snpeff/scripts:${PATH}"

# Set work directory
WORKDIR /app

# Copy requirements file for CLI-only usage (no GUI)
COPY requirements_no_pyqt.txt .

# Install Python dependencies including benchmark tools
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements_no_pyqt.txt && \
    pip install --no-cache-dir matplotlib pandas psutil

# Copy the entire application
COPY core/ ./core/
COPY cli.py sandbox_cli.py main.py ./
COPY run_tests.py ./
COPY tests/ ./tests/

# Create directory for input/output
RUN mkdir -p /data

# Set working directory for data
WORKDIR /data

# Default entrypoint - use python3 so we can run any script
# Usage examples:
#   Regular mode: docker run rsid-retrieval /app/cli.py --help
#   Sandbox mode: docker run rsid-retrieval /app/sandbox_cli.py --help
#   Benchmark: docker run rsid-retrieval /app/wsl_benchmark.py
ENTRYPOINT ["python3"]