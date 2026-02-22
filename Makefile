# Makefile for Voice-Managed Inventory System
# Simplifies common Docker and deployment commands

.PHONY: help dev prod build up down logs clean test deploy

# Default target
help:
	@echo "════════════════════════════════════════════════════════"
	@echo "  Voice-Managed Inventory System - Make Commands"
	@echo "════════════════════════════════════════════════════════"
	@echo ""
	@echo "Local Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start services"
	@echo "  make down         - Stop services"
	@echo "  make logs         - View logs (all services)"
	@echo "  make logs-api     - View API logs"
	@echo "  make logs-dash    - View dashboard logs"
	@echo "  make restart      - Restart all services"
	@echo "  make clean        - Stop and remove all containers/volumes"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-build   - Build production images"
	@echo "  make prod-up      - Start production services"
	@echo "  make prod-down    - Stop production services"
	@echo "  make prod-logs    - View production logs"
	@echo "  make deploy       - Deploy to production"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linting"
	@echo "  make format       - Format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init      - Initialize database"
	@echo "  make db-backup    - Backup database"
	@echo ""
	@echo "Utilities:"
	@echo "  make shell        - Open shell in API container"
	@echo "  make health       - Check application health"
	@echo "  make ps           - Show running containers"
	@echo ""

# Development commands
dev: build up-dev

build:
	@echo "🔨 Building Docker images..."
	docker compose -f docker/docker-compose.yml build

up:
	@echo "🚀 Starting development services..."
	docker compose -f docker/docker-compose.yml up -d
	@echo "✅ Services started!"
	@echo "📱 API: http://localhost:8000"
	@echo "🎨 Dashboard: http://localhost:8501"

up-dev:
	@echo "🚀 Starting development services with ngrok..."
	docker compose -f docker/docker-compose.yml --profile dev up -d
	@echo ""
	@echo "⏳ Waiting for webhook setup..."
	@sleep 5
	@echo ""
	@echo "✅ Development environment started!"
	@echo ""
	@echo "📱 API: http://localhost:8000"
	@echo "🎨 Dashboard: http://localhost:8501"
	@echo "🌐 ngrok Dashboard: http://localhost:4040"
	@echo ""
	@echo "Check webhook setup logs:"
	@echo "  docker logs inventory-webhook-setup"
	@echo ""

down:
	@echo "🛑 Stopping services..."
	docker compose -f docker/docker-compose.yml down

logs:
	docker compose -f docker/docker-compose.yml logs -f

logs-api:
	docker compose -f docker/docker-compose.yml logs -f api

logs-dash:
	docker compose -f docker/docker-compose.yml logs -f dashboard

restart:
	@echo "🔄 Restarting services..."
	docker compose -f docker/docker-compose.yml restart

clean:
	@echo "🧹 Cleaning up..."
	docker compose -f docker/docker-compose.yml down -v
	docker system prune -f

# Production commands
prod: prod-build prod-up

prod-build:
	@echo "🔨 Building production images..."
	docker compose -f docker/docker-compose.prod.yml build --no-cache

prod-up:
	@echo "🚀 Starting production services..."
	docker compose -f docker/docker-compose.prod.yml up -d
	@echo "✅ Production services started!"

prod-down:
	@echo "🛑 Stopping production services..."
	docker compose -f docker/docker-compose.prod.yml down

prod-logs:
	docker compose -f docker/docker-compose.prod.yml logs -f

deploy:
	@echo "🚀 Deploying to production..."
	@if [ -f deploy/deploy-prod.sh ]; then \
		chmod +x deploy/deploy-prod.sh && ./deploy/deploy-prod.sh; \
	else \
		echo "❌ deploy/deploy-prod.sh not found"; \
	fi

# Testing & Quality
test:
	@echo "🧪 Running tests..."
	uv run pytest -v

lint:
	@echo "🔍 Running linting..."
	uv run ruff check src/

format:
	@echo "✨ Formatting code..."
	uv run black src/

# Database commands
db-init:
	@echo "🗄️  Initializing database..."
	docker compose -f docker/docker-compose.yml exec api python -c "from src.database.models import init_db; init_db(); print('✅ Database initialized')"

db-backup:
	@echo "💾 Backing up database..."
	@mkdir -p backups
	docker cp inventory-api:/app/data/inventory.db ./backups/inventory-$(shell date +%Y%m%d-%H%M%S).db
	@echo "✅ Backup created in ./backups/"

# Utilities
shell:
	@echo "🐚 Opening shell in API container..."
	docker compose -f docker/docker-compose.yml exec api /bin/bash

health:
	@echo "❤️  Checking application health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Health check failed"

ps:
	@echo "📊 Running containers:"
	docker compose -f docker/docker-compose.yml ps

# Setup commands
setup:
	@echo "⚙️  Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from .env.example"; \
		echo "⚠️  Please edit .env and add your API keys"; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@chmod +x deploy/*.sh
	@echo "✅ Setup complete!"

