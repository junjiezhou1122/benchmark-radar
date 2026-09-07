from __future__ import annotations

import json
import re
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
render_data = runpy.run_path(str(ROOT / "scripts" / "export_report_figure_data.py"))["render_data"]


@pytest.fixture
def figure_inputs(tmp_path: Path) -> Path:
    data = tmp_path / "site" / "data"
    data.mkdir(parents=True)
    # Most records have no measurement fields at all. They still belong in the
    # catalog, including a fifth source unknown to the original manuscript.
    sources = ["llm_stats", "opencompass_hub", "model_reports", "artificial_analysis", "new"]
    records = [{"key": f"record:{i}", "source": sources[i % 5]} for i in range(1260)]
    (data / "benchmark-index.json").write_text(
        json.dumps({"count": len(records), "benchmarks": records})
    )
    observations = [
        {"source": label}
        for label, count in [("A&B", 9), ("B", 8), ("C", 7), ("D", 6), ("E", 5), ("F", 4), ("G", 3)]
        for _ in range(count)
    ]
    radar = {
        "latest_date": "2026-09-06",
        "snapshot_count": 45,
        "corpus": {
            "observations": observations,
            "observation_count": len(observations),
            "entities": [{"type": "artifact"}, {"type": "organization"}],
        },
    }
    (data / "radar.json").write_text(json.dumps(radar))
    return tmp_path


def test_figure_counts_include_unscored_records_and_new_sources(figure_inputs: Path) -> None:
    result = render_data(figure_inputs)
    assert r"\newcommand{\ReportCatalogCount}{1260}" in result
    assert r"\newcommand{\ReportCatalogSourceCount}{5}" in result
    assert r"\newcommand{\ReportModelReportCount}{252}" in result
    assert r"\newcommand{\ReportArtifactCount}{1}" in result
    assert result == render_data(figure_inputs)


def test_source_bars_cover_all_observations_and_escape_tex(figure_inputs: Path) -> None:
    result = render_data(figure_inputs)
    values = re.findall(r"\\SourceBar\{\d+\}\{[^\n]+\}\{(\d+)\}", result)
    assert sum(map(int, values)) == 42
    assert r"\SourceBar{5}{2 other labels}{7}" in result
    assert r"\SourceBar{0}{A\&B}{9}" in result
    assert r"\newcommand{\ReportObservationCount}{42}" in result


@pytest.mark.parametrize("defect", ["count", "duplicate", "small", "source_loss", "observations"])
def test_incomplete_or_inconsistent_data_fails_visibly(figure_inputs: Path, defect: str) -> None:
    path = figure_inputs / "site" / "data" / "benchmark-index.json"
    index = json.loads(path.read_text())
    if defect == "count":
        index["count"] -= 1
    elif defect == "duplicate":
        index["benchmarks"][0]["key"] = index["benchmarks"][1]["key"]
    elif defect == "small":
        index["benchmarks"] = index["benchmarks"][:30]
        index["count"] = 30
    elif defect == "source_loss":
        for row in index["benchmarks"]:
            row["source"] = "model_reports"
    else:
        radar_path = path.with_name("radar.json")
        radar = json.loads(radar_path.read_text())
        radar["corpus"]["observation_count"] += 1
        radar_path.write_text(json.dumps(radar))
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError):
        render_data(figure_inputs)


def test_missing_generated_data_is_not_replaced_by_dated_numbers(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        render_data(tmp_path)
