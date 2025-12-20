"""
User Statistics MCP Tool
Example tool demonstrating database access via MCP
Source: https://modelcontextprotocol.io/docs/concepts/tools
Verified: 2025-11-14
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mcp.types import TextContent, Tool
from src.db.connection import get_session_maker
from src.models.document import Document
from src.models.user import User
from src.utils.logging import get_logger

logger = get_logger(__name__)


# Tool definition
USER_STATS_TOOL = Tool(
    name="get_user_stats",
    description="Get statistics for a user including total documents and account status",
    inputSchema={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The UUID of the user",
            },
        },
        "required": ["user_id"],
    },
)


SessionFactory = async_sessionmaker[AsyncSession]


async def get_user_stats_handler(
    user_id_str: str,
    session_factory: SessionFactory | None = None,
) -> dict[str, Any]:
    """
    Get user statistics.

    Args:
        user_id_str: User UUID as string

    Returns:
        Dictionary with user stats

    Evidence: MCP tools can access database and services
    Source: https://spec.modelcontextprotocol.io/specification/2025-03-26/server/tools/
    Verified: 2025-11-14
    """
    try:
        user_id = UUID(user_id_str)
    except ValueError as err:
        raise ValueError(f"Invalid user ID format: {user_id_str}") from err

    session_factory = session_factory or get_session_maker()

    async with session_factory() as session:
        user = await _fetch_user(session, user_id)
        doc_count = await _count_documents(session, user_id)

    stats = {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "total_documents": doc_count,
        "created_at": user.created_at.isoformat(),
    }

    logger.info(f"Retrieved stats for user: {user.username}")

    return stats


async def _fetch_user(session: AsyncSession, user_id: UUID) -> User:
    """Load a user via ORM select using the provided async session."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User not found: {user_id}")
    return user


async def _count_documents(session: AsyncSession, user_id: UUID) -> int:
    """Count the documents owned by the given user."""
    result = await session.execute(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    count = result.scalar_one()
    return int(count or 0)


async def list_tools() -> list[Tool]:
    """Expose the user stats tool to the MCP server."""
    return [USER_STATS_TOOL]


async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute the requested MCP tool."""
    if name != USER_STATS_TOOL.name:
        raise ValueError(f"Unknown tool: {name}")

    user_id_str = str(arguments.get("user_id", "")).strip()
    if not user_id_str:
        raise ValueError("user_id is required")

    stats = await get_user_stats_handler(user_id_str)
    return [TextContent(type="text", text=json.dumps(stats))]
