#!/usr/bin/env python3
"""
Docker Test Script for rsID Retrieval

This script tests the Docker build and basic functionality.
Run this AFTER building the Docker image with: docker build -t rsid-retrieval .
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✓ SUCCESS: {description}")
            return True
        else:
            print(f"✗ FAILED: {description} (Exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {description} - {str(e)}")
        return False

def main():
    """Run Docker tests."""
    print("=" * 60)
    print("Docker Build and Test Suite for rsID Retrieval")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Build Docker image
    if run_command(
        ["docker", "build", "-t", "rsid-retrieval", "."],
        "Build Docker image"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
        print("\n✗ Docker build failed. Cannot continue with other tests.")
        sys.exit(1)
    
    # Test 2: Run unit tests inside container
    if run_command(
        ["docker", "run", "--rm", "--entrypoint", "python", 
         "rsid-retrieval", "/app/run_tests.py"],
        "Run unit tests inside container"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 3: Regular CLI help
    if run_command(
        ["docker", "run", "--rm", "rsid-retrieval", "--help"],
        "Regular mode CLI help"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 4: Sandbox CLI help
    if run_command(
        ["docker", "run", "--rm", "--entrypoint", "python",
         "rsid-retrieval", "/app/sandbox_cli.py", "--help"],
        "Sandbox mode CLI help"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 5: Test equation validation
    if run_command(
        ["docker", "run", "--rm", "--entrypoint", "python",
         "rsid-retrieval", "/app/sandbox_cli.py",
         "--test-equation", "--equation", "x + 55758218"],
        "Equation validation test"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 6: Check Python version
    if run_command(
        ["docker", "run", "--rm", "--entrypoint", "python",
         "rsid-retrieval", "--version"],
        "Python version check"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 7: Check installed packages
    if run_command(
        ["docker", "run", "--rm", "--entrypoint", "pip",
         "rsid-retrieval", "list"],
        "List installed packages"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 8: Verify core modules are accessible
    if run_command(
        ["docker", "run", "--rm", "--entrypoint", "python",
         "rsid-retrieval", "-c",
         "import core.vcf_processor, core.entrez_api, core.sandbox; print('All modules imported successfully')"],
        "Core modules import test"
    ):
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Final summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print(f"Total Tests:  {tests_passed + tests_failed}")
    print("=" * 60)
    
    if tests_failed == 0:
        print("\n✓ ALL TESTS PASSED! Docker image is ready to use.")
        print("\nNext steps:")
        print("1. Test with a real VCF file using volume mounting")
        print("2. Push to Docker Hub: docker tag rsid-retrieval your-username/rsid-retrieval")
        print("3. Refer to DOCKER_GUIDE.md for usage examples")
        return 0
    else:
        print(f"\n✗ {tests_failed} TEST(S) FAILED. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
