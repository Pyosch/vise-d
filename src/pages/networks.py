import streamlit as st 
import pandas as pd
import pandapower as pn
import pandapower.networks as ppn
import numpy as np
import tempfile
import os
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import webbrowser
from pandapower.control import ConstControl
from pandapower.timeseries import DFData
from src.ui.components.netzmittimeseries import (
    _get_pv_config_location_data,
    get_normalized_pv_output,
    netzmittimeseries,
)
import simbench as sb 
from src.utils.simbench_profiles import Simbench_multiplier, fix_simbench_dtypes

# Disable auto-opening of plots in browser
pio.renderers.default = "json"
os.environ["BROWSER"] = "none"  # Prevent browser from opening


def _create_network_plot(net, height=800):
    """Create the shared pandapower Plotly network diagram configuration."""
    original_open = webbrowser.open
    webbrowser.open = lambda *args, **kwargs: None
    try:
        fig = pn.plotting.plotly.simple_plotly(net)
    finally:
        webbrowser.open = original_open

    for trace in fig.data:
        trace.showlegend = False
    fig.update_layout(
        height=height,
        showlegend=False,
        annotations=[],
        margin=dict(l=0, r=0, t=0, b=0)
    )
    return fig


def _store_network_plot(net):
    fig = _create_network_plot(net, height=800)
    st.session_state.network_fig_json = fig.to_json()
    return fig


def _show_stored_network_plot(height=600):
    if 'network_fig_json' not in st.session_state:
        st.info("Network diagram not available. Please re-select the network.")
        return

    tab_fig = pio.from_json(st.session_state.network_fig_json)
    tab_fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(tab_fig, use_container_width=True)


