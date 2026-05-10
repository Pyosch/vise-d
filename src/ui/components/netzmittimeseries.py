import streamlit as st
import pandas as pd
import pandapower as pn
import pandapower.networks as ppn
from pandapower.timeseries import DFData
from pandapower.control import ConstControl
from src.utils.simbench_profiles import Simbench_multiplier
import numpy as np
import plotly.graph_objects as go
import webbrowser

# PVlib imports for normalized 1kWp PV model
from pvlib import pvsystem, modelchain, location
from pvlib.irradiance import disc
from src.data_layer.weather_integration import fetch_weather_for_pv


def get_normalized_pv_output(lat, lon, start_date, end_date):
    """
    Create a one-day timeseries for a normalized 1kWp PV system using PVlib + DWD data.
    Returns a pandas Series in kW at 15-minute resolution for exactly one day.
    """
    tz = 'Europe/Berlin'
    day_start = pd.Timestamp(start_date)
    if day_start.tzinfo is None:
        day_start = day_start.tz_localize(tz)
    else:
        day_start = day_start.tz_convert(tz)
    day_start = day_start.normalize()
    day_end = day_start + pd.Timedelta(days=1)

    # --- 1. Normalized 1kWp Reference System ---
    array_kwargs = dict(
        module_parameters=dict(pdc0=1000, gamma_pdc=-0.004),
        temperature_model_parameters=dict(a=-3.56, b=-0.075, deltaT=3)
    )
    arrays = [pvsystem.Array(pvsystem.FixedMount(30, 180), **array_kwargs)]

    loc = location.Location(lat, lon, tz=tz)
    system = pvsystem.PVSystem(arrays=arrays, inverter_parameters=dict(pdc0=1000))
    mc = modelchain.ModelChain(system, loc, aoi_model='physical', spectral_model='no_loss')

    # --- 2. Fetch Weather Data via project integration (same pipeline as PV configuration) ---
    weather, _ = fetch_weather_for_pv(
        latitude=float(lat),
        longitude=float(lon),
        start_date=day_start.tz_localize(None),
        end_date=day_end.tz_localize(None),
        resolution="15min"
    )
    if weather.empty:
        raise ValueError("No weather data available for requested date/location.")

    weather.index = pd.DatetimeIndex(weather.index)
    if weather.index.tz is None:
        weather.index = weather.index.tz_localize(tz)
    else:
        weather.index = weather.index.tz_convert(tz)
    weather = weather.sort_index()

    # Keep exactly one day and align to a fixed 15-min profile index.
    weather = weather[(weather.index >= day_start) & (weather.index < day_end)]
    if weather.empty:
        raise ValueError("No weather rows remain after filtering to the selected day.")

    target_index = pd.date_range(start=day_start, end=day_end, freq='15min', inclusive='left', tz=tz)
    weather = weather.reindex(target_index).interpolate(method='time').ffill().bfill()

    required_cols = ['temp_air', 'ghi', 'wind_speed']
    missing_required = [c for c in required_cols if c not in weather.columns]
    if missing_required:
        raise ValueError(f"Missing required weather columns for PV model: {missing_required}")

    if 'dni' not in weather.columns or 'dhi' not in weather.columns:
        solar_position = loc.get_solarposition(weather.index)
        weather['dni'] = disc(weather['ghi'], solar_position['zenith'], weather.index)['dni']
        weather['dhi'] = (weather['ghi'] - weather['dni'] * np.cos(np.radians(solar_position['zenith']))).clip(lower=0)
    weather = weather.dropna(subset=['temp_air', 'ghi', 'wind_speed', 'dni', 'dhi'])

    # --- 3. Run Model ---
    mc.run_model(weather)

    # --- 4. 1kWp Output Timeseries (kW) ---
    pv_1kw_timeseries = (mc.results.ac / 1000)
    pv_1kw_timeseries = pv_1kw_timeseries.reindex(target_index, fill_value=0.0)

    return pv_1kw_timeseries


def _get_pv_config_location_data():
    """Return (lat, lon, day_start) strictly from PV configuration selection summary."""
    pv_loc = st.session_state.get("pv_location_data")
    if not isinstance(pv_loc, dict):
        return None, None, None

    lat = pv_loc.get("latitude")
    lon = pv_loc.get("longitude")
    day_start = pv_loc.get("start_date")

    if day_start is None:
        day_start = pd.Timestamp.now(tz='Europe/Berlin').normalize()

    return lat, lon, day_start

