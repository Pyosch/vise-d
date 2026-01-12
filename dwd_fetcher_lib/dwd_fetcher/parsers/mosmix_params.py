"""
MOSMIX parameter definition extractor.
Fetches and parses MetElementDefinition.xml from DWD to get parameter codes, units, and descriptions.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Optional, Any
from pathlib import Path
import requests

from ..config import DWDConfig
from ..cache import CacheManager


class MOSMIXParameterManager:
    """Manages MOSMIX parameter definitions from DWD MetElementDefinition.xml."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        Initialize MOSMIX parameter manager.
        
        Args:
            cache_manager: Cache manager instance (creates new if None)
        """
        self.cache_manager = cache_manager or CacheManager()
        self.parameters: Dict[str, Dict[str, str]] = {}
        self._loaded = False
    
    def load_parameters(self, force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
        """
        Load MOSMIX parameter definitions from DWD.
        
        Args:
            force_refresh: Force download even if cached
            
        Returns:
            Dictionary mapping parameter codes to their definitions
        """
        if self._loaded and not force_refresh:
            return self.parameters
        
        # Try to get from cache or fetch
        xml_content = self.cache_manager.get_or_fetch(
            url=DWDConfig.MET_ELEMENT_DEF_URL,
            fetch_func=lambda: self._fetch_xml(),
            expiry_hours=24 * 7,  # Cache for 7 days
            extension=".xml",
            binary=False,
            force_refresh=force_refresh
        )
        
        # Parse XML
        self.parameters = self._parse_xml(xml_content)
        self._loaded = True
        
        return self.parameters
    
    def _fetch_xml(self) -> str:
        """Fetch MetElementDefinition.xml from DWD."""
        try:
            response = requests.get(DWDConfig.MET_ELEMENT_DEF_URL, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch MOSMIX parameter definitions: {e}")
    
    def _parse_xml(self, xml_content: str) -> Dict[str, Dict[str, str]]:
        """
        Parse MetElementDefinition.xml content.
        
        Args:
            xml_content: XML string content
            
        Returns:
            Dictionary of parameter definitions
        """
        parameters = {}
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find all MetElement entries
            # The structure might vary, so we'll look for common patterns
            for element in root.findall(".//{*}MetElement"):
                param_data = {}
                
                # Extract ShortName (parameter code)
                short_name_elem = element.find("{*}ShortName")
                if short_name_elem is None or not short_name_elem.text:
                    continue
                
                param_code = short_name_elem.text.strip()
                
                # Extract description
                desc_elem = element.find("{*}Description")
                if desc_elem is not None and desc_elem.text:
                    param_data['description'] = desc_elem.text.strip()
                
                # Extract unit
                unit_elem = element.find("{*}UnitOfMeasurement")
                if unit_elem is not None and unit_elem.text:
                    param_data['unit'] = unit_elem.text.strip()
                
                # Extract any other useful fields
                for child in element:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if tag not in ['ShortName', 'Description', 'UnitOfMeasurement'] and child.text:
                        param_data[tag.lower()] = child.text.strip()
                
                parameters[param_code] = param_data
            
        except ET.ParseError as e:
            raise RuntimeError(f"Failed to parse MOSMIX parameter XML: {e}")
        
        return parameters
    
    def get_parameter(self, code: str) -> Optional[Dict[str, str]]:
        """
        Get parameter definition by code.
        
        Args:
            code: Parameter code (e.g., 'TTT', 'FF')
            
        Returns:
            Parameter definition or None if not found
        """
        if not self._loaded:
            self.load_parameters()
        
        return self.parameters.get(code)
    
    def get_all_parameters(self) -> Dict[str, Dict[str, str]]:
        """
        Get all parameter definitions.
        
        Returns:
            Dictionary of all parameters
        """
        if not self._loaded:
            self.load_parameters()
        
        return self.parameters.copy()
    
    def search_parameters(self, search_term: str, 
                         search_in: str = "description") -> Dict[str, Dict[str, str]]:
        """
        Search for parameters by keyword.
        
        Args:
            search_term: Term to search for
            search_in: Field to search in ('description', 'unit', 'code')
            
        Returns:
            Dictionary of matching parameters
        """
        if not self._loaded:
            self.load_parameters()
        
        search_term = search_term.lower()
        results = {}
        
        for code, param in self.parameters.items():
            if search_in == "code":
                if search_term in code.lower():
                    results[code] = param
            elif search_in in param:
                if search_term in param[search_in].lower():
                    results[code] = param
        
        return results
    
    def get_unit(self, code: str) -> Optional[str]:
        """
        Get unit for a parameter code.
        
        Args:
            code: Parameter code
            
        Returns:
            Unit string or None
        """
        param = self.get_parameter(code)
        return param.get('unit') if param else None
    
    def get_description(self, code: str) -> Optional[str]:
        """
        Get description for a parameter code.
        
        Args:
            code: Parameter code
            
        Returns:
            Description string or None
        """
        param = self.get_parameter(code)
        return param.get('description') if param else None
    
    def update_from_dwd(self) -> Dict[str, Dict[str, str]]:
        """
        Force update parameter definitions from DWD.
        
        Returns:
            Updated parameter dictionary
        """
        return self.load_parameters(force_refresh=True)
    
    def get_relevant_parameters(self) -> Dict[str, str]:
        """
        Get parameters relevant for solar and wind energy modeling.
        
        Returns:
            Dictionary mapping friendly names to parameter codes
        """
        if not self._loaded:
            self.load_parameters()
        
        relevant = {
            'temperature': 'TTT',
            'temperature_max': 'TX',
            'temperature_min': 'TN',
            'dewpoint': 'Td',
            'wind_speed': 'FF',
            'wind_direction': 'DD',
            'wind_gust': 'FX1',
            'pressure_msl': 'PPPP',
            'pressure_station': 'P0',
            'radiation_global': 'Rad1h',
            'radiation_direct': 'RadS3',
            'radiation_diffuse': 'RadL3',
            'cloud_cover': 'N',
            'precipitation': 'RR1c',
            'humidity': 'Td',  # Can be calculated from Td and TTT
        }
        
        # Verify these parameters exist in the loaded definitions
        verified = {}
        for name, code in relevant.items():
            if code in self.parameters:
                verified[name] = code
        
        return verified
    
    def export_to_json(self, filepath: str):
        """
        Export parameter definitions to JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        import json
        
        if not self._loaded:
            self.load_parameters()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.parameters, f, indent=2, ensure_ascii=False)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache information for parameter definitions.
        
        Returns:
            Dictionary with cache status
        """
        cache_key = self.cache_manager._get_cache_key(DWDConfig.MET_ELEMENT_DEF_URL)
        is_cached = cache_key in self.cache_manager.metadata
        is_valid = self.cache_manager.is_valid(cache_key, expiry_hours=24 * 7)
        
        info = {
            'is_cached': is_cached,
            'is_valid': is_valid,
            'parameter_count': len(self.parameters) if self._loaded else 0,
            'loaded': self._loaded
        }
        
        if is_cached:
            metadata = self.cache_manager.metadata[cache_key]
            import time
            cache_age_hours = (time.time() - metadata['timestamp']) / 3600
            info['cache_age_hours'] = round(cache_age_hours, 2)
        
        return info
