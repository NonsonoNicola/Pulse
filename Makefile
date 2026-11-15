SHELL := /bin/bash
PY := .venv/bin/python
PIP := .venv/bin/pip
PORT ?= 8000
GROUND_PORT ?= 8001

.PHONY: setup dev backend frontend ground seed demo demo-reset test demo-check rebuild-projections eval clean help

help:
	@echo "Pulse — NASA Space Apps 2026 — research prototype (not a medical device)"
	@echo "  make setup      install backend and frontend dependencies"
	@echo "  make dev        run backend (:$(PORT)), ground console (:$(GROUND_PORT)), frontend (:5173)"
	@echo "  make demo       reset synthetic data, seed all scenarios, then run dev"
	@echo "  make seed       (re)generate synthetic mission data"
	@echo "  make test       run the backend test suite"
	@echo "  make demo-check run end-to-end scenario assertions"
	@echo "  make eval       run the deterministic assistant evaluation set"

setup:
	/opt/homebrew/bin/python3.12 -m venv .venv 2>/dev/null || python3 -m venv .venv
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt
	cd frontend && npm install
	@echo "Setup complete. Run: make demo"

backend:
	$(PY) -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $(PORT) --reload

ground:
	$(PY) -m uvicorn app.ground_main:app --app-dir backend --host 127.0.0.1 --port $(GROUND_PORT) --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "Pulse backend :$(PORT) · ground console :$(GROUND_PORT) · frontend :5173"
	@if [ -n "$$CODESPACE_NAME" ]; then \
		echo ""; \
		echo "=== Codespaces forwarded URLs ==="; \
		echo "Frontend:  https://$$CODESPACE_NAME-5173.app.github.dev"; \
		echo "Backend:   https://$$CODESPACE_NAME-8000.app.github.dev"; \
		echo "Ground:    https://$$CODESPACE_NAME-8001.app.github.dev"; \
		echo ""; \
	fi
	@trap 'kill 0' INT TERM EXIT; \
	$(PY) -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $(PORT) & \
	$(PY) -m uvicorn app.ground_main:app --app-dir backend --host 127.0.0.1 --port $(GROUND_PORT) & \
	(cd frontend && npm run dev) & \
	wait

seed:
	$(PY) -m app.sim.seed --reset --app-dir backend

demo: seed
	@echo "Synthetic demo data ready. Starting Pulse..."
	@$(MAKE) dev

demo-reset:
	$(PY) -m app.sim.seed --reset --app-dir backend

test:
	$(PY) -m pytest -q -c backend/pytest.ini

demo-check:
	$(PY) -m pytest -q -c backend/pytest.ini backend/tests/test_scenarios.py

rebuild-projections:
	$(PY) -m app.projections --app-dir backend

eval:
	$(PY) -m app.llm.evaluation --app-dir backend

clean:
	rm -rf data .pytest_cache backend/.pytest_cache frontend/dist
	find backend -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
