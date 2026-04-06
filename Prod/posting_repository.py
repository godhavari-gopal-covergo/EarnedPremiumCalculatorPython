"""Append-only JSON repository for immutable postings."""

from __future__ import annotations

import json
import calendar
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import List

from models import LedgerPosting


def _to_iso(d: date) -> str:
    return d.isoformat()


def _from_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def _from_iso_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _month_end(dt: date) -> date:
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return date(dt.year, dt.month, last_day)


def load_postings(path: Path) -> List[LedgerPosting]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    postings: List[LedgerPosting] = []
    for item in raw:
        reporting_start = _from_iso_date(item.get("reportingperiod_start", item.get("month")))
        reporting_end = _from_iso_date(
            item.get("reportingperiod_end", _month_end(reporting_start).isoformat())
        )
        postings.append(
            LedgerPosting(
                posting_id=item["posting_id"],
                policy_id=item["policy_id"],
                reportingperiod_start=reporting_start,
                reportingperiod_end=reporting_end,
                earned=Decimal(item["earned"]),
                unearned_paid_basis=Decimal(
                    item.get("unearned_paid_basis", item.get("unearned", "0.00"))
                ),
                unearned_written_basis=Decimal(
                    item.get("unearned_written_basis", item.get("unearned", "0.00"))
                ),
                collected_amount=Decimal(item.get("collected_amount", item.get("cash", "0.00"))),
                adjustment_earned=Decimal(item["adjustment_earned"]),
                adjustment_unearned_paid_basis=Decimal(
                    item.get("adjustment_unearned_paid_basis", item.get("adjustment_unearned", "0.00"))
                ),
                adjustment_unearned_written_basis=Decimal(
                    item.get("adjustment_unearned_written_basis", item.get("adjustment_unearned", "0.00"))
                ),
                source=item["source"],
                created_at=_from_iso_dt(item["created_at"]),
                run_id=item["run_id"],
                details={k: Decimal(v) for k, v in item.get("details", {}).items()},
            )
        )
    return postings


def append_postings(path: Path, new_postings: List[LedgerPosting]) -> None:
    existing = load_postings(path)
    all_postings = existing + new_postings

    payload = []
    for posting in all_postings:
        payload.append(
            {
                "posting_id": posting.posting_id,
                "policy_id": posting.policy_id,
                "reportingperiod_start": _to_iso(posting.reportingperiod_start),
                "reportingperiod_end": _to_iso(posting.reportingperiod_end),
                "earned": str(posting.earned),
                "unearned_paid_basis": str(posting.unearned_paid_basis),
                "unearned_written_basis": str(posting.unearned_written_basis),
                "collected_amount": str(posting.collected_amount),
                "adjustment_earned": str(posting.adjustment_earned),
                "adjustment_unearned_paid_basis": str(posting.adjustment_unearned_paid_basis),
                "adjustment_unearned_written_basis": str(posting.adjustment_unearned_written_basis),
                "source": posting.source,
                "created_at": posting.created_at.isoformat(),
                "run_id": posting.run_id,
                "details": {k: str(v) for k, v in posting.details.items()},
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

