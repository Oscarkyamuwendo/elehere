.PHONY: help install dev test docker-check docker-dev docker-test build clean

help:
	@echo "🚀 Elehere Development Commands:"
	@echo ""
	@echo "  make install      - Install Python dependencies"
	@echo "  make dev          - Run Flask development server"
	@echo "  make test         - Run Python tests"
	@echo "  make docker-check - Check if Docker is running"
	@echo "  make docker-dev   - Start app with Docker Compose"
	@echo "  make docker-test  - Run tests in Docker"
	@echo "  make build        - Build Docker image"
	@echo "  make clean        - Clean up temporary files"
	@echo "  make stop         - Stop Docker containers"
	@echo "  make logs         - View Docker logs"
	@echo ""

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

dev:
	@echo "🚀 Starting Flask development server..."
	export FLASK_APP=app.py && export FLASK_ENV=development && flask run

test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

docker-check:
	@echo "🔍 Checking Docker..."
	@if ! docker ps > /dev/null 2>&1; then \
		echo "❌ Docker is not running. Please:"; \
		echo "   1. Open Docker Desktop from Applications"; \
		echo "   2. Wait for 'Docker Desktop is running' message"; \
		echo "   3. Try again"; \
		exit 1; \
	else \
		echo "✅ Docker is running"; \
	fi

docker-dev: docker-check
	@echo "🐳 Starting development environment with Docker Compose..."
	docker-compose up --build

docker-test: docker-check
	@echo "🧪 Running tests in Docker..."
	docker-compose -f docker-compose.test.yml up --build --exit-code-from test

build: docker-check
	@echo "🔨 Building Docker image..."
	docker build -t elehere-app .

stop:
	@echo "🛑 Stopping Docker containers..."
	@docker-compose down 2>/dev/null || true

logs:
	@echo "📋 Showing Docker logs..."
	@docker-compose logs -f 2>/dev/null || echo "No containers running"

clean:
	@echo "🧹 Cleaning up..."
	@docker system prune -f 2>/dev/null || true
	@rm -rf __pycache__ .pytest_cache .coverage htmlcov 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

db-shell: docker-check
	@echo "💾 Opening MySQL shell..."
	docker-compose exec db mysql -u user -ppassword elehere_db