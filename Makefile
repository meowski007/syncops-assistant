.PHONY: setup seed reset-data test test-cov api dashboard frontend frontend-build pipeline train-forecast rag-eval slack-mock smoke docker-up docker-down clean

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn
STREAMLIT ?= .venv/bin/streamlit

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PYTHON) scripts/seed_data.py
	$(PYTHON) -m pipeline.run
	$(PYTHON) -m forecasting.train

seed:
	$(PYTHON) scripts/seed_data.py

reset-data:
	$(PYTHON) scripts/seed_data.py --reset

pipeline:
	$(PYTHON) -m pipeline.run

train-forecast:
	$(PYTHON) -m forecasting.train

rag-eval:
	$(PYTHON) -m evaluation.rag_evaluator

test:
	$(PYTEST) -v

test-cov:
	$(PYTEST) --cov=app --cov=pipeline --cov=forecasting --cov-report=term-missing

api:
	$(UVICORN) app.main:app --reload --port 8000

dashboard:
	$(STREAMLIT) run dashboard/app.py --server.port 8501

frontend:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

slack-mock:
	$(PYTHON) -m app.slack.mock

smoke:
	$(PYTHON) scripts/smoke_test.py

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
