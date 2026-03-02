#!/usr/bin/env bash
set -euo pipefail

# benchmark_wsl.sh
# Run inside WSL (bash). Usage:
#   ./benchmark_wsl.sh  (reads config from scripts/benchmark_config.json)
# The script will normalize CHROM fields, apply offsets (Ces1p1), bgzip+tabix each VCF,
# select appropriate dbSNP file, run bcftools annotate, rsID_retrieval (python),
# attempt VEP via Docker if available, and attempt snpEff if a jar exists.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_WSL="/mnt/c/Users/ayoub/Documents/GitHub/rsID_retrieval"
CONFIG_FILE="$SCRIPT_DIR/benchmark_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "ERROR: Config file not found: $CONFIG_FILE"
  exit 1
fi

# Read config using python3
DB_DIR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['dbsnp_dir'])")
OUTDIR=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['output_dir'])")
mkdir -p "$OUTDIR"
METRICS_JSON="$OUTDIR/benchmark_metrics.json"
echo "[]" > "$METRICS_JSON"

log() { echo "[benchmark] $*" >&2; }

current_millis() {
  date +%s%3N
}

record_metric() {
  local sample="$1"
  local tool="$2"
  local status="$3"
  local duration_ms="${4:-0}"
  local total_variants="${5:-0}"
  local annotated_variants="${6:-0}"
  local output_path="${7:-}"
  SAMPLE="$sample" TOOL="$tool" STATUS="$status" DURATION="$duration_ms" TOTAL="$total_variants" ANNOTATED="$annotated_variants" OUTPUT="$output_path" METRICS_PATH="$METRICS_JSON" python3 - <<'PY'
import json
import os

path = os.environ['METRICS_PATH']
entry = {
  "sample": os.environ['SAMPLE'],
  "tool": os.environ['TOOL'],
  "status": os.environ['STATUS'],
  "duration_seconds": float(os.environ['DURATION']) / 1000.0 if os.environ['DURATION'] else None,
  "total_variants": int(os.environ['TOTAL'] or 0),
  "annotated_variants": int(os.environ['ANNOTATED'] or 0),
  "output_path": os.environ['OUTPUT'],
}
try:
  with open(path) as fh:
    data = json.load(fh)
except FileNotFoundError:
  data = []

# keep only the latest metric per (sample, tool)
data = [d for d in data if not (d['sample'] == entry['sample'] and d['tool'] == entry['tool'])]
data.append(entry)

with open(path, 'w') as fh:
  json.dump(data, fh, indent=2)
PY
}

count_bcftools_annotations() {
  local vcf_file="$1"
  python3 - "$vcf_file" <<'PY'
import gzip
import os
import sys

path = sys.argv[1]
if not path or not os.path.exists(path):
  print("0,0")
  sys.exit(0)

open_fn = gzip.open if path.endswith('.gz') else open
total = annotated = 0
with open_fn(path, 'rt', encoding='utf-8', errors='ignore') as fh:
  for line in fh:
    if line.startswith('#'):
      continue
    total += 1
    fields = line.rstrip('\n').split('\t')
    if len(fields) > 2 and fields[2] and fields[2] != '.':
      annotated += 1
print(f"{total},{annotated}")
PY
}

count_snpeff_annotations() {
  local vcf_file="$1"
  python3 - "$vcf_file" <<'PY'
import os
import sys

path = sys.argv[1]
if not path or not os.path.exists(path):
  print("0,0")
  sys.exit(0)

total = annotated = 0
with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
  for line in fh:
    if line.startswith('#'):
      continue
    total += 1
    fields = line.rstrip('\n').split('\t')
    info = fields[7] if len(fields) > 7 else ''
    if 'ANN=' in info:
      annotated += 1
print(f"{total},{annotated}")
PY
}

