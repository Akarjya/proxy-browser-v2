"""
Application Configuration Module
Handles all configuration settings for the Proxy Browser V2
"""

from pydantic_settings import BaseSettings
from typing import Optional, List, Dict
import os
from functools import lru_cache
from loguru import logger


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application Settings
    app_name: str = "Proxy Browser V2"
    app_version: str = "2.0.0"
    debug: bool = False
    secret_key: str = "change-this-secret-key-in-production"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    
    # Proxy Configuration
    proxy_provider: str = "proxi.es"
    proxy_username: str = ""
    proxy_password: str = ""
    proxy_server: str = "pg.proxi.es:20002"  # Default SOCKS5 port
    proxy_type: str = "socks5"  # "http", "socks5", "socks4"
    
    # Proxidise port mapping
    proxy_ports: Dict[str, int] = {
        "http": 20000,
        "socks5": 20002,
        "socks4": 20001  # If supported
    }
    proxy_country: str = "USA"
    proxy_state: Optional[str] = "NY"
    proxy_city: Optional[str] = "NewYorkCity"
    proxy_rotation_type: str = "sticky"  # "sticky" or "rotating"
    proxy_session_duration: int = 600  # 10 minutes in seconds
    
    # Proxidise specific sticky session IDs (examples)
    proxy_sticky_sessions: List[str] = [
        "Ecnik5GaH8", "sIIpXRcoJm", "PKzbgWiczO", "rigPetKxvi", "dfYwJRS5J6",
        "0Q3PIsLv3B", "E6QemYEknm", "I0NDGemp3n", "hTljfkAsu0", "UXTxtJog62"
    ]
    
    # Database Configuration (for session management)
    database_url: Optional[str] = "sqlite+aiosqlite:///./proxy_browser.db"
    redis_url: Optional[str] = "redis://localhost:6379/0"
    
    # WebSocket Configuration
    ws_heartbeat_interval: int = 30
    ws_message_queue_size: int = 100
    ws_max_connections: int = 1000
    ws_ping_interval: int = 10
    ws_ping_timeout: int = 5
    
    # Browser Pool Settings
    browser_pool_size: int = 10
    browser_headless: bool = True
    browser_timeout: int = 30000  # milliseconds
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080
    browser_args: List[str] = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-setuid-sandbox'
    ]
    
    # Mobile Configuration
    mobile_default_ua: str = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    )
    mobile_viewport_width: int = 390
    mobile_viewport_height: int = 844
    
    # Cache Settings
    cache_ttl: int = 300  # 5 minutes
    cache_max_size: int = 1000
    enable_cache: bool = True
    cache_strategy: str = "lru"  # "lru", "lfu", "ttl"
    
    # Security Settings
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]
    allowed_hosts: List[str] = ["*"]
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    rate_limit_burst: int = 10
    
    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    
    # Monitoring (Optional)
    sentry_dsn: Optional[str] = None
    enable_metrics: bool = False
    metrics_port: int = 9090
    
    # Target Site Configuration
    default_target_url: str = "https://ybsq.xyz/"
    allowed_domains: List[str] = ["*"]
    blocked_domains: List[str] = []
    
    # Geographic Spoofing Configuration
    spoof_timezone: str = "America/New_York"
    spoof_language: str = "en-US"
    spoof_currency: str = "USD"
    spoof_locale: str = "en_US"
    spoof_country_code: str = "US"
    spoof_region: str = "NY"
    
    # Geolocation Coordinates (New York)
    spoof_latitude: float = 40.7128
    spoof_longitude: float = -74.0060
    spoof_accuracy: int = 100
    
    # Performance Settings
    enable_compression: bool = True
    min_compression_size: int = 1024  # bytes
    parallel_requests: int = 5
    request_timeout: int = 30  # seconds
    connection_pool_size: int = 100
    
    # Content Rewriting
    rewrite_urls: bool = True
    rewrite_javascript: bool = True
    rewrite_css: bool = True
    inject_scripts: bool = True
    preserve_original_headers: List[str] = ["User-Agent", "Accept", "Accept-Encoding"]
    
    # Development Settings
    hot_reload: bool = False
    mock_mode: bool = False  # For testing without actual proxy
    verbose_logging: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow extra fields for flexibility
        extra = "allow"


