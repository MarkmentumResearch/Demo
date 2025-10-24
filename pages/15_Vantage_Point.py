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
st.set_page_config(page_title="Markmentum – Vantage Point", layout="wide")
st.cache_data.clear()


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
    st.switch_page("pages/08_Deep_Dive_Dashboard.py")

def row_spacer(height_px: int = 14):
    st.markdown(f"<div style='height:{height_px}px'></div>", unsafe_allow_html=True)

# -------------------------
# Styling helpers (rely on same CSS classes your other pages use: .card, .tbl, etc.)
# -------------------------
def fmt_num(v, d=2):
    if v is None or pd.isna(v): return ""
    return f"{v:,.{d}f}"

def fmt_pct(v, d=2):
    if v is None or pd.isna(v): return ""
    return f"{v*100:.{d}f}%"

def fmt_int(v):
    if v is None or pd.isna(v): return ""
    try:
        return f"{int(round(v))}"
    except Exception:
        return f"{v}"

def mm_badge_html(v):
    # Simple neutral badge that matches existing style hooks
    if v is None or pd.isna(v): return ""
    val = int(round(v))
    tone = "pos" if val > 0 else "neg" if val < 0 else "neu"
    return f'<span class="mm mm-{tone}">{val}</span>'

def spacer_colgroup(n_name_cols=1, total_cols=9):
    # Add a thin spacer column after "Current" block
    # col order: Name | Sharpe | MM | Tape | (spacer) | %Ret | Sharpe▲ | MM▲
    return """
    <colgroup>
      <col class="col-name">
      <col><col><col>
      <col class="col-spacer">
      <col><col><col>
    </colgroup>
    """.strip()

def to_card_table(df, title):
    html = df.to_html(index=False, classes="tbl", escape=False, border=0)
    html = html.replace('class="dataframe tbl"', 'class="tbl"')
    html = html.replace('<table class="tbl">', f'<table class="tbl">{spacer_colgroup()}', 1)
    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a;">{escape(title)}</h3>
            {html}
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

row_spacer = lambda h=8: st.markdown(f"<div style='height:{h}px'></div>", unsafe_allow_html=True)

# -------------------------
# Timeframe mapping (uses exact column names in signal_box.csv)
# -------------------------
TIMEFRAMES = {
    "Daily":   {"ret": "day_pct_change",
                "shp_d": "Sharpe_Rank_daily_change",
                "mm_d":  "MM_Score_daily_change"},
    "WTD":     {"ret": "week_pct_change",
                "shp_d": "Sharpe_Rank_wtd_change",
                "mm_d":  "MM_Score_wtd_change"},
    "MTD":     {"ret": "month_pct_change",
                "shp_d": "Sharpe_Rank_mtd_change",
                "mm_d":  "MM_Score_mtd_change"},
    "QTD":     {"ret": "quarter_pct_change",
                "shp_d": "Sharpe_Rank_qtd_change",
                "mm_d":  "MM_Score_qtd_change"},
}

CURRENT_COLS = {
    "sharpe": "Sharpe_Rank",
    "mm":     "MM_Score",
    "tape":   "Tape_Bias",
}

BASIC_COLUMNS = [
    "Date","Ticker","Ticker_name","Category","Close",
    CURRENT_COLS["sharpe"], CURRENT_COLS["mm"], CURRENT_COLS["tape"],
    "day_pct_change","week_pct_change","month_pct_change","quarter_pct_change",
    "Sharpe_Rank_daily_change","Sharpe_Rank_wtd_change","Sharpe_Rank_mtd_change","Sharpe_Rank_qtd_change",
    "MM_Score_daily_change","MM_Score_wtd_change","MM_Score_mtd_change","MM_Score_qtd_change",
]

# -------------------------
# Data
# -------------------------
@st.cache_data(show_spinner=False)
def load_signal_box(path="signal_box.csv"):
    df = pd.read_csv(path)
    # keep only known columns if file has extras
    keep = [c for c in BASIC_COLUMNS if c in df.columns]
    return df[keep].copy()

sb = load_signal_box()

# -------------------------
# Title + timeframe selector (same centered style as Morning Compass)
# -------------------------
st.markdown("<h1 style='margin-bottom:2px;'>Vantage Point</h1><div style='color:#667; font-size:13px;'>All signals. One view.</div>", unsafe_allow_html=True)
row_spacer(8)

c1, c2, c3 = st.columns([1, 0.8, 1])
with c2:
    timeframe = st.selectbox("Timeframe", list(TIMEFRAMES.keys()), index=0, label_visibility="collapsed")

tf = TIMEFRAMES[timeframe]

