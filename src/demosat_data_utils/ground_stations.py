#Python Imports
import pdb
from abc import ABC, abstractmethod
from datetime import datetime

#JPL Imports
from jpl_time import Time

#This Library Imports
from tts_data_utils.core.data_container import DataContainer
from tts_data_utils.core.data_item import DataItem


class GroundStationItem(DataItem):
    DICT_VALID_KEYS = [
        ('Name', str), 
        ('Abbreviation', str), 
        ('Latitude', float),
        ('Longitude', float),
        ('Altitude', float)                
        ]

    TIME_FORMATS = {
    }
    NAME = 'Ground Station'

    FLOAT_FORMAT = {
        'Latitude': '.2f',  # Display Latitude with 2 decimal places
        'Longitude': '.2f'  # Display Longitude with 2 decimal places
    }

    @property
    def default_html_row_style(self):
        return {}
    
    @property
    def time(self):
        return self.source['Start Time']

    @property
    def time_str(self):
        return datetime.strftime(self.source['Start Time'], self.TIME_FORMATS['Start Time'])
        return Time(self.source['scet'])
    
    @property
    def name(self):
        return self.source['name']


class GroundStationContainer(DataContainer):
    NAME = 'Ground Stations'
    DATA_ITEM_CLS = GroundStationItem
    
    def __init__(self, raw_data=None, **kwargs):
        if raw_data is None:
            raw_data = [
                {'Name': 'Wallops Test Range', 'Abbreviation': 'WGS', 'Latitude': 37.85, 'Longitude': 75.47, 'Altitude': 0.002},
                {'Name': 'McMurdo Station', 'Abbreviation': 'MCO', 'Latitude': -77.80464056923415, 'Longitude': 167.01764541076665, 'Altitude': 0.010},
                {'Name': 'Alaska Satellite Facility', 'Abbreviation': 'ASF', 'Latitude': 64.86111090381861, 'Longitude': -147.84938380883113, 'Altitude': 0.010},
            ]
        super().__init__(raw_data=raw_data, **kwargs)

    def _impl_init(self):
        """
        Internal implementation hook for initialization logic.
        """
        return

    @property
    def repr_cols(self):
        """
        Columns to be used when representing the container (e.g., in tables or CSVs).
        
        :return: List of column names.
        :rtype: list
        """
        return self._repr_cols

    @property
    def default_time_label(self):
        """
        The default time field key used for time-series operations.
        """
        return 

