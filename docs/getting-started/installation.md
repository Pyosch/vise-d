# Installation Guide

**Last Updated:** January 2026

## System Requirements

### Required
- **Python:** 3.11 or higher
- **Operating System:** Windows, Linux, or macOS
- **Memory:** 4 GB RAM minimum (8 GB recommended)
- **Storage:** 2 GB free disk space

### Optional
- **Git:** For cloning repository
- **SQLite browser:** For inspecting MaStR database
- **Docker:** For containerized deployment (future)

## Installation Steps

### 1. Clone Repository

```bash
# HTTPS
git clone https://github.com/your-org/vise-d.git
cd vise-d

# SSH
git clone git@github.com:your-org/vise-d.git
cd vise-d
```

Or download ZIP and extract.

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv vise
.\vise\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv vise
vise\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python3 -m venv vise
source vise/bin/activate
```

**Verify activation:**
```bash
python --version  # Should show Python 3.11+
which python      # Should show path inside vise/ directory
```

### 3. Install Dependencies

```bash
# Install all required packages
pip install --upgrade pip
pip install -r requirements.txt
```

**Installation time:** 2-5 minutes depending on connection speed.

**Key dependencies installed:**
- Streamlit (dashboard framework)
- vpplib 0.0.5 (component models)
- Pandapower (network analysis)
- windpowerlib (wind turbine modeling)
- pandas, numpy (data processing)
- plotly (visualization)

### 4. Download MaStR Database (Optional)

VISE-D uses the German Marktstammdatenregister (MaStR) database for real installation data.

**Option A: Download preprocessed database** (recommended)
```bash
# Download from project releases
# Place in: data/open-mastr.db
```

**Option B: Build from scratch** (advanced)
See [Configuration Guide](configuration.md#mastr-database-setup) for detailed instructions.

### 5. Configure Environment (Optional)

Create `.env` file in project root for custom configuration:

```bash
# data/.env
MASTR_DB_PATH=data/open-mastr.db
WEATHER_DATA_DIR=data/era5_germany_2024_wind
CACHE_TTL_HOURS=1
```

See [Configuration Guide](configuration.md) for all options.

### 6. Verify Installation

```bash
# Run test suite
pytest

# Expected output:
# =========== X passed, Y skipped in Z.XXs ===========
```

**Current test status:** 23/34 passing (67.6%), 11 failures expected (library-level issues)

### 7. Launch Dashboard

```bash
streamlit run dashboard.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Dashboard will open automatically in your default browser.

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Ensure you're in project root directory
cd vise-d
pwd  # Should show .../vise-d

# Verify virtual environment is activated
which python  # Should show path inside vise/ directory

# Reinstall dependencies
pip install -r requirements.txt
```

### vpplib Installation Issues

**Problem:** `ERROR: Could not find a version that satisfies the requirement vpplib==0.0.5`

**Solution:**
```bash
# Install from PyPI
pip install vpplib==0.0.5

# Or install from GitHub if not available
pip install git+https://github.com/greco-project/vpplib.git@0.0.5
```

### Pandapower Network Errors

**Problem:** `KeyError: 'bus'` or similar Pandapower errors

**Solution:**
```bash
# Update Pandapower to compatible version
pip install --upgrade pandapower

# Clear Streamlit cache
rm -rf .streamlit/cache/  # Linux/macOS
Remove-Item -Recurse .streamlit/cache/  # Windows PowerShell
```

### Database Not Found

**Problem:** `FileNotFoundError: data/open-mastr.db not found`

**Solution:**
1. Download MaStR database (see Step 4 above)
2. Place in `data/` directory
3. Verify path in configuration: `src/config/paths.py`

### Streamlit Port Already in Use

**Problem:** `OSError: [Errno 98] Address already in use`

**Solution:**
```bash
# Use different port
streamlit run dashboard.py --server.port 8502

# Or kill existing Streamlit process
# Linux/macOS:
pkill -f streamlit

# Windows:
taskkill /F /IM streamlit.exe
```

### Memory Issues

**Problem:** `MemoryError` or system slowdown

**Solution:**
1. Close other applications
2. Clear Streamlit cache (see "Pandapower Network Errors" above)
3. Reduce cache TTL in configuration:
   ```python
   # src/config/constants.py
   CACHE_TTL_HOURS = 0.5  # Reduce from 1 hour to 30 minutes
   ```

## Platform-Specific Notes

### Windows

**PowerShell Execution Policy:**
If activation fails with "cannot be loaded because running scripts is disabled":
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Long Path Support:**
Enable long paths if you encounter path length errors:
```
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### Linux

**Python Version:**
Some distributions use `python3` instead of `python`:
```bash
python3 -m venv vise
source vise/bin/activate
pip3 install -r requirements.txt
```

**System Packages:**
Install system dependencies for pandas/numpy:
```bash
# Debian/Ubuntu
sudo apt-get install python3-dev build-essential

# Fedora/RHEL
sudo dnf install python3-devel gcc
```

### macOS

**Xcode Command Line Tools:**
Required for compiling some dependencies:
```bash
xcode-select --install
```

**M1/M2 Apple Silicon:**
Some packages may need Rosetta 2:
```bash
# If installation fails, try:
arch -x86_64 pip install -r requirements.txt
```

## Updating VISE-D

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Run migrations (if any)
# Currently no database migrations needed

# Restart dashboard
streamlit run dashboard.py
```

## Uninstallation

```bash
# Deactivate virtual environment
deactivate

# Remove project directory
cd ..
rm -rf vise-d  # Linux/macOS
Remove-Item -Recurse -Force vise-d  # Windows PowerShell
```

## Next Steps

- **[Quickstart Guide](quickstart.md)** - 5-minute walkthrough
- **[Configuration Guide](configuration.md)** - Detailed configuration options
- **[User Guide](../user-guide/)** - Using VISE-D features
- **[Developer Guide](../developer-guide/)** - Contributing to VISE-D

## Getting Help

- **Documentation:** Check [docs/](../) directory
- **Issues:** Report bugs on GitHub Issues
- **Community:** Join discussions on GitHub Discussions

---

**Author:** Pyosch  
**AI Assistance:** GitHub Copilot (Claude Sonnet 4.5)
