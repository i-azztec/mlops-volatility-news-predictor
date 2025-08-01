"""
Test script for the volatility prediction API
"""

import requests
import json
import time

API_BASE = "http://localhost:8001"

def test_api():
    """Test the demo API endpoints."""
    
    print("🧪 Testing Volatility Prediction Demo API")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1️⃣ Testing Health Check...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Single Prediction - Positive
    print("\n2️⃣ Testing Single Prediction (Positive News)...")
    try:
        payload = {"headline": "Stock market rallies on strong earnings reports"}
        response = requests.post(f"{API_BASE}/predict", json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Headline: {data['headline']}")
            print(f"Probability: {data['prediction_probability']}")
            print(f"Class: {data['prediction_class']}")
            print(f"Confidence: {data['confidence_level']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Single Prediction - Negative
    print("\n3️⃣ Testing Single Prediction (Negative News)...")
    try:
        payload = {"headline": "Market crash fears as inflation reaches new highs"}
        response = requests.post(f"{API_BASE}/predict", json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Headline: {data['headline']}")
            print(f"Probability: {data['prediction_probability']}")
            print(f"Class: {data['prediction_class']}")
            print(f"Confidence: {data['confidence_level']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Batch Prediction
    print("\n4️⃣ Testing Batch Prediction...")
    try:
        headlines = [
            "Federal Reserve announces interest rate hike",
            "Tech stocks surge following AI breakthrough", 
            "Oil prices plummet amid oversupply concerns"
        ]
        response = requests.post(f"{API_BASE}/predict/batch", json=headlines, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Headlines processed: {data['headlines_count']}")
            print(f"Individual predictions: {data['individual_predictions']}")
            print(f"Mean probability: {data['aggregated_results']['mean_probability']}")
            print(f"Majority vote: {data['aggregated_results']['majority_vote']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Examples endpoint
    print("\n5️⃣ Testing Examples Endpoint...")
    try:
        response = requests.get(f"{API_BASE}/demo/examples", timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Positive examples:", data['positive_examples'][:1])
            print("Negative examples:", data['negative_examples'][:1])
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n✅ API Testing completed!")
    print(f"🌐 Visit {API_BASE}/docs for interactive documentation")

if __name__ == "__main__":
    # Wait for API to start
    print("⏳ Waiting for API to start...")
    time.sleep(3)
    
    test_api()
