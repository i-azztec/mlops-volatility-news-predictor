#!/bin/bash

# Test script for Volatility Prediction Web Service
# Usage: bash test_webservice.sh

API_BASE="http://localhost:8000"

echo "🧪 Testing Volatility Prediction Web Service"
echo "============================================="

# 1. Health Check
echo ""
echo "1️⃣ Testing Health Check..."
curl -s "$API_BASE/health" | jq '.'

# 2. Model Info
echo ""
echo "2️⃣ Testing Model Info..."
curl -s "$API_BASE/model/info" | jq '.'

# 3. Single Prediction - Positive News
echo ""
echo "3️⃣ Testing Single Prediction (Positive News)..."
curl -s -X POST "$API_BASE/predict" \
  -H "Content-Type: application/json" \
  -d '{"headline": "Stock market rallies on strong earnings reports and economic growth"}' | jq '.'

# 4. Single Prediction - Negative News
echo ""
echo "4️⃣ Testing Single Prediction (Negative News)..."
curl -s -X POST "$API_BASE/predict" \
  -H "Content-Type: application/json" \
  -d '{"headline": "Market crash fears as inflation reaches new highs"}' | jq '.'

# 5. Batch Prediction
echo ""
echo "5️⃣ Testing Batch Prediction..."
curl -s -X POST "$API_BASE/predict/batch" \
  -H "Content-Type: application/json" \
  -d '[
    "Federal Reserve announces interest rate hike to combat inflation",
    "Tech stocks surge following breakthrough AI announcement", 
    "Oil prices plummet amid global oversupply concerns",
    "Economic recession fears grow as GDP contracts",
    "Corporate earnings exceed expectations across all sectors"
  ]' | jq '.'

# 6. Model Reload
echo ""
echo "6️⃣ Testing Model Reload..."
curl -s -X POST "$API_BASE/model/reload" | jq '.'

echo ""
echo "✅ All tests completed!"
echo ""
echo "🌐 Visit http://localhost:8000/docs for interactive API documentation"
