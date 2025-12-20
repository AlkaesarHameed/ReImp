"""
Example MCP Tool
Demonstrates how to create MCP tools callable by LLMs
Source: https://modelcontextprotocol.io/docs/concepts/tools
Verified: 2025-11-14
"""

from typing import Any

from mcp.types import TextContent, Tool
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Tool definition
# Evidence: MCP tool schema
# Source: https://spec.modelcontextprotocol.io/specification/2025-03-26/server/tools/
# Verified: 2025-11-14
EXAMPLE_TOOL = Tool(
    name="echo",
    description="Echo back the input text. Useful for testing MCP connectivity.",
    inputSchema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to echo back",
            },
        },
        "required": ["message"],
    },
)


async def list_tools() -> list[Tool]:
    """
    List available tools.

    Returns:
        List of tool definitions
    """
    return [EXAMPLE_TOOL]


async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Execute a tool.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result as TextContent

    Evidence: Tool execution pattern
    Source: https://spec.modelcontextprotocol.io/specification/2025-03-26/server/tools/#calling-tools
    Verified: 2025-11-14
    """
    if name == "echo":
        message = arguments.get("message", "")
        logger.info(f"Echo tool called with message: {message}")

        return [
            TextContent(
                type="text",
                text=f"Echo: {message}",
            )
        ]

    raise ValueError(f"Unknown tool: {name}")
