"""PostgreSQL persistence for phase 1."""

from __future__ import annotations

from collections.abc import Iterable

from de13_tva.importer import VatRecord
from de13_tva.settings import database_config

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS vat_records (
    source_id integer PRIMARY KEY,
    raison_sociale text NOT NULL,
    pays_declare_brut text NOT NULL,
    pays_declare_normalise text NOT NULL,
    numero_tva_brut text NOT NULL,
    numero_tva_nettoye text NOT NULL,
    date_saisie date,
    source_saisie text NOT NULL,
    structure_verdict text NOT NULL,
    structure_reason text NOT NULL,
    needs_human_review boolean NOT NULL DEFAULT false,
    human_review_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vat_records_numero_tva_nettoye
    ON vat_records (numero_tva_nettoye);

CREATE INDEX IF NOT EXISTS idx_vat_records_structure
    ON vat_records (structure_verdict, structure_reason);

CREATE OR REPLACE VIEW vies_candidates AS
SELECT DISTINCT ON (numero_tva_nettoye)
    numero_tva_nettoye,
    pays_declare_normalise,
    min(source_id) OVER (PARTITION BY numero_tva_nettoye) AS first_source_id,
    count(*) OVER (PARTITION BY numero_tva_nettoye) AS source_rows_count
FROM vat_records
WHERE structure_verdict = 'valid'
  AND numero_tva_nettoye <> ''
ORDER BY numero_tva_nettoye, source_id;
"""

UPSERT_SQL = """
INSERT INTO vat_records (
    source_id,
    raison_sociale,
    pays_declare_brut,
    pays_declare_normalise,
    numero_tva_brut,
    numero_tva_nettoye,
    date_saisie,
    source_saisie,
    structure_verdict,
    structure_reason,
    needs_human_review,
    human_review_reason
) VALUES (
    %(source_id)s,
    %(raison_sociale)s,
    %(pays_declare_brut)s,
    %(pays_declare_normalise)s,
    %(numero_tva_brut)s,
    %(numero_tva_nettoye)s,
    %(date_saisie)s,
    %(source_saisie)s,
    %(structure_verdict)s,
    %(structure_reason)s,
    %(needs_human_review)s,
    %(human_review_reason)s
)
ON CONFLICT (source_id) DO UPDATE SET
    raison_sociale = EXCLUDED.raison_sociale,
    pays_declare_brut = EXCLUDED.pays_declare_brut,
    pays_declare_normalise = EXCLUDED.pays_declare_normalise,
    numero_tva_brut = EXCLUDED.numero_tva_brut,
    numero_tva_nettoye = EXCLUDED.numero_tva_nettoye,
    date_saisie = EXCLUDED.date_saisie,
    source_saisie = EXCLUDED.source_saisie,
    structure_verdict = EXCLUDED.structure_verdict,
    structure_reason = EXCLUDED.structure_reason,
    needs_human_review = EXCLUDED.needs_human_review,
    human_review_reason = EXCLUDED.human_review_reason,
    updated_at = now();
"""


def connect():
    """Open a psycopg connection using project settings."""
    import psycopg

    return psycopg.connect(**database_config())


def ensure_schema(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute(SCHEMA_SQL)
    conn.commit()


def upsert_records(conn, records: Iterable[VatRecord]) -> int:
    count = 0
    with conn.cursor() as cursor:
        for record in records:
            cursor.execute(UPSERT_SQL, record.__dict__)
            count += 1
    conn.commit()
    return count


def fetch_structural_report(conn) -> dict[str, object]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM vat_records")
        total_rows = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT structure_reason, count(*)
            FROM vat_records
            GROUP BY structure_reason
            ORDER BY count(*) DESC, structure_reason
            """
        )
        by_reason = cursor.fetchall()

        cursor.execute(
            """
            SELECT count(DISTINCT NULLIF(numero_tva_nettoye, ''))
            FROM vat_records
            """
        )
        unique_cleaned = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM vies_candidates")
        candidates = cursor.fetchone()[0]

    return {
        "total_rows": total_rows,
        "by_reason": by_reason,
        "unique_cleaned": unique_cleaned,
        "vies_candidates": candidates,
        "vies_calls_avoided": total_rows - candidates,
    }


def fetch_human_review_rows(conn) -> list[dict[str, object]]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                source_id,
                raison_sociale,
                pays_declare_brut,
                pays_declare_normalise,
                numero_tva_brut,
                numero_tva_nettoye,
                structure_reason,
                human_review_reason
            FROM vat_records
            WHERE needs_human_review = true
            ORDER BY source_id
            """
        )
        columns = [column.name for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
