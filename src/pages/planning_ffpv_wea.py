"""FFPV and WEA planning page.

Interactive planning tool for solar (FFPV) and wind (WEA) installations.
Allows users to draw polygons on a map and simulates placement and energy generation.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
from streamlit_folium import st_folium
from streamlit.components.v1 import html
import folium
import time
import numpy as np
from folium.plugins import Draw, MousePosition
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Solar panel specifications (in meters)
SOLAR_PANEL_WIDTH = 1.96
SOLAR_PANEL_HEIGHT = 3.66  # For 4 modules
ROW_SPACING = 3.5

# Wind turbines specifications (in meters)
MIN_SPACING_X = 1270
MIN_SPACING_Y = 762
HUB_HEIGHT = 135


@st.dialog("Anleitung und Hinweise", width="large")
def show_instructions():
    """Display instructions and notes for the planning tool."""
    st.markdown(
        """
        **Anleitung:**  
        1. Wählen Sie die Art der Anlage, die Sie planen möchten (FFPV, WEA oder Hybrid).  
        2. Geben Sie einen Ort oder eine Adresse ein, um die Karte zu zentrieren. Alternativ können Sie die Karte manuell verschieben und zoomen.  
        3. Klicken Sie auf das Kreissymbol oben rechts auf der Karte und ziehen Sie den Kreis auf der Karte auf, indem Sie auf eine Stelle auf der Karte klicken und nach außen ziehen. Lassen Sie die Maus los und das Programm wird automatisch durchgeführt. Der Kreis stellt das zu beplanende Gebiet dar.  
        4. Scrollen Sie nach unten, um die Ergebnisse der Simulation zu sehen.  
        5. Um einen neuen Kreis zu zeichnen, klicken Sie zunächst auf das Mülleimersymbol auf der rechten Seite der Karte unter dem Kreissymbol. Klicken Sie dann auf „Alles löschen", um den aktuellen Kreis zu löschen.  
        6. Zeichnen Sie einen neuen Kreis, indem Sie erneut auf das Kreissymbol klicken und den Kreis auf der Karte ziehen.  

        **Hinweise:**  
        *Dieses Programm funktioniert derzeit nur für Regionen innerhalb Deutschlands.*  
        *Eine Infobox unterhalb der Karte zeigt den Fortschritt der Simulation an. Alternativ bedeutet ein „RUNNING..."-Symbol oben rechts im Browser, dass das Programm gerade läuft.*  
        *In der Infobox wird „Erfolgreich" angezeigt, wenn der Vorgang abgeschlossen ist.*  
        *Sie können im Diagramm verschieben und zoomen. Klicken Sie auf das Symbol oben rechts im Diagramm, um es als Vollbild anzuzeigen. Klicken Sie auf die drei Punkte oben rechts, um das Diagramm zu exportieren.*  
        *Sie können ebenfalls die Karte verschieben und zoomen. Oben rechts auf der Karte können Sie die Layers ein- oder ausblenden.*  
        *Klicken Sie auf die Schaltfläche „Karte als HTML herunterladen", um die Karte als HTML-Datei herunterzuladen.*  

        *Die in diesem Tool erstellten Darstellungen und Simulationen stellen keine vollständige Planung realer Solar- oder Windparks dar*.  
        *Vielmehr handelt es sich um eine theoretische Abschätzung des Flächenpotenzials und der potenziellen Energieerzeugung in einem definierten Gebiet*.  
        *Die Positionierung der Solarmodule und Windturbinen basiert ausschließlich auf öffentlich zugänglichen Geodaten (z.B. OpenStreetMap) und standardisierten Ausschlusskriterien,  
        *ohne Prüfung standortbezogener Genehmigungsbedingungen, Netzanschlussoptionen oder detaillierter Umweltverträglichkeitsprüfungen*.  
        *Dieses Werkzeug dient daher in erster Linie der automatisierten Potenzialanalyse und nicht der Erstellung genehmigungsfähiger Planungsunterlagen*.
        """
    )


def planning_ffpv_wea() -> None:
    """Main planning interface for solar (FFPV) and wind (WEA) installations."""
    st.title("Programm zur Planung von Solar- und Windkraftanlagen")
    
    if st.button("Anleitung und Hinweise"):
        show_instructions()
    
    option = st.radio(
        "Welche Art von Anlage möchten Sie planen?",
        ("FFPV", "WEA", "Hybrid (FFPV + WEA)")
    )

    # Search functionality
    geolocator = Nominatim(user_agent="solar-farm-planner")
    location_input = st.text_input("Suchen Sie nach einem Ort oder einer Adresse:", "")

    # Initialize session state to avoid repeated queries
    if 'geocoded_results' not in st.session_state:
        st.session_state['geocoded_results'] = None
    if 'last_query' not in st.session_state:
        st.session_state['last_query'] = ""

    # Default center
    map_center = [51.1657, 10.4515]
    zoom_level = 6
    location = None

    # Perform geocoding only when query is new
    if location_input and location_input != st.session_state['last_query']:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                locations = geolocator.geocode(location_input, exactly_one=False, addressdetails=True, limit=5)
                if locations:
                    st.session_state['geocoded_results'] = locations
                    st.session_state['last_query'] = location_input
                else:
                    st.warning("Keine Adresse gefunden")
                    st.session_state['geocoded_results'] = None
                break
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    st.error(f"Geocoding error: {e}")
                    st.session_state['geocoded_results'] = None

    # Show dropdown and update map if results exist
    if st.session_state['geocoded_results']:
        locations = st.session_state['geocoded_results']
        location_options = [f"{loc.address} ({loc.latitude:.4f}, {loc.longitude:.4f})" for loc in locations]
        selection = st.selectbox("Ausgewählte Adresse:", location_options)

        selected_index = location_options.index(selection)
        selected_location = locations[selected_index]
        st.session_state["selected_location"] = selected_location
        map_center = [selected_location.latitude, selected_location.longitude]
        zoom_level = 15

    m = folium.Map(location=map_center, zoom_start=zoom_level)
    mouse_position = MousePosition(position='bottomright', separator=' | ', prefix="Coordinates:", num_digits=6)
    m.add_child(mouse_position)

    # Drop marker at the searched location
    if "selected_location" in st.session_state:
        folium.Marker(
            location=[st.session_state["selected_location"].latitude, st.session_state["selected_location"].longitude],
            icon=folium.Icon(color="blue", icon="search")
        ).add_to(m)

    # Add a draw tool to the map (for drawing polygons only)
    draw = Draw(
        export=False,
        draw_options={
            'polyline': False,
            'polygon': True,
            'rectangle': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={
            'edit': False,
            'remove': True
        }
    )
    draw.add_to(m)

    # Display the map and get draw data
    with st.container():
        output = st_folium(m, width=700, height=500, key="map_draw")

    status_box = st.empty()

    # Initialize session state variables
    if "last_polygon_coords" not in st.session_state:
        st.session_state["last_polygon_coords"] = []
    if "num_panels" not in st.session_state:
        st.session_state["num_panels"] = None
    if "num_turbines" not in st.session_state:
        st.session_state["num_turbines"] = None
    if "second_map" not in st.session_state:
        st.session_state["second_map"] = None
    if "results_df" not in st.session_state:
        st.session_state["results_df"] = None
    if "total_energy" not in st.session_state:
        st.session_state["total_energy"] = None
    if "results_ac" not in st.session_state:
        st.session_state["results_ac"] = None
    if "rated_power_solar" not in st.session_state:
        st.session_state["rated_power_solar"] = None
    if "rated_power_wind" not in st.session_state:
        st.session_state["rated_power_wind"] = None

    # Initialize variables
    current_polygon_coords = None
    radius_meters = 0
    
    # Check if the user has drawn a shape
    m2 = None
    lat_center = None
    lon_center = None

    if output and output.get('last_active_drawing'):
        if output.get('last_circle_polygon'):
            try:
                # Circle mode
                circle_data = output['last_circle_polygon']
                lat_center = circle_data['properties']['center'][1]
                lon_center = circle_data['properties']['center'][0]
                radius_meters = circle_data['properties']['radius']
                current_polygon_coords = circle_data['coordinates'][0]
                status_box.info("🔄 Kreis erkannt...")
            except (KeyError, TypeError, IndexError) as e:
                status_box.error(f"❌ Fehler beim Verarbeiten des Kreises: {str(e)}")
                st.stop()
                
        elif output['last_active_drawing']['geometry']['type'] == 'Polygon':
            try:
                # Polygon mode
                current_polygon_coords = output['last_active_drawing']['geometry']['coordinates'][0]
                lat_center = float(np.mean([pt[1] for pt in current_polygon_coords]))
                lon_center = float(np.mean([pt[0] for pt in current_polygon_coords]))
                status_box.info("🔄 Polygon erkannt...")
            except (KeyError, TypeError, IndexError) as e:
                status_box.error(f"❌ Fehler beim Verarbeiten des Polygons: {str(e)}")
                st.stop()
        else:
            status_box.error("❌ Bitte zeichnen Sie einen Kreis oder ein Polygon")
            st.stop()
    else:
        status_box.error("❌ Bitte zeichnen Sie einen Kreis oder ein Polygon")
        st.stop()

    # Store values in output and session state
    output['lat_center'] = lat_center
    output['lon_center'] = lon_center
    st.session_state["last_polygon_coords"] = current_polygon_coords

    # Create base map
    m2 = folium.Map(location=[lat_center, lon_center], zoom_start=20)
    mouse_position = MousePosition(position='bottomright', separator=' | ', prefix="Coordinates:", num_digits=6)
    m2.add_child(mouse_position)

    # Calculate centroid for map recentering and further processing
    lats = [pt[1] for pt in current_polygon_coords]
    lons = [pt[0] for pt in current_polygon_coords]
    lat_center = float(np.mean(lats))
    lon_center = float(np.mean(lons))
    
    # Store in session state for later use
    st.session_state["lat_center"] = lat_center
    st.session_state["lon_center"] = lon_center
    m2 = folium.Map(location=[lat_center, lon_center], zoom_start=20)
    mouse_position = MousePosition(position='bottomright', separator=' | ', prefix="Coordinates:", num_digits=6)
    m2.add_child(mouse_position)
    
    # Execute simulation based on selected option
    _execute_simulation(option, output, current_polygon_coords, lat_center, lon_center, 
                       radius_meters, status_box, m2)
    
    # Display results if available
    if st.session_state["second_map"] and "second_map_html" in st.session_state:
        _display_results(option, status_box)


def _execute_simulation(option: str, output: dict, current_polygon_coords: list, 
                       lat_center: float, lon_center: float, radius_meters: float,
                       status_box, m2) -> None:
    """Execute the appropriate simulation based on user selection."""
    if option == "FFPV":
        from src.planning import fetch_obstacles_solar, packing_solar, simulate_solarfarm_output
        
        obstacles = fetch_obstacles_solar(output, current_polygon_coords, status_box)
        m2_solar, num_panels = packing_solar(lat_center, lon_center, 0,
                                            SOLAR_PANEL_WIDTH, SOLAR_PANEL_HEIGHT, ROW_SPACING,
                                            obstacles, status_box, m2,
                                            polygon_coords=current_polygon_coords)
        
        st.session_state["num_panels"] = num_panels
        st.session_state["second_map"] = m2_solar
        st.session_state["second_map_html"] = m2_solar._repr_html_()
        status_box.info("🧮 Solaranlagen simulieren...")
        results_ac, rated_power_solar = simulate_solarfarm_output(lat_center, lon_center, num_panels)
        st.session_state["results_ac"] = results_ac
        st.session_state["rated_power_solar"] = rated_power_solar
        
    elif option == "WEA":
        from src.planning import fetch_obstacles_wind, packing_wind, get_weather_for_windpowerlib
        
        obstacles = fetch_obstacles_wind(output, current_polygon_coords, status_box, MIN_SPACING_X, MIN_SPACING_Y)
        status_box.info("☁️ Wetterdaten abrufen...")
        weather_df, main_dir = get_weather_for_windpowerlib(lat_center, lon_center, year=2024)
        
        if weather_df is None:
            st.error("❌ Konnte keine DWD Wetterdaten laden. Bitte überprüfen Sie die Netzwerkverbindung und den gewählten Standort.")
            st.stop()
            
        m2_wind, num_turbines, access_roads_gdf, crane_pads_gdf = packing_wind(
            lat_center, lon_center, 0, MIN_SPACING_X, MIN_SPACING_Y, obstacles, 
            main_dir, status_box, m2, option, polygon_coords=current_polygon_coords)
            
        st.session_state["num_turbines"] = num_turbines
        st.session_state["second_map"] = m2_wind
        st.session_state["second_map_html"] = m2_wind._repr_html_()
        st.session_state["lat_center"] = lat_center
        st.session_state["lon_center"] = lon_center
        st.session_state["radius_meters"] = radius_meters
        
    elif option == "Hybrid (FFPV + WEA)":
        _execute_hybrid_simulation(output, current_polygon_coords, lat_center, lon_center, status_box, m2)


def _execute_hybrid_simulation(output: dict, current_polygon_coords: list,
                              lat_center: float, lon_center: float, status_box, m2) -> None:
    """Execute hybrid solar and wind simulation."""
    from src.planning import fetch_obstacles_wind, packing_wind, get_weather_for_windpowerlib
    from src.planning import fetch_obstacles_solar, packing_solar, simulate_solarfarm_output
    import geopandas as gpd
    import pandas as pd
    
    # Fetch wind obstacles
    obstacles_wind = fetch_obstacles_wind(output, current_polygon_coords, status_box, MIN_SPACING_X, MIN_SPACING_Y)
    
    # Get weather data and wind direction
    status_box.info("☁️ Wetterdaten abrufen...")
    weather_df, main_dir = get_weather_for_windpowerlib(lat_center, lon_center, year=2024)
    
    # Place wind turbines and generate access roads and crane pads
    m2_wind, num_turbines, access_roads_gdf, crane_pads_gdf = packing_wind(
        lat_center, lon_center, 0, MIN_SPACING_X, MIN_SPACING_Y, obstacles_wind, 
        main_dir, status_box, m2, "Hybrid (FFPV + WEA)", polygon_coords=current_polygon_coords)
    
    st.session_state["num_turbines"] = num_turbines
    
    # Initialize combined obstacles with wind obstacles
    combined_obstacles = obstacles_wind.copy()
    
    # Merge access roads with wind obstacles for solar placement
    if access_roads_gdf is not None and not access_roads_gdf.empty:
        combined_obstacles = pd.concat([combined_obstacles, access_roads_gdf], ignore_index=True)
    
    if crane_pads_gdf is not None and not crane_pads_gdf.empty:
        combined_obstacles = pd.concat([combined_obstacles, crane_pads_gdf], ignore_index=True)
    
    # Fetch solar-specific obstacles and merge with combined wind obstacles
    obstacles_solar = fetch_obstacles_solar(output, current_polygon_coords, status_box)
    final_obstacles = pd.concat([combined_obstacles, obstacles_solar], ignore_index=True)
    
    # Place solar panels with all obstacles
    status_box.info("☀️ Solarmodule platzieren...")
    m2_combined, num_panels = packing_solar(
        lat_center, lon_center, 0, SOLAR_PANEL_WIDTH, SOLAR_PANEL_HEIGHT, ROW_SPACING,
        final_obstacles, status_box, m2_wind, polygon_coords=current_polygon_coords)
    
    st.session_state["num_panels"] = num_panels
    st.session_state["second_map"] = m2_combined
    st.session_state["second_map_html"] = m2_combined._repr_html_()
    
    # Simulate solar farm output
    status_box.info("🧮 Solarmodule simulieren...")
    results_ac, rated_power_solar = simulate_solarfarm_output(lat_center, lon_center, num_panels)
    st.session_state["results_ac"] = results_ac
    st.session_state["rated_power_solar"] = rated_power_solar


def _display_results(option: str, status_box) -> None:
    """Display simulation results based on the selected option."""
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    
    if option == "FFPV":
        _display_solar_results(status_box)
    elif option == "WEA":
        _display_wind_results(status_box)
    elif option == "Hybrid (FFPV + WEA)":
        _display_hybrid_results(status_box)
    
    # Common download button
    st.download_button(
        "Karte als HTML herunterladen",
        data=st.session_state["second_map_html"],
        file_name="map_fragment.html",
        mime="text/html",
    )
    
    status_box.info("✅ Erfolgreich!")


def _display_solar_results(status_box) -> None:
    """Display solar (FFPV) simulation results."""
    import matplotlib.pyplot as plt
    
    st.subheader("Karte mit Solarmodulen")
    status_box.info("🗺️ Karte mit Solarmodulen erstellen...")
    
    # Display energy generation if available
    if "results_ac" in st.session_state and "rated_power_solar" in st.session_state:
        st.subheader("Energieerzeugung")
        results_ac = st.session_state["results_ac"]
        rated_power_solar = st.session_state["rated_power_solar"]
        
        # Display simulation info
        st.write("Kreisinformationen")
        if "lat_center" in st.session_state and "lon_center" in st.session_state:
            st.write(f"Zentrum (Längengrad, Breitengrad): [{st.session_state['lat_center']:.6f}, {st.session_state['lon_center']:.6f}]")
        
        # Show simulation results
        st.write("Simulationsergebnisse")
        if "num_panels" in st.session_state:
            st.write(f"Anzahl von Solarmodulen: {st.session_state['num_panels']}")
        yearly_energy = results_ac.sum() / 1e9  # Convert to GWh
        st.write(f"Gesamtenergieerzeugung pro Jahr: {yearly_energy:.2f} GWh")
        specific_yield = (yearly_energy * 1e6) / (rated_power_solar / 1000)  # kWh/kWp
        st.write(f"kWh/kWp: {specific_yield:.2f} kWh/kWp/a")

        # Create figures for energy generation
        # Yearly profile
        fig1 = plt.figure(figsize=(10, 6))
        plt.plot(results_ac.index, results_ac.values)
        plt.title('Stromproduktion der Solaranlagen im Jahresverlauf (W)')
        plt.xlabel('2024')
        plt.ylabel('Leistung (W)')
        plt.grid(True)
        st.pyplot(fig1)
        plt.close(fig1)

        # Daily profile (use July 1st as example)
        july_1st = results_ac['2024-07-01']
        fig2 = plt.figure(figsize=(10, 6))
        plt.plot(july_1st.index.hour, july_1st.values)
        plt.title(f'Tägliche Energieerzeugung (Nennleistung: {rated_power_solar/1000:.2f} MW)')
        plt.xlabel('Stunde des Tages')
        plt.ylabel('Leistung (W)')
        plt.grid(True)
        st.pyplot(fig2)
        plt.close(fig2)
    
    _display_map_with_legend(_get_solar_legend_template())


def _display_wind_results(status_box) -> None:
    """Display wind (WEA) simulation results."""
    import plotly.graph_objects as go
    
    # Display wind simulation results first
    if "results_df" in st.session_state and "total_energy" in st.session_state and "rated_power_wind" in st.session_state:
        st.subheader("Kreisinformationen")
        if "lat_center" in st.session_state and "lon_center" in st.session_state:
            st.write(f"Kreiszentrum (Längengrad, Breitengrad): [{st.session_state['lon_center']:.6f}, {st.session_state['lat_center']:.6f}]")
        if "radius_meters" in st.session_state:
            st.write(f"Kreisradius: {st.session_state['radius_meters']:.2f} meter")
        
        st.subheader("Simulationsergebnisse")
        st.write(f"Anzahl von Windturbinen: {st.session_state['num_turbines']}")
        
        total_gwh = st.session_state["total_energy"] / 1000  # Convert MWh to GWh
        st.write(f"Gesamtenergieerzeugung pro Jahr: {total_gwh:.2f} GWh")
        
        # Calculate full load hours
        if st.session_state["rated_power_wind"] > 0:
            full_load_hours = (st.session_state["total_energy"] * 1000) / st.session_state["rated_power_wind"]
            st.write(f"Volllaststunden: {full_load_hours:.2f} h")
        
        # Create monthly power generation chart
        st.write("Stromproduktion der Windturbinen im Jahresverlauf (MW)")
        results_df = st.session_state["results_df"]
        if not results_df.empty:
            monthly_power = results_df["power_output_MW"].groupby(results_df.index.month).mean()
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=month_names[:len(monthly_power)],
                y=monthly_power.values,
                mode='lines+markers',
                name='Wind Power',
                line=dict(color='blue', width=2)
            ))
            fig.update_layout(
                xaxis_title='Month',
                yaxis_title='Power (MW)',
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Karte mit Windturbinen")
    status_box.info("🗺️ Karte mit Windturbinen erstellen...")
    _display_map_with_legend(_get_wind_legend_template())


def _display_hybrid_results(status_box) -> None:
    """Display hybrid (FFPV + WEA) simulation results."""
    st.subheader("Karte mit Solarmodulen und Windturbinen")
    status_box.info("🗺️ Karte mit Windturbinen erstellen...")
    _display_map_with_legend(_get_hybrid_legend_template(), height=1000)


def _display_map_with_legend(legend_template: str, height: int = 700) -> None:
    """Display the map with HTML legend overlay."""
    map_with_legend = f"""
        <style>
            .map-wrapper {{
                margin: 0;
                padding: 0;
                width: 700px;
                height: 500px;
            }}

            .map-wrapper iframe {{
                width: 700px !important;
                height: 500px !important;
                margin: 0 !important;
                padding: 0 !important;
                border: none !important;
                display: block;
                position: relative;
            }}
        </style>

        <div class="map-wrapper">
            {st.session_state["second_map_html"]}
            {legend_template}
        </div>
    """
    html(map_with_legend, height=height)


def _get_solar_legend_template() -> str:
    """Get HTML template for solar obstacle legend."""
    return """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap');

            .legend-container {
                position: absolute;
                top: 520px;
                left: 0px;
                width: 700px;
                padding: 10px;
            }
                
            .legend-box {
                font-family: 'Source Sans Pro', sans-serif;
                font-size: 16px;
                color: rgb(0, 0, 0);
            }
            .legend-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 8px 15px;
                margin-top: 10px;
            }

            .legend-icon {
                width: 16px;
                height: 16px;
                display: inline-block;
                border: 1px solid white;
                margin-right: 6px;
                vertical-align: middle;
                border-radius: 2px;
            }
        </style>

        <div class="legend-container">
            <div class="legend-box">
                <strong>Hindernis-Legende</strong>
                <div class="legend-grid">
                    <div><i style="background: gray;" class="legend-icon"></i> Verkehr</div>
                    <div><i style="background: green;" class="legend-icon"></i> Landnutzung</div>
                    <div><i style="background: red;" class="legend-icon"></i> Gebäude</div>
                    <div><i style="background: blue;" class="legend-icon"></i> Gewässer</div>
                    <div><i style="background: purple;" class="legend-icon"></i> Schutzgebiet</div>
                    <div><i style="background: orange;" class="legend-icon"></i> Stromleitung</div>
                </div>
            </div>
        </div>
    """


def _get_wind_legend_template() -> str:
    """Get HTML template for wind obstacle legend."""
    return """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap');

            .legend-container {
                position: absolute;
                top: 520px;
                color: rgb(0, 0, 0);
                left: 0px;
                width: 700px;
                padding: 10px;
            }
                
            .legend-box {
                font-family: 'Source Sans Pro', sans-serif;
                font-size: 16px;
                color: rgb(0, 0, 0);
            }
            .legend-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 8px 15px;
                margin-top: 10px;
            }

            .legend-icon {
                width: 16px;
                height: 16px;
                display: inline-block;
                border: 1px solid white;
                margin-right: 6px;
                vertical-align: middle;
                border-radius: 2px;
            }
        </style>

        <div class="legend-container">
            <div class="legend-box">
                <strong>Hindernis-Legende</strong>
                <div class="legend-grid">
                    <div><i style="background: rgb(128, 128, 128);" class="legend-icon"></i> Verkehr</div>
                    <div><i style="background: rgb(34, 139, 34);" class="legend-icon"></i> Landnutzung</div>
                    <div><i style="background: rgb(220, 20, 60);" class="legend-icon"></i> Infrastruktur</div>
                    <div><i style="background: rgb(255, 140, 0);" class="legend-icon"></i> Militär</div>
                    <div><i style="background: rgb(128, 0, 128);" class="legend-icon"></i> Artenschutz</div>
                    <div><i style="background: rgb(30, 144, 255);" class="legend-icon"></i> Natur & Landschaft</div>
                    <div><i style="background: rgb(107, 142, 35);" class="legend-icon"></i> Wald</div>
                    <div><i style="background: rgb(32, 178, 170);" class="legend-icon"></i> Gewässer</div>
                    <div><i style="background: rgb(139, 69, 19);" class="legend-icon"></i> Sonstiges</div>
                </div>
            </div>
        </div>
    """


def _get_hybrid_legend_template() -> str:
    """Get HTML template for hybrid solar+wind obstacle legend."""
    return """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro&display=swap');

            .legend-container {
                position: relative;
                margin-top: 100px;
                width: 700px;
                padding: 10px;
                background: none;
                color: rgb(0, 0, 0);
            }
                
            .legend-box {
                font-family: 'Source Sans Pro', sans-serif;
                font-size: 16px;
                color: rgb(0, 0, 0);
                margin-bottom: 30px;
            }
            .legend-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 8px 15px;
                margin-top: 10px;
            }

            .legend-icon {
                width: 16px;
                height: 16px;
                display: inline-block;
                border: 1px solid white;
                margin-right: 6px;
                vertical-align: middle;
                border-radius: 2px;
            }
        </style>

        <div class="legend-container">
            <div class="legend-box">
                <div class="legend-title">Hindernisse-Legende für Solar ☀️</div>
                <div class="legend-grid">
                    <div><i style="background: gray;" class="legend-icon"></i> Verkehr</div>
                    <div><i style="background: green;" class="legend-icon"></i> Landnutzung</div>
                    <div><i style="background: red;" class="legend-icon"></i> Gebäude</div>
                    <div><i style="background: blue;" class="legend-icon"></i> Gewässer</div>
                    <div><i style="background: purple;" class="legend-icon"></i> Schutzgebiet</div>
                    <div><i style="background: orange;" class="legend-icon"></i> Stromleitung</div>
                    <div><i style="background: #FF00FF;" class="legend-icon"></i> Zufahrtswege</div>
                    <div><i style="background: #8B4513;" class="legend-icon"></i> Kranstellplätze</div>
                </div>
            </div>

            <div class="legend-box">
                <div class="legend-title">Hindernisse-Legende für Wind 💨</div>
                <div class="legend-grid">
                    <div><i style="background: rgb(128, 128, 128);" class="legend-icon"></i> Verkehr</div>
                    <div><i style="background: rgb(34, 139, 34);" class="legend-icon"></i> Landnutzung</div>
                    <div><i style="background: rgb(220, 20, 60);" class="legend-icon"></i> Infrastruktur</div>
                    <div><i style="background: rgb(255, 140, 0);" class="legend-icon"></i> Militär</div>
                    <div><i style="background: rgb(128, 0, 128);" class="legend-icon"></i> Artenschutz</div>
                    <div><i style="background: rgb(30, 144, 255);" class="legend-icon"></i> Natur & Landschaft</div>
                    <div><i style="background: rgb(107, 142, 35);" class="legend-icon"></i> Wald</div>
                    <div><i style="background: rgb(32, 178, 170);" class="legend-icon"></i> Gewässer</div>
                    <div><i style="background: rgb(139, 69, 19);" class="legend-icon"></i> Sonstiges</div>
                </div>
            </div>
        </div>
    """
