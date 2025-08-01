"""
Tests for the FastAPI Web Service.
"""

import pytest
import requests
import json
from time import sleep

# Test configuration
API_BASE_URL = "http://localhost:8000"

class TestWebService:
    """Test cases for the volatility prediction web service."""

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = requests.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert "uptime_seconds" in data

    def test_predict_endpoint(self):
        """Test single headline prediction."""
        # Wait for model to load
        sleep(5)
        
        test_headline = "Federal Reserve announces interest rate hike to combat inflation"
        
        payload = {
            "headline": test_headline
        }
        
        response = requests.post(
            f"{API_BASE_URL}/predict", 
            json=payload
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "headline" in data
        assert "prediction_probability" in data
        assert "prediction_class" in data
        assert "confidence_level" in data
        assert "model_version" in data
        assert "prediction_timestamp" in data
        assert "processing_time_ms" in data
        
        # Validate data types and ranges
        assert isinstance(data["prediction_probability"], float)
        assert 0 <= data["prediction_probability"] <= 1
        assert data["prediction_class"] in [0, 1]
        assert data["confidence_level"] in ["High", "Medium", "Low"]

    def test_batch_predict_endpoint(self):
        """Test batch prediction with multiple headlines."""
        test_headlines = [
            "Stock market rallies on positive earnings reports",
            "Economic recession fears grow amid declining GDP",
            "Tech stocks surge following innovation announcement",
            "Oil prices drop due to oversupply concerns",
            "Federal Reserve signals potential policy changes"
        ]
        
        response = requests.post(
            f"{API_BASE_URL}/predict/batch", 
            json=test_headlines
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "headlines_count" in data
        assert "individual_predictions" in data
        assert "individual_probabilities" in data
        assert "aggregated_results" in data
        assert "model_version" in data
        
        # Validate batch processing
        assert data["headlines_count"] == len(test_headlines)
        assert len(data["individual_predictions"]) == len(test_headlines)
        assert len(data["individual_probabilities"]) == len(test_headlines)
        
        # Validate aggregated results
        agg = data["aggregated_results"]
        assert "mean_probability" in agg
        assert "mean_prediction" in agg
        assert "majority_vote" in agg
        assert "max_prob_class" in agg
        assert "max_prob_value" in agg

    def test_model_info_endpoint(self):
        """Test model information endpoint."""
        response = requests.get(f"{API_BASE_URL}/model/info")
        assert response.status_code == 200
        
        data = response.json()
        if "version" in data:  # Model is loaded
            assert "loaded_at" in data
            assert "model_type" in data
            assert "vectorizer_type" in data

    def test_model_reload_endpoint(self):
        """Test manual model reload."""
        response = requests.post(f"{API_BASE_URL}/model/reload")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "reloaded_at" in data

    def test_invalid_input(self):
        """Test handling of invalid input."""
        # Empty headline
        response = requests.post(
            f"{API_BASE_URL}/predict", 
            json={"headline": ""}
        )
        # Should still work but with empty string
        assert response.status_code in [200, 422]
        
        # Missing headline field
        response = requests.post(
            f"{API_BASE_URL}/predict", 
            json={}
        )
        assert response.status_code == 422

    def test_api_documentation(self):
        """Test that API documentation is accessible."""
        # OpenAPI docs
        response = requests.get(f"{API_BASE_URL}/docs")
        assert response.status_code == 200
        
        # ReDoc
        response = requests.get(f"{API_BASE_URL}/redoc")
        assert response.status_code == 200
        
        # OpenAPI JSON schema
        response = requests.get(f"{API_BASE_URL}/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "info" in schema
        assert "paths" in schema

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
