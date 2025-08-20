import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from config.settings import get_settings
    from app.core.app import app
    
    # Configure settings
    settings = get_settings()
    
    # Create required directories
    Path("logs").mkdir(exist_ok=True)
    Path("app/static").mkdir(parents=True, exist_ok=True)
    
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback to simple app
    from fastapi import FastAPI
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
