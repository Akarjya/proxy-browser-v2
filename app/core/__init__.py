"""
Core module for Proxy Browser V2
"""

from .app import create_app, app
from .websocket_manager import WebSocketManager

__all__ = [
    'create_app',
    'app',
    'WebSocketManager'
]
