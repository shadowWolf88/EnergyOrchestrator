.PHONY: help install test lint format run clean

help:
	@echo "AI Energy Orchestrator - Development Commands"
	@echo "=============================================="
	@echo "make install        Install dependencies"
	@echo "make test           Run all tests"
	@echo "make test-cov       Run tests with coverage"
	@echo "make lint           Run linters (ruff, mypy)"
	@echo "make format         Format code (black, isort)"
	@echo "make run            Run main simulation"
	@echo "make run-quick      Run quick 5-minute test"
	@echo "make clean          Clean build artifacts"

install:
	pip install -e .

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=energy_orchestrator_sim --cov-report=html

lint:
	ruff check energy_orchestrator_sim tests
	mypy energy_orchestrator_sim --ignore-missing-imports

format:
	black energy_orchestrator_sim tests
	isort energy_orchestrator_sim tests

run:
	python main.py --homes 50 --days 30

run-quick:
	python main.py --homes 10 --days 3 --seed 42

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage htmlcov/
	rm -f simulation_results_*.csv
