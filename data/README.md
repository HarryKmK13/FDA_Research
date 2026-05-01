# Data

This folder keeps shareable, GitHub-ready data derived from the 2011 FDA citizen petition extraction.

## Files

- `processed/petition_results_validated_v2.csv`: validated petition-level fields extracted from FDA PDFs.
- `processed/response_results_validated_v2.csv`: validated response-level fields extracted from FDA PDFs.
- `processed/fda_2011_decision_rates_by_category.csv`: category and outcome summary from the original exploratory analysis.
- `processed/fda_2011_petition_categories.csv`: topic category counts from the original exploratory analysis.
- `raw_metadata/fda_2011_combined_metadata.csv`: raw document inventory metadata, including file path, docket ID, page count, guessed document type, and title snippet.

## Raw PDFs

The raw FDA PDFs are public regulatory documents, but they are intentionally not committed here because the local folder contains hundreds of files and several cloud-placeholder artifacts. The extraction script expects raw PDFs to be placed in a local folder and then sorted into petitions/responses before field extraction.

