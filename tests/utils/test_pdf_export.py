"""Unit tests for the Netzmodell PDF figure builders (src/utils/pdf_export.py).

Focus on the parts that do not require kaleido/Chromium: the line-loading
heatmap must use a categorical y-axis (so line numbers render as discrete
ticks instead of a continuous -0.5..3.5 range), and the transformer-loading
figure must produce one trace per transformer labelled with its name.
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import numpy as np
import pandas as pd
import pandapower as pp

from src.utils import pdf_export as pe


def _dt(n=6):
    return pd.date_range("2025-06-01", periods=n, freq="15min")


class TestLoadingHeatmapAxis:
    def test_yaxis_is_categorical_so_line_numbers_show_as_ticks(self):
        dt = _dt()
        loading = pd.DataFrame(
            {i: np.linspace(10, 90, len(dt)) for i in range(4)}, index=dt)

        fig = pe._build_loading_figure(loading, dt)

        assert fig.layout.yaxis.type == "category"

    def test_returns_none_for_empty_loading(self):
        assert pe._build_loading_figure(pd.DataFrame(), _dt()) is None


class TestTransformerFigure:
    @staticmethod
    def _net():
        net = pp.create_empty_network()
        hv = pp.create_bus(net, vn_kv=10.0)
        lv = pp.create_bus(net, vn_kv=0.4)
        pp.create_ext_grid(net, bus=hv)
        pp.create_transformer(net, hv_bus=hv, lv_bus=lv,
                              std_type="0.4 MVA 10/0.4 kV", name="Ortsnetztrafo")
        return net

    def test_one_trace_per_transformer_named_from_net(self):
        net = self._net()
        dt = _dt()
        trafo = pd.DataFrame(
            {t: np.linspace(20, 90, len(dt)) for t in net.trafo.index}, index=dt)

        fig = pe._build_trafo_figure(trafo, dt, net)

        assert len(fig.data) == len(net.trafo)
        assert any("Ortsnetztrafo" in (tr.name or "") for tr in fig.data)

    def test_returns_none_when_empty(self):
        assert pe._build_trafo_figure(pd.DataFrame(), _dt(), None) is None
