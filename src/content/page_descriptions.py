"""Zentrale Seitentexte für das VISE-D Dashboard.

Zwei Quellen, je nach Anzeigeort:

* ``PAGE_DESCRIPTIONS`` – kurze Einzeiler. Werden auf der Startseite
  (Übersicht aller Seiten) als Caption angezeigt.
* ``PAGE_INSTRUCTIONS`` – ausführliche, schrittweise Nutzungsanweisungen
  (Markdown). Werden auf der jeweiligen Unterseite im ausklappbaren Hinweis
  „Anleitung & Bedienung" angezeigt.

``render_page_description`` zeigt bevorzugt die Anleitung; existiert für einen
Page-Key keine Anleitung, fällt es auf die Kurzbeschreibung zurück.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Opus 4.8)
"""

from textwrap import dedent

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
        "festlegen; der Wärmebedarf wird aus DWD-Temperaturen berechnet und der "
        "Speicher von einer Wärmepumpe über den gewählten Zeitraum beladen."
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
# Ausführliche Nutzungsanweisungen je Seite (Markdown)
# Schlüssel = Page-Key in dashboard.py. Werden im Hinweis „Anleitung & Bedienung"
# auf der jeweiligen Unterseite angezeigt. Seiten ohne Eintrag fallen auf die
# Kurzbeschreibung aus PAGE_DESCRIPTIONS zurück.
# ---------------------------------------------------------------------------

