"""Unit tests for the Netzmodell-Szenario page (``src/pages/netzmodell.py``).

Focus: the profile-assembly step ``_build_sim_profiles`` must keep MaStR plants
(whose generation timeseries are simulated and stored individually when they are
added) strictly separate from the generic, synthetic PV profile generated in
Section 3.5. Generating the synthetic PV profile must never create or overwrite
a profile for a MaStR plant.
"""

from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pandapower as pp

from src.pages import netzmodell


N_STEPS = 96


def _make_net():
    """Net with one synthetic PV, one MaStR PV and one MaStR wind sgen.

    Returns the net plus the three sgen indices.
    """
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=0.4)
    b1 = pp.create_bus(net, vn_kv=0.4)
    syn_pv = pp.create_sgen(net, bus=b0, p_mw=0.01, name="PV_Gezielt_0", type="PV")
    mastr_pv = pp.create_sgen(net, bus=b1, p_mw=0.005, name="PV_SEE123", type="PV")
    mastr_wind = pp.create_sgen(net, bus=b1, p_mw=0.5, name="Wind_SEE999", type="WKA")
    return net, syn_pv, mastr_pv, mastr_wind


def _build(net, session):
    """Call _build_sim_profiles with a mocked st.session_state."""
    mock_st = Mock()
    mock_st.session_state = session
    with patch.object(netzmodell, "st", mock_st):
        return netzmodell._build_sim_profiles(net, n_steps=N_STEPS)


class TestMastrProfileSeparation:
    """The synthetic PV profile must not bleed into MaStR plants."""

    def test_mastr_plants_keep_individual_profile_when_pv_profile_set(self):
        net, syn_pv, mastr_pv, mastr_wind = _make_net()

        pv_profile = pd.Series(np.linspace(0.0, 1.0, N_STEPS))      # kW/kWp
        mastr_pv_ts = pd.Series(np.full(N_STEPS, 2.0))             # kW
        mastr_wind_ts = pd.Series(np.full(N_STEPS, 100.0))         # kW

        sgen_df = _build(net, {
            "nsv2_profile_pv": pv_profile,
            "nsv2_mastr_sgen_ts": {mastr_pv: mastr_pv_ts, mastr_wind: mastr_wind_ts},
        })["sgen"]

        # Synthetic PV is driven by the generic profile scaled by its p_mw.
        np.testing.assert_allclose(
            sgen_df[syn_pv].to_numpy(), pv_profile.to_numpy() * 0.01
        )

        # MaStR PV keeps its OWN simulated timeseries (kW -> MW) ...
        np.testing.assert_allclose(
            sgen_df[mastr_pv].to_numpy(), mastr_pv_ts.to_numpy() / 1000.0
        )
        # ... and is provably NOT the generic profile applied to its rating.
        assert not np.allclose(
            sgen_df[mastr_pv].to_numpy(), pv_profile.to_numpy() * 0.005
        )

        # MaStR wind is untouched by the PV profile, keeps its own timeseries.
        np.testing.assert_allclose(
            sgen_df[mastr_wind].to_numpy(), mastr_wind_ts.to_numpy() / 1000.0
        )

    def test_mastr_profile_independent_of_missing_pv_profile(self):
        # No synthetic PV profile generated yet (nsv2_profile_pv absent).
        net, syn_pv, mastr_pv, _mastr_wind = _make_net()
        mastr_pv_ts = pd.Series(np.full(N_STEPS, 3.0))            # kW

        sgen_df = _build(net, {
            "nsv2_mastr_sgen_ts": {mastr_pv: mastr_pv_ts},
        })["sgen"]

        # Synthetic PV has no profile -> no column (stays at static p_mw).
        assert syn_pv not in sgen_df.columns
        # MaStR PV still carries its individual profile regardless.
        np.testing.assert_allclose(
            sgen_df[mastr_pv].to_numpy(), mastr_pv_ts.to_numpy() / 1000.0
        )

    def test_same_bus_and_rating_get_distinct_profiles(self):
        # A MaStR PV and a synthetic PV with identical rating at the same bus:
        # membership in nsv2_mastr_sgen_ts (not the name/bus/rating) decides the
        # source, so the two must not collapse onto the same curve.
        net = pp.create_empty_network()
        b = pp.create_bus(net, vn_kv=0.4)
        syn = pp.create_sgen(net, bus=b, p_mw=0.01, name="PV_Szenario_0", type="PV")
        mastr = pp.create_sgen(net, bus=b, p_mw=0.01, name="PV_SEE777", type="PV")

        pv_profile = pd.Series(np.linspace(0.0, 1.0, N_STEPS))
        mastr_ts = pd.Series(np.full(N_STEPS, 5.0))   # 5 kW -> 0.005 MW

        sgen_df = _build(net, {
            "nsv2_profile_pv": pv_profile,
            "nsv2_mastr_sgen_ts": {mastr: mastr_ts},
        })["sgen"]

        np.testing.assert_allclose(sgen_df[syn].to_numpy(), pv_profile.to_numpy() * 0.01)
        np.testing.assert_allclose(sgen_df[mastr].to_numpy(), mastr_ts.to_numpy() / 1000.0)
        assert not np.allclose(sgen_df[syn].to_numpy(), sgen_df[mastr].to_numpy())
