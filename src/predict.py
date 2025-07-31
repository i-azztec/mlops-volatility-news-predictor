"""
Model prediction functions for batch scoring and web service.
"""

import os
import mlflow
import mlflow.pyfunc
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
import pickle


def load_production_model() -> Tuple[Any, Any, str]:
    """
    Load the production model and vectorizer from MLflow Model Registry.
    
    Returns:
        Tuple of (model, vectorizer, model_version)
    """
    # Set MLflow tracking URI
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000'))
    
    model_name = os.getenv('MODEL_REGISTRY_NAME', 'volatility-classifier')
    
    try:
        # Load model in production stage (fallback to staging for demo)
        try:
            model_uri = f"models:/{model_name}/Production"
            model = mlflow.pyfunc.load_model(model_uri)
            stage = "Production"
        except:
            print("No Production model found, trying Staging...")
            model_uri = f"models:/{model_name}/Staging"
            model = mlflow.pyfunc.load_model(model_uri)
            stage = "Staging"
        
        # Get model version info
        client = mlflow.MlflowClient()
        model_version = client.get_latest_versions(
            model_name, 
            stages=[stage]
        )[0]
        
        # Load vectorizer from the same run
        run_id = model_version.run_id
        vectorizer_path = mlflow.artifacts.download_artifacts(
            run_id=run_id,
            artifact_path="vectorizer.pkl"
        )
        
        with open(vectorizer_path, 'rb') as f:
            vectorizer = pickle.load(f)
        
        print(f"✅ Loaded model version {model_version.version} from run {run_id}")
        
        return model, vectorizer, model_version.version
        
    except Exception as e:
        print(f"❌ Error loading production model: {e}")
        print("💡 Make sure a model is registered in 'Production' stage")
        raise


def predict_one(headline: str, model: Any, vectorizer: Any = None, 
                historical_features: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Make prediction for a single headline.
    
    Args:
        headline: News headline text
        model: Trained model pipeline
        vectorizer: Text vectorizer (if separate from model)
        historical_features: Dictionary with historical volatility features
        
    Returns:
        Dictionary with prediction results
    """
    # Default historical features (zeros if not provided)
    if historical_features is None:
        # Create dummy features matching the training data structure
        historical_features = {}
        
        # Volatility lags
        for i in [1, 2, 3, 5, 10]:
            for vol_type in ['realized_vol', 'tr_vol', 'park_vol']:
                historical_features[f'{vol_type}_lag_{i}'] = 0.0
        
        # Moving averages
        for window in [5, 10, 20]:
            for vol_type in ['realized_vol', 'tr_vol', 'park_vol']:
                historical_features[f'{vol_type}_ma_{window}'] = 0.0
        
        # Calendar features (dummy values for Monday, January, Q1)
        for i in range(7):
            historical_features[f'dow_{i}'] = 1.0 if i == 0 else 0.0
        for i in range(1, 13):
            historical_features[f'month_{i}'] = 1.0 if i == 1 else 0.0
        for i in range(1, 5):
            historical_features[f'quarter_{i}'] = 1.0 if i == 1 else 0.0
    
    # Create input DataFrame
    input_data = pd.DataFrame([{
        'Date': pd.Timestamp.now().date(),
        'Headline': headline,
        **historical_features
    }])
    
    try:
        # Make prediction
        prediction_proba = model.predict(input_data)[0]  # Get probability of class 1
        prediction_class = 1 if prediction_proba > 0.5 else 0
        
        return {
            'headline': headline,
            'prediction_class': prediction_class,
            'prediction_proba': float(prediction_proba),
            'confidence': float(abs(prediction_proba - 0.5) * 2),  # Scale to 0-1
            'interpretation': 'Volatility likely to increase' if prediction_class == 1 else 'Volatility likely to decrease'
        }
        
    except Exception as e:
        print(f"❌ Error making prediction: {e}")
        return {
            'headline': headline,
            'prediction_class': 0,
            'prediction_proba': 0.5,
            'confidence': 0.0,
            'interpretation': 'Error in prediction',
            'error': str(e)
        }


def predict_daily_batch(headlines: List[str], model: Any, 
                       historical_features: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Make predictions for a batch of headlines (daily batch).
    
    Args:
        headlines: List of news headlines for the day
        model: Trained model pipeline
        historical_features: Dictionary with historical volatility features
        
    Returns:
        Dictionary with aggregated daily prediction
    """
    if not headlines:
        return {
            'date': pd.Timestamp.now().date(),
            'num_headlines': 0,
            'prediction_mean_proba': 0.5,
            'prediction_mean_class': 0,
            'prediction_majority_vote': 0,
            'prediction_max_proba': 0.5,
            'prediction_max_class': 0,
            'error': 'No headlines provided'
        }
    
    # Get predictions for each headline
    individual_predictions = []
    for headline in headlines:
        pred_result = predict_one(headline, model, None, historical_features)
        individual_predictions.append(pred_result)
    
    # Extract probabilities and classes
    probas = [pred['prediction_proba'] for pred in individual_predictions]
    classes = [pred['prediction_class'] for pred in individual_predictions]
    
    # Aggregate predictions
    mean_proba = np.mean(probas)
    max_proba = np.max(probas)
    
    aggregated_result = {
        'date': pd.Timestamp.now().date(),
        'num_headlines': len(headlines),
        'prediction_mean_proba': float(mean_proba),
        'prediction_mean_class': 1 if mean_proba > 0.5 else 0,
        'prediction_majority_vote': 1 if np.sum(classes) >= len(classes)/2 else 0,
        'prediction_max_proba': float(max_proba),
        'prediction_max_class': 1 if max_proba > 0.5 else 0,
        'individual_predictions': individual_predictions
    }
    
    return aggregated_result


def evaluate_on_test_data(model: Any, test_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluate model on test data with daily aggregation.
    
    Args:
        model: Trained model pipeline
        test_data: Test data in tall format
        
    Returns:
        Dictionary with evaluation results
    """
    from src.train import aggregate_daily_predictions, evaluate_daily_aggregation
    
    # Make predictions on test data
    X_test = test_data.drop('vol_up', axis=1)
    y_test = test_data['vol_up']
    
    # Get predictions
    test_pred_proba = model.predict(X_test)
    test_pred = (test_pred_proba > 0.5).astype(int)
    
    # Add predictions to test data
    test_with_pred = test_data.copy()
    test_with_pred['prediction'] = test_pred
    test_with_pred['prediction_proba'] = test_pred_proba
    
    # Aggregate by day
    daily_results = aggregate_daily_predictions(test_with_pred)
    
    # Calculate metrics
    daily_metrics = evaluate_daily_aggregation(daily_results)
    
    # Headline-level metrics
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    headline_metrics = {
        'accuracy': accuracy_score(y_test, test_pred),
        'f1_score': f1_score(y_test, test_pred),
        'roc_auc': roc_auc_score(y_test, test_pred_proba)
    }
    
    return {
        'headline_metrics': headline_metrics,
        'daily_metrics': daily_metrics,
        'daily_predictions': daily_results,
        'num_test_days': len(daily_results),
        'num_test_headlines': len(test_data)
    }
