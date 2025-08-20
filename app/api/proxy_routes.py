"""
Proxy API Routes
Handles proxy-related HTTP endpoints
"""

from fastapi import APIRouter, Request, Response, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
import base64
from typing import Optional
from loguru import logger

router = APIRouter()


@router.get("/")
async def proxy_request(
    request: Request,
    url: str = Query(..., description="Base64 encoded URL to proxy")
):
    """Proxy HTTP request"""
    
    try:
        # Decode URL
        decoded_url = base64.b64decode(url).decode('utf-8')
        
        # Get proxy service from app state
        proxy_service = request.app.state.proxy_service
        
        # Get session ID from headers or cookies
        session_id = request.headers.get('X-Session-ID') or \
                    request.cookies.get('session_id') or \
                    "default"
        
        # Make proxied request
        result = await proxy_service.make_request(
            method="GET",
            url=decoded_url,
            headers=dict(request.headers),
            session_id=session_id
        )
        
        # Return response
        return Response(
            content=result['body'],
            status_code=result['status'],
            headers=result['headers']
        )
        
    except Exception as e:
        logger.error(f"Proxy request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def proxy_post_request(
    request: Request,
    url: str = Query(..., description="Base64 encoded URL to proxy")
):
    """Proxy POST request"""
    
    try:
        # Decode URL
        decoded_url = base64.b64decode(url).decode('utf-8')
        
        # Get request body
        body = await request.body()
        
        # Get proxy service
        proxy_service = request.app.state.proxy_service
        
        # Get session ID
        session_id = request.headers.get('X-Session-ID') or \
                    request.cookies.get('session_id') or \
                    "default"
        
        # Make proxied request
        result = await proxy_service.make_request(
            method="POST",
            url=decoded_url,
            headers=dict(request.headers),
            body=body,
            session_id=session_id
        )
        
        return Response(
            content=result['body'],
            status_code=result['status'],
            headers=result['headers']
        )
        
    except Exception as e:
        logger.error(f"Proxy POST error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-ip")
async def check_proxy_ip(request: Request):
    """Check current proxy IP and location"""
    
    try:
        proxy_service = request.app.state.proxy_service
        session_id = request.headers.get('X-Session-ID') or "default"
        
        # Make request to IP checking service
        result = await proxy_service.make_request(
            method="GET",
            url="https://ipapi.co/json/",
            session_id=session_id
        )
        
        # Ensure we return valid JSON
        try:
            import json
            ip_info = json.loads(result['body'])
        except:
            # If response is not JSON, create a simple response
            ip_info = {
                "ip": "Unknown",
                "city": "Unknown",
                "country_name": "Unknown",
                "error": "Invalid response format"
            }
        
        return JSONResponse(content={
            "proxy_active": True,
            "ip_info": json.dumps(ip_info)
        })
        
    except Exception as e:
        logger.error(f"IP check error: {str(e)}")
        return JSONResponse(content={
            "proxy_active": False,
            "error": str(e)
        })
