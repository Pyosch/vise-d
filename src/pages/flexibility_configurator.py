"""Flexibility Configurator page.

Lets users configure a household mix and a flexibility shift level, computes the
aggregate baseline and shifted load profiles from the device-level household
model (same precomputed curves the network page uses), and passes them to the
network scenario page via session state.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.utils import flex_baseload as fb

_SEASON_MAP = {
    "Winter": "winter",
    "Übergang": "transition",
    "Sommer": "summer",
}
def _household_mix_editor(classes: list[str]) -> dict[str, int]:
    """Grouped number-table editor for the household mix.

    Renders one expander per working situation, each holding a data_editor with
    an editable ``Anzahl`` column plus read-only Haushaltsgröße / Automatisierung
    columns (the latter carries the automation-level tooltip on its header).
    Returns ``{class_key: count}`` for all classes (default 0). Counts persist in
    session state across reruns.
    """
    stored = st.session_state.get("flex_cfg_counts", {})
    counts: dict[str, int] = {}

    for work_label, group in fb.group_classes_by_work(classes):
        with st.expander(f"{work_label} ({len(group)} Klassen)", expanded=False):
            comps = {c: fb.class_components_de(c) for c in group}
            df = pd.DataFrame(
                {
                    "Anzahl": [int(stored.get(c, 0)) for c in group],
                    "Haushaltsgröße": [comps[c][1] or "?" for c in group],
                    "Automatisierung": [comps[c][2] or "?" for c in group],
                },
                index=group,
            )
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                key=f"flex_cfg_tbl_{work_label}",
                column_config={
                    "Anzahl": st.column_config.NumberColumn(
                        "Anzahl", min_value=0, step=1
                    ),
                    "Haushaltsgröße": st.column_config.TextColumn(disabled=True),
                    "Automatisierung": st.column_config.TextColumn(
                        disabled=True, help=fb.AUTOMATION_COLUMN_HELP_DE
                    ),
                },
            )
            for c in group:
                counts[c] = int(edited.at[c, "Anzahl"] or 0)

    st.session_state["flex_cfg_counts"] = counts
    return counts


def flexibility_configurator():
    st.title("Flexibilitätskonfigurator")
    from src.content.page_descriptions import render_page_description
    render_page_description("flexibility")
    st.write(
        "Konfigurieren Sie den Haushaltsmix und den Verschiebungsgrad der "
        "gerätescharfen Flexibilität (EV und Wärmepumpe werden separat im "
        "Netzmodell behandelt)."
    )

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
    classes = fb.available_classes(season_key)

    # ------------------------------------------------------------------ #
    # 2. Household mix                                                     #
    # ------------------------------------------------------------------ #
    st.subheader("Haushaltsverteilung")
    st.caption("Anzahl Haushalte je Typologie-Klasse eingeben (gruppiert nach Arbeitsweise).")
    counts = _household_mix_editor(classes)

    total_households = sum(counts.values())
    st.caption(f"Haushalte gesamt: **{total_households}**")

    # ------------------------------------------------------------------ #
    # 3. Flexibility shift level (shared slider)                           #
    # ------------------------------------------------------------------ #
    st.subheader("Flexibilität")
    alpha = fb.verschiebung_slider(key="flex_cfg_alpha")

    # ------------------------------------------------------------------ #
    # 4. Compute profiles                                                  #
    # ------------------------------------------------------------------ #
    if st.button("Lastprofil berechnen", type="primary"):
        active = {cls: n for cls, n in counts.items() if n > 0}
        if not active:
            st.warning("Bitte mindestens eine Haushaltsklasse mit n > 0 eingeben.")
            return

        agg_base, agg_shift = fb.aggregate_mix(active, season_key)
        agg_flex = fb.interpolate(agg_base, agg_shift, alpha)
        index = fb.load_flex_profiles(season_key).index

        baseline_load_df = pd.DataFrame({"p_mw": agg_base / 1000.0}, index=index)
        flex_load_df = pd.DataFrame({"p_mw": agg_flex / 1000.0}, index=index)

        # ---------------------------------------------------------------- #
        # 5. Chart                                                          #
        # ---------------------------------------------------------------- #
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=index, y=agg_base,
            name="Ohne Verschiebung",
            line=dict(color="#2563eb", width=1.5),
        ))
        fig.add_trace(go.Scatter(
            x=index, y=agg_flex,
            name=f"Mit Verschiebung ({alpha * 100:.0f} %)",
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
        peak_base = float(agg_base.max())
        peak_flex = float(agg_flex.max())
        # Energy moved = half the total absolute change (added to valleys = removed from peaks)
        shifted_kwh = float(0.5 * np.abs(agg_flex - agg_base).sum() * 0.25)
        m1, m2, m3 = st.columns(3)
        m1.metric("Spitzenlast (Basis)", f"{peak_base:.1f} kW")
        m2.metric("Spitzenlast (verschoben)", f"{peak_flex:.1f} kW",
                  delta=f"{peak_flex - peak_base:.1f} kW", delta_color="inverse")
        m3.metric("Verschobene Energie", f"{shifted_kwh:.0f} kWh/Woche")

        # ---------------------------------------------------------------- #
        # 7. Session state                                                  #
        # ---------------------------------------------------------------- #
        st.session_state["baseline_load_df"] = baseline_load_df
        st.session_state["flex_scenario_load_df"] = flex_load_df
        st.session_state["flex_alpha"] = alpha

        st.success(f"Lastprofile für {total_households} Haushalte berechnet.")

    # Show navigation button if profiles are available
    if "baseline_load_df" in st.session_state:
        st.divider()
        if st.button("→ Im Netzmodell analysieren", type="secondary"):
            st.switch_page(st.session_state["_page_network_scenario"])
