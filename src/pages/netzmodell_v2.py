"""Netzmodell-Szenario v2 — WP1: Network source selection & page skeleton.

Foundation page for the consolidated network scenario tool. Subsequent work
packages will add DER configuration (WP2), inline profile generation (WP3),
and the simulation pipeline (WP4).
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta

import pandapower as pp
import pandapower.networks as pn
import streamlit as st

try:
    from pandapower.plotting.plotly import simple_plotly
    _HAS_PLOTLY_NET = True
except Exception:
    _HAS_PLOTLY_NET = False


_NETWORKS: dict[str, callable] = {
    "Einfaches Beispiel": pn.example_simple,
    "Multispannungs-Beispielnetz": pn.example_multivoltage,
    "4-Knoten-Stichleitung": pn.panda_four_load_branch,
    "CIGRE Mittelspannung": pn.create_cigre_network_mv,
    "Kerber Freileitung": pn.create_kerber_landnetz_freileitung_1,
    "Dickert LV Networks": pn.create_dickert_lv_network,
    "IEEE European LV (3-Phase)": pn.ieee_european_lv_asymmetric,
    "MV-Oberrhein": pn.mv_oberrhein,
}


def _show_network(net: pp.pandapowerNet) -> None:
    """Render summary metrics, geodata indicator, and plotly visualization."""
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Knoten", len(net.bus))
    c2.metric("Leitungen", len(net.line))
    c3.metric("Lasten", len(net.load))
    c4.metric("Transformatoren", len(net.trafo))

    has_geodata = hasattr(net, "bus_geodata") and len(net.bus_geodata) > 0
    st.session_state["nsv2_has_geodata"] = has_geodata
    if has_geodata:
        st.success("Geodaten vorhanden — MaStR-Zuweisung möglich (WP2)")
    else:
        st.info("Keine Geodaten — automatisches Knotenlayout für Visualisierung")

    if _HAS_PLOTLY_NET:
        try:
            fig = simple_plotly(net, auto_open=False)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.caption(f"Netzvisualisierung nicht verfügbar: {e}")
            st.dataframe(net.bus, use_container_width=True)
    else:
        st.dataframe(net.bus, use_container_width=True)


def netzmodell_v2():
    st.title("Netzmodell-Szenario")
    st.caption("Entwicklungsversion — WP1: Netzauswahl & Seitenstruktur")

    # ---------------------------------------------------------------------- #
    # Section 1: Netzauswahl                                                  #
    # ---------------------------------------------------------------------- #
    st.subheader("1. Netzauswahl")

    source = st.radio(
        "Netzquelle",
        options=["Vordefiniertes Netz", "Netz hochladen"],
        horizontal=True,
        key="nsv2_source_radio",
    )

    net: pp.pandapowerNet | None = None

    if source == "Vordefiniertes Netz":
        st.session_state["nsv2_net_source"] = "predefined"

        net_name = st.selectbox(
            "Netz auswählen",
            options=list(_NETWORKS.keys()),
            key="nsv2_net_name_select",
        )
        st.session_state["nsv2_net_name"] = net_name

        try:
            net = _NETWORKS[net_name]()
            st.session_state["nsv2_net"] = net
        except Exception as e:
            st.error(f"Netz konnte nicht geladen werden: {e}")
            return

    else:
        st.session_state["nsv2_net_source"] = "upload"

        uploaded = st.file_uploader(
            "Pandapower-Netz hochladen (.json oder .xlsx)",
            type=["json", "xlsx"],
            key="nsv2_file_upload",
        )

        if uploaded is None:
            # Reuse last successfully uploaded net if available.
            if (
                "nsv2_net" in st.session_state
                and st.session_state.get("nsv2_net_source") == "upload"
            ):
                net = st.session_state["nsv2_net"]
                st.caption(
                    f"Zuletzt geladenes Netz: {st.session_state.get('nsv2_net_name', 'Unbekannt')}"
                )
            else:
                st.info(
                    "Bitte eine Netzdatei hochladen "
                    "(pandapower JSON- oder Excel-Export via `pp.to_json()` / `pp.to_excel()`)."
                )
        else:
            try:
                if uploaded.name.endswith(".json"):
                    net = pp.from_json_string(uploaded.getvalue().decode("utf-8"))
                else:
                    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                        tmp.write(uploaded.getvalue())
                        tmp_path = tmp.name
                    try:
                        net = pp.from_excel(tmp_path)
                    finally:
                        os.unlink(tmp_path)

                st.session_state["nsv2_net"] = net
                st.session_state["nsv2_net_name"] = uploaded.name
                st.success(
                    f"Netz geladen: {len(net.bus)} Knoten, {len(net.line)} Leitungen"
                )
            except Exception as e:
                st.error(f"Datei konnte nicht als pandapower-Netz geladen werden: {e}")
                return

    if net is not None:
        _show_network(net)

    # ---------------------------------------------------------------------- #
    # Section 2: Zeitraum                                                     #
    # ---------------------------------------------------------------------- #
    st.subheader("2. Zeitraum")
    st.caption("Wird in WP4 für die Zeitreihensimulation verwendet.")

    col_start, col_end = st.columns(2)
    default_end = datetime.today().date() - timedelta(days=1)
    default_start = default_end - timedelta(days=6)
    time_start = col_start.date_input("Von", value=default_start, key="nsv2_date_start")
    time_end = col_end.date_input("Bis", value=default_end, key="nsv2_date_end")
    st.session_state["nsv2_time_start"] = time_start
    st.session_state["nsv2_time_end"] = time_end

    # ---------------------------------------------------------------------- #
    # Section 3: DER-Konfiguration                                            #
    # ---------------------------------------------------------------------- #
    st.subheader("3. DER-Konfiguration")
    st.info(
        "DER-Konfiguration folgt in WP2 — Penetrationsszenarien (z.B. '40 % der "
        "Haushaltsknoten mit EV'), Namenssuche für gezielte Platzierung und "
        "MaStR-Zuweisung (bei vorhandenen Geodaten)."
    )

    # ---------------------------------------------------------------------- #
    # Section 4: Simulation & Ergebnisse                                      #
    # ---------------------------------------------------------------------- #
    st.subheader("4. Simulation & Ergebnisse")
    st.info("Simulationspipeline (Lastfluss / Zeitreihe) folgt in WP4.")


# ROADMAP: OPF (Optimale Lastflussberechnung)
# - Deprioritized; do not implement until PF pipeline is stable.
# - When implemented: offer PF | OPF->PF (fix dispatch from OPF, run PF for
#   physically consistent results). Do NOT use a silent PF fallback on OPF failure.
# - Before any OPF work: remove the 0.85-1.15 p.u. voltage limit hack and
#   the post-hoc loading normalization from the intern's netzmittimeseries.py.
