# Registration and Eligibility

Before marks are accepted, students must be registered for the examination courses.

## Registration
- COE/SUPER_ADMIN selects valid students.
- A student must belong to the examination's programme.
- Registration is created for every course already attached to the examination.
- Duplicate registrations are ignored safely.

## Eligibility
Eligibility is stored per student/course.
Attendance and other eligibility decisions are explicit records, not hidden calculation assumptions.

The initial source-based implementation supports the supplied manual's attendance/eligibility concept. Regulation-specific thresholds should later be enforced by the rule engine rather than duplicated in this route.

## User flow

Examination
→ Register Students
→ Check Eligibility
→ Import/Enter Marks
→ Validate
→ Calculate
