# 11_Sharpe_Heatmap.py
# Sharpe Rank — Rank + Δ (Daily/WTD/MTD/QTD)
from pathlib import Path
import base64
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st
from urllib.parse import quote_plus

# ---------- Page ----------
st.cache_data.clear()
st.set_page_config(page_title="Sharpe Heatmap", layout="wide")

# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

# Sharpe sources (as specified)
CSV_BASE = DATA_DIR / "qry_graph_data_48.csv"  # Sharpe_Rank + daily change
CSV_WTD  = DATA_DIR / "qry_graph_data_49.csv"  # Sharpe_Rank_wtd_change
CSV_MTD  = DATA_DIR / "qry_graph_data_50.csv"  # Sharpe_Rank_mtd_change
CSV_QTD  = DATA_DIR / "qry_graph_data_51.csv"  # Sharpe_Rank_qtd_change

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

# --- Clickable Deep Dive helper & router (same UX as Performance/Markmentum pages)
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
# Helpers
# -------------------------
def _robust_vmax(series, q=0.98, floor=1.0, step=1.0):
    s = pd.to_numeric(series, errors="coerce").abs().dropna()
    if s.empty:
        return floor
    vmax = float(np.quantile(s, q))
    return max(floor, np.ceil(vmax / step) * step)

def _fmt_num(x, nd=0):
    try:
        if pd.isna(x): return ""
        return f"{float(x):,.{nd}f}"
    except Exception:
        return ""

# Rank cell tint: Buy green, Neutral gray, Sell red; stronger beyond ±100
def _Rank_cell_html(Rank: float, cap: float = 105.0) -> str:
    if Rank is None or pd.isna(Rank):
        return ""
    s = float(Rank)

    if s >= 25:
        rel = min(abs(s) / cap, 1.0)
        alpha = 0.12 + 0.28 * rel
        bg = f"rgba(16,185,129,{alpha:.3f})"
        color = "#0b513a"
    elif s <= -25:
        rel = min(abs(s) / cap, 1.0)
        alpha = 0.12 + 0.28 * rel
        bg = f"rgba(239,68,68,{alpha:.3f})"
        color = "#641515"
    else:
        bg = "rgba(156,163,175,0.18)"
        color = "#374151"

    label = _fmt_num(s, 0)
    return f'<span style="display:block; background:{bg}; color:{color}; padding:0 6px; border-radius:2px; text-align:right;">{label}</span>'

# Change column tint (independent scale per timeframe)
def _delta_cell_html(val: float, vmax: float) -> str:
    if val is None or pd.isna(val) or vmax is None or vmax <= 0:
        return ""
    s = min(abs(float(val)) / float(vmax), 1.0)
    alpha = 0.12 + 0.28 * s
    if val > 0:
        bg = f"rgba(16,185,129,{alpha:.3f})"
    elif val < 0:
        bg = f"rgba(239,68,68,{alpha:.3f})"
    else:
        bg = "transparent"
    label = _fmt_num(val, 0)
    return f'<span style="display:block; background:{bg}; padding:0 6px; border-radius:2px; text-align:right;">{label}</span>'

