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

RECONCILIATION_DETAIL_COLUMNS = [
    "source_id",
    "raison_sociale",
    "pays_declare_brut",
    "pays_declare_normalise",
    "numero_tva_brut",
    "numero_tva_nettoye",
    "structure_verdict",
    "structure_reason",
    "final_verdict",
    "final_origin",
    "checked_at",
    "freshness_days",
    "needs_human_review",
    "needs_vies_verification",
    "review_reason",
]

VIES_VERDICT_ORDER = ("valide", "invalide", "indetermine")


def write_text_report(content: str, output_file: Path) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(content + "\n", encoding="utf-8")
    return output_file


def format_import_report(imported: int) -> str:
    return "\n".join(
        [
            "Rapport import phase 1",
            f"Lignes importées ou mises à jour: {imported}",
            "Idempotence: source_id est la clé primaire, ON CONFLICT met à jour.",
        ]
    )


def format_structural_report(report: dict[str, object]) -> str:
    lines = [
        "Rapport structurel phase 1",
        f"Total lignes source: {report['total_rows']}",
        f"Numéros nettoyés uniques: {report['unique_cleaned']}",
        f"Candidats VIES uniques: {report['vies_candidates']}",
        f"Appels VIES évités: {report['vies_calls_avoided']}",
        "",
        "Répartition par motif:",
    ]
    for reason, count in report["by_reason"]:
        lines.append(f"- {reason}: {count}")
    return "\n".join(lines)


def format_verify_report(summary: object) -> str:
    return "\n".join(
        [
            "Rapport vérification VIES phase 2",
            f"Candidats sélectionnés: {summary.selected}",
            f"Vérifications traitées: {summary.processed}",
            f"Valides: {summary.valid}",
            f"Invalides: {summary.invalid}",
            f"Indéterminés: {summary.indeterminate}",
            "",
            "Journal:",
            *summary.lines,
        ]
    )


def format_reconciliation_report(report: dict[str, object]) -> str:
    lines = [
        "Rapport réconciliation phase 2",
        f"Total lignes source: {report['total_rows']}",
        f"Numéros nettoyés uniques: {report['unique_cleaned']}",
        f"Candidats VIES uniques: {report['vies_candidates']}",
        f"Appels VIES évités: {report['vies_calls_avoided']}",
        f"Verdicts VIES courants stockés: {report['vies_verifications_total']}",
        f"Tentatives VIES historisées: {report['vies_attempts_total']}",
        f"Numéros VIES uniques en attente: {report['pending_vies_unique']}",
        f"Lignes source en attente de VIES: {report['pending_vies']}",
        f"Doublons par numéro nettoyé: {report['duplicate_numbers']}",
        f"Cas à réviser phase 1: {report['phase1_human_review']}",
        f"Cas à réviser phase 2: {report['phase2_human_review']}",
        "",
        "Verdicts finaux par ligne source:",
    ]
    for verdict, count in _ordered_verdict_counts(report["by_final_verdict"]):
        lines.append(f"- {verdict}: {count}")
    lines.extend(
        [
            "",
            "Verdicts VIES courants:",
        ]
    )
    for verdict, count in _ordered_verdict_counts(report["by_vies_verdict"]):
        lines.append(f"- {verdict}: {count}")
    lines.extend(["", "Tentatives VIES par verdict:"])
    for verdict, count in _ordered_verdict_counts(report["by_attempt_verdict"]):
        lines.append(f"- {verdict}: {count}")
    lines.extend(["", "Motifs structurels:"])
    for reason, count in report["by_reason"]:
        lines.append(f"- {reason}: {count}")
    return "\n".join(lines)


def _ordered_verdict_counts(rows: object) -> list[tuple[str, int]]:
    counts = {verdict: 0 for verdict in VIES_VERDICT_ORDER}
    counts.update(dict(rows))
    ordered = [(verdict, counts[verdict]) for verdict in VIES_VERDICT_ORDER]
    extras = sorted(
        (verdict, count)
        for verdict, count in counts.items()
        if verdict not in VIES_VERDICT_ORDER
    )
    return ordered + extras


def export_reconciliation_details_csv(
    rows: list[dict[str, object]],
    output_file: Path,
) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=RECONCILIATION_DETAIL_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def format_demo_report(
    *,
    imported: int,
    phase1_review_count: int,
    phase2_review_count: int,
    sample_size: int | None,
    skipped_vies: bool,
) -> str:
    vies_message = (
        "Campagne VIES ignorée sur demande."
        if skipped_vies
        else f"Campagne VIES exécutée avec sample-size={sample_size}."
    )
    return "\n".join(
        [
            "Déroulé de démonstration",
            f"Lignes importées ou mises à jour: {imported}",
            f"Cas à réviser phase 1 exportés: {phase1_review_count}",
            vies_message,
            f"Cas à réviser phase 2 exportés: {phase2_review_count}",
            "Rapports générés dans reports/phase_1/ et reports/phase_2/.",
        ]
    )


def export_human_review_csv(rows: list[dict[str, object]], output_file: Path) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=HUMAN_REVIEW_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_phase2_human_review_csv(
    rows: list[dict[str, object]],
    output_file: Path,
) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=PHASE2_HUMAN_REVIEW_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
