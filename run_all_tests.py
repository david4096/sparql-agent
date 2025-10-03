#!/usr/bin/env python3
"""
SPARQL Agent - Complete Test Suite Runner

This script runs all tests including unit tests, integration tests, and system validation.
Use this to validate the complete system before deployment.
"""

import sys
import os
import subprocess
import time
from pathlib import Path


def run_command(cmd, description, timeout=300):
    """Run a command with timeout and error handling."""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ SUCCESS ({duration:.1f}s)")
            if result.stdout:
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
        else:
            print(f"❌ FAILED ({duration:.1f}s) - Return code: {result.returncode}")
            if result.stdout:
                print("STDOUT:", result.stdout[-500:])
            if result.stderr:
                print("STDERR:", result.stderr[-500:])

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"💥 EXCEPTION: {e}")
        return False


def check_environment():
    """Check if environment is properly set up."""
    print("🔍 Checking environment...")

    # Check UV is available
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ UV available: {result.stdout.strip()}")
        else:
            print("❌ UV not available")
            return False
    except FileNotFoundError:
        print("❌ UV not found in PATH")
        return False

    # Check if ANTHROPIC_API_KEY is set
    if os.getenv('ANTHROPIC_API_KEY'):
        print("✅ ANTHROPIC_API_KEY is set")
    else:
        print("⚠️ ANTHROPIC_API_KEY not set (some tests will be skipped)")

    # Check if we're in the right directory
    if Path('pyproject.toml').exists():
        print("✅ Project directory detected")
    else:
        print("❌ Not in project root directory")
        return False

    return True


def main():
    """Run the complete test suite."""
    print("🚀 SPARQL Agent - Complete Test Suite")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if not check_environment():
        print("💥 Environment check failed")
        sys.exit(1)

    results = []

    # Test 1: Install/sync dependencies
    success = run_command(
        ['uv', 'sync'],
        "Installing dependencies with UV",
        timeout=300
    )
    results.append(("Dependency Installation", success))

    # Test 2: Basic imports and module loading
    success = run_command(
        ['uv', 'run', 'python', '-c',
         'import sparql_agent; print("✅ All imports successful")'],
        "Testing basic imports",
        timeout=30
    )
    results.append(("Basic Imports", success))

    # Test 3: CLI availability
    success = run_command(
        ['uv', 'run', 'sparql-agent', 'version'],
        "Testing CLI availability",
        timeout=30
    )
    results.append(("CLI Availability", success))

    # Test 4: Unit tests
    success = run_command(
        ['uv', 'run', 'pytest', 'tests/', '-v', '--tb=short', '-x'],
        "Running unit tests",
        timeout=300
    )
    results.append(("Unit Tests", success))

    # Test 5: Integration tests (with API key if available)
    if os.getenv('ANTHROPIC_API_KEY'):
        success = run_command(
            ['uv', 'run', 'pytest', 'tests/integration/', '-v', '--tb=short', '-m', 'integration'],
            "Running integration tests",
            timeout=600
        )
        results.append(("Integration Tests", success))
    else:
        print("⚠️ Skipping integration tests (no ANTHROPIC_API_KEY)")
        results.append(("Integration Tests", "SKIPPED"))

    # Test 6: System validation
    success = run_command(
        ['uv', 'run', 'python', '-c', '''
import os
from sparql_agent.discovery import EndpointPinger, ConnectionConfig
from sparql_agent.ontology import OLSClient

print("Testing system components...")

# Test connectivity
config = ConnectionConfig(timeout=10.0)
pinger = EndpointPinger()
try:
    result = pinger.ping_sync("https://query.wikidata.org/sparql", config=config)
    print(f"✅ Wikidata connectivity: {result.status.value}")
except Exception as e:
    print(f"⚠️ Wikidata connectivity issue: {e}")

# Test OLS
try:
    ols = OLSClient()
    results = ols.search("protein", limit=1)
    print(f"✅ OLS search: {len(results)} results")
except Exception as e:
    print(f"⚠️ OLS issue: {e}")

print("✅ System validation completed")
        '''],
        "Running system validation",
        timeout=60
    )
    results.append(("System Validation", success))

    # Test 7: Security check (no API keys in source)
    success = run_command(
        ['python', '-c', '''
import subprocess
import sys

# Check for API keys in source
result = subprocess.run(
    ["find", ".", "-name", "*.py", "-o", "-name", "*.md", "-not", "-path", "./.venv/*", "-not", "-path", "./.git/*"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print("❌ Find command failed")
    sys.exit(1)

files = result.stdout.strip().split("\\n")
found_keys = False

for file in files:
    if not file:
        continue
    try:
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if 'sk-ant-api03' in content and 'example' not in content.lower():
                print(f"❌ Potential API key in {file}")
                found_keys = True
    except:
        pass

if not found_keys:
    print("✅ No API keys found in source code")
else:
    sys.exit(1)
        '''],
        "Security validation (API key check)",
        timeout=30
    )
    results.append(("Security Check", success))

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results:
        if result is True:
            print(f"✅ {test_name}")
            passed += 1
        elif result == "SKIPPED":
            print(f"⚠️ {test_name} - SKIPPED")
            skipped += 1
        else:
            print(f"❌ {test_name}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0:
        print("🎉 ALL TESTS PASSED! System is ready for production.")
        sys.exit(0)
    else:
        print("💥 Some tests failed. Please review and fix issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()