import pytest

from app.services.executor import run_user_code


@pytest.mark.asyncio
async def test_executor_returns_figure_for_valid_code():
    code = "import plotly.express as px\nfig = px.bar(df, x='a', y='b')"
    csv = b"a,b\n1,10\n2,20\n3,30\n"
    result = await run_user_code(code, csv)
    assert result.ok
    assert result.figure is not None
    assert result.figure["data"][0]["type"] == "bar"


@pytest.mark.asyncio
async def test_executor_surfaces_missing_fig():
    code = "x = 1  # forgot to assign fig"
    csv = b"a,b\n1,10\n"
    result = await run_user_code(code, csv)
    assert not result.ok
    assert "fig" in (result.error or "")


@pytest.mark.asyncio
async def test_executor_blocks_runaway_loop():
    # Trips RLIMIT_CPU before the wall-clock timeout
    code = "while True: pass\nfig = None"
    csv = b"a,b\n1,10\n"
    result = await run_user_code(code, csv)
    assert not result.ok
