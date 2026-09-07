# Benchmark Radar principles

## The product covers 1,259+ benchmark records across 4+ sources

This is the operating scale of Benchmark Radar. It is not a small collection
of benchmarks from model cards. Every benchmark-facing chart, search, table,
count, and export must start from the full population across all sources.

The current population is the catalog records in `benchmark-index.json` plus
the curated score tracks in `radar.json`: 1,259 records across four sources at
the time this rule was introduced. Rebuild the data and calculate the current
total and source count. Never hard-code these numbers into the interface;
the corpus and its source coverage should be able to grow.

**If a main surface contains only a few dozen benchmarks, assume records are
missing and investigate. Do not present that subset as Benchmark Radar.**

Check which sources, records, and fields disappeared at each join or filter.
A successful render, plausible Pareto frontier, or passing test does not excuse
missing most of the population. A chart and the browser beside it must use the
same record universe and respond consistently to the user's filters.

## Frontier and its score ranking require a reported score

The user explicitly requested this filter: **exclude benchmarks with no numeric
reported score from Benchmark Frontier and its linked score ranking**, including
when the score slider is set to All. Remove the "No score reported" bands and
marks. A genuine score of zero is still a reported score and must remain.

Start from the full corpus, apply this filter, and account for the excluded
records in the counts. Keep the records in the underlying catalog, general
search and dataset exports. A source with no scored records may have zero
visible marks in this view; do not invent scores to preserve source counts.

This exception only concerns missing scores. Missing adoption, an unknown date
or an unverified score scale must not hide a record that has a numeric score.
Keep scored records on other scales inspectable and outside Pareto calculations.
The rules below apply after this explicit filter on the Frontier surface.

## Missing measurements do not delete corpus records

Having a score, release date, reviewed identity, or model-card adoption count
is not a requirement for belonging to the corpus. Do not use an inner join
against the curated registry to define the main chart's population.

Keep records with missing measurements visible and individually inspectable,
using a clearly labelled missing-data area or another suitable representation
within the same surface. A footnote saying that hundreds of records were
excluded does not replace showing them. Do not invent dates, treat unknown
adoption as zero, or rename score observations as unique model cards.

**The main visualization must draw every benchmark that survives the user's
explicit filters, one mark per source record, by default.** Counting a record
in the header, retaining it in search, or putting it in a collapsed list does
not count as drawing it. A 28- or 29-point skyline above a hidden catalog still
fails this rule even when the header says 1,259. Missing dates, adoption or score
units must choose a visible representation, never remove a scored mark.

Preserve the dimensions that are known. A benchmark with a reported score and
date belongs on the time × score plane even when adoption is unrecorded; use
an explicit unknown-adoption mark. Keep unverified source scales visually
distinct from normalized scores and out of Pareto calculations. Benchmarks
whose numeric score cannot use the main scale retain dated, individual marks.
A generic holding area below a tiny curated chart is not sufficient when it
discards known dimensions.

A numeric score cutoff may hide records whose known scores are at or above it.
Records without scores cannot be classified as above or below the cutoff;
Frontier excludes them with its separate reported-score requirement. Show the
full population and account for the visible records, pre-2024 records, records
excluded for missing scores, and records hidden by score or search. Count each
record once so the categories reconcile.

## Calculate only what the evidence supports

Represent every record, but compute a statistic only from records with the
measurements that statistic requires. State that measured coverage beside the
result. In particular, Pareto eligibility requires a declared common score
scale and a recorded value for the selected count. Unknown measurements must
never become zeros or qualify a point for the frontier.

Keep source identities and provenance. Two source records with similar names
are not permission to merge scores or transfer adoption counts. A shared
display scale does not establish equivalent test protocols.

## Chart heights must use the measurements in the full corpus

The default Frontier height is **Models with reported scores**: distinct models
with numeric scores for that source's benchmark record. Aggregate score records
already contain hundreds of model IDs for some benchmarks; a chart that only
uses the small curated document registry discards that measured coverage.
Deduplicate by the source's model ID, preserving separately evaluated
configurations. Curated observations use the exact organization and model name.
Repeated scores, protocols and source documents for the same model must not
increase this count. If model identities are incomplete, mark the count unknown.

