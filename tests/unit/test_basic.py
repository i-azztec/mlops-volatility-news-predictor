#!/usr/bin/env python3
"""
Simple test to check module functionality.
"""

import pandas as pd
from src.preprocess import transform_to_tall_format, calculate_volatility_metrics, add_technical_features

def test_preprocessing():
    """Test data preprocessing."""
    print("🚀 Loading data...")
    df = pd.read_csv('data/raw/Combined_News_DJIA.csv')
    print(f"   Original size: {df.shape}")
    print(f"   Columns: {df.columns.tolist()[:5]}...")
    
    print("\n📊 Converting to tall format...")
    df_tall = transform_to_tall_format(df)
    print(f"   Size after transformation: {df_tall.shape}")
    
    print("\n📈 Calculating volatility metrics...")
    try:
        df_with_vol = calculate_volatility_metrics(df_tall)
        print(f"   Size with volatility: {df_with_vol.shape}")
        print(f"   New columns: {[col for col in df_with_vol.columns if 'volatility' in col.lower()]}")
    except Exception as e:
        print(f"   ❌ Error in volatility calculation: {e}")
    
    print("\n✅ Basic testing completed!")

if __name__ == "__main__":
    test_preprocessing()
