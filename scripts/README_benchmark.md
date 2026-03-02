Benchmark helper scripts
========================

Files added:

- `scripts/benchmark_wsl.sh` — Bash script intended to run inside WSL. It normalizes VCF CHROM fields, bgzips/tabix indexes them, selects dbSNP files under `dbsnp_temp`, runs `bcftools annotate`, attempts to run the repo `cli.py` for `rsID_retrieval`, and will run VEP (Docker image) and SnpEff (if a jar is present) when possible. Results are written to `benchmark_results/` under the repository root.

- `scripts/run_benchmark.ps1` — PowerShell wrapper you run from Windows. It converts the provided Windows VCF paths to WSL-style `/mnt/...` paths and calls the WSL script.

How to run (recommended)

1. Open PowerShell in the repository root.
2. Run (example):

```powershell
Benchmark helper scripts
========================

Files in this directory:

- `scripts/setup_wsl_env.sh` — Run once to install fresh bcftools, bgzip, tabix, python3 in WSL from official sources.
- `scripts/benchmark_config.json` — Configuration file declaring VCF paths, offsets (Ces1p1: +55758218), and dbSNP directory.
- `scripts/benchmark_wsl.sh` — Bash script that runs inside WSL. Reads config, normalizes VCFs (CHROM + offset), bgzips/indexes, selects dbSNP files, runs bcftools, rsID_retrieval, VEP (Docker), SnpEff if available. Results → `benchmark_results/`.
- `scripts/run_benchmark.ps1` — PowerShell wrapper to invoke the WSL script from Windows.

Quick Start
-----------

**Step 1: Setup WSL environment (one-time)**

Open PowerShell in repository root and run:

```powershell
wsl bash scripts/setup_wsl_env.sh
```

This installs bcftools 1.20, htslib (bgzip/tabix), and python3 from source. Takes ~5 minutes.

**Step 2: Edit config (if needed)**

Edit `scripts/benchmark_config.json` to adjust VCF paths or offsets. Current settings:
- Ces1p1: offset +55758218
- DPYD: offset 0
- clinvar_chr20: offset 0

**Step 3: Run benchmark**

From PowerShell in repository root:

```powershell
.\scripts\run_benchmark.ps1
```

This will:
1. Normalize VCF CHROMs (strip `ref|NC_*|:ranges`, `chr` prefix)
2. Apply position offsets (Ces1p1: POS + 55758218)
3. bgzip + tabix index each VCF
4. Run bcftools annotate (local dbSNP lookup)
5. Run rsID_retrieval (via python3 cli.py)
6. Try VEP (Docker image `ensemblorg/ensembl-vep` if present)
7. Try SnpEff (if jar exists at `/opt/snpEff/snpEff.jar`)

Results saved to `benchmark_results/` with tool-specific output VCFs.

Notes
-----

- **Ces1p1 offset**: The script automatically applies `POS = POS + 55758218` for the Ces1p1 file as specified in config.
- **dbSNP files**: Script prefers `dbsnp_chr{N}_numeric.vcf.gz` then falls back to `dbsnp_chr{N}.vcf.gz` or will bgzip `.vcf` on-the-fly.
- **VEP**: Requires Docker image. Pull with: `docker pull ensemblorg/ensembl-vep`
- **SnpEff**: Optional. Not installed by default. Script will skip if jar missing.
- **Python dependencies**: rsID_retrieval needs python3 + dependencies in WSL. If missing, that step is skipped.

Troubleshooting
---------------

- **"bcftools: command not found"**: Run `scripts/setup_wsl_env.sh` first.
- **"VCF not found"**: Check paths in `benchmark_config.json` are correct WSL paths (`/mnt/c/...`).
- **"python3 not available"**: Install python3 in WSL or skip rsID_retrieval step.
- **VEP fails**: Pull Docker image or comment out `run_vep()` call in benchmark_wsl.sh.

Next enhancements
-----------------

- Add result parser to count annotated rsIDs and generate comparison CSV/plots.
- Integrate ground-truth validation if reference rsID lists are available.
```

That will call WSL and execute the heavy work there so `bcftools` (and other Linux-only tools) are available.

Notes & assumptions

- The script expects WSL to be installed and `bash` available via `wsl`.
- It expects `bgzip`, `tabix`, `bcftools` and `python3` to be available inside WSL. If `python3` is missing, `rsID_retrieval` will be skipped (the script will print instructions).
- The script prefers `dbsnp_temp/dbsnp_chr<chrom>_numeric.vcf.gz` when available, otherwise falls back to `dbsnp_chr<chrom>.vcf.gz` or `.vcf` (will bgzip on the fly).
- For the Ces1 offset handling: the script provides a place to add file-specific offsets later (config) but currently does not modify POS automatically — edit the script or use the repo's `vcf_processor` utilities if you need the special offset workflow.
- VEP is invoked via the official Docker image `ensemblorg/ensembl-vep` if present locally; that image may require cache files or extra flags for realistic annotation — adjust the `run_vep()` function in `benchmark_wsl.sh` to fit your preferred VEP invocation.

Next steps I can do for you

- Add an optional JSON config (per-file offsets) and have the script apply offsets automatically.
- Integrate the repo's `vcf_processor` normalization so Ces1 offset logic is reused rather than duplicated.
- Add result parsing (count annotated IDs, compare to ground truth) and a CSV summary.
