from pathlib import Path
import io
import os
import pandas as pd
import numpy as np
import streamlit as st

# PDF (ReportLab)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import simpleSplit

# NEW (UI-only): merge multiple timeframe PDFs into ONE PDF
# requirements.txt needs: pypdf
from pypdf import PdfReader, PdfWriter

try:
    from docx import Document
except Exception:
    Document = None


# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="Markmentum – Reports", layout="wide")


# -------------------------
# Paths (match Morning Compass style)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"


# -------------------------
# Shared helpers (copied/consistent with Morning Compass)
# -------------------------
def fmt_num(x, nd=2):
    try:
        if pd.isna(x):
            return ""
        return f"{float(x):,.{nd}f}"
    except Exception:
        return ""

def fmt_pct(x, nd=2):
    try:
        if pd.isna(x):
            return ""
        return f"{float(x)*100:,.{nd}f}%"
    except Exception:
        return ""

def fmt_int(x):
    try:
        if pd.isna(x):
            return ""
        return f"{int(round(float(x))):,}"
    except Exception:
        return ""

@st.cache_data(show_spinner=False)
def load_csv_by_id(n: int, base_dir: Path) -> pd.DataFrame:
    p = base_dir / f"qry_graph_data_{n}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)

def _read_docx_plain_text(doc_path: Path) -> str:
    """Return docx text, or empty string if missing/unreadable (never print errors into PDF)."""
    if Document is None:
        return ""

    if not doc_path.exists():
        return ""

    try:
        doc = Document(str(doc_path))
        lines = []
        for p in doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                lines.append(t)
        return clean_text("\n".join(lines).strip())
    except Exception:
        # IMPORTANT: do not return the exception string, it ends up in the PDF
        return ""

def clean_text(s: str) -> str:
    """Normalize common unicode punctuation so Helvetica can render it (prevents ■■)."""
    if s is None:
        return ""
    s = str(s)

    # dashes/hyphens
    s = s.replace("\u2011", "-")  # non-breaking hyphen
    s = s.replace("\u2013", "-")  # en dash
    s = s.replace("\u2014", "-")  # em dash

    # quotes/apostrophes
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201C", '"').replace("\u201D", '"')

    # misc invisible/soft
    s = s.replace("\u00ad", "")   # soft hyphen
    s = s.replace("\u200b", "")   # zero-width space

    return s

DISCLAIMER_TEXT = (
    "© 2025 Markmentum Research LLC. Disclaimer: This content is for informational purposes only. "
    "Nothing herein constitutes an offer to sell, a solicitation of an offer to buy, or a recommendation "
    "regarding any security, investment vehicle, or strategy. It does not represent legal, tax, accounting, "
    "or investment advice by Markmentum Research LLC or its employees. The information is provided without "
    "regard to individual objectives or risk parameters and is general, non-tailored, and non-specific. "
    "Sources are believed to be reliable, but accuracy and completeness are not guaranteed. "
    "Markmentum Research LLC is not responsible for errors, omissions, or losses arising from use of this material. "
    "Investments involve risk, and financial markets are subject to fluctuation. Consult your financial professional "
    "before making investment decisions."
)

# Timeframe config (aligned with Morning Compass)
TIMEFRAMES = {
    "Daily": {
        "ids": {"main": 73, "leaders": 74, "mm": 75, "delta": 77},
        "cols": {"ret": "daily_Return", "pr_low": "day_pr_low", "pr_high": "day_pr_high", "rr": "day_rr_ratio"},
        "docx_macro": "bottom_line_daily.docx",
        "title_macro": "Daily Macro Orientation",
        "title_leaders": "Daily Top Five Leaders/Laggards by % Change",
        "title_mm": "Daily Top Five Leaders/Laggards by MM Score",
        "title_delta": "Daily Top Five Leaders/Laggards by MM Score Change",
    },
    "Weekly": {
        "ids": {"main": 78, "leaders": 79, "mm": 80, "delta": 82},
        "cols": {"ret": "weekly_Return", "pr_low": "week_pr_low", "pr_high": "week_pr_high", "rr": "week_rr_ratio"},
        "docx_macro": "bottom_line_weekly.docx",
        "title_macro": "Weekly Macro Orientation",
        "title_leaders": "Weekly Top Five Leaders/Laggards by % Change",
        "title_mm": "Weekly Top Five Leaders/Laggards by MM Score",
        "title_delta": "Weekly Top Five Leaders/Laggards by MM Score Change",
    },
    "Monthly": {
        "ids": {"main": 83, "leaders": 84, "mm": 85, "delta": 87},
        "cols": {"ret": "monthly_Return", "pr_low": "month_pr_low", "pr_high": "month_pr_high", "rr": "month_rr_ratio"},
        "docx_macro": "bottom_line_monthly.docx",
        "title_macro": "Monthly Macro Orientation",
        "title_leaders": "Monthly Top Five Leaders/Laggards by % Change",
        "title_mm": "Monthly Top Five Leaders/Laggards by MM Score",
        "title_delta": "Monthly Top Five Leaders/Laggards by MM Score Change",
    },
}


