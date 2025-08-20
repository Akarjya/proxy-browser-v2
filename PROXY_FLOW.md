# 🚀 Proxy Flow - Proxidise SOCKS5 Implementation

## 📊 Complete User Flow

### 1️⃣ **User Opens Browser (India)**
```
Real Location: Mumbai, India
Real IP: 203.0.113.45
Device: iPhone 13 (Mobile Safari)
```

### 2️⃣ **Connects to Your Server**
```
URL: http://localhost:8000
Protocol: WebSocket (ws://localhost:8000/ws/proxy)
```

### 3️⃣ **Session Creation**
```python
# Backend creates unique session
session_id = "abc-def-123"

# Assigns sticky proxy ID from pool
sticky_ids = ["Ecnik5GaH8", "sIIpXRcoJm", "PKzbgWiczO", ...]
assigned_sticky = sticky_ids[0]  # First user gets first ID
```

### 4️⃣ **Proxy URL Generation**
```
Base Username: KMwYgm4pR4upF6yX
Sticky Session: -s-Ecnik5GaH8
Country: -co-USA
State: -st-NY
City: -ci-NewYorkCity

Final: KMwYgm4pR4upF6yX-s-Ecnik5GaH8-co-USA-st-NY-ci-NewYorkCity
```

### 5️⃣ **SOCKS5 Connection**
```
Protocol: socks5://
Server: pg.proxi.es:20002  # SOCKS5 port (HTTP uses 20000)
Full URL: socks5://KMwYgm4pR4upF6yX-s-Ecnik5GaH8-co-USA-st-NY-ci-NewYorkCity:pMBwu34BjjGr5urD@pg.proxi.es:20002
```

#### ⚠️ **Important Port Information:**
- **HTTP Protocol**: Port 20000
- **SOCKS5 Protocol**: Port 20002
- **SOCKS4 Protocol**: Port 20001 (if supported)

### 6️⃣ **Request Flow**
```
User (India) → Your Server → SOCKS5 Proxy (USA) → Target Website
     ↓              ↓                ↓                    ↓
Real Device    WebSocket       USA IP Address      Sees USA User
```

### 7️⃣ **What Target Website Sees**
```
IP Address: 45.76.123.45 (USA)
Location: New York, NY, USA
Timezone: America/New_York (EST)
Language: en-US
Currency: USD
Device: iPhone 13 (Real device info preserved)
```

## 🔄 Session Persistence

### Same User Returns:
```python
# User comes back with same session_id
session_id = "abc-def-123"

# Gets same sticky ID
sticky_id = "Ecnik5GaH8"  # Same as before

# Result: Same USA IP address throughout session
```

### New User Connects:
```python
# New user gets new session
session_id = "xyz-789-456"

# Gets next sticky ID from pool
sticky_id = "sIIpXRcoJm"  # Second ID from list

# Result: Different USA IP, but also consistent
```

## 📱 Mobile-Specific Flow

### Touch Events:
```javascript
// User taps on mobile
touchEvent → WebSocket → Proxy → Website
         ↓
    Preserved as real touch
```

### Device Info:
```javascript
// Sent to server
{
    userAgent: "Mozilla/5.0 (iPhone...)",  // Real
    screenWidth: 390,                      // Real
    touchSupport: true,                    // Real
    // Geographic data spoofed later
}
```

## 🎯 Analytics Tracking

### Google Analytics Sees:
```
Country: United States
City: New York
Device: iPhone 13
Browser: Safari Mobile
Language: en-US
Currency: USD
```

### AdSense Sees:
```
Traffic Source: USA
Device Category: Mobile
Location: New York, NY
Result: USA ad rates (higher CPM)
```

## 🔐 Security Flow

### Real IP Protection:
```
1. User's real IP (India) → Only your server knows
2. Proxy IP (USA) → What websites see
3. No IP leaks via WebRTC (blocked)
4. No DNS leaks (routed through proxy)
```

### Session Security:
```
- Each session gets unique sticky ID
- Sessions expire after timeout
- Encrypted storage for sensitive data
- Rate limiting per session
```

## 📈 Performance Optimization

### Connection Pooling:
```
User 1 → Sticky ID 1 → Consistent IP
User 2 → Sticky ID 2 → Different consistent IP
User 3 → Sticky ID 3 → Another consistent IP
...
User 11 → Sticky ID 1 → Reuses first IP (round-robin)
```

### Caching:
```
First Request: Proxy → Website → Cache → User
Subsequent: Cache → User (faster)
```

## 🛠️ Troubleshooting Common Issues

### Issue: Different IP on each request
**Solution**: Ensure sticky session is enabled and session_id is consistent

### Issue: Proxy connection failed
**Solution**: Check SOCKS5 credentials and server status

### Issue: Geographic data not changing
**Solution**: Verify JavaScript injections are working

### Issue: Slow performance
**Solution**: Enable caching, reduce browser pool size

## 📊 Monitoring

### Check Proxy Status:
```bash
# Run test script
python test_proxy.py
```

### View Active Sessions:
```
GET /api/session/stats/all
```

### Check Current IP:
```
Click "Check IP" button in UI
```

---

**Remember**: Each user maintains the same USA IP throughout their session thanks to Proxidise sticky sessions!
