#!/usr/bin/env python3
"""
Build verification script to ensure environment variables are accessible.
This runs during build to verify the environment is set up correctly.
"""

import os
import sys
import json
from datetime import datetime

def verify_build():
    """Verify build environment and create verification file."""
    
    print("=" * 60)
    print("Build Verification Script")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Check Python version
    print(f"\nPython Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    
    # Check if we can import critical packages
    packages_to_check = ['dotenv', 'fastapi', 'uvicorn', 'google.generativeai']
    
    print("\nPackage Import Check:")
    for package in packages_to_check:
        try:
            if package == 'dotenv':
                import dotenv
                print(f"✅ {package} - Version: {dotenv.__version__}")
            elif package == 'google.generativeai':
                import google.generativeai as genai
                print(f"✅ {package} - Installed")
            else:
                __import__(package)
                print(f"✅ {package} - Installed")
        except ImportError as e:
            print(f"❌ {package} - Not installed: {e}")
    
    # Check environment variables (at build time)
    print("\nEnvironment Variables at Build Time:")
    env_vars_to_check = [
        'RENDER', 'RENDER_SERVICE_NAME', 'RENDER_GIT_COMMIT',
        'PORT', 'PYTHON_VERSION', 'NODE_VERSION'
    ]
    
    for var in env_vars_to_check:
        value = os.environ.get(var, 'NOT_SET')
        if value != 'NOT_SET':
            print(f"  {var}: {value[:50]}...")  # Truncate long values
        else:
            print(f"  {var}: NOT_SET")
    
    # Count total environment variables
    print(f"\nTotal environment variables: {len(os.environ)}")
    
    # Create verification file
    verification_data = {
        'build_timestamp': datetime.now().isoformat(),
        'python_version': sys.version,
        'platform': sys.platform,
        'env_var_count': len(os.environ),
        'render_detected': 'RENDER' in os.environ,
        'packages': {
            'dotenv': 'dotenv' in sys.modules or can_import('dotenv'),
            'fastapi': can_import('fastapi'),
            'google_adk': can_import('google.adk')
        }
    }
    
    # Write verification file
    with open('build_verification.json', 'w') as f:
        json.dump(verification_data, f, indent=2)
    
    print("\n✅ Build verification complete!")
    print("Created build_verification.json")

def can_import(module_name):
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

if __name__ == "__main__":
    verify_build()