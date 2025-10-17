# 13_Trends.py
# Markmentum — Trends & Changes (ST / MT / LT)

from pathlib import Path
import base64
import pandas as pd
import numpy as np
import streamlit as st
from urllib.parse import quote_plus

# ---------- Page ----------
st.cache_data.clear()
st.set_page_config(page_title="Trends & Changes", layout="wide")

# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

CSV_PATH = DATA_DIR / "qry_graph_data_88.csv"   # <-- single source file for this page

# -------------------------
# Header: logo centered
# -------------------------
def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

if LOGO_PATH.exists():
    st.markdown(
        f"""
        <div style="text-align:center; margin: 8px 0 16px;">
            <img src="data:image/png;base64,{_image_b64(LOGO_PATH)}" width="440">
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Clickable Deep Dive helper & router (same UX as Performance page)
def _mk_ticker_link(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    return (
        f'<a href="?page=Deep%20Dive&ticker={quote_plus(t)}" '
        f'target="_self" rel="noopener" '
        f'style="text-decoration:none; font-weight:600;">{t}</a>'
    )

qp = st.query_params
dest = (qp.get("page") or "").strip().lower()
if dest.replace("%20", " ") == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    st.switch_page("pages/13_Deep_Dive_Dashboard.py")

# -------------------------
# Formatting helpers
# -------------------------
def fmt_pct_1(x):
    try:
        if pd.isna(x):
            return ""
        # Treat source as decimal returns (e.g., 0.012 -> 1.2%)
        return f"{float(x)*100:,.1f}%"
    except Exception:
        return ""

def tint_cell(val, cap=0.03, neutral=0.0005):
    """
    val: decimal (e.g., 0.012 = 1.2%)
    cap: magnitude where tint reaches full strength (default 3%)
    neutral: +/- band rendered as no tint (default 0.05%)
    """
    if val is None or pd.isna(val):
        return ""
    try:
        v = float(val)
    except Exception:
        return ""

    # Neutral band (very small values look untinted)
    if -neutral <= v <= neutral:
        bg = "transparent"
    else:
        # Scale opacity by magnitude, capped
        strength = min(abs(v) / cap, 1.0)     # 0..1
        alpha = 0.15 + 0.35 * strength        # 0.15..0.50
        if v > 0:
            bg = f"rgba(16,185,129,{alpha:.2f})"   # green
        else:
            bg = f"rgba(239,68,68,{alpha:.2f})"    # red

    return (
        f'<span style="display:block; background:{bg}; '
        f'padding:0 6px; border-radius:3px; text-align:right;">{v*100:,.1f}%</span>'
    )

# -------------------------
# Load source
# -------------------------
@st.cache_data(show_spinner=False)
def load_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    required = [
        "Date","Ticker","Ticker_name","Category",
        "st_trend","mt_trend","lt_trend",
        "st_trend_change","mt_trend_change","lt_trend_change",
    ]
    if not all(c in df.columns for c in required):
        return pd.DataFrame()

    # numeric hygiene
    for c in ["st_trend","mt_trend","lt_trend",
              "st_trend_change","mt_trend_change","lt_trend_change"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

df = load_csv(CSV_PATH)

# ---- Page title (under logo) pulled from source Date ----
date_str = ""
if not df.empty and "Date" in df.columns:
    asof = pd.to_datetime(df["Date"], errors="coerce").max()
    if pd.notna(asof):
        date_str = f"{asof.month}/{asof.day}/{asof.year}"

st.markdown(
    f"""
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:18px; font-weight:600; color:#1a1a1a;">
        Trends – {date_str}
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Shared CSS (compass-style card) ----------
st.markdown("""
<style>
.card-wrap { display:flex; justify-content:center; }
.card{
  border:1px solid #cfcfcf; border-radius:8px; background:#fff;
  padding:12px; width:100%; max-width:1200px;
}
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td {
  border:1px solid #d9d9d9; padding:6px 8px; font-size:13px;
  overflow:hidden; text-overflow:ellipsis;
}
.tbl th { background:#f2f2f2; font-weight:700; color:#1a1a1a; text-align:left; }
.tbl th:nth-child(n+2) { text-align:center; }
.tbl td:nth-child(n+2) { text-align:right; white-space:nowrap; }

/* Column width helpers */
.tbl col.col-name   { width:28ch; min-width:28ch; max-width:28ch; }
.tbl col.col-ticker { width:8ch; }
.tbl col.col-num    { width:8ch; }

/* allow wrapping for Name */
.tbl th:nth-child(1), .tbl td:nth-child(1) { white-space:normal; overflow:visible; text-overflow:clip; }

.subnote { border-top:1px solid #e5e5e5; margin-top:8px; padding-top:10px; font-size:11px; color:#6c757d; }
.vspace-16 { height:16px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# Card 1 — Macro Orientation (Trends & Changes)
# =========================================================

macro_list = [
    "SPX","NDX","DJI","RUT",
    "XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY",
    "GLD","UUP","TLT","BTC=F"
]

if df.empty:
    st.info("`qry_graph_data_88.csv` missing or columns incomplete.")
else:
    # keep only the latest row per ticker (in case CSV has multiple dates)
    df["_dt"] = pd.to_datetime(df["Date"], errors="coerce")
    latest = (
        df.sort_values(["Ticker", "_dt"], ascending=[True, False])
          .drop_duplicates(subset=["Ticker"], keep="first")
    )

    m = latest[latest["Ticker"].isin(macro_list)].copy()
    m["__ord__"] = m["Ticker"].map({t:i for i, t in enumerate(macro_list)})
    m = m.sort_values("__ord__", kind="stable")

    m["Ticker_link"] = m["Ticker"].map(_mk_ticker_link)

    macro_tbl = pd.DataFrame({
        "Name":        m["Ticker_name"],
        "Ticker":      m["Ticker_link"],
        "ST":          [tint_cell(v) for v in m["st_trend"]],
        "MT":          [tint_cell(v) for v in m["mt_trend"]],
        "LT":          [tint_cell(v) for v in m["lt_trend"]],
        "ST Change":   [tint_cell(v) for v in m["st_trend_change"]],
        "MT Change":   [tint_cell(v) for v in m["mt_trend_change"]],
        "LT Change":   [tint_cell(v) for v in m["lt_trend_change"]],
    })

    html_macro = macro_tbl.to_html(index=False, classes="tbl", escape=False, border=0)
    html_macro = html_macro.replace('class="dataframe tbl"', 'class="tbl"')
    colgroup_macro = """
    <colgroup>
      <col class="col-name">   <!-- Name -->
      <col class="col-ticker"> <!-- Ticker -->
      <col class="col-num">    <!-- ST -->
      <col class="col-num">    <!-- MT -->
      <col class="col-num">    <!-- LT -->
      <col class="col-num">    <!-- ST Chg -->
      <col class="col-num">    <!-- MT Chg -->
      <col class="col-num">    <!-- LT Chg -->
    </colgroup>
    """.strip()
    html_macro = html_macro.replace('<table class="tbl">', f'<table class="tbl">{colgroup_macro}', 1)

    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a; text-align:center;">
              Macro Orientation — Trends by Timeframe & Changes
            </h3>
            {html_macro}
            <div class="subnote">Ticker links open the Deep Dive Dashboard. Green = positive; Red = negative.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# little breathing room
st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)

# =========================================================
# Card 2 — Category Averages (Trends & Changes)
# =========================================================
if not df.empty:
    g = df.groupby("Category", dropna=True, as_index=False).agg(
        ST=("st_trend","mean"),
        MT=("mt_trend","mean"),
        LT=("lt_trend","mean"),
        ST_Change=("st_trend_change","mean"),
        MT_Change=("mt_trend_change","mean"),
        LT_Change=("lt_trend_change","mean"),
    )

    # Preferred order (same list you use on other pages)
    preferred_order = [
        "Sector & Style ETFs","Indices","Futures","Currencies","Commodities",
        "Bonds","Yields","Volatility","Foreign",
        "Communication Services","Consumer Discretionary","Consumer Staples",
        "Energy","Financials","Health Care","Industrials","Information Technology",
        "Materials","Real Estate","Utilities","MR Discretion"
    ]
    order_map = {name: i for i, name in enumerate(preferred_order)}
    g["__ord__"] = g["Category"].map(order_map)
    g = g.sort_values(["__ord__", "Category"], kind="stable").drop(columns="__ord__")

    cat_tbl = pd.DataFrame({
        "Name":       g["Category"],
        "ST":         [tint_cell(v) for v in g["ST"]],
        "MT":         [tint_cell(v) for v in g["MT"]],
        "LT":         [tint_cell(v) for v in g["LT"]],
        "ST Change":  [tint_cell(v) for v in g["ST_Change"]],
        "MT Change":  [tint_cell(v) for v in g["MT_Change"]],
        "LT Change":  [tint_cell(v) for v in g["LT_Change"]],
    })

    html_cat = cat_tbl.to_html(index=False, classes="tbl", escape=False, border=0)
    html_cat = html_cat.replace('class="dataframe tbl"', 'class="tbl"')
    colgroup_cat = """
    <colgroup>
      <col class="col-name">   <!-- Name -->
      <col class="col-num">    <!-- ST -->
      <col class="col-num">    <!-- MT -->
      <col class="col-num">    <!-- LT -->
      <col class="col-num">    <!-- ST Chg -->
      <col class="col-num">    <!-- MT Chg -->
      <col class="col-num">    <!-- LT Chg -->
    </colgroup>
    """.strip()
    html_cat = html_cat.replace('<table class="tbl">', f'<table class="tbl">{colgroup_cat}', 1)

    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a; text-align:center;">
              Category Averages — Trends by Timeframe & Changes
            </h3>
            {html_cat}
            <div class="subnote">Averages by category.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# little breathing room
st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)

# =========================================================
# Card 3 — Per-Category Tickers (selector)
# =========================================================
if not df.empty:
    # ordered category dropdown
    cats_present = [c for c in preferred_order if c in df["Category"].dropna().unique().tolist()]
    default_cat = "Sector & Style ETFs" if "Sector & Style ETFs" in cats_present else (cats_present[0] if cats_present else None)
    _, csel, _ = st.columns([1, 1, 1])
    with csel:
        sel = st.selectbox("Category", cats_present, index=(cats_present.index(default_cat) if default_cat else 0))

    d = df.loc[df["Category"] == sel].copy()
    # latest per ticker (if multiple dates)
    d = (
        d.sort_values(["Ticker", "_dt"], ascending=[True, False])
         .drop_duplicates(subset=["Ticker"], keep="first")
         if "_dt" in d.columns else d
    )
    d["Ticker_link"] = d["Ticker"].map(_mk_ticker_link)

    per_tbl = pd.DataFrame({
        "Name":        d["Ticker_name"],
        "Ticker":      d["Ticker_link"],
        "ST":          [tint_cell(v) for v in d["st_trend"]],
        "MT":          [tint_cell(v) for v in d["mt_trend"]],
        "LT":          [tint_cell(v) for v in d["lt_trend"]],
        "ST Change":   [tint_cell(v) for v in d["st_trend_change"]],
        "MT Change":   [tint_cell(v) for v in d["mt_trend_change"]],
        "LT Change":   [tint_cell(v) for v in d["lt_trend_change"]],
    })

    html_per = per_tbl.to_html(index=False, classes="tbl", escape=False, border=0)
    html_per = html_per.replace('class="dataframe tbl"', 'class="tbl"')
    colgroup_per = """
    <colgroup>
      <col class="col-name">   <!-- Name -->
      <col class="col-ticker"> <!-- Ticker -->
      <col class="col-num">    <!-- ST -->
      <col class="col-num">    <!-- MT -->
      <col class="col-num">    <!-- LT -->
      <col class="col-num">    <!-- ST Chg -->
      <col class="col-num">    <!-- MT Chg -->
      <col class="col-num">    <!-- LT Chg -->
    </colgroup>
    """.strip()
    html_per = html_per.replace('<table class="tbl">', f'<table class="tbl">{colgroup_per}', 1)

    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a; text-align:center;">
              {sel} — Per Ticker Trends by Timeframe & Changes
            </h3>
            {html_per}
            <div class="subnote">Green = positive; Red = negative.</div>
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