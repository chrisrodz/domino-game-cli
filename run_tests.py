#!/usr/bin/env python3
"""
Test runner script for the domino game CLI.
Runs all tests and reports results.
"""

import sys
import subprocess
from pathlib import Path


def run_test_file(test_file: Path) -> bool:
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {test_file.relative_to(Path.cwd())}")
    print('='*60)

    result = subprocess.run(
        [sys.executable, str(test_file)],
        capture_output=False
    )

    return result.returncode == 0


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DOMINO GAME CLI - TEST SUITE")
    print("="*60)

    # Get all test files
    test_dir = Path(__file__).parent / "tests"
    test_files = sorted(test_dir.rglob("test_*.py"))

    if not test_files:
        print("\n❌ No test files found!")
        return 1

    # Run all tests
    results = {}
    for test_file in test_files:
        # Skip __init__.py files
        if test_file.name == "__init__.py":
            continue

        success = run_test_file(test_file)
        results[test_file.relative_to(test_dir)] = success

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for success in results.values() if success)
    failed = len(results) - passed

    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_file}")

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
    print("="*60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
