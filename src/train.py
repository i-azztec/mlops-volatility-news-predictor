"""
Model training and hyperparameter optimization.
"""

import os
import mlflow
import mlflow.xgboost
import mlflow.sklearn
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Any
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report
from xgboost import XGBClassifier
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
import pickle


def create_model_pipeline(max_features: int = 1000, 
                         ngram_range: Tuple[int, int] = (1, 2),
                         xgb_params: Dict[str, Any] = None) -> Pipeline:
    """
    Create sklearn pipeline with text preprocessing and XGBoost classifier.
    
    Args:
        max_features: Maximum number of TF-IDF features
        ngram_range: N-gram range for text vectorization
        xgb_params: XGBoost parameters
        
    Returns:
        Configured sklearn pipeline
    """
    if xgb_params is None:
        xgb_params = {
            'eval_metric': 'logloss',
            'random_state': 42,
            'max_depth': 6,
            'n_estimators': 100
        }
    
    # Text processing pipeline
    text_features = Pipeline([
        ('vectorizer', CountVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words='english'
        )),
        ('tfidf', TfidfTransformer())
    ])
    
    # Get numeric feature names (will be set during fit)
    numeric_features = 'passthrough'
    
    # Combined preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('text', text_features, 'Headline'),
            ('num', numeric_features, slice(3, None))  # All columns except Date, Headline, vol_up
        ])
    
    # Full pipeline
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', XGBClassifier(**xgb_params))
    ])
    
    return pipeline


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, list]:
    """
    Prepare features and target from tall format data.
    
    Args:
        df: DataFrame in tall format
        
    Returns:
        Tuple of (features_df, target_series, numeric_feature_names)
    """
    # Get numeric feature columns (exclude Date, Headline, vol_up)
    numeric_features = [col for col in df.columns 
                       if col not in ['Date', 'Headline', 'vol_up']]
    
    # Prepare features (all columns except vol_up)
    features = df[['Date', 'Headline'] + numeric_features].copy()
    
    # Target
    target = df['vol_up'].copy()
    
    return features, target, numeric_features


def evaluate_model(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    """
    Evaluate model and return metrics.
    
    Args:
        model: Trained model pipeline
        X_test: Test features
        y_test: Test target
        
    Returns:
        Dictionary with evaluation metrics
    """
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1_score': f1_score(y_test, y_pred),
        'roc_auc': roc_auc_score(y_test, y_proba)
    }
    
    return metrics


