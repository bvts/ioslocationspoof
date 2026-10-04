"""Configuration manager for locationctl with .env and JSON persistence."""

from pathlib import Path
import json
import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field
from ..protocol.models import SimulationSettings, SpeedUnit, AccelerationProfile

# Automatically discover and load .env files
_dotenv_path = find_dotenv(usecwd=True)
if _dotenv_path:
    load_dotenv(_dotenv_path)
else:
    for candidate in [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]:
        if candidate.exists():
            load_dotenv(candidate)
            break


class AppConfig(BaseModel):
    default_speed_kmh: float = 50.0
    speed_unit: SpeedUnit = SpeedUnit.KMH
    default_acceleration: AccelerationProfile = AccelerationProfile.NORMAL
    simulate_stops: bool = True
    server_port: int = Field(default_factory=lambda: int(os.getenv("SERVER_PORT", os.getenv("PORT", "8765"))))
    server_host: str = Field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
    companion_device_ip: str = "127.0.0.1"
    companion_device_port: int = 8765

    # Map & Geocoding configuration
    map_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("MAP_API_KEY") or None)
    map_provider: str = Field(default_factory=lambda: os.getenv("MAP_PROVIDER", "carto").lower())
    map_tile_url: Optional[str] = Field(default_factory=lambda: os.getenv("MAP_TILE_URL") or None)
    persist_simulation_on_exit: bool = Field(
        default_factory=lambda: os.getenv("PERSIST_SIMULATION_ON_EXIT", "true").lower() in ("true", "1", "yes")
    )

    @property
    def effective_tile_url(self) -> str:
        """Returns the tile layer URL template configured for the active provider."""
        if self.map_tile_url:
            url = self.map_tile_url
            if self.map_api_key:
                url = url.replace("{apiKey}", self.map_api_key).replace("{access_token}", self.map_api_key)
            return url

        provider = (self.map_provider or "carto").lower()
        if provider == "geoapify" and self.map_api_key:
            return f"https://maps.geoapify.com/v1/tile/dark-matter/{{z}}/{{x}}/{{y}}.png?apiKey={self.map_api_key}"
        elif provider == "mapbox" and self.map_api_key:
            return f"https://api.mapbox.com/styles/v1/mapbox/dark-v11/tiles/{{z}}/{{x}}/{{y}}?access_token={self.map_api_key}"
        elif provider == "stadia" and self.map_api_key:
            return f"https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{{z}}/{{x}}/{{y}}{{r}}.png?api_key={self.map_api_key}"
        elif provider == "openstreetmap":
            return "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        else:
            # Default: CartoDB Dark Matter basemap (reliable, high-contrast dark theme)
            return "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"


class ConfigManager:
    """Manages persistent JSON configuration merged with environment variables."""

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            self.config_dir = Path.home() / ".locationctl"
        else:
            self.config_dir = config_dir
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_dir()
        self.config = self.load()

    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        data: Dict[str, Any] = {}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        # Environment variables take precedence for deployment & credential settings
        if os.getenv("MAP_API_KEY"):
            data["map_api_key"] = os.getenv("MAP_API_KEY")
        if os.getenv("MAP_PROVIDER"):
            data["map_provider"] = os.getenv("MAP_PROVIDER")
        if os.getenv("MAP_TILE_URL"):
            data["map_tile_url"] = os.getenv("MAP_TILE_URL")
        if os.getenv("SERVER_PORT") or os.getenv("PORT"):
            data["server_port"] = int(os.getenv("SERVER_PORT", os.getenv("PORT", "8765")))
        if os.getenv("SERVER_HOST"):
            data["server_host"] = os.getenv("SERVER_HOST")
        if os.getenv("PERSIST_SIMULATION_ON_EXIT"):
            data["persist_simulation_on_exit"] = os.getenv("PERSIST_SIMULATION_ON_EXIT").lower() in ("true", "1", "yes")

        try:
            return AppConfig(**data)
        except Exception:
            return AppConfig()

    def save(self):
        self._ensure_config_dir()
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config.model_dump(), f, indent=2)

    def get(self, key: str) -> Any:
        return getattr(self.config, key, None)

    def set(self, key: str, value: Any):
        if hasattr(self.config, key):
            current_val = getattr(self.config, key)
            if isinstance(current_val, float):
                value = float(value)
            elif isinstance(current_val, int):
                value = int(value)
            elif isinstance(current_val, bool):
                value = str(value).lower() in ("true", "1", "yes")

            setattr(self.config, key, value)
            self.save()
        else:
            raise KeyError(f"Unknown configuration key: {key}")

    def reset(self):
        self.config = AppConfig()
        self.save()
