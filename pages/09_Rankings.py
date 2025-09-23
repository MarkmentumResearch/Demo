# 09_Rankings_cloud.py
# Markmentum — Rankings (render-only fixes for consistent cross-device layout)

from pathlib import Path
import base64
import sys
from urllib.parse import quote_plus

import altair as alt
import pandas as pd
import streamlit as st

# -------------------------
# Page setup
# -------------------------
st.cache_data.clear()
st.set_page_config(page_title="Markmentum – Rankings", layout="wide")

# -------------------------
# Global CSS (responsive container, centered charts, hide bordered-container "decoration")
# -------------------------
st.markdown("""
<style>
/* Page container width */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div {
  width: 95vw;
  max-width: 2100px;
  margin-left: auto;
  margin-right: auto;
}

/* Hide the little header "decoration" strip from bordered containers */
div[data-testid="stDecoration"] { display: none !important; }

/* Grid baseline */
div[data-testid="stHorizontalBlock"]{
  display:flex; flex-wrap: wrap; gap: 28px;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
  flex: 1 1 32%; min-width: 360px;
}

/* Typography + card shell */
html, body, [class^="css"], .stMarkdown, .stText, .stDataFrame, .stTable, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card {
  border:1px solid #cfcfcf; border-radius:10px; background:#fff;
  padding:16px 16px 14px 16px;
}
.card h3, .card h4 {
  margin:0 0 8px 0; font-weight:700; color:#1a1a1a; text-align:center;
}
.card h3 { font-size: 20px; }
.card h4 { font-size: 16px; }
.small { font-size:12px; color:#666; text-align:center; }

/* Utility: center the chart block */
.viz-center { display:flex; justify-content:center; }

/* Compact select */
div[data-baseweb="select"] { max-width: 36ch !important; }

/* Breakpoints */
@media (min-width: 1500px){
  div[data-testid="stHorizontalBlock"]{ flex-wrap: nowrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex-basis: 32%; }
}
@media (max-width: 1499.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 48%; }
}
@media (max-width: 999.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 100%; }
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

CSV48 = DATA_DIR / "qry_graph_data_48.csv"   # model_score
CSV49 = DATA_DIR / "qry_graph_data_49.csv"   # Sharpe_Rank
CSV50 = DATA_DIR / "qry_graph_data_50.csv"   # Sharpe
CSV51 = DATA_DIR / "qry_graph_data_51.csv"   # Sharpe_Ratio_30D_Change

# -------------------------
# Helpers
# -------------------------
def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

def _mdy_fmt() -> str:
    return "%#m/%#d/%Y" if sys.platform.startswith("win") else "%-m/%-d/%Y"

def _first_date_from_csv(path: Path, date_col: str = "date") -> str:
    if not path.exists():
        return ""
    df = pd.read_csv(path)
    if date_col not in df.columns:
        for alt in ("Date", "DATE"):
            if alt in df.columns:
                date_col = alt
                break
    dt = pd.to_datetime(df[date_col].iloc[0], errors="coerce")
    return "" if pd.isna(dt) else dt.strftime(_mdy_fmt())

def _mk_ticker_link(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if not t:
        return ""
    return (f'<a href="?page=Deep%20Dive&ticker={quote_plus(t)}" '
            f'target="_self" rel="noopener" '
            f'style="text-decoration:none; font-weight:600;">{t}</a>')

# Simple router for deep-dive links
qp = st.query_params
if (qp.get("page") or "").replace("%20", " ").strip().lower() == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    # Adjust if your deep-dive filename differs
    st.switch_page("pages/11_Deep_Dive_Dashboard.py")

@st.cache_data(show_spinner=False)
def load_csv(path: Path, numeric_cols: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if numeric_cols:
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# -------------------------
# Data
# -------------------------
df48 = load_csv(CSV48, numeric_cols=["model_score"])
df49 = load_csv(CSV49, numeric_cols=["Sharpe_Rank"])
df50 = load_csv(CSV50, numeric_cols=["Sharpe"])
df51 = load_csv(CSV51, numeric_cols=["Sharpe_Ratio_30D_Change"])

if any(df.empty for df in [df48, df49, df50, df51]):
    st.warning("One or more CSVs (48–51) are missing or empty.")
    st.stop()

# -------------------------
# Header
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

st.markdown(
    f"""
    <div style="text-align:center; font-size:20px; font-weight:600; color:#233; margin-top:4px; margin-bottom:12px;">
        Rankings – {_first_date_from_csv(CSV48)}
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# Global Heatmap — Current Score (by Category)
#   - fixed width (so it doesn’t stretch)
#   - centered inside a “card”
# =========================
cat_cur = (
    df48[["Category", "model_score"]]
    .dropna(subset=["Category", "model_score"])
    .groupby("Category", as_index=False)
    .agg(avg_score=("model_score", "mean"), n=("model_score", "size"))
    .assign(Timeframe="Current")
)

preferred = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities","Bonds & Yields","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples","Energy","Financials",
    "Health Care","Industrials","Information Technology","Materials","Real Estate","Utilities","MR Discretion"
]
present = list(cat_cur["Category"].unique())
cat_order = [c for c in preferred if c in present] + [c for c in present if c not in preferred]

