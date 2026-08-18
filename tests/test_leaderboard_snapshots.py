from pathlib import Path

import pytest
import yaml

from benchmark_radar.leaderboard_snapshots import (
    DEFAULT_SNAPSHOTS_PATH,
    LeaderboardSnapshotError,
    build_leaderboard_snapshots,
    build_leaderboard_snapshots_layer,
    load_snapshots,
)


def registry_document(**overrides) -> dict:
    document = {
        "schema_version": 1,
        "snapshots": [
            {
                "id": "test_source_2026-08-17",
                "source": "Test Source",
                "source_url": "https://example.test/benchmarks",
                "crawled_at": "2026-08-17T12:00:00+00:00",
                "description": "Fixture snapshot.",
                "benchmark_file": "benchmarks.csv",
                "benchmark_count": 1,
                "benchmark_columns": {
                    "benchmark_id": "benchmark_id",
                    "benchmark_name": "name",
                },
                "scores_file": "scores.csv",
                "score_row_count": 2,
                "columns": {
                    "benchmark_id": "benchmark_id",
                    "benchmark_name": "benchmark_name",
                    "model": "model_name",
                    "model_id": "model_id",
                    "organization": "organization_name",
                    "rank": "rank",
                    "score": "benchmark_score",
                    "normalized_score": "normalized_score",
                },
            }
        ],
    }
    document.update(overrides)
    return document


def write_snapshots(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "leaderboard_snapshots.yml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,Alpha\n", encoding="utf-8"
    )
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1,Org A,1,0.9,0.9\n"
        "alpha,Alpha,Model Two,m2,Org B,2,0.8,0.8\n",
        encoding="utf-8",
    )
    return path


def minimal_registry() -> dict:
    return {
        "benchmarks": [
            {
                "id": "alpha",
                "name": "Alpha",
                "aliases": ["AlphaBench"],
                "domain": "reasoning",
                "url": "https://example.test/alpha",
                "released": "2025-01-01",
            }
        ],
        "model_cards": [],
    }


def test_load_rejects_a_missing_declared_column(tmp_path):
    # A declared column that the CSV does not carry would make every row read
    # as empty, silently collapsing the snapshot. Refuse it.
    path = write_snapshots(tmp_path, registry_document())
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,model_name,model_id,organization_name,rank,benchmark_score,"
        "normalized_score\n"
        "alpha,Model One,m1,Org A,1,0.9,0.9\n",
        encoding="utf-8",
    )
    with pytest.raises(LeaderboardSnapshotError, match="benchmark_name.*missing"):
        load_snapshots(path)


def test_load_rejects_a_row_count_drifting_from_the_declaration(tmp_path):
    # A truncated or partial rerun must not look identical to a complete
    # snapshot: the registry declares what completeness means.
    path = write_snapshots(tmp_path, registry_document())
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,Alpha\nbeta,Beta\n", encoding="utf-8"
    )
    with pytest.raises(LeaderboardSnapshotError, match="registry declares 1"):
        load_snapshots(path)


def test_load_rejects_a_non_finite_score(tmp_path):
    snapshot = {**registry_document()["snapshots"][0], "score_row_count": 1}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1,Org A,1,nan,0.9\n",
        encoding="utf-8",
    )
    with pytest.raises(LeaderboardSnapshotError, match="not finite"):
        load_snapshots(path)


def test_load_rejects_a_duplicate_catalog_benchmark_id(tmp_path):
    snapshot = {**registry_document()["snapshots"][0], "benchmark_count": 2}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,Alpha\nalpha,Alpha Again\n", encoding="utf-8"
    )
    with pytest.raises(LeaderboardSnapshotError, match="duplicate benchmark id 'alpha'"):
        load_snapshots(path)


def test_load_rejects_a_duplicate_model_within_a_benchmark(tmp_path):
    # Two rows with the same model id on one benchmark contradict each other:
    # the leaderboard cannot rank one model twice.
    path = write_snapshots(tmp_path, registry_document())
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1,Org A,1,0.9,0.9\n"
        "alpha,Alpha,Model One,m1,Org A,2,0.8,0.8\n",
        encoding="utf-8",
    )
    with pytest.raises(LeaderboardSnapshotError, match="duplicate row"):
        load_snapshots(path)


def test_load_accepts_two_checkpoints_sharing_a_display_name(tmp_path):
    # Distinct dated checkpoints of one model can share a display name. Row
    # identity is the model_id, so the pair is two rows, not a contradiction.
    path = write_snapshots(tmp_path, registry_document())
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1-2026-01-01,Org A,1,0.9,0.9\n"
        "alpha,Alpha,Model One,m1-2026-06-01,Org A,2,0.8,0.8\n",
        encoding="utf-8",
    )
    loaded = load_snapshots(path)
    assert loaded["snapshots"][0]["score_row_count"] == 2


