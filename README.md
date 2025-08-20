# 🌐 Proxy Browser V2 - Advanced Geographic Spoofing System

A sophisticated proxy browser with **WebSocket-based real-time communication**, **smart content rewriting**, and **comprehensive tracker handling** for GA4, AdSense, Facebook Pixel, and more. Perfect for mobile users who need to appear as if browsing from a different country.

## 🚀 Key Features

### Core Capabilities
- **🔄 Hybrid WebSocket + HTTP Proxy**: Real-time bidirectional communication
- **🌍 Geographic Spoofing**: Complete location masking (IP, timezone, language, GPS)
- **📱 Mobile-First Design**: Optimized for mobile devices with touch support
- **📊 Analytics Tracker Handling**: Smart handling of GA4, AdSense, Facebook Pixel
- **🎯 Device Fingerprint Preservation**: Maintains real device characteristics
- **⚡ Browser Pool Management**: Efficient resource usage with Playwright
- **🔐 Session Persistence**: Cookies, localStorage, and history management
- **🛡️ Security Features**: Rate limiting, CORS, CSP headers

### Advanced Features
- **Smart Content Rewriting**: Automatic URL, JavaScript, and CSS rewriting
- **JavaScript Injection**: Geographic spoofing at the browser level
- **WebRTC Leak Prevention**: Prevents IP leaks through WebRTC
- **Canvas Fingerprinting Protection**: Adds noise to prevent tracking
- **Battery API Spoofing**: Masks battery status
- **Touch Event Optimization**: Native mobile touch handling

## 📋 How It Works

```
Mobile User (India) → Your Server → USA Proxy → Target Site
     ↓                    ↓              ↓
Real Device Info    Geographic Swap   USA User Profile
```

### What Trackers See:
- **Google Analytics**: USA visitor with real device
- **AdSense**: USA traffic for higher CPM rates
- **Facebook Pixel**: USA user demographics
- **Other Trackers**: Consistent USA location data

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Node.js (for Playwright browsers)
- Redis (optional, for session persistence)

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/proxy-browser-v2.git
cd proxy-browser-v2
```

### Step 2: Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Step 3: Configure Environment
```bash
# Copy environment template
cp env.example .env

# Edit .env with your proxy credentials
nano .env
```

Update these key settings in `.env`:
```env
PROXY_USERNAME="your-proxy-username"
PROXY_PASSWORD="your-proxy-password"
PROXY_SERVER="proxy-server:port"
PROXY_COUNTRY="USA"
PROXY_CITY="NewYorkCity"
```

### Step 4: Run the Application
```bash
python main.py
```

The application will start on `http://localhost:8000`

## 🎯 Usage

### Basic Navigation
1. Open `http://localhost:8000` in your browser
2. Enter a URL in the address bar
3. Click "Navigate" or press Enter
4. The site will load through the proxy with geographic spoofing

### Check Your IP
1. Click the "Check IP" button
2. The browser will navigate to an IP checking website
3. You'll see the proxy country's IP instead of your real IP

### Mobile Usage
- Works seamlessly on mobile browsers
- Touch events are preserved
- Mobile viewport is maintained
- Device characteristics remain real

## 🔧 Configuration

### Proxy Settings
Configure your proxy provider in `.env`:
```env
PROXY_PROVIDER="your-provider"
PROXY_USERNAME="username"
PROXY_PASSWORD="password"
PROXY_SERVER="server:port"
PROXY_COUNTRY="USA"
PROXY_CITY="NewYorkCity"
```

### Geographic Spoofing
Customize the spoofed location:
```env
SPOOF_TIMEZONE="America/New_York"
SPOOF_LANGUAGE="en-US"
SPOOF_COUNTRY_CODE="US"
SPOOF_LATITUDE=40.7128
SPOOF_LONGITUDE=-74.0060
```

### Browser Pool
Adjust browser pool settings:
```env
BROWSER_POOL_SIZE=10
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=30000
```

