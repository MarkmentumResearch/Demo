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
st.markdown("""
<style>
.card { border:1px solid #cfcfcf; border-radius:8px; background:#fff; padding:12px; }
.card h3 { margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a; }
.tbl { border-collapse: collapse; width: 100%; table-layout: auto; }  /* was fixed */
.tbl th, .tbl td { border:1px solid #d9d9d9; padding:6px 8px; font-size:13px; overflow:hidden; text-overflow:ellipsis; }
.tbl th { background:#f2f2f2; font-weight:700; text-align:left; }
.center { text-align:center; }
.right  { text-align:right; white-space:nowrap; }
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

    # Keep Deep Dive link on Ticker
    df_render["Ticker"] = df_render["Ticker"].apply(_mk_ticker_link)

    # --- Formatting helpers ---
    def fmt_num(x, nd=2):
        try:
            if pd.isna(x): return ""
            return f"{float(x):,.{nd}f}"
        except Exception:
            return ""

    def fmt_pct(x, nd=2):
        try:
            if pd.isna(x): return ""
            return f"{float(x)*100:,.{nd}f}%"
        except Exception:
            return ""

    def fmt_int(x):
        try:
            if pd.isna(x): return ""
            return f"{int(round(float(x))):,}"
        except Exception:
            return ""

    # Build in the new order (drop Date from the card view)
    df_card = pd.DataFrame({
        "Name":            df_render["Ticker_name"],
        "Ticker":          df_render["Ticker"],
        "Close":           df_render["Close"].map(lambda v: fmt_num(v, 2)),
        "% ▲":            df_render["daily_Return"].map(lambda v: fmt_pct(v, 2)),
        "Probable Low":    df_render["day_pr_low"].map(lambda v: fmt_num(v, 2)),
        "Probable High":   df_render["day_pr_high"].map(lambda v: fmt_num(v, 2)),
        "Risk/Reward":     df_render["day_rr_ratio"].map(lambda v: fmt_num(v, 1)),
        "MM Score":        df_render["model_score"].map(fmt_int),
        "MM Score ▲":      df_render["model_score_delta"].map(fmt_int),
    })

    # HTML table with a colgroup to set widths (Name = 40ch; others auto)
    table_html = df_card.to_html(index=False, classes="tbl", escape=False)
    colgroup = """
    <colgroup>
      <col style="width:40ch">
      <col>
      <col>
      <col>
      <col>
      <col>
      <col>
      <col>
      <col>
    </colgroup>
    """
    # Inject colgroup right after <table ...>
    table_html = table_html.replace("<table ", "<table " + colgroup, 1)

    st.markdown(
        f"""
        <div class="card">
          <h3>Morning Compass</h3>
          {table_html}
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