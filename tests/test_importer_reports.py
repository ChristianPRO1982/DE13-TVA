from pathlib import Path

from de13_tva.importer import build_records
from de13_tva.reports import (
    export_human_review_csv,
    format_import_report,
    format_structural_report,
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
            "human_review_reason": "Code pays absent du referentiel UE local",
        }
    ]

    count = export_human_review_csv(rows, output)

    assert count == 1
    assert output.read_text(encoding="utf-8").splitlines()[1].startswith("1,Bad,QQ")


def test_write_text_report(tmp_path: Path):
    output = tmp_path / "reports" / "phase_1" / "import-data.txt"

    result = write_text_report("hello", output)

    assert result == output
    assert output.read_text(encoding="utf-8") == "hello\n"


def test_format_import_report():
    formatted = format_import_report(10000)

    assert "Rapport import phase 1" in formatted
    assert "Lignes importees ou mises a jour: 10000" in formatted
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
    assert "Appels VIES evites: 4" in formatted
    assert "- ok_structure: 6" in formatted
