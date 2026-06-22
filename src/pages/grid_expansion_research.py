"""Research results page — Grid Expansion Costs (Lilienkamp et al.).

Displays research findings from:
'Flexibility in electricity wholesale markets and distribution grids:
An integrated model and its application to electric vehicles in Germany'
Arne Lilienkamp, Nils Namockel, Oliver Ruhnau

Author: Pyosch
AI Assistance: Antigravity (Claude Sonnet 4.6)
"""

__author__ = "Pyosch"

import streamlit as st


def grid_expansion_research():
    """Display research results for the Lilienkamp et al. grid expansion paper."""

    # ── Paper header ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1a2a4a 0%, #2d4a7a 100%);
            border-radius: 12px;
            padding: 32px 36px 28px 36px;
            margin-bottom: 28px;
        ">
            <p style="
                color: #8ab4f8;
                font-size: 0.78rem;
                font-weight: 600;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin: 0 0 10px 0;
            ">Forschungsergebnis · Veröffentlichte Studie</p>
            <h1 style="
                color: #ffffff;
                font-size: 1.55rem;
                font-weight: 700;
                line-height: 1.4;
                margin: 0 0 18px 0;
            ">
                Flexibility in Electricity Wholesale Markets and Distribution Grids:
                An Integrated Model and Its Application to Electric Vehicles in Germany
            </h1>
            <p style="
                color: #b0c8f0;
                font-size: 0.95rem;
                margin: 0 0 6px 0;
            ">
                <span style="font-weight: 600;">Arne Lilienkamp &nbsp;·&nbsp;
                Nils Namockel &nbsp;·&nbsp; Oliver Ruhnau</span>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Abstract ──────────────────────────────────────────────────────────────
    st.markdown("### Abstract")

    st.markdown(
        """
        <div style="
            background-color: #f8fafc;
            border-left: 4px solid #2d4a7a;
            border-radius: 0 8px 8px 0;
            padding: 22px 26px;
            margin-bottom: 28px;
            color: #1e293b;
            font-size: 0.97rem;
            line-height: 1.75;
        ">
            <p style="margin: 0 0 14px 0;">
                The ongoing transition of our energy systems implies a rise of distributed generators,
                batteries, and new consumers, including electric vehicles and heat pumps. Previous studies
                have found that distributed flexibility may substantially benefit wholesale electricity
                markets, but have neglected that these benefits may be subject to distribution grid
                constraints.
            </p>
            <p style="margin: 0 0 14px 0;">
                Here, we propose using a <strong>virtual storage approach</strong> to aggregate the net
                load and flexibility of individual consumers at the distribution grid level, subject to
                the corresponding grid constraints. We apply our approach to flexible electric vehicle
                charging scenarios in German distribution grids for the years <strong>2030</strong> and
                <strong>2045</strong>.
            </p>
            <p style="margin: 0 0 14px 0;">
                Our results suggest that distributed flexibility <em>exacerbates</em> distribution grid
                congestion if it only follows wholesale market prices. However, there may be the
                potential to alleviate local congestion with stable wholesale market benefits of
                distributed flexibility.
            </p>
            <p style="margin: 0;">
                Local coordination of distributed flexibility appears to be able to resolve distribution
                grid constraints at substantially lower costs than expanding transformer capacity. We
                conclude that <strong>local coordination mechanisms are key</strong> to unlocking the
                wholesale market benefits of distributed flexibility while mitigating hazards in the
                distribution grids.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Key findings pills ────────────────────────────────────────────────────
    st.markdown("### Key Findings")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;
                        padding:16px;text-align:center;height:130px;display:flex;
                        flex-direction:column;justify-content:center;">
                <div style="font-size:1.6rem;margin-bottom:6px;">⚡</div>
                <div style="font-size:0.85rem;color:#92400e;font-weight:600;line-height:1.4;">
                    Uncoordinated flexibility worsens distribution grid congestion
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
                        padding:16px;text-align:center;height:130px;display:flex;
                        flex-direction:column;justify-content:center;">
                <div style="font-size:1.6rem;margin-bottom:6px;">🔗</div>
                <div style="font-size:0.85rem;color:#166534;font-weight:600;line-height:1.4;">
                    Local coordination resolves congestion more cost-effectively than grid expansion
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
                        padding:16px;text-align:center;height:130px;display:flex;
                        flex-direction:column;justify-content:center;">
                <div style="font-size:1.6rem;margin-bottom:6px;">📈</div>
                <div style="font-size:0.85rem;color:#1e40af;font-weight:600;line-height:1.4;">
                    Wholesale market benefits remain stable with local coordination
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Results: bar charts from analyze_grid_expansion_costs.py ─────────────
    st.markdown("### Results")

    _FIGS = "Analysis_expansion_costs/figures"

    # 1. Cost comparison
    st.markdown("#### System Costs and Grid Expansion Costs by Scenario")
    st.image(
        f"{_FIGS}/cost_comparison.jpg",
        use_container_width=True,
    )
    st.caption(
        "Comparison of system costs (congestion-related) and grid expansion costs "
        "across five scenarios for 2030 and 2045. Each bar pair shows the trade-off "
        "between allowing more flexibility (reducing wholesale costs) and the resulting "
        "investment needed to reinforce the distribution grid."
    )

    st.markdown("---")

    # 2. Expansion by cause (PV vs EV stacked)
    st.markdown("#### Required Grid Expansion by Cause — PV vs. EV Charging")
    st.image(
        f"{_FIGS}/eval_expansion.jpg",
        use_container_width=True,
    )
    st.caption(
        "Stacked bar chart showing the total additional grid capacity (GW) required "
        "in each scenario, broken down by the driving cause: photovoltaic feed-in (PV) "
        "and electric vehicle charging load (EV). Scenarios without flexibility coordination "
        "show significantly higher expansion requirements."
    )

    st.markdown("---")

    # 3. Combined capacity + cost overview
    st.markdown("#### Combined Overview: Expansion Capacity and Costs")
    st.image(
        f"{_FIGS}/expansion_costs_cap.jpg",
        use_container_width=True,
    )
    st.caption(
        "Side-by-side comparison of required grid expansion capacity (left) and "
        "associated expansion costs (right) across all five scenarios. "
        "The figure illustrates that local flexibility coordination can substantially "
        "reduce both the physical grid reinforcement needed and the associated investment costs."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Real-World Implications ───────────────────────────────────────────────
    st.markdown("### Real-World Implications")
    st.markdown(
        """
        The model employs deterministic optimization under perfect foresight, meaning results should be
        interpreted as techno-economic potentials rather than precise real-world predictions. In practice,
        imperfect foresight will likely reduce the scheduling efficiency of EV flexibility, though EVs could
        also yield additional benefits not captured here — such as balancing renewable forecast errors or
        reducing suppliers' market power. The grid-constrained model runs represent a benchmark of perfectly
        efficient local coordination, achievable in theory through mechanisms such as redispatch or dynamic
        spatially varying grid fees. However, both approaches face significant real-world barriers: redispatch
        requires detailed grid and asset information alongside central controllability, while efficient dynamic
        grid fees demand precise knowledge of wholesale prices and consumer responsiveness. Germany's current
        time-of-use grid fees illustrate these limitations — they provide average incentives but cannot respond
        to stochastic load variations or address heterogeneity between individual transformers. As a result,
        real-world distribution grid adjustments and associated costs are likely to exceed the model's estimates,
        and the fragmented nature of distribution grids suggests that local coordination may remain imperfect
        for the foreseeable future.
        """
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Geographic Distribution ───────────────────────────────────────────────
    st.markdown("### Geographic Distribution")
    st.markdown(
        "The maps below show how grid expansion requirements and their driving causes "
        "are distributed across Germany's NUTS3 districts for each modelled scenario."
    )

    # 1. Expansion GW heatmaps
    st.markdown("#### Grid Expansion Requirement by District (GW)")
    st.image(
        "Analysis_expansion_costs/figures/expansion_heat_maps.jpg",
        use_container_width=True,
    )
    st.caption(
        "Choropleth maps showing the required grid expansion in GW per NUTS3 district "
        "across all five scenarios. Darker shading indicates districts with greater "
        "need for transformer and line reinforcement."
    )

    st.markdown("---")

    # 2. Expansion cause heatmaps
    st.markdown("#### Expansion Driver by District — PV vs. EV Share")
    st.image(
        "Analysis_expansion_costs/figures/expansion_heat_maps_cause.jpg",
        use_container_width=True,
    )
    st.caption(
        "Choropleth maps showing which factor primarily drives grid expansion in each "
        "district: photovoltaic feed-in (green) or electric vehicle charging load (red). "
        "Districts coloured towards green are predominantly solar-driven; those towards "
        "red are predominantly EV-driven."
    )

    st.markdown("---")

    # 3. Merged combined heatmaps
    st.markdown("#### Combined Overview: Expansion and Driver — All Scenarios")
    st.image(
        "Analysis_expansion_costs/figures/expansion_heat_maps_merged.jpg",
        use_container_width=True,
    )
    st.caption(
        "Merged view combining both the expansion magnitude (GW) and the expansion "
        "driver (PV vs. EV share) side by side for all five scenarios. This provides "
        "a complete district-level picture of where and why grid investment is needed."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Interactive Map ───────────────────────────────────────────────────────
    st.markdown("### Interactive Grid Expansion Map")
    st.markdown(
        "Use the dropdown menu in the top-left corner of the map to switch between the five scenarios "
        "and choose either the **Grid Expansion [GW]** layer or the **Expansion Driver (PV vs. EV share)** layer. "
        "Hover over individual districts to see details, and zoom or pan to explore regions."
    )

    @st.cache_resource
    def load_interactive_map_v2():
        import plotly.io as pio
        return pio.read_json("Analysis_expansion_costs/figures/interactive_expansion_map.json")

    try:
        with st.spinner("Loading interactive map (this may take a few seconds on first load)..."):
            fig_map = load_interactive_map_v2()
            st.plotly_chart(fig_map, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading interactive map: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Conclusion ────────────────────────────────────────────────────────────
    st.markdown("### Conclusion")
    st.markdown(
        """
        While prior studies showed that distributed flexibility can substantially benefit wholesale electricity
        markets, they overlooked distribution grid constraints. This study fills that gap using an enhanced
        virtual storage approach integrated into a wholesale market model. Applied to EV flexibility in Germany,
        the findings show that grid constraints limit not only flexible EV charging but also inflexible charging
        and PV feed-in, with PV curtailment being particularly significant. Flexible EV charging based purely
        on wholesale prices causes herding behaviour — load peaks during low-price hours — though this effect
        is reduced in the integrated model, as shifting load raises prices until equilibrium is reached. The
        resulting local grid adjustments are frequent and sizeable, yet their wholesale market impact is minor,
        since charging can be shifted to adjacent hours with comparable benefits. Crucially, the costs of
        managing distribution grid congestion are an order of magnitude lower than those of full grid expansion,
        suggesting that locally coordinated distributed flexibility is a more cost-effective path forward.
        Effective local coordination — using either price or volume signals and accounting for both generation
        and load constraints alongside wholesale market outcomes — is therefore essential to unlocking the full
        potential of distributed flexibility without compromising grid security.
        """
    )

    # ── Footer logos ──────────────────────────────────────────────────────────
    st.markdown("---")
    footer_cols = st.columns(2)

    with footer_cols[0]:
        st.markdown(
            """
            <div style="background-color:white;padding:10px;text-align:center;border-radius:15px;">
                <img src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/10/VISE_D_neu-1024x470.png"
                    alt="VISE-D Logo" style="width:auto;height:100px;">
            </div>
            """,
            unsafe_allow_html=True,
        )

    with footer_cols[1]:
        st.markdown(
            """
            <div style="background-color:white;padding:10px;text-align:center;border-radius:15px;">
                <img src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/01/Logo_MWIKEPixel.png"
                    alt="MWIKE Logo" style="width:auto;height:70px;">
            </div>
            """,
            unsafe_allow_html=True,
        )