vmax = float(max(1.0, cat_cur["avg_score"].abs().quantile(0.98)))

heat_w  = 640   # fixed plot width (legend sits outside)
heat_h  = max(380, 26 * len(cat_order) + 24)

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
                  padding={"left": 8, "right": 8, "top": 6, "bottom": 6})
      .configure_view(strokeOpacity=0)
)

with st.container():  # no border; we draw our own "card"
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3>Markmentum Heatmap — Current Score (by Category)</h3>', unsafe_allow_html=True)
    st.markdown('<div class="small">Average current Markmentum Score across tickers in each category.</div>', unsafe_allow_html=True)
    st.markdown('<div class="viz-center">', unsafe_allow_html=True)
    st.altair_chart(cur_heat, use_container_width=False)
    st.markdown('</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# =========================
# Controls
# =========================
all_cats = sorted(list(set().union(
    df48["Category"].dropna().unique(),
    df49["Category"].dropna().unique(),
    df50["Category"].dropna().unique(),
    df51["Category"].dropna().unique()
)))
ordered_cats = [c for c in preferred if c in all_cats] + [c for c in all_cats if c not in preferred]

c1, c2, c3 = st.columns([0.36, 0.34, 0.30])
with c1:
    show_cur_ticker_hm = st.checkbox("Show per-ticker current heatmap (category)", value=False)
with c2:
    sel = st.selectbox("Category", ordered_cats, index=0, key="rankings_category")
with c3:
    lock_axes_and_order = st.checkbox("Lock axes", value=False, help="Fix axes and align all charts by ticker A→Z")

# =========================
# Per-Ticker Heatmap — Current (centered, fixed width)
# =========================
if show_cur_ticker_hm:
    tm = (
        df48.loc[df48["Category"] == sel, ["Ticker", "Ticker_name", "Category", "Date", "model_score"]]
        .dropna(subset=["Ticker", "model_score"])
        .assign(Timeframe="Current", score=lambda d: d["model_score"])
    )
    ticker_order = sorted(tm["Ticker"].unique().tolist())

    t_heat_w = 560
    t_heat_h = max(380, 22 * max(1, len(ticker_order)) + 24)
    t_vmax   = float(max(1.0, tm["score"].abs().quantile(0.98)))

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
          .properties(width=t_heat_w, height=t_heat_h,
                      padding={"left": 8, "right": 8, "top": 6, "bottom": 6})
          .configure_view(strokeOpacity=0)
    )

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<h4>{sel} — Per-Ticker Markmentum Heatmap (Current)</h4>', unsafe_allow_html=True)
        st.markdown('<div class="small">Current Markmentum Score by ticker.</div>', unsafe_allow_html=True)
        st.markdown('<div class="viz-center">', unsafe_allow_html=True)
        st.altair_chart(cur_ticker_heat, use_container_width=False)
        st.markdown('</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# =========================
# Ranking Panels (4 charts) — centered band, robust across widths
# =========================
view48 = df48[df48["Category"] == sel].copy().sort_values("model_score", ascending=False)
view49 = df49[df49["Category"] == sel].copy().sort_values("Sharpe_Rank", ascending=False)
view50 = df50[df50["Category"] == sel].copy().sort_values("Sharpe", ascending=False)
view51 = df51[df51["Category"] == sel].copy().sort_values("Sharpe_Ratio_30D_Change", ascending=False)

if view48.empty and view49.empty and view50.empty and view51.empty:
    st.info(f"No tickers found for **{sel}**.")
    st.stop()

# y-axis order
if lock_axes_and_order:
    y_order = sorted(set(view48["Ticker"]) | set(view49["Ticker"]) | set(view50["Ticker"]) | set(view51["Ticker"]))
else:
    y_order_48 = view48["Ticker"].tolist()
    y_order_49 = view49["Ticker"].tolist()
    y_order_50 = view50["Ticker"].tolist()
    y_order_51 = view51["Ticker"].tolist()

row_h     = 24
chart_h   = max(300, row_h * max(len(view48), len(view49), len(view50), len(view51)) + 120)
panel_pad = {"left": 8, "right": 8, "top": 4, "bottom": 4}

# 1) Model Score
base48 = (
    alt.Chart(view48)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_48), title="Ticker"),
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
chart48 = (bars48 + pos48 + neg48).properties(title="Markmentum Score Ranking",
                                              height=chart_h, padding=panel_pad)

