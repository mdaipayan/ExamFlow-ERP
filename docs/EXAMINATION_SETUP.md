# Examination Setup

The simple user flow is:

1. Create or approve the academic regulation version.
2. Create an examination using the approved regulation version.
3. Add courses.
4. Review the setup.
5. Activate the examination.

Activation freezes the regulation parameters into an Examination Rule Snapshot and moves the examination from Draft to In Progress.

The snapshot includes a canonical SHA-256 content hash. Later calculations must use this frozen configuration rather than live regulation settings.

Only SUPER_ADMIN or COE can create/activate examinations. Regulation approval is a COE action and requires a proposer different from the approver.

