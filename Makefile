.PHONY: setup seed test test-cov api dashboard slack-mock smoke docker-up docker-down clean

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

seed:
	$(PYTHON) scripts/seed_data.py

reset-data:
	$(PYTHON) scripts/seed_data.py --reset

test:
	$(PYTEST) -v

test-cov:
	$(PYTEST) --cov=app --cov-report=term-missing

api:
	$(UVICORN) app.main:app --reload --port 8000

dashboard:
	$(STREAMLIT) run dashboard/app.py --server.port 8501

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
