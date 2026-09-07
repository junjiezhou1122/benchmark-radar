"""Cited release and first-score dates missing from immutable catalog crawls.

These facts fill exact source records, never join records by name or transfer
scores. A paper date must belong to the paper introducing that benchmark, not
an arbitrary reference extracted from its README.
Numeric first-score evidence verifies a publication date. It does not turn an
introducing paper into an aggregator's score archive or a known highest score.
"""

from __future__ import annotations

from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from .external_catalog import ExternalCatalogError

DEFAULT_DATES_PATH = Path("data/external/benchmark_dates.yml")
RELEASE_BASES = {
    "paper_first_version",
    "paper_publication",
    "release_announcement",
    "dataset_published",
}


def load_benchmark_dates(
    records: list[dict[str, Any]], path: Path = DEFAULT_DATES_PATH
) -> dict[str, dict[str, Any]]:
    """Validate the cited facts against the current source-record population."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ExternalCatalogError(f"{path}: cannot read benchmark dates: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ExternalCatalogError(f"{path}: expected benchmark dates schema_version 1")
    facts = payload.get("benchmarks")
    if not isinstance(facts, dict):
        raise ExternalCatalogError(f"{path}: benchmarks must be a mapping")
    keys = {row["key"] for row in records}
    validated = {}
    for key, fact in facts.items():
        if key not in keys:
            raise ExternalCatalogError(f"{path}: unknown benchmark key {key!r}")
        if not isinstance(fact, dict):
            raise ExternalCatalogError(f"{path}: {key}: expected a benchmark-date record")
        field = "released" if "released" in fact else "first_score_reported_at"
        if "released" in fact and "first_score_reported_at" in fact:
            raise ExternalCatalogError(f"{path}: {key}: each fact must date one event")
        dated = str(fact.get(field, ""))
        try:
            valid = date.fromisoformat(dated).isoformat() == dated
        except ValueError:
            valid = False
        if not valid:
            raise ExternalCatalogError(f"{path}: {key}: {field} must be an exact ISO date")
        bases = RELEASE_BASES if field == "released" else {"score_publication"}
        if fact.get("basis") not in bases:
            raise ExternalCatalogError(f"{path}: {key}: unsupported release-date basis")
        if field == "first_score_reported_at":
            evidence = fact.get("score_evidence")
            value = evidence.get("value") if isinstance(evidence, dict) else None
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or not all(evidence.get(k) for k in ("model", "metric", "locator"))
            ):
                raise ExternalCatalogError(
                    f"{path}: {key}: first-score dates need numeric LLM score evidence"
                )
        source_url = fact.get("source_url")
        if (
            not isinstance(source_url, str)
            or urlsplit(source_url).scheme != "https"
            or not urlsplit(source_url).netloc
        ):
            raise ExternalCatalogError(f"{path}: {key}: a primary-source HTTPS URL is required")
        if not isinstance(fact.get("note"), str) or not fact["note"].strip():
            raise ExternalCatalogError(f"{path}: {key}: explain which event the evidence dates")
        validated[key] = {**fact, field: dated}
    return validated


def apply_benchmark_dates(
    records: list[dict[str, Any]], facts: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Fill dates and retain the earliest cited score publication when needed."""
    enriched = []
    for record in records:
        fact = facts.get(record["key"])
        if not fact:
            enriched.append(record)
            continue
        field = "released" if "released" in fact else "first_score_reported_at"
        existing = record.get(field)
        if existing and (field == "released" or existing <= fact[field]):
            enriched.append(record)
            continue
        reference = {
            "source_key": record["key"],
            "basis": fact["basis"],
            "source_url": fact["source_url"],
            "note": fact["note"],
        }
        if field == "released":
            enriched.append({**record, field: fact[field], "released_reference": reference})
        else:
            reference.update(
                reported_at=fact[field],
                date_precision="score_publication",
                score_evidence=fact["score_evidence"],
            )
            enriched.append(
                {**record, field: fact[field], "first_score_source_reference": reference}
            )
    return enriched
