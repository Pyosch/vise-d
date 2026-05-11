"""
Interface to vpplib network functions.

Real imports from vpplib dev_refactor branch (operator.py).
To switch to a future PyPI release, this file needs no changes.
"""
from vpplib.operator import assign_assets_to_buses, build_timeseries_net

__all__ = ["assign_assets_to_buses", "build_timeseries_net"]
