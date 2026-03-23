#Python Imports
import pdb
from datetime import datetime
import numpy as np
import spiceypy as sp
from enum import Enum
from typing import Dict, Tuple, Union, Optional

#JPL Imports
from jpl_time import Time

#This Library Imports
from tts_data_utils.core.data_container import DataContainer
from tts_data_utils.core.data_item import DataItem

class Planet(Enum):
    """Enum representing planets and their reference ellipsoid parameters."""
    MERCURY = {
        'name': 'Mercury',
        'a': 2439.7,      # Semi-major axis in km
        'f': 0.0,         # Flattening (Mercury is nearly spherical)
        'frame': 'IAU_MERCURY'
    }
    VENUS = {
        'name': 'Venus',
        'a': 6051.8,      # Semi-major axis in km
        'f': 0.0,         # Flattening (Venus is nearly spherical)
        'frame': 'IAU_VENUS'
    }
    EARTH = {
        'name': 'Earth',
        'a': 6378.1370,   # Semi-major axis in km (WGS84)
        'f': 1 / 298.257223563,  # Flattening (WGS84)
        'frame': 'ITRF93'
    }
    MOON = {
        'name': 'Moon',
        'a': 1737.4,      # Semi-major axis in km
        'f': 0.0012,      # Flattening
        'frame': 'MOON_ME'
    }
    MARS = {
        'name': 'Mars',
        'a': 3396.19,     # Semi-major axis in km
        'f': 1 / 169.8,   # Flattening
        'frame': 'IAU_MARS'
    }
    JUPITER = {
        'name': 'Jupiter',
        'a': 71492.0,     # Semi-major axis in km
        'f': 1 / 15.4,    # Flattening
        'frame': 'IAU_JUPITER'
    }
    SATURN = {
        'name': 'Saturn',
        'a': 60268.0,     # Semi-major axis in km
        'f': 1 / 10.2,    # Flattening
        'frame': 'IAU_SATURN'
    }
    URANUS = {
        'name': 'Uranus',
        'a': 25559.0,     # Semi-major axis in km
        'f': 1 / 43.6,    # Flattening
        'frame': 'IAU_URANUS'
    }
    NEPTUNE = {
        'name': 'Neptune',
        'a': 24764.0,     # Semi-major axis in km
        'f': 1 / 58.5,    # Flattening
        'frame': 'IAU_NEPTUNE'
    }
    PLUTO = {
        'name': 'Pluto',
        'a': 1188.3,      # Semi-major axis in km
        'f': 0.0,         # Flattening (assumed spherical)
        'frame': 'IAU_PLUTO'
    }

