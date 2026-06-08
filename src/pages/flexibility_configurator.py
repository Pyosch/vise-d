"""Flexibility Configurator page.

Lets users configure a household mix and flexibility participation rate,
computes aggregate baseline and flexibility-scenario load profiles, and
passes them to the network scenario page via session state.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config.paths import DATA_DIR

_PROFILES_DIR = DATA_DIR / "flexibility_profiles"
_SEASON_MAP = {
    "Winter": "winter",
    "Übergang": "transition",
    "Sommer": "summer",
}
_TOP_CLASSES_N = 4  # show this many classes outside the expander


@st.cache_data
def _load_profiles(season_key: str) -> pd.DataFrame:
    path = _PROFILES_DIR / f"load_profiles_{season_key}.csv"
    return pd.read_csv(path, index_col="timestamp", parse_dates=True)


@st.cache_data
def _load_flex_summary() -> pd.DataFrame:
    return pd.read_csv(_PROFILES_DIR / "flexibility_summary.csv")


def _get_classes(df: pd.DataFrame) -> list[str]:
    return sorted(set(c.split("__")[0] for c in df.columns if "__" in c))


def _display_name(cls: str) -> str:
    return cls.replace("_", " ").title()


def _shiftable_kwh_per_hh(flex_df: pd.DataFrame) -> dict[str, float]:
    """Total shiftable kWh/week per typology class (sum over all devices)."""
    grouped = flex_df.groupby("typology_class")["mean_shiftable_kwh"].sum()
    return grouped.to_dict()


def flexibility_configurator():
    st.title("Flexibilitätskonfigurator")
    from src.content.page_descriptions import render_page_description
    render_page_description("flexibility")
    st.write(
        "Konfigurieren Sie den Haushaltsmix und die Flexibilitätsquote für ein Netzgebiet."
    )

    flex_df = _load_flex_summary()
    shiftable_per_class = _shiftable_kwh_per_hh(flex_df)

    # ------------------------------------------------------------------ #
    # 1. Season selection                                                  #
    # ------------------------------------------------------------------ #
    season_label = st.radio(
        "Jahreszeit",
        options=list(_SEASON_MAP.keys()),
        horizontal=True,
        index=1,
    )
    season_key = _SEASON_MAP[season_label]
    load_df = _load_profiles(season_key)
    classes = _get_classes(load_df)

    # ------------------------------------------------------------------ #
    # 2. Household mix                                                     #
    # ------------------------------------------------------------------ #
    st.subheader("Haushaltsverteilung")
    counts: dict[str, int] = {}

    top_classes = classes[:_TOP_CLASSES_N]
    other_classes = classes[_TOP_CLASSES_N:]

    cols = st.columns(2)
    for i, cls in enumerate(top_classes):
        with cols[i % 2]:
            counts[cls] = st.number_input(
                _display_name(cls),
                min_value=0,
                value=10,
                step=1,
                key=f"hh_{cls}",
            )

    with st.expander(f"Weitere Klassen ({len(other_classes)})"):
        other_cols = st.columns(2)
        for i, cls in enumerate(other_classes):
            with other_cols[i % 2]:
                counts[cls] = st.number_input(
                    _display_name(cls),
                    min_value=0,
                    value=0,
                    step=1,
                    key=f"hh_{cls}",
                )

    total_households = sum(counts.values())
    st.caption(f"Haushalte gesamt: **{total_households}**")

    # ------------------------------------------------------------------ #
    # 3. Flexibility participation rate                                    #
    # ------------------------------------------------------------------ #
    st.subheader("Flexibilität")
    participation_pct = st.slider(
        "Anteil flexibler Haushalte",
        min_value=0,
        max_value=100,
        value=20,
        step=5,
        format="%d%%",
    )
    participation_rate = participation_pct / 100.0

    # ------------------------------------------------------------------ #
    # 4. Compute profiles                                                  #
    # ------------------------------------------------------------------ #
    if st.button("Lastprofil berechnen", type="primary"):
        active_classes = {cls: n for cls, n in counts.items() if n > 0}

        if not active_classes:
            st.warning("Bitte mindestens eine Haushaltsklasse mit n > 0 eingeben.")
            return

        # Baseline: sum(count × mean_power_kw) per class → MW
        baseline_kw = pd.Series(0.0, index=load_df.index)
        for cls, n in active_classes.items():
            col = f"{cls}__mean_power_kw"
            if col in load_df.columns:
                baseline_kw = baseline_kw + n * load_df[col]

        baseline_load_df = pd.DataFrame({"p_mw": baseline_kw / 1000.0}, index=load_df.index)

        # Flexibility reduction: participation_rate × count × shiftable_kwh_per_hh / 168 h
        flex_reduction_kw = 0.0
        for cls, n in active_classes.items():
            kwh_per_hh = shiftable_per_class.get(cls, 0.0)
            flex_reduction_kw += participation_rate * n * kwh_per_hh / 168.0

        flex_load_df = pd.DataFrame(
            {"p_mw": (baseline_kw - flex_reduction_kw).clip(lower=0) / 1000.0},
            index=load_df.index,
        )

        # ---------------------------------------------------------------- #
        # 5. Chart                                                          #
        # ---------------------------------------------------------------- #
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=baseline_load_df.index,
            y=baseline_load_df["p_mw"] * 1000,
            name="Basis-Lastprofil",
            line=dict(color="#2563eb", width=1.5),
        ))
        fig.add_trace(go.Scatter(
            x=flex_load_df.index,
            y=flex_load_df["p_mw"] * 1000,
            name=f"Flexibilitätsszenario ({participation_pct} %)",
            line=dict(color="#16a34a", width=1.5, dash="dash"),
        ))
        fig.update_layout(
            title="Wöchentliches Lastprofil (15-Min-Auflösung)",
            xaxis_title="Zeitstempel",
            yaxis_title="Leistung (kW)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        # ---------------------------------------------------------------- #
        # 6. Metrics                                                        #
        # ---------------------------------------------------------------- #
        m1, m2, m3 = st.columns(3)
        peak_kw = float(baseline_load_df["p_mw"].max() * 1000)
        avg_kw = float(baseline_load_df["p_mw"].mean() * 1000)
        shiftable_total_kwh = flex_reduction_kw * 168.0
        m1.metric("Spitzenlast (Basis)", f"{peak_kw:.1f} kW")
        m2.metric("Durchschnittslast", f"{avg_kw:.1f} kW")
        m3.metric("Verschiebbare Energie", f"{shiftable_total_kwh:.0f} kWh/Woche")

        # ---------------------------------------------------------------- #
        # 7. Session state                                                  #
        # ---------------------------------------------------------------- #
        st.session_state["baseline_load_df"] = baseline_load_df
        st.session_state["flex_scenario_load_df"] = flex_load_df
        st.session_state["participation_rate"] = participation_rate

        st.success(f"Lastprofile für {total_households} Haushalte berechnet.")

    # Show navigation button if profiles are available
    if "baseline_load_df" in st.session_state:
        st.divider()
        if st.button("→ Im Netzmodell analysieren", type="secondary"):
            st.switch_page(st.session_state["_page_network_scenario"])



