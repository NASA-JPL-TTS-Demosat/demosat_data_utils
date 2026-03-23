import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from demosat_data_utils.comm_windows import CommWindowContainer, CommWindowItem
from demosat_data_utils.ground_stations import GroundStationContainer

class TestCommWindowItem:
    def test_properties(self):
        now = datetime(2025, 1, 1)
        source = {
            'Station': 'Goldstone',
            'Abbreviation': 'GDS', 
            'Start Time': now,
            'End Time': now + timedelta(minutes=10),
            'Max Elevation': 45.5
        }
        item = CommWindowItem(source)
        
        assert item.name == 'Goldstone'
        assert item.time == now
        # Test string formatting
        assert '2025-001T00:00:00.000000' in item.time_str

class TestCommWindowContainer:
    @pytest.fixture
    def mock_ephem(self):
        """Creates a mock EphemerisContainer that behaves like a list of items."""
        start = datetime(2025, 1, 1, 12, 0, 0)
        items = []
        
        # Create a sequence of 5 points:
        # 0: Below horizon (-10) -> 12:00
        # 1: Horizon (0)         -> 12:01
        # 2: Above horizon (10)  -> 12:02 (Start of window)
        # 3: High elevation (80) -> 12:03 (Max elevation)
        # 4: Below horizon (-10) -> 12:04 (End of window)
        elevations = [-10., 0., 10., 80., -10.]
        
        for i, el in enumerate(elevations):
            mock_item = MagicMock()
            # FIX: Capture 'i' immediately using default argument i=i
            mock_item.__getitem__.side_effect = lambda k, i=i: start + timedelta(minutes=i) if k == "Time" else None
            # The calculation calls pos_rel_earth_point(*sta_lla)
            mock_item.pos_rel_earth_point.return_value = {'elevation': el}
            items.append(mock_item)
            
        container = MagicMock()
        container.__iter__.return_value = iter(items)
        container.__len__.return_value = len(items)
        container.__getitem__.side_effect = items.__getitem__
        return container

    @pytest.fixture
    def stations(self):
        # Use 0.0 floats to pass strict validation in DataItem
        data = [{'Name': 'TestStation', 'Abbreviation': 'TST', 'Latitude': 0.0, 'Longitude': 0.0, 'Altitude': 0.0}]
        return GroundStationContainer(raw_data=data)

    def test_calculate_comm_windows(self, mock_ephem, stations):
        """Test the logic that detects start/end of visibility."""
        # Initialize container with mock data
        container = CommWindowContainer(ephem=mock_ephem, stations=stations)
        
        assert len(container) == 1
        window = container[0]
        
        # Window starts at index 2 (12:02) and ends at index 4 (12:04)
        assert window['Start Time'].minute == 2
        assert window['End Time'].minute == 4
        assert window['Max Elevation'] == 80.0
        assert window['Station'] == 'TestStation'

    def test_min_elevation_filter(self, mock_ephem, stations):
        """Test filtering by minimum elevation."""
        # The max elevation in our mock is 80.0
        
        # Case 1: Filter should keep it
        c1 = CommWindowContainer(ephem=mock_ephem, stations=stations, min_el=10.0)
        assert len(c1) == 1
        
        # Case 2: Filter should remove it (min_el 85 > max_el 80)
        c2 = CommWindowContainer(ephem=mock_ephem, stations=stations, min_el=85.0)
        assert len(c2) == 0

    def test_empty_init(self):
        c = CommWindowContainer()
        assert len(c) == 0