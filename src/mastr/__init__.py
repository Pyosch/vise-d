"""MaStR (Marktstammdatenregister) integration package.

Provides data fetching, preprocessing, and simulation utilities for German energy
system data from the Marktstammdatenregister.

Author: Pyosch
AI Assistance: Claude Code (Claude Opus 4.8)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

# Submodules are intentionally NOT re-exported here. Importing any submodule
# (e.g. ``from src.mastr.preprocessing import ...``) executes this __init__ first;
# eager re-exports would then pull in *all* submodules — including ``simulation``
# with its heavy pvlib / windpowerlib / vpplib / fuzzywuzzy imports — even for
# callers that only need the lightweight preprocessing or online helpers.
#
# Import directly from the submodule you need, e.g.:
#     from src.mastr.preprocessing import prepare_solar_data
#     from src.mastr.simulation import wind_turbine_matching
