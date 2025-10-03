"""
Web server module.

This module provides the FastAPI web server, REST API, and WebSocket real-time communication.
"""

from .server import app, create_app
from .websocket import WebSocketManager, MessageType, QueryProgress, ConnectionState
from .websocket_routes import create_websocket_routes

__all__ = [
    "app",
    "create_app",
    "WebSocketManager",
    "MessageType",
    "QueryProgress",
    "ConnectionState",
    "create_websocket_routes",
]