def netzmittimeseries():
    st.markdown("### 📚 Choose One of the Pre-defined networks")
    networks = [
                    'Keine Auswahl', 
                    'Einfaches Beispiel', 
                    'Multispannungs-Beispielnetz', 
                    '4-Knoten-Stichleitung', 
                    'CIGRE Niederspannungsnetz',
                    'Kerber Freileitung 1',
                    'Dickert LV Networks',
                    '3-Phase Grid Data',
                    "MV-Oberrhein"
                ]
    selected_network = st.selectbox('Netzwerk wählen:', networks)
                
    if selected_network != 'Keine Auswahl':
                    # Load or reload selected network
                    if 'network' not in st.session_state or st.button("🔄 Reload Selected Network") or st.session_state.get('last_selected_network') != selected_network:
                        if selected_network == 'Einfaches Beispiel':
                            net = ppn.example_simple()
                        elif selected_network == 'Multispannungs-Beispielnetz':
                            net = ppn.example_multivoltage()
                        elif selected_network == '4-Knoten-Stichleitung':
                            net = ppn.panda_four_load_branch()
                        elif selected_network == 'CIGRE Niederspannungsnetz':
                            net = ppn.create_cigre_network_mv()
                        elif selected_network == 'Kerber Freileitung 1':
                            net = ppn.create_kerber_landnetz_freileitung_1()
                        elif selected_network == 'Dickert LV Networks':
                            net = ppn.create_dickert_lv_network()
                        elif selected_network == '3-Phase Grid Data':
                            net = ppn.ieee_european_lv_asymmetric()
                        elif selected_network == "MV-Oberrhein":
                            net = ppn.mv_oberrhein()
                        st.session_state.network = net
                        st.session_state.last_selected_network = selected_network
                        st.success(f"✅ Network '{selected_network}' loaded!")
                    else:
                        net = st.session_state.network
                        st.info("Using network from session (with any added PV/Storage)")
                    
                    # Display network graph (moved outside if-else to always show)
                    # Temporarily disable browser opening
                    original_open = webbrowser.open
                    webbrowser.open = lambda *args, **kwargs: None
                    
                    try:
                        fig = pn.plotting.plotly.simple_plotly(net)
                    finally:
                        webbrowser.open = original_open
                    
                    # Remove legend completely and save figure to session state for Tab 1
                    for trace in fig.data:
                        trace.showlegend = False
                    fig.update_layout(
                        showlegend=False,
                        annotations=[],
                        margin=dict(l=0, r=0, t=0, b=0)
                    )
                    st.session_state.network_fig_json = fig.to_json()
                    st.plotly_chart(fig, use_container_width=True, height=800)
    else:
                    st.info("👆 Please select a network from the dropdown above")
                    net = None

                    
                # Continue with network operations if network is loaded
    if net is not None:
                    st.markdown("### DER Input (Direct Power Entry)")
                    st.caption("PV and storage are currently added directly by total power in this tab.")

                    
                    with st.expander("Add PV Generator"):
                        PV_name = st.text_input("PV Generator Name", value="PV")
                        selected_bus_pv = st.selectbox("Select bus for PV", net.bus.index.tolist(), key="pv_bus_select")
                        total_pv_power_kw = st.number_input(
                            "Total PV generator power (kW)",
                            min_value=0.0,
                            value=10.0,
                            step=1.0,
                            key="pv_total_power_kw"
                        )
                        
                        
                        if st.button("Add PV Generator"):
                            if total_pv_power_kw <= 0:
                                st.warning("Please enter a PV power greater than 0 kW.")
                            else:
                                pn.create_sgen(
                                    net,
                                    bus=selected_bus_pv,
                                    p_mw=total_pv_power_kw / 1000,
                                    q_mvar=0,
                                    name=PV_name
                                )
                                st.session_state.network = net
                                st.success(f"PV generator {PV_name} ({total_pv_power_kw:.2f} kW) added to bus {selected_bus_pv}.")

                    
                    with st.expander("Add Storage"):
                        storage_name = st.text_input("Storage Name", value="Storage")
                        selected_bus_storage = st.selectbox("Select bus for storage", net.bus.index.tolist(), key="storage_bus_select")
                        storage_power_kw = st.number_input(
                            "Total storage power (kW)",
                            min_value=0.0,
                            value=10.0,
                            step=1.0,
                            key="storage_total_power_kw"
                        )
                        storage_mode = st.radio("Operating mode", ["Charging", "Discharging", "Off"])
                        
                        

                        if st.button("Add Storage"):
                            if storage_power_kw <= 0:
                                st.warning("Please enter a storage power greater than 0 kW.")
                            else:
                                if storage_mode == "Charging":
                                    p_mw = -storage_power_kw / 1000
                                elif storage_mode == "Discharging":
                                    p_mw = storage_power_kw / 1000
                                else:
                                    p_mw = 0

                                pn.create_storage(
                                    net,
                                    bus=selected_bus_storage,
                                    p_mw=p_mw,
                                    max_e_mwh=storage_power_kw / 1000 * 24,
                                    q_mvar=0,
                                    soc_percent=50,
                                    name=storage_name
                                )
                                st.session_state.network = net
                                st.success(f"Storage {storage_name} ({storage_power_kw:.2f} kW, {storage_mode}) added to bus {selected_bus_storage}.")

                    with st.expander("Add Electric Vehicle"):
                        EV_name = st.text_input("EV Load Name", value="EV")
                        selected_bus_ev = st.selectbox("Select bus for EV", net.bus.index.tolist(), key="ev_bus_select")
                        total_ev_power_kw = st.number_input(
                            "Total EV load power (kW)",
                            min_value=0.0,
                            value=11.0,
                            step=1.0,
                            key="ev_total_power_kw"
                        )

                        
                        
                        if st.button("Add Electric Vehicle"):
                            if total_ev_power_kw <= 0:
                                st.warning("Please enter an EV load power greater than 0 kW.")
                            else:
                                pn.create_load(
                                    net,
                                    bus=selected_bus_ev,
                                    p_mw=total_ev_power_kw / 1000,
                                    q_mvar=0,
                                    name=EV_name
                                )
                                st.session_state.network = net
                                st.success(f"EV load {EV_name} ({total_ev_power_kw:.2f} kW) added to bus {selected_bus_ev}.")

                    with st.expander("Heat Pump"):
                        heat_pump_name = st.text_input("Heat Pump Name", value="Heat_Pump")
                        selected_bus_single_port = st.selectbox("Select bus for Heat Pump", net.bus.index.tolist(), key="Heat_Pump_bus_select")
                        heat_pump_power_kw = st.number_input(
                            "Total Heat Pump power (kW)",
                            min_value=0.0,
                            value=7.0,
                            step=1.0,
                            key="Heat_Pump__power_kw"
                        )

                        
                        if st.button("Add Heat Pump"):
                        
                                pn.create_load(
                                    net,
                                    bus=selected_bus_single_port,
                                    p_mw=heat_pump_power_kw / 1000,
                                    q_mvar=0,
                                    name=heat_pump_name
                                )
                                st.session_state.network = net
                                st.success(f"Heat Pump {heat_pump_name} ({heat_pump_power_kw:.2f} kW) added to bus {selected_bus_single_port}.")                        

    if net is None:
        return

    st.markdown("---")

    st.markdown("### 📋 Network Components")
    st.markdown("Click on any component below to view its details:")

    with st.expander("🔵 **Buses**"):
        if len(net.bus) > 0:
            st.dataframe(net.bus, use_container_width=True)
        else:
            st.info("No buses in the network")

    with st.expander("⚡ **Lines**"):
        if len(net.line) > 0:
            st.dataframe(net.line, use_container_width=True)
        else:
            st.info("No lines in the network")

    with st.expander("🔌 **Loads**"):
        if len(net.load) > 0:
            st.dataframe(net.load, use_container_width=True)
        else:
            st.info("No loads in the network")

    with st.expander("🔄 **Transformers**"):
        if 'trafo' in net and len(net.trafo) > 0:
            st.dataframe(net.trafo, use_container_width=True)
        else:
            st.info("No transformers in the network")

    with st.expander("⚙️ **Generators**"):
        if 'sgen' in net and len(net.sgen) > 0:
            st.dataframe(net.sgen, use_container_width=True)
        else:
            st.info("No generators in the network")

    with st.expander("🔋 **Storage**"):
        if 'storage' in net and len(net.storage) > 0:
            st.dataframe(net.storage, use_container_width=True)
        else:
            st.info("No storage devices in the network")

    # Check geodata status
    has_geodata = hasattr(net, 'bus_geodata') and len(net.bus_geodata) > 0
    if has_geodata:
        st.success(f"✅ Network has {len(net.bus_geodata)} buses with geographic coordinates")
    else:
        st.info("📍 Bus coordinates will be auto-generated for visualization (grid layout)")

    st.markdown("---")

    # 5. Run Power Flow
    if st.button("Run Power Flow"):
        try:
            pn.runpp(net)
            st.session_state.power_flow_ran = True
            st.session_state.network = net
            st.success("✅ Power flow calculation completed!")

            # Create tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Network Visualization", "🔌 Bus Results", "⚡ Line Results", "🔋 DER Results"])

            with tab1:
                st.subheader("Interactive Network Diagram")
                try:
                    if 'network_fig_json' in st.session_state:
                        import plotly.io as pio
                        tab_fig = pio.from_json(st.session_state.network_fig_json)
                        tab_fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0))
                        st.plotly_chart(tab_fig, use_container_width=True)
                    else:
                        st.info("Network diagram not available. Please re-select the network.")

                    # Network Status Overview
                    st.markdown("### 📊 Network Status Overview")
                    col_status1, col_status2, col_status3 = st.columns(3)

                    with col_status1:
                        st.markdown("**Bus Voltage Status:**")
                        voltage_low = (net.res_bus['vm_pu'] < 0.95).sum()
                        voltage_high = (net.res_bus['vm_pu'] > 1.05).sum()
                        voltage_ok = len(net.res_bus) - voltage_low - voltage_high

                        if voltage_low > 0:
                            st.error(f"🔴 {voltage_low} bus(es) with undervoltage (<0.95 p.u.)")
                        if voltage_high > 0:
                            st.warning(f"🟠 {voltage_high} bus(es) with overvoltage (>1.05 p.u.)")
                        if voltage_ok == len(net.res_bus):
                            st.success(f"🟢 All {voltage_ok} buses within limits")
                        else:
                            st.info(f"🟢 {voltage_ok} bus(es) within limits")

                    with col_status2:
                        st.markdown("**Line Loading Status:**")
                        if len(net.res_line) > 0:
                            line_overload = (net.res_line['loading_percent'] > 100).sum()
                            line_high = ((net.res_line['loading_percent'] > 80) & (net.res_line['loading_percent'] <= 100)).sum()
                            line_ok = len(net.res_line) - line_overload - line_high

                            if line_overload > 0:
                                st.error(f"🔴 {line_overload} line(s) overloaded (>100%)")
                            if line_high > 0:
                                st.warning(f"🟠 {line_high} line(s) highly loaded (>80%)")
                            if line_ok == len(net.res_line):
                                st.success(f"🟢 All {line_ok} lines within limits")
                            else:
                                st.info(f"🟢 {line_ok} line(s) within limits")
                        else:
                            st.info("No lines in network")

                    with col_status3:
                        st.markdown("**Transformer Status:**")
                        if 'trafo' in net and 'res_trafo' in net and len(net.res_trafo) > 0:
                            trafo_overload = (net.res_trafo['loading_percent'] > 100).sum()
                            trafo_high = ((net.res_trafo['loading_percent'] > 80) & (net.res_trafo['loading_percent'] <= 100)).sum()
                            trafo_ok = len(net.res_trafo) - trafo_overload - trafo_high

                            if trafo_overload > 0:
                                st.error(f"🔴 {trafo_overload} trafo(s) overloaded (>100%)")
                            if trafo_high > 0:
                                st.warning(f"🟠 {trafo_high} trafo(s) highly loaded (>80%)")
                            if trafo_ok == len(net.res_trafo):
                                st.success(f"🟢 All {trafo_ok} trafos within limits")
                            else:
                                st.info(f"🟢 {trafo_ok} trafo(s) within limits")
                        else:
                            st.info("No transformers in network")

                except Exception as e:
                    st.warning(f"Could not create network plot: {e}")
                    st.info("Tip: Some networks may not have bus coordinates (geodata) for plotting. The network will still run correctly.")

                # Summary metrics
                st.markdown("### 📈 Summary Metrics")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    min_voltage = net.res_bus['vm_pu'].min()
                    st.metric("Min Voltage", f"{min_voltage:.4f} p.u.", delta=f"{(min_voltage-1)*100:.2f}%", delta_color="inverse")

                with col2:
                    max_voltage = net.res_bus['vm_pu'].max()
                    st.metric("Max Voltage", f"{max_voltage:.4f} p.u.", delta=f"{(max_voltage-1)*100:.2f}%", delta_color="normal" if max_voltage > 1 else "inverse")

                with col3:
                    max_loading = net.res_line['loading_percent'].max() if len(net.res_line) > 0 else 0
                    st.metric("Max Line Loading", f"{max_loading:.2f}%", delta="Overload!" if max_loading > 100 else "OK", delta_color="inverse" if max_loading > 100 else "normal")

                with col4:
                    total_loss = net.res_line['pl_mw'].sum() if len(net.res_line) > 0 else 0
                    st.metric("Total Losses", f"{total_loss*1000:.2f} kW")

            with tab2:
                st.subheader("Bus Voltage Results")
                bus_results = net.res_bus.copy()
                bus_results['vm_pu'] = bus_results['vm_pu'].round(4)
                bus_results['va_degree'] = bus_results['va_degree'].round(2)

                st.markdown("#### 📊 Voltage Profile")
                fig_voltage = go.Figure()
                colors = ['red' if v < 0.95 else 'orange' if v > 1.05 else 'green' for v in bus_results['vm_pu']]

                fig_voltage.add_trace(go.Bar(
                    x=bus_results.index,
                    y=bus_results['vm_pu'],
                    marker_color=colors,
                    name='Bus Voltage',
                    text=bus_results['vm_pu'].round(4),
                    textposition='outside',
                    hovertemplate='Bus %{x}<br>Voltage: %{y:.4f} p.u.<extra></extra>'
                ))

                fig_voltage.add_hline(y=1.05, line_dash="dash", line_color="red", annotation_text="Upper Limit (1.05 p.u.)", annotation_position="right")
                fig_voltage.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Lower Limit (0.95 p.u.)", annotation_position="right")
                fig_voltage.add_hline(y=1.0, line_dash="dot", line_color="gray", annotation_text="Nominal (1.0 p.u.)", annotation_position="right")

                fig_voltage.update_layout(
                    xaxis_title="Bus Index",
                    yaxis_title="Voltage (p.u.)",
                    yaxis_range=[0.90, 1.10],
                    height=400,
                    showlegend=False,
                    hovermode='x unified'
                )

                st.plotly_chart(fig_voltage, use_container_width=True)
                st.markdown("#### 📋 Detailed Bus Data")

                def highlight_voltage(row):
                    if row['vm_pu'] < 0.95:
                        return ['background-color: #ffcccc'] * len(row)
                    if row['vm_pu'] > 1.05:
                        return ['background-color: #ffffcc'] * len(row)
                    return ['background-color: #ccffcc'] * len(row)

                styled_bus = bus_results.style.apply(highlight_voltage, axis=1)
                st.dataframe(styled_bus, use_container_width=True)

                voltage_low = bus_results['vm_pu'] < 0.95
                voltage_high = bus_results['vm_pu'] > 1.05
                if voltage_low.any():
                    st.error(f"🚨 Undervoltage at {voltage_low.sum()} bus(es): {bus_results[voltage_low].index.tolist()}")
                if voltage_high.any():
                    st.error(f"🚨 Overvoltage at {voltage_high.sum()} bus(es): {bus_results[voltage_high].index.tolist()}")
                if not voltage_low.any() and not voltage_high.any():
                    st.success("✅ All bus voltages within limits (0.95 - 1.05 p.u.)")

            with tab3:
                st.subheader("Line Loading Results")
                if len(net.res_line) > 0:
                    line_results = net.res_line.copy()
                    line_results['loading_percent'] = line_results['loading_percent'].round(2)
                    line_results['pl_mw'] = line_results['pl_mw'].round(6)

                    st.markdown("#### 📊 Line Loading Profile")
                    fig_loading = go.Figure()
                    colors = ['red' if l > 100 else 'orange' if l > 80 else 'green' for l in line_results['loading_percent']]

                    fig_loading.add_trace(go.Bar(
                        x=line_results.index,
                        y=line_results['loading_percent'],
                        marker_color=colors,
                        name='Line Loading',
                        text=line_results['loading_percent'].round(1),
                        textposition='outside',
                        hovertemplate='Line %{x}<br>Loading: %{y:.2f}%<extra></extra>'
                    ))

                    fig_loading.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Capacity Limit (100%)", annotation_position="right")
                    fig_loading.add_hline(y=80, line_dash="dot", line_color="orange", annotation_text="Warning Level (80%)", annotation_position="right")

                    fig_loading.update_layout(
                        xaxis_title="Line Index",
                        yaxis_title="Loading (%)",
                        height=400,
                        showlegend=False,
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig_loading, use_container_width=True)
                    st.markdown("#### 📋 Detailed Line Data")

                    def highlight_loading(row):
                        if row['loading_percent'] > 100:
                            return ['background-color: #ff6666'] * len(row)
                        if row['loading_percent'] > 80:
                            return ['background-color: #ffff99'] * len(row)
                        return ['background-color: #99ff99'] * len(row)

                    styled_line = line_results.style.apply(highlight_loading, axis=1)
                    st.dataframe(styled_line, use_container_width=True)

                    overloaded = line_results['loading_percent'] > 100
                    if overloaded.any():
                        st.error(f"🚨 {overloaded.sum()} line(s) overloaded: {line_results[overloaded].index.tolist()}")
                    else:
                        st.success("✅ All lines within capacity")
                else:
                    st.info("No line results available")

            with tab4:
                st.subheader("Distributed Energy Resources (DER) Results")

                if 'sgen' in net and len(net.sgen) > 0:
                    st.markdown("#### ☀️ PV Generation")
                    pv_object = st.session_state.get('pv')
                    pv_results = net.res_sgen.copy()
                    pv_results.insert(0, 'bus_no', net.sgen['bus'].values)
                    pv_results['p_kw'] = (pv_results['p_mw'] * 1000)
                    pv_results['q_kvar'] = (pv_results['q_mvar'] * 1000)
                    st.dataframe(pv_results[['bus_no', 'p_mw', 'q_mvar', 'p_kw', 'q_kvar']].reset_index(drop=True), use_container_width=True)

                    total_pv_gen = pv_results['p_mw'].sum() * 1000
                    st.metric("Total PV Generation", f"{total_pv_gen:.2f} kW")
                else:
                    st.info("No PV systems in network")

                # Show scaled normalized PV timeseries from get_normalized_pv_output only.
                pv_ts_error = None
                pv_ts_series = pd.Series(dtype=float)

                pv_cfg = st.session_state.get('pv')
                pv_power_kw = float(st.session_state.get("pv_total_power_kw", 0.0) or 0.0)
                if pv_cfg is None:
                    pv_ts_error = "PV configuration is missing."
                elif pv_power_kw <= 0:
                    pv_ts_error = "PV generator power must be greater than 0 kW."
                else:
                    pv_lat_cfg, pv_lon_cfg, pv_day_cfg = _get_pv_config_location_data()
                    if pv_lat_cfg is None or pv_lon_cfg is None:
                        pv_ts_error = "PV configuration coordinates are missing. Please open PV Konfiguration and confirm Auswahl-Zusammenfassung."
                    else:
                        try:
                            pv_ts_scaled_kw = get_normalized_pv_output(
                                lat=pv_lat_cfg,
                                lon=pv_lon_cfg,
                                start_date=pv_day_cfg,
                                end_date=pv_day_cfg + pd.Timedelta(days=1)
                            ) * pv_power_kw
                            pv_ts_series = pd.to_numeric(pd.Series(pv_ts_scaled_kw), errors='coerce').dropna().reset_index(drop=True)
                            st.session_state['ts_pv_scaled_kw'] = pv_ts_series
                        except Exception as e:
                            pv_ts_error = str(e)

                if len(pv_ts_series) > 1:
                    st.markdown("#### 📈 Normalized PV Timeseries (Scaled by Input PV Power)")
                    fig_der_pv_ts = go.Figure()
                    fig_der_pv_ts.add_trace(go.Scatter(
                        x=list(range(len(pv_ts_series))),
                        y=pv_ts_series.values,
                        mode='lines',
                        name='Scaled PV (kW)',
                        line=dict(width=2)
                    ))
                    fig_der_pv_ts.update_layout(
                        xaxis_title="Time Step (15 min)",
                        yaxis_title="PV Power (kW)",
                        height=380,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_der_pv_ts, use_container_width=True)
                else:
                    if pv_ts_error:
                        st.warning(f"Could not generate normalized PV timeseries during power flow: {pv_ts_error}")
                    else:
                        st.info("No scaled normalized PV timeseries available for visualization.")

                st.markdown("---")

                if 'storage' in net and len(net.storage) > 0:
                    st.markdown("#### 🔋 Battery Storage")
                    storage_results = net.res_storage.copy()
                    storage_results.insert(0, 'bus_no', net.storage['bus'].values)
                    storage_results['p_kw'] = (storage_results['p_mw'] * 1000).round(2)
                    st.dataframe(storage_results[['bus_no', 'p_mw', 'q_mvar', 'p_kw']].reset_index(drop=True), use_container_width=True)

                    total_storage_power = storage_results['p_mw'].sum() * 1000
                    if total_storage_power > 0:
                        st.metric("Storage Status", "Discharging", f"{total_storage_power:.2f} kW")
                    elif total_storage_power < 0:
                        st.metric("Storage Status", "Charging", f"{abs(total_storage_power):.2f} kW")
                    else:
                        st.metric("Storage Status", "Idle", "0 kW")
                else:
                    st.info("No storage systems in network")

                st.markdown("---")
                st.markdown("#### ⚖️ Power Balance")
                col_bal1, col_bal2, col_bal3 = st.columns(3)

                total_load = net.load['p_mw'].sum() * 1000 if len(net.load) > 0 else 0
                total_gen = net.res_sgen['p_mw'].sum() * 1000 if 'sgen' in net and len(net.sgen) > 0 else 0
                total_stor = net.res_storage['p_mw'].sum() * 1000 if 'storage' in net and len(net.storage) > 0 else 0

                with col_bal1:
                    st.metric("Total Load", f"{total_load:.2f} kW")
                with col_bal2:
                    st.metric("Total Generation", f"{total_gen:.2f} kW")
                with col_bal3:
                    net_power = total_gen + total_stor - total_load
                    st.metric("Net Power", f"{net_power:.2f} kW")

        except Exception as pf_error:
            st.error(f"❌ Power flow calculation failed: {str(pf_error)}")
            st.exception(pf_error)

    solver_mode = st.radio("Solver Mode",["PF","OPF"],horizontal=True)
    use_opf = solver_mode == "OPF"
    
    if st.button("Update grid models"):
        
        if use_opf:
            st.info("OPF mode selected")

            # Remove an older OPF storage row before creating a fresh one.
            if "name" in net.storage.columns:
                old_opf_idx = net.storage[net.storage["name"] == "OPF_Storage"].index
                if len(old_opf_idx) > 0:
                    net.storage.drop(old_opf_idx, inplace=True)

            opf_storage_bus = 2

            if opf_storage_bus not in net.bus.index:
                st.warning(f"Configured OPF storage bus {opf_storage_bus} is not available in this network.")
                return
            
            opf_storage_idx = pn.create_storage(
                net,
                bus=opf_storage_bus,
                p_mw=0.0,
                max_e_mwh=10.0,
                q_mvar=0.0,
                min_p_mw = -10.0,
                max_p_mw = 10.0,
                min_q_mvar = -10.0,
                max_q_mvar = 10.0,
                soc_percent=50.0,
                controllable=True,
                name="OPF_Storage"
            )
            # Required for OPF feasibility
            net.bus["min_vm_pu"] = 0.95
            net.bus["max_vm_pu"] = 1.05
            net.ext_grid["min_p_mw"] = -9999.0
            net.ext_grid["max_p_mw"] =  9999.0
            net.ext_grid["min_q_mvar"] = -9999.0
            net.ext_grid["max_q_mvar"] =  9999.0
            # Cost pattern: grid is base price, storage is slightly more expensive
            # so it stays idle unless the OPF needs it.
            if len(net.ext_grid) == 0:
                st.warning("OPF requires at least one ext_grid.")
                return

            if hasattr(net, "poly_cost") and len(net.poly_cost) > 0:
                net.poly_cost.drop(net.poly_cost.index, inplace=True)

            pn.create_poly_cost(net, net.ext_grid.index[0], "ext_grid", cp1_eur_per_mw=1.0)
            # Use cp2_eur_per_mw2 to penalize BOTH charging and discharging!
            pn.create_poly_cost(net, opf_storage_idx, "storage", cp1_eur_per_mw=0, cp2_eur_per_mw2=1.0)
            
        pv_object = st.session_state.get('pv')
        bev_object = st.session_state.get("bev")
        # Heat pump page stores the object under "hp".
        # Keep "heat_pump" as fallback for compatibility.
        heatpump_object = st.session_state.get("hp") or st.session_state.get("heat_pump")
        # es_object = st.session_state.get("es")
        if pv_object is None:
            st.warning("❌ PV not configured. Please go to PV Configuration page first.")
            return
        if bev_object is None: 
            st.warning("❌ EV not configured. Please go to EV Configuration page first.")
            return
        
        if heatpump_object is None:
            st.warning("❌ Heat Pump not configured. Please go to Heat Pump Configuration page first.")
            return
        try:

            st.session_state.power_flow_ran = True
            st.session_state.network = net
            net = st.session_state.network
            # if use_storage_opf:
            #     st.info("✅ Initial power flow completed. Starting storage timeseries with OPF...")
            # else:
            #     st.info("✅ Initial power flow completed. Starting timeseries simulation on updated network...")
            st.info("✅ Initial power flow completed. Starting timeseries simulation on updated network...")

            # Step 2: Build normalized 1kWp PV profile and scale by tab PV input (kW).
            pv_lat, pv_lon, pv_day_start = _get_pv_config_location_data()
            if pv_lat is None or pv_lon is None:
                st.warning("❌ Could not read coordinates from PV Konfiguration (Auswahl-Zusammenfassung).")
                return

            # One-day normalized 1kWp profile from PVlib + DWD.
            pv_timeseries_kw = get_normalized_pv_output(
                lat=pv_lat,
                lon=pv_lon,
                start_date=pv_day_start,
                end_date=pv_day_start + pd.Timedelta(days=1)
            )

            installed_pv_power_kw = float(st.session_state.get("pv_total_power_kw", 0.0) or 0.0)
            if installed_pv_power_kw <= 0:
                st.warning("❌ Please enter a PV generator power greater than 0 kW in DER Input.")
                return

            # Scale normalized 1kWp profile to the configured installed PV power.
            pv_timeseries_kw = pv_timeseries_kw * installed_pv_power_kw
            pv_timeseries_mw = pv_timeseries_kw / 1000.0

            # Persist scaled normalized PV profile for DER tab visualization.
            st.session_state['ts_pv_scaled_kw'] = pd.Series(pv_timeseries_kw).reset_index(drop=True)

            # Build profile DataFrame with proper indexing
            profile_df = pd.DataFrame({
                'pv_profile': pv_timeseries_mw.values
            })

            # Set index to match timeseries steps
            profile_df.index = range(len(pv_timeseries_mw))

            # Step 3: Clean up old Timeseries controllers and elements
            if hasattr(net, 'controller') and len(net.controller) > 0:
                net.controller.drop(net.controller.index, inplace=True)
                
            if 'PV_Timeseries' in net.sgen['name'].values:
                old_index = net.sgen[net.sgen['name'] == 'PV_Timeseries'].index[0]
                net.sgen.drop(old_index, inplace=True)

            # Create fresh sgen and get its index
            sgen_index = pn.create_sgen(net, bus=0, p_mw=0, q_mvar=0, name="PV_Timeseries",controllable=False)

            # Step 4: Create DataSource and ConstControl for PV
            ds = DFData(profile_df)
            ConstControl(net, element='sgen', element_index=sgen_index,
                         variable='p_mw', data_source=ds, profile_name='pv_profile')

            # Step 4b: Set up BEV timeseries (same pattern as PV)
            bev_timeseries_kw = bev_object.timeseries

            # Handle different data formats (Series or DataFrame) for BEV
            if isinstance(bev_timeseries_kw, pd.DataFrame):
                if len(bev_timeseries_kw.columns) == 1:
                    bev_timeseries_kw = bev_timeseries_kw.iloc[:, 0]
                else:
                    bev_timeseries_kw = bev_timeseries_kw.iloc[:, 0]

            # Convert to Series if needed
            if not isinstance(bev_timeseries_kw, pd.Series):
                bev_timeseries_kw = pd.Series(bev_timeseries_kw)

            # Convert kW to MW
            bev_timeseries_mw = bev_timeseries_kw / 1000.0

            # Build profile DataFrame with proper indexing for BEV
            bev_profile_df = pd.DataFrame({
                'bev_profile': bev_timeseries_mw.values
            })

            # Set index to match timeseries steps (must align with PV length)
            bev_profile_df.index = range(len(bev_timeseries_mw))

            # Clean up old BEV_Timeseries if exists (avoid duplicates)
            if 'BEV_Timeseries' in net.load['name'].values:
                old_index = net.load[net.load['name'] == 'BEV_Timeseries'].index[0]
                net.load.drop(old_index, inplace=True)

            # Create fresh load element and get its index (for timeseries control)
            bev_load_index = pn.create_load(net, bus=1, p_mw=0, q_mvar=0, name="BEV_Timeseries")

            # Create DataSource and ConstControl for BEV
            ds_bev = DFData(bev_profile_df)
            ConstControl(net, element='load', element_index=bev_load_index,
                         variable='p_mw', data_source=ds_bev, profile_name='bev_profile')

            heat_pump_timeseries_kw = heatpump_object.timeseries
            # Handle different data formats (Series or DataFrame) for Heat Pump
            if isinstance(heat_pump_timeseries_kw, pd.DataFrame):
                if len(heat_pump_timeseries_kw.columns) == 1:
                    heat_pump_timeseries_kw = heat_pump_timeseries_kw.iloc[:, 0]
                else:
                    heat_pump_timeseries_kw = heat_pump_timeseries_kw.iloc[:, 0]
            elif not isinstance(heat_pump_timeseries_kw, pd.Series):
                heat_pump_timeseries_kw = pd.Series(heat_pump_timeseries_kw)
                
            # Convert KW to MW
            heat_pump_timeseries_mw = heat_pump_timeseries_kw / 1000.0
            heat_pump_profile_df = pd.DataFrame({'heat_pump_profile': heat_pump_timeseries_mw.values})
            heat_pump_profile_df.index = range(len(heat_pump_timeseries_mw))
            
            heatpump_load_index = pn.create_load(net,bus=2, p_mw=0, q_mvar=0, name="Heat_Pump_Timeseries")
            
            ds_heat_pump = DFData(heat_pump_profile_df)
            ConstControl(net, element='load', element_index=heatpump_load_index,
                         variable='p_mw', data_source=ds_heat_pump, profile_name='heat_pump_profile')
            
            

            # Step 5: Run timeseries simulation
            from pandapower.timeseries import run_timeseries

            # Ensure all active profiles have same length; use shorter one
            profile_lengths = [len(profile_df), len(bev_profile_df), len(heat_pump_profile_df)]
            # if storage_profile_df is not None:
            #     profile_lengths.append(len(storage_profile_df))
            min_length = min(profile_lengths)
            max_timesteps = min(96, min_length)  # 96 = 24 hours * 4 (15-min intervals)
            time_steps = list(range(max_timesteps))
            
            # --- Base Load (Simbench) Timeseries Setup Using ConstControl ---
            base_load_mask = ~net.load['name'].isin(['BEV_Timeseries', 'Heat_Pump_Timeseries'])
            base_load_indices = net.load[base_load_mask].index.tolist()

            if base_load_indices:
                # Generate exact multipliers
                multiplier_df = Simbench_multiplier(net, amplitude=0.35)
                
                # Compute absolute values by multiplying the original p_mw by the timeframe factor
                abs_load_df = pd.DataFrame(index=multiplier_df.index)
                for idx in base_load_indices:
                    factor = multiplier_df[idx] if idx in multiplier_df.columns else 1.0
                    abs_load_df[str(idx)] = float(net.load.at[idx, 'p_mw']) * factor

                ds_base_loads = DFData(abs_load_df)
                for idx in base_load_indices:
                    ConstControl(
                        net, element='load', element_index=idx,
                        variable='p_mw', data_source=ds_base_loads, profile_name=str(idx)
                    )
            # ----------------------------------------------------------------

            # Clear any cached structures before running
            if hasattr(net, '_is_elements'):
                delattr(net, '_is_elements')

            # Store results for each timestep manually
            voltage_results = []
            loading_results = []

            # Force numeric dtypes before OPF/PF loop — prevents Numba object array crash
            net.sgen['p_mw'] = net.sgen['p_mw'].astype(float)
            net.load['p_mw'] = net.load['p_mw'].astype(float)
            if 'storage' in net and len(net.storage) > 0:
                net.storage['p_mw'] = net.storage['p_mw'].astype(float)
            
            if use_opf:
                net.sgen['controllable'] = False
                net.sgen['min_p_mw'] = 0.0
                # Set max_p_mw based on installed capacity, not the current timestep value
                net.sgen['max_p_mw'] = installed_pv_power_kw / 1000.0  # Use rated capacity
                net.sgen['min_p_mw'] = 0.0
                
            # Run for each time step
            for i, time_step in enumerate(time_steps):
                try:
                    run_func = pn.runopp if use_opf else pn.runpp
                    run_timeseries(net, [time_step], run=run_func)

                except Exception as e:
                    if use_opf:
                        st.warning(f"OPF infeasible at step {time_step}, falling back to PF: {e}")
                try:
                    run_timeseries(net, [time_step], run=pn.runpp)
                except Exception as e2:
                    st.error(f"PF also failed at step {time_step}: {e2}")
                    continue  # skip this timestep rather than aborting everything

                voltage_results.append(net.res_bus['vm_pu'].values.copy())

                # Collect line loading results
                if len(net.res_line) > 0:
                    loading_results.append(net.res_line['loading_percent'].values.copy())

            # Convert to DataFrames
            ts_voltage = pd.DataFrame(voltage_results, columns=net.res_bus.index)
            if loading_results:
                ts_loading = pd.DataFrame(loading_results, columns=net.res_line.index)
            else:
                ts_loading = None

            # Store for later use
            st.session_state['ts_voltage'] = ts_voltage
            st.session_state['ts_loading'] = ts_loading

            if use_opf:
                if "name" in net.storage.columns:
                    opf_cleanup_idx = net.storage[net.storage["name"] == "OPF_Storage"].index
                    if len(opf_cleanup_idx) > 0:
                        net.storage.drop(opf_cleanup_idx, inplace=True)

            # Persist updated network back to session state
            st.session_state.network = net

            # Step 6: Display timeseries results
            st.markdown("### 📊 Timeseries Results")

            # Create time labels in minutes (15-min resolution)
            max_minutes = max_timesteps * 15
            time_labels = list(range(0, max_minutes + 1, 15))  # 0, 15, 30, 45, ... minutes
            
          

            # Plot 1: Voltage over time
            st.markdown("#### ⚡ Bus Voltage Trajectory (Per Bus)")

            # Access timeseries results from session state
            ts_voltage = st.session_state.get('ts_voltage')
            if ts_voltage is not None and ts_voltage.shape[0] > 1:
                fig_voltage_ts = go.Figure()

                # Plot voltage trajectory for each bus
                for bus_col in ts_voltage.columns:
                    bus_data = ts_voltage[bus_col].values
                    has_bus_index = bus_col in net.bus.index
                    if has_bus_index and 'name' in net.bus.columns and pd.notna(net.bus.at[bus_col, 'name']):
                        bus_name = net.bus.at[bus_col, 'name']
                    else:
                        bus_name = f'Bus {bus_col}'
                    fig_voltage_ts.add_trace(go.Scatter(
                        x=time_labels[:len(bus_data)],
                        y=bus_data,
                        name=bus_name,
                        mode='lines',
                        line=dict(width=2)
                    ))

                # Add nominal voltage
                fig_voltage_ts.add_hline(y=1.0, line_dash="dot", line_color="gray",
                                         annotation_text="Nominal (1.0 p.u.)")
                fig_voltage_ts.add_hline(y=1.05, line_dash="dash", line_color="red",
                                         annotation_text="Upper Limit")
                fig_voltage_ts.add_hline(y=0.95, line_dash="dash", line_color="red",
                                         annotation_text="Lower Limit")

                fig_voltage_ts.update_layout(
                    xaxis_title="Time (Minutes)",
                    yaxis_title="Voltage (p.u.)",
                    height=500,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    hovermode='x unified',
                    xaxis=dict(
                        tickformat=',.0f',
                        tickmode='linear',
                        tick0=0,
                        dtick=60  # Show every 60 minutes (1 hour)
                    )
                )

                st.plotly_chart(fig_voltage_ts, use_container_width=True)
            else:
                st.warning("⚠️ No voltage timeseries data found")

            # Plot 2: Line loading over time
            st.markdown("#### 📈 Line Loading Trajectory (Per Line)")

            # Get line loading data from session state
            ts_loading = st.session_state.get('ts_loading')
            if ts_loading is not None and ts_loading.shape[0] > 1:
                fig_loading_ts = go.Figure()

                # ts_loading rows=timesteps, columns=line_indices
                for line_col in ts_loading.columns:
                    line_data = ts_loading[line_col].values
                    has_line_index = line_col in net.line.index
                    if has_line_index and 'name' in net.line.columns and pd.notna(net.line.at[line_col, 'name']):
                        line_name = net.line.at[line_col, 'name']
                    else:
                        line_name = f'Line {line_col}'
                    fig_loading_ts.add_trace(go.Scatter(
                        x=time_labels[:len(line_data)],
                        y=line_data,
                        name=line_name,
                        mode='lines',
                        line=dict(width=2)
                    ))

                # Add thresholds
                fig_loading_ts.add_hline(y=100, line_dash="dash", line_color="red",
                                         annotation_text="Overload (100%)")
                fig_loading_ts.add_hline(y=80, line_dash="dot", line_color="orange",
                                         annotation_text="Warning (80%)")

                fig_loading_ts.update_layout(
                    xaxis_title="Time (Minutes)",
                    yaxis_title="Loading Percent (%)",
                    height=450,
                    hovermode='x unified',
                    xaxis=dict(
                        tickformat=',.0f',
                        tickmode='linear',
                        tick0=0,
                        dtick=60  # Show every 60 minutes (1 hour)
                    )
                )

                st.plotly_chart(fig_loading_ts, use_container_width=True)
            else:
                st.warning("⚠️ No loading timeseries data found")

        except Exception as e:
            st.error(f"❌ Error during simulation: {e}")
            import traceback
            st.error(traceback.format_exc())
