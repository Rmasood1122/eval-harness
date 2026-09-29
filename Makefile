.PHONY: install test lint-registry baseline suite gate demo-block online

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -q

lint-registry:
	python evals/runners/registry_lint.py

baseline:
	python evals/runners/baseline.py --runs 3

suite:
	python evals/runners/run_suite.py

gate:
	python evals/runners/promote.py

demo-block:
	DEGRADE_MODE=1 python evals/runners/run_suite.py evals/reports/candidate_degraded.json
	python evals/runners/promote.py --candidate evals/reports/candidate_degraded.json

online:
	python evals/online/eval_online.py
