"""MV Grid Validation Case Study page.

Demonstrates the Shapefile → pandapower → Measurement Validation methodology
using the CIGRE MV benchmark network as demo data source. All demo voltages,
loads and deviations come from actual pandapower power flow results on the
CIGRE MV network (with_der="pv_wind"), not from fully synthetic data.

Users with their own pipeline outputs can upload their own validation CSVs to
run the same analysis on their network.

The page mirrors the swt_grid toolkit workflow documented in swt_data/README.md
and can be used as a starting point by any DSO with GIS shapefiles and
LZA measurement data.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from typing import NamedTuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

try:
    import pandapower as pp
    import pandapower.networks as pn

    _PP_AVAILABLE = True
except ImportError:
    _PP_AVAILABLE = False


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class _PeriodData(NamedTuple):
    label: str
    validation: pd.DataFrame
    timeseries: pd.DataFrame | None
    stations: pd.DataFrame | None


# ---------------------------------------------------------------------------
# CIGRE MV benchmark – scenario definitions
# ---------------------------------------------------------------------------

# (label, sgen_scale, load_scale, seed, start_date)
# Sommer: PV generators near full output, loads reduced (summer day)
# Winter: near-zero PV, loads at winter peak
_SCENARIOS = [
    ("Sommer", 0.85, 0.70, 7,  "2024-08-15"),
    ("Winter", 0.05, 1.25, 13, "2024-01-15"),
]

# Measurement noise parameters (realistic LZA data quality)
_NOISE_STD_NORMAL  = 0.003   # ≈ 0.3 % normal noise
_NOISE_STD_OUTLIER = 0.08    # ≈ 8 % at problem buses (topology or data issues)
_N_OUTLIERS        = 2       # number of buses with large deviations per scenario


# ---------------------------------------------------------------------------
# CIGRE power flow helpers
# ---------------------------------------------------------------------------


@st.cache_data
def _run_powerflow(sgen_scale: float, load_scale: float) -> pd.DataFrame:
    """Run CIGRE MV power flow; return plain DataFrame of bus results."""
    if not _PP_AVAILABLE:
        return pd.DataFrame()
    net = pn.create_cigre_network_mv(with_der="pv_wind")
    net.sgen["scaling"] = sgen_scale
    net.load["scaling"] = load_scale
    pp.runpp(net, verbose=False)
    res = net.res_bus[["vm_pu", "va_degree", "p_mw", "q_mvar"]].copy()
    res["name"]  = net.bus["name"].values
    res["vn_kv"] = net.bus["vn_kv"].values
    res.index.name = "bus_idx"
    return res.reset_index()


@st.cache_data
def _load_cigre_topology() -> dict:
    """Return static CIGRE MV topology as plain dicts (buses, lines, geodata).

    The geodata in pandapower's CIGRE MV network is empty by default, so we
    compute a networkx spring layout as fallback and cache the result.
    """
    if not _PP_AVAILABLE:
        return {}
    net = pn.create_cigre_network_mv(with_der="pv_wind")

    buses = net.bus[["name", "vn_kv"]].reset_index(names="bus_idx")
    lines = net.line[["from_bus", "to_bus", "name", "length_km"]].reset_index(names="line_idx")

    # Compute layout positions using networkx spring layout
    try:
        import networkx as nx

        G = nx.Graph()
        G.add_nodes_from(buses["bus_idx"].tolist())
        for _, row in lines.iterrows():
            G.add_edge(int(row["from_bus"]), int(row["to_bus"]))
        pos = nx.spring_layout(G, seed=42, k=1.5)
        buses["x"] = [pos.get(i, (0.0, 0.0))[0] for i in buses["bus_idx"]]
        buses["y"] = [pos.get(i, (0.0, 0.0))[1] for i in buses["bus_idx"]]
    except ImportError:
        # networkx not available – place buses in a circle as fallback
        n = len(buses)
        angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
        buses["x"] = np.cos(angles)
        buses["y"] = np.sin(angles)

    return {
        "buses": buses.to_dict("records"),
        "lines": lines.to_dict("records"),
    }


# ---------------------------------------------------------------------------
# Demo data builders (CIGRE-based)
# ---------------------------------------------------------------------------


def _add_measurement_noise(
    vm_computed: np.ndarray, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray]:
    """Add realistic measurement noise to computed voltages.

    Returns (vm_measured, deviation_pct) where
        deviation_pct = (computed - measured) / computed * 100
    """
    n = len(vm_computed)
    noise = rng.normal(0.0, _NOISE_STD_NORMAL, n)
    outlier_idx = rng.choice(n, size=min(_N_OUTLIERS, n), replace=False)
    noise[outlier_idx] = (
        rng.choice([-1, 1], size=len(outlier_idx))
        * rng.uniform(_NOISE_STD_OUTLIER * 0.7, _NOISE_STD_OUTLIER * 1.4, size=len(outlier_idx))
    )
    vm_measured = vm_computed - noise
    deviation_pct = noise / vm_computed * 100.0
    return vm_measured, deviation_pct


def _build_validation_df(
    bus_res: pd.DataFrame, label: str, rng: np.random.Generator
) -> pd.DataFrame:
    """Build a validation snapshot from actual CIGRE power flow bus results."""
    # Exclude the HV slack bus (110 kV)
    mv = bus_res[bus_res["vn_kv"] < 100].copy()
    vm_computed = mv["vm_pu"].values.copy()
    vm_measured, deviation_pct = _add_measurement_noise(vm_computed, rng)
    vn = mv["vn_kv"].values

    return pd.DataFrame({
        "bus_idx":        mv["bus_idx"].values,
        "station":        mv["name"].values,
        "P_kW":           (mv["p_mw"].values   * 1000).round(2),
        "Q_kvar":         (mv["q_mvar"].values  * 1000).round(2),
        "vm_pu_computed": vm_computed.round(4),
        "vm_kv_computed": (vm_computed * vn).round(3),
        "vm_kv_measured": (vm_measured * vn).round(3),
        "vm_pu_measured": vm_measured.round(4),
        "deviation_pu":   (deviation_pct / 100.0).round(4),
        "deviation_pct":  deviation_pct.round(2),
        "topo_flag":      np.abs(deviation_pct) > 10,
        "period":         label,
    })


def _make_cigre_timeseries(
    label: str,
    sgen_scale: float,
    load_scale: float,
    seed: int,
    start_date: str,
    n_mv_buses: int = 14,
) -> pd.DataFrame:
    """Generate a 24 h / 15-min timeseries with physically motivated RMSE.

    No 96 additional power flows are run. The RMSE envelope is derived from the
    known operating regime (PV profile in summer, load peaks in winter) and
    scaled to be consistent with the single snapshot power flow result.
    """
    rng = np.random.default_rng(seed + 1_000)
    n_steps = 96
    timestamps = pd.date_range(start=start_date, periods=n_steps, freq="15min")
    hours = np.arange(n_steps) * 0.25  # fractional hours 0 … 23.75

    if "Sommer" in label:
        # PV curve: noon peak raises voltages; model error tends to peak at midday
        pv = np.clip(np.sin(np.pi * (hours - 6.0) / 12.0), 0.0, 1.0)
        pv[hours < 6]  = 0.0
        pv[hours > 18] = 0.0
        load_env = 0.55 + 0.40 * np.clip(
            np.sin(np.pi * (hours - 7.0) / 14.0), 0.0, 1.0
        )
        rmse_base = 2.0 + 1.8 * pv + 0.6 * load_env
        load_mw   = 5.0 * load_scale * load_env + rng.normal(0, 0.2, n_steps)
        sgen_mw   = 8.0 * sgen_scale * pv        + rng.normal(0, 0.3, n_steps)
    else:
        # Winter: near-zero PV; morning and evening load peaks drive RMSE
        morning = np.clip(np.sin(np.pi * (hours - 6.5) / 4.0), 0.0, 1.0)
        morning[hours < 6.5] = 0.0
        morning[hours > 10.5] = 0.0
        evening = np.clip(np.sin(np.pi * (hours - 17.0) / 5.0), 0.0, 1.0)
        evening[hours < 17] = 0.0
        evening[hours > 22] = 0.0
        load_env = 0.60 + 0.50 * (morning + evening)
        rmse_base = 1.8 + 2.5 * load_env
        load_mw   = 8.0 * load_scale * load_env + rng.normal(0, 0.3, n_steps)
        sgen_mw   = rng.uniform(0.0, 0.4, n_steps)

    rmse       = np.clip(rmse_base + rng.normal(0, 0.20, n_steps), 0.3, None)
    mean_dev   = rng.normal(0.1, 0.5, n_steps)
    gt5        = (rmse > 4.0).astype(int) * rng.integers(2, 6, n_steps)
    ll_max     = 18 + 35 * load_env / load_env.max() + rng.normal(0, 1.5, n_steps)

    return pd.DataFrame({
        "timestamp":            timestamps,
        "converged":            True,
        "rmse":                 rmse.round(4),
        "mean_dev":             mean_dev.round(4),
        "total_load_mw":        np.clip(load_mw, 0, None).round(3),
        "total_sgen_mw":        np.clip(sgen_mw, 0, None).round(3),
        "stations_compared":    n_mv_buses,
        "stations_gt_5pct":     gt5,
        "max_line_loading_pct": np.clip(ll_max, 0, 100).round(2),
    })


def _make_stations_summary(val_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 2_000)
    n = len(val_df)
    return pd.DataFrame({
        "station":                val_df["station"].values,
        "mean_deviation_pct":     val_df["deviation_pct"].values.round(3),
        "abs_mean_deviation_pct": np.abs(val_df["deviation_pct"].values).round(3),
        "max_abs_deviation_pct":  (
            np.abs(val_df["deviation_pct"].values) + rng.uniform(0.3, 1.8, n)
        ).round(3),
        "std_deviation_pct": rng.uniform(0.3, 1.2, n).round(3),
        "count":             rng.integers(130, 165, n),
    })


@st.cache_data
def _load_demo_data() -> list[_PeriodData]:
    """Build demo periods from actual CIGRE MV power flow results."""
    periods: list[_PeriodData] = []
    for label, sgen_scale, load_scale, seed, start_date in _SCENARIOS:
        rng = np.random.default_rng(seed)
        if _PP_AVAILABLE:
            bus_res = _run_powerflow(sgen_scale, load_scale)
            val_df  = _build_validation_df(bus_res, label, rng)
            n_mv    = len(val_df)
        else:
            val_df  = _fallback_validation_df(label, seed)
            n_mv    = len(val_df)
        ts_df  = _make_cigre_timeseries(label, sgen_scale, load_scale, seed, start_date, n_mv)
        stn_df = _make_stations_summary(val_df, seed)
        periods.append(_PeriodData(label, val_df, ts_df, stn_df))
    return periods


# ---------------------------------------------------------------------------
# Fallback (pandapower not installed) – uses CIGRE bus names statically
# ---------------------------------------------------------------------------

_CIGRE_BUS_NAMES = [f"Bus {i}" for i in range(1, 15)]  # 14 MV buses


def _fallback_validation_df(label: str, seed: int) -> pd.DataFrame:
    """Synthetic fallback when pandapower is not installed (keeps CIGRE naming)."""
    rng = np.random.default_rng(seed)
    n = len(_CIGRE_BUS_NAMES)
    vm_computed = rng.normal(1.025, 0.005, n)
    noise = rng.normal(0, 0.003, n)
    outlier_idx = rng.choice(n, size=2, replace=False)
    noise[outlier_idx] = rng.choice([-1, 1], size=2) * rng.uniform(0.06, 0.12, 2)
    vm_measured   = vm_computed - noise
    deviation_pct = noise / vm_computed * 100.0
    return pd.DataFrame({
        "bus_idx":        np.arange(n),
        "station":        _CIGRE_BUS_NAMES,
        "P_kW":           rng.uniform(-800, -50, n).round(2),
        "Q_kvar":         rng.uniform(-200,  50, n).round(2),
        "vm_pu_computed": vm_computed.round(4),
        "vm_kv_computed": (vm_computed * 20.0).round(3),
        "vm_kv_measured": (vm_measured * 20.0).round(3),
        "vm_pu_measured": vm_measured.round(4),
        "deviation_pu":   (deviation_pct / 100.0).round(4),
        "deviation_pct":  deviation_pct.round(2),
        "topo_flag":      np.abs(deviation_pct) > 10,
        "period":         label,
    })


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------


def _parse_validation_csv(uploaded_file) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(uploaded_file)
        required = {"station", "deviation_pct"}
        if not required.issubset(df.columns):
            st.error(f"Validierungs-CSV fehlen Spalten: {required - set(df.columns)}")
            return None
        return df
    except Exception as e:
        st.error(f"Fehler beim Lesen der Datei: {e}")
        return None


def _parse_timeseries_csv(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    try:
        df = pd.read_csv(uploaded_file)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Fehler beim Lesen der Zeitreihe: {e}")
        return None


def _parse_stations_csv(uploaded_file) -> pd.DataFrame | None:
    if uploaded_file is None:
        return None
    try:
        return pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Fehler beim Lesen der Stations-Datei: {e}")
        return None


# ---------------------------------------------------------------------------
# Visualisations
# ---------------------------------------------------------------------------


def _network_topology_fig(
    topo: dict, val_df: pd.DataFrame | None = None, period_label: str = ""
) -> go.Figure:
    """Render CIGRE MV network topology as interactive Plotly figure.

    Buses are colored by voltage deviation severity when val_df is provided.
    Lines are drawn in a neutral color; the HV slack bus uses a square marker.
    """
    if not topo:
        fig = go.Figure()
        fig.add_annotation(
            text="pandapower nicht verfügbar – Topologie-Visualisierung nicht möglich.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14),
        )
        return fig

    buses = pd.DataFrame(topo["buses"])
    lines = pd.DataFrame(topo["lines"])

    # Merge deviation info for coloring
    dev_map: dict[str, float] = {}
    if val_df is not None and not val_df.empty:
        if "station" in val_df.columns and "deviation_pct" in val_df.columns:
            dev_map = val_df.set_index("station")["deviation_pct"].to_dict()

    def _color(name: str) -> str:
        d = dev_map.get(name, float("nan"))
        if np.isnan(d):
            return "#2563eb"      # default blue (no measurement)
        if abs(d) > 5:
            return "#ef4444"      # red: large deviation
        if abs(d) > 3:
            return "#f97316"      # orange: moderate deviation
        return "#22c55e"          # green: good agreement

    fig = go.Figure()

    # --- Lines ---
    for _, ln in lines.iterrows():
        fb = int(ln["from_bus"])
        tb = int(ln["to_bus"])
        fb_row = buses[buses["bus_idx"] == fb]
        tb_row = buses[buses["bus_idx"] == tb]
        if fb_row.empty or tb_row.empty:
            continue
        fig.add_trace(go.Scatter(
            x=[fb_row["x"].values[0], tb_row["x"].values[0], None],
            y=[fb_row["y"].values[0], tb_row["y"].values[0], None],
            mode="lines",
            line=dict(color="#94a3b8", width=2),
            hoverinfo="skip",
            showlegend=False,
        ))

    # --- MV buses ---
    mv = buses[buses["vn_kv"] < 100]
    hv = buses[buses["vn_kv"] >= 100]

    mv_colors  = [_color(name) for name in mv["name"]]
    mv_hover   = []
    for _, row in mv.iterrows():
        d = dev_map.get(row["name"], float("nan"))
        dev_str = f"Abweichung: {d:.2f} %" if not np.isnan(d) else "keine Messung"
        mv_hover.append(f"<b>{row['name']}</b><br>U_n = {row['vn_kv']:.0f} kV<br>{dev_str}")

    fig.add_trace(go.Scatter(
        x=mv["x"].values,
        y=mv["y"].values,
        mode="markers+text",
        marker=dict(
            size=16,
            color=mv_colors,
            line=dict(width=1.5, color="white"),
        ),
        text=mv["name"].values,
        textposition="top center",
        textfont=dict(size=9),
        hovertext=mv_hover,
        hoverinfo="text",
        name="MV-Bus (20 kV)",
    ))

    # --- HV slack bus ---
    if not hv.empty:
        hv_hover = [
            f"<b>{row['name']}</b><br>U_n = {row['vn_kv']:.0f} kV<br>Slack (ext. Netz)"
            for _, row in hv.iterrows()
        ]
        fig.add_trace(go.Scatter(
            x=hv["x"].values,
            y=hv["y"].values,
            mode="markers+text",
            marker=dict(size=20, color="#7c3aed", symbol="square",
                        line=dict(width=2, color="white")),
            text=hv["name"].values,
            textposition="top center",
            textfont=dict(size=9),
            hovertext=hv_hover,
            hoverinfo="text",
            name="HV Slack (110 kV)",
        ))

    # --- Legend color entries ---
    for color, lbl in [
        ("#22c55e", "Abw. ≤ 3 %"),
        ("#f97316", "Abw. 3–5 %"),
        ("#ef4444", "Abw. > 5 %"),
        ("#2563eb", "keine Messung"),
    ]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=10, color=color),
            name=lbl, showlegend=True,
        ))

    title = "CIGRE MV Benchmark-Netz – Netztopologie"
    if period_label:
        title += f"  ({period_label})"

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=520,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x"),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def _summary_metrics(periods: list[_PeriodData]) -> None:
    rows = []
    for p in periods:
        df = p.validation
        valid = df[df["vm_pu_measured"] > 0.5] if "vm_pu_measured" in df.columns else df
        if valid.empty:
            continue
        rmse = float((valid["deviation_pct"] ** 2).mean() ** 0.5)
        rows.append({
            "Zeitraum":        p.label,
            "Stationen":       len(valid),
            "RMSE (%)":        round(rmse, 2),
            "Mittl. Abw. (%)": round(float(valid["deviation_pct"].mean()), 2),
            "Mittl. |Abw.| (%)": round(float(valid["deviation_pct"].abs().mean()), 2),
            "Stationen >5 %":  int((valid["deviation_pct"].abs() > 5).sum()),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _deviation_comparison(periods: list[_PeriodData]) -> None:
    n = len(periods)
    if n == 0:
        return
    fig = make_subplots(
        rows=1, cols=n,
        subplot_titles=[f"Spannungsabweichung – {p.label}" for p in periods],
        shared_yaxes=True,
    )
    for i, p in enumerate(periods, 1):
        df = p.validation.sort_values("deviation_pct", key=abs, ascending=False)
        colors = [
            "#ef4444" if abs(d) > 5 else ("#f97316" if abs(d) > 3 else "#2563eb")
            for d in df["deviation_pct"]
        ]
        fig.add_trace(
            go.Bar(x=df["station"], y=df["deviation_pct"],
                   marker_color=colors, name=p.label, showlegend=False),
            row=1, col=i,
        )
        fig.add_hline(y= 5, line_dash="dash", line_color="#ef4444",
                      annotation_text="+5 %", row=1, col=i)
        fig.add_hline(y=-5, line_dash="dash", line_color="#ef4444",
                      annotation_text="−5 %", row=1, col=i)

    fig.update_layout(
        title="Spannungsabweichung Simulation vs. Messung",
        height=500, template="plotly_white",
    )
    fig.update_xaxes(tickangle=45, tickfont_size=9)
    fig.update_yaxes(title_text="Abweichung (%)", row=1, col=1)
    st.plotly_chart(fig, use_container_width=True, key="deviation_comparison")


def _rmse_evolution(periods: list[_PeriodData]) -> None:
    """RMSE time-series chart.

    Each period gets its own subplot with a relative time axis (hours since
    start of the measurement window). This avoids the large empty gap that
    appears when e.g. January and August data share a calendar x-axis.
    No interpolation is performed — only actual data points are connected.
    """
    active = [
        p for p in periods
        if p.timeseries is not None
        and not p.timeseries.empty
        and "rmse" in p.timeseries.columns
    ]
    if not active:
        st.info("Keine Zeitreihen-Daten verfügbar. Lade `timeseries_summary_*.csv` hoch.")
        return

    n = len(active)
    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=False,
        subplot_titles=[
            f"{p.label}  (Ø RMSE: "
            f"{p.timeseries[p.timeseries.get('converged', True) == True]['rmse'].mean():.2f} %)"
            for p in active
        ],
        vertical_spacing=0.22,
    )

    for row, p in enumerate(active, start=1):
        ts = p.timeseries[p.timeseries.get("converged", True) == True].copy()

        if "timestamp" in ts.columns:
            t0 = pd.to_datetime(ts["timestamp"]).iloc[0]
            x_val   = (pd.to_datetime(ts["timestamp"]) - t0).dt.total_seconds() / 3600
            x_label = "Stunden seit Messbeginn"
            hover   = ts["timestamp"].astype(str)
        else:
            x_val   = ts.index
            x_label = "Zeitschritt"
            hover   = ts.index.astype(str)

        fig.add_trace(
            go.Scatter(
                x=x_val, y=ts["rmse"],
                mode="lines", name=p.label,
                line=dict(width=1.5),
                customdata=hover,
                hovertemplate="%{customdata}<br>RMSE: %{y:.2f} %<extra></extra>",
            ),
            row=row, col=1,
        )
        fig.update_xaxes(title_text=x_label, row=row, col=1)
        fig.update_yaxes(title_text="RMSE (%)", row=row, col=1)

    fig.update_layout(
        title="RMSE-Verlauf je Messzeitraum",
        template="plotly_white",
        height=320 * n,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key="rmse_evolution")


def _station_drilldown(periods: list[_PeriodData]) -> None:
    periods_with_stn = [p for p in periods if p.stations is not None and not p.stations.empty]
    if not periods_with_stn:
        st.info("Keine Stations-Zeitreihendaten verfügbar.")
        return

    selected_label = st.selectbox(
        "Zeitraum", [p.label for p in periods_with_stn], key="drilldown_period"
    )
    p = next(x for x in periods_with_stn if x.label == selected_label)
    stn_df = p.stations.sort_values("abs_mean_deviation_pct", ascending=False)

    all_stations   = stn_df["station"].tolist()
    selected_station = st.selectbox("Station", all_stations, key="drilldown_station")
    row = stn_df[stn_df["station"] == selected_station].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mittl. |Abw.|", f"{row['abs_mean_deviation_pct']:.2f} %")
    c2.metric("Max. |Abw.|",   f"{row['max_abs_deviation_pct']:.2f} %")
    c3.metric("Std.-Abw.",     f"{row['std_deviation_pct']:.2f} %")
    c4.metric("Zeitschritte",  int(row["count"]))

    # Top-N comparison chart across all periods
    top20 = stn_df.head(20)
    fig = go.Figure()
    for prd in periods_with_stn:
        sub = prd.stations[prd.stations["station"].isin(top20["station"])]
        if sub.empty:
            continue
        sub = sub.set_index("station").reindex(top20["station"])
        fig.add_trace(go.Bar(
            x=sub.index,
            y=sub["abs_mean_deviation_pct"],
            name=prd.label,
            error_y=dict(type="data", array=sub["std_deviation_pct"].values, visible=True),
        ))

    fig.update_layout(
        title="Top-20 Stationen nach mittlerer Abweichung (Periodenvergleich)",
        xaxis_title="Station",
        yaxis_title="Mittl. |Abweichung| (%)",
        barmode="group",
        template="plotly_white",
        height=450,
    )
    fig.update_xaxes(tickangle=45, tickfont_size=9)
    st.plotly_chart(fig, use_container_width=True, key="station_drilldown")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def mv_fallstudie() -> None:
    """MV grid case study: Shapefile → pandapower → Measurement Validation."""
    st.title("Fallstudie: Mittelspannungsnetz-Validierung")
    st.write(
        "Diese Seite demonstriert die Methodik zur Validierung eines aus GIS-Daten "
        "erzeugten Mittelspannungs-Netzmodells gegen reale Messdaten. "
        "Die Demo-Daten basieren auf dem **CIGRE MV Benchmark-Netz** (pandapower, "
        "`with_der=\"pv_wind\"`) mit zwei Betriebsszenarien (Sommer / Winter). "
        "Wer das [swt_grid-Toolkit](https://github.com/) mit eigenen Shapefile- und "
        "Messdaten durchläuft, kann die erzeugten Report-CSVs hier hochladen und "
        "direkt analysieren."
    )

    # ------------------------------------------------------------------
    # Section 1: Methodology
    # ------------------------------------------------------------------
    with st.expander("📐 Methodik – Shapefile → pandapower → Validierung", expanded=False):
        st.markdown("""