PAGE_INSTRUCTIONS: dict[str, str] = {
    "netzmodell": dedent("""\
        Diese Seite baut ein Verteilnetz auf, platziert dezentrale Erzeuger und
        Verbraucher (DER) und rechnet eine Zeitreihen-Lastflussberechnung mit
        Spannungsband- und Leitungsauslastungs-Prüfung.

        **So gehen Sie vor:**

        1. **Netz wählen (Abschnitt 1)** – Unter „Netzquelle" entweder ein
           *Vordefiniertes Netz* aus der Liste auswählen oder *Netz hochladen*
           (pandapower JSON/Excel oder CIM/CGMES). Für eigene Netze die
           Excel-Vorlage herunterladen, befüllen und wieder hochladen.
        2. **Zeitraum festlegen (Abschnitt 2)** – Start- und Enddatum unter
           „Von"/„Bis" setzen.
        3. **DER konfigurieren (Abschnitt 3)** – Über die Reiter Anlagen ergänzen:
           *Szenario (Penetration)* nach Durchdringungsgrad je Technologie,
           *Gezielt (Namenssuche)* an einzelnen Knoten oder *MaStR-Anlagen* aus
           dem Register. Jeweils mit „DER zum Netz hinzufügen" übernehmen.
        4. **Profile erzeugen (Abschnitt 3.5)** – In den Reitern (PV, EV,
           Wärmepumpe, Speicher, Basislast) die Zeitreihen für die platzierten
           Anlagen generieren oder aus den Konfigurationsseiten importieren.
        5. **Simulation starten (Abschnitt 4)** – „Zeitreihensimulation starten"
           klicken.

        **Ergebnis:** Auswertung in den Reitern „⚡ Spannungsband" (Zielband
        0,9–1,1 p.u.) und „📈 Leitungsauslastung" als Zeitreihen-Diagramme samt
        Kennzahlen zu Grenzwertverletzungen.

        **Hinweis:** Die Abschnitte bauen aufeinander auf — ohne geladenes Netz
        (Abschnitt 1) bleiben die folgenden Abschnitte gesperrt.
        """).strip(),

    "flexibility": dedent("""\
        Diese Seite aggregiert die gerätescharfe Flexibilität eines Haushaltsmix
        und vergleicht das Lastprofil ohne und mit Lastverschiebung.

        **So gehen Sie vor:**

        1. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen. Aus dem
           Startdatum wird automatisch die Jahreszeit abgeleitet (bestimmt die
           verfügbaren Haushaltsklassen); dargestellt wird eine repräsentative
           Woche.
        2. **Haushaltsmix festlegen** – In den nach Arbeitsweise gruppierten
           Tabellen je Haushaltsklasse die „Anzahl" eintragen. Haushaltsgröße und
           Automatisierungsgrad werden informativ angezeigt.
        3. **Verschiebungsgrad setzen** – Mit dem Schieberegler den Grad der
           Lastverschiebung (0–100 %) wählen.
        4. **Berechnen** – „Lastprofil berechnen" klicken.

        **Ergebnis:** Liniendiagramm mit Basisprofil (durchgezogen) gegen
        verschobenes Profil (gestrichelt) sowie Kennzahlen (Spitzenlast
        Basis/verschoben, verschobene Energie pro Woche). Mit
        „→ Im Netzmodell analysieren" werden die Profile an die Netzmodell-Seite
        übergeben.
        """).strip(),

    "solar_mastr": dedent("""\
        Diese Seite zeigt die Solaranlagen einer Stadt aus dem
        Marktstammdatenregister (MaStR) auf einer interaktiven Karte und kann
        optional deren Erzeugung simulieren.

        **So gehen Sie vor:**

        1. **Stadt wählen** – Ort bzw. PLZ im Feld „Stadt" auswählen oder eingeben.
        2. **Anlagen anzeigen** – Button „Anlagen anzeigen" klicken: Karte und
           Kennzahlen (Anzahl, Brutto-/Nettoleistung, Ø Leistung) erscheinen.
           Unter „Detaillierte Statistiken" finden Sie ein Leistungs-Histogramm,
           die 10 größten Anlagen und einen CSV-Export.
        3. **Erzeugung simulieren (optional)** – Im Abschnitt
           „Erzeugungssimulation" Zeitraum unter „Von"/„Bis" setzen und
           „Erzeugung berechnen" klicken. Es werden MaStR- und DWD-Wetterdaten
           geladen und die Einspeisung im 15-min-Raster berechnet.

        **Ergebnis:** Kennzahlen (PV-Systeme, installierte Leistung,
        Spitzenleistung), ein Liniendiagramm der aggregierten Solareinspeisung
        sowie CSV-Downloads (aggregierte und einzelne Systemzeitreihen).
        """).strip(),

    "wind_mastr": dedent("""\
        Diese Seite zeigt die Windanlagen einer Stadt aus dem
        Marktstammdatenregister (MaStR) auf einer interaktiven Karte und kann
        optional deren Erzeugung simulieren.

        **So gehen Sie vor:**

        1. **Stadt wählen** – Ort bzw. PLZ im Feld „Stadt" auswählen oder eingeben.
        2. **Anlagen anzeigen** – Button „Anlagen anzeigen" klicken: Karte und
           Kennzahlen (Anzahl, Brutto-/Nettoleistung, Ø Leistung) erscheinen.
           Unter „Detaillierte Statistiken" gibt es ein Leistungs-Histogramm, die
           10 größten Anlagen und einen CSV-Export.
        3. **Erzeugung simulieren (optional)** – Im Abschnitt
           „Erzeugungssimulation" Zeitraum unter „Von"/„Bis" setzen und
           „Erzeugung berechnen" klicken. Turbinentypen werden abgeglichen,
           DWD-Winddaten geladen und die Einspeisung im 15-min-Raster berechnet.

        **Ergebnis:** Kennzahlen (Windturbinen, installierte Leistung,
        Spitzenleistung), ein Liniendiagramm der aggregierten Windeinspeisung
        sowie CSV-Downloads (aggregierte und einzelne Turbinenzeitreihen).
        """).strip(),

    "storage_mastr": dedent("""\
        Diese Seite zeigt die Speicheranlagen einer Stadt aus dem
        Marktstammdatenregister (MaStR) als Karte, Tabelle und Auswertungen.
        Diese Seite enthält keine Simulation.

        **So gehen Sie vor:**

        1. **Stadt wählen** – Ort bzw. PLZ im Feld „Stadt" auswählen oder eingeben.
        2. **Anlagen anzeigen** – Button „Anlagen anzeigen" klicken.

        **Ergebnis:** Interaktive Karte der Speicheranlagen, eine Datentabelle
        (Name, Brutto-/Nettoleistung, Koordinaten, Ort), ein Tortendiagramm nach
        Betriebsstatus und ein Balkendiagramm der Anlagen je Nettoleistungsklasse
        (<50, 50–200, 200–1000, >1000 kW).
        """).strip(),

    "research_results": dedent("""\
        Diese Seite fasst Forschungsergebnisse zur Integration von
        Elektrofahrzeugen in Verteilnetze zusammen. Es ist eine reine
        Informationsseite ohne Eingaben.

        **So lesen Sie die Seite:**

        1. **Kurzfassung** – Überblick über Fragestellung und zentrale
           Erkenntnisse zu Tarifmodellen (Festpreis, Time-of-Use, Real-Time) und
           DSO-Eingriffsstrategien.
        2. **Abbildungen** – Vier Abschnitte mit Diagrammen: Großhandels- und
           Verbraucherpreise, wirtschaftliche Auswirkungen der Tarifstrukturen,
           Flexibilitätsbedarf durch E-Fahrzeuge und Vergleich der Kostendeltas.
           Der Text unter jeder Abbildung erläutert deren Aussage.

        **Ergebnis:** Ein Verständnis der Studienergebnisse; die vollständige
        Publikation ist über den Link in der Kurzfassung erreichbar (Englisch).
        """).strip(),

    "bev_settings": dedent("""\
        Diese Seite konfiguriert ein Elektrofahrzeug (BEV) und erzeugt das
        zugehörige Lade-Lastprofil.

        **So gehen Sie vor:**

        1. **Fahrzeug konfigurieren** – Im Formular Batteriekapazität (max./min.),
           Tagesverbrauch, Ladeleistung, Wirkungsgrad sowie An-/Absteckzeiten
           festlegen.
        2. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen; die
           Zahl der Zeitschritte (15-min-Raster) wird angezeigt.
        3. **Simulieren** – „BEV simulieren" klicken.

        **Ergebnis:** Eine Vorschau der Zeitreihendaten und ein Diagramm der
        Ladeleistung (kW) über die Zeit, das die Ladefenster sichtbar macht.
        """).strip(),

    "heatpump": dedent("""\
        Diese Seite konfiguriert eine Wärmepumpe und simuliert ihren Betrieb auf
        Basis von DWD-Wetterdaten und dem Wärmebedarf des Gebäudes.

        **So gehen Sie vor:**

        1. **Standort wählen** – Stadtnamen unter „Ort (Stadtname)" eingeben; die
           Koordinaten werden per Geocoding ermittelt.
        2. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen.
        3. **Wärmepumpe parametrieren** – Im Formular Pumpentyp, elektrische und
           thermische Leistung sowie Systemtemperatur wählen; unter „Gebäude und
           Wärmebedarf" Jahreswärmebedarf, Gebäudetyp und Heizgrenztemperatur
           festlegen.
        4. **Simulieren** – „🚀 Wärmepumpe Simulation starten" klicken.

        **Ergebnis:** Kennzahlen (Gesamtverbrauch, max. Leistung, Ø COP), der
        COP-Verlauf, eine Zeitreihen-Vorschau und ein Diagramm der
        Leistungsaufnahme. Unter „Wetterdaten-Information" werden die genutzte
        DWD-Station und ihre Entfernung angezeigt.
        """).strip(),

    "pv": dedent("""\
        Diese Seite erzeugt ein normiertes PV-Einspeiseprofil auf Basis von
        DWD-Wetterdaten – wahlweise für einen frei gewählten Standort oder für
        reale MaStR-Anlagen.

        **So gehen Sie vor:**

        1. **Modus wählen** – Zwischen *Standortbasierte Simulation* und
           *Anlagenbasierte Simulation* umschalten.
        2. **Standort/Anlagen festlegen** –
           *Standortbasiert:* Stadtnamen eingeben (wird geocodiert) und
           installierte Leistung in kWp angeben.
           *Anlagenbasiert:* Stadt wählen, optional über das Namensfeld filtern
           und Anlagen in der Mehrfachauswahl markieren.
        3. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen; die
           Zahl der Zeitschritte (15-min-Raster) wird angezeigt.
        4. **Profil generieren** – Button „Profil generieren" klicken; die
           Solarstrahlung des DWD wird geladen und ein 1-kWp-Referenzsystem auf
           Ihre Leistung skaliert.

        **Ergebnis:** Liniendiagramm der PV-Leistung (kW) plus Kennzahlen
        (Spitzenleistung, Energie, Kapazitätsfaktor). Bei mehreren Anlagen je
        Anlage ein Reiter plus ein aggregierter Gesamt-Reiter; Profile als CSV
        herunterladbar.
        """).strip(),

    "wind": dedent("""\
        Diese Seite erzeugt ein Windeinspeiseprofil aus DWD-Winddaten (10 m) mit
        Nabenhöhen-Korrektur über den Hellman-Exponenten – standort- oder
        anlagenbasiert (MaStR).

        **So gehen Sie vor:**

        1. **Modus wählen** – Zwischen *Standortbasierte Simulation* und
           *Anlagenbasierte Simulation* umschalten.
        2. **Standort/Anlagen festlegen** –
           *Standortbasiert:* Stadtnamen eingeben sowie Nabenhöhe (m) und
           Nennleistung (kW) angeben.
           *Anlagenbasiert:* Stadt wählen, optional über das Namensfeld (Anlagen-
           oder Windparkname) filtern und Anlagen in der Mehrfachauswahl markieren.
        3. **Hellman-Exponent setzen** – Geländerauigkeit wählen (0,10 =
           Küste/Offshore · 0,20 = offenes Gelände · 0,30–0,40 = Wald/Bebauung).
        4. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen.
        5. **Profil generieren** – Button „Profil generieren" klicken.

        **Ergebnis:** Liniendiagramm der Windleistung (kW) plus Kennzahlen
        (Spitzenleistung, Energie, Kapazitätsfaktor). Bei mehreren Anlagen je
        Anlage ein Reiter plus ein aggregierter Gesamt-Reiter; Profile als CSV
        herunterladbar.
        """).strip(),

    "electrical_storage": dedent("""\
        Diese Seite konfiguriert einen Batteriespeicher und simuliert seinen
        Betrieb im Zusammenspiel mit PV-Erzeugung und einer konstanten Grundlast.

        **So gehen Sie vor:**

        1. **Standort wählen** – Stadtnamen unter „Ort (Stadtname)" eingeben.
        2. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen.
        3. **Speicher parametrieren** – Im Formular Kapazität, max. Leistung,
           Lade-/Entladewirkungsgrad und C-Rate festlegen; unter „Lastprofil
           Einstellungen" die Grundlast (kW) angeben.
        4. **Simulieren** – „🚀 Speicher Simulation starten" klicken.

        **Ergebnis:** Kennzahlen (geladen, entladen, max. Leistung), eine
        Energiebilanz mit Eigenverbrauchsanteil, eine Datenvorschau und zwei
        Diagramme (PV/Grundlast/Residuallast sowie Speicherbetrieb:
        positiv = laden, negativ = entladen).

        **Hinweis:** Konfigurieren Sie zuvor ein PV-System auf der Seite
        „Photovoltaik" — ohne PV-System lässt sich die Simulation nicht ausführen.
        """).strip(),

    "thermal_storage": dedent("""\
        Diese Seite konfiguriert einen thermischen Speicher (Warmwasserspeicher)
        und simuliert seine Beladung durch eine Wärmepumpe gegen den
        wetterabhängigen Wärmebedarf.

        **So gehen Sie vor:**

        1. **Standort wählen** – Stadtnamen unter „Ort (Stadtname)" eingeben.
        2. **Zeitraum wählen** – Start-/Enddatum unter „Von"/„Bis" setzen.
        3. **Gebäude & Wärmebedarf** – Jahreswärmebedarf, Gebäudetyp und
           Heizgrenztemperatur festlegen (daraus wird der Wärmebedarf über ein
           Referenzjahr kalibriert).
        4. **Speicher parametrieren** – Ziel-/Minimaltemperatur, Hysterese, Masse,
           Wärmekapazität und Tagesverlust eingeben und „Einstellungen speichern".
        5. **Wärmeerzeuger parametrieren** – Unter „Wärmeerzeuger (Wärmepumpe)"
           Typ, Vorlauftemperatur sowie elektrische/thermische Leistung festlegen
           und „Einstellungen speichern".
        6. **Simulieren** – „Thermischen Speicher simulieren" klicken.

        **Ergebnis:** Vorschau-Tabellen sowie Diagramme des Temperaturverlaufs
        (mit Ziel- und Minimaltemperatur) und des elektrischen Bedarfs des
        Wärmeerzeugers. Bei Unterdeckung erscheint ein Hinweis mit
        Lösungsvorschlägen.
        """).strip(),
}