class GeodeticConverter:
    """Converts between geodetic (lat/lon/alt) and Cartesian coordinates for any planet."""
    
    def __init__(self, planet: Union[Planet, Dict, str] = Planet.EARTH):
        """Initialize the converter with planetary parameters.
        
        Args:
            planet: Can be a Planet enum, a dictionary with 'a' and 'f' keys,
                   or a string matching a Planet enum name
        """
        # Process the planet parameter
        if isinstance(planet, str):
            try:
                planet = Planet[planet.upper()]
            except KeyError:
                raise ValueError(f"Unknown planet name: {planet}. Use one of {[p.name for p in Planet]}")
        
        if isinstance(planet, Planet):
            self.planet_name = planet.value['name']
            self.a = planet.value['a']            # Semi-major axis in km
            self.f = planet.value['f']            # Flattening
            self.frame = planet.value['frame']     # Reference frame
        elif isinstance(planet, dict):
            self.planet_name = planet.get('name', 'Custom')
            self.a = planet['a']                  # Semi-major axis must be provided
            self.f = planet['f']                  # Flattening must be provided
            self.frame = planet.get('frame', '')   # Reference frame is optional
        else:
            raise TypeError("Planet must be a Planet enum, a string name, or a dict with 'a' and 'f' keys")
            
        # Derived parameters
        self.b = self.a * (1 - self.f)     # Semi-minor axis
        self.e2 = self.f * (2 - self.f)    # First eccentricity squared
        self.e_prime2 = self.e2 / (1 - self.e2) # Second eccentricity squared

    def lla_to_cartesian(self, lat, lon, alt=0):
        """lat/lon in degrees, alt in km. Returns ECEF XYZ in km.
        
        Uses a numerically stable formula that works well for all planet shapes.
        """
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        
        sin_lat = np.sin(lat_rad)
        cos_lat = np.cos(lat_rad)
        sin_lon = np.sin(lon_rad)
        cos_lon = np.cos(lon_rad)
        
        # Radius of curvature in prime vertical
        N = self.a / np.sqrt(1 - self.e2 * sin_lat**2)
        
        # Calculate position
        x = (N + alt) * cos_lat * cos_lon
        y = (N + alt) * cos_lat * sin_lon
        
        # More accurate formula for Z coordinate
        z = (N * (1 - self.e2) + alt) * sin_lat
        
        return np.array([x, y, z])

    def cartesian_to_lla(self, x, y, z):
        """Returns Lat (deg), Lon (deg), Alt (km).
        
        Uses the Olson algorithm with modifications for high-flattening bodies.
        This is one of the most accurate algorithms for geodetic coordinate conversion.
        """
        # Calculate longitude (this is exact)
        lon = np.arctan2(y, x)
        
        # Handle special case at poles
        p = np.sqrt(x**2 + y**2)
        if p < 1e-12:
            lat = np.pi/2 if z > 0 else -np.pi/2
            alt = abs(z) - self.b
            return np.degrees(lat), np.degrees(lon), alt
        
        # Cache frequently used values
        e2 = self.e2
        b = self.b
        a = self.a
        
        # For high flattening bodies, use a different approach
        if self.f > 0.05:  # High flattening
            # Use a direct approach that works better for high flattening
            # Start with a good initial guess
            r = np.sqrt(x*x + y*y + z*z)
            sin_lat_init = z / r
            lat = np.arcsin(sin_lat_init)
            
            # Iterative refinement
            for _ in range(15):  # More iterations for high flattening
                prev_lat = lat
                sin_lat = np.sin(lat)
                cos_lat = np.cos(lat)
                
                # Calculate meridional radius of curvature
                M = a * (1 - e2) / np.power(1 - e2 * sin_lat * sin_lat, 1.5)
                
                # Calculate normal radius of curvature
                N = a / np.sqrt(1 - e2 * sin_lat * sin_lat)
                
                # Improved latitude estimate
                h = p / cos_lat - N
                lat = np.arctan2(z * (N + h), p * (N * (1 - e2) + h))
                
                # Check for convergence
                if abs(lat - prev_lat) < 1e-13:
                    break
            
            # Final height calculation
            sin_lat = np.sin(lat)
            cos_lat = np.cos(lat)
            N = a / np.sqrt(1 - e2 * sin_lat * sin_lat)
            
            if abs(cos_lat) < 1e-10:  # Near poles
                alt = abs(z) / abs(sin_lat) - N * (1 - e2)
            else:
                alt = p / cos_lat - N
        
        else:  # Normal flattening
            # Use the standard iterative approach for Earth-like planets
            # This is proven to be very accurate for normal flattening values
            
            # Initial estimate of latitude
            lat = np.arctan2(z, p * (1 - self.e2))
            
            # Iterative refinement
            for _ in range(6):  # Usually converges in 2-3 iterations
                sin_lat = np.sin(lat)
                cos_lat = np.cos(lat)
                
                # Radius of curvature in prime vertical
                N = a / np.sqrt(1 - e2 * sin_lat * sin_lat)
                
                # Height estimate
                h = p / cos_lat - N
                
                # Improved latitude estimate
                prev_lat = lat
                lat = np.arctan2(z, p * (1 - e2 * N / (N + h)))
                
                # Check for convergence
                if abs(lat - prev_lat) < 1e-14:
                    break
            
            # Final height calculation
            sin_lat = np.sin(lat)
            cos_lat = np.cos(lat)
            N = a / np.sqrt(1 - e2 * sin_lat * sin_lat)
            alt = p / cos_lat - N
        
        return np.degrees(lat), np.degrees(lon), alt

    def get_enu(self, observer_lla, target_lla):
        """Calculates ENU vector (km) from observer to target."""
        obs_lat, obs_lon, obs_alt = observer_lla
        
        p_obs = self.lla_to_cartesian(obs_lat, obs_lon, obs_alt)
        p_target = self.lla_to_cartesian(*target_lla)
        
        v_ecef = p_target - p_obs
        
        phi = np.radians(obs_lat)
        lam = np.radians(obs_lon)
        
        # Rotation Matrix: ECEF to ENU
        R_mat = np.array([
            [-np.sin(lam),                  np.cos(lam),                 0],
            [-np.sin(phi)*np.cos(lam), -np.sin(phi)*np.sin(lam),  np.cos(phi)],
            [ np.cos(phi)*np.cos(lam),  np.cos(phi)*np.sin(lam),  np.sin(phi)]
        ])
        
        return R_mat @ v_ecef

    def calculate_look_angles(self, observer_lla, target_lla):
        """Returns Azimuth (deg), Elevation (deg), and Range (km)."""
        east, north, up = self.get_enu(observer_lla, target_lla)
        
        range_dist = np.sqrt(east**2 + north**2 + up**2)
        # Handle zero-range case to avoid arcsin(nan)
        if range_dist < 1e-9:
            return {"azimuth": 0.0, "elevation": 90.0, "range": 0.0}
            
        elevation = np.degrees(np.arcsin(up / range_dist))
        azimuth = np.degrees(np.arctan2(east, north)) % 360
        
        return {
            "azimuth": azimuth,
            "elevation": elevation,
            "range": range_dist
        }


