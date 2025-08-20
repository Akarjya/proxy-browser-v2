"""
Direct Proxy Service
Simplified proxy implementation using httpx directly
"""

import httpx
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlparse, urljoin, quote
import re
from loguru import logger
from bs4 import BeautifulSoup

from config.settings import Settings, ProxyConfig


class DirectProxyService:
    """Direct proxy service using httpx"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.proxy_config = ProxyConfig(settings)
        self._clients: Dict[str, httpx.AsyncClient] = {}
        
    async def get_client(self, session_id: str) -> httpx.AsyncClient:
        """Get or create HTTP client for session"""
        
        if session_id not in self._clients:
            # Force HTTP proxy for header forwarding
            original_proxy_type = self.settings.proxy_type
            if original_proxy_type == "socks5":
                # Temporarily switch to HTTP proxy for proper header forwarding
                self.settings.proxy_type = "http"
                logger.warning("Switching from SOCKS5 to HTTP proxy for header forwarding support")
            
            proxy_url = self.proxy_config.get_proxy_url(session_id)
            logger.info(f"Creating HTTP client for session {session_id} with proxy {proxy_url}")
            
            # Restore original proxy type
            self.settings.proxy_type = original_proxy_type
            
            # Create client with proxy
            self._clients[session_id] = httpx.AsyncClient(
                proxies={
                    "http://": proxy_url,
                    "https://": proxy_url
                },
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                verify=False,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Accept-Language": self.settings.spoof_language,
                    "Accept-Encoding": "gzip, deflate",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                    # Add location headers that some sites check
                    "X-Forwarded-For": "104.28.246.156",  # US IP (New York)
                    "CF-IPCountry": "US",
                    "CloudFront-Viewer-Country": "US",
                    "X-Real-IP": "104.28.246.156",
                    "X-Country-Code": "US",
                    "X-City": "New York",
                    "X-Region": "NY",
                    "X-Timezone": "America/New_York",
                    # Additional headers for GA4
                    "X-Appengine-User-IP": "104.28.246.156",
                    "X-Appengine-Country": "US",
                    "X-Appengine-Region": "ny",
                    "X-Appengine-City": "new york",
                    "Forwarded": "for=104.28.246.156;proto=https",
                    "True-Client-IP": "104.28.246.156"
                }
            )
            
        return self._clients[session_id]
    
    def _get_injection_script(self, session_id: str, base_url: str) -> str:
        """Get JavaScript and navigation interception injection"""
        # Extract domain from base_url for base tag
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        base_href = f"{parsed.scheme}://{parsed.netloc}/"
        
        return f"""
        <base href="{base_href}">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
        <meta name="x-proxy-ip" content="104.28.246.156">
        <meta name="x-proxy-country" content="US">
        <meta name="x-proxy-city" content="New York">
        <style id="proxy-hide-style">
        /* Hide body content briefly to prevent IP flash */
        body > * {{ opacity: 0 !important; transition: opacity 0.3s; }}
        </style>
        <style id="proxy-fixes">
        /* Fix common styling issues */
        html, body {{
            overflow-x: auto !important;
            -webkit-text-size-adjust: 100% !important;
            width: 100% !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        
        /* Ensure proper viewport on mobile */
        * {{
            box-sizing: border-box !important;
        }}
        
        /* Ensure ads containers are visible */
        .adsbygoogle, ins.adsbygoogle, [id*="google_ads"], [class*="google-ad"] {{
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            min-height: 50px !important;
        }}
        
        /* Fix responsive issues */
        @media (max-width: 768px) {{
            body {{
                min-width: 320px !important;
            }}
        }}
        </style>
        <!-- PHP Override for server-side detection -->
        <?php
        if (!defined('PROXY_OVERRIDE')) {{
            define('PROXY_OVERRIDE', true);
            $_SERVER['REMOTE_ADDR'] = '104.28.246.156';
            $_SERVER['HTTP_X_FORWARDED_FOR'] = '104.28.246.156';
            $_SERVER['HTTP_X_REAL_IP'] = '104.28.246.156';
            $_SERVER['HTTP_CF_IPCOUNTRY'] = 'US';
            $_SERVER['GEOIP_COUNTRY_CODE'] = 'US';
            $_SERVER['GEOIP_CITY'] = 'New York';
            $_SERVER['GEOIP_REGION'] = 'NY';
        }}
        ?>
        <script>
        // Immediate IP replacement before page renders
        (function() {{
            // Replace IPs in the initial HTML immediately
            const ipv4Pattern = /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g;
            const ipv6Pattern = /(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}/g;
            
            // Create MutationObserver to catch any dynamic changes
            const observer = new MutationObserver((mutations) => {{
                mutations.forEach((mutation) => {{
                    if (mutation.type === 'childList') {{
                        mutation.addedNodes.forEach((node) => {{
                            if (node.nodeType === 3) {{ // Text node
                                const text = node.textContent;
                                if (text && (ipv4Pattern.test(text) || ipv6Pattern.test(text))) {{
                                    node.textContent = text.replace(ipv4Pattern, '104.28.246.156').replace(ipv6Pattern, '104.28.246.156');
                                }}
                            }}
                        }});
                    }}
                }});
            }});
            
            // Start observing immediately
            observer.observe(document.documentElement, {{
                childList: true,
                subtree: true,
                characterData: true
            }});
            
            // Stop observer after page loads
            window.addEventListener('load', () => {{
                setTimeout(() => observer.disconnect(), 2000);
            }});
        }})();
        
        (function() {{
            const SESSION_ID = {session_id!r};
            const BASE_URL = {base_url!r};

            const toAbsolute = (u) => {{
                try {{ 
                    // Handle already proxied URLs
                    if (u && (u.includes('localhost:8000') || u.includes('/api/direct-proxy/'))) {{
                        const match = u.match(/url=([^&]+)/);
                        if (match) {{
                            const decoded = decodeURIComponent(match[1]);
                            console.log('Extracted original URL:', decoded);
                            return decoded;
                        }}
                    }}
                    const absUrl = new URL(u, BASE_URL).href;
                    return absUrl;
                }} catch {{ return u; }}
            }};
            const toProxyNav = (u) => {{
                const absUrl = toAbsolute(u);
                // Don't proxy localhost URLs
                if (absUrl.includes('localhost:8000')) return absUrl;
                return `/api/direct-proxy/navigate?url=${{encodeURIComponent(absUrl)}}&session_id=${{encodeURIComponent(SESSION_ID)}}`;
            }};
            const toProxyRes = (u) => {{
                const absUrl = toAbsolute(u);
                // Don't proxy localhost URLs
                if (absUrl.includes('localhost:8000')) return absUrl;
                return `/api/direct-proxy/resource?url=${{encodeURIComponent(absUrl)}}&session_id=${{encodeURIComponent(SESSION_ID)}}`;
            }};

            // Intercept anchor clicks
            document.addEventListener('click', (e) => {{
                const a = e.target.closest('a[href]');
                if (!a) return;
                const href = a.getAttribute('href');
                if (!href || href.includes('/api/direct-proxy/')) return;
                e.preventDefault();
                const absoluteUrl = toAbsolute(href);
                const proxyUrl = toProxyNav(absoluteUrl);
                console.log('Link click intercepted:', href, '->', proxyUrl);
                window.location.href = proxyUrl;
            }}, true);

            // Intercept form submissions
            document.addEventListener('submit', (e) => {{
                const form = e.target;
                if (!form || !form.action) return;
                e.preventDefault();
                window.location.href = toProxyNav(form.action);
            }}, true);

            // Intercept window.location changes
            const _assign = window.location.assign.bind(window.location);
            window.location.assign = (u) => _assign(toProxyNav(u));
            const _replace = window.location.replace.bind(window.location);
            window.location.replace = (u) => _replace(toProxyNav(u));

            // Intercept History API
            const _pushState = history.pushState.bind(history);
            history.pushState = (state, title, url) => _pushState(state, title, toProxyNav(url));
            const _replaceState = history.replaceState.bind(history);
            history.replaceState = (state, title, url) => _replaceState(state, title, toProxyNav(url));

            // Intercept fetch with IP API override
            const _fetch = window.fetch.bind(window);
            window.fetch = (input, init = {{}}) => {{
                const url = typeof input === 'string' ? input : (input?.url || '');
                
                // Intercept IP detection APIs
                if (url.includes('ipapi.co/json') || url.includes('api.ipify.org') || url.includes('ipinfo.io')) {{
                    // Return fake US data
                    return Promise.resolve(new Response(JSON.stringify({{
                        ip: '104.28.246.156',
                        city: 'New York',
                        region: 'New York',
                        region_code: 'NY',
                        country: 'US',
                        country_name: 'United States',
                        country_code: 'US',
                        country_code_iso3: 'USA',
                        country_capital: 'Washington',
                        country_tld: '.us',
                        continent_code: 'NA',
                        in_eu: false,
                        postal: '10001',
                        latitude: 40.7128,
                        longitude: -74.0060,
                        timezone: 'America/New_York',
                        utc_offset: '-0500',
                        country_calling_code: '+1',
                        currency: 'USD',
                        currency_name: 'Dollar',
                        languages: 'en-US',
                        country_area: 9372610.0,
                        country_population: 331002651,
                        asn: 'AS13335',
                        org: 'Cloudflare, Inc.'
                    }}), {{
                        status: 200,
                        statusText: 'OK',
                        headers: new Headers({{
                            'Content-Type': 'application/json'
                        }})
                    }}));
                }}
                
                return _fetch(toProxyRes(url), init);
            }};

            // Intercept XHR
            const _open = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url, ...rest) {{
                return _open.call(this, method, toProxyRes(url), ...rest);
            }};

            // Override geolocation
            const mockPosition = {{
                coords: {{
                    latitude: {self.settings.spoof_latitude},
                    longitude: {self.settings.spoof_longitude},
                    accuracy: 100,
                    altitude: null,
                    altitudeAccuracy: null,
                    heading: null,
                    speed: null
                }},
                timestamp: Date.now()
            }};
            
            navigator.geolocation.getCurrentPosition = function(success, error) {{
                success(mockPosition);
            }};
            
            navigator.geolocation.watchPosition = function(success, error) {{
                success(mockPosition);
                return Math.floor(Math.random() * 10000);
            }};
            
            // Override timezone
            const originalDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = function(...args) {{
                if (args[1] && typeof args[1] === 'object') {{
                    args[1].timeZone = '{self.settings.spoof_timezone}';
                }} else {{
                    args[1] = {{ timeZone: '{self.settings.spoof_timezone}' }};
                }}
                return new originalDateTimeFormat(...args);
            }};
            
            // Override Date timezone methods
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {{
                // Return offset for America/New_York (EST/EDT)
                const now = new Date();
                const jan = new Date(now.getFullYear(), 0, 1);
                const jul = new Date(now.getFullYear(), 6, 1);
                const stdOffset = Math.max(jan.getTimezoneOffset(), jul.getTimezoneOffset());
                return now.getTimezoneOffset() === stdOffset ? 300 : 240; // EST: +5 hours, EDT: +4 hours
            }};
            
            // Override language
            Object.defineProperty(navigator, 'language', {{
                get: () => '{self.settings.spoof_language}',
                configurable: true
            }});
            
            Object.defineProperty(navigator, 'languages', {{
                get: () => ['{self.settings.spoof_language}'],
                configurable: true
            }});
            
            console.log('Geographic spoofing injected');
            
                               // Immediately replace any visible IPs on page load
                   const replaceAllIPs = () => {{
                       const ipv4Regex = /\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b/g;
                       const ipv6Regex = /(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}/g;

                       // Replace in all text nodes
                       const walk = document.createTreeWalker(
                           document.body,
                           NodeFilter.SHOW_TEXT,
                           null,
                           false
                       );

                       let node;
                       while (node = walk.nextNode()) {{
                           if (node.nodeValue && (ipv4Regex.test(node.nodeValue) || ipv6Regex.test(node.nodeValue))) {{
                               node.nodeValue = node.nodeValue.replace(ipv4Regex, '104.28.246.156').replace(ipv6Regex, '104.28.246.156');
                           }}
                       }}

                       // Replace in attributes
                       const allElements = document.querySelectorAll('*');
                       allElements.forEach(el => {{
                           Array.from(el.attributes).forEach(attr => {{
                               if (attr.value && (ipv4Regex.test(attr.value) || ipv6Regex.test(attr.value))) {{
                                   attr.value = attr.value.replace(ipv4Regex, '104.28.246.156').replace(ipv6Regex, '104.28.246.156');
                               }}
                           }});
                       }});

                       // Show content after replacement
                       const hideStyle = document.getElementById('proxy-hide-style');
                       if (hideStyle) {{
                           hideStyle.remove();
                       }}
                       document.querySelectorAll('body > *').forEach(el => {{
                           el.style.opacity = '1';
                       }});
                   }};

                   // Run immediately
                   if (document.readyState === 'loading') {{
                       document.addEventListener('DOMContentLoaded', replaceAllIPs);
                   }} else {{
                       replaceAllIPs();
                   }}
                   
                   // Run multiple times to catch dynamic content
                   setTimeout(replaceAllIPs, 0);
                   setTimeout(replaceAllIPs, 100);
                   setTimeout(replaceAllIPs, 500);
                   setTimeout(replaceAllIPs, 1000);
            
            // Override server-side detection methods
            if (window.XMLHttpRequest) {{
                const _send = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.send = function() {{
                    this.setRequestHeader('X-Forwarded-For', '104.28.246.156');
                    this.setRequestHeader('X-Real-IP', '104.28.246.156');
                    return _send.apply(this, arguments);
                }};
            }}
            
            // Enable AdSense in iframe
            window.adsbygoogle = window.adsbygoogle || [];
            
            // Override document.domain check for ads
            try {{
                Object.defineProperty(document, 'domain', {{
                    get: function() {{ return '{parsed.netloc}'; }},
                    set: function(val) {{ return val; }}
                }});
            }} catch(e) {{}}
            
            // Add fake server variables for PHP
            window.__SERVER = {{
                REMOTE_ADDR: '104.28.246.156',
                HTTP_X_FORWARDED_FOR: '104.28.246.156',
                HTTP_X_REAL_IP: '104.28.246.156',
                HTTP_CF_IPCOUNTRY: 'US',
                GEOIP_COUNTRY_CODE: 'US',
                GEOIP_CITY: 'New York',
                GEOIP_REGION: 'NY'
            }};
            
            // Override any IP display on the page
            setTimeout(() => {{
                // Find and replace both IPv4 and IPv6 addresses
                const ipv4Regex = /\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b/g;
                const ipv6Regex = /(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}/g;
                
                const walkTextNodes = (node) => {{
                    if (node.nodeType === 3) {{ // Text node
                        const text = node.textContent;
                        let newText = text;
                        // Replace IPv4
                        if (ipv4Regex.test(text)) {{
                            newText = newText.replace(ipv4Regex, '104.28.246.156');
                        }}
                        // Replace IPv6
                        if (ipv6Regex.test(text)) {{
                            newText = newText.replace(ipv6Regex, '104.28.246.156');
                        }}
                        if (newText !== text) {{
                            node.textContent = newText;
                            console.log('Replaced IP in text:', text, '->', newText);
                        }}
                    }} else {{
                        for (let child of node.childNodes) {{
                            walkTextNodes(child);
                        }}
                    }}
                }};
                walkTextNodes(document.body);
                
                // Also check for elements with specific IDs or classes
                const ipElements = document.querySelectorAll('[id*="ip"], [class*="ip"], [id*="IP"], [class*="IP"], .ip-address, #ip-display');
                ipElements.forEach(el => {{
                    let text = el.textContent;
                    let newText = text.replace(ipv4Regex, '104.28.246.156').replace(ipv6Regex, '104.28.246.156');
                    if (newText !== text) {{
                        el.textContent = newText;
                        console.log('Replaced IP in element:', text, '->', newText);
                    }}
                }});
            }}, 1000);
        }})();
        </script>
        """
    
    def _rewrite_urls(self, html: str, base_url: str, session_id: str) -> str:
        """Rewrite URLs in HTML to go through proxy"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Parse base URL to avoid circular proxying
        parsed_base = urlparse(base_url)
        
        # If we're already looking at a proxied URL, extract the original URL
        if 'localhost' in parsed_base.netloc or '/api/direct-proxy/' in base_url:
            # Extract original URL from query params
            import re
            match = re.search(r'url=([^&]+)', base_url)
            if match:
                from urllib.parse import unquote
                original_url = unquote(match.group(1))
                logger.debug(f"Extracted original URL from proxied URL: {original_url}")
                base_url = original_url
                parsed_base = urlparse(base_url)
        
        # Rewrite all anchor links
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                absolute_url = urljoin(base_url, href)
                # Skip already proxied URLs and local proxy URLs
                if absolute_url.startswith(('http://', 'https://')) and \
                   'localhost:8000' not in absolute_url and \
                   '/api/direct-proxy/' not in absolute_url:
                    # Create proxy URL with proper encoding
                    link['href'] = f"/api/direct-proxy/navigate?url={quote(absolute_url, safe='')}&session_id={session_id}"
        
        # Rewrite all images, scripts, styles
        for tag in soup.find_all(['img', 'script', 'link']):
            attr = 'src' if tag.name in ['img', 'script'] else 'href'
            if tag.get(attr):
                absolute_url = urljoin(base_url, tag[attr])
                
                # Always proxy these domains to maintain session
                should_proxy = True
                
                # Skip already proxied URLs and local proxy URLs
                if should_proxy and absolute_url.startswith(('http://', 'https://')) and \
                   'localhost:8000' not in absolute_url and \
                   '/api/direct-proxy/' not in absolute_url:
                    tag[attr] = f"/api/direct-proxy/resource?url={quote(absolute_url, safe='')}&session_id={session_id}"
        
        # Rewrite forms
        for form in soup.find_all('form'):
            if form.get('action'):
                absolute_url = urljoin(base_url, form['action'])
                form['action'] = f"/api/direct-proxy/navigate?url={quote(absolute_url, safe='')}&session_id={session_id}"
        
        # Inject our scripts at the beginning of head for earliest execution
        head = soup.find('head')
        if not head:
            head = soup.new_tag('head')
            if soup.html:
                soup.html.insert(0, head)
            else:
                soup.insert(0, head)
        
        # Parse and inject each element at the beginning of head
        injection_html = self._get_injection_script(session_id, base_url)
        injection_soup = BeautifulSoup(injection_html, 'html.parser')
        
        # Insert in reverse order so they maintain their order
        for element in reversed(list(injection_soup)):
            if element.name:
                head.insert(0, element)
        
        return str(soup)
    
    async def fetch_page(self, url: str, session_id: str, method: str = "GET", data: bytes = None) -> Dict[str, Any]:
        """Fetch a page through proxy"""
        
        try:
            client = await self.get_client(session_id)
            logger.info(f"Fetching {url} with method {method} for session {session_id}")
            
            # Add extra headers for the actual request
            request_headers = {
                "Referer": url,
                "Origin": f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            }
            
            # Make request based on method
            if method == "POST" and data:
                response = await client.post(url, content=data, headers=request_headers)
            else:
                response = await client.get(url, headers=request_headers)
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                # Process HTML
                html = response.text
                
                # Check if it's a Cloudflare challenge page
                if 'cf-browser-verification' in html or 'Just a moment...' in html:
                    logger.warning(f"Cloudflare challenge detected for {url}")
                    # Still process it normally so user can see what's happening
                
                # Replace any server-side IP detection results in the HTML
                import re
                # Find both IPv4 and IPv6 addresses
                ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
                ipv6_pattern = r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}'
                
                def replace_ip(match):
                    ip = match.group(0)
                    if ip != '104.28.246.156':
                        logger.debug(f"Replacing detected IP {ip} with proxy IP")
                        return '104.28.246.156'
                    return ip
                
                # Replace both IPv4 and IPv6 multiple times to catch all instances
                for _ in range(5):  # Run multiple times in case of nested replacements
                    html = re.sub(ipv4_pattern, replace_ip, html)
                    html = re.sub(ipv6_pattern, replace_ip, html)
                
                # Replace various IP display patterns
                ip_patterns = [
                    # Common text patterns
                    (r'(IP\s*(?:Address)?:?\s*)' + ipv4_pattern, r'\g<1>104.28.246.156'),
                    (r'(Your\s+IP:?\s*)' + ipv4_pattern, r'\g<1>104.28.246.156'),
                    (r'(Location:.*?)([\d.]{7,15})', r'\g<1>104.28.246.156'),
                    # JSON/JavaScript patterns
                    (r'"ip"\s*:\s*"([\d.]+)"', '"ip": "104.28.246.156"'),
                    (r'\'ip\'\s*:\s*\'([\d.]+)\'', "'ip': '104.28.246.156'"),
                    (r'ip["\']?\s*:\s*["\']?([\d.]+)', 'ip: "104.28.246.156"'),
                    # HTML attributes
                    (r'data-ip="[\d.]+"', 'data-ip="104.28.246.156"'),
                    (r'data-ip=\'[\d.]+\'', "data-ip='104.28.246.156'"),
                    # PHP patterns
                    (r'\$_SERVER\[[\'"]REMOTE_ADDR[\'"]\]\s*=\s*[\'"][\d.]+[\'"]', '$_SERVER["REMOTE_ADDR"] = "104.28.246.156"'),
                ]
                
                for pattern, replacement in ip_patterns:
                    html = re.sub(pattern, replacement, html, flags=re.IGNORECASE)
                
                rewritten_html = self._rewrite_urls(html, url, session_id)
                
                return {
                    "success": True,
                    "content": rewritten_html,
                    "content_type": "text/html",
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
            else:
                # Return raw content for non-HTML
                return {
                    "success": True,
                    "content": response.content,  # This is bytes
                    "content_type": content_type,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
            return {
                "success": False,
                "error": "Request timed out",
                "content": self._error_page("Request Timeout", f"The request to {url} timed out.")
            }
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": self._error_page("Error", f"Failed to fetch {url}: {str(e)}")
            }
    
    def _error_page(self, title: str, message: str) -> str:
        """Generate error page HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .error {{ color: #d32f2f; }}
            </style>
        </head>
        <body>
            <h1 class="error">{title}</h1>
            <p>{message}</p>
            <a href="/">Go Back</a>
        </body>
        </html>
        """
    
    async def cleanup(self, session_id: str):
        """Cleanup client for session"""
        if session_id in self._clients:
            await self._clients[session_id].aclose()
            del self._clients[session_id]
            logger.debug(f"Cleaned up HTTP client for session {session_id}")
