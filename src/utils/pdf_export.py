"""pdf_export.py — Simulation report builder for the VISE-D Netzmodell page.

Public functions:

    build_netzmodell_pdf(net, voltage_df, loading_df, dt_index, session_state, …)
        → bytes   (Netzmodell-specific, branded A4 portrait report)

    generate_pdf_report_matplotlib(figures, ...)
        → bytes   (generic Matplotlib-figure PDF, kept for other pages)

Figures are rendered to PNG with matplotlib (Agg backend, in-process) and
assembled with fpdf2 — no kaleido/Chromium dependency, which keeps PDF
generation fast and the deployment lean.
"""

from __future__ import annotations

import io
import datetime
from typing import Any

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap


# ---------------------------------------------------------------------------
# Optional imports — fail gracefully so the rest of the app keeps working
# ---------------------------------------------------------------------------
try:
    from fpdf import FPDF
    _HAS_FPDF = True
except ImportError:
    _HAS_FPDF = False


# ---------------------------------------------------------------------------
# Shared colour palette
# ---------------------------------------------------------------------------
_PRIMARY   = (30, 64, 175)     # deep blue header  (brand)
_ACCENT    = (37, 99, 235)     # lighter accent blue
_SECONDARY = (240, 245, 255)   # very light blue background
_GREEN_RGB = (34, 197, 94)
_RED_RGB   = (239, 68, 68)
_DARK      = (20, 20, 30)
_LIGHT_BG  = (248, 249, 252)
_WHITE     = (255, 255, 255)
_LIGHT_GRAY = (245, 245, 245)


# ---------------------------------------------------------------------------
# Latin-1 safety helper
# ---------------------------------------------------------------------------
# fpdf2 core fonts (Helvetica, Times, Courier) only support Latin-1 (ISO-8859-1).
# Any character outside that range causes FPDFUnicodeEncodingException.
# _safe() converts a string to a safe Latin-1 representation:
#   - em dash (U+2014) and en dash (U+2013) -> hyphen
#   - middle dot (U+00B7) is Latin-1 but kept as '|' for clarity in header
#   - multiplication sign (U+00D7) -> 'x'
#   - emoji / other high codepoints -> stripped
_CHAR_MAP = str.maketrans({
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u00B7": "|",   # middle dot  (technically Latin-1 but safer as pipe)
    "\u00D7": "x",   # multiplication sign
    "\u2018": "'",   # left single quotation mark
    "\u2019": "'",   # right single quotation mark
    "\u201C": '"',   # left double quotation mark
    "\u201D": '"',   # right double quotation mark
    "\u2026": "...", # ellipsis
})

def _safe(text: str) -> str:
    """Return *text* with all non-Latin-1 characters made safe for fpdf2 core fonts."""
    text = text.translate(_CHAR_MAP)
    # Strip any remaining characters outside Latin-1 (e.g. emoji)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


# ===========================================================================
# ── NETZMODELL-SPECIFIC PDF ─────────────────────────────────────────────────
# ===========================================================================

