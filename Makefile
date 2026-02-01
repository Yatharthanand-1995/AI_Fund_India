.PHONY: help install dev-install test test-fast test-cov clean lint format run docs

# Default target
.DEFAULT_GOAL := help

help:  ## Show this help message
	@echo "AI Hedge Fund India - Makefile Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

dev-install:  ## Install all dependencies including dev tools
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-asyncio black ruff mypy

setup:  ## Run the setup script
	./setup.sh

test:  ## Run all tests with coverage
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

test-fast:  ## Run fast tests only (skip integration tests)
	pytest tests/ -v -m "not slow"

test-unit:  ## Run unit tests only
	pytest tests/ -v -m "unit"

test-integration:  ## Run integration tests only
	pytest tests/ -v -m "integration"

test-cov:  ## Generate coverage report and open in browser
	pytest tests/ --cov=. --cov-report=html
	open htmlcov/index.html || xdg-open htmlcov/index.html

lint:  ## Run code linters (ruff and mypy)
	@echo "Running ruff..."
	ruff check .
	@echo "Running mypy..."
	mypy . --exclude venv --exclude frontend

format:  ## Format code with black and ruff
	@echo "Running black..."
	black .
	@echo "Running ruff --fix..."
	ruff check . --fix

format-check:  ## Check code formatting without making changes
	black --check .
	ruff check .

clean:  ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf htmlcov/ .coverage build/ dist/

run:  ## Start the API server
	python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

run-api:  ## Alias for run
	$(MAKE) run

run-prod:  ## Start the API server in production mode (no reload)
	python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4

test-api:  ## Test all API endpoints
	python scripts/test_api.py

logs:  ## Tail application logs
	tail -f logs/app.log

logs-error:  ## Tail error logs
	tail -f logs/error.log

logs-daily:  ## Tail daily logs
	tail -f logs/daily.log

analyze-logs:  ## Analyze application logs
	python scripts/analyze_logs.py

analyze-logs-json:  ## Analyze logs (JSON output)
	python scripts/analyze_logs.py --json

analyze-errors:  ## Analyze errors only
	python scripts/analyze_logs.py --errors-only

monitor:  ## Start real-time monitoring dashboard
	python scripts/monitor_system.py

metrics:  ## View current metrics
	curl "http://localhost:8000/metrics" | jq .

metrics-summary:  ## View metrics summary
	curl "http://localhost:8000/metrics/summary" | jq .

env:  ## Create .env file from template
	cp .env.example .env
	@echo "✅ .env file created. Please edit it and add your API keys."

docker-build:  ## Build Docker image
	docker build -t ai-hedge-fund-india:latest .

docker-run:  ## Run Docker container
	docker run -p 8000:8000 --env-file .env ai-hedge-fund-india:latest

docker-compose-up:  ## Start all services with docker-compose
	docker-compose up -d

docker-compose-down:  ## Stop all services
	docker-compose down

docker-compose-logs:  ## Show docker-compose logs
	docker-compose logs -f

# Analysis commands
analyze:  ## Analyze a stock (usage: make analyze SYMBOL=TCS)
	@if [ -z "$(SYMBOL)" ]; then \
		echo "Usage: make analyze SYMBOL=TCS"; \
	else \
		curl -X POST "http://localhost:8000/analyze" \
			-H "Content-Type: application/json" \
			-d '{"symbol": "$(SYMBOL)"}' | jq .; \
	fi

top-picks:  ## Get top picks from NIFTY 50
	curl "http://localhost:8000/portfolio/top-picks" | jq .

health:  ## Check API health
	curl "http://localhost:8000/health" | jq .

regime:  ## Check current market regime
	curl "http://localhost:8000/market/regime" | jq .

universe:  ## View stock universe
	curl "http://localhost:8000/stocks/universe" | jq .

# Stock Universe Explorer
explore:  ## Explore stock universe interactively
	python scripts/explore_universe.py

universe-stats:  ## Show universe statistics
	python scripts/explore_universe.py indices

stock-info:  ## Get stock info (usage: make stock-info SYMBOL=TCS)
	@if [ -z "$(SYMBOL)" ]; then \
		echo "Usage: make stock-info SYMBOL=TCS"; \
	else \
		python scripts/explore_universe.py stock $(SYMBOL); \
	fi

search-stocks:  ## Search stocks (usage: make search-stocks QUERY=tata)
	@if [ -z "$(QUERY)" ]; then \
		echo "Usage: make search-stocks QUERY=tata"; \
	else \
		python scripts/explore_universe.py search $(QUERY); \
	fi

# Development
shell:  ## Start IPython shell with project context
	ipython

notebook:  ## Start Jupyter notebook
	jupyter notebook

# Frontend
frontend-install:  ## Install frontend dependencies
	cd frontend && npm install

frontend-dev:  ## Start frontend dev server
	cd frontend && npm run dev

frontend-build:  ## Build frontend for production
	cd frontend && npm run build

frontend-preview:  ## Preview production build
	cd frontend && npm run preview

frontend-lint:  ## Lint frontend code
	cd frontend && npm run lint

# Git helpers
git-status:  ## Show git status
	git status

git-diff:  ## Show git diff
	git diff

# Info
version:  ## Show Python and package versions
	@echo "Python version:"
	@python --version
	@echo ""
	@echo "Key package versions:"
	@pip show pandas numpy fastapi yfinance | grep -E "Name|Version"

tree:  ## Show project directory tree
	tree -I 'venv|__pycache__|*.pyc|.git|node_modules|htmlcov|.pytest_cache' -L 3
