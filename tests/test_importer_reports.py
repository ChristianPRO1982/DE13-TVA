from pathlib import Path

from de13_tva.importer import build_records
from de13_tva.reports import (
    export_human_review_csv,
    export_phase2_human_review_csv,
    export_reconciliation_details_csv,
    format_demo_report,
    format_import_report,
    format_reconciliation_report,
    format_structural_report,
    format_verify_report,
    write_text_report,
)


def test_build_records_from_csv(tmp_path: Path):
    data_file = tmp_path / "data.csv"
    eu_file = tmp_path / "eu.csv"
    data_file.write_text(
        "id,raison_sociale,pays_declare,numero_tva,date_saisie,source_saisie\n"
        "1,Acme,FR,FR 27 552 032 534,2026-01-01,crm\n"
        "2,Bad,QQ,QQ123,2026-01-02,crm",
        encoding="utf-8",
    )
    eu_file.write_text(
        "Code (ISO 3166)\nFR\nBE\n",
        encoding="utf-8",
    )

    records = build_records(data_file, eu_file)

    assert len(records) == 2
    assert records[0].numero_tva_nettoye == "FR27552032534"
    assert records[0].structure_verdict == "valid"
    assert records[1].structure_reason == "pays_hors_referentiel_ue"
    assert records[1].needs_human_review


def test_export_human_review_csv(tmp_path: Path):
    output = tmp_path / "reports" / "a_reviser.csv"
    rows = [
        {
            "source_id": 1,
            "raison_sociale": "Bad",
            "pays_declare_brut": "QQ",
            "pays_declare_normalise": "QQ",
            "numero_tva_brut": "QQ123",
            "numero_tva_nettoye": "QQ123",
            "structure_reason": "pays_hors_referentiel_ue",
            "human_review_reason": "Code pays absent du référentiel UE local",
        }
    ]

    count = export_human_review_csv(rows, output)

    assert count == 1
    assert output.read_text(encoding="utf-8").splitlines()[1].startswith("1,Bad,QQ")


def test_export_phase2_human_review_csv(tmp_path: Path):
    output = tmp_path / "reports" / "phase_2" / "a_reviser.csv"
    rows = [
        {
            "source": "api",
            "input_raw": "---",
            "numero_tva_nettoye": "",
            "review_reason": "pays_absent",
            "created_at": "2026-09-09T12:00:00Z",
        }
    ]

    count = export_phase2_human_review_csv(rows, output)

    assert count == 1
    assert output.read_text(encoding="utf-8").splitlines()[1].startswith("api,---")


def test_export_reconciliation_details_csv(tmp_path: Path):
    output = tmp_path / "reports" / "phase_2" / "reconciliation-details.csv"
    rows = [
        {
            "source_id": 1,
            "raison_sociale": "Acme",
            "pays_declare_brut": "FR",
            "pays_declare_normalise": "FR",
            "numero_tva_brut": "FR 27 552 032 534",
            "numero_tva_nettoye": "FR27552032534",
            "structure_verdict": "valid",
            "structure_reason": "ok_structure",
            "final_verdict": "valide",
            "final_origin": "campaign",
            "checked_at": "2026-09-09T12:00:00Z",
            "freshness_days": 0,
            "needs_human_review": False,
            "needs_vies_verification": False,
            "review_reason": None,
        }
    ]

    count = export_reconciliation_details_csv(rows, output)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert count == 1
    assert lines[0].startswith("source_id,raison_sociale")
    assert lines[1].startswith("1,Acme,FR")


def test_write_text_report(tmp_path: Path):
    output = tmp_path / "reports" / "phase_1" / "import-data.txt"

    result = write_text_report("hello", output)

    assert result == output
    assert output.read_text(encoding="utf-8") == "hello\n"


def test_format_import_report():
    formatted = format_import_report(10000)

    assert "Rapport import phase 1" in formatted
    assert "Lignes importées ou mises à jour: 10000" in formatted
    assert "Idempotence:" in formatted


def test_format_structural_report():
    report = {
        "total_rows": 10,
        "unique_cleaned": 8,
        "vies_candidates": 6,
        "vies_calls_avoided": 4,
        "by_reason": [("ok_structure", 6), ("format_invalide", 4)],
    }

    formatted = format_structural_report(report)

    assert "Total lignes source: 10" in formatted
    assert "Appels VIES évités: 4" in formatted
    assert "- ok_structure: 6" in formatted


def test_format_verify_report():
    from types import SimpleNamespace

    formatted = format_verify_report(
        SimpleNamespace(
            selected=2,
            processed=2,
            valid=1,
            invalid=1,
            indeterminate=0,
            lines=["1/2 FR: valide", "2/2 BE: invalide"],
        )
    )

    assert "Rapport vérification VIES phase 2" in formatted
    assert "Valides: 1" in formatted
    assert "2/2 BE: invalide" in formatted


def test_format_reconciliation_report():
    report = {
        "total_rows": 10,
        "unique_cleaned": 8,
        "vies_candidates": 6,
        "vies_calls_avoided": 4,
        "vies_verifications_total": 3,
        "vies_attempts_total": 4,
        "duplicate_numbers": 2,
        "phase1_human_review": 1,
        "phase2_human_review": 1,
        "pending_vies": 4,
        "pending_vies_unique": 3,
        "by_vies_verdict": [("valide", 2), ("indetermine", 1)],
        "by_attempt_verdict": [("indetermine", 2), ("valide", 2)],
        "by_final_verdict": [("indetermine", 7), ("valide", 3)],
        "by_reason": [("ok_structure", 6), ("format_invalide", 4)],
    }

    formatted = format_reconciliation_report(report)

    assert "Rapport réconciliation phase 2" in formatted
    assert "Verdicts VIES courants stockés: 3" in formatted
    assert "Tentatives VIES historisées: 4" in formatted
    assert "Numéros VIES uniques en attente: 3" in formatted
    assert "Lignes source en attente de VIES: 4" in formatted
    assert "Verdicts finaux par ligne source:" in formatted
    assert "- valide: 3" in formatted
    assert "- invalide: 0" in formatted
    assert "- indetermine: 1" in formatted


def test_format_reconciliation_report_without_vies_verdicts():
    report = {
        "total_rows": 1,
        "unique_cleaned": 1,
        "vies_candidates": 1,
        "vies_calls_avoided": 0,
        "vies_verifications_total": 0,
        "vies_attempts_total": 0,
        "duplicate_numbers": 0,
        "phase1_human_review": 0,
        "phase2_human_review": 0,
        "pending_vies": 1,
        "pending_vies_unique": 1,
        "by_vies_verdict": [],
        "by_attempt_verdict": [],
        "by_final_verdict": [("indetermine", 1)],
        "by_reason": [("ok_structure", 1)],
    }

    formatted = format_reconciliation_report(report)

    assert "- valide: 0" in formatted
    assert "- invalide: 0" in formatted
    assert "- indetermine: 1" in formatted


def test_format_demo_report():
    formatted = format_demo_report(
        imported=10,
        phase1_review_count=2,
        phase2_review_count=1,
        sample_size=3,
        skipped_vies=False,
    )

    assert "Déroulé de démonstration" in formatted
    assert "sample-size=3" in formatted
