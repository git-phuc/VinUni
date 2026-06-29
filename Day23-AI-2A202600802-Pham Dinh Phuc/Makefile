.PHONY: install test lint typecheck run-scenarios grade-local clean diagram demo-persistence

install:
	pip install -e '.[dev]'

test:
	pytest

lint:
	ruff check src tests

typecheck:
	mypy src

run-scenarios:
	python -m langgraph_agent_lab.cli run-scenarios --config configs/lab.yaml --output outputs/metrics.json

grade-local:
	python -m langgraph_agent_lab.cli validate-metrics --metrics outputs/metrics.json

diagram:
	python scripts/export_diagram.py

demo-persistence:
	python scripts/demo_persistence.py write
	python scripts/demo_persistence.py read

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov dist build *.egg-info outputs/*.json
