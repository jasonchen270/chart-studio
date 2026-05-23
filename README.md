# Chart Studio

Natural-language to Plotly charts over uploaded CSVs: type a prompt and get back generated Python that renders an interactive chart, then tweak the code in a split-pane Monaco editor with live preview. The frontend is React + TypeScript + Vite with Supabase auth; the backend is FastAPI running a Claude tool-use loop that executes generated Python in a restricted subprocess, caches dataframes in Redis, and persists charts in Supabase Postgres.

## Prerequisites

- Node 18+
- pnpm 8+
- Python 3.11+ with `uv`
- Redis 7+
- Supabase project (Postgres + auth)

## Installation

```bash
# Backend
cd backend
uv sync

# Frontend
cd frontend
pnpm install
```

Apply the database migrations to your Supabase project. This creates the `charts` table and the row-level-security policies (each user can only see their own charts):

```bash
supabase db push   # or paste supabase/migrations/*.sql into the SQL editor in order
```

## Usage

```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm dev
```
