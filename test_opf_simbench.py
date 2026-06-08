import simbench as sb
import pandapower as pp
import numpy as np
import traceback
import warnings
warnings.filterwarnings('ignore')

codes = [
    '1-LV-rural1--0-sw',
    '1-LV-semiurb4--0-sw',
    '1-LV-urban6--0-sw',
    '1-MV-rural--0-sw',
    '1-MV-semiurb--0-sw',
    '1-MV-urban--0-sw',
    '1-MVLV-semiurb-all-0-sw',
]


def fix_simbench_dtypes(net):
    """Fix all dtype issues that SimBench introduces (object/float columns that should be bool/numeric)."""
    for element in ['bus', 'line', 'trafo', 'trafo3w', 'load', 'sgen', 'gen',
                    'ext_grid', 'shunt', 'ward', 'xward', 'storage', 'switch']:
        if element not in net or net[element] is None or len(net[element]) == 0:
            continue
        df = net[element]

        # 'in_service': NaN → True (element is active by default)
        if 'in_service' in df.columns and df['in_service'].dtype != bool:
            net[element]['in_service'] = df['in_service'].fillna(True).astype(bool)

        # 'controllable': NaN → False (not controllable by default)
        if 'controllable' in df.columns and df['controllable'].dtype != bool:
            net[element]['controllable'] = df['controllable'].fillna(False).astype(bool)

        # Fix min/max columns that are object type with NaN to float
        for col in df.columns:
            if any(col.startswith(p) for p in ['min_p', 'max_p', 'min_q', 'max_q']):
                if df[col].dtype == 'object':
                    net[element][col] = pd.to_numeric(df[col], errors='coerce')


def prepare_opf_like_app(net):
    """
    Prepare OPF using the SAME approach as netzmittimeseries.py:
    - Wide voltage limits (0.85-1.15)
    - Add controllable storage at stressed buses
    - Cost functions for ext_grid + storage
    """
    fix_simbench_dtypes(net)

    # === Voltage limits (same as netzmittimeseries.py line 755) ===
    net.bus["min_vm_pu"] = 0.85
    net.bus["max_vm_pu"] = 1.15

    # === Ext grid limits ===
    net.ext_grid["min_p_mw"] = -9999.0
    net.ext_grid["max_p_mw"] = 9999.0
    net.ext_grid["min_q_mvar"] = -9999.0
    net.ext_grid["max_q_mvar"] = 9999.0

    # === Clear old costs ===
    if hasattr(net, "poly_cost") and net.poly_cost is not None and len(net.poly_cost) > 0:
        net.poly_cost.drop(net.poly_cost.index, inplace=True)

    # === Cost for every ext_grid ===
    for eg_idx in net.ext_grid.index:
        pp.create_poly_cost(net, eg_idx, "ext_grid", cp1_eur_per_mw=1.0)

    # === Add controllable storage (same logic as netzmittimeseries.py lines 683-741) ===
    try:
        pp.runpp(net, verbose=False)
        vm_deviation = (net.res_bus["vm_pu"] - 1.0).abs()
        slack_buses = set(net.ext_grid["bus"].values)
        candidates = vm_deviation.drop(
            index=[b for b in slack_buses if b in vm_deviation.index], errors="ignore"
        )
        n_units = min(max(1, len(candidates) // 20), 10)
        opf_storage_buses = candidates.nlargest(n_units).index.tolist()
    except Exception:
        slack_buses = set(net.ext_grid["bus"].values)
        opf_storage_buses = [b for b in net.bus.index if b not in slack_buses][:1]
        n_units = len(opf_storage_buses)

    total_load_mw = net.load["p_mw"].sum() if len(net.load) > 0 else 1.0
    per_unit_power = float(np.clip((total_load_mw * 0.3) / max(1, n_units), 0.1, 5.0))

    opf_storage_indices = []
    for k, bus in enumerate(opf_storage_buses):
        idx = pp.create_storage(
            net, bus=bus, p_mw=0.0,
            max_e_mwh=per_unit_power * 2.0,
            q_mvar=0.0,
            min_p_mw=-per_unit_power,
            max_p_mw=per_unit_power,
            min_q_mvar=-per_unit_power,
            max_q_mvar=per_unit_power,
            soc_percent=50.0,
            controllable=True,
            name=f"OPF_Storage_{k}"
        )
        opf_storage_indices.append(idx)

    for s_idx in opf_storage_indices:
        pp.create_poly_cost(net, s_idx, "storage", cp1_eur_per_mw=0.0, cp2_eur_per_mw2=1.0)

    # === Loads: non-controllable ===
    if len(net.load) > 0:
        net.load["controllable"] = False

    # === Sgens: non-controllable (fixed generation) ===
    if len(net.sgen) > 0:
        net.sgen["controllable"] = False

    return net, n_units, opf_storage_buses


import pandas as pd

for code in codes:
    print(f"\n{'='*60}")
    print(f"  {code}")
    print(f"{'='*60}")
    net = sb.get_simbench_net(code)
    print(f"  Buses: {len(net.bus)}, Lines: {len(net.line)}, Loads: {len(net.load)}, Sgen: {len(net.sgen)}")

    # PF test
    fix_simbench_dtypes(net)
    try:
        pp.runpp(net)
        print(f"  PF:  OK  (Vmin={net.res_bus.vm_pu.min():.4f}, Vmax={net.res_bus.vm_pu.max():.4f})")
    except Exception as e:
        print(f"  PF:  FAILED - {e}")
        continue

    # Skip huge network
    if len(net.bus) > 1000:
        print(f"  OPF: SKIPPED (too large: {len(net.bus)} buses, PF confirmed OK)")
        continue

    # OPF test (using app's approach)
    net2 = sb.get_simbench_net(code)  # fresh copy
    try:
        net2, n_units, storage_buses = prepare_opf_like_app(net2)
        print(f"  OPF setup: {n_units} storage units at buses {storage_buses}")
        pp.runopp(net2, verbose=False, init='pf', calculate_voltage_angles=False)
        print(f"  OPF: OK  (Vmin={net2.res_bus.vm_pu.min():.4f}, Vmax={net2.res_bus.vm_pu.max():.4f})")
    except Exception as e:
        print("  OPF Exception traceback:")
        traceback.print_exc()
        err = str(e)[:300]
        print(f"  OPF: FAILED - {err}")