Keep **Unique model cards** as a separate height option, counted from distinct
registry documents. Models, score rows, model-card documents and citations are
different quantities. Never substitute or sum them, transfer a count between
similarly named source records, or label hundreds of evaluated models as
hundreds of model-card citations. Both counts and the selected coverage must be
inspectable. Switching height measures must preserve the filtered benchmark IDs.

Use `log1p(count)` for height and raw counts for ticks, tooltips and dominance.
Derive the maximum from the entire scored 2024+ cohort for the selected measure,
before the score and search filters. Do not cap it at 20, 100 or any fixed value.
The wall projection uses the same selected count as the main chart; unverified
score scales retain hollow projections and remain outside Pareto calculations.

## Use benchmark dates and show only 2024 onward

The Benchmark Frontier timeline starts on **2024-01-01, inclusive**. Exclude
earlier benchmarks from this view; do not add an earlier segment or clamp them
to the start of the axis. Keep the original records in the underlying corpus
and account for the date filter in the displayed counts.

Use the benchmark's valid release date first. If it has no release date, use
the earliest dated numeric LLM score for that benchmark, labelled **First LLM
score reported**. Take the earliest score across the available history, before
applying the 2024 cutoff; do not pick its first score after 2024 to force it into
the view. Keep the evidence and date basis inspectable. A batch crawl timestamp
or an adoption-only mention is not a score date.

A missing date in a crawl is a gap to investigate. Check the benchmark's own
release announcement, dataset card, and introducing paper before leaving it
undated. Store recovered dates with their exact source-record key, citation,
and basis, and regenerate the chart's inputs. A README's bibliography can
contain older component methods and unrelated datasets; its earliest paper
is not automatically this benchmark's release. New dates must reach the main
timeline, with their evidence accessible from the mark.

An old model can be evaluated retrospectively on a new benchmark. Audit any
pre-2024 exclusion based only on a model-release proxy, especially records with
hundreds of scored models. HLE and SciCode must not disappear merely because
their evaluated models include releases from 2023. Recover the benchmark's own
date before interpreting such a proxy as evidence of benchmark age.

When an aggregator dates its numeric LLM score records by model release, use
the earliest dated score record as a **model-release proxy**, after any known
benchmark release or actual score-publication date. Carry that date precision
into the chart and tooltip. Do not discard all such records or move hundreds
of scored benchmarks into a second chart: they belong in the main skyline.
Never label this proxy as the benchmark's release or actual score-publication
date. It is the earliest score-entry date available from that source.

If neither date is known, show an individual mark in the main visualization's
clearly labelled undated panel, visible without expanding anything. Preserve
its score position when a score is known. Do not place it at an invented point
on the dated axis or claim it belongs to the 2024+ cohort. Report dated,
undated, pre-2024, and other filtered counts so they reconcile to the full
population. Unknown dates do not satisfy the pre-2024 exclusion condition.

Position dated marks chronologically, using the exact date on a linear axis.
Do not arrange them alphabetically inside year bins. Separate overlapping marks
without changing their dates; explain any stacking or alternate layout. A mass
of benchmarks landing on one collection day is a date-provenance defect to
investigate, not evidence that they were all introduced that day.

## Verify coverage before delivery

- Rebuild the inputs and compute the full population and its sources.
- Check that every input record is represented or accounted for by the explicit
  date, reported-score and cutoff filters, including records without measurements.
- Count actual individually inspectable marks in the default main chart and
  compare their IDs with the filtered full corpus. Counts or collapsed lists
  cannot substitute for missing marks. Every source with matching scored records
  must render; account for sources excluded by the reported-score requirement.
- Check that filtered, visible, and unknown counts reconcile to that population.
- Test missing fields and every source, not just a few curated fixtures.
- Verify release-date priority, earliest-score fallback, the inclusive 2024
  boundary, rejection of crawl dates, and explicit labelling of model-date
  proxies. Missing adoption must not remove dated scores from the main plot,
  and undated records must remain inspectable.
- Treat an unexplained drop from thousands of records to dozens as a defect
  that blocks delivery.

These coverage rules apply alongside the interface guidance in `design.md`.
If a narrower interpretation of that guidance would drop a source or a record
because a measurement is absent, follow this file.
