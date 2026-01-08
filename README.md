# VISE-D: Virtual Integrated Smart Energy - Deutschland

Ein interaktives Dashboard zur Analyse von Energiesystemen in deutschen Verteilnetzen.

An interactive dashboard for energy system analysis in German distribution grids.

## 🌟 Übersicht / Overview

**VISE-D** ist ein Streamlit-basiertes Analysetool für die Planung und Bewertung von Energiesystemen mit Fokus auf:

- **Erneuerbare Energien**: Photovoltaik- und Windenergieanlagen
- **Speichersysteme**: Batteriespeicher und Elektrofahrzeuge (BEV)
- **Sektorenkopplung**: Wärmepumpen und Power-to-Heat
- **Netzanalyse**: Pandapower-Integration für Lastflussberechnungen
- **Prognosen**: OpenSTEF-Integration für Einspeise-Forecasting
- **MaStR-Daten**: Echte Anlagendaten aus dem Marktstammdatenregister

**VISE-D** is a Streamlit-based analysis tool for planning and evaluating energy systems, focusing on:

- **Renewable Energy**: Photovoltaic and wind power systems
- **Storage Systems**: Battery storage and battery electric vehicles (BEV)
- **Sector Coupling**: Heat pumps and power-to-heat
- **Network Analysis**: Pandapower integration for power flow calculations
- **Forecasting**: OpenSTEF integration for generation forecasting
- **MaStR Data**: Real plant data from Germany's Marktstammdatenregister

## 🚀 Installation

### Voraussetzungen / Prerequisites

- Python 3.11 oder höher / Python 3.11 or higher
- pip (Python package manager)

### Setup

1. **Repository klonen / Clone repository:**
```bash
git clone <repository-url>
cd vise-d
```

2. **Virtuelle Umgebung erstellen / Create virtual environment:**
```bash
python -m venv venv
```

3. **Virtuelle Umgebung aktivieren / Activate virtual environment:**

Windows:
```bash
.\venv\Scripts\activate
```

Linux/macOS:
```bash
source venv/bin/activate
```

4. **Abhängigkeiten installieren / Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Dashboard starten / Start dashboard:**
```bash
streamlit run dashboard.py
```

Die Anwendung öffnet sich automatisch im Browser unter `http://localhost:8501`.

The application will automatically open in your browser at `http://localhost:8501`.

## 📁 Projektstruktur / Project Structure

```
vise-d/
├── dashboard.py              # Hauptanwendung / Main application
├── src/                      # Quelcode-Module / Source code modules
│   ├── config/              # Konfiguration (Pfade, Konstanten)
│   ├── ui/                  # UI-Komponenten (deutsche Oberfläche)
│   │   ├── components/      # Technologie-Formulare
│   │   └── layout.py        # Seitenleiste, Navigation
│   ├── pages/               # Dashboard-Seiten (17 Module)
│   ├── data_layer/          # Datenladen und Caching
│   ├── mastr/               # MaStR-Datenbankintegration
│   ├── forecasting/         # OpenSTEF und Prognosemodelle
│   ├── planning/            # Solar- und Windplanungstools
│   ├── visualization/       # Visualisierungsutilities
│   ├── network/             # Pandapower-Netzanalyse
│   └── utils/               # Gemeinsame Utilities
├── tests/                   # Test-Suite (spiegelt src/ Struktur)
├── examples/                # Standalone-Beispielskripte
├── data/                    # Datendateien (nicht in Git)
├── docs/                    # Dokumentation
└── requirements.txt         # Python-Abhängigkeiten
```

## 🔑 Kernfunktionen / Key Features

### Technologiekomponenten / Technology Components

- **Photovoltaik**: Anlagenplanung, Ertragssimulation, Standortanalyse
- **Windenergie**: Turbinenwahl, Windpotentialanalyse, ERA5-Datenintegration
- **Batteriespeicher**: Kapazitätsauslegung, Lastmanagement
- **Elektrofahrzeuge**: Lademanagement, V2G-Potentiale
- **Wärmepumpen**: Thermische Last, Sektorenkopplung

### Netzanalyse / Network Analysis

- Lastflussberechnungen mit Pandapower
- Spannungsbandanalyse
- Transformatorenauslastung
- Netzausbauplanung

### Prognosen / Forecasting

- PV-Einspeiseprognosen mit OpenSTEF
- Wetterdatenintegration (DWD)
- MLflow-Modelltracking

## 🌍 Sprachen / Languages

**VISE-D folgt einer dualen Sprachstrategie:**

- **Benutzeroberfläche**: Deutsch (alle UI-Texte, Beschriftungen, Nachrichten)
- **Code & Kommentare**: Englisch (PEP 8-konform, internationale Zusammenarbeit)

**VISE-D follows a dual-language strategy:**

- **User Interface**: German (all UI text, labels, messages)
- **Code & Comments**: English (PEP 8 compliant, international collaboration)

