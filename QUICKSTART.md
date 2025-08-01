

## 🚀 Quick Start Guide

### Prerequisites:
- Docker Desktop (latest version) + Docker Compose
- Python 3.9+ + pip
- Git for cloning repository
- 4GB RAM minimum for all services

### Setup Instructions:

```bash
# 1. Clone repository
git clone https://github.com/i-azztec/mlops-volatility-news-predictor.git
cd mlops-volatility-news-predictor

# 2. Setup environment
cp .env.example .env
# Edit .env if needed (default values work for local development)

# 3. Install Python dependencies  
pip install pipenv
pipenv install --dev

# 4. Start all infrastructure
make up
# Wait 2-3 minutes for all services to initialize

# 5. Run complete MLOps pipeline
make flows
# This runs: preprocess → training → scoring → monitoring
```

### Access Web Interfaces:

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Prefect UI** | http://localhost:4200 | - | Workflow orchestration & monitoring |
| **MLflow** | http://localhost:5000 | - | ML experiments & model registry |
| **API Docs** | http://localhost:8000/docs | - | Interactive API documentation |
| **Grafana** | http://localhost:3000 | admin/admin | Monitoring dashboards & alerts |
| **Evidently** | http://localhost:8001 | - | ML monitoring reports |  
| **Database** | http://localhost:8080 | user/password | PostgreSQL via Adminer |
| **S3 (LocalStack)** | http://localhost:4566 | - | AWS S3 emulation via LocalStack |

### Test the System:

```bash
# Test single prediction via API
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"headline": "Fed raises interest rates amid inflation concerns"}'

# Check model registry
open http://localhost:5000/#/models/volatility-classifier

# View monitoring metrics  
open http://localhost:3000/d/volatility-monitoring/volatility-model-monitoring

# Run tests
make test
```

## Expected Results

- **Model Accuracy:** ~52-54% (realistic for volatility)
- **Training Time:** ~2-5 minutes
- **Daily Predictions:** Saved to S3
- **Monitoring:** Weekly drift reports

## Troubleshooting

**Docker not found?**
```bash
# Install Docker Desktop and try again
make up
```

**Services not starting?**
```bash
# Check logs
make logs

# Restart services
make restart
```

**Flow fails?**
```bash
# Check if data exists
ls data/processed/

# Run tests
make test
```

Ready to dive deeper? See the full [README.md](README.md) for detailed documentation!
