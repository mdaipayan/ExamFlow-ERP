# Data Model

## Institution
institutions · institution_settings · users · roles · user_roles · audit_events

## Academic
regulations · regulation_versions · programmes · semesters · courses · course_components · course_schemes

## Students
students · student_programme_enrolments · student_semester_registrations

## Examinations
examinations · examination_courses · examination_registrations · eligibility_records · examination_parameter_snapshots

## Marks
mark_entries · mark_import_batches · mark_import_rows · mark_validation_issues

## Results
result_versions · result_courses · grade_cutoffs · semester_results · cgpa_records · grace_applications · scrutiny_records · revaluation_records

## Workflow
workflow_definitions · workflow_instances · workflow_actions · approvals

## Reporting
report_jobs · generated_documents · publication_records

## Integrity
Original marks are preserved. Grace marks are separate. Locked results are immutable. Corrections create a new version. Audit records are append-only.
