"""Tool registry for MCP server."""

from __future__ import annotations

from typing import Any, Protocol

from mcp.types import TextContent, Tool

from . import example, user_stats


class ToolProvider(Protocol):
    async def list_tools(self) -> list[Tool]:  # pragma: no cover - Protocol definition
        ...

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:  # pragma: no cover - Protocol definition
        ...


_TOOL_MODULES: list[ToolProvider] = [example, user_stats]


async def list_tools() -> list[Tool]:
    """Aggregate tool metadata from all registered modules."""
    tools: list[Tool] = []
    for module in _TOOL_MODULES:
        tools.extend(await module.list_tools())
    return tools


async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool execution to the module that owns the tool name."""
    last_error: ValueError | None = None

    for module in _TOOL_MODULES:
        try:
            return await module.call_tool(name, arguments)
        except ValueError as exc:
            last_error = exc
            continue

    raise ValueError(f"Unknown tool: {name}") from last_error


__all__ = ["call_tool", "list_tools"]
