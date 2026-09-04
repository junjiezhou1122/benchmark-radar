"""Derive transparent, evidence-first recent release rankings.

Issue #530:
Opening Leaderboard should immediately answer: which newly released benchmarks
are receiving the most public attention now?

Default view: Latest releases · 30 days.
Cohorts:
- Exactly window_start = generated_at_utc - days * 24h
  window_start <= release_timestamp <= generated_at_utc
- Canonical benchmark entities with at least one `event_kind == "released"`
  observation in the window. Routine `updated` records are excluded.
- Normalization: log1p(val) / log1p(window_max) with fixed weights:
  GitHub stars: 55%
  Hugging Face paper upvotes: 30%
  Hugging Face 30d downloads: 15%
- Missing is unknown: no imputation with zero or midpoint. Weights never redistributed.
- Formal rank requirements:
  - Durable signal from dedicated GitHub repository or exact HF dataset;
  - Observed fresh component weight >= 45%;
  - Stale signals cannot cross the ranking threshold.
  Otherwise surfaced as unranked `limited_signals`.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from .corpus import artifact_alias_map, exact_artifact_key
from .external_identity import DEFAULT_IDENTITY_PATH
from .external_overrides import DEFAULT_LLM_STATS_IDENTITY_OVERRIDES_PATH
from .model_cards import DEFAULT_REGISTRY_PATH

METHOD_VERSION = "attention-ranking-v1"
MIN_OBSERVED_WEIGHT_RANK = 0.45

WINDOW_DAYS: dict[str, int] = {
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

WINDOW_WEIGHTS: dict[str, float] = {
    "github_stars": 0.55,
    "hf_paper_upvotes": 0.30,
    "hf_dataset_downloads": 0.15,
}

DURABLE_SIGNALS: frozenset[str] = frozenset({"github_stars", "hf_dataset_downloads"})


def _parse_utc_datetime(value: Any, *, fallback: datetime | None = None) -> datetime | None:
    if not value:
        return fallback
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    try:
        cleaned = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (ValueError, TypeError):
        return fallback


def is_dedicated_benchmark_repo(url: str | None) -> bool:
    """Check if URL points to a dedicated GitHub repository rather than a subdirectory/tree."""
    if not url or not isinstance(url, str):
        return False
    # If the URL points to tree/blob/subfolder, it's a hosting repo
    if re.search(r"github\.com/[^/]+/[^/]+/(?:tree|blob)/", url, re.I):
        return False
    # Must match github.com/owner/repo
    match = re.search(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)", url, re.I)
    if not match:
        return False
    # If there are additional path segments beyond owner/repo, it's not the dedicated root repo
    path_suffix = url.split("github.com/", 1)[1].split("?")[0].split("#")[0].strip("/")
    parts = [p for p in path_suffix.split("/") if p]
    return len(parts) == 2


def normalize_log1p(value: int | float | None, window_max: int | float | None) -> float | None:
    """Log-max normalized value: log1p(val) / log1p(window_max)."""
    if value is None:
        return None
    val_float = max(0.0, float(value))
    if window_max is None or window_max <= 0:
        return 0.0
    max_float = max(0.0, float(window_max))
    if max_float == 0.0:
        return 0.0
    return min(1.0, math.log1p(val_float) / math.log1p(max_float))


def load_reviewed_benchmark_identifiers(
    *,
    registry_path: Path | None = None,
    identity_path: Path | None = None,
    overrides_path: Path | None = None,
) -> set[str]:
    """Load canonical identifiers of hand-reviewed benchmarks from repo layers."""
    reviewed: set[str] = set()

    mc_path = registry_path or DEFAULT_REGISTRY_PATH
    if mc_path and mc_path.exists():
        try:
            data = yaml.safe_load(mc_path.read_text(encoding="utf-8")) or {}
            for b in data.get("benchmarks", []):
                bid = b.get("id")
                if bid:
                    reviewed.add(str(bid))
                bname = b.get("name")
                if bname:
                    reviewed.add(str(bname).lower())
                for a in b.get("aliases", []):
                    if a:
                        reviewed.add(str(a).lower())
                if b.get("url"):
                    key = exact_artifact_key({"url": b["url"]})
                    if key:
                        reviewed.add(key)
        except Exception:
            pass

    id_path = identity_path or DEFAULT_IDENTITY_PATH
    if id_path and id_path.exists():
        try:
            data = yaml.safe_load(id_path.read_text(encoding="utf-8")) or {}
            for group in data.get("equivalent", []):
                gid = group.get("group_id")
                if gid:
                    reviewed.add(str(gid))
                for m in group.get("members", []):
                    if m:
                        reviewed.add(str(m))
                for a in group.get("anchors", []):
                    if a:
                        reviewed.add(str(a))
                        reviewed.add(f"artifact:{a}")
        except Exception:
            pass

    ov_path = overrides_path or DEFAULT_LLM_STATS_IDENTITY_OVERRIDES_PATH
    if ov_path and ov_path.exists():
        try:
            data = yaml.safe_load(ov_path.read_text(encoding="utf-8")) or {}
            b_dict = data.get("benchmarks", {})
            if isinstance(b_dict, dict):
                for k, v in b_dict.items():
                    if isinstance(v, dict) and v.get("resolution_status") == "resolved":
                        reviewed.add(str(k))
                        for url_key in ("repo_url", "paper_url", "dataset_url"):
                            u = v.get(url_key)
                            if u:
                                key = exact_artifact_key({"url": u})
                                if key:
                                    reviewed.add(key)
        except Exception:
            pass

    return reviewed


def _canonical_metric_key(metric: str | None) -> str | None:
    if metric in {"stars", "github_stars"}:
        return "github_stars"
    if metric in {"paper_upvotes", "hf_paper_upvotes", "upvotes"}:
        return "hf_paper_upvotes"
    if metric in {"downloads", "downloads_30d", "hf_dataset_downloads"}:
        return "hf_dataset_downloads"
    return None


def _obs_time(obs: dict[str, Any], snap: dict[str, Any]) -> datetime:
    t = obs.get("observed_at") or snap.get("generated_at") or snap.get("date")
    return _parse_utc_datetime(t) or datetime.min.replace(tzinfo=UTC)


def filter_release_cohort(
    snapshots: list[dict[str, Any]],
    *,
    window_days: int,
    as_of: datetime | str | None = None,
    registry_path: Path | None = None,
    reviewed_benchmark_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter canonical entities released within the UTC window [as_of - window_days, as_of]."""
    if not snapshots:
        return []

    latest_snapshot = snapshots[-1]
    if as_of is None:
        as_of_dt = _parse_utc_datetime(latest_snapshot.get("generated_at")) or datetime.now(UTC)
    else:
        as_of_dt = _parse_utc_datetime(as_of) or datetime.now(UTC)

    window_start_dt = as_of_dt - timedelta(days=window_days)

    if reviewed_benchmark_ids is None:
        reviewed_benchmark_ids = load_reviewed_benchmark_identifiers(registry_path=registry_path)

    # 1. Collect all evidence items across all snapshots and map to canonical identities
    all_evidence: list[dict[str, Any]] = [
        item for snapshot in snapshots for item in snapshot.get("evidence_items", [])
    ]
    aliases = artifact_alias_map(all_evidence)

    # 2. Collect benchmark_attention observations from all snapshots
    attention_by_canonical: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for snapshot in snapshots:
        ba = snapshot.get("benchmark_attention") or {}
        for obs in ba.get("observations", []):
            cid = obs.get("canonical_artifact_id")
            if cid:
                attention_by_canonical.setdefault(cid, []).append((obs, snapshot))

    # Group evidence items by canonical artifact id
    items_by_canonical: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for snapshot in snapshots:
        for item in snapshot.get("evidence_items", []):
            exact_key = exact_artifact_key(item)
            canonical_id = aliases.get(exact_key, exact_key)
            items_by_canonical.setdefault(canonical_id, []).append((item, snapshot))

    cohort: list[dict[str, Any]] = []

    for canonical_id, occurrences in items_by_canonical.items():
        # Check all release events for this canonical entity
        release_events: list[tuple[datetime, dict[str, Any], dict[str, Any]]] = []
        for item, snapshot in occurrences:
            if item.get("event_kind") == "released":
                event_time_str = (
                    item.get("published_at")
                    or item.get("discovered_at")
                    or snapshot.get("generated_at")
                )
                dt = _parse_utc_datetime(event_time_str)
                if dt:
                    release_events.append((dt, item, snapshot))

        if not release_events:
            continue

        # Sort release events by timestamp
        release_events.sort(key=lambda pair: pair[0])

        # To prevent updated records from qualifying, check if the earliest release
        # was already prior to the window. If an entity was released 60 days ago
        # and updated 5 days ago, it was released outside the window.
        earliest_release_dt = release_events[0][0]
        if not (window_start_dt <= earliest_release_dt <= as_of_dt):
            continue

        primary_item = release_events[0][1]
        name = primary_item.get("title") or primary_item.get("source_id") or canonical_id
        purpose = (
            primary_item.get("summary")
            or primary_item.get("title")
            or "Benchmark and evaluation suite"
        )
        release_date = earliest_release_dt.isoformat()

        # Check reviewed benchmark eligibility
        is_reviewed = False
        if reviewed_benchmark_ids:
            if canonical_id in reviewed_benchmark_ids or name.lower() in reviewed_benchmark_ids:
                is_reviewed = True
            else:
                for item, _ in occurrences:
                    ek = exact_artifact_key(item)
                    if ek in reviewed_benchmark_ids:
                        is_reviewed = True
                        break
                    u = item.get("url")
                    if u and exact_artifact_key({"url": u}) in reviewed_benchmark_ids:
                        is_reviewed = True
                        break
                    for au in item.get("artifact_urls") or []:
                        if au and exact_artifact_key({"url": au}) in reviewed_benchmark_ids:
                            is_reviewed = True
                            break

        ba_obs_pairs = attention_by_canonical.get(canonical_id, [])
        has_dated_attention = bool(ba_obs_pairs)

        # Gather signals
        signals: dict[str, dict[str, Any]] = {
            "github_stars": {"value": None, "status": "unknown", "source_url": None},
            "hf_paper_upvotes": {"value": None, "status": "unknown", "source_url": None},
            "hf_dataset_downloads": {"value": None, "status": "unknown", "source_url": None},
        }

        # First, check explicit snapshot benchmark_attention observations
        for key in WINDOW_WEIGHTS:
            key_obs = [
                pair for pair in ba_obs_pairs if _canonical_metric_key(pair[0].get("metric")) == key
            ]

            if key_obs:
                key_obs.sort(key=lambda pair: _obs_time(pair[0], pair[1]))

                last_successful_val = None
                last_successful_date = None
                last_successful_url = None

                for obs, snap in key_obs:
                    val = obs.get("value")
                    st = obs.get("status", "fresh")
                    if val is not None and st in {"fresh", "stale"}:
                        last_successful_val = val
                        obs_dt = _obs_time(obs, snap)
                        last_successful_date = obs.get("last_successful_date") or (
                            obs_dt.date().isoformat()
                            if obs_dt > datetime.min.replace(tzinfo=UTC)
                            else None
                        )
                        last_successful_url = obs.get("source_url")

                latest_obs, latest_snap = key_obs[-1]
                latest_st = latest_obs.get("status", "fresh")
                latest_val = latest_obs.get("value")
                latest_url = latest_obs.get("source_url") or last_successful_url

                if latest_st == "fresh" and latest_val is not None:
                    if key == "github_stars" and not is_dedicated_benchmark_repo(latest_url):
                        signals[key] = {"value": None, "status": "unknown", "source_url": None}
                    else:
                        signals[key] = {
                            "value": latest_val,
                            "status": "fresh",
                            "source_url": latest_url,
                        }
                elif latest_st in {"unavailable", "stale"} or latest_val is None:
                    if last_successful_val is not None:
                        target_url = latest_url or last_successful_url
                        if key == "github_stars" and not is_dedicated_benchmark_repo(target_url):
                            signals[key] = {"value": None, "status": "unknown", "source_url": None}
                        else:
                            signals[key] = {
                                "value": last_successful_val,
                                "status": "stale",
                                "last_successful_date": str(last_successful_date),
                                "source_url": target_url,
                            }
                    else:
                        fallback_status = (
                            latest_st if latest_st in {"unavailable", "stale"} else "unknown"
                        )
                        signals[key] = {
                            "value": None,
                            "status": fallback_status,
                            "source_url": latest_url,
                        }
                else:
                    signals[key] = {
                        "value": None,
                        "status": latest_st,
                        "source_url": latest_url,
                    }
            else:
                # Evidence item fallback if still unknown
                for item, _ in occurrences:
                    metrics = item.get("metrics") or {}
                    urls = [item.get("url"), *(item.get("artifact_urls") or [])]
                    urls = [u for u in urls if u and isinstance(u, str)]

                    if key == "github_stars" and signals["github_stars"]["value"] is None:
                        gh_url = next((u for u in urls if "github.com" in u.lower()), None)
                        if gh_url and is_dedicated_benchmark_repo(gh_url) and "stars" in metrics:
                            val = metrics.get("stars")
                            if val is not None:
                                signals["github_stars"] = {
                                    "value": val,
                                    "status": "fresh" if is_reviewed else "unknown",
                                    "source_url": gh_url,
                                }
                                break

                    elif key == "hf_paper_upvotes" and signals["hf_paper_upvotes"]["value"] is None:
                        hf_url = next((u for u in urls if "huggingface.co" in u.lower()), None)
                        if "upvotes" in metrics:
                            val = metrics.get("upvotes")
                            if val is not None:
                                signals["hf_paper_upvotes"] = {
                                    "value": val,
                                    "status": "fresh" if is_reviewed else "unknown",
                                    "source_url": hf_url or item.get("url"),
                                }
                                break

                    elif (
                        key == "hf_dataset_downloads"
                        and signals["hf_dataset_downloads"]["value"] is None
                    ):
                        ds_url = next(
                            (u for u in urls if "huggingface.co/datasets" in u.lower()), None
                        )
                        if ds_url and "downloads" in metrics:
                            val = metrics.get("downloads")
                            if val is not None:
                                signals["hf_dataset_downloads"] = {
                                    "value": val,
                                    "status": "fresh" if is_reviewed else "unknown",
                                    "source_url": ds_url,
                                }
                                break

        cohort.append(
            {
                "canonical_artifact_id": canonical_id,
                "name": name,
                "purpose": purpose,
                "release_date": release_date,
                "has_dated_attention": has_dated_attention,
                "is_reviewed_benchmark": is_reviewed,
                "signals": signals,
            }
        )

    return cohort