### Performance Tuning
```env
CACHE_TTL=300
RATE_LIMIT_REQUESTS=100
WORKERS=4
```

## 📊 Analytics & Tracking

### Supported Trackers
- ✅ Google Analytics 4 (GA4)
- ✅ Google Tag Manager (GTM)
- ✅ Google AdSense
- ✅ Facebook Pixel
- ✅ Mixpanel
- ✅ Hotjar
- ✅ Custom Analytics

### How Trackers Are Handled
1. **IP Address**: Shows proxy country IP
2. **Timezone**: Reports spoofed timezone
3. **Language**: Uses target country language
4. **Geolocation**: Returns spoofed coordinates
5. **Device Info**: Preserves real device characteristics

## 🏗️ Architecture

### Component Overview
```
┌─────────────────────────────────────┐
│         Frontend (HTML/JS)          │
│    WebSocket Client + UI Controls   │
└──────────────┬──────────────────────┘
               │ WebSocket
┌──────────────▼──────────────────────┐
│        FastAPI Application          │
│   WebSocket Handler + HTTP Routes   │
└──────────────┬──────────────────────┘
               │
     ┌─────────┴─────────┬─────────────┬──────────────┐
     │                   │             │              │
┌────▼─────┐    ┌────────▼──────┐ ┌───▼────┐  ┌──────▼──────┐
│  Proxy   │    │Content Rewriter│ │Browser │  │   Session   │
│ Service  │    │   HTML/JS/CSS  │ │  Pool  │  │   Manager   │
└──────────┘    └────────────────┘ └────────┘  └─────────────┘
```

### Key Components
- **WebSocket Manager**: Handles real-time communication
- **Proxy Service**: Routes requests through proxy
- **Content Rewriter**: Modifies HTML/JS/CSS content
- **Browser Pool**: Manages Playwright browser instances
- **Session Manager**: Handles user sessions and storage

## 🚀 API Endpoints

### WebSocket
- `/ws/proxy` - Main WebSocket endpoint for browsing

### HTTP Endpoints
- `/api/proxy/` - Proxy HTTP requests
- `/api/proxy/check-ip` - Check current proxy IP
- `/api/session/create` - Create new session
- `/api/session/{id}` - Get session info
- `/api/analytics/*` - Analytics tracking endpoints

## 🔒 Security

### Implemented Security Measures
- **Rate Limiting**: Prevents abuse
- **CORS Headers**: Controlled cross-origin access
- **CSP Headers**: Content Security Policy
- **XSS Protection**: Input sanitization
- **WebRTC Leak Prevention**: IP leak protection
- **Session Encryption**: Encrypted session storage

## 🐛 Troubleshooting

### Common Issues

#### WebSocket Connection Failed
- Check if the server is running
- Verify firewall settings
- Ensure correct WebSocket URL

#### Proxy Not Working
- Verify proxy credentials in `.env`
- Check proxy server connectivity
- Ensure proxy supports your target country

#### Browser Pool Errors
- Run `playwright install chromium`
- Check system resources
- Reduce `BROWSER_POOL_SIZE` if needed

## 📈 Performance Tips

1. **Enable Caching**: Set `ENABLE_CACHE=true`
2. **Adjust Pool Size**: Balance between performance and resources
3. **Use Redis**: For better session persistence
4. **Enable Compression**: Reduces bandwidth usage
5. **Optimize Images**: Use CDN for static assets

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This tool is for educational and legitimate purposes only. Users are responsible for complying with all applicable laws and terms of service of websites they visit. The authors are not responsible for any misuse of this software.

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Read the documentation thoroughly

## 🔮 Future Enhancements

- [ ] Multiple proxy country support
- [ ] Advanced fingerprinting options
- [ ] Browser extension support
- [ ] API for programmatic access
- [ ] Dashboard with analytics
- [ ] Automated proxy rotation
- [ ] Cloud deployment templates

---

**Made with ❤️ for the privacy-conscious internet user**
