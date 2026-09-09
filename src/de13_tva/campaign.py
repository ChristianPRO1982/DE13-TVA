"""Batch VIES verification campaign."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import sleep

from de13_tva.database import (
    fetch_vies_candidates_for_verification,
    upsert_vies_verification,
)
from de13_tva.vies import INDETERMINATE_VIES, INVALID_VIES, VALID_VIES, ViesClient


@dataclass(frozen=True)
class VerificationSummary:
    selected: int
    processed: int
    valid: int
    invalid: int
    indeterminate: int
    lines: list[str]


def run_vies_campaign(
    conn,
    *,
    client: ViesClient,
    sample_size: int | None,
    limit: int | None,
    delay: float,
    timeout: float,
    force_refresh: bool,
    refresh_days: int | None,
    batch_size: int = 100,
    progress: Callable[[str], None] | None = None,
    sleeper: Callable[[float], None] = sleep,
) -> VerificationSummary:
    if batch_size <= 0:
        raise ValueError("batch_size doit être strictement positif")

    max_rows = sample_size if sample_size is not None else limit
    lines = ["Début campagne VIES"]
    counts = {VALID_VIES: 0, INVALID_VIES: 0, INDETERMINATE_VIES: 0}
    processed = 0
    selected = 0
    batch_number = 0

    _emit(progress, lines[0])

    while max_rows is None or processed < max_rows:
        remaining = None if max_rows is None else max_rows - processed
        current_limit = batch_size if remaining is None else min(batch_size, remaining)

        candidates = fetch_vies_candidates_for_verification(
            conn,
            limit=current_limit,
            refresh_days=refresh_days,
            force_refresh=force_refresh,
        )
        if not candidates:
            break

        batch_number += 1
        selected += len(candidates)
        batch_line = (
            f"Batch {batch_number}: {len(candidates)} candidat(s) chargé(s), "
            "sauvegarde en base après chaque résultat."
        )
        lines.append(batch_line)
        _emit(progress, batch_line)

        for candidate in candidates:
            processed += 1
            normalized = candidate["numero_tva_nettoye"]
            result = client.verify(normalized, timeout=timeout)
            upsert_vies_verification(conn, result, origin="campaign")
            counts[result.vies_verdict] += 1
            line = (
                f"{processed} {normalized}: "
                f"{result.vies_verdict} ({result.response_time_ms} ms)"
            )
            lines.append(line)
            _emit(progress, line)
            if delay > 0 and (max_rows is None or processed < max_rows):
                sleeper(delay)

        if force_refresh:
            break

    return VerificationSummary(
        selected=selected,
        processed=processed,
        valid=counts[VALID_VIES],
        invalid=counts[INVALID_VIES],
        indeterminate=counts[INDETERMINATE_VIES],
        lines=lines,
    )


def _emit(progress: Callable[[str], None] | None, line: str) -> None:
    if progress is not None:
        progress(line)