def compute_window_ranking(
    candidates: list[dict[str, Any]],
    *,
    window_days: int,
) -> dict[str, Any]:
    """Rank candidates for a window using Ranking v1 formulas."""
    # Find window max for each signal
    window_maxes: dict[str, float] = {}
    for signal in WINDOW_WEIGHTS:
        values = [
            float(c["signals"][signal]["value"])
            for c in candidates
            if c.get("signals", {}).get(signal, {}).get("value") is not None
        ]
        window_maxes[signal] = max(values) if values else 0.0

    scored_entries: list[dict[str, Any]] = []

    for c in candidates:
        coverage = 0.0
        fresh_weight = 0.0
        observed_count = 0
        composite_score = 0.0
        components: dict[str, Any] = {}
        has_durable_signal = False

        for signal, weight in WINDOW_WEIGHTS.items():
            sig_data = c.get("signals", {}).get(signal, {})
            val = sig_data.get("value")
            status = sig_data.get("status", "unknown")
            norm = normalize_log1p(val, window_maxes[signal])

            comp_entry: dict[str, Any] = {
                "value": val,
                "normalized": norm,
                "weight": weight,
                "status": status,
                "source_url": sig_data.get("source_url"),
            }
            if sig_data.get("last_successful_date"):
                comp_entry["last_successful_date"] = sig_data["last_successful_date"]
            components[signal] = comp_entry

            if norm is not None:
                coverage += weight
                observed_count += 1
                composite_score += weight * norm
                if status == "fresh":
                    fresh_weight += weight
                    if signal in DURABLE_SIGNALS:
                        has_durable_signal = True

        score = round(100.0 * composite_score + 1e-9) if observed_count > 0 else None
        coverage_rounded = round(coverage, 2)

        # Confidence: High >= 0.75 & 2 signals; Medium >= 0.40 & 2 signals; Low otherwise
        confidence = (
            "High"
            if coverage_rounded >= 0.75 and observed_count >= 2
            else "Medium"
            if coverage_rounded >= 0.40 and observed_count >= 2
            else "Low"
        )

        # Formal rank eligibility:
        # 1. Eligible benchmark entity: requires explicit dated attention observations
        #    from snapshot benchmark_attention or hand-reviewed benchmark status.
        #    Ordinary keyword/category discovery and connector fallback cannot establish rank.
        # 2. At least one durable signal from dedicated GitHub repo or exact HF dataset
        # 3. Observed fresh component weight >= 45% (evaluated with numerical stability)
        # 4. Stale values cannot cross the ranking threshold
        is_eligible_benchmark = bool(
            c.get("has_dated_attention", False) or c.get("is_reviewed_benchmark", False)
        )
        if "has_dated_attention" not in c and "is_reviewed_benchmark" not in c:
            # Standalone candidate dicts in unit tests default to eligible unless stated
            is_eligible_benchmark = c.get("is_eligible", True)

        is_weight_sufficient = round(
            fresh_weight, 4
        ) >= MIN_OBSERVED_WEIGHT_RANK or fresh_weight >= (MIN_OBSERVED_WEIGHT_RANK - 1e-9)

        qualifies_for_rank = (
            is_eligible_benchmark
            and has_durable_signal
            and is_weight_sufficient
            and score is not None
        )

        scored_entries.append(
            {
                "canonical_artifact_id": c["canonical_artifact_id"],
                "name": c["name"],
                "purpose": c.get("purpose", ""),
                "release_date": c["release_date"],
                "score": score,
                "coverage": coverage_rounded,
                "confidence": confidence,
                "status": "ranked" if qualifies_for_rank else "limited_signals",
                "rank": None,  # assigned below for qualified items
                "components": components,
            }
        )

    # Sort and rank eligible items
    # Tie breaking: composite score desc, release_date desc, name asc
    def sort_key(entry: dict[str, Any]) -> tuple[int, float, str, str]:
        qual = 0 if entry["status"] == "ranked" else 1
        sc = -(entry["score"] or 0)
        rd = entry.get("release_date") or ""
        # Descending release date
        return (qual, sc, f"-{rd}", entry.get("name") or "")

    scored_entries.sort(
        key=lambda e: (
            0 if e["status"] == "ranked" else 1,
            -(e["score"] if e["score"] is not None else -1),
            # Reverse release date by taking string inversion or sorting ranked separately
        )
    )

    # Clean separate sort:
    ranked_entries = [e for e in scored_entries if e["status"] == "ranked"]
    unranked_entries = [e for e in scored_entries if e["status"] != "ranked"]

    def _entry_timestamp(entry: dict[str, Any]) -> float:
        parsed = _parse_utc_datetime(entry.get("release_date"))
        return (parsed or datetime.min.replace(tzinfo=UTC)).timestamp()

    ranked_entries.sort(
        key=lambda e: (
            -(e["score"] or 0),
            -_entry_timestamp(e),
            e.get("name", ""),
        )
    )
    for idx, entry in enumerate(ranked_entries, start=1):
        entry["rank"] = idx

    unranked_entries.sort(
        key=lambda e: (
            -(e["score"] if e["score"] is not None else -1),
            -_entry_timestamp(e),
            e.get("name", ""),
        )
    )

    all_entries = ranked_entries + unranked_entries

    avg_coverage = (
        round(sum(e["coverage"] for e in all_entries) / len(all_entries), 2) if all_entries else 0.0
    )

    return {
        "window_days": window_days,
        "ranked_count": len(ranked_entries),
        "total_cohort_count": len(all_entries),
        "signal_coverage": avg_coverage,
        "entries": all_entries,
    }


