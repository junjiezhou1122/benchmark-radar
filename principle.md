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

## Missing measurements do not remove benchmarks

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
fails this rule even when the header says 1,259. Missing dates, adoption, score
units, or scores must choose a visible representation, never remove a mark.

Preserve the dimensions that are known. A benchmark with a reported score and
date belongs on the time × score plane even when adoption is unrecorded; use
an explicit unknown-adoption mark. Keep unverified source scales visually
distinct from normalized scores and out of Pareto calculations. Benchmarks
without a usable score retain dated, individual marks. A generic holding area
below a tiny curated chart is not sufficient when it discards known dimensions.

A numeric score cutoff may hide records whose known scores are at or above it.
Records without scores cannot be classified as above or below the cutoff;
keep them in the visible unknown-score area. Show the full population, the
matching records, the unknown measurements, and the records hidden by the
user's filters so the counts reconcile.

## Calculate only what the evidence supports

Represent every record, but compute a statistic only from records with the
measurements that statistic requires. State that measured coverage beside the
result. In particular, Pareto eligibility requires a declared common score
scale and a real adoption measurement. Unknown measurements must never become
zeros or qualify a point for the frontier.

Keep source identities and provenance. Two source records with similar names
are not permission to merge scores or transfer adoption counts. A shared
display scale does not establish equivalent test protocols.

## Use benchmark dates and show only 2024 onward

The Benchmark Frontier timeline starts on **2024-01-01, inclusive**. Exclude
earlier benchmarks from this view; do not add an earlier segment or clamp them
to the start of the axis. Keep the original records in the underlying corpus
and account for the date filter in the displayed counts.

Use the benchmark's valid release date first. If it has no release date, use
the earliest dated numeric LLM score for that benchmark, labelled **First LLM
score reported**. Take the earliest score across the available history, before
applying the 2024 cutoff; do not pick its first score after 2024 to force it into
the view. Keep the evidence and date basis inspectable. Neither a batch crawl
timestamp nor a model's release date is a benchmark release or score report date.
An adoption-only mention is not a score.

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
  date and score filters, including records without measurements.
- Count actual individually inspectable marks in the default main chart and
  compare their IDs with the filtered full corpus. Counts or collapsed lists
  cannot substitute for missing marks. All four or more sources must render.
- Check that filtered, visible, and unknown counts reconcile to that population.
- Test missing fields and every source, not just a few curated fixtures.
- Verify release-date priority, earliest-score fallback, the inclusive 2024
  boundary, and rejection of crawl/model dates. Missing adoption must not remove
  dated scores from the main plot, and undated records must remain inspectable.
- Treat an unexplained drop from thousands of records to dozens as a defect
  that blocks delivery.

These coverage rules apply alongside the interface guidance in `design.md`.
If a narrower interpretation of that guidance would drop a source or a record
because a measurement is absent, follow this file.
