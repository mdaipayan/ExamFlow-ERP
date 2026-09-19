# Architecture

Browser → React/TypeScript → FastAPI → PostgreSQL
                                   ├─ Auth/RBAC
                                   ├─ Academic configuration
                                   ├─ Examination workflow
                                   ├─ Marks validation
                                   ├─ Result calculation
                                   ├─ Reports
                                   └─ Audit

## Environments
develop → Staging
main → Production

Staging and Production use separate databases and storage.

## Multi-tenant
Platform → Institution A / Institution B / Institution C

Tenant isolation is server-side; a client cannot choose an arbitrary institution by editing a request.

## Core domains
identity · academic · students · examination · marks · results · workflow · reports · audit

## Result lifecycle
DRAFT → IN_PROGRESS → TRIAL → UNDER_REVIEW → APPROVED → LOCKED → PUBLISHED

Locked/published results cannot be edited in place. Corrections/revaluation create a new result version.