# -------------------------
# PDF styling + builders
# -------------------------
styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], alignment=TA_LEFT, fontSize=12, spaceBefore=10, spaceAfter=6)
P  = ParagraphStyle("P", parent=styles["BodyText"], fontSize=9, leading=12)
NOTE = ParagraphStyle("NOTE", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.grey)
TH = ParagraphStyle(
    "TH",
    parent=styles["BodyText"],
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=9,
    alignment=TA_CENTER,
)

def th(text: str) -> Paragraph:
    return Paragraph(clean_text(text), TH)

def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillGray(0.45)

    available_width = doc.width
    lines = simpleSplit(DISCLAIMER_TEXT.strip(), "Helvetica", 7, available_width)

    x = doc.leftMargin
    y = 0.25 * inch  # closer to bottom edge
    max_lines = 6    # show more (but still controlled)

    for i, line in enumerate(lines[:max_lines]):
        canvas.drawString(x, y + (max_lines - 1 - i) * 9, line)

    canvas.restoreState()

def _rr_bg_color(v: float, cap: float = 3.0):
    """Light green/red shading similar to portal RR tint."""
    try:
        v = float(v)
    except Exception:
        return colors.white
    s = min(abs(v) / cap, 1.0)
    # light pastel
    if v > 0:
        return colors.Color(0.90 - 0.10*s, 0.98, 0.94 - 0.10*s)  # greenish
    if v < 0:
        return colors.Color(0.98, 0.92 - 0.08*s, 0.92 - 0.08*s)  # reddish
    return colors.white

def _mm_bg_color(v: float):
    """MM pill-like shading bins similar to portal logic."""
    try:
        v = float(v)
    except Exception:
        return colors.white

    if v <= -100:
        return colors.Color(0.93, 0.75, 0.75)  # deeper red
    if v < -25:
        return colors.Color(0.97, 0.84, 0.84)  # red
    if v <= 25:
        return colors.Color(0.93, 0.93, 0.93)  # gray
    if v < 100:
        return colors.Color(0.84, 0.95, 0.90)  # green
    return colors.Color(0.75, 0.92, 0.85)      # darker green

def _build_table(data_rows, col_widths, shade_rr=False, shade_mm=False, rr_col=None, mm_col=None):
    """
    data_rows: list of lists (already strings for display)
    shade_rr/mm: apply background colors based on numeric values
    rr_col/mm_col: index of RR / MM Score columns in the table
    """
    tbl = Table(data_rows, colWidths=col_widths, repeatRows=1)

    base = TableStyle([
        ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#1a1a1a")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d9d9d9")),
        ("FONT", (0,1), (-1,-1), "Helvetica", 8),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        # center headers except first col
        ("ALIGN", (1,0), (-1,0), "CENTER"),
        # center ticker col (assumes col 1)
        ("ALIGN", (1,1), (1,-1), "CENTER"),
        # right-align numeric cols (from col 2 onward)
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,0), 6),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,1), (-1,-1), 4),
        ("BOTTOMPADDING", (0,1), (-1,-1), 4),
    ])
    tbl.setStyle(base)

    # shading
    if shade_rr and rr_col is not None:
        for r in range(1, len(data_rows)):
            raw = data_rows[r][rr_col]
            try:
                v = float(str(raw).replace(",", ""))
            except Exception:
                continue
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (rr_col, r), (rr_col, r), _rr_bg_color(v))
            ]))

    if shade_mm and mm_col is not None:
        for r in range(1, len(data_rows)):
            raw = data_rows[r][mm_col]
            try:
                v = float(str(raw).replace(",", ""))
            except Exception:
                continue
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (mm_col, r), (mm_col, r), _mm_bg_color(v))
            ]))

    return tbl


