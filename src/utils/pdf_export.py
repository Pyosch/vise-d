"""pdf_export.py — Simulation report builder for the VISE-D Netzmodell page.

Provides two public functions:

    build_netzmodell_pdf(net, voltage_df, loading_df, dt_index, session_state)
        → bytes   (Netzmodell-specific, branded A4 portrait report)

    generate_pdf_report_plotly(figures, chart_titles, title, metadata, summary_stats)
        → bytes   (generic Plotly-figure PDF, kept for other pages)

    generate_pdf_report_matplotlib(figures, ...)
        → bytes   (generic Matplotlib-figure PDF, kept for other pages)

Both approaches use:
  • kaleido  — Plotly figure → PNG bytes
  • fpdf2    — PDF layout / assembly
"""

from __future__ import annotations

import io
import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


# ---------------------------------------------------------------------------
# Optional imports — fail gracefully so the rest of the app keeps working
# ---------------------------------------------------------------------------
try:
    from fpdf import FPDF
    _HAS_FPDF = True
except ImportError:
    _HAS_FPDF = False

try:
    import kaleido  # noqa: F401 — side-effect: activates kaleido back-end
    _HAS_KALEIDO = True
except ImportError:
    _HAS_KALEIDO = False


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
# Figure builders — re-create Plotly figures from raw DataFrames
# (so the export works even when Streamlit's widget state is unavailable)
# ---------------------------------------------------------------------------

def _build_voltage_figure(
    voltage_df: pd.DataFrame, dt_index
) -> go.Figure:
    x_labels = [str(t) for t in dt_index]
    vm_min = voltage_df.min(axis=1)
    vm_max = voltage_df.max(axis=1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_labels, y=vm_max.values, name="Max U (p.u.)",
        line=dict(color="#2563eb"), fill=None,
    ))
    fig.add_trace(go.Scatter(
        x=x_labels, y=vm_min.values, name="Min U (p.u.)",
        line=dict(color="#dc2626"), fill="tonexty",
        fillcolor="rgba(239,68,68,0.1)",
    ))
    fig.add_hline(y=1.05, line_dash="dot", line_color="gray",
                  annotation_text="1.05 p.u.")
    fig.add_hline(y=0.95, line_dash="dot", line_color="gray",
                  annotation_text="0.95 p.u.")
    fig.update_layout(
        title="Spannungsband (p.u.)",
        xaxis_title="Zeit", yaxis_title="Spannung (p.u.)",
        height=450, showlegend=True, hovermode="x unified",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Helvetica, Arial", size=11),
        margin=dict(l=65, r=20, t=55, b=60),
    )
    return fig


def _build_loading_figure(
    loading_df: pd.DataFrame, dt_index
) -> go.Figure | None:
    if loading_df.empty:
        return None
    x_labels = [str(t) for t in dt_index]
    heat_df = loading_df.copy()
    heat_df.columns = [str(c) for c in heat_df.columns]
    heat_df.index = x_labels[: len(heat_df)]

    fig = px.imshow(
        heat_df.T,
        color_continuous_scale=[[0, "#22c55e"], [0.667, "#facc15"], [1.0, "#ef4444"]],
        zmin=0, zmax=120,
        labels={"x": "Zeit", "y": "Leitung", "color": "Auslastung (%)"},
        title="Leitungsauslastung (%)",
    )
    n_lines = len(loading_df.columns)
    fig.update_layout(
        height=max(350, n_lines * 22 + 130),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Helvetica, Arial", size=10),
        margin=dict(l=65, r=20, t=55, b=60),
    )
    return fig


def _build_profile_figure(
    series: pd.Series, ylabel: str, title: str
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=series.values, mode="lines",
        line=dict(width=2, color="#2563eb"), showlegend=False,
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Zeitschritt (15 min)", yaxis_title=ylabel,
        height=320,
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Helvetica, Arial", size=10),
        margin=dict(l=65, r=20, t=55, b=55),
    )
    return fig


def _fig_to_png(
    fig: go.Figure, width: int = 1000, height: int = 500
) -> bytes:
    """Convert a Plotly figure to PNG bytes via kaleido."""
    if not _HAS_KALEIDO:
        return b""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return b""


# ---------------------------------------------------------------------------
# Public — Netzmodell-specific report
# ---------------------------------------------------------------------------

