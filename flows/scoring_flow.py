"""
Prefect flow for daily batch scoring.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from prefect import flow, task
from dotenv import load_dotenv

# Import our custom modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import read_parquet_from_s3, save_parquet_to_s3
from src.predict import load_production_model, predict_daily_batch

load_dotenv()


@task
def load_model_and_vectorizer():
    """Load production model and vectorizer from MLflow."""
    print("🔄 Loading production model from MLflow...")
    
    try:
        model, vectorizer, model_version = load_production_model()
        print(f"✅ Loaded model version {model_version}")
        return model, vectorizer, model_version
    except Exception as e:
        print(f"❌ Failed to load production model: {e}")
        raise


@task
def get_daily_data(target_date: str = None):
    """
    Get daily data for scoring.
    In real scenario, this would fetch new data from data sources.
    For simulation, we'll use test data.
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"📅 Getting data for date: {target_date}")
    
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    
    # Load test data for simulation
    test_data = read_parquet_from_s3(bucket_name, 'processed/test_tall.parquet')
    
    # Convert Date column to datetime for filtering
    test_data['Date'] = pd.to_datetime(test_data['Date'])
    target_date_dt = pd.to_datetime(target_date)
    
    # Get data for the target date
    daily_data = test_data[test_data['Date'].dt.date == target_date_dt.date()]
    
    if daily_data.empty:
        # If no data for exact date, get a random date from test set
        available_dates = test_data['Date'].dt.date.unique()
        if len(available_dates) > 0:
            random_date = available_dates[0]  # Take first available date
            daily_data = test_data[test_data['Date'].dt.date == random_date]
            print(f"⚠️  No data for {target_date}, using {random_date} instead")
            target_date = random_date.strftime('%Y-%m-%d')
    
    if daily_data.empty:
        raise ValueError(f"No data available for scoring")
    
    # Extract headlines and historical features
    headlines = daily_data['Headline'].tolist()
    
    # Get historical features (all columns except Date, Headline, vol_up)
    feature_cols = [col for col in daily_data.columns 
                   if col not in ['Date', 'Headline', 'vol_up']]
    
    # Use first row's features (should be same for all headlines of the day)
    historical_features = daily_data[feature_cols].iloc[0].to_dict()
    
    # Get true label for evaluation (if available)
    true_vol_up = daily_data['vol_up'].iloc[0] if 'vol_up' in daily_data.columns else None
    
    print(f"📰 Found {len(headlines)} headlines for {target_date}")
    
    return {
        'date': target_date,
        'headlines': headlines,
        'historical_features': historical_features,
        'true_vol_up': true_vol_up
    }


@task
def make_predictions(daily_data: dict, model, vectorizer, model_version: str):
    """Make predictions for the daily data."""
    print(f"🔮 Making predictions for {daily_data['date']}...")
    
    # Make batch prediction
    prediction_result = predict_daily_batch(
        headlines=daily_data['headlines'],
        model=model,
        historical_features=daily_data['historical_features']
    )
    
    # Add metadata
    prediction_result.update({
        'date': daily_data['date'],
        'model_version': model_version,
        'true_vol_up': daily_data.get('true_vol_up'),
        'prediction_timestamp': datetime.now().isoformat()
    })
    
    # Log prediction summary
    print(f"📊 Prediction summary for {daily_data['date']}:")
    print(f"  - Mean probability: {prediction_result['prediction_mean_proba']:.3f}")
    print(f"  - Mean class: {prediction_result['prediction_mean_class']}")
    print(f"  - Majority vote: {prediction_result['prediction_majority_vote']}")
    print(f"  - Max probability: {prediction_result['prediction_max_proba']:.3f}")
    print(f"  - Number of headlines: {prediction_result['num_headlines']}")
    
    if prediction_result.get('true_vol_up') is not None:
        true_label = prediction_result['true_vol_up']
        pred_label = prediction_result['prediction_mean_class']
        accuracy = "✅ Correct" if pred_label == true_label else "❌ Incorrect"
        print(f"  - True label: {true_label}, Predicted: {pred_label} ({accuracy})")
    
    return prediction_result


@task
def save_predictions(prediction_result: dict):
    """Save predictions to S3 in monitoring-friendly format."""
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    date_str = prediction_result['date']
    
    # Create DataFrame for saving (daily aggregated predictions)
    pred_df = pd.DataFrame([{
        'Date': prediction_result['date'],
        'prediction_mean_proba': prediction_result['prediction_mean_proba'],
        'prediction_mean_class': prediction_result['prediction_mean_class'],
        'prediction_majority_vote': prediction_result['prediction_majority_vote'],
        'prediction_max_proba': prediction_result['prediction_max_proba'],
        'prediction_max_class': prediction_result['prediction_max_class'],
        'num_headlines': prediction_result['num_headlines'],
        'model_version': prediction_result['model_version'],
        'vol_change_binary': prediction_result.get('true_vol_up'),  # Ground truth for monitoring
        'prediction_timestamp': prediction_result['prediction_timestamp']
    }])
    
    # Also create detailed predictions with historical features for drift monitoring
    if 'individual_predictions' in prediction_result:
        detailed_data = []
        historical_features = prediction_result.get('historical_features', {})
        
        for i, pred in enumerate(prediction_result['individual_predictions']):
            row = {
                'Date': prediction_result['date'],
                'Headline': pred['headline'],
                'prediction_mean_class': prediction_result['prediction_mean_class'],
                'prediction_mean_proba': prediction_result['prediction_mean_proba'],
                'vol_change_binary': prediction_result.get('true_vol_up'),
                'model_version': prediction_result['model_version'],
                # Add historical features for drift detection
                **{k: v for k, v in historical_features.items() if k.startswith(('vol_', 'dayofweek', 'month', 'quarter'))}
            }
            detailed_data.append(row)
        
        # Save detailed data for monitoring
        detailed_df = pd.DataFrame(detailed_data)
        detailed_s3_key = f"predictions/detailed/{date_str}_detailed.parquet"
        save_parquet_to_s3(detailed_df, bucket_name, detailed_s3_key)
        print(f"💾 Detailed predictions saved: s3://{bucket_name}/{detailed_s3_key}")
    
    # Save aggregated predictions
    s3_key = f"predictions/{date_str}.parquet"
    save_parquet_to_s3(pred_df, bucket_name, s3_key)
    
    print(f"💾 Saved predictions to s3://{bucket_name}/{s3_key}")
    
    return s3_key


@flow(name="scoring-flow")
def scoring_flow(target_date: str = None):
    """
    Main scoring flow that:
    1. Loads production model from MLflow
    2. Gets daily data for scoring
    3. Makes predictions
    4. Saves predictions to S3
    
    Args:
        target_date: Date to score in YYYY-MM-DD format. If None, uses yesterday.
    """
    
    print("🚀 Starting daily scoring flow...")
    
    # Load model
    model, vectorizer, model_version = load_model_and_vectorizer()
    
    # Get daily data
    daily_data = get_daily_data(target_date)
    
    # Make predictions
    prediction_result = make_predictions(daily_data, model, vectorizer, model_version)
    
    # Save predictions
    s3_key = save_predictions(prediction_result)
    
    print("✅ Scoring flow completed successfully!")
    
    return {
        "date": prediction_result['date'],
        "prediction_mean_proba": prediction_result['prediction_mean_proba'],
        "prediction_mean_class": prediction_result['prediction_mean_class'],
        "model_version": model_version,
        "s3_key": s3_key
    }


if __name__ == "__main__":
    # Run the flow locally for testing
    result = scoring_flow()
    print("🎉 Scoring completed!")
    print(f"📊 Results: {result}")
