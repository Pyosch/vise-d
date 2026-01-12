"""
MOSMIX forecast data parser.
"""

import io
import zipfile
from typing import Optional, List, Dict
from datetime import datetime
from lxml import etree
import pandas as pd

from ..config import DWDConfig
from ..downloader import Downloader
from .mosmix_params import MOSMIXParameterManager


class ForecastParser:
    """Parses MOSMIX forecast data from KMZ/KML files."""
    
    def __init__(self, downloader: Optional[Downloader] = None,
                 param_manager: Optional[MOSMIXParameterManager] = None):
        """
        Initialize forecast parser.
        
        Args:
            downloader: Downloader instance
            param_manager: MOSMIX parameter manager
        """
        self.downloader = downloader or Downloader()
        self.param_manager = param_manager or MOSMIXParameterManager()
    
    def fetch_forecast(self, station_ids: Optional[List[str]] = None,
                      parameters: Optional[List[str]] = None,
                      force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch MOSMIX forecast data.
        
        Args:
            station_ids: List of station IDs (None = all stations)
            parameters: List of parameter codes to extract (None = relevant params)
            force_refresh: Force re-download
            
        Returns:
            DataFrame with forecast data
        """
        # Download KMZ file
        url = f"{DWDConfig.MOSMIX_S}/{DWDConfig.MOSMIX_LATEST_FILE}"
        
        kmz_content = self.downloader.download(
            url,
            binary=True,
            force_refresh=force_refresh,
            expiry_hours=1  # MOSMIX updates hourly
        )
        
        # Parse KML from KMZ
        kml_root = self._extract_kml_from_kmz(kmz_content)
        
        # Determine parameters to extract
        if parameters is None:
            # Load parameter manager and get relevant parameters
            self.param_manager.load_parameters()
            parameters = list(self.param_manager.get_relevant_parameters().values())
        
        # Parse forecast data
        forecast_data = self._parse_kml_forecast(kml_root, station_ids, parameters)
        
        return forecast_data
    
    def _extract_kml_from_kmz(self, kmz_content: bytes) -> etree._Element:
        """
        Extract KML from KMZ archive.
        
        Args:
            kmz_content: KMZ file content
            
        Returns:
            Parsed KML root element
        """
        with zipfile.ZipFile(io.BytesIO(kmz_content)) as kmz:
            # KMZ typically contains a file named 'kmz' or similar
            kml_files = [f for f in kmz.namelist() if f.endswith('.kml')]
            
            if not kml_files:
                raise ValueError("No KML file found in KMZ archive")
            
            with kmz.open(kml_files[0]) as kml_file:
                kml_content = kml_file.read()
        
        # Parse KML
        root = etree.fromstring(kml_content)
        return root
    
    def _parse_kml_forecast(self, kml_root: etree._Element,
                           station_ids: Optional[List[str]],
                           parameters: List[str]) -> pd.DataFrame:
        """
        Parse KML forecast data.
        
        Args:
            kml_root: Parsed KML root element
            station_ids: Station IDs to extract (None = all)
            parameters: Parameter codes to extract
            
        Returns:
            DataFrame with forecast data
        """
        # Define KML namespaces
        namespaces = {
            'kml': 'http://www.opengis.net/kml/2.2',
            'dwd': 'https://opendata.dwd.de/weather/lib/pointforecast_dwd_extension_V1_0.xsd'
        }
        
        # Find timestamp information
        timestamps = self._extract_timestamps(kml_root, namespaces)
        
        # Find all station placemarks
        placemarks = kml_root.findall('.//kml:Placemark', namespaces)
        
        all_data = []
        
        for placemark in placemarks:
            # Extract station ID
            station_name = placemark.find('.//kml:name', namespaces)
            if station_name is None:
                continue
            
            station_id = station_name.text.strip()
            
            # Filter by station ID if specified
            if station_ids and station_id not in station_ids:
                continue
            
            # Extract coordinates
            coords_elem = placemark.find('.//kml:coordinates', namespaces)
            coordinates = None
            if coords_elem is not None:
                coord_parts = coords_elem.text.strip().split(',')
                if len(coord_parts) >= 2:
                    coordinates = {
                        'longitude': float(coord_parts[0]),
                        'latitude': float(coord_parts[1])
                    }
            
            # Extract forecast data
            extended_data = placemark.find('.//kml:ExtendedData', namespaces)
            if extended_data is None:
                continue
            
            station_data = self._extract_station_forecast(
                extended_data, namespaces, parameters, timestamps
            )
            
            # Add station info
            for record in station_data:
                record['station_id'] = station_id
                if coordinates:
                    record.update(coordinates)
            
            all_data.extend(station_data)
        
        # Convert to DataFrame
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        
        # Set datetime as index if available
        if 'datetime' in df.columns:
            df.set_index('datetime', inplace=True)
        
        return df
    
    def _extract_timestamps(self, kml_root: etree._Element,
                           namespaces: Dict[str, str]) -> List[datetime]:
        """Extract forecast timestamps from KML."""
        timestamps = []
        
        # Look for ForecastTimeSteps
        timesteps_elem = kml_root.find('.//dwd:ForecastTimeSteps', namespaces)
        
        if timesteps_elem is not None:
            timesteps_text = timesteps_elem.text
            if timesteps_text:
                # Parse ISO format timestamps
                time_strings = timesteps_text.strip().split()
                for ts in time_strings:
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        timestamps.append(dt)
                    except ValueError:
                        continue
        
        return timestamps
    
    def _extract_station_forecast(self, extended_data: etree._Element,
                                  namespaces: Dict[str, str],
                                  parameters: List[str],
                                  timestamps: List[datetime]) -> List[Dict]:
        """Extract forecast values for a station."""
        records = []
        
        # Find all Forecast elements
        forecasts = extended_data.findall('.//dwd:Forecast', namespaces)
        
        for forecast in forecasts:
            # Get parameter code
            param_elem = forecast.get(f"{{{namespaces['dwd']}}}elementName")
            if param_elem is None:
                param_elem = forecast.find('.//dwd:elementName', namespaces)
                if param_elem is not None:
                    param_elem = param_elem.text
            
            if not param_elem or param_elem not in parameters:
                continue
            
            # Get values
            values_elem = forecast.find('.//dwd:value', namespaces)
            if values_elem is None:
                continue
            
            values_text = values_elem.text
            if not values_text:
                continue
            
            # Parse values (space or comma separated)
            values = []
            for v in values_text.strip().split():
                try:
                    values.append(float(v))
                except ValueError:
                    values.append(None)
            
            # Match values with timestamps
            for i, (timestamp, value) in enumerate(zip(timestamps, values)):
                # Find or create record for this timestamp
                record = None
                for r in records:
                    if r.get('datetime') == timestamp:
                        record = r
                        break
                
                if record is None:
                    record = {'datetime': timestamp}
                    records.append(record)
                
                record[param_elem] = value
        
        return records
    
    def get_forecast_for_location(self, latitude: float, longitude: float,
                                  parameters: Optional[List[str]] = None,
                                  force_refresh: bool = False) -> pd.DataFrame:
        """
        Get forecast for a specific location (finds nearest station).
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameters: Parameter codes to extract
            force_refresh: Force re-download
            
        Returns:
            DataFrame with forecast data for nearest station
        """
        # Fetch all forecasts
        df = self.fetch_forecast(parameters=parameters, force_refresh=force_refresh)
        
        if df.empty:
            return df
        
        # Find nearest station
        if 'latitude' in df.columns and 'longitude' in df.columns:
            # Calculate distances
            from ..stations import StationManager
            
            min_distance = float('inf')
            nearest_station = None
            
            for station_id in df['station_id'].unique():
                station_data = df[df['station_id'] == station_id].iloc[0]
                station_lat = station_data['latitude']
                station_lon = station_data['longitude']
                
                distance = StationManager._haversine_distance(
                    latitude, longitude, station_lat, station_lon
                )
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_station = station_id
            
            # Filter by nearest station
            return df[df['station_id'] == nearest_station].copy()
        
        return df
