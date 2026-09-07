"""One document and citation contract for every benchmark source."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def attach_evidence(
    records: list[dict[str, Any]],
    series: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach source documents and auditable counts without merging identities."""
    summaries = {item["key"]: item.get("score_summary") or {} for item in series}
    by_record: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        by_record[row["key"]].append(row)
    result = []
    for record in records:
        source = record["source"]
        documents = {doc["source_url"]: dict(doc) for doc in record.get("documents", [])}
        # A registry page is a source document, just as a model report is.
        # Explicit document collections already identify the cited evidence;
        # the benchmark's homepage is not an extra model report.
        urls = [row.get("source_url") for row in by_record[record["key"]]]
        if "documents" not in record:
            urls.append((record.get("provenance") or {}).get("source_url"))
        for url in urls:
            if url and url not in documents:
                documents[url] = {
                    "id": f"{source}:{url}",
                    "source": source,
                    "source_url": url,
                    "document_type": "registry_page",
                    "title": record["name"],
                }
        for row in by_record[record["key"]]:
            row["source"] = source
            row["document_id"] = (documents.get(row.get("source_url")) or {}).get("id")
        summary = summaries.get(record["key"]) or {}
        result.append(
            {
                **record,
                "documents": sorted(documents.values(), key=lambda doc: doc["id"]),
                "evidence_summary": {
                    "document_count": len(documents) if documents else None,
                    "model_count": summary.get("model_count"),
                    "model_count_basis": summary.get("model_count_basis"),
                },
            }
        )
    return result


def document_registry(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Rank documentation coverage using the same cited-document identities."""
    documents = {}
    references: dict[str, list[dict[str, Any]]] = defaultdict(list)
    entries = []
    for record in records:
        cited = record.get("documents") or []
        publishers = sorted({doc.get("organization") or doc["source"] for doc in cited})
        entry = {
            "benchmark_id": record["slug"],
            "name": record["name"],
            "source": record["source"],
            "domain": next(iter(record.get("categories") or []), "other"),
            "aliases": record.get("aliases") or [],
            "released": record.get("released"),
            "url": (record.get("provenance") or {}).get("source_url"),
            "caveat": " ".join((record.get("description") or {}).values()) or None,
            "document_count": len(cited),
            "organization_count": len(publishers),
            "organizations": publishers,
            "document_ids": [doc["id"] for doc in cited],
        }
        entries.append(entry)
        for document in cited:
            documents.setdefault(document["id"], document)
            references[document["id"]].append(
                {key: entry[key] for key in ("benchmark_id", "name", "domain", "released", "url")}
            )
    entries.sort(
        key=lambda row: (
            -row["document_count"],
            -row["organization_count"],
            row["name"].casefold(),
            row["benchmark_id"],
        )
    )
    for rank, entry in enumerate(entries, 1):
        entry["rank"] = rank
        entry["document_share"] = entry["document_count"] / len(documents) if documents else 0
    return {
        "schema_version": 1,
        "benchmark_count": len(entries),
        "document_count": len(documents),
        "organization_count": len(
            {doc.get("organization") or doc["source"] for doc in documents.values()}
        ),
        "organizations": dict(
            sorted(
                Counter(
                    doc.get("organization") or doc["source"] for doc in documents.values()
                ).items()
            )
        ),
        "domains": dict(sorted(Counter(entry["domain"] for entry in entries).items())),
        "entries": entries,
        "documents": [
            {
                **documents[key],
                "benchmarks": sorted(references[key], key=lambda row: row["benchmark_id"]),
            }
            for key in sorted(documents)
        ],
        "measures": (
            "Counts distinct source documents that record each benchmark. "
            "Model reports and registry pages use the same rule. "
            "Each document counts once per benchmark record. "
            "This measures documentation coverage, not benchmark quality."
        ),
    }
