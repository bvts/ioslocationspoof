"""Unit tests for configuration manager."""

import tempfile
from pathlib import Path
from locationctl.config.manager import ConfigManager, AppConfig


def test_config_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_dir = Path(tmpdir)
        mgr = ConfigManager(config_dir=cfg_dir)

        assert mgr.config.default_speed_kmh == 50.0

        mgr.set("default_speed_kmh", 80.0)
        assert mgr.get("default_speed_kmh") == 80.0

        # Reload from disk
        mgr2 = ConfigManager(config_dir=cfg_dir)
        assert mgr2.get("default_speed_kmh") == 80.0

        mgr2.reset()
        assert mgr2.get("default_speed_kmh") == 50.0


def test_effective_tile_url_configurations():
    # Default Carto basemap
    cfg = AppConfig(map_provider="carto")
    assert "cartocdn.com" in cfg.effective_tile_url

    # OpenStreetMap
    cfg_osm = AppConfig(map_provider="openstreetmap")
    assert "tile.openstreetmap.org" in cfg_osm.effective_tile_url

    # Geoapify with API key
    cfg_geo = AppConfig(map_provider="geoapify", map_api_key="test_geo_key")
    assert "geoapify.com" in cfg_geo.effective_tile_url
    assert "apiKey=test_geo_key" in cfg_geo.effective_tile_url

    # Mapbox with API key
    cfg_mb = AppConfig(map_provider="mapbox", map_api_key="pk.test_mapbox_token")
    assert "mapbox.com" in cfg_mb.effective_tile_url
    assert "access_token=pk.test_mapbox_token" in cfg_mb.effective_tile_url

    # Custom tile URL template
    cfg_custom = AppConfig(map_tile_url="https://tiles.example.com/{z}/{x}/{y}.png?key={apiKey}", map_api_key="my_secret")
    assert cfg_custom.effective_tile_url == "https://tiles.example.com/{z}/{x}/{y}.png?key=my_secret"

