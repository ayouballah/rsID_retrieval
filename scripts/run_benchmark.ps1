<#
run_benchmark.ps1
PowerShell wrapper to run the WSL benchmark script. Usage (from repo root):
  .\scripts\run_benchmark.ps1

This script invokes the WSL bash script which reads VCF paths and offsets from
scripts/benchmark_config.json. Edit the config to change files or offsets.
#>

$ErrorActionPreference = "Stop"

$repoWin = (Resolve-Path -LiteralPath .).Path
$scriptWsl = '/mnt/c' + (($repoWin -replace '^[A-Za-z]:','') -replace '\\','/') + '/scripts/benchmark_wsl.sh'

Write-Host "=== rsID_retrieval Benchmark Tool ===" -ForegroundColor Cyan
Write-Host "Running WSL benchmark script: $scriptWsl" -ForegroundColor Cyan
Write-Host "VCF files and offsets are read from: scripts/benchmark_config.json" -ForegroundColor Yellow
Write-Host ""

# Run in WSL
wsl bash -lc "cd /mnt/c/Users/ayoub/Documents/GitHub/rsID_retrieval && bash $scriptWsl"

Write-Host ""
Write-Host "Benchmark complete! Check benchmark_results/ for outputs." -ForegroundColor Green
