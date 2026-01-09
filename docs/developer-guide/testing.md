# Testing Guide

**Last Updated:** January 2026

## Phase 1 Testing Checklist

### ✅ Changes Applied:
- Updated all `mastr_preprocessing` imports → `src.mastr`
- Updated all `mastr_energy_generation` imports → `src.mastr.simulation`
- Updated `utils` imports → `src.utils`
- Added `src.config.MASTR_DB_PATH` import
- Replaced hardcoded database path with config-based path

## 🧪 Testing Steps:

### 1. Start Dashboard (2 minutes)
```bash
streamlit run dashboard.py
```

**Expected:** Dashboard loads without import errors

**If error:** Check terminal for missing modules/imports

---

### 2. Test MaStR Solar Analysis (~3 minutes)
**Steps:**
1. Navigate to "Photovoltaic Analysis" or MaStR solar page
2. Select a location from dropdown (e.g., "Essen", "Aachen")
3. Click to load solar data

**Expected:** 
- ✅ Location dropdown populates
- ✅ Solar installation data loads
- ✅ Map/visualizations display

**If error:** Note which function fails (preprocessing, simulation, etc.)

---

### 3. Test MaStR Wind Analysis (~2 minutes)
**Steps:**
1. Navigate to wind energy page
2. Select location
3. Load wind turbine data

**Expected:**
- ✅ Wind locations load
- ✅ Turbine data displays

---

### 4. Test MaStR Storage Analysis (~2 minutes)
**Steps:**
1. Navigate to storage page
2. Select location
3. Load storage data

**Expected:**
- ✅ Storage locations load
- ✅ Storage systems display

---

### 5. Quick Validation Test (~1 minute)
**Steps:**
1. Try entering invalid parameters in any technology form
2. Check if validation messages appear

**Expected:**
- ✅ Validation works (if ADVANCED_VALIDATION_AVAILABLE = True)

---

## ⚠️ Known Configuration Note:
Database path in dashboard.py line 62 is:
```python
mastr_db_path = str(MASTR_DB_PATH)  # Points to src/config default
# Alternative: mastr_db_path = 'C:/Users/mashu/.open-MaStR/data/sqlite/open-mastr.db'
```

If your MaStR database is at a different location, either:
- **Option A:** Update `src/config/paths.py` MASTR_DB_PATH
- **Option B:** Uncomment the alternative line with your path

---

## 📝 If Issues Found:

### Import Errors:
- Check if old files still exist causing confusion
- Verify Python can find `src/` directory

### Database Path Errors:
- Update `src/config/paths.py` with your database location
- Or use the alternative hardcoded path in dashboard.py

### Module Not Found:
- Ensure you're running from project root: `c:\Users\sbirk\Documents\Code\vise-d\`
- Python needs to see the `src/` directory

---

## ✅ Success Criteria:
- [ ] Dashboard starts without errors
- [ ] At least one MaStR page loads data successfully
- [ ] No import errors in terminal
- [ ] Validation utilities work (if available)

---

## 🎯 After Testing:
Report results:
- "Working perfectly" → Continue to Phase 2
- "Error in [specific function]" → We'll fix it immediately
- "Database path issue" → We'll adjust configuration

This validates the Phase 1 foundation before building Phases 2-5 on top.
