#Python Imports
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Tuple, Optional
import spiceypy as sp

#JPL Imports
from jpl_time import Time
import tts_spice.furnish

#This Library Imports
from tts_data_utils.core.data_container import DataContainer
from tts_data_utils.core.data_item import DataItem

# Constants for Earth shadow calculations
EARTH_RADIUS = 6378.1370  # Earth equatorial radius in km
SUN_RADIUS = 696340.0    # Sun radius in km
AU = 149597870.7         # Astronomical Unit in km

tts_spice.furnish.leap_seconds()
tts_spice.furnish.planetary_ephemerides()
tts_spice.furnish.planetary_constants()
tts_spice.furnish.rotation_kernels("Earth")

class OrbitEventItem(DataItem):
    """
    Represents a single orbit event such as an ascending/descending node crossing,
    pole crossing, or Earth shadow event.
    """
    DICT_VALID_KEYS = [
        ('Time', datetime),
        ('Type', str),
        ('Orbit Number', int)
    ]
        
    TIME_FORMATS = {
        'Time': '%Y-%jT%H:%M:%S.%f',
    }
    
    # Limit microseconds to 2 decimal places
    TIME_FORMAT_PRECISION = {
        'Time': 2
    }
    
    NAME = 'Orbit Event'

    @property
    def default_html_row_style(self):
        """
        Define custom row styling based on event type.
        """
        event_type = self.source.get('Type', '')
        if 'Ascending' in event_type:
            return {'background-color': '#e6f7ff'}  # Light blue for ascending
        elif 'Descending' in event_type:
            return {'background-color': '#fff2e6'}  # Light orange for descending
        elif 'North Pole' in event_type:
            return {'background-color': '#e6fffa'}  # Light cyan for north pole
        elif 'South Pole' in event_type:
            return {'background-color': '#f9f2ff'}  # Light purple for south pole
        elif 'Penumbra Entry' in event_type:
            return {'background-color': '#f2f2f2'}  # Light gray for penumbra entry
        elif 'Umbra Entry' in event_type:
            return {'background-color': '#d9d9d9'}  # Darker gray for umbra entry
        elif 'Umbra Exit' in event_type:
            return {'background-color': '#e6e6e6'}  # Medium gray for umbra exit
        elif 'Penumbra Exit' in event_type:
            return {'background-color': '#f9f9f9'}  # Very light gray for penumbra exit
        elif 'into shadow' in event_type:
            return {'background-color': '#333333', 'color': '#ffffff'}  # Dark gray with white text for entering shadow (night)
        elif 'out of shadow' in event_type:
            return {'background-color': '#ffff99'}  # Light yellow for exiting shadow (entering daylight)
        return {}
    
    @property
    def time(self):
        """
        Return the time of the orbit event.
        """
        return self.source['Time']
    
    @property
    def name(self):
        """
        Return a descriptive name for the orbit event.
        """
        event_type = self.source.get('Type', 'Unknown')
        orbit_num = self.source.get('Orbit Number', '')
        if orbit_num:
            return f"{event_type} (Orbit {orbit_num})"
        return event_type


