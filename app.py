import os
import sys
import re
import json
import base64
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
import asyncio
import brotli

app = FastAPI(title="Proxy Browser V2 - CroxyProxy Style")

# Proxy configuration
PROXY_CONFIG = {
    "server": os.environ.get("PROXY_SERVER", "pg.proxi.es:20000"),
    "username": os.environ.get("PROXY_USERNAME", "KMwYgm4pR4upF6yX-s-session123-co-US-st-NY-ci-NewYork"),  # Force US location
    "password": os.environ.get("PROXY_PASSWORD", "pMBwu34BjjGr5urD"),
    "country": os.environ.get("PROXY_COUNTRY", "USA"),
    "timezone": os.environ.get("SPOOF_TIMEZONE", "America/New_York"),
    "language": os.environ.get("SPOOF_LANGUAGE", "en-US"),
    "target_url": os.environ.get("DEFAULT_TARGET_URL", "https://ybsq.xyz/")
}

# Global variable to store actual proxy IP
CURRENT_PROXY_IP = None

def get_proxy_url():
    return f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['server']}"

async def get_actual_proxy_ip():
    """Get the actual IP address from our proxy"""
    global CURRENT_PROXY_IP
    
    if CURRENT_PROXY_IP:
        return CURRENT_PROXY_IP
    
    try:
        proxy_url = get_proxy_url()
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=10.0,
            verify=False
        ) as client:
            # Get IP from httpbin
            response = await client.get("https://httpbin.org/ip")
            if response.status_code == 200:
                ip_data = response.json()
                CURRENT_PROXY_IP = ip_data.get("origin", "").split(",")[0].strip()
                print(f"🌐 PROXY: Detected actual proxy IP: {CURRENT_PROXY_IP}")
                return CURRENT_PROXY_IP
    except Exception as e:
        print(f"❌ Failed to get proxy IP: {e}")
    
    # Fallback IP
    CURRENT_PROXY_IP = "8.8.8.8"
    return CURRENT_PROXY_IP

async def get_spoofed_headers(original_request: Request, target_url: str):
    """Get headers with US location spoofing while preserving original User-Agent"""
    headers = {}
    
    # Get actual proxy IP dynamically
    proxy_ip = await get_actual_proxy_ip()
    
    # Preserve original headers but modify location-related ones
    for name, value in original_request.headers.items():
        if name.lower() not in ['host', 'connection', 'content-length', 'transfer-encoding']:
            headers[name] = value
    
    # Override location-related headers with US data using dynamic proxy IP
    headers.update({
        "Accept-Language": "en-US,en;q=0.9",
        "X-Forwarded-For": proxy_ip,
        "CF-IPCountry": "US", 
        "CF-Region": "NY",
        "CF-City": "New York",
        "X-Real-IP": proxy_ip,
        "X-Forwarded-Proto": "https",
        "X-Appengine-Country": "US",
        "X-Appengine-Region": "ny", 
        "X-Appengine-City": "newyork",
        "X-Appengine-User-IP": proxy_ip,
        "X-Client-IP": proxy_ip,
        "X-Cluster-Client-IP": proxy_ip,
        "X-Original-Forwarded-For": proxy_ip,
        "True-Client-IP": proxy_ip,
        "X-Remote-IP": proxy_ip,
        "X-Remote-Addr": proxy_ip,
        "Remote-Addr": proxy_ip,
        "HTTP_X_FORWARDED_FOR": proxy_ip,
        "HTTP_CLIENT_IP": proxy_ip,
        "HTTP_X_REAL_IP": proxy_ip,
        "Forwarded": f"for={proxy_ip};proto=https;host={urlparse(target_url).netloc}",
        "X-Forwarded-Host": urlparse(target_url).netloc,
        "X-Original-Host": urlparse(target_url).netloc,
        "Host": urlparse(target_url).netloc,
        "X-ISP": "DigitalOcean, LLC",
        "X-ASN": "AS14061",
        "X-Organization": "DigitalOcean, LLC",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    })
    
    return headers

