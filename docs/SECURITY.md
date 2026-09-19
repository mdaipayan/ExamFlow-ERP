# Security

## Authentication
Use secure authentication. No switch-user endpoint. No client-side-only authorization.

## RBAC
SUPER_ADMIN · COE · TC · SCRUTINIZER · DATA_ENTRY · FACULTY · STUDENT

SUPER_ADMIN is technical/platform administration. COE is the academic/statutory authority.

## Critical actions
Require re-authentication for regulation approval, rule freeze, grace approval, result approval, result lock, publication, and destructive administration.

Critical rule changes require proposer != approver, explicit reason, audit event, and impact preview.

## Audit
Record actor, institution, action, entity, state summary, timestamp, request/correlation ID, and required reason.

## Production
HTTPS, secure cookies where applicable, rate limiting, backups, reviewed migrations, separate environment configuration, and production reset protection.
