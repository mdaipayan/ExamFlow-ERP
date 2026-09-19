from decimal import Decimal

import pytest

from app.result_engine import AcademicConfigurationError, calculate_course_results, calculate_sgpa


def base_config():
    return {
        "grade_points": {
            "A+": 10,
            "A": 9,
            "B+": 8.25,
            "B": 7.5,
            "C+": 6.75,
            "C": 6,
            "D": 5,
            "F": 0,
        },
        "grading": {
            "method": "ABSOLUTE",
            "boundaries": [
                {"grade": "A+", "min": 80},
                {"grade": "A", "min": 70},
                {"grade": "B+", "min": 60},
                {"grade": "B", "min": 50},
                {"grade": "C+", "min": 45},
                {"grade": "C", "min": 40},
                {"grade": "D", "min": 30},
                {"grade": "F", "min": 0},
            ],
        },
        "sgpa": {
            "included_grades": ["A+", "A", "B+", "B", "C+", "C", "D", "F"],
            "non_counting_grades": ["G", "H", "I", "T"],
        },
        "result": {
            "pass_grades": ["A+", "A", "B+", "B", "C+", "C", "D"],
        },
    }


def test_absolute_result_uses_configured_boundaries():
    config = base_config()
    out = calculate_course_results(
        config,
        [],
        [{"student_id": "s1", "registration_number": "001", "total_marks": Decimal("72"), "credits": Decimal("4")}],
    )
    assert out["results"][0]["grade"] == "A"
    assert out["results"][0]["grade_point"] == Decimal("9")


def test_missing_required_grading_config_fails():
    config = base_config()
    del config["grade_points"]
    with pytest.raises(AcademicConfigurationError):
        calculate_course_results(
            config,
            [],
            [{"student_id": "s1", "registration_number": "001", "total_marks": Decimal("72"), "credits": Decimal("4")}],
        )


def test_sgpa_is_credit_weighted():
    config = base_config()
    results = [
        {"grade": "A", "grade_point": Decimal("9"), "credits": Decimal("4")},
        {"grade": "B+", "grade_point": Decimal("8.25"), "credits": Decimal("4")},
        {"grade": "C", "grade_point": Decimal("6"), "credits": Decimal("3")},
        {"grade": "F", "grade_point": Decimal("0"), "credits": Decimal("3")},
    ]
    assert calculate_sgpa(results, config) == Decimal("6.21")


def test_relative_method_requires_cohort_threshold():
    config = base_config()
    config["grading"] = {
        "method": "STATISTICAL_RELATIVE",
        "relative": {
            "minimum_cohort_size": 30,
            "bands": [
                {"grade": "A", "min_offset_sd": 1.0},
                {"grade": "B", "min_offset_sd": 0.0},
                {"grade": "C", "min_offset_sd": -1.0},
            ],
            "fallback_grade": "F",
        },
    }
    cohort = [
        {"student_id": str(i), "registration_number": str(i), "total_marks": Decimal("50"), "credits": Decimal("1")}
        for i in range(29)
    ]
    with pytest.raises(AcademicConfigurationError):
        calculate_course_results(config, [], cohort)
