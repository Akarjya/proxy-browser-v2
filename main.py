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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