Beispiel / Example:
```python
# English code and comments
def render_pv_analysis_page() -> None:
    """Render the photovoltaic analysis page."""
    # German UI text for users
    st.title("Photovoltaik-Analyse")
    st.sidebar.selectbox("Standort auswählen", options=locations)
```

## 🔧 Konfiguration / Configuration

Die Anwendung verwendet `pathlib` für plattformunabhängige Pfadverwaltung. Konfigurationen finden Sie in:

The application uses `pathlib` for cross-platform path management. Configuration is found in:

- `src/config/paths.py` - Verzeichnispfade / Directory paths
- `src/config/constants.py` - Anwendungskonstanten / Application constants

## 🧪 Tests

Tests werden mit pytest durchgeführt:

Tests are run using pytest:

```bash
# Alle Tests ausführen / Run all tests
pytest

# Mit Coverage / With coverage
pytest --cov=src --cov-report=html
```

Ziel-Coverage: >70% initial, >90% für Produktion

Target coverage: >70% initially, >90% for production

## 📚 Dokumentation / Documentation

- **[roadmap.md](roadmap.md)**: Projektphasen und Entwicklungsziele
- **[docs/](docs/)**: Technische Dokumentation
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)**: Entwicklungsrichtlinien

## 🤝 Abhängigkeiten / Dependencies

### Kernabhängigkeiten / Core Dependencies

- **Streamlit**: Interaktive Dashboard-Oberfläche
- **vpplib 0.0.5**: Technologiekomponentenmodelle (PV, Wind, BEV, Wärmepumpen)
- **Pandapower**: Netzanalyse und Lastflussberechnungen
- **windpowerlib**: Windturbinen-Modellierung
- **pandas/numpy**: Datenverarbeitung
- **plotly**: Interaktive Visualisierungen

Vollständige Liste: siehe [requirements.txt](requirements.txt)

Complete list: see [requirements.txt](requirements.txt)

## 📖 vpplib Integration

VISE-D baut auf vpplib-Komponentenmodellen auf:

VISE-D builds on vpplib component models:

- **Komponenten**: Photovoltaic, WindPower, BatteryElectricVehicle, HeatPump, ElectricalEnergyStorage
- **Datenintegration**: vpplib generiert Last-/Erzeugungsprofile → Pandapower-Netzanalyse
- **UI-Komponenten**: `src/ui/components/` enthält **nur Formulare**, keine Modellimplementierungen
- **Caching**: vpplib Environment-Objekte werden 1 Stunde gecacht

## 🚧 Aktueller Entwicklungsstand / Current Development Status

**Phase 0: Codebase-Umstrukturierung** (Januar 2026)

Refactoring von monolithischer Struktur zu modularer `src/`-Architektur:

- ✅ Grundlegende Verzeichnisstruktur erstellt
- ✅ Konfigurationsmanagement mit pathlib implementiert
- ⏳ Extraktion der 17 Seitenfunktionen aus dashboard.py
- ⏳ Konsolidierung verstreuter Utilities
- ⏳ Test-Infrastruktur aufbauen (pytest, >70% Coverage-Ziel)
- ⏳ Umfassende Dokumentation erstellen

**Zukunft**: Phase 7 (Tariff Design Studio) beginnt nach Abschluss der Umstrukturierung

**Future**: Phase 7 (Tariff Design Studio) will begin after restructuring completion

## 🐛 Fehlerbehebung / Troubleshooting

### Häufige Probleme / Common Issues

1. **Import-Fehler / Import errors:**
   - Stellen Sie sicher, dass Sie sich im vise-d-Hauptverzeichnis befinden
   - Ensure you're in the vise-d root directory
   - Virtuelle Umgebung aktivieren / Activate virtual environment

2. **Fehlende Daten / Missing data:**
   - Datenverzeichnisse werden automatisch erstellt
   - Data directories are created automatically
   - MaStR-Datenbank separat herunterladen / Download MaStR database separately

3. **Streamlit-Fehler / Streamlit errors:**
   - Cache löschen: `.streamlit/cache/` Ordner löschen
   - Clear cache: Delete `.streamlit/cache/` folder
   - Neustart: `streamlit run dashboard.py`
   - Restart: `streamlit run dashboard.py`

## 📄 Lizenz / License

[Lizenzinformationen hier einfügen / Add license information here]

## ✍️ Autoren / Authors

- **Pyosch** - Hauptentwickler / Lead Developer
- **GitHub Copilot (Claude Sonnet 4.5)** - AI-Unterstützung / AI Assistance

## 🙏 Danksagungen / Acknowledgments

- vpplib Team für Technologiekomponentenmodelle
- Pandapower Team für Netzanalyse-Tools
- OpenSTEF Community für Forecasting-Framework
- Bundesnetzagentur für MaStR-Daten

---

**Hinweis**: Dieses Projekt befindet sich in aktiver Entwicklung. Funktionen und Struktur können sich ändern.

**Note**: This project is under active development. Features and structure may change.