class EpehmerisItem(DataItem):
    DICT_VALID_KEYS = [
        ('JD', float), 
        ('Time', datetime), 
        ('x', float), 
        ('y', float), 
        ('z', float), 
        ('v_x', float),
        ('v_y', float),
        ('v_z', float),
        ('planet', str),  # Added planet field
        ]

    TIME_FORMATS = {
        'Time': 'A.D. %Y-%b-%d %H:%M:%S.%f',
    }
    NAME = 'Ephermis Item'

    @property
    def default_html_row_style(self):
        return {}
    
    @property
    def time(self):
        return self.source['Time']
        return Time(self.source['scet'])

    @property
    def time_str(self):
        return datetime.strftime(self.source['Time'], self.TIME_FORMATS['Time'])
        return Time(self.source['scet'])
    
    @property
    def name(self):
        return self.source['name']

    @property
    def state_vector(self):
        return np.array([x,y,z,vx,vy,vz])

    @property
    def position(self):
        return np.array([self['x'], self['y'], self['z']])

    @property
    def velocity(self):
        return np.array([self['v_x'], self['v_y'], self['v_z']])

    @property
    def et(self):
        return sp.str2et(self.spice_utc_str)

    @property
    def planet(self) -> Planet:
        """Get the planet for this ephemeris item."""
        if 'planet' in self.source and self.source['planet']:
            try:
                return Planet[self.source['planet'].upper()]
            except (KeyError, AttributeError):
                # Default to Earth if planet string doesn't match any enum
                return Planet.EARTH
        return Planet.EARTH
        
    @property
    def rotation_matrix(self):
        """Get rotation matrix from J2000 to planet-fixed frame."""
        frame = self.planet.value['frame']
        return sp.pxform("J2000", frame, self.et)

    @property
    def spice_utc_str(self):
        return datetime.strftime(self['Time'], "%Y-%m-%d T%H:%M:%S")

    @property
    def planet_fixed(self):
        """Get position in planet-fixed coordinates."""
        return self.rotation_matrix @ self.position  # using numpy
        
    @property
    def earth_fixed(self):
        """Legacy property for backward compatibility."""
        return self.planet_fixed

    @property
    def spherical_coords(self):
        """Calculate spherical coordinates (r, theta, phi) from planet-fixed Cartesian coordinates."""
        x, y, z = self.planet_fixed
        r = np.sqrt(x**2 + y**2 + z**2)
        # Handle the case where r is very small to avoid division by zero
        if r < 1e-9:
            return r, 0.0, 0.0
        theta = np.arccos(z / r)          # polar angle from z-axis
        phi = np.arctan2(y, x)            # azimuth from x-axis
        return r, theta, phi

    @property
    def lat_lon(self):
        r, phi, theta = self.spherical_coords
        lat = (np.pi/2 - phi)/np.pi*180
        lon = theta/np.pi*180
        return lat, lon

    def pos_rel_planet_point(self, lat, lon, alt, planet=None):
        """Calculate look angles from a point on a planet to the spacecraft.
        
        Args:
            lat: Observer latitude in degrees
            lon: Observer longitude in degrees
            alt: Observer altitude in km above reference ellipsoid
            planet: Planet to use (defaults to the item's planet)
            
        Returns:
            Dictionary with azimuth, elevation, and range
        """
        if planet is None:
            planet = self.planet
            
        gc = GeodeticConverter(planet)
        sc_lla = gc.cartesian_to_lla(*self.planet_fixed)
        obs_lla = (lat, lon, alt)
        return gc.calculate_look_angles(obs_lla, sc_lla)
        
    def pos_rel_earth_point(self, lat, lon, alt):
        """Legacy method for backward compatibility."""
        return self.pos_rel_planet_point(lat, lon, alt, Planet.EARTH)