class _NetzPDF(FPDF if _HAS_FPDF else object):
    """Custom FPDF subclass with VISE-D branding and convenience helpers.

    Falls back to `object` when fpdf2 is not installed so the module
    still imports without error (the build function raises ImportError).
    """

    def __init__(self, net_name: str, date_range: str):
        if not _HAS_FPDF:
            return
        super().__init__(orientation="P", unit="mm", format="A4")
        self.net_name = net_name
        self.date_range = date_range
        self.set_auto_page_break(auto=True, margin=18)
        self.set_font("Helvetica", size=10)

    # ------------------------------------------------------------------ #
    # Header / footer
    # ------------------------------------------------------------------ #

    def header(self):
        self.set_fill_color(*_PRIMARY)
        self.rect(0, 0, 210, 14, "F")
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 9)
        self.set_xy(8, 3)
        self.cell(0, 8, "VISE-D | Netzmodell-Szenario - Simulationsbericht", ln=False)
        self.set_xy(-60, 3)
        self.set_font("Helvetica", "", 8)
        self.cell(52, 8, _safe(f"Netz: {self.net_name}"), align="R", ln=False)
        self.set_text_color(*_DARK)
        self.ln(17)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 160)
        self.cell(
            0, 6,
            _safe(f"Seite {self.page_no()} | Erstellt {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')} | VISE-D"),
            align="C",
        )
        self.set_text_color(*_DARK)

    # ------------------------------------------------------------------ #
    # Layout helpers
    # ------------------------------------------------------------------ #

    def section_title(self, title: str) -> None:
        """Compact coloured section heading."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*_ACCENT)
        self.cell(0, 6, _safe(title), ln=True)
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.3)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.ln(2)
        self.set_text_color(*_DARK)
        self.set_font("Helvetica", size=8)

    def kv_row(
        self,
        label: str,
        value: str,
        highlight: bool = False,
        x: float | None = None,
        col_w: float = 190,
        label_w: float = 70,
        row_h: float = 5,
    ) -> None:
        """Single key-value row, optionally positioned at a specific x."""
        if x is not None:
            self.set_x(x)
        fill_color = _LIGHT_GRAY if highlight else _WHITE
        self.set_fill_color(*fill_color)
        self.set_font("Helvetica", "", 8)
        self.cell(label_w, row_h, _safe(label), border=0, fill=True)
        self.set_font("Helvetica", "B", 8)
        self.cell(col_w - label_w, row_h, _safe(value), border=0, fill=True, ln=True)

    def metric_box(
        self,
        label: str,
        value: str,
        good: bool | None = None,
        x: float | None = None,
        box_w: float = 30,
    ) -> None:
        """Compact coloured metric box — fits 6 across an A4 page."""
        if x is not None:
            self.set_x(x)
        h = 11
        if good is True:
            self.set_fill_color(*_GREEN_RGB)
        elif good is False:
            self.set_fill_color(*_RED_RGB)
        else:
            self.set_fill_color(*_ACCENT)
        self.set_text_color(*_WHITE)
        saved_x = self.get_x()
        # Value row
        self.set_font("Helvetica", "B", 10)
        self.cell(box_w, h * 0.55, _safe(value), align="C", ln=False, fill=True)
        # Label row
        self.set_xy(saved_x, self.get_y() + h * 0.55)
        self.set_font("Helvetica", "", 6)
        self.cell(box_w, h * 0.45, _safe(label), align="C", ln=False, fill=True)
        self.set_text_color(*_DARK)
        # Advance x for next box (2mm gap)
        self.set_xy(saved_x + box_w + 2, self.get_y() - h * 0.55)

    def embed_png(self, png_bytes: bytes, caption: str = "", img_h_mm: float = 76.0) -> None:
        """Embed a PNG (raw bytes) as a full-width chart image.

        Parameters
        ----------
        img_h_mm : float
            Rendered image height in mm. Default 76 mm (~A4-width 4:3 crop).
        """
        if not png_bytes:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(160, 160, 170)
            self.cell(0, 6, "[Diagramm konnte nicht gerendert werden]", ln=True)
            self.set_text_color(*_DARK)
            return
        buf = io.BytesIO(png_bytes)
        img_w = 185
        x = (210 - img_w) / 2
        self.image(buf, x=x, y=self.get_y(), w=img_w, h=img_h_mm)
        self.ln(img_h_mm + 1)
        if caption:
            self.set_font("Helvetica", "I", 6)
            self.set_text_color(110, 110, 120)
            self.cell(0, 4, _safe(caption), align="C", ln=True)
            self.set_text_color(*_DARK)
        self.ln(1)
    def check_for_chart(self, min_h: float = 70) -> None:
        """Break to new page only when fewer than *min_h* mm remain."""
        remaining = (self.h - self.b_margin) - self.get_y()
        if remaining < min_h:
            self.add_page()
        else:
            self.ln(4)

    def two_col_tables(
        self,
        left_title: str,
        left_rows: list[tuple[str, str]],
        right_title: str,
        right_rows: list[tuple[str, str]],
    ) -> None:
        """Render two labelled kv-tables side by side to save vertical space."""
        lx, rx = 10.0, 107.0          # left / right column x-positions
        col_w = 93.0                   # width of each column
        lbl_w = 42.0                   # width of label portion
        row_h = 5.0

        # Column headers
        y0 = self.get_y()
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_ACCENT)
        self.set_xy(lx, y0)
        self.cell(col_w, 5, _safe(left_title), ln=False)
        self.set_xy(rx, y0)
        self.cell(col_w, 5, _safe(right_title), ln=True)
        # Underlines
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.3)
        self.line(lx, self.get_y(), lx + col_w, self.get_y())
        self.line(rx, self.get_y(), rx + col_w, self.get_y())
        self.ln(2)
        self.set_text_color(*_DARK)

        n = max(len(left_rows), len(right_rows))
        for i in range(n):
            y = self.get_y()
            alt = i % 2 == 0
            fill = _LIGHT_GRAY if alt else _WHITE
            self.set_fill_color(*fill)

            if i < len(left_rows):
                lbl, val = left_rows[i]
                self.set_xy(lx, y)
                self.set_font("Helvetica", "", 8)
                self.cell(lbl_w, row_h, _safe(lbl), fill=True)
                self.set_font("Helvetica", "B", 8)
                self.cell(col_w - lbl_w, row_h, _safe(val), fill=True, ln=False)

            if i < len(right_rows):
                lbl, val = right_rows[i]
                self.set_xy(rx, y)
                self.set_font("Helvetica", "", 8)
                self.cell(lbl_w, row_h, _safe(lbl), fill=True)
                self.set_font("Helvetica", "B", 8)
                self.cell(col_w - lbl_w, row_h, _safe(val), fill=True, ln=True)
            else:
                self.set_xy(lx, y + row_h)
                self.ln(0)


# ---------------------------------------------------------------------------
# Figure builders — render report charts with matplotlib (Agg, in-process).
# No kaleido/Chromium: matplotlib rasterises directly to PNG, which is both
# much faster and far leaner for deployment.
# ---------------------------------------------------------------------------

def _time_xticks(ax, dt_index, n: int, max_ticks: int = 7) -> None:
    """Place a handful of readable time ticks on the x-axis of *ax*."""
    if n <= 0:
        return
    step = max(1, n // max_ticks)
    pos = list(range(0, n, step))
    idx = pd.Index(dt_index)
    if isinstance(idx, pd.DatetimeIndex):
        labels = [idx[i].strftime("%H:%M") for i in pos]
    else:
        labels = [str(idx[i]) for i in pos]
    ax.set_xticks(pos)
    ax.set_xticklabels(labels, fontsize=7)


def _build_voltage_figure(voltage_df: pd.DataFrame, dt_index) -> Figure:
    vm_min = voltage_df.min(axis=1).to_numpy()
    vm_max = voltage_df.max(axis=1).to_numpy()
    n = len(voltage_df)
    x = np.arange(n)

    fig = Figure(figsize=(11, 4.5), dpi=100)
    ax = fig.subplots()
    ax.plot(x, vm_max, color="#2563eb", linewidth=1.6, label="Max U (p.u.)")
    ax.plot(x, vm_min, color="#dc2626", linewidth=1.6, label="Min U (p.u.)")
    ax.fill_between(x, vm_min, vm_max, color="#dc2626", alpha=0.08)
    ax.axhline(1.05, ls=":", color="gray", linewidth=1)
    ax.axhline(0.95, ls=":", color="gray", linewidth=1)
    ax.set_title("Spannungsband (p.u.)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Zeit", fontsize=9)
    ax.set_ylabel("Spannung (p.u.)", fontsize=9)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    _time_xticks(ax, dt_index, n)
    fig.tight_layout()
    return fig


def _build_loading_figure(loading_df: pd.DataFrame, dt_index) -> Figure | None:
    if loading_df.empty:
        return None
    data = loading_df.to_numpy().T            # rows = lines, cols = time steps
    n_lines, n = data.shape

    cmap = LinearSegmentedColormap.from_list(
        "load", [(0.0, "#22c55e"), (0.667, "#facc15"), (1.0, "#ef4444")]
    )
    fig = Figure(figsize=(11, max(2.2, min(8.0, n_lines * 0.45 + 1.6))), dpi=100)
    ax = fig.subplots()
    im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=0, vmax=120)
    # Discrete line-number ticks — avoids the continuous -0.5..n-0.5 axis that
    # Plotly/kaleido produced from numeric-looking string labels.
    ax.set_yticks(np.arange(n_lines))
    ax.set_yticklabels([str(c) for c in loading_df.columns], fontsize=7)
    ax.set_ylabel("Leitung", fontsize=9)
    ax.set_xlabel("Zeit", fontsize=9)
    ax.set_title("Leitungsauslastung (%)", fontsize=12, fontweight="bold")
    _time_xticks(ax, dt_index, n)
    fig.colorbar(im, ax=ax, label="Auslastung (%)", fraction=0.025, pad=0.01)
    fig.tight_layout()
    return fig


def _build_trafo_figure(
    trafo_loading_df: pd.DataFrame, dt_index, net: Any = None
) -> Figure | None:
    """Transformer loading over time: one line per transformer.

    Returns ``None`` when there is no transformer data. Lines are labelled with
    the transformer name from *net* when available.
    """
    if trafo_loading_df is None or trafo_loading_df.empty:
        return None
    n = len(trafo_loading_df)
    x = np.arange(n)

    fig = Figure(figsize=(11, 3.6), dpi=100)
    ax = fig.subplots()
    for col in trafo_loading_df.columns:
        label = f"Trafo {col}"
        if net is not None and hasattr(net, "trafo") and col in net.trafo.index:
            name = net.trafo.at[col, "name"]
            if isinstance(name, str) and name:
                label = name
        ax.plot(x, trafo_loading_df[col].to_numpy(), linewidth=1.6, label=label)
    ax.axhline(100, ls=":", color="#ef4444", linewidth=1)
    ax.axhline(80, ls=":", color="#facc15", linewidth=1)
    ax.set_title("Transformatorauslastung (%)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Zeit", fontsize=9)
    ax.set_ylabel("Auslastung (%)", fontsize=9)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    _time_xticks(ax, dt_index, n)
    fig.tight_layout()
    return fig


def _build_profile_figure(series: pd.Series, ylabel: str, title: str) -> Figure:
    fig = Figure(figsize=(11, 3.3), dpi=100)
    ax = fig.subplots()
    ax.plot(np.arange(len(series)), np.asarray(series.values),
            color="#2563eb", linewidth=1.8)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Zeitschritt (15 min)", fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def _fig_to_png(fig: Figure | None) -> bytes:
    """Rasterise a matplotlib figure to PNG bytes (Agg renderer, in-process).

    Returns ``b""`` when *fig* is None so optional charts can be skipped.
    """
    if fig is None:
        return b""
    buf = io.BytesIO()
    # The builders already call tight_layout(); skip bbox_inches="tight" so
    # savefig does not trigger a second full render pass per figure.
    fig.savefig(buf, format="png")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Per-scenario result block (voltage / line loading / transformer loading)
# ---------------------------------------------------------------------------

def _add_result_block(
    pdf: "_NetzPDF",
    net: Any,
    voltage_df: pd.DataFrame,
    loading_df: pd.DataFrame | None,
    trafo_loading_df: pd.DataFrame | None,
    dt_index: Any,
    suffix: str = "",
) -> None:
    """Render one scenario's result charts (voltage band, line-loading heatmap,
    transformer loading) each followed by a stats table.

    ``suffix`` (e.g. ``" (ohne Verschiebung)"``) is appended to the section
    titles so the comparison report distinguishes the two scenarios.
    """
    if voltage_df is None or voltage_df.empty:
        return
    if loading_df is None:
        loading_df = pd.DataFrame()
    n_steps = max(1, len(voltage_df))
    vm_min = voltage_df.min(axis=1)
    vm_max = voltage_df.max(axis=1)
    violations = int(((vm_min < 0.95) | (vm_max > 1.05)).sum())

    # ── Voltage band ── #
    fig_v = _build_voltage_figure(voltage_df, dt_index)
    png_v = _fig_to_png(fig_v)
    pdf.section_title(f"Spannungsband - Zeitreihenergebnisse{suffix}")
    pdf.embed_png(
        png_v, caption="Spannungsband (Min./Max.) uber den Simulationszeitraum"
    )
    pdf.two_col_tables(
        left_title="Spannungsstatistik",
        left_rows=[
            ("Min. Spannung", f"{vm_min.min():.4f} p.u."),
            ("Max. Spannung", f"{vm_max.max():.4f} p.u."),
            ("Mittl. Min.",   f"{vm_min.mean():.4f} p.u."),
            ("Mittl. Max.",   f"{vm_max.mean():.4f} p.u."),
        ],
        right_title="Grenzwertanalyse",
        right_rows=[
            ("Band 0.95-1.05 p.u.", "EN 50160"),
            ("Verletzungen",        str(violations)),
            ("Verletzungsquote",    f"{violations / n_steps * 100:.1f} %"),
        ],
    )

    # ── Line loading ── #
    if not loading_df.empty:
        n_lines = len(loading_df.columns)
        fig_l = _build_loading_figure(loading_df, dt_index)
        png_l = _fig_to_png(fig_l)
        if png_l:
            max_load = float(loading_df.max().max())
            warn_steps = int((loading_df > 80).any(axis=1).sum())
            over_steps = int((loading_df > 100).any(axis=1).sum())
            pdf.check_for_chart(min_h=70)
            pdf.section_title(f"Leitungsauslastung - Zeitreihenergebnisse{suffix}")
            load_h = min(76.0, max(40.0, n_lines * 8.0))  # scale with line count
            pdf.embed_png(
                png_l,
                caption="Leitungsauslastung (%) als Heatmap - Zeitachse x Leitung",
                img_h_mm=load_h,
            )
            pdf.two_col_tables(
                left_title="Auslastungsstatistik",
                left_rows=[
                    ("Max. Auslastung",  f"{max_load:.1f} %"),
                    ("Anzahl Leitungen", str(n_lines)),
                ],
                right_title="Engpassanalyse",
                right_rows=[
                    ("> 80 % Schritte",  str(warn_steps)),
                    ("> 100 % Schritte", str(over_steps)),
                    ("Uberlastquote",    f"{over_steps / n_steps * 100:.1f} %"),
                ],
            )

    # ── Transformer loading ── #
    if trafo_loading_df is not None and not trafo_loading_df.empty:
        n_trafo = len(trafo_loading_df.columns)
        fig_t = _build_trafo_figure(trafo_loading_df, dt_index, net)
        png_t = _fig_to_png(fig_t)
        if png_t:
            t_max = float(trafo_loading_df.max().max())
            t_warn = int((trafo_loading_df > 80).any(axis=1).sum())
            t_over = int((trafo_loading_df > 100).any(axis=1).sum())
            pdf.check_for_chart(min_h=70)
            pdf.section_title(f"Transformatorauslastung - Zeitreihenergebnisse{suffix}")
            pdf.embed_png(
                png_t,
                caption="Transformatorauslastung (%) uber den Simulationszeitraum",
                img_h_mm=60.0,
            )
            pdf.two_col_tables(
                left_title="Trafo-Auslastungsstatistik",
                left_rows=[
                    ("Max. Auslastung",        f"{t_max:.1f} %"),
                    ("Anzahl Transformatoren", str(n_trafo)),
                ],
                right_title="Engpassanalyse",
                right_rows=[
                    ("> 80 % Schritte",  str(t_warn)),
                    ("> 100 % Schritte", str(t_over)),
                    ("Uberlastquote",    f"{t_over / n_steps * 100:.1f} %"),
                ],
            )


# ---------------------------------------------------------------------------
# Public — Netzmodell-specific report
# ---------------------------------------------------------------------------

def build_netzmodell_pdf(
    net: Any,
    voltage_df: pd.DataFrame,
    loading_df: pd.DataFrame,
    dt_index: Any,
    session_state: dict,
    trafo_loading_df: pd.DataFrame | None = None,
    flex_results: dict | None = None,
) -> bytes:
    """Build and return a branded A4 PDF report for the Netzmodell simulation.

    Parameters
    ----------
    net           : pandapowerNet used for the simulation.
    voltage_df    : shape (n_steps, n_buses) — vm_pu results.
    loading_df    : shape (n_steps, n_lines) — loading_percent results.
    dt_index      : DatetimeIndex or RangeIndex aligned with the DataFrames.
    session_state : Streamlit session_state dict (or equivalent plain dict)
                    containing optional profile keys (nsv2_profile_pv, _ev …).
    trafo_loading_df : shape (n_steps, n_trafos) — transformer loading_percent;
                    omitted (or empty) when the net has no transformers.
    flex_results  : optional dict for the flexibility comparison run with keys
                    ``voltage_df`` / ``loading_df`` / ``trafo_loading_df``. When
                    given, the baseline sections are labelled "(ohne Verschiebung)"
                    and a second block "(mit Verschiebung)" is appended.

    Returns
    -------
    bytes  – raw PDF bytes ready for ``st.download_button``.
    """
    if not _HAS_FPDF:
        raise ImportError(
            "fpdf2 ist nicht installiert. Bitte 'pip install fpdf2' ausführen."
        )

    # ── Metadata ── #
    net_name: str = (
        getattr(net, "name", None)
        or session_state.get("nsv2_net_name", "Unbekannt")
    )
    time_start = session_state.get("nsv2_time_start")
    time_end   = session_state.get("nsv2_time_end")
    date_range = f"{time_start} - {time_end}" if time_start and time_end else "-"

    # ── Pre-compute stats ── #
    vm_min   = voltage_df.min(axis=1)
    vm_max   = voltage_df.max(axis=1)
    n_steps  = len(voltage_df)
    violations = int(((vm_min < 0.95) | (vm_max > 1.05)).sum())

    max_load   = float(loading_df.max().max()) if not loading_df.empty else float("nan")
    warn_steps = int((loading_df > 80).any(axis=1).sum()) if not loading_df.empty else 0
    over_steps = int((loading_df > 100).any(axis=1).sum()) if not loading_df.empty else 0

    n_sgen    = len(net.sgen)    if hasattr(net, "sgen")    else 0
    n_storage = len(net.storage) if (hasattr(net, "storage") and net.storage is not None) else 0

    # ── Optional profile PNGs ── #
    profile_charts: list[tuple[str, bytes]] = []
    _profile_defs = [
        ("nsv2_profile_pv",      "PV-Einspeiseprofil",      "kW / kWp"),
        ("nsv2_profile_ev",      "EV-Lastprofil",            "kW"),
        ("nsv2_profile_hp",      "Waermepumpen-Lastprofil",  "kW (el.)"),
        ("nsv2_profile_storage", "Speicherprofil",           "kW (-Laden / +Entladen)"),
    ]
    for key, title, ylabel in _profile_defs:
        prof = session_state.get(key)
        if prof is None:
            continue
        try:
            series = prof.mean(axis=1) if isinstance(prof, pd.DataFrame) else pd.Series(prof)
            fig_p  = _build_profile_figure(series, ylabel, title)
            png_p  = _fig_to_png(fig_p)
            if png_p:
                profile_charts.append((title, png_p))
        except Exception:
            pass  # skip silently — never crash the export

    # ================================================================== #
    # Assemble PDF  — target: 2 pages for core results + extra for profiles
    # ================================================================== #
    pdf = _NetzPDF(net_name=net_name, date_range=date_range)
    pdf.set_margins(left=10, top=18, right=10)

    # ──────────────────────────────────────────────────────────────────
    # Page 1 — compact header + two-column info + KPI row + voltage chart
    # ──────────────────────────────────────────────────────────────────
    pdf.add_page()

    # Slim title bar (10 mm, single line)
    pdf.set_fill_color(*_PRIMARY)
    pdf.set_text_color(*_WHITE)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Netzmodell-Szenario  |  Simulationsbericht", ln=True, fill=True, align="C")
    pdf.set_text_color(*_DARK)
    pdf.ln(3)

    # Two-column table: Berichtsinformationen (left) | Netztopologie (right)
    pdf.two_col_tables(
        left_title="Berichtsinformationen",
        left_rows=[
            ("Netz",                _safe(net_name)),
            ("Zeitraum",            date_range),
            ("Erstellt am",         datetime.datetime.now().strftime("%d.%m.%Y %H:%M")),
            ("Schritte",           f"{n_steps} x 15 min = {n_steps * 0.25:.0f} h"),
        ],
        right_title="Netztopologie",
        right_rows=[
            ("Busse",              str(len(net.bus))),
            ("Leitungen",          str(len(net.line))),
            ("Lasten",             str(len(net.load)) if hasattr(net, "load") else "-"),
            ("Transformatoren",    str(len(net.trafo)) if hasattr(net, "trafo") else "-"),
            ("Einspeiser (sgen)",  str(n_sgen)),
            ("Speicher",           str(n_storage)),
        ],
    )
    pdf.ln(3)

    # ── KPI strip: all 6 metric boxes in one horizontal row ── #
    # 6 boxes × 30 mm + 5 gaps × 2 mm = 190 mm → fills the full text width
    pdf.section_title("Ergebnisübersicht")
    start_x = pdf.get_x()
    pdf.metric_box("Min. Spannung",      f"{vm_min.min():.4f} p.u.",
                   good=(vm_min.min() >= 0.95), x=start_x)
    pdf.metric_box("Max. Spannung",      f"{vm_max.max():.4f} p.u.",
                   good=(vm_max.max() <= 1.05))
    pdf.metric_box("Spg.-Verletzungen",  str(violations),
                   good=(violations == 0))
    if not loading_df.empty:
        pdf.metric_box("Max. Auslastung", f"{max_load:.1f} %",
                       good=(max_load <= 80))
        pdf.metric_box("> 80 % Schritte", str(warn_steps),
                       good=(warn_steps == 0))
        pdf.metric_box("> 100 % Schritte", str(over_steps),
                       good=(over_steps == 0))
    pdf.ln(15)   # advance past the 11 mm boxes
    pdf.ln(2)

    # ── Result charts (voltage / line loading / transformer loading) ── #
    base_suffix = " (ohne Verschiebung)" if flex_results else ""
    _add_result_block(
        pdf, net, voltage_df, loading_df, trafo_loading_df, dt_index,
        suffix=base_suffix,
    )

    # ── Comparison: append the flexibility ("mit Verschiebung") scenario ── #
    if flex_results:
        pdf.add_page()
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 9, _safe("Ergebnisse mit Verschiebung (Flexibilitaet)"),
                 ln=True, fill=True, align="C")
        pdf.set_text_color(*_DARK)
        pdf.ln(3)
        _add_result_block(
            pdf, net,
            flex_results.get("voltage_df"),
            flex_results.get("loading_df"),
            flex_results.get("trafo_loading_df"),
            dt_index,
            suffix=" (mit Verschiebung)",
        )

    # ──────────────────────────────────────────────────────────────────
    # Profile charts — flow on same page when room exists
    # ──────────────────────────────────────────────────────────────────
    for idx, (title, png_p) in enumerate(profile_charts, start=1):
        pdf.check_for_chart(min_h=65)
        pdf.section_title(f"Profil {idx}: {title}")
        pdf.embed_png(
            png_p,
            caption=_safe(f"{title} - 15-min-Schritte"),
            img_h_mm=55.0,
        )

    return bytes(pdf.output())


# ===========================================================================
# ── GENERIC PDF HELPERS (used by other pages) ───────────────────────────────
# ===========================================================================

def _make_pdf(
    title: str,
    chart_titles: list[str],
    metadata: dict[str, Any] | None,
    summary_stats: dict[str, Any] | None,
    png_buffers: list[bytes],
) -> bytes:
    """Internal: assemble a generic landscape PDF from PNG byte buffers."""
    if not _HAS_FPDF:
        raise ImportError(
            "fpdf2 is required for PDF export. Install it with: pip install fpdf2"
        )

    class _SimPDF(FPDF):
        def header(self):
            if self.page_no() > 1:
                self.set_fill_color(*_PRIMARY)
                self.rect(0, 0, 297, 12, "F")
                self.set_text_color(*_WHITE)
                self.set_font("Helvetica", "B", 9)
                self.set_xy(8, 2)
                self.cell(0, 8, _safe(title), ln=False)
                self.set_xy(-70, 2)
                self.cell(
                    62, 8,
                    _safe(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"),
                    align="R",
                )
                self.set_text_color(*_DARK)
                self.ln(14)

        def footer(self):
            self.set_y(-13)
            self.set_draw_color(*_PRIMARY)
            self.set_line_width(0.4)
            self.line(10, self.get_y(), 200, self.get_y())
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(120, 120, 140)
            self.cell(
                0, 6,
                f"Page {self.page_no()} | VISE-D Power System Simulation Report",
                align="C",
            )

    pdf = _SimPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=12, top=14, right=12)

    # Cover page
    pdf.add_page()
    pdf.set_fill_color(*_PRIMARY)
    pdf.rect(0, 0, 297, 50, "F")
    pdf.set_fill_color(*_GREEN_RGB)
    pdf.rect(0, 50, 297, 4, "F")
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*_WHITE)
    pdf.set_xy(15, 10)
    pdf.cell(0, 16, _safe(title), ln=True)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(180, 210, 255)
    pdf.set_x(15)
    pdf.cell(0, 8, "Power System Simulation Report", ln=True)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 190, 255)
    pdf.set_x(15)
    pdf.cell(
        0, 8,
        _safe(f"Generated on: {datetime.datetime.now().strftime('%A, %B %d %Y  -  %H:%M:%S')}"),
        ln=True,
    )

    pdf.set_xy(15, 62)
    pdf.set_text_color(*_DARK)

    if metadata:
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(265, 7, "  Simulation Parameters", ln=True, fill=True)
        pdf.set_text_color(*_DARK)
        col_w = min(90, 265 // max(1, len(metadata)))
        for row_start in range(0, len(list(metadata.items())), 3):
            row = list(metadata.items())[row_start: row_start + 3]
            pdf.set_fill_color(*_SECONDARY)
            for k, v in row:
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(col_w // 2, 6, _safe(f"  {k}:"), fill=True)
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(col_w // 2, 6, _safe(str(v)), fill=True)
            pdf.ln(7)

    if summary_stats:
        pdf.ln(4)
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(265, 7, "  Key Performance Indicators", ln=True, fill=True)
        items = list(summary_stats.items())
        col_w = min(80, 265 // max(1, min(len(items), 4)))
        pdf.set_text_color(*_DARK)
        for i, (k, v) in enumerate(items):
            if i > 0 and i % 4 == 0:
                pdf.ln(12)
            x0 = 12 + (i % 4) * (col_w + 4)
            pdf.set_xy(x0, pdf.get_y())
            pdf.set_fill_color(*_PRIMARY)
            pdf.set_text_color(*_WHITE)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(col_w, 6, _safe(f"  {k}"), fill=True, ln=False)
            pdf.ln(6)
            pdf.set_xy(x0, pdf.get_y())
            pdf.set_fill_color(220, 235, 255)
            pdf.set_text_color(*_DARK)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(col_w, 10, _safe(f"  {v}"), fill=True, ln=False)
        pdf.ln(14)

    if png_buffers:
        pdf.ln(6)
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(265, 7, "  Contents", ln=True, fill=True)
        pdf.set_text_color(*_DARK)
        pdf.set_font("Helvetica", "", 9)
        for i, ct in enumerate(chart_titles[: len(png_buffers)], start=1):
            pdf.set_fill_color(*(_LIGHT_BG if i % 2 == 0 else _SECONDARY))
            pdf.cell(10, 6, f"  {i}.", fill=True)
            pdf.cell(255, 6, _safe(f"  {ct}"), fill=True, ln=True)

    for i, (png_bytes, chart_title) in enumerate(zip(png_buffers, chart_titles)):
        pdf.add_page()
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_y(14)
        pdf.cell(0, 8, _safe(f"  {i + 1}.  {chart_title}"), fill=True, ln=True)
        pdf.ln(2)
        try:
            img_buf = io.BytesIO(png_bytes)
            img_buf.seek(0)
            pdf.image(img_buf, x=pdf.get_x(), y=pdf.get_y(), w=272, h=0, type="PNG")
        except Exception as e:
            pdf.set_text_color(200, 0, 0)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 8, _safe(f"[Chart could not be rendered: {e}]"), ln=True)

    return bytes(pdf.output())


def generate_pdf_report_matplotlib(
    figures: list,
    chart_titles: list[str] | None = None,
    title: str = "Simulation Results",
    metadata: dict[str, Any] | None = None,
    summary_stats: dict[str, Any] | None = None,
    dpi: int = 150,
) -> bytes:
    """Generate a PDF report from a list of Matplotlib figures.

    Parameters
    ----------
    figures      : list of matplotlib.figure.Figure
    chart_titles : list of str, optional
    title        : str
    metadata     : dict, optional
    summary_stats: dict, optional
    dpi          : int — rasterisation resolution (default 150).

    Returns
    -------
    bytes — raw PDF bytes for ``st.download_button``.
    """
    if chart_titles is None:
        chart_titles = [f"Chart {i + 1}" for i in range(len(figures))]
    png_buffers: list[bytes] = []
    for fig in figures:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        png_buffers.append(buf.read())
    return _make_pdf(title, chart_titles, metadata, summary_stats, png_buffers)
