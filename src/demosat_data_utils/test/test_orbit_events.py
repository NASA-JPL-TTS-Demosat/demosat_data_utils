import pytest
from datetime import datetime, timedelta
from demosat_data_utils.orbit_events import OrbitEventContainer

class TestOrbitEventContainer:
    @pytest.fixture
    def sample_events(self):
        """Create a container with synthetic node crossings."""
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        events = []
        
        # Simulate 5 orbits, 90 minute period (5400 seconds)
        period = 5400
        for i in range(5):
            # Ascending Node
            events.append({
                'Time': base_time + timedelta(seconds=i*period),
                'Type': 'Ascending Node Crossing',
                'Orbit Number': 1000 + i
            })
            # Descending Node (halfway through)
            events.append({
                'Time': base_time + timedelta(seconds=i*period + period/2),
                'Type': 'Descending Node Crossing',
                'Orbit Number': 1000 + i
            })
            
        return OrbitEventContainer(raw_data=events)

    def test_filter_by_type(self, sample_events):
        """Test filtering events by their type string."""
        ascending = sample_events.filter_by_type('Ascending Node Crossing')
        descending = sample_events.filter_by_type('Descending Node Crossing')
        
        assert len(ascending) == 5
        assert len(descending) == 5
        assert all(e['Type'] == 'Ascending Node Crossing' for e in ascending)

    def test_get_orbit_period_ascending(self, sample_events):
        """Calculate period using ascending nodes."""
        # We set the period to 5400 seconds (90 mins)
        period = sample_events.get_orbit_period(num_orbits=3, node_type='Ascending')
        
        assert period.total_seconds() == 5400.0

    def test_get_orbit_period_descending(self, sample_events):
        """Calculate period using descending nodes."""
        period = sample_events.get_orbit_period(num_orbits=3, node_type='Descending')
        assert period.total_seconds() == 5400.0

    def test_get_orbit_period_insufficient_data(self, sample_events):
        """Test error handling when requesting more orbits than available."""
        # We have 5 orbits (5 ascending nodes). Requesting average over 5 requires 6 nodes (start + 5).
        # We only have 5 nodes total.
        with pytest.raises(ValueError) as excinfo:
            sample_events.get_orbit_period(num_orbits=5, node_type='Ascending')
        
        assert "Not enough" in str(excinfo.value)

    def test_container_initialization(self):
        """Test empty initialization."""
        container = OrbitEventContainer()
        assert len(container) == 0