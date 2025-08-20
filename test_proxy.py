"""
Test script to verify Proxidise SOCKS5 proxy configuration
"""

import asyncio
import httpx
from httpx_socks import AsyncProxyTransport
from config.settings import get_settings, ProxyConfig

async def test_proxy():
    """Test proxy connection and IP"""
    
    settings = get_settings()
    proxy_config = ProxyConfig(settings)
    
    # Generate proxy URL with sticky session
    session_id = "test-session-123"
    proxy_url = proxy_config.get_proxy_url(session_id)
    
    print(f"🔧 Proxy Configuration:")
    print(f"   Provider: {settings.proxy_provider}")
    print(f"   Type: {settings.proxy_type}")
    print(f"   Server: {settings.proxy_server}")
    print(f"   Country: {settings.proxy_country}")
    print(f"   State: {settings.proxy_state}")
    print(f"   City: {settings.proxy_city}")
    print(f"   Generated URL: {proxy_url}")
    print()
    
    # Test with httpx
    print("🌐 Testing proxy connection...")
    
    try:
        # Create SOCKS5 transport
        transport = AsyncProxyTransport.from_url(proxy_url)
        
        async with httpx.AsyncClient(transport=transport, verify=False) as client:
            # Check IP
            response = await client.get("https://ipapi.co/json/", timeout=30)
            data = response.json()
            
            print(f"✅ Proxy working!")
            print(f"   IP: {data.get('ip')}")
            print(f"   Country: {data.get('country_name')} ({data.get('country_code')})")
            print(f"   Region: {data.get('region')}")
            print(f"   City: {data.get('city')}")
            print(f"   Timezone: {data.get('timezone')}")
            print(f"   ISP: {data.get('org')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"   Make sure your proxy credentials are correct in .env file")


async def test_multiple_sessions():
    """Test multiple sessions with different sticky IDs"""
    
    settings = get_settings()
    proxy_config = ProxyConfig(settings)
    
    print("\n🔄 Testing multiple sessions with sticky IPs...")
    
    # Test 3 different sessions
    for i in range(3):
        session_id = f"user-session-{i}"
        proxy_url = proxy_config.get_proxy_url(session_id)
        
        print(f"\n📍 Session {i+1} (ID: {session_id}):")
        
        try:
            transport = AsyncProxyTransport.from_url(proxy_url)
            async with httpx.AsyncClient(transport=transport, verify=False) as client:
                response = await client.get("https://httpbin.org/ip", timeout=30)
                data = response.json()
                print(f"   IP: {data.get('origin')}")
                
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        await asyncio.sleep(1)  # Small delay between requests


if __name__ == "__main__":
    print("🚀 Proxidise SOCKS5 Proxy Test")
    print("=" * 50)
    
    # Run tests
    asyncio.run(test_proxy())
    asyncio.run(test_multiple_sessions())
