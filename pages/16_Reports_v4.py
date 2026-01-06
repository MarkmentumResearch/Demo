import io
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Reports", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGO_PATH = os.path.join(PROJECT_ROOT, "assets", "logo.png")

DISCLAIMER_TEXT = (
    "© 2025 Markmentum Research LLC. Disclaimer: This content is for informational purposes only. "
    "Nothing herein constitutes an offer to sell, a solicitation of an offer to buy, or a recommendation "
    "regarding any security, investment vehicle, or strategy. It does not represent legal, tax, accounting, "
    "or investment advice by Markmentum Research LLC or its employees. The information is provided without "
    "regard to individual objectives or risk parameters and is general, non-tailored, and non-specific. "
    "Sources are believed to be reliable, but accuracy and completeness are not guaranteed. Markmentum Research LLC "
    "is not responsible for errors, omissions, or losses arising from use of this material. Investments involve risk, "
    "and financial markets are subject to fluctuation. Consult your financial professional before making investment decisions."
)

# -------------------------
# CSV HELPERS (Morning Compass uses qry ids)
# -------------------------
def _safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        try:
            return pd.read_csv(path, encoding="latin1")
        except Exception:
            return pd.DataFrame()


def _load_qry_csv(qry_id: int) -> pd.DataFrame:
    # expects files named like: qry_graph_data_92.csv, etc
    path = os.path.join(DATA_DIR, f"qry_graph_data_{qry_id}.csv")
    return _safe_read_csv(path)


def _infer_asof_date_from_df(df: pd.DataFrame) -> str | None:
    # Tries to find a date in the DF (common columns: 'date', 'Date', 'asof', etc)
    if df is None or df.empty:
        return None
    date_cols = [c for c in df.columns if c.lower() in ("date", "asof", "as_of", "dt")]
    if not date_cols:
        return None

    col = date_cols[0]
    s = df[col].dropna().astype(str)
    if s.empty:
        return None

    # Take the last value; normalize to M/D/YYYY if possible
    val = s.iloc[-1]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
        try:
            d = datetime.strptime(val.split(" ")[0], fmt)
            return f"{d.month}/{d.day}/{d.year}"
        except Exception:
            continue
    return val


def _asof_date_from_main(tf_key: str) -> str | None:
    # Morning Compass “main” df differs by timeframe
    # Daily uses 32 in our prior flow (from Morning Compass page)
    # Weekly uses 33, Monthly uses 34, etc (adjust if your IDs differ).
    tf_to_qry = {
        "Daily": 32,
        "Weekly": 33,
        "Monthly": 34,
        "Quarterly": 35,
    }
    qry_id = tf_to_qry.get(tf_key)
    if not qry_id:
        return None
    df = _load_qry_csv(qry_id)
    return _infer_asof_date_from_df(df)


# -------------------------
# PDF UTILITIES (Morning Compass)
# -------------------------
def _register_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="MR_Title",
            fontSize=16,
            leading=18,
            spaceAfter=8,
            alignment=1,  # center
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="MR_Subtitle",
            fontSize=11,
            leading=13,
            spaceAfter=12,
            alignment=1,
            textColor=colors.HexColor("#6c757d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="MR_H2",
            fontSize=12,
            leading=14,
            spaceBefore=10,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="MR_Body",
            fontSize=9,
            leading=11,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MR_Note",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#6c757d"),
            spaceBefore=6,
            spaceAfter=6,
        )
    )
    return styles


STYLES = _register_styles()


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#808080"))
    w, h = letter
    canvas.drawString(0.6 * inch, 0.45 * inch, DISCLAIMER_TEXT[:240])
    canvas.drawString(0.6 * inch, 0.33 * inch, DISCLAIMER_TEXT[240:480])
    canvas.drawString(0.6 * inch, 0.21 * inch, DISCLAIMER_TEXT[480:720])
    canvas.restoreState()


def _header_logo(story):
    if os.path.exists(LOGO_PATH):
        try:
            story.append(Image(LOGO_PATH, width=4.6 * inch, height=0.7 * inch))
            story.append(Spacer(1, 10))
        except Exception:
            pass


def _table_from_df(
    df: pd.DataFrame,
    col_widths=None,
    header_bg=colors.HexColor("#f2f2f2"),
    font_size=8,
    header_font_size=8,
    repeat_header=True,
):
    if df is None or df.empty:
        return Paragraph("No data available.", STYLES["MR_Note"])

    # Make sure column names are clean strings
    df = df.copy()
    df.columns = [str(c) for c in df.columns]

    data = [list(df.columns)] + df.values.tolist()

    # Basic cleanup to avoid ■■ for weird characters
    cleaned = []
    for row in data:
        cleaned_row = []
        for cell in row:
            if pd.isna(cell):
                cleaned_row.append("")
            else:
                s = str(cell)
                s = s.replace("\u25a0", "").replace("■", "")  # kill black squares
                cleaned_row.append(s)
        cleaned.append(cleaned_row)

    tbl = Table(cleaned, colWidths=col_widths, repeatRows=1 if repeat_header else 0)

    ts = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), header_font_size),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9d9d9")),
            ("FONTSIZE", (0, 1), (-1, -1), font_size),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ]
    )
    tbl.setStyle(ts)
    return tbl


