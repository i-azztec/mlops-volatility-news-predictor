"""
Simple test web service for volatility prediction - DEMO VERSION
This version works without MLflow connection for testing purposes.
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Volatility Prediction API - DEMO",
    description="Demo version: Predict DJIA volatility direction based on news headlines",
    version="1.0.0-demo",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
    model_version: str = Field(description="Model version used")
    prediction_timestamp: str = Field(description="ISO timestamp of prediction")
    processing_time_ms: float = Field(description="Prediction processing time in milliseconds")

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    model_version: str = None
    uptime_seconds: float
    demo_mode: bool = True

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

def demo_predict(headline: str) -> float:
    """
    Demo prediction function - generates realistic probabilities
    based on sentiment keywords in headlines.
    """
    headline = headline.lower()
    
    # Positive keywords (high volatility probability)
    positive_keywords = ['rally', 'surge', 'soar', 'boom', 'growth', 'rise', 'gains', 'breakthrough']
    # Negative keywords (high volatility probability) 
    negative_keywords = ['crash', 'plummet', 'decline', 'fall', 'crisis', 'recession', 'drop', 'fears']
    # Neutral keywords (low volatility probability)
    neutral_keywords = ['maintain', 'stable', 'steady', 'unchanged', 'holds']
    
    base_prob = 0.5  # Start with neutral
    
    # Check for keywords
    for word in positive_keywords:
        if word in headline:
            base_prob += 0.15
    
    for word in negative_keywords:
        if word in headline:
            base_prob += 0.15
            
    for word in neutral_keywords:
        if word in headline:
            base_prob -= 0.1
    
    # Add some randomness
    base_prob += random.uniform(-0.1, 0.1)
    
    # Ensure probability is between 0 and 1
    return max(0.0, min(1.0, base_prob))

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    uptime = (datetime.now() - app_start_time).total_seconds()
    
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_version="demo-v1.0",
        uptime_seconds=uptime,
        demo_mode=True
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_volatility(request: PredictionRequest):
    """
    Predict volatility direction for a single news headline.
    DEMO VERSION - Uses rule-based prediction instead of ML model.
    """
    start_time = datetime.now()
    
    try:
        # Make demo prediction
        probability = demo_predict(request.headline)
        
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
            model_version="demo-v1.0",
            prediction_timestamp=datetime.now().isoformat(),
            processing_time_ms=round(processing_time, 2)
        )
        
        logger.info(f"Demo prediction: {probability:.4f} for headline: {request.headline[:50]}...")
        return response
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/predict/batch")
async def predict_batch(headlines: list[str]):
    """
    Predict volatility for multiple headlines and aggregate results.
    DEMO VERSION.
    """
    try:
        predictions = []
        probabilities = []
        
        for headline in headlines:
            prob = demo_predict(headline)
            predictions.append(1 if prob >= 0.5 else 0)
            probabilities.append(prob)
        
        # Calculate aggregated results
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
            "model_version": "demo-v1.0",
            "demo_mode": True
        }
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")

@app.get("/demo/examples")
async def get_demo_examples():
    """Get example headlines for testing."""
    return {
        "positive_examples": [
            "Stock market rallies on strong earnings reports",
            "Tech stocks surge following breakthrough AI announcement",
            "Corporate earnings exceed expectations across all sectors"
        ],
        "negative_examples": [
            "Market crash fears as inflation reaches new highs",
            "Economic recession fears grow as GDP contracts",
            "Oil prices plummet amid global oversupply concerns"
        ],
        "neutral_examples": [
            "Federal Reserve maintains current interest rates",
            "Market holds steady amid mixed economic signals",
            "Trading volume remains unchanged from previous session"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Demo Volatility Prediction API...")
    logger.info("Note: This is a DEMO version with rule-based predictions")
    
    uvicorn.run(
        "demo_webservice:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
