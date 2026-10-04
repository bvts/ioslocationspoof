# LocationControl — Real iOS Location Simulation Suite

A production-grade, hardware-level location simulation system for physical Apple iPhones (iPhone 11 through iPhone 16+, iOS 16.0 – 18.x+).

LocationControl communicates directly with Apple's internal developer service (`com.apple.dt.simulatelocation` / DVT RemoteXPC) to override the device's GNSS coordinates. The simulated coordinate is accepted device-wide by `locationd`, updating your location across Apple Maps, Google Maps, Tinder, Uber, Snapchat, Life360, and system frameworks.

---

## Architecture Overview

```text
┌─────────────────────────────────┐       Wi-Fi / LAN       ┌─────────────────────────────────┐
│     iPhone (Handheld App)       │ ──────────────────────► │      PC Companion Server        │
│                                 │   HTTP/REST (Port 8765) │                                 │
│  - SwiftUI Native MapKit UI     │                         │  - aiohttp Web & REST API       │
│  - Pin Selection & Search       │                         │  - Leaflet World Map UI         │
│  - Real-time Spoofing Status    │                         │  - Map Tile & Geocoding Proxy   │
└─────────────────────────────────┘                         └────────────────┬────────────────┘
                                                                             │
                                                                 USB Cable   │ Apple RemoteXPC
                                                              (Port 27015)   │ DVT SimulateLocation
                                                                             ▼
                                                            ┌─────────────────────────────────┐
                                                            │     Physical iPhone Hardware    │
                                                            │                                 │
                                                            │  - iOS Developer Mode           │
                                                            │  - locationd GPS Daemon         │
                                                            │  - All System Apps Updated      │
                                                            └─────────────────────────────────┘
```

---

## Supported Environment

- **Host Operating System:** Windows 10 or Windows 11 (64-bit), macOS 14+, or Linux.
- **Physical Device:** Any physical iPhone running **iOS 16.0 up to iOS 18.x+** (e.g. iPhone 13).
- **Physical Connection:** USB-to-Lightning / USB-C cable connected to host PC.
- **Host Runtime:** Python 3.10+ (Tested on Python 3.11.7).
- **Host Apple Software:** iTunes for Windows or Apple Devices app (provides the `Apple Mobile Device Service` / `usbmuxd` driver on TCP port 27015).

---

## Prerequisites

Before running the suite, ensure you have the following installed on your PC:

