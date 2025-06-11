#!/usr/bin/env python3
"""
Quick test script to verify Gemini API is working
"""

import json

import google.generativeai as genai

# Configure API
GEMINI_API_KEY = "AIzaSyAIl8F81WwFfx5_62y19KuO12ermaDC6FQ"
genai.configure(api_key=GEMINI_API_KEY)

# Test with a simple prompt
model = genai.GenerativeModel('gemini-2.0-flash')

# Test memory content
test_memory = """
Meeting notes from VBE strategy session:
- John Smith (CEO) discussed partnership with Nike
- Sarah Johnson (CTO) proposed using React and Python for the new platform
- Meeting held in Atlanta office
- Budget approved for $50k
- Timeline: Q1 2025 launch
"""

# Simple prompt
prompt = f"""
Extract entities from this text and return as JSON:

{test_memory}

Format:
{{
  "entities": [
    {{"name": "...", "type": "PERSON|ORG|TECH|LOCATION", "importance": 0.0-1.0}}
  ],
  "relationships": [
    {{"source": "...", "target": "...", "type": "...", "strength": 0.0-1.0}}
  ]
}}
"""

print("🧪 Testing Gemini API...")
print(f"📝 Test memory: {test_memory[:50]}...")

try:
    response = model.generate_content(prompt)
    print("\n✅ API Response received!")
    print(f"📊 Response text:\n{response.text}")

    # Try to parse as JSON
    try:
        data = json.loads(response.text)
        print("\n✅ Valid JSON response!")
        print(f"🔍 Entities found: {len(data.get('entities', []))}")
        print(f"🔗 Relationships found: {len(data.get('relationships', []))}")

        print("\nEntities:")
        for entity in data.get('entities', []):
            print(f"  - {entity['name']} ({entity['type']})")

    except json.JSONDecodeError:
        print("⚠️ Response is not valid JSON, but API is working")

except Exception as e:
    print(f"❌ API Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check if API key is valid")
    print("2. Ensure you have API access enabled")
    print("3. Check quota limits")
