"""
Simple Proxy Service
Direct HTTP proxy implementation without browser pool
"""

import httpx
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlparse, urljoin
import json
from loguru import logger
from bs4 import BeautifulSoup
import re

from config.settings import Settings, ProxyConfig


class SimpleProxyService:
    """Simplified proxy service using direct HTTP requests"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.proxy_config = ProxyConfig(settings)
        self._clients: Dict[str, httpx.AsyncClient] = {}
        
    async def get_client(self, session_id: str) -> httpx.AsyncClient:
        """Get or create HTTP client for session"""
        
        if session_id not in self._clients:
            proxy_url = self.proxy_config.get_proxy_url(session_id)
            logger.info(f"Creating HTTP client for session {session_id} with proxy {proxy_url}")
            
            # Create client with HTTP proxy
            self._clients[session_id] = httpx.AsyncClient(
                proxies={
                    "http://": proxy_url,
                    "https://": proxy_url
                },
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                verify=False,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            
        return self._clients[session_id]
    
    async def fetch_page(
        self,
        url: str,
        session_id: str,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Fetch page content through proxy"""
        
        try:
            client = await self.get_client(session_id)
            
            # Prepare headers
            request_headers = {
                "User-Agent": headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            if headers:
                request_headers.update(headers)
            
            # Make request
            logger.info(f"Fetching {url} for session {session_id}")
            response = await client.get(url, headers=request_headers)
            
            # Process response
            content_type = response.headers.get("content-type", "")
            
            if "text/html" in content_type:
                # Process HTML
                html = response.text
                processed_html = await self._process_html(html, url, session_id)
                
                return {
                    "success": True,
                    "content": processed_html,
                    "content_type": "text/html",
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
            else:
                # Return other content types as-is
                return {
                    "success": True,
                    "content": response.text,
                    "content_type": content_type,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": self._error_page(url, str(e))
            }
    
    async def _process_html(self, html: str, base_url: str, session_id: str) -> str:
        """Process HTML to inject spoofing scripts"""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Create injection script
            injection_script = soup.new_tag('script')
            injection_script.string = self._get_injection_script()
            
            # Insert at the beginning of head or body
            if soup.head:
                soup.head.insert(0, injection_script)
            elif soup.body:
                soup.body.insert(0, injection_script)
            else:
                # Create head if doesn't exist
                head = soup.new_tag('head')
                head.append(injection_script)
                if soup.html:
                    soup.html.insert(0, head)
            
            # Add base tag for relative URLs
            if soup.head and not soup.find('base'):
                base_tag = soup.new_tag('base', href=base_url)
                soup.head.insert(0, base_tag)
            
            return str(soup)
            
        except Exception as e:
            logger.error(f"Error processing HTML: {str(e)}")
            return html
    
    def _get_injection_script(self) -> str:
        """Get JavaScript injection for geographic spoofing"""
        
        return f"""
        (function() {{
            'use strict';
            
            // Override timezone
            const originalDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = new Proxy(originalDateTimeFormat, {{
                construct(target, args) {{
                    if (args[1] && !args[1].timeZone) {{
                        args[1] = {{...args[1], timeZone: '{self.settings.spoof_timezone}'}};
                    }}
                    return new target(...args);
                }}
            }});
            
            // Override geolocation
            if (navigator.geolocation) {{
                const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition;
                navigator.geolocation.getCurrentPosition = function(success, error, options) {{
                    success({{
                        coords: {{
                            latitude: {self.settings.spoof_latitude},
                            longitude: {self.settings.spoof_longitude},
                            altitude: null,
                            accuracy: 50,
                            altitudeAccuracy: null,
                            heading: null,
                            speed: null
                        }},
                        timestamp: Date.now()
                    }});
                }};
            }}
            
            // Override language
            Object.defineProperty(navigator, 'language', {{
                get: () => '{self.settings.spoof_language}'
            }});
            
            Object.defineProperty(navigator, 'languages', {{
                get: () => ['{self.settings.spoof_language}', 'en-US', 'en']
            }});
            
            // Remove webdriver property
            delete navigator.__proto__.webdriver;
            
            // Override plugins to appear more real
            Object.defineProperty(navigator, 'plugins', {{
                get: () => {{
                    return {{
                        0: {{description: "Portable Document Format", filename: "internal-pdf-viewer", length: 1, name: "Chrome PDF Plugin"}},
                        1: {{description: "Portable Document Format", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", length: 1, name: "Chrome PDF Viewer"}},
                        length: 2
                    }};
                }}
            }});
            
            console.log('Geographic spoofing initialized');
        }})();
        """
    
    def _error_page(self, url: str, error: str) -> str:
        """Generate error page HTML"""
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error Loading Page</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f0f0f0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }}
                .error-container {{
                    background-color: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                }}
                h1 {{
                    color: #d32f2f;
                    margin-bottom: 20px;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                }}
                .url {{
                    background-color: #f5f5f5;
                    padding: 10px;
                    border-radius: 5px;
                    word-break: break-all;
                    margin: 20px 0;
                }}
                .error-details {{
                    background-color: #fee;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                    color: #c33;
                }}
                button {{
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                }}
                button:hover {{
                    background-color: #1565c0;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <h1>⚠️ Error Loading Page</h1>
                <p>We encountered an error while loading the requested page.</p>
                <div class="url">
                    <strong>URL:</strong> {url}
                </div>
                <div class="error-details">
                    <strong>Error:</strong> {error}
                </div>
                <p>This could be due to:</p>
                <ul style="text-align: left; display: inline-block;">
                    <li>Network connectivity issues</li>
                    <li>The website being temporarily unavailable</li>
                    <li>Proxy server issues</li>
                    <li>Invalid URL</li>
                </ul>
                <button onclick="window.location.reload()">Try Again</button>
            </div>
        </body>
        </html>
        """
    
    async def cleanup(self, session_id: Optional[str] = None):
        """Clean up client connections"""
        
        if session_id and session_id in self._clients:
            await self._clients[session_id].aclose()
            del self._clients[session_id]
        elif not session_id:
            # Clean up all clients
            for client in self._clients.values():
                await client.aclose()
            self._clients.clear()