def _asof_date_from_main(tf_key: str) -> str:
    cfg = TIMEFRAMES[tf_key]
    df = load_csv_by_id(cfg["ids"]["main"], DATA_DIR)
    if df.empty or "Date" not in df.columns:
        return ""
    asof = pd.to_datetime(df["Date"], errors="coerce").max()
    if pd.isna(asof):
        return ""
    return f"{asof.month}/{asof.day}/{asof.year}"


def _section_correlations(flowables):
    """Daily-only correlations section (USD + Rates)."""
    # USD correlations = id 93
    df_usd = load_csv_by_id(93, DATA_DIR)
    df_tnx = load_csv_by_id(94, DATA_DIR)

    if df_usd.empty:
        flowables.append(Paragraph("USD Correlations (missing qry_graph_data_93.csv)", NOTE))
        return
    if df_tnx.empty:
        flowables.append(Paragraph("Rates Correlations (missing qry_graph_data_94.csv)", NOTE))
        return

    # format tables
    def corr_table(df, title, bottom_docx, note_text):
        flowables.append(Paragraph(title, H2))

        cols = [c for c in ["Metric", "15D", "30D", "90D"] if c in df.columns]
        d = df[cols].copy()
        for c in ["15D", "30D", "90D"]:
            if c in d.columns:
                d[c] = d[c].map(lambda v: fmt_num(v, 2))

        data_rows = [cols] + d.values.tolist()

        # widths: Metric wide, 3 equal
        w_metric = 3.6 * inch
        w_num = 1.1 * inch
        col_widths = [w_metric] + [w_num]*(len(cols)-1)

        t = _build_table(data_rows, col_widths)
        flowables.append(t)

        bl = _read_docx_plain_text(DATA_DIR / bottom_docx)
        if bl:
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(clean_text(bl).replace("\n", "<br/>"), P))

        flowables.append(Spacer(1, 4))
        flowables.append(Paragraph(note_text, NOTE))
        flowables.append(Spacer(1, 10))

    corr_table(
        df_usd,
        "USD Correlations",
        "usd_correlation_bottom_line.docx",
        "Note: USD correlations use UUP as the proxy for the U.S. Dollar Index. 15D/30D/90D are trading-day windows. "
        "Correlation ranges from -1 to +1. Negative = tends to move opposite. Positive = tends to move together."
    )

    flowables.append(PageBreak())

    corr_table(
        df_tnx,
        "Rates Correlations",
        "tnx_correlation_bottom_line.docx",
        "Note: Rate correlations use the 10-Year U.S. Treasury yield (TNX) as the rates proxy. 15D/30D/90D are trading-day windows. "
        "Correlation ranges from -1 to +1. Negative = tends to move opposite. Positive = tends to move together."
    )


