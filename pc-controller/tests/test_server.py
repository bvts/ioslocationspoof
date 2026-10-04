"""Unit tests for the web and REST server endpoints."""

import pytest
from aiohttp.test_utils import TestClient, TestServer
from locationctl.transport.server import create_app
from locationctl.backend.developer_service import DeveloperServiceBackend


@pytest.mark.asyncio
async def test_server_routes():
    backend = DeveloperServiceBackend()
    app = create_app(backend=backend)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        # Test GET /
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "iOS Location Control" in text

        # Test GET /api/status
        resp = await client.get("/api/status")
        assert resp.status == 200
        data = await resp.json()
        assert "state" in data

        # Test GET /api/devices
        resp = await client.get("/api/devices")
        assert resp.status == 200
        devices = await resp.json()
        assert isinstance(devices, list)

        # Test POST /api/spoof with invalid bounds
        resp = await client.post("/api/spoof", json={"lat": 100.0, "lon": 50.0})
        assert resp.status == 200
        res_data = await resp.json()
        assert res_data["success"] is False
        assert res_data["error"] == "LATITUDE_OUT_OF_BOUNDS"

        # Test GET /api/config
        resp = await client.get("/api/config")
        assert resp.status == 200
        config_data = await resp.json()
        assert "tile_url" in config_data
        assert "map_provider" in config_data
        assert "has_api_key" in config_data

        # Test GET /api/geocode/search with empty query
        resp = await client.get("/api/geocode/search?q=")
        assert resp.status == 400

        # Test GET /api/geocode/reverse with invalid coordinates
        resp = await client.get("/api/geocode/reverse?lat=invalid&lon=invalid")
        assert resp.status == 400

        # Test POST /api/clear
        resp = await client.post("/api/clear")
        assert resp.status == 200
        clear_data = await resp.json()
        assert clear_data["success"] is True
    finally:
        await client.close()
