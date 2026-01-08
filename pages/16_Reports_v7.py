# 16_Reports_v4.py
from pathlib import Path
import io
import os
import pandas as pd
import numpy as np
import streamlit as st

# PDF (ReportLab)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, KeepInFrame
)
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import ListFlowable, ListItem

# Merge PDFs (UI layer only)
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
# Shared helpers (unchanged)
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

def mo_load_for_timeframe(tf_key: str) -> list[pd.DataFrame]:
    nums = MO_CSV_MAP[tf_key]
    dfs: list[pd.DataFrame] = []
    for n in nums:
        if n is None:
            dfs.append(pd.DataFrame())
        else:
            dfs.append(load_csv_by_id(n, DATA_DIR))
    return dfs

def _mo_asof_from_df(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    date_col = None
    for c in df.columns:
        if str(c).strip().lower() in ("date", "as_of_date", "trade_date"):
            date_col = c
            break
    if not date_col:
        return ""
    asof = pd.to_datetime(df[date_col], errors="coerce").max()
    if pd.isna(asof):
        return ""
    return f"{asof.month}/{asof.day}/{asof.year}"


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
        return ""

def _market_read_to_flowables(mr_text: str) -> list:
    """
    Converts Market Read plain text into PDF flowables with bullets for key lines.
    """
    out = []
    lines = [ln.strip() for ln in (mr_text or "").splitlines()]
    lines = [ln for ln in lines if ln]  # drop blanks

    bullets = []
    in_bullets = False

    for ln in lines:
        low = ln.lower()

        # section headers / labels
        if low.startswith("market read:") or low.startswith("weekly market read:") or low.startswith("monthly market read:") or low.startswith("quarterly market read:"):
            out.append(Spacer(1, 6))
            out.append(Paragraph(clean_text(ln), H2))
            in_bullets = False
            continue

        if low in ("the market is saying:", "the market is saying (all numbers are wtd % returns):", 
                   "the market is saying (all numbers are mtd % returns):","the market is saying (all numbers are qtd % returns):","macro levers:", "macro levers (wtd % returns):", 
                   "macro levers (mtd % returns):", "macro levers (qtd % returns):"):
            # flush existing bullets
            if bullets:
                out.append(ListFlowable(bullets, bulletType="bullet", leftIndent=18))
                bullets = []
            out.append(Spacer(1, 6))
            out.append(Paragraph(clean_text(ln), H2))
            in_bullets = True
            continue

        if low.startswith("bottom line:"):
            if bullets:
                out.append(ListFlowable(bullets, bulletType="bullet", leftIndent=18))
                bullets = []
            out.append(Spacer(1, 10))
            out.append(Paragraph(clean_text(ln), P))
            in_bullets = False
            continue

        # normal lines
        if in_bullets:
            bullets.append(ListItem(Paragraph(clean_text(ln), P)))
        else:
            out.append(Paragraph(clean_text(ln), P))

    if bullets:
        out.append(ListFlowable(bullets, bulletType="bullet", leftIndent=18))

    return out


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

# =========================
# Market Overview config (from 03_Market_Overview.py)
# =========================
MO_TF_LABELS = ["Daily", "Weekly", "Monthly", "Quarterly"]

MO_CSV_MAP = {
    "Daily":     [26, 27, 28, 70, 71, 72, 29, 30, 31],
    "Weekly":    [52, 53, 54, 55, 56, 57, None, None, None],
    "Monthly":   [58, 59, 60, 61, 62, 63, None, None, None],
    "Quarterly": [64, 65, 66, 67, 68, 69, None, None, None],
}

# Market Read docx (same filenames as Market Overview page)
MO_MARKET_READ_DOCX = {
    "Daily":     "Market_Read_daily.docx",
    "Weekly":    "Market_Read_weekly.docx",
    "Monthly":   "Market_Read_monthly.docx",
    "Quarterly": "Market_Read_quarterly.docx",
}

# Opportunity Density (daily only in your page)
MO_OPPORTUNITY_DENSITY_CSV_ID = 92


# -------------------------
# PDF styling + builders (unchanged)
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
    y = 0.25 * inch
    max_lines = 6

    for i, line in enumerate(lines[:max_lines]):
        canvas.drawString(x, y + (max_lines - 1 - i) * 9, line)

    canvas.restoreState()

def _rr_bg_color(v: float, cap: float = 3.0):
    try:
        v = float(v)
    except Exception:
        return colors.white
    s = min(abs(v) / cap, 1.0)
    if v > 0:
        return colors.Color(0.90 - 0.10*s, 0.98, 0.94 - 0.10*s)
    if v < 0:
        return colors.Color(0.98, 0.92 - 0.08*s, 0.92 - 0.08*s)
    return colors.white

def _mm_bg_color(v: float):
    try:
        v = float(v)
    except Exception:
        return colors.white

    if v <= -100:
        return colors.Color(0.93, 0.75, 0.75)
    if v < -25:
        return colors.Color(0.97, 0.84, 0.84)
    if v <= 25:
        return colors.Color(0.93, 0.93, 0.93)
    if v < 100:
        return colors.Color(0.84, 0.95, 0.90)
    return colors.Color(0.75, 0.92, 0.85)

def _build_table(data_rows, col_widths, shade_rr=False, shade_mm=False, rr_col=None, mm_col=None):
    tbl = Table(data_rows, colWidths=col_widths, repeatRows=1)

    base = TableStyle([
        ("FONT", (0,0), (-1,0), "Helvetica-Bold", 9),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f2f2f2")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#1a1a1a")),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d9d9d9")),
        ("FONT", (0,1), (-1,-1), "Helvetica", 8),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (-1,0), "CENTER"),
        ("ALIGN", (1,1), (1,-1), "CENTER"),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,0), 6),
        ("BOTTOMPADDING", (0,0), (-1,0), 6),
        ("TOPPADDING", (0,1), (-1,-1), 4),
        ("BOTTOMPADDING", (0,1), (-1,-1), 4),
    ])
    tbl.setStyle(base)

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
    df_usd = load_csv_by_id(93, DATA_DIR)
    df_tnx = load_csv_by_id(94, DATA_DIR)

    if df_usd.empty:
        flowables.append(Paragraph("USD Correlations (missing qry_graph_data_93.csv)", NOTE))
        return
    if df_tnx.empty:
        flowables.append(Paragraph("Rates Correlations (missing qry_graph_data_94.csv)", NOTE))
        return

    def corr_table(df, title, bottom_docx, note_text):
        flowables.append(Paragraph(title, H2))

        cols = [c for c in ["Metric", "15D", "30D", "90D"] if c in df.columns]
        d = df[cols].copy()
        for c in ["15D", "30D", "90D"]:
            if c in d.columns:
                d[c] = d[c].map(lambda v: fmt_num(v, 2))

        data_rows = [cols] + d.values.tolist()

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

    col_widths = [
        2.35*inch,
        0.70*inch,
        0.75*inch,
        0.80*inch,
        0.85*inch,
        0.85*inch,
        0.75*inch,
        0.70*inch,
        0.85*inch,
    ]

    rr_col = 6
    mm_col = 7

    t = _build_table(
        data_rows=data_rows,
        col_widths=col_widths,
        shade_rr=True, shade_mm=True,
        rr_col=rr_col, mm_col=mm_col
    )
    flowables.append(t)

    bl = _read_docx_plain_text(DATA_DIR / bottom_docx) if bottom_docx else ""
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
# !!! DO NOT CHANGE OUTPUT LOGIC !!!
# Morning Compass PDF builder stays intact; we wrap it as a module.
# -------------------------
def build_title_page_pdf(asof: str) -> bytes:
    """
    Creates a simple title page:
    - centered logo
    - centered title: "Markmentum Research Pack"
    - date line
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch
    )

    flow = []

    # Spacer down a bit so it feels like a cover
    flow.append(Spacer(1, 0.6 * inch))

    if LOGO_PATH.exists():
        img = RLImage(str(LOGO_PATH))
        img.drawHeight = 0.9 * inch
        img.drawWidth = 7.2 * inch
        img.hAlign = "CENTER"
        flow.append(img)

    flow.append(Spacer(1, 0.5 * inch))

    # Big centered title
    cover_title = Paragraph("Research Pack", ParagraphStyle(
        "COVER_TITLE",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=22,
        spaceAfter=12
    ))
    flow.append(cover_title)

    if asof:
        flow.append(Paragraph(asof, ParagraphStyle(
            "COVER_DATE",
            parent=styles["BodyText"],
            alignment=TA_CENTER,
            fontSize=14,
            textColor=colors.HexColor("#444444")
        )))

    # IMPORTANT: no disclaimer/footer on title page
    doc.build(flow)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


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

    # Logo + title only for Daily (matches your current behavior)
    if tf_key == "Daily":
        #if LOGO_PATH.exists():
        #    img = RLImage(str(LOGO_PATH))
        #    img.drawHeight = 0.55 * inch
        #    img.drawWidth = 4.8 * inch
        #    img.hAlign = "CENTER"
        #    flow.append(img)
        #    flow.append(Spacer(1, 8))
        #else:
        #    flow.append(Paragraph("Markmentum Research", H1))

        asof = _asof_date_from_main(tf_key)
        title = f"Morning Compass" if asof else "Morning Compass"
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
            bottom_docx=""
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


def build_market_overview_pdf(
    tf_key: str,
    include_top_cards: bool = True,
    include_score_change_cards: bool = True,
    include_daily_extras: bool = True,      # highest/lowest/hist + opp density (Daily only)
    include_market_read: bool = True
) -> bytes:
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.45*inch, rightMargin=0.45*inch,
        topMargin=0.50*inch, bottomMargin=0.95*inch
    )

    flow: list = []

    dfs = mo_load_for_timeframe(tf_key)
    asof = _mo_asof_from_df(dfs[0])

    # Header
    title = f"{tf_key} Market Overview" + (f" – {asof}" if asof else "")
    flow.append(Paragraph(clean_text(title), H1))
    flow.append(Spacer(1, 6))

    def _simple_card(title_txt: str, df: pd.DataFrame, value_header: str = "Value"):
        if df.empty:
            flow.append(Paragraph(f"{title_txt} (no data)", NOTE))
            flow.append(Spacer(1, 8))
            return

        # Try to map columns robustly (tolerant like your page)
        cols_lower = {str(c).lower(): c for c in df.columns}
        tcol = cols_lower.get("ticker", None)
        ncol = cols_lower.get("ticker_name", None) or cols_lower.get("company", None)
        ccol = cols_lower.get("category", None) or cols_lower.get("exposure", None)

        # pick the "value" column: last numeric-ish column that isn't the known text columns
        known = {tcol, ncol, ccol}
        value_col = None
        for c in df.columns[::-1]:
            if c in known:
                continue
            value_col = c
            break

        # Build output with 4 columns max (Name/Ticker/Category/Value)
        use_cols = []
        if ncol: use_cols.append(ncol)
        if tcol: use_cols.append(tcol)
        if ccol: use_cols.append(ccol)
        if value_col: use_cols.append(value_col)

        d = df[use_cols].copy() if use_cols else df.copy()

        # rename
        rename_map = {}
        if ncol: rename_map[ncol] = "Name"
        if tcol: rename_map[tcol] = "Ticker"
        if ccol: rename_map[ccol] = "Category"
        if value_col: rename_map[value_col] = value_header
        d = d.rename(columns=rename_map)

        # formatting: if looks like percent (0.xx), show %; else int
        if value_header in d.columns:
            def _fmt_val(v):
                try:
                    fv = float(v)
                except Exception:
                    return str(v) if v is not None else ""

                # Formatting by type
                if value_header.lower() == "percent":
                    return fmt_pct(fv, 2)
                if value_header.lower() == "shares":
                    return fmt_num(fv, 2)  # you can switch to fmt_int if you want no decimals
                if value_header.lower() in ("change", "score"):
                    return fmt_int(fv)
                return fmt_num(fv, 2)

            d[value_header] = d[value_header].map(_fmt_val)

        header = [th(c) for c in d.columns.tolist()]
        data_rows = [header] + d.values.tolist()

        # widths
        widths = []
        for col in d.columns.tolist():
            if col == "Name":
                widths.append(2.8*inch)
            elif col == "Ticker":
                widths.append(0.8*inch)
            elif col == "Category":
                widths.append(1.7*inch)
            else:
                widths.append(1.0*inch)

        flow.append(Paragraph(clean_text(title_txt), H2))
        flow.append(_build_table(data_rows, widths))
        flow.append(Spacer(1, 10))

    # -------------------------
    # Row 1: gainers/decliners/most active
    # -------------------------
    if include_top_cards:
        _simple_card(f"{tf_key} – Top Ten Percentage Gainers", dfs[0], value_header="Percent")
        flow.append(PageBreak())
        _simple_card(f"{tf_key} – Top Ten Percentage Decliners", dfs[1], value_header="Percent")
        flow.append(PageBreak())
        _simple_card(f"{tf_key} – Most Active (Shares)", dfs[2], value_header="Shares")
        flow.append(PageBreak())

    # -------------------------
    # Row 2: Score gainers/decliners + score change distribution
    # -------------------------
    if include_score_change_cards:
        _simple_card(f"{tf_key} – Top Ten Markmentum Score Gainers", dfs[3], value_header="Change")
        _simple_card(f"{tf_key} – Top Ten Markmentum Score Decliners", dfs[4], value_header="Change")

        # Dist table (Score Bin / Ticker Count)
        df_dist = dfs[5].copy()
        flow.append(Paragraph(clean_text(f"{tf_key} – Markmentum Score Change Distribution"), H2))
        if df_dist.empty:
            flow.append(Paragraph("No data.", NOTE))
        else:
            # normalize columns
            cols_lower = {str(c).lower(): c for c in df_dist.columns}
            score_bin_col = cols_lower.get("score_bin") or cols_lower.get("score bin")
            count_col = cols_lower.get("tickercount") or cols_lower.get("ticker_count") or cols_lower.get("ticker count")
            if score_bin_col and count_col:
                d = df_dist[[score_bin_col, count_col]].copy()
                d.columns = ["Score Bin", "Ticker Count"]
                data_rows = [[th("Score Bin"), th("Ticker Count")]] + d.values.tolist()
                flow.append(_build_table(data_rows, [2.2*inch, 1.4*inch]))
            else:
                flow.append(Paragraph("Missing Score Bin / Count columns.", NOTE))
        flow.append(Spacer(1, 10))
        flow.append(PageBreak())

    # -------------------------
    # Daily extras: highest/lowest/hist + opportunity density
    # -------------------------
    if tf_key == "Daily" and include_daily_extras:
        _simple_card("Daily – Highest Markmentum Score", dfs[6], value_header="Score")
        _simple_card("Daily – Lowest Markmentum Score", dfs[7], value_header="Score")

        # Histogram table
        df_hist = dfs[8].copy()
        flow.append(Paragraph("Daily – Markmentum Score Histogram", H2))
        if df_hist.empty:
            flow.append(Paragraph("No data.", NOTE))
        else:
            cols_lower = {str(c).lower(): c for c in df_hist.columns}
            score_bin_col = cols_lower.get("score_bin") or cols_lower.get("score bin")
            count_col = cols_lower.get("tickercount") or cols_lower.get("ticker_count") or cols_lower.get("ticker count")

            if score_bin_col and count_col:
                mapping = {
                    "Below -100": "Strong Sell",
                    "-100 to -26": "Sell",
                    "-25 to 25": "Neutral",
                    "26 to 100": "Buy",
                    "Above 100": "Strong Buy",
                }
                df_hist["Classification"] = df_hist[score_bin_col].map(mapping)
                d = df_hist[["Classification", score_bin_col, count_col]].copy()
                d.columns = ["Classification", "Score Bin", "Ticker Count"]
                data_rows = [[th("Classification"), th("Score Bin"), th("Ticker Count")]] + d.values.tolist()
                flow.append(_build_table(data_rows, [2.2*inch, 1.6*inch, 1.4*inch]))
            else:
                flow.append(Paragraph("Missing histogram columns.", NOTE))

        flow.append(Spacer(1, 10))
        flow.append(PageBreak())

        # Opportunity Density (qry_graph_data_92.csv)
        df_od = load_csv_by_id(MO_OPPORTUNITY_DENSITY_CSV_ID, DATA_DIR).copy()
        flow.append(Paragraph("Opportunity Density", H2))
        if df_od.empty:
            flow.append(Paragraph("No data.", NOTE))
        else:
            # format percent columns if present
            for col in ["Buy %", "Neutral %", "Sell %"]:
                if col in df_od.columns:
                    df_od[col] = df_od[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
            header = [th(c) for c in df_od.columns.tolist()]
            data_rows = [header] + df_od.values.tolist()

            # widths: first column wide
            widths = [2.3*inch] + [0.70*inch]*(len(df_od.columns)-1)
            flow.append(_build_table(data_rows, widths))
            flow.append(Spacer(1, 6))
            flow.append(Paragraph(
                "Note: Buy classifications require Risk/Reward ≥ 3 and MM Score > 25. "
                "Sell classifications require Risk/Reward ≤ −3 and MM Score < −25.",
                NOTE
            ))

        flow.append(Spacer(1, 10))
        flow.append(PageBreak())

    # -------------------------
    # Market Read (docx)
    # -------------------------
    if include_market_read:
        #flow.append(Paragraph("Market Read", H1))
        docx_name = MO_MARKET_READ_DOCX.get(tf_key, "")
        mr_text = _read_docx_plain_text(DATA_DIR / docx_name) if docx_name else ""

        if not mr_text:
            flow.append(Paragraph(f"Market Read missing or empty: {docx_name}", NOTE))
        else:
            mr_items = _market_read_to_flowables(mr_text)

    # Force Market Read to stay on ONE page by shrinking content if needed
    # doc.height is the usable height (already respects your margins: bottomMargin=0.95")
    mr_box = KeepInFrame(
        maxWidth=doc.width,
        maxHeight=doc.height,
        content=mr_items,
        mode="shrink",      # <— key: auto-scale down to fit
        hAlign="LEFT",
        vAlign="TOP",
    )
    flow.append(mr_box)

    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes




# =========================================================
# MODULAR PACKET ARCHITECTURE (NEW)
# =========================================================
def merge_pdf_bytes_in_order(pdf_blobs: list[bytes]) -> bytes:
    """Merge already-built PDFs into one PDF (order preserved)."""
    writer = PdfWriter()
    for blob in pdf_blobs:
        reader = PdfReader(io.BytesIO(blob))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

def normalize_timeframes(selected: list[str]) -> list[str]:
    """Enforce your current behavior: Daily always included for Morning Compass packet."""
    if not selected:
        return ["Daily"]
    # ensure Daily first if included
    s = list(dict.fromkeys(selected))
    if "Daily" in s:
        s = ["Daily"] + [x for x in s if x != "Daily"]
    return s

class ReportModuleBase:
    key: str = "base"
    label: str = "Base Module"

    def ui(self) -> dict:
        """
        Render module UI and return an options dict.
        Must be deterministic given Streamlit state.
        """
        return {}

    def build(self, options: dict) -> tuple[list[bytes], str]:
        """
        Return (pdfs_in_order, filename_stub)
        - pdfs_in_order: list of pdf bytes blobs
        - filename_stub: used to name download file
        """
        return ([], "report")


class MorningCompassModule(ReportModuleBase):
    key = "morning_compass"
    label = "Morning Compass"

    def ui(self) -> dict:
        left, mid, right = st.columns([1, 1, 1])

        with left:
            tf_keys = st.multiselect(
                "Add Timeframes (Optional)",
                ["Weekly", "Monthly"],
                default=[]
            )
            # preserve your current rule: Daily always included
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

        # Preview metadata (show all selected timeframes)
        preview_parts = []
        for k in tf_keys:
            asof_k = _asof_date_from_main(k)
            preview_parts.append(f"{k}: {asof_k if asof_k else '(date not found)'}")
        st.markdown("**Preview:** Morning Compass – " + " | ".join(preview_parts))

        return {
            "tf_keys": tf_keys,
            "include_correlations": include_correlations,
            "include_macro": include_macro,
            "include_pct": include_pct,
            "include_mm": include_mm,
            "include_delta": include_delta,
        }

    def build(self, options: dict) -> tuple[list[bytes], str]:
        tf_keys = options.get("tf_keys", ["Daily"])
        # already Daily-first; keep as-is
        blobs: list[bytes] = []

        for tf_key in tf_keys:
            blobs.append(
                build_morning_compass_pdf(
                    include_correlations=options.get("include_correlations", True),
                    include_macro=options.get("include_macro", True),
                    include_pct=options.get("include_pct", True),
                    include_mm=options.get("include_mm", True),
                    include_delta=options.get("include_delta", True),
                    tf_key=tf_key
                )
            )

        # naming: matches your current logic using Daily date if present
        tf_for_date = "Daily" if "Daily" in tf_keys else tf_keys[0]
        asof = _asof_date_from_main(tf_for_date)
        tf_slug = "-".join([t.lower() for t in tf_keys])
        filename_stub = f"markmentum_morning_compass_{tf_slug}_{asof.replace('/','-') if asof else 'report'}"
        return (blobs, filename_stub)


class MarketOverviewModule(ReportModuleBase):
    key = "market_overview"
    label = "Market Overview"

    #def ui(self) -> dict:
    #    tf_key = st.selectbox(
    #        "Timeframe",
    #        MO_TF_LABELS,
    #        index=0
    #    )

    def ui(self) -> dict:
        extra_tfs = st.multiselect(
            "Add Timeframes (Optional)",
                ["Weekly", "Monthly", "Quarterly"],
                default=[]
        )
        tf_keys = ["Daily"] + extra_tfs

        c1, c2, c3 = st.columns([1, 1, 1])

        with c1:
            include_top_cards = st.checkbox("Include Top/Bottom/Most Active", value=True)
            include_score_change_cards = st.checkbox("Include MM Score Gainers/Decliners + Change Distribution", value=True)

        with c2:
#            include_daily_extras = st.checkbox(
#                "Include Daily extras (Highest/Lowest/Histogram + Opportunity Density)",
#                value=True,
#                disabled=(tf_key != "Daily")
#            )

            include_daily_extras = st.checkbox(
                "Include Daily extras (Highest/Lowest/Histogram + Opportunity Density)",
                value=True
            )


        with c3:
            include_market_read = st.checkbox("Include Market Read", value=True)

        # Preview
        preview_parts = []
        for k in tf_keys:
            dfs = mo_load_for_timeframe(k)
            asof = _mo_asof_from_df(dfs[0])
            preview_parts.append(f"{k}: {asof if asof else '(date not found)'}")
        st.markdown("**Preview:** Market Overview – " + " | ".join(preview_parts))

        return {
            "tf_keys": tf_keys,
            "include_top_cards": include_top_cards,
            "include_score_change_cards": include_score_change_cards,
            "include_daily_extras": include_daily_extras,   # applies to Daily only in build()
            "include_market_read": include_market_read,
        }

    def build(self, options: dict) -> tuple[list[bytes], str]:
        tf_keys = options.get("tf_keys", ["Daily"])

        # enforce order: Daily, Weekly, Monthly, Quarterly
        order = ["Daily", "Weekly", "Monthly", "Quarterly"]
        tf_keys = [t for t in order if t in tf_keys]

        blobs: list[bytes] = []

        for tf_key in tf_keys:
            blobs.append(
                build_market_overview_pdf(
                    tf_key=tf_key,
                    include_top_cards=options.get("include_top_cards", True),
                    include_score_change_cards=options.get("include_score_change_cards", True),
                    include_daily_extras=(tf_key == "Daily" and options.get("include_daily_extras", True)),
                    include_market_read=options.get("include_market_read", True),
                )
            )

        # filename stub
        tf_for_date = "Daily" if "Daily" in tf_keys else tf_keys[0]
        asof = _mo_asof_from_df(mo_load_for_timeframe(tf_for_date)[0])
        date_slug = asof.replace("/", "-") if asof else "report"
        tf_slug = "-".join([t.lower() for t in tf_keys])
        stub = f"market_overview_{tf_slug}_{date_slug}"

        return (blobs, stub)


class PlaceholderModule(ReportModuleBase):
    """Safe placeholder so you can turn on modules without breaking the packet builder."""
    def __init__(self, key: str, label: str):
        self.key = key
        self.label = label

    def ui(self) -> dict:
        st.info(f"{self.label} module is not wired to PDF yet. (Placeholder)")
        return {}

    def build(self, options: dict) -> tuple[list[bytes], str]:
        # returns no pdfs; packet builder will skip it
        return ([], self.key)


REGISTERED_MODULES: list[ReportModuleBase] = [
    MorningCompassModule(),
    MarketOverviewModule(),
    PlaceholderModule("performance_heatmap", "Performance Heatmap"),
    PlaceholderModule("sharpe_rank_heatmap", "Sharpe Rank Heatmap"),
    PlaceholderModule("markmentum_heatmap", "Markmentum Heatmap"),
    PlaceholderModule("directional_trends", "Directional Trends"),
    PlaceholderModule("vantage_point", "Vantage Point"),
]

MODULE_BY_KEY = {m.key: m for m in REGISTERED_MODULES}


# =========================================================
# UI (MODULAR)
# =========================================================
st.markdown(
    "<div style='text-align:center; font-size:22px; font-weight:700; margin-top:8px;'>Reports</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center; color:#6c757d; margin-bottom:16px;'>Build a PDF from portal sections</div>",
    unsafe_allow_html=True
)

st.divider()

# ---- Module selection ----
# Default only Morning Compass ON (same as your current behavior)
default_selected = ["morning_compass"]

selected_keys = []
for m in REGISTERED_MODULES:
    checked = st.checkbox(m.label, value=(m.key in default_selected))
    if checked:
        selected_keys.append(m.key)

# ---- Module options blocks ----
module_options: dict[str, dict] = {}

# Separator between selection list and builder options
st.divider()

for key in selected_keys:
    module = MODULE_BY_KEY[key]
    with st.expander(f"{module.label} Options", expanded=(key in selected_keys)):
        module_options[key] = module.ui()

st.divider()

# ---- Generate packet ----
gen = st.button("Generate PDF", type="primary", disabled=(len(selected_keys) == 0))

if gen:
    pdf_parts: list[bytes] = []
    filename_parts: list[str] = []

    for key in selected_keys:
        module = MODULE_BY_KEY[key]
        blobs, stub = module.build(module_options.get(key, {}))
        if blobs:
            pdf_parts.extend(blobs)
            filename_parts.append(stub)

    if not pdf_parts:
        st.warning("No PDFs were generated (selected modules are placeholders or missing data).")
        st.stop()

    # If only one part, keep exact “single blob” behavior; else merge.
    #if len(pdf_parts) == 1:
    #    final_pdf = pdf_parts[0]
    #else:
    #    final_pdf = merge_pdf_bytes_in_order(pdf_parts)

    # Build cover page using Daily as-of (best effort)
    asof = _asof_date_from_main("Daily")
    cover_pdf = build_title_page_pdf(asof)

    # Always prepend cover page
    pdf_parts_with_cover = [cover_pdf] + pdf_parts

    # Merge into one PDF (cover + content)
    final_pdf = merge_pdf_bytes_in_order(pdf_parts_with_cover)


    # Filename:
    # - If only Morning Compass, the stub already matches your v3 naming.
    # - If multiple modules, create a clean packet name.
    #if len(filename_parts) == 1:
    #    filename = f"{filename_parts[0]}.pdf"
    #else:
        # include Daily as-of if possible (best-effort)
    #    asof = _asof_date_from_main("Daily")
    #    date_slug = asof.replace("/", "-") if asof else "report"
    #    filename = f"markmentum_packet_{date_slug}.pdf"

    asof = _asof_date_from_main("Daily")
    date_slug = asof.replace("/", "-") if asof else "report"
    filename = f"Markmentum Research Pack - {date_slug}.pdf"


    st.success("PDF ready.")
    st.download_button(
        label="Download PDF",
        data=final_pdf,
        file_name=filename,
        mime="application/pdf"
    )

st.markdown("---")
st.markdown(
    f"<div style='font-size: 12px; color: gray;'>{DISCLAIMER_TEXT}</div>",
    unsafe_allow_html=True
)