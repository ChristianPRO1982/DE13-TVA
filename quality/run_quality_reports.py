"""Run read-only SQL quality reports and export them as Markdown."""

from __future__ import annotations

import argparse
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from de13_tva.database import connect, ensure_schema
from de13_tva.settings import DEFAULT_REPORTS_DIR

DEFAULT_OUTPUT = DEFAULT_REPORTS_DIR / "quality" / "quality_control.md"


@dataclass(frozen=True)
class QualityQuery:
    title: str
    explanation: str
    sql: str


QUERIES = [
    QualityQuery(
        "01 - Répartition des verdicts structurels",
        "Montre combien de lignes sont structurellement valides ou rejetées avant VIES.",
        """
        SELECT
          vr.structure_verdict,
          count(*) AS total
        FROM vat_records vr
        GROUP BY vr.structure_verdict
        ORDER BY total DESC, vr.structure_verdict;
        """,
    ),
    QualityQuery(
        "02 - Répartition des motifs structurels",
        "Détaille les motifs métier associés à la validation structurelle.",
        """
        SELECT
          vr.structure_reason,
          count(*) AS total
        FROM vat_records vr
        GROUP BY vr.structure_reason
        ORDER BY total DESC, vr.structure_reason;
        """,
    ),
    QualityQuery(
        "03 - Cas à réviser humainement en phase 1",
        "Liste les familles d'anomalies qui ne doivent pas être tranchées automatiquement.",
        """
        SELECT
          vr.human_review_reason,
          count(*) AS total
        FROM vat_records vr
        WHERE vr.needs_human_review = true
        GROUP BY vr.human_review_reason
        ORDER BY total DESC, vr.human_review_reason;
        """,
    ),
    QualityQuery(
        "04 - Répartition par pays déclaré",
        "Permet de voir le poids de chaque pays dans le référentiel.",
        """
        SELECT
          vr.pays_declare_normalise,
          count(*) AS total
        FROM vat_records vr
        GROUP BY vr.pays_declare_normalise
        ORDER BY total DESC, vr.pays_declare_normalise;
        """,
    ),
    QualityQuery(
        "05 - Formats invalides par pays",
        "Identifie les pays qui concentrent le plus de formats invalides.",
        """
        SELECT
          vr.pays_declare_normalise,
          count(*) AS total
        FROM vat_records vr
        WHERE vr.structure_reason = 'format_invalide'
        GROUP BY vr.pays_declare_normalise
        ORDER BY total DESC, vr.pays_declare_normalise;
        """,
    ),
    QualityQuery(
        "06 - Sources de saisie les plus problématiques",
        "Croise les sources de saisie et les motifs structurels.",
        """
        SELECT
          vr.source_saisie,
          vr.structure_reason,
          count(*) AS total
        FROM vat_records vr
        GROUP BY vr.source_saisie, vr.structure_reason
        ORDER BY vr.source_saisie, total DESC, vr.structure_reason;
        """,
    ),
    QualityQuery(
        "07 - Numéros TVA nettoyés uniques",
        "Mesure le volume unique réel après nettoyage.",
        """
        SELECT
          count(DISTINCT NULLIF(vr.numero_tva_nettoye, ''))
            AS numeros_nettoyes_uniques
        FROM vat_records vr;
        """,
    ),
    QualityQuery(
        "08 - Candidats VIES uniques",
        "Compte les numéros structurellement valides qui peuvent être appelés auprès de VIES.",
        """
        SELECT
          count(*) AS candidats_vies_uniques
        FROM vies_candidates;
        """,
    ),
    QualityQuery(
        "09 - Appels VIES évités",
        "Compare les 10 000 lignes source avec le nombre de candidats VIES uniques.",
        """
        SELECT
          (SELECT count(*) FROM vat_records) AS lignes_source,
          (SELECT count(*) FROM vies_candidates) AS candidats_vies_uniques,
          (SELECT count(*) FROM vat_records) - (SELECT count(*) FROM vies_candidates)
            AS appels_vies_evites;
        """,
    ),
    QualityQuery(
        "10 - Doublons par numéro nettoyé",
        "Liste les numéros nettoyés présents sur plusieurs lignes source.",
        """
        SELECT
          vr.numero_tva_nettoye,
          count(*) AS total_lignes
        FROM vat_records vr
        WHERE vr.numero_tva_nettoye <> ''
        GROUP BY vr.numero_tva_nettoye
        HAVING count(*) > 1
        ORDER BY total_lignes DESC, vr.numero_tva_nettoye
        LIMIT 50;
        """,
    ),
    QualityQuery(
        "11 - Verdicts VIES courants",
        "Résume les derniers verdicts VIES exploitables stockés.",
        """
        SELECT
          vv.vies_verdict,
          count(*) AS total
        FROM vies_verifications vv
        GROUP BY vv.vies_verdict
        ORDER BY total DESC, vv.vies_verdict;
        """,
    ),
    QualityQuery(
        "12 - Tentatives VIES historisées",
        "Résume toutes les tentatives VIES, y compris les erreurs et indéterminés.",
        """
        SELECT
          va.vies_verdict,
          count(*) AS total
        FROM vies_attempts va
        GROUP BY va.vies_verdict
        ORDER BY total DESC, va.vies_verdict;
        """,
    ),
    QualityQuery(
        "13 - Numéros en attente de VIES",
        "Compte les candidats qui n'ont pas encore de verdict VIES exploitable.",
        """
        SELECT
          count(*) AS numeros_vies_en_attente
        FROM vies_candidates vc
        LEFT JOIN vies_verifications vv
          ON vv.numero_tva_nettoye = vc.numero_tva_nettoye
        WHERE vv.numero_tva_nettoye IS NULL;
        """,
    ),
    QualityQuery(
        "14 - Verdict final par ligne source",
        "Répond directement à la question centrale du brief.",
        """
        SELECT
          CASE
            WHEN vr.structure_verdict <> 'valid' THEN 'indetermine'
            WHEN vv.vies_verdict = 'valide' THEN 'valide'
            WHEN vv.vies_verdict = 'invalide' THEN 'invalide'
            ELSE 'indetermine'
          END AS verdict_final,
          count(*) AS total
        FROM vat_records vr
        LEFT JOIN vies_verifications vv
          ON vv.numero_tva_nettoye = vr.numero_tva_nettoye
        GROUP BY verdict_final
        ORDER BY total DESC, verdict_final;
        """,
    ),
    QualityQuery(
        "15 - Dernières tentatives VIES",
        "Affiche les derniers appels VIES pour vérifier reprise, origines et erreurs.",
        """
        SELECT
          va.checked_at,
          va.numero_tva_nettoye,
          va.vies_verdict,
          va.origin,
          va.http_status,
          va.response_time_ms,
          va.error_message
        FROM vies_attempts va
        ORDER BY va.checked_at DESC, va.id DESC
        LIMIT 50;
        """,
    ),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Génère les rapports qualité SQL.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    with connect() as conn:
        ensure_schema(conn)
        sections = [run_query(conn, query) for query in QUERIES]

    content = "\n\n".join(["# Rapport Qualité SQL", *sections])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content + "\n", encoding="utf-8")
    print(f"Rapport qualité SQL écrit dans {args.output}")
    return 0


def run_query(conn, query: QualityQuery) -> str:
    sql = textwrap.dedent(query.sql).strip()
    with conn.cursor() as cursor:
        cursor.execute(sql)
        columns = [column.name for column in cursor.description]
        rows = cursor.fetchall()

    return "\n\n".join(
        [
            f"## {query.title}",
            query.explanation,
            "```sql\n" + sql + "\n```",
            markdown_table(columns, rows),
        ]
    )


def markdown_table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    if not rows:
        return "_Aucun résultat._"

    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(format_cell(value) for value in row) + " |" for row in rows
    ]
    return "\n".join([header, separator, *body])


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
