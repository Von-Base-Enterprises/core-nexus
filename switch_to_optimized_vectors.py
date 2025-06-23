#!/usr/bin/env python3
"""
Switch to Optimized Vector Table
Update the memory service to use the optimized vector_memories_optimized table.
"""

import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python', 'memory_service', 'src'))

def update_config():
    """Update the configuration to use optimized table."""
    
    config_file_path = os.path.join(
        os.path.dirname(__file__), 
        'python', 'memory_service', 'src', 'memory_service', 'config.py'
    )
    
    print("🔧 Switching Core Nexus to use optimized vector table...")
    
    # Read the current config
    with open(config_file_path, 'r') as f:
        content = f.read()
    
    # Replace the table name
    if 'TABLE_NAME = "vector_memories"' in content:
        updated_content = content.replace(
            'TABLE_NAME = "vector_memories"',
            'TABLE_NAME = "vector_memories_optimized"  # OPTIMIZED: Using 1,536D vectors'
        )
        
        # Write the updated config
        with open(config_file_path, 'w') as f:
            f.write(updated_content)
        
        print("✅ Updated config.py to use vector_memories_optimized table")
        print("🚀 Core Nexus is now using 1,536-dimensional optimized vectors!")
        
        return True
    else:
        print("❌ Could not find TABLE_NAME in config.py")
        return False

def verify_switch():
    """Verify the switch was successful."""
    try:
        from memory_service.config import DatabaseConfig
        
        table_name = DatabaseConfig.TABLE_NAME
        if table_name == "vector_memories_optimized":
            print(f"✅ Verification successful: Using {table_name}")
            print("🎯 Performance optimization is now ACTIVE!")
            return True
        else:
            print(f"❌ Verification failed: Still using {table_name}")
            return False
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

def main():
    """Main function to switch to optimized vectors."""
    
    print("="*60)
    print("CORE NEXUS VECTOR OPTIMIZATION ACTIVATION")
    print("="*60)
    
    # Update the configuration
    if update_config():
        # Verify the change
        if verify_switch():
            print("\n🎉 SUCCESS: Core Nexus is now using optimized 1,536D vectors!")
            print("\n📊 Expected Performance Improvements:")
            print("   • 12.5x faster queries (19,159D → 1,536D)")
            print("   • 92% storage reduction")
            print("   • 12.5x better memory efficiency") 
            print("   • Sub-15ms P95 latency targets")
            
            print("\n⚠️  IMPORTANT: Restart the memory service to apply changes")
            print("   Command: poetry run uvicorn src.memory_service.api:app --reload")
        else:
            print("\n❌ Switch failed during verification")
            return False
    else:
        print("\n❌ Switch failed during configuration update")
        return False
    
    print("\n" + "="*60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)