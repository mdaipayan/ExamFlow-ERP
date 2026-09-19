# Getting Started

## Prerequisites
Git · Node.js 20+ · Python 3.12+ · PostgreSQL (or Supabase)

## Backend
cd backend
python -m venv .venv
.venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

## Frontend
cd frontend
npm install
npm run dev

## First milestone
Login → institution → programme → course → student import → examination → marks import → validation → trial result → lock in staging.
