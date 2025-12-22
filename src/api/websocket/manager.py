"""
WebSocket Manager for Document Processing Progress.

Provides real-time progress updates for document processing,
replacing polling-based status checks with push notifications.

Source: Design Document 07-document-extraction-system-design.md
FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
Verified: 2025-12-20
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """WebSocket connection states."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MessageType(str, Enum):
    """WebSocket message types."""

    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class DocumentProgressMessage:
    """Progress update message for document processing."""

    type: MessageType
    document_id: str
    stage: str
    progress_percent: int = 0
    message: str = ""
    ocr_confidence: Optional[float] = None
    parsing_confidence: Optional[float] = None
    needs_review: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "document_id": self.document_id,
            "stage": self.stage,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "ocr_confidence": self.ocr_confidence,
            "parsing_confidence": self.parsing_confidence,
            "needs_review": self.needs_review,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection."""

    websocket: WebSocket
    document_id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: Optional[datetime] = None
    state: ConnectionState = ConnectionState.CONNECTING


class WebSocketManager:
    """
    Manages WebSocket connections for document processing progress.

    Features:
    - Per-document connection tracking
    - Broadcast progress updates to connected clients
    - Automatic cleanup of disconnected clients
    - Ping/pong for connection health checks

    Usage:
        manager = WebSocketManager()

        # In WebSocket endpoint
        await manager.connect(websocket, document_id)
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming messages
        except WebSocketDisconnect:
            manager.disconnect(document_id, websocket)

        # From document processor
        await manager.broadcast_progress(document_id, progress_message)
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        # Map of document_id -> list of connections
        self._connections: dict[str, list[WebSocketConnection]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        # Ping interval in seconds
        self._ping_interval = 30
        # Connection timeout in seconds
        self._connection_timeout = 120

    @property
    def active_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def tracked_documents(self) -> int:
        """Get number of documents being tracked."""
        return len(self._connections)

    async def connect(
        self,
        websocket: WebSocket,
        document_id: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> WebSocketConnection:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            document_id: Document being tracked
            tenant_id: Optional tenant ID for isolation
            user_id: Optional user ID for authorization

        Returns:
            WebSocketConnection instance
        """
        await websocket.accept()

        connection = WebSocketConnection(
            websocket=websocket,
            document_id=document_id,
            tenant_id=tenant_id,
            user_id=user_id,
            state=ConnectionState.CONNECTED,
        )

        async with self._lock:
            if document_id not in self._connections:
                self._connections[document_id] = []
            self._connections[document_id].append(connection)

        logger.info(
            f"WebSocket connected: document={document_id}, "
            f"total_connections={self.active_connections}"
        )

        # Send initial connection acknowledgment
        await self._send_message(
            websocket,
            DocumentProgressMessage(
                type=MessageType.PROGRESS,
                document_id=document_id,
                stage="connected",
                progress_percent=0,
                message="Connected to progress updates",
            ),
        )

        return connection

    async def disconnect(
        self,
        document_id: str,
        websocket: WebSocket,
    ) -> None:
        """
        Remove a WebSocket connection.

        Args:
            document_id: Document being tracked
            websocket: WebSocket to remove
        """
        async with self._lock:
            if document_id in self._connections:
                self._connections[document_id] = [
                    conn for conn in self._connections[document_id]
                    if conn.websocket != websocket
                ]
                # Clean up empty document entries
                if not self._connections[document_id]:
                    del self._connections[document_id]

        logger.info(
            f"WebSocket disconnected: document={document_id}, "
            f"total_connections={self.active_connections}"
        )

    async def broadcast_progress(
        self,
        document_id: str,
        message: DocumentProgressMessage,
    ) -> int:
        """
        Broadcast a progress update to all connections for a document.

        Args:
            document_id: Document ID
            message: Progress message to send

        Returns:
            Number of clients that received the message
        """
        connections = self._connections.get(document_id, [])
        if not connections:
            return 0

        sent_count = 0
        failed_connections = []

        for connection in connections:
            try:
                await self._send_message(connection.websocket, message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                failed_connections.append(connection.websocket)

        # Clean up failed connections
        for ws in failed_connections:
            await self.disconnect(document_id, ws)

        return sent_count

    async def send_progress(
        self,
        document_id: str,
        stage: str,
        progress_percent: int,
        message: str = "",
        ocr_confidence: Optional[float] = None,
        parsing_confidence: Optional[float] = None,
    ) -> int:
        """
        Convenience method to send a progress update.

        Args:
            document_id: Document ID
            stage: Current processing stage
            progress_percent: Progress percentage (0-100)
            message: Human-readable status message
            ocr_confidence: OCR confidence if available
            parsing_confidence: Parsing confidence if available

        Returns:
            Number of clients notified
        """
        return await self.broadcast_progress(
            document_id,
            DocumentProgressMessage(
                type=MessageType.PROGRESS,
                document_id=document_id,
                stage=stage,
                progress_percent=progress_percent,
                message=message,
                ocr_confidence=ocr_confidence,
                parsing_confidence=parsing_confidence,
            ),
        )

    async def send_complete(
        self,
        document_id: str,
        ocr_confidence: float,
        parsing_confidence: float,
        needs_review: bool = False,
    ) -> int:
        """
        Send completion notification.

        Args:
            document_id: Document ID
            ocr_confidence: Final OCR confidence
            parsing_confidence: Final parsing confidence
            needs_review: Whether manual review is needed

        Returns:
            Number of clients notified
        """
        return await self.broadcast_progress(
            document_id,
            DocumentProgressMessage(
                type=MessageType.COMPLETE,
                document_id=document_id,
                stage="complete",
                progress_percent=100,
                message="Processing complete",
                ocr_confidence=ocr_confidence,
                parsing_confidence=parsing_confidence,
                needs_review=needs_review,
            ),
        )

    async def send_error(
        self,
        document_id: str,
        error: str,
        stage: str = "unknown",
    ) -> int:
        """
        Send error notification.

        Args:
            document_id: Document ID
            error: Error message
            stage: Stage where error occurred

        Returns:
            Number of clients notified
        """
        return await self.broadcast_progress(
            document_id,
            DocumentProgressMessage(
                type=MessageType.ERROR,
                document_id=document_id,
                stage=stage,
                progress_percent=0,
                message="Processing failed",
                error=error,
            ),
        )

    async def _send_message(
        self,
        websocket: WebSocket,
        message: DocumentProgressMessage,
    ) -> None:
        """Send a message to a WebSocket."""
        await websocket.send_text(message.to_json())

    async def handle_client_message(
        self,
        websocket: WebSocket,
        document_id: str,
        data: str,
    ) -> None:
        """
        Handle incoming message from client.

        Currently supports:
        - ping: Respond with pong for keepalive

        Args:
            websocket: Client WebSocket
            document_id: Document being tracked
            data: Raw message data
        """
        try:
            message = json.loads(data)
            msg_type = message.get("type", "").lower()

            if msg_type == "ping":
                # Update last ping time
                async with self._lock:
                    for conn in self._connections.get(document_id, []):
                        if conn.websocket == websocket:
                            conn.last_ping = datetime.now(timezone.utc)
                            break

                # Send pong
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }))

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {data[:100]}")
        except Exception as e:
            logger.warning(f"Error handling client message: {e}")

    def get_connection_info(self, document_id: str) -> dict[str, Any]:
        """
        Get information about connections for a document.

        Args:
            document_id: Document ID

        Returns:
            Connection statistics
        """
        connections = self._connections.get(document_id, [])
        return {
            "document_id": document_id,
            "connection_count": len(connections),
            "connections": [
                {
                    "connected_at": conn.connected_at.isoformat(),
                    "tenant_id": conn.tenant_id,
                    "user_id": conn.user_id,
                    "state": conn.state.value,
                }
                for conn in connections
            ],
        }

    async def cleanup_stale_connections(self) -> int:
        """
        Remove connections that have timed out.

        Returns:
            Number of connections removed
        """
        removed = 0
        cutoff = datetime.now(timezone.utc)

        async with self._lock:
            for document_id in list(self._connections.keys()):
                stale = []
                for conn in self._connections[document_id]:
                    # Check if connection is stale
                    age = (cutoff - conn.connected_at).total_seconds()
                    if age > self._connection_timeout:
                        if conn.last_ping:
                            ping_age = (cutoff - conn.last_ping).total_seconds()
                            if ping_age > self._ping_interval * 2:
                                stale.append(conn)
                        else:
                            stale.append(conn)

                for conn in stale:
                    try:
                        await conn.websocket.close()
                    except Exception:
                        pass
                    self._connections[document_id].remove(conn)
                    removed += 1

                # Clean up empty entries
                if not self._connections[document_id]:
                    del self._connections[document_id]

        if removed > 0:
            logger.info(f"Cleaned up {removed} stale WebSocket connections")

        return removed


# =============================================================================
# Singleton Instance
# =============================================================================

_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get the global WebSocket manager instance.

    Returns:
        WebSocketManager singleton
    """
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
