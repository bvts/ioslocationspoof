"""Unit tests for the location simulation backend and state machine."""

import pytest
from locationctl.backend.state import BackendState, DeviceInfo, CapabilityReport, SimulationResult
from locationctl.backend.developer_service import DeveloperServiceBackend


def test_coordinate_validation_latitude_out_of_bounds():
    backend = DeveloperServiceBackend()
    res = backend.set_location_sync(91.0, 21.0122)
    assert res.success is False
    assert res.error == "LATITUDE_OUT_OF_BOUNDS"
    assert "Invalid latitude" in res.message


def test_coordinate_validation_longitude_out_of_bounds():
    backend = DeveloperServiceBackend()
    res = backend.set_location_sync(52.2297, 185.0)
    assert res.success is False
    assert res.error == "LONGITUDE_OUT_OF_BOUNDS"
    assert "Invalid longitude" in res.message


def test_valid_coordinate_boundaries():
    backend = DeveloperServiceBackend()
    # Test valid boundary coordinates when disconnected
    res = backend.set_location_sync(-90.0, -180.0)
    # Validation passes, errors out on missing physical device (not bounds)
    assert res.error != "LATITUDE_OUT_OF_BOUNDS"
    assert res.error != "LONGITUDE_OUT_OF_BOUNDS"

    res = backend.set_location_sync(90.0, 180.0)
    assert res.error != "LATITUDE_OUT_OF_BOUNDS"
    assert res.error != "LONGITUDE_OUT_OF_BOUNDS"


def test_backend_state_transitions():
    backend = DeveloperServiceBackend()
    status = backend.get_status_sync()
    assert status.state in (BackendState.DISCONNECTED, BackendState.READY)
    assert status.active_coordinate is None

    # Clear location on idle backend restores READY without crashing
    clear_res = backend.clear_location_sync()
    assert clear_res.success is True
    assert backend.get_status_sync().state in (BackendState.DISCONNECTED, BackendState.READY)


@pytest.mark.asyncio
async def test_async_backend_calls():
    backend = DeveloperServiceBackend()
    status = await backend.get_status()
    assert status.state in (BackendState.DISCONNECTED, BackendState.READY)

    clear_res = await backend.clear_location()
    assert clear_res.success is True



def test_device_info_model():
    dev = DeviceInfo(
        udid="00008110-0006512A3681801E",
        name="iPhone 13",
        product_type="iPhone14,5",
        ios_version="17.4",
        is_paired=True,
        developer_mode=True,
    )
    assert dev.udid == "00008110-0006512A3681801E"
    assert dev.developer_mode is True
    assert dev.is_paired is True


def test_capability_report_empty():
    backend = DeveloperServiceBackend()
    caps = backend.get_capabilities_sync()
    assert isinstance(caps, CapabilityReport)


@pytest.mark.asyncio
async def test_persistent_session_fastpath_reuse():
    from unittest.mock import AsyncMock
    backend = DeveloperServiceBackend()
    mock_loc_sim = AsyncMock()
    mock_loc_sim.set = AsyncMock()

    backend._state = BackendState.SIMULATING
    backend._loc_sim = mock_loc_sim
    backend._active_coordinate = (48.8584, 2.2945)

    res = await backend.set_location(40.7128, -74.0060)
    assert res.success is True
    assert backend._active_coordinate == (40.7128, -74.0060)
    mock_loc_sim.set.assert_awaited_once_with(40.7128, -74.0060)


@pytest.mark.asyncio
async def test_cleanup_simulation_session():
    from unittest.mock import AsyncMock
    backend = DeveloperServiceBackend()
    mock_loc_sim = AsyncMock()
    mock_dvt = AsyncMock()

    backend._state = BackendState.SIMULATING
    backend._loc_sim = mock_loc_sim
    backend._dvt = mock_dvt
    backend._active_coordinate = (48.8584, 2.2945)

    res = await backend.clear_location()
    assert res.success is True
    assert backend._state == BackendState.READY
    assert backend._active_coordinate is None
    assert backend._loc_sim is None
    assert backend._dvt is None
    mock_loc_sim.clear.assert_awaited_once()
    mock_dvt.close.assert_awaited_once()

