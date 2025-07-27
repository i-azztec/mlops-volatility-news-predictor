#!/usr/bin/env python3
"""
Test scoring flow without dependency on production model
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.predict import predict_daily_batch
from src.train import create_model_pipeline, prepare_features
import pandas as pd

def test_scoring_locally():
    print("🚀 Testing scoring functionality...")
    
    # Load small sample for quick model training
    train_data = pd.read_parquet('data/processed/train_tall.parquet').head(1000)
    test_data = pd.read_parquet('data/processed/test_tall.parquet').head(100)
    
    # Train simple model
    X_train, y_train, _ = prepare_features(train_data)
    model = create_model_pipeline(
        max_features=100,
        ngram_range=(1, 1),
        xgb_params={'eval_metric': 'logloss', 'random_state': 42, 'max_depth': 3, 'n_estimators': 10}
    )
    model.fit(X_train, y_train)
    print("✅ Model trained for testing")
    
    # Test prediction for one day
    test_day = test_data[test_data['Date'] == test_data['Date'].iloc[0]]
    headlines = test_day['Headline'].tolist()
    
    # Create historical features from data
    historical_features = {
        col: test_day[col].iloc[0] 
        for col in test_day.columns 
        if col not in ['Date', 'Headline', 'vol_up']
    }
    
    print(f"📰 Testing with {len(headlines)} headlines")
    
    # Make batch prediction
    result = predict_daily_batch(headlines, model, historical_features)
    
    print("📊 Prediction results:")
    print(f"  - Date: {result['date']}")
    print(f"  - Number of headlines: {result['num_headlines']}")
    print(f"  - Mean probability: {result['prediction_mean_proba']:.3f}")
    print(f"  - Class (mean): {result['prediction_mean_class']}")
    print(f"  - Majority vote: {result['prediction_majority_vote']}")
    print(f"  - Max probability: {result['prediction_max_proba']:.3f}")
    
    # Compare with true label
    true_label = test_day['vol_up'].iloc[0]
    pred_label = result['prediction_mean_class']
    accuracy = "✅ Correct" if pred_label == true_label else "❌ Incorrect"
    print(f"  - True label: {true_label}, Prediction: {pred_label} ({accuracy})")
    
    return result

if __name__ == "__main__":
    result = test_scoring_locally()
    print("🎉 Scoring test completed successfully!")
