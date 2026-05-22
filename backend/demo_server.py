"""Standalone demo backend.

Replaces the full FastAPI app for portfolio/demo purposes:
  - No Supabase: every request is treated as authenticated.
  - No Redis: a process-local dict caches uploaded CSV bytes.
  - LLM: shells out to the `claude` CLI in --print mode with a JSON
    schema for structured output. The CLI handles auth via the user's
    existing Claude Code session, so we don't need an API key here.
  - /api/execute runs the model-or-user Python in a subprocess, exactly
    like the production executor, so the split-pane editor is fully live.

Run:
    python demo_server.py
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import sys
import tempfile
import textwrap
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Chart Studio (demo)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Process-local cache: {csv_hash: (csv_bytes, dataframe)}
_CACHE: dict[str, tuple[bytes, pd.DataFrame]] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "demo"}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    csv_hash = hashlib.sha256(content).hexdigest()
    _CACHE[csv_hash] = (content, df)
    return {
        "csv_hash": csv_hash,
        "rows": int(df.shape[0]),
        "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
    }


class GenerateRequest(BaseModel):
    csv_hash: str
    prompt: str


_SCHEMA = {
    "type": "object",
    "properties": {
        "chart_type": {
            "type": "string",
            "enum": ["bar", "line", "scatter", "histogram", "box", "heatmap", "pie", "area"],
        },
        "x": {"type": "string"},
        "y": {"type": "string"},
        "rationale": {"type": "string"},
        "code": {"type": "string"},
    },
    "required": ["chart_type", "rationale", "code"],
}


def _build_llm_prompt(df: pd.DataFrame, user_prompt: str) -> str:
    """The CLI is one-shot, so we pack the dataframe summary into the prompt
    rather than exposing it as a tool. The model still has to commit to a
    chart_type before emitting code, which is the same plan-then-act
    discipline the production tool loop enforces."""
    sample = df.head(5).to_dict(orient="records")
    schema_desc = "\n".join(f"  - {c}: {df[c].dtype}" for c in df.columns)
    return (
        "You are Chart Studio. Generate Plotly Python for the user's request.\n\n"
        f"Data shape: {df.shape[0]} rows x {df.shape[1]} cols\n"
        f"Columns:\n{schema_desc}\n"
        f"Sample rows: {sample}\n\n"
        f"User request: {user_prompt}\n\n"
        "Rules for the `code` field:\n"
        "  - Assume `df` is already in scope (do NOT call pd.read_csv).\n"
        "  - Use plotly.express or plotly.graph_objects only.\n"
        "  - Assign the figure to a variable named `fig`.\n"
        "  - No I/O, no network, no os/sys imports.\n"
        "  - Keep it under 20 lines."
    )


async def _call_claude(prompt: str) -> dict:
    """Invoke the claude CLI and return the structured_output dict."""
    proc = await asyncio.create_subprocess_exec(
        "claude",
        "-p",
        "--output-format", "json",
        "--model", "claude-haiku-4-5",
        "--json-schema", json.dumps(_SCHEMA),
        prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {stderr.decode('utf-8', errors='replace')}")

    events = json.loads(stdout.decode("utf-8", errors="replace"))
    # Walk to the `result` event; it carries `structured_output`.
    for evt in reversed(events):
        if evt.get("type") == "result" and "structured_output" in evt:
            return evt["structured_output"]
    raise RuntimeError("claude CLI returned no structured_output")


@app.post("/api/generate")
async def generate(req: GenerateRequest) -> EventSourceResponse:
    """Stream a tool-use-style trace around a real claude CLI call.

    The CLI is one-shot (it doesn't expose its internal tool loop to us),
    so we synthesise describe_df/suggest_chart/render_chart events to keep
    the UI's trace log informative. The *content* of those events is real
    (real shape/columns, real model rationale, real generated code).
    """
    if req.csv_hash not in _CACHE:
        async def err():
            yield {"event": "done", "data": json.dumps({"type": "done", "code": None, "stop_reason": "no_csv"})}
        return EventSourceResponse(err())

    _, df = _CACHE[req.csv_hash]

    async def stream():
        # Phase 1: data inspection (real).
        yield {"event": "thought", "data": json.dumps({"type": "thought", "text": "Inspecting the uploaded data..."})}
        yield {"event": "tool_call", "data": json.dumps({"type": "tool_call", "name": "describe_df", "input": {}})}
        yield {
            "event": "tool_result",
            "data": json.dumps({
                "type": "tool_result",
                "name": "describe_df",
                "result": {
                    "shape": list(df.shape),
                    "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
                },
            }),
        }

        # Phase 2: real CLI call.
        yield {"event": "thought", "data": json.dumps({"type": "thought", "text": "Asking Claude for a chart plan and code..."})}
        try:
            result = await _call_claude(_build_llm_prompt(df, req.prompt))
        except Exception as exc:
            yield {"event": "done", "data": json.dumps({"type": "done", "code": None, "stop_reason": f"error: {exc}"})}
            return

        # Phase 3: surface the model's actual commitments.
        yield {
            "event": "tool_call",
            "data": json.dumps({
                "type": "tool_call",
                "name": "suggest_chart",
                "input": {
                    "chart_type": result.get("chart_type"),
                    "x": result.get("x"),
                    "y": result.get("y"),
                    "rationale": result.get("rationale"),
                },
            }),
        }
        yield {"event": "tool_result", "data": json.dumps({"type": "tool_result", "name": "suggest_chart", "result": {"ack": True}})}

        code = result.get("code", "")
        yield {"event": "tool_call", "data": json.dumps({"type": "tool_call", "name": "render_chart", "input": {"code": code}})}
        yield {
            "event": "tool_result",
            "data": json.dumps({
                "type": "tool_result",
                "name": "render_chart",
                "result": {"received": True, "lines": code.count("\n") + 1},
            }),
        }
        yield {"event": "code", "data": json.dumps({"type": "code", "code": code})}
        yield {"event": "done", "data": json.dumps({"type": "done", "code": code, "stop_reason": "end_turn"})}

    return EventSourceResponse(stream())


class ExecuteRequest(BaseModel):
    csv_hash: str
    code: str


_RUNNER = textwrap.dedent(
    """
    import json, sys, pandas as pd, plotly.io as pio
    csv_path = sys.argv[1]
    df = pd.read_csv(csv_path)
    ns = {{"df": df, "pd": pd}}
    try:
        exec(compile({code!r}, "<user>", "exec"), ns)
    except Exception as e:
        print(json.dumps({{"error": f"{{type(e).__name__}}: {{e}}"}}))
        sys.exit(1)
    fig = ns.get("fig")
    if fig is None:
        print(json.dumps({{"error": "no `fig` variable was assigned"}}))
        sys.exit(1)
    print(pio.to_json(fig))
    """
).strip()


@app.post("/api/execute")
async def execute(req: ExecuteRequest) -> dict:
    if req.csv_hash not in _CACHE:
        return {"ok": False, "figure": None, "error": "csv not in cache", "duration_ms": 0}

    csv_bytes, _ = _CACHE[req.csv_hash]
    started = asyncio.get_event_loop().time()

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "data.csv"
        csv_path.write_bytes(csv_bytes)
        runner_src = _RUNNER.format(code=req.code)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-I", "-c", runner_src, str(csv_path),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=tmp,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {"ok": False, "figure": None, "error": "timeout", "duration_ms": 10000}

    duration_ms = int((asyncio.get_event_loop().time() - started) * 1000)
    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        try:
            err_obj = json.loads(out)
            return {"ok": False, "figure": None, "error": err_obj.get("error", err or "unknown"), "duration_ms": duration_ms}
        except json.JSONDecodeError:
            return {"ok": False, "figure": None, "error": err or "non-zero exit", "duration_ms": duration_ms}

    try:
        figure = json.loads(out)
    except json.JSONDecodeError as exc:
        return {"ok": False, "figure": None, "error": f"bad figure JSON: {exc}", "duration_ms": duration_ms}

    return {"ok": True, "figure": figure, "error": None, "duration_ms": duration_ms}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
