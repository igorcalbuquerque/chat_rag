.PHONY: help up down build test test-local lint logs

help:
	@echo "Targets:"
	@echo "  make up       - build and start all services (docker-compose up --build)"
	@echo "  make down     - stop services and remove volumes"
	@echo "  make build    - build all images"
	@echo "  make logs     - tail service logs"
	@echo "  make test     - run backend tests in a container"
	@echo "  make test-local - run backend tests with local Python"

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

lint:
	cd backend && python -m py_compile app/*.py app/**/*.py
