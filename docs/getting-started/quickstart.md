# Quickstart Guide

**Last Updated:** January 2026

Get VISE-D running in 5 minutes with this streamlined guide.

## Prerequisites

✅ Python 3.11+ installed  
✅ Terminal/command prompt access  
✅ Internet connection

## 5-Minute Setup

### 1. Clone and Enter Project (30 seconds)

```bash
git clone https://github.com/your-org/vise-d.git
cd vise-d
```

### 2. Create Virtual Environment (30 seconds)

**Windows:**
```powershell
python -m venv vise
.\vise\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv vise
source vise/bin/activate
```

### 3. Install Dependencies (2-3 minutes)

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

*Coffee break recommended* ☕

### 4. Launch Dashboard (10 seconds)

```bash
streamlit run dashboard.py
```

Browser opens automatically at `http://localhost:8501` 🎉

## First Steps in Dashboard

### Explore Navigation

**17 pages organized in 5 categories:**

1. **🔬 Research & Analysis**
   - Research Results (EV integration studies)
   - Hydrogen Research (DSO interventions)

2. **⚙️ Technology Configuration**
   - BEV Settings (electric vehicles)
   - Heat Pump Configuration
   - PV Configuration (solar)
   - Wind Configuration
   - Electrical Storage
   - Thermal Storage
   - Hydrogen Electrolyzer

3. **📊 MaStR Data Analysis**
   - Solar Installations (11,558 installations)
   - Wind Installations (3,827 turbines)
   - Storage Installations (11,042 systems)

4. **⚡ Energy Generation**
   - Solar Energy Analysis
   - Wind Energy Analysis

5. **🗺️ Planning & Forecasting**
   - FFPV & WEA Planning (site planning)
   - OpenSTEF Forecasting (predictions)

### Try Simple Analysis

**Option 1: Solar Installation Map** (1 minute)
1. Navigate to **"Solar Installations (MaStR)"**
2. Select region: **"Baden-Württemberg"**
3. View interactive map with 11,558+ installations
4. Explore installation details and statistics

**Option 2: PV Configuration** (2 minutes)
1. Navigate to **"PV Configuration"**
2. Default values pre-filled (30° tilt, 180° azimuth)
3. Click **"Simulate PV System"**
4. View energy generation profile and statistics

**Option 3: Network Analysis** (2 minutes)
1. Navigate to **"Network Calculations"**
2. Select example network: **"Simple LV Network"**
3. Click **"Run Power Flow"**
4. View voltage levels and line loading

## Key Features to Explore

### 1. Interactive Maps (MaStR Pages)
- **Geographic visualization** of real German installations
- **Filter by region**: Bundesland → Kreis → Gemeinde
- **Installation details**: Capacity, age, technology type

### 2. Technology Simulation (Configuration Pages)
- **Parameter forms** with German UI labels
- **Real-time validation** with industry standards
- **vpplib integration** for accurate component models
- **Energy profiles** with hourly/daily/yearly views

### 3. Site Planning (FFPV & WEA Planning)
- **Draw polygons** on interactive map
- **Obstacle detection** from OpenStreetMap
- **Automated placement** for solar panels/wind turbines
- **Energy generation** simulation

### 4. Forecasting (OpenSTEF Forecasting)
- **ML-based predictions** for PV/wind generation
- **Weather data integration** (DWD/ERA5)
- **MLflow tracking** for model versions
- **Forecast visualization** with confidence intervals

### 5. Network Analysis (Network Calculations)
- **Pandapower integration** for power flow
- **Voltage analysis** across buses
- **Line loading** and transformer utilization
- **Grid planning** insights

## Quick Tips

### Performance
- **First load is slow** (15-30 seconds) - data caching in progress
- **Subsequent loads are fast** (<3 seconds) - cached data reused
- **Clear cache** if needed: Sidebar → "Cache leeren" button

### Language
- **UI text**: German (for target users)
- **Code/docs**: English (for developers)
- **Database columns**: German (MaStR compatibility)

### Data
- **MaStR database** optional for most features
- **Some pages** work without database (examples, simulations)
- **Download database** for full functionality ([Installation Guide](installation.md#4-download-mastr-database-optional))

### Errors
- **Import errors**: Ensure virtual environment activated
- **Port in use**: Try `streamlit run dashboard.py --server.port 8502`
- **Cache issues**: Delete `.streamlit/cache/` directory

## Common Workflows

### Workflow 1: Analyze Existing Installations
```
MaStR Data Analysis pages → Select region → Explore map → View statistics
```

**Time:** 2-5 minutes  
**Requirements:** MaStR database (optional, works with examples)

### Workflow 2: Design New PV System
```
PV Configuration → Enter parameters → Simulate → Analyze results
```

**Time:** 5-10 minutes  
**Requirements:** None (uses default weather data)

### Workflow 3: Plan Solar Farm
```
FFPV & WEA Planning → Draw site boundary → Detect obstacles → Pack panels → Simulate
```

**Time:** 10-15 minutes  
**Requirements:** Internet (for OpenStreetMap data)

### Workflow 4: Forecast Energy Production
```
OpenSTEF Forecasting → Configure model → Train → Generate forecast → Evaluate
```

**Time:** 15-30 minutes  
**Requirements:** Historical weather data

### Workflow 5: Analyze Grid Impact
```
Technology Configuration → Network Calculations → Add components → Run power flow → Analyze voltage/loading
```

**Time:** 10-20 minutes  
**Requirements:** None (uses example networks)

## Next Steps

### Learn More
- **[Dashboard Documentation](../project/dashboard-dokumentation.md)** - Page-by-page guide (German)
- **[Configuration Guide](configuration.md)** - Advanced configuration options

### Get Data
- **[MaStR Database Setup](configuration.md#mastr-database-setup)** - Real installation data
- **[Weather Data](configuration.md#weather-data-configuration)** - ERA5 historical data

### Contribute
- **[Developer Guide](../developer-guide/)** - Architecture and testing
- **[Project Overview](../../roadmap.md)** - Project status and overview

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Module not found" | Activate virtual environment: `source vise/bin/activate` |
| "Port already in use" | Use different port: `--server.port 8502` |
| Slow performance | Wait for cache to populate (~30 seconds first run) |
| Empty MaStR pages | Download database or use example data |
| Plot not rendering | Clear cache: `.streamlit/cache/` directory |

## Getting Help

- **[Installation Guide](installation.md)** - Detailed setup instructions
- **GitHub Issues** - Report bugs
- **GitHub Discussions** - Ask questions

---

**Enjoy exploring VISE-D!** 🚀

**Author:** Pyosch  
**AI Assistance:** Claude Code (Claude Opus 4.8)
