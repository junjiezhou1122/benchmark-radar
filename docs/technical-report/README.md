# Benchmark Radar technical report

This directory holds the LaTeX source, the built PDF, and the deposit metadata
for the citable Benchmark Radar technical report. `latex/main.tex` is the single
source of truth for the report. Edit it directly; nothing generates it from
Python, Markdown, or the running site.

The current manuscript evaluates software version 0.10.0, its full collection and
publication pipeline, the public collection sources, the 1,283-entry web search
surface, and the public data snapshot dated 2026-09-06.

## Build

Requires a TeX distribution with `latexmk` (TinyTeX or TeX Live).

```bash
cd docs/technical-report/latex
make
```

That writes `latex/main.pdf`, which is tracked so the report is readable
directly on GitHub. Commit the rebuilt PDF alongside any change to `main.tex`,
so the checked-in PDF always matches the checked-in source.

## arXiv upload

```bash
cd docs/technical-report/latex
make arxiv
```

That writes `arxiv.tar.gz`. arXiv runs no BibTeX pass of its own, so the tarball
ships the built `main.bbl` rather than `references.bib`, together with
`figure-data.tex` and the native figure sources. It also flattens every
figure into one `figures/` directory, because the use-case screenshots live in
`assets/use-case-492/` in this repository and that path does not exist upstream.
Unpack the tarball and build it once on its own before uploading.

## Figures

The four PDF figures in `latex/figures/` now have native TikZ sources with
matching `.tex` names. `make` rebuilds them before the manuscript; `make figures`
builds just those four PDFs. Their shared styles live in
`figures/figure-style.tex`. TeX Live's `pgf` (TikZ) and `helvet` packages are
required in addition to the manuscript's existing dependencies. No ReportLab,
PDF-page extraction, or downloaded ZIP is needed.

`figure-data.tex` is a checked-in, dated export of numbers, shared by the figures
and the corresponding manuscript counts. Normal builds use that file so a
manuscript rebuild does not silently pick up a new corpus. To refresh it, first
run the six-step clean-checkout CI sequence in `AGENTS.md`, then:

```bash
cd docs/technical-report/latex
make refresh-figure-data  # Python reads the freshly rebuilt index and radar.json
make check-figure-data    # verifies the export, including input SHA-256 hashes
make
```

Review the cutoff, related prose and tables, all four figures, and the rendered
manuscript together; commit `figure-data.tex`, the four figure PDFs, and
`main.pdf` with the source changes. The exporter writes only numbers and input
hashes, never manuscript prose. Missing inputs and incomplete corpus counts fail
visibly. Source-composition bars show the five largest normalized discovery
labels plus every remaining observation; these are not benchmark catalog source
counts. `make clean` preserves the tracked PDFs and removes build intermediates.

The reconstruction follows the legacy drawing routines in commit `6270ff3` and
the checked-in PDFs. The supplied `Benchmark_Radar (1).zip` contained PDFs but no
drawing sources. Rebuilding the catalog confirmed 1,283 records across four
sources: the older 1,259 figure omitted 24 model-report benchmarks without scores,
and the unused search illustration still said 1,242. Both now use the same full
catalog count as the manuscript. The search illustration remains unembedded.

The graphical abstract (`figures/abstract_overview.png`) is an authored raster
asset, not one of these four generated diagrams.

The use-case screenshots in `assets/use-case-492/` are likewise committed
assets, captured from the running site.

## Deposit

The published v0.9.0 PDF at
`output/pdf/benchmark-radar-technical-report-v0.9.0.pdf` is frozen. It is the
artifact behind DOI 10.5281/zenodo.22167102 and must stay byte-for-byte
unchanged. Nothing in this repository writes to that path; do not overwrite it
by hand.

A new deposit copies the reviewed `latex/main.pdf` to
`output/pdf/benchmark-radar-technical-report-v<version>.pdf` and updates
`zenodo-metadata.json` in the same change. Prepare release metadata only when a
report version is approved for deposit.

## Byline and credit

The byline is provisional until each contributor has reviewed and approved the
integrated manuscript, supplied a contribution statement, and accepted
accountability for the work, as described in
`docs/designs/technical-report-collaboration-scoring.md` and issue #447.

## Section 6.2 saturation audit

The appendix tables come from `saturation-audit-6.2.json`, generated from the
curated score archive and the model-report registry with:

```bash
python3 -m benchmark_radar.saturation_audit
```

Regenerate that file and update the appendix tables together.

### Independent reproduction

On 2026-09-05, a Codex-assisted maintainer review regenerated the audit from the
two canonical YAML files. It reproduced four counts: eight raw near-ceiling
readings; no raw-best setup spanning two dates; four benchmarks with a different
repeated setup; and one of those four within five points. The review also checked
the HMMT sample against Table 7 of the
[DeepSeek-V4 primary report](https://arxiv.org/html/2606.19348): HMMT 2026 Feb,
Pass@1, Think Max is 94.8 for DeepSeek-V4-Flash and 95.2 for
DeepSeek-V4-Pro. Those values match the `deepseek_v4_technical_report` and
`deepseek_v4_model_card` rows in `data/benchmark_scores.yml`.

The audit was regenerated again at v0.10.0 and the output was byte-identical, so
the finding still holds at the current cutoff.

## Audited inputs

The report derives its quantitative claims from these versioned files and from
the current README and report documentation:

- `site/data/radar.json` (generated from the dated snapshots)
- `site/data/benchmark-index.json` (generated from normalized catalogs)
- `data/snapshots/2026-09-06.json`
- `data/model_cards.yml`
- `data/benchmark_scores.yml`
- `site/data/models.json`
- `config.yml`
- `docs/reports/ai-benchmark-landscape-report.md`
- `docs/source-probe-evidence.md`

The last two are project-history and data-validation context, not evidence for a
benchmark claim. Rebuild and review the report when any of those inputs or the
report text changes.

## Licensing

The software remains under the MIT License. The technical report and original
editorial content use CC BY-NC 4.0. Commercial republication, resale, paid
newsletters, dataset packaging, or commercial product integration requires
prior written permission from Koutian Wu. Third-party source material remains
under its original terms.
