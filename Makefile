.PHONY: analysis check

PYTHON ?= python3

analysis:
	PYTHONPATH=src $(PYTHON) -m fda_research.analyze_2011

check:
	PYTHONPATH=src $(PYTHON) -m fda_research.analyze_2011 --no-plots