# 2) Sharpe Percentile Rank
base49 = (
    alt.Chart(view49)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_49), title="Ticker"),
          x=alt.X("Sharpe_Rank:Q", title="Sharpe Percentile Rank", scale=alt.Scale(domain=[0, 100])),
          href=alt.Href("url:N"),
          tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("Sharpe_Rank:Q", format=",.1f")],
      )
)
bars49  = base49.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
label49 = base49.mark_text(align="left", baseline="middle", dx=4)\
                 .encode(text=alt.Text("Sharpe_Rank:Q", format=",.1f"))
chart49 = (bars49 + label49).properties(title="Sharpe Percentile Ranking",
                                        height=chart_h, padding=panel_pad)

# 3) Sharpe Ratio
base50 = (
    alt.Chart(view50)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_50), title="Ticker"),
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
chart50 = (bars50 + pos50 + neg50).properties(title="Sharpe Ratio Ranking",
                                              height=chart_h, padding=panel_pad)

# 4) Sharpe Ratio 30-Day Change
base51 = (
    alt.Chart(view51)
      .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
      .encode(
          y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_51), title="Ticker"),
          x=alt.X("Sharpe_Ratio_30D_Change:Q", title="Sharpe Ratio 30-Day Change"),
          href=alt.Href("url:N"),
          tooltip=[
              "Ticker", "Ticker_name", "Category",
              alt.Tooltip("Sharpe_Ratio_30D_Change:Q", format=",.1f")
          ],
      )
)
bars51 = base51.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos51  = base51.transform_filter("datum.Sharpe_Ratio_30D_Change >= 0").mark_text(align="left",  baseline="middle", dx=4)\
                 .encode(text=alt.Text("Sharpe_Ratio_30D_Change:Q", format=",.1f"))
neg51  = base51.transform_filter("datum.Sharpe_Ratio_30D_Change < 0").mark_text(align="right", baseline="middle", dx=-10)\
                 .encode(text=alt.Text("Sharpe_Ratio_30D_Change:Q", format=",.1f"))
chart51 = (bars51 + pos51 + neg51).properties(title="Sharpe Ratio 30-Day Change",
                                              height=chart_h, padding=panel_pad)

# Concat with | (avoids the v5 hconcat subspec error); modest spacing keeps it centered
concat = (chart48 | chart49 | chart50 | chart51).configure_view(strokeOpacity=0).configure_axis(
    labelFontSize=12, titleFontSize=12
).resolve_scale(
    x='independent', y='independent'
).properties(spacing=24)

# Single full-width container — Altair handles centering within
st.altair_chart(concat, use_container_width=True)

st.markdown(
    "<div style='margin-top:6px; color:#6b7280; font-size:13px;'>"
    "Tip: <b>Click any bar</b> to open the Deep Dive for that ticker."
    "</div>",
    unsafe_allow_html=True,
)

# -------------------------
# Footer
# -------------------------
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