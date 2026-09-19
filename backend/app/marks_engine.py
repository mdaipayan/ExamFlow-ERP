from decimal import Decimal
from typing import Iterable


class MarksEngineError(Exception):
    """Base error for deterministic marks processing."""


def validate_mark(mark: Decimal | None, max_marks: Decimal) -> str | None:
    if mark is None:
        return None
    if mark < 0:
        return "MARK_NEGATIVE"
    if mark > max_marks:
        return "MARK_EXCEEDS_MAX"
    return None


def validate_weightages(weightages: Iterable[Decimal]) -> str | None:
    total = sum(weightages, Decimal("0"))
    if total != Decimal("100"):
        return f"WEIGHTAGE_TOTAL_INVALID:{total}"
    return None


def weighted_total(components: list[tuple[Decimal, Decimal, Decimal]]) -> Decimal:
    """Return total out of 100 from (marks, max_marks, weightage)."""
    total = Decimal("0")
    for marks, max_marks, weightage in components:
        if max_marks <= 0:
            raise MarksEngineError("Component maximum marks must be greater than zero.")
        total += (marks / max_marks) * weightage
    return total.quantize(Decimal("0.001"))
