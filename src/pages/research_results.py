"""Research results page for VISE-D dashboard.

This page displays research findings on EV integration in distribution networks
and DSO intervention strategies.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

import streamlit as st
from src.visualization import fig_5, fig_7, fig_8, fig_9


def research_results():
    """Display research results on EV integration in distribution networks.
    
    Shows research findings including:
    - Executive summary
    - Wholesale and consumer electricity prices
    - Economic impacts of different tariff structures
    - Flexibility from electric vehicles
    - Cost delta comparisons
    """
    st.write('## Integration von E-Fahrzeugen in Verteilnetze - Untersuchung der Auswirkungen \
        verschiedener DSO-Eingriffsstrategien auf optimiertes Laden')
    from src.content.page_descriptions import render_page_description
    render_page_description("research_results")
    st.write('### Kurzfassung')
    st.write(
        'Die Einführung von Elektrofahrzeugen (EVs) und die Einführung variabler Stromtarife erhöhen die \
        Spitzennachfrage und das Risiko von Überlastungen in den Verteilnetzen. Um kritische Netzsituationen \
        abzuwenden und teure Netzerweiterungen zu vermeiden, müssen Verteilnetzbetreiber (DSOs) über \
        Eingriffsrechte verfügen, die es ihnen ermöglichen, Ladevorgänge zu drosseln. Es sind verschiedene \
        Drosselungsstrategien möglich, die sich in der räumlich-zeitlichen Differenzierung und der möglichen \
        Diskriminierung unterscheiden. Die Bewertung verschiedener Strategien ist jedoch \
        aufgrund des Zusammenspiels von wirtschaftlichen Faktoren, technischen Anforderungen und regulatorischen \
        Beschränkungen komplex – eine Komplexität, die in der aktuellen Literatur nicht vollständig behandelt \
        wird. Unsere Studie stellt ein ausgeklügeltes Modell zur Optimierung von Ladestrategien für Elektrofahrzeuge \
        vor, um diese Lücke zu schließen. Dieses Modell berücksichtigt verschiedene Tarifmodelle (Festpreis, \
        Time-of-Use und Real-Time) und bezieht (grundlegende, variable und intelligente) DSO Interventionen in seinen Optimierungsrahmen \
        ein. Basierend auf dem Modell analysieren wir den Flexibilitätsbedarf und die Gesamtstromkosten aus der Sicht \
        der Nutzer. Bei der Anwendung unseres Modells auf ein synthetisches Verteilernetz stellen wir fest, dass \
        flexible Tarife den Verbrauchern nur marginale wirtschaftliche Vorteile bieten und das Risiko von Netzengpässen \
        aufgrund von Herdenverhalten erhöhen. Alle Kürzungsstrategien verringern Engpässe effektiv, wobei variable \
        Kürzungen eine räumlich-zeitliche Differenzierung aufweisen und sich der Optimalität in Bezug auf den \
        Flexibilitätsbedarf annähern. Bemerkenswert ist, dass die Anwendung von Kürzungen aus der Sicht der Nutzer \
        die Kosteneinsparungen nicht wesentlich senkt.'
    )
    st.write('*Die Veröffentlichung finden Sie [hier](https://www.sciencedirect.com/science/article/pii/S0306261924021585?dgcid=author) (Englisch).*')

    st.write('### Großhandelspreise und abgeleitete durchschnittliche Verbraucherpreise für Festtarif und ToU-Tarif')
    st.pyplot(fig=fig_5(), clear_figure=True)
    st.write(
        'Hier sind die Strompreise für die Kumulierte Verteilung der angenommenen Stromgroßhandelspreise \
        für 2030 (links) und die endgültige Zusammensetzung der Strompreise für den Fix- und ToU-Tarif \
        für 2030 (rechts) dargestellt. Der ToU-Tarif besteht aus drei Acht-Stunden-Zeitfenstern \
        mit unterschiedlichen Preisen. Der erste ToU-Zeitraum (0–8) umfasst die ersten acht Stunden des Tages. \
        Beim RT-Tarif werden die Netznutzungsgebühr, Abgaben und Steuern zum Großhandelspreis addiert, \
        was zu unterschiedlichen Preisen für jedes Intervall führt.'
    )

    st.write('### Wirtschaftliche Auswirkungen unterschiedlicher Tarifstrukturen für das Laden von Elektrofahrzeugen')
    st.pyplot(fig=fig_7(), clear_figure=True)
    st.write(
        'In der Abbildung sind die Auswirkungen von Tarifstrukturen auf optimale Ladestrategien \
        und damit verbundene Ladekosten ohne Drosselung dargestellt. \
        Das linke Segment der Abbildung zeigt konkret die Nachfragemuster, die an einen einzelnen Transformator für drei \
        Tage angelegt sind. Die rechts dargestellte Verteilung der Ladekosten wird jährlich berechnet und umfasst alle \
        Fahrzeuge, die auf die zwölf Netze verteilt sind. Jede Zeile spiegelt die Ergebnisse für eine bestimmte \
        Durchdringungsrate wider.'
    )

    st.write('### Flexibilität durch Elektrofahrzeuge')
    st.pyplot(fig=fig_8(), clear_figure=True)
    st.write(
        'Die obige Abbildung zeigt einen signifikanten Trend: Die Einführung zeitvariabler \
        Tarife, wie ToU- und RT-Tarife, korreliert direkt mit einem erhöhten \
        Flexibilitätsbedarf zur Vermeidung von Engpässen. Wenn man eine 30%ige oder \
        sogar 50%ige EV-Durchdringungsrate betrachtet, ist eine Einschränkung bei festen Tarifen nicht erforderlich. \
        Mit der Einführung dynamischer Tarife wird dies jedoch notwendig. \
        Das Ausmaß des Anstiegs des Flexibilitätsbedarfs aufgrund der Einführung \
        der dynamischen Tarife ist nicht konstant, sondern hängt vom \
        Verbreitungsgrad von Elektrofahrzeugen ab.'
    )

    st.write('### Vergleich der Kostendeltas')
    st.pyplot(fig=fig_9(), clear_figure=True)
    st.write(
        'Die Abbildung veranschaulicht eine vergleichende Analyse der jährlichen Schwankungen der \
        Stromkosten unter Berücksichtigung der ToU- und RT-Tarife, der EV-Durchdringung \
        und die drei verschiedenen Abregelungsstrategien. Der Vergleich wird durchgeführt \
        mit dem Szenario mit festem Tarif ohne Drosselung. Dabei \
        werden die Kostenunterschiede für den Festtarif nicht dargestellt, da diese \
        Tarifstruktur unabhängig von der eingesetzten Strategie gleichbleibende Kosten verursacht. /n \
        Anmerkung: "before" bezieht sich auf den hypothetischen Fall, dass die Abrechnung ausschließlich \
        auf der Grundlage von Preissignalen erfolgt, bevor Drosselungsstrategien eingesetzt werden.'
    )

    # Footer with Logos
    footer_cols = st.columns(2)

    with footer_cols[0]:
        st.markdown(
            """
            <div style="background-color: white; padding: 10px; text-align: center; border-radius: 15px;">
                <img src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/10/VISE_D_neu-1024x470.png" \
                    alt="VISE-D Logo" style="width: auto; height: 100px;">
            </div>
            """,
            unsafe_allow_html=True
        )
        
    with footer_cols[1]:
        st.markdown(
            """
            <div style="background-color: white; padding: 10px; text-align: center; border-radius: 15px;">
                <img src="https://smart-energy-nrw.web.th-koeln.de/wp-content/uploads/2023/01/Logo_MWIKEPixel.png" \
                    alt="MWIKE Logo" style="width: auto; height: 70px;">
            </div>
            """,
            unsafe_allow_html=True
        )
