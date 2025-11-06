# Use the official Python base image with a specific Python version
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ARG PYTHONPATH=""
ENV PYTHONPATH=/app:${PYTHONPATH}

# Install necessary system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements file for CLI-only usage (no GUI)
COPY requirements_no_pyqt.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements_no_pyqt.txt

# Copy the entire application
COPY core/ ./core/
COPY cli.py sandbox_cli.py main.py ./
COPY run_tests.py ./
COPY tests/ ./tests/

# Create directory for input/output
RUN mkdir -p /data

# Set working directory for data
WORKDIR /data

# Default to regular CLI mode, but can be overridden
# Usage examples:
#   Regular mode: docker run rsid-retrieval cli.py --help
#   Sandbox mode: docker run rsid-retrieval sandbox_cli.py --help
ENTRYPOINT ["python", "/app/cli.py"]