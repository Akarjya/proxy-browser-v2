"""
Main entry point for Proxy Browser V2
Run this file to start the application
"""

from fastapi import FastAPI
import os

app = FastAPI(title="Proxy Browser V2")

@app.get("/")
def root():
    return {"message": "Proxy Browser V2 is running"}

@app.get("/ping")
def ping():
    return {"pong": True}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "proxy-browser-v2"}

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Get port from environment variable or default to 8000
    port_str = os.environ.get("PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        print(f"Invalid PORT value: {port_str}, using default 8000")
        port = 8000
    
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