def aggregate_daily_predictions(df_with_predictions: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate predictions by date using multiple methods.
    
    Args:
        df_with_predictions: DataFrame with Date, vol_up, and prediction columns
        
    Returns:
        DataFrame aggregated by date with different aggregation methods
    """
    # Group by date
    daily_results = []
    
    for date, group in df_with_predictions.groupby('Date'):
        true_label = group['vol_up'].iloc[0]  # Same for all headlines of the day
        probs = group['prediction_proba'].values
        preds = group['prediction'].values
        
        # Aggregation methods
        result = {
            'Date': date,
            'true_vol_up': true_label,
            'prediction_mean_proba': np.mean(probs),
            'prediction_mean_class': 1 if np.mean(probs) > 0.5 else 0,
            'prediction_majority_vote': 1 if np.sum(preds) >= len(preds)/2 else 0,
            'prediction_max_proba': np.max(probs),
            'prediction_max_class': 1 if np.max(probs) > 0.5 else 0,
            'num_headlines': len(group)
        }
        daily_results.append(result)
    
    return pd.DataFrame(daily_results)


def evaluate_daily_aggregation(daily_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Evaluate different aggregation methods on daily level.
    
    Args:
        daily_df: DataFrame with daily aggregated predictions
        
    Returns:
        Dictionary with metrics for each aggregation method
    """
    methods = {
        'mean_proba': ('prediction_mean_class', 'prediction_mean_proba'),
        'majority_vote': ('prediction_majority_vote', None),
        'max_proba': ('prediction_max_class', 'prediction_max_proba')
    }
    
    results = {}
    
    for method_name, (pred_col, proba_col) in methods.items():
        metrics = {
            'accuracy': accuracy_score(daily_df['true_vol_up'], daily_df[pred_col]),
            'f1_score': f1_score(daily_df['true_vol_up'], daily_df[pred_col])
        }
        
        if proba_col:
            metrics['roc_auc'] = roc_auc_score(daily_df['true_vol_up'], daily_df[proba_col])
        
        results[method_name] = metrics
    
    return results


def objective_function(params: Dict[str, Any], X_train: pd.DataFrame, y_train: pd.Series, 
                      X_val: pd.DataFrame, y_val: pd.Series) -> Dict[str, Any]:
    """
    Objective function for hyperopt optimization.
    
    Args:
        params: Hyperparameters to optimize
        X_train: Training features
        y_train: Training target
        X_val: Validation features
        y_val: Validation target
        
    Returns:
        Dictionary with loss and status for hyperopt
    """
    # Convert hyperopt params to model params
    xgb_params = {
        'eval_metric': 'logloss',
        'random_state': 42,
        'max_depth': int(params['max_depth']),
        'n_estimators': int(params['n_estimators']),
        'learning_rate': params['learning_rate'],
        'subsample': params['subsample'],
        'colsample_bytree': params['colsample_bytree']
    }
    
    # Create and train model
    model = create_model_pipeline(
        max_features=int(params['max_features']),
        ngram_range=(1, int(params['max_ngram'])),
        xgb_params=xgb_params
    )
    
    try:
        # Train model
        model.fit(X_train, y_train)
        
        # Get validation predictions
        val_pred_proba = model.predict_proba(X_val)[:, 1]
        val_pred = model.predict(X_val)
        
        # Add predictions to validation data for aggregation
        X_val_with_pred = X_val.copy()
        X_val_with_pred['vol_up'] = y_val
        X_val_with_pred['prediction'] = val_pred
        X_val_with_pred['prediction_proba'] = val_pred_proba
        
        # Aggregate by day
        daily_results = aggregate_daily_predictions(X_val_with_pred)
        
        # Calculate daily metrics
        daily_metrics = evaluate_daily_aggregation(daily_results)
        
        # Use mean_proba method for optimization (most stable)
        auc_score = daily_metrics['mean_proba']['roc_auc']
        
        # Log to MLflow
        with mlflow.start_run(nested=True):
            # Log parameters
            mlflow.log_params(params)
            
            # Log headline-level metrics
            headline_metrics = evaluate_model(model, X_val, y_val)
            for name, value in headline_metrics.items():
                mlflow.log_metric(f"headline_{name}", value)
            
            # Log daily aggregated metrics
            for method, metrics in daily_metrics.items():
                for metric_name, value in metrics.items():
                    mlflow.log_metric(f"daily_{method}_{metric_name}", value)
            
            # Primary metric for optimization
            mlflow.log_metric("optimization_metric", auc_score)
        
        # Return negative AUC because hyperopt minimizes
        return {'loss': -auc_score, 'status': STATUS_OK}
        
    except Exception as e:
        print(f"Error in objective function: {e}")
        return {'loss': 0, 'status': STATUS_OK}


def find_best_model(X_train: pd.DataFrame, y_train: pd.Series,
                   X_val: pd.DataFrame, y_val: pd.Series,
                   max_evals: int = 50) -> Tuple[Pipeline, Dict[str, Any]]:
    """
    Find best model using hyperparameter optimization.
    
    Args:
        X_train: Training features
        y_train: Training target
        X_val: Validation features
        y_val: Validation target
        max_evals: Maximum number of evaluations for hyperopt
        
    Returns:
        Tuple of (best_model, best_params)
    """
    # Define search space
    space = {
        'max_features': hp.choice('max_features', [500, 800, 1000, 1500]),
        'max_ngram': hp.choice('max_ngram', [1, 2]),
        'max_depth': hp.choice('max_depth', [3, 4, 5, 6, 7]),
        'n_estimators': hp.choice('n_estimators', [50, 100, 150, 200]),
        'learning_rate': hp.uniform('learning_rate', 0.01, 0.3),
        'subsample': hp.uniform('subsample', 0.6, 1.0),
        'colsample_bytree': hp.uniform('colsample_bytree', 0.6, 1.0)
    }
    
    # Run optimization
    trials = Trials()
    
    best = fmin(
        fn=lambda params: objective_function(params, X_train, y_train, X_val, y_val),
        space=space,
        algo=tpe.suggest,
        max_evals=max_evals,
        trials=trials,
        verbose=True
    )
    
    # Convert best params back to actual values
    best_params = {
        'max_features': [500, 800, 1000, 1500][best['max_features']],
        'max_ngram': [1, 2][best['max_ngram']],
        'max_depth': [3, 4, 5, 6, 7][best['max_depth']],
        'n_estimators': [50, 100, 150, 200][best['n_estimators']],
        'learning_rate': best['learning_rate'],
        'subsample': best['subsample'],
        'colsample_bytree': best['colsample_bytree']
    }
    
    # Train final model with best params
    xgb_params = {
        'eval_metric': 'logloss',
        'random_state': 42,
        'max_depth': best_params['max_depth'],
        'n_estimators': best_params['n_estimators'],
        'learning_rate': best_params['learning_rate'],
        'subsample': best_params['subsample'],
        'colsample_bytree': best_params['colsample_bytree']
    }
    
    best_model = create_model_pipeline(
        max_features=best_params['max_features'],
        ngram_range=(1, best_params['max_ngram']),
        xgb_params=xgb_params
    )
    
    # Train on full training data
    best_model.fit(X_train, y_train)
    
    return best_model, best_params
