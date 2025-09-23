# 09_Rankings_cloud.py
# Rendering-only updates: remove stray “pill” bars, center heatmaps, narrow heatmap cells,
# and render bottom 4 charts in columns (avoids Altair concat error). No data/logic changes.

from pathlib import Path
import base64
import sys
from urllib.parse import quote_plus

import altair as alt
import pandas as pd
import streamlit as st

# ---------- Page ----------
st.cache_data.clear()
st.set_page_config(page_title="Markmentum – Rankings", layout="wide")

# ---------- Global CSS ----------
st.markdown("""
<style>
/* Page container sizing */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div {
  width: 95vw;
  max-width: 2100px;
  margin-left: auto;
  margin-right: auto;
}

/* Kill any bordered-container “decoration” / pill bars */
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stVerticalBlockBorderWrapper"] {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div[aria-hidden="true"] {
  display: none !important;
}

/* Centering helper for charts */
.viz-center { display:flex; justify-content:center; }

/* Type + headings */
html, body, [class^="css"], .stMarkdown, .stText, .stDataFrame, .stTable, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.h-title { text-align:center; font-size:20px; font-weight:700; color:#1a1a1a; margin: 4px 0 8px; }
.h-sub   { text-align:center; font-size:12px; color:#666; margin: 2px 0 10px; }

/* Compact select width (doesn't create any pill) */
div[data-baseweb="select"] { max-width: 36ch !important; }

/* Let Streamlit column rows wrap nicely on smaller widths */
div[data-testid="stHorizontalBlock"]{ display:flex; flex-wrap: wrap; gap: 24px; }
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 24%; min-width: 360px; }
@media (max-width: 1499.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 48%; }
}
@media (max-width: 999.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 100%; }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Center ALL Altair/Vega charts (canvas + legend) */
.vega-embed, .vega-embed > div {
  margin-left: auto !important;
  margin-right: auto !important;
}
</style>
""", unsafe_allow_html=True)

# ---------- Paths ----------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent
DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

CSV48 = DATA_DIR / "qry_graph_data_48.csv"   # model_score
CSV49 = DATA_DIR / "qry_graph_data_49.csv"   # Sharpe_Rank
CSV50 = DATA_DIR / "qry_graph_data_50.csv"   # Sharpe
CSV51 = DATA_DIR / "qry_graph_data_51.csv"   # Sharpe_Ratio_30D_Change

# ---------- Helpers ----------
def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

def _mdy_fmt() -> str:
    return "%#m/%#d/%Y" if sys.platform.startswith("win") else "%-m/%-d/%Y"

def _first_date_from_csv(path: Path, date_col: str = "date") -> str:
    if not path.exists(): return ""
    df = pd.read_csv(path)
    if date_col not in df.columns:
        for alt in ("Date","DATE"):
            if alt in df.columns:
                date_col = alt; break
    dt = pd.to_datetime(df[date_col].iloc[0], errors="coerce")
    return "" if pd.isna(dt) else dt.strftime(_mdy_fmt())

# Router for Deep Dive
qp = st.query_params
if (qp.get("page") or "").replace("%20"," ").strip().lower() == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    st.switch_page("pages/11_Deep_Dive_Dashboard.py")

@st.cache_data(show_spinner=False)
def load_csv(path: Path, numeric_cols: list[str] | None = None) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    df = pd.read_csv(path)
    if numeric_cols:
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ---------- Data ----------
df48 = load_csv(CSV48, numeric_cols=["model_score"])
df49 = load_csv(CSV49, numeric_cols=["Sharpe_Rank"])
df50 = load_csv(CSV50, numeric_cols=["Sharpe"])
df51 = load_csv(CSV51, numeric_cols=["Sharpe_Ratio_30D_Change"])

if any(df.empty for df in [df48, df49, df50, df51]):
    st.warning("One or more CSVs (48–51) are missing or empty.")
    st.stop()

