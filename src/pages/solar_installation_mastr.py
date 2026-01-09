"""
Solar installation MaStR dashboard page.

Visualizes solar installations from German MaStR database with interactive maps.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
import plotly.express as px
from src.data_layer.cache import get_cached_unique_locations, get_cached_mastr_data, create_cached_scatter_map
from src.config import MASTR_DB_PATH


def solar_installation_mastr() -> None:
    """Display and visualize solar installations from MaStR database."""
    st.title("☀️ Solar Installations Dashboard")
    
    st.markdown("""
    **Explore solar installations from the German MaStR (Market Master Data Register)**
    
    This dashboard visualizes real solar power installations registered in Germany, 
    showing their locations, capacity, and technical specifications.
    """)

    # Enhanced error handling for database operations with caching
    try:
        with st.spinner("🔄 Loading available locations from database..."):
            unique_locations = get_cached_unique_locations("solar", str(MASTR_DB_PATH))
        
        if not unique_locations:
            st.error("❌ No locations available in the database")
            st.info("💡 Please check if the MaStR database file exists and contains data.")
            return
            
    except Exception as e:
        st.error("🗄️ **Database Connection Error**")
        st.error("Unable to load location data from the MaStR database.")
        
        with st.expander("🔧 **Troubleshooting Steps**"):
            st.markdown("""
            1. **Check database file**: Ensure `data/open-mastr.db` exists
            2. **Verify file permissions**: Make sure the database file is readable
            3. **Database integrity**: The database file may be corrupted
            4. **Restart application**: Try refreshing the page
            """)
        
        with st.expander("🔍 **Technical Details**"):
            st.code(str(e))
        return

    # Input validation for location selection
    st.markdown("### 📍 **Location Selection**")
    location = st.selectbox(
        "Select city", 
        options=unique_locations, 
        index=unique_locations.index("Essen") if "Essen" in unique_locations else 0,
        help="Choose a city to visualize its solar installations"
    )
    
    # Validate location selection
    if not location:
        st.warning("⚠️ Please select a location from the dropdown")
        return
    
    if location not in unique_locations:
        st.error(f"❌ Selected location '{location}' is not available in the database")
        return

    # Enhanced visualization button with progress tracking
    if st.button("🗺️ Visualize Solar Installations", key="visualize_solar"):
        if location:
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Load data with caching
                status_text.text("🔄 Loading solar installation data...")
                progress_bar.progress(20)
                
                gdf_solar, city_district = get_cached_mastr_data(location, "solar", str(MASTR_DB_PATH))
                
                # Validate loaded data
                if gdf_solar is None or len(gdf_solar) == 0:
                    st.error(f"❌ No solar installations found for {location}")
                    st.info("💡 Try selecting a different location or check if the database contains data for this city.")
                    return
                
                progress_bar.progress(40)
                status_text.text("🗺️ Creating interactive map...")
                
                # Step 2: Create visualization with caching
                fig = create_cached_scatter_map(
                    gdf_solar,
                    lat_col='Breitengrad',
                    lon_col='Laengengrad',
                    hover_data=['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung'],
                    center_lat=city_district.lat.item(),
                    center_lon=city_district.lon.item(),
                    color='red',
                    title=f"Solar Installations in {location}"
                )
                
                progress_bar.progress(60)
                status_text.text("🏘️ Adding district boundaries...")

                # Step 3: Create choropleth map with error handling
                try:
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
                    
                except Exception as choropleth_error:
                    st.warning("⚠️ Could not load district boundaries, showing installations only")
                    st.write("District boundary error:", str(choropleth_error))
                
                progress_bar.progress(80)
                status_text.text("📊 Generating statistics...")
                
                # Step 4: Calculate and display statistics
                total_installations = len(gdf_solar)
                total_capacity_brutto = gdf_solar['Bruttoleistung'].sum() / 1000  # Convert to MW
                total_capacity_netto = gdf_solar['Nettonennleistung'].sum() / 1000  # Convert to MW
                avg_capacity = gdf_solar['Bruttoleistung'].mean()
                
                progress_bar.progress(100)
                status_text.text("✅ Visualization complete!")
                
                # Display results
                st.success(f"✅ Successfully loaded {total_installations} solar installations for {location}")
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Installations", f"{total_installations:,}")
                with col2:
                    st.metric("Total Capacity (Gross)", f"{total_capacity_brutto:.1f} MW")
                with col3:
                    st.metric("Total Capacity (Net)", f"{total_capacity_netto:.1f} MW")
                with col4:
                    st.metric("Average Capacity", f"{avg_capacity:.1f} kW")
                
                # Display the map
                st.plotly_chart(fig, use_container_width=True)
                
                # Additional data insights
                with st.expander("📊 **Detailed Statistics**"):
                    st.subheader("Capacity Distribution")
                    capacity_hist = px.histogram(
                        gdf_solar, 
                        x='Bruttoleistung',
                        nbins=20,
                        title="Distribution of Solar Installation Capacities",
                        labels={'Bruttoleistung': 'Gross Capacity (kW)', 'count': 'Number of Installations'}
                    )
                    st.plotly_chart(capacity_hist, use_container_width=True)
                    
                    st.subheader("Installation Details")
                    st.dataframe(
                        gdf_solar[['NameStromerzeugungseinheit', 'Bruttoleistung', 'Nettonennleistung', 'Breitengrad', 'Laengengrad']].head(10),
                        use_container_width=True
                    )
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
            except Exception as e:
                st.error("❌ **Visualization Failed**")
                st.error(f"An error occurred while creating the visualization: {str(e)}")
                
                with st.expander("🔧 **Troubleshooting Steps**"):
                    st.markdown("""
                    1. **Check location data**: Verify the selected location has solar installations
                    2. **Database connectivity**: Ensure the MaStR database is accessible
                    3. **Data integrity**: The location data may be corrupted
                    4. **Try another location**: Some cities may have incomplete data
                    """)
                
                with st.expander("🔍 **Technical Details**"):
                    st.code(str(e))
                
                # Clear progress indicators on error
                progress_bar.empty()
                status_text.empty()
    
    # Information panel
    with st.expander("ℹ️ **About This Dashboard**"):
        st.markdown("""
        **Data Source**: German Market Master Data Register (MaStR)
        
        **What you can see**:
        - 📍 Exact locations of registered solar installations
        - ⚡ Power capacity (gross and net) for each installation
        - 🏘️ District boundaries and administrative divisions
        - 📊 Statistical distribution of installation sizes
        
        **Technical Notes**:
        - Red dots represent individual solar installations
        - Hover over installations to see detailed information
        - District boundaries show administrative divisions
        - Capacity values are from official registry data
        """)