def rewrite_html_content(content: str, base_url: str, proxy_base: str, proxy_ip: str = "8.8.8.8"):
    """Rewrite HTML content like CroxyProxy"""
    
    # Parse base URL
    parsed_base = urlparse(base_url)
    domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    # CroxyProxy-style URL rewriting (same domain approach)
    import base64
    
    # Rewrite absolute URLs with Base64 encoding
    def encode_url(match):
        attr, quote, url = match.groups()
        if url.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            return match.group(0)
        
        # Encode URL like CroxyProxy
        if url.startswith('http'):
            encoded = base64.b64encode(url.encode()).decode()
            return f'{attr}={quote}/?url={encoded}{quote}'
        return match.group(0)
    
    content = re.sub(
        r'(href|src|action)=(["\'])(https?://[^"\']+)\2',
        encode_url,
        content
    )
    
    # Rewrite protocol-relative URLs
    content = re.sub(
        r'(href|src|action)=(["\'])//([^"\']+)\2',
        lambda m: f'{m.group(1)}={m.group(2)}/?url={base64.b64encode(f"https://{m.group(3)}".encode()).decode()}{m.group(2)}',
        content
    )
    
    # Rewrite relative URLs to stay on same domain
    content = re.sub(
        r'(href|src|action)=(["\'])(?!http|//|#|mailto:|tel:|javascript:|/\?)([^"\']+)\2',
        lambda m: f'{m.group(1)}={m.group(2)}/?url={base64.b64encode(f"{domain}/{m.group(3)}".encode()).decode()}{m.group(2)}',
        content
    )
    
    # Add comprehensive spoofing script
    spoof_script = f"""
    <script>
    // CroxyProxy-style spoofing
    console.log('🇺🇸 CROXYPROXY: Initializing location spoofing...');
    
    // Block WebRTC completely to prevent IP leaks
    console.log('🇺🇸 CROXYPROXY: Disabling WebRTC completely');
    
    // Disable RTCPeerConnection
    delete window.RTCPeerConnection;
    delete window.webkitRTCPeerConnection;
    delete window.mozRTCPeerConnection;
    
    // Override with null functions
    window.RTCPeerConnection = function() {{
        console.log('🚫 WEBRTC: Blocked RTCPeerConnection creation');
        throw new Error('WebRTC is disabled for privacy');
    }};
    
    window.webkitRTCPeerConnection = window.RTCPeerConnection;
    window.mozRTCPeerConnection = window.RTCPeerConnection;
    
    // Block getUserMedia as well
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {{
        navigator.mediaDevices.getUserMedia = function() {{
            console.log('🚫 WEBRTC: Blocked getUserMedia');
            return Promise.reject(new Error('getUserMedia is disabled for privacy'));
        }};
    }}
    
    if (navigator.getUserMedia) {{
        navigator.getUserMedia = function() {{
            console.log('🚫 WEBRTC: Blocked getUserMedia (legacy)');
        }};
    }}
    
    // Override geolocation
    if (navigator.geolocation) {{
        const fakePosition = {{
            coords: {{
                latitude: 40.7128,
                longitude: -74.0060,
                accuracy: 10,
                altitude: null,
                altitudeAccuracy: null,
                heading: null,
                speed: null
            }},
            timestamp: Date.now()
        }};
        
        navigator.geolocation.getCurrentPosition = function(success, error, options) {{
            console.log('🇺🇸 CROXYPROXY: Spoofing getCurrentPosition');
            if (success) setTimeout(() => success(fakePosition), 100);
        }};
        
        navigator.geolocation.watchPosition = function(success, error, options) {{
            console.log('🇺🇸 CROXYPROXY: Spoofing watchPosition');
            if (success) setTimeout(() => success(fakePosition), 100);
            return 1;
        }};
    }}
    
    // Override timezone (comprehensive)
    Date.prototype.getTimezoneOffset = function() {{
        console.log('🇺🇸 CROXYPROXY: Spoofing timezone offset');
        return 300; // EST (-5 UTC)
    }};
    
    // Override Date toString to show EST
    const originalToString = Date.prototype.toString;
    Date.prototype.toString = function() {{
        const date = originalToString.call(this);
        return date.replace(/GMT[+-]\\d{{4}}.*$/, 'GMT-0500 (Eastern Standard Time)');
    }};
    
    // Override Intl DateTimeFormat
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(locale, options) {{
        console.log('🇺🇸 CROXYPROXY: Spoofing DateTimeFormat');
        return new originalDateTimeFormat('en-US', {{...options, timeZone: 'America/New_York'}});
    }};
    
    // Override Intl.DateTimeFormat.prototype.resolvedOptions
    const originalResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
    Intl.DateTimeFormat.prototype.resolvedOptions = function() {{
        const options = originalResolvedOptions.call(this);
        options.timeZone = 'America/New_York';
        options.locale = 'en-US';
        return options;
    }};
    
    // Override timezone detection methods
    if (window.Intl && window.Intl.DateTimeFormat) {{
        Object.defineProperty(window.Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
            value: function() {{
                return {{
                    locale: 'en-US',
                    timeZone: 'America/New_York',
                    calendar: 'gregory',
                    numberingSystem: 'latn'
                }};
            }}
        }});
    }}
    
    // Override navigator properties
    Object.defineProperty(navigator, 'language', {{
        get: () => 'en-US',
        configurable: true
    }});
    
    Object.defineProperty(navigator, 'languages', {{
        get: () => ['en-US', 'en'],
        configurable: true
    }});
    
    // Override fetch for IP detection and analytics
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {{}}) {{
        const urlStr = url.toString();
        
        // Block ALL IP detection APIs and return fake US data
        if (urlStr.includes('ipapi') || urlStr.includes('ipify') || urlStr.includes('ipinfo') || 
            urlStr.includes('ip-api') || urlStr.includes('whatismyip') || urlStr.includes('myip') ||
            urlStr.includes('ipgeolocation') || urlStr.includes('geoip') || urlStr.includes('ip2location') ||
            urlStr.includes('maxmind') || urlStr.includes('iplocation') || urlStr.includes('getip') ||
            urlStr.includes('checkip') || urlStr.includes('showip') || urlStr.includes('findip')) {{
            console.log('🇺🇸 CROXYPROXY: Blocking IP detection API:', urlStr);
            return Promise.resolve(new Response(JSON.stringify({{
                ip: "{proxy_ip}",
                country: "United States",
                country_code: "US",
                country_name: "United States", 
                region: "NY",
                region_name: "New York",
                region_code: "NY",
                city: "New York",
                zip: "10001",
                postal: "10001",
                lat: 40.7128,
                lon: -74.0060,
                latitude: 40.7128,
                longitude: -74.0060,
                timezone: "America/New_York",
                utc_offset: "-05:00",
                country_calling_code: "+1",
                currency: "USD",
                languages: "en-US,en",
                isp: "DigitalOcean, LLC",
                org: "DigitalOcean, LLC",
                as: "AS14061 DigitalOcean, LLC",
                asname: "DIGITALOCEAN-ASN",
                query: "{proxy_ip}"
            }}), {{
                headers: {{ 'Content-Type': 'application/json' }}
            }}));
        }}
        
        // Redirect GA4 collect requests to our custom endpoint
        if (urlStr.includes('google-analytics.com/g/collect') || 
            urlStr.includes('google-analytics.com/collect')) {{
            console.log('🎯 GA4: Redirecting collect to custom endpoint');
            const newUrl = window.location.origin + '/g/collect?' + urlStr.split('?')[1];
            return originalFetch.call(this, newUrl, options);
        }}
        
        // Add US headers to all other analytics requests
        if (urlStr.includes('google') || urlStr.includes('analytics') || urlStr.includes('adsense')) {{
            console.log('🇺🇸 CROXYPROXY: Adding US headers to analytics');
            options.headers = {{
                ...options.headers,
                'CF-IPCountry': 'US',
                'X-Forwarded-For': '{proxy_ip}',
                'Accept-Language': 'en-US,en;q=0.9'
            }};
        }}
        
        return originalFetch.call(this, url, options);
    }};
    
    // Override XMLHttpRequest for IP detection
    const originalXHROpen = XMLHttpRequest.prototype.open;
    const originalXHRSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url, ...args) {{
        this._url = url;
        return originalXHROpen.call(this, method, url, ...args);
    }};
    
    XMLHttpRequest.prototype.send = function(data) {{
        if (this._url && (this._url.includes('ipapi') || this._url.includes('ipify') || 
            this._url.includes('ipinfo') || this._url.includes('whatismyip') || 
            this._url.includes('geoip') || this._url.includes('iplocation'))) {{
            console.log('🇺🇸 CROXYPROXY: Blocking XHR IP detection:', this._url);
            
            // Simulate successful response with fake data
            setTimeout(() => {{
                if (this.onreadystatechange) {{
                    Object.defineProperty(this, 'readyState', {{ value: 4, writable: false }});
                    Object.defineProperty(this, 'status', {{ value: 200, writable: false }});
                    Object.defineProperty(this, 'responseText', {{ 
                        value: JSON.stringify({{
                            ip: "{proxy_ip}",
                            country: "United States",
                            country_code: "US",
                            city: "New York",
                            region: "NY",
                            lat: 40.7128,
                            lon: -74.0060,
                            timezone: "America/New_York",
                            isp: "DigitalOcean, LLC",
                            org: "DigitalOcean, LLC"
                        }}),
                        writable: false 
                    }});
                    this.onreadystatechange();
                }}
            }}, 100);
            return;
        }}
        
        return originalXHRSend.call(this, data);
    }};
    
    // Text replacement
    function replaceLocationText() {{
        const walker = document.createTreeWalker(
            document.body || document.documentElement,
            NodeFilter.SHOW_TEXT
        );
        
        let node;
        while (node = walker.nextNode()) {{
            if (node.textContent) {{
                let text = node.textContent;
                let changed = false;
                
                if (text.includes('India')) {{
                    text = text.replace(/India/g, 'United States');
                    changed = true;
                }}
                if (text.includes('Bhubaneswar')) {{
                    text = text.replace(/Bhubaneswar/g, 'New York');
                    changed = true;
                }}
                if (text.includes('Asia/Calcutta')) {{
                    text = text.replace(/Asia\/Calcutta/g, 'America/New_York');
                    changed = true;
                }}
                
                if (changed) {{
                    node.textContent = text;
                    console.log('🇺🇸 CROXYPROXY: Replaced location text');
                }}
            }}
        }}
    }}
    
    // Run replacements
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', replaceLocationText);
    }} else {{
        replaceLocationText();
    }}
    
    // Monitor for changes
    if (window.MutationObserver) {{
        new MutationObserver(() => setTimeout(replaceLocationText, 100))
            .observe(document.body || document.documentElement, {{
                childList: true,
                subtree: true,
                characterData: true
            }});
    }}
    
    // Override common global variables used for IP detection with dynamic IP
    window.userIP = "{proxy_ip}";
    window.userCountry = "United States";
    window.userCity = "New York";
    window.userRegion = "NY";
    window.userTimezone = "America/New_York";
    window.userLatitude = 40.7128;
    window.userLongitude = -74.0060;
    window.userISP = "DigitalOcean, LLC";
    window.userOrg = "DigitalOcean, LLC";
    window.userASN = "AS14061";
    window.userHosting = true;
    window.userProxy = false;
    window.userVPN = false;
    window.userTor = false;
    
    // Override any existing IP detection functions
    if (window.getIP) window.getIP = () => "{proxy_ip}";
    if (window.getUserIP) window.getUserIP = () => "{proxy_ip}";
    if (window.getLocation) window.getLocation = () => "New York, United States";
    if (window.getCountry) window.getCountry = () => "United States";
    
    // Override Google Analytics gtag function
    if (window.gtag) {{
        const originalGtag = window.gtag;
        window.gtag = function(command, target, config) {{
            if (config && typeof config === 'object') {{
                // Force US location data in GA4 config
                config.country = 'US';
                config.region = 'NY';
                config.city = 'New York';
                config.custom_map = {{
                    ...config.custom_map,
                    country: 'US',
                    region: 'NY',
                    city: 'New York'
                }};
                console.log('🇺🇸 CROXYPROXY: Modified GA4 config with US location');
            }}
            return originalGtag.call(this, command, target, config);
        }};
    }}
    
    // Override gtag before it loads
    window.gtag = window.gtag || function() {{
        (window.gtag.q = window.gtag.q || []).push(arguments);
    }};
    
    // Intercept gtag calls and add US data
    const originalGtagQ = window.gtag.q || [];
    window.gtag.q = new Proxy(originalGtagQ, {{
        set: function(target, property, value) {{
            if (Array.isArray(value) && value[0] === 'config') {{
                console.log('🇺🇸 CROXYPROXY: Intercepting GA4 config');
                value[2] = value[2] || {{}};
                value[2].country = 'US';
                value[2].region = 'NY';
                value[2].city = 'New York';
            }}
            target[property] = value;
            return true;
        }}
    }});
    
    console.log('🇺🇸 CROXYPROXY: Location spoofing initialized');
    </script>
    """
    
    # Replace proxy_ip placeholder in the script
    spoof_script = spoof_script.replace('{proxy_ip}', proxy_ip)
    
    # Inject script and meta tags
    meta_viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
    
    if '<head>' in content:
        content = content.replace('<head>', f'<head>{meta_viewport}{spoof_script}')
    elif '<html>' in content:
        content = content.replace('<html>', f'<html><head>{meta_viewport}{spoof_script}</head>')
    else:
        content = f'<html><head>{meta_viewport}{spoof_script}</head><body>{content}</body></html>'
    
    # Don't add status indicator (user requested removal)
    
    return content

