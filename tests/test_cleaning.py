from de13_tva.cleaning import is_empty_like, normalize_country, normalize_vat_number


def test_normalize_vat_number_removes_any_non_alphanumeric_character():
    assert normalize_vat_number("AA 9999 9999") == "AA99999999"
    assert normalize_vat_number("AA-9999.9999") == "AA99999999"
    assert normalize_vat_number("AA/9999_9999") == "AA99999999"


def test_normalize_vat_number_handles_empty_values():
    assert normalize_vat_number("") == ""
    assert normalize_vat_number("   ") == ""
    assert normalize_vat_number("--- / _ ...") == ""
    assert normalize_vat_number(None) == ""


def test_normalize_country():
    assert normalize_country(" fr ") == "FR"
    assert normalize_country(None) == ""


def test_is_empty_like():
    assert is_empty_like("")
    assert is_empty_like(" ")
    assert is_empty_like("-")
    assert is_empty_like("N/A")
    assert is_empty_like("null")
    assert not is_empty_like("FR27552032534")
