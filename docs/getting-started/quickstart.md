# Quickstart Guide

**Last Updated:** June 2026

Get VISE-D running in a few minutes.

## Prerequisites

- Python 3.11+ installed
- Terminal / command prompt access
- Internet connection (for live weather and online MaStR data)

## Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/your-org/vise-d.git
cd vise-d
```

### 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv vise
.\vise\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv vise
source vise/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Launch the dashboard

```bash
streamlit run dashboard.py
```

The dashboard opens at `http://localhost:8501`.

## The dashboard at a glance

The sidebar groups the pages into five sections (the UI is German):

- **Übersicht** – *Startseite*: entry page with a categorized overview of all analyses.
- **Energiesystemanalysen**
  - *Netzmodell-Szenario* – the central tool: build a distribution grid, place DER
    (PV, wind, battery, heat pump, EV), generate profiles, and run a time-series power flow.
  - *Flexibilitätskonfigurator* – aggregate household flexibility and compare the load profile
    with and without load shifting.
- **Marktstammdatenregister** – *Solaranlagen*, *Windanlagen*, *Speicheranlagen*: map-based
  analysis of real installations from the MaStR, with optional generation simulation.
- **Forschungsergebnisse** – *Integration von E-Fahrzeugen in Verteilnetze* and *Flexibilität
  in Groß- und Verteilnetzen*: read-only summaries of published research.
- **Lastprofilgeneratoren** – per-technology profile generators: *E-Mobilität*, *Wärmepumpe*,
  *Photovoltaik*, *Windenergie*, *Elektrischer Speicher*, *Thermischer Speicher*.

A full page-by-page guide is in
[Dashboard Documentation](../project/dashboard-dokumentation.md) (German).

## First analyses to try

**Generate a PV profile** (*Lastprofilgeneratoren → Photovoltaik*)
1. Choose the location-based mode, enter a town name and installed power (kWp).
2. Set a date range, then click *Profil generieren*.
3. Inspect the PV power time series and key figures.

**Explore real installations** (*Marktstammdatenregister → Solaranlagen*)
1. Enter a town or postal code.
2. Click *Anlagen anzeigen* to see the interactive map and statistics.
3. Optionally run a generation simulation for a chosen period.

**Run a grid scenario** (*Energiesystemanalysen → Netzmodell-Szenario*)
1. Load a predefined network (or upload your own).
2. Set a period, configure DER placement, and generate the profiles.
3. Start the time-series simulation and review the voltage-band, line- and
   transformer-loading results.

## Tips

- **First run is slower** while caches populate; subsequent runs are fast.
- Clear caches via the sidebar **"Cache leeren"** button.
- **UI text is German**; code and docs are English.
- The local MaStR database is optional — without it the app falls back to the shipped town
  lists and the live online register (see the Configuration Guide).

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Module not found" | Activate the virtual environment first |
| "Port already in use" | `streamlit run dashboard.py --server.port 8502` |
| Slow first load | Wait for caches to populate |
| Empty MaStR pages | Provide a database or use the online fallback / examples |

## Next steps

- **[Installation Guide](installation.md)** – detailed setup
- **[Configuration Guide](configuration.md)** – MaStR database and weather data
- **[Dashboard Documentation](../project/dashboard-dokumentation.md)** – page-by-page guide (German)
- **[Developer Guide](../developer-guide/)** – architecture and testing

---

**Author:** Pyosch  
**AI Assistance:** Claude Code (Claude Opus 4.8)
