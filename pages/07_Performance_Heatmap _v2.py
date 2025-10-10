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

def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -------------------------
# Global CSS (same as Heatmap page)
# -------------------------
st.markdown("""
<style>
/* ============== Page & Shared style ============== */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div { width:95vw; max-width:2100px; margin-left:auto; margin-right:auto; }

div[data-testid="stDecoration"]{ display:none !important; }
div[data-testid="stVerticalBlockBorderWrapper"]{ border:none !important; background:transparent !important; box-shadow:none !important; }
div[data-testid="stVerticalBlockBorderWrapper"] > div[aria-hidden="true"]{ display:none !important; }

html, body, [class^="css"], .stMarkdown, .stText, .stDataFrame, .stTable, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.h-title { text-align:center; font-size:20px; font-weight:700; color:#1a1a1a; margin:4px 0 8px; }
.h-sub   { text-align:center; font-size:12px; color:#666;     margin:2px 0 10px; }
div[data-baseweb="select"] { max-width:36ch !important; }

/* A) Global heatmap centering row */
#hm-center + div[data-testid="stHorizontalBlock"]{
  display:flex !important; justify-content:center !important; gap:0 !important;
}
#hm-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
#hm-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3){
  flex:1 1 0 !important; min-width:0 !important;
}
#hm-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2){
  flex:0 0 auto !important; min-width:0 !important;
}

/* B) Bottom 4 charts grid: 4-up desktop, 2×2 laptops/MBA, 1-up small screens */
div[data-testid="stHorizontalBlock"]:has(#grid4) { display:flex; flex-wrap:wrap; gap:24px; }
div[data-testid="stHorizontalBlock"]:has(#grid4) > div[data-testid="column"]{ flex:1 1 22%; min-width:280px; }
@media (max-width:1499.98px){
  div[data-testid="stHorizontalBlock"]:has(#grid4) > div[data-testid="column"]{ flex:1 1 48%; }
}
@media (max-width:799.98px){
  div[data-testid="stHorizontalBlock"]:has(#grid4) > div[data-testid="column"]{ flex:1 1 100%; }
}

/* C) Altair/Vega sizing+centering backstop */
div[data-testid="stAltairChart"], div[data-testid="stVegaLiteChart"]{
  display:grid !important; place-items:center !important; width:100%;
}
div[data-testid="stAltairChart"] .vega-embed, div[data-testid="stVegaLiteChart"] .vega-embed{
  width:auto !important; max-width:100% !important; margin:0 auto !important; display:inline-block !important;
}
</style>
""", unsafe_allow_html=True)

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

