# Environments

## Staging
Used for integration, rule testing, sample data, UI testing, and demos. It may be reset. It contains no official examination data.

## Production / Live
Used for real institution operations and official examination records. No destructive reset. Locked result records are immutable.

## Git flow
feature/* → develop → Staging → verification → pull request → main → Production

## Free-tier-first MVP
GitHub + Vercel + Supabase + free/low-cost FastAPI hosting where available.

Do not buy a domain, VPS, or dedicated server before a client requires it.

## Required environment variables
ENVIRONMENT
DATABASE_URL
JWT_SECRET
STORAGE_ENDPOINT
STORAGE_BUCKET
FRONTEND_URL

Production has independent values.

A destructive seed/reset command must refuse to run in Production.