class EphemerisContainer(DataContainer):
    NAME = 'Epehmeris'
    DATA_ITEM_CLS = EpehmerisItem
    
    def __init__(self, raw_data=None, metadata=None, name=None, cast_fields=False, **kwargs):
        if metadata is not None:
            metadata = {k:v for k, v in metadata.items() if k[0] != '_' and k != 'dictionary'}
        super().__init__(raw_data=raw_data, metadata=metadata, cast_fields=cast_fields, **kwargs)
        self.name = 'EVR Container' if name is None else name
        self._repr_cols = ['vcid', 'name', 'scet', 'message']
        self._default_time_label = 'Time'
        self._repr_cols = [x for x, _ in self.DATA_ITEM_CLS.DICT_VALID_KEYS]
        self._csv_cols = [x for x, _ in self.DATA_ITEM_CLS.DICT_VALID_KEYS]

    def _impl_init(self):
        """
        Internal implementation hook for initialization logic.
        """
        return

    def read_csv(self, csv_path, planet='EARTH'):
        """Read ephemeris data from a CSV file.
        
        Args:
            csv_path: Path to the CSV file
            planet: Planet name or Planet enum (defaults to EARTH)
            
        Returns:
            List of record dictionaries
        """
        # Convert planet to string if it's an enum
        if isinstance(planet, Planet):
            planet = planet.name
        elif isinstance(planet, dict) and 'name' in planet:
            planet = planet['name'].upper()
            
        soe_found = False
        eoe_found = False
        records = []
        for line in open(csv_path, 'r'):
            line = line.strip()
            if line == '$$EOE':
                eoe_found = True
            if soe_found and not eoe_found:
                row = [x.strip() for x in line.split(',')]
                records.append({
                    'JD': row[0],
                    'Time': row[1],
                    'x': row[2],
                    'y': row[3],
                    'z': row[4],
                    'v_x': row[5],
                    'v_y': row[6],
                    'v_z': row[7],
                    'planet': planet
                })
            if line == '$$SOE':
                soe_found = True
        return records

    @property
    def repr_cols(self):
        return self._repr_cols

    @property
    def default_time_label(self):
        return self._default_time_label

