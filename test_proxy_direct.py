#!/usr/bin/env python3
"""
Direct proxy test script
Tests proxy connection without browser or complex setup
"""

import httpx
import asyncio
from loguru import logger

# Proxy configuration
PROXY_USERNAME = "KMwYgm4pR4upF6yX"
PROXY_PASSWORD = "pMBwu34BjjGr5urD"
PROXY_SERVER = "pg.proxi.es"
PROXY_PORT = 20000  # HTTP port
STICKY_ID = "Ecnik5GaH8"
PROXY_COUNTRY = "USA"
PROXY_STATE = "NY"
PROXY_CITY = "NewYorkCity"

async def test_proxy():
    """Test proxy connection directly"""
    
    # Build username with Proxidise format
    username_parts = [PROXY_USERNAME]
    username_parts.append(f"s-{STICKY_ID}")
    username_parts.append(f"co-{PROXY_COUNTRY}")
    username_parts.append(f"st-{PROXY_STATE}")
    username_parts.append(f"ci-{PROXY_CITY}")
    
    full_username = "-".join(username_parts)
    proxy_url = f"http://{full_username}:{PROXY_PASSWORD}@{PROXY_SERVER}:{PROXY_PORT}"
    
    logger.info(f"Testing proxy URL: {proxy_url}")
    
    # Create HTTP client with proxy
    async with httpx.AsyncClient(
        proxies={
            "http://": proxy_url,
            "https://": proxy_url
        },
        timeout=httpx.Timeout(30.0),
        verify=False
    ) as client:
        
        try:
            # Test 1: Simple IP check
            logger.info("Test 1: Checking IP via httpbin.org...")
            response = await client.get("http://httpbin.org/ip")
            logger.success(f"Response: {response.json()}")
            
            # Test 2: Check headers
            logger.info("\nTest 2: Checking headers via httpbin.org...")
            response = await client.get("http://httpbin.org/headers")
            headers = response.json()
            logger.info(f"Headers: {headers}")
            
            # Test 3: Try whatismyipaddress.com
            logger.info("\nTest 3: Trying whatismyipaddress.com...")
            response = await client.get(
                "https://www.whatismyipaddress.com/",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
            logger.success(f"Status: {response.status_code}")
            logger.info(f"Content length: {len(response.text)} bytes")
            
            # Check if we got blocked
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                logger.warning("Site might be blocking proxy access!")
            
        except httpx.TimeoutException:
            logger.error("Request timed out!")
        except httpx.ProxyError as e:
            logger.error(f"Proxy error: {e}")
        except Exception as e:
            logger.error(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy())
