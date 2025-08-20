"""
Session API Routes
Handles session management endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
from loguru import logger

router = APIRouter()


@router.post("/create")
async def create_session(request: Request):
    """Create a new session"""
    
    try:
        session_manager = request.app.state.session_manager
        
        # Get real IP
        real_ip = request.client.host
        
        # Create session
        session = await session_manager.create_session(real_ip=real_ip)
        
        return JSONResponse(content={
            "session_id": session.id,
            "created_at": session.created_at.isoformat(),
            "proxy_country": session.proxy_country,
            "proxy_city": session.proxy_city
        })
        
    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}")
async def get_session(request: Request, session_id: str):
    """Get session information"""
    
    try:
        session_manager = request.app.state.session_manager
        session = await session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return JSONResponse(content=session.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/device-info")
async def update_device_info(request: Request, session_id: str):
    """Update device information for session"""
    
    try:
        session_manager = request.app.state.session_manager
        device_info = await request.json()
        
        await session_manager.update_device_info(session_id, device_info)
        
        return JSONResponse(content={"status": "updated"})
        
    except Exception as e:
        logger.error(f"Device info update error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/cookies")
async def update_cookies(request: Request, session_id: str):
    """Update cookies for session"""
    
    try:
        session_manager = request.app.state.session_manager
        cookies = await request.json()
        
        await session_manager.update_cookies(session_id, cookies)
        
        return JSONResponse(content={"status": "updated"})
        
    except Exception as e:
        logger.error(f"Cookie update error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/storage")
async def update_storage(request: Request, session_id: str):
    """Update local/session storage"""
    
    try:
        session_manager = request.app.state.session_manager
        data = await request.json()
        
        storage_type = data.get("type", "local")
        storage_data = data.get("data", {})
        
        await session_manager.update_storage(
            session_id, storage_type, storage_data
        )
        
        return JSONResponse(content={"status": "updated"})
        
    except Exception as e:
        logger.error(f"Storage update error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/history")
async def get_history(request: Request, session_id: str):
    """Get browsing history for session"""
    
    try:
        session_manager = request.app.state.session_manager
        history = await session_manager.get_session_history(session_id)
        
        return JSONResponse(content={"history": history})
        
    except Exception as e:
        logger.error(f"Get history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def end_session(request: Request, session_id: str):
    """End a session"""
    
    try:
        session_manager = request.app.state.session_manager
        await session_manager.end_session(session_id)
        
        return JSONResponse(content={"status": "ended"})
        
    except Exception as e:
        logger.error(f"End session error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/all")
async def get_session_stats(request: Request):
    """Get session statistics"""
    
    try:
        session_manager = request.app.state.session_manager
        stats = session_manager.get_session_stats()
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        logger.error(f"Get stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
