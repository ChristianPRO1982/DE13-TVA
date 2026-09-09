"""Command line pipeline for phase 1."""

from __future__ import annotations

import argparse
from pathlib import Path

from de13_tva.campaign import run_vies_campaign
from de13_tva.database import (
    connect,
    ensure_schema,
    fetch_human_review_rows,
    fetch_phase2_human_review_rows,
    fetch_reconciliation_report,
    fetch_structural_report,
    upsert_records,
)
from de13_tva.importer import build_records
from de13_tva.reports import (
    export_human_review_csv,
    export_phase2_human_review_csv,
    format_import_report,
    format_reconciliation_report,
    format_structural_report,
    format_verify_report,
    write_text_report,
)
from de13_tva.settings import (
    DEFAULT_DATA_FILE,
    DEFAULT_EU_CODES_FILE,
    DEFAULT_PHASE_1_REPORTS_DIR,
    DEFAULT_PHASE_2_REPORTS_DIR,
    DEFAULT_VIES_TIMEOUT_SECONDS,
)
from de13_tva.vies import ViesClient


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DE13 TVA pipeline")
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

    verify_parser = subparsers.add_parser("verify-vies")
    verify_parser.add_argument("--sample-size", type=int)
    verify_parser.add_argument("--limit", type=int)
    verify_parser.add_argument("--delay", type=float, default=1.0)
    verify_parser.add_argument(
        "--timeout", type=float, default=DEFAULT_VIES_TIMEOUT_SECONDS
    )
    verify_parser.add_argument("--force-refresh", action="store_true")
    verify_parser.add_argument("--refresh-days", type=int)
    verify_parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_PHASE_2_REPORTS_DIR / "verify-vies.txt",
    )
    verify_parser.set_defaults(func=verify_vies)

    reconciliation_parser = subparsers.add_parser("reconciliation-report")
    reconciliation_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PHASE_2_REPORTS_DIR / "reconciliation-report.txt",
    )
    reconciliation_parser.set_defaults(func=reconciliation_report)

    phase2_review_parser = subparsers.add_parser("export-phase2-human-review")
    phase2_review_parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_PHASE_2_REPORTS_DIR / "a_reviser.csv",
    )
    phase2_review_parser.set_defaults(func=export_phase2_human_review)

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


def verify_vies(args: argparse.Namespace) -> None:
    with connect() as conn:
        ensure_schema(conn)
        summary = run_vies_campaign(
            conn,
            client=ViesClient(),
            sample_size=args.sample_size,
            limit=args.limit,
            delay=args.delay,
            timeout=args.timeout,
            force_refresh=args.force_refresh,
            refresh_days=args.refresh_days,
        )
    content = format_verify_report(summary)
    write_text_report(content, args.report_output)
    print(content)
    print(f"Rapport ecrit dans {args.report_output}")


def reconciliation_report(args: argparse.Namespace) -> None:
    with connect() as conn:
        ensure_schema(conn)
        report = fetch_reconciliation_report(conn)
    content = format_reconciliation_report(report)
    write_text_report(content, args.output)
    print(content)
    print(f"Rapport ecrit dans {args.output}")


def export_phase2_human_review(args: argparse.Namespace) -> None:
    with connect() as conn:
        ensure_schema(conn)
        rows = fetch_phase2_human_review_rows(conn)
    exported = export_phase2_human_review_csv(rows, args.output)
    print(f"{exported} lignes exportees vers {args.output}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
