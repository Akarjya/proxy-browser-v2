"""
Session Manager
Manages user sessions with device info, cookies, and state persistence
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from loguru import logger
import hashlib
import pickle
try:
    import redis.asyncio as aioredis
except ImportError:
    import aioredis
from cryptography.fernet import Fernet


@dataclass
class DeviceInfo:
    """Device information from client"""
    
    user_agent: str
    platform: str
    screen_width: int
    screen_height: int
    pixel_ratio: float
    touch_support: bool
    device_memory: Optional[int] = None
    hardware_concurrency: Optional[int] = None
    language: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    timezone_offset: Optional[int] = None
    connection_type: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DeviceInfo':
        return cls(**data)


@dataclass
class Session:
    """User session with all associated data"""
    
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    device_info: Optional[DeviceInfo] = None
    proxy_country: Optional[str] = None
    proxy_city: Optional[str] = None
    real_ip: Optional[str] = None
    proxy_ip: Optional[str] = None
    cookies: Dict[str, Any] = field(default_factory=dict)
    local_storage: Dict[str, Any] = field(default_factory=dict)
    session_storage: Dict[str, Any] = field(default_factory=dict)
    history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def add_to_history(self, url: str):
        """Add URL to browsing history"""
        self.history.append(url)
        # Keep only last 100 URLs
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        if self.device_info:
            data['device_info'] = self.device_info.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        if data.get('device_info'):
            data['device_info'] = DeviceInfo.from_dict(data['device_info'])
        return cls(**data)


class SessionManager:
    """Manages all user sessions"""
    
    def __init__(self, settings):
        self.settings = settings
        self.sessions: Dict[str, Session] = {}
        self.redis_client: Optional[aioredis.Redis] = None
        self.session_timeout = 3600  # 1 hour
        self.cleanup_interval = 300  # 5 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Generate encryption key for session data
        self.cipher_suite = Fernet(Fernet.generate_key())
        
        # Session limits
        self.max_sessions = 10000
        self.max_session_size = 1024 * 100  # 100KB per session
    
    async def initialize(self):
        """Initialize session manager"""
        
        # Connect to Redis if configured
        if self.settings.redis_url:
            try:
                if hasattr(aioredis, 'from_url'):
                    self.redis_client = await aioredis.from_url(
                        self.settings.redis_url,
                        encoding="utf-8",
                        decode_responses=True
                    )
                else:
                    # Older aioredis version
                    self.redis_client = await aioredis.create_redis_pool(
                        self.settings.redis_url,
                        encoding="utf-8"
                    )
                await self.redis_client.ping()
                logger.info("Connected to Redis for session storage")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {str(e)}")
                logger.info("Using in-memory session storage")
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Session manager initialized")
    
    async def create_session(
        self,
        session_id: Optional[str] = None,
        real_ip: Optional[str] = None
    ) -> Session:
        """Create a new session"""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = Session(
            id=session_id,
            real_ip=real_ip,
            proxy_country=self.settings.proxy_country,
            proxy_city=self.settings.proxy_city
        )
        
        async with self._lock:
            # Check session limit
            if len(self.sessions) >= self.max_sessions:
                # Remove oldest inactive session
                await self._remove_oldest_inactive()
            
            self.sessions[session_id] = session
            
            # Store in Redis if available
            if self.redis_client:
                await self._store_in_redis(session)
        
        logger.info(f"Created new session: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        
        # Check memory first
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.update_activity()
            return session
        
        # Check Redis
        if self.redis_client:
            session = await self._load_from_redis(session_id)
            if session:
                self.sessions[session_id] = session
                session.update_activity()
                return session
        
        return None
    
    async def update_session(self, session_id: str, **kwargs):
        """Update session attributes"""
        
        session = await self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            session.update_activity()
            
            # Update in Redis
            if self.redis_client:
                await self._store_in_redis(session)
    
    async def update_device_info(self, session_id: str, device_info: dict):
        """Update device information for session"""
        
        session = await self.get_session(session_id)
        if session:
            session.device_info = DeviceInfo(
                user_agent=device_info.get('userAgent', ''),
                platform=device_info.get('platform', ''),
                screen_width=device_info.get('screenWidth', 0),
                screen_height=device_info.get('screenHeight', 0),
                pixel_ratio=device_info.get('pixelRatio', 1.0),
                touch_support=device_info.get('touchSupport', False),
                device_memory=device_info.get('deviceMemory'),
                hardware_concurrency=device_info.get('hardwareConcurrency'),
                language=device_info.get('language'),
                languages=device_info.get('languages', []),
                timezone_offset=device_info.get('timezoneOffset'),
                connection_type=device_info.get('connectionType')
            )
            
            session.update_activity()
            
            # Determine if mobile based on user agent
            ua_lower = session.device_info.user_agent.lower()
            is_mobile = any(
                keyword in ua_lower 
                for keyword in ['mobile', 'android', 'iphone', 'ipad']
            )
            
            session.metadata['is_mobile'] = is_mobile
            
            # Update in Redis
            if self.redis_client:
                await self._store_in_redis(session)
            
            logger.info(f"Updated device info for session {session_id}")
    
    async def update_cookies(self, session_id: str, cookies: dict):
        """Update cookies for session"""
        
        session = await self.get_session(session_id)
        if session:
            session.cookies.update(cookies)
            session.update_activity()
            
            # Update in Redis
            if self.redis_client:
                await self._store_in_redis(session)
    
    async def update_storage(
        self,
        session_id: str,
        storage_type: str,
        data: dict
    ):
        """Update local/session storage for session"""
        
        session = await self.get_session(session_id)
        if session:
            if storage_type == "local":
                session.local_storage.update(data)
            elif storage_type == "session":
                session.session_storage.update(data)
            
            session.update_activity()
            
            # Update in Redis
            if self.redis_client:
                await self._store_in_redis(session)
    
    async def add_to_history(self, session_id: str, url: str):
        """Add URL to session history"""
        
        session = await self.get_session(session_id)
        if session:
            session.add_to_history(url)
            session.update_activity()
            
            # Update in Redis
            if self.redis_client:
                await self._store_in_redis(session)
    
    async def end_session(self, session_id: str):
        """End a session"""
        
        async with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.is_active = False
                
                # Remove from Redis
                if self.redis_client:
                    try:
                        await self.redis_client.delete(f"session:{session_id}")
                    except Exception as e:
                        logger.warning(f"Redis delete failed for session {session_id}: {e}")
                
                # Remove from memory
                del self.sessions[session_id]
                
                logger.info(f"Ended session: {session_id}")
    
    async def _store_in_redis(self, session: Session):
        """Store session in Redis"""
        
        if not self.redis_client:
            return
        
        try:
            # Serialize session
            session_data = json.dumps(session.to_dict())
            
            # Check size
            if len(session_data) > self.max_session_size:
                logger.warning(f"Session {session.id} exceeds size limit")
                # Trim history if needed
                session.history = session.history[-50:]
                session_data = json.dumps(session.to_dict())
            
            # Encrypt if sensitive
            encrypted = self.cipher_suite.encrypt(session_data.encode())
            
            # Store with expiration
            await self.redis_client.setex(
                f"session:{session.id}",
                self.session_timeout,
                encrypted.decode()
            )
        except Exception as e:
            logger.error(f"Failed to store session in Redis: {str(e)}")
    
    async def _load_from_redis(self, session_id: str) -> Optional[Session]:
        """Load session from Redis"""
        
        if not self.redis_client:
            return None
        
        try:
            # Get from Redis
            encrypted = await self.redis_client.get(f"session:{session_id}")
            if not encrypted:
                return None
            
            # Decrypt
            decrypted = self.cipher_suite.decrypt(encrypted.encode())
            
            # Deserialize
            session_data = json.loads(decrypted.decode())
            session = Session.from_dict(session_data)
            
            return session
        except Exception as e:
            logger.error(f"Failed to load session from Redis: {str(e)}")
            return None
    
    async def _cleanup_loop(self):
        """Periodically clean up expired sessions"""
        
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Cleanup loop error: {str(e)}")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        
        now = datetime.now()
        expired_sessions = []
        
        async with self._lock:
            for session_id, session in self.sessions.items():
                if not session.is_active:
                    expired_sessions.append(session_id)
                elif (now - session.last_activity).total_seconds() > self.session_timeout:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                # Remove from Redis
                if self.redis_client:
                    try:
                        await self.redis_client.delete(f"session:{session_id}")
                    except Exception as e:
                        logger.warning(f"Redis delete failed for session {session_id}: {e}")
                
                # Remove from memory
                del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    async def _remove_oldest_inactive(self):
        """Remove oldest inactive session"""
        
        if not self.sessions:
            return
        
        # Find oldest inactive session
        oldest_session = None
        oldest_time = datetime.now()
        
        for session in self.sessions.values():
            if not session.is_active and session.last_activity < oldest_time:
                oldest_session = session
                oldest_time = session.last_activity
        
        if oldest_session:
            await self.end_session(oldest_session.id)
    
    async def cleanup(self):
        """Clean up session manager"""
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Session manager cleaned up")
    
    def get_active_sessions(self) -> int:
        """Get count of active sessions"""
        return sum(1 for s in self.sessions.values() if s.is_active)
    
    def get_total_sessions(self) -> int:
        """Get total session count"""
        return len(self.sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        
        mobile_count = sum(
            1 for s in self.sessions.values()
            if s.metadata.get('is_mobile', False)
        )
        
        desktop_count = len(self.sessions) - mobile_count
        
        countries = {}
        for session in self.sessions.values():
            country = session.proxy_country or 'Unknown'
            countries[country] = countries.get(country, 0) + 1
        
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": self.get_active_sessions(),
            "mobile_sessions": mobile_count,
            "desktop_sessions": desktop_count,
            "countries": countries,
            "redis_connected": self.redis_client is not None
        }
    
    async def export_session(self, session_id: str) -> Optional[dict]:
        """Export session data"""
        
        session = await self.get_session(session_id)
        if session:
            return session.to_dict()
        return None
    
    async def import_session(self, session_data: dict) -> Session:
        """Import session data"""
        
        session = Session.from_dict(session_data)
        
        async with self._lock:
            self.sessions[session.id] = session
            
            # Store in Redis
            if self.redis_client:
                await self._store_in_redis(session)
        
        return session
    
    async def get_session_history(self, session_id: str) -> List[str]:
        """Get browsing history for session"""
        
        session = await self.get_session(session_id)
        if session:
            return session.history
        return []
    
    async def clear_session_data(self, session_id: str):
        """Clear session data (cookies, storage, history)"""
        
        session = await self.get_session(session_id)
        if session:
            session.cookies.clear()
            session.local_storage.clear()
            session.session_storage.clear()
            session.history.clear()
            session.update_activity()
            
            # Update in Redis
            if self.redis_client:
                await self._store_in_redis(session)
            
            logger.info(f"Cleared data for session {session_id}")
