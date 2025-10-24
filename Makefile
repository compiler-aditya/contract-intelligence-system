.PHONY: up down build logs test clean

# Start services
up:
	docker-compose up -d

# Stop services
down:
	docker-compose down

# Build containers
build:
	docker-compose build

# View logs
logs:
	docker-compose logs -f app

# Run tests
test:
	docker-compose exec app pytest tests/ -v --cov=app

# Clean up
clean:
	docker-compose down -v
	rm -rf data/

# Database migrations
migrate:
	docker-compose exec app alembic upgrade head

# Create new migration
migration:
	docker-compose exec app alembic revision --autogenerate -m "$(name)"

# Shell access
shell:
	docker-compose exec app /bin/bash

# Install dependencies locally (for IDE)
install:
	pip install -r requirements.txt
