"""Crawled leaderboard snapshots (aggregator layer).

`benchmark_scores.py` answers "what have reported scores done" from one kind of
number: a value read verbatim out of a cited document, joined only where
instrument and protocol are identical. That layer cannot hold a leaderboard
dump, because a leaderboard row carries no protocol. LLM Stats does not record
how many shots a model ran, on which harness, with what tool access, or how
many attempts, and the silence rule the score file states applies here with at
least the same force: an unstated condition is never treated as equal to
another unstated condition.

This module publishes the second kind of number beside it, deliberately
unjoined: point-in-time snapshots of what public aggregator leaderboards
reported, kept in `data/leaderboard_snapshots.yml` and committed CSV files. A
snapshot row is a fact about what an aggregator published on a crawl date, and
nothing more. The payload labels it as such and never lets it join the curated
score series.

WHAT THE LAYER DOES AND DOES NOT DO

`benchmarks`
    The merged view the layer actually supports: for every canonical benchmark
    (an id the model card registry declares) that an external leaderboard also
    carries, all crawled rows are published together, each labeled with its
    snapshot, rank, and the aggregator's own `verified` and `self_reported`
    flags when the source provides them. Rows from different sources are never
    ranked against each other: they come from different evaluators under
    different unstated protocols, and presenting a merged ordering would be
    inventing the comparison the layer refuses to make. The consumer draws
    one ordered table per source.

`unmatched`
    External benchmarks with no canonical id are counted, not dropped: the
    full rows remain in the committed snapshot files, addressable by their
    external id. The count exists so a reader can see that "461 benchmarks"
    and "5544 score rows" did not silently collapse into the canonical set.

`headroom`, `best`, `trend`
    Never computed here. A crawled number has no documented protocol, so it
    cannot be compared with another crawled number to claim movement, and it
    cannot be joined to the curated series to extend one. The layer reports
    what the sources reported and leaves interpretation to the reader.

Completeness is certified, not assumed: each registry entry declares the row
counts its files must contain, and the loader refuses to publish a file whose
count drifts from the declaration, because a truncated or partial rerun would
otherwise look identical to a complete snapshot.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

SNAPSHOTS_SCHEMA_VERSION = 1

DEFAULT_SNAPSHOTS_PATH = Path("data/leaderboard_snapshots.yml")

_REQUIRED_SNAPSHOT_FIELDS = (
    "id",
    "source",
    "source_url",
    "crawled_at",
    "benchmark_file",
    "benchmark_count",
    "columns",
)
_REQUIRED_COLUMN_FIELDS = ("benchmark_id", "benchmark_name")

# How a canonical id is looked up from an external name. The registry carries
# the vocabulary, and the score file carries the join discipline; this layer
# only joins on the id, never on the number.
_ALIAS_PRIORITY = ("name", "aliases")


class LeaderboardSnapshotError(ValueError):
    """Raised when the snapshot registry or a declared file is inconsistent."""


def _require(value: Any, fields: tuple[str, ...], *, label: str) -> None:
    if not isinstance(value, dict):
        raise LeaderboardSnapshotError(f"{label} must be a mapping")
    missing = [
        field
        for field in fields
        if value.get(field) is None or (isinstance(value[field], str) and not value[field].strip())
    ]
    if missing:
        raise LeaderboardSnapshotError(f"{label} is missing fields: {', '.join(missing)}")


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
            rows = [{key: (value or "") for key, value in row.items()} for row in reader]
    except (OSError, csv.Error) as error:
        raise LeaderboardSnapshotError(f"{path}: cannot read CSV: {error}") from error
    if not header or not rows:
        raise LeaderboardSnapshotError(f"{path}: CSV has no header or no data rows")
    return header, rows


def _require_column(header: list[str], column: str, *, path: Path, label: str) -> None:
    if column not in header:
        raise LeaderboardSnapshotError(f"{path}: {label} column {column!r} missing from header")


def _finite_float(value: str, *, path: Path, label: str) -> float | None:
    if not value.strip():
        return None
    try:
        parsed = float(value)
    except ValueError as error:
        raise LeaderboardSnapshotError(
            f"{path}: {label} value {value!r} is not a number"
        ) from error
    if not math.isfinite(parsed):
        raise LeaderboardSnapshotError(f"{path}: {label} value {value!r} is not finite")
    return parsed


def _require_iso_timestamp(value: str, *, label: str) -> str:
    if not value.strip():
        raise LeaderboardSnapshotError(f"{label} must not be empty")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise LeaderboardSnapshotError(f"{label} {value!r} is not an ISO timestamp") from error
    return value


def _load_snapshot_files(snapshot: dict[str, Any], base: Path) -> dict[str, Any]:
    """Load and validate one declared snapshot's committed CSV files.

    Row counts are certified against the registry declaration, so a truncated
    copy, a partial rerun, or an accidental append fails loudly instead of
    publishing a snapshot whose completeness cannot be stated.
    """
    path = base / str(snapshot["benchmark_file"])
    header, rows = _read_csv_rows(path)
    columns = snapshot["columns"]
    benchmark_columns = snapshot.get("benchmark_columns") or columns
    _require_column(
        header, str(benchmark_columns["benchmark_id"]), path=path, label="benchmark_id"
    )
    _require_column(
        header, str(benchmark_columns["benchmark_name"]), path=path, label="benchmark_name"
    )
    expected = int(snapshot["benchmark_count"])
    if len(rows) != expected:
        raise LeaderboardSnapshotError(
            f"{path}: {len(rows)} rows, registry declares {expected}"
        )
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        benchmark_id = row[str(benchmark_columns["benchmark_id"])].strip()
        if not benchmark_id:
            raise LeaderboardSnapshotError(f"{path}: row {index} has an empty benchmark id")
        if benchmark_id in seen_ids:
            raise LeaderboardSnapshotError(f"{path}: duplicate benchmark id {benchmark_id!r}")
        seen_ids.add(benchmark_id)
    benchmark_rows = rows

    score_rows: list[dict[str, str]] | None = None
    if snapshot.get("scores_file"):
        scores_path = base / str(snapshot["scores_file"])
        score_header, score_rows = _read_csv_rows(scores_path)
        _require_column(
            score_header, str(columns["benchmark_id"]), path=scores_path, label="benchmark_id"
        )
        _require_column(
            score_header, str(columns["benchmark_name"]), path=scores_path, label="benchmark_name"
        )
        _require_column(score_header, str(columns["model"]), path=scores_path, label="model")
        _require_column(
            score_header, str(columns["organization"]), path=scores_path, label="organization"
        )
        _require_column(score_header, str(columns["score"]), path=scores_path, label="score")
        if "score_row_count" not in snapshot:
            raise LeaderboardSnapshotError(
                f"{scores_path}: scores_file declared without score_row_count"
            )
        expected_scores = int(snapshot["score_row_count"])
        if len(score_rows) != expected_scores:
            raise LeaderboardSnapshotError(
                f"{scores_path}: {len(score_rows)} rows, registry declares {expected_scores}"
            )
        # Row identity is (benchmark_id, model_id) when the source carries an
        # id, because distinct dated checkpoints can share a display name. The
        # name is display vocabulary; the id is what a row actually is.
        model_key = str(columns.get("model_id") or columns["model"])
        pairs: set[tuple[str, str]] = set()
        for index, row in enumerate(score_rows):
            benchmark_id = row[str(columns["benchmark_id"])].strip()
            model = row[model_key].strip()
            if not benchmark_id or not model:
                raise LeaderboardSnapshotError(
                    f"{scores_path}: row {index} has an empty benchmark id or model"
                )
            pair = (benchmark_id, model)
            if pair in pairs:
                raise LeaderboardSnapshotError(
                    f"{scores_path}: duplicate row for benchmark {benchmark_id!r} model {model!r}"
                )
            pairs.add(pair)
            score_value = row[str(columns["score"])]
            if not score_value.strip():
                raise LeaderboardSnapshotError(
                    f"{scores_path}: row {index} has an empty score"
                )
            _finite_float(
                score_value, path=scores_path, label=f"row {index} score"
            )
            normalized = row.get(str(columns.get("normalized_score") or ""))
            if normalized:
                _finite_float(normalized, path=scores_path, label=f"row {index} normalized_score")
            rank = row.get(str(columns.get("rank") or ""))
            if rank and not rank.strip().isdigit():
                raise LeaderboardSnapshotError(
                    f"{scores_path}: row {index} rank {rank!r} is not a positive integer"
                )

    return {"benchmark_rows": benchmark_rows, "score_rows": score_rows}


def load_snapshots(path: Path = DEFAULT_SNAPSHOTS_PATH) -> dict[str, Any]:
    """Read and validate the snapshot registry and every file it declares."""
    if not path.exists():
        raise LeaderboardSnapshotError(f"{path}: snapshot registry not found")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise LeaderboardSnapshotError(f"{path}: snapshot registry must be a mapping")
    version = document.get("schema_version")
    if version != SNAPSHOTS_SCHEMA_VERSION:
        raise LeaderboardSnapshotError(f"{path}: unsupported schema_version {version!r}")

    snapshots = document.get("snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise LeaderboardSnapshotError(f"{path}: snapshots must be a non-empty array")

    base = path.parent
    loaded: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(snapshots):
        label = f"{path}: snapshot {index}"
        _require(entry, _REQUIRED_SNAPSHOT_FIELDS, label=label)
        snapshot_id = str(entry["id"])
        if snapshot_id in seen_ids:
            raise LeaderboardSnapshotError(f"{label} repeats snapshot id {snapshot_id!r}")
        seen_ids.add(snapshot_id)
        columns = entry["columns"]
        benchmark_columns = entry.get("benchmark_columns") or columns
        _require(columns, _REQUIRED_COLUMN_FIELDS, label=f"{label} columns")
        _require(benchmark_columns, _REQUIRED_COLUMN_FIELDS, label=f"{label} benchmark_columns")
        _require_iso_timestamp(str(entry["crawled_at"]), label=f"{label} crawled_at")
        files = _load_snapshot_files(entry, base)
        loaded.append(
            {
                "id": snapshot_id,
                "source": str(entry["source"]),
                "source_url": str(entry["source_url"]),
                "crawled_at": str(entry["crawled_at"]),
                "description": str(entry.get("description") or ""),
                "benchmark_file": str(entry["benchmark_file"]),
                "benchmark_count": int(entry["benchmark_count"]),
                "scores_file": str(entry["scores_file"]) if entry.get("scores_file") else None,
                "score_row_count": int(entry["score_row_count"]) if entry.get("scores_file") else 0,
                "columns": {str(key): str(value) for key, value in columns.items()},
                "benchmark_columns": {
                    str(key): str(value) for key, value in benchmark_columns.items()
                },
                "benchmark_rows": files["benchmark_rows"],
                "score_rows": files["score_rows"],
            }
        )

    return {"schema_version": SNAPSHOTS_SCHEMA_VERSION, "snapshots": loaded}


def _canonical_alias_map(registry: dict[str, Any]) -> dict[str, str]:
    """External names to canonical ids, from the registry's own vocabulary.

    Case-insensitive by construction: external spellings are not a controlled
    vocabulary, and "mmlu" and "MMLU" are the same benchmark without being the
    same string. A name matching more than one canonical id is left unmapped
    rather than guessed, and reported, because the alternative silently
    merges two different benchmarks into one id.
    """
    mapping: dict[str, str] = {}
    collisions: set[str] = set()
    for benchmark in registry["benchmarks"]:
        benchmark_id = str(benchmark["id"])
        candidates = [str(benchmark["name"])]
        candidates.extend(str(alias) for alias in (benchmark.get("aliases") or []))
        for candidate in candidates:
            key = candidate.strip().lower()
            if not key:
                continue
            if key in mapping and mapping[key] != benchmark_id:
                collisions.add(key)
            else:
                mapping[key] = benchmark_id
    for key in collisions:
        mapping.pop(key, None)
    return mapping


def _match_canonical(name: str, alias_map: dict[str, str]) -> str | None:
    key = name.strip().lower()
    if key not in alias_map:
        return None
    return alias_map[key]


def build_leaderboard_snapshots(
    snapshots: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the aggregator-snapshot layer the dashboard draws.

    The registry is optional and is only used for id mapping: a checkout
    without the curated registry still publishes the crawled layer, because
    the snapshot files carry their own names and sources and do not cite the
    registry the way the score layer's `source_id` cross-check does.
    """
    alias_map = _canonical_alias_map(registry) if registry else {}
    canonical_names = {
        str(benchmark["id"]): str(benchmark["name"])
        for benchmark in (registry["benchmarks"] if registry else [])
    }

    sources: list[dict[str, Any]] = []
    matched: dict[str, dict[str, Any]] = {}

    for snapshot in snapshots["snapshots"]:
        columns = snapshot["columns"]
        benchmark_columns = snapshot["benchmark_columns"]
        catalog_name_column = str(benchmark_columns["benchmark_name"])
        catalog_id_column = str(benchmark_columns["benchmark_id"])
        scores_name_column = str(columns["benchmark_name"])
        scores_file = Path(str(snapshot["scores_file"])) if snapshot["scores_file"] else None

        matched_ids: set[str] = set()
        # The catalog row is the authoritative identity: a score row joins
        # through its own snapshot's catalog entry, never through a benchmark
        # another snapshot happened to match. The id resolves the name.
        external_id_to_canonical: dict[str, str | None] = {}
        for row in snapshot["benchmark_rows"]:
            external_id = row[catalog_id_column].strip()
            canonical = _match_canonical(row[catalog_name_column], alias_map)
            external_id_to_canonical[external_id] = canonical
            if canonical is not None:
                matched_ids.add(canonical)
                matched.setdefault(
                    canonical,
                    {"benchmark_id": canonical, "entries": [], "snapshots": set()},
                )
                matched[canonical]["snapshots"].add(snapshot["id"])

        for row in snapshot["score_rows"] or []:
            external_id = row[str(columns["benchmark_id"])].strip()
            if external_id not in external_id_to_canonical:
                # Unknown ids are refused: a score row for a benchmark this
                # snapshot's catalog never carried would otherwise publish a
                # benchmark whose name the source itself does not record.
                raise LeaderboardSnapshotError(
                    f"{scores_file}: score row references benchmark {external_id!r} "
                    f"absent from the catalog"
                )
            canonical = external_id_to_canonical[external_id]
            if canonical is None:
                # The catalog entry could not resolve (unknown or ambiguous
                # name); its score rows stay external with it.
                continue
            if _match_canonical(row[scores_name_column], alias_map) != canonical:
                raise LeaderboardSnapshotError(
                    f"{scores_file}: score row for {external_id!r} has a name that "
                    f"resolves to a different benchmark than its id"
                )
            entry: dict[str, Any] = {
                "snapshot": snapshot["id"],
                "model": row[str(columns["model"])].strip(),
                "organization": row[str(columns["organization"])].strip(),
                "score": _finite_float(
                    row[str(columns["score"])], path=scores_file, label="score"
                ),
            }
            if columns.get("model_id"):
                model_id = row.get(str(columns["model_id"]))
                if model_id and model_id.strip():
                    entry["model_id"] = model_id.strip()
            if columns.get("rank"):
                rank = row.get(str(columns["rank"]))
                entry["rank"] = int(rank) if rank and rank.strip().isdigit() else None
            if columns.get("normalized_score"):
                normalized = _finite_float(
                    row.get(str(columns["normalized_score"])),
                    path=scores_file,
                    label="normalized_score",
                )
                if normalized is not None:
                    entry["normalized_score"] = normalized
            if "verified" in row and row["verified"].strip():
                entry["verified"] = row["verified"].strip()
            if "self_reported" in row and row["self_reported"].strip():
                entry["self_reported"] = row["self_reported"].strip()
            matched[canonical]["entries"].append(entry)

        external_ids = {row[catalog_id_column].strip() for row in snapshot["benchmark_rows"]}
        matched_external_ids = {
            external_id
            for external_id, canonical in external_id_to_canonical.items()
            if canonical is not None
        }
        sources.append(
            {
                "id": snapshot["id"],
                "source": snapshot["source"],
                "source_url": snapshot["source_url"],
                "crawled_at": snapshot["crawled_at"],
                "description": snapshot["description"],
                "benchmark_count": snapshot["benchmark_count"],
                "score_row_count": snapshot["score_row_count"],
                # Counted per catalog row, not per canonical id: two external
                # names resolving to one canonical id are both matched.
                "matched_benchmark_count": len(matched_external_ids),
                "unmatched_benchmark_count": len(external_ids) - len(matched_external_ids),
            }
        )

    benchmark_payload = {}
    for canonical, record in sorted(matched.items()):
        record["entries"].sort(key=lambda entry: (entry["snapshot"], -(entry["score"] or 0)))
        benchmark_payload[canonical] = {
            "benchmark_id": canonical,
            "name": canonical_names.get(canonical, canonical),
            "entry_count": len(record["entries"]),
            "snapshots": sorted(record["snapshots"]),
            "entries": record["entries"],
        }

    return {
        "schema_version": SNAPSHOTS_SCHEMA_VERSION,
        "snapshot_count": len(sources),
        "score_row_count": sum(snapshot["score_row_count"] for snapshot in snapshots["snapshots"]),
        "sources": sources,
        "benchmarks": benchmark_payload,
        "measures": (
            "Scores as reported to third-party aggregator leaderboards, captured at the "
            "crawl timestamps above. A row carries no protocol: the number of shots, "
            "harness, tool access, and attempt treatment are not stated by the source, "
            "so these rows never join each other or the curated document readings."
        ),
        "join_rule": (
            "Rows are published per source, never ranked across sources, because different "
            "evaluators under unstated protocols are not a comparison. Only the benchmark "
            "identity joins: an external name mapped onto a canonical id via the model "
            "card registry's aliases."
        ),
    }


def build_leaderboard_snapshots_layer(
    path: Path = DEFAULT_SNAPSHOTS_PATH,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_leaderboard_snapshots(load_snapshots(path), registry)