# 11_Performance_Heatmap.py
# Markmentum — Performance Heatmap (Daily/WTD/MTD/QTD % Change)

from pathlib import Path
import base64
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
from urllib.parse import quote_plus

# ---------- Page ----------
st.cache_data.clear()
st.set_page_config(page_title="Performance Heatmap", layout="wide")



# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

CSV_PATH = DATA_DIR / "ticker_data.csv"   # <-- single source file

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

# --- Clickable Deep Dive helper & router (same UX as Heatmap)
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




def _fmt_pct(x, nd=2):
    try:
        if pd.isna(x): return ""
        return f"{float(x):,.{nd}f}%"
    except Exception:
        return ""

# gradient cell (independent scaling by timeframe; pass per-column vmax)
def _divergent_tint_html(val: float, vmax: float) -> str:
    if val is None or pd.isna(val) or vmax is None or vmax <= 0:
        return ""
    # scale 0..1 capped, keep near-zero very light
    s = min(abs(float(val)) / float(vmax), 1.0)
    alpha = 0.12 + 0.28 * s  # 0.12 → 0.40 opacity
    if val > 0:
        bg = f"rgba(16,185,129,{alpha:.3f})"   # green
    elif val < 0:
        bg = f"rgba(239,68,68,{alpha:.3f})"   # red
    else:
        bg = "transparent"
    label = _fmt_pct(val, 2)
    return f'<span style="display:block; background:{bg}; padding:0 4px; border-radius:2px; text-align:right;">{label}</span>'

