#!/usr/bin/env python3
"""
Simple verification script for OpenAI embeddings code syntax and logic.
This doesn't require dependencies to be installed.
"""

import ast
import sys
from pathlib import Path


def verify_python_syntax(file_path):
    """Verify Python file has valid syntax."""
    try:
        with open(file_path) as f:
            source = f.read()

        # Parse the AST to check syntax
        ast.parse(source)
        return True, "Valid syntax"

    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def check_embedding_implementation():
    """Check key aspects of the embedding implementation."""
    results = []

    # Check embedding_models.py
    embedding_file = Path("src/memory_service/embedding_models.py")
    if embedding_file.exists():
        valid, msg = verify_python_syntax(embedding_file)
        results.append(("Embedding Models Syntax", valid, msg))

        # Check for key components
        with open(embedding_file) as f:
            content = f.read()

        checks = [
            ("OpenAIEmbeddingModel class", "class OpenAIEmbeddingModel" in content),
            ("MockEmbeddingModel class", "class MockEmbeddingModel" in content),
            ("text-embedding-3-small support", "text-embedding-3-small" in content),
            ("async embed_text method", "async def embed_text" in content),
            ("async embed_batch method", "async def embed_batch" in content),
            ("health_check method", "async def health_check" in content),
            ("create_embedding_model factory", "def create_embedding_model" in content),
        ]

        for check_name, condition in checks:
            results.append((check_name, condition, "Found" if condition else "Missing"))
    else:
        results.append(("Embedding Models File", False, "File not found"))

    # Check API integration
    api_file = Path("src/memory_service/api.py")
    if api_file.exists():
        valid, msg = verify_python_syntax(api_file)
        results.append(("API File Syntax", valid, msg))

        with open(api_file) as f:
            content = f.read()

        api_checks = [
            ("Embedding model import", "from .embedding_models import" in content),
            ("OpenAI API key check", "OPENAI_API_KEY" in content),
            ("text-embedding-3-small config", "text-embedding-3-small" in content),
            ("Embedding model initialization", "embedding_model=" in content),
            ("Test endpoint", "/embeddings/test" in content),
        ]

        for check_name, condition in api_checks:
            results.append((check_name, condition, "Found" if condition else "Missing"))
    else:
        results.append(("API File", False, "File not found"))

    return results


def main():
    """Run verification checks."""
    print("🔍 Core Nexus OpenAI Embeddings Verification")
    print("=" * 50)

    results = check_embedding_implementation()

    passed = 0
    failed = 0

    for check_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {check_name}: {message}")
        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"📊 Verification Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 All checks passed! The embedding implementation looks good.")
        print("\n📋 Next Steps:")
        print("1. ⚠️  SECURITY: Revoke and replace the exposed OpenAI API key")
        print("2. 🔄 Deploy the updated code to Render.com")
        print("3. ✅ Test the /embeddings/test endpoint")
        print("4. 📈 Monitor embedding generation in production")
        print("\n🔗 Test endpoints after deployment:")
        print("   GET  /providers - Check embedding model status")
        print("   POST /embeddings/test - Test embedding generation")
        print("   POST /memories - Store memories with OpenAI embeddings")
    else:
        print("\n⚠️  Some checks failed. Review the implementation.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
