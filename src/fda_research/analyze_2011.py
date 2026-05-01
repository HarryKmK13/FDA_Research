"""Reproducible analysis for the 2011 FDA citizen petition extraction.

The script reads validated petition and response tables, derives docket-level
matching fields, writes summary CSV/Markdown reports, and creates figures for
GitHub presentation.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_METADATA_DIR = DATA_DIR / "raw_metadata"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = ROOT / "figures"


DOCKET_RE = re.compile(r"(FDA-\d{4}-P-\d{4})")


def extract_docket_id(value: object) -> str | None:
    match = DOCKET_RE.search(str(value))
    return match.group(1) if match else None


def classify_response(value: object) -> str:
    """Map free-text FDA response labels into normalized outcome categories."""
    if pd.isna(value):
        return "missing"

    text = str(value).strip().lower()

    if "partial" in text and ("approved" in text or "approval" in text or "grant" in text):
        return "partially approved"
    if "approved" in text or "approval" in text or "grant" in text:
        return "approved"
    if "denied" in text or "deny" in text:
        return "denied"
    if "withdraw" in text:
        return "withdrawn"
    if any(term in text for term in ["interim", "tentative", "pending", "review", "evaluating"]):
        return "interim"
    if "other" in text:
        return "other"
    if text in {"not mentioned", ""}:
        return "uncategorized"
    return "uncategorized"


def read_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    processed = root / "data" / "processed"
    raw_metadata = root / "data" / "raw_metadata"

    petitions = pd.read_csv(processed / "petition_results_validated_v2.csv")
    responses = pd.read_csv(processed / "response_results_validated_v2.csv")
    inventory = pd.read_csv(raw_metadata / "fda_2011_combined_metadata.csv")

    petitions["Docket_ID"] = petitions["File Name"].map(extract_docket_id)
    responses["Docket_ID"] = responses["File Name"].map(extract_docket_id)
    responses["Response_Category"] = responses["Response to Petition"].map(classify_response)

    petitions["Date of Petition"] = pd.to_datetime(petitions["Date of Petition"], errors="coerce")
    responses["Date of Response"] = pd.to_datetime(responses["Date of Response"], errors="coerce")

    return petitions, responses, inventory


def build_response_pairs(petitions: pd.DataFrame, responses: pd.DataFrame) -> pd.DataFrame:
    matched = petitions.merge(
        responses,
        on="Docket_ID",
        how="inner",
        suffixes=("_petition", "_response"),
    )
    matched["Response_Days"] = (
        matched["Date of Response"] - matched["Date of Petition"]
    ).dt.days

    columns = [
        "Docket_ID",
        "File Name_petition",
        "Date of Petition",
        "Identity of Submitting Entity",
        "Requested Action",
        "File Name_response",
        "Date of Response",
        "Responding FDA Center",
        "Response to Petition",
        "Response_Category",
        "Response_Days",
    ]
    return matched[[column for column in columns if column in matched.columns]]


def make_key_metrics(
    petitions: pd.DataFrame,
    responses: pd.DataFrame,
    inventory: pd.DataFrame,
    pairs: pd.DataFrame,
) -> pd.DataFrame:
    valid_pairs = pairs[pairs["Response_Days"].ge(0)]
    metrics = [
        ("raw_document_records", len(inventory)),
        ("raw_document_dockets", inventory["docket_id"].nunique()),
        ("petition_rows_validated", len(petitions)),
        ("petition_dockets", petitions["Docket_ID"].nunique()),
        ("response_rows_validated", len(responses)),
        ("response_dockets", responses["Docket_ID"].nunique()),
        ("matched_petition_response_pairs", len(pairs)),
        ("valid_nonnegative_response_pairs", len(valid_pairs)),
        ("valid_response_pair_dockets", valid_pairs["Docket_ID"].nunique()),
        ("pairs_with_response_within_150_days", int(valid_pairs["Response_Days"].le(150).sum())),
        ("pairs_with_response_within_200_days", int(valid_pairs["Response_Days"].le(200).sum())),
        ("median_response_days", round(float(valid_pairs["Response_Days"].median()), 1)),
        ("mean_response_days", round(float(valid_pairs["Response_Days"].mean()), 1)),
    ]
    return pd.DataFrame(metrics, columns=["metric", "value"])


def write_reports(
    root: Path,
    petitions: pd.DataFrame,
    responses: pd.DataFrame,
    inventory: pd.DataFrame,
    pairs: pd.DataFrame,
) -> None:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    valid_pairs = pairs[pairs["Response_Days"].ge(0)].copy()
    key_metrics = make_key_metrics(petitions, responses, inventory, pairs)
    key_metrics.to_csv(reports_dir / "summary_statistics.csv", index=False)

    response_counts = (
        responses["Response_Category"]
        .value_counts()
        .rename_axis("response_category")
        .reset_index(name="count")
    )
    response_counts.to_csv(reports_dir / "response_category_counts.csv", index=False)

    center_counts = (
        responses["Responding FDA Center"]
        .fillna("Not Mentioned")
        .value_counts()
        .rename_axis("responding_center")
        .reset_index(name="count")
    )
    center_counts.to_csv(reports_dir / "responding_center_counts.csv", index=False)

    inventory_counts = (
        inventory["doc_type_guess"]
        .fillna("unknown")
        .value_counts()
        .rename_axis("document_type_guess")
        .reset_index(name="count")
    )
    inventory_counts.to_csv(reports_dir / "document_inventory_counts.csv", index=False)

    valid_pairs.sort_values(["Docket_ID", "Response_Days"]).to_csv(
        reports_dir / "response_time_by_pair.csv",
        index=False,
    )

    def format_metric(value: object) -> str:
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    metrics = {row.metric: format_metric(row.value) for row in key_metrics.itertuples()}
    markdown = f"""# Key Metrics

