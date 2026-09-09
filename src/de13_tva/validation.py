"""Structural validation for VAT numbers before VIES calls."""

from __future__ import annotations

import re
from dataclasses import dataclass

from de13_tva.cleaning import is_empty_like, normalize_country, normalize_vat_number
from de13_tva.countries import OUT_OF_SCOPE_COUNTRIES

SUPPORTED_PATTERNS: dict[str, re.Pattern[str]] = {
    "BE": re.compile(r"^BE\d{10}$"),
    "DK": re.compile(r"^DK\d{8}$"),
    "FI": re.compile(r"^FI\d{8}$"),
    "FR": re.compile(r"^FR[A-Z0-9]{2}\d{9}$"),
    "IT": re.compile(r"^IT\d{11}$"),
    "LU": re.compile(r"^LU\d{8}$"),
    "NL": re.compile(r"^NL\d{9}B\d{2}$"),
    "PL": re.compile(r"^PL\d{10}$"),
    "PT": re.compile(r"^PT\d{9}$"),
    "SE": re.compile(r"^SE\d{12}$"),
}

VALID = "valid"
INVALID = "invalid"
REVIEW = "review"


@dataclass(frozen=True)
class StructuralValidationResult:
    country_normalized: str
    vat_normalized: str
    structure_verdict: str
    structure_reason: str
    needs_human_review: bool
    human_review_reason: str | None


def validate_structural(
    country_raw: object,
    vat_raw: object,
    eu_country_codes: set[str],
) -> StructuralValidationResult:
    """Validate a raw VAT row structurally without calling VIES."""
    country = normalize_country(country_raw)
    vat = normalize_vat_number(vat_raw)

    if not country:
        return _review(country, vat, "pays_absent", "Pays déclaré absent")

    if country in OUT_OF_SCOPE_COUNTRIES:
        return _review(
            country,
            vat,
            "pays_hors_perimetre_vies",
            "Pays présent dans le fichier mais hors Union européenne",
        )

    if country not in eu_country_codes:
        return _review(
            country,
            vat,
            "pays_hors_referentiel_ue",
            "Code pays absent du référentiel UE local",
        )

    if is_empty_like(vat_raw) or not vat:
        return _review(country, vat, "numero_tva_absent", "Numéro TVA absent")

    prefix = vat[:2]
    if len(vat) >= 2 and prefix.isalpha() and prefix != country:
        return _review(
            country,
            vat,
            "prefixe_pays_incoherent",
            "Préfixe du numéro TVA différent du pays déclaré",
        )

    pattern = SUPPORTED_PATTERNS.get(country)
    if pattern is None:
        return _review(
            country,
            vat,
            "pays_hors_perimetre_vies",
            "Pays UE non couvert par les formats de ce jeu",
        )

    if not pattern.fullmatch(vat):
        return _review(
            country,
            vat,
            "format_invalide",
            "Numéro nettoyé non conforme au format attendu pour le pays",
        )

    return StructuralValidationResult(
        country_normalized=country,
        vat_normalized=vat,
        structure_verdict=VALID,
        structure_reason="ok_structure",
        needs_human_review=False,
        human_review_reason=None,
    )


def _review(
    country: str,
    vat: str,
    reason: str,
    human_reason: str,
) -> StructuralValidationResult:
    return StructuralValidationResult(
        country_normalized=country,
        vat_normalized=vat,
        structure_verdict=REVIEW,
        structure_reason=reason,
        needs_human_review=True,
        human_review_reason=human_reason,
    )
