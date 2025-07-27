"""
Unit tests for preprocessing functions.
"""

import pytest
import pandas as pd
import numpy as np
from src.preprocess import transform_to_tall_format, add_calendar_features


def test_transform_to_tall_format():
    """Test the transformation from wide to tall format."""
    # Create sample wide format data
    wide_data = pd.DataFrame({
        'Date': ['2023-01-01', '2023-01-02'],
        'vol_up': [1, 0],
        'Top1': ['News headline 1', 'News headline 3'],
        'Top2': ['News headline 2', 'News headline 4'],
        'Top3': [None, 'News headline 5'],  # Test missing headline
        'feature1': [10.5, 20.3],
        'feature2': [5.2, 8.1]
    })
    
    # Transform to tall format
    tall_data = transform_to_tall_format(wide_data)
    
    # Check structure
    assert 'Date' in tall_data.columns
    assert 'Headline' in tall_data.columns
    assert 'vol_up' in tall_data.columns
    assert 'feature1' in tall_data.columns
    assert 'feature2' in tall_data.columns
    
    # Check number of rows (should have 5 headlines total: 2+2+1)
    assert len(tall_data) == 5
    
    # Check that features are preserved
    date1_data = tall_data[tall_data['Date'] == '2023-01-01']
    assert all(date1_data['feature1'] == 10.5)
    assert all(date1_data['feature2'] == 5.2)
    assert all(date1_data['vol_up'] == 1)
    
    # Check headlines
    headlines = tall_data['Headline'].tolist()
    expected_headlines = ['News headline 1', 'News headline 2', 
                         'News headline 3', 'News headline 4', 'News headline 5']
    assert set(headlines) == set(expected_headlines)


def test_add_calendar_features():
    """Test calendar feature addition."""
    # Create sample data
    data = pd.DataFrame({
        'Date': ['2023-01-01', '2023-01-02', '2023-02-01'],  # Sunday, Monday, Wednesday
        'some_feature': [1, 2, 3]
    })
    
    # Add calendar features
    result = add_calendar_features(data)
    
    # Check that calendar columns are added
    assert any(col.startswith('dow_') for col in result.columns)
    assert any(col.startswith('month_') for col in result.columns)
    assert any(col.startswith('quarter_') for col in result.columns)
    
    # Check specific values for 2023-01-01 (Sunday = 6)
    jan_1_row = result[result['Date'] == '2023-01-01'].iloc[0]
    assert jan_1_row['dow_6'] == 1  # Sunday
    assert jan_1_row['month_1'] == 1  # January
    assert jan_1_row['quarter_1'] == 1  # Q1


def test_transform_empty_data():
    """Test transformation with empty data."""
    empty_data = pd.DataFrame(columns=['Date', 'vol_up', 'Top1', 'Top2'])
    result = transform_to_tall_format(empty_data)
    
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    assert 'Headline' in result.columns


def test_transform_with_missing_headlines():
    """Test transformation when some headlines are missing."""
    data_with_nulls = pd.DataFrame({
        'Date': ['2023-01-01'],
        'vol_up': [1],
        'Top1': ['Headline 1'],
        'Top2': [None],
        'Top3': [''],  # Empty string
        'Top4': ['Headline 4'],
        'feature1': [10.0]
    })
    
    result = transform_to_tall_format(data_with_nulls)
    
    # Should only have 2 rows (headline 1 and headline 4)
    assert len(result) == 2
    headlines = result['Headline'].tolist()
    assert 'Headline 1' in headlines
    assert 'Headline 4' in headlines