@app.get("/")
async def root(url: str = None):
    """CroxyProxy-style root with Base64 encoded URL"""
    if url:
        # Decode Base64 URL like CroxyProxy
        try:
            import base64
            decoded_url = base64.b64decode(url).decode('utf-8')
            return RedirectResponse(url=f"/proxy/{decoded_url}")
        except:
            pass
    
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proxy Browser V2</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 500px;
                width: 100%;
            }
            h1 { color: #333; margin-bottom: 10px; }
            p { color: #666; margin-bottom: 30px; }
            .btn {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 16px;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .btn:hover { transform: translateY(-2px); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌐 Proxy Browser V2</h1>
            <p>Browse with US IP address and location</p>
            <button class="btn" onclick="window.location.href='/?url=aHR0cHM6Ly9leGFtcGxlLmNvbQ=='">
                Test Example.com
            </button>
            <br><br>
            <button class="btn" onclick="window.location.href='/?url=aHR0cHM6Ly9odHRwYmluLm9yZy9pcA=='">
                Test IP Detection
            </button>
            <br><br>
            <button class="btn" onclick="window.location.href='/?url=aHR0cHM6Ly95YnNxLnh5eg=='">
                Your Site (ybsq.xyz)
            </button>
        </div>
    </body>
    </html>
    """)

@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "proxy-browser-v2"}

@app.get("/api_v1/{path:path}")
async def handle_whoer_api(path: str, request: Request):
    """Handle whoer.com API requests with fake US data"""
    proxy_ip = await get_actual_proxy_ip()
    print(f"🛡️ WHOER API: {path} - Returning US data with IP: {proxy_ip}")
    
    # Return fake US data for all whoer.com API calls
    return {
        "success": True,
        "ip": proxy_ip,
        "country": "United States",
        "country_code": "US",
        "region": "NY",
        "city": "New York",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York",
        "isp": "DigitalOcean, LLC",
        "organization": "DigitalOcean, LLC",
        "as": "AS14061 DigitalOcean, LLC",
        "asname": "DIGITALOCEAN-ASN",
        "mobile": False,
        "proxy": False,
        "hosting": True,
        "fraud_score": 0,
        "risk_level": "low",
        "vpn": False,
        "tor": False,
        "anonymizer": False,
        "source": "datacenter",
        "dns": ["8.8.8.8", "8.8.4.4"]
    }

@app.get("/images/{path:path}")
async def handle_images(path: str):
    """Handle missing image requests"""
    # Return 1x1 transparent pixel
    return Response(
        content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
        media_type="image/png"
    )

@app.get("/fonts/{path:path}")
async def handle_fonts(path: str):
    """Handle missing font requests"""
    return Response(content="", media_type="font/woff2")

@app.get("/_ipx/{path:path}")
async def handle_ipx(path: str):
    """Handle missing _ipx requests"""
    return Response(
        content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82',
        media_type="image/png"
    )

@app.get("/g/collect")
@app.post("/g/collect")
async def ga4_collect_override(request: Request):
    """Override GA4 collect endpoint to force US location"""
    proxy_ip = await get_actual_proxy_ip()
    print(f"🎯 GA4 COLLECT: Intercepting with proxy IP {proxy_ip}")
    
    # Get original parameters
    params = dict(request.query_params)
    
    # Force US location in GA4 parameters
    params.update({
        'uip': proxy_ip,  # User IP override
        'geoid': '21167',  # New York geo ID
        'ul': 'en-us',     # User language
        'cn': 'United States',  # Country name
        'cs': 'DigitalOcean',   # Campaign source (ISP)
        'cm': 'organic',        # Campaign medium
        'dr': f'https://{request.headers.get("host", "scrap.ybsq.xyz")}',  # Document referrer
    })
    
    # Forward to real GA4 through proxy with US IP
    try:
        proxy_url = get_proxy_url()
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=10.0,
            verify=False
        ) as client:
            # Forward to real GA4 collect endpoint
            ga4_url = "https://www.google-analytics.com/g/collect"
            
            # Add US headers
            headers = {
                "User-Agent": request.headers.get("User-Agent", ""),
                "CF-IPCountry": "US",
                "X-Forwarded-For": proxy_ip,
                "X-Real-IP": proxy_ip,
                "Accept-Language": "en-US,en;q=0.9",
                "X-Appengine-Country": "US",
                "X-Appengine-Region": "ny",
                "X-Appengine-City": "newyork"
            }
            
            # Send to GA4 through proxy
            if request.method == "GET":
                response = await client.get(ga4_url, params=params, headers=headers)
            else:
                response = await client.post(ga4_url, params=params, headers=headers)
            
            print(f"🎯 GA4: Forwarded to real GA4 - Status: {response.status_code}")
            
            return Response(
                content=response.content,
                media_type="image/gif",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
    except Exception as e:
        print(f"❌ GA4 forward error: {e}")
        
    # Fallback success pixel
    return Response(
        content=b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00;',
        media_type="image/gif",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/proxy/{path:path}")
async def proxy_page(path: str, request: Request):
    try:
        # Decode URL
        path = unquote(path)
        
        # Ensure proper URL format
        if not path.startswith(('http://', 'https://')):
            path = 'https://' + path
        
        print(f"🌐 PROXY: Fetching {path}")
        
        # Get spoofed headers with dynamic proxy IP
        headers = await get_spoofed_headers(request, path)
        
        # Create proxy client
        proxy_url = get_proxy_url()
        
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=30.0,
            verify=False,
            follow_redirects=True
        ) as client:
            response = await client.get(path, headers=headers)
            
            # Handle Brotli compression properly
            content_encoding = response.headers.get('content-encoding', '')
            if 'br' in content_encoding:
                print("🔧 Brotli compression detected, decompressing...")
                try:
                    # Decompress Brotli content
                    decompressed_content = brotli.decompress(response.content)
                    # Create a new response with decompressed content
                    response._content = decompressed_content
                    response.headers['content-encoding'] = 'identity'
                    print("✅ Brotli decompression successful")
                except Exception as e:
                    print(f"❌ Brotli decompression failed: {e}")
                    # Fallback: retry without Brotli
                    headers["Accept-Encoding"] = "gzip, deflate"
                    headers["Cache-Control"] = "no-cache, no-store"
                    response = await client.get(path, headers=headers)
                    print("🔄 Retried without Brotli")
            
            print(f"📊 Status: {response.status_code} | Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            content_type = response.headers.get('content-type', '').lower()
            
            # Handle different content types properly
            if 'text/html' in content_type:
                # HTML content - process and rewrite
                try:
                    html_content = response.text
                    
                    # Check if content is garbled (Brotli issue)
                    if len([c for c in html_content[:200] if ord(c) > 127]) > 100:
                        print("❌ Content appears garbled, likely compression issue")
                        return HTMLResponse(f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Content Error</title>
                            <style>
                                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                                .error {{ background: #f8d7da; color: #721c24; padding: 20px; border-radius: 8px; }}
                            </style>
                        </head>
                        <body>
                            <h1>🌐 Proxy Browser V2</h1>
                            <div class="error">
                                <h3>Content Encoding Error</h3>
                                <p>The website returned compressed content that couldn't be decoded.</p>
                                <p><strong>URL:</strong> {path}</p>
                                <p>Try refreshing or use a different site.</p>
                            </div>
                            <button onclick="window.location.href='/'">🏠 Home</button>
                        </body>
                        </html>
                        """)
                    
                    # Server-side IP replacement (aggressive) with dynamic proxy IP
                    current_proxy_ip = await get_actual_proxy_ip()
                    print(f"🔧 Performing server-side IP replacement with {current_proxy_ip}...")
                    
                    # Replace various IP patterns
                    html_content = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', current_proxy_ip, html_content)
                    html_content = re.sub(r'\b[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){7}\b', current_proxy_ip, html_content)  # IPv6
                    
                    # Location replacement
                    html_content = re.sub(r'\bIndia\b', 'United States', html_content)
                    html_content = re.sub(r'\bBhubaneswar\b', 'New York', html_content)
                    html_content = re.sub(r'\bOdisha\b', 'New York', html_content)
                    html_content = re.sub(r'\bKhordha\b', 'New York', html_content)
                    html_content = re.sub(r'\bAsia/Calcutta\b', 'America/New_York', html_content)
                    html_content = re.sub(r'\ben-GB\b', 'en-US', html_content)
                    
                    # ISP replacement
                    html_content = re.sub(r'\bBharti Airtel\b', 'DigitalOcean LLC', html_content)
                    html_content = re.sub(r'\bBharti Airtel Limited\b', 'DigitalOcean, LLC', html_content)
                    html_content = re.sub(r'\bAS45609\b', 'AS14061', html_content)
                    
                    # Add JavaScript to override any remaining detection
                    isp_override = f'''
                    <script>
                    // Override ISP detection
                    Object.defineProperty(window, 'userISP', {{value: 'DigitalOcean, LLC', writable: false}});
                    Object.defineProperty(window, 'userOrganization', {{value: 'DigitalOcean, LLC', writable: false}});
                    Object.defineProperty(window, 'userASN', {{value: 'AS14061', writable: false}});
                    Object.defineProperty(window, 'userCountryCode', {{value: 'US', writable: false}});
                    Object.defineProperty(window, 'userRegionCode', {{value: 'NY', writable: false}});
                    
                    // Override any ISP detection functions
                    if (window.getISP) window.getISP = () => 'DigitalOcean, LLC';
                    if (window.getOrganization) window.getOrganization = () => 'DigitalOcean, LLC';
                    if (window.getASN) window.getASN = () => 'AS14061';
                    
                    console.log('🇺🇸 ISP: Forced DigitalOcean ISP data');
                    </script>
                    '''
                    
                    # Inject ISP override early
                    if '<head>' in html_content:
                        html_content = html_content.replace('<head>', f'<head>{isp_override}')
                    
                    # Inject AdSense domain fix
                    adsense_fix = f'''
                    <script>
                    // Complete Domain Spoofing - Make everything think we're on ybsq.xyz
                    const originalDomain = 'ybsq.xyz';
                    const originalOrigin = 'https://ybsq.xyz';
                    
                    // Override document properties
                    Object.defineProperty(document, 'domain', {{
                        get: function() {{ 
                            console.log('📢 ADSENSE: Spoofed document.domain to ybsq.xyz');
                            return originalDomain; 
                        }},
                        set: function() {{ /* ignore */ }}
                    }});
                    
                    Object.defineProperty(document, 'URL', {{
                        get: function() {{ 
                            return originalOrigin + window.location.pathname.replace('/proxy/https://ybsq.xyz', '');
                        }}
                    }});
                    
                    Object.defineProperty(document, 'documentURI', {{
                        get: function() {{ 
                            return originalOrigin + window.location.pathname.replace('/proxy/https://ybsq.xyz', '');
                        }}
                    }});
                    
                    // Override window.location properties
                    Object.defineProperty(window.location, 'hostname', {{
                        get: function() {{ 
                            console.log('📢 ADSENSE: Spoofed location.hostname to ybsq.xyz');
                            return originalDomain; 
                        }}
                    }});
                    
                    Object.defineProperty(window.location, 'host', {{
                        get: function() {{ return originalDomain; }}
                    }});
                    
                    Object.defineProperty(window.location, 'origin', {{
                        get: function() {{ 
                            console.log('📢 ADSENSE: Spoofed location.origin to https://ybsq.xyz');
                            return originalOrigin; 
                        }}
                    }});
                    
                    Object.defineProperty(window.location, 'href', {{
                        get: function() {{ 
                            return originalOrigin + window.location.pathname.replace('/proxy/https://ybsq.xyz', '');
                        }}
                    }});
                    
                    // Override document.referrer for AdSense
                    Object.defineProperty(document, 'referrer', {{
                        get: function() {{ 
                            console.log('📢 ADSENSE: Spoofed document.referrer to ybsq.xyz');
                            return originalOrigin + '/'; 
                        }}
                    }});
                    
                    // Override top.location for iframe ads
                    try {{
                        Object.defineProperty(top.location, 'hostname', {{
                            get: function() {{ return originalDomain; }}
                        }});
                        Object.defineProperty(top.location, 'origin', {{
                            get: function() {{ return originalOrigin; }}
                        }});
                    }} catch(e) {{ /* ignore cross-origin */ }}
                    
                    console.log('📢 ADSENSE: Domain spoofed to ybsq.xyz');
                    </script>
                    '''
                    
                    # Inject AdSense fix early
                    if 'googlesyndication.com' in html_content or 'adsbygoogle' in html_content:
                        html_content = html_content.replace('<head>', f'<head>{adsense_fix}')
                        print("📢 ADSENSE: Injected domain fix for AdSense")
                    
                    # Inject GA4 location override before any GA4 scripts
                    ga4_override = '''
                    <script>
                    // GA4 Location Override - Must run before GA4 loads
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    
                    // Override gtag to force US location
                    const originalGtag = window.gtag || gtag;
                    window.gtag = function(command, target, config) {
                        if (command === 'config' && config) {
                            config.country = 'US';
                            config.region = 'NY'; 
                            config.city = 'New York';
                            config.custom_map = config.custom_map || {};
                            config.custom_map.country = 'US';
                            config.custom_map.region = 'NY';
                            config.custom_map.city = 'New York';
                            console.log('🇺🇸 GA4: Forced US location in config');
                        }
                        return originalGtag.call(this, command, target, config);
                    };
                    
                    // Set global location data for GA4
                    gtag('config', 'G-BX28RFEZ30', {
                        country: 'US',
                        region: 'NY',
                        city: 'New York',
                        custom_map: {
                            country: 'US',
                            region: 'NY',
                            city: 'New York'
                        }
                    });
                    </script>
                    '''
                    
                    # Inject GA4 override before any Google Analytics scripts
                    if 'googletagmanager.com' in html_content or 'google-analytics.com' in html_content:
                        html_content = html_content.replace('<head>', f'<head>{ga4_override}')
                    
                    print("✅ Server-side IP replacement completed")
                    
                    # Rewrite content like CroxyProxy
                    proxy_base = f"https://{request.headers.get('host', 'scrap.ybsq.xyz')}/proxy"
                    processed_content = rewrite_html_content(html_content, path, proxy_base, current_proxy_ip)
                    
                    # Template replacement already done in rewrite_html_content function
                    
                    return HTMLResponse(
                        content=processed_content,
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "X-Frame-Options": "ALLOWALL",
                            "Content-Security-Policy": "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
                        }
                    )
                except Exception as e:
                    print(f"❌ HTML processing error: {e}")
                    return HTMLResponse(f"<h1>Error processing HTML</h1><p>{str(e)}</p>")
            
            elif 'text/css' in content_type:
                # CSS content - rewrite URLs
                css_content = response.text
                proxy_base = f"https://{request.headers.get('host', 'scrap.ybsq.xyz')}/proxy"
                
                # Rewrite CSS URLs
                css_content = re.sub(
                    r'url\(["\']?([^"\'\\)]+)["\']?\)',
                    rf'url("{proxy_base}/\1")',
                    css_content
                )
                
                return Response(
                    content=css_content,
                    media_type="text/css",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            
            elif 'javascript' in content_type:
                # JavaScript content - return as-is with CORS
                return Response(
                    content=response.content,
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            
            elif 'application/json' in content_type:
                # JSON content - format nicely
                try:
                    json_data = response.json()
                    return HTMLResponse(f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>JSON Response</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; padding: 20px; }}
                            .status {{ position: fixed; top: 10px; right: 10px; background: #28a745; color: white; padding: 8px 12px; border-radius: 5px; }}
                            pre {{ background: #f8f9fa; padding: 20px; border-radius: 8px; overflow: auto; }}
                        </style>
                    </head>
                    <body>
                        <div class="status">🇺🇸 US Proxy Active</div>
                        <h1>Proxy Response</h1>
                        <p><strong>URL:</strong> {path}</p>
                        <p><strong>Status:</strong> {response.status_code}</p>
                        <pre>{json.dumps(json_data, indent=2)}</pre>
                        <button onclick="history.back()">← Back</button>
                    </body>
                    </html>
                    """)
                except:
                    return Response(content=response.content, media_type=content_type)
            
            else:
                # Binary content (images, etc.) - return as-is
                return Response(
                    content=response.content,
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
                
    except Exception as e:
        print(f"❌ Proxy error: {str(e)}")
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Proxy Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ background: #f8d7da; color: #721c24; padding: 20px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>🌐 Proxy Browser V2</h1>
            <div class="error">
                <h3>Connection Error</h3>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>URL:</strong> {path}</p>
            </div>
            <button onclick="history.back()">← Back</button>
            <button onclick="window.location.href='/'">🏠 Home</button>
        </body>
        </html>
        """)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