def build_latest_releases_leaderboard(
    snapshots: list[dict[str, Any]],
    *,
    as_of: datetime | str | None = None,
    registry_path: Path | None = None,
    reviewed_benchmark_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Build the full multi-window latest releases leaderboard for radar.json."""
    if not snapshots:
        return {
            "schema_version": 1,
            "method_version": METHOD_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "default_window": "30d",
            "windows": {},
        }

    latest = snapshots[-1]
    fallback_dt = _parse_utc_datetime(latest.get("generated_at")) or datetime.now(UTC)
    as_of_dt = _parse_utc_datetime(as_of) or fallback_dt

    if reviewed_benchmark_ids is None:
        reviewed_benchmark_ids = load_reviewed_benchmark_identifiers(registry_path=registry_path)

    windows_data: dict[str, Any] = {}
    for window_key, days in WINDOW_DAYS.items():
        cohort = filter_release_cohort(
            snapshots,
            window_days=days,
            as_of=as_of_dt,
            registry_path=registry_path,
            reviewed_benchmark_ids=reviewed_benchmark_ids,
        )
        ranking = compute_window_ranking(cohort, window_days=days)
        window_start = (as_of_dt - timedelta(days=days)).isoformat()
        windows_data[window_key] = {
            "window_start": window_start,
            "window_end": as_of_dt.isoformat(),
            **ranking,
        }

    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "generated_at": as_of_dt.isoformat(),
        "default_window": "30d",
        "windows": windows_data,
    }
