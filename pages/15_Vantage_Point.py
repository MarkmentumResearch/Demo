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



DATA_DIR = APP_DIR / "data"
SIGNAL_PATH = DATA_DIR / "signal_box.csv"

# -------- Controls --------
st.title("Vantage Point")
st.caption("All signals. One view.")
top_c1, top_c2 = st.columns([1,1])
with top_c1:
    timeframe = st.segmented_control(
        "Timeframe",
        options=["Daily","WTD","MTD","QTD"],
        default="Daily"
    )
with top_c2:
    view_mode = st.segmented_control(
        "View",
        options=["By Category","By Tickers"],
        default="By Category"
    )

# Macro Orientation universe (adjust as you wish)
MACRO_TICKERS = [
    "SPX","NDX","DJI","RUT",
    "XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY",
    "GLD","UUP","TLT","BTC-F"
]

# -------- Field maps (exact names from signal_box.csv) --------
RET_COL = {
    "Daily":   "day_pct_change",
    "WTD":     "week_pct_change",
    "MTD":     "month_pct_change",
    "QTD":     "quarter_pct_change",
}
SHARPE_D_COL = {
    "Daily":   "Sharpe_Rank_daily_change",
    "WTD":     "Sharpe_Rank_wtd_change",
    "MTD":     "Sharpe_Rank_mtd_change",
    "QTD":     "Sharpe_Rank_qtd_change",
}
MM_D_COL = {
    "Daily":   "MM_Score_daily_change",
    "WTD":     "MM_Score_wtd_change",
    "MTD":     "MM_Score_mtd_change",
    "QTD":     "MM_Score_qtd_change",
}

CURR_COLS = ["Sharpe_Rank","MM_Score","Tape_Bias"]
BASE_COLS = ["Date","Ticker","Ticker_name","Category","Close"]

@st.cache_data(ttl=86400, show_spinner=False)
def load_signal_box() -> pd.DataFrame:
    df = pd.read_csv(SIGNAL_PATH)
    # Light cleanup / ordering
    for col in ["Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

sb = load_signal_box()
if sb.empty:
    st.warning("signal_box.csv not found or empty.")
    st.stop()

def fmt_pct(v):
    try:
        return f"{float(v)*100:,.2f}%"
    except Exception:
        return ""

def fmt_int(v):
    try:
        return f"{int(round(float(v))):,}"
    except Exception:
        return ""

def mk_current(df: pd.DataFrame) -> pd.DataFrame:
    out = df[BASE_COLS + CURR_COLS].copy()
    out.rename(columns={
        "Ticker_name":"Name",
        "Sharpe_Rank":"Sharpe",
        "MM_Score":"MM"
    }, inplace=True)
    return out

def mk_changes(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    out = df[BASE_COLS + [RET_COL[tf], SHARPE_D_COL[tf], MM_D_COL[tf]]].copy()
    out.rename(columns={
        "Ticker_name":"Name",
        RET_COL[tf]: "% Return",
        SHARPE_D_COL[tf]: "Sharpe Δ",
        MM_D_COL[tf]: "MM Score Δ"
    }, inplace=True)
    # Pretty formatting
    out["% Return"] = out["% Return"].map(fmt_pct)
    out["Sharpe Δ"] = out["Sharpe Δ"].map(fmt_int)
    out["MM Score Δ"] = out["MM Score Δ"].map(fmt_int)
    return out

def render_two_panel(title: str, df_current: pd.DataFrame, df_tf: pd.DataFrame):
    st.subheader(title)
    c1, c_sp, c2 = st.columns([1.1, 0.08, 1.1])
    with c1:
        st.markdown("**Current — Sharpe / MM / Tape Bias**")
        st.dataframe(
            df_current[["Name","Ticker","Category","Sharpe","MM","Tape_Bias"]],
            use_container_width=True, height=520
        )
    with c2:
        st.markdown(f"**{timeframe} — % Return / Sharpe Δ / MM Score Δ**")
        st.dataframe(
            df_tf[["Name","Ticker","Category","% Return","Sharpe Δ","MM Score Δ"]],
            use_container_width=True, height=520
        )

# =========================================================
# 1) MACRO ORIENTATION (tickers)
# =========================================================
macro_df = sb[sb["Ticker"].isin(MACRO_TICKERS)].copy()
if not macro_df.empty:
    cur_tbl = mk_current(macro_df)
    chg_tbl = mk_changes(macro_df, timeframe)
    render_two_panel("Macro Orientation", cur_tbl, chg_tbl)
    row_spacer(8)

# =========================================================
# 2) CATEGORY AVERAGES
#    - Current: avg Sharpe, avg MM, mode Tape_Bias
#    - Changes: avg %Return, avg Sharpe Δ, avg MM Score Δ
# =========================================================
def _mode(series: pd.Series):
    try:
        return series.mode().iloc[0]
    except Exception:
        return ""

grp = sb.groupby("Category", dropna=True)

cat_cur = grp.agg({
    "Sharpe_Rank":"mean",
    "MM_Score":"mean",
    "Tape_Bias": _mode
}).reset_index().rename(columns={
    "Category":"Name",
    "Sharpe_Rank":"Sharpe",
    "MM_Score":"MM"
})
cat_cur.insert(1, "Ticker", "")  # placeholder for column consistency
cat_cur.insert(2, "Category", cat_cur["Name"])

cat_delta = grp.agg({
    RET_COL[timeframe]: "mean",
    SHARPE_D_COL[timeframe]: "mean",
    MM_D_COL[timeframe]: "mean"
}).reset_index().rename(columns={
    "Category":"Name",
    RET_COL[timeframe]:"% Return",
    SHARPE_D_COL[timeframe]:"Sharpe Δ",
    MM_D_COL[timeframe]:"MM Score Δ"
})
cat_delta.insert(1, "Ticker", "")
cat_delta.insert(2, "Category", cat_delta["Name"])
cat_delta["% Return"] = cat_delta["% Return"].map(fmt_pct)
cat_delta["Sharpe Δ"] = cat_delta["Sharpe Δ"].map(fmt_int)
cat_delta["MM Score Δ"] = cat_delta["MM Score Δ"].map(fmt_int)

render_two_panel("Category Averages", cat_cur, cat_delta)
row_spacer(8)

# =========================================================
# 3) TICKERS WITHIN SELECTED CATEGORY
# =========================================================
present_cats = sorted([c for c in sb["Category"].dropna().unique().tolist()])
pick = st.selectbox("Category (tickers view)", present_cats, index=0)
df_cat = sb[sb["Category"].eq(pick)].copy()
if not df_cat.empty:
    cur_tbl = mk_current(df_cat)
    chg_tbl = mk_changes(df_cat, timeframe)
    render_two_panel(f"Tickers — {pick}", cur_tbl, chg_tbl)
















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