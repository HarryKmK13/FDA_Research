# Research Brief: NLP-Assisted Analysis of 2011 FDA Citizen Petitions

## Abstract

Citizen petitions give outside parties a formal channel to ask the FDA to issue, amend, revoke, or refrain from taking administrative action. This project studies 2011 FDA citizen petition documents by converting public regulatory PDFs into structured petition and response data. The analysis creates validated petition and response tables, matches records by docket ID, and summarizes FDA response outcomes, responding centers, and petition-to-response timing. The work complements related multi-year EDA and modeling repositories by focusing on the document extraction and data validation layer.

## Background

FDA citizen petitions sit at the intersection of public participation, regulatory capacity, and market competition. Under 21 CFR 10.30, FDA may approve, deny, dismiss, or provide a tentative response to a petition, and the regulation describes a general 180-day response framework. For petitions subject to Section 505(q), FDA identifies a 150-day final-action timeline when the petition concerns certain pending abbreviated drug or biosimilar approval pathways.

The literature treats this process as both a governance tool and a possible source of delay. HHS OIG reported in 1998 that FDA had a backlog of roughly 250 unresolved petitions, some dating back many years, and connected timeliness problems to public confidence in the regulatory process. Carrier and Wander's empirical study of 2001-2010 petitions found heavy use by brand-name drug companies in generic-drug contexts and relatively low grant rates. Later work by Carrier and Minniti focused on late-filed 505(q) petitions, while Fahim and Ngorsuraches found that ANDAs associated with citizen petitions had longer average approval times than ANDAs without petitions.

## Data and Methods

The dataset contains a 2011 FDA document inventory and validated extraction outputs:

- 652 raw document metadata records across 156 docket IDs.
- 129 validated petition rows across 96 petition docket IDs.
- 120 validated response rows across 87 response docket IDs.
- Extracted fields including petitioner identity, requested action, cited statutes or regulations, FDA center, response outcome, and justification text.

The extraction pipeline uses PDF text extraction, OCR fallback logic, and a local Ollama model to return structured fields. The analysis pipeline then:

1. Extracts docket IDs from filenames.
2. Classifies response labels into normalized categories.
3. Matches petition and response rows by docket ID.
4. Computes response-time intervals where both dates are valid and nonnegative.
5. Exports summary tables and figures.

## Findings

The most common response category in the validated response table is interim response, with 62 of 120 response rows classified as interim. Other normalized outcomes include withdrawn, denied, partially approved, approved, other, and uncategorized.

CDER is the most common responding center, appearing in 64 response rows. CDRH and CFSAN are the next most common named centers, while 22 rows do not mention a center.

The matched table contains 87 petition-response row pairs. After removing negative date intervals, 64 pair-level records remain across 41 docket IDs. Among these valid pairs, the median petition-to-response interval is 182.5 days and the mean is 562.5 days. The difference between median and mean suggests a long right tail: many responses cluster around a few months, but some dockets remain active for years.

Only 3 valid pair-level matches fall within 150 days, while 43 fall within 200 days. These numbers should be interpreted carefully because the project includes broader citizen petition records, not only 505(q) petitions, and because pair-level matching can duplicate a docket when multiple documents exist.

## Interpretation

The 2011 data support a cautious but useful finding: many FDA responses in this extracted sample are not immediate final decisions. Interim and tentative responses are central to the administrative record, and response timing varies substantially across dockets. This aligns with the broader literature's emphasis on agency workload, statutory timelines, and the tension between public participation and regulatory delay.

The project also shows why data engineering matters for regulatory analytics. Before modeling delay, petitioner behavior, or outcome patterns, the underlying PDFs must be sorted, extracted, validated, and matched. The validation flags reveal that petition extraction was more complete than response extraction, making quality control a necessary part of any downstream causal or predictive analysis.

## Limitations

- The response-time analysis is pair-level, not fully docket-level.
- Some response rows are marked as PDF read errors, incomplete, or missing center information.
- The category labels are rule-based and should be manually audited before publication.
- The data should not be used to make claims about all 505(q) petitions without separately identifying which dockets are subject to 505(q).

## Research Takeaway

This repository demonstrates an end-to-end regulatory NLP workflow: raw public documents to structured data, validation, reproducible analysis, visual outputs, and literature-grounded interpretation. The strongest next step would be harmonizing this 2011 dataset with the multi-year modeling schema used in the companion FDA citizen petition research.

## Sources

- 21 CFR 10.30, Citizen petition: https://ecfr.io/Title-21/Section-10.30
- FDA Annual CDER Reports to Congress: https://www.fda.gov/about-fda/reports-budgets-cder/annual-cder-reports-congress
- FDA Sixteenth Annual Report on 505(q) Petitions, FY 2023: https://www.fda.gov/media/184951/download
- Carrier and Wander, Citizen Petitions: An Empirical Study: https://larc.cardozo.yu.edu/clr/vol34/iss1/7/
- Carrier and Minniti, Citizen Petitions: Long, Late-Filed, and At-Last Denied: https://digitalcommons.wcl.american.edu/aulr/vol66/iss2/1/
- Fahim and Ngorsuraches, Did citizen petitions prolong the number of approval days of generic drugs?: https://www.sciencedirect.com/science/article/abs/pii/S1551741119301081
- HHS OIG, Review of the FDA Citizen Petition Process: https://oig.hhs.gov/reports/all/1998/review-of-the-food-and-drug-administrations-citizen-petition-process/
