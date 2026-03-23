#Python Imports
from abc import ABC, abstractmethod
from datetime import datetime

#JPL Imports
from jpl_time import Time


from tts_data_utils.core.data_container import DataContainer
from tts_data_utils.core.data_item import DataItem

#This Library Imports
from demosat_data_utils.ground_stations import GroundStationContainer

class CommWindowItem(DataItem):
    DICT_VALID_KEYS = [
        ('Station', str),
        ('Abbreviation', str),
        ('Start Time', datetime), 
        ('End Time', datetime),
        ('Max Elevation', float)
        ]
        
    # Format for float values in representation (e.g., ':.2f' for 2 decimal places)
    FLOAT_FORMAT = {
        'Max Elevation': '.2f'  # Display elevation with 2 decimal places
    }

    TIME_FORMATS = {
        'Start Time': '%Y-%jT%H:%M:%S.%f',
        'End Time': '%Y-%jT%H:%M:%S.%f',
    }

    TIME_FORMAT_PRECISION = {
        'Start Time': 2,
        'End Time': 2
    }

    NAME = 'Comm Window'



    @property
    def default_html_row_style(self):
        return {}
    
    @property
    def time(self):
        return self.source['Start Time']

    # No need to override printable_values anymore - the base class handles float formatting now
    
    @property
    def time_str(self):
        return datetime.strftime(self.source['Start Time'], self.TIME_FORMATS['Start Time'])
    
    @property
    def name(self):
        return self.source['Station']


class CommWindowContainer(DataContainer):
    NAME = 'Comm Windows'
    DATA_ITEM_CLS = CommWindowItem
    
    def __init__(self, ephem=None, min_el=None, stations=None, raw_data=None, **kwargs):
        """
        Initialize a CommWindowContainer with communication windows for all stations.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            stations: GroundStationContainer with ground stations (default: use built-in stations)
            raw_data: Optional raw data to initialize the container with
            **kwargs: Additional arguments to pass to DataContainer
        """
        # Allow initialization with either ephem or raw_data
        if raw_data is not None:
            # Initialize directly with provided raw_data
            super().__init__(raw_data=raw_data, **kwargs)
        elif ephem is not None:
            # Calculate comm windows from ephemeris
            if stations is None: 
                stations = GroundStationContainer()
            
            # Calculate comm windows for all stations
            calculated_data = self._calculate_all_comm_windows(ephem, stations, min_el)
            
            # Initialize the container with the calculated windows
            super().__init__(raw_data=calculated_data, **kwargs)
        else:
            # Initialize with empty data if neither is provided
            super().__init__(raw_data=[], **kwargs)
        
    def _calculate_all_comm_windows(self, ephem, stations, min_el):
        """
        Calculate communication windows for all stations in the container.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            stations: GroundStationContainer with ground stations
            
        Returns:
            List of dictionaries with comm window data
        """
        all_windows = []
        
        # Process each station
        for station in stations:
            # Get station coordinates
            sta_lla = (station['Latitude'], station['Longitude'], station['Altitude'])
            
            # Calculate view periods for this station
            view_periods = self._calculate_view_periods(ephem, sta_lla)
            
            # Convert to comm window format
            for period in view_periods:
                all_windows.append({
                    'Station': station['Name'],
                    'Abbreviation': station['Abbreviation'],
                    'Start Time': period['start'],
                    'End Time': period['end'],
                    'Max Elevation': period['max_elevation']
                })
        if min_el is not None:
            all_windows = [window for window in all_windows if window['Max Elevation'] >= min_el]
        return all_windows
    
    def _calculate_view_periods(self, ephem, sta_lla):
        """
        Calculate satellite visibility periods from a ground station.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            sta_lla: Tuple of (latitude, longitude, altitude) for the ground station
            
        Returns:
            List of dictionaries with 'start' and 'end' times for each visibility period
        """
        # Initialize variables
        last_vector_in_view = False
        this_vector_in_view = False
        start_of_view = []
        end_of_view = []
        max_elevations = []  # Store max elevation for each pass
        current_max_elevation = 0.0  # Track max elevation for current pass
        view_periods = []
        
        # Check if ephemeris is empty
        if not ephem:
            return []
        
        # Check if we start in view
        first_aer = ephem[0].pos_rel_earth_point(*sta_lla)
        last_vector_in_view = first_aer['elevation'] > 0
        if last_vector_in_view:
            # If we start in view, record the start time
            start_of_view.append(ephem[0]["Time"])
            # Initialize max elevation for this pass
            current_max_elevation = first_aer['elevation']
        
        # Process all ephemeris points
        for e in ephem:
            aer = e.pos_rel_earth_point(*sta_lla)
            this_vector_in_view = aer['elevation'] > 0
            
            # Track max elevation if in view
            if this_vector_in_view and aer['elevation'] > current_max_elevation:
                current_max_elevation = aer['elevation']
            
            # Detect transitions
            if last_vector_in_view and not this_vector_in_view:
                # Transition from in-view to out-of-view
                end_of_view.append(e["Time"])
                # Store max elevation for this pass
                max_elevations.append(current_max_elevation)
                # Reset max elevation for next pass
                current_max_elevation = 0.0
            elif not last_vector_in_view and this_vector_in_view:
                # Transition from out-of-view to in-view
                start_of_view.append(e["Time"])
                # Initialize max elevation for this pass
                current_max_elevation = aer['elevation']
                
            last_vector_in_view = this_vector_in_view
        
        # Check if we end in view
        if last_vector_in_view:
            # If we end in view, record the end time
            end_of_view.append(ephem[-1]["Time"])
            # Store max elevation for this pass
            max_elevations.append(current_max_elevation)
        
        # Safety check for empty lists
        if not start_of_view or not end_of_view:
            return []  # No visibility periods
        
        # Ensure we have matching pairs
        num_periods = min(len(start_of_view), len(end_of_view))
        
        # Create the view periods
        for i in range(num_periods):
            view_periods.append({
                'start': start_of_view[i],
                'end': end_of_view[i],
                'duration': end_of_view[i] - start_of_view[i],
                'max_elevation': max_elevations[i]
            })
        
        return view_periods
        
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
        return ['Station', 'Abbreviation', 'Start Time', 'End Time', 'Max Elevation']

    # No need to override methods from DataContainer
    # The float formatting is handled by the CommWindowItem.printable_values property
        
    @property
    def default_time_label(self):
        """
        The default time field key used for time-series operations.
        
        :return: The key for the default time field.
        :rtype: str
        """
        return 'Start Time'

