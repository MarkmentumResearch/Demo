from pathlib import Path
import base64
import textwrap
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from urllib.parse import quote_plus

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – Morning Compass", layout="wide")
st.cache_data.clear()
# ---- LAYOUT & WIDTH TUNING (Cloud parity + your constraints) ----





# -------------------------
# Paths (portable for Cloud)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"


# -------------------------
# Header (logo centered)
# -------------------------
def _image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


if LOGO_PATH.exists():
    st.markdown(
        f"""
        <div style="text-align:center; margin: 8px 0 16px;">
            <img src="data:image/png;base64,{_image_to_base64(LOGO_PATH)}" width="440">
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------
# Helpers
# -------------------------
def _mk_ticker_link(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    return (
        f'<a href="?page=Deep%20Dive&ticker={quote_plus(t)}" '
        f'target="_self" rel="noopener" '
        f'style="text-decoration:none; font-weight:600;">{t}</a>'
    )

# Lightweight router for Deep Dive links
qp = st.query_params
dest = (qp.get("page") or "").strip().lower()
if dest.replace("%20", " ") == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    st.switch_page("pages/13_Deep_Dive_Dashboard.py")

def row_spacer(height_px: int = 14):
    st.markdown(f"<div style='height:{height_px}px'></div>", unsafe_allow_html=True)

# -------------------------
# Morning Compass – styling
# -------------------------
# -------------------------
# Morning Compass – styling
# -------------------------
st.markdown("""
<style>
/* Center the single card on the page */
.card-wrap { display:flex; justify-content:center; }
.card { 
  border:1px solid #cfcfcf; border-radius:8px; background:#fff;
  padding:12px 12px 8px 12px; width:100%;
  max-width:1320px;  /* was 1120px -> more room so names show */
}

/* Table styling to match Daily Overview */
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td {
  border:1px solid #d9d9d9; padding:6px 8px; font-size:13px;
  overflow:hidden; text-overflow:ellipsis;
}
.tbl th { background:#f2f2f2; font-weight:700; color:#1a1a1a; text-align:left; }

/* Alignment rules */
.tbl th:nth-child(2), .tbl td:nth-child(2) { text-align:center; }    /* Ticker centered */

/* HEADERS from Close..MM Score Change centered */
.tbl th:nth-child(n+3) { text-align:center; }

/* CELLS from Close..MM Score Change right-aligned */
.tbl td:nth-child(n+3) { text-align:right; white-space:nowrap; }

/* Name column = 40ch, allow wrapping so full name shows */
.tbl col.col-name { min-width:40ch; width:40ch; max-width:40ch; }
.tbl th:nth-child(1), .tbl td:nth-child(1) {
  white-space:normal;               /* allow wrap */
  overflow:visible; text-overflow:clip;
}

/* Keep ticker links bold without underline */
.tbl a { text-decoration:none; font-weight:600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* bottom line inside the card, attached to table border */
.bl {
  border-top: 1px solid #e5e5e5;
  margin-top: 8px;
  padding-top: 10px;
  font-size: 13px;
  line-height: 1.45;
  color: #1a1a1a;
}
.card .note {
  font-size: 0.85em;
  color: #6c757d;   /* muted gray */
  line-height: 1.3;
}
</style>
""", unsafe_allow_html=True)



# -------------------------
# Load Morning Compass CSV
# -------------------------
@st.cache_data(show_spinner=False)
def load_mc_73(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df

df73 = load_mc_73(DATA_DIR / "qry_graph_data_73.csv")

# -------------------------
# Page title under the logo
# -------------------------
date_str = ""
if not df73.empty and "Date" in df73.columns:
    asof = pd.to_datetime(df73["Date"], errors="coerce").max()
    if pd.notna(asof):
        date_str = f"{asof.month}/{asof.day}/{asof.year}"

st.markdown(
    f"""
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:18px; font-weight:600; color:#1a1a1a;">
        Morning Compass – {date_str}
    </div>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# Card 1: Morning Compass table
# -------------------------
required_cols = [
    "Date","Ticker","Ticker_name","Close",
    "daily_Return","day_pr_low","day_pr_high",
    "day_rr_ratio","model_score","model_score_delta"
]

if df73.empty or not all(c in df73.columns for c in required_cols):
    st.info("Morning Compass: `qry_graph_data_73.csv` is missing or columns are incomplete.")
else:
    df_render = df73.copy()
    df_render["Ticker"] = df_render["Ticker"].apply(_mk_ticker_link)

    # formatters
    def fmt_num(x, nd=2):
        try:
            if pd.isna(x): return ""
            return f"{float(x):,.{nd}f}"
        except Exception: return ""

    def fmt_pct(x, nd=2):
        try:
            if pd.isna(x): return ""
            return f"{float(x)*100:,.{nd}f}%"
        except Exception: return ""

    def fmt_int(x):
        try:
            if pd.isna(x): return ""
            return f"{int(round(float(x))):,}"
        except Exception: return ""

    # Diverging tint for Risk/Reward (−cap … +cap), subtle + readable
    def rr_tinted_html(x, cap=3.0):
        try:
            if pd.isna(x): 
                return ""
            v = float(x)
        except Exception:
            return ""

        # scale 0..1 (capped), keep near-zero very light
        s = min(abs(v) / cap, 1.0)
        alpha = 0.12 + 0.28 * s     # 0.12 → 0.40 opacity

        if v > 0:
            # green (tailwind-ish 10B981)
            bg = f"rgba(16,185,129,{alpha:.3f})"
        elif v < 0:
            # red (EF4444)
            bg = f"rgba(239,68,68,{alpha:.3f})"
        else:
            bg = "transparent"

        # numeric label with 1 decimal, same as before
        label = f"{v:,.1f}"
        return f'<span style="display:block; background:{bg}; padding:0 4px; border-radius:2px;">{label}</span>'

    # Discrete tint for MM Score using bins:
    # ≤ -100: deep red | -100 < v < -25: red | -25 ≤ v ≤ 25: gray | 25 < v < 100: green | ≥ 100: dark green
    def mm_badge_html(x):
        try:
            if pd.isna(x):
                return ""
            v = float(x)
        except Exception:
            return ""

        if v <= -100:
            bg, alpha = "rgba(185,28,28,0.35)", 0.35   # deep red
        elif v < -25:
            bg, alpha = "rgba(239,68,68,0.28)", 0.28   # red
        elif v <= 25:
            bg, alpha = "rgba(229,231,235,1.00)", 1.00 # gray pill
        elif v < 100:
            bg, alpha = "rgba(16,185,129,0.28)", 0.28  # green
        else:
            bg, alpha = "rgba(6,95,70,0.35)", 0.35     # dark green

        label = f"{int(round(v)):,}"
        # block so it fills the cell nicely; cell stays right-aligned from CSS
        return f'<span style="display:block; background:{bg}; padding:0 4px; border-radius:2px;">{label}</span>'

    df_card = pd.DataFrame({
    "Name":          df_render["Ticker_name"],
    "Ticker":        df_render["Ticker"],
    "Close":         df_render["Close"].map(lambda v: fmt_num(v, 2)),
    "% Change":       df_render["daily_Return"].map(lambda v: fmt_pct(v, 2)),   # renamed
    "Probable Low":  df_render["day_pr_low"].map(lambda v: fmt_num(v, 2)),
    "Probable High": df_render["day_pr_high"].map(lambda v: fmt_num(v, 2)),
    "Risk / Reward":   df_render["day_rr_ratio"].map(rr_tinted_html),
    "MM Score":      df_render["model_score"].map(mm_badge_html),
    "MM Score Change":df_render["model_score_delta"].map(fmt_int),              # renamed
    })

    # Clean HTML (no border attr, no 'dataframe' class)
    table_html = df_card.to_html(index=False, classes="tbl", escape=False, border=0)
    table_html = table_html.replace('class="dataframe tbl"', 'class="tbl"')

    # Insert a proper colgroup AFTER the opening <table class="tbl">
    colgroup = """
    <colgroup>
    <col class="col-name"> <!-- Name (40ch) -->
    <col>                   <!-- Ticker (center) -->
    <col>                   <!-- Close (right) -->
    <col>                   <!-- % Change (right) -->
    <col>                   <!-- Probable Low (right) -->
    <col>                   <!-- Probable High (right) -->
    <col>                   <!-- Risk/Reward (right) -->
    <col>                   <!-- MM Score (right) -->
    <col>                   <!-- MM Score Change (right) -->
    </colgroup>
    """.strip()

    table_html = table_html.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)


    import os
    try:
        from docx import Document  # pip install python-docx
    except Exception:
        Document = None

    def _is_list_paragraph(paragraph) -> bool:
        try:
            return paragraph._p.pPr.numPr is not None
        except Exception:
            return False

    @st.cache_data(show_spinner=False)
    def load_market_read_md(doc_path: str = "data/bottom_line_daily.docx") -> str:
        if Document is None:
            return "⚠️ **Market Read**: python-docx is not installed (run: `pip install python-docx`)."
        if not os.path.exists(doc_path):
            return f"⚠️ **Market Read** file not found: `{doc_path}`"
        try:
            doc = Document(doc_path)
        except Exception as e:
            return f"⚠️ Could not open **Market Read** file `{doc_path}`: {e}"
        lines: list[str] = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            lines.append(f"- {text}" if _is_list_paragraph(p) else text)
        for i, l in enumerate(lines):
            if l.startswith("Market Read:") and "The model is saying:" in l:
                left, right = l.split("The model is saying:", 1)
                lines[i] = left.strip()
                lines.insert(i + 1, "The model is saying:")
                if right.strip():
                    lines.insert(i + 2, right.strip())
                break
        return "\n\n".join(lines)

    from html import escape

    docx_path = (DATA_DIR / "bottom_line_daily.docx").resolve()
    bl_text = load_market_read_md(str(docx_path)).strip()
    bl_html_safe = escape(bl_text)  # keep it plain, no markdown parsing needed
    note_text = "Note: MM Score → Contrarian positioning (higher = crowded short, lower = crowded long)."
    note_html_safe = escape(note_text)

    # Centered card, no inner title
    card_html = f'''
    <div class="card-wrap">
        <div class="card">
            <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a;">
              Daily Compass
            </h3>
            {table_html}
            <div class="bl">{bl_html_safe}</div>
            <div class="bl note">{note_html_safe}</div>
        </div>
    </div>
    '''
    st.markdown(card_html, unsafe_allow_html=True)

# -------------------------
# Card 2: Leaders/Laggard by % Change
# -------------------------
# =========================
# Card: Leaders/Laggard by % Change  (single table, 10 rows)
# =========================
@st.cache_data(show_spinner=False)
def load_mc_74(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

df74 = load_mc_74(DATA_DIR / "qry_graph_data_74.csv")

required_cols_74 = [
    "Date","Ticker","Ticker_name","Close",
    "daily_Return","day_pr_low","day_pr_high",
    "day_rr_ratio","model_score","model_score_delta"
]

if df74.empty or not all(c in df74.columns for c in required_cols_74):
    row_spacer(8)
    st.info("Top 5 Leaders/Laggard by % Change: `qry_graph_data_74.csv` is missing or columns are incomplete.")
else:
    d = df74.copy()

    # Keep Deep Dive link on Ticker (same as first card)
    d["Ticker"] = d["Ticker"].apply(_mk_ticker_link)

    # ---- build card with same columns/order/formatting as the first card ----
    df_74_card = pd.DataFrame({
        "Name":          d["Ticker_name"],
        "Ticker":        d["Ticker"],
        "Close":         d["Close"].map(lambda v: fmt_num(v, 2)),
        "% Change":       d["daily_Return"].map(lambda v: fmt_pct(v, 2)),
        "Probable Low":  d["day_pr_low"].map(lambda v: fmt_num(v, 2)),
        "Probable High": d["day_pr_high"].map(lambda v: fmt_num(v, 2)),
        "Risk / Reward":   d["day_rr_ratio"].map(rr_tinted_html),   # same gradient tint
        "MM Score":      d["model_score"].map(mm_badge_html),
        "MM Score Change":d["model_score_delta"].map(fmt_int),
    })

    # to HTML (same classes/alignment as first card)
    tbl_html_74 = df_74_card.to_html(index=False, classes="tbl", escape=False, border=0)
    tbl_html_74 = tbl_html_74.replace('class="dataframe tbl"', 'class="tbl"')

    # same colgroup (Name = 40ch; Ticker centered; numbers right-aligned via CSS)
    colgroup = """
    <colgroup>
      <col class="col-name"> <!-- Name (40ch) -->
      <col>                   <!-- Ticker -->
      <col>                   <!-- Close -->
      <col>                   <!-- % Change -->
      <col>                   <!-- Probable Low -->
      <col>                   <!-- Probable High -->
      <col>                   <!-- Risk/Reward -->
      <col>                   <!-- MM Score -->
      <col>                   <!-- MM Score Change -->
    </colgroup>
    """.strip()
    tbl_html_74 = tbl_html_74.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

    note_text = "Note: MM Score → Contrarian positioning (higher = crowded short, lower = crowded long)."
    note_html_safe = escape(note_text)

    # render centered card below the first card
    row_spacer(10)
    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a;">
              Top 5 Leaders/Laggards by % Change
            </h3>
            {tbl_html_74}
            <div class="bl note">{note_html_safe}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# Card 3: Leaders/Laggard by % MM Score  (single table, 10 rows)
# =========================
@st.cache_data(show_spinner=False)
def load_mc_75(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

df75 = load_mc_75(DATA_DIR / "qry_graph_data_75.csv")

required_cols_75 = [
    "Date","Ticker","Ticker_name","Close",
    "daily_Return","day_pr_low","day_pr_high",
    "day_rr_ratio","model_score","model_score_delta"
]

if df75.empty or not all(c in df74.columns for c in required_cols_74):
    row_spacer(8)
    st.info("Top 5 Leaders/Laggard by % Change: `qry_graph_data_75.csv` is missing or columns are incomplete.")
else:
    d = df75.copy()

    # Keep Deep Dive link on Ticker (same as first card)
    d["Ticker"] = d["Ticker"].apply(_mk_ticker_link)

    # ---- build card with same columns/order/formatting as the first card ----
    df_75_card = pd.DataFrame({
        "Name":          d["Ticker_name"],
        "Ticker":        d["Ticker"],
        "Close":         d["Close"].map(lambda v: fmt_num(v, 2)),
        "% Change":       d["daily_Return"].map(lambda v: fmt_pct(v, 2)),
        "Probable Low":  d["day_pr_low"].map(lambda v: fmt_num(v, 2)),
        "Probable High": d["day_pr_high"].map(lambda v: fmt_num(v, 2)),
        "Risk / Reward":   d["day_rr_ratio"].map(rr_tinted_html),   # same gradient tint
        "MM Score":      d["model_score"].map(mm_badge_html),
        "MM Score Change":d["model_score_delta"].map(fmt_int),
    })

    # to HTML (same classes/alignment as first card)
    tbl_html_75 = df_75_card.to_html(index=False, classes="tbl", escape=False, border=0)
    tbl_html_75 = tbl_html_75.replace('class="dataframe tbl"', 'class="tbl"')

    # same colgroup (Name = 40ch; Ticker centered; numbers right-aligned via CSS)
    colgroup = """
    <colgroup>
      <col class="col-name"> <!-- Name (40ch) -->
      <col>                   <!-- Ticker -->
      <col>                   <!-- Close -->
      <col>                   <!-- % Change -->
      <col>                   <!-- Probable Low -->
      <col>                   <!-- Probable High -->
      <col>                   <!-- Risk/Reward -->
      <col>                   <!-- MM Score -->
      <col>                   <!-- MM Score Change -->
    </colgroup>
    """.strip()
    tbl_html_75 = tbl_html_75.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

    note_text = "Note: MM Score → Contrarian positioning (higher = crowded short, lower = crowded long)."
    note_html_safe = escape(note_text)

    # render centered card below the first card
    row_spacer(10)
    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a;">
              Top 5 Leaders/Laggards by MM Score
            </h3>
            {tbl_html_75}
            <div class="bl note">{note_html_safe}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================
# Card 4: Leaders/Laggard by MM Score Change (single table, 10 rows)
# =========================
@st.cache_data(show_spinner=False)
def load_mc_77(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

df77 = load_mc_77(DATA_DIR / "qry_graph_data_77.csv")

required_cols_77 = [
    "Date","Ticker","Ticker_name","Close",
    "daily_Return","day_pr_low","day_pr_high",
    "day_rr_ratio","model_score","model_score_delta"
]

if df77.empty or not all(c in df77.columns for c in required_cols_74):
    row_spacer(8)
    st.info("Top 5 Leaders/Laggard by % Change: `qry_graph_data_77.csv` is missing or columns are incomplete.")
else:
    d = df77.copy()

    # Keep Deep Dive link on Ticker (same as first card)
    d["Ticker"] = d["Ticker"].apply(_mk_ticker_link)

    # ---- build card with same columns/order/formatting as the first card ----
    df_77_card = pd.DataFrame({
        "Name":          d["Ticker_name"],
        "Ticker":        d["Ticker"],
        "Close":         d["Close"].map(lambda v: fmt_num(v, 2)),
        "% Change":       d["daily_Return"].map(lambda v: fmt_pct(v, 2)),
        "Probable Low":  d["day_pr_low"].map(lambda v: fmt_num(v, 2)),
        "Probable High": d["day_pr_high"].map(lambda v: fmt_num(v, 2)),
        "Risk / Reward":   d["day_rr_ratio"].map(rr_tinted_html),   # same gradient tint
        "MM Score":      d["model_score"].map(mm_badge_html),
        "MM Score Change":d["model_score_delta"].map(fmt_int),
    })

    # to HTML (same classes/alignment as first card)
    tbl_html_77 = df_77_card.to_html(index=False, classes="tbl", escape=False, border=0)
    tbl_html_77 = tbl_html_77.replace('class="dataframe tbl"', 'class="tbl"')

    # same colgroup (Name = 40ch; Ticker centered; numbers right-aligned via CSS)
    colgroup = """
    <colgroup>
      <col class="col-name"> <!-- Name (40ch) -->
      <col>                   <!-- Ticker -->
      <col>                   <!-- Close -->
      <col>                   <!-- % Change -->
      <col>                   <!-- Probable Low -->
      <col>                   <!-- Probable High -->
      <col>                   <!-- Risk/Reward -->
      <col>                   <!-- MM Score -->
      <col>                   <!-- MM Score Change -->
    </colgroup>
    """.strip()
    tbl_html_77 = tbl_html_77.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

    note_text = "Note: MM Score → Contrarian positioning (higher = crowded short, lower = crowded long)."
    note_html_safe = escape(note_text)

    # render centered card below the first card
    row_spacer(10)
    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a;">
              Top 5 Leaders/Laggards by MM Score
            </h3>
            {tbl_html_77}
            <div class="bl note">{note_html_safe}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Card 5: (optional) Category Snapshot – uses qry_graph_data_76.csv
# =========================
@st.cache_data(show_spinner=False)
def load_mc_76(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

row_spacer(6)
show_cat = st.checkbox("View Category Snapshot", value=False)

if show_cat:
    df76 = load_mc_76(DATA_DIR / "qry_graph_data_76.csv")
    required_cols_76 = [
        "Date","Ticker","Ticker_name","Category","Close",
        "daily_Return","day_pr_low","day_pr_high",
        "day_rr_ratio","model_score","model_score_delta"
    ]

    if df76.empty or not all(c in df76.columns for c in required_cols_76):
        st.info("Category Snapshot: `qry_graph_data_76.csv` is missing or columns are incomplete.")
    else:
        # Preferred category order (exact text)
        cat_order = [
            "Sector & Style ETFs","Indices","Futures","Currencies","Commodities","Bonds","Yields","Volatility","Foreign",
            "Communication Services","Consumer Discretionary","Consumer Staples","Energy","Financials",
            "Health Care","Industrials","Information Technology","Materials","Real Estate","Utilities","MR Discretion"
        ]

        # Center the selector
        c1, c2, c3 = st.columns([1, .9, 1])
        with c2:
            # Show only categories present in the CSV but ordered by your preference
            present = [c for c in cat_order if c in df76["Category"].dropna().unique().tolist()]
            sel = st.selectbox("Category", present, index=0)

        d = df76[df76["Category"] == sel].copy()

        # Link ticker
        d["Ticker"] = d["Ticker"].apply(_mk_ticker_link)

        # Build the card (do NOT show Category column)
        df_cat_card = pd.DataFrame({
            "Name":           d["Ticker_name"],
            "Ticker":         d["Ticker"],
            "Close":          d["Close"].map(lambda v: fmt_num(v, 2)),
            "% Change":        d["daily_Return"].map(lambda v: fmt_pct(v, 2)),
            "Probable Low":   d["day_pr_low"].map(lambda v: fmt_num(v, 2)),
            "Probable High":  d["day_pr_high"].map(lambda v: fmt_num(v, 2)),
            "Risk / Reward":    d["day_rr_ratio"].map(rr_tinted_html),
            "MM Score":      d["model_score"].map(mm_badge_html),
            "MM Score Change": d["model_score_delta"].map(fmt_int),
        })

        tbl_html_76 = df_cat_card.to_html(index=False, classes="tbl", escape=False, border=0)
        tbl_html_76 = tbl_html_76.replace('class="dataframe tbl"', 'class="tbl"')

        # Same colgroup as other cards (Name = 40ch)
        colgroup = """
        <colgroup>
          <col class="col-name">
          <col>
          <col>
          <col>
          <col>
          <col>
          <col>
          <col>
          <col>
        </colgroup>
        """.strip()
        tbl_html_76 = tbl_html_76.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

        note_text = "Note: MM Score → Contrarian positioning (higher = crowded short, lower = crowded long)."
        note_html_safe = escape(note_text)

        row_spacer(6)
        st.markdown(
            f"""
            <div class="card-wrap">
              <div class="card">
                <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a;">
                  Category Snapshot – {sel}
                </h3>
                {tbl_html_76}
                <div class="bl note">{note_html_safe}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )



# -------------------------
# Footer disclaimer
# -------------------------
st.markdown("---")
st.markdown(
    """
    <div style="font-size: 12px; color: gray;">
    © 2025 Markmentum Research LLC. <b>Disclaimer</b>: This content is for informational purposes only. 
    Nothing herein constitutes an offer to sell, a solicitation of an offer to buy, or a recommendation regarding any security, 
    investment vehicle, or strategy. It does not represent legal, tax, accounting, or investment advice by Markmentum Research LLC 
    or its employees. The information is provided without regard to individual objectives or risk parameters and is general, 
    non-tailored, and non-specific. Sources are believed to be reliable, but accuracy and completeness are not guaranteed. 
    Markmentum Research LLC is not responsible for errors, omissions, or losses arising from use of this material. 
    Investments involve risk, and financial markets are subject to fluctuation. Consult your financial professional before 
    making investment decisions.
    </div>
    """,
    unsafe_allow_html=True,
)