# Methods Comparison

This note compares the GitHub and Drive materials reviewed for the FDA citizen petition research project. The goal is to show what this repository contributes and how it relates to adjacent work.

## Reference Repositories Reviewed

### `AshleyAHuang/SummaryQuality`

Primary file reviewed: `evalue_summary_quality.py`.

This repository provides a summary-evaluation utility that compares full texts with generated summaries using BERTScore, BLEURT, and NLI entailment. Its strength is evaluation design: it asks whether summaries are semantically similar, fluent/factual, and logically entailed by source documents.

How it relates here: useful future extension for scoring any generated summaries of FDA petitions or response letters, especially if the project adds extractive or abstractive summarization.

### `aanht/ucb-fda-citizen-research`

Primary materials reviewed: `README.md`, `all_years_eda_modeling/`, and `eda_modeling_2017/`.

This repository is strongest on multi-year structured analysis. It includes cleaned multi-year data, EDA notebooks, Cox/survival modeling feature tables, and figures for response timing and decision patterns.

How it relates here: this 2011 repository fills a year-specific extraction and validation gap, while the reference repo provides a template for scaling into multi-year modeling after the 2011 tables are harmonized.

### `smritirangarajan/fda-citizen`

Primary materials reviewed: `FDA_Citizen_Petition.ipynb` and `FDA_Citizen_Summarizing.ipynb`.

This repository explores petition outcomes, cited statutes, requested actions, TF-IDF features, KMeans clustering, PCA visualization, and simple knowledge graphs.

How it relates here: those NLP exploration techniques are good candidates for a second-stage analysis of the 2011 petition text fields after validation and topic normalization.

## This Repository's Contribution

This repository is organized around a different part of the research pipeline:

- Raw 2011 FDA PDF inventory and docket metadata.
- LLM-assisted structured extraction from petition and response PDFs.
- Validation flags that make extraction quality visible.
- Reproducible response-outcome, FDA-center, and response-time analysis.
- Clear documentation and figures for public research sharing.

## Best Interview Framing

The strongest framing is not "I made another notebook." It is:

"I worked on the document-to-data layer of the FDA citizen petition project. I converted messy public regulatory PDFs into structured petition and response tables, validated extraction quality, matched records by docket ID, and created a reproducible analysis package that can be extended into the broader multi-year modeling and NLP work."

## Future Work

- Harmonize 2011 column names with the multi-year schema in `aanht/ucb-fda-citizen-research`.
- Add TF-IDF topic models for requested actions and justifications.
- Add summary-quality evaluation for any generated document summaries.
- Convert pair-level matching to a stricter docket-level panel for survival or Cox modeling.
- Manually audit PDF-read-error rows before making strong claims about response rates.
