"""
Wind installation MaStR dashboard page.

Visualizes wind installations from German MaStR database with interactive maps.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import plotly.express as px
from src.mastr.preprocessing import get_unique_wind_locations, prepare_wind_data
from src.config import MASTR_DB_PATH


def wind_installation_mastr() -> None:
    """Display and visualize wind installations from MaStR database."""
    st.title("Wind Installations Dashboard")
    
    # Fetch unique locations for dropdown
    unique_locations = get_unique_wind_locations(mastr_db_path=str(MASTR_DB_PATH))

    # Dropdown for location selection
    location = st.selectbox("Select city", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)

    # Button to trigger visualization
    if st.button("Visualize"):
        if location:
            # Get data 
            with st.spinner("Loading data..."):
                gdf_wind, city_district = prepare_wind_data(location=location, mastr_db_path=str(MASTR_DB_PATH))

            # Create scatter map
            fig = px.scatter_mapbox(
                gdf_wind,
                lat='Breitengrad',
                lon='Laengengrad',
                size_max=15,
                color_discrete_sequence=['brown'],
                zoom=10,
                center={"lat": city_district.lat.item(),  
                        "lon": city_district.lon.item()},
                mapbox_style='open-street-map',
                hover_data=['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung'],
            )

            # Create choropleth map
            choropleth = px.choropleth_mapbox(
                city_district,
                geojson=city_district.geometry,
                locations=city_district.index,
                color=None,
                opacity=0.3,
                labels={location: 'City District'},
            )

            # Add choropleth trace to the figure
            fig.add_trace(choropleth.data[0])

            # Move the choropleth trace to the background
            fig.data = fig.data[::-1]

            # Update layout
            fig.update_layout(
                margin={"r":0, "t":0, "l":0, "b":0},
            )

            # Display the plot in Streamlit
            st.plotly_chart(fig, use_container_width=True)
            
            # Display DataFrame below map
            st.subheader("Plotted Wind Installations")
            st.dataframe(
                gdf_wind[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad']]
                )
        else:
            st.warning("Please enter a city name.")