# ---------- Header ----------
if LOGO_PATH.exists():
    st.markdown(
        f'<div style="text-align:center; margin: 8px 0 14px;">'
        f'<img src="data:image/png;base64,{_image_b64(LOGO_PATH)}" width="440"></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    f'<div class="h-title">Rankings – {_first_date_from_csv(CSV48)}</div>',
    unsafe_allow_html=True,
)

# =========================================================
# Global Heatmap — Current Score (by Category)
#   - Title centered
#   - Chart centered
#   - Narrow column width ~ matches “Current” header
# =========================================================
cat_cur = (
    df48[["Category","model_score"]]
      .dropna(subset=["Category","model_score"])
      .groupby("Category", as_index=False)
      .agg(avg_score=("model_score","mean"), n=("model_score","size"))
      .assign(Timeframe="Current")
)

preferred = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities","Bonds & Yields","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples","Energy","Financials",
    "Health Care","Industrials","Information Technology","Materials","Real Estate","Utilities","MR Discretion"
]
present  = list(cat_cur["Category"].unique())
cat_order = [c for c in preferred if c in present] + [c for c in present if c not in preferred]

vmax    = float(max(1.0, cat_cur["avg_score"].abs().quantile(0.98)))
heat_w  = 285   # << narrow column (~“Current” header width)
heat_h  = max(420, 26 * len(cat_order) + 24)

st.markdown('<div class="h-title">Markmentum Heatmap — Current Score (by Category)</div>', unsafe_allow_html=True)
st.markdown('<div class="h-sub">Average current Markmentum Score across tickers in each category.</div>', unsafe_allow_html=True)

cur_heat = (
    alt.Chart(cat_cur)
      .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
      .encode(
          x=alt.X("Timeframe:N", sort=["Current"],
                  axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8)),
          y=alt.Y("Category:N", sort=cat_order, axis=alt.Axis(title=None, labelLimit=420)),
          color=alt.Color("avg_score:Q",
                          scale=alt.Scale(scheme="blueorange", domain=[-vmax, 0, vmax]),
                          legend=alt.Legend(orient="right", title="Avg Score", gradientLength=160)),
          tooltip=[
              alt.Tooltip("Category:N"),
              alt.Tooltip("avg_score:Q", title="Avg Score", format=",.2f"),
              alt.Tooltip("n:Q", title="Count"),
          ],
      )
      .properties(width=heat_w, height=heat_h,
                  padding={"left": 6, "right": 6, "top": 6, "bottom": 6})
      .configure_view(strokeOpacity=0)
)

st.markdown('<div class="viz-center">', unsafe_allow_html=True)
st.altair_chart(cur_heat, use_container_width=False)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ---------- Controls ----------
all_cats = sorted(list(set().union(
    df48["Category"].dropna().unique(),
    df49["Category"].dropna().unique(),
    df50["Category"].dropna().unique(),
    df51["Category"].dropna().unique()
)))
ordered_cats = [c for c in preferred if c in all_cats] + [c for c in all_cats if c not in preferred]

c1, c2, c3 = st.columns([0.60, 0.50, 0.25])
with c1:
    show_cur_ticker_hm = st.checkbox("Show per-ticker current heatmap (category)", value=False)
with c2:
    sel = st.selectbox("Category", ordered_cats, index=0, key="rankings_category")
with c3:
    lock_axes_and_order = st.checkbox("Lock axes", value=False, help="Fix axes and align all charts by ticker A→Z")

