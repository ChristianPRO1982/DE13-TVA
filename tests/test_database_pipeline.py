from pathlib import Path

import psycopg

from de13_tva import database, pipeline
from de13_tva.importer import VatRecord
from de13_tva.vies import ViesVerification


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


def sample_vies_verification(payload=None) -> ViesVerification:
    from datetime import UTC, datetime

    return ViesVerification(
        numero_tva_nettoye="FR27552032534",
        country_code="FR",
        vat_number="27552032534",
        vies_verdict="valide",
        checked_at=datetime(2026, 9, 9, tzinfo=UTC),
        http_status=200,
        response_time_ms=10,
        response_payload=payload,
        error_message=None,
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
    assert "CREATE TABLE IF NOT EXISTS vies_attempts" in conn.cursor_obj.queries[0]
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


def test_fetch_vies_candidates_for_verification_filters_unverified():
    conn = FakeConnection()
    conn.cursor_obj.description = [FakeDescription("numero_tva_nettoye")]
    conn.cursor_obj.fetchall_results = [[("FR27552032534",)]]

    rows = database.fetch_vies_candidates_for_verification(
        conn,
        limit=5,
        refresh_days=None,
        force_refresh=False,
    )

    assert rows == [{"numero_tva_nettoye": "FR27552032534"}]
    assert "vv.numero_tva_nettoye IS NULL" in conn.cursor_obj.queries[0]
    assert conn.cursor_obj.params[0]["limit"] == 5


def test_fetch_vies_candidates_for_verification_filters_stale():
    conn = FakeConnection()
    conn.cursor_obj.description = [FakeDescription("numero_tva_nettoye")]
    conn.cursor_obj.fetchall_results = [[]]

    database.fetch_vies_candidates_for_verification(
        conn,
        limit=None,
        refresh_days=30,
        force_refresh=False,
    )

    assert "refresh_days" in conn.cursor_obj.params[0]
    assert "checked_at < now()" in conn.cursor_obj.queries[0]


def test_fetch_vies_candidates_for_verification_force_refresh_has_no_filter():
    conn = FakeConnection()
    conn.cursor_obj.description = [FakeDescription("numero_tva_nettoye")]
    conn.cursor_obj.fetchall_results = [[]]

    database.fetch_vies_candidates_for_verification(
        conn,
        limit=None,
        refresh_days=30,
        force_refresh=True,
    )

    assert "WHERE" not in conn.cursor_obj.queries[0]
    assert conn.cursor_obj.params[0] == {}


def test_upsert_vies_verification_with_payload_and_without_payload():
    conn = FakeConnection()

    database.upsert_vies_verification(
        conn,
        sample_vies_verification({"isValid": True}),
        origin="api",
    )
    database.upsert_vies_verification(
        conn,
        sample_vies_verification(None),
        origin="campaign",
    )

    assert len(conn.cursor_obj.queries) == 4
    assert "INSERT INTO vies_attempts" in conn.cursor_obj.queries[0]
    assert "INSERT INTO vies_verifications" in conn.cursor_obj.queries[1]
    assert conn.cursor_obj.params[0]["origin"] == "api"
    assert conn.cursor_obj.params[0]["response_payload"] is not None
    assert conn.cursor_obj.params[2]["response_payload"] is None
    assert conn.commits == 2


def test_insert_vies_attempt_commits_without_upserting_current_verdict():
    conn = FakeConnection()

    database.insert_vies_attempt(
        conn,
        sample_vies_verification({"isValid": True}),
        origin="api",
    )

    assert len(conn.cursor_obj.queries) == 1
    assert "INSERT INTO vies_attempts" in conn.cursor_obj.queries[0]
    assert "INSERT INTO vies_verifications" not in conn.cursor_obj.queries[0]
    assert conn.cursor_obj.params[0]["origin"] == "api"
    assert conn.commits == 1


def test_fetch_stored_vies_verification_returns_none():
    conn = FakeConnection()
    conn.cursor_obj.fetchone_results = [None]

    assert database.fetch_stored_vies_verification(conn, "FR27552032534") is None


def test_fetch_stored_vies_verification_returns_dict():
    conn = FakeConnection()
    conn.cursor_obj.description = [
        FakeDescription("numero_tva_nettoye"),
        FakeDescription("vies_verdict"),
    ]
    conn.cursor_obj.fetchone_results = [("FR27552032534", "valide")]

    assert database.fetch_stored_vies_verification(conn, "FR27552032534") == {
        "numero_tva_nettoye": "FR27552032534",
        "vies_verdict": "valide",
    }


def test_record_human_review_item_commits():
    conn = FakeConnection()

    database.record_human_review_item(
        conn,
        source="api",
        input_raw="---",
        numero_tva_nettoye="",
        review_reason="pays_absent",
    )

    assert "INSERT INTO human_review_items" in conn.cursor_obj.queries[0]
    assert conn.cursor_obj.params[0]["source"] == "api"
    assert conn.commits == 1


def test_fetch_phase2_human_review_rows():
    conn = FakeConnection()
    conn.cursor_obj.description = [
        FakeDescription("source"),
        FakeDescription("input_raw"),
    ]
    conn.cursor_obj.fetchall_results = [[("api", "---")]]

    assert database.fetch_phase2_human_review_rows(conn) == [
        {"source": "api", "input_raw": "---"}
    ]


def test_fetch_reconciliation_details():
    conn = FakeConnection()
    conn.cursor_obj.description = [
        FakeDescription("source_id"),
        FakeDescription("final_verdict"),
    ]
    conn.cursor_obj.fetchall_results = [[(1, "valide"), (2, "indetermine")]]

    rows = database.fetch_reconciliation_details(conn)

    assert rows == [
        {"source_id": 1, "final_verdict": "valide"},
        {"source_id": 2, "final_verdict": "indetermine"},
    ]
    assert "final_verdict" in conn.cursor_obj.queries[0]
    assert "LEFT JOIN vies_verifications" in conn.cursor_obj.queries[0]


def test_fetch_reconciliation_report():
    conn = FakeConnection()
    conn.cursor_obj.fetchone_results = [
        (10,),
        (8,),
        (6,),
        (2,),
        (3,),
        (4,),
        (5,),
        (7,),
        (6,),
    ]
    conn.cursor_obj.fetchall_results = [
        [("ok_structure", 6)],
        [("indetermine", 1), ("valide", 1)],
        [("indetermine", 8), ("invalide", 1), ("valide", 1)],
    ]

    report = database.fetch_reconciliation_report(conn)

    assert report["total_rows"] == 10
    assert report["vies_verifications_total"] == 2
    assert report["by_final_verdict"] == [
        ("indetermine", 8),
        ("invalide", 1),
        ("valide", 1),
    ]
    assert report["duplicate_numbers"] == 3
    assert report["phase1_human_review"] == 4
    assert report["phase2_human_review"] == 5
    assert report["pending_vies"] == 7
    assert report["pending_vies_unique"] == 6


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


def test_pipeline_verify_vies(monkeypatch, tmp_path: Path, capsys):
    from types import SimpleNamespace

    conn = FakeConnection()
    output = tmp_path / "verify.txt"
    summary = SimpleNamespace(
        selected=1,
        processed=1,
        valid=1,
        invalid=0,
        indeterminate=0,
        lines=["ok"],
    )
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(pipeline, "ensure_schema", lambda connection: None)
    monkeypatch.setattr(
        pipeline, "run_vies_campaign", lambda connection, **kwargs: summary
    )

    assert (
        pipeline.main(
            [
                "verify-vies",
                "--sample-size",
                "1",
                "--delay",
                "0",
                "--report-output",
                str(output),
            ]
        )
        == 0
    )

    assert "Rapport verification VIES phase 2" in capsys.readouterr().out
    assert output.exists()


def test_pipeline_reconciliation_report(monkeypatch, tmp_path: Path, capsys):
    conn = FakeConnection()
    output = tmp_path / "reconciliation.txt"
    details = tmp_path / "reconciliation.csv"
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(pipeline, "ensure_schema", lambda connection: None)
    monkeypatch.setattr(pipeline, "fetch_reconciliation_report", lambda connection: {})
    monkeypatch.setattr(
        pipeline, "fetch_reconciliation_details", lambda connection: [{"source_id": 1}]
    )
    monkeypatch.setattr(
        pipeline,
        "format_reconciliation_report",
        lambda report: "reconciliation",
    )
    monkeypatch.setattr(
        pipeline,
        "export_reconciliation_details_csv",
        lambda rows, output_file: len(rows),
    )

    assert (
        pipeline.main(
            [
                "reconciliation-report",
                "--output",
                str(output),
                "--details-output",
                str(details),
            ]
        )
        == 0
    )

    captured = capsys.readouterr().out
    assert "Rapport ecrit" in captured
    assert f"1 lignes exportees vers {details}" in captured
    assert output.read_text(encoding="utf-8") == "reconciliation\n"


def test_pipeline_export_phase2_human_review(monkeypatch, tmp_path: Path, capsys):
    conn = FakeConnection()
    output = tmp_path / "phase2.csv"
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(pipeline, "ensure_schema", lambda connection: None)
    monkeypatch.setattr(
        pipeline,
        "fetch_phase2_human_review_rows",
        lambda connection: [{"source": "api"}],
    )
    monkeypatch.setattr(
        pipeline,
        "export_phase2_human_review_csv",
        lambda rows, output_file: len(rows),
    )

    assert pipeline.main(["export-phase2-human-review", "--output", str(output)]) == 0

    assert f"1 lignes exportees vers {output}" in capsys.readouterr().out


def test_pipeline_demo_run(monkeypatch, tmp_path: Path, capsys):
    from types import SimpleNamespace

    conn = FakeConnection()
    monkeypatch.setattr(pipeline, "DEFAULT_PHASE_1_REPORTS_DIR", tmp_path / "phase_1")
    monkeypatch.setattr(pipeline, "DEFAULT_PHASE_2_REPORTS_DIR", tmp_path / "phase_2")
    monkeypatch.setattr(pipeline, "DEFAULT_DATA_FILE", tmp_path / "data.csv")
    monkeypatch.setattr(pipeline, "DEFAULT_EU_CODES_FILE", tmp_path / "eu.csv")
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(pipeline, "ensure_schema", lambda connection: None)
    monkeypatch.setattr(pipeline, "build_records", lambda csv, eu: ["record"])
    monkeypatch.setattr(
        pipeline, "upsert_records", lambda connection, records: len(records)
    )
    monkeypatch.setattr(
        pipeline,
        "fetch_structural_report",
        lambda connection: {
            "total_rows": 1,
            "unique_cleaned": 1,
            "vies_candidates": 1,
            "vies_calls_avoided": 0,
            "by_reason": [("ok_structure", 1)],
        },
    )
    monkeypatch.setattr(
        pipeline,
        "fetch_reconciliation_report",
        lambda connection: {
            "total_rows": 1,
            "unique_cleaned": 1,
            "vies_candidates": 1,
            "vies_calls_avoided": 0,
            "vies_verifications_total": 0,
            "duplicate_numbers": 0,
            "phase1_human_review": 0,
            "phase2_human_review": 0,
            "pending_vies": 1,
            "pending_vies_unique": 1,
            "by_vies_verdict": [],
            "by_final_verdict": [("indetermine", 1)],
            "by_reason": [("ok_structure", 1)],
        },
    )
    monkeypatch.setattr(pipeline, "fetch_human_review_rows", lambda connection: [])
    monkeypatch.setattr(pipeline, "fetch_reconciliation_details", lambda connection: [])
    monkeypatch.setattr(
        pipeline, "fetch_phase2_human_review_rows", lambda connection: []
    )
    monkeypatch.setattr(
        pipeline,
        "run_vies_campaign",
        lambda connection, **kwargs: SimpleNamespace(
            selected=0,
            processed=0,
            valid=0,
            invalid=0,
            indeterminate=0,
            lines=[],
        ),
    )

    assert (
        pipeline.main(
            [
                "demo-run",
                "--sample-size",
                "1",
                "--delay",
                "0",
                "--report-output",
                str(tmp_path / "demo.txt"),
            ]
        )
        == 0
    )

    assert "Déroulé de démonstration" in capsys.readouterr().out
    assert (tmp_path / "phase_2" / "reconciliation-details.csv").exists()


def test_pipeline_demo_run_can_skip_vies(monkeypatch, tmp_path: Path, capsys):
    conn = FakeConnection()
    monkeypatch.setattr(pipeline, "DEFAULT_PHASE_1_REPORTS_DIR", tmp_path / "phase_1")
    monkeypatch.setattr(pipeline, "DEFAULT_PHASE_2_REPORTS_DIR", tmp_path / "phase_2")
    monkeypatch.setattr(pipeline, "DEFAULT_DATA_FILE", tmp_path / "data.csv")
    monkeypatch.setattr(pipeline, "DEFAULT_EU_CODES_FILE", tmp_path / "eu.csv")
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    monkeypatch.setattr(pipeline, "ensure_schema", lambda connection: None)
    monkeypatch.setattr(pipeline, "build_records", lambda csv, eu: ["record"])
    monkeypatch.setattr(
        pipeline, "upsert_records", lambda connection, records: len(records)
    )
    monkeypatch.setattr(
        pipeline,
        "fetch_structural_report",
        lambda connection: {
            "total_rows": 1,
            "unique_cleaned": 1,
            "vies_candidates": 1,
            "vies_calls_avoided": 0,
            "by_reason": [("ok_structure", 1)],
        },
    )
    monkeypatch.setattr(
        pipeline,
        "fetch_reconciliation_report",
        lambda connection: {
            "total_rows": 1,
            "unique_cleaned": 1,
            "vies_candidates": 1,
            "vies_calls_avoided": 0,
            "vies_verifications_total": 0,
            "duplicate_numbers": 0,
            "phase1_human_review": 0,
            "phase2_human_review": 0,
            "pending_vies": 1,
            "pending_vies_unique": 1,
            "by_vies_verdict": [],
            "by_final_verdict": [("indetermine", 1)],
            "by_reason": [("ok_structure", 1)],
        },
    )
    monkeypatch.setattr(pipeline, "fetch_human_review_rows", lambda connection: [])
    monkeypatch.setattr(pipeline, "fetch_reconciliation_details", lambda connection: [])
    monkeypatch.setattr(
        pipeline, "fetch_phase2_human_review_rows", lambda connection: []
    )
    monkeypatch.setattr(
        pipeline,
        "run_vies_campaign",
        lambda connection, **kwargs: (_ for _ in ()).throw(AssertionError),
    )

    assert (
        pipeline.main(
            [
                "demo-run",
                "--skip-vies",
                "--report-output",
                str(tmp_path / "demo.txt"),
            ]
        )
        == 0
    )

    assert "Campagne VIES ignorée sur demande." in capsys.readouterr().out