extract_sandbox_counts() {
  local results_dir="$1"
  python3 - "$results_dir" <<'PY'
import os
import re
import sys

base = sys.argv[1]
summary_path = None
for root, _, files in os.walk(base):
  for name in files:
    if name.startswith('sandbox_report_') and name.endswith('.txt'):
      summary_path = os.path.join(root, name)
      break
  if summary_path:
    break

if not summary_path or not os.path.exists(summary_path):
  print("0,0")
  sys.exit(0)

total = annotated = 0
with open(summary_path, 'r', encoding='utf-8', errors='ignore') as fh:
  for line in fh:
    if 'Total variants:' in line:
      numbers = re.findall(r"\d+", line)
      if numbers:
        total = int(numbers[0])
    elif 'With rsID:' in line or 'with rsID:' in line:
      numbers = re.findall(r"\d+", line)
      if numbers:
        annotated = int(numbers[0])
print(f"{total},{annotated}")
PY
}

normalize_and_index() {
  local in_vcf="$1"
  local base_name=$(basename "$in_vcf")
  local tmp_vcf="$OUTDIR/${base_name%.vcf}.normalized.vcf"
  local gz_vcf="$tmp_vcf.gz"

  log "Normalizing CHROMs for $base_name -> $tmp_vcf"
  # ONLY normalize CHROM column - DO NOT change POS (that's rsID_retrieval's job)
  awk 'BEGIN{OFS="\t"}
    /^#/ {print; next}
    {
     chrom=$1;
     
     # Normalize CHROM: strip ref|NC_...|:ranges and convert to numeric
     if (match(chrom,/NC_[0-9]+\.[0-9]+/)) {
       nc=substr(chrom,RSTART,RLENGTH);
       # remove NC_ and leading zeros, drop version
       gsub(/^NC_0*/,"",nc);
       sub(/\..*/,"",nc);
       chrom=nc
     } else if (index(chrom,":")>0 && index(chrom,"ref|")>0) {
       if (match(chrom,/NC_[0-9]+\.[0-9]+/)) {
         nc=substr(chrom,RSTART,RLENGTH); gsub(/^NC_0*/,"",nc); sub(/\..*/,"",nc); chrom=nc
       }
     } else if (substr(chrom,1,3)=="chr") {
       chrom=substr(chrom,4)
     }
     
     # Update only CHROM column, preserve all other columns as-is
     $1=chrom;
     print
    }' "$in_vcf" > "$tmp_vcf"

  log "bgzip + tabix $tmp_vcf -> $gz_vcf"
  bgzip -f -c "$tmp_vcf" > "$gz_vcf" 2>&1
  tabix -f -p vcf "$gz_vcf" 2>&1 || log "Warning: tabix indexing failed (may not affect annotation)"
  printf "%s" "$gz_vcf"
}

select_dbsnp() {
  local chrom_raw="$1"
  # normalize chrom_raw to numeric if NC_* or numeric
  chrom="$chrom_raw"
  if [[ "$chrom" =~ NC_[0-9]+\.[0-9]+ ]]; then
    # extract digits
    chrom=$(echo "$chrom" | sed -E 's/NC_0*([0-9]+)\..*/\1/')
  fi
  # prefer numeric dbsnp file
  if [ -f "$DB_DIR/dbsnp_chr${chrom}_numeric.vcf.gz" ]; then
    echo "$DB_DIR/dbsnp_chr${chrom}_numeric.vcf.gz"
  elif [ -f "$DB_DIR/dbsnp_chr${chrom}.vcf.gz" ]; then
    echo "$DB_DIR/dbsnp_chr${chrom}.vcf.gz"
  elif [ -f "$DB_DIR/dbsnp_chr${chrom}.vcf" ]; then
    # compress on the fly
    bgzip -c "$DB_DIR/dbsnp_chr${chrom}.vcf" > "$OUTDIR/dbsnp_chr${chrom}.vcf.gz"
    tabix -p vcf "$OUTDIR/dbsnp_chr${chrom}.vcf.gz"
    echo "$OUTDIR/dbsnp_chr${chrom}.vcf.gz"
  else
    echo ""
  fi
}

