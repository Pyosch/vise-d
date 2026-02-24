import streamlit as st 
import pandas as pd
import pandapower as pn
import numpy as np
import tempfile
import os
import plotly.graph_objects as go
import plotly.express as px

def Netzberechnung_mit_excel_daten():
    
    st.title('Netzberechnung mit Excel-Daten')

    uploaded_file = st.file_uploader("Laden Sie Ihre Excel-Datei hoch",type=["xlsx","xls"])

    if uploaded_file is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # 1. Load network (only once, then persist in session_state)
            if 'network' not in st.session_state or st.button("🔄 Reload Network from File"):
                net = pn.from_excel(tmp_path)
                st.session_state.network = net
                st.success("✅ Network loaded from Excel!")
            else:
                net = st.session_state.network
                st.info("Using network from session (with any added PV/Storage)")

            # 2. Display network info
            st.write("buses", net.bus.head())
            st.write("lines", net.line.head())
            st.write("loads", net.load.head())
            
            # Check geodata status
            has_geodata = hasattr(net, 'bus_geodata') and len(net.bus_geodata) > 0
            if has_geodata:
                st.success(f"✅ Network has bus coordinates for {len(net.bus_geodata)} buses")
            else:
                st.warning("⚠️ No bus coordinates found in Excel file")
                st.info("💡 Tip: Add a 'bus_geodata' sheet to your Excel with columns: bus, x, y")
            
            # Show what's currently in the network
            if 'sgen' in net and len(net.sgen) > 0:
                st.success(f"🔆 Network contains {len(net.sgen)} PV system(s)")
            if 'storage' in net and len(net.storage) > 0:
                st.success(f"🔋 Network contains {len(net.storage)} storage system(s)")

            st.markdown("---")

            # 3. Check if PV config exists
            if "pv_settings" in st.session_state:
                pv_config = st.session_state.pv_settings
                st.success("✅ PV Configuration found")
                
                # Extract values INSIDE the if block
                modules_per_string = pv_config["PV Modules per String"]
                strings_per_inverter = pv_config["PV Strings per Inverter"]
                
                # Calculate power
                total_panels = modules_per_string * strings_per_inverter
                total_pv_power_kw = total_panels * 0.22
                
                st.info(f"Configured PV System: {total_panels} panels = {total_pv_power_kw:.2f} kW")
                
                # UI to add PV
                with st.expander("Add PV to Network"):
                    selected_bus_pv = st.selectbox("Select bus for PV", net.bus.index.tolist(), key="pv_bus_select")
                    if st.button("Add PV to Network"):
                        pn.create_sgen(
                            net, 
                            bus=selected_bus_pv, 
                            p_mw=total_pv_power_kw/1000,
                            q_mvar=0,
                            name="PV_from_dashboard"
                        )
                        st.session_state.network = net  # Save updated network
                        st.success(f"✅ PV added to bus {selected_bus_pv}! (Persisted in session)")
            else:
                st.warning("⚠️ No PV configured. Please configure PV in 'PV Konfiguration' page first.")

            # 4. Check if storage config exists
            if "electrical_storage" in st.session_state:
                storage_config = st.session_state.electrical_storage
                st.success("✅ Storage Configuration found")
                
                # Extract values INSIDE the if block
                storage_power = storage_config["Max Power"]
                storage_capacity = storage_config["Max Capacity"]
                
                st.info(f"Configured Storage: {storage_power:.2f} kW / {storage_capacity:.2f} kWh")
                
                # UI to add storage
                with st.expander("Add Storage to Network"):
                    selected_bus_storage = st.selectbox("Select bus for storage", net.bus.index.tolist(), key="storage_bus_select")
                    storage_mode = st.radio("Operating mode", ["Charging", "Discharging", "Off"])
                    
                    if st.button("Add Storage to Network"):
                        # Determine power based on mode
                        if storage_mode == "Charging":
                            p_mw = -storage_power / 1000  # Negative for charging
                        elif storage_mode == "Discharging":
                            p_mw = storage_power / 1000  # Positive for discharging
                        else:
                            p_mw = 0
                        
                        pn.create_storage(
                            net, 
                            bus=selected_bus_storage, 
                            p_mw=p_mw,
                            max_e_mwh=storage_capacity/1000,
                            q_mvar=0,
                            soc_percent=50,
                            name="Storage_from_dashboard"
                        )
                        st.session_state.network = net  # Save updated network
                        st.success(f"✅ Storage added to bus {selected_bus_storage} in {storage_mode} mode! (Persisted in session)")
            else:
                st.warning("⚠️ No Storage configured. Please configure storage in 'Elektrischer Speicher' page first.")

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
                            # Create custom color-coded topology plot
                            fig = go.Figure()
                            
                            # Get or generate bus geodata using Köln coordinates
                            if not hasattr(net, 'bus_geodata') or len(net.bus_geodata) == 0:
                                st.info("📍 Using Köln city coordinates for network layout...")
                                num_buses = len(net.bus)
                                
                                # Köln city center coordinates
                                koeln_lon_center = 6.9603  # Longitude (x)
                                koeln_lat_center = 50.9375  # Latitude (y)
                                
                                # Spread buses across ~5km radius (roughly 0.05 degrees)
                                net.bus_geodata = pd.DataFrame(index=net.bus.index)
                                import math
                                
                                # Distribute buses in a grid pattern across Köln
                                grid_size = math.ceil(math.sqrt(num_buses))
                                for i, bus_idx in enumerate(net.bus.index):
                                    row = i // grid_size
                                    col = i % grid_size
                                    
                                    # Spread buses across city (roughly 0.1 degrees = ~10km)
                                    net.bus_geodata.at[bus_idx, 'x'] = koeln_lon_center + (col - grid_size/2) * 0.02
                                    net.bus_geodata.at[bus_idx, 'y'] = koeln_lat_center + (row - grid_size/2) * 0.02
                            
                            bus_geo = net.bus_geodata
                            
                            # Plot lines first (behind buses)
                            if len(net.line) > 0 and len(net.res_line) > 0:
                                for idx in net.line.index:
                                    try:
                                        from_bus = net.line.at[idx, 'from_bus']
                                        to_bus = net.line.at[idx, 'to_bus']
                                        
                                        if from_bus in bus_geo.index and to_bus in bus_geo.index:
                                            x0 = bus_geo.at[from_bus, 'x']
                                            y0 = bus_geo.at[from_bus, 'y']
                                            x1 = bus_geo.at[to_bus, 'x']
                                            y1 = bus_geo.at[to_bus, 'y']
                                            
                                            # Color based on loading
                                            loading = net.res_line.at[idx, 'loading_percent']
                                            if loading > 100:
                                                color, width = 'red', 4
                                            elif loading > 80:
                                                color, width = 'orange', 3
                                            else:
                                                color, width = 'green', 2
                                            
                                            fig.add_trace(go.Scatter(
                                                x=[x0, x1, None],
                                                y=[y0, y1, None],
                                                mode='lines',
                                                line=dict(color=color, width=width),
                                                hovertext=f"Line {idx}<br>Loading: {loading:.1f}%",
                                                hoverinfo='text',
                                                showlegend=False
                                            ))
                                    except (KeyError, IndexError):
                                        continue
                            
                            # Plot buses on top
                            for idx in net.bus.index:
                                try:
                                    if idx in bus_geo.index:
                                        x = bus_geo.at[idx, 'x']
                                        y = bus_geo.at[idx, 'y']
                                        vm = net.res_bus.at[idx, 'vm_pu']
                                        
                                        # Color based on voltage
                                        if vm < 0.95:
                                            color, symbol = 'red', 'square'
                                        elif vm > 1.05:
                                            color, symbol = 'orange', 'diamond'
                                        else:
                                            color, symbol = 'green', 'circle'
                                        
                                        fig.add_trace(go.Scatter(
                                            x=[x], y=[y],
                                            mode='markers+text',
                                            marker=dict(size=12, color=color, symbol=symbol,
                                                      line=dict(width=2, color='white')),
                                            text=str(idx),
                                            textposition='top center',
                                            textfont=dict(size=9),
                                            hovertext=f"Bus {idx}<br>Voltage: {vm:.4f} p.u.",
                                            hoverinfo='text',
                                            showlegend=False
                                        ))
                                except (KeyError, IndexError):
                                    continue
                            
                            fig.update_layout(
                                xaxis=dict(showgrid=False, zeroline=False, visible=False),
                                yaxis=dict(showgrid=False, zeroline=False, visible=False),
                                plot_bgcolor='white',
                                height=600,
                                hovermode='closest',
                                margin=dict(l=0, r=0, t=0, b=0)
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Color legend
                            st.markdown("""
                            **🎨 Color Legend:**
                            - **Buses:** 🟢 Normal (0.95-1.05 p.u.) | 🟠 Overvoltage (>1.05 p.u.) | 🔴 Undervoltage (<0.95 p.u.)
                            - **Lines:** 🟢 Normal (<80%) | 🟠 High loading (80-100%) | 🔴 Overloaded (>100%)
                            """)
                            
                            # Network Status Overview
                            st.markdown("### 📊 Network Status Overview")
                            col_status1, col_status2 = st.columns(2)
                            
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
                            pv_results['p_kw'] = (pv_results['p_mw'] * 1000).round(2)
                            pv_results['q_kvar'] = (pv_results['q_mvar'] * 1000).round(2)
                            st.dataframe(pv_results[['p_mw', 'q_mvar', 'p_kw', 'q_kvar']], use_container_width=True)
                            
                            total_pv_gen = pv_results['p_mw'].sum() * 1000
                            st.metric("Total PV Generation", f"{total_pv_gen:.2f} kW")
                        else:
                            st.info("No PV systems in network")
                        
                        st.markdown("---")
                        
                        # Storage Results
                        if 'storage' in net and len(net.storage) > 0:
                            st.markdown("#### 🔋 Battery Storage")
                            storage_results = net.res_storage.copy()
                            storage_results['p_kw'] = (storage_results['p_mw'] * 1000).round(2)
                            st.dataframe(storage_results, use_container_width=True)
                            
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
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
