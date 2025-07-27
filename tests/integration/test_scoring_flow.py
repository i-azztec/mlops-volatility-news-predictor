"""
Integration tests for scoring flow with LocalStack.
"""

import pytest
import pandas as pd
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils import get_s3_client, ensure_bucket_exists, save_parquet_to_s3
from src.predict import predict_one, predict_daily_batch
from src.train import create_model_pipeline


@pytest.fixture
def s3_setup():
    """Setup LocalStack S3 for testing."""
    # Ensure LocalStack is running and bucket exists
    bucket_name = "test-volatility-data"
    
    try:
        ensure_bucket_exists(bucket_name)
        yield bucket_name
    except Exception as e:
        pytest.skip(f"LocalStack not available: {e}")


@pytest.fixture
def sample_test_data():
    """Create sample test data for integration testing."""
    data = pd.DataFrame({
        'Date': ['2023-01-01'] * 3,
        'Headline': [
            'Stock market volatility expected to rise',
            'Economic uncertainty drives market fears',
            'Fed policy announcement tomorrow'
        ],
        'vol_up': [1, 1, 0],
        'realized_vol_lag_1': [15.2, 15.2, 15.2],
        'realized_vol_lag_2': [14.8, 14.8, 14.8],
        'tr_vol_lag_1': [12.5, 12.5, 12.5],
        'park_vol_lag_1': [16.1, 16.1, 16.1],
        'realized_vol_ma_5': [15.0, 15.0, 15.0],
        'dow_0': [1, 1, 1],  # Monday
        'month_1': [1, 1, 1],  # January
        'quarter_1': [1, 1, 1]  # Q1
    })
    
    # Add all required feature columns with zeros
    feature_template = {
        'realized_vol_lag_3': 14.5, 'realized_vol_lag_5': 14.0, 'realized_vol_lag_10': 13.8,
        'tr_vol_lag_2': 12.3, 'tr_vol_lag_3': 12.1, 'tr_vol_lag_5': 11.8, 'tr_vol_lag_10': 11.5,
        'park_vol_lag_2': 15.8, 'park_vol_lag_3': 15.5, 'park_vol_lag_5': 15.2, 'park_vol_lag_10': 14.9,
        'realized_vol_ma_10': 14.8, 'realized_vol_ma_20': 14.5,
        'tr_vol_ma_5': 12.0, 'tr_vol_ma_10': 11.8, 'tr_vol_ma_20': 11.5,
        'park_vol_ma_5': 15.8, 'park_vol_ma_10': 15.5, 'park_vol_ma_20': 15.2
    }
    
    # Add calendar features
    for i in range(7):
        if i != 0:  # Monday is already set
            feature_template[f'dow_{i}'] = 0
    for i in range(1, 13):
        if i != 1:  # January is already set
            feature_template[f'month_{i}'] = 0
    for i in range(1, 5):
        if i != 1:  # Q1 is already set
            feature_template[f'quarter_{i}'] = 0
    
    # Add missing features to data
    for col, value in feature_template.items():
        if col not in data.columns:
            data[col] = value
    
    return data


@pytest.fixture
def simple_model():
    """Create a simple trained model for testing."""
    # Create a simple model pipeline
    model = create_model_pipeline(
        max_features=100,
        ngram_range=(1, 1),
        xgb_params={
            'eval_metric': 'logloss',
            'random_state': 42,
            'max_depth': 3,
            'n_estimators': 10
        }
    )
    
    return model


def test_predict_one_function(simple_model, sample_test_data):
    """Test the predict_one function with sample data."""
    # Use first row for training to fit the model
    X_train = sample_test_data.drop('vol_up', axis=1)
    y_train = sample_test_data['vol_up']
    
    # Fit the model
    simple_model.fit(X_train, y_train)
    
    # Test prediction
    headline = "Market volatility expected to increase"
    historical_features = {
        col: sample_test_data[col].iloc[0] 
        for col in sample_test_data.columns 
        if col not in ['Date', 'Headline', 'vol_up']
    }
    
    result = predict_one(headline, simple_model, None, historical_features)
    
    # Check result structure
    assert 'headline' in result
    assert 'prediction_class' in result
    assert 'prediction_proba' in result
    assert 'confidence' in result
    assert 'interpretation' in result
    
    # Check value ranges
    assert result['prediction_class'] in [0, 1]
    assert 0 <= result['prediction_proba'] <= 1
    assert 0 <= result['confidence'] <= 1


def test_predict_daily_batch(simple_model, sample_test_data):
    """Test the predict_daily_batch function."""
    # Fit the model
    X_train = sample_test_data.drop('vol_up', axis=1)
    y_train = sample_test_data['vol_up']
    simple_model.fit(X_train, y_train)
    
    # Test batch prediction
    headlines = sample_test_data['Headline'].tolist()
    historical_features = {
        col: sample_test_data[col].iloc[0] 
        for col in sample_test_data.columns 
        if col not in ['Date', 'Headline', 'vol_up']
    }
    
    result = predict_daily_batch(headlines, simple_model, historical_features)
    
    # Check result structure
    assert 'date' in result
    assert 'num_headlines' in result
    assert 'prediction_mean_proba' in result
    assert 'prediction_mean_class' in result
    assert 'prediction_majority_vote' in result
    assert 'prediction_max_proba' in result
    assert 'prediction_max_class' in result
    assert 'individual_predictions' in result
    
    # Check values
    assert result['num_headlines'] == len(headlines)
    assert 0 <= result['prediction_mean_proba'] <= 1
    assert result['prediction_mean_class'] in [0, 1]
    assert result['prediction_majority_vote'] in [0, 1]
    assert len(result['individual_predictions']) == len(headlines)


def test_s3_data_upload_download(s3_setup, sample_test_data):
    """Test uploading and downloading data to/from S3."""
    bucket_name = s3_setup
    
    # Upload test data
    s3_key = "test/sample_data.parquet"
    save_parquet_to_s3(sample_test_data, bucket_name, s3_key)
    
    # Download and verify
    from src.utils import read_parquet_from_s3
    downloaded_data = read_parquet_from_s3(bucket_name, s3_key)
    
    # Check that data is preserved
    assert downloaded_data.shape == sample_test_data.shape
    assert list(downloaded_data.columns) == list(sample_test_data.columns)
    
    # Check a few values
    assert downloaded_data['Headline'].iloc[0] == sample_test_data['Headline'].iloc[0]
    assert downloaded_data['vol_up'].iloc[0] == sample_test_data['vol_up'].iloc[0]


def test_empty_headlines_handling(simple_model):
    """Test handling of empty headlines list."""
    result = predict_daily_batch([], simple_model)
    
    assert result['num_headlines'] == 0
    assert result['prediction_mean_proba'] == 0.5
    assert 'error' in result


def test_invalid_headline_handling(simple_model):
    """Test handling of invalid/empty headlines."""
    historical_features = {f'feature_{i}': 0.0 for i in range(10)}
    
    # Test with empty string
    result = predict_one("", simple_model, None, historical_features)
    assert 'headline' in result
    
    # Test with None (should be handled gracefully)
    result = predict_one("Valid headline", simple_model, None, historical_features)
    assert result['headline'] == "Valid headline"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
