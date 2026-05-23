# Chart Studio

Natural-language → Plotly charts over uploaded CSVs. Type a prompt, get back generated
Python that renders an interactive chart; tweak the code in a split-pane editor and the
preview re-renders.

## What's inside

- **Frontend**: React + TypeScript + Vite, split-pane editor (Monaco), Plotly preview,
  Supabase auth, streaming tool-use traces over SSE.
- **Backend**: FastAPI. Claude tool-use loop (`load_csv`, `describe_df`, `render_chart`)
  with intermediate dataframes cached in Redis keyed by CSV content hash. Generated
  Python is executed in a restricted subprocess.
- **Storage**: Supabase Postgres for saved charts + row-level security on `owner_id`.

## Local dev

```bash
# Backend
cd backend
uv sync
uvicorn app.main:app --reload

# Frontend
cd frontend
pnpm install
pnpm dev
```

Env vars: see `.env.example` in each folder.
