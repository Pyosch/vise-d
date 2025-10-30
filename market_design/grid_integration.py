"""
Pandapower network integration for tariff analysis.

Provides coupling logic between tariff models and Pandapower network
analysis to evaluate grid impacts of different pricing schemes.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd
import pandapower as pp

# Implementation in Phase 7.3 - See roadmap.md Section 7.2
