# Optimized Performance Tests

**Test Date:** November 26, 2025  
**Optimization Applied:** 3 workers, batch_size=10, smart rate limiter  
**Expected Speedup:** 1.37x (27% faster)

---

## 📋 Test Plan

### Test Datasets:

1. **GIAB_subset_A** (1,000 variants)
   - Path: `benchmark_speed_results/GIAB_subset_A_output/HG001_subset_A_sandbox_results/HG001_subset_A_annotated.vcf`
   - Characteristics: 99.4% already annotated (6 missing)
   - Expected: Minimal speedup (most variants already have rsIDs)

2. **GIAB_subset_B** (1,000 variants)
   - Path: `benchmark_speed_results/GIAB_subset_B_output/HG001_subset_B_sandbox_results/HG001_subset_B_custom_modified.vcf`
   - Characteristics: 100% missing rsIDs
   - Expected: Full 1.37x speedup (all need annotation)

3. **ClinVar_chr20_subset** (To be determined)
   - Mixed annotation status
   - Real-world scenario

---

## 🎯 Success Criteria

- [ ] Faster runtime than old version
- [ ] Maintains 99%+ annotation accuracy
- [ ] No errors or crashes
- [ ] Progress bar works correctly
- [ ] Output VCF format is correct

---

## 📊 Results

### GIAB_subset_A
- **Runtime**: ___ minutes
- **Annotated**: ___/1000 variants
- **vs Baseline**: ___

### GIAB_subset_B
- **Runtime**: ___ minutes
- **Annotated**: ___/1000 variants
- **vs Baseline**: ___

### ClinVar_chr20_subset
- **Runtime**: ___ minutes
- **Annotated**: ___/___ variants
- **vs Baseline**: ___

---

## 🔬 Test Commands

Will run tests using the optimized `core/entrez_api.py`
