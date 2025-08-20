"""
Content Rewriter Service
Advanced content rewriting for HTML, JavaScript, CSS with tracker handling
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin, quote
import json
import base64
from bs4 import BeautifulSoup, Comment
from loguru import logger


class ContentRewriter:
    """Rewrites web content to work through proxy with geographic spoofing"""
    
    def __init__(self, settings):
        self.settings = settings
        self.tracker_patterns = {
            'ga4': [
                r'gtag\s*\(',
                r'gtm\.js',
                r'google-analytics\.com',
                r'googletagmanager\.com'
            ],
            'adsense': [
                r'googlesyndication\.com',
                r'adsbygoogle',
                r'google_ad_client',
                r'pagead2\.googlesyndication\.com'
            ],
            'facebook': [
                r'facebook\.com/tr',
                r'fbq\s*\(',
                r'facebook-pixel',
                r'connect\.facebook\.net'
            ],
            'hotjar': [
                r'hotjar\.com',
                r'hjid\s*=',
                r'_hjSettings'
            ],
            'mixpanel': [
                r'mixpanel\.com',
                r'mixpanel\.init',
                r'mixpanel\.track'
            ]
        }
    
    async def rewrite_html(
        self,
        html: str,
        base_url: str,
        session_id: str,
        is_mobile: bool = False
    ) -> Dict:
        """Comprehensive HTML rewriting with tracker handling"""
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Inject spoofing script first
        await self._inject_spoofing_script(soup)
        
        # Handle different trackers
        await self._handle_google_analytics(soup)
        await self._handle_adsense(soup)
        await self._handle_facebook_pixel(soup)
        await self._handle_other_trackers(soup)
        
        # Rewrite URLs
        await self._rewrite_all_urls(soup, base_url)
        
        # Add mobile optimizations
        if is_mobile:
            await self._add_mobile_optimizations(soup)
        
        # Extract and categorize resources
        resources = await self._extract_resources(soup)
        
        return {
            'html': str(soup),
            'resources': resources,
            'trackers_found': await self._detect_trackers(soup),
            'injections_added': True
        }
    
    async def _inject_spoofing_script(self, soup: BeautifulSoup):
        """Inject comprehensive spoofing script"""
        
        spoofing_script = f"""
        <!-- Geographic Spoofing & Tracker Handling -->
        <script id="proxy-spoofing-script">
        (function() {{
            'use strict';
            
            // ============= Configuration =============
            const config = {{
                proxy: {{
                    country: '{self.settings.spoof_country_code}',
                    city: '{self.settings.proxy_city}',
                    timezone: '{self.settings.spoof_timezone}',
                    language: '{self.settings.spoof_language}',
                    currency: '{self.settings.spoof_currency}'
                }},
                location: {{
                    latitude: {self.settings.spoof_latitude},
                    longitude: {self.settings.spoof_longitude},
                    accuracy: {self.settings.spoof_accuracy}
                }},
                preserve: {{
                    userAgent: true,
                    deviceMemory: true,
                    hardwareConcurrency: true,
                    platform: true,
                    vendor: true
                }}
            }};
            
            // ============= Geolocation Override =============
            const fakePosition = {{
                coords: {{
                    latitude: config.location.latitude,
                    longitude: config.location.longitude,
                    accuracy: config.location.accuracy,
                    altitude: null,
                    altitudeAccuracy: null,
                    heading: null,
                    speed: null
                }},
                timestamp: Date.now()
            }};
            
            if (navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition = function(success, error, options) {{
                    setTimeout(() => success(fakePosition), 100);
                }};
                
                navigator.geolocation.watchPosition = function(success, error, options) {{
                    const id = setInterval(() => success(fakePosition), 1000);
                    return id;
                }};
            }}
            
            // ============= Language & Locale Override =============
            Object.defineProperty(navigator, 'language', {{
                get: () => config.proxy.language
            }});
            
            Object.defineProperty(navigator, 'languages', {{
                get: () => [config.proxy.language, 'en-US', 'en']
            }});
            
            // ============= Timezone Override =============
            const OriginalDate = Date;
            const OriginalDateTimeFormat = Intl.DateTimeFormat;
            
            // Override Intl.DateTimeFormat
            Intl.DateTimeFormat = new Proxy(OriginalDateTimeFormat, {{
                construct(target, args) {{
                    if (args[1]) {{
                        args[1].timeZone = config.proxy.timezone;
                    }} else {{
                        args[1] = {{ timeZone: config.proxy.timezone }};
                    }}
                    return new target(...args);
                }}
            }});
            
            // Override Date.prototype.getTimezoneOffset
            Date.prototype.getTimezoneOffset = function() {{
                // Calculate offset based on timezone
                const tzOffsets = {{
                    'America/New_York': 300,  // EST
                    'America/Los_Angeles': 480,  // PST
                    'Europe/London': 0,  // GMT
                    'Asia/Tokyo': -540  // JST
                }};
                return tzOffsets[config.proxy.timezone] || 0;
            }};
            
            // ============= GA4/Google Analytics Handler =============
            window.dataLayer = window.dataLayer || [];
            const originalGtag = window.gtag || function() {{ dataLayer.push(arguments); }};
            
            window.gtag = function() {{
                const args = Array.from(arguments);
                
                // Intercept config calls
                if (args[0] === 'config') {{
                    args[2] = args[2] || {{}};
                    args[2].custom_map = args[2].custom_map || {{}};
                    
                    // Add custom dimensions for real location (optional)
                    args[2].custom_map.dimension1 = 'real_country';
                    
                    // Override location data
                    args[2].page_location = window.location.href;
                    args[2].page_referrer = document.referrer;
                    
                    console.log('[GA4] Config intercepted:', args);
                }}
                
                // Forward to original
                return originalGtag.apply(this, args);
            }};
            
            // ============= AdSense Handler =============
            (function() {{
                const originalWrite = document.write;
                const originalWriteln = document.writeln;
                
                // Override document.write for AdSense
                document.write = function(content) {{
                    if (content.includes('googlesyndication.com')) {{
                        console.log('[AdSense] Ad request intercepted');
                        // Modify ad request if needed
                        content = content.replace(/data-ad-client/g, 'data-ad-client');
                    }}
                    return originalWrite.call(this, content);
                }};
                
                document.writeln = function(content) {{
                    if (content.includes('googlesyndication.com')) {{
                        console.log('[AdSense] Ad request intercepted');
                    }}
                    return originalWriteln.call(this, content);
                }};
            }})();
            
            // ============= Facebook Pixel Handler =============
            const originalFbq = window.fbq || function() {{}};
            window.fbq = function() {{
                const args = Array.from(arguments);
                
                if (args[0] === 'track' || args[0] === 'trackCustom') {{
                    // Modify event data
                    if (args[2] && typeof args[2] === 'object') {{
                        args[2]._proxy_country = config.proxy.country;
                        args[2]._proxy_city = config.proxy.city;
                    }}
                    console.log('[FB Pixel] Event tracked:', args);
                }}
                
                // Call original if exists
                if (typeof originalFbq === 'function') {{
                    return originalFbq.apply(this, args);
                }}
            }};
            
            // ============= Network Request Interceptor =============
            (function() {{
                // Intercept Fetch API
                const originalFetch = window.fetch;
                window.fetch = function(url, options = {{}}) {{
                    // Modify headers for geographic spoofing
                    options.headers = options.headers || {{}};
                    options.headers['Accept-Language'] = config.proxy.language;
                    
                    // Log tracker requests
                    const urlString = url.toString();
                    if (urlString.includes('google-analytics') || 
                        urlString.includes('facebook.com/tr') ||
                        urlString.includes('googlesyndication')) {{
                        console.log('[Tracker Request]', urlString);
                    }}
                    
                    return originalFetch.call(this, url, options);
                }};
                
                // Intercept XMLHttpRequest
                const OriginalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {{
                    const xhr = new OriginalXHR();
                    const originalOpen = xhr.open;
                    const originalSetRequestHeader = xhr.setRequestHeader;
                    
                    xhr.open = function(method, url, ...args) {{
                        xhr._url = url;
                        return originalOpen.call(this, method, url, ...args);
                    }};
                    
                    xhr.setRequestHeader = function(header, value) {{
                        // Override language header
                        if (header.toLowerCase() === 'accept-language') {{
                            value = config.proxy.language;
                        }}
                        return originalSetRequestHeader.call(this, header, value);
                    }};
                    
                    return xhr;
                }};
            }})();
            
            // ============= WebRTC Leak Prevention =============
            if (window.RTCPeerConnection) {{
                const pc = window.RTCPeerConnection.prototype;
                const originalCreateOffer = pc.createOffer;
                const originalCreateAnswer = pc.createAnswer;
                
                pc.createOffer = async function(options) {{
                    const offer = await originalCreateOffer.call(this, options);
                    // Remove local IP from SDP
                    offer.sdp = offer.sdp.replace(/a=candidate:.*typ host.*/g, '');
                    offer.sdp = offer.sdp.replace(/a=candidate:.*typ srflx.*/g, '');
                    return offer;
                }};
                
                pc.createAnswer = async function(options) {{
                    const answer = await originalCreateAnswer.call(this, options);
                    // Remove local IP from SDP
                    answer.sdp = answer.sdp.replace(/a=candidate:.*typ host.*/g, '');
                    answer.sdp = answer.sdp.replace(/a=candidate:.*typ srflx.*/g, '');
                    return answer;
                }};
            }}
            
            // ============= Canvas Fingerprinting Protection =============
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            const originalToBlob = HTMLCanvasElement.prototype.toBlob;
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            
            // Add slight noise to canvas operations
            CanvasRenderingContext2D.prototype.getImageData = function() {{
                const imageData = originalGetImageData.apply(this, arguments);
                // Add minimal noise to prevent fingerprinting while preserving functionality
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] = imageData.data[i] ^ 1;
                }}
                return imageData;
            }};
            
            // ============= Battery API Spoofing =============
            if (navigator.getBattery) {{
                navigator.getBattery = async function() {{
                    return {{
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 0.99,
                        addEventListener: () => {{}},
                        removeEventListener: () => {{}}
                    }};
                }};
            }}
            
            // ============= Screen Resolution (Keep Real for Mobile) =============
            // Preserve real screen dimensions for proper mobile rendering
            
            console.log('[Proxy Browser] Spoofing initialized for:', config.proxy.country);
        }})();
        </script>
        """
        
        # Insert at the very beginning of head
        script_tag = BeautifulSoup(spoofing_script, 'html.parser')
        
        if soup.head:
            soup.head.insert(0, script_tag)
        elif soup.body:
            soup.body.insert(0, script_tag)
        else:
            # Create head if doesn't exist
            head = soup.new_tag('head')
            head.insert(0, script_tag)
            if soup.html:
                soup.html.insert(0, head)
    
    async def _handle_google_analytics(self, soup: BeautifulSoup):
        """Handle Google Analytics/GA4 tracking"""
        
        # Find all GA scripts
        ga_scripts = soup.find_all('script', string=re.compile('gtag|google-analytics|googletagmanager'))
        
        for script in ga_scripts:
            if script.string:
                # Wrap GA calls
                wrapped = f"""
                (function() {{
                    // Original GA Script
                    {script.string}
                    
                    // Log GA events for debugging
                    if (window.gtag) {{
                        console.log('[GA4] Initialized with proxy location');
                    }}
                }})();
                """
                script.string = wrapped
    
    async def _handle_adsense(self, soup: BeautifulSoup):
        """Handle Google AdSense"""
        
        # Find AdSense scripts
        adsense_scripts = soup.find_all('script', src=re.compile('googlesyndication'))
        
        for script in adsense_scripts:
            # Add data attributes for tracking
            script['data-proxy-country'] = self.settings.spoof_country_code
            script['data-proxy-handled'] = 'true'
        
        # Find ad slots
        ad_slots = soup.find_all('ins', class_='adsbygoogle')
        for slot in ad_slots:
            slot['data-proxy-country'] = self.settings.spoof_country_code
    
    async def _handle_facebook_pixel(self, soup: BeautifulSoup):
        """Handle Facebook Pixel"""
        
        # Find FB pixel scripts
        fb_scripts = soup.find_all('script', string=re.compile('fbq|facebook\.com/tr'))
        
        for script in fb_scripts:
            if script.string:
                # Wrap FB pixel calls
                wrapped = f"""
                (function() {{
                    // Store original fbq
                    const _fbq = window.fbq;
                    
                    {script.string}
                    
                    // Log FB events
                    if (window.fbq && window.fbq !== _fbq) {{
                        console.log('[FB Pixel] Initialized with proxy location');
                    }}
                }})();
                """
                script.string = wrapped
    
    async def _handle_other_trackers(self, soup: BeautifulSoup):
        """Handle other common trackers (Hotjar, Mixpanel, etc.)"""
        
        # Add handlers for other trackers
        tracker_injection = """
        <script>
        (function() {
            // Hotjar
            if (window.hj) {
                const originalHj = window.hj;
                window.hj = function() {
                    console.log('[Hotjar] Event:', arguments);
                    return originalHj.apply(this, arguments);
                };
            }
            
            // Mixpanel
            if (window.mixpanel) {
                const originalTrack = window.mixpanel.track;
                window.mixpanel.track = function(event, properties) {
                    properties = properties || {};
                    properties.$country = '%s';
                    properties.$city = '%s';
                    console.log('[Mixpanel] Track:', event, properties);
                    return originalTrack.call(this, event, properties);
                };
            }
        })();
        </script>
        """ % (self.settings.spoof_country_code, self.settings.proxy_city)
        
        if soup.body:
            tracker_script = BeautifulSoup(tracker_injection, 'html.parser')
            soup.body.append(tracker_script)
    
    async def _rewrite_all_urls(self, soup: BeautifulSoup, base_url: str):
        """Rewrite all URLs to go through proxy"""
        
        # Parse base URL
        base_parsed = urlparse(base_url)
        
        # Define URL attributes to rewrite
        url_attrs = {
            'a': ['href'],
            'link': ['href'],
            'script': ['src'],
            'img': ['src', 'srcset'],
            'iframe': ['src'],
            'form': ['action'],
            'video': ['src', 'poster'],
            'audio': ['src'],
            'source': ['src', 'srcset'],
            'embed': ['src'],
            'object': ['data']
        }
        
        for tag_name, attrs in url_attrs.items():
            for tag in soup.find_all(tag_name):
                for attr in attrs:
                    if tag.get(attr):
                        if attr == 'srcset':
                            # Handle srcset specially
                            tag[attr] = self._rewrite_srcset(tag[attr], base_url)
                        else:
                            tag[attr] = self._create_proxy_url(tag[attr], base_url)
        
        # Rewrite inline styles
        for tag in soup.find_all(style=True):
            tag['style'] = self._rewrite_css_urls(tag['style'], base_url)
        
        # Rewrite style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                style_tag.string = self._rewrite_css_urls(style_tag.string, base_url)
    
    def _create_proxy_url(self, url: str, base_url: str) -> str:
        """Create proxy URL from original URL"""
        
        if not url or url.startswith('data:') or url.startswith('javascript:') or url.startswith('#'):
            return url
        
        # Make absolute URL
        absolute_url = urljoin(base_url, url)
        
        # Encode and create proxy URL
        encoded = base64.b64encode(absolute_url.encode()).decode()
        return f"/proxy?url={encoded}"
    
    def _rewrite_srcset(self, srcset: str, base_url: str) -> str:
        """Rewrite srcset attribute"""
        
        parts = []
        for part in srcset.split(','):
            part = part.strip()
            if ' ' in part:
                url, descriptor = part.rsplit(' ', 1)
                url = self._create_proxy_url(url, base_url)
                parts.append(f"{url} {descriptor}")
            else:
                parts.append(self._create_proxy_url(part, base_url))
        
        return ', '.join(parts)
    
    def _rewrite_css_urls(self, css: str, base_url: str) -> str:
        """Rewrite URLs in CSS"""
        
        def replace_url(match):
            url = match.group(1).strip('\'"')
            proxy_url = self._create_proxy_url(url, base_url)
            return f'url("{proxy_url}")'
        
        # Replace url() declarations
        css = re.sub(r'url\((.*?)\)', replace_url, css)
        
        # Replace @import statements
        def replace_import(match):
            url = match.group(1).strip('\'"')
            proxy_url = self._create_proxy_url(url, base_url)
            return f'@import "{proxy_url}"'
        
        css = re.sub(r'@import\s+["\']([^"\']+)["\']', replace_import, css)
        css = re.sub(r'@import\s+url\((.*?)\)', replace_import, css)
        
        return css
    
    async def _add_mobile_optimizations(self, soup: BeautifulSoup):
        """Add mobile-specific optimizations"""
        
        # Add viewport meta tag
        if soup.head:
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            if not viewport:
                viewport = soup.new_tag('meta')
                viewport['name'] = 'viewport'
                viewport['content'] = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
                soup.head.insert(0, viewport)
        
        # Add mobile CSS
        mobile_css = """
        <style>
        /* Mobile Optimizations */
        * {
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
        }
        
        body {
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
            touch-action: manipulation;
        }
        
        input, textarea, select {
            font-size: 16px; /* Prevent zoom on iOS */
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
            -webkit-overflow-scrolling: touch;
        }
        </style>
        """
        
        if soup.head:
            style_tag = BeautifulSoup(mobile_css, 'html.parser')
            soup.head.append(style_tag)
        
        # Add touch event handlers
        touch_script = """
        <script>
        // Mobile touch optimization
        document.addEventListener('DOMContentLoaded', function() {
            // Fast click implementation
            let touchStartTime;
            let touchStartX, touchStartY;
            
            document.addEventListener('touchstart', function(e) {
                touchStartTime = Date.now();
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            }, {passive: true});
            
            document.addEventListener('touchend', function(e) {
                const touchEndTime = Date.now();
                const touchEndX = e.changedTouches[0].clientX;
                const touchEndY = e.changedTouches[0].clientY;
                
                // Check if it's a tap (not a swipe)
                const distance = Math.sqrt(
                    Math.pow(touchEndX - touchStartX, 2) + 
                    Math.pow(touchEndY - touchStartY, 2)
                );
                
                if (distance < 10 && (touchEndTime - touchStartTime) < 300) {
                    // It's a tap, trigger click immediately
                    const clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: touchEndX,
                        clientY: touchEndY
                    });
                    e.target.dispatchEvent(clickEvent);
                }
            }, {passive: true});
            
            // Prevent double-tap zoom
            let lastTouchEnd = 0;
            document.addEventListener('touchend', function(e) {
                const now = Date.now();
                if (now - lastTouchEnd <= 300) {
                    e.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
        });
        </script>
        """
        
        if soup.body:
            script_tag = BeautifulSoup(touch_script, 'html.parser')
            soup.body.append(script_tag)
    
    async def _extract_resources(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract and categorize resources from HTML"""
        
        resources = {
            'scripts': [],
            'styles': [],
            'images': [],
            'fonts': [],
            'media': []
        }
        
        # Extract scripts
        for script in soup.find_all('script', src=True):
            resources['scripts'].append(script['src'])
        
        # Extract stylesheets
        for link in soup.find_all('link', rel='stylesheet'):
            if link.get('href'):
                resources['styles'].append(link['href'])
        
        # Extract images
        for img in soup.find_all('img', src=True):
            resources['images'].append(img['src'])
        
        # Extract fonts
        for link in soup.find_all('link', rel='preload'):
            if link.get('as') == 'font':
                resources['fonts'].append(link['href'])
        
        # Extract media
        for tag in soup.find_all(['video', 'audio']):
            if tag.get('src'):
                resources['media'].append(tag['src'])
            for source in tag.find_all('source', src=True):
                resources['media'].append(source['src'])
        
        return resources
    
    async def _detect_trackers(self, soup: BeautifulSoup) -> Dict[str, bool]:
        """Detect presence of various trackers"""
        
        detected = {}
        html_str = str(soup)
        
        for tracker_name, patterns in self.tracker_patterns.items():
            detected[tracker_name] = any(
                re.search(pattern, html_str, re.IGNORECASE)
                for pattern in patterns
            )
        
        return detected
    
    async def rewrite_javascript(self, js: str, base_url: str) -> str:
        """Rewrite JavaScript content"""
        
        # Wrap in IIFE to prevent global pollution
        wrapped = f"""
        (function() {{
            'use strict';
            
            // Proxy configuration
            const PROXY_BASE = '/proxy';
            const ORIGINAL_DOMAIN = '{urlparse(base_url).netloc}';
            
            // Override fetch to use proxy
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {{
                if (typeof url === 'string' && !url.startsWith(PROXY_BASE)) {{
                    const absoluteUrl = new URL(url, '{base_url}').href;
                    url = PROXY_BASE + '?url=' + btoa(absoluteUrl);
                }}
                return originalFetch.call(this, url, options);
            }};
            
            // Override XMLHttpRequest
            const OriginalXHR = window.XMLHttpRequest;
            window.XMLHttpRequest = function() {{
                const xhr = new OriginalXHR();
                const originalOpen = xhr.open;
                
                xhr.open = function(method, url, ...args) {{
                    if (typeof url === 'string' && !url.startsWith(PROXY_BASE)) {{
                        const absoluteUrl = new URL(url, '{base_url}').href;
                        url = PROXY_BASE + '?url=' + btoa(absoluteUrl);
                    }}
                    return originalOpen.call(this, method, url, ...args);
                }};
                
                return xhr;
            }};
            
            // Original JavaScript
            {js}
        }})();
        """
        
        return wrapped
    
    async def rewrite_css(self, css: str, base_url: str) -> str:
        """Rewrite CSS content"""
        
        return self._rewrite_css_urls(css, base_url)