def _section_macro_table(flowables, tf_key: str, title: str, csv_id: int, bottom_docx: str):
    cfg = TIMEFRAMES[tf_key]
    cols = cfg["cols"]

    df = load_csv_by_id(csv_id, DATA_DIR)
    req = ["Ticker_name", "Ticker", "Close", cols["ret"], cols["pr_low"], cols["pr_high"], cols["rr"], "model_score", "model_score_delta"]
    if df.empty or not all(c in df.columns for c in req):
        flowables.append(Paragraph(f"{title} (missing or incomplete qry_graph_data_{csv_id}.csv)", NOTE))
        flowables.append(Spacer(1, 8))
        return

    flowables.append(Paragraph(title, H2))

    # build display table
    d = df.copy()

    out = pd.DataFrame({
        "Name": d["Ticker_name"],
        "Ticker": d["Ticker"],
        "Close": d["Close"].map(lambda v: fmt_num(v, 2)),
        "% Change": d[cols["ret"]].map(lambda v: fmt_pct(v, 2)),
        "Probable Low": d[cols["pr_low"]].map(lambda v: fmt_num(v, 2)),
        "Probable High": d[cols["pr_high"]].map(lambda v: fmt_num(v, 2)),
        "Risk / Reward": d[cols["rr"]].map(lambda v: fmt_num(v, 1)),
        "MM Score": d["model_score"].map(lambda v: fmt_int(v)),
        "MM Score Change": d["model_score_delta"].map(lambda v: fmt_int(v)),
    })

    # Wrap headers to prevent collisions in PDF
    header = [
        th("Name"),
        th("Ticker"),
        th("Close"),
        th("% Change"),
        th("Probable<br/>Low"),
        th("Probable<br/>High"),
        th("Risk /<br/>Reward"),
        th("MM<br/>Score"),
        th("MM Score<br/>Change"),
    ]
    data_rows = [header] + out.values.tolist()

    # widths tuned for letter
    col_widths = [
        2.35*inch,  # Name
        0.70*inch,  # Ticker
        0.75*inch,  # Close
        0.80*inch,  # % Change
        0.85*inch,  # Prob Low
        0.85*inch,  # Prob High
        0.75*inch,  # RR
        0.70*inch,  # MM
        0.85*inch,  # MM Chg
    ]

    rr_col = 6  # Risk / Reward column index in our fixed header list
    mm_col = 7  # MM Score column index in our fixed header list

    t = _build_table(
        data_rows=data_rows,
        col_widths=col_widths,
        shade_rr=True, shade_mm=True,
        rr_col=rr_col, mm_col=mm_col
    )
    flowables.append(t)

    # bottom line (macro)
    bl = _read_docx_plain_text(DATA_DIR / bottom_docx)
    if bl:
        flowables.append(Spacer(1, 6))
        flowables.append(Paragraph(clean_text(bl).replace("\n", "<br/>"), P))

    flowables.append(Spacer(1, 4))
    flowables.append(Paragraph(
        "Note: MM Score → Rules-based contrarian score designed to avoid chasing stretch, identify crowding, and size conviction sensibly.",
        NOTE
    ))
    flowables.append(Spacer(1, 10))


# -------------------------
# !!! DO NOT CHANGE !!!
# PDF generation (working) stays as-is
# -------------------------
def build_morning_compass_pdf(
    include_correlations: bool,
    include_macro: bool,
    include_pct: bool,
    include_mm: bool,
    include_delta: bool,
    tf_key: str
) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.45*inch, rightMargin=0.45*inch,
        topMargin=0.50*inch, bottomMargin=0.95*inch
    )

    flow = []

    # Logo
    if tf_key == "Daily":
        if LOGO_PATH.exists():
            # scale to ~4.8 in wide
            img = RLImage(str(LOGO_PATH))
            img.drawHeight = 0.55 * inch
            img.drawWidth = 4.8 * inch
            img.hAlign = "CENTER"
            flow.append(img)
            flow.append(Spacer(1, 8))
        else:
            flow.append(Paragraph("Markmentum Research", H1))

        asof = _asof_date_from_main(tf_key)
        title = f"Morning Compass – {asof}" if asof else "Morning Compass"
        flow.append(Paragraph(title, H1))
        flow.append(Spacer(1, 6))

    # Correlations (Daily only)
    if include_correlations and tf_key == "Daily":
        _section_correlations(flow)
        flow.append(PageBreak())

    cfg = TIMEFRAMES[tf_key]

    if include_macro:
        _section_macro_table(
            flowables=flow,
            tf_key=tf_key,
            title=cfg["title_macro"],
            csv_id=cfg["ids"]["main"],
            bottom_docx=cfg["docx_macro"]
        )
        flow.append(PageBreak())

    if include_pct:
        _section_macro_table(
            flowables=flow,
            tf_key=tf_key,
            title=cfg["title_leaders"],
            csv_id=cfg["ids"]["leaders"],
            bottom_docx=""  # no bottom line on those cards
        )
        flow.append(PageBreak())

    if include_mm:
        _section_macro_table(
            flowables=flow,
            tf_key=tf_key,
            title=cfg["title_mm"],
            csv_id=cfg["ids"]["mm"],
            bottom_docx=""
        )
        flow.append(PageBreak())

    if include_delta:
        _section_macro_table(
            flowables=flow,
            tf_key=tf_key,
            title=cfg["title_delta"],
            csv_id=cfg["ids"]["delta"],
            bottom_docx=""
        )
        flow.append(PageBreak())

    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# -------------------------