run_bcftools() {
  local sample_name="$1"
  local vcf_gz="$2"
  local chrom_sample
  chrom_sample=$(zcat "$vcf_gz" | grep -v '^#' | head -n1 | cut -f1 || true)
  if [ -z "$chrom_sample" ]; then
    log "Could not detect chromosome in $vcf_gz"
    record_metric "$sample_name" "bcftools" "failed_no_chrom" 0 0 0 ""
    return
  fi
  local dbsnp_file
  dbsnp_file=$(select_dbsnp "$chrom_sample")
  if [ -z "$dbsnp_file" ]; then
    log "No dbSNP file found for chromosome '$chrom_sample' in $DB_DIR; skipping bcftools for $vcf_gz"
    record_metric "$sample_name" "bcftools" "skipped_no_dbsnp" 0 0 0 ""
    return
  fi

  local base_vcf_name=$(basename "${vcf_gz/.gz/}")
  local out="$OUTDIR/bcftools_${base_vcf_name}.gz"
  log "Running bcftools annotate (dbsnp=$dbsnp_file) on $vcf_gz -> $out"
  local start_ms=$(current_millis)
  if bcftools annotate -a "$dbsnp_file" -c ID -o "$out" -O z "$vcf_gz"; then
    tabix -f -p vcf "$out" 2>/dev/null || true
    local end_ms=$(current_millis)
    local duration=$((end_ms - start_ms))
    local counts
    counts=$(count_bcftools_annotations "$out")
  local total=${counts%%,*}
  local annotated=${counts##*,}
  total=${total//[[:space:]]/}
  annotated=${annotated//[[:space:]]/}
    record_metric "$sample_name" "bcftools" "success" "$duration" "$total" "$annotated" "$out"
  else
    local end_ms=$(current_millis)
    local duration=$((end_ms - start_ms))
    record_metric "$sample_name" "bcftools" "failed" "$duration" 0 0 "$out"
  fi
}

run_rsid_retrieval() {
  local sample_name="$1"
  local original_vcf="$2"
  
  # Try running local Python CLI if python3 exists.
  if command -v python3 >/dev/null 2>&1; then
    log "Running rsID_retrieval (sandbox) on ORIGINAL file: $original_vcf"
    
    # Determine chromosome and equation based on file name
    local chrom=""
    local equation=""
    local chrom_format="RefSeq"
    
    if [[ "$sample_name" == *"Ces1"* ]]; then
      chrom="16"
      equation="x + 55758218"  # Ces1p1 offset
    elif [[ "$sample_name" == *"DPYD"* ]]; then
      chrom="1"
      equation="x"  # No offset
      chrom_format="numeric"
    elif [[ "$sample_name" == *"chr20"* ]] || [[ "$sample_name" == *"clinvar"* ]]; then
      chrom="20"
      equation="x"  # No offset
      chrom_format="numeric"
    else
      log "Unknown file type: $sample_name, skipping rsID_retrieval"
      record_metric "$sample_name" "rsID_retrieval (sandbox)" "skipped_unknown_sample" 0 0 0 ""
      return
    fi
    
    log "  Using chromosome=$chrom, equation='$equation', format=$chrom_format"
    local start_ms=$(current_millis)
    if python3 "$REPO_WSL/sandbox_cli.py" \
      --input_vcf "$original_vcf" \
      --output_dir "$OUTDIR/rsid_${sample_name}" \
      --email "ayoubellah4@gmail.com" \
      --chromosome "$chrom" \
      --equation "$equation" \
      --format "$chrom_format"; then
      local end_ms=$(current_millis)
      local duration=$((end_ms - start_ms))
      local results_dir="$OUTDIR/rsid_${sample_name}"
      local counts
      counts=$(extract_sandbox_counts "$results_dir")
  local total=${counts%%,*}
  local annotated=${counts##*,}
  total=${total//[[:space:]]/}
  annotated=${annotated//[[:space:]]/}
  total=${total//[[:space:]]/}
  annotated=${annotated//[[:space:]]/}
      record_metric "$sample_name" "rsID_retrieval (sandbox)" "success" "$duration" "$total" "$annotated" "$results_dir"
    else
      local end_ms=$(current_millis)
      local duration=$((end_ms - start_ms))
      record_metric "$sample_name" "rsID_retrieval (sandbox)" "failed" "$duration" 0 0 "$OUTDIR/rsid_${sample_name}"
      log "rsID_retrieval failed for $original_vcf"
    fi
  else
    log "python3 not available in WSL; skipping rsID_retrieval (or run via Docker)."
    record_metric "$sample_name" "rsID_retrieval (sandbox)" "skipped_no_python" 0 0 0 ""
  fi
}

run_vep() {
  local sample_name="$1"
  local vcf_gz="$2"
  if docker image inspect ensemblorg/ensembl-vep >/dev/null 2>&1; then
    log "Running VEP docker image on $vcf_gz"
    local base_vcf_name=$(basename "${vcf_gz/.gz/}")
    local out_base="$OUTDIR/vep_${base_vcf_name}"
    local start_ms=$(current_millis)
    if docker run --rm -v "$REPO_WSL":/data ensemblorg/ensembl-vep vep -i "/data/${vcf_gz#${REPO_WSL}/}" -o "/data/${out_base}" --vcf --compress_output bgzip; then
      local end_ms=$(current_millis)
      local duration=$((end_ms - start_ms))
      local out_path="${out_base}.gz"
      local counts
      counts=$(count_bcftools_annotations "$out_path")
      local total=${counts%%,*}
      local annotated=${counts##*,}
  total=${total//[[:space:]]/}
  annotated=${annotated//[[:space:]]/}
      record_metric "$sample_name" "VEP" "success" "$duration" "$total" "$annotated" "$out_path"
    else
      local end_ms=$(current_millis)
      local duration=$((end_ms - start_ms))
      record_metric "$sample_name" "VEP" "failed" "$duration" 0 0 "${out_base}.gz"
      log "VEP run failed"
    fi
  else
    log "VEP docker image not available locally; skipping VEP."
    record_metric "$sample_name" "VEP" "skipped_missing_image" 0 0 0 ""
  fi
}

run_snpeff() {
  local sample_name="$1"
  local vcf_gz="$2"
  local file_name=$(basename "$vcf_gz" .normalized.vcf.gz)
  
  # Try to find snpEff jar in common locations
  if [ -f "/opt/snpEff/snpEff.jar" ]; then
    log "Running snpEff on $vcf_gz"
    local out="$OUTDIR/snpeff_${file_name}.vcf"
    local start_ms=$(current_millis)
    if java -Xmx4g -jar /opt/snpEff/snpEff.jar ann -v GRCh38.86 "$vcf_gz" > "$out" 2>&1; then
      local end_ms=$(current_millis)
      local duration=$((end_ms - start_ms))
      local counts
      counts=$(count_snpeff_annotations "$out")
      local total=${counts%%,*}
      local annotated=${counts##*,}
  total=${total//[[:space:]]/}
  annotated=${annotated//[[:space:]]/}
      record_metric "$sample_name" "snpEff" "success" "$duration" "$total" "$annotated" "$out"
    else
      local end_ms=$(current_millis)
      local duration=$((end_ms - start_ms))
      record_metric "$sample_name" "snpEff" "failed" "$duration" 0 0 "$out"
      log "snpeff failed for $vcf_gz"
    fi
  else
    log "snpEff jar not found at /opt/snpEff/snpEff.jar; skipping snpEff."
    record_metric "$sample_name" "snpEff" "skipped_missing_jar" 0 0 0 ""
  fi
}

### Main loop over VCFs from config
log "Reading VCF list from config: $CONFIG_FILE"
python3 -c "
import json
import sys

with open('$CONFIG_FILE') as f:
    config = json.load(f)

for vcf in config['vcf_files']:
    print(f\"{vcf['name']}|{vcf['path']}\")
" | while IFS='|' read -r name path; do
  log "Processing: $name (path=$path)"
  
  if [ ! -f "$path" ]; then
    log "  ERROR: VCF not found: $path"
    continue
  fi
  
  # Create normalized VCF (CHROM only) for bcftools/VEP/SnpEff
  normalized_gz=$(normalize_and_index "$path")
  
  # Run tools:
  # bcftools, VEP, SnpEff use normalized (CHROM-only changed) VCF
  run_bcftools "$name" "$normalized_gz"
  run_vep "$name" "$normalized_gz"
  run_snpeff "$name" "$normalized_gz"
  
  # rsID_retrieval uses ORIGINAL file (handles Ces1p1 offset internally via sandbox equations)
  run_rsid_retrieval "$name" "$path"
  
  log "  ✓ Completed: $name"
done

log "Benchmark finished. Results in $OUTDIR"
