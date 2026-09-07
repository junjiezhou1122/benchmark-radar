# Benchmark Radar technical report

This directory holds the LaTeX source, the built PDF, and the deposit metadata
for the citable Benchmark Radar technical report. `latex/main.tex` is the single
source of truth for the report. Edit it directly; nothing generates it from
Python, Markdown, or the running site.

The current manuscript evaluates software version 0.10.0, its full collection and
publication pipeline, the public collection sources, the 1,259-entry web search
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
ships the built `main.bbl` rather than `references.bib`. It also flattens every
figure into one `figures/` directory, because the use-case screenshots live in
`assets/use-case-492/` in this repository and that path does not exist upstream.
Unpack the tarball and build it once on its own before uploading.

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
