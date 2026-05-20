"""Location and weather station selector UI component.

Provides a reusable Streamlit component for selecting DWD weather stations
or entering coordinates manually. Includes address search with geocoding.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from typing import Optional, Dict, List
from datetime import datetime, date, timedelta
import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from vpplib.dwd_client import DWDClient
from src.config import DWD, DATA_DIR


def location_weather_selector(
    form_key_suffix: str,
    parameters: List[str],
    show_date_range: bool = True,
    default_lat: float = 51.4,
    default_lon: float = 6.97,
    default_start: Optional[date] = None,
    default_end: Optional[date] = None
) -> Optional[Dict]:
    """
    Shared UI component for DWD station and weather data selection.
    
    Provides a consistent interface across all pages for selecting weather data
    location and date range. Supports both DWD station selection (with search)
    and direct coordinate input.
    
    Args:
        form_key_suffix: Unique suffix for form keys to avoid conflicts
        parameters: List of weather parameters needed
            Options: 'solar', 'wind', 'temperature', 'pressure'
        show_date_range: Whether to show date range selection
        default_lat: Default latitude for coordinate input
        default_lon: Default longitude for coordinate input
        default_start: Default start date (None = 7 days ago)
        default_end: Default end date (None = today)
    
    Returns:
        Dict with location and weather parameters, or None if incomplete:
        {
            'method': 'station' or 'coordinates',
            'station_id': str (if station method),
            'latitude': float,
            'longitude': float,
            'start_date': datetime (if show_date_range),
            'end_date': datetime (if show_date_range),
            'parameters': List[str],
            'station_metadata': Dict (if station method)
        }
    
    Usage Example:
        ```python
        from src.ui.components.location_weather import location_weather_selector
        
        # In a Streamlit page
        location_data = location_weather_selector(
            form_key_suffix="pv_config",
            parameters=['solar', 'temperature', 'wind'],
            show_date_range=True,
            default_lat=51.4,
            default_lon=6.97
        )
        
        if location_data:
            # User has completed selection
            lat = location_data['latitude']
            lon = location_data['longitude']
            start = location_data['start_date']
            end = location_data['end_date']
            
            # Fetch weather data
            weather_data, metadata = fetch_weather_for_pv(
                latitude=lat, longitude=lon,
                start_date=start, end_date=end
            )
        ```
    """
    st.markdown("### 📍 Standort wählen")
    
    # Location method selection
    location_method = st.radio(
        "Methode:",
        ["DWD-Station auswählen", "Koordinaten eingeben"],
        key=f"location_method_{form_key_suffix}",
        help="Wählen Sie eine DWD-Wetterstation oder geben Sie Koordinaten direkt ein"
    )
    
    result = {
        "parameters": parameters
    }
    
    # =========================================================================
    # Option 1: DWD Station Selection
    # =========================================================================
    if location_method == "DWD-Station auswählen":
        st.markdown("#### 🔍 Stationssuche")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            address = st.text_input(
                "Suche nach Standort oder Adresse:",
                value="Köln",
                key=f"address_{form_key_suffix}",
                help="Geben Sie eine Stadt, Adresse oder einen Ortsnamen ein"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacing
            search_button = st.button(
                "🔍 Suchen",
                key=f"search_{form_key_suffix}",
                use_container_width=True
            )
        
        # Perform station search
        if search_button and address:
            with st.spinner(f"Suche nach Stationen in der Nähe von {address}..."):
                try:
                    # Geocode address
                    geolocator = Nominatim(user_agent="vise-d-dashboard")
                    location = geolocator.geocode(address, timeout=10)
                    
                    if not location:
                        st.error(f"❌ Standort '{address}' konnte nicht gefunden werden.")
                        st.info("💡 Versuchen Sie es mit einer anderen Schreibweise oder einer bekannteren Stadt.")
                        return None
                    
                    lat, lon = location.latitude, location.longitude
                    st.success(f"✅ Standort gefunden: {location.address}")
                    st.info(f"📍 Koordinaten: {lat:.4f}°N, {lon:.4f}°E")
                    
                    # Find nearest DWD stations via vpplib DWDClient
                    cache_dir = DATA_DIR / ".." / DWD.CACHE_DIR
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    _client = DWDClient(
                        cache_dir=str(cache_dir),
                        cache_expiry_hours=DWD.CACHE_EXPIRY_HOURS,
                        timezone=DWD.TIMEZONE,
                    )
                    stations = {}
                    for _param in parameters:
                        _objs = _client.station_manager.find_nearest_stations(
                            latitude=lat,
                            longitude=lon,
                            parameter=_param,
                            n=5,
                            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
                            resolution='hourly',
                            active_only=False,
                        )
                        stations[_param] = [
                            {
                                'station_id': s.station_id,
                                'name': s.name,
                                'latitude': s.latitude,
                                'longitude': s.longitude,
                                'elevation': s.elevation,
                                'distance_km': round(s.distance_km, 2),
                                'is_active': s.end_date.isoformat() if s.end_date else None,
                                'quality_score': s.quality_score,
                            }
                            for s in _objs
                        ]
                    
                    # Store in session state
                    st.session_state[f"stations_{form_key_suffix}"] = stations
                    st.session_state[f"search_lat_{form_key_suffix}"] = lat
                    st.session_state[f"search_lon_{form_key_suffix}"] = lon
                    st.session_state[f"search_address_{form_key_suffix}"] = location.address
                    
                except (GeocoderTimedOut, GeocoderServiceError) as e:
                    st.error(f"🌐 Geocoding-Dienst nicht verfügbar: {e}")
                    st.info("💡 Bitte versuchen Sie es später erneut oder verwenden Sie die Koordinateneingabe.")
                    return None
                except Exception as e:
                    st.error(f"❌ Fehler bei der Stationssuche: {e}")
                    return None
        
        # Display station selection if search was performed
        if f"stations_{form_key_suffix}" in st.session_state:
            stations = st.session_state[f"stations_{form_key_suffix}"]
            search_lat = st.session_state[f"search_lat_{form_key_suffix}"]
            search_lon = st.session_state[f"search_lon_{form_key_suffix}"]
            search_address = st.session_state.get(f"search_address_{form_key_suffix}", "")
            
            st.markdown("#### 📊 Gefundene DWD-Stationen")
            
            # Combine stations from all parameters into a single list
            station_map = {}
            for param, station_list in stations.items():
                for station in station_list:
                    station_id = station['station_id']
                    if station_id not in station_map:
                        station_map[station_id] = station
                        # Add parameter info
                        station_map[station_id]['available_params'] = [param]
                    else:
                        station_map[station_id]['available_params'].append(param)
            
            # Create dropdown options
            station_options = []
            for station_id, station in station_map.items():
                params_str = ", ".join(station['available_params'])
                option = (
                    f"ID: {station_id} - {station['name']} "
                    f"({station['distance_km']:.1f} km) | {params_str}"
                )
                station_options.append(option)
            
            if not station_options:
                st.warning("⚠️ Keine passenden Stationen in der Nähe gefunden.")
                st.info(f"💡 Versuchen Sie einen anderen Standort oder verwenden Sie die Koordinateneingabe.")
                return None
            
            selected = st.selectbox(
                "Wählen Sie eine Station:",
                station_options,
                key=f"station_select_{form_key_suffix}",
                help="Stationen sind nach Qualität und Entfernung sortiert"
            )
            
            if selected:
                # Extract station ID from selection
                station_id = selected.split(" - ")[0].replace("ID: ", "")
                station = station_map[station_id]
                
                # Display station details
                st.markdown("##### 📋 Stationsdetails")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Entfernung", f"{station['distance_km']:.1f} km")
                with col2:
                    st.metric("Höhe", f"{station['elevation']:.0f} m")
                with col3:
                    if 'quality_score' in station:
                        quality_pct = station['quality_score'] * 100
                        st.metric("Datenqualität", f"{quality_pct:.0f}%")
                
                # Additional info
                with st.expander("ℹ️ Weitere Informationen"):
                    st.write(f"**Station-ID:** {station_id}")
                    st.write(f"**Name:** {station['name']}")
                    st.write(f"**Koordinaten:** {station['latitude']:.4f}°N, {station['longitude']:.4f}°E")
                    st.write(f"**Verfügbare Parameter:** {', '.join(station['available_params'])}")
                    if 'quality_score' in station:
                        st.write(f"**Datenqualität:** {station['quality_score']:.2f}")
                
                # Populate result dict
                result["method"] = "station"
                result["station_id"] = station_id
                result["latitude"] = station['latitude']
                result["longitude"] = station['longitude']
                result["station_metadata"] = station
        else:
            st.info("👆 Geben Sie einen Standort ein und klicken Sie auf 'Suchen', um DWD-Stationen zu finden.")
            return None
    
    # =========================================================================
    # Option 2: Manual Coordinate Input
    # =========================================================================
    else:
        # Clear station search data when switching to coordinate input
        # This prevents Arrow serialization warnings from leftover session state
        if f"stations_{form_key_suffix}" in st.session_state:
            del st.session_state[f"stations_{form_key_suffix}"]
        if f"search_lat_{form_key_suffix}" in st.session_state:
            del st.session_state[f"search_lat_{form_key_suffix}"]
        if f"search_lon_{form_key_suffix}" in st.session_state:
            del st.session_state[f"search_lon_{form_key_suffix}"]
        if f"search_address_{form_key_suffix}" in st.session_state:
            del st.session_state[f"search_address_{form_key_suffix}"]
        
        st.markdown("#### 🗺️ Koordinateneingabe")
        col1, col2 = st.columns(2)
        
        with col1:
            lat = st.number_input(
                "Breitengrad:",
                min_value=-90.0,
                max_value=90.0,
                value=float(default_lat),  # Ensure float type
                format="%.6f",
                key=f"lat_{form_key_suffix}",
                help="Breitengrad in Dezimalgrad (-90 bis 90)"
            )
        
        with col2:
            lon = st.number_input(
                "Längengrad:",
                min_value=-180.0,
                max_value=180.0,
                value=float(default_lon),  # Ensure float type
                format="%.6f",
                key=f"lon_{form_key_suffix}",
                help="Längengrad in Dezimalgrad (-180 bis 180)"
            )
        
        # Ensure returned values are standard Python floats
        result["method"] = "coordinates"
        result["latitude"] = float(lat)
        result["longitude"] = float(lon)
    
    # =========================================================================
    # Date Range Selection (Optional)
    # =========================================================================
    if show_date_range:
        st.markdown("### 📅 Zeitraum wählen")
        
        # Calculate defaults (past 7 days if not provided)
        # Ensure all date objects are standard Python date type for Arrow compatibility
        today = date.today()
        if default_start is None:
            default_start = today - timedelta(days=8)
        if default_end is None:
            default_end = today - timedelta(days=1)
        
        # Ensure defaults are date objects, not datetime
        if isinstance(default_start, datetime):
            default_start = default_start.date()
        if isinstance(default_end, datetime):
            default_end = default_end.date()
        
        col1, col2 = st.columns(2)
        
        with col1:
            start = st.date_input(
                "Von:",
                value=default_start,
                key=f"start_date_{form_key_suffix}",
                help="Startdatum für Wetterdaten"
            )
        
        with col2:
            # Auto-adjust end date if start date is after current end date
            # Ensure start is a date object
            if isinstance(start, datetime):
                start = start.date()
            
            end_value = default_end
            if start > default_end:
                end_value = start + timedelta(days=1)
            
            end = st.date_input(
                "Bis:",
                value=end_value,
                key=f"end_date_{form_key_suffix}",
                help="Enddatum für Wetterdaten"
            )
        
        # Validate and auto-adjust date range
        # Ensure both start and end are date objects
        if isinstance(start, datetime):
            start = start.date()
        if isinstance(end, datetime):
            end = end.date()
        
        if start > end:
            st.warning("⚠️ Startdatum liegt nach Enddatum. Enddatum wird automatisch angepasst.")
            end = start + timedelta(days=1)
            result["start_date"] = datetime.combine(start, datetime.min.time())
            result["end_date"] = datetime.combine(end, datetime.max.time())
        else:
            result["start_date"] = datetime.combine(start, datetime.min.time())
            result["end_date"] = datetime.combine(end, datetime.max.time())
    
    # =========================================================================
    # Summary Display
    # =========================================================================
    if "latitude" in result:
        st.markdown("---")
        st.markdown("### ✅ Auswahl-Zusammenfassung")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Methode:** {result['method']}")
            st.write(f"**Koordinaten:** {result['latitude']:.4f}°N, {result['longitude']:.4f}°E")
            if result['method'] == 'station':
                st.write(f"**Station:** {result['station_id']}")
        
        with col2:
            st.write(f"**Parameter:** {', '.join(parameters)}")
            if show_date_range and "start_date" in result:
                st.write(f"**Zeitraum:** {result['start_date'].date()} bis {result['end_date'].date()}")
        
        return result
    
    return None


def station_override_selector(
    form_key_suffix: str,
    default_lat: float,
    default_lon: float,
    parameters: List[str]
) -> Optional[Dict]:
    """
    Compact station selector for MaStR pages with automatic city centroid.
    
    Provides an optional station override in an expander, maintaining the
    default behavior of using city centroid coordinates.
    
    Args:
        form_key_suffix: Unique suffix for form keys
        default_lat: Default latitude (city centroid)
        default_lon: Default longitude (city centroid)
        parameters: Weather parameters needed
    
    Returns:
        Dict with override location info, or None to use default
    
    Usage Example:
        ```python
        # In energy_generation_solar.py or wind_energy_generation.py
        with st.expander("🔧 Erweitert: Wetterstation überschreiben"):
            override = station_override_selector(
                form_key_suffix="solar_mastr",
                default_lat=city_district.lat,
                default_lon=city_district.lon,
                parameters=['solar', 'temperature']
            )
        
        if override:
            # Use custom station
            lat, lon = override['latitude'], override['longitude']
        else:
            # Use city centroid (default)
            lat, lon = city_district.lat, city_district.lon
        ```
    """
    st.info(f"ℹ️ Standard: Verwende Stadtzentrum-Koordinaten ({default_lat:.4f}°N, {default_lon:.4f}°E)")
    
    use_custom = st.checkbox(
        "Eigene Wetterstation auswählen",
        key=f"use_custom_{form_key_suffix}",
        help="Aktivieren, um eine spezifische DWD-Station auszuwählen"
    )
    
    if not use_custom:
        return None
    
    # Show compact location selector
    return location_weather_selector(
        form_key_suffix=form_key_suffix,
        parameters=parameters,
        show_date_range=False,
        default_lat=default_lat,
        default_lon=default_lon
    )
