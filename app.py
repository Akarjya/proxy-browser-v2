from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Proxy Browser V2", version="2.0.0")

@app.get("/")
async def root():
    return {"message": "Proxy Browser V2 is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "proxy-browser-v2"}

@app.get("/ping")
async def ping():
    return {"pong": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