class ProxyConfig:
    """Proxy-specific configuration"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._session_sticky_map = {}  # Map session IDs to sticky IDs
        self._sticky_index = 0
        
    def get_proxy_url(self, session_id: Optional[str] = None) -> str:
        """Generate proxy URL with authentication"""
        username = self.settings.proxy_username
        
        # Get the correct server address with port
        proxy_server = self.settings.proxy_server
        
        # For Proxidise, use correct port based on protocol
        if self.settings.proxy_provider == "proxidise" and self.settings.proxy_type in self.settings.proxy_ports:
            # Extract host and replace with correct port
            host = proxy_server.split(':')[0]
            port = self.settings.proxy_ports[self.settings.proxy_type]
            proxy_server = f"{host}:{port}"
            logger.debug(f"Using Proxidise {self.settings.proxy_type} port: {port}")
        
        # Handle Proxidise specific format
        if self.settings.proxy_provider == "proxidise":
            # Get or assign sticky session ID
            if session_id and self.settings.proxy_rotation_type == "sticky":
                if session_id not in self._session_sticky_map:
                    # Assign a sticky session ID from the pool
                    sticky_id = self.settings.proxy_sticky_sessions[
                        self._sticky_index % len(self.settings.proxy_sticky_sessions)
                    ]
                    self._session_sticky_map[session_id] = sticky_id
                    self._sticky_index += 1
                    logger.info(f"Assigned sticky session {sticky_id} to user session {session_id}")
                
                sticky_id = self._session_sticky_map[session_id]
                
                # Build Proxidise format: username-s-stickyID-co-country-st-state-ci-city
                parts = [username]
                parts.append(f"s-{sticky_id}")
                if self.settings.proxy_country:
                    parts.append(f"co-{self.settings.proxy_country}")
                if self.settings.proxy_state:
                    parts.append(f"st-{self.settings.proxy_state}")
                if self.settings.proxy_city:
                    parts.append(f"ci-{self.settings.proxy_city}")
                
                username = "-".join(parts)
            else:
                # Non-sticky or no session ID
                parts = [username]
                if self.settings.proxy_country:
                    parts.append(f"co-{self.settings.proxy_country}")
                if self.settings.proxy_state:
                    parts.append(f"st-{self.settings.proxy_state}")
                if self.settings.proxy_city:
                    parts.append(f"ci-{self.settings.proxy_city}")
                
                username = "-".join(parts)
        else:
            # Generic proxy format
            if session_id and self.settings.proxy_rotation_type == "sticky":
                username = f"{username}-session-{session_id}"
                
            # Add country/city targeting
            if self.settings.proxy_country:
                username = f"{username}-country-{self.settings.proxy_country}"
            if self.settings.proxy_city:
                username = f"{username}-city-{self.settings.proxy_city}"
            
        # Return appropriate proxy URL based on type
        if self.settings.proxy_type.lower() == "socks5":
            return f"socks5://{username}:{self.settings.proxy_password}@{proxy_server}"
        elif self.settings.proxy_type.lower() == "socks4":
            return f"socks4://{username}:{self.settings.proxy_password}@{proxy_server}"
        else:  # Default to HTTP
            return f"http://{username}:{self.settings.proxy_password}@{proxy_server}"
    
    def get_proxy_dict(self, session_id: Optional[str] = None) -> dict:
        """Get proxy configuration dictionary"""
        proxy_url = self.get_proxy_url(session_id)
        
        if self.settings.proxy_type.lower() in ["socks5", "socks4"]:
            return {
                "http": proxy_url,
                "https": proxy_url
            }
        else:
            return {
                "http": proxy_url,
                "https": proxy_url
            }


class BrowserConfig:
    """Browser-specific configuration"""
    
    def __init__(self, settings: Settings, is_mobile: bool = False):
        self.settings = settings
        self.is_mobile = is_mobile
        
    def get_viewport(self) -> dict:
        """Get viewport configuration"""
        if self.is_mobile:
            return {
                "width": self.settings.mobile_viewport_width,
                "height": self.settings.mobile_viewport_height
            }
        return {
            "width": self.settings.browser_viewport_width,
            "height": self.settings.browser_viewport_height
        }
    
    def get_user_agent(self) -> str:
        """Get user agent string"""
        if self.is_mobile:
            return self.settings.mobile_default_ua
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    
    def get_launch_args(self) -> List[str]:
        """Get browser launch arguments"""
        args = self.settings.browser_args.copy()
        
        if self.settings.proxy_server:
            # Add proxy-specific args if needed
            args.append('--ignore-certificate-errors')
            
        return args


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export for easy access
settings = get_settings()
