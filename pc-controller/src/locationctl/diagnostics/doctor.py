"""Diagnostic checks for host OS, Python runtime, tooling, networking, and devices."""

import sys
import platform
import shutil
import socket
from typing import Dict, List, Any
from pydantic import BaseModel
from ..protocol.models import PROTOCOL_VERSION


class DiagnosticItem(BaseModel):
    name: str
    status: str  # OK, WARN, FAIL, INFO
    detail: str
    recommendation: str = ""


class DiagnosticReport(BaseModel):
    platform: str
    python_version: str
    protocol_version: int
    items: List[DiagnosticItem]


class Doctor:
    """Performs system diagnostic scans for locationctl."""

    @staticmethod
    def run_checks() -> DiagnosticReport:
        items: List[DiagnosticItem] = []

        # 1. OS & Runtime Check
        os_name = f"{platform.system()} {platform.release()}"
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 10):
            items.append(
                DiagnosticItem(
                    name="Python Runtime",
                    status="OK",
                    detail=f"Python {py_ver} (meets >=3.10 requirement)",
                )
            )
        else:
            items.append(
                DiagnosticItem(
                    name="Python Runtime",
                    status="WARN",
                    detail=f"Python {py_ver} (Python 3.10+ recommended)",
                    recommendation="Upgrade to Python 3.10 or later.",
                )
            )

        # 2. pymobiledevice3 Library Check
        try:
            import pymobiledevice3
            items.append(
                DiagnosticItem(
                    name="Device Communication Stack",
                    status="OK",
                    detail=f"pymobiledevice3 installed at {pymobiledevice3.__file__}",
                )
            )
        except ImportError:
            items.append(
                DiagnosticItem(
                    name="Device Communication Stack",
                    status="FAIL",
                    detail="pymobiledevice3 is not installed",
                    recommendation="Run 'pip install pymobiledevice3' to enable iOS hardware communication.",
                )
            )

        # 3. usbmuxd (Port 27015) Connectivity Check
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            mux_res = sock.connect_ex(("127.0.0.1", 27015))
            sock.close()
            if mux_res == 0:
                items.append(
                    DiagnosticItem(
                        name="usbmuxd Daemon (Port 27015)",
                        status="OK",
                        detail="usbmuxd is actively listening for iOS USB devices",
                    )
                )
            else:
                items.append(
                    DiagnosticItem(
                        name="usbmuxd Daemon (Port 27015)",
                        status="WARN",
                        detail="usbmuxd is not listening on port 27015",
                        recommendation=(
                            "On Windows: Start 'Apple Mobile Device Service' via Services or launch iTunes. "
                            "On macOS: native usbmuxd runs automatically."
                        ),
                    )
                )
        except Exception as e:
            items.append(
                DiagnosticItem(
                    name="usbmuxd Check",
                    status="WARN",
                    detail=f"Error testing port 27015: {e}",
                )
            )

        # 4. Web & Bridge Port (8765) Availability
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", 8765))
            sock.close()
            if result == 0:
                items.append(
                    DiagnosticItem(
                        name="Companion Bridge Port (8765)",
                        status="INFO",
                        detail="Port 8765 is actively listening (server daemon running)",
                    )
                )
            else:
                items.append(
                    DiagnosticItem(
                        name="Companion Bridge Port (8765)",
                        status="OK",
                        detail="Port 8765 is available for local Map UI / API server",
                    )
                )
        except Exception as e:
            items.append(
                DiagnosticItem(
                    name="Network Socket",
                    status="WARN",
                    detail=f"Socket check error: {e}",
                )
            )

        # 5. Apple Tooling / Platform Check
        if platform.system() == "Darwin":
            xcrun_path = shutil.which("xcrun")
            if xcrun_path:
                items.append(
                    DiagnosticItem(
                        name="Xcode CLI (xcrun)",
                        status="OK",
                        detail=f"Found at {xcrun_path}",
                    )
                )
            else:
                items.append(
                    DiagnosticItem(
                        name="Xcode CLI (xcrun)",
                        status="WARN",
                        detail="xcrun not found in PATH",
                        recommendation="Install Xcode Command Line Tools via 'xcode-select --install'.",
                    )
                )
        else:
            items.append(
                DiagnosticItem(
                    name="Host Platform",
                    status="INFO",
                    detail=f"Host OS: {platform.system()}. Pure-Python userspace developer simulation enabled.",
                )
            )

        # 6. Physical Device Enumeration
        try:
            from ..backend.developer_service import DeveloperServiceBackend
            backend = DeveloperServiceBackend()
            devices = backend.list_devices_sync()

            if devices:
                dev_str = ", ".join(f"{d.name} ({d.udid[:8]}...)" for d in devices)
                items.append(
                    DiagnosticItem(
                        name="Connected iOS Devices",
                        status="OK",
                        detail=f"{len(devices)} device(s) detected: {dev_str}",
                    )
                )
            else:
                items.append(
                    DiagnosticItem(
                        name="Connected iOS Devices",
                        status="INFO",
                        detail="No iOS device currently connected via USB or usbmuxd not running.",
                        recommendation="Plug in iPhone 13 via USB and ensure screen is unlocked.",
                    )
                )
        except Exception as e:
            items.append(
                DiagnosticItem(
                    name="Device Check",
                    status="WARN",
                    detail=f"Device enumeration check failed: {e}",
                )
            )

        # 7. Map & Geocoding Configuration
        try:
            from ..config.manager import ConfigManager
            cfg = ConfigManager().config
            provider = (cfg.map_provider or "carto").lower()
            if provider in ("geoapify", "mapbox", "stadia") and not cfg.map_api_key:
                items.append(
                    DiagnosticItem(
                        name="Map & Geocoding",
                        status="WARN",
                        detail=f"Provider '{provider}' selected but MAP_API_KEY is not set in .env",
                        recommendation=f"Add MAP_API_KEY=your_key to .env or switch MAP_PROVIDER=carto for free tiles.",
                    )
                )
            else:
                has_key_str = " (API Key active)" if cfg.map_api_key else " (Free / No key required)"
                items.append(
                    DiagnosticItem(
                        name="Map & Geocoding",
                        status="OK",
                        detail=f"Provider: {provider}{has_key_str}",
                    )
                )
        except Exception as e:
            items.append(
                DiagnosticItem(
                    name="Map Configuration",
                    status="WARN",
                    detail=f"Could not verify map configuration: {e}",
                )
            )

        return DiagnosticReport(
            platform=os_name,
            python_version=py_ver,
            protocol_version=PROTOCOL_VERSION,
            items=items,
        )