# ---------- Load source ----------
@st.cache_data(show_spinner=False)
def load_perf_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p)
    # enforce expected schema
    need = [
        "Ticker","Ticker_name","Category","Date","Close",
        "day_pct_change","week_pct_change","month_pct_change","quarter_pct_change"
    ]
    if not all(c in df.columns for c in need):
        return pd.DataFrame()
    # numeric hygiene
    for c in ["day_pct_change","week_pct_change","month_pct_change","quarter_pct_change","Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # multiply by 100 to convert to percentage space (locked requirement)
    for c in ["day_pct_change","week_pct_change","month_pct_change","quarter_pct_change"]:
        df[c] = df[c] * 100.0
    return df


# ---------- Shared CSS (compass-style card + 40ch Name) ----------
st.markdown("""
<style>
.card-wrap { display:flex; justify-content:center; }

/* Base card width (smaller than before) */
.card{
  border:1px solid #cfcfcf; border-radius:8px; background:#fff;
  padding:12px 12px 10px 12px; width:100%;
  max-width:700px; /* was 1320px */
}

/* Optional even narrower variants */
.card.narrow { max-width:900px; }
.card.xnarrow { max-width:820px; }

/* Keep cards full-bleed on small screens */
@media (max-width:1100px){
  .card, .card.narrow, .card.xnarrow { max-width:100%; }
}

/* table base */
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td {
  border:1px solid #d9d9d9; padding:6px 8px; font-size:13px;
  overflow:hidden; text-overflow:ellipsis;
}
/* headings: name left; numeric headings centered */
.tbl th { background:#f2f2f2; font-weight:700; color:#1a1a1a; text-align:left; }
.tbl th:nth-child(n+2) { text-align:center; }
/* cells: name left-wrap; numeric right */
.tbl td:nth-child(n+2) { text-align:right; white-space:nowrap; }

/* Column width helpers (shrink Name on both cards) */
.tbl col.col-name        { width:20ch; min-width:20ch; max-width:20ch; }  /* Card 1 Name (smaller) */
.tbl col.col-name-wide   { width:20ch; min-width:20ch; max-width:20ch; }  /* Card 2 Name (smaller) */
.tbl col.col-ticker-nar  { width:7ch; }                                    /* Card 2 Ticker */
.tbl col.col-num-sm      { width:6ch; }                                     /* Card 1 numerics */
.tbl col.col-num-lg      { width:6ch; }                                    /* Card 2 numerics */

/* allow wrapping for Name */
.tbl th:nth-child(1), .tbl td:nth-child(1) { white-space:normal; overflow:visible; text-overflow:clip; }

/* smaller note text */
.subnote { border-top:1px solid #e5e5e5; margin-top:8px; padding-top:10px; font-size:11px; color:#6c757d; }

/* Center the Ticker column ONLY in Card 2 */
.detail .tbl td:nth-child(2), .detail .tbl th:nth-child(2) { text-align:center; }
.vspace-16 { height:16px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* …existing styles… */
.card h3 { margin:0 0 4px 0; font-size:16px; font-weight:700; color:#1a1a1a; text-align:center; }
.card .subtitle { margin:0 0 8px 0; font-size:14px; font-weight:500; color:#6b7280; text-align:center; }
/* …existing styles… */
</style>
""", unsafe_allow_html=True)



perf = load_perf_csv(CSV_PATH)
if perf.empty:
    st.info("`ticker_data.csv` missing or columns incomplete.")

 
g = perf.groupby("Category", dropna=True, as_index=False).agg(
    Daily=("day_pct_change","mean"),
    WTD=("week_pct_change","mean"),
    MTD=("month_pct_change","mean"),
    QTD=("quarter_pct_change","mean"),
).sort_values("Category", kind="stable")

# ---- Page title (under logo) pulled from source Date ----
date_str = ""
if not perf.empty and "Date" in perf.columns:
    asof = pd.to_datetime(perf["Date"], errors="coerce").max()
    if pd.notna(asof):
        date_str = f"{asof.month}/{asof.day}/{asof.year}"

st.markdown(
    f"""
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:18px; font-weight:600; color:#1a1a1a;">
        Performance – {date_str}
    </div>
    """,
    unsafe_allow_html=True,
)

# ===== Card 1 — Performance – Macro Orientation (same layout as Card 2) =====

# Use the same macro list you show on Compass (only those that exist in the file will render)
macro_list = [
    "SPX","NDX","DJI","RUT",
    "XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY",
    "GLD","UUP","TLT","BTC=F"
]

# keep only the latest row per ticker (in case CSV has multiple dates)
if not perf.empty:
    perf["_dt"] = pd.to_datetime(perf["Date"], errors="coerce")
    latest = (
        perf.sort_values(["Ticker", "_dt"], ascending=[True, False])
            .drop_duplicates(subset=["Ticker"], keep="first")
    )
else:
    latest = perf.copy()

m = latest[latest["Ticker"].isin(macro_list)].copy()
# preserve the macro_list order
m["__ord__"] = m["Ticker"].map({t:i for i, t in enumerate(macro_list)})
m = m.sort_values(["__ord__"], kind="stable")

# build ticker links
m["Ticker_link"] = m["Ticker"].map(_mk_ticker_link)

# independent scaling by timeframe **within just these macro tickers**
vmaxM = {
    "Daily":  m["day_pct_change"].abs().max(skipna=True) or 0.0,
    "WTD":    m["week_pct_change"].abs().max(skipna=True) or 0.0,
    "MTD":    m["month_pct_change"].abs().max(skipna=True) or 0.0,
    "QTD":    m["quarter_pct_change"].abs().max(skipna=True) or 0.0,
}

m_render = pd.DataFrame({
    "Name":   m["Ticker_name"],
    "Ticker": m["Ticker_link"],
    "Daily":  [ _divergent_tint_html(v, vmaxM["Daily"]) for v in m["day_pct_change"] ],
    "WTD":    [ _divergent_tint_html(v, vmaxM["WTD"])   for v in m["week_pct_change"] ],
    "MTD":    [ _divergent_tint_html(v, vmaxM["MTD"])   for v in m["month_pct_change"] ],
    "QTD":    [ _divergent_tint_html(v, vmaxM["QTD"])   for v in m["quarter_pct_change"] ],
})

html_macro = m_render.to_html(index=False, classes="tbl", escape=False, border=0)
html_macro = html_macro.replace('class="dataframe tbl"', 'class="tbl"')

# Use the SAME column widths as Card 2 (Name wider, Ticker narrow, numerics roomy)
colgroup_macro = """
<colgroup>
  <col class="col-name-wide">  <!-- Name -->
  <col class="col-ticker-nar"> <!-- Ticker -->
  <col class="col-num-lg">     <!-- Daily -->
  <col class="col-num-lg">     <!-- WTD -->
  <col class="col-num-lg">     <!-- MTD -->
  <col class="col-num-lg">     <!-- QTD -->
</colgroup>
""".strip()
html_macro = html_macro.replace('<table class="tbl">', f'<table class="tbl">{colgroup_macro}', 1)

st.markdown(
    f"""
    <div class="card-wrap">
      <div class="card detail">
             <h3 style="margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a;text-align:center;">
              Performance — Macro Orientation</h3>
        <div class="subtitle">Avg % change by ticker and timeframe</div>
        {html_macro}
        <div class="subnote">Ticker links open the Deep Dive Dashboard. Each timeframe’s shading is scaled independently.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# little breathing room before the next card
st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)




# =========================================================
# Card 2 — Category averages (Name, Daily, WTD, MTD, QTD)
# =========================================================

preferred_order = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities",
    "Bonds","Yields","Volatility","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples",
    "Energy","Financials","Health Care","Industrials","Information Technology",
    "Materials","Real Estate","Utilities","MR Discretion"
]
order_map = {name: i for i, name in enumerate(preferred_order)}
g["__ord__"] = g["Category"].map(order_map)
g = g.sort_values(["__ord__", "Category"], kind="stable")
g = g.drop(columns="__ord__")

# independent scaling by timeframe
vmax = {
        "Daily":  g["Daily"].abs().max(skipna=True) or 0.0,
        "WTD":    g["WTD"].abs().max(skipna=True) or 0.0,
        "MTD":    g["MTD"].abs().max(skipna=True) or 0.0,
        "QTD":    g["QTD"].abs().max(skipna=True) or 0.0,
    }

g_render = pd.DataFrame({
        "Name": g["Category"],
        "Daily": [ _divergent_tint_html(v, vmax["Daily"]) for v in g["Daily"] ],
        "WTD":   [ _divergent_tint_html(v, vmax["WTD"])   for v in g["WTD"]   ],
        "MTD":   [ _divergent_tint_html(v, vmax["MTD"])   for v in g["MTD"]   ],
        "QTD":   [ _divergent_tint_html(v, vmax["QTD"])   for v in g["QTD"]   ],
    })

html_cat = g_render.to_html(index=False, classes="tbl", escape=False, border=0)
html_cat = html_cat.replace('class="dataframe tbl"', 'class="tbl"')
colgroup = """
<colgroup>
  <col class="col-name">   <!-- Name (40ch) -->
  <col class="col-num-sm"> <!-- Daily -->
  <col class="col-num-sm"> <!-- WTD -->
  <col class="col-num-sm"> <!-- MTD -->
  <col class="col-num-sm"> <!-- QTD -->
</colgroup>
""".strip()
html_cat = html_cat.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3 style="margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a;text-align:center;">
              Performance — Category Averages</h3>
              <div class="subtitle">Avg % change by each category and timeframe</div>
            {html_cat}
            <div class="subnote">Each column uses its own red/green gradient scale.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)

# ===== Category Averages — Heatmap (single matrix like prior page) =====
# Long form from the grouped averages 'g'
glong = g.melt(
    id_vars=["Category"],
    value_vars=["Daily", "WTD", "MTD", "QTD"],
    var_name="Timeframe",
    value_name="Pct",
)

# Keep preferred row order
preferred_order = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities",
    "Bonds","Yields","Volatility","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples",
    "Energy","Financials","Health Care","Industrials","Information Technology",
    "Materials","Real Estate","Utilities","MR Discretion"
]
glong["Category"] = pd.Categorical(glong["Category"], categories=preferred_order, ordered=True)

vmax = float(glong["Pct"].abs().max())

# Single grid heatmap (shared, centered legend at bottom)
base_hm = (
    alt.Chart(glong)
    .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
    .encode(
        x=alt.X(
            "Timeframe:N",
            sort=["Daily", "WTD", "MTD", "QTD"],
            axis=alt.Axis(orient="top",title=None, labelFontSize=12, labelAngle=0,labelFlush=False,labelPadding=6)
        ),
        y=alt.Y(
            "Category:N",
            sort=list(glong["Category"].cat.categories),
            axis=alt.Axis(title=None, labelFlush=False,labelFontSize=12, labelLimit=240)
        ),
        color=alt.Color(
            "Pct:Q",
            # diverging blue↔orange with 0 as midpoint (matches your prior style)
            scale=alt.Scale(scheme="blueorange",domain=[-vmax, vmax], domainMid=0),
            legend=alt.Legend(orient="bottom", labelExpr="''",title="Avg % Change (per timeframe)")
        ),
        tooltip=[
            alt.Tooltip("Category:N"),
            alt.Tooltip("Timeframe:N"),
            alt.Tooltip("Pct:Q", format=".2f", title="%")
        ],
    )
    .properties(width=450, height=24 * len(preferred_order))
    .configure_view(strokeWidth=0)
)

st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:18px; font-weight:600; color:#1a1a1a;">
        Performance Heatmap – Avg % Change
    </div>
    """,
    unsafe_allow_html=True,
)

left, center, right = st.columns([1, 1, 1])
with center:
    st.altair_chart(base_hm, use_container_width=False)

# =========================================================
# Card 3 — Category selector → per-ticker rows
# =========================================================
preferred = [
        "Sector & Style ETFs","Indices","Futures","Currencies","Commodities",
        "Bonds","Yields","Volatility","Foreign",
        "Communication Services","Consumer Discretionary","Consumer Staples",
        "Energy","Financials","Health Care","Industrials","Information Technology",
        "Materials","Real Estate","Utilities","MR Discretion"
    ]
custom_order = preferred
cats = [c for c in custom_order if c in perf["Category"].dropna().unique().tolist()]
default_cat = "Sector & Style ETFs" if "Sector & Style ETFs" in cats else (cats[0] if cats else None)

_, csel, _ = st.columns([1, 1, 1])
with csel:
        sel = st.selectbox("Category", cats, index=(cats.index(default_cat) if default_cat else 0))

d = perf.loc[perf["Category"] == sel].copy()
d["Ticker_link"] = d["Ticker"].map(_mk_ticker_link)

    # independent scaling by timeframe **within the selected category**
vmax2 = {
        "Daily":  d["day_pct_change"].abs().max(skipna=True) or 0.0,
        "WTD":    d["week_pct_change"].abs().max(skipna=True) or 0.0,
        "MTD":    d["month_pct_change"].abs().max(skipna=True) or 0.0,
        "QTD":    d["quarter_pct_change"].abs().max(skipna=True) or 0.0,
    }

d_render = pd.DataFrame({
        "Name":   d["Ticker_name"],
        "Ticker": d["Ticker_link"],
        "Daily":  [ _divergent_tint_html(v, vmax2["Daily"]) for v in d["day_pct_change"] ],
        "WTD":    [ _divergent_tint_html(v, vmax2["WTD"])   for v in d["week_pct_change"] ],
        "MTD":    [ _divergent_tint_html(v, vmax2["MTD"])   for v in d["month_pct_change"] ],
        "QTD":    [ _divergent_tint_html(v, vmax2["QTD"])   for v in d["quarter_pct_change"] ],
    })

html_detail = d_render.to_html(index=False, classes="tbl", escape=False, border=0)
html_detail = html_detail.replace('class="dataframe tbl"', 'class="tbl"')
colgroup2 = """
<colgroup>
  <col class="col-name-wide">  <!-- Name wider (48ch) -->
  <col class="col-ticker-nar"> <!-- Ticker narrower -->
  <col class="col-num-lg">     <!-- Daily bigger -->
  <col class="col-num-lg">     <!-- WTD bigger -->
  <col class="col-num-lg">     <!-- MTD bigger -->
  <col class="col-num-lg">     <!-- QTD bigger -->
</colgroup>
""".strip()
html_detail = html_detail.replace('<table class="tbl">', f'<table class="tbl">{colgroup2}', 1)

st.markdown(
    f"""
    <div class="card-wrap">
      <div class="card detail">  <!-- add 'detail' here -->
        <h3 style="margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a;text-align:center;">
          {sel} — Per Ticker Performance</h3>
          <div class="subtitle">% change by ticker and timeframe</div>
        {html_detail}
        <div class="subnote">Ticker links open the Deep Dive Dashboard. Each timeframe’s shading is scaled independently.</div>
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