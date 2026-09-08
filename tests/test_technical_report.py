from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEX = ROOT / "docs" / "technical-report" / "latex"
MANUSCRIPT = LATEX / "main.tex"
FROZEN_DEPOSIT = ROOT / "output" / "pdf" / "benchmark-radar-technical-report-v0.9.0.pdf"


def test_latex_is_the_only_report_source() -> None:
    assert MANUSCRIPT.is_file()
    assert (LATEX / "references.bib").is_file()
    assert (LATEX / "Makefile").is_file()

    # The ReportLab builders were the previous source. Their return would give
    # the report two sources that can disagree.
    assert not (ROOT / "scripts" / "build_system_evaluation.py").exists()
    assert not (ROOT / "scripts" / "build_technical_report.py").exists()


def test_built_pdf_is_tracked_so_the_report_reads_on_github() -> None:
    assert (LATEX / "main.pdf").is_file()
    ignored = (LATEX / ".gitignore").read_text(encoding="utf-8").split()
    assert "main.pdf" not in ignored


def test_manuscript_records_contributor_names_and_affiliations() -> None:
    source = MANUSCRIPT.read_text(encoding="utf-8")

    for author in ("Koutian Wu", "Junjie Zhou", "Ergan Shang", "Jiayu Wang", "Pengqian Han"):
        assert author in source
    for affiliation in (
        "Tacite AI",
        "Hangzhou Dianzi University",
        "Carnegie Mellon University",
        "Xi'an Jiaotong University",
        "The University of Auckland",
    ):
        assert affiliation in source
    assert "k@tacite.ai" in source


def test_manuscript_embeds_use_case_figures() -> None:
    source = MANUSCRIPT.read_text(encoding="utf-8")
    names = (
        "agent-session.png",
        "artifact-status-paper.png",
        "artifact-status-code.png",
        "cross-validation.png",
        "survey-table.png",
        "manual-prior-art-table.png",
    )

    for name in names:
        assert name in source
        assert (LATEX / "figures" / name).read_bytes() == (
            ROOT / "assets" / "use-case-492" / name
        ).read_bytes()


def test_frozen_deposit_is_present_and_is_never_a_write_target() -> None:
    # The artifact behind DOI 10.5281/zenodo.22167102. A new report version is
    # deposited under a new versioned filename, never by replacing this one.
    assert FROZEN_DEPOSIT.is_file()

    for path in ROOT.joinpath("scripts").rglob("*.py"):
        assert FROZEN_DEPOSIT.name not in path.read_text(encoding="utf-8")
    assert FROZEN_DEPOSIT.name not in (LATEX / "Makefile").read_text(encoding="utf-8")
