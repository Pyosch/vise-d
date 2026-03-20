import pvlib

cec_modules = pvlib.pvsystem.retrieve_sam('CECMod')

print(cec_modules)
# Find all Canadian Solar entries (try both naming conventions)
cs1 = [m for m in cec_modules.columns if 'Canadian_Solar' in m]
cs2 = [m for m in cec_modules.columns if 'CSI_Solar' in m]

print("Canadian Solar entries:", cs1[:10])
print("CSI Solar entries:", cs2[:10])