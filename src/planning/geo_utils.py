"""Geographic utilities for planning operations.

Provides coordinate system transformations and Folium helper functions.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import folium
from pyproj import CRS


def get_local_crs(lon: float, lat: float) -> CRS:
    """Create a local Transverse Mercator CRS centered at given coordinates.
    
    Args:
        lon: Longitude in decimal degrees
        lat: Latitude in decimal degrees
        
    Returns:
        pyproj.CRS: Local coordinate reference system
    """
    return CRS.from_proj4(
        f"+proj=tmerc +lat_0={lat} +lon_0={lon} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    )


def find_circle_markers(obj) -> list:
    """Recursively find all CircleMarker objects in a Folium map.
    
    Args:
        obj: Folium map object or child element
        
    Returns:
        list: List of folium.CircleMarker objects found
    """
    markers = []
    if isinstance(obj, folium.CircleMarker):
        markers.append(obj)
    if hasattr(obj, '_children'):
        for child in obj._children.values():
            markers.extend(find_circle_markers(child))
    return markers