# =========================================================
# Per-Ticker Heatmap — Current
#   - Title centered
#   - Chart centered
#   - Narrow column width like global heatmap
# =========================================================
if show_cur_ticker_hm:
    tm = (
        df48.loc[df48["Category"] == sel, ["Ticker","Ticker_name","Category","Date","model_score"]]
            .dropna(subset=["Ticker","model_score"])
            .assign(Timeframe="Current", score=lambda d: d["model_score"])
    )
    ticker_order = sorted(tm["Ticker"].unique().tolist())
    t_vmax  = float(max(1.0, tm["score"].abs().quantile(0.98)))
    t_w     = 175
    t_h     = max(420, 22 * max(1, len(ticker_order)) + 24)

    st.markdown(f'<div class="h-title">{sel} — Per-Ticker Markmentum Heatmap (Current)</div>', unsafe_allow_html=True)
    st.markdown('<div class="h-sub">Current Markmentum Score by ticker.</div>', unsafe_allow_html=True)

    cur_ticker_heat = (
        alt.Chart(tm)
          .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
          .encode(
              x=alt.X("Timeframe:N", sort=["Current"],
                      axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8)),
              y=alt.Y("Ticker:N", sort=ticker_order,
                      axis=alt.Axis(title=None, labelLimit=160, labelOverlap=False)),
              color=alt.Color("score:Q",
                              scale=alt.Scale(scheme="blueorange", domain=[-t_vmax, 0, t_vmax]),
                              legend=alt.Legend(orient="right", title="Score", gradientLength=160)),
              tooltip=[
                  alt.Tooltip("Ticker:N"),
                  alt.Tooltip("Ticker_name:N", title="Name"),
                  alt.Tooltip("score:Q", title="Current", format=",.2f"),
                  alt.Tooltip("Date:N", title="Date"),
              ],
          )
          .properties(width=t_w, height=t_h,
                      padding={"left": 6, "right": 6, "top": 6, "bottom": 6})
          .configure_view(strokeOpacity=0)
    )

    st.markdown('<div class="viz-center">', unsafe_allow_html=True)
    st.altair_chart(cur_ticker_heat, use_container_width=False)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# =========================================================
# Ranking Panels (4 charts)
#   - Render in 4 Streamlit columns (no hconcat → no Altair error)
#   - Each column is responsive; on small screens they wrap cleanly
# =========================================================
view48 = df48[df48["Category"] == sel].copy().sort_values("model_score", ascending=False)
view49 = df49[df49["Category"] == sel].copy().sort_values("Sharpe_Rank", ascending=False)
view50 = df50[df50["Category"] == sel].copy().sort_values("Sharpe", ascending=False)
view51 = df51[df51["Category"] == sel].copy().sort_values("Sharpe_Ratio_30D_Change", ascending=False)

if view48.empty and view49.empty and view50.empty and view51.empty:
    st.info(f"No tickers found for **{sel}**.")
    st.stop()

if lock_axes_and_order:
    y_order_all = sorted(set(view48["Ticker"]) | set(view49["Ticker"]) | set(view50["Ticker"]) | set(view51["Ticker"]))
else:
    y_order_48 = view48["Ticker"].tolist()
    y_order_49 = view49["Ticker"].tolist()
    y_order_50 = view50["Ticker"].tolist()
    y_order_51 = view51["Ticker"].tolist()

row_h   = 24
max_len = max(len(view48), len(view49), len(view50), len(view51))
chart_h = max(300, row_h * max_len + 120)

# 1) Model Score
base48 = (
    alt.Chart(view48)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order_all if lock_axes_and_order else y_order_48), title="Ticker"),
          x=alt.X("model_score:Q", title="Model Score"),
          href=alt.Href("url:N"),
          tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("model_score:Q", format=",.0f")],
      )
)
bars48 = base48.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos48  = base48.transform_filter("datum.model_score >= 0").mark_text(align="left",  baseline="middle", dx=4)\
                 .encode(text=alt.Text("model_score:Q", format=",.0f"))
neg48  = base48.transform_filter("datum.model_score < 0").mark_text(align="right", baseline="middle", dx=-10)\
                 .encode(text=alt.Text("model_score:Q", format=",.0f"))
chart48 = (bars48 + pos48 + neg48).properties(title="Markmentum Score Ranking", height=chart_h)

