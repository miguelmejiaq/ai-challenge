#!/usr/bin/env python3
"""
Test runner script for MiniTel-Lite Emergency Protocol Client.

This script provides various options for running tests with different
configurations and coverage reporting.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\n{description}")
        print("=" * len(description))
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        return False
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="MiniTel-Lite Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--html", action="store_true", help="Generate HTML coverage report")
    parser.add_argument("--fast", action="store_true", help="Run tests without coverage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", "-f", help="Run specific test file")
    parser.add_argument("--test", "-t", help="Run specific test function")
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add verbosity
    if args.verbose:
        cmd.append("-vv")
    
    # Test selection
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    
    # Specific file or test
    if args.file:
        cmd.append(f"tests/{args.file}")
    elif args.test:
        cmd.extend(["-k", args.test])
    
    # Coverage options
    if args.fast:
        # Remove coverage options for fast runs
        cmd.extend(["--no-cov"])
    elif args.coverage or args.html:
        cmd.extend([
            "--cov=src",
            "--cov-report=term-missing"
        ])
        if args.html:
            cmd.extend(["--cov-report=html:htmlcov"])
    
    # Run the tests
    success = run_command(cmd, "Running MiniTel-Lite Tests")
    
    if success:
        print("\n✅ All tests passed!")
        
        if args.html or args.coverage:
            print("\n📊 Coverage report generated:")
            if args.html:
                print("  HTML report: htmlcov/index.html")
            print("  Terminal report shown above")
    else:
        print("\n❌ Some tests failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