# -------------------------
# Helpers to build the three cards
# -------------------------
def build_current_block(df):
    out = pd.DataFrame({
        "Name":      df["Ticker_name"],
        "Ticker":    df["Ticker"],
        "Category":  df["Category"],
        "Sharpe":    df[CURRENT_COLS["sharpe"]].map(fmt_int),
        "MM":        df[CURRENT_COLS["mm"]].map(mm_badge_html),
        "Tape_Bias": df[CURRENT_COLS["tape"]].fillna(""),
    })
    return out

def build_change_block(df):
    out = pd.DataFrame({
        "% Return":  df[tf["ret"]].map(fmt_pct),
        "Sharpe ▲": df[tf["shp_d"]].map(fmt_int),
        "MM Score ▲": df[tf["mm_d"]].map(fmt_int),
    })
    return out

def build_card_table(df, title):
    if df.empty:
        to_card_table(pd.DataFrame({"Notice":["No data"]}), title)
        return
    cur = build_current_block(df)
    chg = build_change_block(df)
    # Assemble with a thin spacer column
    tbl = pd.concat([cur[["Name","Ticker","Category","Sharpe","MM","Tape_Bias"]],
                     pd.DataFrame({"": [""]*len(cur)}),
                     chg], axis=1)
    # Ticker as blue link to deep-dive (same convention as the rest of app)
    # If you already have a _mk_ticker_link helper elsewhere, swap it in.
    tbl["Ticker"] = tbl["Ticker"].apply(lambda t: f'<a href="?page=deep_dive&t={escape(str(t))}">{escape(str(t))}</a>')
    to_card_table(tbl, title)

# -------------------------
# 1) Macro Orientation (subset, like Performance/Morning Compass)
# -------------------------
# If you maintain a canonical macro list, drop it here; we’ll filter to what's present
macro_pref = [
    # Indices + S&P sectors
    "SPX","NDX","DJI","RUT","XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY",
    # Macro levers
    "GLD","UUP","TLT","BTC=F"
]
macro = sb[sb["Ticker"].isin(macro_pref)].copy()
# preserve preferred order
macro["__ord__"] = macro["Ticker"].apply(lambda t: macro_pref.index(t) if t in macro_pref else 999)
macro = macro.sort_values(["__ord__","Category","Ticker"]).drop(columns="__ord__", errors="ignore")

build_card_table(macro, "Macro Orientation — Current • and Changes by Timeframe")

row_spacer(10)

# -------------------------
# 2) Category Averages
# -------------------------
def cat_agg(df):
    # Current: averages for Sharpe & MM; Tape Bias left blank (not meaningful to average)
    cur = (df.groupby("Category", as_index=False)
             .agg({CURRENT_COLS["sharpe"]:"mean", CURRENT_COLS["mm"]:"mean"})
             .rename(columns={CURRENT_COLS["sharpe"]:"Sharpe",
                              CURRENT_COLS["mm"]:"MM"}))
    cur.insert(0, "Name", cur["Category"])
    cur["Ticker"] = ""
    cur["MM"] = cur["MM"].map(lambda v: "" if pd.isna(v) else mm_badge_html(v))
    cur["Sharpe"] = cur["Sharpe"].map(fmt_int)
    cur["Tape_Bias"] = ""

    # Changes for selected timeframe
    chg = (df.groupby("Category", as_index=False)
             .agg({tf["ret"]:"mean", tf["shp_d"]:"mean", tf["mm_d"]:"mean"})
             .rename(columns={tf["ret"]:"% Return", tf["shp_d"]:"Sharpe ▲", tf["mm_d"]:"MM Score ▲"}))
    chg["% Return"] = chg["% Return"].map(fmt_pct)
    chg["Sharpe ▲"] = chg["Sharpe ▲"].map(fmt_int)
    chg["MM Score ▲"] = chg["MM Score ▲"].map(fmt_int)

    card = pd.concat([
        cur[["Name","Ticker","Category","Sharpe","MM","Tape_Bias"]],
        pd.DataFrame({"": [""]*len(cur)}),
        chg[["% Return","Sharpe ▲","MM Score ▲"]],
    ], axis=1)

    return card.sort_values("Name")

to_card_table(cat_agg(sb), "Category Averages — Current • and Changes by Timeframe")

row_spacer(10)

# -------------------------
# 3) Per-Ticker (by category)
# -------------------------
cat_order = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities","Bonds","Yields","Volatility","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples","Energy","Financials",
    "Health Care","Industrials","Information Technology","Materials","Real Estate","Utilities","MR Discretion"
]
present_cats = [c for c in cat_order if c in sb["Category"].dropna().unique().tolist()]
sel_cat = st.selectbox("Category", present_cats, index=0)

df_cat = sb[sb["Category"].eq(sel_cat)].copy().sort_values(["Ticker_name","Ticker"])
build_card_table(df_cat, f"{sel_cat} — Per Ticker")


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