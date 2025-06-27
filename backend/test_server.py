#!/usr/bin/env python3
"""
Simple test script to verify backend endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health endpoint status: {response.status_code}")
        print(f"Health response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health endpoint error: {e}")
        return False

def test_chat():
    """Test chat endpoint"""
    try:
        payload = {
            "message": "Hello, this is a test message",
            "conversation_id": None
        }
        response = requests.post(f"{BASE_URL}/chat/", json=payload)
        print(f"Chat endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Chat response: {response.json()}")
        else:
            print(f"Chat error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        return False

def test_docs():
    """Test docs endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Docs endpoint status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Docs endpoint error: {e}")
        return False

if __name__ == "__main__":
    print("Testing backend endpoints...")
    print("=" * 50)
    
    print("\n1. Testing docs endpoint...")
    test_docs()
    
    print("\n2. Testing health endpoint...")
    test_health()
    
    print("\n3. Testing chat endpoint...")
    test_chat()
    
    print("\n" + "=" * 50)
    print("Test completed!") 