"""Wind farm planning and simulation tools.

This module provides functions for planning wind energy installations
using OpenStreetMap obstacle data, ERA5 weather data, site packing algorithms,
and windpowerlib simulation.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import folium
from shapely.geometry import Point, Polygon, box
from shapely.affinity import scale, rotate, translate
from shapely.ops import transform as shapely_transform
from shapely.ops import unary_union
import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
import osmnx as ox
import geopandas as gpd
import random
import os
from windpowerlib import WindTurbine, ModelChain
import math
import plotly.graph_objects as go
from datetime import datetime
from shapely.geometry import LineString,Polygon
from shapely.ops import nearest_points


# Function to get local CRS based on latitude and longitude
def get_local_crs(lon, lat):
    return CRS.from_proj4(
        f"+proj=tmerc +lat_0={lat} +lon_0={lon} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    )

def simulate_wind_power(lat, lon, turbine_type, num_turbines=1):
    """
    Simulate wind power generation for given location and turbine type
    """
    # Example turbine types (you can add more from the windpowerlib database)
    turbine_types = {
        'E-126/4200': {
            'hub_height': 135,
            'rotor_diameter': 127,
            'nominal_power': 4200000  # in W
        },
        'V150/4200': {
            'hub_height': 105,
            'rotor_diameter': 150,
            'nominal_power': 4200000
        }
    }

    # Get turbine specifications
    turbine_data = turbine_types[turbine_type]
    
    # Create wind turbine object
    turbine = WindTurbine(
        hub_height=turbine_data['hub_height'],
        rotor_diameter=turbine_data['rotor_diameter'],
        nominal_power=turbine_data['nominal_power'],
        turbine_type=turbine_type
    )

    # Create weather data (example - replace with actual weather data source)
    weather_data = pd.DataFrame(
        index=pd.date_range(start='2024-01-01', end='2024-12-31', freq='H'),
        data={
            'wind_speed': np.random.weibull(2, 8760) * 8,  # Example wind speeds
            'temperature': np.random.normal(15, 5, 8760),
            'roughness_length': np.full(8760, 0.1),
            'pressure': np.full(8760, 101325),
        }
    )

    # Set up model chain for power calculation
    modelchain = ModelChain(turbine).run_model(weather_data)
    
    # Calculate power output
    power_output = modelchain.power_output
    
    # Calculate statistics
    annual_energy = power_output.sum() / 1e6  # Convert to MWh
    full_load_hours = annual_energy / (turbine_data['nominal_power'] / 1e6)
    
    # Monthly averages for visualization
    monthly_power = power_output.groupby(power_output.index.month).mean() / 1e6  # Convert to MW
    
    return {
        'annual_energy': annual_energy * num_turbines,
        'full_load_hours': full_load_hours,
        'monthly_power': monthly_power.tolist(),
        'num_turbines': num_turbines
    }

def create_power_timeline_plot(monthly_power):
    """
    Create a plotly figure showing power production over time
    """
    months = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=monthly_power,
        mode='lines+markers',
        name='Wind Power Production'
    ))
    
    fig.update_layout(
        title='Stromproduktion der Windturbinen im Jahresverlauf (MW)',
        xaxis_title='Month',
        yaxis_title='Power (MW)',
        showlegend=False
    )
    
    return fig

def calculate_wind_potential(coords, turbine_type='E-126/4200'):
    """
    Calculate wind potential for a given area
    """
    # Get center coordinates
    center_lat = np.mean([coord[1] for coord in coords])
    center_lon = np.mean([coord[0] for coord in coords])
    
    # Calculate area size (approximate)
    transformer = Transformer.from_crs("EPSG:4326", get_local_crs(center_lon, center_lat))
    coords_local = [transformer.transform(lon, lat) for lon, lat in coords]
    polygon = Polygon(coords_local)
    area = polygon.area
    
    # Estimate number of possible turbines based on area
    # Assuming minimum spacing of 5 rotor diameters
    turbine_spacing = 5 * 127  # for E-126/4200
    num_turbines = int(area / (turbine_spacing ** 2))
    
    # Simulate power generation
    results = simulate_wind_power(center_lat, center_lon, turbine_type, num_turbines)
    
    # Create visualization
    timeline_fig = create_power_timeline_plot(results['monthly_power'])
    
    return {
        'kreiszentrum': f"[{center_lat:.6f}, {center_lon:.6f}]",
        'radius': f"{math.sqrt(area/math.pi):.2f} meter",
        'num_turbines': results['num_turbines'],
        'annual_energy': f"{results['annual_energy']:.2f} GWh",
        'full_load_hours': f"{results['full_load_hours']:.2f} h",
        'timeline_fig': timeline_fig
    }

# Function to fetch obstacles for Wind Farm (Polygon mode only)
def fetch_obstacles_wind(output, center, status_box, min_spacing_x, min_spacing_y):
    status_box.info("🔍 Hindernisse aus OSM abrufen...")
    
    # Create polygon from center coordinates
    polygon_shape = Polygon(center)
    
    # Get bounding box from polygon
    bounds = polygon_shape.bounds
    west, south, east, north = bounds
    
    # Add small padding
    padding = 0.001
    west -= padding
    south -= padding
    east += padding
    north += padding

    # Alle erforderliche Schlüssel (Tags)
    tags = {
        "highway": True,    "railway": True,    "aeroway": True,    "man_made": True,
        "landuse": True,    "building": True,   "amenity": True,    "healthcare": True,
        "tourism": True,    "power": True,      "military": True,   "protect_class": True,
        "leaf_type": True,  "waterway": True,   "natural": True,     "tower:type": True,
        "usage": True,      "generator:source": True,   "monitoring:seismic_activity": True,
        "boundary": True
    }

    # Fetch features from OSM using osmnx and return empty GeoDataFrame if no features found
    try:
        features = ox.features_from_bbox((west, south, east, north), tags=tags)
    except ox._errors.InsufficientResponseError:
        return gpd.GeoDataFrame({'buffered_geometry': []}, geometry='buffered_geometry', crs="EPSG:4326")

    status_box.info("⚙️ Hindernisse verarbeiten...")
    # Ensure all relevant columns exist
    for col in ["highway",      "railway",  "aeroway",      "man_made",     "landuse", 
                "building",     "amenity",  "healthcare",   "tourism",      "protect_class",
                "military",     "power",    "leaf_type",    "tower:type",   "natural",
                "waterway",     "usage",    "generator:source", "monitoring:seismic_activity",
                "boundary"]:
        if col not in features.columns:
            features[col] = np.nan
    
    # Calculate polygon centroid for center coordinates
    centroid = polygon_shape.centroid
    lon_center = centroid.x
    lat_center = centroid.y
    
    crs_local = get_local_crs(lon_center, lat_center)

    obstacle_geoms = []
    
    # Define landuse features
    landuse = features[
        ((features["landuse"].isin(["residential", "recreation_ground", "allotments", "commercial", "industrial", "landfill"])) | 
         (features["amenity"].notna()) | 
         (features["healthcare"].notna()) | 
         (features["tourism"].isin(["apartment", "guest_house", "camp_site", "wilderness_hut", "caravan_site"])) | 
         (features["building"].notna())) & 
        (features.geometry.type == "Polygon")
    ].copy()

    # Process landuse if any
    if not landuse.empty:
        landuse = landuse.to_crs(crs_local)
        # Define buffer distances for landuse
        def landuse_buffer(row):
            if row.get("landuse") == "residential": #2
                return 700
            elif pd.notna(row.get("building")): #1   
                return 700
            elif row.get("landuse") == "recreation_ground": #5'
                return 500
            elif row.get("landuse") == "allotments": #7
                return 500
            elif row.get("tourism") in ["apartment", "guest_house", "camp_site", "wilderness_hut", "caravan_site"]: #7
                return 500
            elif row.get("landuse") == "commercial": #4
                return 0
            elif row.get("landuse") == "industrial": #3
                return 0
            elif row.get("landuse") == "landfill":
                return 0
            elif pd.notna(row.get("amenity")): #6
                return 0
            elif pd.notna(row.get("healthcare")): #6
                return 0
            return 0  # fallback
        
        # Apply buffer to landuse
        landuse["buffer_distance"] = landuse.apply(landuse_buffer, axis=1)
        landuse["buffered_geometry"] = landuse.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        # Append to GeoDataFrame
        gdf = gpd.GeoDataFrame(landuse[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Landnutzung" #landuse
        obstacle_geoms.append(gdf)

    # Define traffic features
    traffic = features[
    (
        (features["highway"].notna()) |
        (features["railway"].notna()) |
        (features["aeroway"].isin(["Navigation aid", "aerodrome", "airstrip"])) |
        (features["man_made"] == "communications_tower") |
        ((features["man_made"] == "tower") & (features["tower:type"] == "radar"))
        ) &
        (features.geometry.type.isin(["LineString", "Polygon", "MultiPolygon", "Point"]))
    ].copy()

    # Process traffic if any
    if not traffic.empty:
        traffic = traffic.to_crs(crs_local)

        # Define buffer distances for traffic
        def traffic_buffer(row):
            if row.get("aeroway") == "navigationaid": #15
                return 7000  
            elif row.get("man_made") == "communications_tower": #15
                return 7000  
            elif row.get("man_made") == "tower" and row.get("tower:type") == "radar": #15
                return 7000  #15
            elif row.get("aeroway") == "aerodrome": #13,14
                return 4000
            elif row.get("aeroway") == "airstrip":  #13,14
                return 1500
            elif row.get("railway") == "rail":
                if row.get("electrified") in ["contact_line", "rail", "4th_rail", "yes"]:
                    return 175 #12
                elif row.get("electrified") == "no":
                    return 95 #11
            elif row.get("highway") == "motorway": #8
                return 115
            elif row.get("highway") == "primary": #9
                return 95
            elif pd.notna(row.get("highway")): #10
                return 5
            return 0

        # Apply buffer to traffic
        traffic["buffer_distance"] = traffic.apply(traffic_buffer, axis=1)
        traffic["buffered_geometry"] = traffic.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        # Append to GeoDataFrame
        gdf = gpd.GeoDataFrame(traffic[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Verkehr" #traffic
        obstacle_geoms.append(gdf)
    
    # Define infrastructure features
    infrastructure = features[
    (
        (features["landuse"] == "quarry") |
        ((features["man_made"] == "tower") & (features["tower:type"] == "radar")) |
        (features["power"].notna()) & (features["power"] != "cable")  
        ) &
        (features.geometry.type.isin(["LineString", "Polygon", "MultiPolygon", "Point"]))
    ].copy()

    turbines = features[
        (
            ((features["power"] == "generator") & (features["generator:source"] == "wind")) |
            (features["man_made"] == "wind_turbine")
        ) &
        (features.geometry.type.isin(["Point", "LineString", "Polygon", "MultiPolygon"]))
    ].copy()
    
    geoms = []

    # Process infrastructure if any
    if not infrastructure.empty:
        infrastructure = infrastructure.to_crs(crs_local)

        # Define buffer distances for infrastructure
        def infrastructure_buffer(row):
            if row.get("landuse") == "quarry": #17
                return 0  
            elif row.get("power") in ["line", "minor_line"]: #18
                return 175 
            elif pd.notna(row.get("power")):
                return 5
            elif row.get("man_made") == "tower" and row.get("tower:type") == "radar": #20,23
                return 5000
            elif row.get("man_made") == "monitoring_station" and row.get("monitoring:seismic_activity") == "yes": #19
                return 5000
            return 0

        # Apply buffer to infrastructure
        infrastructure["buffer_distance"] = infrastructure.apply(infrastructure_buffer, axis=1)
        infrastructure["buffered_geometry"] = infrastructure.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )
        geoms.append(infrastructure[["buffered_geometry"]])

    # extra code to add wind-turbine ellipses
    if not turbines.empty:
        turbines = turbines.to_crs(crs_local)

        def turbine_ellipse(row):
            a =  min_spacing_y  # semi-major axis
            b =  min_spacing_x  # semi-minor axis
            centre = (row.geometry.centroid
                      if row.geometry.geom_type != "Point"
                      else row.geometry)
            ell = Point(centre).buffer(1)                  # unit circle
            return scale(ell, xfact=a, yfact=b)            # stretch

        turbines["buffered_geometry"] = turbines.apply(turbine_ellipse, axis=1)
        geoms.append(turbines[["buffered_geometry"]])

    # Append to GeoDataFrame
    if geoms:
        infra_combined = pd.concat(geoms, ignore_index=True)
        gdf = gpd.GeoDataFrame(infra_combined, geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf["obstacle_type"] = "Infrastruktur"
        obstacle_geoms.append(gdf)

    # Define military features
    military = features[
    (
        (features["military"].isin(["training_area", "airfield"]))
        ) &
        (features.geometry.type.isin(["LineString", "Polygon", "MultiPolygon", "Point"]))
    ].copy()
    
    # Process military if any
    if not military.empty:
        military = military.to_crs(crs_local)

        # Define buffer distances for military
        def military_buffer(row):
            if row.get("military") == "training_area": #21
                return 75  
            elif row.get("military") == "airfield": #22
                return 0  
            return 0

        # Apply buffer to military
        military["buffer_distance"] = military.apply(military_buffer, axis=1)
        military["buffered_geometry"] = military.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        # Append to GeoDataFrame
        gdf = gpd.GeoDataFrame(military[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Militärische Belange" #military
        obstacle_geoms.append(gdf)
    
    # Define boundary features
    boundary = features[(features["protect_class"] == "97")].copy()

    # Process boundary if any
    if not boundary.empty:
        boundary = boundary.to_crs(crs_local)

        # Define buffer distances for boundary
        def boundary_buffer(row):
            if row.get("protect_class") == "97": #25,28
                return 75 
            return 0
        
        # Apply buffer to boundary
        boundary["buffer_distance"] = boundary.apply(boundary_buffer, axis=1)
        boundary["buffered_geometry"] = boundary.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        # Append to GeoDataFrame
        gdf = gpd.GeoDataFrame(boundary[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Artenschutz" #boundary
        obstacle_geoms.append(gdf)

    # Define nature features
    nature = features[
    (
        features["protect_class"].isin(["1", "2", "3", "4", "5", "6", "7"]) |
        (features["boundary"] == "protected_area")
    )].copy()

    # Process nature if any
    if not nature.empty:
        nature = nature.to_crs(crs_local)

        # Define buffer distances for nature
        def nature_buffer(row):
            if row.get("protect_class") in ["2", "97"]: #27, 28, 30
                return 75
            elif row.get("boundary") == "protected_area": #27, 30
                return 75
            elif row.get("protect_class") == "4": #29
                return 0
            return 0
        
        # Apply buffer to nature
        nature["buffer_distance"] = nature.apply(nature_buffer, axis=1)
        nature["buffered_geometry"] = nature.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        # Append to GeoDataFrame
        gdf = gpd.GeoDataFrame(nature[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Natur und Landschaft" #nature
        obstacle_geoms.append(gdf)
    
    # Define forest features
    forest = features[
    (
        ((features["landuse"] == "forest") & (features["leaf_type"].isin(["broadleaved", "mixed"]))) |
        (features["landuse"] == "cemetery") |
        (features["protect_class"] == "1")
    ) &
        (features.geometry.type.isin(["Polygon", "MultiPolygon"]))
    ].copy()

    # Process forest if any
    if not forest.empty:
        forest = forest.to_crs(crs_local)

        # Define buffer distances for forest
        def forest_buffer(row):
            if row.get("landuse") == "forest" and row.get("leaf_type") in ["broadleaved", "mixed"]: #32
                return 0 
            elif row.get("landuse") == "cemetery": #33
                return 0
            elif row.get("protect_class") == "1": #33
                return 0
            return 0
        
        # Apply buffer to forest
        forest["buffer_distance"] = forest.apply(forest_buffer, axis=1)
        forest["buffered_geometry"] = forest.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        # Append to GeoDataFrame
        gdf = gpd.GeoDataFrame(forest[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Wald" #forest
        obstacle_geoms.append(gdf)
    
    # Define water features
    water = features[
    (
        ((features["natural"] == "water") & (features.geometry.type.isin(["Polygon", "MultiPolygon"]))) |
        (features["waterway"].isin(["river", "canal"])) |
        (features["usage"] == "transportation") |
        (features["protect_class"] == "12")
    )
    ].copy()

    # Process water if any
    if not water.empty:
        water = water.to_crs(crs_local)

        # Calculate area if applicable (only for polygonal water bodies)
        if "area_m2" not in water.columns:
            water["area_m2"] = water.geometry.area

        # Apply buffer distances
        def water_buffer(row):
            if row.get("natural") == "water": #34
                return 50 if row.get("area_m2", 0) > 500000 else 0
            elif row.get("waterway") in ["river", "canal"] and row.get("usage") == "transportation": #35
                return 50 
            elif row.get("waterway") in ["river", "canal"]: #35
                return 0
            elif row.get("protect_class") == "12": #36
                return 0
            return 0

        water["buffer_distance"] = water.apply(water_buffer, axis=1)
        water["buffered_geometry"] = water.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        gdf = gpd.GeoDataFrame(water[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Gewässer"  #Water
        obstacle_geoms.append(gdf)
    
    # Define other features
    other = features[
        (
            (features["natural"].isin(["cliff", "ridge", "peak", "valley", "hill"]))
        )
    ].copy()

    if not other.empty:
        other = other.to_crs(crs_local)

        # Define buffer distances for other
        def other_buffer(row):
            if pd.notna(row.get("natural")):
                return 50
        
        # Apply buffer to other
        other["buffer_distance"] = other.apply(other_buffer, axis=1)
        other["buffered_geometry"] = other.apply(
            lambda row: row.geometry.buffer(row.buffer_distance), axis=1
        )

        gdf = gpd.GeoDataFrame(other[['buffered_geometry']], geometry="buffered_geometry")
        gdf.set_crs(crs_local, inplace=True)
        gdf['obstacle_type'] = "Sonstiges" #other
        obstacle_geoms.append(gdf)
                            
    # Combine all obstacles (or create empty if none)
    if obstacle_geoms:
        combined = pd.concat(obstacle_geoms, ignore_index=True)
        combined = gpd.GeoDataFrame(combined, geometry='buffered_geometry', crs=crs_local)
        
        # Convert polygon to local CRS for clipping
        transformer = Transformer.from_crs("EPSG:4326", crs_local, always_xy=True)
        polygon_coords_local = [transformer.transform(x, y) for x, y in polygon_shape.exterior.coords]
        polygon_local = Polygon(polygon_coords_local)
        
        # Clip obstacles to polygon boundary
        combined['buffered_geometry'] = combined['buffered_geometry'].apply(
            lambda geom: geom.intersection(polygon_local) if geom.intersects(polygon_local) else None
        )
        
        # Remove empty geometries
        combined = combined[combined['buffered_geometry'].notna()]
        combined = combined[~combined['buffered_geometry'].is_empty]
        
        # Convert back to WGS84
        combined = combined.to_crs("EPSG:4326")
    else:
        # Return empty GeoDataFrame with correct structure if nothing is found
        combined = gpd.GeoDataFrame({'buffered_geometry': []}, geometry='buffered_geometry', crs="EPSG:4326")
    
    return combined

# Function to perform Poisson Disk Sampling within a polygon boundary
def poisson_disk_sampling_polygon(polygon_shape, min_spacing_x, min_spacing_y, wind_direction_deg, obstacles_local_crs, k=30):
    """
    Poisson disk sampling adapted for polygon boundaries instead of circular boundaries.
    """
    # Get polygon bounds to set up grid
    bounds = polygon_shape.bounds
    min_x, min_y, max_x, max_y = bounds
    
    # Calculate polygon centroid for reference
    centroid = polygon_shape.centroid
    x_center, y_center = centroid.x, centroid.y
    
    cell_size = min(min_spacing_x, min_spacing_y) / np.sqrt(2)
    grid_width = int((max_x - min_x) / cell_size) + 1
    grid_height = int((max_y - min_y) / cell_size) + 1
    grid = [[None for _ in range(grid_height)] for _ in range(grid_width)]

    wind_rad = np.radians(wind_direction_deg)
    cos_wind = np.cos(wind_rad)
    sin_wind = np.sin(wind_rad)
        
    def point_fits(pt_xy):
        # Check grid for nearby points
        gx = int((pt_xy[0] - min_x) / cell_size)
        gy = int((pt_xy[1] - min_y) / cell_size)

        for i in range(max(gx - 2, 0), min(gx + 3, grid_width)):
            for j in range(max(gy - 2, 0), min(gy + 3, grid_height)):
                neighbor = grid[i][j]
                if neighbor:
                    dx = pt_xy[0] - neighbor[0]
                    dy = pt_xy[1] - neighbor[1]

                    # Apply wind direction rotation for elliptical spacing
                    dx_rot = dx * cos_wind + dy * sin_wind
                    dy_rot = -dx * sin_wind + dy * cos_wind

                    if (dx_rot / min_spacing_x) ** 2 + (dy_rot / min_spacing_y) ** 2 < 1:
                        return False

        # Check if point is within polygon boundary (instead of circle)
        if not polygon_shape.contains(Point(pt_xy)):
            return False

        # Check obstacles
        pt_geom = Point(pt_xy)
        for obstacle in obstacles_local_crs['buffered_geometry']:
            if obstacle.contains(pt_geom):
                return False

        return True

    def get_candidate_grid_polygon(polygon_shape, spacing):
        """Generate initial candidate grid within polygon bounds"""
        candidates = []
        bounds = polygon_shape.bounds
        min_x, min_y, max_x, max_y = bounds

        x = min_x
        while x <= max_x:
            y = min_y
            while y <= max_y:
                if polygon_shape.contains(Point(x, y)):
                    candidates.append((x, y))
                y += spacing
            x += spacing
        return candidates

    # Initial seeding - find first valid point
    candidates = get_candidate_grid_polygon(polygon_shape, spacing=cell_size)
    random.shuffle(candidates)
    
    first_point = None
    for candidate in candidates:
        if point_fits(candidate):
            first_point = candidate
            break
    
    if first_point is None:
        return []  # No valid starting point found

    process_list = [first_point]
    sample_points = [first_point]
    gx = int((first_point[0] - min_x) / cell_size)
    gy = int((first_point[1] - min_y) / cell_size)
    grid[gx][gy] = first_point

    rejection_count = 0
    while process_list:
        idx = random.randint(0, len(process_list) - 1)
        base = process_list[idx]
        found = False
        local_k = k + int(rejection_count / 5)  # Adaptive k

        for _ in range(local_k):
            r = random.uniform(min(min_spacing_x, min_spacing_y), 2.5 * max(min_spacing_x, min_spacing_y))
            angle = random.uniform(0, 2 * np.pi)
            new_x = base[0] + r * np.cos(angle)
            new_y = base[1] + r * np.sin(angle)
            candidate = (new_x, new_y)

            if point_fits(candidate):
                process_list.append(candidate)
                sample_points.append(candidate)
                gx = int((candidate[0] - min_x) / cell_size)
                gy = int((candidate[1] - min_y) / cell_size)
                if 0 <= gx < grid_width and 0 <= gy < grid_height:
                    grid[gx][gy] = candidate
                rejection_count = 0
                found = True
                break

        if not found:
            rejection_count += 1
            process_list.pop(idx)

    # Additional refinement passes similar to the original algorithm
    def systematic_post_pass():
        added = 0
        spacing = cell_size / 3
        x_offset = spacing / 2
        y_offset = spacing / 2

        x_range = np.arange(min_x + x_offset, max_x, spacing)
        y_range = np.arange(min_y + y_offset, max_y, spacing)

        for x in x_range:
            for y in y_range:
                cand = (x, y)
                if point_fits(cand):
                    sample_points.append(cand)
                    gx = int((x - min_x) / cell_size)
                    gy = int((y - min_y) / cell_size)
                    if 0 <= gx < grid_width and 0 <= gy < grid_height:
                        grid[gx][gy] = cand
                    added += 1
        return added

    # Apply refinement
    systematic_post_pass()

    return sample_points

# ============================================================================
# CIRCLE-BASED POISSON DISK SAMPLING - COMMENTED OUT (Not used - polygon only)
# ============================================================================
# Function to perform Poisson Disk Sampling with wind direction and obstacles
def poisson_disk_sampling(center_xy, radius, min_spacing_x, min_spacing_y, wind_direction_deg, obstacles_local_crs, k=30):
    x_center, y_center = center_xy
    cell_size = min(min_spacing_x, min_spacing_y) / np.sqrt(2)
    grid_width = int((2 * radius) / cell_size) + 1
    grid_height = int((2 * radius) / cell_size) + 1
    grid = [[None for _ in range(grid_height)] for _ in range(grid_width)]

    wind_rad = np.radians(wind_direction_deg)
    cos_wind = np.cos(wind_rad)
    sin_wind = np.sin(wind_rad)
        
    def point_fits(pt_xy):
        gx = int((pt_xy[0] - (x_center - radius)) / cell_size)
        gy = int((pt_xy[1] - (y_center - radius)) / cell_size)

        for i in range(max(gx - 2, 0), min(gx + 3, grid_width)):
            for j in range(max(gy - 2, 0), min(gy + 3, grid_height)):
                neighbor = grid[i][j]
                if neighbor:
                    dx = pt_xy[0] - neighbor[0]
                    dy = pt_xy[1] - neighbor[1]

                    dx_rot = dx * cos_wind + dy * sin_wind
                    dy_rot = -dx * sin_wind + dy * cos_wind

                    if (dx_rot / min_spacing_x) ** 2 + (dy_rot / min_spacing_y) ** 2 < 1:
                        return False

        if (pt_xy[0] - x_center) ** 2 + (pt_xy[1] - y_center) ** 2 > radius ** 2:
            return False

        pt_geom = Point(pt_xy)
        for obstacle in obstacles_local_crs['buffered_geometry']:
            if obstacle.contains(pt_geom):
                return False

        return True

    def get_candidate_grid(center_xy, radius, spacing):
        x_center, y_center = center_xy
        candidates = []
        x_start = x_center - radius
        y_start = y_center - radius
        x_end = x_center + radius
        y_end = y_center + radius

        x = x_start
        while x <= x_end:
            y = y_start
            while y <= y_end:
                if (x - x_center) ** 2 + (y - y_center) ** 2 <= radius ** 2:
                    candidates.append((x, y))
                y += spacing
            x += spacing
        return candidates

    # Initial seeding
    candidates = get_candidate_grid(center_xy, radius, spacing=cell_size)
    random.shuffle(candidates)
    for candidate in candidates:
        if point_fits(candidate):
            first_point = candidate
            break
    else:
        return []

    process_list = [first_point]
    sample_points = [first_point]
    gx = int((first_point[0] - (x_center - radius)) / cell_size)
    gy = int((first_point[1] - (y_center - radius)) / cell_size)
    grid[gx][gy] = first_point

    rejection_count = 0
    while process_list:
        idx = random.randint(0, len(process_list) - 1)
        base = process_list[idx]
        found = False
        local_k = k + int(rejection_count / 5)  # more aggressive adaptation

        for _ in range(local_k):
            r = random.uniform(min(min_spacing_x, min_spacing_y), 2.5 * max(min_spacing_x, min_spacing_y))
            angle = random.uniform(0, 2 * np.pi)
            new_x = base[0] + r * np.cos(angle)
            new_y = base[1] + r * np.sin(angle)
            candidate = (new_x, new_y)

            if point_fits(candidate):
                process_list.append(candidate)
                sample_points.append(candidate)
                gx = int((candidate[0] - (x_center - radius)) / cell_size)
                gy = int((candidate[1] - (y_center - radius)) / cell_size)
                grid[gx][gy] = candidate
                rejection_count = 0
                found = True
                break

        if not found:
            rejection_count += 1
            process_list.pop(idx)

    # Post-pass: adaptive grid refinement near borders
    def refined_border_pass():
        added = 0
        border_band = 0.15 * radius
        fine_spacing = cell_size / 1.5

        x_start = x_center - radius
        x_end = x_center + radius
        y_start = y_center - radius
        y_end = y_center + radius

        x = x_start
        while x <= x_end:
            y = y_start
            while y <= y_end:
                dist = math.hypot(x - x_center, y - y_center)
                if radius - border_band <= dist <= radius and point_fits((x, y)):
                    sample_points.append((x, y))
                    gx = int((x - (x_center - radius)) / cell_size)
                    gy = int((y - (y_center - radius)) / cell_size)
                    if 0 <= gx < grid_width and 0 <= gy < grid_height:
                        grid[gx][gy] = (x, y)
                    added += 1
                y += fine_spacing
            x += fine_spacing
        return added

    def systematic_post_pass():
        added = 0
        spacing = cell_size / 3
        x_offset = spacing / 2
        y_offset = spacing / 2

        x_range = np.arange(x_center - radius + x_offset,
                        x_center + radius, spacing)
        y_range = np.arange(y_center - radius + y_offset,
                        y_center + radius, spacing)

        total_rows = len(x_range)

        for i, x in enumerate(x_range):
            for y in y_range:
                cand = (x, y)
                if point_fits(cand):
                    sample_points.append(cand)
                    gx = int((x - (x_center - radius)) / cell_size)
                    gy = int((y - (y_center - radius)) / cell_size)
                    if 0 <= gx < grid_width and 0 <= gy < grid_height:
                        grid[gx][gy] = cand
                    added += 1

            # print every 10% of rows
            if i % max(1, total_rows // 10) == 0:
                percent = (i + 1) / total_rows * 100
                print(f"[systematic_post_pass] Progress: {percent:.1f}%")

        return added

    def elliptical_final_pass():
        added = 0
        step_x = min_spacing_x / 2.5
        step_y = min_spacing_y / 2.5

        angle_rad = np.radians(wind_direction_deg)
        cos_theta = np.cos(angle_rad)
        sin_theta = np.sin(angle_rad)

        # Create a rotated grid aligned with wind direction
        grid_extent = np.arange(-radius, radius, step_x)
        for dx in grid_extent:
            for dy in np.arange(-radius, radius, step_y):
                # Rotate elliptical grid
                x = x_center + dx * cos_theta - dy * sin_theta
                y = y_center + dx * sin_theta + dy * cos_theta
                if (x - x_center) ** 2 + (y - y_center) ** 2 <= radius ** 2:
                    if point_fits((x, y)):
                        sample_points.append((x, y))
                        gx = int((x - (x_center - radius)) / cell_size)
                        gy = int((y - (y_center - radius)) / cell_size)
                        if 0 <= gx < grid_width and 0 <= gy < grid_height:
                            grid[gx][gy] = (x, y)
                        added += 1
        return added

    def repel_turbines():
        max_iterations = 10
        moved = 0
        for _ in range(max_iterations):
            for i, pt in enumerate(sample_points):
                force_x, force_y = 0.0, 0.0
                for j, other in enumerate(sample_points):
                    if i == j:
                        continue
                    dx = pt[0] - other[0]
                    dy = pt[1] - other[1]
                    dist_sq = dx**2 + dy**2
                    if dist_sq < 1e-2:
                        continue
                    if dist_sq < (min_spacing_x**2):
                        force = 1.0 / dist_sq
                        force_x += dx * force
                        force_y += dy * force
                new_x = pt[0] + 0.25 * force_x
                new_y = pt[1] + 0.25 * force_y
                new_pt = (new_x, new_y)
                if point_fits(new_pt):
                    sample_points[i] = new_pt
                    moved += 1
        return moved

    # Apply both refinements
    refined_border_pass()
    systematic_post_pass()
    elliptical_final_pass()
    repel_turbines()
    elliptical_final_pass() 

    return sample_points



def generate_crane_pads(turbine_points_local, polygon_shape_local, to_wgs, wind_direction_deg):
    """
    Generate crane pads around each turbine point, oriented with wind direction.
    
    Args:
        turbine_points_local: List of (x, y) turbine positions in local CRS
        polygon_shape_local: Polygon shape in local CRS (unused but kept for consistency)
        to_wgs: Transformer to convert from local CRS to WGS84
        wind_direction_deg: Wind direction in degrees (0=North, 90=East, etc.)
    
    Returns:
        GeoDataFrame with buffered crane pad polygons in WGS84
    """
    crane_pads_list = []
    
    for turbine_pt in turbine_points_local:
        # Create 60m x 30m rectangle centered at origin
        crane_pad = box(-30, -15, 30, 15)  # 60m wide (x), 30m tall (y)
        
        # Rotate to align with wind direction
        crane_pad = rotate(crane_pad, wind_direction_deg, origin=(0, 0))
        
        # Translate to turbine position
        crane_pad = translate(crane_pad, xoff=turbine_pt[0], yoff=turbine_pt[1])
        
        # Transform to WGS84
        crane_pad_wgs = shapely_transform(to_wgs.transform, crane_pad)
        crane_pads_list.append(crane_pad_wgs)
    
    # Create GeoDataFrame with crane pads
    crane_pads_gdf = gpd.GeoDataFrame({
        'buffered_geometry': crane_pads_list,
        'obstacle_type': ['Kranstellplätze'] * len(crane_pads_list)
    }, geometry='buffered_geometry', crs="EPSG:4326")
    
    return crane_pads_gdf





def generate_access_roads_nearest(turbine_points_local, obstacles_gdf, polygon_shape_local, to_wgs, grid_cell_Size=20):
    """
    Generate access roads connecting turbines to nearest main road.
    Uses straight LineStrings with obstacle avoidance checking.
    
    Returns:
        GeoDataFrame with buffered road polygons in WGS84
    """

    
    # If no turbines, return empty GeoDataFrame
    if len(turbine_points_local) == 0:
        return gpd.GeoDataFrame({
            'buffered_geometry': [],
            'obstacle_type': []
        }, geometry='buffered_geometry', crs="EPSG:4326")
    
    # Filter traffic obstacles (roads)
    traffic_obstacles = obstacles_gdf[obstacles_gdf["obstacle_type"] == "Verkehr"]
    
    # Debug: Check if we found roads
    st.write(f"🛣️ Gefundene Verkehrshindernisse (Straßen): {len(traffic_obstacles)}")
    
    # Get non-road obstacles for collision checking
    non_road_obstacles = obstacles_gdf[obstacles_gdf["obstacle_type"] != "Verkehr"]
    
    access_roads_list = []
    
    # If no roads found, connect to polygon centroid instead
    if traffic_obstacles.empty:
        st.write("⚠️ Keine Straßen gefunden - verbinde mit Polygon-Zentrum")
        centroid = polygon_shape_local.centroid
        
        for turbine_pt in turbine_points_local:
            turbine_point = Point(turbine_pt)
            road_line = LineString([turbine_pt, (centroid.x, centroid.y)])
            
            if road_line.length < 10:
                continue
            
            hits_obstacle = False
            for _, obstacle_row in non_road_obstacles.iterrows():
                if road_line.intersects(obstacle_row['buffered_geometry']):
                    hits_obstacle = True
                    break
            
            if not hits_obstacle:
                road_buffered = road_line.buffer(10)
                road_wgs = shapely_transform(to_wgs.transform, road_buffered)
                access_roads_list.append(road_wgs)
    else:
        # Generate road for each turbine - find nearest road CENTER (not buffered edge)
        for turbine_pt in turbine_points_local:
            turbine_point = Point(turbine_pt)
            
            # Find the nearest road CENTERLINE (use representative_point of each road)
            min_distance = float('inf')
            nearest_road_center = None
            
            for _, road_row in traffic_obstacles.iterrows():
                # Get center point of road (approximate centerline)
                road_center = road_row['buffered_geometry'].representative_point()
                distance = turbine_point.distance(road_center)
                if distance < min_distance:
                    min_distance = distance
                    nearest_road_center = road_center
            
            # Connect turbine to nearest road center point
            road_line = LineString([turbine_pt, (nearest_road_center.x, nearest_road_center.y)])
            
            # st.write(f"   Turbine an ({turbine_pt[0]:.1f}, {turbine_pt[1]:.1f}), Straßenlänge: {road_line.length:.1f}m")
            
            # Skip if road length is too small (turbine already on/near road)
            if road_line.length < 10:  # Less than 10 meters
                # st.write(f"   ⚠️ Turbine bereits an Straße ({road_line.length:.1f}m) - überspringe Zufahrtsweg")
                continue
            
            # Check if line intersects non-road obstacles
            hits_obstacle = False
            for _, obstacle_row in non_road_obstacles.iterrows():
                if road_line.intersects(obstacle_row['buffered_geometry']):
                    hits_obstacle = True
                    # st.write(f"   ⚠️ Zufahrtsweg blockiert durch {obstacle_row.get('obstacle_type', 'Hindernis')}")
                    break
            
            # Only create road if path is clear
            if not hits_obstacle:
                # Buffer the line to create 20m wide road (10m on each side)
                road_buffered = road_line.buffer(10)
                
                # Transform to WGS84
                road_wgs = shapely_transform(to_wgs.transform, road_buffered)
                access_roads_list.append(road_wgs)
                # st.write(f"   ✅ Zufahrtsweg erstellt!")
            # else:
                # st.write(f"   ❌ Kein Zufahrtsweg - Weg blockiert")
    
    # Create GeoDataFrame with access roads
    if access_roads_list:
        st.write(f"✅ {len(access_roads_list)} Zufahrtswege erfolgreich erstellt (von {len(turbine_points_local)} Turbinen)")
        access_roads_gdf = gpd.GeoDataFrame({
            'buffered_geometry': access_roads_list,
            'obstacle_type': ['Zufahrtswege'] * len(access_roads_list)
        }, geometry='buffered_geometry', crs="EPSG:4326")
    else:
        st.write(f"⚠️ Keine Zufahrtswege erstellt - alle {len(turbine_points_local)} Wege durch Hindernisse blockiert")
        # Return empty GeoDataFrame if no roads created
        access_roads_gdf = gpd.GeoDataFrame({
            'buffered_geometry': [],
            'obstacle_type': []
        }, geometry='buffered_geometry', crs="EPSG:4326")
    
    return access_roads_gdf

# Function to pack wind turbines within a circle
def packing_wind(lat_center, lon_center, radius_meters, min_spacing_x, min_spacing_y, obstacles, wind_direction_deg, status_box, m2, option, polygon_coords=None):
    crs_local = get_local_crs(lon_center, lat_center)
    to_local = Transformer.from_crs("EPSG:4326", crs_local, always_xy=True)
    to_wgs = Transformer.from_crs(crs_local, "EPSG:4326", always_xy=True)
    x_center, y_center = to_local.transform(lon_center, lat_center)
    access_roads_gdf = None
    if polygon_coords is not None:
        status_box.info("💨 Windturbinen innerhalb des Polygons platzieren...")
        
        # Convert polygon coordinates to local CRS
        polygon_local = []
        for coord in polygon_coords:
            x, y = to_local.transform(coord[0], coord[1])
            polygon_local.append((x, y))
        
        
        polygon_shape = Polygon(polygon_local)
        
        # Convert obstacles to local CRS
        local_obstacles = obstacles.to_crs(crs_local)

        if wind_direction_deg is None:
            wind_direction_deg = 240
            st.write("⚠️ Hauptwindrichtung nicht gefunden. Standardwert 240° verwendet.")
        
        # Use polygon-based Poisson disk sampling (same algorithm as circle, but with polygon boundary)
        turbine_points = poisson_disk_sampling_polygon(
            polygon_shape=polygon_shape,
            min_spacing_x=min_spacing_x,
            min_spacing_y=min_spacing_y,
            wind_direction_deg=wind_direction_deg,
            obstacles_local_crs=local_obstacles,
        )
        
        access_roads_gdf = generate_access_roads_nearest(turbine_points_local=turbine_points,
                                      obstacles_gdf=local_obstacles,
                                      polygon_shape_local=polygon_shape,
                                      to_wgs=to_wgs)
        
        # Generate crane pads oriented with wind direction
        crane_pads_gdf = generate_crane_pads(turbine_points_local=turbine_points,
                                             polygon_shape_local=polygon_shape,
                                             to_wgs=to_wgs,
                                             wind_direction_deg=wind_direction_deg)
        
        # Debug output
        if access_roads_gdf is not None and not access_roads_gdf.empty:
            st.write(f"✅ {len(access_roads_gdf)} Zufahrtswege generiert")
        else:
            st.write("⚠️ Keine Zufahrtswege generiert (alle Wege blockiert oder keine Straßen gefunden)")
        
        if crane_pads_gdf is not None and not crane_pads_gdf.empty:
            st.write(f"✅ {len(crane_pads_gdf)} Kranstellplätze generiert")
        else:
            st.write("⚠️ Keine Kranstellplätze generiert")
        
    else:
        status_box.info("💨 Windturbinen innerhalb des Kreises platzieren...")

        # Poisson sampling for circle mode
        local_obstacles = obstacles.to_crs(crs_local)

        if wind_direction_deg is None:
            wind_direction_deg = 240
            st.write("⚠️ Hauptwindrichtung nicht gefunden. Standardwert 50° verwendet.")
        
        turbine_points = poisson_disk_sampling(
            center_xy=(x_center, y_center),
            radius=radius_meters,
            min_spacing_x=min_spacing_x,
            min_spacing_y=min_spacing_y,
            wind_direction_deg=wind_direction_deg,
            obstacles_local_crs=local_obstacles,
        )

    # Initialize layers
    turbine_layer = folium.FeatureGroup(name="Windturbinen")
    wind_obstacle_layer = folium.FeatureGroup(name="Wind_Hindernisse")
    Zufahrtswege_layer = folium.FeatureGroup(name="Zufahrtswege")
    Kranstellplaetze_layer = folium.FeatureGroup(name="Kranstellplätze")

    for pt in turbine_points:
        latlon = to_wgs.transform(pt[0], pt[1])[::-1]
        folium.CircleMarker(location=latlon, radius=5, color='orange', fill=True, fill_opacity=0.8).add_to(turbine_layer)
        
        # Rotated ellipse buffer
        ellipse = Point(pt).buffer(1)  # Unit circle
        ellipse = scale(ellipse, xfact=min_spacing_x, yfact=min_spacing_y)
        ellipse = rotate(ellipse, angle=wind_direction_deg, origin=pt, use_radians=False)
        ellipse_wgs = shapely_transform(to_wgs.transform, ellipse)

        if ellipse_wgs.geom_type == 'Polygon':
            coords = [(lat, lon) for lon, lat in ellipse_wgs.exterior.coords]
            folium.Polygon(
                locations=coords,
                color='orange',
                weight=1,
                fill=False,
                tooltip='Turbinenabstand'
            ).add_to(turbine_layer)

    # Define obstacle colors
    color_map = {
        "Verkehr": "#808080",                # Gray
        "Landnutzung": "#228B22",            # Green
        "Infrastruktur": "#DC143C",          # Crimson Red
        "Militärische Belange": "#FF8C00",   # Dark Orange
        "Artenschutz": "#800080",            # Purple
        "Natur und Landschaft": "#1E90FF",   # Dodger Blue
        "Wald": "#6B8E23",                   # Olive Drab
        "Gewässer": "#20B2AA",               # Light Sea Green
        "Sonstiges": "#8B4513"         # Saddle Brown
    }
    
    merged_obstacles = []

    for obstacle_type in obstacles['obstacle_type'].unique():
        category_gdf = obstacles[obstacles['obstacle_type'] == obstacle_type]
        unioned = unary_union(category_gdf['buffered_geometry'])

        # Ensure union result is iterable
        geoms_to_draw = []

        if unioned.geom_type in ["Polygon", "MultiPolygon"]:
            geoms_to_draw = list(unioned.geoms) if unioned.geom_type == "MultiPolygon" else [unioned]

        elif unioned.geom_type == "GeometryCollection":
            geoms_to_draw = [g for g in unioned.geoms if g.geom_type in ["Polygon", "MultiPolygon"]]
        
        for geom in geoms_to_draw:
            merged_obstacles.append({
                "geometry": geom,
                "obstacle_type": obstacle_type
            })

    # Convert to GeoDataFrame
    merged_gdf = gpd.GeoDataFrame(merged_obstacles, geometry="geometry", crs=obstacles.crs)

    # Draw shaded obstacles
    for _, row in merged_gdf.iterrows():
        obstacle_type = row["obstacle_type"]
        color = color_map.get(obstacle_type, "red")
        geom = row["geometry"]

        if geom.geom_type == 'Polygon':
            if geom.is_empty or geom.exterior.is_empty:
                continue
            exterior_coords = [(lat, lon) for lon, lat in geom.exterior.coords]
            hole_coords = [[(lat, lon) for lon, lat in hole.coords] for hole in geom.interiors]
            folium.Polygon(
                locations=[exterior_coords] + hole_coords,
                color=color,
                weight=0.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.5,
                tooltip=obstacle_type
            ).add_to(wind_obstacle_layer)

        
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                if poly.is_empty or poly.exterior.is_empty:
                    continue
                exterior_coords = [(lat, lon) for lon, lat in poly.exterior.coords]
                hole_coords = [[(lat, lon) for lon, lat in hole.coords] for hole in poly.interiors]

                folium.Polygon(
                    locations=[exterior_coords] + hole_coords,
                    color=color,
                    weight=0.5,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.5,
                    tooltip=obstacle_type
                ).add_to(wind_obstacle_layer)
    
    # Draw access roads on map (if they exist)
    if access_roads_gdf is not None and not access_roads_gdf.empty:
        # st.write(f"🎨 Zeichne {len(access_roads_gdf)} Zufahrtswege auf Karte...")
        for idx, road_row in access_roads_gdf.iterrows():
            road_geom = road_row['buffered_geometry']
            # st.write(f"   Straße {idx+1}: Geometrie-Typ = {road_geom.geom_type}, Koordinaten-Anzahl = {len(list(road_geom.exterior.coords)) if road_geom.geom_type == 'Polygon' else 'N/A'}")
            
            if road_geom.geom_type == 'Polygon':
                exterior_coords = [(lat, lon) for lon, lat in road_geom.exterior.coords]
                folium.Polygon(
                    locations=exterior_coords,
                    color='#FF00FF',        # Bright Magenta/Purple color
                    weight=1,               # Thinner border line
                    fill=True,
                    fill_color='#FF00FF',
                    fill_opacity=0.6,       # Slightly more transparent
                    tooltip='Zufahrtsweg'
                ).add_to(Zufahrtswege_layer)
    
    # Draw crane pads on map (if they exist)
    if crane_pads_gdf is not None and not crane_pads_gdf.empty:
        for idx, crane_row in crane_pads_gdf.iterrows():
            crane_geom = crane_row['buffered_geometry']
            
            if crane_geom.geom_type == 'Polygon':
                exterior_coords = [(lat, lon) for lon, lat in crane_geom.exterior.coords]
                folium.Polygon(
                    locations=exterior_coords,
                    color='#8B4513',        # Brown color for crane pads
                    weight=1,
                    fill=True,
                    fill_color='#8B4513',
                    fill_opacity=0.7,
                    tooltip='Kranstellplatz'
                ).add_to(Kranstellplaetze_layer)
    
    # ============================================================================
    # CIRCLE BOUNDARY - COMMENTED OUT (Not used - polygon only)
    # ============================================================================
    # folium.Circle(
    #     location=[lat_center, lon_center],
    #     radius=radius_meters,
    #     color='rgb(255, 225, 25)',
    #     weight=2,
    #     fill=False,
    #     fill_opacity=0.2,
    # ).add_to(m2)
    # ============================================================================

    # Get projection transformers
    crs_local = get_local_crs(lon_center, lat_center)
    to_local = Transformer.from_crs("EPSG:4326", crs_local, always_xy=True)
    to_wgs = Transformer.from_crs(crs_local, "EPSG:4326", always_xy=True)

    # Convert center to projected coordinates
    x_center, y_center = to_local.transform(lon_center, lat_center)

    # Arrow length in meters
    arrow_length = 100  # adjust as needed for visibility

    # Compute endpoint in projected space
    dx = arrow_length * np.sin(np.radians(wind_direction_deg))
    dy = arrow_length * np.cos(np.radians(wind_direction_deg))
    x_end = x_center + dx
    y_end = y_center + dy

    # Convert both points back to lat/lon
    lon_end, lat_end = to_wgs.transform(x_end, y_end)

    # Draw on map
    arrow_coords = [[lat_center, lon_center], [lat_end, lon_end]]
    folium.PolyLine(arrow_coords, color="black", weight=3, tooltip="Windrichtung").add_to(turbine_layer)

    m2.add_child(turbine_layer)
    m2.add_child(wind_obstacle_layer)
    m2.add_child(Zufahrtswege_layer)
    m2.add_child(Kranstellplaetze_layer)

    if not ("Hybrid" in option):
        m2.add_child(folium.LayerControl())

    return m2, len(turbine_points), access_roads_gdf, crane_pads_gdf

@st.cache_data(show_spinner=False)
def get_weather_for_windpowerlib(lat, lon, year=2024, months=None):
    """Fetch wind weather data from DWD for windpowerlib simulations.

    Returns (weather_df, main_dir) where weather_df is a MultiIndex DataFrame
    formatted for windpowerlib and main_dir is the prevailing wind direction (°).
    """
    import calendar
    from datetime import datetime
    from src.data_layer.weather_integration import fetch_weather_for_wind

    if months is None:
        months = list(range(1, 13))

    start_date = datetime(year, min(months), 1)
    last_month = max(months)
    last_day = calendar.monthrange(year, last_month)[1]
    end_date = datetime(year, last_month, last_day, 23, 59, 59)

    try:
        weather_data, _meta = fetch_weather_for_wind(
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
            resolution="hourly",
        )
    except Exception as e:
        st.error(f"❌ Konnte keine DWD Wetterdaten laden: {e}")
        return None, None

    main_dir = _get_prevailing_wind_direction(lat, lon, start_date, end_date)
    return weather_data, main_dir


def _get_prevailing_wind_direction(lat, lon, start_date, end_date, default=225.0):
    """Return prevailing wind direction (°) from DWD observations, or SW default."""
    try:
        from src.data_layer.weather_integration import get_dwd_fetcher
        from src.config import DWD

        fetcher = get_dwd_fetcher()
        raw_data, _ = fetcher.get_observations(
            latitude=lat,
            longitude=lon,
            parameters=['wind'],
            start_date=start_date,
            end_date=end_date,
            resolution='10_minutes',
            max_distance_km=DWD.MAX_STATION_DISTANCE_KM,
            n_stations=1,
        )
        dir_col = next((c for c in raw_data.columns if 'DD' in str(c).upper()), None)
        if dir_col is None:
            return default
        directions = raw_data[dir_col].dropna()
        directions = directions[directions > 0]
        if directions.empty:
            return default
        rad = np.deg2rad(directions)
        return float(np.degrees(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())) % 360)
    except Exception:
        return default