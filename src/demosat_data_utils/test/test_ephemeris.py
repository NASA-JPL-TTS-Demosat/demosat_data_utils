import pytest
import numpy as np
from datetime import datetime
from demosat_data_utils.ephemeris import EpehmerisItem, Planet, EphemerisContainer
from unittest.mock import patch, mock_open

# Helper subclass to bypass SPICE rotations for geometric testing.
class GeometricTestItem(EpehmerisItem):
    @property
    def rotation_matrix(self):
        return np.eye(3)

class TestEphemerisItem:
    @pytest.fixture
    def earth_item(self):
        source = {
            'JD': 2460677.0,
            'Time': datetime(2025, 1, 1, 12, 0, 0),
            'x': 6378.137, 'y': 0.0, 'z': 0.0,
            'v_x': 0.0, 'v_y': 7.5, 'v_z': 0.0,
            'planet': 'EARTH'
        }
        return GeometricTestItem(source)

    @pytest.fixture
    def mars_item(self):
        source = {
            'JD': 2460677.0,
            'Time': datetime(2025, 1, 1, 12, 0, 0),
            'x': 0.0, 'y': 0.0, 'z': 3396.19,
            'v_x': 0.0, 'v_y': 0.0, 'v_z': 0.0,
            'planet': 'MARS'
        }
        return GeometricTestItem(source)

    def test_planet_property(self, earth_item, mars_item):
        assert earth_item.planet == Planet.EARTH
        assert mars_item.planet == Planet.MARS

        invalid_planet_source = {
            'JD': 2460677.0,
            'Time': datetime(2025, 1, 1),
            'x': 1000.0, 'y': 0.0, 'z': 0.0, 
            'v_x': 0.0, 'v_y': 0.0, 'v_z': 0.0,
            'planet': 'NOT_A_PLANET' 
        }
        item = EpehmerisItem(invalid_planet_source)
        assert item.planet == Planet.EARTH

    def test_spherical_coords(self, earth_item):
        r, theta, phi = earth_item.spherical_coords
        assert np.isclose(r, 6378.137)
        assert np.isclose(theta, np.pi/2)
        assert np.isclose(phi, 0.0)

    def test_lat_lon_equator(self, earth_item):
        lat, lon = earth_item.lat_lon
        assert np.isclose(lat, 0.0, atol=1e-12)
        assert np.isclose(lon, 0.0, atol=1e-12)

    def test_lat_lon_pole(self, mars_item):
        lat, lon = mars_item.lat_lon
        assert np.isclose(lat, 90.0, atol=1e-12)
    
    def test_lat_lon_quadrants(self):
        val = 100.0
        source = {
            'JD': 2460677.0,
            'Time': datetime(2025, 1, 1),
            'x': val, 'y': val, 'z': val * np.sqrt(2),
            'v_x': 0.0, 'v_y': 0.0, 'v_z': 0.0,
            'planet': 'EARTH'
        }
        item = GeometricTestItem(source)
        lat, lon = item.lat_lon
        assert np.isclose(lat, 45.0, atol=1e-12)
        assert np.isclose(lon, 45.0, atol=1e-12)

class TestEphemerisCSV:
    def test_read_csv(self):
        csv_content = """header1,header2
$$SOE
2460677.0, 2025-001T12:00:00, 100.0, 200.0, 300.0, 1.0, 2.0, 3.0
2460677.1, 2025-001T13:00:00, 110.0, 210.0, 310.0, 1.1, 2.1, 3.1
$$EOE
footer_stuff
"""
        # Create mock and fix iteration for Python 3.6
        m = mock_open(read_data=csv_content)
        m.return_value.__iter__ = lambda f: iter(csv_content.splitlines(keepends=True))

        with patch("builtins.open", m):
            container = EphemerisContainer()
            records = container.read_csv("dummy_path.csv", planet="MARS")
            
            assert len(records) == 2
            rec = records[0]
            assert rec['JD'] == '2460677.0'
            assert rec['x'] == '100.0'
            assert rec['planet'] == 'MARS'

    def test_read_csv_with_enum(self):
        csv_content = """$$SOE
2460677.0, 2025-001T12:00:00, 100, 200, 300, 1, 2, 3
$$EOE"""
        
        # Create mock and fix iteration for Python 3.6
        m = mock_open(read_data=csv_content)
        m.return_value.__iter__ = lambda f: iter(csv_content.splitlines(keepends=True))

        with patch("builtins.open", m):
            container = EphemerisContainer()
            records = container.read_csv("dummy.csv", planet=Planet.VENUS)
            
            assert len(records) == 1
            assert records[0]['planet'] == 'VENUS'
            
    def test_read_csv_with_dict(self):
        csv_content = """$$SOE
2460677.0, time, 1, 2, 3, 4, 5, 6
$$EOE"""
        
        # Create mock and fix iteration for Python 3.6
        m = mock_open(read_data=csv_content)
        m.return_value.__iter__ = lambda f: iter(csv_content.splitlines(keepends=True))

        with patch("builtins.open", m):
            container = EphemerisContainer()
            custom_planet = {'name': 'Pluto', 'a': 1000, 'f': 0}
            records = container.read_csv("dummy.csv", planet=custom_planet)
            
            assert len(records) > 0
            assert records[0]['planet'] == 'PLUTO'