# -------------------------
# Load sources + assemble Sharpe frame
# -------------------------
@st.cache_data(show_spinner=False)
def load_sharpe_frames():
    # Base / daily
    base = pd.read_csv(CSV_BASE) if CSV_BASE.exists() else pd.DataFrame()
    if not base.empty and "Date" in base.columns:
        base["_dt"] = pd.to_datetime(base["Date"], errors="coerce")
        base = (base.sort_values(["Ticker","_dt"], ascending=[True, False])
                    .drop_duplicates(subset=["Ticker"], keep="first"))
    for c in ["Sharpe_Rank","previous_Sharpe_Rank","Sharpe_Rank_daily_change"]:
        if c in base.columns:
            base[c] = pd.to_numeric(base[c], errors="coerce")
    if "Sharpe_Rank_daily_change" not in base.columns or base["Sharpe_Rank_daily_change"].isna().all():
        if "Sharpe_Rank" in base.columns and "previous_Sharpe_Rank" in base.columns:
            base["Sharpe_Rank_daily_change"] = base["Sharpe_Rank"] - base["previous_Sharpe_Rank"]

    # WTD / MTD / QTD
    def _load_delta(p, delta_col):
        if not p.exists():
            return pd.DataFrame(columns=["Ticker", delta_col])
        df = pd.read_csv(p)
        if "Ticker" not in df.columns:
            return pd.DataFrame(columns=["Ticker", delta_col])
        df[delta_col] = pd.to_numeric(df.get(delta_col), errors="coerce")
        df = df[["Ticker", delta_col]].drop_duplicates("Ticker", keep="first")
        return df

    wtd = _load_delta(CSV_WTD, "Sharpe_Rank_wtd_change")
    mtd = _load_delta(CSV_MTD, "Sharpe_Rank_mtd_change")
    qtd = _load_delta(CSV_QTD, "Sharpe_Rank_qtd_change")

    # Merge
    df = base.copy()
    for add in (wtd, mtd, qtd):
        df = df.merge(add, on="Ticker", how="left")

    # Final schema (rename to common labels)
    df = df.rename(columns={
        "Ticker_name": "Name",
        "Sharpe_Rank": "Rank",
        "Sharpe_Rank_daily_change": "ΔDaily",
        "Sharpe_Rank_wtd_change":   "ΔWTD",
        "Sharpe_Rank_mtd_change":   "ΔMTD",
        "Sharpe_Rank_qtd_change":   "ΔQTD",
    })
    for c in ["Rank","ΔDaily","ΔWTD","ΔMTD","ΔQTD"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

Ranks = load_sharpe_frames()
if Ranks.empty:
    st.warning("Sharpe files not found or missing required columns.")
    st.stop()

# As-of
date_str = ""
if "Date" in Ranks.columns:
    dmax = pd.to_datetime(Ranks["Date"], errors="coerce").max()
    if pd.notna(dmax):
        date_str = f"{dmax.month}/{dmax.day}/{dmax.year}"

# -------------------------
# Shared CSS
# -------------------------
st.markdown("""
<style>
.card-wrap { display:flex; justify-content:center; }
.card{
  border:1px solid #cfcfcf; border-radius:8px; background:#fff;
  padding:12px 12px 10px 12px; width:100%;
  max-width:900px;
}
@media (max-width:1100px){
  .card { max-width:100%; }
}
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td {
  border:1px solid #d9d9d9; padding:6px 8px; font-size:13px;
  overflow:hidden; text-overflow:ellipsis;
}
.tbl th { background:#f2f2f2; font-weight:700; color:#1a1a1a; text-align:left; }
.tbl th:nth-child(n+3) { text-align:center; }
.tbl td:nth-child(n+3) { text-align:right; white-space:nowrap; }

.tbl col.col-name-wide   { width:22ch; min-width:22ch; max-width:22ch; }
.tbl col.col-ticker-nar  { width:7ch; }
.tbl col.col-num         { width:8ch; }

/* Center the Ticker column (2nd column) */
.tbl th:nth-child(2),
.tbl td:nth-child(2) { text-align: center; }

/* Make the ticker link fill the cell so the centering is perfect */
.tbl td:nth-child(2) a {
  display: inline-block;
  width: 100%;
}


.tbl th:nth-child(1), .tbl td:nth-child(1) { white-space:normal; overflow:visible; text-overflow:clip; }
.subnote { border-top:1px solid #e5e5e5; margin-top:8px; padding-top:10px; font-size:11px; color:#6c757d; }
.card h3 { margin:0 0 -6px 0; font-size:16px; font-weight:700; color:#1a1a1a; text-align:center; }
.card .subtitle { margin:0 0 8px 0; font-size:14px; font-weight:500; color:#6b7280; text-align:center; }
.vspace-16 { height:16px; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Title
# -------------------------
st.markdown(
    f"""
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:18px; font-weight:600; color:#1a1a1a;">
        Sharpe Percentile Rank Heatmap – {date_str}
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Macro Orientation
# -------------------------
macro_list = [
    "SPX","NDX","DJI","RUT",
    "XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY",
    "GLD","UUP","TLT","BTC=F"
]
Ranks["_dt"] = pd.to_datetime(Ranks["Date"], errors="coerce")
latest = (
    Ranks.sort_values(["Ticker","_dt"], ascending=[True, False])
          .drop_duplicates(subset=["Ticker"], keep="first")
)

m = latest[latest["Ticker"].isin(macro_list)].copy()
m["__ord__"] = m["Ticker"].map({t:i for i,t in enumerate(macro_list)})
m = m.sort_values(["__ord__"], kind="stable")
m["Ticker_link"] = m["Ticker"].map(_mk_ticker_link)

# independent scaling for deltas by timeframe (within macro card)
vmaxM = {
    "ΔDaily": _robust_vmax(m["ΔDaily"], q=0.98, floor=1.0, step=1.0),
    "ΔWTD":   _robust_vmax(m["ΔWTD"],   q=0.98, floor=1.0, step=1.0),
    "ΔMTD":   _robust_vmax(m["ΔMTD"],   q=0.98, floor=1.0, step=1.0),
    "ΔQTD":   _robust_vmax(m["ΔQTD"],   q=0.98, floor=1.0, step=1.0),
}

m_render = pd.DataFrame({
    "Name":   m["Name"],
    "Ticker": m["Ticker_link"],
    "Rank":  [ _Rank_cell_html(v) for v in m["Rank"] ],
    "Daily":  [ _delta_cell_html(v, vmaxM["ΔDaily"]) for v in m["ΔDaily"] ],
    "WTD":    [ _delta_cell_html(v, vmaxM["ΔWTD"])   for v in m["ΔWTD"]   ],
    "MTD":    [ _delta_cell_html(v, vmaxM["ΔMTD"])   for v in m["ΔMTD"]   ],
    "QTD":    [ _delta_cell_html(v, vmaxM["ΔQTD"])   for v in m["ΔQTD"]   ],
})

html_macro = m_render.to_html(index=False, classes="tbl", escape=False, border=0)
html_macro = html_macro.replace('class="dataframe tbl"', 'class="tbl"')
colgroup_macro = """
<colgroup>
  <col class="col-name-wide">
  <col class="col-ticker-nar">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
</colgroup>
""".strip()
html_macro = html_macro.replace('<table class="tbl">', f'<table class="tbl">{colgroup_macro}', 1)

st.markdown(
    f"""
    <div class="card-wrap">
      <div class="card">
        <h3>Macro Orientation</h3>
        <div class="subtitle">Current Sharpe Percentile Rank and Change by timeframe</div>
        {html_macro}
        <div class="subnote">Rank cells are High/Neutral/Low (green/gray/red); change columns use independent per-timeframe scales.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)

# -------------------------
# Category Averages card
# -------------------------
grouped = latest.groupby("Category", dropna=True, as_index=False).agg(
    Rank=("Rank","mean"),
    ΔDaily=("ΔDaily","mean"),
    ΔWTD=("ΔWTD","mean"),
    ΔMTD=("ΔMTD","mean"),
    ΔQTD=("ΔQTD","mean"),
)

preferred_order = [
    "Sector & Style ETFs","Indices","Futures","Currencies","Commodities",
    "Bonds","Yields","Volatility","Foreign",
    "Communication Services","Consumer Discretionary","Consumer Staples",
    "Energy","Financials","Health Care","Industrials","Information Technology",
    "Materials","Real Estate","Utilities","MR Discretion"
]
order_map = {name: i for i, name in enumerate(preferred_order)}
grouped["__ord__"] = grouped["Category"].map(order_map)
grouped = grouped.sort_values(["__ord__", "Category"], kind="stable").drop(columns="__ord__")

vmax_cat = {
    "ΔDaily": _robust_vmax(grouped["ΔDaily"], q=0.98, floor=1.0, step=1.0),
    "ΔWTD":   _robust_vmax(grouped["ΔWTD"],   q=0.98, floor=1.0, step=1.0),
    "ΔMTD":   _robust_vmax(grouped["ΔMTD"],   q=0.98, floor=1.0, step=1.0),
    "ΔQTD":   _robust_vmax(grouped["ΔQTD"],   q=0.98, floor=1.0, step=1.0),
}

g_render = pd.DataFrame({
    "Name":  grouped["Category"],
    "Rank": [ _Rank_cell_html(v) for v in grouped["Rank"] ],
    "Daily": [ _delta_cell_html(v, vmax_cat["ΔDaily"]) for v in grouped["ΔDaily"] ],
    "WTD":   [ _delta_cell_html(v, vmax_cat["ΔWTD"])   for v in grouped["ΔWTD"]   ],
    "MTD":   [ _delta_cell_html(v, vmax_cat["ΔMTD"])   for v in grouped["ΔMTD"]   ],
    "QTD":   [ _delta_cell_html(v, vmax_cat["ΔQTD"])   for v in grouped["ΔQTD"]   ],
})

html_cat = g_render.to_html(index=False, classes="tbl", escape=False, border=0)
html_cat = html_cat.replace('class="dataframe tbl"', 'class="tbl"')
colgroup = """
<colgroup>
  <col class="col-name-wide">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
</colgroup>
""".strip()
html_cat = html_cat.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

st.markdown(
    f"""
    <div class="card-wrap">
      <div class="card">
        <h3>Category Averages</h3>
        <div class="subtitle">Avg Sharpe Percentile Rank and Change by category and timeframe</div>
        {html_cat}
        <div class="subnote">Each change column uses an independent red/green scale; Rank cells use High/Neutral/Low shading.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)

# ===== Category Heatmap — ONE matrix (Rank + ΔDaily/ΔWTD/ΔMTD/ΔQTD), all blue↔orange =====
glong = grouped.melt(
    id_vars=["Category"],
    value_vars=["Rank", "ΔDaily", "ΔWTD", "ΔMTD", "ΔQTD"],
    var_name="Timeframe",
    value_name="Value",
)
glong["Category"] = pd.Categorical(glong["Category"], categories=preferred_order, ordered=True)

# Robust |max| per timeframe INCLUDING Rank; cap Rank's vmax at 105
vmax_tf = {}
for tf, sub in glong.groupby("Timeframe"):
    vmax = _robust_vmax(sub["Value"], q=0.98, floor=1.0, step=1.0)
    if tf == "Rank":
        vmax = min(105.0, max(vmax, 1.0))
    vmax_tf[tf] = vmax

# Normalize each cell by its timeframe-specific vmax → [-1, 1]
glong["norm"] = glong.apply(
    lambda r: float(np.clip((r["Value"] or 0.0) / (vmax_tf.get(r["Timeframe"], 1.0) or 1.0), -1, 1)),
    axis=1
)

timeframe_order = ["Rank", "ΔDaily", "ΔWTD", "ΔMTD", "ΔQTD"]

cat_hm = (
    alt.Chart(glong)
      .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
      .encode(
          x=alt.X("Timeframe:N",
                  sort=timeframe_order,
                  axis=alt.Axis(orient="top", title=None, labelAngle=0,
                                labelColor="#1a1a1a", labelFontSize=12, labelFlush=False)),
          y=alt.Y("Category:N",
                  sort=list(glong["Category"].cat.categories),
                  axis=alt.Axis(title=None, labelColor="#1a1a1a",
                                labelFlush=False, labelFontSize=12, labelLimit=240)),
          color=alt.Color("norm:Q",
                          scale=alt.Scale(scheme="blueorange", domain=[-1, 0, 1]),
                          legend=alt.Legend(orient="bottom",
                                            title="Avg Rank and Change",
                                            labelExpr="''")),
          tooltip=[
              alt.Tooltip("Category:N"),
              alt.Tooltip("Timeframe:N"),
              alt.Tooltip("Value:Q", title="Rank / Δ", format=",.0f"),
          ],
      )
      .properties(width=510, height=24 * len(preferred_order))
      .configure_view(strokeWidth=0)
)

st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)
st.markdown(
    """
    <div style="text-align:center; margin:0 0 8px;
                font-size:16px; font-weight:700; color:#1a1a1a;">
        Category Heatmap — Sharpe Percentile Rank and Changes
    </div>
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:14px; font-weight:500; color:#6b7280;">
        Average Sharpe Percentile Rank and Change by category and timeframe
    </div>
    """,
    unsafe_allow_html=True,
)
mid = st.columns([1, 1, 1])[1]
with mid:
    st.altair_chart(cat_hm, use_container_width=True)

# -------------------------
# Category selector — Table / Heatmap / Both
# -------------------------
cats_available = [c for c in preferred_order if c in latest["Category"].dropna().unique().tolist()]
default_cat = "Sector & Style ETFs" if "Sector & Style ETFs" in cats_available else (cats_available[0] if cats_available else None)

_, csel, _ = st.columns([1, 1, 1])
with csel:
    sel = st.selectbox("Category", cats_available, index=(cats_available.index(default_cat) if default_cat else 0))

col_left, col_center, col_right = st.columns([1, 1, 1])
with col_center:
    view_choice = st.radio(
        "View",
        ["Table", "Heatmap", "Both"],
        index=2,
        horizontal=True,
        label_visibility="visible",
    )

d = latest.loc[latest["Category"] == sel].copy()
d["Ticker_link"] = d["Ticker"].map(_mk_ticker_link)

vmax_sel = {
    "ΔDaily": _robust_vmax(d["ΔDaily"], q=0.98, floor=1.0, step=1.0),
    "ΔWTD":   _robust_vmax(d["ΔWTD"],   q=0.98, floor=1.0, step=1.0),
    "ΔMTD":   _robust_vmax(d["ΔMTD"],   q=0.98, floor=1.0, step=1.0),
    "ΔQTD":   _robust_vmax(d["ΔQTD"],   q=0.98, floor=1.0, step=1.0),
}

d_render = pd.DataFrame({
    "Name":   d["Name"],
    "Ticker": d["Ticker_link"],
    "Rank":  [ _Rank_cell_html(v) for v in d["Rank"] ],
    "Daily":  [ _delta_cell_html(v, vmax_sel["ΔDaily"]) for v in d["ΔDaily"] ],
    "WTD":    [ _delta_cell_html(v, vmax_sel["ΔWTD"])   for v in d["ΔWTD"]   ],
    "MTD":    [ _delta_cell_html(v, vmax_sel["ΔMTD"])   for v in d["ΔMTD"]   ],
    "QTD":    [ _delta_cell_html(v, vmax_sel["ΔQTD"])   for v in d["ΔQTD"]   ],
})

html_detail = d_render.to_html(index=False, classes="tbl", escape=False, border=0)
html_detail = html_detail.replace('class="dataframe tbl"', 'class="tbl"')
colgroup2 = """
<colgroup>
  <col class="col-name-wide">
  <col class="col-ticker-nar">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
  <col class="col-num">
</colgroup>
""".strip()
html_detail = html_detail.replace('<table class="tbl">', f'<table class="tbl">{colgroup2}', 1)

if view_choice in ("Table","Both"):
    st.markdown(
        f"""
        <div class="card-wrap">
          <div class="card">
            <h3>{sel} — Per Ticker</h3>
            <div class="subtitle">Current Sharpe Percentile Rank and Change by ticker and timeframe</div>
            {html_detail}
            <div class="subnote">Ticker links open the Deep Dive Dashboard. Change columns are independently scaled.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# Per-ticker heatmap (Rank + Δ columns, independent scale per timeframe, universe-wide)
# -------------------------
# Long frame across entire universe, INCLUDING Rank
tlong_all = latest.melt(
    id_vars=["Ticker","Name","Category"],
    value_vars=["Rank","ΔDaily","ΔWTD","ΔMTD","ΔQTD"],
    var_name="Timeframe",
    value_name="Value"
)

# Universe-wide robust vmax per timeframe; cap Rank at 105
vmax_univ_tf = {}
for tf, sub in tlong_all.groupby("Timeframe"):
    vmax = _robust_vmax(sub["Value"], q=0.98, floor=1.0, step=1.0)
    if tf == "Rank":
        vmax = min(105.0, max(vmax, 1.0))
    vmax_univ_tf[tf] = vmax

# Selected category long
tlong_sel = tlong_all.loc[tlong_all["Category"] == sel].copy()
tickers_order = sorted(tlong_sel["Ticker"].dropna().unique().tolist())

# Normalize each cell by the universe max for its timeframe → [-1, 1]
tlong_sel["norm"] = tlong_sel.apply(
    lambda r: np.clip(
        (r["Value"] or 0.0) / (vmax_univ_tf.get(r["Timeframe"], 1.0) or 1.0),
        -1, 1
    ),
    axis=1
)

hm_sel = (
    alt.Chart(tlong_sel)
      .mark_rect(stroke="#2b2f36", strokeWidth=0.6, strokeOpacity=0.95)
      .encode(
          x=alt.X("Timeframe:N",
                  sort=["Rank","ΔDaily","ΔWTD","ΔMTD","ΔQTD"],
                  axis=alt.Axis(orient="top", title=None, labelAngle=0,
                                labelColor="#1a1a1a", labelFlush=False, labelFontSize=12)),
          y=alt.Y("Ticker:N",
                  sort=tickers_order,
                  axis=alt.Axis(title=None, labelFontSize=12, labelColor="#1a1a1a",
                                labelFlush=False, labelLimit=260)),
          color=alt.Color("norm:Q",
                          scale=alt.Scale(scheme="blueorange", domain=[-1, 0, 1]),
                          legend=alt.Legend(orient="bottom",
                                            title="Rank and Change",
                                            labelExpr="''")),
          tooltip=[
              alt.Tooltip("Ticker:N"),
              alt.Tooltip("Timeframe:N", title="Timeframe"),
              alt.Tooltip("Value:Q", title="Rank / Δ", format=",.0f"),
          ],
      )
      .properties(width=520, height=max(360, 22*len(tickers_order)+24))
      .configure_view(strokeWidth=0)
)

if view_choice in ("Heatmap","Both"):
    st.markdown('<div class="vspace-16"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="text-align:center; margin:0 0 8px;
                    font-size:16px; font-weight:700; color:#1a1a1a;">
            {sel} — Per Ticker Heatmap Sharpe Percentile Rank and Changes
        </div>
        <div style="text-align:center; margin:-6px 0 14px;
                    font-size:14px; font-weight:500; color:#6b7280;">
            Current Sharpe Percentile Rank and Change by ticker and timeframe
        </div>
        """,
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1.2, .8, 1.2])
    with center:
        st.altair_chart(hm_sel, use_container_width=False)

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