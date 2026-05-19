
import pandapower.networks as ppn
import pandapower.timeseries as ts
from pandapower.control import ConstControl
import pandas as pd
import numpy as np

net = ppn.create_cigre_network_mv()
from src.utils.simbench_profiles import Simbench_multiplier

base_load_indices = net.load.index.tolist()
multiplier_df = Simbench_multiplier(net, amplitude=0.35)

abs_load_df = pd.DataFrame(index=multiplier_df.index)
for idx in base_load_indices:
    factor = multiplier_df[idx] if idx in multiplier_df.columns else 1.0
    abs_load_df[str(idx)] = float(net.load.at[idx, 'p_mw']) * factor

print('Time 0 expected load 1:', abs_load_df['1'].iloc[0])
print('Time 24 expected load 1:', abs_load_df['1'].iloc[24])

ds_base_loads = ts.DFData(abs_load_df)
for idx in base_load_indices:
    ConstControl(
        net, element='load', element_index=idx,
        variable='p_mw', data_source=ds_base_loads, profile_name=str(idx)
    )

print('Before:', net.load.at[1, 'p_mw'])
ts.run_timeseries(net, time_steps=[0, 24])
print('After (should be time step 24):', net.load.at[1, 'p_mw'])
