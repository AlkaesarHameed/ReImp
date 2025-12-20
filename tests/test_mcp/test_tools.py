"""Tests for MCP tool registration and user stats handler."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

# Skip all tests if mcp is not installed
try:
    from mcp.types import TextContent
except ImportError:
    pytest.skip("MCP not installed, skipping MCP tests", allow_module_level=True)

from src.mcp.tools import call_tool as aggregated_call_tool
from src.mcp.tools import list_tools as aggregated_list_tools
from src.mcp.tools import user_stats
from src.mcp.tools.example import EXAMPLE_TOOL
from src.mcp.tools.user_stats import USER_STATS_TOOL, get_user_stats_handler


@pytest.mark.asyncio
async def test_list_tools_includes_registered_modules():
    """Aggregator should surface both example and user_stats tools."""
    tools = await aggregated_list_tools()
    tool_names = {tool.name for tool in tools}

    assert EXAMPLE_TOOL.name in tool_names
    assert USER_STATS_TOOL.name in tool_names


@pytest.mark.asyncio
async def test_call_tool_delegates_to_user_stats(monkeypatch):
    """Ensure aggregated dispatcher routes calls to the correct module."""

    async def fake_user_stats_call(name: str, arguments: dict[str, str]) -> list[TextContent]:
        if name != USER_STATS_TOOL.name:
            raise ValueError("Unknown tool")
        return [TextContent(type="text", text="ok")]

    monkeypatch.setattr(user_stats, "call_tool", fake_user_stats_call)

    response = await aggregated_call_tool(USER_STATS_TOOL.name, {"user_id": str(uuid4())})

    assert response == [TextContent(type="text", text="ok")]


class _DummyResult:
    def __init__(self, *, user: SimpleNamespace | None = None, count: int | None = None):
        self._user = user
        self._count = count

    def scalar_one_or_none(self):
        return self._user

    def scalar_one(self):
        return self._count

    def scalar(self):
        return self._count


class _DummySession:
    def __init__(self, user: SimpleNamespace, doc_count: int):
        self._user = user
        self._doc_count = doc_count
        self._calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _stmt):
        self._calls += 1
        if self._calls == 1:
            return _DummyResult(user=self._user)
        if self._calls == 2:
            return _DummyResult(count=self._doc_count)
        raise AssertionError("execute called more times than expected")


class _DummySessionFactory:
    def __init__(self, session: _DummySession):
        self._session = session

    def __call__(self):
        return self._session


@pytest.mark.asyncio
async def test_get_user_stats_handler_uses_async_session_factory():
    """Handler should run queries through the provided session factory."""
    user = SimpleNamespace(
        id=uuid4(),
        username="demo",
        email="demo@example.com",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(UTC),
    )
    session = _DummySession(user=user, doc_count=3)
    factory = _DummySessionFactory(session)

    stats = await get_user_stats_handler(str(user.id), session_factory=factory)

    assert stats["user_id"] == str(user.id)
    assert stats["total_documents"] == 3
    assert stats["email"] == "demo@example.com"
