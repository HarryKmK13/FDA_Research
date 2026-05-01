# FDA Citizen Petitions: 2011 Extraction and Response Analysis

This repository presents a reproducible analysis of 2011 FDA citizen petition documents. The project extracts structured fields from public FDA petition and response PDFs, validates the extracted tables, and analyzes how petitions were routed, categorized, and answered.

The project is organized around clean data, scripts, figures, and concise research notes so readers can quickly understand the research question, method, and results.

## Research Question

How can NLP-assisted document extraction and structured analysis help characterize FDA citizen petitions, including petitioner identity, requested action, FDA center, response outcome, and response timing?

## Project Highlights

- Built a PDF extraction workflow using text extraction, OCR fallbacks, and a local Ollama LLM prompt for structured field extraction.
- Created validated petition and response datasets for 2011 FDA citizen petition dockets.
- Matched petition and response records by docket ID to estimate petition-to-response timing.
- Produced GitHub-ready figures, summary tables, and a short research brief that situates the results in the citizen-petition literature.

## Key Results

Generated from `src/fda_research/analyze_2011.py`:

- Raw document metadata records: 652
- Raw docket IDs represented: 156
- Validated petition rows: 129
- Validated response rows: 120
- Matched petition-response rows: 87
- Nonnegative response-time pairs: 64 across 41 docket IDs
- Median response time among valid pairs: 182.5 days
- Mean response time among valid pairs: 562.5 days
- Most common response category: interim response
- Most common FDA responding center: CDER

Pair-level counts are not unique docket counts because some dockets contain multiple petition or response files.

## Repository Structure

```text
.
|-- data/
|   |-- processed/                  # Validated shareable CSVs
|   `-- raw_metadata/               # Raw FDA document inventory metadata
|-- figures/                        # Generated charts for GitHub and presentations
|-- notebooks/
|   `-- archive/                    # Original exploratory notebook
|-- reports/                        # Summary metrics, and writing sample
|-- src/fda_research/
|   |-- analyze_2011.py             # Reproducible analysis and figure generation
|   `-- extract_fields_ollama.py    # Original extraction pipeline using Ollama and OCR
|-- Makefile
|-- requirements.txt
`-- README.md
```

## Reproduce the Analysis

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
make PYTHON=.venv/bin/python analysis
```

This writes refreshed outputs to `reports/` and `figures/`.

## Main Outputs

- `reports/key_metrics.md`
- `reports/writing_sample/Kyaw_Min_Khant_FDA_Citizen_Petitions_Research_Paper.pdf`
- `reports/writing_sample/Kyaw_Min_Khant_FDA_Citizen_Petitions_Research_Paper.docx`
- `reports/writing_sample/Kyaw_Min_Khant_FDA_Citizen_Petitions_Research_Paper.md`
- `reports/summary_statistics.csv`
- `reports/response_category_counts.csv`
- `reports/responding_center_counts.csv`
- `reports/response_time_by_pair.csv`
- `figures/response_outcomes_2011.png`
- `figures/responding_centers_2011.png`
- `figures/response_time_distribution_2011.png`
- `figures/document_inventory_2011.png`

## Method Context

FDA citizen petitions are governed by 21 CFR 10.30, which generally provides response categories such as approval, denial, dismissal, or tentative response. Section 505(q) creates a 150-day final-action framework for certain petitions related to pending abbreviated drug or biosimilar approval pathways.

This project differs from the reference repositories by focusing on the missing 2011 year and on extraction from raw PDFs. The companion work in the reference repos emphasizes multi-year EDA, survival modeling, TF-IDF clustering, knowledge-graph exploration, and summary-quality evaluation.

## References

- [21 CFR 10.30, Citizen petition](https://ecfr.io/Title-21/Section-10.30)
- [FDA Annual CDER Reports to Congress](https://www.fda.gov/about-fda/reports-budgets-cder/annual-cder-reports-congress)
- [FDA Sixteenth Annual Report on 505(q) Petitions, FY 2023](https://www.fda.gov/media/184951/download)
- [Carrier and Wander, Citizen Petitions: An Empirical Study, Cardozo Law Review](https://larc.cardozo.yu.edu/clr/vol34/iss1/7/)
- [Carrier and Minniti, Citizen Petitions: Long, Late-Filed, and At-Last Denied, American University Law Review](https://digitalcommons.wcl.american.edu/aulr/vol66/iss2/1/)
- [Fahim and Ngorsuraches, Did citizen petitions prolong the number of approval days of generic drugs?](https://www.sciencedirect.com/science/article/abs/pii/S1551741119301081)
- [HHS OIG, Review of the FDA Citizen Petition Process](https://oig.hhs.gov/reports/all/1998/review-of-the-food-and-drug-administrations-citizen-petition-process/)
