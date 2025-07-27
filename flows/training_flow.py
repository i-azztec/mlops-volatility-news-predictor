"""
Prefect flow for model training and registration.
"""

import os
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import pandas as pd
import pickle
from pathlib import Path
from prefect import flow, task
from dotenv import load_dotenv

# Import our custom modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.utils import read_parquet_from_s3
from src.train import prepare_features, find_best_model, evaluate_model
from src.predict import evaluate_on_test_data

load_dotenv()


@task
def setup_mlflow():
    """Setup MLflow tracking and experiment."""
    # Set tracking URI
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)
    
    # Set or create experiment
    experiment_name = os.getenv('EXPERIMENT_NAME', 'volatility-hyperopt')
    
    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(experiment_name)
            print(f"Created new experiment: {experiment_name}")
        else:
            experiment_id = experiment.experiment_id
            print(f"Using existing experiment: {experiment_name}")
    except Exception as e:
        print(f"Error setting up experiment: {e}")
        experiment_id = "0"  # Default experiment
    
    mlflow.set_experiment(experiment_name)
    return experiment_id


@task
def load_training_data():
    """Load training and validation data from S3."""
    bucket_name = os.getenv('S3_BUCKET_NAME', 'volatility-news-data')
    
    print("📥 Loading training data from S3...")
    
    # Load datasets
    train_data = read_parquet_from_s3(bucket_name, 'processed/train_tall.parquet')
    val_data = read_parquet_from_s3(bucket_name, 'processed/val_tall.parquet')
    test_data = read_parquet_from_s3(bucket_name, 'processed/test_tall.parquet')
    
    print(f"📊 Loaded data:")
    print(f"  - Train: {train_data.shape[0]:,} samples")
    print(f"  - Val:   {val_data.shape[0]:,} samples")
    print(f"  - Test:  {test_data.shape[0]:,} samples")
    
    # Prepare features
    X_train, y_train, numeric_features = prepare_features(train_data)
    X_val, y_val, _ = prepare_features(val_data)
    X_test, y_test, _ = prepare_features(test_data)
    
    return {
        'X_train': X_train, 'y_train': y_train,
        'X_val': X_val, 'y_val': y_val,
        'X_test': X_test, 'y_test': y_test,
        'test_data': test_data,
        'numeric_features': numeric_features
    }


@task
def run_optimization(data_dict: dict, max_evals: int = 20):
    """Run hyperparameter optimization."""
    print("🔍 Starting hyperparameter optimization...")
    
    X_train = data_dict['X_train']
    y_train = data_dict['y_train']
    X_val = data_dict['X_val']
    y_val = data_dict['y_val']
    
    # Start parent MLflow run
    with mlflow.start_run(run_name="hyperopt_session"):
        # Run optimization
        best_model, best_params = find_best_model(
            X_train, y_train, X_val, y_val, max_evals=max_evals
        )
        
        # Log best parameters
        mlflow.log_params(best_params)
        
        # Evaluate best model on validation set
        val_metrics = evaluate_model(best_model, X_val, y_val)
        for name, value in val_metrics.items():
            mlflow.log_metric(f"best_val_{name}", value)
        
        print(f"✅ Optimization completed!")
        print(f"📈 Best validation metrics:")
        for name, value in val_metrics.items():
            print(f"  - {name}: {value:.4f}")
        
        return best_model, best_params


