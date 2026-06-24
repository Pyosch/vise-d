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
from PIL import Image as _PILImage

# The research figures are large, trusted renders shipped with the repo. Lift
# Pillow's decompression-bomb guard (default ~89.5 MP) so st.image() does not
# emit a DecompressionBombWarning when loading them.
_PILImage.MAX_IMAGE_PIXELS = None


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

    # ── Link to publication ───────────────────────────────────────────────────
    st.markdown(
        '<p style="margin: -8px 0 28px 0; font-size: 0.95rem;">'
        '🔗 <a href="https://www.ewi.uni-koeln.de/de/publikationen/'
        "flexibility-in-electricity-wholesale-markets-and-distribution-grids-an-"
        "integrated-model-and-its-application-to-electric-vehicles-in-germany/\" "
        'target="_blank" rel="noopener noreferrer" '
        'style="color: #2d4a7a; font-weight: 600; text-decoration: none;">'
        "Zur Veröffentlichung (EWI – Energiewirtschaftliches Institut, "
        "Universität zu Köln)</a></p>",
        unsafe_allow_html=True,
    )

    # ── Abstract ──────────────────────────────────────────────────────────────
    st.markdown("### Zusammenfassung")

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
                Der fortschreitende Umbau unserer Energiesysteme bringt eine Zunahme dezentraler
                Erzeuger, Batterien und neuer Verbraucher mit sich, darunter Elektrofahrzeuge und
                Wärmepumpen. Frühere Studien haben gezeigt, dass dezentrale Flexibilität den
                Stromgroßhandelsmärkten einen erheblichen Nutzen bringen kann, dabei jedoch
                vernachlässigt, dass dieser Nutzen durch Restriktionen der Verteilnetze begrenzt
                sein könnte.
            </p>
            <p style="margin: 0 0 14px 0;">
                Wir schlagen einen <strong>virtuellen Speicheransatz</strong> vor, um die Netzlast
                und Flexibilität einzelner Verbraucher auf Ebene des Verteilnetzes – unter
                Berücksichtigung der entsprechenden Netzrestriktionen – zu aggregieren. Wir wenden
                unseren Ansatz auf Szenarien für flexibles Laden von Elektrofahrzeugen in deutschen
                Verteilnetzen für die Jahre <strong>2030</strong> und <strong>2045</strong> an.
            </p>
            <p style="margin: 0 0 14px 0;">
                Unsere Ergebnisse deuten darauf hin, dass dezentrale Flexibilität Engpässe im
                Verteilnetz <em>verschärft</em>, wenn sie ausschließlich den Großhandelspreisen
                folgt. Es besteht jedoch möglicherweise das Potenzial, lokale Engpässe zu verringern,
                während der Nutzen dezentraler Flexibilität für den Großhandelsmarkt stabil bleibt.
            </p>
            <p style="margin: 0;">
                Eine lokale Koordination dezentraler Flexibilität scheint in der Lage zu sein,
                Restriktionen im Verteilnetz zu deutlich geringeren Kosten zu beheben als ein Ausbau
                der Transformatorkapazität. Wir schlussfolgern, dass <strong>lokale
                Koordinationsmechanismen entscheidend sind</strong>, um den Großhandelsnutzen
                dezentraler Flexibilität zu erschließen und zugleich Gefahren in den Verteilnetzen
                zu mindern.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Key findings pills ────────────────────────────────────────────────────
    st.markdown("### Zentrale Erkenntnisse")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;
                        padding:16px;text-align:center;height:130px;display:flex;
                        flex-direction:column;justify-content:center;">
                <div style="font-size:1.6rem;margin-bottom:6px;">⚡</div>
                <div style="font-size:0.85rem;color:#92400e;font-weight:600;line-height:1.4;">
                    Unkoordinierte Flexibilität verschärft Engpässe im Verteilnetz
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
                    Lokale Koordination behebt Engpässe kostengünstiger als ein Netzausbau
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
                    Der Nutzen für den Großhandelsmarkt bleibt bei lokaler Koordination stabil
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Results: bar charts from analyze_grid_expansion_costs.py ─────────────
    st.markdown("### Ergebnisse")

    _FIGS = "Analysis_expansion_costs/figures"

    # 1. Cost comparison
    st.markdown("#### Systemkosten und Netzausbaukosten nach Szenario")
    st.image(
        f"{_FIGS}/cost_comparison.jpg",
        use_column_width=True,
    )
    st.caption(
        "Vergleich der (engpassbedingten) Systemkosten und der Netzausbaukosten über fünf "
        "Szenarien für 2030 und 2045. Jedes Balkenpaar zeigt den Zielkonflikt zwischen mehr "
        "zugelassener Flexibilität (geringere Großhandelskosten) und den daraus resultierenden "
        "Investitionen, die zur Verstärkung des Verteilnetzes erforderlich sind."
    )

    st.markdown("---")

    # 2. Expansion by cause (PV vs EV stacked)
    st.markdown("#### Erforderlicher Netzausbau nach Ursache — PV vs. E-Fahrzeug-Laden")
    st.image(
        f"{_FIGS}/eval_expansion.jpg",
        use_column_width=True,
    )
    st.caption(
        "Gestapeltes Balkendiagramm der gesamten zusätzlich erforderlichen Netzkapazität (GW) "
        "je Szenario, aufgeschlüsselt nach Ursache: Photovoltaik-Einspeisung (PV) und Ladelast "
        "von Elektrofahrzeugen (E-Fahrzeuge). Szenarien ohne Flexibilitätskoordination weisen "
        "einen deutlich höheren Ausbaubedarf auf."
    )

    st.markdown("---")

    # 3. Combined capacity + cost overview
    st.markdown("#### Kombinierte Übersicht: Ausbaukapazität und Kosten")
    st.image(
        f"{_FIGS}/expansion_costs_cap.jpg",
        use_column_width=True,
    )
    st.caption(
        "Gegenüberstellung der erforderlichen Netzausbaukapazität (links) und der damit "
        "verbundenen Ausbaukosten (rechts) über alle fünf Szenarien. Die Abbildung verdeutlicht, "
        "dass eine lokale Flexibilitätskoordination sowohl die physische Netzverstärkung als auch "
        "die damit verbundenen Investitionskosten erheblich verringern kann."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Real-World Implications ───────────────────────────────────────────────
    st.markdown("### Praktische Implikationen")
    st.markdown(
        """
        <div style="
            background-color: #fffbeb;
            border-left: 4px solid #d97706;
            border-radius: 0 8px 8px 0;
            padding: 22px 26px;
            margin-bottom: 28px;
            color: #1e293b;
            font-size: 0.97rem;
            line-height: 1.75;
        ">
            <p style="margin: 0 0 14px 0;">
                Das Modell verwendet eine <strong>deterministische Optimierung unter vollständiger
                Voraussicht</strong>, sodass die Ergebnisse als techno-ökonomische Potenziale und
                nicht als präzise Vorhersagen der Realität zu verstehen sind. In der Praxis wird
                eine unvollständige Voraussicht die Einsatzeffizienz der Flexibilität von
                Elektrofahrzeugen voraussichtlich verringern, wobei Elektrofahrzeuge auch hier nicht
                erfasste zusätzliche Vorteile bringen könnten — etwa den Ausgleich von Prognosefehlern
                erneuerbarer Energien oder die Verringerung der Marktmacht von Anbietern.
            </p>
            <p style="margin: 0 0 14px 0;">
                Die netzrestringierten Modellläufe stellen einen Referenzwert für eine perfekt
                effiziente lokale Koordination dar, der theoretisch über Mechanismen wie Redispatch
                oder dynamische, räumlich variierende Netzentgelte erreichbar ist. Beide Ansätze
                stoßen in der Praxis jedoch auf erhebliche Hürden: Redispatch erfordert detaillierte
                Netz- und Anlageninformationen sowie eine zentrale Steuerbarkeit, während effiziente
                dynamische Netzentgelte eine präzise Kenntnis der Großhandelspreise und der
                Reaktionsbereitschaft der Verbraucher voraussetzen.
            </p>
            <p style="margin: 0;">
                Die derzeitigen <strong>zeitvariablen Netzentgelte</strong> in Deutschland
                verdeutlichen diese Grenzen — sie bieten durchschnittliche Anreize, können jedoch
                nicht auf stochastische Lastschwankungen reagieren oder die Heterogenität einzelner
                Transformatoren berücksichtigen. Folglich dürften die tatsächlichen Anpassungen der
                Verteilnetze und die damit verbundenen Kosten die Modellschätzungen übersteigen, und
                die fragmentierte Struktur der Verteilnetze legt nahe, dass die lokale Koordination
                auf absehbare Zeit unvollständig bleiben könnte.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Geographic Distribution ───────────────────────────────────────────────
    st.markdown("### Geografische Verteilung")
    st.markdown(
        "Die nachstehenden Karten zeigen, wie sich der Netzausbaubedarf und seine Ursachen "
        "über die NUTS3-Kreise Deutschlands für jedes modellierte Szenario verteilen."
    )

    # 1. Expansion GW heatmaps
    st.markdown("#### Netzausbaubedarf nach Kreis (GW)")
    st.image(
        "Analysis_expansion_costs/figures/expansion_heat_maps.jpg",
        use_column_width=True,
    )
    st.caption(
        "Choroplethenkarten des erforderlichen Netzausbaus in GW je NUTS3-Kreis über alle fünf "
        "Szenarien. Dunklere Schattierungen kennzeichnen Kreise mit höherem Bedarf an "
        "Transformator- und Leitungsverstärkung."
    )

    st.markdown("---")

    # 2. Expansion cause heatmaps
    st.markdown("#### Ausbautreiber nach Kreis — Anteil PV vs. E-Fahrzeuge")
    st.image(
        "Analysis_expansion_costs/figures/expansion_heat_maps_cause.jpg",
        use_column_width=True,
    )
    st.caption(
        "Choroplethenkarten, die zeigen, welcher Faktor den Netzausbau in jedem Kreis "
        "überwiegend antreibt: Photovoltaik-Einspeisung (grün) oder Ladelast von "
        "Elektrofahrzeugen (rot). Kreise mit grüner Färbung sind überwiegend solargetrieben, "
        "jene mit roter Färbung überwiegend durch Elektrofahrzeuge getrieben."
    )

    st.markdown("---")

    # 3. Merged combined heatmaps
    st.markdown("#### Kombinierte Übersicht: Ausbau und Treiber — alle Szenarien")
    st.image(
        "Analysis_expansion_costs/figures/expansion_heat_maps_merged.jpg",
        use_column_width=True,
    )
    st.caption(
        "Zusammengeführte Ansicht, die das Ausmaß des Ausbaus (GW) und den Ausbautreiber "
        "(Anteil PV vs. E-Fahrzeuge) für alle fünf Szenarien nebeneinander darstellt. Dies "
        "liefert ein vollständiges Bild auf Kreisebene, wo und warum Netzinvestitionen "
        "erforderlich sind."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Interactive Map ───────────────────────────────────────────────────────
    st.markdown("### Interaktive Netzausbaukarte")
    st.markdown(
        "Verwenden Sie das Dropdown-Menü oben links in der Karte, um zwischen den fünf Szenarien "
        "zu wechseln und entweder die Ebene **Netzausbau [GW]** oder die Ebene "
        "**Ausbautreiber (Anteil PV vs. E-Fahrzeuge)** auszuwählen. Bewegen Sie den Mauszeiger "
        "über einzelne Kreise, um Details anzuzeigen, und zoomen oder verschieben Sie die Ansicht, "
        "um Regionen zu erkunden."
    )

    @st.cache_resource
    def load_interactive_map_v2():
        import plotly.io as pio
        return pio.read_json("Analysis_expansion_costs/figures/interactive_expansion_map.json")

    try:
        with st.spinner("Interaktive Karte wird geladen (kann beim ersten Laden einige Sekunden dauern)..."):
            fig_map = load_interactive_map_v2()
            st.plotly_chart(fig_map, use_container_width=True)
    except Exception as e:
        st.error(f"Fehler beim Laden der interaktiven Karte: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Conclusion ────────────────────────────────────────────────────────────
    st.markdown("### Fazit")
    st.markdown(
        """
        <div style="
            background-color: #f0fdfa;
            border-left: 4px solid #0d9488;
            border-radius: 0 8px 8px 0;
            padding: 22px 26px;
            margin-bottom: 28px;
            color: #1f2937;
            font-size: 0.97rem;
            line-height: 1.75;
        ">
            <p style="margin: 0 0 14px 0;">
                Während frühere Studien zeigten, dass dezentrale Flexibilität den
                Stromgroßhandelsmärkten einen erheblichen Nutzen bringen kann, ließen sie die
                Restriktionen der Verteilnetze außer Acht. Diese Studie schließt diese Lücke
                mithilfe eines erweiterten <strong>virtuellen Speicheransatzes</strong>, der in ein
                Großhandelsmarktmodell integriert ist. Angewendet auf die Flexibilität von
                Elektrofahrzeugen in Deutschland zeigen die Ergebnisse, dass Netzrestriktionen
                nicht nur das flexible Laden von Elektrofahrzeugen, sondern auch das unflexible
                Laden und die PV-Einspeisung begrenzen, wobei die PV-Abregelung besonders ins
                Gewicht fällt.
            </p>
            <p style="margin: 0 0 14px 0;">
                Flexibles Laden von Elektrofahrzeugen, das sich allein an Großhandelspreisen
                orientiert, führt zu <strong>Herdenverhalten</strong> — Lastspitzen in
                Niedrigpreisstunden —, wobei dieser Effekt im integrierten Modell geringer ausfällt,
                da das Verschieben von Last die Preise so lange erhöht, bis ein Gleichgewicht
                erreicht ist. Die daraus resultierenden lokalen Netzanpassungen sind häufig und
                beträchtlich, ihr Einfluss auf den Großhandelsmarkt ist jedoch gering, da das Laden
                mit vergleichbarem Nutzen auf benachbarte Stunden verschoben werden kann.
            </p>
            <p style="margin: 0;">
                Entscheidend ist, dass die Kosten für das Management von Engpässen im Verteilnetz
                <strong>um eine Größenordnung niedriger</strong> sind als die eines vollständigen
                Netzausbaus, was darauf hindeutet, dass lokal koordinierte dezentrale Flexibilität
                ein kosteneffizienterer Weg ist. Eine wirksame lokale Koordination — über Preis-
                oder Mengensignale und unter Berücksichtigung sowohl der Erzeugungs- als auch der
                Lastrestriktionen neben den Ergebnissen des Großhandelsmarkts — ist daher
                unerlässlich, um das volle Potenzial dezentraler Flexibilität zu erschließen, ohne
                die Netzsicherheit zu gefährden.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
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
