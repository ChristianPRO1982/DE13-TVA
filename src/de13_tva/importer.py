"""CSV import preparation for phase 1."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from de13_tva.cleaning import clean_text
from de13_tva.countries import load_eu_country_codes
from de13_tva.validation import validate_structural


@dataclass(frozen=True)
class VatRecord:
    source_id: int
    raison_sociale: str
    pays_declare_brut: str
    pays_declare_normalise: str
    numero_tva_brut: str
    numero_tva_nettoye: str
    date_saisie: str
    source_saisie: str
    structure_verdict: str
    structure_reason: str
    needs_human_review: bool
    human_review_reason: str | None


def build_records(data_file: Path, eu_codes_file: Path) -> list[VatRecord]:
    """Read source CSV and return validated records ready for persistence."""
    eu_codes = load_eu_country_codes(eu_codes_file)
    records: list[VatRecord] = []

    with data_file.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            validation = validate_structural(
                row.get("pays_declare"),
                row.get("numero_tva"),
                eu_codes,
            )
            records.append(
                VatRecord(
                    source_id=int(row["id"]),
                    raison_sociale=row.get("raison_sociale", ""),
                    pays_declare_brut=row.get("pays_declare", ""),
                    pays_declare_normalise=validation.country_normalized,
                    numero_tva_brut=row.get("numero_tva", ""),
                    numero_tva_nettoye=validation.vat_normalized,
                    date_saisie=clean_text(row.get("date_saisie")) or None,
                    source_saisie=row.get("source_saisie", ""),
                    structure_verdict=validation.structure_verdict,
                    structure_reason=validation.structure_reason,
                    needs_human_review=validation.needs_human_review,
                    human_review_reason=validation.human_review_reason,
                )
            )
    return records
