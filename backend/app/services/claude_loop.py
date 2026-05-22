"""Claude tool-use loop that turns a prompt into runnable Plotly code.

The model is given three tools:

    describe_df   : returns shape + dtypes + sample rows for the cached CSV
    suggest_chart : model commits to a chart type + columns (forces a plan
                    before code, which dramatically improves first-pass quality)
    render_chart  : model emits the final Python; we DON'T execute it here.
                    The frontend gets the code, lets the user tweak it, then
                    POSTs to /api/execute. That separation is the whole point
                    of the split-pane editor.

Each step yields a dict that the SSE endpoint streams to the client as a
"trace" event, so the UI can show the model's reasoning live.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.services.cache import get_dataframe

_SYSTEM = """\
You are Chart Studio's data viz assistant. The user has uploaded a CSV
(referenced by a content hash) and given you a natural-language request.

Workflow:
  1. Call `describe_df` to inspect the data.
  2. Call `suggest_chart` to commit to chart type + columns.
  3. Call `render_chart` with the final Python source.

The Python you emit MUST:
  - Assume `df` (a pandas DataFrame) is already in scope.
  - Assign the resulting Plotly figure to a variable named `fig`.
  - Use `plotly.express` or `plotly.graph_objects` only.
  - Not perform I/O, network access, or imports beyond pandas/plotly.

Prefer plotly.express for clarity. Keep the code short, under 25 lines.
"""

TOOLS = [
    {
        "name": "describe_df",
        "description": "Return shape, dtypes, and a 5-row sample of the cached DataFrame.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "suggest_chart",
        "description": "Commit to a chart type and the columns that will be used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": [
                    "bar", "line", "scatter", "histogram", "box", "heatmap", "pie", "area",
                ]},
                "x": {"type": "string"},
                "y": {"type": "string"},
                "color": {"type": ["string", "null"]},
                "rationale": {"type": "string"},
            },
            "required": ["chart_type", "rationale"],
        },
    },
    {
        "name": "render_chart",
        "description": "Emit the final Python source. The user will edit it before execution.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
]


async def _describe(csv_hash: str) -> dict:
    df = await get_dataframe(csv_hash)
    if df is None:
        return {"error": "no cached dataframe for this csv_hash"}
    return {
        "shape": list(df.shape),
        "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
        "sample": df.head(5).to_dict(orient="records"),
    }


async def stream_generate(prompt: str, csv_hash: str) -> AsyncIterator[dict]:
    """Drive the tool loop, yielding trace events the SSE layer forwards."""
    client = AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    messages: list[dict] = [
        {"role": "user", "content": f"CSV hash: {csv_hash}\n\nRequest: {prompt}"}
    ]
    final_code: str | None = None

    # Hard cap on iterations: prevents an obstinate model from looping forever
    # if it can't satisfy its own schema. 6 is generous; typical run is 3.
    for _ in range(6):
        response = await client.messages.create(
            model=get_settings().model,
            max_tokens=2048,
            system=_SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        assistant_blocks = response.content
        messages.append({"role": "assistant", "content": assistant_blocks})

        if response.stop_reason != "tool_use":
            yield {"type": "done", "code": final_code, "stop_reason": response.stop_reason}
            return

        tool_results = []
        for block in assistant_blocks:
            if block.type == "text" and block.text.strip():
                yield {"type": "thought", "text": block.text}
            if block.type != "tool_use":
                continue

            yield {"type": "tool_call", "name": block.name, "input": block.input}

            if block.name == "describe_df":
                result = await _describe(csv_hash)
            elif block.name == "suggest_chart":
                # Pure-acknowledge tool: returning the input lets the model see
                # its own commitment on the next turn and reference it in code.
                result = {"ack": True, **block.input}
            elif block.name == "render_chart":
                final_code = block.input.get("code", "")
                result = {"received": True, "lines": final_code.count("\n") + 1}
            else:
                result = {"error": f"unknown tool {block.name}"}

            yield {"type": "tool_result", "name": block.name, "result": result}
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})

        if final_code is not None:
            # Model committed code via render_chart; one more turn so the model
            # can wrap up with a short natural-language note, then we're done.
            yield {"type": "code", "code": final_code}

    yield {"type": "done", "code": final_code, "stop_reason": "max_iterations"}
