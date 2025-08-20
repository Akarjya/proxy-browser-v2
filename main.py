"""
Main entry point for Proxy Browser V2
Run this file to start the application
"""

import asyncio
import uvicorn
from loguru import logger
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from app.core.app import app

settings = get_settings()

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format=settings.log_format,
    level=settings.log_level,
    colorize=True
)

if settings.log_file:
    logger.add(
        settings.log_file,
        format=settings.log_format,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip"
    )

def main():
    """Main function to run the application"""
    
    logger.info(f"""
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║            🌐 Proxy Browser V2 Starting 🌐           ║
    ║                                                      ║
    ║  Advanced Geographic Spoofing & Analytics Handling   ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    logger.info(f"Configuration:")
    logger.info(f"  • Host: {settings.host}:{settings.port}")
    logger.info(f"  • Proxy Country: {settings.proxy_country}")
    logger.info(f"  • Proxy City: {settings.proxy_city}")
    logger.info(f"  • Spoof Timezone: {settings.spoof_timezone}")
    logger.info(f"  • Debug Mode: {settings.debug}")
    
    # Create required directories
    Path("logs").mkdir(exist_ok=True)
    Path("app/static").mkdir(parents=True, exist_ok=True)
    
    # Run the application
    uvicorn.run(
        "app.core.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload or settings.hot_reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        sys.exit(1)

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
