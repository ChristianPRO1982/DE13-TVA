from pathlib import Path

import psycopg

from de13_tva import database, pipeline
from de13_tva.importer import VatRecord


class FakeDescription:
    def __init__(self, name: str):
        self.name = name


class FakeCursor:
    def __init__(self):
        self.queries = []
        self.params = []
        self.fetchone_results = []
        self.fetchall_results = []
        self.description = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.queries.append(query)
        self.params.append(params)

    def fetchone(self):
        return self.fetchone_results.pop(0)

    def fetchall(self):
        return self.fetchall_results.pop(0)


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


def sample_record(source_id: int = 1) -> VatRecord:
    return VatRecord(
        source_id=source_id,
        raison_sociale="Acme",
        pays_declare_brut="FR",
        pays_declare_normalise="FR",
        numero_tva_brut="FR 27 552 032 534",
        numero_tva_nettoye="FR27552032534",
        date_saisie="2026-01-01",
        source_saisie="crm",
        structure_verdict="valid",
        structure_reason="ok_structure",
        needs_human_review=False,
        human_review_reason=None,
    )


def test_connect_uses_database_config(monkeypatch):
    calls = []
    monkeypatch.setattr(
        database,
        "database_config",
        lambda: {"host": "localhost", "port": 5435, "dbname": "tva"},
    )
    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: calls.append(kwargs))

    database.connect()

    assert calls == [{"host": "localhost", "port": 5435, "dbname": "tva"}]


def test_ensure_schema_executes_schema_and_commits():
    conn = FakeConnection()

    database.ensure_schema(conn)

    assert "CREATE TABLE IF NOT EXISTS vat_records" in conn.cursor_obj.queries[0]
    assert conn.commits == 1


def test_upsert_records_is_counted_and_committed():
    conn = FakeConnection()

    count = database.upsert_records(conn, [sample_record(1), sample_record(2)])

    assert count == 2
    assert len(conn.cursor_obj.queries) == 2
    assert conn.cursor_obj.params[0]["source_id"] == 1
    assert conn.commits == 1


def test_fetch_structural_report():
    conn = FakeConnection()
    conn.cursor_obj.fetchone_results = [(10,), (8,), (6,)]
    conn.cursor_obj.fetchall_results = [[("ok_structure", 6), ("format_invalide", 4)]]

    report = database.fetch_structural_report(conn)

    assert report == {
        "total_rows": 10,
        "by_reason": [("ok_structure", 6), ("format_invalide", 4)],
        "unique_cleaned": 8,
        "vies_candidates": 6,
        "vies_calls_avoided": 4,
    }


def test_fetch_human_review_rows():
    conn = FakeConnection()
    conn.cursor_obj.description = [
        FakeDescription("source_id"),
        FakeDescription("raison_sociale"),
    ]
    conn.cursor_obj.fetchall_results = [[(1, "Bad")]]

    assert database.fetch_human_review_rows(conn) == [
        {"source_id": 1, "raison_sociale": "Bad"}
    ]


def test_pipeline_import_data(monkeypatch, tmp_path: Path, capsys):
    conn = FakeConnection()
    calls = []
    output = tmp_path / "import.txt"
    monkeypatch.setattr(pipeline, "build_records", lambda csv, eu_codes: ["record"])
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(
        pipeline, "ensure_schema", lambda connection: calls.append(connection)
    )
    monkeypatch.setattr(
        pipeline, "upsert_records", lambda connection, records: len(records)
    )

    assert (
        pipeline.main(
            [
                "import-data",
                "--csv",
                str(tmp_path / "in.csv"),
                "--report-output",
                str(output),
            ]
        )
        == 0
    )

    assert calls == [conn]
    assert "Lignes importees ou mises a jour: 1" in capsys.readouterr().out
    assert output.exists()


def test_pipeline_structural_report(monkeypatch, tmp_path: Path, capsys):
    conn = FakeConnection()
    output = tmp_path / "structural.txt"
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(
        pipeline, "fetch_structural_report", lambda connection: {"x": 1}
    )
    monkeypatch.setattr(pipeline, "format_structural_report", lambda report: "report")

    assert pipeline.main(["structural-report", "--output", str(output)]) == 0

    assert f"Rapport ecrit dans {output}" in capsys.readouterr().out
    assert output.read_text(encoding="utf-8") == "report\n"


def test_pipeline_export_human_review(monkeypatch, tmp_path: Path, capsys):
    conn = FakeConnection()
    output = tmp_path / "review.csv"
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(
        pipeline, "fetch_human_review_rows", lambda connection: [{"x": 1}]
    )
    monkeypatch.setattr(
        pipeline,
        "export_human_review_csv",
        lambda rows, output_file: len(rows),
    )

    assert pipeline.main(["export-human-review", "--output", str(output)]) == 0

    assert f"1 lignes exportees vers {output}" in capsys.readouterr().out