1. **Python 3.10 or newer:**  
   Download from [python.org](https://www.python.org/downloads/) (check the box *"Add python.exe to PATH"* during installation).

2. **Apple Mobile Device Support:**  
   Install **iTunes for Windows** (standalone installer from [apple.com](https://www.apple.com/itunes/) or Microsoft Store) or the **Apple Devices** app. This runs the background driver `usbmuxd.exe` that communicates with iOS over USB.

3. **Sideloadly (For iOS App Sideloading):**  
   Download from [sideloadly.io](https://sideloadly.io/) to install the `.ipa` onto your iPhone.

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Tofu4K/locationspooferapp.git locationcontrol
cd locationcontrol
```

### 2. Install PC Companion Dependencies
```powershell
pip install -r pc-controller/requirements.txt
pip install -e pc-controller
```

### 3. Configure Environment Variables
Copy the template configuration file:
```powershell
copy .env.example .env
```

---

## Map & Geocoding Configuration

The PC Companion includes an interactive dark-themed World Map UI. By default, it works out-of-the-box using free high-contrast CartoDB tiles and server-side proxied OpenStreetMap geocoding with **no API key required**.

If you wish to use a dedicated provider with custom quotas or vector styles, open `.env` and configure:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MAP_PROVIDER` | `carto` | Options: `carto`, `openstreetmap`, `geoapify`, `mapbox`, `stadia` |
| `MAP_API_KEY` | *(empty)* | Optional API key for Geoapify, Mapbox, or Stadia Maps |
| `MAP_TILE_URL` | *(empty)* | Custom tile layer URL template (supports `{z}`, `{x}`, `{y}`, `{apiKey}`) |
| `SERVER_HOST` | `0.0.0.0` | Bind IP address for companion server |
| `SERVER_PORT` | `8765` | TCP port for web UI and companion REST API |
| `PERSIST_SIMULATION_ON_EXIT`| `true` | If `true`, simulated GPS stays locked on iPhone when server closes |

### Supported Providers:
- **CartoDB (`carto` - Default):** Free, dark-themed raster tiles. No API key needed.
- **OpenStreetMap (`openstreetmap`):** Standard worldwide map tiles. No API key needed.
- **Geoapify (`geoapify`):** High-resolution dark tiles and fast geocoding. Get a free key at [geoapify.com](https://www.geoapify.com/).
- **Mapbox (`mapbox`):** Premium navigation tiles and places search. Get a free key at [mapbox.com](https://www.mapbox.com/).

---

## iPhone Setup (One-Time)

1. **Enable Developer Mode on iPhone:**
   - On your iPhone, open **Settings > Privacy & Security > Developer Mode**.
   - Toggle **Developer Mode ON**.
   - Tap **Restart** when prompted.
   - After reboot, unlock your iPhone and tap **Turn On**, then enter your device passcode.

2. **Trust Your Computer:**
   - Connect your iPhone to your PC with the USB cable.
   - Unlock the iPhone screen.
   - Tap **Trust This Computer** when prompted and enter your passcode.

3. **Verify Connection:**
   Run the diagnostics tool in PowerShell:
   ```powershell
   locationctl doctor
   ```
   Both `usbmuxd Daemon` and `Connected iOS Devices` should display `[OK]`.

---

## Running the Application

### Option A: 1-Click Launch (Recommended)
Double-click **`START_SERVER.bat`** in the project folder.

A window will open and display:
```text
============================================================
       LocationControl PC Companion Server Active
============================================================
 [+] Web Map UI:             http://localhost:8765
 [+] iPhone Companion API:   http://192.168.1.93:8765
============================================================
Leave this window open while using the iPhone app.
```

### Option B: Command Line Launch
```powershell
python -m locationctl serve
# or simply:
locationctl serve
```

---

## Controlling Location

### From Your iPhone (Handheld App)
1. Open the **LocationControl** app on your iPhone.
2. In Companion Setup, ensure the URL matches your PC's IP (e.g. `http://192.168.1.93:8765`).
3. Tap anywhere on the map or type an address in the search bar.
4. Tap **`SPOOF LOCATION`**.
5. The badge will turn green (**`• SPOOFING ACTIVE`**), and your physical iPhone GPS will immediately shift to that coordinate.

### From Your PC Browser (Web UI)
Open **`http://localhost:8765`** in Chrome, Edge, or Firefox. Click anywhere on the map and click **SPOOF**.

### Direct CLI Commands
You can also simulate coordinates directly without opening a browser:
```powershell
# Simulate Eiffel Tower, Paris
locationctl spoof --lat 48.8584 --lon 2.2945

# Query current hardware simulation status
locationctl status

# Restore device to genuine hardware GNSS GPS
locationctl clear
```

---

## Keeping the Spoof Active After Leaving Your House

To take your phone with you while retaining the fake location:

1. Connect your iPhone to your PC and spoof your desired location (**`• SPOOFING ACTIVE`**).
2. **DO NOT** tap "STOP" or "CLEAR".
3. **Simply unplug the USB cable from your iPhone.**
4. Apple's internal `locationd` daemon keeps the simulated coordinate locked in memory.
5. **Crucial:** Turn **OFF** Wi-Fi in your iPhone's **Settings > Wi-Fi** (not just Control Center). This prevents apps like Bump or Zenly from estimating your true location via nearby Wi-Fi router BSSIDs.
6. **To restore real GPS when you return:**
   - Plug back into the PC and tap **STOP**, OR
   - Simply **restart your iPhone** (power off and back on). iOS flushes developer overrides on reboot.

---

## iOS App Building & Sideloading

The iOS native companion is a pure Swift Package app located in `LocationControl/`.

### Automated GitHub Actions Build
The repository includes `.github/workflows/build-ipa.yml`, which compiles the native arm64 binary against the `iphoneos` SDK and packages `LocationControl.ipa` as an artifact on every push.

### Sideloading with Sideloadly
1. Download `LocationControl.ipa` from the latest GitHub Actions build artifact.
2. Open **Sideloadly** on your PC.
3. Connect your iPhone via USB.
4. Drag `LocationControl.ipa` into Sideloadly.
5. Enter your Apple ID and click **Start**.
6. On your iPhone: Go to **Settings > General > VPN & Device Management**, tap your Apple ID under Developer App, and tap **Trust**.

### Why Did the App Stop Opening After 7 Days?
> [!IMPORTANT]
> **Free Apple ID Certificate Expiration:**  
> Apple enforces a strict **7-day expiration** on provisioning profiles created with personal (free) Apple IDs.
> When 7 days pass, iOS will refuse to launch the app (the app crashes immediately on launch or displays *"LocationControl is No Longer Available"*).
> 
> **How to Fix (Takes 30 seconds):**  
> Simply plug your iPhone into your PC, open Sideloadly, drag `LocationControl.ipa` in, and click **Start**. Sideloadly will re-sign the app for another 7 days. None of your app settings or saved locations will be lost!

---

## Project Structure

```text
locationcontrol/
├── .github/
│   └── workflows/
│       └── build-ipa.yml         # Automated GitHub Actions iOS IPA build pipeline
├── pc-controller/                 # Python desktop companion suite
│   ├── src/locationctl/
│   │   ├── backend/              # Apple Developer Service (DVT RemoteXPC) interaction
│   │   ├── cli/                  # Command-line interface commands (serve, spoof, doctor)
│   │   ├── config/               # Settings manager with .env loading
│   │   ├── diagnostics/          # Doctor hardware and environment readiness checks
│   │   ├── protocol/             # Coordinate models and message types
│   │   ├── routes/               # Geo-math and GPX processing
│   │   ├── simulation/           # Simulation engine and pacing clocks
│   │   ├── transport/            # aiohttp web server, geocoding proxies, REST API
│   │   └── ui/                   # Dark-themed Leaflet World Map web interface
│   ├── tests/                    # Automated pytest suite (backend, server, config, math)
│   ├── pyproject.toml            # Modern Python package specification
│   ├── requirements.txt          # Pinned dependency requirements
│   └── .env.example              # Local environment configuration template
├── LocationControl/              # Native iOS companion application
│   ├── Package.swift             # Swift Package Manager manifest (iOS 17+)
│   ├── Info.plist                # App permissions, transport security, and icons
│   ├── Resources/                # Application icon assets (1024, 180, 120, 60)
│   └── Sources/
│       ├── LocationControlApp/   # SwiftUI Views (MapKit, WebController, Settings)
│       └── LocationControlCore/  # Pure core simulation logic and models
├── .env.example                  # Root environment configuration template
├── .gitignore                    # Comprehensive Python, Swift, IDE, and secret filters
├── HOW_TO_RUN.txt                # Plain-text quickstart & troubleshooting guide
├── START_SERVER.bat              # 1-click Windows launcher with auto-detected local IP
└── README.md                     # Comprehensive project documentation
```

---

## Troubleshooting Guide

### 1. `No iOS device detected via USB`
- **Cause:** The USB cable is unplugged, the screen is locked, or the computer is untrusted.
- **Fix:** Plug in your iPhone with the USB cable, unlock the screen, tap "Trust This Computer", and enter your passcode. Run `locationctl doctor` to verify.

### 2. `Apple Mobile Device Service / usbmuxd is stopped`
- **Cause:** The background Windows service for Apple devices is not active.
- **Fix:** Press `Win + R`, type `services.msc`, locate **Apple Mobile Device Service**, right-click, and select **Start** (or restart iTunes).

### 3. Map Geocoding or Search Fails / Rate Limited
- **Cause:** Direct public OpenStreetMap Nominatim queries are being rate-limited.
- **Fix:** Copy `.env.example` to `.env`, set `MAP_PROVIDER=geoapify` (or `mapbox`), and paste a free API key from [geoapify.com](https://www.geoapify.com/). All searches will route through your dedicated free quota.

### 4. `Port 8765 is already in use`
- **Cause:** Another instance of `locationctl` is running in the background.
- **Fix:** In PowerShell, run:
  ```powershell
  Get-Process -Name python | Stop-Process -Force
  ```
  Then double-click `START_SERVER.bat` again.

---

## Running Automated Tests

Run the complete test suite from the project root:

```powershell
pytest -v pc-controller/tests
```

All 20 test cases cover:
- Coordinate boundary validation (-90 to +90 lat, -180 to +180 lon)
- State transitions (DISCONNECTED, READY, SIMULATING)
- Hardware DVT session keepalive & reuse
- Server routes (`/`, `/api/config`, `/api/status`, `/api/devices`, `/api/geocode/*`, `/api/spoof`, `/api/clear`)
- Map provider tile generation and `.env` precedence
- Haversine distance and bearing calculations
- GPX route import/export

---

## Security & Secrets Policy

- **No Secrets in Source:** API keys and credentials should **never** be committed to version control. Always place keys in `.env` (which is excluded by `.gitignore`).
- **No Private Signing Material:** Never commit `.p12` certificates, private keys, or `.mobileprovision` files to the repository. Sideloadly generates temporary development certificates on demand.
- **Network Boundaries:** By default, `locationctl serve` binds to `0.0.0.0:8765` to enable communication with your iPhone on your private home network. Never expose port 8765 directly to the public internet without authentication.

---

## License

MIT License. Designed for authorized developer testing and QA location simulation on personal hardware.
