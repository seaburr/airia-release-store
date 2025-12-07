PYTHON ?= python

.PHONY: lint test build venv

lint:
	$(PYTHON) -m flake8 . --exclude .venv

test:
	$(PYTHON) -m pytest

build: lint test
	docker build -t airia-release-store .

venv:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "Run 'source .venv/bin/activate' to activate the virtual environment."
