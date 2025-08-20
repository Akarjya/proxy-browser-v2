"""
Browser Pool Manager
Manages a pool of Playwright browser instances for efficient resource usage
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import stealth_async
from loguru import logger
import uuid
from dataclasses import dataclass, field


@dataclass
class BrowserInstance:
    """Represents a single browser instance in the pool"""
    
    id: str
    context: BrowserContext
    page: Page
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    is_busy: bool = False
    is_mobile: bool = False
    
    def update_last_used(self):
        """Update last used timestamp"""
        self.last_used = datetime.now()
    
    def mark_busy(self, session_id: str):
        """Mark instance as busy"""
        self.is_busy = True
        self.session_id = session_id
        self.update_last_used()
    
    def mark_free(self):
        """Mark instance as free"""
        self.is_busy = False
        self.session_id = None
    
    @property
    def idle_time(self) -> float:
        """Get idle time in seconds"""
        return (datetime.now() - self.last_used).total_seconds()


class BrowserPoolManager:
    """Manages a pool of browser instances"""
    
    def __init__(self, settings):
        self.settings = settings
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.pool: Dict[str, BrowserInstance] = {}
        self.session_map: Dict[str, str] = {}  # session_id -> instance_id
        self.max_pool_size = settings.browser_pool_size
        self.idle_timeout = 300  # 5 minutes
        self.cleanup_interval = 60  # 1 minute
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize the browser pool"""
        
        logger.info("Initializing browser pool...")
        
        # Start Playwright
        self.playwright = await async_playwright().start()
        
        # Launch browser
        launch_args = self.settings.browser_args.copy()
        
        # Add proxy server if configured
        proxy_config = None
        if self.settings.proxy_server:
            # Playwright supports HTTP proxy with authentication
            if self.settings.proxy_type.lower() == "http":
                proxy_server = f"http://{self.settings.proxy_server}"
                proxy_config = {
                    "server": proxy_server,
                    "username": self.settings.proxy_username,
                    "password": self.settings.proxy_password
                }
                logger.info(f"Browser will use HTTP proxy: {self.settings.proxy_server}")
            else:
                # For SOCKS5, we'll use httpx for requests instead of browser
                logger.warning("Playwright doesn't support SOCKS5 authentication. Using HTTP proxy for browser.")
                proxy_config = None
            
            logger.info(f"Browser proxy configuration: {proxy_config}")
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.settings.browser_headless,
            args=launch_args,
            proxy=proxy_config
        )
        
        # Pre-create some instances
        await self._pre_create_instances(min(3, self.max_pool_size))
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Browser pool initialized with {len(self.pool)} instances")
    
    async def _pre_create_instances(self, count: int):
        """Pre-create browser instances"""
        
        tasks = []
        for _ in range(count):
            tasks.append(self._create_instance())
        
        instances = await asyncio.gather(*tasks, return_exceptions=True)
        
        for instance in instances:
            if isinstance(instance, BrowserInstance):
                self.pool[instance.id] = instance
    
    async def _create_instance(
        self,
        is_mobile: bool = False,
        user_agent: Optional[str] = None
    ) -> BrowserInstance:
        """Create a new browser instance"""
        
        instance_id = str(uuid.uuid4())
        
        # Determine viewport and user agent
        if is_mobile:
            viewport = {
                "width": self.settings.mobile_viewport_width,
                "height": self.settings.mobile_viewport_height
            }
            default_ua = self.settings.mobile_default_ua
        else:
            viewport = {
                "width": self.settings.browser_viewport_width,
                "height": self.settings.browser_viewport_height
            }
            default_ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        
        # Create context with spoofed properties
        context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent or default_ua,
            locale=self.settings.spoof_locale,
            timezone_id=self.settings.spoof_timezone,
            geolocation={
                "latitude": self.settings.spoof_latitude,
                "longitude": self.settings.spoof_longitude
            },
            permissions=["geolocation"],
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
            extra_http_headers={
                "Accept-Language": f"{self.settings.spoof_language},en;q=0.9"
            }
        )
        
        # Create page
        page = await context.new_page()
        
        # Apply stealth techniques
        await stealth_async(page)
        
        # Add initialization scripts
        await self._add_init_scripts(page)
        
        # Set default timeout
        page.set_default_timeout(self.settings.browser_timeout)
        page.set_default_navigation_timeout(self.settings.browser_timeout)
        
        instance = BrowserInstance(
            id=instance_id,
            context=context,
            page=page,
            is_mobile=is_mobile
        )
        
        logger.debug(f"Created browser instance: {instance_id}")
        
        return instance
    
    async def _add_init_scripts(self, page: Page):
        """Add initialization scripts to page"""
        
        # Override navigator properties
        await page.add_init_script("""
            // Override timezone
            Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
                value: function() {
                    return {
                        ...Intl.DateTimeFormat.prototype.resolvedOptions.call(this),
                        timeZone: '%s'
                    };
                }
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['%s', 'en-US', 'en']
            });
            
            // Override plugins to appear more realistic
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf"},
                            description: "Portable Document Format",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }
                    ];
                }
            });
            
            // Override WebGL vendor and renderer
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.call(this, parameter);
            };
            
            // Remove automation indicators
            delete navigator.__proto__.webdriver;
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """ % (self.settings.spoof_timezone, self.settings.spoof_language))
        
        # Add console message
        await page.add_init_script("""
            console.log('[Proxy Browser] Page initialized with geographic spoofing');
        """)
    
    async def acquire(
        self,
        session_id: str,
        is_mobile: bool = False,
        user_agent: Optional[str] = None
    ) -> BrowserInstance:
        """Acquire a browser instance for a session"""
        
        async with self._lock:
            # Check if session already has an instance
            if session_id in self.session_map:
                instance_id = self.session_map[session_id]
                if instance_id in self.pool:
                    instance = self.pool[instance_id]
                    instance.update_last_used()
                    return instance
            
            # Find a free instance
            for instance in self.pool.values():
                if not instance.is_busy and instance.is_mobile == is_mobile:
                    instance.mark_busy(session_id)
                    self.session_map[session_id] = instance.id
                    logger.debug(f"Assigned existing instance {instance.id} to session {session_id}")
                    return instance
            
            # Create new instance if pool not full
            if len(self.pool) < self.max_pool_size:
                instance = await self._create_instance(is_mobile, user_agent)
                instance.mark_busy(session_id)
                self.pool[instance.id] = instance
                self.session_map[session_id] = instance.id
                logger.debug(f"Created new instance {instance.id} for session {session_id}")
                return instance
            
            # Wait for an instance to become available
            logger.warning(f"Browser pool full, waiting for available instance...")
            
            while True:
                await asyncio.sleep(0.5)
                for instance in self.pool.values():
                    if not instance.is_busy:
                        instance.mark_busy(session_id)
                        self.session_map[session_id] = instance.id
                        return instance
    
    async def release(self, session_id: str):
        """Release a browser instance"""
        
        async with self._lock:
            if session_id in self.session_map:
                instance_id = self.session_map[session_id]
                if instance_id in self.pool:
                    instance = self.pool[instance_id]
                    
                    # Clear page content
                    try:
                        if instance.page and not instance.page.is_closed():
                            await instance.page.goto("about:blank")
                    except Exception as e:
                        logger.debug(f"Error clearing page: {e}")
                    
                    instance.mark_free()
                    del self.session_map[session_id]
                    
                    logger.debug(f"Released instance {instance_id} from session {session_id}")
    
    async def _cleanup_loop(self):
        """Periodically clean up idle instances"""
        
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_idle_instances()
            except Exception as e:
                logger.error(f"Cleanup loop error: {str(e)}")
    
    async def _cleanup_idle_instances(self):
        """Clean up instances that have been idle too long"""
        
        async with self._lock:
            instances_to_remove = []
            
            for instance_id, instance in self.pool.items():
                if not instance.is_busy and instance.idle_time > self.idle_timeout:
                    instances_to_remove.append(instance_id)
            
            # Keep at least 2 instances
            while instances_to_remove and len(self.pool) - len(instances_to_remove) < 2:
                instances_to_remove.pop()
            
            for instance_id in instances_to_remove:
                instance = self.pool[instance_id]
                try:
                    await instance.page.close()
                    await instance.context.close()
                except:
                    pass
                
                del self.pool[instance_id]
                logger.debug(f"Cleaned up idle instance: {instance_id}")
            
            if instances_to_remove:
                logger.info(f"Cleaned up {len(instances_to_remove)} idle instances")
    
    async def cleanup(self):
        """Clean up all browser instances"""
        
        logger.info("Cleaning up browser pool...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Close all instances
        for instance in self.pool.values():
            try:
                await instance.page.close()
                await instance.context.close()
            except Exception as e:
                logger.error(f"Error closing instance {instance.id}: {str(e)}")
        
        # Close browser
        if self.browser:
            await self.browser.close()
        
        # Stop Playwright
        if self.playwright:
            await self.playwright.stop()
        
        self.pool.clear()
        self.session_map.clear()
        
        logger.info("Browser pool cleaned up")
    
    def get_pool_size(self) -> int:
        """Get current pool size"""
        return len(self.pool)
    
    def get_active_count(self) -> int:
        """Get count of active instances"""
        return sum(1 for instance in self.pool.values() if instance.is_busy)
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        
        active_count = self.get_active_count()
        idle_count = len(self.pool) - active_count
        
        stats = {
            "total_instances": len(self.pool),
            "active_instances": active_count,
            "idle_instances": idle_count,
            "max_pool_size": self.max_pool_size,
            "sessions": len(self.session_map),
            "instances": []
        }
        
        for instance in self.pool.values():
            stats["instances"].append({
                "id": instance.id,
                "is_busy": instance.is_busy,
                "session_id": instance.session_id,
                "is_mobile": instance.is_mobile,
                "created_at": instance.created_at.isoformat(),
                "last_used": instance.last_used.isoformat(),
                "idle_time": instance.idle_time
            })
        
        return stats
    
    async def execute_script(self, session_id: str, script: str) -> Any:
        """Execute JavaScript in a session's browser"""
        
        if session_id in self.session_map:
            instance_id = self.session_map[session_id]
            if instance_id in self.pool:
                instance = self.pool[instance_id]
                result = await instance.page.evaluate(script)
                instance.update_last_used()
                return result
        
        raise ValueError(f"No browser instance for session {session_id}")
    
    async def take_screenshot(self, session_id: str) -> bytes:
        """Take screenshot of current page"""
        
        if session_id in self.session_map:
            instance_id = self.session_map[session_id]
            if instance_id in self.pool:
                instance = self.pool[instance_id]
                screenshot = await instance.page.screenshot(full_page=True)
                instance.update_last_used()
                return screenshot
        
        raise ValueError(f"No browser instance for session {session_id}")
    
    async def navigate(self, session_id: str, url: str, wait_until: str = "networkidle"):
        """Navigate to a URL"""
        
        if session_id in self.session_map:
            instance_id = self.session_map[session_id]
            if instance_id in self.pool:
                instance = self.pool[instance_id]
                await instance.page.goto(url, wait_until=wait_until)
                instance.update_last_used()
                return
        
        raise ValueError(f"No browser instance for session {session_id}")
