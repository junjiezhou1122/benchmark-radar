"""Score cutoff semantics and the data shared by ranking, charts and HTML seeds."""

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from benchmark_radar.app_seeds import _display_value, _score_browser_seed
from benchmark_radar.score_summary import score_summary


@pytest.mark.parametrize(
    ("values", "options", "factor", "maximum"),
    [
        ([0.2, 0.699], {"fractional_display": True}, 100, 69.9),
        ([0.2, 0.7], {"fractional_display": True}, 100, 70),
        ([0.2, 0.95], {"fractional_display": True}, 100, 95),
        ([0.2, 0.95], {"fractional_display": True, "declared_max": 100}, 1, 0.95),
        ([0.5], {"fractional_display": True, "max_score_contradicted": True}, 1, 0.5),
        ([1000, 1400], {"fractional_display": True}, 1, 1400),
        ([5, 69.9], {"unit": "percent"}, 1, 69.9),
        ([None, "unreported", math.nan, math.inf, True], {}, 1, None),
        ([0], {}, 1, 0),
    ],
)
def test_summary_preserves_display_units_and_missing_scores(values, options, factor, maximum):
    result = score_summary([{"value": value} for value in values], **options)
    assert result["display_multiplier"] == factor
    if maximum is None:
        assert result["numeric_count"] == 0
        assert result["display_max"] is None
        assert result["source_reference"] is None
    else:
        assert result["display_max"] == pytest.approx(maximum)


def test_undated_high_score_prevents_false_under70_membership():
    result = score_summary(
        [
            {"value": 0.6, "reported_date": "2026-01-01", "obs_id": "dated"},
            {
                "value": 0.95,
                "reported_date": None,
                "obs_id": "undated",
                "source_url": "https://example.org/scores",
            },
        ],
        fractional_display=True,
    )
    assert result["numeric_count"] == 2
    assert result["display_max"] == 95
    assert result["source_reference"]["obs_id"] == "undated"
    assert result["source_reference"]["reported_date"] is None


def test_highest_is_numeric_maximum_even_for_lower_is_better_metrics():
    result = score_summary([{"value": 80}, {"value": 20}], unit="error")
    assert result["raw_max"] == 80
    assert result["display_multiplier"] == 1


def test_summary_ties_choose_a_stable_source_reference():
    rows = [{"value": 60, "obs_id": "z"}, {"value": 60, "obs_id": "a"}]
    assert score_summary(rows) == score_summary(list(reversed(rows)))
    assert score_summary(rows)["source_reference"]["obs_id"] == "a"


def test_generated_external_index_and_shards_share_summary():
    index = json.loads(Path("site/data/benchmark-index.json").read_text())["benchmarks"]
    for record in index:
        shard = json.loads(Path(f"site/data/benchmarks/{record['slug']}.json").read_text())
        payload = shard["scores_by_source"].get(record["source"])
        if not payload:
            assert record["score_summary"] is None
            continue
        series = payload["series"]
        expected = score_summary(
            payload["rows"],
            fractional_display=True,
            declared_max=series["declared_max"],
            max_score_contradicted=series["max_score_contradicted"],
        )
        assert series["score_summary"] == expected
        assert record["score_summary"] == expected


def test_generated_curated_summary_counts_all_observations():
    data = json.loads(Path("site/data/radar.json").read_text())
    for record in data["benchmark_score_progression"]["benchmarks"].values():
        assert record["score_summary"] == score_summary(record["observations"], unit=record["unit"])


def test_seed_ranks_score_points_without_source_preference():
    def summary(count, value):
        return score_summary([{"value": value}] * count)

    data = {
        "model_card_leaderboard": {"entries": [{"benchmark_id": "curated", "name": "Curated"}]},
        "benchmark_score_progression": {
            "benchmarks": {"curated": {"score_summary": summary(2, 50)}}
        },
    }
    index = [
        {
            "slug": "external",
            "name": "External",
            "source": "llm_stats",
            "score_summary": summary(9, 60),
        },
        {
            "slug": "excluded",
            "name": "Excluded",
            "source": "llm_stats",
            "score_summary": summary(20, 70),
        },
    ]
    seeds = _score_browser_seed(data, index)
    markup = seeds['<ol class="leaderboard-top-list" id="score-ranking-list"></ol>']
    assert markup.index("External") < markup.index("Curated")
    assert "9 data points" in markup
    assert "2 data points" in markup
    assert "Excluded" not in markup
    assert "LLM Stats" in markup


def test_browser_date_and_score_filter_contracts():
    node = shutil.which("node")
    assert node, "Node.js is required for the site behavior tests"
    subprocess.run(
        [node, "tests/score_filters_harness.mjs"], check=True, capture_output=True, text=True
    )


def test_seed_and_browser_format_scores_identically():
    """The seed and app.js must print one decimal the same way, half-up included."""
    node = shutil.which("node")
    assert node, "Node.js is required for the site behavior tests"
    values = [55.468026, 94.949495, 70, 0, 32.285714, 1400, 69.95, 69.94, 0.95, 0.05, 1234.567]
    script = (
        "console.log(JSON.stringify("
        f"{values}.map(v => v.toLocaleString('en', {{maximumFractionDigits: 1}}))))"
    )
    result = subprocess.run([node, "-e", script], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == [_display_value(value) for value in values]
