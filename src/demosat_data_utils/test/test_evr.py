import unittest
from datetime import datetime, timedelta
import unittest.mock as mock

# Adjust this import to match your file structure
from demosat_data_utils.evr import EvrItem, EvrContainer, EVR_LEVEL_COLORS

class TestEvrItem(unittest.TestCase):
    def setUp(self):
        self.base_scet = datetime(2024, 1, 1, 12, 0, 0)
        self.valid_source = {
            'recordType': 'EVR',
            'sessionId': 100,
            'sessionHost': 'host',
            'name': 'TEST_EVR',
            'module': 'FSW',
            'level': 'FATAL',
            'eventId': 12345,
            'vcid': 1,
            'dssId': 10,
            'fromSse': False,
            'realtime': True,
            'sclk': 123456.78,
            'scet': self.base_scet, # Pass datetime object directly
            'ert': self.base_scet,
            'rct': None,
            'lst': None,
            'message': 'Something bad happened',
            'metadataKeywordList': '[]',
            'metadataValuesList': '[]',
            'metadata': {'CategorySequenceId': '1'}
        }

    def test_init_valid(self):
        """Test that EvrItem initializes correctly with valid data."""
        item = EvrItem(self.valid_source)
        self.assertTrue(item.valid)
        self.assertEqual(item.name, 'TEST_EVR')
        self.assertEqual(item.level, 'FATAL')

    def test_init_casting(self):
        """Test that cast_fields=True converts string times to datetime objects."""
        source_copy = self.valid_source.copy()
        # Provide a string instead of datetime
        source_copy['scet'] = '2024-001T12:00:00.000000'
        
        # Initialize with casting
        item = EvrItem(source_copy, cast_fields=True)
        
        self.assertIsInstance(item.source['scet'], datetime)
        self.assertEqual(item.source['scet'], self.base_scet)

    def test_is_warning(self):
        """Test the is_warning logic based on EVR levels."""
        fatal_item = EvrItem({**self.valid_source, 'level': 'FATAL'})
        warn_item = EvrItem({**self.valid_source, 'level': 'WARNING_LO'})
        info_item = EvrItem({**self.valid_source, 'level': 'ACTIVITY_HI'})

        self.assertTrue(fatal_item.is_warning())
        self.assertTrue(warn_item.is_warning())
        self.assertFalse(info_item.is_warning())

    def test_html_style(self):
        """Test that the correct CSS style is returned based on level."""
        item = EvrItem(self.valid_source) # level is FATAL
        expected_color = EVR_LEVEL_COLORS['FATAL']
        self.assertEqual(item.default_html_row_style, expected_color)

