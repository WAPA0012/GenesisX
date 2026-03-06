"""Test runner script for Genesis X.

Runs all tests and generates a coverage report.
"""
import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all tests."""
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"

    # Run pytest
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(tests_dir),
            "-v",
            "--tb=short",
            "--cov=.",
            "--cov-report=html",
            "--cov-report=term-missing",
        ],
        cwd=project_root,
    )

    return result.returncode


def run_specific_test(test_file: str):
    """Run a specific test file."""
    project_root = Path(__file__).parent

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
        ],
        cwd=project_root,
    )

    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_file = sys.argv[1]
        exit_code = run_specific_test(test_file)
    else:
        # Run all tests
        exit_code = run_tests()

    sys.exit(exit_code)
