"""Unified HTTP REST and WebSocket companion server for iOS Location Simulation."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional, Set
from urllib.parse import quote

import aiohttp
from aiohttp import web
import websockets

from ..backend.base import SimulationBackend
from ..backend.developer_service import DeveloperServiceBackend
from ..config.manager import ConfigManager

logger = logging.getLogger("locationctl.transport.server")

# Default HTTP User-Agent for compliant OpenStreetMap / Nominatim access
DEFAULT_USER_AGENT = "LocationControl-Companion/1.0 (https://github.com/Tofu4K/locationspooferapp)"


@web.middleware
async def cors_middleware(request: web.Request, handler):
    """Enable CORS for local network and mobile WebView clients."""
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def create_app(
    backend: Optional[SimulationBackend] = None,
    config_mgr: Optional[ConfigManager] = None
) -> web.Application:
    """Create the aiohttp web application serving UI, configuration, and REST API."""
    if backend is None:
        backend = DeveloperServiceBackend()
    if config_mgr is None:
        config_mgr = ConfigManager()

    config = config_mgr.config
    app = web.Application(middlewares=[cors_middleware])
    ui_dir = Path(__file__).parent.parent / "ui"
    index_file = ui_dir / "index.html"

    # Persistent HTTP client session for proxying geocode queries cleanly
    client_session_holder = {"session": None}

    async def get_client_session() -> aiohttp.ClientSession:
        if client_session_holder["session"] is None or client_session_holder["session"].closed:
            client_session_holder["session"] = aiohttp.ClientSession(
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=8.0)
            )
        return client_session_holder["session"]

    async def handle_index(request: web.Request) -> web.Response:
        if index_file.exists():
            return web.FileResponse(index_file)
        return web.Response(text="LocationControl UI not found.", status=404)

    async def handle_get_config(request: web.Request) -> web.Response:
        """Expose public configuration for the Map UI."""
        return web.json_response({
            "map_provider": config.map_provider,
            "tile_url": config.effective_tile_url,
            "has_api_key": bool(config.map_api_key),
            "server_host": config.server_host,
            "server_port": config.server_port,
            "persist_on_exit": config.persist_simulation_on_exit,
        })

    async def handle_get_status(request: web.Request) -> web.Response:
        status = await backend.get_status()
        return web.json_response(status.model_dump())

    async def handle_get_devices(request: web.Request) -> web.Response:
        devices = await backend.list_devices()
        return web.json_response([d.model_dump() for d in devices])

    async def handle_post_spoof(request: web.Request) -> web.Response:
        try:
            data = await request.json()
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
        except Exception as e:
            return web.json_response({"success": False, "message": f"Invalid coordinate payload: {e}"}, status=400)

        result = await backend.set_location(latitude=lat, longitude=lon)
        return web.json_response(result.model_dump())

    async def handle_post_clear(request: web.Request) -> web.Response:
        result = await backend.clear_location()
        return web.json_response(result.model_dump())

    async def handle_geocode_search(request: web.Request) -> web.Response:
        """Server-side geocoding search proxy to avoid browser CORS and User-Agent restrictions."""
        query = request.query.get("q", "").strip()
        if not query:
            return web.json_response({"success": False, "error": "EMPTY_QUERY", "message": "Query parameter 'q' is required."}, status=400)

        session = await get_client_session()
        provider = (config.map_provider or "carto").lower()
        api_key = config.map_api_key

        results = []
        try:
            if provider == "geoapify" and api_key:
                url = f"https://api.geoapify.com/v1/geocode/search?text={quote(query)}&apiKey={api_key}&limit=5"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for feat in data.get("features", []):
                            props = feat.get("properties", {})
                            results.append({
                                "name": props.get("formatted") or props.get("address_line1") or query,
                                "lat": float(props.get("lat", 0.0)),
                                "lon": float(props.get("lon", 0.0)),
                            })
                    elif resp.status in (401, 403):
                        return web.json_response({
                            "success": False,
                            "error": "MAP_API_KEY_INVALID",
                            "message": "Geoapify authentication failed. Check MAP_API_KEY in your .env file."
                        }, status=resp.status)

            elif provider == "mapbox" and api_key:
                url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json?access_token={api_key}&limit=5"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for feat in data.get("features", []):
                            center = feat.get("center", [0.0, 0.0])
                            results.append({
                                "name": feat.get("place_name") or query,
                                "lat": float(center[1]),
                                "lon": float(center[0]),
                            })
                    elif resp.status in (401, 403):
                        return web.json_response({
                            "success": False,
                            "error": "MAP_API_KEY_INVALID",
                            "message": "Mapbox authentication failed. Check MAP_API_KEY in your .env file."
                        }, status=resp.status)

            # Default fallback: OpenStreetMap Nominatim with compliant User-Agent
            if not results:
                url = f"https://nominatim.openstreetmap.org/search?format=json&q={quote(query)}&limit=5"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data:
                            results.append({
                                "name": item.get("display_name", query),
                                "lat": float(item.get("lat", 0.0)),
                                "lon": float(item.get("lon", 0.0)),
                            })
                    elif resp.status == 403:
                        return web.json_response({
                            "success": False,
                            "error": "RATE_LIMITED",
                            "message": "OpenStreetMap geocoding rate limited. Provide a MAP_API_KEY in your .env file (e.g. Geoapify or Mapbox) for dedicated quota."
                        }, status=429)

            return web.json_response({"success": True, "results": results})

        except Exception as e:
            logger.warning(f"Geocoding search failed: {e}")
            return web.json_response({
                "success": False,
                "error": "GEOCODE_ERROR",
                "message": f"Geocoding service unavailable: {e}. Check internet connection or MAP_API_KEY in .env."
            }, status=502)

    async def handle_geocode_reverse(request: web.Request) -> web.Response:
        """Server-side reverse geocoding proxy to convert (lat, lon) into human-readable address."""
        try:
            lat = float(request.query.get("lat", "0"))
            lon = float(request.query.get("lon", "0"))
        except (TypeError, ValueError):
            return web.json_response({"success": False, "error": "INVALID_COORDINATES", "message": "Valid 'lat' and 'lon' query parameters are required."}, status=400)

        session = await get_client_session()
        provider = (config.map_provider or "carto").lower()
        api_key = config.map_api_key

        try:
            if provider == "geoapify" and api_key:
                url = f"https://api.geoapify.com/v1/geocode/reverse?lat={lat}&lon={lon}&apiKey={api_key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        features = data.get("features", [])
                        if features:
                            props = features[0].get("properties", {})
                            name = props.get("formatted") or props.get("address_line1") or f"{lat:.4f}, {lon:.4f}"
                            return web.json_response({"success": True, "name": name, "lat": lat, "lon": lon})
                    elif resp.status in (401, 403):
                        return web.json_response({
                            "success": False,
                            "error": "MAP_API_KEY_INVALID",
                            "message": "Geoapify key invalid. Check MAP_API_KEY in .env."
                        }, status=resp.status)

            # Default fallback: Nominatim reverse geocode
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    name = data.get("display_name", f"{lat:.4f}, {lon:.4f}")
                    return web.json_response({"success": True, "name": name, "lat": lat, "lon": lon})
                else:
                    return web.json_response({"success": True, "name": f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon})

        except Exception as e:
            logger.debug(f"Reverse geocode fallback: {e}")
            return web.json_response({"success": True, "name": f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon})

    async def on_cleanup(app_instance):
        # Close internal HTTP client session
        if client_session_holder["session"] and not client_session_holder["session"].closed:
            await client_session_holder["session"].close()

        # Only clear simulation if persist_simulation_on_exit is explicitly disabled
        if not config.persist_simulation_on_exit:
            try:
                await backend.clear_location()
            except Exception:
                pass

    app.on_cleanup.append(on_cleanup)

    # Routes
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/config", handle_get_config)
    app.router.add_get("/api/status", handle_get_status)
    app.router.add_get("/api/devices", handle_get_devices)
    app.router.add_get("/api/geocode/search", handle_geocode_search)
    app.router.add_get("/api/geocode/reverse", handle_geocode_reverse)
    app.router.add_post("/api/spoof", handle_post_spoof)
    app.router.add_post("/api/clear", handle_post_clear)

    return app


def _get_local_ip() -> str:
    """Attempt to detect the primary local IP on the local subnet."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_server(host: str = "0.0.0.0", port: int = 8765, backend: Optional[SimulationBackend] = None):
    """Run the web and REST server synchronously."""
    local_ip = _get_local_ip()
    print("=" * 60)
    print("       LocationControl PC Companion Server Active")
    print("=" * 60)
    print(f" [+] Web Map UI:             http://localhost:{port}")
    print(f" [+] iPhone Companion API:   http://{local_ip}:{port}")
    print("=" * 60)
    print("Leave this window open while using the iPhone app.\n")
    app = create_app(backend=backend)
    web.run_app(app, host=host, port=port)