def build_netzmodell_pdf(
    net: Any,
    voltage_df: pd.DataFrame,
    loading_df: pd.DataFrame,
    dt_index: Any,
    session_state: dict,
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

    Returns
    -------
    bytes  – raw PDF bytes ready for ``st.download_button``.
    """
    if not _HAS_FPDF:
        raise ImportError(
            "fpdf2 ist nicht installiert. Bitte 'pip install fpdf2' ausführen."
        )
    if not _HAS_KALEIDO:
        raise ImportError(
            "kaleido ist nicht installiert. Bitte 'pip install kaleido' ausführen."
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

    # ── Render Plotly figures → PNG ── #
    fig_v   = _build_voltage_figure(voltage_df, dt_index)
    png_v   = _fig_to_png(fig_v, width=1100, height=520)

    fig_l   = _build_loading_figure(loading_df, dt_index)
    n_lines = len(loading_df.columns) if not loading_df.empty else 0
    png_l   = _fig_to_png(fig_l, width=1100, height=max(400, n_lines * 22 + 130)) \
              if fig_l is not None else b""

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
            png_p  = _fig_to_png(fig_p, width=1000, height=360)
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

    # ── Voltage chart ── #
    pdf.section_title("Spannungsband - Zeitreihenergebnisse")
    pdf.embed_png(png_v, caption="Spannungsband (Min./Max.) uber den Simulationszeitraum")

    # ── Voltage stats — two columns side by side ── #
    pdf.two_col_tables(
        left_title="Spannungsstatistik",
        left_rows=[
            ("Min. Spannung",     f"{vm_min.min():.4f} p.u."),
            ("Max. Spannung",     f"{vm_max.max():.4f} p.u."),
            ("Mittl. Min.",       f"{vm_min.mean():.4f} p.u."),
            ("Mittl. Max.",       f"{vm_max.mean():.4f} p.u."),
        ],
        right_title="Grenzwertanalyse",
        right_rows=[
            ("Band 0.95-1.05 p.u.", "EN 50160"),
            ("Verletzungen",        str(violations)),
            ("Verletzungsquote",    f"{violations / n_steps * 100:.1f} %"),
        ],
    )

    # ──────────────────────────────────────────────────────────────────
    # Page 2 (or continuation) — Line loading chart
    # ──────────────────────────────────────────────────────────────────
    if not loading_df.empty and png_l:
        pdf.check_for_chart(min_h=70)
        pdf.section_title("Leitungsauslastung - Zeitreihenergebnisse")
        load_h = min(76.0, max(40.0, n_lines * 8.0))  # scale with line count
        pdf.embed_png(png_l,
                      caption="Leitungsauslastung (%) als Heatmap - Zeitachse x Leitung",
                      img_h_mm=load_h)

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
                self.cell(0, 8, title, ln=False)
                self.set_xy(-70, 2)
                self.cell(
                    62, 8,
                    f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
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
    pdf.cell(0, 16, title, ln=True)
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(180, 210, 255)
    pdf.set_x(15)
    pdf.cell(0, 8, "Power System Simulation Report", ln=True)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 190, 255)
    pdf.set_x(15)
    pdf.cell(
        0, 8,
        f"Generated on: {datetime.datetime.now().strftime('%A, %B %d %Y  –  %H:%M:%S')}",
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
                pdf.cell(col_w // 2, 6, f"  {k}:", fill=True)
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(col_w // 2, 6, str(v), fill=True)
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
            pdf.cell(col_w, 6, f"  {k}", fill=True, ln=False)
            pdf.ln(6)
            pdf.set_xy(x0, pdf.get_y())
            pdf.set_fill_color(220, 235, 255)
            pdf.set_text_color(*_DARK)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(col_w, 10, f"  {v}", fill=True, ln=False)
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
            pdf.cell(255, 6, f"  {ct}", fill=True, ln=True)

    for i, (png_bytes, chart_title) in enumerate(zip(png_buffers, chart_titles)):
        pdf.add_page()
        pdf.set_fill_color(*_PRIMARY)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_y(14)
        pdf.cell(0, 8, f"  {i + 1}.  {chart_title}", fill=True, ln=True)
        pdf.ln(2)
        try:
            img_buf = io.BytesIO(png_bytes)
            img_buf.seek(0)
            pdf.image(img_buf, x=pdf.get_x(), y=pdf.get_y(), w=272, h=0, type="PNG")
        except Exception as e:
            pdf.set_text_color(200, 0, 0)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 8, f"[Chart could not be rendered: {e}]", ln=True)

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


def generate_pdf_report_plotly(
    figures: list,
    chart_titles: list[str] | None = None,
    title: str = "Simulation Results",
    metadata: dict[str, Any] | None = None,
    summary_stats: dict[str, Any] | None = None,
    width: int = 1400,
    height: int = 620,
) -> bytes:
    """Generate a PDF report from a list of Plotly figures.

    Requires ``kaleido`` (pip install kaleido).

    Parameters
    ----------
    figures      : list of plotly.graph_objects.Figure
    chart_titles : list of str, optional
    title        : str
    metadata     : dict, optional
    summary_stats: dict, optional
    width, height: int — pixel dimensions for PNG rendering.

    Returns
    -------
    bytes — raw PDF bytes for ``st.download_button``.
    """
    if chart_titles is None:
        chart_titles = [f"Chart {i + 1}" for i in range(len(figures))]
    png_buffers: list[bytes] = []
    for fig in figures:
        try:
            png_buffers.append(
                fig.to_image(format="png", width=width, height=height, scale=2)
            )
        except Exception as e:
            raise RuntimeError(
                "Could not render Plotly chart to PNG. "
                "Make sure 'kaleido' is installed (pip install kaleido). "
                f"Error: {e}"
            )
    return _make_pdf(title, chart_titles, metadata, summary_stats, png_buffers)