# ---------------------------------------------------------------------------
# Gruppierung und Titel für die Startseiten-Übersicht
# (Reihenfolge entspricht der Navigation in dashboard.py)
# ---------------------------------------------------------------------------

PAGE_OVERVIEW: dict[str, list[tuple[str, str]]] = {
    "Energiesystemanalysen": [
        ("netzmodell", "Netzmodell-Szenario"),
        ("flexibility", "Flexibilitätskonfigurator"),
    ],
    "Marktstammdatenregister": [
        ("solar_mastr", "Solaranlagen"),
        ("wind_mastr", "Windanlagen"),
        ("storage_mastr", "Speicheranlagen"),
    ],
    "Forschungsergebnisse": [
        ("research_results", "Integration von E-Fahrzeugen in Verteilnetze"),
    ],
    "Lastprofilgeneratoren": [
        ("bev_settings", "E-Mobilität"),
        ("heatpump", "Wärmepumpe"),
        ("pv", "Photovoltaik"),
        ("wind", "Windenergie"),
        ("electrical_storage", "Elektrischer Speicher"),
        ("thermal_storage", "Thermischer Speicher"),
    ],
}


def render_page_description(key: str) -> None:
    """Zeigt die Anleitung einer Seite in einem ausklappbaren Hinweis.

    Wird oben auf jeder Unterseite aufgerufen. Bevorzugt wird die ausführliche
    Nutzungsanweisung aus ``PAGE_INSTRUCTIONS`` (Markdown) angezeigt; existiert
    dafür kein Eintrag, fällt es auf die Kurzbeschreibung aus
    ``PAGE_DESCRIPTIONS`` zurück.

    Args:
        key: Page-Key aus ``PAGE_INSTRUCTIONS`` bzw. ``PAGE_DESCRIPTIONS``.
    """
    instructions = PAGE_INSTRUCTIONS.get(key)
    if instructions:
        with st.expander("📖 Anleitung & Bedienung"):
            st.markdown(instructions)
        return

    # Seiten ohne ausführliche Anleitung zeigen weiter die Kurzbeschreibung.
    description = PAGE_DESCRIPTIONS.get(key)
    if not description:
        return
    with st.expander("ℹ️ Über diese Seite"):
        st.write(description)
