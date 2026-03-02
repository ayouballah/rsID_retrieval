#!/usr/bin/env bash
set -euo pipefail

# setup_wsl_env.sh
# Install bcftools, samtools (bgzip/tabix), python3, and dependencies in WSL from scratch.
# Run this once: wsl bash setup_wsl_env.sh

echo "[setup] Installing bcftools, samtools (bgzip/tabix), python3..."

# Update package lists
sudo apt-get update

# Install build dependencies and tools
sudo apt-get install -y \
  wget \
  bzip2 \
  gcc \
  make \
  zlib1g-dev \
  libbz2-dev \
  liblzma-dev \
  libcurl4-openssl-dev \
  libssl-dev \
  libncurses5-dev \
  python3 \
  python3-pip \
  python3-venv

# Create temporary build directory
BUILD_DIR="/tmp/biotools_build"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Install htslib (provides bgzip and tabix) - latest stable version
HTSLIB_VERSION="1.20"
echo "[setup] Downloading htslib ${HTSLIB_VERSION}..."
wget -q "https://github.com/samtools/htslib/releases/download/${HTSLIB_VERSION}/htslib-${HTSLIB_VERSION}.tar.bz2"
tar -xjf "htslib-${HTSLIB_VERSION}.tar.bz2"
cd "htslib-${HTSLIB_VERSION}"
echo "[setup] Building htslib..."
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
cd "$BUILD_DIR"

# Install bcftools - latest stable version
BCFTOOLS_VERSION="1.20"
echo "[setup] Downloading bcftools ${BCFTOOLS_VERSION}..."
wget -q "https://github.com/samtools/bcftools/releases/download/${BCFTOOLS_VERSION}/bcftools-${BCFTOOLS_VERSION}.tar.bz2"
tar -xjf "bcftools-${BCFTOOLS_VERSION}.tar.bz2"
cd "bcftools-${BCFTOOLS_VERSION}"
echo "[setup] Building bcftools..."
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
cd "$BUILD_DIR"

# Update library cache
sudo ldconfig

# Clean up
cd ~
rm -rf "$BUILD_DIR"

# Install SnpEff
echo "[setup] Installing SnpEff..."
SNPEFF_DIR="/opt/snpEff"
sudo mkdir -p "$SNPEFF_DIR"
cd "$SNPEFF_DIR"
echo "[setup] Downloading SnpEff (latest core)..."
sudo wget -q https://snpeff.blob.core.windows.net/versions/snpEff_latest_core.zip
echo "[setup] Extracting SnpEff..."
sudo unzip -q snpEff_latest_core.zip
sudo mv snpEff/* .
sudo rmdir snpEff
sudo rm snpEff_latest_core.zip

# Download GRCh38 database for SnpEff
echo "[setup] Downloading GRCh38 database for SnpEff..."
sudo java -jar "$SNPEFF_DIR/snpEff.jar" download -v GRCh38.mane.1.0.refseq || echo "[setup] Warning: Database download failed, continuing..."

# Verify installations
echo "[setup] Verifying installations..."
echo "  bgzip version:"
bgzip --version | head -n1
echo "  tabix version:"
tabix --version | head -n1
echo "  bcftools version:"
bcftools --version | head -n1
echo "  python3 version:"
python3 --version
echo "  snpEff location:"
ls -lh "$SNPEFF_DIR/snpEff.jar"

echo "[setup] ✓ Environment ready! bcftools, bgzip, tabix, python3, and SnpEff installed."
echo "[setup] You can now run: ./scripts/run_benchmark.ps1"
