"""Score cutoff semantics and the data shared by ranking, charts and HTML seeds."""

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from benchmark_radar.app_seeds import _benchmark_date, _display_value, _score_browser_seed
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


def test_seed_excludes_unscored_but_keeps_zero_scores_and_unjoined_records():
    data = {
        "model_card_leaderboard": {"entries": []},
        "benchmark_score_progression": {
            "benchmarks": {"unjoined": {"score_summary": score_summary([{"value": 50}])}}
        },
    }
    index = [
        {"slug": "unknown", "name": "Unknown score", "source": "opencompass_hub"},
        {
            "slug": "zero",
            "name": "Zero score",
            "source": "llm_stats",
            "score_summary": score_summary([{"value": 0}]),
        },
        {
            "slug": "high",
            "name": "Above cutoff",
            "source": "llm_stats",
            "score_summary": score_summary([{"value": 90}]),
        },
    ]
    seeds = _score_browser_seed(data, index)
    rendered = "".join(seeds.values())
    assert "unjoined" in rendered
    assert "Unknown score" not in rendered
    assert "No score reported" not in rendered
    assert "Zero score" in rendered
    assert "Above cutoff" not in rendered
    assert "2 of 2 matches" in rendered


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


def test_seed_uses_release_then_earliest_score_and_applies_inclusive_2024_cutoff():
    assert _benchmark_date({"released": "2025-01-01", "first_reported_at": "2023-01-01"}) == (
        "2025-01-01",
        "Released",
    )
    assert _benchmark_date(
        {
            "released": "2025-02-29",
            "observations": [
                {"value": 40, "reported_at": "2025-03-01"},
                {"value": 30, "reported_at": "2024-01-01"},
                {
                    "value": 30,
                    "reported_date": "2019-01-01",
                    "date_precision": "model_announcement",
                },
                {"value": None, "reported_at": "2020-01-01"},
            ],
        }
    ) == ("2024-01-01", "First LLM score reported")
    assert _benchmark_date(
        {"collected_at": "2026-08-17", "first_observed": "2026-08-17"},
        {"adopters": [{"published": "2025-01-01"}]},
    ) == (None, None)
    index = [
        {
            "slug": "old",
            "name": "Old release",
            "source": "llm_stats",
            "released": "2023-12-31",
            "first_score_reported_at": "2025-01-01",
        },
        {
            "slug": "old-score",
            "name": "Old score",
            "source": "llm_stats",
            "first_score_reported_at": "2023-12-31",
        },
        {
            "slug": "boundary",
            "name": "Boundary release",
            "source": "llm_stats",
            "released": "2024-01-01",
        },
        {
            "slug": "fallback",
            "name": "Dated score",
            "source": "llm_stats",
            "first_score_reported_at": "2024-01-01",
        },
        {"slug": "unknown", "name": "Undated evidence", "source": "llm_stats"},
    ]
    for record in index:
        record["score_summary"] = score_summary([{"value": 50}])
    markup = "".join(_score_browser_seed({}, index).values())
    assert "Old release" not in markup
    assert "Old score" not in markup
    assert "Boundary release" in markup
    assert "Dated score" in markup
    assert "First LLM score reported Jan 1, 2024" in markup
    assert "Undated evidence" in markup
    assert "Date unknown" in markup
    assert "3 of 3 matches" in markup


def test_seed_preserves_score_entry_proxy_and_prefers_release_or_publication():
    proxy = {
        "first_score_record": {
            "reported_at": "2024-02-29",
            "date_precision": "model_announcement",
            "obs_id": "earliest-numeric-score",
        }
    }
    assert _benchmark_date(proxy) == (
        "2024-02-29",
        "First dated LLM score (model-release proxy)",
    )
    assert _benchmark_date({**proxy, "released": "2025-01-01"}) == ("2025-01-01", "Released")
    assert _benchmark_date({**proxy, "first_score_reported_at": "2025-02-01"}) == (
        "2025-02-01",
        "First LLM score reported",
    )
    assert _benchmark_date(
        {"first_score_record": {"reported_at": "2024-01-01", "date_precision": "crawl"}}
    ) == (None, None)
    index = [
        {"slug": "proxy", "name": "Score entry", "source": "llm_stats", **proxy},
        {
            "slug": "old-proxy",
            "name": "Pre-2024 score entry",
            "source": "llm_stats",
            "first_score_record": {
                "reported_at": "2023-12-31",
                "date_precision": "model_announcement",
            },
        },
    ]
    for record in index:
        record["score_summary"] = score_summary([{"value": 50}])
    markup = "".join(_score_browser_seed({}, index).values())
    assert "First dated LLM score (model-release proxy) Feb 29, 2024" in markup
    assert "Pre-2024 score entry" not in markup
    assert "1 of 1 matches" in markup
