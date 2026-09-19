from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Any

from .marks_engine import MarksEngineError, weighted_total


class AcademicConfigurationError(Exception):
    pass


Q = Decimal("0.01")


def _require(mapping: dict, path: str):
    current: Any = mapping
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise AcademicConfigurationError(f"Required academic parameter is missing: {path}")
        current = current[key]
    return current


def grade_points(config: dict) -> dict[str, Decimal]:
    raw = _require(config, "grade_points")
    if not isinstance(raw, dict) or not raw:
        raise AcademicConfigurationError("Required academic parameter is invalid: grade_points")
    return {str(k): Decimal(str(v)) for k, v in raw.items()}


def _absolute_grade(total: Decimal, grading: dict) -> str:
    boundaries = grading.get("boundaries")
    if not isinstance(boundaries, list) or not boundaries:
        raise AcademicConfigurationError("Required academic parameter is missing: grading.boundaries")

    normalized = sorted(
        (
            {"grade": str(item["grade"]), "min": Decimal(str(item["min"]))}
            for item in boundaries
            if "grade" in item and "min" in item
        ),
        key=lambda x: x["min"],
        reverse=True,
    )
    if len(normalized) != len(boundaries):
        raise AcademicConfigurationError("Each grading boundary must contain grade and min.")
    for item in normalized:
        if total >= item["min"]:
            return item["grade"]
    raise AcademicConfigurationError("No grading boundary covers the calculated total.")


def _relative_grade(total: Decimal, scores: list[Decimal], grading: dict) -> tuple[str, dict]:
    n = len(scores)
    threshold = int(_require(grading, "relative.minimum_cohort_size"))
    if n < threshold:
        raise AcademicConfigurationError(
            f"Statistical relative grading requires at least {threshold} students; got {n}."
        )

    mean = sum(scores, Decimal("0")) / Decimal(n)
    variance = sum((x - mean) ** 2 for x in scores) / Decimal(n)
    sd = variance.sqrt()

    bands = grading.get("relative", {}).get("bands")
    if not isinstance(bands, list) or not bands:
        raise AcademicConfigurationError("Required academic parameter is missing: grading.relative.bands")

    computed = []
    for band in bands:
        if "grade" not in band or "min_offset_sd" not in band:
            raise AcademicConfigurationError("Each relative band must contain grade and min_offset_sd.")
        cutoff = mean + Decimal(str(band["min_offset_sd"])) * sd
        computed.append({
            "grade": str(band["grade"]),
            "cutoff": cutoff.quantize(Q, rounding=ROUND_HALF_UP),
        })

    computed.sort(key=lambda x: x["cutoff"], reverse=True)
    for band in computed:
        if total >= band["cutoff"]:
            return band["grade"], {
                "mean": mean.quantize(Q, rounding=ROUND_HALF_UP),
                "population_sd": sd.quantize(Q, rounding=ROUND_HALF_UP),
                "cutoffs": computed,
                "cohort_size": n,
            }

    fallback = grading.get("relative", {}).get("fallback_grade")
    if fallback is None:
        raise AcademicConfigurationError("Required academic parameter is missing: grading.relative.fallback_grade")
    return str(fallback), {
        "mean": mean.quantize(Q, rounding=ROUND_HALF_UP),
        "population_sd": sd.quantize(Q, rounding=ROUND_HALF_UP),
        "cutoffs": computed,
        "cohort_size": n,
    }


def calculate_course_total(components: list[dict], marks_by_code: dict[str, Decimal]) -> Decimal:
    if not components:
        raise AcademicConfigurationError("Course has no assessment components.")

    weightage_total = sum(Decimal(str(c["weightage"])) for c in components)
    if weightage_total != Decimal("100"):
        raise AcademicConfigurationError(
            f"Course component weightage must total 100; got {weightage_total}."
        )

    values: list[tuple[Decimal, Decimal, Decimal]] = []
    for component in components:
        code = str(component["code"])
        if code not in marks_by_code or marks_by_code[code] is None:
            raise AcademicConfigurationError(f"Missing mark for component: {code}")
        values.append(
            (
                Decimal(str(marks_by_code[code])),
                Decimal(str(component["max_marks"])),
                Decimal(str(component["weightage"])),
            )
        )
    return weighted_total(values).quantize(Q, rounding=ROUND_HALF_UP)


def calculate_course_results(
    config: dict,
    components: list[dict],
    cohort: list[dict],
) -> dict:
    gp = grade_points(config)
    grading = _require(config, "grading")
    method = str(grading.get("method", "")).upper()
    if method not in {"ABSOLUTE", "STATISTICAL_RELATIVE"}:
        raise AcademicConfigurationError("Unsupported grading.method.")

    totals = [Decimal(str(row["total_marks"])) for row in cohort if row.get("total_marks") is not None]
    results = []

    for row in cohort:
        total = Decimal(str(row["total_marks"])) if row.get("total_marks") is not None else None
        override = row.get("grade_override")
        statistics = None

        if override:
            grade = str(override)
        elif total is None:
            raise AcademicConfigurationError(
                f"Missing total marks for student {row['registration_number']}."
            )
        elif method == "ABSOLUTE":
            grade = _absolute_grade(total, grading)
        else:
            grade, statistics = _relative_grade(total, totals, grading)

        if grade not in gp:
            raise AcademicConfigurationError(f"No grade point configured for grade: {grade}")

        results.append({
            **row,
            "grade": grade,
            "grade_point": gp[grade],
            "statistics": statistics,
        })

    return {"results": results, "statistics": statistics if method == "STATISTICAL_RELATIVE" else None}


def calculate_sgpa(results: list[dict], config: dict) -> Decimal:
    inclusion = config.get("sgpa", {}).get("included_grades")
    if not isinstance(inclusion, list) or not inclusion:
        raise AcademicConfigurationError("Required academic parameter is missing: sgpa.included_grades")

    included = set(str(x) for x in inclusion)
    numerator = Decimal("0")
    denominator = Decimal("0")

    for row in results:
        if row["grade"] not in included:
            continue
        credits = Decimal(str(row["credits"]))
        numerator += credits * Decimal(str(row["grade_point"]))
        denominator += credits

    if denominator == 0:
        return Decimal("0.00")
    return (numerator / denominator).quantize(Q, rounding=ROUND_HALF_UP)
