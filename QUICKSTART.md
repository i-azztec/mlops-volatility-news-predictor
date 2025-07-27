# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### 1. Setup Environment
```bash
# Clone and enter directory
cd mlops-volatility-news-predictor

# Copy environment file
cp .env.example .env

# Install dependencies
make setup
```

### 2. Start Infrastructure
```bash
# Start all services
make up

# Check status
make status
```

### 3. Run the Pipeline
```bash
# 1. Prepare data (run once)
make preprocess-flow

# 2. Train model
make training-flow

# 3. Promote model to Production
# Go to http://localhost:5000 → Models → volatility-classifier
# Select latest version → Transition to "Production"

# 4. Run scoring
make scoring-flow

# 5. Run monitoring  
make monitoring-flow
```

### 4. Access Dashboards
- **MLflow UI:** http://localhost:5000
- **Prefect UI:** http://localhost:4200  
- **Grafana:** http://localhost:3000 (admin/admin)
- **Database:** http://localhost:8080 (adminer)

## 📊 What You'll See

1. **MLflow**: Models, experiments, metrics tracking
2. **Prefect**: Workflow runs and scheduling
3. **Grafana**: Model performance monitoring
4. **S3 (LocalStack)**: Data storage simulation

## 🔧 Commands

```bash
make help          # See all commands
make test          # Run tests
make lint          # Format code
make logs          # View service logs
make down          # Stop services
```

## 📁 Key Files

- `src/` - ML logic (train, predict, preprocess)
- `flows/` - Prefect workflows
- `data/processed/` - Ready datasets (48k samples)
- `tests/` - Unit & integration tests

## 🎯 Expected Results

- **Model Accuracy:** ~52-54% (realistic for volatility)
- **Training Time:** ~2-5 minutes
- **Daily Predictions:** Saved to S3
- **Monitoring:** Weekly drift reports

## ❓ Troubleshooting

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
