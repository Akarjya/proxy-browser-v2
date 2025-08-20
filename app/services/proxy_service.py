"""
Proxy Service
Handles all proxy operations including geographic spoofing and request routing
"""

import httpx
import asyncio
from typing import Dict, Optional, Any, List
from urllib.parse import urlparse, urljoin, urlunparse
import json
import base64
from loguru import logger
from bs4 import BeautifulSoup
import re

try:
    from httpx_socks import AsyncProxyTransport
    SOCKS_SUPPORT = True
except ImportError:
    SOCKS_SUPPORT = False
    logger.warning("httpx-socks not installed, SOCKS proxy support disabled")

from config.settings import Settings, ProxyConfig


class ProxyService:
    """Main proxy service for handling requests and responses"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.proxy_config = ProxyConfig(settings)
        self.client_pool: Dict[str, httpx.AsyncClient] = {}
        self.max_clients = 100
        
    async def create_client(self, session_id: str) -> httpx.AsyncClient:
        """Create an HTTP client with proxy configuration"""
        
        # Get proxy URL for this session
        proxy_url = self.proxy_config.get_proxy_url(session_id)
        
        # Check if SOCKS proxy
        if proxy_url.startswith(("socks5://", "socks4://")):
            if not SOCKS_SUPPORT:
                raise RuntimeError("SOCKS proxy support not available. Install httpx-socks.")
            
            # Create SOCKS transport
            transport = AsyncProxyTransport.from_url(proxy_url)
            
            client = httpx.AsyncClient(
                transport=transport,
                timeout=httpx.Timeout(self.settings.request_timeout),
                follow_redirects=True,
                verify=False  # Disable SSL verification for proxy
            )
        else:
            # HTTP proxy
            client = httpx.AsyncClient(
                proxies={
                    "http://": proxy_url,
                    "https://": proxy_url
                },
                timeout=httpx.Timeout(self.settings.request_timeout),
                follow_redirects=True,
                verify=False  # Disable SSL verification for proxy
            )
        
        # Store in pool
        if len(self.client_pool) < self.max_clients:
            self.client_pool[session_id] = client
        
        logger.info(f"Created proxy client for session {session_id} using {proxy_url.split('://')[0]} proxy")
        
        return client
    
    async def get_client(self, session_id: str) -> httpx.AsyncClient:
        """Get or create HTTP client for session"""
        if session_id not in self.client_pool:
            return await self.create_client(session_id)
        return self.client_pool[session_id]
    
    async def make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """Make HTTP request through proxy"""
        
        try:
            # Get client
            client = await self.get_client(session_id or "default")
            
            # Prepare headers with geographic spoofing
            request_headers = self._prepare_headers(headers)
            
            # Make request
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                content=body
            )
            
            # Process response
            return {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "url": str(response.url)
            }
            
        except Exception as e:
            logger.error(f"Proxy request error: {str(e)}")
            return {
                "status": 500,
                "headers": {},
                "body": f"Proxy error: {str(e)}",
                "url": url
            }
    
    async def fetch_and_process(
        self,
        url: str,
        session_id: str,
        browser_instance=None,
        user_agent: Optional[str] = None,
        is_mobile: bool = False
    ) -> Dict:
        """Fetch and process web content with injections"""
        
        try:
            # If browser instance available, use it for JavaScript-heavy sites
            if browser_instance:
                return await self._fetch_with_browser(
                    url, session_id, browser_instance, user_agent, is_mobile
                )
            
            # Otherwise use HTTP client
            client = await self.get_client(session_id)
            
            # Prepare headers
            headers = self._prepare_headers({
                "User-Agent": user_agent or self._get_default_user_agent(is_mobile)
            })
            
            # Fetch content
            response = await client.get(url, headers=headers)
            
            # Process content based on type
            content_type = response.headers.get("content-type", "").lower()
            
            if "text/html" in content_type:
                # Process HTML with injections
                processed = await self._process_html(
                    response.text,
                    url,
                    session_id,
                    is_mobile
                )
                return processed
            
            elif "javascript" in content_type or "json" in content_type:
                # Process JavaScript
                processed = await self._process_javascript(
                    response.text,
                    url,
                    session_id
                )
                return {
                    "content": processed,
                    "scripts": [],
                    "styles": [],
                    "injections": []
                }
            
            elif "css" in content_type:
                # Process CSS
                processed = await self._process_css(
                    response.text,
                    url
                )
                return {
                    "content": processed,
                    "scripts": [],
                    "styles": [],
                    "injections": []
                }
            
            else:
                # Return as-is for other content types
                return {
                    "content": response.text,
                    "scripts": [],
                    "styles": [],
                    "injections": []
                }
                
        except Exception as e:
            logger.error(f"Fetch and process error: {str(e)}")
            return {
                "content": f"Error loading page: {str(e)}",
                "scripts": [],
                "styles": [],
                "injections": []
            }
    
    async def _fetch_with_browser(
        self,
        url: str,
        session_id: str,
        browser_instance,
        user_agent: Optional[str],
        is_mobile: bool
    ) -> Dict:
        """Fetch content using browser instance"""
        
        try:
            # Navigate to page
            page = browser_instance.page
            
            # Check if page is still valid
            if page.is_closed():
                raise Exception("Browser page has been closed")
            
            # Set user agent if provided
            if user_agent:
                await page.set_extra_http_headers({
                    "User-Agent": user_agent
                })
            
            # Add geographic spoofing scripts before navigation
            await page.add_init_script(self._get_injection_script())
            
            # Navigate with shorter timeout
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Get content
            content = await page.content()
            
            # Extract scripts and styles
            scripts = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script[src]'))
                    .map(s => s.src)
            """)
            
            styles = await page.evaluate("""
                () => Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
                    .map(l => l.href)
            """)
            
            # Process HTML
            processed = await self._process_html(
                content,
                url,
                session_id,
                is_mobile
            )
            
            return processed
            
        except Exception as e:
            logger.error(f"Browser fetch error: {str(e)}")
            # Return error page instead of raising
            return {
                "content": f"""
                <html>
                <head><title>Error Loading Page</title></head>
                <body>
                    <h1>Error Loading Page</h1>
                    <p>Failed to load: {url}</p>
                    <p>Error: {str(e)}</p>
                    <p>Please try again or contact support.</p>
                </body>
                </html>
                """,
                "scripts": [],
                "styles": [],
                "injections": []
            }
    
    async def _process_html(
        self,
        html: str,
        base_url: str,
        session_id: str,
        is_mobile: bool
    ) -> Dict:
        """Process HTML content with injections and URL rewriting"""
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Rewrite URLs
        if self.settings.rewrite_urls:
            await self._rewrite_urls(soup, base_url)
        
        # Extract scripts and styles
        scripts = [tag.get('src') for tag in soup.find_all('script', src=True)]
        styles = [tag.get('href') for tag in soup.find_all('link', rel='stylesheet')]
        
        # Add injection script
        injections = []
        if self.settings.inject_scripts:
            injection_script = soup.new_tag('script')
            injection_script.string = self._get_injection_script()
            
            # Insert at the beginning of head or body
            if soup.head:
                soup.head.insert(0, injection_script)
            elif soup.body:
                soup.body.insert(0, injection_script)
            
            injections.append(self._get_injection_script())
        
        # Add mobile-specific optimizations
        if is_mobile:
            viewport_tag = soup.new_tag('meta')
            viewport_tag.attrs['name'] = 'viewport'
            viewport_tag.attrs['content'] = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
            
            if soup.head:
                soup.head.insert(0, viewport_tag)
        
        return {
            "content": str(soup),
            "scripts": scripts,
            "styles": styles,
            "injections": injections
        }
    
    async def _rewrite_urls(self, soup: BeautifulSoup, base_url: str):
        """Rewrite URLs in HTML to go through proxy"""
        
        base_parsed = urlparse(base_url)
        
        # Rewrite link hrefs
        for tag in soup.find_all(['a', 'link']):
            if tag.get('href'):
                tag['href'] = self._rewrite_url(tag['href'], base_url)
        
        # Rewrite script and img srcs
        for tag in soup.find_all(['script', 'img', 'iframe']):
            if tag.get('src'):
                tag['src'] = self._rewrite_url(tag['src'], base_url)
        
        # Rewrite form actions
        for tag in soup.find_all('form'):
            if tag.get('action'):
                tag['action'] = self._rewrite_url(tag['action'], base_url)
        
        # Rewrite CSS urls in style attributes
        for tag in soup.find_all(style=True):
            tag['style'] = self._rewrite_css_urls(tag['style'], base_url)
    
    def _rewrite_url(self, url: str, base_url: str) -> str:
        """Rewrite a single URL to go through proxy"""
        
        if not url or url.startswith('data:') or url.startswith('javascript:'):
            return url
        
        # Make absolute URL
        absolute_url = urljoin(base_url, url)
        
        # Return proxy URL
        return f"/proxy?url={base64.b64encode(absolute_url.encode()).decode()}"
    
    def _rewrite_css_urls(self, css: str, base_url: str) -> str:
        """Rewrite URLs in CSS"""
        
        def replace_url(match):
            url = match.group(1).strip('\'"')
            return f'url("{self._rewrite_url(url, base_url)}")'
        
        return re.sub(r'url\((.*?)\)', replace_url, css)
    
    async def _process_javascript(self, js: str, url: str, session_id: str) -> str:
        """Process JavaScript content"""
        
        if not self.settings.rewrite_javascript:
            return js
        
        # Add proxy wrapper for fetch and XMLHttpRequest
        proxy_wrapper = """
        (function() {
            // Store original functions
            const originalFetch = window.fetch;
            const originalXHR = window.XMLHttpRequest;
            
            // Override fetch
            window.fetch = function(url, options) {
                const proxyUrl = '/proxy?url=' + btoa(new URL(url, window.location.href).href);
                return originalFetch.call(this, proxyUrl, options);
            };
            
            // Override XMLHttpRequest
            window.XMLHttpRequest = function() {
                const xhr = new originalXHR();
                const originalOpen = xhr.open;
                
                xhr.open = function(method, url, ...args) {
                    const proxyUrl = '/proxy?url=' + btoa(new URL(url, window.location.href).href);
                    return originalOpen.call(this, method, proxyUrl, ...args);
                };
                
                return xhr;
            };
        })();
        """
        
        return proxy_wrapper + "\n" + js
    
    async def _process_css(self, css: str, base_url: str) -> str:
        """Process CSS content"""
        
        if not self.settings.rewrite_css:
            return css
        
        return self._rewrite_css_urls(css, base_url)
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepare headers with geographic spoofing"""
        
        prepared = headers or {}
        
        # Add/modify headers for geographic spoofing
        prepared.update({
            "Accept-Language": f"{self.settings.spoof_language},en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # Remove headers that might reveal real location
        headers_to_remove = [
            "X-Real-IP",
            "X-Forwarded-For",
            "X-Client-IP",
            "CF-Connecting-IP"
        ]
        
        for header in headers_to_remove:
            prepared.pop(header, None)
        
        return prepared
    
    def _get_default_user_agent(self, is_mobile: bool) -> str:
        """Get default user agent based on device type"""
        
        if is_mobile:
            return self.settings.mobile_default_ua
        
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    
    def _get_injection_script(self) -> str:
        """Get JavaScript injection script for geographic spoofing"""
        
        return f"""
        (function() {{
            'use strict';
            
            // Store original values
            const originalUA = navigator.userAgent;
            const originalPlatform = navigator.platform;
            const originalVendor = navigator.vendor;
            
            // Geographic spoofing configuration
            const spoofConfig = {{
                timezone: '{self.settings.spoof_timezone}',
                language: '{self.settings.spoof_language}',
                languages: ['{self.settings.spoof_language}', 'en-US', 'en'],
                locale: '{self.settings.spoof_locale}',
                country: '{self.settings.spoof_country_code}',
                region: '{self.settings.spoof_region}',
                currency: '{self.settings.spoof_currency}',
                coords: {{
                    latitude: {self.settings.spoof_latitude},
                    longitude: {self.settings.spoof_longitude},
                    accuracy: {self.settings.spoof_accuracy}
                }}
            }};
            
            // Override geolocation
            if (navigator.geolocation) {{
                const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition;
                const originalWatchPosition = navigator.geolocation.watchPosition;
                
                navigator.geolocation.getCurrentPosition = function(success, error, options) {{
                    const position = {{
                        coords: {{
                            latitude: spoofConfig.coords.latitude,
                            longitude: spoofConfig.coords.longitude,
                            accuracy: spoofConfig.coords.accuracy,
                            altitude: null,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        }},
                        timestamp: Date.now()
                    }};
                    setTimeout(() => success(position), 100);
                }};
                
                navigator.geolocation.watchPosition = function(success, error, options) {{
                    const position = {{
                        coords: {{
                            latitude: spoofConfig.coords.latitude,
                            longitude: spoofConfig.coords.longitude,
                            accuracy: spoofConfig.coords.accuracy,
                            altitude: null,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        }},
                        timestamp: Date.now()
                    }};
                    const id = setInterval(() => success(position), 1000);
                    return id;
                }};
            }}
            
            // Override language properties
            Object.defineProperty(navigator, 'language', {{
                get: () => spoofConfig.language
            }});
            
            Object.defineProperty(navigator, 'languages', {{
                get: () => spoofConfig.languages
            }});
            
            // Override timezone
            const originalDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = new Proxy(originalDateTimeFormat, {{
                construct(target, args) {{
                    if (args[1]) {{
                        args[1].timeZone = spoofConfig.timezone;
                    }} else {{
                        args[1] = {{ timeZone: spoofConfig.timezone }};
                    }}
                    return new target(...args);
                }}
            }});
            
            // Override Date timezone methods
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {{
                // Return offset for spoofed timezone (EST = +5 hours = 300 minutes)
                return spoofConfig.timezone === 'America/New_York' ? 300 : 0;
            }};
            
            // Preserve device characteristics
            Object.defineProperty(navigator, 'userAgent', {{
                get: () => originalUA
            }});
            
            Object.defineProperty(navigator, 'platform', {{
                get: () => originalPlatform
            }});
            
            Object.defineProperty(navigator, 'vendor', {{
                get: () => originalVendor
            }});
            
            // WebRTC IP leak prevention
            if (window.RTCPeerConnection) {{
                const pc = window.RTCPeerConnection.prototype;
                const originalCreateOffer = pc.createOffer;
                const originalCreateAnswer = pc.createAnswer;
                
                pc.createOffer = async function(options) {{
                    const offer = await originalCreateOffer.call(this, options);
                    // Remove local IP candidates
                    offer.sdp = offer.sdp.replace(/a=candidate:.*host.*/g, '');
                    return offer;
                }};
                
                pc.createAnswer = async function(options) {{
                    const answer = await originalCreateAnswer.call(this, options);
                    // Remove local IP candidates
                    answer.sdp = answer.sdp.replace(/a=candidate:.*host.*/g, '');
                    return answer;
                }};
            }}
            
            // Console log for debugging
            console.log('Geographic spoofing initialized:', spoofConfig);
        }})();
        """
    
    async def cleanup(self):
        """Cleanup proxy service resources"""
        
        # Close all HTTP clients
        for client in self.client_pool.values():
            await client.aclose()
        
        self.client_pool.clear()
        logger.info("Proxy service cleaned up")