def test_load_rejects_a_crawl_timestamp_the_browser_cannot_format(tmp_path):
    snapshot = {**registry_document()["snapshots"][0], "crawled_at": "yesterday"}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    with pytest.raises(LeaderboardSnapshotError, match="not an ISO timestamp"):
        load_snapshots(path)


def test_canonical_mapping_uses_registry_aliases_case_insensitively(tmp_path):
    path = write_snapshots(tmp_path, registry_document())
    snapshots = load_snapshots(path)
    layer = build_leaderboard_snapshots(snapshots, minimal_registry())
    assert "alpha" in layer["benchmarks"]
    assert layer["benchmarks"]["alpha"]["entry_count"] == 2


def test_an_ambiguous_alias_is_left_unmapped_rather_than_guessed(tmp_path):
    # Two canonical benchmarks sharing one external spelling are not resolved
    # by guessing: the merged view would otherwise blend two instruments.
    registry = minimal_registry()
    registry["benchmarks"].append(
        {
            "id": "beta",
            "name": "Beta",
            "aliases": ["AlphaBench"],
            "domain": "reasoning",
            "url": "https://example.test/beta",
        }
    )
    path = write_snapshots(tmp_path, registry_document())
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,AlphaBench\n", encoding="utf-8"
    )
    layer = build_leaderboard_snapshots(load_snapshots(path), registry)
    assert "alpha" not in layer["benchmarks"]
    source = layer["sources"][0]
    assert source["matched_benchmark_count"] == 0
    assert source["unmatched_benchmark_count"] == 1


def test_entries_from_different_snapshots_keep_their_source(tmp_path):
    # Rows from different evaluators under unstated protocols are never ranked
    # against each other; each entry carries the snapshot it came from.
    document = registry_document()
    document["snapshots"].append(
        {**document["snapshots"][0], "id": "other_source_2026-08-17", "score_row_count": 1}
    )
    (tmp_path / "scores2.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model Two,m2,Org C,1,0.7,0.7\n",
        encoding="utf-8",
    )
    document["snapshots"][1]["scores_file"] = "scores2.csv"
    document["snapshots"][1]["benchmark_file"] = "benchmarks.csv"
    path = write_snapshots(tmp_path, document)
    layer = build_leaderboard_snapshots(load_snapshots(path), minimal_registry())
    entries = layer["benchmarks"]["alpha"]["entries"]
    snapshots = {entry["snapshot"] for entry in entries}
    assert snapshots == {"test_source_2026-08-17", "other_source_2026-08-17"}
    assert len(layer["benchmarks"]["alpha"]["snapshots"]) == 2


def test_unmatched_benchmarks_are_counted_not_dropped(tmp_path):
    snapshot = {**registry_document()["snapshots"][0], "benchmark_count": 2}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,Alpha\nomega,Omega\n", encoding="utf-8"
    )
    layer = build_leaderboard_snapshots(load_snapshots(path), minimal_registry())
    source = layer["sources"][0]
    assert source["matched_benchmark_count"] == 1
    assert source["unmatched_benchmark_count"] == 1
    assert "alpha" in layer["benchmarks"]


def test_score_row_for_an_uncatalogued_benchmark_is_refused(tmp_path):
    # A score row must join through its own snapshot's catalog: publishing a
    # row whose benchmark the catalog never carried would invent a benchmark
    # the source itself does not record.
    snapshot = {**registry_document()["snapshots"][0], "score_row_count": 1}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "ghost,Ghost,Model One,m1,Org A,1,0.9,0.9\n",
        encoding="utf-8",
    )
    with pytest.raises(LeaderboardSnapshotError, match="absent from the catalog"):
        build_leaderboard_snapshots(load_snapshots(path), minimal_registry())


def test_a_score_row_cannot_leak_through_another_snapshots_match(tmp_path):
    # Snapshot B carries no Alpha row in its catalog, so its Alpha score rows
    # must not flow into the canonical that snapshot A happened to match: the
    # join is scoped to the snapshot that published the row.
    document = registry_document()
    second = {**document["snapshots"][0], "id": "other_source_2026-08-17", "score_row_count": 1}
    second["benchmark_count"] = 1
    document["snapshots"].append(second)
    (tmp_path / "benchmarks2.csv").write_text(
        "benchmark_id,name\nomega,Omega\n", encoding="utf-8"
    )
    (tmp_path / "scores2.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1,Org A,1,0.9,0.9\n",
        encoding="utf-8",
    )
    document["snapshots"][1]["benchmark_file"] = "benchmarks2.csv"
    document["snapshots"][1]["scores_file"] = "scores2.csv"
    path = write_snapshots(tmp_path, document)
    with pytest.raises(LeaderboardSnapshotError, match="absent from the catalog"):
        build_leaderboard_snapshots(load_snapshots(path), minimal_registry())


