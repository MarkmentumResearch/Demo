# mr_signals_v1.py — Signals page
# Layout mirrors mr_vol_spreads_v4.py: Row 1 = 3 cards, Row 2 = 1 card

from pathlib import Path
import base64
import textwrap
import pandas as pd
import streamlit as st
import os, datetime as dt
from urllib.parse import quote_plus

# -------------------------
# Page & shared style (same as Overview / Vol Spreads)
# -------------------------
st.set_page_config(page_title="Markmentum – Signals", layout="wide")

st.markdown("""
<style>
/* ---------------- Base layout ---------------- */
div[data-testid="stHorizontalBlock"]{
  display:flex;
  flex-wrap: wrap;
  gap: 28px;
}

/* Each Streamlit column behaves like a grid item */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
  flex: 1 1 32%;                 /* desktop target ~3-up */
  min-width: 300px;              /* allow 3-up comfortably on wide screens */
}

/* Container width & side margins */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div {
  width: 95vw;
  max-width: 2100px;
  margin-left: auto;
  margin-right: auto;
}

/* Base typography + card shell */
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card {
  border: 1px solid #cfcfcf;
  border-radius: 8px;
  background: #fff;
  padding: 12px 12px 8px 12px;
  box-shadow: 0 0 0 rgba(0,0,0,0);
  max-width: 720px;            /* standard card width for non-desktop */
  width: 100%;
}
.card h3 { margin: 0 0 8px 0; font-size: 16px; font-weight: 700; color:#1a1a1a; }

/* Table */
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td { border: 1px solid #d9d9d9; padding: 6px 8px; font-size: 13px; overflow:hidden; text-overflow:ellipsis; }
.tbl th { background: #f2f2f2; font-weight: 700; text-align: left; }
.center { text-align: center; }
.right  { text-align: right; white-space: nowrap; }

/* --- Column widths & no-wrap (override any inline styles) --- */
.tbl thead th:nth-child(1), .tbl tbody td:nth-child(1){
  white-space: nowrap; min-width:11ch !important; width:39ch !important; max-width:39ch !important;
}
.tbl thead th:nth-child(2), .tbl tbody td:nth-child(2){ width:74px !important; }
.tbl thead th:nth-child(3), .tbl tbody td:nth-child(3){
  white-space: nowrap; min-width:6ch !important; width:22ch !important; max-width:22ch !important;
}
.tbl thead th:nth-child(4), .tbl tbody td:nth-child(4){ width:90px; }

/* ---------------- Breakpoints ---------------- */

/* DESKTOP (>=1500px): force 3-up, cards can expand within their column */
@media (min-width: 1500px){
  div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
    flex: 0 0 32%;
    min-width: 300px;
  }
  .card { max-width: none; }   /* let desktop cards fill their columns */
}

/* NON-DESKTOP (<1500px): ALWAYS 1-up, centered, fixed standard width */
@media (max-width: 1499.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
    flex: 0 0 100%;
  }
  .card{
    max-width: 720px;          /* standard width */
    margin-left: auto;
    margin-right: auto;
  }
  /* Slightly loosen text columns for readability on smaller screens */
  .tbl thead th:nth-child(1), .tbl tbody td:nth-child(1){ width:36ch !important; max-width:36ch !important; }
  .tbl thead th:nth-child(3), .tbl tbody td:nth-child(3){ width:22ch !important; max-width:22ch !important; }
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Paths (same pattern as the other pages)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

# CSVs for this page
CSV_FILES = [
    (44, "Lowest Sharpe Percentile Rank"),   # shows Sharpe_Rank
    (45, "Highest Sharpe Percentile Rank"),  # shows Sharpe_Rank
    (46, "Highest Upside"),                  # shows change_pct
    (47, "Highest Downside"),                # shows change_pct
]

# -------------------------
# Helpers (same approach as Overview / Vol Spreads)
# -------------------------
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
    st.switch_page("pages/11_Deep_Dive_Dashboard.py")




def row_spacer(height_px: int = 14):
    st.markdown(f"<div style='height:{height_px}px'></div>", unsafe_allow_html=True)

def _image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

def _pick(df: pd.DataFrame, candidates, default=None):
    """Case-tolerant column picker."""
    for c in candidates:
        if c in df.columns:
            return c
        for col in df.columns:
            if col.lower() == c.lower():
                return col
    return default

def _fmt_1dec(val):
    try:
        return f"{float(val):,.1f}"
    except Exception:
        return "—"
def _fmt_pct1(val):
    try:
        return f"{float(val) * 100:,.1f}%"
    except Exception:
        return "—"

def _table_html(title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    # tolerant mapping for standard names used in your CSVs
    cmap = {c.lower(): c for c in df.columns}
    tcol = cmap.get("ticker") or "Ticker"
    ncol = cmap.get("ticker_name") or cmap.get("company") or "Company"
    ccol = cmap.get("category") 

    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"""
<tr>
  <td class="company">{r.get(ncol, "")}</td>
  <td class="center" style="width:74px">{_mk_ticker_link(r.get(tcol, ""))}</td>
  <td style="min-width:25ch">{r.get(ccol, "")}</td>
  <td class="right" style="width:90px">{value_fmt(r.get(value_col))}</td>
</tr>"""
        )

    html = f"""
<div class="card">
  <h3>{title}</h3>
  <table class="tbl">
    <thead>
      <tr>
        <th style="min-width:42ch">Company</th>
        <th style="width:74px">Ticker</th>
        <th style="min-width:25ch">Category</th>
        <th style="width:90px" class="right">{value_label}</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
"""
    return textwrap.dedent(html).strip()

def render_card(slot, title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    with slot:
        if df.empty or value_col is None:
            st.info(f"No data for {title}.")
            return
        st.markdown(_table_html(title, df, value_col, value_label, value_fmt), unsafe_allow_html=True)

# -------------------------
# Header (logo centered)
# -------------------------
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
# Load CSVs (cache-clearable)
# -------------------------

# clear cache automatically on each run
st.cache_data.clear()

@st.cache_data(show_spinner=False)
def load_all_csvs(csv_files, data_dir: Path):
    return [load_csv(data_dir / f"qry_graph_data_{num}.csv") for num, _ in csv_files]

dfs = load_all_csvs(CSV_FILES, DATA_DIR)

def _extract_report_date_from_df(df) -> str | None:
    """Return m/d/YYYY (no leading zeros) from a Date column if present."""
    # find a 'Date' column (any case)
    date_col = next((c for c in df.columns if c.lower() == "date"), None)
    if not date_col:
        return None
    s = df[date_col].dropna()
    if s.empty:
        return None
    d = pd.to_datetime(s.iloc[0], errors="coerce")
    if pd.isna(d):
        return None
    # no-leading-zero format (Windows uses %#m/%#d, others %-m/%-d)
    fmt = "%#m/%#d/%Y" if os.name == "nt" else "%-m/%-d/%Y"
    return d.strftime(fmt)

# df #44 is already loaded into dfs[0] below; grab the date from it
# If this block appears before dfs is defined in your file, move the st.markdown
# line to just after `dfs = load_all_csvs(...)`.
report_date = None  # will be set after dfs loads

# derive the report date from csv #44 (dfs[0]); fall back to today if missing
report_date = _extract_report_date_from_df(dfs[0]) or (
    dt.date.today().strftime("%#m/%#d/%Y") if os.name == "nt" else dt.date.today().strftime("%-m/%-d/%Y")
)

# centered subtitle
st.markdown(
    f"""
    <div style="text-align:center; font-weight:600; font-size:18px; margin:-6px 0 12px;">
        Signals – {report_date}
    </div>
    """,
    unsafe_allow_html=True,
)

# Normalize "Category" -> "Exposure" to match the table headers
for d in dfs:
    if "Category" in d.columns and "Category" not in d.columns:
        d.rename(columns={"Category": "Category"}, inplace=True)

# -------------------------
# ROW 1 (3 cards)
# -------------------------
c1, c2, c3 = st.columns(3, gap="large")

df_low_sharpe  = dfs[0].copy()
df_high_sharpe = dfs[1].copy()
df_upside      = dfs[2].copy()

col_low  = _pick(df_low_sharpe,  ["Sharpe_Rank"])
col_high = _pick(df_high_sharpe, ["Sharpe_Rank"])
col_up   = _pick(df_upside,      ["change_pct", "Change_pct", "Change %", "Change"])

render_card(c1, CSV_FILES[0][1], df_low_sharpe,  col_low,  "Sharpe Rank", _fmt_1dec)
render_card(c2, CSV_FILES[1][1], df_high_sharpe, col_high, "Sharpe Rank", _fmt_1dec)
render_card(c3, CSV_FILES[2][1], df_upside,      col_up,   "Change %",   _fmt_pct1)

row_spacer(14)

# -------------------------
# ROW 2 (1 card)
# -------------------------
r2c1, r2c2, r2c3 = st.columns(3, gap="large")

df_downside = dfs[3].copy()
col_down = _pick(df_downside, ["change_pct", "Change_pct", "Change %", "Change"])


render_card(r2c1, CSV_FILES[3][1], df_downside, col_down, "Change %", _fmt_pct1)


# Middle: interpretation text only (inside a card)
with r2c2:
    st.markdown(
        """
<div class="card">
  <h3>How to interpret the four lists</h3>
  <ol style="margin-top:6px; line-height:1.5; font-size:10px;">
    <li><b>Sharpe Ratio Rank</b> - Measures performance relative to a risk-free asset. The rank is a trailing 1-year percentile. Extreme highs or lows often signal an upcoming change in trend.
    <li><b>Upside/Downside Change Percentage</b> - The variance between the current close and the Long-Term Probable Anchor, expressed as a percentage. Highlights upside or downside potential.
  </ol>
</div>
""",
        unsafe_allow_html=True,
    )


# -------------------------
# Footer disclaimer (same wording as the other pages)
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