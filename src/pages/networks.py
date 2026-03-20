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

# Disable auto-opening of plots in browser
pio.renderers.default = "json"
os.environ["BROWSER"] = "none"  # Prevent browser from opening

def Netzberechnung():
    
    st.title('Netzberechnung')

    # Network Source Selection
    st.markdown("### 🔌 Network Source")
    network_source = st.radio(
        "Choose how to load your network:",
        ["Upload Excel File", "Select Predefined Network"],
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
    
    else:  # Select Predefined Network
        st.markdown("### 📚 Predefined Network Templates")
        networks = [
            'Keine Auswahl', 
            'Einfaches Beispiel', 
            'Multispannungs-Beispielnetz', 
            '4-Knoten-Stickleitung', 
            'CIGRE Niederspannungsnetz',
            'Kerber freileitung_1',
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
                elif selected_network == '4-Knoten-Stickleitung':
                    net = ppn.panda_four_load_branch()
                elif selected_network == 'CIGRE Niederspannungsnetz':
                    net = ppn.create_cigre_network_mv()
                elif selected_network == 'Kerber freileitung_1':
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

        st.markdown("---")

        st.markdown("### Additional Demand Inputs")

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

        # 5. Run Power Flow
        if st.button("Run Power Flow"):
            try:
                pn.runpp(net)
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

                        # st.markdown("""
                        # **🎨 Color Legend:**
                        # - **Buses:** 🔵 Normal (0.95–1.05 p.u.) | 🟠 Overvoltage (>1.05 p.u.) | 🔴 Undervoltage (<0.95 p.u.)
                        # - **Lines:** 🟢 Normal (<80%) | 🟠 High (80–100%) | 🔴 Overloaded (>100%)
                        # - **Transformers (dashed):** 🔵 Normal | 🟠 High | 🔴 Overloaded
                        # """)
                        
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
                        st.metric("Min Voltage", f"{min_voltage:.4f} p.u.", 
                                 delta=f"{(min_voltage-1)*100:.2f}%",
                                 delta_color="inverse")
                    
                    with col2:
                        max_voltage = net.res_bus['vm_pu'].max()
                        st.metric("Max Voltage", f"{max_voltage:.4f} p.u.",
                                 delta=f"{(max_voltage-1)*100:.2f}%",
                                 delta_color="normal" if max_voltage > 1 else "inverse")
                    
                    with col3:
                        max_loading = net.res_line['loading_percent'].max() if len(net.res_line) > 0 else 0
                        st.metric("Max Line Loading", f"{max_loading:.2f}%",
                                 delta="Overload!" if max_loading > 100 else "OK",
                                 delta_color="inverse" if max_loading > 100 else "normal")
                    
                    with col4:
                        total_loss = net.res_line['pl_mw'].sum() if len(net.res_line) > 0 else 0
                        st.metric("Total Losses", f"{total_loss*1000:.2f} kW")
                
                with tab2:
                    st.subheader("Bus Voltage Results")
                    bus_results = net.res_bus.copy()
                    bus_results['vm_pu'] = bus_results['vm_pu'].round(4)
                    bus_results['va_degree'] = bus_results['va_degree'].round(2)
                    
                    # Create voltage profile chart
                    st.markdown("#### 📊 Voltage Profile")
                    fig_voltage = go.Figure()
                    
                    # Add voltage bars
                    colors = ['red' if v < 0.95 else 'orange' if v > 1.05 else 'green' 
                             for v in bus_results['vm_pu']]
                    
                    fig_voltage.add_trace(go.Bar(
                        x=bus_results.index,
                        y=bus_results['vm_pu'],
                        marker_color=colors,
                        name='Bus Voltage',
                        text=bus_results['vm_pu'].round(4),
                        textposition='outside',
                        hovertemplate='Bus %{x}<br>Voltage: %{y:.4f} p.u.<extra></extra>'
                    ))
                    
                    # Add limit lines
                    fig_voltage.add_hline(y=1.05, line_dash="dash", line_color="red", 
                                        annotation_text="Upper Limit (1.05 p.u.)",
                                        annotation_position="right")
                    fig_voltage.add_hline(y=0.95, line_dash="dash", line_color="red",
                                        annotation_text="Lower Limit (0.95 p.u.)",
                                        annotation_position="right")
                    fig_voltage.add_hline(y=1.0, line_dash="dot", line_color="gray",
                                        annotation_text="Nominal (1.0 p.u.)",
                                        annotation_position="right")
                    
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
                    
                    # Highlight voltage violations
                    def highlight_voltage(row):
                        if row['vm_pu'] < 0.95:
                            return ['background-color: #ffcccc'] * len(row)
                        elif row['vm_pu'] > 1.05:
                            return ['background-color: #ffffcc'] * len(row)
                        else:
                            return ['background-color: #ccffcc'] * len(row)
                    
                    styled_bus = bus_results.style.apply(highlight_voltage, axis=1)
                    st.dataframe(styled_bus, use_container_width=True)
                    
                    # Voltage violation warnings
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
                        
                        # Create line loading chart
                        st.markdown("#### 📊 Line Loading Profile")
                        fig_loading = go.Figure()
                        
                        # Add loading bars
                        colors = ['red' if l > 100 else 'orange' if l > 80 else 'green' 
                                 for l in line_results['loading_percent']]
                        
                        fig_loading.add_trace(go.Bar(
                            x=line_results.index,
                            y=line_results['loading_percent'],
                            marker_color=colors,
                            name='Line Loading',
                            text=line_results['loading_percent'].round(1),
                            textposition='outside',
                            hovertemplate='Line %{x}<br>Loading: %{y:.2f}%<extra></extra>'
                        ))
                        
                        # Add limit lines
                        fig_loading.add_hline(y=100, line_dash="dash", line_color="red",
                                            annotation_text="Capacity Limit (100%)",
                                            annotation_position="right")
                        fig_loading.add_hline(y=80, line_dash="dot", line_color="orange",
                                            annotation_text="Warning Level (80%)",
                                            annotation_position="right")
                        
                        fig_loading.update_layout(
                            xaxis_title="Line Index",
                            yaxis_title="Loading (%)",
                            height=400,
                            showlegend=False,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig_loading, use_container_width=True)
                        
                        st.markdown("#### 📋 Detailed Line Data")
                        
                        # Highlight overloaded lines
                        def highlight_loading(row):
                            if row['loading_percent'] > 100:
                                return ['background-color: #ff6666'] * len(row)
                            elif row['loading_percent'] > 80:
                                return ['background-color: #ffff99'] * len(row)
                            else:
                                return ['background-color: #99ff99'] * len(row)
                        
                        styled_line = line_results.style.apply(highlight_loading, axis=1)
                        st.dataframe(styled_line, use_container_width=True)
                        
                        # Overload warnings
                        overloaded = line_results['loading_percent'] > 100
                        if overloaded.any():
                            st.error(f"🚨 {overloaded.sum()} line(s) overloaded: {line_results[overloaded].index.tolist()}")
                        else:
                            st.success("✅ All lines within capacity")
                    else:
                        st.info("No line results available")
                
                with tab4:
                    st.subheader("Distributed Energy Resources (DER) Results")
                    
                    # PV Results
                    if 'sgen' in net and len(net.sgen) > 0:
                        st.markdown("#### ☀️ PV Generation")
                        pv_results = net.res_sgen.copy()
                        pv_results.insert(0, 'bus_no', net.sgen['bus'].values)
                        pv_results['p_kw'] = (pv_results['p_mw'] * 1000).round(2)
                        pv_results['q_kvar'] = (pv_results['q_mvar'] * 1000).round(2)
                        st.dataframe(pv_results[['bus_no', 'p_mw', 'q_mvar', 'p_kw', 'q_kvar']].reset_index(drop=True), use_container_width=True)
                        
                        total_pv_gen = pv_results['p_mw'].sum() * 1000
                        st.metric("Total PV Generation", f"{total_pv_gen:.2f} kW")
                    else:
                        st.info("No PV systems in network")
                    
                    st.markdown("---")
                    
                    # Storage Results
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
                    
                    # Power Balance
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
