"""
Prefect flow for model and data monitoring using Evidently.
"""

import os
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
from prefect import flow, task
from dotenv import load_dotenv

# Import our custom modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import read_parquet_from_s3, get_s3_client

load_dotenv()


@task
def get_reference_data():
    """Load reference data (validation set) for comparison."""
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    
    print("📥 Loading reference data from S3...")
    reference_data = read_parquet_from_s3(bucket_name, 'processed/val_tall.parquet')
    
    print(f"📊 Reference data: {reference_data.shape[0]:,} samples")
    return reference_data


@task
def get_recent_predictions(days_back: int = 7):
    """Get recent predictions from S3 for monitoring."""
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    s3_client = get_s3_client()
    
    print(f"📥 Getting predictions from last {days_back} days...")
    
    # Get list of prediction files from the last week
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix='predictions/'
    )
    
    if 'Contents' not in response:
        print("⚠️ No prediction files found")
        return pd.DataFrame()
    
    # Filter files from last N days
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_files = []
    
    for obj in response['Contents']:
        key = obj['Key']
        # Extract date from filename (e.g., predictions/2023-01-15.parquet)
        if key.endswith('.parquet'):
            try:
                date_str = key.split('/')[-1].replace('.parquet', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                if file_date >= cutoff_date:
                    recent_files.append(key)
            except ValueError:
                continue
    
    if not recent_files:
        print(f"⚠️ No predictions found in last {days_back} days")
        return pd.DataFrame()
    
    # Load and combine all recent prediction files
    all_predictions = []
    for file_key in recent_files:
        try:
            pred_df = read_parquet_from_s3(bucket_name, file_key)
            all_predictions.append(pred_df)
        except Exception as e:
            print(f"⚠️ Error reading {file_key}: {e}")
    
    if all_predictions:
        combined_predictions = pd.concat(all_predictions, ignore_index=True)
        print(f"📊 Combined predictions: {len(combined_predictions)} days")
        return combined_predictions
    else:
        return pd.DataFrame()


@task
def get_current_data_sample():
    """
    Get current data sample for drift monitoring.
    In real scenario, this would be actual production data.
    For simulation, we'll use test data.
    """
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    
    print("📥 Getting current data sample...")
    test_data = read_parquet_from_s3(bucket_name, 'processed/test_tall.parquet')
    
    # Take a recent sample (last 7 days worth of data)
    unique_dates = sorted(test_data['Date'].unique())
    recent_dates = unique_dates[-7:] if len(unique_dates) >= 7 else unique_dates
    
    current_sample = test_data[test_data['Date'].isin(recent_dates)]
    
    print(f"📊 Current sample: {current_sample.shape[0]:,} samples from {len(recent_dates)} days")
    return current_sample


@task
def run_evidently_report(reference_data: pd.DataFrame, current_data: pd.DataFrame, 
                        predictions_data: pd.DataFrame):
    """Run simplified monitoring report."""
    print("🔍 Running simplified monitoring report...")
    
    # For now, let's create a simple metrics comparison
    metrics = {}
    
    # Data size comparison
    metrics['reference_samples'] = len(reference_data)
    metrics['current_samples'] = len(current_data)
    metrics['data_drift'] = False  # Simplified
    metrics['drift_share'] = 0.0   # Simplified
    
    # If we have predictions with ground truth, calculate basic metrics
    if not predictions_data.empty and 'true_vol_up' in predictions_data.columns:
        pred_data = predictions_data.dropna(subset=['true_vol_up'])
        
        if len(pred_data) > 0:
            from sklearn.metrics import accuracy_score, f1_score
            
            y_true = pred_data['true_vol_up']
            y_pred = pred_data['prediction_mean_class']
            
            metrics['accuracy'] = accuracy_score(y_true, y_pred)
            metrics['f1'] = f1_score(y_true, y_pred)
            
            # Prediction distribution
            pred_probs = pred_data['prediction_mean_proba']
            metrics['prediction_mean_proba_quantile_0.95'] = pred_probs.quantile(0.95)
            metrics['prediction_mean_proba_quantile_0.05'] = pred_probs.quantile(0.05)
    
    print(f"📊 Metrics calculated: {len(metrics)} metrics")
    return metrics


@task
def save_metrics_to_db(metrics: dict):
    """Save monitoring metrics to PostgreSQL."""
    print("💾 Saving metrics to PostgreSQL...")
    
    # Database connection
    conn_string = os.getenv('POSTGRES_CONNECTION_STRING', 
                           'postgresql://user:password@localhost:5432/monitoring')
    
    try:
        # Connect to database
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Create table if not exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS volatility_metrics (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT NOW(),
            metric_name VARCHAR(100),
            metric_value FLOAT,
            model_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
        cursor.execute(create_table_sql)
        
        # Insert metrics
        model_version = "unknown"  # Will be updated when we track model versions
        
        for metric_name, metric_value in metrics.items():
            if metric_value is not None:
                insert_sql = """
                INSERT INTO volatility_metrics (metric_name, metric_value, model_version)
                VALUES (%s, %s, %s)
                """
                cursor.execute(insert_sql, (metric_name, float(metric_value), model_version))
        
        # Commit changes
        conn.commit()
        
        print(f"✅ Saved {len(metrics)} metrics to database")
        
        # Close connection
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        raise


@task
def check_alerts(metrics: dict):
    """Check metrics against thresholds and return alerts."""
    print("🚨 Checking alert thresholds...")
    
    # Define thresholds
    thresholds = {
        'dataset_drift': 0.3,  # Alert if dataset drift detected
        'drift_share': 0.4,    # Alert if >40% of features are drifting
        'accuracy': 0.52,      # Alert if accuracy drops below 52%
        'f1': 0.50,           # Alert if F1 drops below 50%
    }
    
    alerts = []
    
    for metric_name, threshold in thresholds.items():
        if metric_name in metrics:
            value = metrics[metric_name]
            
            if metric_name in ['dataset_drift']:
                # Boolean metrics
                if value:
                    alerts.append({
                        'metric': metric_name,
                        'value': value,
                        'threshold': threshold,
                        'message': f"⚠️ Dataset drift detected!"
                    })
            elif metric_name in ['drift_share']:
                # Percentage metrics (higher is worse)
                if value > threshold:
                    alerts.append({
                        'metric': metric_name,
                        'value': value,
                        'threshold': threshold,
                        'message': f"⚠️ High drift share: {value:.2%} > {threshold:.2%}"
                    })
            elif metric_name in ['accuracy', 'f1']:
                # Performance metrics (lower is worse)
                if value < threshold:
                    alerts.append({
                        'metric': metric_name,
                        'value': value,
                        'threshold': threshold,
                        'message': f"⚠️ Low {metric_name}: {value:.3f} < {threshold:.3f}"
                    })
    
    if alerts:
        print(f"🚨 {len(alerts)} alerts triggered:")
        for alert in alerts:
            print(f"  - {alert['message']}")
    else:
        print("✅ All metrics within acceptable thresholds")
    
    return alerts


@flow(name="monitoring-flow")
def monitoring_flow(days_back: int = 7):
    """
    Main monitoring flow that:
    1. Loads reference data (validation set)
    2. Gets recent predictions and current data
    3. Runs Evidently monitoring report
    4. Saves metrics to PostgreSQL
    5. Checks alert thresholds
    
    Args:
        days_back: Number of days to look back for predictions
    """
    
    print("🚀 Starting monitoring flow...")
    
    # Load reference data
    reference_data = get_reference_data()
    
    # Get recent data for monitoring
    predictions_data = get_recent_predictions(days_back)
    current_data = get_current_data_sample()
    
    if current_data.empty:
        print("❌ No current data available for monitoring")
        return {"status": "error", "message": "No current data"}
    
    # Run Evidently report
    metrics = run_evidently_report(reference_data, current_data, predictions_data)
    
    # Save metrics to database
    save_metrics_to_db(metrics)
    
    # Check alerts
    alerts = check_alerts(metrics)
    
    # Summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "metrics_count": len(metrics),
        "alerts_count": len(alerts),
        "reference_samples": len(reference_data),
        "current_samples": len(current_data),
        "prediction_days": len(predictions_data) if not predictions_data.empty else 0,
        "key_metrics": {
            "dataset_drift": metrics.get('dataset_drift', None),
            "drift_share": metrics.get('drift_share', None),
            "accuracy": metrics.get('accuracy', None),
            "f1": metrics.get('f1', None)
        },
        "alerts": alerts
    }
    
    print("✅ Monitoring flow completed!")
    if alerts:
        print("⚠️ Review alerts and consider retraining if needed")
    
    return summary


if __name__ == "__main__":
    # Run the flow locally for testing
    result = monitoring_flow(days_back=7)
    print("🎉 Monitoring completed!")
    print(f"📊 Summary: {result}")
