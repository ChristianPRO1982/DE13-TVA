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

PHASE2_HUMAN_REVIEW_COLUMNS = [
    "source",
    "input_raw",
    "numero_tva_nettoye",
    "review_reason",
    "created_at",
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


def format_verify_report(summary: object) -> str:
    return "\n".join(
        [
            "Rapport verification VIES phase 2",
            f"Candidats selectionnes: {summary.selected}",
            f"Verifications traitees: {summary.processed}",
            f"Valides: {summary.valid}",
            f"Invalides: {summary.invalid}",
            f"Indetermines: {summary.indeterminate}",
            "",
            "Journal:",
            *summary.lines,
        ]
    )


def format_reconciliation_report(report: dict[str, object]) -> str:
    lines = [
        "Rapport reconciliation phase 2",
        f"Total lignes source: {report['total_rows']}",
        f"Numeros nettoyes uniques: {report['unique_cleaned']}",
        f"Candidats VIES uniques: {report['vies_candidates']}",
        f"Appels VIES evites: {report['vies_calls_avoided']}",
        f"Verifications VIES stockees: {report['vies_verifications_total']}",
        f"Doublons par numero nettoye: {report['duplicate_numbers']}",
        f"Cas a reviser phase 1: {report['phase1_human_review']}",
        f"Cas a reviser phase 2: {report['phase2_human_review']}",
        "",
        "Verdicts VIES:",
    ]
    for verdict, count in report["by_vies_verdict"]:
        lines.append(f"- {verdict}: {count}")
    lines.extend(["", "Motifs structurels:"])
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


def export_phase2_human_review_csv(
    rows: list[dict[str, object]],
    output_file: Path,
) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PHASE2_HUMAN_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