This report is generated by `src/fda_research/analyze_2011.py`.

## Data Coverage

- Raw document metadata records: {metrics["raw_document_records"]}
- Raw docket IDs represented: {metrics["raw_document_dockets"]}
- Validated petition rows: {metrics["petition_rows_validated"]}
- Validated petition docket IDs: {metrics["petition_dockets"]}
- Validated response rows: {metrics["response_rows_validated"]}
- Validated response docket IDs: {metrics["response_dockets"]}

## Petition Response Matching

- Matched petition-response rows: {metrics["matched_petition_response_pairs"]}
- Nonnegative response-time pairs: {metrics["valid_nonnegative_response_pairs"]}
- Dockets represented among nonnegative response-time pairs: {metrics["valid_response_pair_dockets"]}
- Pairs with response within 150 days: {metrics["pairs_with_response_within_150_days"]}
- Pairs with response within 200 days: {metrics["pairs_with_response_within_200_days"]}
- Median response time among valid pairs: {metrics["median_response_days"]} days
- Mean response time among valid pairs: {metrics["mean_response_days"]} days

Notes: response-time rows are pair-level matches. Some dockets have multiple petition or response documents, so pair counts should not be interpreted as unique docket counts.
"""
    (reports_dir / "key_metrics.md").write_text(markdown, encoding="utf-8")


def horizontal_bar(series: pd.Series, title: str, xlabel: str, path: Path) -> None:
    ordered = series.sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(9, max(4.5, len(ordered) * 0.45)))
    ax.barh(ordered.index.astype(str), ordered.values, color="#2F6F73")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_plots(root: Path, responses: pd.DataFrame, inventory: pd.DataFrame, pairs: pd.DataFrame) -> None:
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    horizontal_bar(
        responses["Response_Category"].value_counts(),
        "FDA Petition Response Outcomes, 2011",
        "Response records",
        figures_dir / "response_outcomes_2011.png",
    )

    horizontal_bar(
        responses["Responding FDA Center"].fillna("Not Mentioned").value_counts().head(10),
        "Most Common FDA Responding Centers, 2011",
        "Response records",
        figures_dir / "responding_centers_2011.png",
    )

    horizontal_bar(
        inventory["doc_type_guess"].fillna("unknown").value_counts(),
        "Raw FDA Document Inventory, 2011",
        "Document records",
        figures_dir / "document_inventory_2011.png",
    )

    valid_pairs = pairs[pairs["Response_Days"].ge(0)]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(valid_pairs["Response_Days"], bins=24, color="#7A4E2F", edgecolor="white")
    ax.axvline(150, color="#B3312C", linestyle="--", linewidth=1.4, label="150 days")
    ax.axvline(valid_pairs["Response_Days"].median(), color="#2F6F73", linewidth=1.4, label="Median")
    ax.set_title("Petition to Response Time, 2011")
    ax.set_xlabel("Days from petition date to response date")
    ax.set_ylabel("Matched petition-response pairs")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures_dir / "response_time_distribution_2011.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze validated 2011 FDA citizen petition data.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    parser.add_argument("--no-plots", action="store_true", help="Skip PNG figure generation.")
    args = parser.parse_args()

    root = args.root.resolve()
    petitions, responses, inventory = read_inputs(root)
    pairs = build_response_pairs(petitions, responses)
    write_reports(root, petitions, responses, inventory, pairs)
    if not args.no_plots:
        write_plots(root, responses, inventory, pairs)

    print(f"Wrote reports to {root / 'reports'}")
    if not args.no_plots:
        print(f"Wrote figures to {root / 'figures'}")


if __name__ == "__main__":
    main()