def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    # Safe merge without adding dependencies (PyPDF2 not assumed).
    # ReportLab can’t merge, so we keep this minimal:
    # If you already added a merge function in your working version, keep using it.
    # Here we use PyPDF2 if installed; otherwise fall back to returning the first doc.
    try:
        from PyPDF2 import PdfMerger

        merger = PdfMerger()
        for b in pdf_bytes_list:
            merger.append(io.BytesIO(b))
        out = io.BytesIO()
        merger.write(out)
        merger.close()
        return out.getvalue()
    except Exception:
        # fallback: return first
        return pdf_bytes_list[0] if pdf_bytes_list else b""


# -------------------------
# Morning Compass PDF BUILDER (EXISTING)
# -------------------------
def build_morning_compass_pdf(
    include_correlations: bool,
    include_macro: bool,
    include_pct: bool,
    include_mm: bool,
    include_delta: bool,
    tf_key: str,
    asof: str | None,
) -> bytes:
    buffer = io.BytesIO()

    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.75 * inch,
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
        showBoundary=0,
    )

    template = PageTemplate(id="Main", frames=[frame], onPage=_footer)
    doc.addPageTemplates([template])

    story = []

    # Header (keep as you already had)
    _header_logo(story)

    title_asof = asof if asof else "(date not found)"
    story.append(Paragraph(f"Morning Compass – {title_asof}", STYLES["MR_Title"]))
    story.append(Spacer(1, 8))

    # NOTE: correlations daily-only
    if include_correlations and tf_key == "Daily":
        # USD correlations
        story.append(Paragraph("USD Correlations", STYLES["MR_H2"]))
        df_usd = _load_qry_csv(36)  # adjust if your ids differ
        story.append(_table_from_df(df_usd, col_widths=[3.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch]))
        story.append(PageBreak())

        # Rates correlations
        story.append(Paragraph("Rates Correlations", STYLES["MR_H2"]))
        df_rates = _load_qry_csv(37)  # adjust if your ids differ
        story.append(_table_from_df(df_rates, col_widths=[3.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch]))
        story.append(Spacer(1, 10))
    elif include_correlations and tf_key != "Daily":
        story.append(Paragraph("Correlations are available for Daily only.", STYLES["MR_Note"]))
        story.append(Spacer(1, 10))

    # Macro Orientation (by timeframe)
    if include_macro:
        story.append(Paragraph(f"{tf_key} Macro Orientation", STYLES["MR_H2"]))
        tf_to_macro_qry = {"Daily": 32, "Weekly": 33, "Monthly": 34, "Quarterly": 35}
        df_macro = _load_qry_csv(tf_to_macro_qry.get(tf_key, 32))
        story.append(_table_from_df(df_macro))
        story.append(Spacer(1, 10))

        # Bottom line text (if your daily/weekly/mth have it in another qry id, add it here)
        # Keeping minimal and consistent with your working version:
        story.append(Paragraph("Bottom line:", STYLES["MR_Body"]))
        story.append(Paragraph(" ", STYLES["MR_Body"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Note: MM Score → Rules-based contrarian score designed to avoid chasing stretch, identify crowding, and size conviction sensibly.", STYLES["MR_Note"]))
        story.append(Spacer(1, 8))

    # Top Five sections (by timeframe)
    if include_pct:
        story.append(Paragraph(f"{tf_key} Top Five Leaders/Laggards by % Change", STYLES["MR_H2"]))
        df_pct = _load_qry_csv(38)  # adjust
        story.append(_table_from_df(df_pct))
        story.append(Spacer(1, 10))

    if include_mm:
        story.append(Paragraph(f"{tf_key} Top Five Leaders/Laggards by MM Score", STYLES["MR_H2"]))
        df_mm = _load_qry_csv(39)  # adjust
        story.append(_table_from_df(df_mm))
        story.append(Spacer(1, 10))

    if include_delta:
        story.append(Paragraph(f"{tf_key} Top Five Leaders/Laggards by MM Score Change", STYLES["MR_H2"]))
        df_delta = _load_qry_csv(40)  # adjust
        story.append(_table_from_df(df_delta))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()


# -------------------------
# UI (v4 layout)
# -------------------------
st.markdown(
    "<div style='text-align:center; font-size:22px; font-weight:700; margin-top:8px;'>Reports</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center; color:#6c757d; margin-bottom:16px;'>Build a PDF from portal sections</div>",
    unsafe_allow_html=True
)

c1, c2, c3 = st.columns([1, 1.2, 1])
with c2:
    st.subheader("Report Builder")

st.divider()

# ---- Module checkboxes (future-ready) ----
include_morning_compass = st.checkbox("Morning Compass", value=True)
include_market_overview = st.checkbox("Market Overview", value=False)

st.markdown("---")

# NOTE: other pages will become checkboxes too (later)
# st.checkbox("Performance Heatmap", value=False)
# st.checkbox("Sharpe Rank Heatmap", value=False)
# st.checkbox("Markmentum Heatmap", value=False)
# st.checkbox("Directional Trends", value=False)
# st.checkbox("Vantage Point", value=False)

# -------------------------
# Morning Compass options
# -------------------------
mc_tf_keys = []
include_correlations = False
include_macro = False
include_pct = False
include_mm = False
include_delta = False

if include_morning_compass:
    st.markdown("**Morning Compass**")

    left, mid, right = st.columns([1, 1, 1])

    with left:
        mc_tf_keys = st.multiselect(
            "Add Timeframes (Optional)",
            ["Weekly", "Monthly"],
            default=[]
        )

        # Always include Daily first
        mc_tf_keys = ["Daily"] + mc_tf_keys

        st.caption(
            "Daily Morning Compass is always included by default. "
            "Select Weekly and/or Monthly to add them to the report."
        )

    with mid:
        st.markdown("**Include Sections**")
        include_correlations = st.checkbox("Correlations (USD + Rates) (Daily only)", value=True)
        include_macro        = st.checkbox("Macro Orientation (by timeframe)", value=True)

    with right:
        st.markdown("**Top Five Cards (by timeframe)**")
        include_pct   = st.checkbox("Top Five Leaders/Laggards by % Change", value=True)
        include_mm    = st.checkbox("Top Five Leaders/Laggards by MM Score", value=True)
        include_delta = st.checkbox("Top Five Leaders/Laggards by MM Score Change", value=True)

# Separator between module blocks
if include_morning_compass and include_market_overview:
    st.divider()

# -------------------------
# Market Overview options (UI only for now)
# -------------------------
mo_tf_keys = []

if include_market_overview:
    st.markdown("**Market Overview**")

    mo_tf_keys = st.multiselect(
        "Add Timeframes (Optional)",
        ["Weekly", "Monthly", "Quarterly"],
        default=[],
        key="mo_timeframes"
    )

    # Always include Daily first
    mo_tf_keys = ["Daily"] + mo_tf_keys

    st.caption(
        "Daily Market Overview includes Highest/Lowest MM Score, MM Score Histogram, and Opportunity Density. "
        "Other timeframes omit those daily-only sections."
    )

st.divider()

# -------------------------
# Preview + Generate (single output PDF)
# -------------------------
if not include_morning_compass and not include_market_overview:
    st.info("Select at least one report module to generate a PDF.")
    st.stop()

preview_parts = []

if include_morning_compass:
    for k in mc_tf_keys:
        asof_k = _asof_date_from_main(k)
        preview_parts.append(f"Morning Compass – {k}: {asof_k if asof_k else '(date not found)'}")

if include_market_overview:
    for k in mo_tf_keys:
        asof_k = _asof_date_from_main(k)
        preview_parts.append(f"Market Overview – {k}: {asof_k if asof_k else '(date not found)'}")

st.markdown("**Preview:** " + " | ".join(preview_parts))

gen = st.button("Generate PDF", type="primary")

if gen:
    pdf_blobs = []

    # ---- Morning Compass PDFs (existing builder, unchanged) ----
    if include_morning_compass:
        if not mc_tf_keys:
            st.warning("Morning Compass: select at least one timeframe.")
            st.stop()

        # If only one timeframe, keep exact behavior (single builder call)
        if len(mc_tf_keys) == 1:
            tf_key = mc_tf_keys[0]
            asof = _asof_date_from_main(tf_key)

            pdf_bytes = build_morning_compass_pdf(
                include_correlations=include_correlations,
                include_macro=include_macro,
                include_pct=include_pct,
                include_mm=include_mm,
                include_delta=include_delta,
                tf_key=tf_key,
                asof=asof,
            )
            pdf_blobs.append(pdf_bytes)
        else:
            # Multi-timeframe: build each, then merge (existing behavior)
            blobs = []
            for tf_key in mc_tf_keys:
                asof = _asof_date_from_main(tf_key)
                blobs.append(
                    build_morning_compass_pdf(
                        include_correlations=include_correlations,
                        include_macro=include_macro,
                        include_pct=include_pct,
                        include_mm=include_mm,
                        include_delta=include_delta,
                        tf_key=tf_key,
                        asof=asof,
                    )
                )
            pdf_blobs.append(merge_pdfs(blobs))

    # ---- Market Overview (UI is ready; PDF wiring comes next) ----
    if include_market_overview:
        st.warning("Market Overview PDF generation is not wired yet (UI only).")

    if not pdf_blobs:
        st.stop()

    # If multiple module PDFs exist, merge them into ONE output
    merged_pdf = merge_pdfs(pdf_blobs) if len(pdf_blobs) > 1 else pdf_blobs[0]

    # Build filename
    asof_for_name = _asof_date_from_main("Daily")
    file_date = asof_for_name.replace("/", "-") if asof_for_name else "report"
    filename = f"markmentum_report_{file_date}.pdf"

    st.success("PDF ready.")
    st.download_button(
        label="Download PDF",
        data=merged_pdf,
        file_name=filename,
        mime="application/pdf"
    )

st.markdown("---")
st.markdown(
    f"<div style='font-size: 12px; color: gray;'>{DISCLAIMER_TEXT}</div>",
    unsafe_allow_html=True
)