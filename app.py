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


app = FastAPI(title="Proxy Browser V2 - CroxyProxy Style")

# Proxy configuration
PROXY_CONFIG = {
    "server": os.environ.get("PROXY_SERVER", "pg.proxi.es:20000"),
    "username": os.environ.get("PROXY_USERNAME", "KMwYgm4pR4upF6yX"),
    "password": os.environ.get("PROXY_PASSWORD", "pMBwu34BjjGr5urD"),
    "country": os.environ.get("PROXY_COUNTRY", "USA"),
    "timezone": os.environ.get("SPOOF_TIMEZONE", "America/New_York"),
    "language": os.environ.get("SPOOF_LANGUAGE", "en-US"),
    "target_url": os.environ.get("DEFAULT_TARGET_URL", "https://ybsq.xyz/")
}

def get_proxy_url():
    return f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['server']}"

def get_spoofed_headers(original_request: Request, target_url: str):
    """Get headers with US location spoofing while preserving original User-Agent"""
    headers = {}
    
    # Preserve original headers but modify location-related ones
    for name, value in original_request.headers.items():
        if name.lower() not in ['host', 'connection', 'content-length', 'transfer-encoding']:
            headers[name] = value
    
    # Override location-related headers with US data
    headers.update({
        "Accept-Language": "en-US,en;q=0.9",
        "X-Forwarded-For": "172.56.47.191",
        "CF-IPCountry": "US", 
        "CF-Region": "NY",
        "CF-City": "New York",
        "X-Real-IP": "172.56.47.191",
        "X-Forwarded-Proto": "https",
        "X-Appengine-Country": "US",
        "X-Appengine-Region": "ny", 
        "X-Appengine-City": "newyork",
        "X-Appengine-User-IP": "172.56.47.191",
        "X-Client-IP": "172.56.47.191",
        "X-Cluster-Client-IP": "172.56.47.191",
        "X-Original-Forwarded-For": "172.56.47.191",
        "True-Client-IP": "172.56.47.191",
        "X-Remote-IP": "172.56.47.191",
        "X-Remote-Addr": "172.56.47.191",
        "Remote-Addr": "172.56.47.191",
        "HTTP_X_FORWARDED_FOR": "172.56.47.191",
        "HTTP_CLIENT_IP": "172.56.47.191",
        "HTTP_X_REAL_IP": "172.56.47.191",
        "Forwarded": "for=172.56.47.191;proto=https;host=ybsq.xyz",
        "X-Forwarded-Host": "ybsq.xyz",
        "X-Original-Host": "ybsq.xyz",
        "Host": urlparse(target_url).netloc,
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    })
    
    return headers

def rewrite_html_content(content: str, base_url: str, proxy_base: str):
    """Rewrite HTML content like CroxyProxy"""
    
    # Parse base URL
    parsed_base = urlparse(base_url)
    domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    # Rewrite absolute URLs
    content = re.sub(
        r'(href|src|action)=(["\'])https?://([^"\']+)\2',
        rf'\1=\2{proxy_base}/\3\2',
        content
    )
    
    # Rewrite protocol-relative URLs
    content = re.sub(
        r'(href|src|action)=(["\'])//([^"\']+)\2',
        rf'\1=\2{proxy_base}/https://\3\2',
        content
    )
    
    # Rewrite relative URLs
    content = re.sub(
        r'(href|src|action)=(["\'])(?!http|//|#|mailto:|tel:|javascript:)([^"\']+)\2',
        rf'\1=\2{proxy_base}/{domain}/\3\2',
        content
    )
    
    # Add comprehensive spoofing script
    spoof_script = f"""
    <script>
    // CroxyProxy-style spoofing
    console.log('🇺🇸 CROXYPROXY: Initializing location spoofing...');
    
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
    
    // Override timezone
    Date.prototype.getTimezoneOffset = function() {{
        return 300; // EST
    }};
    
    // Override Intl
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(locale, options) {{
        return new originalDateTimeFormat('en-US', {{...options, timeZone: 'America/New_York'}});
    }};
    
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
                ip: "172.56.47.191",
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
                isp: "Digital Ocean",
                org: "Digital Ocean",
                as: "AS14061 DigitalOcean, LLC",
                query: "172.56.47.191"
            }}), {{
                headers: {{ 'Content-Type': 'application/json' }}
            }}));
        }}
        
        // Add US headers to all analytics requests
        if (urlStr.includes('google') || urlStr.includes('analytics') || urlStr.includes('adsense')) {{
            console.log('🇺🇸 CROXYPROXY: Adding US headers to analytics');
            options.headers = {{
                ...options.headers,
                'CF-IPCountry': 'US',
                'X-Forwarded-For': '172.56.47.191',
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
                            ip: "172.56.47.191",
                            country: "United States",
                            country_code: "US",
                            city: "New York",
                            region: "NY",
                            lat: 40.7128,
                            lon: -74.0060,
                            timezone: "America/New_York"
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
    
    // Override common global variables used for IP detection
    window.userIP = "172.56.47.191";
    window.userCountry = "United States";
    window.userCity = "New York";
    window.userRegion = "NY";
    window.userTimezone = "America/New_York";
    window.userLatitude = 40.7128;
    window.userLongitude = -74.0060;
    
    // Override any existing IP detection functions
    if (window.getIP) window.getIP = () => "172.56.47.191";
    if (window.getUserIP) window.getUserIP = () => "172.56.47.191";
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
async def root():
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
            <button class="btn" onclick="window.location.href='/proxy/https://example.com/'">
                Test Example.com
            </button>
            <br><br>
            <button class="btn" onclick="window.location.href='/proxy/https://httpbin.org/ip'">
                Test IP Detection
            </button>
            <br><br>
            <button class="btn" onclick="window.location.href='/proxy/https://ybsq.xyz/'">
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

@app.get("/proxy/{path:path}")
async def proxy_page(path: str, request: Request):
    try:
        # Decode URL
        path = unquote(path)
        
        # Ensure proper URL format
        if not path.startswith(('http://', 'https://')):
            path = 'https://' + path
        
        print(f"🌐 PROXY: Fetching {path}")
        
        # Get spoofed headers
        headers = get_spoofed_headers(request, path)
        
        # Create proxy client
        proxy_url = get_proxy_url()
        
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=30.0,
            verify=False,
            follow_redirects=True
        ) as client:
            response = await client.get(path, headers=headers)
            
            # Handle Brotli compression by avoiding it
            content_encoding = response.headers.get('content-encoding', '')
            if 'br' in content_encoding:
                print("⚠️ Brotli compression detected, retrying without Brotli...")
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
                    
                    # Server-side IP replacement (aggressive)
                    print("🔧 Performing server-side IP replacement...")
                    # Replace various IP patterns
                    html_content = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '172.56.47.191', html_content)
                    html_content = re.sub(r'\b[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{1,4}){7}\b', '172.56.47.191', html_content)  # IPv6
                    html_content = re.sub(r'\bIndia\b', 'United States', html_content)
                    html_content = re.sub(r'\bBhubaneswar\b', 'New York', html_content)
                    html_content = re.sub(r'\bAsia/Calcutta\b', 'America/New_York', html_content)
                    html_content = re.sub(r'\ben-GB\b', 'en-US', html_content)
                    
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
                    processed_content = rewrite_html_content(html_content, path, proxy_base)
                    
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
