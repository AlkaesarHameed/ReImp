"""
MCP Server
Model Context Protocol server with integrated tools
Source: https://github.com/modelcontextprotocol/python-sdk
Verified: 2025-11-14
"""

import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from src.api.config import settings
from src.mcp.tools import call_tool, list_tools
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Initialize MCP server
# Evidence: MCP for LLM-tool integration
# Source: https://modelcontextprotocol.io/introduction
# Verified: 2025-11-14
app = Server(settings.MCP_SERVER_NAME)


# Register tool dispatcher
app.list_tools = list_tools
app.call_tool = call_tool


async def main():
    """
    Run MCP server.

    Evidence: Stdio transport for MCP
    Source: https://spec.modelcontextprotocol.io/specification/basic/transports/
    Verified: 2025-11-14
    """
    logger.info(f"Starting MCP server: {settings.MCP_SERVER_NAME}")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
