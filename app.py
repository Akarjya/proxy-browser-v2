import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx
import json
import re
from urllib.parse import quote, unquote

app = FastAPI(title="Proxy Browser V2")

# Simple proxy configuration
PROXY_CONFIG = {
    "server": os.environ.get("PROXY_SERVER", "pg.proxi.es:20000"),
    "username": os.environ.get("PROXY_USERNAME", "KMwYgm4pR4upF6yX"),
    "password": os.environ.get("PROXY_PASSWORD", "pMBwu34BjjGr5urD"),
    "country": os.environ.get("PROXY_COUNTRY", "USA"),
    "timezone": os.environ.get("SPOOF_TIMEZONE", "America/New_York"),
    "language": os.environ.get("SPOOF_LANGUAGE", "en-US"),
    "target_url": os.environ.get("DEFAULT_TARGET_URL", "https://httpbin.org/ip")
}

# Simple app

@app.get("/")
async def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Proxy Browser V2</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .btn { background: #007bff; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; }
            .loading { display: none; }
        </style>
    </head>
    <body>
        <h1>🌐 Proxy Browser V2</h1>
        <p>Browse with US IP address and location</p>
        <button class="btn" onclick="startBrowsing()">Start Browsing</button>
        <div class="loading" id="loading">Loading...</div>
        <div id="content"></div>
        
        <script>
            async function startBrowsing() {
                document.getElementById('loading').style.display = 'block';
                try {
                    // Try multiple sites
                    const sites = [
                        '/proxy/https://httpbin.org/ip',
                        '/proxy/https://example.com',
                        '/proxy/https://ybsq.xyz'
                    ];
                    
                    for (const site of sites) {
                        try {
                            const response = await fetch(site);
                            if (response.ok) {
                                const html = await response.text();
                                document.getElementById('content').innerHTML = html;
                                break;
                            }
                        } catch (e) {
                            console.log(`Failed to load ${site}:`, e);
                        }
                    }
                } catch (error) {
                    document.getElementById('content').innerHTML = 'Error: ' + error.message;
                }
                document.getElementById('loading').style.display = 'none';
            }
        </script>
    </body>
    </html>
    """)

@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "proxy-browser-v2"}

@app.get("/test-proxy")
async def test_proxy():
    try:
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['server']}"
        
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=10.0,
            verify=False
        ) as client:
            response = await client.get("https://httpbin.org/ip")
            return {"status": "success", "proxy_ip": response.json()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/proxy/{path:path}")
async def proxy_page(path: str):
    print(f"Received proxy request for path: {path}")
    try:
        # Decode URL if needed
        path = unquote(path)
        
        # Construct full URL
        if not path.startswith('http'):
            path = 'https://' + path
        elif path.startswith('http://'):
            path = path.replace('http://', 'https://', 1)
        
        print(f"Proxying request to: {path}")
        print(f"Proxy config: {PROXY_CONFIG}")
        
        # Validate URL
        if not path.startswith(('http://', 'https://')):
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head><title>Invalid URL</title></head>
            <body>
                <h1>Invalid URL</h1>
                <p>URL must start with http:// or https://</p>
                <p>Received: {path}</p>
                <button onclick="window.location.reload()">Try Again</button>
            </body>
            </html>
            """)
        
        # Create proxy client
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['server']}"
        
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=30.0,
            verify=False
        ) as client:
            # Add spoofed headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": PROXY_CONFIG['language'],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "X-Forwarded-For": "8.8.8.8",
                "CF-IPCountry": "US",
                "X-Real-IP": "8.8.8.8",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "ybsq.xyz"
            }
            
            response = await client.get(path, headers=headers)
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            # Check for unsupported content encoding
            content_encoding = response.headers.get('content-encoding', '')
            if 'br' in content_encoding:
                print(f"Warning: Brotli compression detected - {content_encoding}")
                # Try again with different headers to avoid Brotli
                headers.update({
                    "Accept-Encoding": "gzip, deflate",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                })
                response = await client.get(path, headers=headers)
                print(f"Retry response status: {response.status_code}")
                print(f"Retry response headers: {dict(response.headers)}")
            
            if response.status_code == 403:
                return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head><title>403 Forbidden</title></head>
                <body>
                    <h1>403 - Forbidden</h1>
                    <p>The target site is blocking proxy requests.</p>
                    <p>Status: {response.status_code}</p>
                    <p>Headers: {dict(response.headers)}</p>
                    <button onclick="window.location.reload()">Try Again</button>
                </body>
                </html>
                """)
            
            # Get content and check if it's readable
            try:
                content = response.text
                # Quick check if content is garbled (contains lots of non-printable chars)
                if len([c for c in content[:100] if ord(c) > 127]) > 50:
                    raise UnicodeDecodeError("utf-8", b"", 0, 0, "Garbled content detected")
            except (UnicodeDecodeError, Exception) as e:
                print(f"Content decode error: {e}")
                return HTMLResponse(f"""
                <!DOCTYPE html>
                <html>
                <head><title>Content Encoding Error</title></head>
                <body>
                    <div style="position:fixed;top:10px;right:10px;background:green;color:white;padding:10px;border-radius:5px;z-index:9999;">🇺🇸 US Proxy Active - {PROXY_CONFIG["country"]}</div>
                    <h1>Content Encoding Error</h1>
                    <p>The website returned compressed content that couldn't be decoded.</p>
                    <p><strong>URL:</strong> {path}</p>
                    <p><strong>Status:</strong> {response.status_code}</p>
                    <p><strong>Content-Encoding:</strong> {response.headers.get('content-encoding', 'none')}</p>
                    <p>This site may be using Brotli compression which is not supported yet.</p>
                    <button onclick="window.location.reload()">Try Again</button>
                    <button onclick="window.location.href='/'">Go Back</button>
                </body>
                </html>
                """)
            
            # Check if it's JSON response (like httpbin)
            if response.headers.get('content-type', '').startswith('application/json'):
                # Format JSON nicely for display
                json_content = json.loads(content)
                formatted_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Proxy Response</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; padding: 20px; }}
                        .status {{ position: fixed; top: 10px; right: 10px; background: green; color: white; padding: 10px; border-radius: 5px; z-index: 9999; }}
                        .json {{ background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                        pre {{ font-size: 16px; line-height: 1.5; }}
                    </style>
                </head>
                <body>
                    <div class="status">🇺🇸 US Proxy Active - {PROXY_CONFIG["country"]}</div>
                    <h1>Proxy Response</h1>
                    <p><strong>URL:</strong> {path}</p>
                    <p><strong>Status:</strong> {response.status_code}</p>
                    <div class="json">
                        <h3>Response Data:</h3>
                        <pre>{json.dumps(json_content, indent=2)}</pre>
                    </div>
                    <button onclick="window.location.reload()">Refresh</button>
                </body>
                </html>
                """
                return HTMLResponse(formatted_content)
            else:
                # Regular HTML content
                # Simple URL rewriting with regex (no BeautifulSoup)
                content = re.sub(r'href=["\'](https?://[^"\']+)["\']', r'href="/proxy/\1"', content)
                content = re.sub(r'src=["\'](https?://[^"\']+)["\']', r'src="/proxy/\1"', content)
                
                # Server-side location text replacement
                print("🇺🇸 PROXY: Performing server-side location replacement...")
                content = re.sub(r'\bIndia\b', 'United States', content)
                content = re.sub(r'\bBhubaneswar\b', 'New York', content) 
                content = re.sub(r'\bAsia/Calcutta\b', 'America/New_York', content)
                content = re.sub(r'\ben-GB\b', 'en-US', content)
                content = re.sub(r'\bUnknown\b', 'New York, NY', content)
                print("🇺🇸 PROXY: Server-side location replacement completed")
                
                # Add comprehensive JavaScript injection for spoofing
                spoof_script = f"""
                <script>
                console.log('🇺🇸 PROXY: Initializing US location spoofing...');
                
                // Override geolocation API
                if (navigator.geolocation) {{
                    const originalGetCurrentPosition = navigator.geolocation.getCurrentPosition;
                    const originalWatchPosition = navigator.geolocation.watchPosition;
                    
                    navigator.geolocation.getCurrentPosition = function(success, error, options) {{
                        console.log('🇺🇸 PROXY: Spoofing geolocation.getCurrentPosition');
                        const spoofedPosition = {{
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
                        if (success) success(spoofedPosition);
                    }};
                    
                    navigator.geolocation.watchPosition = function(success, error, options) {{
                        console.log('🇺🇸 PROXY: Spoofing geolocation.watchPosition');
                        return originalGetCurrentPosition.call(this, success, error, options);
                    }};
                }}
                
                // Override timezone
                const originalDateTimeFormat = Intl.DateTimeFormat;
                Intl.DateTimeFormat = function(...args) {{
                    console.log('🇺🇸 PROXY: Spoofing Intl.DateTimeFormat');
                    if (args.length === 0 || !args[0]) {{
                        args[0] = 'en-US';
                    }}
                    const options = args[1] || {{}};
                    options.timeZone = 'America/New_York';
                    return new originalDateTimeFormat(args[0], options);
                }};
                
                // Override Date timezone offset
                const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
                Date.prototype.getTimezoneOffset = function() {{
                    console.log('🇺🇸 PROXY: Spoofing timezone offset to EST/EDT');
                    return 300; // EST offset (UTC-5)
                }};
                
                // Override timezone string
                const originalToString = Date.prototype.toString;
                Date.prototype.toString = function() {{
                    const date = originalToString.call(this);
                    console.log('🇺🇸 PROXY: Spoofing Date.toString timezone');
                    return date.replace(/GMT[+-]\\d{{4}}.*$/, 'GMT-0500 (Eastern Standard Time)');
                }};
                
                // Override Intl.DateTimeFormat resolvedOptions
                const originalResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
                Intl.DateTimeFormat.prototype.resolvedOptions = function() {{
                    const options = originalResolvedOptions.call(this);
                    console.log('🇺🇸 PROXY: Spoofing DateTimeFormat resolvedOptions');
                    options.timeZone = 'America/New_York';
                    options.locale = 'en-US';
                    return options;
                }};
                
                // Override fetch for IP detection APIs
                const originalFetch = window.fetch;
                window.fetch = function(url, options) {{
                    const urlStr = url.toString();
                    console.log('🇺🇸 PROXY: Intercepting fetch:', urlStr);
                    
                    // Block or redirect IP detection services
                    if (urlStr.includes('ipapi.co') || urlStr.includes('api.ipify.org') || 
                        urlStr.includes('ipinfo.io') || urlStr.includes('ip-api.com') ||
                        urlStr.includes('whatismyipaddress.com') || urlStr.includes('myip.com') ||
                        urlStr.includes('geoip') || urlStr.includes('location') || urlStr.includes('geolocation')) {{
                        console.log('🇺🇸 PROXY: Blocking IP/Location detection API:', urlStr);
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
                            asname: "DIGITALOCEAN-ASN",
                            mobile: false,
                            proxy: false,
                            hosting: true
                        }}), {{
                            headers: {{ 'Content-Type': 'application/json' }}
                        }}));
                    }}
                    
                    // Intercept WordPress tracking
                    if (urlStr.includes('wp-json') || urlStr.includes('wp-admin')) {{
                        console.log('🇺🇸 PROXY: Intercepting WordPress API:', urlStr);
                        // Add US headers to WordPress requests
                        const newOptions = {{ ...options }};
                        newOptions.headers = {{
                            ...newOptions.headers,
                            'X-Forwarded-For': '172.56.47.191',
                            'CF-IPCountry': 'US',
                            'X-Real-IP': '172.56.47.191'
                        }};
                        return originalFetch.call(this, url, newOptions);
                    }}
                    
                    return originalFetch.call(this, url, options);
                }};
                
                // Override XMLHttpRequest
                const originalXHROpen = XMLHttpRequest.prototype.open;
                const originalXHRSend = XMLHttpRequest.prototype.send;
                
                XMLHttpRequest.prototype.open = function(method, url, ...args) {{
                    console.log('🇺🇸 PROXY: Intercepting XHR:', url);
                    this._url = url;
                    return originalXHROpen.call(this, method, url, ...args);
                }};
                
                XMLHttpRequest.prototype.send = function(data) {{
                    if (this._url && (this._url.includes('wp-json') || this._url.includes('wp-admin'))) {{
                        console.log('🇺🇸 PROXY: Adding US headers to XHR:', this._url);
                        this.setRequestHeader('X-Forwarded-For', '172.56.47.191');
                        this.setRequestHeader('CF-IPCountry', 'US');
                        this.setRequestHeader('X-Real-IP', '172.56.47.191');
                    }}
                    return originalXHRSend.call(this, data);
                }};
                
                // Override navigator properties
                Object.defineProperty(navigator, 'language', {{
                    get: function() {{
                        console.log('🇺🇸 PROXY: Spoofing navigator.language');
                        return 'en-US';
                    }}
                }});
                
                Object.defineProperty(navigator, 'languages', {{
                    get: function() {{
                        console.log('🇺🇸 PROXY: Spoofing navigator.languages');
                        return ['en-US', 'en'];
                    }}
                }});
                
                // Replace IP addresses in DOM content
                function replaceIPsInDOM() {{
                    try {{
                        if (!document.body) {{
                            console.log('🇺🇸 PROXY: Document body not ready yet');
                            return;
                        }}
                        
                        const walker = document.createTreeWalker(
                            document.body,
                            NodeFilter.SHOW_TEXT,
                            null,
                            false
                        );
                        
                        let node;
                        const ipRegex = /\\b(?:[0-9]{{1,3}}\\.)[0-9]{{1,3}}\\.[0-9]{{1,3}}\\.[0-9]{{1,3}}\\b/g;
                        const replacements = [];
                        
                        while ((node = walker.nextNode())) {{
                            if (node && node.textContent) {{
                                let newText = node.textContent;
                                let changed = false;
                                
                                // Replace IP addresses
                                if (ipRegex.test(newText)) {{
                                    newText = newText.replace(ipRegex, '172.56.47.191');
                                    changed = true;
                                }}
                                
                                // Replace location text
                                if (newText.includes('India') || newText.includes('Bhubaneswar') || 
                                    newText.includes('Asia/Calcutta') || newText.includes('en-GB')) {{
                                    newText = newText.replace(/India/g, 'United States');
                                    newText = newText.replace(/Bhubaneswar/g, 'New York');
                                    newText = newText.replace(/Asia\/Calcutta/g, 'America/New_York');
                                    newText = newText.replace(/en-GB/g, 'en-US');
                                    changed = true;
                                }}
                                
                                if (changed && newText !== node.textContent) {{
                                    console.log('🇺🇸 PROXY: Replacing location in DOM:', node.textContent.substring(0, 50), '->', newText.substring(0, 50));
                                    replacements.push({{node: node, newText: newText}});
                                }}
                            }}
                        }}
                        
                        replacements.forEach(function(replacement) {{
                            if (replacement.node && replacement.node.textContent !== undefined) {{
                                replacement.node.textContent = replacement.newText;
                            }}
                        }});
                        
                        console.log('🇺🇸 PROXY: IP replacement completed, ' + replacements.length + ' replacements made');
                    }} catch (error) {{
                        console.error('🇺🇸 PROXY: Error in replaceIPsInDOM:', error);
                    }}
                }}
                
                // Run IP replacement periodically
                setTimeout(replaceIPsInDOM, 100);
                setTimeout(replaceIPsInDOM, 500);
                setTimeout(replaceIPsInDOM, 1000);
                setTimeout(replaceIPsInDOM, 2000);
                
                // Monitor for dynamic content changes
                if (window.MutationObserver) {{
                    const observer = new MutationObserver(function(mutations) {{
                        let shouldReplace = false;
                        for (let i = 0; i < mutations.length; i++) {{
                            const mutation = mutations[i];
                            if (mutation.type === 'childList' || mutation.type === 'characterData') {{
                                shouldReplace = true;
                                break;
                            }}
                        }}
                        if (shouldReplace) {{
                            setTimeout(replaceIPsInDOM, 50);
                        }}
                    }});
                    
                    observer.observe(document.body, {{
                        childList: true,
                        subtree: true,
                        characterData: true
                    }});
                }}
                
                console.log('🇺🇸 PROXY: US location spoofing initialized successfully!');
                </script>
                """
                
                # Add proxy status and inject script
                status_html = f'<div style="position:fixed;top:10px;right:10px;background:green;color:white;padding:10px;border-radius:5px;z-index:9999;">🇺🇸 US Proxy Active - {PROXY_CONFIG["country"]}</div>'
                
                # Inject script in head for early execution
                if '<head>' in content:
                    content = content.replace('<head>', f'<head>{spoof_script}')
                else:
                    content = spoof_script + content
                    
                # Add status indicator
                content = content.replace('<body', f'<body>{status_html}')
                
                return HTMLResponse(content)
            
    except Exception as e:
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Proxy Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: red; background: #ffe6e6; padding: 20px; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <h1>🌐 Proxy Browser V2</h1>
            <div class="error">
                <h2>Connection Error</h2>
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Please try again or check your proxy settings.</p>
            </div>
            <button onclick="window.location.reload()">Try Again</button>
        </body>
        </html>
        """
        return HTMLResponse(error_html)



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