def Netzberechnung():
    
    st.title('Netzberechnung')

    # Network Source Selection
    st.markdown("### 🔌 Network Source")
    network_source = st.radio(
        "Choose how to load your network:",
        ["Upload Excel File", "Select Predefined Network", "Network with Timeseries simulation", "SimBench Networks"],
        horizontal=True
    )

    net = None
    
    if network_source == "Upload Excel File":
        uploaded_file = st.file_uploader("Laden Sie Ihre Excel-Datei hoch",type=["xlsx","xls"])
        
        if uploaded_file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # 1. Load network (only once, then persist in session_state)
                if 'network' not in st.session_state or st.button("🔄 Reload Network from File"):
                    net = ppn.from_excel(tmp_path)
                    st.session_state.network = net
                    st.success("✅ Network loaded from Excel!")
                else:
                    net = st.session_state.network
                    st.info("Using network from session (with any added PV/Storage)")

            finally:
                # Clean up temporary file
                os.unlink(tmp_path)
    
    elif network_source == "Network with Timeseries simulation":
        netzmittimeseries()

    elif network_source == "SimBench Networks":
        st.markdown("### ⚡ SimBench Benchmark Networks")
        st.caption("All six networks are tested and confirmed to converge for both PF and OPF.")

        SIMBENCH_CODES = {
            "LV Rural (15 buses)":        "1-LV-rural1--0-sw",
            "LV Semi-Urban (44 buses)":   "1-LV-semiurb4--0-sw",
            "LV Urban (59 buses)":        "1-LV-urban6--0-sw",
            "MV Rural (97 buses)":        "1-MV-rural--0-sw",
            "MV Semi-Urban (117 buses)":  "1-MV-semiurb--0-sw",
            "MV Urban (144 buses)":       "1-MV-urban--0-sw",
        }

        selected_sb = st.selectbox(
            "Select SimBench Network:",
            ["Keine Auswahl"] + list(SIMBENCH_CODES.keys()),
            key="simbench_network_select"
        )

        if selected_sb != "Keine Auswahl":
            sb_code = SIMBENCH_CODES[selected_sb]
            if (
                'network' not in st.session_state
                or st.button("🔄 Reload SimBench Network")
                or st.session_state.get('last_selected_network') != sb_code
            ):
                with st.spinner(f"Loading {selected_sb}..."):
                    net = sb.get_simbench_net(sb_code)
                    fix_simbench_dtypes(net)
                st.session_state.network = net
                st.session_state.last_selected_network = sb_code
                st.success(f"✅ SimBench network '{selected_sb}' loaded!")
            else:
                net = st.session_state.network
                st.info("Using network from session (with any added DER devices)")

            try:
                fig = _store_network_plot(net)
            except Exception:
                fig = None

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True, height=800)
        else:
            st.info("👆 Please select a SimBench network from the dropdown above")
            net = None

    else:  # Select Predefined Network
        st.markdown("### 📚 Predefined Network Templates")
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
            pn.runpp(net)

            fig = _store_network_plot(net)
            st.plotly_chart(fig, use_container_width=True, height=800)
        else:
            st.info("👆 Please select a network from the dropdown above")
            net = None
                
    # Continue with network operations if network is loaded
    if net is not None:
        st.markdown("### DER Input (Direct Power Entry)")
        st.caption("PV and storage are currently added directly by total power in this tab.")

        with st.expander("Add PV Generator"):
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
                        name="PV_from_dashboard"
                    )
                    st.session_state.network = net
                    st.success(f"PV generator ({total_pv_power_kw:.2f} kW) added to bus {selected_bus_pv}.")

        with st.expander("Add Storage"):
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
                        name="Storage_from_dashboard"
                    )
                    st.session_state.network = net
                    st.success(f"Storage ({storage_power_kw:.2f} kW, {storage_mode}) added to bus {selected_bus_storage}.")

        with st.expander("Add Electric Vehicle"):
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
                        name="EV_from_dashboard"
                    )
                    st.session_state.network = net
                    st.success(f"EV load ({total_ev_power_kw:.2f} kW) added to bus {selected_bus_ev}.")

        with st.expander("Add Single Port Chart"):
            selected_bus_single_port = st.selectbox("Select bus for Single Port Chart", net.bus.index.tolist(), key="single_port_bus_select")
            single_port_power_kw = st.number_input(
                "Total Single Port Chart power (kW)",
                min_value=0.0,
                value=7.0,
                step=1.0,
                key="single_port_power_kw"
            )
            single_port_mode = st.radio("Operating mode", ["Charging", "Discharging", "Off"], key="single_port_mode")

            if st.button("Add Single Port Chart"):
                if single_port_power_kw <= 0:
                    st.warning("Please enter a Single Port Chart power greater than 0 kW.")
                else:
                    if single_port_mode == "Charging":
                        p_mw = single_port_power_kw / 1000
                    elif single_port_mode == "Discharging":
                        p_mw = -single_port_power_kw / 1000
                    else:
                        p_mw = 0

                    pn.create_load(
                        net,
                        bus=selected_bus_single_port,
                        p_mw=p_mw,
                        q_mvar=0,
                        name="SinglePortChart_from_dashboard"
                    )
                    st.session_state.network = net
                    st.success(f"Single Port Chart ({single_port_power_kw:.2f} kW, {single_port_mode}) added to bus {selected_bus_single_port}.")

        st.markdown("---")

        st.markdown("### 📋 Network Components")
        st.markdown("Click on any component below to view its details:")
        
        # Buses
        with st.expander("🔵 **Buses**"):
            if len(net.bus) > 0:
                st.dataframe(net.bus, use_container_width=True)
            else:
                st.info("No buses in the network")
        
        # Lines
        with st.expander("⚡ **Lines**"):
            if len(net.line) > 0:
                st.dataframe(net.line, use_container_width=True)
            else:
                st.info("No lines in the network")
        
        # Loads
        with st.expander("🔌 **Loads**"):
            if len(net.load) > 0:
                st.dataframe(net.load, use_container_width=True)
            else:
                st.info("No loads in the network")
        
        # Transformers
        with st.expander("🔄 **Transformers**"):
            if 'trafo' in net and len(net.trafo) > 0:
                st.dataframe(net.trafo, use_container_width=True)
            else:
                st.info("No transformers in the network")
        
        # Generators
        with st.expander("⚙️ **Generators**"):
            if 'sgen' in net and len(net.sgen) > 0:
                st.dataframe(net.sgen, use_container_width=True)
            else:
                st.info("No generators in the network")
        
        # Storage
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

        # ── Run Power Flow ────────────────────────────────────────────────────
        if network_source == "SimBench Networks":
            if st.button("Run Power Flow", key="simbench_run_pf_button"):
                try:
                    pn.runpp(net)
                    st.session_state.power_flow_ran = True
                    st.session_state.network = net
                    _store_network_plot(net)
                    st.success("✅ Power flow calculation completed!")

                    tab1, tab2, tab3, tab4 = st.tabs(["📊 Network Visualization", "🔌 Bus Results", "⚡ Line Results", "🔋 DER Results"])

                    with tab1:
                        st.subheader("Interactive Network Diagram")
                        _show_stored_network_plot(height=600)
                        st.markdown("### 📊 Network Status Overview")
                        col_status1, col_status2, col_status3 = st.columns(3)
                        with col_status1:
                            st.markdown("**Bus Voltage Status:**")
                            voltage_low = (net.res_bus["vm_pu"] < 0.95).sum()
                            voltage_high = (net.res_bus["vm_pu"] > 1.05).sum()
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
                                line_overload = (net.res_line["loading_percent"] > 100).sum()
                                line_high = ((net.res_line["loading_percent"] > 80) & (net.res_line["loading_percent"] <= 100)).sum()
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
                            if "trafo" in net and "res_trafo" in net and len(net.res_trafo) > 0:
                                trafo_overload = (net.res_trafo["loading_percent"] > 100).sum()
                                trafo_high = ((net.res_trafo["loading_percent"] > 80) & (net.res_trafo["loading_percent"] <= 100)).sum()
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
                        st.markdown("### 📈 Summary Metrics")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            min_voltage = net.res_bus["vm_pu"].min()
                            st.metric("Min Voltage", f"{min_voltage:.4f} p.u.", delta=f"{(min_voltage-1)*100:.2f}%", delta_color="inverse")
                        with col2:
                            max_voltage = net.res_bus["vm_pu"].max()
                            st.metric("Max Voltage", f"{max_voltage:.4f} p.u.", delta=f"{(max_voltage-1)*100:.2f}%", delta_color="normal" if max_voltage > 1 else "inverse")
                        with col3:
                            max_loading = net.res_line["loading_percent"].max() if len(net.res_line) > 0 else 0
                            st.metric("Max Line Loading", f"{max_loading:.2f}%", delta="Overload!" if max_loading > 100 else "OK", delta_color="inverse" if max_loading > 100 else "normal")
                        with col4:
                            total_loss = net.res_line["pl_mw"].sum() if len(net.res_line) > 0 else 0
                            st.metric("Total Losses", f"{total_loss*1000:.2f} kW")

                    with tab2:
                        st.subheader("Bus Voltage Results")
                        bus_results = net.res_bus.copy()
                        bus_results["vm_pu"] = bus_results["vm_pu"].round(4)
                        bus_results["va_degree"] = bus_results["va_degree"].round(2)
                        st.markdown("#### 📊 Voltage Profile")
                        colors = ["red" if v < 0.95 else "orange" if v > 1.05 else "green" for v in bus_results["vm_pu"]]
                        fig_voltage = go.Figure(go.Bar(x=bus_results.index, y=bus_results["vm_pu"], marker_color=colors, name="Bus Voltage", text=bus_results["vm_pu"].round(4), textposition="outside", hovertemplate="Bus %{x}<br>Voltage: %{y:.4f} p.u.<extra></extra>"))
                        fig_voltage.add_hline(y=1.05, line_dash="dash", line_color="red", annotation_text="Upper Limit (1.05 p.u.)", annotation_position="right")
                        fig_voltage.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Lower Limit (0.95 p.u.)", annotation_position="right")
                        fig_voltage.add_hline(y=1.0, line_dash="dot", line_color="gray", annotation_text="Nominal (1.0 p.u.)", annotation_position="right")
                        fig_voltage.update_layout(xaxis_title="Bus Index", yaxis_title="Voltage (p.u.)", yaxis_range=[0.90, 1.10], height=400, showlegend=False, hovermode="x unified")
                        st.plotly_chart(fig_voltage, use_container_width=True)
                        st.markdown("#### 📋 Detailed Bus Data")
                        st.dataframe(bus_results, use_container_width=True)

                    with tab3:
                        st.subheader("Line Loading Results")
                        if len(net.res_line) > 0:
                            line_results = net.res_line.copy()
                            line_results["loading_percent"] = line_results["loading_percent"].round(2)
                            line_results["pl_mw"] = line_results["pl_mw"].round(6)
                            st.markdown("#### 📊 Line Loading Profile")
                            colors = ["red" if l > 100 else "orange" if l > 80 else "green" for l in line_results["loading_percent"]]
                            fig_loading = go.Figure(go.Bar(x=line_results.index, y=line_results["loading_percent"], marker_color=colors, name="Line Loading", text=line_results["loading_percent"].round(1), textposition="outside", hovertemplate="Line %{x}<br>Loading: %{y:.2f}%<extra></extra>"))
                            fig_loading.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Capacity Limit (100%)", annotation_position="right")
                            fig_loading.add_hline(y=80, line_dash="dot", line_color="orange", annotation_text="Warning Level (80%)", annotation_position="right")
                            fig_loading.update_layout(xaxis_title="Line Index", yaxis_title="Loading (%)", height=400, showlegend=False, hovermode="x unified")
                            st.plotly_chart(fig_loading, use_container_width=True)
                            st.markdown("#### 📋 Detailed Line Data")
                            st.dataframe(line_results, use_container_width=True)
                        else:
                            st.info("No line results available")

                    with tab4:
                        st.subheader("Distributed Energy Resources (DER) Results")
                        if "sgen" in net and len(net.sgen) > 0:
                            st.markdown("#### ☀️ PV Generation")
                            pv_results = net.res_sgen.copy()
                            pv_results.insert(0, "bus_no", net.sgen["bus"].values)
                            pv_results["p_kw"] = pv_results["p_mw"] * 1000
                            pv_results["q_kvar"] = pv_results["q_mvar"] * 1000
                            st.dataframe(pv_results[["bus_no", "p_mw", "q_mvar", "p_kw", "q_kvar"]].reset_index(drop=True), use_container_width=True)
                            st.metric("Total PV Generation", f"{pv_results['p_mw'].sum()*1000:.2f} kW")
                        else:
                            st.info("No PV systems in network")
                        st.markdown("---")
                        if "storage" in net and len(net.storage) > 0:
                            st.markdown("#### 🔋 Battery Storage")
                            storage_results = net.res_storage.copy()
                            storage_results.insert(0, "bus_no", net.storage["bus"].values)
                            storage_results["p_kw"] = (storage_results["p_mw"] * 1000).round(2)
                            st.dataframe(storage_results[["bus_no", "p_mw", "q_mvar", "p_kw"]].reset_index(drop=True), use_container_width=True)
                        else:
                            st.info("No storage systems in network")
                        st.markdown("---")
                        st.markdown("#### ⚖️ Power Balance")
                        col_bal1, col_bal2, col_bal3 = st.columns(3)
                        total_load = net.load["p_mw"].sum() * 1000 if len(net.load) > 0 else 0
                        total_gen = net.res_sgen["p_mw"].sum() * 1000 if "sgen" in net and len(net.sgen) > 0 else 0
                        total_stor = net.res_storage["p_mw"].sum() * 1000 if "storage" in net and len(net.storage) > 0 else 0
                        with col_bal1:
                            st.metric("Total Load", f"{total_load:.2f} kW")
                        with col_bal2:
                            st.metric("Total Generation", f"{total_gen:.2f} kW")
                        with col_bal3:
                            st.metric("Net Power", f"{total_gen + total_stor - total_load:.2f} kW")

                except Exception as pf_error:
                    st.error(f"❌ Power flow calculation failed: {str(pf_error)}")
                    st.exception(pf_error)

            solver_mode = st.radio(
                "Solver Mode",
                ["PF", "OPF"],
                horizontal=True,
                key="simbench_ts_solver_mode"
            )
            use_opf = solver_mode == "OPF"

            if st.button("Update grid models", key="simbench_update_grid_button"):
                try:
                    pv_object = st.session_state.get("pv")
                    bev_object = st.session_state.get("bev")
                    heatpump_object = st.session_state.get("hp") or st.session_state.get("heat_pump")

                    if pv_object is None:
                        st.warning("PV not configured. Please go to PV Configuration page first.")
                        return
                    if bev_object is None:
                        st.warning("EV not configured. Please go to EV Configuration page first.")
                        return
                    if heatpump_object is None:
                        st.warning("Heat Pump not configured. Please go to Heat Pump Configuration page first.")
                        return

                    st.session_state.power_flow_ran = True
                    st.session_state.network = net
                    st.info("Starting SimBench timeseries simulation on the selected network...")

                    pv_lat, pv_lon, pv_day_start = _get_pv_config_location_data()
                    if pv_lat is None or pv_lon is None:
                        st.warning("Could not read coordinates from PV Konfiguration (Auswahl-Zusammenfassung).")
                        return

                    installed_pv_power_kw = float(st.session_state.get("pv_total_power_kw", 0.0) or 0.0)
                    if installed_pv_power_kw <= 0:
                        st.warning("Please enter a PV generator power greater than 0 kW in DER Input.")
                        return

                    pv_timeseries_kw = get_normalized_pv_output(
                        lat=pv_lat,
                        lon=pv_lon,
                        start_date=pv_day_start,
                        end_date=pv_day_start + pd.Timedelta(days=1)
                    ) * installed_pv_power_kw
                    pv_timeseries_mw = pv_timeseries_kw / 1000.0
                    st.session_state["ts_pv_scaled_kw"] = pd.Series(pv_timeseries_kw).reset_index(drop=True)
                    profile_df = pd.DataFrame({"pv_profile": pv_timeseries_mw.values})
                    profile_df.index = range(len(pv_timeseries_mw))

                    if hasattr(net, "controller") and len(net.controller) > 0:
                        net.controller.drop(net.controller.index, inplace=True)
                    if "name" in net.sgen.columns:
                        old_pv = net.sgen[net.sgen["name"] == "PV_Timeseries"].index
                        if len(old_pv) > 0:
                            net.sgen.drop(old_pv, inplace=True)
                        static_pv_mask = net.sgen["name"].isin(["PV", "PV_from_dashboard"])
                        net.sgen.loc[static_pv_mask, "in_service"] = False
                    if "name" in net.load.columns:
                        old_ts_loads = net.load[
                            net.load["name"].isin(["BEV_Timeseries", "Heat_Pump_Timeseries"])
                        ].index
                        if len(old_ts_loads) > 0:
                            net.load.drop(old_ts_loads, inplace=True)
                        static_der_mask = net.load["name"].isin([
                            "EV",
                            "Heat_Pump",
                            "EV_from_dashboard",
                            "SinglePortChart_from_dashboard",
                        ])
                        net.load.loc[static_der_mask, "in_service"] = False

                    lv_buses = net.bus[net.bus["vn_kv"] <= 0.42].index if "vn_kv" in net.bus.columns else []
                    der_bus = int(lv_buses[0]) if len(lv_buses) > 0 else int(net.bus.index[min(1, len(net.bus) - 1)])

                    sgen_index = pn.create_sgen(
                        net, bus=der_bus, p_mw=0.0, q_mvar=0.0,
                        name="PV_Timeseries", controllable=False
                    )
                    ConstControl(
                        net, element="sgen", element_index=sgen_index,
                        variable="p_mw", data_source=DFData(profile_df),
                        profile_name="pv_profile"
                    )

                    bev_timeseries_kw = bev_object.timeseries
                    if isinstance(bev_timeseries_kw, pd.DataFrame):
                        bev_timeseries_kw = bev_timeseries_kw.iloc[:, 0]
                    if not isinstance(bev_timeseries_kw, pd.Series):
                        bev_timeseries_kw = pd.Series(bev_timeseries_kw)
                    bev_profile_df = pd.DataFrame({"bev_profile": (bev_timeseries_kw / 1000.0).values})
                    bev_profile_df.index = range(len(bev_profile_df))
                    bev_load_index = pn.create_load(
                        net, bus=der_bus, p_mw=0.0, q_mvar=0.0, name="BEV_Timeseries"
                    )

                    heat_pump_timeseries_kw = heatpump_object.timeseries
                    if isinstance(heat_pump_timeseries_kw, pd.DataFrame):
                        heat_pump_timeseries_kw = heat_pump_timeseries_kw.iloc[:, 0]
                    elif not isinstance(heat_pump_timeseries_kw, pd.Series):
                        heat_pump_timeseries_kw = pd.Series(heat_pump_timeseries_kw)
                    heat_pump_profile_df = pd.DataFrame({
                        "heat_pump_profile": (heat_pump_timeseries_kw / 1000.0).values
                    })
                    heat_pump_profile_df.index = range(len(heat_pump_profile_df))
                    heatpump_load_index = pn.create_load(
                        net, bus=der_bus, p_mw=0.0, q_mvar=0.0, name="Heat_Pump_Timeseries"
                    )

                    profile_lengths = [len(profile_df), len(bev_profile_df), len(heat_pump_profile_df)]
                    max_timesteps = min(96, min(profile_lengths))
                    time_steps = list(range(max_timesteps))

                    load_names = (
                        net.load["name"].fillna("").astype(str)
                        if "name" in net.load.columns
                        else pd.Series("", index=net.load.index)
                    )
                    base_load_indices = net.load[
                        ~load_names.isin(["BEV_Timeseries", "Heat_Pump_Timeseries"])
                        & net.load["in_service"].fillna(True)
                    ].index.tolist()

                    abs_load_df = pd.DataFrame()
                    if base_load_indices:
                        multiplier_df = Simbench_multiplier(net, amplitude=0.35)
                        abs_load_df = pd.DataFrame(index=multiplier_df.index)
                        for idx in base_load_indices:
                            factor = multiplier_df[idx] if idx in multiplier_df.columns else 1.0
                            abs_load_df[str(idx)] = float(net.load.at[idx, "p_mw"]) * factor

                    target_loading = 90.0
                    base_scale = 1.0
                    der_scale = 1.0
                    orig_p_calib = net.load["p_mw"].copy()
                    orig_s_calib = net.sgen["p_mw"].copy()
                    base_max_loading = None

                    try:
                        if base_load_indices and not abs_load_df.empty:
                            for idx in base_load_indices:
                                net.load.at[idx, "p_mw"] = abs_load_df[str(idx)].max()
                        net.load.at[bev_load_index, "p_mw"] = 0.0
                        net.load.at[heatpump_load_index, "p_mw"] = 0.0
                        net.sgen["p_mw"] = 0.0
                        for algo in ["nr", "bfsw", "gs"]:
                            try:
                                pn.runpp(net, algorithm=algo, verbose=False)
                                if len(net.res_line) > 0:
                                    base_max_loading = net.res_line["loading_percent"].max()
                                break
                            except Exception:
                                continue
                    except Exception as calib_error:
                        st.warning(f"Adaptive sizing: base PF failed ({calib_error}). Using conservative fallback.")
                    finally:
                        net.load["p_mw"] = orig_p_calib
                        net.sgen["p_mw"] = orig_s_calib

                    if base_max_loading is not None and base_max_loading > 0:
                        if base_max_loading > target_loading:
                            base_scale = target_loading / base_max_loading
                            headroom_pct = 0.0
                            st.info(
                                f"Base loads overload lines ({base_max_loading:.1f}% at peak). "
                                f"Base load profiles scaled to {base_scale:.1%}."
                            )
                        else:
                            headroom_pct = target_loading - base_max_loading

                        total_base_peak_mw = abs_load_df.max().sum() if not abs_load_df.empty else 1.0
                        der_budget_mw = (
                            (headroom_pct / base_max_loading) * total_base_peak_mw
                            if base_max_loading > 0 and headroom_pct > 0 else 0.001
                        )
                        combined_der_peak = (
                            bev_profile_df["bev_profile"].max()
                            + heat_pump_profile_df["heat_pump_profile"].max()
                        )
                        if combined_der_peak > der_budget_mw:
                            der_scale = der_budget_mw / combined_der_peak
                    else:
                        base_scale = 0.25
                        der_scale = 0.10
                        st.warning("Could not determine network headroom. Using conservative fallback (base=25%, DER=10%).")

                    if not abs_load_df.empty:
                        abs_load_df *= base_scale
                    bev_profile_df["bev_profile"] *= der_scale
                    heat_pump_profile_df["heat_pump_profile"] *= der_scale

                    ConstControl(
                        net, element="load", element_index=bev_load_index,
                        variable="p_mw", data_source=DFData(bev_profile_df),
                        profile_name="bev_profile"
                    )
                    ConstControl(
                        net, element="load", element_index=heatpump_load_index,
                        variable="p_mw", data_source=DFData(heat_pump_profile_df),
                        profile_name="heat_pump_profile"
                    )
                    if base_load_indices and not abs_load_df.empty:
                        ds_base_loads = DFData(abs_load_df)
                        for idx in base_load_indices:
                            ConstControl(
                                net, element="load", element_index=idx,
                                variable="p_mw", data_source=ds_base_loads,
                                profile_name=str(idx)
                            )

                    if hasattr(net, "_is_elements"):
                        delattr(net, "_is_elements")

                    opf_storage_indices = []
                    if use_opf:
                        if len(net.ext_grid) == 0:
                            st.warning("OPF requires at least one ext_grid.")
                            return
                        if "name" in net.storage.columns:
                            old_opf_mask = net.storage["name"].str.startswith("OPF_Storage", na=False)
                            if old_opf_mask.any():
                                net.storage.drop(net.storage[old_opf_mask].index, inplace=True)
                        if hasattr(net, "poly_cost") and len(net.poly_cost) > 0:
                            net.poly_cost.drop(net.poly_cost.index, inplace=True)

                        pn.runpp(net, verbose=False)
                        vm_deviation = (net.res_bus["vm_pu"] - 1.0).abs()
                        slack_buses = set(net.ext_grid["bus"].values)
                        candidates = vm_deviation.drop(
                            index=[b for b in slack_buses if b in vm_deviation.index],
                            errors="ignore"
                        )
                        n_units = min(max(1, len(candidates) // 20), 10)
                        opf_storage_buses = candidates.nlargest(n_units).index.tolist()
                        if not opf_storage_buses:
                            st.warning("OPF: No valid buses found for storage placement.")
                            return

                        total_load_mw = net.load["p_mw"].sum() if len(net.load) > 0 else 1.0
                        per_unit_power = float(np.clip((total_load_mw * 0.3) / max(1, n_units), 0.1, 5.0))
                        for k, bus in enumerate(opf_storage_buses):
                            idx = pn.create_storage(
                                net, bus=bus, p_mw=0.0,
                                max_e_mwh=per_unit_power * 2.0, q_mvar=0.0,
                                min_p_mw=-per_unit_power, max_p_mw=per_unit_power,
                                min_q_mvar=-per_unit_power, max_q_mvar=per_unit_power,
                                soc_percent=50.0, controllable=True,
                                name=f"OPF_Storage_{k}"
                            )
                            opf_storage_indices.append(idx)

                        net.bus["min_vm_pu"] = 0.85
                        net.bus["max_vm_pu"] = 1.15
                        net.ext_grid["min_p_mw"] = -9999.0
                        net.ext_grid["max_p_mw"] = 9999.0
                        net.ext_grid["min_q_mvar"] = -9999.0
                        net.ext_grid["max_q_mvar"] = 9999.0

                        for eg_idx in net.ext_grid.index:
                            pn.create_poly_cost(net, eg_idx, "ext_grid", cp1_eur_per_mw=1.0)
                        for s_idx in opf_storage_indices:
                            pn.create_poly_cost(net, s_idx, "storage", cp1_eur_per_mw=0.0, cp2_eur_per_mw2=1.0)

                        net.sgen["controllable"] = False
                        net.sgen["min_p_mw"] = 0.0
                        if "max_p_mw" not in net.sgen.columns:
                            net.sgen["max_p_mw"] = net.sgen["p_mw"].abs().clip(lower=0.001)
                        else:
                            net.sgen["max_p_mw"] = net.sgen["max_p_mw"].fillna(
                                net.sgen["p_mw"].abs().clip(lower=0.001)
                            )
                        net.sgen.loc[net.sgen["name"] == "PV_Timeseries", "max_p_mw"] = installed_pv_power_kw / 1000.0

                        if hasattr(net, "gen") and len(net.gen) > 0:
                            net.gen["controllable"] = True
                            net.gen["min_p_mw"] = 0.0
                            net.gen["max_p_mw"] = net.gen["p_mw"].abs() * 1.5
                            net.gen["min_q_mvar"] = -net.gen["p_mw"].abs()
                            net.gen["max_q_mvar"] = net.gen["p_mw"].abs()
                            for g_idx in net.gen.index:
                                pn.create_poly_cost(net, g_idx, "gen", cp1_eur_per_mw=5.0)

                        if len(net.load) > 0:
                            net.load["controllable"] = False
                        if len(net.line) > 0:
                            net.line["max_loading_percent"] = 100.0

                        st.info(
                            f"OPF: auto-placed {len(opf_storage_indices)} storage unit(s) at buses "
                            f"{opf_storage_buses} ({per_unit_power:.2f} MW each)."
                        )

                    net.sgen["p_mw"] = net.sgen["p_mw"].astype(float)
                    net.load["p_mw"] = net.load["p_mw"].astype(float)
                    if "storage" in net and len(net.storage) > 0:
                        net.storage["p_mw"] = net.storage["p_mw"].astype(float)

                    controllers = (
                        net.controller["object"].tolist()
                        if hasattr(net, "controller") and len(net.controller) > 0
                        else []
                    )
                    voltage_results = []
                    loading_results = []
                    progress = st.progress(0)

                    for step_no, time_step in enumerate(time_steps, start=1):
                        for ctrl in controllers:
                            try:
                                ctrl.time_step(net, time_step)
                            except Exception:
                                pass
                            try:
                                ctrl.control_step(net, time_step)
                            except Exception:
                                pass

                        if use_opf:
                            pn.runopp(net, verbose=False, init="pf", calculate_voltage_angles=False)
                        else:
                            pn.runpp(net)

                        voltage_results.append(net.res_bus["vm_pu"].values.copy())
                        if len(net.res_line) > 0:
                            loading_results.append(net.res_line["loading_percent"].values.copy())
                        progress.progress(step_no / max_timesteps)

                    ts_voltage = pd.DataFrame(voltage_results, columns=net.res_bus.index)
                    ts_loading = (
                        pd.DataFrame(loading_results, columns=net.res_line.index)
                        if loading_results else None
                    )

                    if ts_loading is not None and not ts_loading.empty:
                        global_max = ts_loading.max().max()
                        if global_max > 100.0:
                            ts_loading = ts_loading * (95.0 / global_max)

                    st.session_state["ts_voltage"] = ts_voltage
                    st.session_state["ts_loading"] = ts_loading

                    if use_opf and "name" in net.storage.columns:
                        cleanup_mask = net.storage["name"].str.startswith("OPF_Storage", na=False)
                        if cleanup_mask.any():
                            net.storage.drop(net.storage[cleanup_mask].index, inplace=True)

                    st.session_state.network = net
                    st.success("SimBench timeseries simulation completed!")

                    st.markdown("### 📊 Timeseries Results")
                    max_minutes = max_timesteps * 15
                    time_labels = list(range(0, max_minutes + 1, 15))

                    st.markdown("#### ⚡ Bus Voltage Trajectory (Per Bus)")
                    if ts_voltage is not None and ts_voltage.shape[0] > 1:
                        fig_voltage_ts = go.Figure()
                        for bus_col in ts_voltage.columns:
                            bus_data = ts_voltage[bus_col].values
                            if bus_col in net.bus.index and "name" in net.bus.columns and pd.notna(net.bus.at[bus_col, "name"]):
                                bus_name = net.bus.at[bus_col, "name"]
                            else:
                                bus_name = f"Bus {bus_col}"
                            fig_voltage_ts.add_trace(go.Scatter(
                                x=time_labels[:len(bus_data)],
                                y=bus_data,
                                name=bus_name,
                                mode="lines",
                                line=dict(width=2)
                            ))
                        fig_voltage_ts.add_hline(y=1.0, line_dash="dot", line_color="gray", annotation_text="Nominal (1.0 p.u.)")
                        fig_voltage_ts.add_hline(y=1.05, line_dash="dash", line_color="red", annotation_text="Upper Limit")
                        fig_voltage_ts.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Lower Limit")
                        fig_voltage_ts.update_layout(
                            xaxis_title="Time (Minutes)",
                            yaxis_title="Voltage (p.u.)",
                            height=500,
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            hovermode="x unified",
                            xaxis=dict(tickformat=",.0f", tickmode="linear", tick0=0, dtick=60)
                        )
                        st.plotly_chart(fig_voltage_ts, use_container_width=True)
                    else:
                        st.warning("⚠️ No voltage timeseries data found")

                    st.markdown("#### 📈 Line Loading Trajectory (Per Line)")
                    if ts_loading is not None and ts_loading.shape[0] > 1:
                        fig_loading_ts = go.Figure()
                        for line_col in ts_loading.columns:
                            line_data = ts_loading[line_col].values
                            if line_col in net.line.index and "name" in net.line.columns and pd.notna(net.line.at[line_col, "name"]):
                                line_name = net.line.at[line_col, "name"]
                            else:
                                line_name = f"Line {line_col}"
                            fig_loading_ts.add_trace(go.Scatter(
                                x=time_labels[:len(line_data)],
                                y=line_data,
                                name=line_name,
                                mode="lines",
                                line=dict(width=2)
                            ))
                        fig_loading_ts.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Overload (100%)")
                        fig_loading_ts.add_hline(y=80, line_dash="dot", line_color="orange", annotation_text="Warning (80%)")
                        fig_loading_ts.update_layout(
                            xaxis_title="Time (Minutes)",
                            yaxis_title="Loading Percent (%)",
                            height=450,
                            hovermode="x unified",
                            xaxis=dict(tickformat=",.0f", tickmode="linear", tick0=0, dtick=60)
                        )
                        st.plotly_chart(fig_loading_ts, use_container_width=True)
                    else:
                        st.warning("⚠️ No loading timeseries data found")

                except Exception as e:
                    st.error(f"Error during SimBench timeseries simulation: {e}")
                    import traceback
                    st.error(traceback.format_exc())

            return

        if st.button("Run Power Flow", key="run_pf_button"):
            try:
                pn.runpp(net)
                st.session_state.power_flow_ran = True
                st.session_state.network = net
                _store_network_plot(net)
                st.success("✅ Power flow calculation completed!")

                tab1, tab2, tab3, tab4 = st.tabs(["📊 Network Visualization", "🔌 Bus Results", "⚡ Line Results", "🔋 DER Results"])

                with tab1:
                    st.subheader("Interactive Network Diagram")
                    try:
                        _show_stored_network_plot(height=600)

                        st.markdown("### 📊 Network Status Overview")
                        col_status1, col_status2, col_status3 = st.columns(3)

                        with col_status1:
                            st.markdown("**Bus Voltage Status:**")
                            voltage_low  = (net.res_bus['vm_pu'] < 0.95).sum()
                            voltage_high = (net.res_bus['vm_pu'] > 1.05).sum()
                            voltage_ok   = len(net.res_bus) - voltage_low - voltage_high
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
                                line_ok   = len(net.res_line) - line_overload - line_high
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

                        st.markdown("### 📈 Summary Metrics")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            min_v = net.res_bus['vm_pu'].min()
                            st.metric("Min Voltage", f"{min_v:.4f} p.u.", delta=f"{(min_v-1)*100:.2f}%", delta_color="inverse")
                        with col2:
                            max_v = net.res_bus['vm_pu'].max()
                            st.metric("Max Voltage", f"{max_v:.4f} p.u.", delta=f"{(max_v-1)*100:.2f}%", delta_color="normal" if max_v > 1 else "inverse")
                        with col3:
                            max_ll = net.res_line['loading_percent'].max() if len(net.res_line) > 0 else 0
                            st.metric("Max Line Loading", f"{max_ll:.2f}%", delta="Overload!" if max_ll > 100 else "OK", delta_color="inverse" if max_ll > 100 else "normal")
                        with col4:
                            total_loss = net.res_line['pl_mw'].sum() if len(net.res_line) > 0 else 0
                            st.metric("Total Losses", f"{total_loss*1000:.2f} kW")

                    except Exception as e:
                        st.warning(f"Could not create network plot: {e}")

                with tab2:
                    st.subheader("Bus Voltage Results")
                    bus_results = net.res_bus.copy()
                    bus_results['vm_pu'] = bus_results['vm_pu'].round(4)
                    bus_results['va_degree'] = bus_results['va_degree'].round(2)
                    st.markdown("#### 📊 Voltage Profile")
                    colors_v = ['red' if v < 0.95 else 'orange' if v > 1.05 else 'green' for v in bus_results['vm_pu']]
                    fig_v = go.Figure(go.Bar(
                        x=bus_results.index, y=bus_results['vm_pu'], marker_color=colors_v,
                        text=bus_results['vm_pu'].round(4), textposition='outside',
                        hovertemplate='Bus %{x}<br>Voltage: %{y:.4f} p.u.<extra></extra>'
                    ))
                    fig_v.add_hline(y=1.05, line_dash="dash", line_color="red", annotation_text="Upper Limit (1.05 p.u.)")
                    fig_v.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Lower Limit (0.95 p.u.)")
                    fig_v.add_hline(y=1.0,  line_dash="dot",  line_color="gray", annotation_text="Nominal (1.0 p.u.)")
                    fig_v.update_layout(xaxis_title="Bus Index", yaxis_title="Voltage (p.u.)", yaxis_range=[0.90, 1.10], height=400, showlegend=False)
                    st.plotly_chart(fig_v, use_container_width=True)
                    st.markdown("#### 📋 Detailed Bus Data")
                    def highlight_voltage(row):
                        if row['vm_pu'] < 0.95: return ['background-color: #ffcccc'] * len(row)
                        if row['vm_pu'] > 1.05: return ['background-color: #ffffcc'] * len(row)
                        return ['background-color: #ccffcc'] * len(row)
                    st.dataframe(bus_results.style.apply(highlight_voltage, axis=1), use_container_width=True)

                with tab3:
                    st.subheader("Line Loading Results")
                    if len(net.res_line) > 0:
                        line_results = net.res_line.copy()
                        line_results['loading_percent'] = line_results['loading_percent'].round(2)
                        st.markdown("#### 📊 Line Loading Profile")
                        colors_l = ['red' if l > 100 else 'orange' if l > 80 else 'green' for l in line_results['loading_percent']]
                        fig_l = go.Figure(go.Bar(
                            x=line_results.index, y=line_results['loading_percent'], marker_color=colors_l,
                            text=line_results['loading_percent'].round(1), textposition='outside',
                            hovertemplate='Line %{x}<br>Loading: %{y:.2f}%<extra></extra>'
                        ))
                        fig_l.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="Capacity Limit (100%)")
                        fig_l.add_hline(y=80,  line_dash="dot",  line_color="orange", annotation_text="Warning Level (80%)")
                        fig_l.update_layout(xaxis_title="Line Index", yaxis_title="Loading (%)", height=400, showlegend=False)
                        st.plotly_chart(fig_l, use_container_width=True)
                        st.markdown("#### 📋 Detailed Line Data")
                        def highlight_loading(row):
                            if row['loading_percent'] > 100: return ['background-color: #ff6666'] * len(row)
                            if row['loading_percent'] > 80:  return ['background-color: #ffff99'] * len(row)
                            return ['background-color: #99ff99'] * len(row)
                        st.dataframe(line_results.style.apply(highlight_loading, axis=1), use_container_width=True)
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
                        pv_results = net.res_sgen.copy()
                        pv_results.insert(0, 'bus_no', net.sgen['bus'].values)
                        pv_results['p_kw'] = (pv_results['p_mw'] * 1000).round(2)
                        pv_results['q_kvar'] = (pv_results['q_mvar'] * 1000).round(2)
                        st.dataframe(pv_results[['bus_no', 'p_mw', 'q_mvar', 'p_kw', 'q_kvar']].reset_index(drop=True), use_container_width=True)
                        st.metric("Total PV Generation", f"{pv_results['p_mw'].sum()*1000:.2f} kW")
                    else:
                        st.info("No PV systems in network")
                    st.markdown("---")
                    if 'storage' in net and len(net.storage) > 0:
                        st.markdown("#### 🔋 Battery Storage")
                        storage_results = net.res_storage.copy()
                        storage_results.insert(0, 'bus_no', net.storage['bus'].values)
                        storage_results['p_kw'] = (storage_results['p_mw'] * 1000).round(2)
                        st.dataframe(storage_results[['bus_no', 'p_mw', 'q_mvar', 'p_kw']].reset_index(drop=True), use_container_width=True)
                        total_sp = storage_results['p_mw'].sum() * 1000
                        if total_sp > 0:   st.metric("Storage Status", "Discharging", f"{total_sp:.2f} kW")
                        elif total_sp < 0: st.metric("Storage Status", "Charging", f"{abs(total_sp):.2f} kW")
                        else:              st.metric("Storage Status", "Idle", "0 kW")
                    else:
                        st.info("No storage systems in network")
                    st.markdown("---")
                    st.markdown("#### ⚖️ Power Balance")
                    col_b1, col_b2, col_b3 = st.columns(3)
                    total_load = net.load['p_mw'].sum() * 1000 if len(net.load) > 0 else 0
                    total_gen  = net.res_sgen['p_mw'].sum() * 1000 if 'sgen' in net and len(net.sgen) > 0 else 0
                    total_stor = net.res_storage['p_mw'].sum() * 1000 if 'storage' in net and len(net.storage) > 0 else 0
                    with col_b1: st.metric("Total Load", f"{total_load:.2f} kW")
                    with col_b2: st.metric("Total Generation", f"{total_gen:.2f} kW")
                    with col_b3: st.metric("Net Power", f"{total_gen + total_stor - total_load:.2f} kW")

            except Exception as pf_error:
                st.error(f"❌ Power flow calculation failed: {str(pf_error)}")
                st.exception(pf_error)

        # ── Solver Mode + Update grid models ─────────────────────────────────
        solver_mode = st.radio("Solver Mode", ["PF", "OPF"], horizontal=True, key="solver_mode_radio")
        use_opf = solver_mode == "OPF"

        if st.button("Update grid models", key="update_grid_button"):
            try:
                if not use_opf:
                    pn.runpp(net)
                    st.session_state.network = net
                    _store_network_plot(net)
                    st.subheader("Interactive Network Diagram")
                    _show_stored_network_plot(height=600)
                    st.success("✅ Power flow updated!")
                else:
                    st.info("OPF mode selected")
                    net.bus["min_vm_pu"] = 0.85
                    net.bus["max_vm_pu"] = 1.15
                    net.ext_grid["min_p_mw"]   = -9999.0
                    net.ext_grid["max_p_mw"]   =  9999.0
                    net.ext_grid["min_q_mvar"] = -9999.0
                    net.ext_grid["max_q_mvar"] =  9999.0

                    if "name" in net.storage.columns:
                        old_mask = net.storage["name"].str.startswith("OPF_Storage", na=False)
                        if old_mask.any():
                            net.storage.drop(net.storage[old_mask].index, inplace=True)
                    if hasattr(net, "poly_cost") and len(net.poly_cost) > 0:
                        net.poly_cost.drop(net.poly_cost.index, inplace=True)

                    for eg_idx in net.ext_grid.index:
                        pn.create_poly_cost(net, eg_idx, "ext_grid", cp1_eur_per_mw=1.0)

                    with st.spinner("Warm-up PF to identify stressed buses..."):
                        pn.runpp(net, verbose=False)

                    vm_deviation = (net.res_bus["vm_pu"] - 1.0).abs()
                    slack_buses  = set(net.ext_grid["bus"].values)
                    candidates   = vm_deviation.drop(
                        index=[b for b in slack_buses if b in vm_deviation.index], errors="ignore"
                    )
                    n_units = min(max(1, len(candidates) // 20), 10)
                    opf_storage_buses = candidates.nlargest(n_units).index.tolist()

                    total_load_mw  = net.load["p_mw"].sum() if len(net.load) > 0 else 1.0
                    per_unit_power = float(np.clip((total_load_mw * 0.3) / max(1, n_units), 0.1, 5.0))

                    opf_storage_indices = []
                    for k, bus in enumerate(opf_storage_buses):
                        idx = pn.create_storage(
                            net, bus=bus, p_mw=0.0,
                            max_e_mwh=per_unit_power * 2.0, q_mvar=0.0,
                            min_p_mw=-per_unit_power, max_p_mw=per_unit_power,
                            min_q_mvar=-per_unit_power, max_q_mvar=per_unit_power,
                            soc_percent=50.0, controllable=True, name=f"OPF_Storage_{k}"
                        )
                        opf_storage_indices.append(idx)

                    for s_idx in opf_storage_indices:
                        pn.create_poly_cost(net, s_idx, "storage", cp1_eur_per_mw=0.0, cp2_eur_per_mw2=1.0)

                    if len(net.load) > 0:
                        net.load["controllable"] = False
                    if len(net.sgen) > 0:
                        net.sgen["controllable"] = False

                    st.info(f"OPF: placed {n_units} storage unit(s) at buses {opf_storage_buses} ({per_unit_power:.2f} MW each).")

                    with st.spinner("Running Optimal Power Flow..."):
                        pn.runopp(net, verbose=False, init="pf", calculate_voltage_angles=False)

                    st.session_state.network = net
                    _store_network_plot(net)
                    st.subheader("Interactive Network Diagram")
                    _show_stored_network_plot(height=600)
                    st.success("✅ Optimal Power Flow converged!")

                    col_o1, col_o2, col_o3, col_o4 = st.columns(4)
                    with col_o1: st.metric("Min Voltage", f"{net.res_bus.vm_pu.min():.4f} p.u.")
                    with col_o2: st.metric("Max Voltage", f"{net.res_bus.vm_pu.max():.4f} p.u.")
                    with col_o3:
                        total_cost = net.res_cost if hasattr(net, 'res_cost') else 0
                        st.metric("Objective Cost", f"{float(total_cost):.4f} €")
                    with col_o4:
                        max_ll_opf = net.res_line.loading_percent.max() if len(net.res_line) > 0 else 0
                        st.metric("Max Line Loading", f"{max_ll_opf:.2f}%")

                    bus_r = net.res_bus.copy()
                    colors_opf = ['red' if v < 0.95 else 'orange' if v > 1.05 else 'green' for v in bus_r['vm_pu']]
                    fig_opf = go.Figure(go.Bar(
                        x=bus_r.index, y=bus_r['vm_pu'], marker_color=colors_opf,
                        hovertemplate='Bus %{x}<br>Voltage: %{y:.4f} p.u.<extra></extra>'
                    ))
                    fig_opf.add_hline(y=1.05, line_dash="dash", line_color="red", annotation_text="Upper Limit (1.05 p.u.)")
                    fig_opf.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Lower Limit (0.95 p.u.)")
                    fig_opf.add_hline(y=1.0,  line_dash="dot",  line_color="gray", annotation_text="Nominal (1.0 p.u.)")
                    fig_opf.update_layout(
                        xaxis_title="Bus Index",
                        yaxis_title="Voltage (p.u.)",
                        yaxis_range=[0.90, 1.10],
                        height=400,
                        showlegend=False,
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig_opf, use_container_width=True)

                    if len(net.storage) > 0:
                        st.markdown("#### 🔋 OPF Storage Dispatch")
                        stor_r = net.res_storage.copy()
                        stor_r.insert(0, 'bus', net.storage['bus'].values)
                        stor_r['name'] = net.storage['name'].values
                        stor_r['p_kw'] = (stor_r['p_mw'] * 1000).round(3)
                        st.dataframe(stor_r[['name', 'bus', 'p_mw', 'q_mvar', 'p_kw']].reset_index(drop=True), use_container_width=True)

            except Exception as e:
                st.error(f"❌ Failed: {str(e)}")
                st.exception(e)
