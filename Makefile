.PHONY: help build up down logs init-db stop clean

help:
	@echo "E-commerce Analytics Warehouse - Make Commands"
	@echo "=============================================="
	@echo "make build          - Build Docker images"
	@echo "make up             - Start all containers"
	@echo "make down           - Stop all containers"
	@echo "make logs           - View Airflow scheduler logs"
	@echo "make init-db        - Initialize database (runs with docker-compose up)"
	@echo "make clean          - Remove containers and volumes"
	@echo "make test           - Run Python tests"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f airflow-scheduler

init-db:
	docker exec ecomm-postgres psql -U airflow -d ecommerce_warehouse -f /docker-entrypoint-initdb.d/00_schemas.sql

clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

test:
	pytest tests/ -v --cov=src

shell-postgres:
	docker exec -it ecomm-postgres psql -U airflow -d ecommerce_warehouse

shell-airflow:
	docker exec -it ecomm-airflow-webserver bash

reset-airflow:
	docker exec ecomm-airflow-webserver airflow db reset --yes

airflow-ui:
	@echo "Opening Airflow UI at http://localhost:8080"
	@echo "Username: admin"
	@echo "Password: admin"

pgadmin:
	@echo "Opening pgAdmin at http://localhost:5050"
	@echo "Email: admin@example.com"
	@echo "Password: admin"
