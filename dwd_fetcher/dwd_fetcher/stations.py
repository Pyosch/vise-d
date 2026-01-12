"""
Station metadata management.
Downloads, parses, and searches DWD station description files.
"""

import io
import math
import requests
import pandas as pd
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

from .config import DWDConfig
from .cache import CacheManager


@dataclass
class Station:
    """Represents a DWD weather station."""
    station_id: str
    name: str
    latitude: float
    longitude: float
    elevation: float
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    parameter: str  # Which parameter this station provides
    distance_km: Optional[float] = None  # Distance from search location
    quality_score: Optional[float] = None  # Data availability score (0.0-1.0)
    combined_score: Optional[float] = None  # Combined quality/distance score
    
    def is_active(self, date: Optional[datetime] = None) -> bool:
        """Check if station is active for a given date."""
        if date is None:
            date = datetime.now()
        
        if self.start_date and date < self.start_date:
            return False
        if self.end_date and date > self.end_date:
            return False
        
        return True
    
    def __repr__(self) -> str:
        return (f"Station({self.station_id}, {self.name}, "
                f"lat={self.latitude:.2f}, lon={self.longitude:.2f}, "
                f"param={self.parameter})")
    
    def __hash__(self) -> int:
        """Make Station hashable for use in dictionaries."""
        return hash((self.station_id, self.parameter))
    
    def __eq__(self, other) -> bool:
        """Compare stations by ID and parameter."""
        if not isinstance(other, Station):
            return False
        return self.station_id == other.station_id and self.parameter == other.parameter


