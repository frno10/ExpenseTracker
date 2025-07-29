#!/usr/bin/env python3
"""Test runner script for comprehensive testing."""
import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run comprehensive tests for expense tracker")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks")
    parser.add_argument("--all", action="store_true", help="Run all tests and checks")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    success = True
    
    # Build pytest command options
    pytest_opts = []
    if args.verbose:
        pytest_opts.append("-v")
    if args.parallel:
        pytest_opts.append("-n auto")
    if args.fast:
        pytest_opts.append("-m 'not slow'")
    
    pytest_base = f"python -m pytest {' '.join(pytest_opts)}"
    
    # Run specific test categories
    if args.unit or args.all:
        cmd = f"{pytest_base} -m unit tests/unit/"
        if not run_command(cmd, "Unit Tests"):
            success = False
    
    if args.integration or args.all:
        cmd = f"{pytest_base} -m integration tests/integration/"
        if not run_command(cmd, "Integration Tests"):
            success = False
    
    if args.e2e or args.all:
        cmd = f"{pytest_base} -m e2e tests/e2e/"
        if not run_command(cmd, "End-to-End Tests"):
            success = False
    
    if args.performance or args.all:
        cmd = f"{pytest_base} -m performance tests/performance/"
        if not run_command(cmd, "Performance Tests"):
            success = False
    
    # Run all tests if no specific category selected
    if not any([args.unit, args.integration, args.e2e, args.performance, args.all]):
        cmd = f"{pytest_base} tests/"
        if not run_command(cmd, "All Tests"):
            success = False
    
    # Generate coverage report
    if args.coverage or args.all:
        cmd = "python -m pytest --cov=app --cov-report=html --cov-report=xml --cov-report=term-missing tests/"
        if not run_command(cmd, "Coverage Report"):
            success = False
        
        print("\n📊 Coverage report generated:")
        print("  - HTML: htmlcov/index.html")
        print("  - XML: coverage.xml")
    
    # Run code quality checks
    if args.quality or args.all:
        quality_commands = [
            ("python -m flake8 app/ tests/", "Flake8 Linting"),
            ("python -m black --check app/ tests/", "Black Code Formatting Check"),
            ("python -m isort --check-only app/ tests/", "Import Sorting Check"),
            ("python -m mypy app/", "Type Checking"),
            ("python -m bandit -r app/", "Security Analysis"),
        ]
        
        for cmd, desc in quality_commands:
            if not run_command(cmd, desc):
                success = False
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests and checks completed successfully!")
        sys.exit(0)
    else:
        print("❌ Some tests or checks failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()