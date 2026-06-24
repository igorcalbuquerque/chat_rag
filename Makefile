.PHONY: help up down build test test-local test-frontend lint logs

help:
	@echo "Targets:"
	@echo "  make up            - build and start all services (docker-compose up --build)"
	@echo "  make down          - stop services and remove volumes"
	@echo "  make build         - build all images"
	@echo "  make logs          - tail service logs"
	@echo "  make test          - run backend tests in a container"
	@echo "  make test-local    - run backend tests with local Python"
	@echo "  make test-frontend - type-check + run frontend tests with coverage"

up:
	docker-compose up --build

down:
	docker-compose down -v

build:
	docker-compose build

logs:
	docker-compose logs -f

# Run the test suite inside a throwaway Python container (no local setup needed).
test:
	docker run --rm -v $(PWD)/backend:/app -w /app python:3.11-slim \
		bash -c "pip install -q -r requirements.txt && pytest"

# Run tests against a local virtualenv (requires `pip install -r requirements.txt`).
test-local:
	cd backend && pytest

# Type-check and run the frontend test suite with coverage (inside a container,
# no local Node needed).
test-frontend:
	docker run --rm -v $(PWD)/frontend:/app -w /app node:20-alpine \
		sh -c "npm ci && npm run typecheck && npm run test:coverage"

lint:
	cd backend && python -m py_compile app/*.py app/**/*.py
