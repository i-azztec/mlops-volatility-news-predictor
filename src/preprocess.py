"""Data preprocessing functions."""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Tuple


def transform_to_tall_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform data from wide format (25 headlines per row) to tall format.
    
    Args:
        df: DataFrame with columns Date, vol_up, Top1, Top2, ..., Top25, and feature columns
        
    Returns:
        DataFrame in tall format where each row is one headline with features
    """
    tall_data = []
    
    # Get feature columns (all columns except Date, vol_up/Label, and Top1-Top25)
    headline_cols = [f'Top{i}' for i in range(1, 26)]
    feature_cols = [col for col in df.columns 
                   if col not in ['Date', 'Label', 'vol_up'] + headline_cols]
    
    for idx, row in df.iterrows():
        # Get features for this date
        features = {col: row[col] for col in feature_cols}
        
        # Create one row for each headline
        for i in range(1, 26):
            headline_col = f'Top{i}'
            if headline_col in row.index:  # Check if column exists
                headline = row[headline_col]
                if isinstance(headline, str) and headline.strip() and not pd.isna(headline):  # Check for non-empty strings
                    tall_data.append({
                        'Date': row['Date'],
                        'Headline': headline,
                        'vol_up': row['vol_up'] if 'vol_up' in row.index else row.get('Label', 0),  # Support both column names
                        **features
                    })
    
    result_df = pd.DataFrame(tall_data)
    
    # Ensure the DataFrame has the expected columns even if empty
    if len(result_df) == 0:
        result_df = pd.DataFrame(columns=['Date', 'Headline', 'vol_up'])
    
    return result_df


def calculate_volatility_metrics(data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    Calculate features from news data for volatility prediction.
    
    Args:
        data: DataFrame with news headlines and target labels
        window: Rolling window for calculations
        
    Returns:
        DataFrame with engineered features added
    """
    result = data.copy()
    
    # Convert Date to datetime if it's not already
    if not pd.api.types.is_datetime64_any_dtype(result['Date']):
        result['Date'] = pd.to_datetime(result['Date'])
    
    # Sort by date to ensure proper rolling calculations
    result = result.sort_values('Date').reset_index(drop=True)
    
    # Basic text features
    result['headline_length'] = result['Headline'].astype(str).str.len()
    result['word_count'] = result['Headline'].astype(str).str.split().str.len()
    
    # Rolling statistics on historical labels
    result['historical_vol_mean'] = result['vol_up'].rolling(window=window, min_periods=1).mean()
    result['historical_vol_std'] = result['vol_up'].rolling(window=window, min_periods=1).std()
    
    return result


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators using only historical information.
    
    Args:
        df: DataFrame with volatility metrics
        
    Returns:
        DataFrame with technical features added
    """
    result = df.copy()
    
    # Lags of volatility (avoid data leakage)
    for i in [1, 2, 3, 5, 10]:
        result[f'realized_vol_lag_{i}'] = result['realized_vol'].shift(i)
        result[f'tr_vol_lag_{i}'] = result['tr_vol'].shift(i)
        result[f'park_vol_lag_{i}'] = result['park_vol'].shift(i)
    
    # Moving averages on historical data
    for window in [5, 10, 20]:
        result[f'realized_vol_ma_{window}'] = result['realized_vol'].shift(1).rolling(window).mean()
        result[f'tr_vol_ma_{window}'] = result['tr_vol'].shift(1).rolling(window).mean()
        result[f'park_vol_ma_{window}'] = result['park_vol'].shift(1).rolling(window).mean()
    
    # Remove current volatility values to avoid leakage
    result = result.drop(['realized_vol', 'tr_vol', 'park_vol'], axis=1)
    
    return result


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add calendar features.
    
    Args:
        df: DataFrame with Date column
        
    Returns:
        DataFrame with calendar features added
    """
    result = df.copy()
    result['day_of_week'] = pd.to_datetime(result['Date']).dt.dayofweek
    result['month'] = pd.to_datetime(result['Date']).dt.month
    result['quarter'] = pd.to_datetime(result['Date']).dt.quarter
    
    # One-hot encoding
    result = pd.get_dummies(result, columns=['day_of_week', 'month', 'quarter'], 
                           prefix=['dow', 'month', 'quarter'])
    return result


def create_target_variable(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create binary target variable for volatility direction.
    
    Args:
        df: DataFrame with realized_vol column
        
    Returns:
        DataFrame with vol_up target variable
    """
    result = df.copy()
    result['vol_change'] = result['realized_vol'].diff()
    result['vol_up'] = (result['vol_change'] > 0).astype(int)
    return result
