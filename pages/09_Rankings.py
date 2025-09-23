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

st.cache_data.clear()

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – Ranking", layout="wide")

st.markdown(
    """
<style>
/* ---------- Responsive page width ---------- */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div {
  width: 95vw;
  max-width: 2100px;
  margin-left: auto;
  margin-right: auto;
}

/* ---------- Responsive grid: 3-up desktop, 2-up laptop, 1-up narrow ---------- */
div[data-testid="stHorizontalBlock"]{
  display:flex;
  flex-wrap: wrap;      /* allow wrapping by default */
  gap: 28px;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
  flex: 1 1 32%;
  min-width: 360px;
}

/* Typography + cards */
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card { border:1px solid #cfcfcf; border-radius:8px; background:#fff; padding:14px 14px 10px 14px; }
.card h3 { margin:0 0 10px 0; font-size:16px; font-weight:700; color:#1a1a1a; }
.small { font-size:12px; color:#666; }

/* Compact select control */
div[data-baseweb="select"] { max-width: 36ch !important; }

/* ---------- Breakpoints ---------- */
/* Big desktop (>=1500px): encourage 3-up rows */
@media (min-width: 1500px){
  div[data-testid="stHorizontalBlock"]{ flex-wrap: nowrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex-basis: 32%; }
}

/* Laptops (1000–1499px): switch to 2-up rows */
@media (max-width: 1499.98px){
  div[data-testid="stHorizontalBlock"]{ flex-wrap: wrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 48%; }
}

/* Narrow (<1000px): single column */
@media (max-width: 999.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 100%; }
}
</style>
""",
    unsafe_allow_html=True,
)

def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

CSV_PATH_48  = DATA_DIR / "qry_graph_data_48.csv"   # model_score
CSV_PATH_49  = DATA_DIR / "qry_graph_data_49.csv"   # Sharpe_Rank
CSV_PATH_50  = DATA_DIR / "qry_graph_data_50.csv"   # Sharpe
CSV_PATH_51  = DATA_DIR / "qry_graph_data_51.csv"   # Sharpe_Ratio_30D_Change

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

# --- clickable links helper ---
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
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    st.switch_page("pages/10_Deep_Dive_Dashboard.py")

# -------------------------
# Loaders
# -------------------------
last_modified = (DATA_DIR / "qry_graph_data_48.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv48(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker", "Ticker_name", "Category", "Date", "model_score"])
    df = pd.read_csv(path)
    for col in ("Ticker", "Ticker_name", "Category"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["Ticker"] = df["Ticker"].str.upper()
    df["model_score"] = pd.to_numeric(df["model_score"], errors="coerce")
    return df

last_modified = (DATA_DIR / "qry_graph_data_49.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv49(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker", "Ticker_name", "Category", "Date", "Sharpe_Rank"])
    df = pd.read_csv(path)
    df["Sharpe_Rank"] = pd.to_numeric(df["Sharpe_Rank"], errors="coerce")
    return df

last_modified = (DATA_DIR / "qry_graph_data_50.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv50(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker", "Ticker_name", "Category", "Date", "Sharpe"])
    df = pd.read_csv(path)
    df["Sharpe"] = pd.to_numeric(df["Sharpe"], errors="coerce")
    return df