# -------------------------
# Load & prep
# -------------------------
@st.cache_data(show_spinner=False)
def load_perf(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=[
            "Ticker","Ticker_name","Category",
            "day_pct_change","week_pct_change","month_pct_change","quarter_pct_change"
        ])
    df = pd.read_csv(path)

    # Normalize basics
    for c in ("Ticker","Ticker_name","Category"):
        if c in df.columns: df[c] = df[c].astype(str).str.strip()
    if "Ticker" in df.columns: df["Ticker"] = df["Ticker"].str.upper()

    # Ensure numeric; multiply by 100 (input assumed in decimal)
    num_cols = ["day_pct_change","week_pct_change","month_pct_change","quarter_pct_change"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce") * 100.0

    return df

df = load_perf(CSV_PATH)
if df.empty:
    st.warning("Missing or empty data/ticker_data.csv.")
    st.stop()

# --- Derive "as of" date from any date-like column in the CSV
date_col = next((c for c in ["date","Date","as_of","asOf","asof_date","AsOf","As_of"] if c in df.columns), None)
as_of_str = ""
if date_col:
    as_of = pd.to_datetime(df[date_col], errors="coerce").max()
    if pd.notna(as_of):
        # Month/Day/Year without leading zeros
        as_of_str = f"{as_of.month}/{as_of.day}/{as_of.year}"

# --- robust per-timeframe vmax (winsorized)
def _robust_vmax(s: pd.Series, q: float = 0.98, floor: float = 1.0, step: float = 1.0) -> float:
    if s is None or len(s) == 0:
        return floor
    vmax = float(np.quantile(np.abs(pd.to_numeric(s, errors="coerce").dropna()), q))
    # optional neat rounding
    return max(floor, np.ceil(vmax / step) * step)

# --- Universe-wide robust vmax per timeframe (all tickers)
_univ_vmax = {}
if "day_pct_change" in df.columns:
    _univ_vmax["Daily"] = _robust_vmax(df["day_pct_change"])
if "week_pct_change" in df.columns:
    _univ_vmax["WTD"]   = _robust_vmax(df["week_pct_change"])
if "month_pct_change" in df.columns:
    _univ_vmax["MTD"]   = _robust_vmax(df["month_pct_change"])
if "quarter_pct_change" in df.columns:
    _univ_vmax["QTD"]   = _robust_vmax(df["quarter_pct_change"])

# -------------------------
# Title (now includes as-of date when available)
# -------------------------
st.markdown(
    f"""
    <div style="
        text-align:center;
        font-size:20px;
        font-weight:600;
        color:#233;
        margin-top:8px;
        margin-bottom:12px;">
        Performance Heatmap{f" – {as_of_str}" if as_of_str else ""}
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# Global Heatmap — Avg % Change (Category × Timeframe)
# =========================
parts = []
if "day_pct_change" in df.columns:
    parts.append(df[["Category","day_pct_change"]].rename(columns={"day_pct_change":"delta"}).assign(Timeframe="Daily"))
if "week_pct_change" in df.columns:
    parts.append(df[["Category","week_pct_change"]].rename(columns={"week_pct_change":"delta"}).assign(Timeframe="WTD"))
if "month_pct_change" in df.columns:
    parts.append(df[["Category","month_pct_change"]].rename(columns={"month_pct_change":"delta"}).assign(Timeframe="MTD"))
if "quarter_pct_change" in df.columns:
    parts.append(df[["Category","quarter_pct_change"]].rename(columns={"quarter_pct_change":"delta"}).assign(Timeframe="QTD"))

hm = pd.concat(parts, ignore_index=True).dropna(subset=["Category","delta"])

agg = (
    hm.groupby(["Category","Timeframe"], as_index=False)
      .agg(avg_delta=("delta","mean"), n=("delta","size"))
)

# Preferred ordering (filtered to present ones)
preferred = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities",
    "Bonds","Yields","Foreign","Communication Services","Consumer Discretionary",
    "Consumer Staples","Energy","Financials","Health Care","Industrials",
    "Information Technology","Materials","Real Estate","Utilities","MR Discretion"
]
present = list(agg["Category"].unique())
cat_order = [c for c in preferred if c in present] + [c for c in present if c not in preferred]
tf_order  = ["Daily","WTD","MTD","QTD"]

# --- Per-timeframe robust vmax across categories
_tf_key = {"Daily":"Daily","WTD":"WTD","MTD":"MTD","QTD":"QTD"}
vmax_by_tf = {
    tf: _robust_vmax(agg.loc[agg["Timeframe"]==tf, "avg_delta"], q=0.98, floor=1.0, step=1.0)
    for tf in _tf_key.values()
}

# --- Normalize within each timeframe (independent color for each column)
agg_norm = agg.assign(
    norm=lambda d: d.apply(lambda r: np.clip(
        (r["avg_delta"] / (vmax_by_tf.get(r["Timeframe"], 1.0) or 1.0)), -1, 1
    ), axis=1)
)

row_h = 26
chart_h = max(360, row_h * len(cat_order) + 24)
chart_w = 625
legend_w = 120

heat = (
    alt.Chart(agg_norm)
    .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
    .encode(
        x=alt.X("Timeframe:N", sort=tf_order,
                axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8,
                              labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
        y=alt.Y("Category:N", sort=cat_order,
                axis=alt.Axis(title=None, labelLimit=460, orient="left", labelPadding=6,
                              labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
        # color by normalized value so each timeframe is independent
        color=alt.Color("norm:Q",
                        scale=alt.Scale(scheme="blueorange", domain=[-1, 0, 1]),
                        legend=alt.Legend(orient="bottom", title="Avg % Change (per timeframe)",
                                          titleColor="#1a1a1a", labelColor="#1a1a1a",
                                          gradientLength=360, labelLimit=80,labelExpr="''")),
        tooltip=[alt.Tooltip("Category:N"),
                 alt.Tooltip("Timeframe:N"),
                 alt.Tooltip("avg_delta:Q", title="Avg %", format=",.2f"),
                 alt.Tooltip("n:Q", title="Count")]
    )
    .properties(width=chart_w, height=chart_h,
                padding={"left": legend_w, "right": 0, "top": 6, "bottom": 0})
    .configure_view(strokeOpacity=0)
)

st.markdown('<div id="hm-center"></div>', unsafe_allow_html=True)
pad_l, center_col, pad_r = st.columns([1,3,1])
with center_col:
    with st.container(border=True):
        st.markdown(
            '<div style="text-align:center;">'
            '<h3 style="margin:0;">Performance Heatmap – Avg % Changes</h3>'
            '<div class="small" style="margin-top:4px;">'
            'Average % Δ across tickers in each category and timeframe'
            '</div></div>',
            unsafe_allow_html=True,
        )
        _l, _c, _r = st.columns([1,7,1])
        with _c:
            st.altair_chart(heat, use_container_width=False)

col1, col2, col3 = st.columns([1.5, 3, .5])
with col2:
    st.caption("Note: Each timeframe column uses its own color scale derived from that timeframe’s dispersion (independent per timeframe)")



# -------------------------
# Controls
# -------------------------
custom_order = preferred
all_cats = [c for c in custom_order if c in df["Category"].dropna().unique().tolist()]
default_cat = "Sector & Style ETFs" if "Sector & Style ETFs" in all_cats else (all_cats[0] if all_cats else None)

c_blank, c_sel, c_blank2 = st.columns([2.5,3,.3])
with c_sel:
    sel = st.selectbox("Category", all_cats, index=(all_cats.index(default_cat) if default_cat else 0))

# Always show per-ticker matrix (mirrors your latest UX)
show_ticker_hm = True

# =========================
# Per-Ticker Heatmap (selected category)
# =========================
if show_ticker_hm and sel:
    tm_parts = []
    if "day_pct_change" in df.columns:
        tm_parts.append(df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","day_pct_change"]]
                          .rename(columns={"day_pct_change":"delta"}).assign(Timeframe="Daily"))
    if "week_pct_change" in df.columns:
        tm_parts.append(df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","week_pct_change"]]
                          .rename(columns={"week_pct_change":"delta"}).assign(Timeframe="WTD"))
    if "month_pct_change" in df.columns:
        tm_parts.append(df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","month_pct_change"]]
                          .rename(columns={"month_pct_change":"delta"}).assign(Timeframe="MTD"))
    if "quarter_pct_change" in df.columns:
        tm_parts.append(df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","quarter_pct_change"]]
                          .rename(columns={"quarter_pct_change":"delta"}).assign(Timeframe="QTD"))

    tm = pd.concat(tm_parts, ignore_index=True).dropna(subset=["Ticker","delta"])
    # Normalize by universe vmax per timeframe so each column is independent
    tm["norm"] = tm.apply(
        lambda r: np.clip(r["delta"] / (_univ_vmax.get(r["Timeframe"], 1.0) or 1.0), -1, 1),
        axis=1
    )
    ticker_order = sorted(tm["Ticker"].unique().tolist())
    tf_order = ["Daily","WTD","MTD","QTD"]

    # Use global vmax based on per-ticker dispersion (robust)
    #vmax_ticker = float(np.quantile(np.abs(tm["delta"].values), 0.99))
    #vmax_ticker = max(1.0, np.ceil(vmax_ticker / 5.0) * 5.0)

    row_h = 22
    chart_h = max(360, row_h*len(ticker_order) + 24)
    chart_w = 530
    legend_w = 120

    ticker_heat = (
        alt.Chart(tm)
        .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
        .encode(
            x=alt.X("Timeframe:N", sort=tf_order,
                    axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8,
                                  labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
            y=alt.Y("Ticker:N", sort=ticker_order,
                    axis=alt.Axis(title=None, labelLimit=140, labelPadding=10, orient="left",
                                  labelFlush=False, labelColor="#1a1a1a", labelFontSize=13, labelOverlap=False)),
            color=alt.Color("norm:Q",
                            scale=alt.Scale(scheme="blueorange", domain=[-1,0,1]),
                            legend=alt.Legend(orient="bottom", title="% Change (per timeframe)",
                                              titleColor="#1a1a1a", labelColor="#1a1a1a",
                                              gradientLength=355, labelLimit=80,labelExpr="''")),
            tooltip=[alt.Tooltip("Ticker:N"),
                     alt.Tooltip("Ticker_name:N", title="Name"),
                     alt.Tooltip("Timeframe:N"),
                     alt.Tooltip("delta:Q", title="% Δ", format=",.2f")]
        )
        .properties(width=chart_w, height=chart_h,
                    padding={"left": legend_w, "right": 0, "top": 6, "bottom": -4})
        .configure_view(strokeOpacity=0)
    )

    pad_l, center_col, pad_r = st.columns([1.08, 3, .92])
    with center_col:
        with st.container(border=True):
            st.markdown(
                f'<div style="text-align:center;">'
                f'<h4 style="margin:0;">{sel} — Per-Ticker Performance Heatmap</h4>'
                f'<div class="small" style="margin-top:4px;">% Δ by ticker and timeframe</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            _l, _c, _r = st.columns([1, 4, 1])
            with _c:
                st.altair_chart(ticker_heat, use_container_width=False)

#col1, col2, col3 = st.columns([1.85, 3, .3])
#with col2:
#    st.caption("Note: Color scale uses a robust symmetric range; values beyond the range clip to the end color.")
col1, col2, col3 = st.columns([1.5, 3, .5])
with col2:
    st.caption("Note: Each timeframe column uses its own color scale derived from that timeframe’s dispersion (independent per timeframe)")


st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# -------------------------
# Helper: padded x-domain for negative-capable bar charts
# -------------------------
def padded_domain(series: pd.Series, frac: float = 0.06, min_pad: float = 2.0):
    if series.empty:
        return alt.Undefined
    s_min = float(series.min())
    s_max = float(series.max())
    rng = max(s_max - s_min, 1e-9)
    pad = max(rng * frac, min_pad)
    left = s_min - pad if s_min < 0 else s_min
    right = s_max + 0.02 * rng
    return [left, right]

# -------------------------
# Filter frames for selected category
# -------------------------
viewD  = df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","day_pct_change"]].dropna()
viewW  = df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","week_pct_change"]].dropna()
viewM  = df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","month_pct_change"]].dropna()
viewQ  = df.loc[df["Category"]==sel, ["Ticker","Ticker_name","Category","quarter_pct_change"]].dropna()

if all(v.empty for v in (viewD,viewW,viewM,viewQ)):
    st.info(f"No tickers found for **{sel}**.")
    st.stop()

c_lock, _, _ = st.columns([1,4,1])
with c_lock:
    lock_axes_and_order = st.checkbox("Lock axes", value=False, help="Fix axes and align all charts by ticker A→Z")

if lock_axes_and_order:
    y_order = sorted(set(viewD["Ticker"]) | set(viewW["Ticker"]) | set(viewM["Ticker"]) | set(viewQ["Ticker"]))
else:
    yD = viewD.sort_values("day_pct_change", ascending=False)["Ticker"].tolist()
    yW = viewW.sort_values("week_pct_change", ascending=False)["Ticker"].tolist()
    yM = viewM.sort_values("month_pct_change", ascending=False)["Ticker"].tolist()
    yQ = viewQ.sort_values("quarter_pct_change", ascending=False)["Ticker"].tolist()

chart_height = max(260, 24 * max(len(viewD),len(viewW),len(viewM),len(viewQ)) + 120)


# -------------------------
# Chart #1: 
# -------------------------

category_ms_min = float(viewD["day_pct_change"].min()-3) if not viewD.empty else 0.0
category_ms_max = float(viewD["day_pct_change"].max()+3) if not viewD.empty else 0.0

if lock_axes_and_order:
    ms_dom = padded_domain(pd.Series([category_ms_min, category_ms_max]), frac=0.06, min_pad=2.0)
else:
    ms_dom = padded_domain(pd.Series([category_ms_min, category_ms_max]),frac=0.06, min_pad=2.0)

xchartD = alt.X("day_pct_change:Q", title="Daily % Change", scale=alt.Scale(domain=ms_dom))

hint = "'Click to open Deep Dive'"
baseD = (
    alt.Chart(viewD)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else yD), title="Ticker"),
        x=xchartD,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("day_pct_change:Q", format=",.1f")],
    )
)

barsD = baseD.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posD = baseD.transform_filter("datum.day_pct_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("day_pct_change:Q", format=",.1f"))
negD = baseD.transform_filter("datum.day_pct_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("day_pct_change:Q", format=",.1f"))

chartD = (barsD + posD + negD).properties(title="Daily % Change", height=chart_height).configure_title(anchor="middle")

# -------------------------
# Chart #2: 
# -------------------------

category_ms_min2 = float(viewW["week_pct_change"].min()-3) if not viewW.empty else 0.0
category_ms_max2 = float(viewW["week_pct_change"].max()+3) if not viewW.empty else 0.0

if lock_axes_and_order:
    ms_dom = padded_domain(pd.Series([category_ms_min2, category_ms_max2]), frac=0.06, min_pad=2.0)
else:
    ms_dom = padded_domain(pd.Series([category_ms_min2, category_ms_max2]),frac=0.06, min_pad=2.0)

xchartW = alt.X("week_pct_change:Q", title="WTD % Change", scale=alt.Scale(domain=ms_dom))

hint = "'Click to open Deep Dive'"
baseW = (
    alt.Chart(viewW)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else yW), title="Ticker"),
        x=xchartW,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("week_pct_change:Q", format=",.1f")],
    )
)

barsW = baseW.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posW = baseW.transform_filter("datum.week_pct_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("week_pct_change:Q", format=",.1f"))
negW = baseW.transform_filter("datum.week_pct_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("week_pct_change:Q", format=",.1f"))

chartW = (barsW + posW + negW).properties(title="WTD % Change", height=chart_height).configure_title(anchor="middle")

# -------------------------
# Chart #3: 
# -------------------------

category_ms_min3 = float(viewM["month_pct_change"].min()-3) if not viewM.empty else 0.0
category_ms_max3 = float(viewM["month_pct_change"].max()+3) if not viewM.empty else 0.0

if lock_axes_and_order:
    ms_dom = padded_domain(pd.Series([category_ms_min3, category_ms_max3]), frac=0.06, min_pad=2.0)
else:
    ms_dom = padded_domain(pd.Series([category_ms_min3, category_ms_max3]),frac=0.06, min_pad=2.0)

xchartM = alt.X("month_pct_change:Q", title="MTD % Change", scale=alt.Scale(domain=ms_dom))

hint = "'Click to open Deep Dive'"
baseM = (
    alt.Chart(viewM)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else yM), title="Ticker"),
        x=xchartM,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("month_pct_change:Q", format=",.1f")],
    )
)

barsM = baseM.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posM = baseM.transform_filter("datum.month_pct_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("month_pct_change:Q", format=",.1f"))
negM = baseM.transform_filter("datum.month_pct_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("month_pct_change:Q", format=",.1f"))

chartM = (barsM + posM + negM).properties(title="MTD % Change", height=chart_height).configure_title(anchor="middle")

# -------------------------
# Chart #4: 
# -------------------------

category_ms_min4 = float(viewQ["quarter_pct_change"].min()-3) if not viewQ.empty else 0.0
category_ms_max4 = float(viewQ["quarter_pct_change"].max()+3) if not viewQ.empty else 0.0

if lock_axes_and_order:
    ms_dom = padded_domain(pd.Series([category_ms_min4, category_ms_max4]), frac=0.06, min_pad=2.0)
else:
    ms_dom = padded_domain(pd.Series([category_ms_min4, category_ms_max4]),frac=0.06, min_pad=2.0)

xchartQ = alt.X("quarter_pct_change:Q", title="QTD % Change", scale=alt.Scale(domain=ms_dom))

hint = "'Click to open Deep Dive'"
baseQ = (
    alt.Chart(viewQ)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else yQ), title="Ticker"),
        x=xchartQ,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("quarter_pct_change:Q", format=",.1f")],
    )
)

barsQ = baseQ.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posQ = baseQ.transform_filter("datum.quarter_pct_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("quarter_pct_change:Q", format=",.1f"))
negQ = baseQ.transform_filter("datum.quarter_pct_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("quarter_pct_change:Q", format=",.1f"))

chartQ = (barsQ + posQ + negQ).properties(title="QTD % Change", height=chart_height).configure_title(anchor="middle")


st.markdown('<div class="h-title">Bar Charts by Ticker</div>', unsafe_allow_html=True)

# Render 4-up (responsive via CSS)
cA, cB, cC, cD = st.columns(4)
with cA:
    #st.markdown('<span id="grid4" style="display:block;height:0;overflow:hidden"></span>', unsafe_allow_html=True)
    st.altair_chart(chartD, use_container_width=True)
with cB: st.altair_chart(chartW, use_container_width=True)
with cC: st.altair_chart(chartM, use_container_width=True)
with cD: st.altair_chart(chartQ, use_container_width=True)

st.markdown(
    "<div style='margin-top:6px; color:#6b7280; font-size:13px;'>"
    "Tip: <b>Click any bar</b> to open the Deep Dive for that ticker."
    "</div>",
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