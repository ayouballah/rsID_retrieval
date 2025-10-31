# Test Suite for rsID Retrieval

This directory contains smoke tests and integration tests for the rsID Retrieval tool.

## Test Structure

```
tests/
├── test_core.py           # Main test suite
├── fixtures/              # Test data files
│   └── test_sample.vcf   # Sample VCF for testing
└── README.md             # This file
```

## Running Tests

### Run All Tests

From the project root directory:

```bash
python run_tests.py
```

Or directly:

```bash
python -m pytest tests/
```

Or using unittest:

```bash
python -m unittest discover tests
```

### Run Specific Test Class

```bash
python -m unittest tests.test_core.TestVCFValidation
```

### Run Specific Test Method

```bash
python -m unittest tests.test_core.TestVCFValidation.test_valid_vcf_file
```

## Test Coverage

### VCF Validation Tests (`TestVCFValidation`)
- Valid VCF file validation
- Nonexistent file handling
- Invalid file extension detection
- Empty file detection

### Sandbox Processor Tests (`TestSandboxProcessor`)
- Equation validation (simple, complex, invalid)
- Empty equation handling
- Wrong variable detection
- Negative result detection
- Chromosome format conversion (RefSeq, UCSC, Ensembl, numeric)
- Sex chromosome formatting

### Integration Tests (`TestIntegration`)
- Basic VCF modification workflow
- Format conversion during modification
- Invalid VCF rejection
- Invalid equation rejection

## Test Philosophy

These are **smoke tests** designed to:
1. Verify core functionality works before code reorganization
2. Catch regressions during cleanup
3. Provide confidence when refactoring
4. Serve as safety net for future development

They do **NOT** test:
- NCBI Entrez API calls (would require network and rate limiting)
- GUI functionality (requires Qt testing framework)
- Complete pipeline runs (too slow for smoke tests)

## Adding New Tests

When adding new tests:
1. Follow the existing structure
2. Use descriptive test names: `test_what_is_being_tested`
3. Include docstrings explaining the test purpose
4. Add test fixtures to `fixtures/` directory
5. Clean up temporary files in `tearDown()`

## Test Requirements

All tests use standard library modules:
- `unittest` - Test framework
- `tempfile` - Temporary file creation
- `os`, `sys` - File system operations

No additional dependencies required beyond the main application requirements.