@task
def evaluate_on_test(model, data_dict: dict):
    """Evaluate the best model on test set."""
    print("🧪 Evaluating on test set...")
    
    test_data = data_dict['test_data']
    X_test = data_dict['X_test']
    y_test = data_dict['y_test']
    
    # Evaluate model
    test_results = evaluate_on_test_data(model, test_data)
    
    # Log test metrics to MLflow
    headline_metrics = test_results['headline_metrics']
    daily_metrics = test_results['daily_metrics']
    
    for name, value in headline_metrics.items():
        mlflow.log_metric(f"test_headline_{name}", value)
    
    for method, metrics in daily_metrics.items():
        for metric_name, value in metrics.items():
            mlflow.log_metric(f"test_daily_{method}_{metric_name}", value)
    
    print(f"📊 Test results (headline level):")
    for name, value in headline_metrics.items():
        print(f"  - {name}: {value:.4f}")
    
    print(f"📊 Test results (daily aggregation):")
    for method, metrics in daily_metrics.items():
        print(f"  {method}:")
        for metric_name, value in metrics.items():
            print(f"    - {metric_name}: {value:.4f}")
    
    return test_results


@task
def register_model(model, test_results: dict, model_params: dict):
    """Register the model in MLflow Model Registry."""
    print("📝 Registering model in MLflow Model Registry...")
    
    model_name = os.getenv('MODEL_REGISTRY_NAME', 'volatility-classifier')
    
    # Extract vectorizer from the model pipeline
    vectorizer = model.named_steps['preprocessor'].named_transformers_['text']
    
    # Log model and artifacts
    mlflow.sklearn.log_model(
        model, 
        "model",
        registered_model_name=model_name
    )
    
    # Save and log vectorizer separately for easier loading
    vectorizer_path = "vectorizer.pkl"
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(vectorizer, f)
    mlflow.log_artifact(vectorizer_path)
    
    # Log additional info
    mlflow.log_dict(test_results['daily_metrics'], "daily_metrics.json")
    mlflow.log_dict(model_params, "model_params.json")
    
    # Add model description
    client = mlflow.MlflowClient()
    run_id = mlflow.active_run().info.run_id
    
    # Get the latest version
    model_version = client.get_latest_versions(model_name, stages=["None"])[0]
    
    # Update model version with description
    best_auc = test_results['daily_metrics']['mean_proba']['roc_auc']
    description = f"""
    Volatility Prediction Model
    
    **Model Type:** XGBoost with TF-IDF text features
    **Training Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    **Test AUC (daily aggregation):** {best_auc:.4f}
    
    **Features:**
    - Text: TF-IDF from news headlines
    - Numeric: Historical volatility lags and moving averages
    
    **Aggregation:** Uses mean probability for daily predictions
    
    **Status:** Ready for promotion to Production stage
    """
    
    client.update_model_version(
        name=model_name,
        version=model_version.version,
        description=description.strip()
    )
    
    # Transition to Staging
    client.transition_model_version_stage(
        name=model_name,
        version=model_version.version,
        stage="Staging"
    )
    
    print(f"✅ Model registered as {model_name} v{model_version.version}")
    print(f"📋 Model moved to 'Staging' stage")
    print(f"💡 Manually promote to 'Production' when ready")
    
    return model_version.version


@flow(name="training-flow")
def training_flow(max_evals: int = 20):
    """
    Main training flow that:
    1. Sets up MLflow experiment
    2. Loads training data from S3
    3. Runs hyperparameter optimization
    4. Evaluates best model on test set
    5. Registers model in MLflow Model Registry
    """
    
    print("🚀 Starting model training flow...")
    
    # Setup MLflow
    experiment_id = setup_mlflow()
    
    # Load data
    data_dict = load_training_data()
    
    # Run optimization and get best model
    best_model, best_params = run_optimization(data_dict, max_evals)
    
    # Evaluate on test set
    test_results = evaluate_on_test(best_model, data_dict)
    
    # Register model
    model_version = register_model(best_model, test_results, best_params)
    
    print("✅ Training flow completed successfully!")
    print(f"🎯 Model version {model_version} is ready for production")
    
    return {
        "model_version": model_version,
        "test_metrics": test_results['daily_metrics'],
        "experiment_id": experiment_id
    }


if __name__ == "__main__":
    # Run the flow locally for testing
    result = training_flow(max_evals=5)  # Small number for testing
    print("🎉 Training completed!")
    print(f"📊 Results: {result}")
