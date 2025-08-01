"""
FastAPI Web Service for Single News Headline Volatility Prediction

Stage 2: Web Service that provides REST API for real-time volatility predictions
based on individual news headlines using the production model from MLflow.
"""

import os
import sys
import pickle
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from src.predict import predict_one, load_production_model
from src.utils import setup_s3_client

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Volatility Prediction API",
    description="Predict DJIA volatility direction based on news headlines",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global variables for model caching
model_cache = {
    "model": None,
    "vectorizer": None, 
    "version": None,
    "loaded_at": None
}

class PredictionRequest(BaseModel):
    """Request model for single news headline prediction."""
    headline: str = Field(
        ..., 
        description="News headline text to analyze",
        example="Fed announces interest rate hike amid inflation concerns"
    )

class PredictionResponse(BaseModel):
    """Response model with multiple prediction methods."""
    headline: str = Field(description="Original headline text")
    prediction_probability: float = Field(description="Probability of volatility increase (0-1)")
    prediction_class: int = Field(description="Binary prediction (0=decrease, 1=increase)")
    confidence_level: str = Field(description="High/Medium/Low confidence based on probability")
    model_version: str = Field(description="MLflow model version used")
    prediction_timestamp: str = Field(description="ISO timestamp of prediction")
    processing_time_ms: float = Field(description="Prediction processing time in milliseconds")

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    model_version: str = None
    uptime_seconds: float

# App startup time for uptime calculation
app_start_time = datetime.now()

def get_confidence_level(probability: float) -> str:
    """Determine confidence level based on prediction probability."""
    if probability >= 0.7 or probability <= 0.3:
        return "High"
    elif probability >= 0.6 or probability <= 0.4:
        return "Medium"
    else:
        return "Low"

@app.on_event("startup")
async def startup_event():
    """Load the production model on app startup."""
    try:
        logger.info("Starting Volatility Prediction API...")
        
        # Setup MLflow connection
        mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        mlflow.set_tracking_uri(mlflow_uri)
        logger.info(f"Connected to MLflow at {mlflow_uri}")
        
        # Load production model
        await reload_model()
        
        logger.info("API startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}")
        raise e

async def reload_model():
    """Load or reload the production model from MLflow."""
    try:
        logger.info("Loading production model from MLflow...")
        
        model, vectorizer, version = load_production_model()
        
        # Cache the model
        model_cache.update({
            "model": model,
            "vectorizer": vectorizer,
            "version": version,
            "loaded_at": datetime.now()
        })
        
        logger.info(f"Successfully loaded model version {version}")
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise e

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = (datetime.now() - app_start_time).total_seconds()
    
    return HealthResponse(
        status="healthy" if model_cache["model"] is not None else "unhealthy",
        model_loaded=model_cache["model"] is not None,
        model_version=model_cache["version"],
        uptime_seconds=uptime
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_volatility(request: PredictionRequest):
    """
    Predict volatility direction for a single news headline.
    
    Returns prediction with probability, binary class, and confidence level.
    """
    start_time = datetime.now()
    
    try:
        # Check if model is loaded
        if model_cache["model"] is None:
            logger.warning("Model not loaded, attempting to reload...")
            await reload_model()
            
            if model_cache["model"] is None:
                raise HTTPException(
                    status_code=503, 
                    detail="Model not available. Please try again later."
                )
        
        # Make prediction
        probability = predict_one(
            headline=request.headline,
            model=model_cache["model"],
            vectorizer=model_cache["vectorizer"]
        )
        
        # Convert to binary prediction
        binary_prediction = 1 if probability >= 0.5 else 0
        
        # Calculate confidence level
        confidence = get_confidence_level(probability)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Create response
        response = PredictionResponse(
            headline=request.headline,
            prediction_probability=round(probability, 4),
            prediction_class=binary_prediction,
            confidence_level=confidence,
            model_version=model_cache["version"],
            prediction_timestamp=datetime.now().isoformat(),
            processing_time_ms=round(processing_time, 2)
        )
        
        logger.info(f"Prediction completed: {probability:.4f} (class: {binary_prediction})")
        return response
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/batch")
async def predict_batch(headlines: list[str]):
    """
    Predict volatility for multiple headlines and aggregate results.
    
    This simulates the daily batch processing for multiple headlines.
    """
    try:
        if model_cache["model"] is None:
            await reload_model()
        
        predictions = []
        probabilities = []
        
        for headline in headlines:
            prob = predict_one(
                headline=headline,
                model=model_cache["model"],
                vectorizer=model_cache["vectorizer"]
            )
            predictions.append(1 if prob >= 0.5 else 0)
            probabilities.append(prob)
        
        # Calculate aggregated results (like in scoring_flow)
        mean_probability = sum(probabilities) / len(probabilities)
        majority_vote = 1 if sum(predictions) > len(predictions) / 2 else 0
        max_prob_idx = probabilities.index(max(probabilities))
        max_prob_class = predictions[max_prob_idx]
        max_prob_value = probabilities[max_prob_idx]
        
        return {
            "headlines_count": len(headlines),
            "individual_predictions": predictions,
            "individual_probabilities": [round(p, 4) for p in probabilities],
            "aggregated_results": {
                "mean_probability": round(mean_probability, 4),
                "mean_prediction": 1 if mean_probability >= 0.5 else 0,
                "majority_vote": majority_vote,
                "max_prob_class": max_prob_class,
                "max_prob_value": round(max_prob_value, 4)
            },
            "model_version": model_cache["version"]
        }
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@app.post("/model/reload")
async def reload_model_endpoint():
    """Manually reload the production model from MLflow."""
    try:
        await reload_model()
        return {
            "message": "Model reloaded successfully",
            "version": model_cache["version"],
            "reloaded_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Model reload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model reload failed: {str(e)}")

@app.get("/model/info")
async def get_model_info():
    """Get information about the currently loaded model."""
    if model_cache["model"] is None:
        return {"message": "No model loaded"}
    
    return {
        "version": model_cache["version"],
        "loaded_at": model_cache["loaded_at"].isoformat() if model_cache["loaded_at"] else None,
        "model_type": str(type(model_cache["model"]).__name__),
        "vectorizer_type": str(type(model_cache["vectorizer"]).__name__)
    }

# Custom exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
