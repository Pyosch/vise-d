"""Zentrale Seitenbeschreibungen für das VISE-D Dashboard.

Single Source of Truth: Die hier hinterlegten Kurzbeschreibungen werden sowohl
auf der Startseite (Übersicht aller Seiten) als auch auf der jeweiligen
Unterseite (ausklappbarer Hinweis „Über diese Seite") angezeigt. So bleiben
beide Darstellungen automatisch konsistent.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Opus 4.8)
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Kurzbeschreibungen je Seite (Schlüssel = Page-Key in dashboard.py)
# ---------------------------------------------------------------------------

PAGE_DESCRIPTIONS: dict[str, str] = {
    "research_results": (
        "Forschungsergebnisse zur Integration von Elektrofahrzeugen in "
        "Verteilnetze: Wie wirken sich verschiedene DSO-Eingriffsstrategien "
        "und Tarifmodelle (Festpreis, Time-of-Use, Real-Time) auf das "
        "optimierte Laden, den Flexibilitätsbedarf und die Stromkosten aus?"
    ),
    "mv_fallstudie": (
        "Fallstudie zur Validierung eines Mittelspannungsnetzes nach der "
        "Methodik Shapefile → pandapower → Messdaten-Abgleich. Eigene "
        "Validierungs-CSVs können hochgeladen werden, um die Analyse auf dem "
        "eigenen Netz auszuführen (Demodaten: CIGRE-MS-Referenznetz)."
    ),
    "bev_settings": (
        "Konfiguration und Simulation von Ladevorgängen für Elektrofahrzeuge "
        "(BEV). Batteriekapazität, Ladeleistung, Wirkungsgrad und Nutzungszeiten "
        "festlegen und das resultierende Lade-Lastprofil erzeugen."
    ),
    "heatpump": (
        "Konfiguration und Simulation des Wärmepumpenbetriebs. Pumpentyp, "
        "elektrische und thermische Leistung sowie Gebäudeparameter wählen und "
        "den Betrieb auf Basis von DWD-Wetterdaten und Wärmebedarf simulieren."
    ),
    "pv": (
        "Erzeugung normierter Photovoltaik-Profile – wahlweise standortbasiert "
        "(Stadtname oder Koordinaten) oder anlagenbasiert über ausgewählte "
        "MaStR-Anlagen. Die Berechnung nutzt ein 1-kWp-Referenzsystem und "
        "DWD-Wetterdaten."
    ),
    "wind": (
        "Simulation von Windenergieanlagen mit Nabenhöhen-Korrektur "
        "(Hellmann-Exponent). Standort- oder anlagenbasiert (MaStR) ein "
        "normiertes Windeinspeiseprofil erzeugen."
    ),
    "electrical_storage": (
        "Konfiguration und Simulation eines elektrischen Batteriespeichers. "
        "Kapazität, Lade-/Entladeleistung und Wirkungsgrade festlegen und den "
        "Speicherbetrieb im Zusammenspiel mit PV-Erzeugung simulieren."
    ),
    "thermal_storage": (
        "Konfiguration und Simulation eines thermischen Speichers "
        "(Warmwasserspeicher). Speichermasse, Zieltemperatur und Hysterese "
        "festlegen und den Betrieb mit Heizstab über eine Beispielwoche "
        "simulieren."
    ),
    "netzmodell": (
        "Aufbau und Analyse von Netzszenarien: vordefinierte oder eigene Netze "
        "laden, dezentrale Erzeuger (DER) nach Durchdringung, Name oder MaStR "
        "konfigurieren, Profile erzeugen und eine Zeitreihen-Lastflussrechnung "
        "mit Spannungsband-Prüfung durchführen."
    ),
    "flexibility": (
        "Aggregation von Haushalts-Flexibilität und Szenarienvergleich. "
        "Haushaltsmix und Teilnahmequote festlegen und Basis-Lastprofil gegen "
        "das flexibilisierte Lastprofil vergleichen."
    ),
    "solar_mastr": (
        "Interaktive Karte der Solaranlagen einer Stadt aus dem "
        "Marktstammdatenregister (MaStR) inklusive optionaler Simulation der "
        "Energieerzeugung auf Basis von DWD-Wetterdaten."
    ),
    "wind_mastr": (
        "Interaktive Karte der Windanlagen einer Stadt aus dem "
        "Marktstammdatenregister (MaStR) inklusive optionaler Simulation der "
        "Energieerzeugung auf Basis von DWD-Wetterdaten."
    ),
    "storage_mastr": (
        "Interaktive Karte und Datentabelle der Speicheranlagen einer Stadt "
        "aus dem Marktstammdatenregister (MaStR), inklusive Auswertungen nach "
        "Betriebsstatus und Leistungsklassen."
    ),
}

# ---------------------------------------------------------------------------
# Gruppierung und Titel für die Startseiten-Übersicht
# (Reihenfolge entspricht der Navigation in dashboard.py)
# ---------------------------------------------------------------------------

PAGE_OVERVIEW: dict[str, list[tuple[str, str]]] = {
    "Forschungsergebnisse": [
        ("research_results", "Integration von E-Fahrzeugen in Verteilnetze"),
        ("mv_fallstudie", "Fallstudie: MS-Netz Validierung"),
    ],
    "Lastprofilgeneratoren": [
        ("bev_settings", "E-Mobilität"),
        ("heatpump", "Wärmepumpe"),
        ("pv", "Photovoltaik"),
        ("wind", "Windenergie"),
        ("electrical_storage", "Elektrischer Speicher"),
        ("thermal_storage", "Thermischer Speicher"),
    ],
    "Energiesystemanalysen": [
        ("netzmodell", "Netzmodell-Szenario"),
        ("flexibility", "Flexibilitätskonfigurator"),
    ],
    "Marktstammdatenregister": [
        ("solar_mastr", "Solaranlagen"),
        ("wind_mastr", "Windanlagen"),
        ("storage_mastr", "Speicheranlagen"),
    ],
}


def render_page_description(key: str) -> None:
    """Zeigt die Kurzbeschreibung einer Seite in einem ausklappbaren Hinweis.

    Wird oben auf jeder Unterseite aufgerufen, damit dort dieselbe Erläuterung
    erscheint wie auf der Startseite.

    Args:
        key: Page-Key aus ``PAGE_DESCRIPTIONS``.
    """
    description = PAGE_DESCRIPTIONS.get(key)
    if not description:
        return
    with st.expander("ℹ️ Über diese Seite"):
        st.write(description)
