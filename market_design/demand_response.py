"""
Demand response modeling for price-responsive consumer behavior.

Provides functions to model load shifting and reduction based on
price signals from TOU or RTP tariffs.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

# Implementation in Phase 7.1.3 - See roadmap.md Section 7.2