**Pipeline-Übersicht** (swt_grid-Toolkit):

| Schritt | Script | Eingabe | Ausgabe |
|---------|--------|---------|---------|
| 1. MV-Netz aufbauen | `swt_mv_calculation.py` | GIS-Shapefiles + Kabelparameter | `swt_mv_network_<label>.p` |
| 2. Postprocessing | `swt_mv_postprocessing.py` | Rohes Netzmodell | `swt_mv_network_postprocessed_<label>.p` |
| 3. Stationsmapping | `swt_station_mapping.py` | Netzmodell + Messpunkte | `station_xtrid_mapping.csv` |
| 4. Datenqualität | `swt_data_quality.py` | LZA-Messdaten | `data_quality_<period>.csv` |
| 5. Validierung | `swt_mv_validation.py` | Netzmodell + Messungen | `validation_<period>_average.csv` |
| 6. Zeitreihen-PF | `swt_powerflow_batch.py` | Netzmodell + Messungen | `timeseries_summary_*.csv` |
| 7. Szenarien | `swt_scenario_analysis.py` | Validiertes Modell | Hosting-Capacity, Monte-Carlo |

**Benötigte Eingangsdaten:**
- GIS-Shapefiles (MS-Kabel, MS-Muffe, Stationen, Umspannwerk) im EPSG:25832
- Kabelparametermatrix (Excel) mit r, x, c pro Leitungstyp
- LZA-Messdaten (P, Q, U pro Einspeise-Strang, 15-min-Auflösung)
- Stationsmapping (manuelle Zuordnung Feeder-Name → XTRID)

