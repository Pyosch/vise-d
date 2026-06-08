"""
Storage installation MaStR dashboard page.

Visualizes storage installations from German MaStR database with interactive maps.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import pandas as pd
import streamlit as st
import plotly.express as px
from src.mastr.preprocessing import get_unique_storage_locations, prepare_storage_data
from src.config import MASTR_DB_PATH


def storage_installation_mastr() -> None:
    """Display and visualize storage installations from MaStR database."""
    st.title("🔌 Speicheranlagen")
    from src.content.page_descriptions import render_page_description
    render_page_description("storage_mastr")

    # Fetch unique locations for dropdown
    unique_locations = get_unique_storage_locations(mastr_db_path=str(MASTR_DB_PATH))

    # Dropdown for location selection
    location = st.selectbox("Stadt", options=unique_locations, index=unique_locations.index("Essen") if "Essen" in unique_locations else 0)

    # Button to trigger visualization
    if st.button("Anlagen anzeigen"):
        if location:
            # Get data from mastr_main
            with st.spinner("Daten werden geladen…"):
                gdf_storage, city_district = prepare_storage_data(location=location, mastr_db_path=str(MASTR_DB_PATH))

            # Create scatter map
            fig = px.scatter_mapbox(
                gdf_storage,
                lat='Breitengrad',
                lon='Laengengrad',
                size_max=15,
                color_discrete_sequence=['purple'],
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
                labels={location: 'Stadtteil'},
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
            
            # Display the filtered data as a DataFrame and Pie Chart side by side
            st.subheader("Dargestellte Speicheranlagen")
            
            # Display DataFrame
            st.dataframe(
                    gdf_storage[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad', 'Ort']]
                )

            # Create Pie Chart for Operating Status Distribution
            tech_counts = gdf_storage['EinheitBetriebsstatus'].value_counts()
            pie_fig = px.pie(
                    values=tech_counts.values,
                    names=tech_counts.index,
                    title="Verteilung nach Betriebsstatus",
                    hole=0.3  # Optional: Make it a donut chart for aesthetics
                )
            pie_fig.update_layout(
                    margin={"r":0, "t":0, "l":0, "b":0},  # Adjust margins for compact display
                    height=300  # Set height to align with DataFrame
                )
            st.plotly_chart(pie_fig, use_container_width=True)
            
            st.subheader("Balkendiagramm der Speicheranlagen")
            # Define bins and sort them
            bins = [0, 50, 200, 1000, gdf_storage['Nettonennleistung'].max()]
            bins = sorted(bins)  # Ensure increasing order for pd.cut internally
            labels = ['<50 kW', '50–200 kW', '200–1000 kW', '>1000 kW']

            # Create a temporary column with binned data
            gdf_storage['Capacity_Range'] = pd.cut(gdf_storage['Nettonennleistung'], bins=bins, labels=labels, ordered=False)

            # Plot bar chart using value counts
            capacity_fig = px.bar(
                gdf_storage['Capacity_Range'].value_counts(),
                labels={'index': 'Leistungsklasse', 'value': 'Anzahl Anlagen'},
                title="Speicheranlagen nach Nettoleistungsklasse"
            )

            st.plotly_chart(capacity_fig, use_container_width=True)

        else:
            st.warning("Bitte eine Stadt auswählen.")