class OrbitEventContainer(DataContainer):
    """
    Container for orbit events such as ascending/descending node crossings,
    pole crossings, and Earth shadow events.
    """
    NAME = 'Orbit Events'
    DATA_ITEM_CLS = OrbitEventItem
    
    def __init__(self, ephem=None, raw_data=None, **kwargs):
        """
        Initialize an OrbitEventContainer with orbit events calculated from ephemeris data.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            raw_data: Optional raw data to initialize the container with
            **kwargs: Additional arguments to pass to DataContainer
        """
        # Allow initialization with either ephem or raw_data
        if raw_data is not None:
            # Initialize directly with provided raw_data
            super().__init__(raw_data=raw_data, **kwargs)
        elif ephem is not None:
            # Calculate orbit events from ephemeris
            calculated_data = self._calculate_orbit_events(ephem)
            
            # Initialize the container with the calculated events
            super().__init__(raw_data=calculated_data, **kwargs)
        else:
            # Initialize with empty data if neither is provided
            super().__init__(raw_data=[], **kwargs)
    
    def _calculate_orbit_events(self, ephem):
        """Calculate all orbit events from ephemeris data.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            
        Returns:
            List of orbit event dictionaries
        """
        orbit_events = []
        orbit_events += self._calculate_node_and_pole_crossings(ephem)
        orbit_events += self._calculate_earth_shadow_events(ephem)
        
        # Sort all events by time
        orbit_events.sort(key=lambda x: x['Time'])
        return orbit_events

    def _calculate_earth_shadow_events(self, ephem) -> List[Dict]:
        """
        Calculate Earth shadow events using a geometric model.
        
        This method determines if the spacecraft is in Earth's shadow by:
        1. Checking if the spacecraft is on the night side of Earth (dot product of Sun-Earth
           vector and spacecraft position vector is negative)
        2. Checking if the spacecraft is within Earth's shadow cone (angle between Sun-Earth
           vector and spacecraft-Earth vector is less than Earth's angular radius)
        
        Shadow detection logic:
        - The spacecraft is on the night side when the angle between the Sun-Earth vector
          and the spacecraft position vector is > 90 degrees (dot product < 0)
        - The spacecraft is within the shadow cone when the angle between the Sun-Earth vector
          and the spacecraft-Earth vector is LESS than Earth's angular radius
        - The spacecraft is in shadow only when BOTH conditions are true
        
        It adds events for:
        - "Terminator crossing into shadow": when spacecraft transitions from day to night
        - "Terminator crossing out of shadow": when spacecraft transitions from night to day
        
        This calculation should match the Earth map visualization, which shows the terminator
        (day/night boundary) on the Earth's surface.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            
        Returns:
            List of orbit event dictionaries for shadow events
        """
        # Make sure ephemeris is sorted by time
        ephem.sort()
        
        # Initialize events list
        shadow_events = []
        
        # Previous shadow state (None for first iteration)
        prev_in_shadow = None
        
        # Process each ephemeris point
        for i, point in enumerate(ephem):
            # Get the spacecraft position in J2000 frame
            sc_pos = point.position  # km
            sc_time = point.time
            
            # Get the ET (ephemeris time) for SPICE calculations
            et = point.et
            
            # Get the position of the Sun relative to Earth in J2000 frame
            # (The sun's position vector relative to the earth)
            sun_pos_rel_earth, _ = sp.spkpos('SUN', et, 'J2000', 'NONE', 'EARTH')
            
            # Calculate the position of the spacecraft relative to Earth
            # (already in ephem.position)
            
            # Calculate the angle between the Sun-Earth vector and the SC-Earth vector
            sun_earth_vec = np.array(sun_pos_rel_earth)  # km
            sc_earth_vec = -sc_pos  # Negative because we want Earth->SC, not SC->Earth
            
            # Normalize the vectors
            sun_earth_unit = sun_earth_vec / np.linalg.norm(sun_earth_vec)
            sc_earth_unit = sc_earth_vec / np.linalg.norm(sc_earth_vec)
            
            # Calculate the angle between the two vectors
            cos_angle = np.dot(sun_earth_unit, sc_earth_unit)
            angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))  # radians
            
            # Calculate the distance from the spacecraft to Earth
            sc_earth_dist = np.linalg.norm(sc_earth_vec)  # km
            
            # Calculate the Earth's angular radius as seen from the spacecraft
            earth_angular_radius = np.arcsin(EARTH_RADIUS / sc_earth_dist)  # radians
            
            # First, check if the spacecraft is on the night side of Earth
            # Get the Sun-Earth vector (from Earth to Sun)
            sun_earth_vec = np.array(sun_pos_rel_earth)  # km
            
            # Calculate the dot product between the normalized Sun-Earth vector
            # and the normalized spacecraft position vector
            sun_earth_unit = sun_earth_vec / np.linalg.norm(sun_earth_vec)
            sc_pos_unit = sc_pos / np.linalg.norm(sc_pos)
            dot_product = np.dot(sun_earth_unit, sc_pos_unit)
            
            # If the dot product is negative, the spacecraft is on the night side of Earth
            # (angle between vectors > 90 degrees)
            on_night_side = dot_product < 0
            
            # Now check if the spacecraft is within Earth's shadow cone
            # For the spacecraft to be in shadow:
            # 1. It must be on the night side of Earth
            # 2. The angle between the Sun-Earth vector and spacecraft-Earth vector must be LESS than Earth's angular radius
            in_shadow = on_night_side and angle < earth_angular_radius
            
            # Check for shadow entry/exit events
            if prev_in_shadow is not None and in_shadow != prev_in_shadow:
                # Find the orbit number from the nearest node crossing
                orbit_number = self._find_nearest_orbit_number(sc_time, shadow_events)
                
                # Determine the event type
                if in_shadow:
                    # Spacecraft is transitioning from day to night
                    event_type = "Terminator crossing into shadow"
                else:
                    # Spacecraft is transitioning from night to day
                    event_type = "Terminator crossing out of shadow"
                
                # If this is not the first point, interpolate to find the exact crossing time
                if i > 0:
                    prev_point = ephem[i-1]
                    prev_time = prev_point.time
                    time_diff = (sc_time - prev_time).total_seconds()
                    
                    # Simple linear interpolation for the crossing time
                    # Assuming the change in shadow state is approximately linear over the time step
                    frac = 0.5  # Default to midpoint if we can't calculate better
                    
                    # Better interpolation if we have the previous point's angle and Earth angular radius
                    prev_sc_pos = prev_point.position
                    prev_et = prev_point.et
                    prev_sun_pos_rel_earth, _ = sp.spkpos('SUN', prev_et, 'J2000', 'NONE', 'EARTH')
                    prev_sun_earth_vec = np.array(prev_sun_pos_rel_earth)
                    prev_sc_earth_vec = -prev_sc_pos
                    
                    prev_sun_earth_unit = prev_sun_earth_vec / np.linalg.norm(prev_sun_earth_vec)
                    prev_sc_earth_unit = prev_sc_earth_vec / np.linalg.norm(prev_sc_earth_vec)
                    
                    prev_cos_angle = np.dot(prev_sun_earth_unit, prev_sc_earth_unit)
                    prev_angle = np.arccos(np.clip(prev_cos_angle, -1.0, 1.0))
                    
                    prev_sc_earth_dist = np.linalg.norm(prev_sc_earth_vec)
                    prev_earth_angular_radius = np.arcsin(EARTH_RADIUS / prev_sc_earth_dist)
                    
                    # Calculate the fraction based on the difference between angles and thresholds
                    prev_diff = prev_angle - prev_earth_angular_radius
                    curr_diff = angle - earth_angular_radius
                    
                    # If the differences have opposite signs, we can interpolate
                    if prev_diff * curr_diff < 0:
                        frac = abs(prev_diff) / (abs(prev_diff) + abs(curr_diff))
                    
                    # Calculate the interpolated crossing time
                    crossing_time = prev_time + timedelta(seconds=time_diff * frac)
                else:
                    crossing_time = sc_time
                
                # Add the shadow event
                shadow_events.append({
                    'Time': crossing_time,
                    'Type': event_type,
                    'Orbit Number': orbit_number
                })
            
            # Update the previous shadow state
            prev_in_shadow = in_shadow
        
        return shadow_events
    
    def _find_nearest_orbit_number(self, event_time, existing_events):
        """
        Find the orbit number for a new event based on the nearest existing event.
        
        Args:
            event_time: Time of the new event
            existing_events: List of existing orbit events
            
        Returns:
            Orbit number for the new event
        """
        # Default orbit number if we can't find a better one
        default_orbit_number = 1000
        
        # If there are no existing events, return the default
        if not existing_events:
            return default_orbit_number
        
        # Find the event with the closest time
        closest_event = min(existing_events, key=lambda x: abs((x['Time'] - event_time).total_seconds()))
        
        # Return the orbit number from the closest event
        return closest_event.get('Orbit Number', default_orbit_number)
        
    def _calculate_node_and_pole_crossings(self, ephem):
        """
        Calculate equator crossings (nodes) and pole crossings from ephemeris data.
        
        Args:
            ephem: EphemerisContainer with spacecraft ephemeris data
            
        Returns:
            List of orbit event dictionaries including node and pole crossings
        """
        # Make sure ephemeris is sorted by time
        ephem.sort()
        
        # Extract latitude and time pairs
        # Use the lat_lon property which returns (lat, lon)
        latitude_time_pairs = [(ephemeris_point.lat_lon[0], ephemeris_point.time) for ephemeris_point in ephem]
        
        # Initialize orbit events list and orbit counter (starting from 1000)
        orbit_events = []
        orbit_number = 1000
        
        # For pole crossings, we need to track max/min latitude points for each orbit
        current_hemisphere_data = []
        hemisphere_segments = []
        
        # Process consecutive pairs to detect node crossings
        for i in range(len(latitude_time_pairs) - 1):
            latitude1, time1 = latitude_time_pairs[i]
            latitude2, time2 = latitude_time_pairs[i + 1]
            
            # Skip if latitudes are equal (shouldn't happen with proper ephemeris)
            if latitude1 == latitude2:
                continue
                
            # Detect descending node crossing (from north to south)
            if latitude1 > 0 and latitude2 < 0:
                # Linear interpolation to find exact crossing time
                equator_crossing_time = time1 + (0 - latitude1) * (time2 - time1) / (latitude2 - latitude1)
                
                # Increment orbit number before the descending node crossing
                # This ensures the descending node is part of the same orbit as subsequent events
                orbit_number += 1
                
                # Add the event
                orbit_events.append({
                    'Time': equator_crossing_time,
                    'Type': 'Descending Node Crossing',
                    'Orbit Number': orbit_number
                })
                
                # Mark the end of the northern hemisphere pass
                if current_hemisphere_data:
                    hemisphere_segments.append((orbit_number - 1, 'north', current_hemisphere_data))
                    current_hemisphere_data = []
                
            # Detect ascending node crossing (from south to north)
            elif latitude1 < 0 and latitude2 > 0:
                # Linear interpolation to find exact crossing time
                equator_crossing_time = time1 + (0 - latitude1) * (time2 - time1) / (latitude2 - latitude1)
                
                # Add the event
                orbit_events.append({
                    'Time': equator_crossing_time,
                    'Type': 'Ascending Node Crossing',
                    'Orbit Number': orbit_number
                })
                
                # Mark the end of the southern hemisphere pass
                if current_hemisphere_data:
                    hemisphere_segments.append((orbit_number, 'south', current_hemisphere_data))
                    current_hemisphere_data = []
            
            # Add the current point to the hemisphere data for pole crossing detection
            current_hemisphere_data.append((latitude1, time1))
            
            # Add the last point too if we're at the end
            if i == len(latitude_time_pairs) - 2:
                current_hemisphere_data.append((latitude2, time2))
                # Determine hemisphere based on last latitude
                hemisphere = 'north' if latitude2 > 0 else 'south'
                hemisphere_segments.append((orbit_number, hemisphere, current_hemisphere_data))
        
        # Process hemisphere segments to find pole crossings
        for orbit_num, hemisphere, data in hemisphere_segments:
            if not data or len(data) < 2:
                continue
                
            # Find the two points with max/min latitude depending on hemisphere
            if hemisphere == 'north':
                # Find the two points with maximum latitude
                sorted_by_latitude = sorted(data, key=lambda x: x[0], reverse=True)
                if len(sorted_by_latitude) >= 2:
                    max_lat_point, second_max_lat_point = sorted_by_latitude[0], sorted_by_latitude[1]
                    
                    # Calculate weighted average time based on latitude
                    max_latitude, max_lat_time = max_lat_point
                    second_max_latitude, second_max_time = second_max_lat_point
                    max_weight = max_latitude / (max_latitude + second_max_latitude)
                    second_max_weight = second_max_latitude / (max_latitude + second_max_latitude)
                    
                    # Calculate weighted average time
                    time_diff_seconds = (second_max_time - max_lat_time).total_seconds()
                    pole_crossing_time = max_lat_time + timedelta(seconds=time_diff_seconds * second_max_weight)
                    
                    # Add North Pole crossing event
                    orbit_events.append({
                        'Time': pole_crossing_time,
                        'Type': 'North Pole Crossing',
                        'Orbit Number': orbit_num
                    })
            else:  # hemisphere == 'south'
                # Find the two points with minimum latitude
                sorted_by_latitude = sorted(data, key=lambda x: x[0])  # Ascending order for minimum
                if len(sorted_by_latitude) >= 2:
                    min_lat_point, second_min_lat_point = sorted_by_latitude[0], sorted_by_latitude[1]
                    
                    # Calculate weighted average time based on absolute latitude
                    min_latitude, min_lat_time = min_lat_point
                    second_min_latitude, second_min_time = second_min_lat_point
                    abs_min_latitude, abs_second_min_latitude = abs(min_latitude), abs(second_min_latitude)
                    min_weight = abs_min_latitude / (abs_min_latitude + abs_second_min_latitude)
                    second_min_weight = abs_second_min_latitude / (abs_min_latitude + abs_second_min_latitude)
                    
                    # Calculate weighted average time
                    time_diff_seconds = (second_min_time - min_lat_time).total_seconds()
                    pole_crossing_time = min_lat_time + timedelta(seconds=time_diff_seconds * second_min_weight)
                    
                    # Add South Pole crossing event
                    orbit_events.append({
                        'Time': pole_crossing_time,
                        'Type': 'South Pole Crossing',
                        'Orbit Number': orbit_num
                    })
        
        return orbit_events
    
    @property
    def repr_cols(self):
        """
        Columns to be used when representing the container (e.g., in tables or CSVs).
        
        :return: List of column names.
        :rtype: list
        """
        return ['Time', 'Type', 'Orbit Number']
    
    @property
    def default_time_label(self):
        """
        The default time field key used for time-series operations.
        
        :return: The key for the default time field.
        :rtype: str
        """
        return 'Time'
    
    def get_orbit_period(self, start_idx=0, num_orbits=1, node_type='Descending'):
        """
        Calculate the average orbit period based on node crossings.
        
        Args:
            start_idx: Index of the first node crossing to use
            num_orbits: Number of orbits to average over
            node_type: Type of node crossing to use ('Descending' or 'Ascending')
            
        Returns:
            Average orbit period as a timedelta
        """
        # Filter for specified node crossings
        node_type_str = f"{node_type} Node Crossing"
        nodes = [event for event in self if event['Type'] == node_type_str]
        
        if len(nodes) < start_idx + num_orbits + 1:
            raise ValueError(f"Not enough {node_type.lower()} node crossings to calculate {num_orbits} orbit periods")
        
        # Calculate time differences between consecutive node crossings
        periods = []
        for i in range(start_idx, start_idx + num_orbits):
            period = nodes[i+1]['Time'] - nodes[i]['Time']
            periods.append(period)
        
        # Calculate average period
        total_seconds = sum(p.total_seconds() for p in periods)
        return timedelta(seconds=total_seconds / len(periods))
    
    def filter_by_type(self, event_type):
        """
        Filter events by type.
        
        Args:
            event_type: Type of event to filter for (e.g., 'Ascending Node Crossing')
            
        Returns:
            New OrbitEventContainer with filtered events
        """
        filtered_data = [event.source for event in self if event['Type'] == event_type]
        return OrbitEventContainer(raw_data=filtered_data)
