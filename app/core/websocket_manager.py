"""
WebSocket Manager
Handles WebSocket connections, message routing, and heartbeat management
"""

from typing import Dict, List, Optional, Set
from fastapi import WebSocket
import asyncio
import json
from datetime import datetime, timedelta
from loguru import logger
import uuid


class WebSocketConnection:
    """Represents a single WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.is_active = True
        self.device_info = {}
        self.message_queue = asyncio.Queue(maxsize=100)
        
    async def send_json(self, data: dict):
        """Send JSON data to client"""
        try:
            await self.websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending to {self.session_id}: {str(e)}")
            self.is_active = False
            return False
    
    async def send_text(self, text: str):
        """Send text data to client"""
        try:
            await self.websocket.send_text(text)
            return True
        except Exception as e:
            logger.error(f"Error sending text to {self.session_id}: {str(e)}")
            self.is_active = False
            return False


class WebSocketManager:
    """Manages all WebSocket connections"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.rooms: Dict[str, Set[str]] = {}  # For grouping connections
        self.heartbeat_interval = 60  # seconds
        self.ping_timeout = 120  # seconds
        
    async def connect(self, websocket: WebSocket, session_id: str) -> WebSocketConnection:
        """Add new WebSocket connection"""
        connection = WebSocketConnection(websocket, session_id)
        self.connections[session_id] = connection
        
        logger.info(f"WebSocket connected: {session_id}")
        logger.info(f"Total active connections: {len(self.connections)}")
        
        # Start message processor for this connection
        asyncio.create_task(self._process_message_queue(connection))
        
        return connection
    
    async def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.connections:
            connection = self.connections[session_id]
            connection.is_active = False
            
            # Remove from all rooms
            for room_id in list(self.rooms.keys()):
                if session_id in self.rooms[room_id]:
                    self.rooms[room_id].remove(session_id)
                    if not self.rooms[room_id]:
                        del self.rooms[room_id]
            
            # Close WebSocket
            try:
                await connection.websocket.close()
            except:
                pass
            
            del self.connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
            logger.info(f"Total active connections: {len(self.connections)}")
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections"""
        session_ids = list(self.connections.keys())
        for session_id in session_ids:
            await self.disconnect(session_id)
    
    async def send_to_client(self, session_id: str, data: dict) -> bool:
        """Send data to specific client"""
        if session_id in self.connections:
            connection = self.connections[session_id]
            if connection.is_active:
                return await connection.send_json(data)
        return False
    
    async def broadcast(self, data: dict, exclude: Optional[List[str]] = None):
        """Broadcast to all connected clients"""
        exclude = exclude or []
        tasks = []
        
        for session_id, connection in self.connections.items():
            if session_id not in exclude and connection.is_active:
                tasks.append(connection.send_json(data))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_room(self, room_id: str, data: dict, exclude: Optional[List[str]] = None):
        """Send data to all clients in a room"""
        exclude = exclude or []
        
        if room_id in self.rooms:
            tasks = []
            for session_id in self.rooms[room_id]:
                if session_id not in exclude and session_id in self.connections:
                    connection = self.connections[session_id]
                    if connection.is_active:
                        tasks.append(connection.send_json(data))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def join_room(self, session_id: str, room_id: str):
        """Add client to a room"""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(session_id)
        logger.debug(f"Session {session_id} joined room {room_id}")
    
    def leave_room(self, session_id: str, room_id: str):
        """Remove client from a room"""
        if room_id in self.rooms and session_id in self.rooms[room_id]:
            self.rooms[room_id].remove(session_id)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
            logger.debug(f"Session {session_id} left room {room_id}")
    
    async def heartbeat_sender(self):
        """Send periodic heartbeat to all connections"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check for inactive connections
                now = datetime.now()
                inactive_sessions = []
                
                for session_id, connection in self.connections.items():
                    if not connection.is_active:
                        inactive_sessions.append(session_id)
                        continue
                    
                    # Check ping timeout
                    if (now - connection.last_ping).total_seconds() > self.ping_timeout:
                        logger.warning(f"Session {session_id} ping timeout")
                        inactive_sessions.append(session_id)
                        continue
                    
                    # Send heartbeat
                    asyncio.create_task(connection.send_json({
                        "type": "heartbeat",
                        "timestamp": now.isoformat()
                    }))
                
                # Clean up inactive connections
                for session_id in inactive_sessions:
                    await self.disconnect(session_id)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
    
    async def _process_message_queue(self, connection: WebSocketConnection):
        """Process queued messages for a connection"""
        while connection.is_active:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(
                    connection.message_queue.get(),
                    timeout=1.0
                )
                
                if message:
                    await connection.send_json(message)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message queue error for {connection.session_id}: {str(e)}")
                break
    
    def get_active_connections(self) -> int:
        """Get count of active connections"""
        return len(self.connections)
    
    def get_connection_info(self, session_id: str) -> Optional[dict]:
        """Get information about a specific connection"""
        if session_id in self.connections:
            connection = self.connections[session_id]
            return {
                "session_id": session_id,
                "connected_at": connection.connected_at.isoformat(),
                "last_ping": connection.last_ping.isoformat(),
                "is_active": connection.is_active,
                "device_info": connection.device_info
            }
        return None
    
    def get_all_connections(self) -> List[dict]:
        """Get information about all connections"""
        return [
            self.get_connection_info(session_id)
            for session_id in self.connections.keys()
        ]
    
    async def handle_ping(self, session_id: str):
        """Handle ping from client"""
        if session_id in self.connections:
            self.connections[session_id].last_ping = datetime.now()
            await self.send_to_client(session_id, {"type": "pong"})
    
    async def queue_message(self, session_id: str, message: dict) -> bool:
        """Queue message for delayed sending"""
        if session_id in self.connections:
            connection = self.connections[session_id]
            try:
                await connection.message_queue.put(message)
                return True
            except asyncio.QueueFull:
                logger.warning(f"Message queue full for {session_id}")
                return False
        return False
    
    def update_device_info(self, session_id: str, device_info: dict):
        """Update device information for a connection"""
        if session_id in self.connections:
            self.connections[session_id].device_info = device_info
            logger.info(f"Updated device info for {session_id}: {device_info}")
