# -------------------------
# Markmentum — Ranking (Model Scores + Sharpe Rank + Sharpe Ratio + Sharpe Ratio 30D Change)
# -------------------------

from pathlib import Path
import base64
import pandas as pd
import altair as alt
import streamlit as st
import sys
import numpy as np
from urllib.parse import quote_plus

# ---------- Page ----------
st.cache_data.clear()
st.set_page_config(page_title="Markmentum Heatmap", layout="wide")
def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -------------------------
# Global CSS
# -------------------------
st.markdown("""
<style>
/* ============== Page & Shared style (clean, #9 rules) ============== */

/* Container */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div { width:95vw; max-width:2100px; margin-left:auto; margin-right:auto; }

/* Remove bordered “decoration” wrappers */
div[data-testid="stDecoration"]{ display:none !important; }
div[data-testid="stVerticalBlockBorderWrapper"]{ border:none !important; background:transparent !important; box-shadow:none !important; }
div[data-testid="stVerticalBlockBorderWrapper"] > div[aria-hidden="true"]{ display:none !important; }

/* Type + optional heatmap headings (kept as in #9) */
html, body, [class^="css"], .stMarkdown, .stText, .stDataFrame, .stTable, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.h-title { text-align:center; font-size:20px; font-weight:700; color:#1a1a1a; margin:4px 0 8px; }
.h-sub   { text-align:center; font-size:12px; color:#666;     margin:2px 0 10px; }

/* Compact select width */
div[data-baseweb="select"] { max-width:36ch !important; }

/* -------- SCOPED layout rules (so we don't affect unrelated rows) -------- */

/* A) Global heatmap centering row: applies to the st.columns row placed right after #hm-center */
#hm-center + div[data-testid="stHorizontalBlock"]{
  display:flex !important; justify-content:center !important; gap:0 !important;
}
#hm-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
#hm-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3){
  flex:1 1 0 !important; min-width:0 !important;   /* side columns flex */
}
#hm-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2){
  flex:0 0 auto !important; min-width:0 !important; /* middle column shrinks to chart */
}

/* B) Bottom 4 charts grid: 4-up desktop, 2×2 laptops/MBA, 1-up small screens */
div[data-testid="stHorizontalBlock"]:has(#grid4) { display:flex; flex-wrap:wrap; gap:24px; }
div[data-testid="stHorizontalBlock"]:has(#grid4) > div[data-testid="column"]{ flex:1 1 22%; min-width:280px; }   /* 4-up desktop */
@media (max-width:1499.98px){  /* laptops / MacBook Air → 2-up */
  div[data-testid="stHorizontalBlock"]:has(#grid4) > div[data-testid="column"]{ flex:1 1 48%; }
}
@media (max-width:799.98px){   /* small screens → 1-up */
  div[data-testid="stHorizontalBlock"]:has(#grid4) > div[data-testid="column"]{ flex:1 1 100%; }
}

/* C) Altair/Vega: intrinsic sizing + centering inside their column (backstop) */
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

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"




CSV_PATH_48  = DATA_DIR / "qry_graph_data_48.csv"   # model_score
CSV_PATH_WTD  = DATA_DIR / "model_score_wtd_change.csv"   # Sharpe_Rank
CSV_PATH_MTD  = DATA_DIR / "model_score_mtd_change.csv"   # Sharpe
CSV_PATH_QTD  = DATA_DIR / "model_score_qtd_change.csv"   # Sharpe_Ratio_30D_Change


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


#---clickable links helper------
def _mk_ticker_link(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    return (
        f'<a href="?page=Deep%20Dive&ticker={quote_plus(t)}" '
        f'target="_self" rel="noopener" '
        f'style="text-decoration:none; font-weight:600;">{t}</a>'
    )

# --- lightweight router: handle links like ?page=Deep%20Dive&ticker=NVDA ---
qp = st.query_params
dest = (qp.get("page") or "").strip().lower()

if dest.replace("%20", " ") == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        # make Deep Dive happy even if it uses session_state only
        st.session_state["ticker"] = t
        # keep the ticker in the URL for shareability
        st.query_params.clear()
        st.query_params["ticker"] = t
    # jump to the page file in /pages
    st.switch_page("pages/13_Deep_Dive_Dashboard.py")


# -------------------------
# Loaders
# -------------------------

last_modified = (DATA_DIR / "qry_graph_data_48.csv").stat().st_mtime
@st.cache_data(show_spinner=False)

def load_csv48(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker", "Ticker_name", "Category", "Date", "model_score_daily_change"])
    df = pd.read_csv(path)

    # NEW: normalize keys to avoid whitespace/case issues that can hide axis labels
    for col in ("Ticker", "Ticker_name", "Category"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df["Ticker"] = df["Ticker"].str.upper()   # optional but helps keep things uniform
    df["model_score_daily_change"] = pd.to_numeric(df["model_score_daily_change"], errors="coerce")
    return df



last_modified = (DATA_DIR / "model_score_wtd_change.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv_WTD(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker","Ticker_name","Category","Date","model_score_wtd_change"])
    df = pd.read_csv(path)
    for col in ("Ticker","Ticker_name","Category"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Ticker"] = df["Ticker"].str.upper()
    df["model_score_wtd_change"] = pd.to_numeric(df["model_score_wtd_change"], errors="coerce")
    return df

last_modified = (DATA_DIR / "model_score_mtd_change.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv_MTD(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker","Ticker_name","Category","Date","model_score_mtd_change"])
    df = pd.read_csv(path)
    for col in ("Ticker","Ticker_name","Category"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Ticker"] = df["Ticker"].str.upper()
    df["model_score_mtd_change"] = pd.to_numeric(df["model_score_mtd_change"], errors="coerce")
    return df

last_modified = (DATA_DIR / "model_score_qtd_change.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv_QTD(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker","Ticker_name","Category","Date","model_score_qtd_change"])
    df = pd.read_csv(path)
    for col in ("Ticker","Ticker_name","Category"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Ticker"] = df["Ticker"].str.upper()
    df["model_score_qtd_change"] = pd.to_numeric(df["model_score_qtd_change"], errors="coerce")
    return df

df48 = load_csv48(CSV_PATH_48).copy()
dfWTD = load_csv_WTD(CSV_PATH_WTD).copy()
dfMTD = load_csv_MTD(CSV_PATH_MTD).copy()
dfQTD = load_csv_QTD(CSV_PATH_QTD).copy()

if df48.empty or dfWTD.empty or dfMTD.empty or dfQTD.empty:
    st.warning("Missing one of the input CSVs (48, 49, 50, or 51). Please confirm files exist.")
    st.stop()


#====title=================
def _mdy_fmt() -> str:
    """Platform-safe month/day format (no leading zeros)."""
    return "%#m/%#d/%Y" if sys.platform.startswith("win") else "%-m/%-d/%Y"

def _first_date_from_csv(path: str, date_col: str = "date") -> str:
    df = pd.read_csv(path)
    # Be tolerant to 'Date' vs 'date'
    if date_col not in df.columns:
        for alt in ("Date", "DATE"):
            if alt in df.columns:
                date_col = alt
                break
    dt = pd.to_datetime(df[date_col].iloc[0], errors="coerce")
    return "" if pd.isna(dt) else dt.strftime(_mdy_fmt())

date_text = _first_date_from_csv(CSV_PATH_48, date_col="date")

st.markdown(
    f"""
    <div style="
        text-align:center;
        font-size:20px;
        font-weight:600;
        color:#233;
        margin-top:8px;
        margin-bottom:12px;">
        Markmentum Heatmap – {date_text}
    </div>
    """,
    unsafe_allow_html=True,
)
#=====title end

# --- robust per-timeframe vmax (winsorized)
def _robust_vmax(s: pd.Series, q: float = 0.98, floor: float = 1.0, step: float = 5.0) -> float:
    if s is None or len(s) == 0:
        return floor
    vmax = float(np.quantile(np.abs(pd.to_numeric(s, errors="coerce").dropna()), q))
    return max(floor, np.ceil(vmax / step) * step)

# --- Universe-wide robust vmax per timeframe (all 635 tickers)
_univ_vmax = {}
if "model_score_daily_change" in df48.columns:
    _univ_vmax["Daily"] = _robust_vmax(df48["model_score_daily_change"], step=10.0)
if "model_score_wtd_change" in dfWTD.columns:
    _univ_vmax["WTD"]   = _robust_vmax(dfWTD["model_score_wtd_change"], step=10.0)
if "model_score_mtd_change" in dfMTD.columns:
    _univ_vmax["MTD"]   = _robust_vmax(dfMTD["model_score_mtd_change"], step=10.0)
if "model_score_qtd_change" in dfQTD.columns:
    _univ_vmax["QTD"]   = _robust_vmax(dfQTD["model_score_qtd_change"], step=10.0)



# =========================
# Global Heatmap — Avg Model Score Changes
# Paste this block right after the page title and before your controls.
# =========================
import altair as alt
import pandas as pd
import streamlit as st

# ---- Build Category × Timeframe table from your four dataframes
parts = []
if "model_score_daily_change" in df48.columns:
    parts.append(
        df48[["Category","model_score_daily_change"]]
          .rename(columns={"model_score_daily_change":"delta"})
          .assign(Timeframe="Daily")
    )
parts.append(dfWTD[["Category","model_score_wtd_change"]]
             .rename(columns={"model_score_wtd_change":"delta"})
             .assign(Timeframe="WTD"))
parts.append(dfMTD[["Category","model_score_mtd_change"]]
             .rename(columns={"model_score_mtd_change":"delta"})
             .assign(Timeframe="MTD"))
parts.append(dfQTD[["Category","model_score_qtd_change"]]
             .rename(columns={"model_score_qtd_change":"delta"})
             .assign(Timeframe="QTD"))

hm = pd.concat(parts, ignore_index=True)
hm["Category"]  = hm["Category"].astype(str).str.strip()
hm["Timeframe"] = hm["Timeframe"].astype(str).str.strip()
hm["delta"]     = pd.to_numeric(hm["delta"], errors="coerce")

# 1) Aggregate
agg = (hm.groupby(["Category","Timeframe"], as_index=False)
         .agg(avg_delta=("delta","mean"), n=("delta","size")))

# 2) Densify to full Category×Timeframe grid so Altair always has rows to draw
preferred = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities","Bonds","Yields","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples","Energy","Financials","Health Care",
    "Industrials","Information Technology","Materials","Real Estate","Utilities","MR Discretion"
]
present   = list(agg["Category"].unique())
cat_order = [c for c in preferred if c in present] + [c for c in present if c not in preferred]
tf_order  = ["Daily","WTD","MTD","QTD"]

grid = pd.MultiIndex.from_product([cat_order, tf_order], names=["Category","Timeframe"]).to_frame(index=False)
agg = grid.merge(agg, on=["Category","Timeframe"], how="left")
# only fill truly-missing cells
agg["avg_delta"] = pd.to_numeric(agg["avg_delta"], errors="coerce")
agg["n"]        = agg["n"].fillna(0).astype(int)

# 3) Per-timeframe scale (independent columns; robust winsorized vmax)
def _robust_vmax(s: pd.Series, q=0.98, floor=1.0, step=5.0):
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty: return floor
    vmax = float(np.quantile(np.abs(s), q))
    return max(floor, np.ceil(vmax/step)*step)

vmax_by_tf = {tf: _robust_vmax(agg.loc[agg["Timeframe"]==tf, "avg_delta"]) for tf in tf_order}
tf_scale = agg["Timeframe"].map(vmax_by_tf).replace(0.0, 1.0).fillna(1.0).astype(float)

# 4) Normalize; impute only where nothing existed
norm = agg["avg_delta"].where(~agg["avg_delta"].isna(), 0.0) / tf_scale
agg_norm = agg.assign(norm=np.clip(norm, -1, 1)).fillna({"avg_delta": 0.0})

# 5) Draw with visible cell borders even if color=white at 0
row_h   = 26
chart_h = max(360, row_h * len(cat_order) + 24)
chart_w = 625
legend_w = 120

heat = (
    alt.Chart(agg_norm)
      .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=1.0)  # stroke forced visible
      .encode(
          x=alt.X("Timeframe:N", sort=tf_order,
                  axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8,
                                labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
          y=alt.Y("Category:N", sort=cat_order,
                  axis=alt.Axis(title=None, labelLimit=460, orient="left", labelPadding=6,
                                labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
          color=alt.Color("norm:Q",
                          scale=alt.Scale(scheme="blueorange", domain=[-1, 0, 1]),
                          legend=alt.Legend(orient="bottom", title="Avg Δ Score (per timeframe)",
                                            titleColor="#1a1a1a", labelColor="#1a1a1a",
                                            gradientLength=360, labelLimit=80, labelExpr="''")),
          tooltip=[
              alt.Tooltip("Category:N"),
              alt.Tooltip("Timeframe:N"),
              alt.Tooltip("avg_delta:Q", title="Avg Δ", format=",+.2f"),
              alt.Tooltip("n:Q", title="Count"),
          ],
      )
      .properties(width=chart_w, height=chart_h,
                  padding={"left": legend_w, "right": 0, "top": 6, "bottom": 6})
      .configure_view(strokeOpacity=0)
)

st.markdown('<div id="hm-center"></div>', unsafe_allow_html=True)
pad_l, center_col, pad_r = st.columns([1, 3, 1])
with center_col:
    with st.container(border=True):
        st.markdown(
            '<div style="text-align:center;">'
            '<h3 style="margin:0;">Markmentum Heatmap – Avg Score Changes</h3>'
            '<div class="small" style="margin-top:4px;">Average Score Δ across tickers in each category and timeframe</div>'
            '</div>', unsafe_allow_html=True,
        )
        _l, _c, _r = st.columns([1, 7, 1])
        with _c:
            st.altair_chart(heat, use_container_width=False)



# -------------------------
# Controls (selector + lock)
# -------------------------
# Desired manual order
custom_order = [
    "Sector & Style ETFs",
    "Indices",
    "Futures",
    "Currencies",
    "Commodities",
    "Bonds",
    "Yields",
    "Foreign",
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
    "MR Discretion"
]

# Keep only categories that exist in your data
all_cats = [cat for cat in custom_order if cat in (
    set(df48["Category"].dropna().unique())
    | set(dfWTD["Category"].dropna().unique())
    | set(dfMTD["Category"].dropna().unique())
    | set(dfQTD["Category"].dropna().unique())
)]


default_cat = "Sector & Style ETFs"
default_index = all_cats.index(default_cat) if default_cat in all_cats else 0



#left_toggle,c_blank,c_blank= st.columns([1,4,1])
#with left_toggle:
#        show_ticker_hm = st.checkbox("Show per-ticker heatmap (category)", value=False, key="show_ticker_hm")
show_ticker_hm = True

c_blank,c_sel,c_blank = st.columns([2.5,3,.3])
with c_sel:
        sel = st.selectbox("Category", all_cats, index=default_index, key="rankings_category")
    




#left_toggle, c_sel, c_lock = st.columns([0.50, 0.45, 0.15])
#with left_toggle:
#    show_ticker_hm = st.checkbox("Show per-ticker heatmap (category)", value=False, key="show_ticker_hm")
#with c_sel:
#    sel = st.selectbox("Category", all_cats, index=default_index, key="rankings_category")
#with c_lock:
#    lock_axes_and_order = st.checkbox("Lock axes", value=False, help="Fix axes and align all charts by ticker A→Z")


# =========================
# Per-Ticker Heatmap (Category)
# Place this block RIGHT UNDER your Category selectbox and ABOVE the four ranking charts.
# Expects your selectbox variable to be named `sel`.
# Uses df48 (Daily), dfWTD, dfMTD, dfQTD already loaded on the page.
# =========================

# Left-aligned toggle to reveal the matrix
#left_toggle, _ = st.columns([1, 9])
#with left_toggle:
#    show_ticker_hm = st.checkbox("Show per-ticker heatmap (category)", value=False, key="show_ticker_hm")





if show_ticker_hm:
    # --- Build a unified per-ticker table across Daily / WTD / MTD / QTD for the selected category
    def _daily_part(df_daily: pd.DataFrame) -> pd.DataFrame:
        # csv #48 columns: model_score, previous_model_score, model_score_daily_change
        cols = [
            "Ticker", "Ticker_name", "Category", "Date",
            "model_score_daily_change", "model_score", "previous_model_score",
        ]
        cols = [c for c in cols if c in df_daily.columns]
        return (
            df_daily.loc[df_daily["Category"] == sel, cols]
                    .rename(columns={
                        "model_score_daily_change": "delta",
                        "model_score": "current_model_score",
                    })
                    .assign(Timeframe="Daily")
        )

    def _part(df: pd.DataFrame, delta_col: str, tf_label: str) -> pd.DataFrame:
        # WTD/MTD/QTD files already have current_model_score / previous_model_score
        cols = [
            "Ticker", "Ticker_name", "Category", "Date",
            delta_col, "current_model_score", "previous_model_score",
        ]
        cols = [c for c in cols if c in df.columns]
        return (
            df.loc[df["Category"] == sel, cols]
              .rename(columns={delta_col: "delta"})
              .assign(Timeframe=tf_label)
        )

    parts = []
    if "model_score_daily_change" in df48.columns:
        parts.append(_daily_part(df48))
    parts.append(_part(dfWTD, "model_score_wtd_change", "WTD"))
    parts.append(_part(dfMTD, "model_score_mtd_change", "MTD"))
    parts.append(_part(dfQTD, "model_score_qtd_change", "QTD"))

    tm = pd.concat(parts, ignore_index=True).dropna(subset=["Ticker", "delta"])
    # Normalize by universe vmax per timeframe so each column is independent
    tm["norm"] = tm.apply(
        lambda r: np.clip(r["delta"] / (_univ_vmax.get(r["Timeframe"], 1.0) or 1.0), -1, 1),
        axis=1
    )



    # --- Sort tickers alphabetically for the Y-axis
    ticker_order = sorted(tm["Ticker"].unique().tolist())
    tf_order = ["Daily", "WTD", "MTD", "QTD"]

    # --- Chart sizing (narrow, card hugs chart)
    row_h   = 22
    chart_h = max(360, row_h * max(1, len(ticker_order)) + 24)
    chart_w = 530
    legend_w = 120

    # --- Symmetric diverging scale centered at 0 (winsorized)
    vmax = float(max(1.0, tm["delta"].abs().quantile(0.98)))

    ticker_heat = (
        alt.Chart(tm)
        .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
        .encode(
            x=alt.X(
                "Timeframe:N",
                sort=tf_order,
                axis=alt.Axis(
                    orient="top",
                    title=None,
                    labelAngle=0,
                    labelPadding=8,
                    labelFlush=False,          # keeps 'Daily' centered
                    labelColor="#1a1a1a",
                    labelFontSize=13,
                ),
            ),
            y=alt.Y(
                "Ticker:N",
                sort=ticker_order,             # <- alphabetical tickers on the left
                axis=alt.Axis(
                    title=None,
                    labelLimit=140,
                    labelPadding=10,
                    orient = "left",
                    labelFlush=False, 
                    labelColor="#1a1a1a",
                    labelFontSize=13,
                    labelOverlap=False,
                ),
            ),
            color=alt.Color(
                "norm:Q",
                scale=alt.Scale(scheme="blueorange", domain=[-1, 0, 1]),
                legend=alt.Legend(
                    orient="bottom",
                    title="Δ Score (per timeframe)",
                    titleColor="#1a1a1a",
                    labelColor="#1a1a1a",
                    gradientLength=355,
                    labelLimit=80,
                    labelExpr="''"
                ),
            ),
            tooltip=[
                alt.Tooltip("Ticker:N"),
                alt.Tooltip("Ticker_name:N", title="Name"),
                alt.Tooltip("Timeframe:N"),
                alt.Tooltip("delta:Q", title="Δ Score", format=",.2f"),
                alt.Tooltip("current_model_score:Q", title="Current", format=",.2f"),
                alt.Tooltip("previous_model_score:Q", title="Previous", format=",.2f"),
                alt.Tooltip("Date:N", title="Date"),
            ],
        )
        .properties(
            width=chart_w,
            height=chart_h,
            padding={"left": legend_w, "right": 0, "top": 6, "bottom": -4},  # balances right legend
        )
        .configure_view(strokeOpacity=0)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )

    # --- Centered, snug card
    pad_l, center_col, pad_r = st.columns([1.08, 3, .92])
    with center_col:
        with st.container(border=True):
            st.markdown(
                f'<div style="text-align:center;">'
                f'<h4 style="margin:0;">{sel} — Per-Ticker Markmentum Heatmap</h4>'
                f'<div class="small" style="margin-top:4px;">'
                f'Score Δ by ticker and timeframe'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            _l, _c, _r = st.columns([1, 4, 1])
            with _c:
                st.altair_chart(ticker_heat, use_container_width=False)

#col1, col2, col3 = st.columns([1.85, 3, .3])
#with col2:
#    st.caption(f"Note: Color scale fixed globally to ±{vmax_ticker:g}. Values outside this range are shown at the end color.")
#st.divider()  # thin horizontal line
st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)  # small gap after
st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)  # small gap after

# global model-score min/max for locked mode
global_ms_min = float(df48["model_score_daily_change"].min()) if not df48.empty else 0.0
global_ms_max = float(df48["model_score_daily_change"].max()) if not df48.empty else 0.0

# -------------------------
# Helper: padded domain for negative-capable charts
# -------------------------
def padded_domain(series: pd.Series, frac: float = 0.06, min_pad: float = 2.0):
    """
    Extend the x-domain a bit on the left (and a hair on the right) so
    large negative bars have room for labels and tickers.
    """
    if series.empty:
        return alt.Undefined
    s_min = float(series.min())
    s_max = float(series.max())
    rng = max(s_max - s_min, 1e-9)
    pad = max(rng * frac, min_pad)
    left = s_min - pad if s_min < 0 else s_min
    right = s_max + 0.02 * rng  # tiny right pad
    return [left, right]

# -------------------------
# Filter dataframes for the selected category
# -------------------------

c_lock,c_blank, c_blank = st.columns([1,4,1])
with c_lock:
        lock_axes_and_order = st.checkbox("Lock axes", value=False, help="Fix axes and align all charts by ticker A→Z")

st.markdown('<div class="h-title">Bar Charts by Ticker</div>', unsafe_allow_html=True)

view48 = df48[df48["Category"] == sel].copy().sort_values("model_score_daily_change", ascending=False)
viewWTD = dfWTD[dfWTD["Category"] == sel].copy().sort_values("model_score_wtd_change", ascending=False)
viewMTD = dfMTD[dfMTD["Category"] == sel].copy().sort_values("model_score_mtd_change", ascending=False)
viewQTD = dfQTD[dfQTD["Category"] == sel].copy().sort_values("model_score_qtd_change", ascending=False)

if view48.empty and viewWTD.empty and viewMTD.empty and viewQTD.empty:
    st.info(f"No tickers found for **{sel}**.")
    st.stop()

# y (row) order handling
if lock_axes_and_order:
    y_order = sorted(set(view48["Ticker"]) | set(viewWTD["Ticker"]) | set(viewMTD["Ticker"]) | set(viewQTD["Ticker"]))
else:
    y_order_48 = view48["Ticker"].tolist()
    y_order_WTD = viewWTD["Ticker"].tolist()
    y_order_MTD = viewMTD["Ticker"].tolist()
    y_order_QTD = viewQTD["Ticker"].tolist()

chart_height = max(260, 24 * max(len(view48), len(viewWTD), len(viewMTD), len(viewQTD)) + 120)

# -------------------------
# Chart #1: Model Score  (now with padded domain)
# -------------------------
# global model-score min/max for locked mode
category_ms_min = float(view48["model_score_daily_change"].min()-25) if not df48.empty else 0.0
category_ms_max = float(view48["model_score_daily_change"].max()+25) if not df48.empty else 0.0

if lock_axes_and_order:
    ms_dom = padded_domain(pd.Series([global_ms_min, global_ms_max]), frac=0.06, min_pad=2.0)
else:
    ms_dom = padded_domain(pd.Series([category_ms_min, category_ms_max]),frac=0.06, min_pad=2.0)

x48 = alt.X("model_score_daily_change:Q", title="Score Daily Change", scale=alt.Scale(domain=ms_dom))

hint = "'Click to open Deep Dive'"
base48 = (
    alt.Chart(view48)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_48), title="Ticker"),
        x=x48,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("model_score_daily_change:Q", format=",.0f")],
    )
)

bars48 = base48.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

pos48 = base48.transform_filter("datum.model_score_daily_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("model_score_daily_change:Q", format=",.0f"))
neg48 = base48.transform_filter("datum.model_score_daily_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("model_score_daily_change:Q", format=",.0f"))

chart48 = (bars48 + pos48 + neg48).properties(title="Score Daily Change Ranking", height=chart_height).configure_title(anchor="middle")

# -------------------------
# Chart #2: Sharpe Percentile Rank (unchanged)
# -------------------------
# global model-score min/max for locked mode
category_ms_min2 = float(viewWTD["model_score_wtd_change"].min()-10) if not dfWTD.empty else 0.0
category_ms_max2 = float(viewWTD["model_score_wtd_change"].max()+10) if not dfWTD.empty else 0.0

if lock_axes_and_order:
    ms_dom2 = padded_domain(pd.Series([global_ms_min, global_ms_max]), frac=0.06, min_pad=2.0)
else:
    ms_dom2 = padded_domain(pd.Series([category_ms_min2, category_ms_max2]),frac=0.06, min_pad=2.0)

xWTD = alt.X("model_score_wtd_change:Q", title="Score WTD Change", scale=alt.Scale(domain=ms_dom2))


baseWTD = (
    alt.Chart(viewWTD)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_WTD), title="Ticker"),
        x=xWTD,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("model_score_wtd_change:Q", format=",.1f")],
    )
)

barsWTD = baseWTD.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posWTD = baseWTD.transform_filter("datum.model_score_wtd_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("model_score_wtd_change:Q", format=",.0f"))
negWTD = baseWTD.transform_filter("datum.model_score_wtd_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("model_score_wtd_change:Q", format=",.0f"))

chartWTD = (barsWTD + posWTD + negWTD).properties(title="Score WTD Change Ranking", height=chart_height).configure_title(anchor="middle")

# -------------------------
# Chart #3: Sharpe Ratio  (now with padded domain)
# -------------------------
category_ms_min3 = float(viewMTD["model_score_mtd_change"].min()-10) if not dfMTD.empty else 0.0
category_ms_max3 = float(viewMTD["model_score_mtd_change"].max()+10) if not dfMTD.empty else 0.0

if lock_axes_and_order:
    ms_dom3 = padded_domain(pd.Series([global_ms_min, global_ms_max]), frac=0.06, min_pad=2.0)
else:
    ms_dom3 = padded_domain(pd.Series([category_ms_min3, category_ms_max3]),frac=0.06, min_pad=2.0)

xMTD = alt.X("model_score_mtd_change:Q", title="Score MTD Change", scale=alt.Scale(domain=ms_dom3))

baseMTD = (
    alt.Chart(viewMTD)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_MTD), title="Ticker"),
        x=xMTD,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("model_score_mtd_change:Q", format=",.0f")],
    )
)

barsMTD = baseMTD.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posMTD = baseMTD.transform_filter("datum.model_score_mtd_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("model_score_mtd_change:Q", format=",.0f"))
negMTD = baseMTD.transform_filter("datum.model_score_mtd_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("model_score_mtd_change:Q", format=",.0f"))

chartMTD = (barsMTD + posMTD + negMTD).properties(title="Score MTD Change Ranking", height=chart_height).configure_title(anchor="middle")

# -------------------------
# Chart #4: Sharpe Ratio 30-Day Change  (now with padded domain)
# -------------------------
category_ms_min4 = float(viewQTD["model_score_qtd_change"].min()-10) if not dfQTD.empty else 0.0
category_ms_max4 = float(viewQTD["model_score_qtd_change"].max()+10) if not dfQTD.empty else 0.0

if lock_axes_and_order:
    ms_dom4 = padded_domain(pd.Series([global_ms_min, global_ms_max]), frac=0.06, min_pad=2.0)
else:
    ms_dom4 = padded_domain(pd.Series([category_ms_min4, category_ms_max4]),frac=0.06, min_pad=2.0)

xQTD = alt.X("model_score_qtd_change:Q", title="Score QTD Change", scale=alt.Scale(domain=ms_dom4))

baseQTD = (
    alt.Chart(viewQTD)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_QTD), title="Ticker"),
        x=xQTD,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("model_score_qtd_change:Q", format=",.0f")],
    )
)

barsQTD = baseQTD.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")

posQTD = baseQTD.transform_filter("datum.model_score_qtd_change >= 0") \
              .mark_text(align="left", baseline="middle", dx=4) \
              .encode(text=alt.Text("model_score_qtd_change:Q", format=",.0f"))
negQTD = baseQTD.transform_filter("datum.model_score_qtd_change < 0") \
              .mark_text(align="right", baseline="middle", dx=-10) \
              .encode(text=alt.Text("model_score_qtd_change:Q", format=",.0f"))

chartQTD = (barsQTD + posQTD + negQTD).properties(title="Score QTD Change Ranking", height=chart_height).configure_title(anchor="middle")

# Render in 4 columns (centered row; wraps on smaller screens)
cA, cB, cC, cD = st.columns(4)

with cA:
    #st.markdown('<span id="grid4" style="display:block;height:0;overflow:hidden"></span>', unsafe_allow_html=True)
    st.altair_chart(chart48, use_container_width=True)

with cB: st.altair_chart(chartWTD, use_container_width=True)
with cC: st.altair_chart(chartMTD, use_container_width=True)
with cD: st.altair_chart(chartQTD, use_container_width=True)

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