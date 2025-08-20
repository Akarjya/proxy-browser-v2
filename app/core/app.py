"""
Main FastAPI Application
Handles WebSocket connections and HTTP endpoints for the proxy browser
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, Optional
import uuid
from loguru import logger
import json

from config.settings import get_settings
from app.core.websocket_manager import WebSocketManager
from app.services.proxy_service import ProxyService
from app.services.simple_proxy import SimpleProxyService
from app.services.direct_proxy import DirectProxyService
# from app.services.browser_pool import BrowserPoolManager  # Disabled for Railway
from app.services.session_manager import SessionManager
from app.services.content_rewriter import ContentRewriter
from app.middleware.security import SecurityMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.api import proxy_routes, session_routes, analytics_routes, direct_proxy_routes

settings = get_settings()

# Global managers
ws_manager: Optional[WebSocketManager] = None
# browser_pool: Optional[BrowserPoolManager] = None  # Disabled for Railway
session_manager: Optional[SessionManager] = None
proxy_service: Optional[ProxyService] = None
simple_proxy: Optional[SimpleProxyService] = None
direct_proxy: Optional[DirectProxyService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ws_manager, browser_pool, session_manager, proxy_service, simple_proxy, direct_proxy
    
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize managers
    ws_manager = WebSocketManager()
    # browser_pool = BrowserPoolManager(settings)  # Disabled for Railway
    session_manager = SessionManager(settings)
    proxy_service = ProxyService(settings)
    simple_proxy = SimpleProxyService(settings)
    direct_proxy = DirectProxyService(settings)
    
    # Store in app state for access in routes
    app.state.ws_manager = ws_manager
    # app.state.browser_pool = browser_pool  # Disabled for Railway
    app.state.session_manager = session_manager
    app.state.proxy_service = proxy_service
    app.state.simple_proxy = simple_proxy
    app.state.direct_proxy = direct_proxy
    app.state.settings = settings
    
    # Initialize session manager
    await session_manager.initialize()
    
    # Start browser pool (disabled for Railway deployment)
    # await browser_pool.initialize()
    
    # Start background tasks
    asyncio.create_task(ws_manager.heartbeat_sender())
    asyncio.create_task(session_manager.cleanup_expired_sessions())
    
    logger.info("Application startup complete")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down application...")
    # await browser_pool.cleanup()  # Disabled for Railway
    await session_manager.cleanup()
    await ws_manager.disconnect_all()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    if settings.enable_compression:
        app.add_middleware(
            GZipMiddleware,
            minimum_size=settings.min_compression_size
        )
    
    app.add_middleware(SecurityMiddleware)
    
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimiterMiddleware,
            requests_per_minute=1000,  # Increased from 300 for proxy usage
            burst_size=200  # Increased from 50 for proxy usage
        )
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Include API routes
    app.include_router(proxy_routes.router, prefix="/api/proxy", tags=["proxy"])
    app.include_router(session_routes.router, prefix="/api/session", tags=["session"])
    app.include_router(analytics_routes.router, prefix="/api/analytics", tags=["analytics"])
    app.include_router(direct_proxy_routes.router)
    app.include_router(direct_proxy_routes.legacy_router)
    app.include_router(direct_proxy_routes.cf_router)
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the main application page"""
        with open("app/templates/index_simple.html", "r") as f:
            content = f.read()
            # Replace template variables
            content = content.replace("{{ settings.default_target_url }}", settings.default_target_url)
            return HTMLResponse(content=content)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            return {
                "status": "healthy",
                "version": settings.app_version,
                "active_connections": ws_manager.get_active_connections() if ws_manager else 0,
                "browser_pool_size": browser_pool.get_pool_size() if browser_pool else 0
            }
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    @app.websocket("/ws/proxy")
    async def websocket_proxy(websocket: WebSocket):
        """Main WebSocket endpoint for proxy communication"""
        session_id = str(uuid.uuid4())
        await websocket.accept()
        
        # Add to manager
        await ws_manager.connect(websocket, session_id)
        
        # Create session
        session = await session_manager.create_session(session_id)
        
        # Skip browser instance for now - use simple proxy
        browser_instance = None
        
        try:
            logger.info(f"New WebSocket connection: {session_id}")
            
            # Send initial configuration
            await websocket.send_json({
                "type": "init",
                "session_id": session_id,
                "config": {
                    "proxy_country": settings.proxy_country,
                    "timezone": settings.spoof_timezone,
                    "language": settings.spoof_language,
                    "coordinates": {
                        "latitude": settings.spoof_latitude,
                        "longitude": settings.spoof_longitude
                    }
                }
            })
            
            # Message handler loop
            while True:
                data = await websocket.receive_json()
                await handle_websocket_message(
                    websocket, session_id, data, browser_instance
                )
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {session_id}: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        finally:
            # Cleanup
            await ws_manager.disconnect(session_id)
            if browser_instance:
                await browser_pool.release(session_id)
            await session_manager.end_session(session_id)
            await direct_proxy.cleanup(session_id)
    
    async def handle_websocket_message(
        websocket: WebSocket,
        session_id: str,
        data: dict,
        browser_instance
    ):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "navigate":
            # Navigate to URL
            url = data.get("url")
            
            # Extract actual URL if it's a proxied URL
            if url and ('localhost' in url or '/api/direct-proxy/' in url):
                import re
                match = re.search(r'url=([^&]+)', url)
                if match:
                    from urllib.parse import unquote
                    original_url = unquote(match[1])
                    logger.info(f"Extracted original URL: {original_url} from proxy URL: {url}")
                    url = original_url
            
            logger.info(f"Session {session_id} navigating to: {url}")
            
            # Use direct proxy service to fetch content
            result = await direct_proxy.fetch_page(
                url=url,
                session_id=session_id
            )
            
            if result.get("success"):
                content = result["content"]
                # Handle bytes content
                if isinstance(content, bytes):
                    try:
                        content = content.decode('utf-8')
                    except:
                        content = f"<html><body><p>Binary content cannot be displayed</p></body></html>"
                
                # Extra aggressive IP replacement before sending
                import re
                ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
                ipv6_pattern = r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}'
                
                # Replace all IPs
                content = re.sub(ipv4_pattern, '104.28.246.156', content)
                content = re.sub(ipv6_pattern, '104.28.246.156', content)
                
                logger.info(f"Sending content to websocket, length: {len(content)}")
                logger.debug(f"Content preview: {content[:200]}...")
                
                await websocket.send_json({
                    "type": "page_content",
                    "url": url,
                    "content": content,
                    "scripts": [],
                    "styles": [],
                    "injections": []
                })
            else:
                await websocket.send_json({
                    "type": "page_content",
                    "url": url,
                    "content": result.get("content", result.get("error", "Failed to load page")),
                    "scripts": [],
                    "styles": [],
                    "injections": []
                })
            
        elif message_type == "http_request":
            # Handle HTTP request through proxy
            request_id = data.get("id")
            method = data.get("method", "GET")
            url = data.get("url")
            headers = data.get("headers", {})
            body = data.get("body")
            
            response = await proxy_service.make_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                session_id=session_id
            )
            
            await websocket.send_json({
                "type": "http_response",
                "id": request_id,
                "status": response["status"],
                "headers": response["headers"],
                "body": response["body"]
            })
            
        elif message_type == "touch_event":
            # Forward touch events to browser
            await browser_instance.handle_touch(data.get("touches"))
            
        elif message_type == "device_info":
            # Update session with device info
            await session_manager.update_device_info(
                session_id,
                data.get("device_info")
            )
            
        elif message_type == "analytics_event":
            # Handle analytics events
            await handle_analytics_event(session_id, data)
            
        elif message_type == "ping":
            # Respond to ping
            await websocket.send_json({"type": "pong"})
            
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_analytics_event(session_id: str, data: dict):
        """Handle analytics tracking events"""
        event_type = data.get("event_type")
        
        if event_type == "ga4":
            # Handle GA4 events with geographic spoofing
            logger.debug(f"GA4 event from {session_id}: {data}")
        elif event_type == "adsense":
            # Handle AdSense events
            logger.debug(f"AdSense event from {session_id}: {data}")
        elif event_type == "facebook_pixel":
            # Handle Facebook Pixel events
            logger.debug(f"FB Pixel event from {session_id}: {data}")
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler"""
        logger.error(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    return app


# Create app instance
app = create_app()
