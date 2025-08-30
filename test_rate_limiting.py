#!/usr/bin/env python3
"""
Test script for rate limiting and bot protection
Run this to verify the implementation works correctly
"""

import requests
import time
import json

# Test configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-key"  # Use the test key from your config

def test_rate_limiting():
    """Test rate limiting functionality"""
    print("🧪 Testing Rate Limiting...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "InstaFit-Test-Client/1.0"
    }
    
    # Test 1: Check rate limit status
    print("\n1. Checking rate limit status...")
    response = requests.get(f"{BASE_URL}/rate-limit/status", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Rate limit info: {json.dumps(data, indent=2)}")
    
    # Test 2: Make multiple requests to trigger rate limiting
    print("\n2. Making multiple requests to test rate limiting...")
    for i in range(5):
        response = requests.get(f"{BASE_URL}/health", headers=headers)
        print(f"Request {i+1}: Status {response.status_code}")
        
        if response.status_code == 429:
            print("✅ Rate limiting triggered successfully!")
            data = response.json()
            print(f"Rate limit response: {json.dumps(data, indent=2)}")
            break
        
        time.sleep(0.1)  # Small delay between requests
    
    # Test 3: Wait and try again
    print("\n3. Waiting 2 seconds and trying again...")
    time.sleep(2)
    response = requests.get(f"{BASE_URL}/health", headers=headers)
    print(f"Status after wait: {response.status_code}")

def test_bot_protection():
    """Test bot protection functionality"""
    print("\n🤖 Testing Bot Protection...")
    
    # Test 1: Request without User-Agent (should be blocked)
    print("\n1. Testing request without User-Agent...")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(f"{BASE_URL}/health", headers=headers)
    print(f"Status without User-Agent: {response.status_code}")
    if response.status_code == 403:
        print("✅ Bot protection working - blocked request without User-Agent")
    
    # Test 2: Request with bot User-Agent (should be blocked)
    print("\n2. Testing request with bot User-Agent...")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "python-requests/2.31.0"
    }
    response = requests.get(f"{BASE_URL}/health", headers=headers)
    print(f"Status with bot User-Agent: {response.status_code}")
    if response.status_code == 403:
        print("✅ Bot protection working - blocked bot User-Agent")
    
    # Test 3: Request with legitimate User-Agent (should work)
    print("\n3. Testing request with legitimate User-Agent...")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(f"{BASE_URL}/health", headers=headers)
    print(f"Status with legitimate User-Agent: {response.status_code}")
    if response.status_code == 200:
        print("✅ Bot protection working - allowed legitimate User-Agent")

def test_api_endpoint():
    """Test the main API endpoint with rate limiting"""
    print("\n🚀 Testing Main API Endpoint...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "User-Agent": "InstaFit-Test-Client/1.0",
        "Content-Type": "application/json"
    }
    
    # Mock data for the API
    test_data = {
        "user_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",  # 1x1 transparent PNG
        "product_image_url": "https://via.placeholder.com/300x400/FF0000/FFFFFF?text=Test+Product",
        "meta": {
            "productTitle": "Test Product",
            "selectedSize": "M",
            "selectedColor": "Red"
        }
    }
    
    print("Making request to /instafit endpoint...")
    response = requests.post(f"{BASE_URL}/instafit", headers=headers, json=test_data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ API endpoint working with rate limiting")
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
    elif response.status_code == 429:
        print("✅ Rate limiting working on API endpoint")
        data = response.json()
        print(f"Rate limit response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ Unexpected status: {response.status_code}")
        print(f"Response: {response.text}")

def main():
    """Run all tests"""
    print("🧪 InstaFit Rate Limiting & Bot Protection Test Suite")
    print("=" * 60)
    
    try:
        # Test bot protection first
        test_bot_protection()
        
        # Test rate limiting
        test_rate_limiting()
        
        # Test main API endpoint
        test_api_endpoint()
        
        print("\n✅ All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running on localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main() 