import pytest

from de13_tva.countries import OUT_OF_SCOPE_COUNTRIES
from de13_tva.validation import REVIEW, VALID, validate_structural

EU_CODES = {"BE", "DK", "FI", "FR", "IT", "LU", "NL", "PL", "PT", "SE"}


@pytest.mark.parametrize(
    ("country", "vat"),
    [
        ("BE", "BE0123456789"),
        ("DK", "DK12345678"),
        ("FI", "FI12345678"),
        ("FR", "FRAB123456789"),
        ("IT", "IT12345678901"),
        ("LU", "LU12345678"),
        ("NL", "NL123456789B01"),
        ("PL", "PL1234567890"),
        ("PT", "PT123456789"),
        ("SE", "SE123456789012"),
    ],
)
def test_valid_formats_for_supported_countries(country, vat):
    result = validate_structural(country, vat, EU_CODES)

    assert result.structure_verdict == VALID
    assert result.structure_reason == "ok_structure"
    assert not result.needs_human_review


@pytest.mark.parametrize("country", ["QQ", "XX", "ZZ"])
def test_country_outside_eu_reference_is_for_review(country):
    result = validate_structural(country, f"{country}123456789", EU_CODES)

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "pays_hors_referentiel_ue"
    assert result.needs_human_review


@pytest.mark.parametrize("country", sorted(OUT_OF_SCOPE_COUNTRIES))
def test_gb_and_uk_are_out_of_scope_for_review(country):
    result = validate_structural(country, f"{country}123456789", EU_CODES)

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "pays_hors_perimetre_vies"
    assert result.needs_human_review


def test_missing_vat_number_is_for_review():
    result = validate_structural("FR", "   ", EU_CODES)

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "numero_tva_absent"
    assert result.needs_human_review


def test_missing_country_is_for_review():
    result = validate_structural(" ", "FR27552032534", EU_CODES)

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "pays_absent"
    assert result.needs_human_review


def test_country_prefix_mismatch_is_for_review():
    result = validate_structural("FR", "BE0123456789", EU_CODES)

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "prefixe_pays_incoherent"
    assert result.needs_human_review


def test_invalid_format_after_cleaning_is_for_review():
    result = validate_structural("FR", "FR123", EU_CODES)

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "format_invalide"
    assert result.needs_human_review


def test_eu_country_not_supported_by_dataset_formats_is_for_review():
    result = validate_structural("DE", "DE123456789", EU_CODES | {"DE"})

    assert result.structure_verdict == REVIEW
    assert result.structure_reason == "pays_hors_perimetre_vies"
    assert result.needs_human_review


def test_no_country_prefix_is_invalid_format_not_prefix_mismatch():
    result = validate_structural("FR", "123456789", EU_CODES)

    assert result.structure_reason == "format_invalide"
