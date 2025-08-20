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
                "Accept-Encoding": "gzip, deflate, br",
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
            
            content = response.text
            
            # Simple URL rewriting with regex (no BeautifulSoup)
            content = re.sub(r'href=["\'](https?://[^"\']+)["\']', r'href="/proxy/\1"', content)
            content = re.sub(r'src=["\'](https?://[^"\']+)["\']', r'src="/proxy/\1"', content)
            
            # Add proxy status
            status_html = f'<div style="position:fixed;top:10px;right:10px;background:green;color:white;padding:10px;border-radius:5px;z-index:9999;">🇺🇸 US Proxy Active - {PROXY_CONFIG["country"]}</div>'
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
