import pytest
from datetime import datetime
from demosat_data_utils.ground_stations import GroundStationItem, GroundStationContainer

class TestGroundStationItem:
    @pytest.fixture
    def sample_source(self):
        return {
            'Name': 'Goldstone',
            'Abbreviation': 'GDS',
            'Latitude': 35.42,
            'Longitude': -116.89,
            'Altitude': 1.0,
            'Start Time': datetime(2025, 1, 1, 12, 0, 0),
            'scet': 100.0, # for the alternative time property check
            'name': 'GDS_01' # for the name property check
        }

    def test_properties(self, sample_source):
        item = GroundStationItem(sample_source)
        
        # Test property mappings
        assert item.time == sample_source['Start Time']
        assert item.name == 'GDS_01'
        
        # Test formatting
        assert 'Latitude' in item.FLOAT_FORMAT
        assert item.FLOAT_FORMAT['Latitude'] == '.2f'

class TestGroundStationContainer:
    def test_default_init(self):
        """Test that the container loads default stations if no data provided."""
        container = GroundStationContainer()
        
        assert len(container) == 3 # WGS, MCO, ASF are hardcoded defaults
        
        # Verify one of the defaults
        wgs = next(s for s in container if s['Abbreviation'] == 'WGS')
        assert wgs['Name'] == 'Wallops Test Range'
        assert wgs['Latitude'] == 37.85

    def test_custom_init(self):
        """Test initialization with custom data."""
        # Fix: Use 0.0 (float) instead of 0 (int) to pass strict validation
        custom_data = [{'Name': 'Custom', 'Abbreviation': 'CST', 'Latitude': 0.0, 'Longitude': 0.0, 'Altitude': 0.0}]
        container = GroundStationContainer(raw_data=custom_data)
        
        assert len(container) == 1
        assert container[0]['Name'] == 'Custom'

    def test_metadata_properties(self):
        container = GroundStationContainer()
        # This currently fails because the source code returns self._default_time_label 
        # but never defines it in __init__
        assert container.default_time_label is None
        assert isinstance(container.repr_cols, list) or container.repr_cols is None