# UI (FIXED)
# -------------------------
st.markdown(
    "<div style='text-align:center; font-size:22px; font-weight:700; margin-top:8px;'>Reports</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center; color:#6c757d; margin-bottom:16px;'>Build a PDF from portal sections</div>",
    unsafe_allow_html=True
)

# Packet builder model:
# - Pages (modules) are checkboxes (future-ready)
# - Timeframes are multi-select (Daily/Weekly/Monthly)
# - Output is ONE PDF even with multiple timeframes (merge PDFs in UI layer)

c1, c2, c3 = st.columns([1, 1.2, 1])
with c2:
    st.subheader("Report Builder")

st.divider()

# ---- Module checkboxes (future-ready) ----
include_morning_compass = st.checkbox("Morning Compass", value=True)

# Placeholder (future): other pages will become checkboxes too
# st.checkbox("Market Overview", value=False)
# st.checkbox("Performance Heatmap", value=False)
# st.checkbox("Sharpe Rank Heatmap", value=False)
# st.checkbox("Markmentum Heatmap", value=False)
# st.checkbox("Directional Trends", value=False)
# st.checkbox("Vantage Point", value=False)

# Morning Compass builder options
if include_morning_compass:
    left, mid, right = st.columns([1, 1, 1])

    with left:
        tf_keys = st.multiselect(
            "Add Timeframes (Optional)",
            ["Weekly", "Monthly"],
            default=[]
        )

        # Always include Daily first
        tf_keys = ["Daily"] + tf_keys
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

    st.divider()

    if not tf_keys:
        st.warning("Select at least one timeframe.")
        st.stop()

    # Preview metadata (show all selected timeframes)
    preview_parts = []
    for k in tf_keys:
        asof_k = _asof_date_from_main(k)
        preview_parts.append(f"{k}: {asof_k if asof_k else '(date not found)'}")
    st.markdown("**Preview:** Morning Compass – " + " | ".join(preview_parts))

    # Generate ONE PDF
    gen = st.button("Generate PDF", type="primary")

    if gen:
        # If only one timeframe, keep exact behavior (single builder call)
        if len(tf_keys) == 1:
            tf_key = tf_keys[0]
            asof = _asof_date_from_main(tf_key)

            pdf_bytes = build_morning_compass_pdf(
                include_correlations=include_correlations,
                include_macro=include_macro,
                include_pct=include_pct,
                include_mm=include_mm,
                include_delta=include_delta,
                tf_key=tf_key
            )

            filename = f"markmentum_morning_compass_{tf_key.lower()}_{asof.replace('/','-') if asof else 'report'}.pdf"

            st.success("PDF ready.")
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf"
            )

        else:
            # Multiple timeframes -> build each using the WORKING builder, then merge into ONE PDF (UI layer)
            writer = PdfWriter()

            for tf_key in tf_keys:
                pdf_bytes = build_morning_compass_pdf(
                    include_correlations=include_correlations,
                    include_macro=include_macro,
                    include_pct=include_pct,
                    include_mm=include_mm,
                    include_delta=include_delta,
                    tf_key=tf_key
                )

                reader = PdfReader(io.BytesIO(pdf_bytes))
                for page in reader.pages:
                    writer.add_page(page)

            out_buf = io.BytesIO()
            writer.write(out_buf)
            merged_pdf = out_buf.getvalue()

            # Use Daily's date if included, otherwise first selected
            tf_for_date = "Daily" if "Daily" in tf_keys else tf_keys[0]
            asof = _asof_date_from_main(tf_for_date)

            tf_slug = "-".join([t.lower() for t in tf_keys])
            filename = f"markmentum_morning_compass_{tf_slug}_{asof.replace('/','-') if asof else 'report'}.pdf"

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