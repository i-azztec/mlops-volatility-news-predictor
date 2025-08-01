"""
Manual test script for the Volatility Prediction Web Service.
Run this after starting the web service to verify all endpoints work correctly.
"""

import requests
import json
from time import sleep

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("1️⃣ Testing Health Check...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_model_info():
    """Test model info endpoint."""
    print("\n2️⃣ Testing Model Info...")
    response = requests.get(f"{API_BASE}/model/info")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

def test_single_prediction():
    """Test single prediction endpoint."""
    print("\n3️⃣ Testing Single Prediction...")
    
    test_cases = [
        {
            "name": "Positive News",
            "headline": "Stock market rallies on strong earnings reports and economic growth"
        },
        {
            "name": "Negative News", 
            "headline": "Market crash fears as inflation reaches new highs"
        },
        {
            "name": "Neutral News",
            "headline": "Federal Reserve maintains current interest rates"
        }
    ]
    
    for case in test_cases:
        print(f"\n  📰 {case['name']}: {case['headline']}")
        response = requests.post(
            f"{API_BASE}/predict",
            json={"headline": case["headline"]}
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"  Probability: {result['prediction_probability']:.4f}")
            print(f"  Class: {result['prediction_class']} ({result['confidence_level']} confidence)")
            print(f"  Processing time: {result['processing_time_ms']:.2f}ms")
        else:
            print(f"  Error: {response.text}")

def test_batch_prediction():
    """Test batch prediction endpoint."""
    print("\n4️⃣ Testing Batch Prediction...")
    
    headlines = [
        "Federal Reserve announces interest rate hike to combat inflation",
        "Tech stocks surge following breakthrough AI announcement", 
        "Oil prices plummet amid global oversupply concerns",
        "Economic recession fears grow as GDP contracts",
        "Corporate earnings exceed expectations across all sectors"
    ]
    
    response = requests.post(f"{API_BASE}/predict/batch", json=headlines)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Headlines processed: {result['headlines_count']}")
        print("Individual predictions:", result['individual_predictions'])
        print("Individual probabilities:", [f"{p:.3f}" for p in result['individual_probabilities']])
        
        agg = result['aggregated_results']
        print(f"\nAggregated Results:")
        print(f"  Mean probability: {agg['mean_probability']:.4f}")
        print(f"  Mean prediction: {agg['mean_prediction']}")
        print(f"  Majority vote: {agg['majority_vote']}")
        print(f"  Max prob class: {agg['max_prob_class']} (prob: {agg['max_prob_value']:.4f})")
    else:
        print(f"Error: {response.text}")

def test_model_reload():
    """Test model reload endpoint."""
    print("\n5️⃣ Testing Model Reload...")
    response = requests.post(f"{API_BASE}/model/reload")
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

def main():
    """Run all tests."""
    print("🧪 Testing Volatility Prediction Web Service")
    print("=" * 50)
    
    # Wait for service to be ready
    print("⏳ Waiting for service to start...")
    for i in range(10):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Service is ready!")
                break
        except requests.exceptions.ConnectionError:
            pass
        sleep(2)
    else:
        print("❌ Service is not responding. Make sure it's running on port 8000.")
        return
    
    # Run tests
    test_health()
    test_model_info()
    test_single_prediction()
    test_batch_prediction()
    test_model_reload()
    
    print("\n✅ All tests completed!")
    print(f"\n🌐 Visit {API_BASE}/docs for interactive API documentation")

if __name__ == "__main__":
    main()
