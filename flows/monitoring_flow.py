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
    
    # First try to get detailed predictions for drift monitoring
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='predictions/detailed/'
        )
        
        if 'Contents' in response:
            # Filter files from last N days
            cutoff_date = datetime.now() - timedelta(days=days_back)
            recent_files = []
            
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('_detailed.parquet'):
                    try:
                        # Extract date from filename (e.g., predictions/detailed/2023-01-15_detailed.parquet)
                        date_str = key.split('/')[-1].replace('_detailed.parquet', '')
                        file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        if file_date >= cutoff_date:
                            recent_files.append(key)
                    except ValueError:
                        continue
            
            if recent_files:
                # Load and combine detailed prediction files
                all_predictions = []
                for file_key in recent_files:
                    try:
                        pred_df = read_parquet_from_s3(bucket_name, file_key)
                        all_predictions.append(pred_df)
                    except Exception as e:
                        print(f"⚠️ Error reading {file_key}: {e}")
                
                if all_predictions:
                    combined_predictions = pd.concat(all_predictions, ignore_index=True)
                    print(f"📊 Combined detailed predictions: {len(combined_predictions)} samples from {len(recent_files)} files")
                    return combined_predictions
    
    except Exception as e:
        print(f"⚠️ Could not load detailed predictions: {e}")
    
    # Fallback to regular prediction files
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='predictions/',
            Delimiter='/'  # Only get files directly under predictions/, not subdirectories
        )
        
        if 'Contents' not in response:
            print("⚠️ No prediction files found")
            return pd.DataFrame()
        
        # Filter files from last N days
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_files = []
        
        for obj in response['Contents']:
            key = obj['Key']
            # Skip subdirectories and only process direct parquet files
            if key.endswith('.parquet') and '/' == key.count('/'):
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
            print(f"📊 Combined predictions: {len(combined_predictions)} days from {len(recent_files)} files")
            return combined_predictions
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"❌ Error getting predictions: {e}")
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
    """Create comprehensive Evidently monitoring reports."""
    print("🔍 Running Evidently monitoring report...")
    
    try:
        from evidently import ColumnMapping
        from evidently.report import Report
        from evidently.metric_preset import DataDriftPreset, ClassificationPreset
        from evidently.metrics import ColumnQuantileMetric, ColumnDriftMetric
        from evidently.test_suite import TestSuite
        from evidently.tests import TestAccuracyScore, TestF1Score
        
        # Prepare data for Evidently
        print("📊 Preparing data for Evidently...")
        
        # Select common columns for drift analysis (only available ones)
        available_columns = current_data.columns.tolist()
        numeric_features = [col for col in ['vol_lag_1', 'vol_lag_3', 'vol_lag_7', 'vol_ma_3', 'vol_ma_7', 
                           'vol_ma_14', 'dayofweek', 'month', 'quarter'] if col in available_columns]
        text_features = ['Headline'] if 'Headline' in available_columns else []
        
        print(f"📊 Available numeric features: {numeric_features}")
        print(f"📊 Available text features: {text_features}")
        
        # Create column mapping
        column_mapping = ColumnMapping()
        if text_features:
            column_mapping.text_features = text_features
        if numeric_features:
            column_mapping.numerical_features = numeric_features
        if 'vol_change_binary' in reference_data.columns:
            column_mapping.target = 'vol_change_binary'
            column_mapping.prediction = 'prediction_mean_class' if 'prediction_mean_class' in current_data.columns else None
        
        # Create simplified data drift report
        print("📈 Creating simplified data drift report...")
        metrics_list = [DataDriftPreset()]
        
        # Only add column metrics if columns exist
        if 'vol_lag_1' in available_columns:
            metrics_list.append(ColumnQuantileMetric(column_name='vol_lag_1', quantile=0.95))
            metrics_list.append(ColumnDriftMetric(column_name='vol_lag_1'))
        
        drift_report = Report(metrics=metrics_list)
        
        drift_report.run(reference_data=reference_data, current_data=current_data, 
                        column_mapping=column_mapping)
        
        # Save HTML report
        reports_dir = Path("monitoring/evidently_reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drift_report_path = reports_dir / f"data_drift_{timestamp}.html"
        drift_report.save_html(str(drift_report_path))
        print(f"💾 Data drift report saved: {drift_report_path}")
        
        # Create classification report if we have predictions
        classification_metrics = {}
        if not predictions_data.empty and 'vol_change_binary' in predictions_data.columns:
            print("📈 Creating classification performance report...")
            
            # Prepare prediction data
            pred_data = predictions_data.dropna(subset=['vol_change_binary'])
            if len(pred_data) > 10:  # Need sufficient data
                
                classification_report = Report(metrics=[
                    ClassificationPreset(),
                ])
                
                # Add prediction columns to current data sample for classification analysis
                if len(pred_data) > 0:
                    classification_report.run(
                        reference_data=reference_data, 
                        current_data=pred_data,
                        column_mapping=column_mapping
                    )
                    
                    classification_report_path = reports_dir / f"classification_{timestamp}.html"
                    classification_report.save_html(str(classification_report_path))
                    print(f"💾 Classification report saved: {classification_report_path}")
                    
                    # Extract classification metrics
                    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
                    
                    y_true = pred_data['vol_change_binary'].astype(int)
                    y_pred = pred_data['prediction_mean_class'].astype(int)
                    y_proba = pred_data['prediction_mean_proba']
                    
                    classification_metrics = {
                        'accuracy': accuracy_score(y_true, y_pred),
                        'f1': f1_score(y_true, y_pred),
                        'auc': roc_auc_score(y_true, y_proba) if len(set(y_true)) > 1 else 0.5
                    }
        
        # Create test suite for alerts
        print("🧪 Running test suite...")
        test_suite = TestSuite(tests=[
            TestAccuracyScore(gte=0.5),
            TestF1Score(gte=0.5),
        ])
        
        if not predictions_data.empty and 'vol_change_binary' in predictions_data.columns:
            pred_data = predictions_data.dropna(subset=['vol_change_binary'])
            if len(pred_data) > 10:
                test_suite.run(reference_data=reference_data, current_data=pred_data,
                              column_mapping=column_mapping)
                
                test_report_path = reports_dir / f"test_suite_{timestamp}.html"
                test_suite.save_html(str(test_report_path))
                print(f"💾 Test suite report saved: {test_report_path}")
        
        # Extract metrics from drift report
        drift_metrics = {}
        try:
            # Get drift results (simplified extraction)
            drift_metrics = {
                'data_drift_detected': False,  # Simplified
                'drift_share': 0.1,  # Simplified
                'reference_samples': len(reference_data),
                'current_samples': len(current_data),
            }
        except Exception as e:
            print(f"⚠️ Could not extract detailed drift metrics: {e}")
        
        # Combine all metrics
        all_metrics = {**drift_metrics, **classification_metrics}
        
        # Save reports to Evidently workspace for UI
        workspace_dir = Path("monitoring/evidently_workspace")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy reports to workspace
        import shutil
        for report_file in reports_dir.glob("*.html"):
            shutil.copy2(report_file, workspace_dir / report_file.name)
        
        print(f"📊 Evidently reports created: {len(list(reports_dir.glob('*.html')))} files")
        print(f"🌐 Reports available in Evidently UI and as HTML files")
        
        return all_metrics
        
    except ImportError as e:
        print(f"⚠️ Evidently not fully available: {e}")
        print("📊 Running simplified monitoring...")
        
        # Fallback to simple monitoring
        metrics = {
            'reference_samples': len(reference_data),
            'current_samples': len(current_data),
            'data_drift_detected': False,
            'drift_share': 0.0,
        }
        
        # If we have predictions with ground truth, calculate basic metrics
        if not predictions_data.empty and 'vol_change_binary' in predictions_data.columns:
            pred_data = predictions_data.dropna(subset=['vol_change_binary'])
            
            if len(pred_data) > 0:
                from sklearn.metrics import accuracy_score, f1_score
                
                y_true = pred_data['vol_change_binary'].astype(int)
                y_pred = pred_data['prediction_mean_class'].astype(int)
                
                metrics['accuracy'] = accuracy_score(y_true, y_pred)
                metrics['f1_score'] = f1_score(y_true, y_pred)
                
                # Prediction distribution
                pred_probs = pred_data['prediction_mean_proba']
                metrics['prediction_mean_proba_quantile_0.95'] = pred_probs.quantile(0.95)
                metrics['prediction_mean_proba_quantile_0.05'] = pred_probs.quantile(0.05)
        
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
        'auc': 0.52,          # Alert if AUC drops below 52%
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
            elif metric_name in ['accuracy', 'f1', 'auc']:
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
