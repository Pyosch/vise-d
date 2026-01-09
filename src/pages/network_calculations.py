"""Network calculations page for VISE-D dashboard.

This page displays pandapower network analysis examples.

Author: Pyosch
AI Assistance: GitHub Copilot (Claude Sonnet 4.5)
Created: January 2026
"""

__author__ = "Pyosch"
__credits__ = ["GitHub Copilot (Claude Sonnet 4.5)"]

from src.network import pp_networks


def network_calculations():
    """Display pandapower network calculation examples.
    
    This is a simple wrapper that calls the pp_networks() function
    to display German distribution network examples.
    """
    pp_networks()
