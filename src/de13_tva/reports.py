"""Report formatting and export helpers."""

from __future__ import annotations

import csv
from pathlib import Path

HUMAN_REVIEW_COLUMNS = [
    "source_id",
    "raison_sociale",
    "pays_declare_brut",
    "pays_declare_normalise",
    "numero_tva_brut",
    "numero_tva_nettoye",
    "structure_reason",
    "human_review_reason",
]


def write_text_report(content: str, output_file: Path) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content + "\n", encoding="utf-8")
    return output_file


def format_import_report(imported: int) -> str:
    return "\n".join(
        [
            "Rapport import phase 1",
            f"Lignes importees ou mises a jour: {imported}",
            "Idempotence: source_id est la cle primaire, ON CONFLICT met a jour.",
        ]
    )


def format_structural_report(report: dict[str, object]) -> str:
    lines = [
        "Rapport structurel phase 1",
        f"Total lignes source: {report['total_rows']}",
        f"Numeros nettoyes uniques: {report['unique_cleaned']}",
        f"Candidats VIES uniques: {report['vies_candidates']}",
        f"Appels VIES evites: {report['vies_calls_avoided']}",
        "",
        "Repartition par motif:",
    ]
    for reason, count in report["by_reason"]:
        lines.append(f"- {reason}: {count}")
    return "\n".join(lines)


def export_human_review_csv(rows: list[dict[str, object]], output_file: Path) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=HUMAN_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
