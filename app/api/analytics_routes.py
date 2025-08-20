"""
Analytics API Routes
Handles analytics tracking endpoints for GA4, AdSense, Facebook Pixel, etc.
"""

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from loguru import logger
import json
import httpx

router = APIRouter()


@router.post("/ga4")
async def handle_ga4_event(request: Request):
    """Handle Google Analytics 4 events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        # Log GA4 event with spoofed location
        logger.info(f"GA4 Event from session {session_id}: {data.get('event_name')}")
        
        # Modify event data to include proxy location
        modified_data = {
            **data,
            "geo": {
                "country": request.app.state.settings.spoof_country_code,
                "city": request.app.state.settings.proxy_city,
                "region": request.app.state.settings.spoof_region
            }
        }
        
        # Forward to actual GA4 if measurement ID provided
        if data.get('measurement_id'):
            await forward_to_ga4(modified_data)
        
        return JSONResponse(content={
            "status": "tracked",
            "proxy_location": modified_data["geo"]
        })
        
    except Exception as e:
        logger.error(f"GA4 handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gtag")
async def handle_gtag_event(request: Request):
    """Handle Google Tag Manager events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        logger.info(f"GTM Event from session {session_id}: {data}")
        
        # Process and modify event
        modified_data = process_gtm_event(data, request.app.state.settings)
        
        return JSONResponse(content={
            "status": "tracked",
            "modified": modified_data
        })
        
    except Exception as e:
        logger.error(f"GTM handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/adsense")
async def handle_adsense_event(request: Request):
    """Handle Google AdSense events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        logger.info(f"AdSense Event from session {session_id}")
        
        # AdSense will use proxy IP automatically
        # Log for monitoring
        event_data = {
            "session_id": session_id,
            "ad_client": data.get("ad_client"),
            "ad_slot": data.get("ad_slot"),
            "proxy_country": request.app.state.settings.spoof_country_code,
            "timestamp": data.get("timestamp")
        }
        
        return JSONResponse(content={
            "status": "tracked",
            "event": event_data
        })
        
    except Exception as e:
        logger.error(f"AdSense handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facebook-pixel")
async def handle_facebook_pixel(request: Request):
    """Handle Facebook Pixel events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        logger.info(f"FB Pixel Event from session {session_id}: {data.get('event')}")
        
        # Modify event data for proxy location
        modified_data = {
            **data,
            "custom_data": {
                **(data.get("custom_data", {})),
                "proxy_country": request.app.state.settings.spoof_country_code,
                "proxy_city": request.app.state.settings.proxy_city
            }
        }
        
        # Forward to Facebook if pixel ID provided
        if data.get('pixel_id'):
            await forward_to_facebook(modified_data)
        
        return JSONResponse(content={
            "status": "tracked",
            "event": data.get("event"),
            "proxy_location": {
                "country": request.app.state.settings.spoof_country_code,
                "city": request.app.state.settings.proxy_city
            }
        })
        
    except Exception as e:
        logger.error(f"FB Pixel handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mixpanel")
async def handle_mixpanel_event(request: Request):
    """Handle Mixpanel events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        logger.info(f"Mixpanel Event from session {session_id}: {data.get('event')}")
        
        # Add proxy location to properties
        properties = data.get("properties", {})
        properties.update({
            "$country": request.app.state.settings.spoof_country_code,
            "$city": request.app.state.settings.proxy_city,
            "$region": request.app.state.settings.spoof_region,
            "$timezone": request.app.state.settings.spoof_timezone
        })
        
        modified_data = {
            **data,
            "properties": properties
        }
        
        return JSONResponse(content={
            "status": "tracked",
            "event": data.get("event"),
            "properties": properties
        })
        
    except Exception as e:
        logger.error(f"Mixpanel handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hotjar")
async def handle_hotjar_event(request: Request):
    """Handle Hotjar events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        logger.info(f"Hotjar Event from session {session_id}")
        
        # Hotjar will use proxy IP for location
        return JSONResponse(content={
            "status": "tracked",
            "session_id": session_id,
            "proxy_active": True
        })
        
    except Exception as e:
        logger.error(f"Hotjar handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom")
async def handle_custom_analytics(request: Request):
    """Handle custom analytics events"""
    
    try:
        data = await request.json()
        session_id = request.headers.get('X-Session-ID', 'unknown')
        
        tracker_name = data.get("tracker", "unknown")
        event_name = data.get("event", "unknown")
        
        logger.info(f"Custom Event [{tracker_name}] from session {session_id}: {event_name}")
        
        # Add proxy information
        modified_data = {
            **data,
            "proxy_info": {
                "country": request.app.state.settings.spoof_country_code,
                "city": request.app.state.settings.proxy_city,
                "timezone": request.app.state.settings.spoof_timezone,
                "language": request.app.state.settings.spoof_language
            }
        }
        
        return JSONResponse(content={
            "status": "tracked",
            "tracker": tracker_name,
            "event": event_name,
            "proxy_info": modified_data["proxy_info"]
        })
        
    except Exception as e:
        logger.error(f"Custom analytics handler error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_analytics_stats(request: Request):
    """Get analytics tracking statistics"""
    
    try:
        # This would normally fetch from a database
        # For now, return mock stats
        stats = {
            "total_events": 0,
            "events_by_type": {
                "ga4": 0,
                "adsense": 0,
                "facebook_pixel": 0,
                "mixpanel": 0,
                "hotjar": 0,
                "custom": 0
            },
            "proxy_country": request.app.state.settings.spoof_country_code,
            "proxy_city": request.app.state.settings.proxy_city
        }
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Get analytics stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

async def forward_to_ga4(data: Dict[str, Any]):
    """Forward event to actual GA4"""
    
    try:
        # GA4 Measurement Protocol endpoint
        url = "https://www.google-analytics.com/mp/collect"
        
        # Prepare payload
        payload = {
            "client_id": data.get("client_id"),
            "events": [{
                "name": data.get("event_name"),
                "params": data.get("params", {})
            }]
        }
        
        # Send to GA4
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"measurement_id": data.get("measurement_id")},
                json=payload
            )
            
        logger.debug(f"Forwarded to GA4: {response.status_code}")
        
    except Exception as e:
        logger.error(f"GA4 forwarding error: {str(e)}")


async def forward_to_facebook(data: Dict[str, Any]):
    """Forward event to Facebook Pixel"""
    
    try:
        # Facebook Conversions API endpoint
        url = f"https://graph.facebook.com/v18.0/{data.get('pixel_id')}/events"
        
        # Prepare payload
        payload = {
            "data": [{
                "event_name": data.get("event"),
                "event_time": data.get("timestamp"),
                "custom_data": data.get("custom_data", {}),
                "action_source": "website"
            }]
        }
        
        # Send to Facebook
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"access_token": data.get("access_token")},
                json=payload
            )
            
        logger.debug(f"Forwarded to Facebook: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Facebook forwarding error: {str(e)}")


def process_gtm_event(data: Dict[str, Any], settings) -> Dict[str, Any]:
    """Process and modify GTM event"""
    
    # Add geographic spoofing data
    modified = {
        **data,
        "geo_override": {
            "country": settings.spoof_country_code,
            "region": settings.spoof_region,
            "city": settings.proxy_city
        },
        "language_override": settings.spoof_language,
        "timezone_override": settings.spoof_timezone
    }
    
    return modified
