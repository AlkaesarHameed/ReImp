"""
WebSocket module for real-time document processing updates.

Source: Design Document 07-document-extraction-system-design.md Section 4.4
Verified: 2025-12-20
"""

from src.api.websocket.manager import (
    WebSocketManager,
    get_websocket_manager,
    DocumentProgressMessage,
    ConnectionState,
)

__all__ = [
    "WebSocketManager",
    "get_websocket_manager",
    "DocumentProgressMessage",
    "ConnectionState",
]