class StationQualityScorer:
    """Scores stations based on data availability and quality."""
    
    def __init__(self, cache_manager: CacheManager, downloader):
        """
        Initialize quality scorer.
        
        Args:
            cache_manager: Cache manager for caching availability checks
            downloader: Downloader instance for HEAD requests
        """
        self.cache_manager = cache_manager
        self.downloader = downloader
        self.availability_cache_hours = 24 * 7  # 7 days
    
    def get_availability_score(self, station: Station, parameter: str, 
                              resolution: str, 
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> float:
        """
        Calculate availability score for a station.
        
        Checks if data files exist AND evaluates temporal relevance.
        Score combines file existence with how well the station's active period
        matches the requested date range.
        
        Args:
            station: Station to check
            parameter: Parameter name
            resolution: Time resolution
            start_date: Optional start date for date range check
            end_date: Optional end date for date range check
            
        Returns:
            Score between 0.0 (no/irrelevant data) and 1.0 (relevant data available)
            - 1.0: File exists AND station active during requested period
            - 0.7: File exists AND station ended recently (< 1 year ago)
            - 0.3: File exists AND station ended 1-3 years ago
            - 0.1: File exists AND station ended > 3 years ago
            - 0.0: No file OR station never active during relevant period
        """
        # Build cache key for this specific check
        cache_key = (f"quality_{station.station_id}_{parameter}_{resolution}_"
                    f"{start_date.strftime('%Y%m%d') if start_date else 'none'}")
        
        # Check cache first
        cached_score = self.cache_manager.get(
            cache_key, 
            expiry_hours=self.availability_cache_hours,
            binary=False
        )
        if cached_score is not None:
            try:
                return float(cached_score)
            except (ValueError, TypeError):
                pass  # Invalid cache, continue to check
        
        # Determine which file(s) to check based on date range
        # Match logic from observations.py
        need_recent = True
        need_historical = False
        
        if start_date is not None:
            # If start_date is far in the past, we likely need historical data
            # DWD typically keeps ~500 days in recent files
            from datetime import timedelta
            recent_boundary = datetime.now() - timedelta(days=400)
            if start_date < recent_boundary:
                need_historical = True
        
        # Build URLs for file checks
        base_url = DWDConfig.get_obs_url(parameter, resolution)
        param_code = DWDConfig.get_param_code(parameter, resolution)
        
        # Build filename based on resolution, matching observations.py logic
        station_id_str = f"{int(station.station_id):05d}"
        
        # Check recent file
        score = 0.0
        if need_recent:
            # Special handling for 10-minute data (different naming conventions)
            if resolution == "10_minutes":
                if param_code == "ST":
                    # Solar 10-minute data uses "10minutenwerte_SOLAR" format
                    recent_filename = f"10minutenwerte_SOLAR_{station_id_str}_akt.zip"
                elif param_code == "FF":
                    # Wind 10-minute data uses "10minutenwerte_wind" format
                    recent_filename = f"10minutenwerte_wind_{station_id_str}_akt.zip"
                else:
                    # Other 10-minute parameters use standard format
                    recent_filename = f"10minutenwerte_{param_code}_{station_id_str}_akt.zip"
            else:
                # Standard naming for hourly and daily data
                if resolution == "hourly":
                    time_str = "stundenwerte"
                elif resolution == "daily":
                    time_str = "tageswerte"
                else:
                    time_str = "stundenwerte"
                
                recent_filename = f"{time_str}_{param_code}_{station_id_str}_akt.zip"
            
            recent_url = f"{base_url}/recent/{recent_filename}"
            
            file_exists = self.downloader.check_file_exists(recent_url)
        
        # If we need historical and recent doesn't exist, check historical
        if need_historical and not file_exists:
            # Historical files have variable naming with date ranges
            # Build pattern matching historical naming
            if resolution == "10_minutes":
                if param_code == "ST":
                    hist_pattern = f"10minutenwerte_SOLAR_{station_id_str}_"
                elif param_code == "FF":
                    hist_pattern = f"10minutenwerte_wind_{station_id_str}_"
                else:
                    hist_pattern = f"10minutenwerte_{param_code}_{station_id_str}_"
            else:
                if resolution == "hourly":
                    time_str = "stundenwerte"
                elif resolution == "daily":
                    time_str = "tageswerte"
                else:
                    time_str = "stundenwerte"
                hist_pattern = f"{time_str}_{param_code}_{station_id_str}_"
            
            try:
                files = self.downloader.list_directory(f"{base_url}/historical/")
                # Check if any file matches our pattern
                for file in files:
                    if file.startswith(hist_pattern) and file.endswith('_hist.zip'):
                        file_exists = True
                        break
            except Exception:
                # If directory listing fails, assume no historical data
                pass
        
        # Calculate temporal relevance score
        temporal_score = self._calculate_temporal_relevance(
            station, start_date, end_date
        )
        
        # Final score = file existence × temporal relevance
        score = (1.0 if file_exists else 0.0) * temporal_score
        
        # Cache the score
        self.cache_manager.set(
            cache_key, 
            str(score),
            extension=".txt",
            binary=False
        )
        
        return score
    
    def _calculate_temporal_relevance(self, station: Station,
                                     start_date: Optional[datetime],
                                     end_date: Optional[datetime]) -> float:
        """
        Calculate temporal relevance score based on station's active period.
        
        Args:
            station: Station to evaluate
            start_date: Requested start date (None = any time)
            end_date: Requested end date (None = current time)
            
        Returns:
            Score between 0.0 (not relevant) and 1.0 (highly relevant)
        """
        # If no date constraints, file existence is sufficient
        if start_date is None and end_date is None:
            return 1.0
        
        # Use current time if no end_date specified
        request_end = end_date if end_date else datetime.now()
        request_start = start_date if start_date else request_end
        
        # If station has no metadata about active period, assume it might be relevant
        if station.end_date is None and station.start_date is None:
            return 0.5  # Unknown, give benefit of doubt
        
        # Check if station was active during requested period
        station_end = station.end_date if station.end_date else datetime.now()
        station_start = station.start_date if station.start_date else datetime(1900, 1, 1)
        
        # Check for temporal overlap
        overlap_start = max(station_start, request_start)
        overlap_end = min(station_end, request_end)
        
        # If there's overlap, perfect score
        if overlap_start <= overlap_end:
            return 1.0
        
        # No overlap - score based on how recently station ended
        from datetime import timedelta
        
        # Calculate time gap between station end and request start
        if station_end < request_start:
            gap_days = (request_start - station_end).days
            
            if gap_days <= 365:  # Within 1 year
                return 0.7
            elif gap_days <= 1095:  # 1-3 years
                return 0.3
            elif gap_days <= 1825:  # 3-5 years
                return 0.1
            else:  # > 5 years
                return 0.05
        
        # Station starts after requested period (future data)
        # This shouldn't normally happen, but give low score
        return 0.1


class StationManager:
    """Manages DWD station metadata and search functionality."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None, downloader = None):
        """
        Initialize station manager.
        
        Args:
            cache_manager: Cache manager instance
            downloader: Downloader instance for quality checks
        """
        self.cache_manager = cache_manager or CacheManager()
        self.stations: Dict[str, Dict[str, Station]] = {}  # param -> {station_id -> Station}
        self._loaded_parameters: Set[str] = set()
        
        # Initialize quality scorer if downloader provided
        self.quality_scorer = None
        if downloader is not None:
            self.quality_scorer = StationQualityScorer(self.cache_manager, downloader)
    
    def load_stations(self, parameter: str, resolution: str = "hourly",
                     force_refresh: bool = False) -> Dict[str, Station]:
        """
        Load station metadata for a parameter.
        
        Args:
            parameter: Parameter name ('solar', 'wind', 'temperature', 'pressure')
            resolution: Time resolution
            force_refresh: Force refresh from server
            
        Returns:
            Dictionary mapping station IDs to Station objects
        """
        cache_key = f"{parameter}_{resolution}"
        
        if cache_key in self._loaded_parameters and not force_refresh:
            return self.stations.get(parameter, {})
        
        # Get station description file URL
        # Station files are in the parameter-specific directory
        base_url = DWDConfig.get_obs_url(parameter, resolution)
        filename = DWDConfig.get_station_description_filename(parameter, resolution)
        # Try multiple possible locations for station files
        urls_to_try = [
            f"{base_url}/{filename}",  # In parameter directory
            f"{base_url}/recent/{filename}",  # In recent subdirectory (for solar)
            f"{base_url}/historical/{filename}",  # In historical subdirectory (for solar)
            f"{DWDConfig.HELP_URL}/{filename}",  # In help directory
        ]
        
        # Fetch station description file - try multiple locations
        content = None
        last_error = None
        
        for url in urls_to_try:
            try:
                content = self.cache_manager.get_or_fetch(
                    url=url,
                    fetch_func=lambda u=url: self._fetch_station_file(u),
                    expiry_hours=24 * 7,  # Cache for 7 days
                    extension=".txt",
                    binary=False,
                    force_refresh=force_refresh
                )
                break  # Success, exit loop
            except Exception as e:
                last_error = e
                continue
        
        if content is None:
            raise RuntimeError(f"Failed to fetch station file for {parameter}. Tried locations: {urls_to_try}. Last error: {last_error}")
        
        # Parse station data
        stations = self._parse_station_file(content, parameter)
        
        if parameter not in self.stations:
            self.stations[parameter] = {}
        
        self.stations[parameter] = stations
        self._loaded_parameters.add(cache_key)
        
        return stations
    
    def _fetch_station_file(self, url: str) -> str:
        """Fetch station description file from DWD."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            # DWD files are typically in Latin-1 or UTF-8
            return response.content.decode('latin-1')
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch station file from {url}: {e}")
    
    def _parse_station_file(self, content: str, parameter: str) -> Dict[str, Station]:
        """
        Parse DWD station description file.
        
        Args:
            content: File content
            parameter: Parameter name
            
        Returns:
            Dictionary of Station objects
        """
        stations = {}
        
        # DWD station files are fixed-width format
        lines = content.strip().split('\n')
        
        # Skip header lines (usually first 2 lines)
        data_start = 2
        for i, line in enumerate(lines):
            if line.strip().startswith('---'):
                data_start = i + 1
                break
        
        for line in lines[data_start:]:
            line = line.strip()
            if not line:
                continue
            
            try:
                # Split by whitespace and filter empty strings
                parts = [p for p in line.split() if p]
                
                if len(parts) < 7:
                    continue
                
                station_id = parts[0].strip()
                date_from_str = parts[1].strip()
                date_to_str = parts[2].strip()
                elevation = float(parts[3])
                latitude = float(parts[4])
                longitude = float(parts[5])
                # Station name might have multiple words - join the rest
                name = ' '.join(parts[6:])
                # Remove Bundesland if present (last token)
                name_parts = name.rsplit(maxsplit=1)
                if len(name_parts) > 1:
                    name = name_parts[0].strip()
                
                # Parse dates (format: YYYYMMDD)
                start_date = None
                end_date = None
                
                try:
                    if date_from_str and date_from_str.isdigit() and len(date_from_str) == 8:
                        start_date = datetime.strptime(date_from_str, '%Y%m%d')
                except ValueError:
                    pass
                
                try:
                    if date_to_str and date_to_str.isdigit() and len(date_to_str) == 8:
                        end_date = datetime.strptime(date_to_str, '%Y%m%d')
                except ValueError:
                    pass
                
                station = Station(
                    station_id=station_id,
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    elevation=elevation,
                    start_date=start_date,
                    end_date=end_date,
                    parameter=parameter
                )
                
                stations[station_id] = station
                
            except (ValueError, IndexError) as e:
                # Skip malformed lines
                continue
        
        return stations
    
    def find_nearest_stations(self, latitude: float, longitude: float,
                             parameter: str, n: int = 5,
                             max_distance_km: Optional[float] = None,
                             resolution: str = "hourly",
                             active_only: bool = True,
                             date: Optional[datetime] = None,
                             ranking_strategy: str = "distance_only",
                             quality_check_limit: int = 5,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List[Station]:
        """
        Find nearest stations to a location.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameter: Parameter name
            n: Number of stations to return
            max_distance_km: Maximum distance in km
            resolution: Time resolution
            active_only: Only return active stations
            date: Date for which station should be active
            ranking_strategy: Strategy for ranking stations:
                - "distance_only": Sort by distance only (default, fastest)
                - "quality_weighted": Score by quality/distance² (best balance)
                - "quality_first": Sort by quality, then distance (prioritize data availability)
            quality_check_limit: Number of closest stations to check for quality (default: 5)
            start_date: Optional start date for quality assessment
            end_date: Optional end date for quality assessment
            
        Returns:
            List of Station objects sorted by chosen strategy
        """
        # Load stations if not already loaded
        if parameter not in self.stations:
            self.load_stations(parameter, resolution)
        
        stations_list = list(self.stations[parameter].values())
        
        # Filter active stations
        if active_only:
            stations_list = [s for s in stations_list if s.is_active(date)]
        
        # Calculate distances
        for station in stations_list:
            station.distance_km = self._haversine_distance(
                latitude, longitude,
                station.latitude, station.longitude
            )
        
        # Sort by distance initially
        stations_list.sort(key=lambda s: s.distance_km)
        
        # Filter by max distance
        if max_distance_km is not None:
            stations_list = [s for s in stations_list if s.distance_km <= max_distance_km]
        
        # Apply quality-based ranking if requested and quality scorer available
        if ranking_strategy != "distance_only" and self.quality_scorer is not None:
            # Only check quality for the closest N stations to save time
            candidates = stations_list[:quality_check_limit]
            rest = stations_list[quality_check_limit:]
            
            # Score each candidate
            for station in candidates:
                quality_score = self.quality_scorer.get_availability_score(
                    station, parameter, resolution, start_date, end_date
                )
                station.quality_score = quality_score
            
            # Sort candidates by chosen strategy
            if ranking_strategy == "quality_weighted":
                # Combined score: (quality² × 1000) / distance²
                # This gives temporal relevance more weight
                # A station with perfect quality (1.0) at 20km beats
                # a station with poor quality (0.3) at 6km
                for station in candidates:
                    if station.distance_km > 0:
                        # Square the quality score to amplify differences
                        # Multiply by 1000 to put quality and distance on similar scales
                        station.combined_score = (station.quality_score ** 2 * 1000) / (station.distance_km ** 2)
                    else:
                        station.combined_score = station.quality_score * 1000000  # Very close station
                candidates.sort(key=lambda s: s.combined_score, reverse=True)
                
            elif ranking_strategy == "quality_first":
                # Sort by quality (descending), then by distance (ascending)
                candidates.sort(key=lambda s: (-s.quality_score, s.distance_km))
            
            # Recombine: scored candidates + remaining stations
            stations_list = candidates + rest
        
        # Return top n
        return stations_list[:n]
    
    def find_stations_with_all_parameters(self, latitude: float, longitude: float,
                                         parameters: List[str],
                                         n: int = 5,
                                         max_distance_km: Optional[float] = None,
                                         resolution: str = "hourly") -> Dict[str, List[Station]]:
        """
        Find stations that provide all required parameters.
        
        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            parameters: List of parameter names
            n: Number of stations per parameter
            max_distance_km: Maximum distance in km
            resolution: Time resolution
            
        Returns:
            Dictionary mapping parameter to list of stations
        """
        result = {}
        
        for param in parameters:
            stations = self.find_nearest_stations(
                latitude, longitude, param, n,
                max_distance_km, resolution
            )
            result[param] = stations
        
        return result
    
    def get_station_by_id(self, station_id: str, parameter: str,
                         resolution: str = "hourly") -> Optional[Station]:
        """
        Get station by ID.
        
        Args:
            station_id: Station ID
            parameter: Parameter name
            resolution: Time resolution
            
        Returns:
            Station object or None
        """
        if parameter not in self.stations:
            self.load_stations(parameter, resolution)
        
        return self.stations[parameter].get(station_id)
    
    def check_parameter_availability(self, station_ids: List[str],
                                    parameters: List[str],
                                    resolution: str = "hourly") -> Dict[str, Dict[str, bool]]:
        """
        Check which parameters are available at which stations.
        
        Args:
            station_ids: List of station IDs
            parameters: List of parameter names
            resolution: Time resolution
            
        Returns:
            Nested dict: {station_id: {parameter: is_available}}
        """
        availability = {}
        
        for station_id in station_ids:
            availability[station_id] = {}
            
            for param in parameters:
                if param not in self.stations:
                    self.load_stations(param, resolution)
                
                availability[station_id][param] = station_id in self.stations.get(param, {})
        
        return availability
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float,
                           lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula.
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in km
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine formula
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_station_coverage_report(self, parameters: List[str],
                                   resolution: str = "hourly") -> Dict[str, Dict[str, int]]:
        """
        Get report on station coverage for parameters.
        
        Args:
            parameters: List of parameters
            resolution: Time resolution
            
        Returns:
            Report dictionary
        """
        report = {}
        
        for param in parameters:
            if param not in self.stations:
                self.load_stations(param, resolution)
            
            stations = self.stations.get(param, {})
            active_count = sum(1 for s in stations.values() if s.is_active())
            
            report[param] = {
                'total_stations': len(stations),
                'active_stations': active_count,
                'inactive_stations': len(stations) - active_count
            }
        
        return report
