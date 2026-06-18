"""Unit tests for the Netzmodell timeseries Excel serializer.

``_timeseries_to_xlsx_bytes`` turns the simulated per-step results (network +
DER) into a single ``.xlsx`` workbook. Single-run scenarios use one sheet per
table; the flexibility comparison run writes each table twice with an
``_ohne`` / ``_mit`` suffix. Columns are relabelled with the element name from
the configured net, and empty tables are skipped.
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

from io import BytesIO

import numpy as np
import pandas as pd
import pandapower as pp

from src.pages import netzmodell


N_STEPS = 4


def _make_net():
    """Small net: 2 buses, 1 line, 1 sgen, 1 load, 1 storage (all named)."""
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=0.4, name="Knoten A")
    b1 = pp.create_bus(net, vn_kv=0.4, name="Knoten B")
    pp.create_ext_grid(net, bus=b0)
    pp.create_line(net, from_bus=b0, to_bus=b1, length_km=0.1,
                   std_type="NAYY 4x50 SE", name="Leitung 1")
    pp.create_sgen(net, bus=b1, p_mw=0.01, name="PV 1")
    pp.create_load(net, bus=b1, p_mw=0.02, name="Last 1")
    pp.create_storage(net, bus=b1, p_mw=0.0, max_e_mwh=0.01, name="Speicher 1")
    return net


def _dt_index(n=N_STEPS):
    return pd.date_range("2025-06-01", periods=n, freq="15min")


def _tables(net):
    """A full per-scenario table dict with the real element indices as columns."""
    idx = _dt_index()
    return {
        "voltage": pd.DataFrame(
            {b: np.linspace(1.0, 0.98, N_STEPS) for b in net.bus.index}, index=idx),
        "loading": pd.DataFrame(
            {ln: np.linspace(10.0, 80.0, N_STEPS) for ln in net.line.index}, index=idx),
        "sgen": pd.DataFrame(
            {s: np.full(N_STEPS, 0.005) for s in net.sgen.index}, index=idx),
        "load": pd.DataFrame(
            {ld: np.full(N_STEPS, 0.02) for ld in net.load.index}, index=idx),
        "storage": pd.DataFrame(
            {stg: np.full(N_STEPS, 0.0) for stg in net.storage.index}, index=idx),
    }


def _read(xlsx_bytes):
    return pd.read_excel(BytesIO(xlsx_bytes), sheet_name=None)


class TestSingleRun:
    def test_workbook_has_one_sheet_per_table(self):
        net = _make_net()
        scenarios = {"": _tables(net)}

        sheets = _read(netzmodell._timeseries_to_xlsx_bytes(scenarios, net))

        assert set(sheets) == {
            "Spannung_pu", "Leitungsausl_%",
            "DER_Einspeisung_MW", "DER_Last_MW", "DER_Speicher_MW",
        }

    def test_rows_match_steps_and_columns_carry_element_names(self):
        net = _make_net()
        scenarios = {"": _tables(net)}

        sheets = _read(netzmodell._timeseries_to_xlsx_bytes(scenarios, net))
        voltage = sheets["Spannung_pu"]

        # One row per timestep.
        assert len(voltage) == N_STEPS
        # Headers are relabelled "{idx} ({name})" — the bus names must appear.
        headers = " | ".join(str(c) for c in voltage.columns)
        assert "Knoten A" in headers and "Knoten B" in headers
        # DER feed-in is in MW with the sgen name in the header.
        sgen = sheets["DER_Einspeisung_MW"]
        assert any("PV 1" in str(c) for c in sgen.columns)


class TestComparison:
    def test_each_table_is_written_per_scenario_with_suffix(self):
        net = _make_net()
        scenarios = {"ohne": _tables(net), "mit": _tables(net)}

        sheets = _read(netzmodell._timeseries_to_xlsx_bytes(scenarios, net))

        assert "Spannung_pu_ohne" in sheets
        assert "Spannung_pu_mit" in sheets
        assert "DER_Last_MW_ohne" in sheets
        assert "DER_Last_MW_mit" in sheets

    def test_sheet_names_stay_within_excel_31_char_limit(self):
        net = _make_net()
        scenarios = {"ohne": _tables(net), "mit": _tables(net)}

        sheets = _read(netzmodell._timeseries_to_xlsx_bytes(scenarios, net))

        assert all(len(name) <= 31 for name in sheets)


class TestEmptyTables:
    def test_empty_or_missing_tables_are_skipped(self):
        net = _make_net()
        tables = _tables(net)
        tables["loading"] = pd.DataFrame()      # e.g. net without lines
        tables.pop("storage")                   # table absent entirely
        scenarios = {"": tables}

        sheets = _read(netzmodell._timeseries_to_xlsx_bytes(scenarios, net))

        assert "Leitungsausl_%" not in sheets
        assert "DER_Speicher_MW" not in sheets
        assert "Spannung_pu" in sheets


class TestTsTables:
    def test_der_profiles_are_reindexed_onto_network_time_index(self):
        idx = _dt_index()
        voltage = pd.DataFrame({0: np.ones(N_STEPS)}, index=idx)
        # Profiles come integer-indexed (simulation step) from _build_sim_profiles.
        profiles = {"sgen": pd.DataFrame({0: np.full(N_STEPS, 0.01)},
                                         index=range(N_STEPS))}

        tables = netzmodell._ts_tables(voltage, pd.DataFrame(), profiles)

        assert list(tables["sgen"].index) == list(idx)

    def test_length_mismatch_leaves_profile_index_untouched(self):
        idx = _dt_index(N_STEPS)
        voltage = pd.DataFrame({0: np.ones(N_STEPS)}, index=idx)
        profiles = {"sgen": pd.DataFrame({0: [0.01, 0.02]}, index=range(2))}

        tables = netzmodell._ts_tables(voltage, pd.DataFrame(), profiles)

        assert list(tables["sgen"].index) == [0, 1]


class TestHasAnyTable:
    def test_false_when_all_tables_empty_or_none(self):
        scenarios = {"": {"voltage": pd.DataFrame(), "loading": None}}
        assert netzmodell._has_any_table(scenarios) is False

    def test_true_when_any_table_has_data(self):
        scenarios = {"": {"voltage": pd.DataFrame({0: [1.0]}), "loading": None}}
        assert netzmodell._has_any_table(scenarios) is True
