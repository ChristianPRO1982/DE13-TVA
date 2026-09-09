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
    sleeper: Callable[[float], None] = sleep,
) -> VerificationSummary:
    max_rows = sample_size if sample_size is not None else limit
    candidates = fetch_vies_candidates_for_verification(
        conn,
        limit=max_rows,
        refresh_days=refresh_days,
        force_refresh=force_refresh,
    )
    lines = ["Debut campagne VIES"]
    counts = {VALID_VIES: 0, INVALID_VIES: 0, INDETERMINATE_VIES: 0}

    for index, candidate in enumerate(candidates, start=1):
        normalized = candidate["numero_tva_nettoye"]
        result = client.verify(normalized, timeout=timeout)
        upsert_vies_verification(conn, result, origin="campaign")
        counts[result.vies_verdict] += 1
        lines.append(
            f"{index}/{len(candidates)} {normalized}: "
            f"{result.vies_verdict} ({result.response_time_ms} ms)"
        )
        if delay > 0 and index < len(candidates):
            sleeper(delay)

    return VerificationSummary(
        selected=len(candidates),
        processed=len(candidates),
        valid=counts[VALID_VIES],
        invalid=counts[INVALID_VIES],
        indeterminate=counts[INDETERMINATE_VIES],
        lines=lines,
    )
