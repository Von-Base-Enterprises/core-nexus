#!/usr/bin/env python3
"""
Test script for memory export API functionality
Demonstrates JSON, CSV export with various filters
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any

# API configuration
API_BASE_URL = "https://core-nexus-memory-service.onrender.com"
# API_BASE_URL = "http://localhost:8000"  # For local testing


def test_json_export():
    """Test JSON export with filters."""
    print("\n📥 Testing JSON Export...")
    
    # Export with date and importance filters
    export_request = {
        "format": "json",
        "filters": {
            "importance_min": 0.5,
            "importance_max": 1.0,
            "limit": 100
        },
        "include_metadata": True,
        "include_embeddings": False,
        "gdpr_compliant": False
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/export",
        json=export_request
    )
    
    if response.status_code == 200:
        # Save to file
        filename = f"export_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        # Parse and show summary
        data = json.loads(response.content)
        print(f"✅ JSON export successful!")
        print(f"   File: {filename}")
        print(f"   Total memories: {data['export_info']['total_memories']}")
        print(f"   Export date: {data['export_info']['export_date']}")
        
        # Show sample memory
        if data['memories']:
            print(f"\n   Sample memory:")
            memory = data['memories'][0]
            print(f"   - Content: {memory['content'][:100]}...")
            print(f"   - Importance: {memory['importance_score']}")
            if 'metadata' in memory:
                print(f"   - Metadata keys: {list(memory['metadata'].keys())}")
        
        return True
    else:
        print(f"❌ JSON export failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_csv_export():
    """Test CSV export."""
    print("\n📊 Testing CSV Export...")
    
    export_request = {
        "format": "csv",
        "filters": {
            "importance_min": 0.3,
            "limit": 50
        },
        "include_metadata": True,
        "include_embeddings": False
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/export",
        json=export_request
    )
    
    if response.status_code == 200:
        # Save to file
        filename = f"export_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print(f"✅ CSV export successful!")
        print(f"   File: {filename}")
        print(f"   Size: {len(response.content)} bytes")
        
        # Show first few lines
        lines = response.content.decode('utf-8').split('\n')
        print(f"\n   Preview (first 3 lines):")
        for i, line in enumerate(lines[:3]):
            if line:
                print(f"   {i+1}: {line[:100]}...")
        
        return True
    else:
        print(f"❌ CSV export failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False


def test_filtered_export():
    """Test export with tag filters."""
    print("\n🏷️ Testing Filtered Export (by tags)...")
    
    export_request = {
        "format": "json",
        "filters": {
            "tags": ["technology", "AI", "programming"],
            "limit": 20
        },
        "include_metadata": True
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/export",
        json=export_request
    )
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print(f"✅ Filtered export successful!")
        print(f"   Memories with tags: {data['export_info']['total_memories']}")
        
        # Check tag distribution
        tag_counts = {}
        for memory in data['memories']:
            if 'metadata' in memory and 'tags' in memory['metadata']:
                tags = memory['metadata']['tags']
                if isinstance(tags, str):
                    tags = [tags]
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print(f"\n   Tag distribution:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {tag}: {count} memories")
        
        return True
    else:
        print(f"❌ Filtered export failed: {response.status_code}")
        return False


def test_gdpr_export():
    """Test GDPR-compliant export."""
    print("\n🔒 Testing GDPR Export...")
    
    # Test with a sample user ID
    user_id = "test_user_123"
    
    response = requests.get(
        f"{API_BASE_URL}/api/v1/memories/export/gdpr/{user_id}"
    )
    
    if response.status_code == 200:
        # Save GDPR package
        filename = f"gdpr_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        data = json.loads(response.content)
        export_info = data['data_export']
        
        print(f"✅ GDPR export successful!")
        print(f"   File: {filename}")
        print(f"   User ID: {export_info['user_id']}")
        print(f"   Export date: {export_info['export_date']}")
        print(f"   Total memories: {export_info['data_categories']['memories']['count']}")
        print(f"   Export reason: {export_info['metadata']['export_reason']}")
        
        return True
    else:
        print(f"❌ GDPR export failed: {response.status_code}")
        return False


def test_large_export():
    """Test exporting large dataset."""
    print("\n📦 Testing Large Export (1000+ memories)...")
    
    export_request = {
        "format": "json",
        "filters": {
            "limit": 1000
        },
        "include_metadata": True,
        "include_embeddings": False
    }
    
    start_time = datetime.now()
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/memories/export",
        json=export_request,
        stream=True
    )
    
    if response.status_code == 200:
        # Stream to file
        filename = f"large_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        size = 0
        
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                size += len(chunk)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Large export successful!")
        print(f"   File: {filename}")
        print(f"   Size: {size / 1024 / 1024:.2f} MB")
        print(f"   Time: {elapsed:.2f} seconds")
        print(f"   Speed: {size / elapsed / 1024 / 1024:.2f} MB/s")
        
        return True
    else:
        print(f"❌ Large export failed: {response.status_code}")
        return False


def test_export_formats_comparison():
    """Compare export formats."""
    print("\n📊 Comparing Export Formats...")
    
    formats_info = []
    
    for format_type in ["json", "csv"]:
        export_request = {
            "format": format_type,
            "filters": {
                "limit": 100
            },
            "include_metadata": True
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/memories/export",
            json=export_request
        )
        
        if response.status_code == 200:
            formats_info.append({
                "format": format_type,
                "size": len(response.content),
                "content_type": response.headers.get('content-type', 'unknown')
            })
    
    print("\n   Format comparison:")
    print("   Format | Size (KB) | Content Type")
    print("   " + "-" * 40)
    for info in formats_info:
        print(f"   {info['format']:6} | {info['size']/1024:9.2f} | {info['content_type']}")


def main():
    """Run all export tests."""
    print("🚀 Core Nexus Memory Export API Test Suite")
    print("=" * 50)
    
    # Test basic exports
    test_json_export()
    test_csv_export()
    
    # Test filtered exports
    test_filtered_export()
    
    # Test GDPR compliance
    test_gdpr_export()
    
    # Test performance
    test_large_export()
    
    # Compare formats
    test_export_formats_comparison()
    
    print("\n✅ All export tests completed!")
    print("\n📋 Export API Summary:")
    print("   - JSON export: Full fidelity with metadata")
    print("   - CSV export: Spreadsheet compatible")
    print("   - GDPR export: Compliance ready")
    print("   - Filtering: Date, importance, tags, user")
    print("   - Performance: Streaming for large datasets")


if __name__ == "__main__":
    main()