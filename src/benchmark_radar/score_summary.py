"""Numeric summaries for score browsing, not saturation or comparability claims."""

from __future__ import annotations

import math
from typing import Any


def score_summary(
    rows: list[dict[str, Any]],
    *,
    unit: str | None = None,
    fractional_display: bool = False,
    declared_max: float | None = None,
    max_score_contradicted: bool = False,
) -> dict[str, Any]:
    """Summarize every numeric observation, including ones without a plot date.

    Fractional display is the existing external chart convention: multiply a
    series inside [0, 1] by 100 unless its declared maximum forbids it. This
    changes display units only; it never establishes a percentage or ceiling.
    The maximum is numeric even for lower-is-better metrics, hence "highest"
    rather than "best" in the UI.
    """
    numeric = [
        row
        for row in rows
        if isinstance(row.get("value"), (int, float))
        and not isinstance(row["value"], bool)
        and math.isfinite(row["value"])
    ]
    # Count models within this source record, never score rows or citations.
    # Aggregator IDs preserve distinct checkpoints/configurations with the same
    # display name. Curated results identify models by publisher and name.
    # Do not mix these identity schemes when a source ID is missing: a name
    # could refer to an already counted ID, producing a false extra model.
    source_ids = any("model_id" in row for row in numeric)
    model_keys = []
    for row in numeric:
        model_id = row.get("model_id")
        model = row.get("model") or row.get("model_name")
        organization = row.get("organization")
        if source_ids:
            if isinstance(model_id, str) and model_id.strip():
                model_keys.append((model_id.strip(),))
        elif (
            isinstance(model, str)
            and model.strip()
            and isinstance(organization, str)
            and organization.strip()
        ):
            model_keys.append((organization.strip(), model.strip()))
    complete_models = bool(numeric) and len(model_keys) == len(numeric)
    multiplier = 1
    if (
        numeric
        and fractional_display
        and not max_score_contradicted
        and (declared_max is None or declared_max <= 1)
        and all(0 <= row["value"] <= 1 for row in numeric)
    ):
        multiplier = 100
    highest = min(
        numeric,
        key=lambda row: (
            -row["value"],
            str(row.get("observation_id") or row.get("obs_id") or ""),
        ),
        default=None,
    )
    return {
        "numeric_count": len(numeric),
        "model_count": len(set(model_keys)) if complete_models else None,
        "model_count_basis": ("source_model_id" if source_ids else "organization_and_model")
        if complete_models
        else None,
        "raw_max": highest["value"] if highest else None,
        "display_multiplier": multiplier,
        "display_max": highest["value"] * multiplier if highest else None,
        "unit": unit,
        "source_reference": (
            {
                key: highest[key]
                for key in (
                    "observation_id",
                    "obs_id",
                    "source_id",
                    "source_url",
                    "reported_at",
                    "reported_date",
                    "crawled_at",
                )
                if key in highest
            }
            if highest
            else None
        ),
    }
