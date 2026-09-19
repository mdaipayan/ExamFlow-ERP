# Rule Engine

Academic policy values are data/configuration. Calculation algorithms are application code.

## Rule families
AttendanceRule
ComponentMinimumRule
EligibilityRule
GradingRule
GradePointRule
CreditRule
GraceRule
AttemptRule
SGPARule
CGPARule
ClassificationRule
PublicationRule

## No hidden defaults
A missing required academic parameter must raise an explicit AcademicConfigurationError. Never silently substitute values such as 20, 30, 40, 50, 75, or 1.5.

## Examination rule snapshot
Every official examination gets a frozen configuration containing:
- examination_id
- regulation_id
- regulation_version_id
- version_label
- parameters
- content_hash
- frozen_at
- frozen_by_user_id

Official calculations use and verify this frozen configuration.

## Explainability
Each course result can show total marks, component calculation, eligibility checks, grading method, statistics/cutoffs where relevant, grade, grade point, special notation, and failure/ineligibility reason.
