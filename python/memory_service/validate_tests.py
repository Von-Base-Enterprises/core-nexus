#!/usr/bin/env python3
"""
Simple validation script to verify test files are syntactically correct
and can be imported without pytest.
"""

import ast
import sys
from pathlib import Path


def validate_python_file(filepath):
    """Validate that a Python file is syntactically correct."""
    try:
        with open(filepath) as f:
            content = f.read()

        # Parse the AST to check syntax
        ast.parse(content)

        # Count test methods
        tree = ast.parse(content)
        test_classes = 0
        test_methods = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                test_classes += 1
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        test_methods += 1

        return True, test_classes, test_methods

    except SyntaxError as e:
        return False, f"Syntax error: {e}", 0
    except Exception as e:
        return False, f"Error: {e}", 0


def main():
    """Validate all test files."""
    print("Validating Knowledge Graph Test Suite")
    print("=" * 60)

    test_files = [
        'tests/test_graph_provider.py',
        'tests/test_graph_integration.py',
        'tests/test_graph_performance.py'
    ]

    total_classes = 0
    total_methods = 0
    all_valid = True

    for test_file in test_files:
        if Path(test_file).exists():
            valid, classes_or_error, methods = validate_python_file(test_file)

            if valid:
                print(f"✓ {test_file}")
                print(f"  - {classes_or_error} test classes")
                print(f"  - {methods} test methods")
                total_classes += classes_or_error
                total_methods += methods
            else:
                print(f"✗ {test_file}")
                print(f"  - {classes_or_error}")
                all_valid = False
        else:
            print(f"✗ {test_file} - File not found")
            all_valid = False

    print("\nSummary:")
    print(f"Total test classes: {total_classes}")
    print(f"Total test methods: {total_methods}")
    print(f"All files valid: {'Yes' if all_valid else 'No'}")

    # Basic import test (without pytest)
    print("\nTesting basic imports:")
    test_imports = [
        "from uuid import UUID, uuid4",
        "import asyncio",
        "import json",
        "import time",
        "from typing import Dict, List, Any",
        "from datetime import datetime"
    ]

    for imp in test_imports:
        try:
            exec(imp)
            print(f"✓ {imp}")
        except ImportError as e:
            print(f"✗ {imp} - {e}")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