def test_a_score_row_whose_name_resolves_differently_than_its_id_is_refused(tmp_path):
    # The id and the name are two spellings of one benchmark; disagreement
    # between them means at least one row is wrong, so both are refused.
    snapshot = {**registry_document()["snapshots"][0], "score_row_count": 1}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Omega,Model One,m1,Org A,1,0.9,0.9\n",
        encoding="utf-8",
    )
    with pytest.raises(LeaderboardSnapshotError, match="different benchmark than its id"):
        build_leaderboard_snapshots(load_snapshots(path), minimal_registry())


def test_a_score_row_for_an_unresolved_catalog_entry_stays_external(tmp_path):
    # An ambiguous catalog name leaves the benchmark unmatched; its score
    # rows stay external with it instead of raising or guessing.
    registry = minimal_registry()
    registry["benchmarks"].append(
        {
            "id": "beta",
            "name": "Beta",
            "aliases": ["AlphaBench"],
            "domain": "reasoning",
            "url": "https://example.test/beta",
        }
    )
    snapshot = {**registry_document()["snapshots"][0], "score_row_count": 1}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,AlphaBench\n", encoding="utf-8"
    )
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,AlphaBench,Model One,m1,Org A,1,0.9,0.9\n",
        encoding="utf-8",
    )
    layer = build_leaderboard_snapshots(load_snapshots(path), registry)
    assert "alpha" not in layer["benchmarks"]
    assert layer["sources"][0]["unmatched_benchmark_count"] == 1


def test_many_to_one_aliases_count_per_catalog_row(tmp_path):
    # Two external names resolving to one canonical id are both matched: the
    # count answers "how many of this source's benchmarks resolved", not "how
    # many canonical ids were touched".
    registry = minimal_registry()
    registry["benchmarks"][0]["aliases"] = ["AlphaBench", "AlphaV2"]
    snapshot = {**registry_document()["snapshots"][0], "benchmark_count": 2}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "benchmarks.csv").write_text(
        "benchmark_id,name\nalpha,Alpha\nalpha-v2,AlphaV2\n", encoding="utf-8"
    )
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1,Org A,1,0.9,0.9\n"
        "alpha-v2,AlphaV2,Model Two,m2,Org B,2,0.8,0.8\n",
        encoding="utf-8",
    )
    layer = build_leaderboard_snapshots(load_snapshots(path), registry)
    source = layer["sources"][0]
    assert source["matched_benchmark_count"] == 2
    assert source["unmatched_benchmark_count"] == 0
    assert layer["benchmarks"]["alpha"]["entry_count"] == 2


def test_load_rejects_an_empty_required_score(tmp_path):
    snapshot = {**registry_document()["snapshots"][0], "score_row_count": 1}
    path = write_snapshots(tmp_path, registry_document(snapshots=[snapshot]))
    (tmp_path / "scores.csv").write_text(
        "benchmark_id,benchmark_name,model_name,model_id,organization_name,"
        "rank,benchmark_score,normalized_score\n"
        "alpha,Alpha,Model One,m1,Org A,1,,0.9\n",
        encoding="utf-8",
    )
    with pytest.raises(LeaderboardSnapshotError, match="empty score"):
        load_snapshots(path)


def test_the_shipped_snapshot_files_are_valid_and_complete():
    # The committed crawl snapshots must keep loading: their row counts are
    # the certification the registry's descriptions promise.
    from benchmark_radar.model_cards import load_registry

    loaded = load_snapshots(DEFAULT_SNAPSHOTS_PATH)
    by_id = {snapshot["id"]: snapshot for snapshot in loaded["snapshots"]}
    assert by_id["llm_stats_2026-08-17"]["benchmark_count"] == 687
    assert by_id["llm_stats_2026-08-17"]["score_row_count"] == 5544
    assert by_id["opencompass_hub_2026-08-17"]["benchmark_count"] == 461
    layer = build_leaderboard_snapshots(
        loaded, load_registry(Path("data/model_cards.yml"))
    )
    assert layer["snapshot_count"] == 2
    assert layer["score_row_count"] == 5544
    assert layer["sources"][0]["matched_benchmark_count"] > 0
    # Every matched benchmark carries entries, and every entry carries a
    # finite score: a NaN would reach the browser as the bare token `NaN`,
    # which is not valid JSON and would take the whole dashboard down.
    for record in layer["benchmarks"].values():
        assert record["entry_count"] > 0
        for entry in record["entries"]:
            assert abs(entry["score"]) < 1e300


def test_the_shipped_payload_contains_no_non_finite_tokens():
    import json

    layer = build_leaderboard_snapshots_layer()
    assert "NaN" not in json.dumps(layer)
    assert "Infinity" not in json.dumps(layer)