# 2) Sharpe Percentile Rank
base49 = (
    alt.Chart(view49)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order_all if lock_axes_and_order else y_order_49), title="Ticker"),
          x=alt.X("Sharpe_Rank:Q", title="Sharpe Percentile Rank", scale=alt.Scale(domain=[0,100])),
          href=alt.Href("url:N"),
          tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("Sharpe_Rank:Q", format=",.1f")],
      )
)
bars49  = base49.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
label49 = base49.mark_text(align="left", baseline="middle", dx=4)\
                 .encode(text=alt.Text("Sharpe_Rank:Q", format=",.1f"))
chart49 = (bars49 + label49).properties(title="Sharpe Percentile Ranking", height=chart_h)

# 3) Sharpe Ratio
base50 = (
    alt.Chart(view50)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order_all if lock_axes_and_order else y_order_50), title="Ticker"),
          x=alt.X("Sharpe:Q", title="Sharpe Ratio"),
          href=alt.Href("url:N"),
          tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("Sharpe:Q", format=",.1f")],
      )
)
bars50 = base50.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos50  = base50.transform_filter("datum.Sharpe >= 0").mark_text(align="left",  baseline="middle", dx=4)\
                 .encode(text=alt.Text("Sharpe:Q", format=",.1f"))
neg50  = base50.transform_filter("datum.Sharpe < 0").mark_text(align="right", baseline="middle", dx=-10)\
                 .encode(text=alt.Text("Sharpe:Q", format=",.1f"))
chart50 = (bars50 + pos50 + neg50).properties(title="Sharpe Ratio Ranking", height=chart_h)

# 4) Sharpe Ratio 30-Day Change
base51 = (
    alt.Chart(view51)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order_all if lock_axes_and_order else y_order_51), title="Ticker"),
          x=alt.X("Sharpe_Ratio_30D_Change:Q", title="Sharpe Ratio 30-Day Change"),
          href=alt.Href("url:N"),
          tooltip=["Ticker", "Ticker_name", "Category",
                   alt.Tooltip("Sharpe_Ratio_30D_Change:Q", format=",.1f")],
      )
)
bars51 = base51.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos51  = base51.transform_filter("datum.Sharpe_Ratio_30D_Change >= 0").mark_text(align="left",  baseline="middle", dx=4)\
                 .encode(text=alt.Text("Sharpe_Ratio_30D_Change:Q", format=",.1f"))
neg51  = base51.transform_filter("datum.Sharpe_Ratio_30D_Change < 0").mark_text(align="right", baseline="middle", dx=-10)\
                 .encode(text=alt.Text("Sharpe_Ratio_30D_Change:Q", format=",.1f"))
chart51 = (bars51 + pos51 + neg51).properties(title="Sharpe Ratio 30-Day Change", height=chart_h)

# Render in 4 columns (centered row; wraps on smaller screens)
cA, cB, cC, cD = st.columns(4)
with cA: st.altair_chart(chart48, use_container_width=True)
with cB: st.altair_chart(chart49, use_container_width=True)
with cC: st.altair_chart(chart50, use_container_width=True)
with cD: st.altair_chart(chart51, use_container_width=True)

st.markdown(
    "<div style='margin-top:6px; color:#6b7280; font-size:13px;'>"
    "Tip: <b>Click any bar</b> to open the Deep Dive for that ticker."
    "</div>",
    unsafe_allow_html=True,
)

# ---------- Footer ----------
st.markdown("---")
st.markdown(
    """
    <div style="font-size: 12px; color: gray;">
    © 2025 Markmentum Research. <b>Disclaimer</b>: This content is for informational purposes only.
    Nothing herein constitutes an offer to sell, a solicitation of an offer to buy, or a recommendation regarding any security,
    investment vehicle, or strategy. It does not represent legal, tax, accounting, or investment advice by Markmentum Research
    or its employees. The information is provided without regard to individual objectives or risk parameters and is general,
    non-tailored, and non-specific. Sources are believed to be reliable, but accuracy and completeness are not guaranteed.
    Markmentum Research is not responsible for errors, omissions, or losses arising from use of this material.
    Investments involve risk, and financial markets are subject to fluctuation. Consult your financial professional before
    making investment decisions.
    </div>
    """,
    unsafe_allow_html=True,
)