"""
Direct proxy API routes
"""

from fastapi import APIRouter, Request, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
from typing import Optional

router = APIRouter(prefix="/api/direct-proxy", tags=["direct-proxy"])

# Create a legacy router for backward compatibility
legacy_router = APIRouter(prefix="/api/proxy", tags=["proxy-legacy"])

# Create a cloudflare bypass router
cf_router = APIRouter(tags=["cloudflare"])


@router.get("/navigate")
async def navigate_proxy(
    request: Request,
    url: str = Query(..., description="URL to navigate to"),
    session_id: str = Query(..., description="Session ID")
):
    """Navigate to URL through proxy"""
    
    direct_proxy = request.app.state.direct_proxy
    
    try:
        result = await direct_proxy.fetch_page(url, session_id)
        
        if result["success"]:
            # Return HTML response
            return HTMLResponse(
                content=result["content"],
                status_code=result.get("status_code", 200),
                headers={
                    "X-Original-URL": url,
                    "X-Session-ID": session_id
                }
            )
        else:
            # Return error page
            return HTMLResponse(
                content=result["content"],
                status_code=500
            )
            
    except Exception as e:
        logger.error(f"Navigation error: {e}")
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>Error</title></head>
            <body>
                <h1>Navigation Error</h1>
                <p>Failed to navigate to: {url}</p>
                <p>Error: {str(e)}</p>
            </body>
            </html>
            """,
            status_code=500
        )


@router.get("/resource")
@router.post("/resource")
async def fetch_resource(
    request: Request,
    url: str = Query(..., description="Resource URL"),
    session_id: str = Query(..., description="Session ID")
):
    """Fetch resource through proxy"""
    
    direct_proxy = request.app.state.direct_proxy
    
    try:
        # Handle POST data if present
        post_data = None
        if request.method == "POST":
            try:
                post_data = await request.body()
            except:
                pass
        
        result = await direct_proxy.fetch_page(url, session_id, method=request.method, data=post_data)
        
        if result["success"]:
            content_type = result.get("content_type", "application/octet-stream")
            
            # Return appropriate response based on content type
            if isinstance(result["content"], bytes):
                return Response(
                    content=result["content"],
                    media_type=content_type,
                    headers={
                        "X-Original-URL": url,
                        "Cache-Control": "public, max-age=3600"
                    }
                )
            else:
                return Response(
                    content=result["content"],
                    media_type=content_type,
                    headers={
                        "X-Original-URL": url
                    }
                )
        else:
            return Response(
                content=f"Error loading resource: {result.get('error', 'Unknown error')}",
                status_code=500
            )
            
    except Exception as e:
        logger.error(f"Resource fetch error: {e}")
        return Response(
            content=f"Error: {str(e)}",
            status_code=500
        )


# Legacy routes for backward compatibility
@legacy_router.get("/resource")
@legacy_router.post("/resource")
async def legacy_fetch_resource(
    request: Request,
    url: str = Query(..., description="Resource URL"),
    session_id: str = Query(..., description="Session ID")
):
    """Legacy resource fetch endpoint"""
    return await fetch_resource(request, url, session_id)


# Cloudflare challenge routes
@cf_router.get("/cdn-cgi/challenge-platform/{path:path}")
async def handle_cloudflare_challenge(path: str, request: Request):
    """Handle Cloudflare challenge requests"""
    logger.info(f"Cloudflare challenge requested: {path}")
    
    # Return a simple response to bypass the challenge
    return HTMLResponse(
        content="""
        <html>
        <head><title>Challenge Bypassed</title></head>
        <body>
            <script>
                // Auto-redirect to the original page
                window.location.href = document.referrer || '/';
            </script>
        </body>
        </html>
        """,
        status_code=200
    )
