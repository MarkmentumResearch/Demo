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
st.set_page_config(page_title="Markmentum – Morning Compass", layout="wide")

# ---- LAYOUT & WIDTH TUNING (Cloud parity + your constraints) ----





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
    st.switch_page("pages/13_Deep_Dive_Dashboard.py")

def row_spacer(height_px: int = 14):
    st.markdown(f"<div style='height:{height_px}px'></div>", unsafe_allow_html=True)

# -------------------------
# Morning Compass – styling
# -------------------------
# -------------------------
# Morning Compass – styling
# -------------------------
st.markdown("""
<style>
/* Center the single card on the page */
.card-wrap { display:flex; justify-content:center; }
.card { 
  border:1px solid #cfcfcf; border-radius:8px; background:#fff;
  padding:12px 12px 8px 12px; width:100%;
  max-width:1320px;  /* was 1120px -> more room so names show */
}

/* Table styling to match Daily Overview */
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td {
  border:1px solid #d9d9d9; padding:6px 8px; font-size:13px;
  overflow:hidden; text-overflow:ellipsis;
}
.tbl th { background:#f2f2f2; font-weight:700; color:#1a1a1a; text-align:left; }

/* Alignment rules */
.tbl th:nth-child(2), .tbl td:nth-child(2) { text-align:center; }    /* Ticker centered */

/* HEADERS from Close..MM Score Delta centered */
.tbl th:nth-child(n+3) { text-align:center; }

/* CELLS from Close..MM Score Delta right-aligned */
.tbl td:nth-child(n+3) { text-align:right; white-space:nowrap; }

/* Name column = 40ch, allow wrapping so full name shows */
.tbl col.col-name { min-width:40ch; width:40ch; max-width:40ch; }
.tbl th:nth-child(1), .tbl td:nth-child(1) {
  white-space:normal;               /* allow wrap */
  overflow:visible; text-overflow:clip;
}

/* Keep ticker links bold without underline */
.tbl a { text-decoration:none; font-weight:600; }
</style>
""", unsafe_allow_html=True)


# -------------------------
# Load Morning Compass CSV
# -------------------------
@st.cache_data(show_spinner=False)
def load_mc_73(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df

df73 = load_mc_73(DATA_DIR / "qry_graph_data_73.csv")

# -------------------------
# Page title under the logo
# -------------------------
date_str = ""
if not df73.empty and "Date" in df73.columns:
    asof = pd.to_datetime(df73["Date"], errors="coerce").max()
    if pd.notna(asof):
        date_str = f"{asof.month}/{asof.day}/{asof.year}"

st.markdown(
    f"""
    <div style="text-align:center; margin:-6px 0 14px;
                font-size:18px; font-weight:600; color:#1a1a1a;">
        Morning Compass – {date_str}
    </div>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# Card: Morning Compass table
# -------------------------
required_cols = [
    "Date","Ticker","Ticker_name","Close",
    "daily_Return","day_pr_low","day_pr_high",
    "day_rr_ratio","model_score","model_score_delta"
]

if df73.empty or not all(c in df73.columns for c in required_cols):
    st.info("Morning Compass: `qry_graph_data_73.csv` is missing or columns are incomplete.")
else:
    df_render = df73.copy()
    df_render["Ticker"] = df_render["Ticker"].apply(_mk_ticker_link)

    # formatters
    def fmt_num(x, nd=2):
        try:
            if pd.isna(x): return ""
            return f"{float(x):,.{nd}f}"
        except Exception: return ""

    def fmt_pct(x, nd=2):
        try:
            if pd.isna(x): return ""
            return f"{float(x)*100:,.{nd}f}%"
        except Exception: return ""

    def fmt_int(x):
        try:
            if pd.isna(x): return ""
            return f"{int(round(float(x))):,}"
        except Exception: return ""

    # Diverging tint for Risk/Reward (−cap … +cap), subtle + readable
    def rr_tinted_html(x, cap=3.0):
        try:
            if pd.isna(x): 
                return ""
            v = float(x)
        except Exception:
            return ""

        # scale 0..1 (capped), keep near-zero very light
        s = min(abs(v) / cap, 1.0)
        alpha = 0.12 + 0.28 * s     # 0.12 → 0.40 opacity

        if v > 0:
            # green (tailwind-ish 10B981)
            bg = f"rgba(16,185,129,{alpha:.3f})"
        elif v < 0:
            # red (EF4444)
            bg = f"rgba(239,68,68,{alpha:.3f})"
        else:
            bg = "transparent"

        # numeric label with 1 decimal, same as before
        label = f"{v:,.1f}"
        return f'<span style="display:block; background:{bg}; padding:0 4px; border-radius:2px;">{label}</span>'

    df_card = pd.DataFrame({
    "Name":          df_render["Ticker_name"],
    "Ticker":        df_render["Ticker"],
    "Close":         df_render["Close"].map(lambda v: fmt_num(v, 2)),
    "% Delta":       df_render["daily_Return"].map(lambda v: fmt_pct(v, 2)),   # renamed
    "Probable Low":  df_render["day_pr_low"].map(lambda v: fmt_num(v, 2)),
    "Probable High": df_render["day_pr_high"].map(lambda v: fmt_num(v, 2)),
    "Risk/Reward":   df_render["day_rr_ratio"].map(rr_tinted_html),
    "MM Score":      df_render["model_score"].map(fmt_int),
    "MM Score Delta":df_render["model_score_delta"].map(fmt_int),              # renamed
    })

    # Clean HTML (no border attr, no 'dataframe' class)
    table_html = df_card.to_html(index=False, classes="tbl", escape=False, border=0)
    table_html = table_html.replace('class="dataframe tbl"', 'class="tbl"')

    # Insert a proper colgroup AFTER the opening <table class="tbl">
    colgroup = """
    <colgroup>
    <col class="col-name"> <!-- Name (40ch) -->
    <col>                   <!-- Ticker (center) -->
    <col>                   <!-- Close (right) -->
    <col>                   <!-- % Delta (right) -->
    <col>                   <!-- Probable Low (right) -->
    <col>                   <!-- Probable High (right) -->
    <col>                   <!-- Risk/Reward (right) -->
    <col>                   <!-- MM Score (right) -->
    <col>                   <!-- MM Score Delta (right) -->
    </colgroup>
    """.strip()

    table_html = table_html.replace('<table class="tbl">', f'<table class="tbl">{colgroup}', 1)

    # Centered card, no inner title
    st.markdown(f'<div class="card-wrap"><div class="card">{table_html}</div></div>', unsafe_allow_html=True)





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