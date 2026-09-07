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

## Verify coverage before delivery

- Rebuild the inputs and compute the full population and its sources.
- Check that the unfiltered surface represents every input record once,
  including records without scores or adoption measurements.
- Check that filtered, visible, and unknown counts reconcile to that population.
- Test missing fields and every source, not just a few curated fixtures.
- Treat an unexplained drop from thousands of records to dozens as a defect
  that blocks delivery.

These coverage rules apply alongside the interface guidance in `design.md`.
If a narrower interpretation of that guidance would drop a source or a record
because a measurement is absent, follow this file.
