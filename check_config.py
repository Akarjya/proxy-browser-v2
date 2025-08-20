"""
Configuration Validator for Proxy Browser V2
Checks proxy settings and displays current configuration
"""

from config.settings import get_settings, ProxyConfig
from loguru import logger
import sys

def check_proxy_config():
    """Check and display proxy configuration"""
    
    print("🔍 Checking Proxy Configuration...")
    print("=" * 50)
    
    try:
        settings = get_settings()
        proxy_config = ProxyConfig(settings)
        
        print(f"✅ Settings loaded successfully!")
        print()
        
        print("📋 Current Configuration:")
        print(f"   Provider: {settings.proxy_provider}")
        print(f"   Type: {settings.proxy_type}")
        print(f"   Server: {settings.proxy_server}")
        print(f"   Username: {settings.proxy_username}")
        print(f"   Country: {settings.proxy_country}")
        print(f"   State: {settings.proxy_state}")
        print(f"   City: {settings.proxy_city}")
        print()
        
        print("🔌 Port Configuration:")
        for protocol, port in settings.proxy_ports.items():
            current = "✓" if settings.proxy_type == protocol else " "
            print(f"   [{current}] {protocol.upper()}: {port}")
        print()
        
        # Generate example URLs
        print("🌐 Example Proxy URLs:")
        for i, sticky_id in enumerate(settings.proxy_sticky_sessions[:3]):
            session_id = f"test-session-{i}"
            proxy_url = proxy_config.get_proxy_url(session_id)
            print(f"   Session {i+1}: {proxy_url}")
        print()
        
        # Check if ports match
        if settings.proxy_provider == "proxidise":
            expected_port = settings.proxy_ports.get(settings.proxy_type)
            actual_port = int(settings.proxy_server.split(':')[1])
            
            if actual_port != expected_port:
                print(f"⚠️  WARNING: Port mismatch!")
                print(f"   Expected {settings.proxy_type.upper()} port: {expected_port}")
                print(f"   Configured port: {actual_port}")
                print(f"   Update PROXY_SERVER in .env to: pg.proxi.es:{expected_port}")
            else:
                print(f"✅ Port configuration correct for {settings.proxy_type.upper()}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
        print("Make sure you have:")
        print("1. Created .env file from env.example")
        print("2. Installed dependencies: pip install -r requirements.txt")
        return False
    
    return True


if __name__ == "__main__":
    success = check_proxy_config()
    sys.exit(0 if success else 1)