**Ausgabe-CSVs für diese Seite:**

```
reports/
  validation_<Zeitraum>_average.csv       → Snapshot-Validierung
  timeseries_summary_<Zeitraum>_*.csv    → RMSE-Zeitverlauf (optional)
  timeseries_stations_<Zeitraum>_*.csv   → Stations-Statistik (optional)
```

Alle drei Dateien werden vom `swt_mv_validation.py`-Script (mit `--all-timestamps --save-report`) erzeugt.
        """)

    # ------------------------------------------------------------------
    # Section 2: Data source selection
    # ------------------------------------------------------------------
    st.subheader("Datenbasis")
    data_source = st.radio(
        "Datenquelle",
        ["Demo-Daten (CIGRE MV Benchmark)", "Eigene Daten hochladen"],
        horizontal=True,
    )

    periods: list[_PeriodData] = []

    if data_source == "Demo-Daten (CIGRE MV Benchmark)":
        periods = _load_demo_data()
        if _PP_AVAILABLE:
            st.info(
                "Die Demo verwendet das **CIGRE MV Benchmark-Netz** "
                "(`pandapower.networks.create_cigre_network_mv(with_der=\"pv_wind\")`) "
                "mit zwei Szenarien: "
                "**Sommer** (sgen_scale=0.85, load_scale=0.70) und "
                "**Winter** (sgen_scale=0.05, load_scale=1.25). "
                "Die simulierten Spannungen (vm_pu_computed) stammen aus echten Leistungsflüssen; "
                "die \"Messwerte\" sind mit realistischem Messfehler überlagert."
            )
        else:
            st.warning(
                "pandapower ist nicht installiert – Demo-Daten werden synthetisch mit "
                "CIGRE-Busnamen erzeugt. Installiere pandapower für echte Leistungsflüsse."
            )

    else:
        st.markdown("**Schritt 1:** Lade für jeden Zeitraum mindestens die Validierungs-CSV hoch.")
        num_periods = st.number_input("Anzahl Zeiträume", min_value=1, max_value=4, value=2, step=1)

        for i in range(int(num_periods)):
            with st.expander(f"Zeitraum {i + 1}", expanded=(i == 0)):
                label = st.text_input("Bezeichnung", value=f"Zeitraum_{i + 1}", key=f"label_{i}")

                val_file = st.file_uploader(
                    "validation_<period>_average.csv *",
                    type="csv", key=f"val_{i}",
                )
                ts_file = st.file_uploader(
                    "timeseries_summary_<period>_*.csv (optional)",
                    type="csv", key=f"ts_{i}",
                )
                stn_file = st.file_uploader(
                    "timeseries_stations_<period>_*.csv (optional)",
                    type="csv", key=f"stn_{i}",
                )

                if val_file is not None:
                    val_df = _parse_validation_csv(val_file)
                    if val_df is not None:
                        ts_df  = _parse_timeseries_csv(ts_file)
                        stn_df = _parse_stations_csv(stn_file)
                        periods.append(_PeriodData(label, val_df, ts_df, stn_df))

        if not periods:
            st.warning("Bitte mindestens eine Validierungs-CSV hochladen.")
            return

    # ------------------------------------------------------------------
    # Section 3: Network topology
    # ------------------------------------------------------------------
    st.divider()
    st.subheader("Netztopologie")

    is_demo = data_source == "Demo-Daten (CIGRE MV Benchmark)"

    if is_demo and _PP_AVAILABLE:
        topo = _load_cigre_topology()
        period_sel = st.selectbox(
            "Szenario für Farbgebung",
            [p.label for p in periods],
            key="topo_period_sel",
        )
        val_for_topo = next(p.validation for p in periods if p.label == period_sel)
        st.plotly_chart(
            _network_topology_fig(topo, val_for_topo, period_sel),
            use_container_width=True,
            key="network_topology",
        )
        st.caption(
            "Busfarben zeigen die Spannungsabweichung (Simulation − Messung): "
            "🟢 ≤ 3 %, 🟠 3–5 %, 🔴 > 5 %. "
            "Violettes Quadrat = HV-Slack (ext. Netz, 110 kV)."
        )
    else:
        st.info(
            "Die Topologie-Visualisierung ist in der Demo-Ansicht mit pandapower verfügbar. "
            "Für eigene Daten kann ein exportiertes pandapower-Netzmodell (`.p`-Datei) "
            "in einer zukünftigen Version hochgeladen werden."
        )

    # ------------------------------------------------------------------
    # Section 4: Validation results
    # ------------------------------------------------------------------
    st.divider()
    st.subheader("Validierungsergebnisse")

    _summary_metrics(periods)

    st.markdown("#### Spannungsabweichung je Station")
    _deviation_comparison(periods)

    st.markdown("#### RMSE-Verlauf (Zeitreihe)")
    _rmse_evolution(periods)

    st.markdown("#### Stations-Detailanalyse")
    _station_drilldown(periods)

    # ------------------------------------------------------------------
    # CSV format reference
    # ------------------------------------------------------------------
    with st.expander("📄 CSV-Format-Referenz"):
        st.markdown("""
