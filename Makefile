SHELL := /bin/bash

.PHONY: help config build up down restart ps logs health ready compile django-check check model-list model-pull django-shell status

help:
	@echo "Available commands:"
	@echo "  make config         Validate Docker Compose configuration"
	@echo "  make build          Build all service images"
	@echo "  make up             Start the complete stack"
	@echo "  make down           Stop containers without deleting volumes"
	@echo "  make restart        Restart the complete stack"
	@echo "  make ps             Show service status"
	@echo "  make logs           Follow service logs"
	@echo "  make health         Check Django and FastAPI health endpoints"
	@echo "  make ready          Check Django and FastAPI readiness endpoints"
	@echo "  make compile        Compile Python files"
	@echo "  make django-check   Run Django system checks"
	@echo "  make check          Run project configuration checks"
	@echo "  make model-list     List models installed inside Ollama"
	@echo "  make model-pull     Pull qwen3:4b inside the Ollama container"
	@echo "  make django-shell   Open a Django shell"
	@echo "  make status         Show Git working-tree status"

config:
	docker compose config

build:
	docker compose build

up:
	docker compose up --build -d
	docker compose ps

down:
	docker compose down

restart:
	docker compose restart
	docker compose ps

ps:
	docker compose ps

logs:
	docker compose logs -f --tail=100

health:
	@echo "Django health:"
	curl -fsS http://localhost:8000/health
	@echo
	@echo "FastAPI health:"
	curl -fsS http://localhost:8001/health
	@echo

ready:
	@echo "Django readiness:"
	curl -fsS http://localhost:8000/ready
	@echo
	@echo "FastAPI readiness:"
	curl -fsS http://localhost:8001/ready
	@echo

compile:
	python -m compileall django_service fastapi_service

django-check:
	docker compose exec -T django python manage.py check

check: compile django-check config
	git diff --check
	@echo "Project checks completed successfully."

model-list:
	docker compose exec -T ollama ollama list

model-pull:
	docker compose exec ollama ollama pull qwen3:4b

django-shell:
	docker compose exec django python manage.py shell

status:
	git status --short
