"""Unit tests for the Netzmodell PDF figure builders (src/utils/pdf_export.py).

The report figures are rendered with matplotlib (Agg, in-process) — no kaleido
/Chromium. The line-loading heatmap must label its y-axis with the line numbers
as discrete ticks, the transformer-loading figure must draw one line per
transformer (named from the net), and ``_fig_to_png`` must return PNG bytes.
"""

__author__ = "Pyosch"
__credits__ = ["Claude Code (Claude Opus 4.8)"]

import numpy as np
import pandas as pd
import pandapower as pp

from src.utils import pdf_export as pe


def _dt(n=6):
    return pd.date_range("2025-06-01", periods=n, freq="15min")


class TestLoadingHeatmap:
    def test_yaxis_ticklabels_are_the_line_numbers(self):
        dt = _dt()
        loading = pd.DataFrame(
            {i: np.linspace(10, 90, len(dt)) for i in range(4)}, index=dt)

        fig = pe._build_loading_figure(loading, dt)
        ax = fig.axes[0]
        labels = [t.get_text() for t in ax.get_yticklabels()]

        assert labels == ["0", "1", "2", "3"]

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

    def test_one_line_per_transformer_named_from_net(self):
        net = self._net()
        dt = _dt()
        trafo = pd.DataFrame(
            {t: np.linspace(20, 90, len(dt)) for t in net.trafo.index}, index=dt)

        fig = pe._build_trafo_figure(trafo, dt, net)
        _, labels = fig.axes[0].get_legend_handles_labels()

        assert labels == ["Ortsnetztrafo"]   # one legend entry per transformer

    def test_returns_none_when_empty(self):
        assert pe._build_trafo_figure(pd.DataFrame(), _dt(), None) is None


class TestFigToPng:
    def test_returns_png_bytes(self):
        net = TestTransformerFigure._net()
        dt = _dt()
        trafo = pd.DataFrame(
            {t: np.linspace(20, 90, len(dt)) for t in net.trafo.index}, index=dt)

        png = pe._fig_to_png(pe._build_trafo_figure(trafo, dt, net))

        assert png[:8] == b"\x89PNG\r\n\x1a\n"   # PNG magic number