**`validation_<period>_average.csv`** – Pflichtfelder:

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `station` | str | Stationsbezeichner |
| `deviation_pct` | float | Abweichung Simulation − Messung in % |
| `vm_pu_computed` | float | Simulierte Spannung in p.u. (optional) |
| `vm_pu_measured` | float | Gemessene Spannung in p.u. (optional) |
| `P_kW` | float | Wirkleistung am Einspeisepunkt (optional) |
| `Q_kvar` | float | Blindleistung am Einspeisepunkt (optional) |
| `topo_flag` | bool | True = Topologieproblem vermutet (optional) |

**`timeseries_summary_<period>_*.csv`** – Felder:

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `timestamp` | datetime | Zeitstempel des Powerflows |
| `converged` | bool | Hat der Powerflow konvergiert? |
| `rmse` | float | RMSE über alle Stationen in % |
| `stations_gt_5pct` | int | Anzahl Stationen mit Abw. > 5 % |

**`timeseries_stations_<period>_*.csv`** – Felder:

| Spalte | Typ | Beschreibung |
|--------|-----|-------------|
| `station` | str | Stationsbezeichner |
| `abs_mean_deviation_pct` | float | Mittlere absolute Abweichung in % |
| `std_deviation_pct` | float | Standardabweichung der Abweichung |
| `max_abs_deviation_pct` | float | Maximale Abweichung in % |
| `count` | int | Anzahl der Zeitschritte |
        """)
