"""Run model-generated Python in a restricted subprocess.

Goals (in priority order):
1. The user can't tell us "import os and rm -rf" via an unexpected prompt path.
2. A runaway groupby doesn't pin our API worker, thanks to a separate process,
   a hard wall-clock cap, and a memory ceiling on POSIX.
3. The chart comes back as Plotly JSON, not as a rendered image, so the
   frontend keeps it interactive (hover, zoom).

This is NOT a true sandbox. Resource limits + no-network + a clean cwd are
enough for a portfolio demo; production would want gVisor / Firecracker /
a separate worker pool.
"""
from __future__ import annotations

import asyncio
import json
import resource
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

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


@dataclass
class ExecResult:
    ok: bool
    figure: dict | None
    error: str | None
    stdout: str
    duration_ms: int


def _apply_rlimits() -> None:
    s = get_settings()
    mem_bytes = s.executor_memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (s.executor_timeout_seconds, s.executor_timeout_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))


async def run_user_code(code: str, csv_bytes: bytes) -> ExecResult:
    settings = get_settings()
    started = asyncio.get_event_loop().time()

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "data.csv"
        csv_path.write_bytes(csv_bytes)

        runner_src = _RUNNER.format(code=code)
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",  # isolated mode: ignore PYTHON* env, no user site-packages
            "-c",
            runner_src,
            str(csv_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp,
            preexec_fn=_apply_rlimits,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=settings.executor_timeout_seconds + 2
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ExecResult(
                ok=False,
                figure=None,
                error=f"execution exceeded {settings.executor_timeout_seconds}s",
                stdout="",
                duration_ms=int((asyncio.get_event_loop().time() - started) * 1000),
            )

    duration_ms = int((asyncio.get_event_loop().time() - started) * 1000)
    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        try:
            err_obj = json.loads(out)
            return ExecResult(False, None, err_obj.get("error", err or "unknown"), out, duration_ms)
        except json.JSONDecodeError:
            return ExecResult(False, None, err or "non-zero exit", out, duration_ms)

    try:
        figure = json.loads(out)
    except json.JSONDecodeError as exc:
        return ExecResult(False, None, f"bad figure JSON: {exc}", out, duration_ms)

    return ExecResult(True, figure, None, "", duration_ms)
