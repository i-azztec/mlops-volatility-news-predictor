#!/usr/bin/env python3
"""
Local test of MLOps pipeline without Docker
"""

from src.train import create_model_pipeline, prepare_features
import pandas as pd
from sklearn.metrics import accuracy_score

def test_model_training():
    print("🚀 Testing model training...")
    
    # Load small data sample
    train_data = pd.read_parquet('data/processed/train_tall.parquet').head(1000)
    val_data = pd.read_parquet('data/processed/val_tall.parquet').head(500)
    
    print(f"Training data: {train_data.shape}")
    print(f"Validation data: {val_data.shape}")
    
    # Prepare features
    X_train, y_train, numeric_features = prepare_features(train_data)
    X_val, y_val, _ = prepare_features(val_data)
    
    print(f"Features prepared: {X_train.shape}, target variable: {y_train.shape}")
    
    # Create simple model
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
    
    print("✅ Model created, starting training...")
    
    # Train
    model.fit(X_train, y_train)
    print("✅ Model trained!")
    
    # Simple evaluation
    pred = model.predict(X_val)
    acc = accuracy_score(y_val, pred)
    print(f"📊 Validation accuracy: {acc:.3f}")
    
    return model

if __name__ == "__main__":
    model = test_model_training()
    print("🎉 Local test completed successfully!")
