.PHONY: setup test lint clean up down logs install-hooks flows

# Development setup
setup:
	pipenv install --dev

install-hooks:
	pipenv run pre-commit install
	pipenv run pre-commit install --hook-type pre-push

# Testing
test:
	pipenv run pytest tests/ -v

test-unit:
	pipenv run pytest tests/unit/ -v

test-integration:
	pipenv run pytest tests/integration/ -v

# Code quality
lint:
	pipenv run black src/ flows/ tests/
	pipenv run isort src/ flows/ tests/
	pipenv run pylint src/ flows/ tests/ --disable=C0114,C0116,R0903,W0613

format:
	pipenv run black src/ flows/ tests/
	pipenv run isort src/ flows/ tests/

check:
	pipenv run black --check src/ flows/ tests/
	pipenv run isort --check-only src/ flows/ tests/
	pipenv run flake8 src/ flows/ tests/ --max-line-length=100

# Infrastructure
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

# Web Service
web-service:
	cd webservice && python main.py

web-service-dev:
	cd webservice && uvicorn main:app --reload --host 0.0.0.0 --port 8000

web-service-build:
	docker build -f webservice/Dockerfile -t volatility-webservice .

web-service-run:
	docker run -p 8000:8000 --env-file .env volatility-webservice

web-service-test:
	pipenv run pytest tests/integration/test_webservice.py -v

# UI endpoints
ui-links:
	@echo "🌐 Available UIs:"
	@echo "  MLflow:        http://localhost:5000"
	@echo "  Prefect:       http://localhost:4200"  
	@echo "  Grafana:       http://localhost:3000 (admin/admin)"
	@echo "  S3 Browser:    http://localhost:8090"
	@echo "  Web Service:   http://localhost:8000/docs"
	@echo "  Evidently:     http://localhost:8001"
	@echo "  Adminer:       http://localhost:8080"

# MLflow and Prefect
mlflow-ui:
	@echo "MLflow UI: http://localhost:5000"

prefect-ui:
	@echo "Prefect UI: http://localhost:4200"

grafana-ui:
	@echo "Grafana UI: http://localhost:3000 (admin/admin)"

# Run flows locally
flows: preprocess-flow training-flow scoring-flow monitoring-flow

preprocess-flow:
	pipenv run python flows/preprocess_flow.py

training-flow:
	pipenv run python flows/training_flow.py

scoring-flow:
	pipenv run python flows/scoring_flow.py

monitoring-flow:
	pipenv run python flows/monitoring_flow.py

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete

clean-data:
	rm -rf data/predictions/* 2>/dev/null || true
	rm -rf mlruns/ 2>/dev/null || true

# Project info
status:
	@echo "🚀 MLOps Volatility News Predictor"
	@echo "=================================="
	@echo "📊 Services:"
	@echo "   - MLflow UI:  http://localhost:5000"
	@echo "   - Prefect UI: http://localhost:4200"
	@echo "   - Grafana:    http://localhost:3000"
	@echo "   - Adminer:    http://localhost:8080"
	@echo ""
	@echo "📁 Project structure:"
	@echo "   - src/: Core ML logic"
	@echo "   - flows/: Prefect workflows"
	@echo "   - tests/: Unit & integration tests"
	@echo "   - data/: Processed datasets ready to use"
	@echo ""
	@echo "🔧 Commands:"
	@echo "   make up          - Start all services"
	@echo "   make flows       - Run all flows locally"
	@echo "   make test        - Run all tests"
	@echo "   make lint        - Format and lint code"

help:
	@echo "Available commands:"
	@echo "  setup            Install dependencies"
	@echo "  install-hooks    Install pre-commit hooks"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  lint             Format and lint code"
	@echo "  format           Format code only"
	@echo "  check            Check code formatting"
	@echo "  up               Start Docker services"
	@echo "  down             Stop Docker services"
	@echo "  logs             Show Docker logs"
	@echo "  restart          Restart Docker services"
	@echo "  flows            Run all flows locally"
	@echo "  preprocess-flow  Run data preprocessing"
	@echo "  training-flow    Run model training"
	@echo "  scoring-flow     Run daily scoring"
	@echo "  monitoring-flow  Run monitoring"
	@echo "  clean            Clean Python cache files"
	@echo "  clean-data       Clean generated data files"
	@echo "  status           Show project overview"
	@echo "  help             Show this help message"
