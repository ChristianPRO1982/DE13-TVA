from pathlib import Path

import pytest

from de13_tva import settings
from de13_tva.countries import load_eu_country_codes


def test_load_eu_country_codes(tmp_path: Path):
    eu_file = tmp_path / "eu.csv"
    eu_file.write_text(
        "Code (ISO 3166),Name\nfr,France\n BE ,Belgique\n,\n",
        encoding="utf-8",
    )

    assert load_eu_country_codes(eu_file) == {"FR", "BE"}


def test_load_eu_country_codes_requires_code_column(tmp_path: Path):
    eu_file = tmp_path / "eu.csv"
    eu_file.write_text("code\nFR\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing expected column"):
        load_eu_country_codes(eu_file)


def test_load_dotenv_returns_empty_when_file_is_missing(tmp_path: Path):
    assert settings.load_dotenv(tmp_path / "missing.env") == {}


def test_load_dotenv_parses_simple_values(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# ignored\n\nPOSTGRES_DB='tva'\nPOSTGRES_USER=\"meridian\"\nINVALID",
        encoding="utf-8",
    )

    assert settings.load_dotenv(env_file) == {
        "POSTGRES_DB": "tva",
        "POSTGRES_USER": "meridian",
    }


def test_database_config_prefers_environment(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("POSTGRES_HOST", "db.example")
    monkeypatch.setenv("POSTGRES_PORT", "5436")
    monkeypatch.setenv("POSTGRES_DB", "env_db")
    monkeypatch.setenv("POSTGRES_USER", "env_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "env_password")

    assert settings.database_config() == {
        "host": "db.example",
        "port": 5436,
        "dbname": "env_db",
        "user": "env_user",
        "password": "env_password",
    }


def test_database_config_uses_dotenv_then_defaults(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "PROJECT_ROOT", tmp_path)
    for key in (
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text("POSTGRES_DB=from_file\n", encoding="utf-8")

    assert settings.database_config() == {
        "host": "localhost",
        "port": 5435,
        "dbname": "from_file",
        "user": "meridian",
        "password": "meridian",
    }
