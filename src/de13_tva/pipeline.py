"""Command line pipeline for phase 1."""

from __future__ import annotations

import argparse
from pathlib import Path

from de13_tva.database import (
    connect,
    ensure_schema,
    fetch_human_review_rows,
    fetch_structural_report,
    upsert_records,
)
from de13_tva.importer import build_records
from de13_tva.reports import (
    export_human_review_csv,
    format_import_report,
    format_structural_report,
    write_text_report,
)
from de13_tva.settings import (
    DEFAULT_DATA_FILE,
    DEFAULT_EU_CODES_FILE,
    DEFAULT_PHASE_1_REPORTS_DIR,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DE13 TVA phase 1 pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import-data")
    import_parser.add_argument("--csv", type=Path, default=DEFAULT_DATA_FILE)
    import_parser.add_argument("--eu-codes", type=Path, default=DEFAULT_EU_CODES_FILE)
    import_parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_PHASE_1_REPORTS_DIR / "import-data.txt",
    )
    import_parser.set_defaults(func=import_data)

    report_parser = subparsers.add_parser("structural-report")
    report_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PHASE_1_REPORTS_DIR / "structural-report.txt",
    )
    report_parser.set_defaults(func=structural_report)

    export_parser = subparsers.add_parser("export-human-review")
    export_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PHASE_1_REPORTS_DIR / "a_reviser.csv",
    )
    export_parser.set_defaults(func=export_human_review)

    return parser


def import_data(args: argparse.Namespace) -> None:
    records = build_records(args.csv, args.eu_codes)
    with connect() as conn:
        ensure_schema(conn)
        imported = upsert_records(conn, records)
    report = format_import_report(imported)
    write_text_report(report, args.report_output)
    print(report)
    print(f"Rapport ecrit dans {args.report_output}")


def structural_report(args: argparse.Namespace) -> None:
    with connect() as conn:
        report = fetch_structural_report(conn)
    content = format_structural_report(report)
    write_text_report(content, args.output)
    print(content)
    print(f"Rapport ecrit dans {args.output}")


def export_human_review(args: argparse.Namespace) -> None:
    with connect() as conn:
        rows = fetch_human_review_rows(conn)
    exported = export_human_review_csv(rows, args.output)
    print(f"{exported} lignes exportees vers {args.output}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