last_modified = (DATA_DIR / "qry_graph_data_51.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_csv51(path: Path, _mtime: float = last_modified) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["Ticker", "Ticker_name", "Category", "Date", "Sharpe_Ratio_30D_Change"])
    df = pd.read_csv(path)
    df["Sharpe_Ratio_30D_Change"] = pd.to_numeric(df["Sharpe_Ratio_30D_Change"], errors="coerce")
    return df

df48 = load_csv48(CSV_PATH_48).copy()
df49 = load_csv49(CSV_PATH_49).copy()
df50 = load_csv50(CSV_PATH_50).copy()
df51 = load_csv51(CSV_PATH_51).copy()

if df48.empty or df49.empty or df50.empty or df51.empty:
    st.warning("Missing one of the input CSVs (48, 49, 50, or 51). Please confirm files exist.")
    st.stop()

# ===== title =====
def _mdy_fmt() -> str:
    return "%#m/%#d/%Y" if sys.platform.startswith("win") else "%-m/%-d/%Y"

def _first_date_from_csv(path: str, date_col: str = "date") -> str:
    df = pd.read_csv(path)
    if date_col not in df.columns:
        for alt in ("Date", "DATE"):
            if alt in df.columns:
                date_col = alt
                break
    dt = pd.to_datetime(df[date_col].iloc[0], errors="coerce")
    return "" if pd.isna(dt) else dt.strftime(_mdy_fmt())

date_text = _first_date_from_csv(str(CSV_PATH_48), date_col="date")
st.markdown(
    f"""
    <div style="text-align:center; font-size:20px; font-weight:600; color:#233; margin-top:8px; margin-bottom:12px;">
        Rankings – {date_text}
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# Global Heatmap — Current Markmentum Score (by Category)
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

row_h   = 26
chart_h = max(360, row_h * len(cat_order) + 24)
chart_w = 400
legend_w = 120

vmax = float(max(1.0, cat_cur["avg_score"].abs().quantile(0.98)))

cur_heat = (
    alt.Chart(cat_cur)
    .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
    .encode(
        x=alt.X("Timeframe:N", sort=["Current"],
                axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8,
                              labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
        y=alt.Y("Category:N", sort=cat_order,
                axis=alt.Axis(title=None, labelLimit=460, labelPadding=6,
                              labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
        color=alt.Color("avg_score:Q",
                        scale=alt.Scale(scheme="blueorange", domain=[-vmax, 0, vmax]),
                        legend=alt.Legend(orient="right", title="Avg Score", titleColor="#1a1a1a",
                                          labelColor="#1a1a1a", gradientLength=180, labelLimit=80)),
        tooltip=[alt.Tooltip("Category:N"),
                 alt.Tooltip("avg_score:Q", title="Avg Score", format=",.2f"),
                 alt.Tooltip("n:Q", title="Count")],
    )
    .properties(width=chart_w, height=chart_h,
                padding={"left": legend_w, "right": 0, "top": 6, "bottom": 6})
    .configure_view(strokeOpacity=0)
    .configure_axis(labelFontSize=12, titleFontSize=12)
)

# Center the heatmap INSIDE the card
pad_l, center_col, pad_r = st.columns([5, 5.6, 5])
with center_col:
    with st.container(border=True):
        st.markdown(
            '<div style="text-align:center;">'
            '<h3 style="margin:0;">Markmentum Heatmap — Current Score (by Category)</h3>'
            '<div class="small" style="margin-top:4px;">Average current Markmentum Score across tickers in each category.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        _l, _c, _r = st.columns([1, 6, 1])   # inner centering for the chart
        with _c:
            st.altair_chart(cur_heat, use_container_width=False)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# -------------------------
# Controls (toggle + selector + lock)
# -------------------------
custom_order = preferred
all_cats = [cat for cat in custom_order if cat in (
    set(df48["Category"].dropna().unique())
    | set(df49["Category"].dropna().unique())
    | set(df50["Category"].dropna().unique())
    | set(df51["Category"].dropna().unique())
)]
default_cat = "Sector Style ETFs"  # falls back to first if not matched
default_index = all_cats.index(default_cat) if default_cat in all_cats else 0

c_blank, left_toggle, c_sel, c_lock = st.columns([0.10, 0.30, 0.35, 0.15])
with left_toggle:
    show_cur_ticker_hm = st.checkbox("Show per-ticker current heatmap (category)", value=False, key="show_cur_ticker_hm")
with c_sel:
    sel = st.selectbox("Category", all_cats, index=default_index, key="rankings_category")
with c_lock:
    lock_axes_and_order = st.checkbox("Lock axes", value=False, help="Fix axes and align all charts by ticker A→Z")

# =========================
# Per-Ticker Heatmap — Current Markmentum Score (for selected category)
# =========================
if show_cur_ticker_hm:
    tm = (
        df48.loc[df48["Category"] == sel, ["Ticker", "Ticker_name", "Category", "Date", "model_score"]]
        .dropna(subset=["Ticker", "model_score"])
        .assign(Timeframe="Current", score=lambda d: d["model_score"])
    )
    ticker_order = sorted(tm["Ticker"].unique().tolist())

    row_h   = 22
    chart_h = max(360, row_h * max(1, len(ticker_order)) + 24)
    chart_w = 285
    legend_w = 120
    vmax = float(max(1.0, tm["score"].abs().quantile(0.98)))

    cur_ticker_heat = (
        alt.Chart(tm)
        .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
        .encode(
            x=alt.X("Timeframe:N", sort=["Current"],
                    axis=alt.Axis(orient="top", title=None, labelAngle=0, labelPadding=8,
                                  labelFlush=False, labelColor="#1a1a1a", labelFontSize=13)),
            y=alt.Y("Ticker:N", sort=ticker_order,
                    axis=alt.Axis(title=None, labelLimit=140, labelPadding=6,
                                  labelFlush=False, labelColor="#1a1a1a", labelFontSize=13, labelOverlap=False)),
            color=alt.Color("score:Q",
                            scale=alt.Scale(scheme="blueorange", domain=[-vmax, 0, vmax]),
                            legend=alt.Legend(orient="right", title="Score", titleColor="#1a1a1a",
                                              labelColor="#1a1a1a", gradientLength=180, labelLimit=80)),
            tooltip=[alt.Tooltip("Ticker:N"),
                     alt.Tooltip("Ticker_name:N", title="Name"),
                     alt.Tooltip("score:Q", title="Current", format=",.2f"),
                     alt.Tooltip("Date:N", title="Date")],
        )
        .properties(width=chart_w, height=chart_h,
                    padding={"left": legend_w, "right": 0, "top": 6, "bottom": 6})
        .configure_view(strokeOpacity=0)
        .configure_axis(labelFontSize=12, titleFontSize=12)
    )

    # Center the per-ticker heatmap INSIDE its card
    pad_l, center_col, pad_r = st.columns([5, 5.6, 5])
    with center_col:
        with st.container(border=True):
            st.markdown(
                f'<div style="text-align:center;"><h4 style="margin:0;">{sel} — Per-Ticker Markmentum Heatmap (Current)</h4>'
                f'<div class="small" style="margin-top:4px;">Current Markmentum Score by ticker.</div></div>',
                unsafe_allow_html=True,
            )
            _l, _c, _r = st.columns([1, 2.6, 1])  # inner centering
            with _c:
                st.altair_chart(cur_ticker_heat, use_container_width=False)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# -------------------------
# Helper: padded domain for nicer label space (visual)
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
# Filter dataframes for the selected category
# -------------------------
view48 = df48[df48["Category"] == sel].copy().sort_values("model_score", ascending=False)
view49 = df49[df49["Category"] == sel].copy().sort_values("Sharpe_Rank", ascending=False)
view50 = df50[df50["Category"] == sel].copy().sort_values("Sharpe", ascending=False)
view51 = df51[df51["Category"] == sel].copy().sort_values("Sharpe_Ratio_30D_Change", ascending=False)

if view48.empty and view49.empty and view50.empty and view51.empty:
    st.info(f"No tickers found for **{sel}**.")
    st.stop()

# y (row) order handling
if lock_axes_and_order:
    y_order = sorted(set(view48["Ticker"]) | set(view49["Ticker"]) | set(view50["Ticker"]) | set(view51["Ticker"]))
else:
    y_order_48 = view48["Ticker"].tolist()
    y_order_49 = view49["Ticker"].tolist()
    y_order_50 = view50["Ticker"].tolist()
    y_order_51 = view51["Ticker"].tolist()

chart_height = max(260, 24 * max(len(view48), len(view49), len(view50), len(view51)) + 120)

# -------------------------
# Chart #1: Model Score
# -------------------------
# use padded domain per-category (visual tweak)
category_ms_min = float(view48["model_score"].min() - 50) if not df48.empty else 0.0
category_ms_max = float(view48["model_score"].max() + 10) if not df48.empty else 0.0
ms_dom = padded_domain(pd.Series([category_ms_min, category_ms_max]), frac=0.06, min_pad=2.0)

x48 = alt.X("model_score:Q", title="Model Score", scale=alt.Scale(domain=ms_dom))
base48 = (
    alt.Chart(view48)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_48), title="Ticker"),
        x=x48,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("model_score:Q", format=",.0f")],
    )
)
bars48 = base48.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos48 = base48.transform_filter("datum.model_score >= 0").mark_text(align="left",  baseline="middle", dx=4)  \
                .encode(text=alt.Text("model_score:Q", format=",.0f"))
neg48 = base48.transform_filter("datum.model_score < 0").mark_text(align="right", baseline="middle", dx=-10) \
                .encode(text=alt.Text("model_score:Q", format=",.0f"))
chart48 = (bars48 + pos48 + neg48).properties(title="Markmentum Score Ranking", height=chart_height)

# -------------------------
# Chart #2: Sharpe Percentile Ranking
# -------------------------
x49 = alt.X("Sharpe_Rank:Q", title="Sharpe Percentile Rank", scale=alt.Scale(domain=[0, 100]))
base49 = (
    alt.Chart(view49)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_49), title="Ticker"),
        x=x49,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("Sharpe_Rank:Q", format=",.1f")],
    )
)
bars49 = base49.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
labels49 = base49.mark_text(align="left", baseline="middle", dx=4).encode(text=alt.Text("Sharpe_Rank:Q", format=",.1f"))
chart49 = (bars49 + labels49).properties(title="Sharpe Percentile Ranking", height=chart_height)

# -------------------------
# Chart #3: Sharpe Ratio
# -------------------------
category_ms_min3 = float(view50["Sharpe"].min() - 10) if not df50.empty else 0.0
category_ms_max3 = float(view50["Sharpe"].max() + 10) if not df50.empty else 0.0
ms_dom3 = padded_domain(pd.Series([category_ms_min3, category_ms_max3]), frac=0.06, min_pad=2.0)

x50 = alt.X("Sharpe:Q", title="Sharpe Ratio", scale=alt.Scale(domain=ms_dom3))
base50 = (
    alt.Chart(view50)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_50), title="Ticker"),
        x=x50,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("Sharpe:Q", format=",.1f")],
    )
)
bars50 = base50.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos50 = base50.transform_filter("datum.Sharpe >= 0").mark_text(align="left",  baseline="middle", dx=4)  \
                .encode(text=alt.Text("Sharpe:Q", format=",.1f"))
neg50 = base50.transform_filter("datum.Sharpe < 0").mark_text(align="right", baseline="middle", dx=-10) \
                .encode(text=alt.Text("Sharpe:Q", format=",.1f"))
chart50 = (bars50 + pos50 + neg50).properties(title="Sharpe Ratio Ranking", height=chart_height)

# -------------------------
# Chart #4: Sharpe Ratio 30-Day Change
# -------------------------
category_ms_min4 = float(view51["Sharpe_Ratio_30D_Change"].min() - 10) if not df51.empty else 0.0
category_ms_max4 = float(view51["Sharpe_Ratio_30D_Change"].max() + 30) if not df51.empty else 0.0
ms_dom4 = padded_domain(pd.Series([category_ms_min4, category_ms_max4]), frac=0.06, min_pad=2.0)

x51 = alt.X("Sharpe_Ratio_30D_Change:Q", title="Sharpe Ratio 30-Day Change", scale=alt.Scale(domain=ms_dom4))
base51 = (
    alt.Chart(view51)
    .transform_calculate(url="'?page=Deep%20Dive&ticker=' + datum.Ticker")
    .encode(
        y=alt.Y("Ticker:N", sort=(y_order if lock_axes_and_order else y_order_51), title="Ticker"),
        x=x51,
        href=alt.Href("url:N"),
        tooltip=["Ticker", "Ticker_name", "Category", alt.Tooltip("Sharpe_Ratio_30D_Change:Q", format=",.1f")],
    )
)
bars51 = base51.mark_bar(size=16, cornerRadiusEnd=3, color="#4472C4")
pos51 = base51.transform_filter("datum.Sharpe_Ratio_30D_Change >= 0").mark_text(align="left",  baseline="middle", dx=4)  \
                .encode(text=alt.Text("Sharpe_Ratio_30D_Change:Q", format=",.1f"))
neg51 = base51.transform_filter("datum.Sharpe_Ratio_30D_Change < 0").mark_text(align="right", baseline="middle", dx=-10) \
                .encode(text=alt.Text("Sharpe_Ratio_30D_Change:Q", format=",.1f"))
chart51 = (bars51 + pos51 + neg51).properties(title="Sharpe Ratio 30-Day Change", height=chart_height)

# -------------------------
# Side-by-side layout (4 charts) — centered on the screen
# -------------------------
left_spacer, mid, right_spacer = st.columns([1, 10, 1])
with mid:
    st.altair_chart(
        (chart48 | chart49 | chart50 | chart51)
            .configure_axis(labelFontSize=12, titleFontSize=12)
            .configure_view(strokeOpacity=0),
        use_container_width=True
    )

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