# filters.py — Markmentum Filters Page (8 cards: 32..39 in 3/3/2 layout)
from pathlib import Path
import base64
import pandas as pd
import streamlit as st
import textwrap
import streamlit.components.v1 as components
from urllib.parse import quote_plus

# -------------------------
# Page setup
# -------------------------
st.set_page_config(page_title="Markmentum – Filters", layout="wide")

# -------------------------
# Responsive, no-wrap render styles (desktop + laptop)
# -------------------------

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
  min-width: 300px;              /* allow 3-up comfortably */
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

/* --- Column widths (desktop defaults) --- */
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
  /* Optional: loosen text columns slightly for readability on smaller screens */
  .tbl thead th:nth-child(1), .tbl tbody td:nth-child(1){ width:36ch !important; max-width:36ch !important; }
  .tbl thead th:nth-child(3), .tbl tbody td:nth-child(3){ width:22ch !important; max-width:22ch !important; }
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

CSV_FILES = [
    (32, "Short Term Trend Gainers"),
    (33, "Short Term Trend Decliners"),
    (34, "Mid Term Trend Gainers"),
    (35, "Mid Term Trend Decliners"),
    (36, "Chase List"),
    (37, "No Chase List"),
    (38, "Watch List"),
    (39, "Up Cycle List"),
]

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

# Lightweight router: handle links like ?page=Deep%20Dive&ticker=NVDA
qp = st.query_params
dest = (qp.get("page") or "").strip().lower()
if dest.replace("%20", " ") == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    st.switch_page("pages/11_Deep_Dive_Dashboard.py")

def row_spacer(height_px: int = 14):
    st.markdown(f"<div style='height:{height_px}px'></div>", unsafe_allow_html=True)

def _card_table_html_three(df: pd.DataFrame):
    """Render a 3-column table: Company | Ticker | category (no value column)."""
    if df.empty:
        return ""
    cmap = {c.lower(): c for c in df.columns}
    tcol = cmap.get("ticker") or "Ticker"
    ncol = cmap.get("ticker_name") or cmap.get("company") or "Company"
    ccol = cmap.get("category") or cmap.get("category") or "category"

    rows = []
    for _, r in df.iterrows():
        rows.append(f"""
<tr>
  <td class="company">{r.get(ncol, "")}</td>
  <td class="center" style="width:74px">{_mk_ticker_link(r.get(tcol, ""))}</td>
  <td style="min-width:25ch">{r.get(ccol, "")}</td>
</tr>""")
    return f"""
<div class="card">
  <h3>__TITLE__</h3>
  <table class="tbl">
    <thead>
      <tr>
        <th style="min-width:42ch">Company</th>
        <th style="width:74px">Ticker</th>
        <th style="min-width:25ch">Category</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
"""

def _render_card_no_value(slot, title: str, df: pd.DataFrame):
    with slot:
        if df.empty:
            st.info(f"No data for {title}.")
            return
        html = _card_table_html_three(df).replace("__TITLE__", title)
        st.markdown(html, unsafe_allow_html=True)

def _pick_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return df.columns[-1] if len(df.columns) else None

def _render_card_custom(slot, title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    with slot:
        if df.empty or value_col is None:
            st.info(f"No data for {title}.")
            return
        st.markdown(_card_table_html(title, df, value_col, value_label, value_fmt), unsafe_allow_html=True)

def _image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)

def _fmt_pct(val):
    try:
        v = float(val)
        if abs(v) <= 1.0:
            v *= 100.0
        return f"{v:,.2f}%"
    except:
        return "—"

def _fmt_millions(val):
    try:
        v = float(val)
        if v > 1000:
            v = v / 1_000_000.0
        return f"{v:,.2f} M"
    except:
        return "—"

def _fmt_num(val):
    try:
        return f"{float(val):,.1f}"
    except:
        return "—"

def _guess_value_col(df: pd.DataFrame):
    if df.empty:
        return None, "Value", _fmt_num
    cmap = {c.lower(): c for c in df.columns}
    for key, label, fmt in [
        ("daily_return_pct", "Percent", _fmt_pct),
        ("percent",          "Percent", _fmt_pct),
        ("volume",           "Shares",  _fmt_millions),
        ("shares",           "Shares",  _fmt_millions),
        ("model_score",      "Score",   _fmt_num),
    ]:
        if key in cmap:
            return cmap[key], label, fmt
    dims = {"ticker","ticker_name","company","category","category","date"}
    for col in df.columns:
        if col.lower() in dims:
            continue
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() >= max(1, len(s)//4):
            return col, "Value", _fmt_num
    return df.columns[-1], "Value", _fmt_num

def _card_table_html(title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    safe = {c.lower(): c for c in df.columns}
    tcol = safe.get("ticker") or "Ticker"
    ncol = safe.get("ticker_name") or safe.get("company") or "Company"
    ccol = safe.get("category") or safe.get("category") or "category"

    rows = []
    for _, r in df.iterrows():
        rows.append(f"""
<tr>
  <td class="company">{r.get(ncol, '')}</td>
  <td class="center" style="width:74px">{_mk_ticker_link(r.get(tcol, ""))}</td>
  <td style="min-width:25ch">{r.get(ccol, '')}</td>
  <td class="right" style="width:90px">{value_fmt(r.get(value_col))}</td>
</tr>""")

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

def _render_card(slot, title: str, df: pd.DataFrame):
    with slot:
        if df.empty:
            st.info(f"No data for {title}.")
            return
        vcol, vlabel, vfmt = _guess_value_col(df)
        st.markdown(_card_table_html(title, df, vcol, vlabel, vfmt), unsafe_allow_html=True)

# ========= HEADER =========
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
# Load data (cache-clearable)
# -------------------------
st.cache_data.clear()

@st.cache_data(show_spinner=False)
def load_all_csvs(csv_files, data_dir: Path):
    dfs_local = []
    for num, _ in csv_files:
        dfs_local.append(load_csv(data_dir / f"qry_graph_data_{num}.csv"))
    return dfs_local

dfs = load_all_csvs(CSV_FILES, DATA_DIR)

# === Title under logo (date from csv #32) ===
def _mdy_no_leading_zeros(dt: pd.Timestamp) -> str:
    dt = pd.to_datetime(dt)
    return f"{dt.month}/{dt.day}/{dt.year}"

@st.cache_data(show_spinner=False)
def _filters_title_date() -> str:
    df = load_csv(DATA_DIR / "qry_graph_data_32.csv")  # #32
    if df.empty:
        return _mdy_no_leading_zeros(pd.Timestamp.today())
    dmax = pd.to_datetime(df.get("Date"), errors="coerce").max()
    if pd.isna(dmax):
        dmax = pd.Timestamp.today()
    return _mdy_no_leading_zeros(dmax)

st.markdown(
    f"""
    <div style="text-align:center; font-size:18px; font-weight:600; margin:-6px 0 10px;">
        Filters – {_filters_title_date()}
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Layout: 3 / 3 / 2 rows
# -------------------------
titles = [label for _, label in CSV_FILES]

# Row 1: 0,1,2  (all show % Change)
r1c1, r1c2, r1c3 = st.columns(3, gap="large")
vcol = _pick_col(dfs[0], ["Value", "daily_return_pct", "percent"])
_render_card_custom(r1c1, titles[0], dfs[0], vcol, "% Change", _fmt_pct)
vcol = _pick_col(dfs[1], ["Value", "daily_return_pct", "percent"])
_render_card_custom(r1c2, titles[1], dfs[1], vcol, "% Change", _fmt_pct)
vcol = _pick_col(dfs[2], ["Value", "daily_return_pct", "percent"])
_render_card_custom(r1c3, titles[2], dfs[2], vcol, "% Change", _fmt_pct)

row_spacer(14)

# Row 2: 3,4,5  (card 4 %Change; cards 5–6 Chase Score)
r2c1, r2c2, r2c3 = st.columns(3, gap="large")
vcol = _pick_col(dfs[3], ["Value", "daily_return_pct", "percent"])
_render_card_custom(r2c1, titles[3], dfs[3], vcol, "% Change", _fmt_pct)

score_col = _pick_col(dfs[4], ["ChaseScore", "chasescore", "chase_score", "Chase_Score","Score", "score", "model_score"])
dfs[4][score_col] = dfs[4][score_col] * 100
_render_card_custom(r2c2, titles[4], dfs[4], score_col, "Chase Score", _fmt_num)

score_col = _pick_col(dfs[5], ["ChaseScore", "chasescore", "chase_score", "Chase_Score","Score", "score", "model_score"])
dfs[5][score_col] = dfs[5][score_col] * 100
_render_card_custom(r2c3, titles[5], dfs[5], score_col, "Chase Score", _fmt_num)

row_spacer(14)

# Row 3: 6,7 (use 3 columns so card sizes match row 2; leave last empty)
r3c1, r3c2, r3c3 = st.columns(3, gap="large")

score_col = _pick_col(dfs[6], ["Score", "score"])
if score_col is not None and not dfs[6].empty:
    dfs[6] = dfs[6].copy()
    dfs[6]["watch_x100"] = pd.to_numeric(dfs[6][score_col], errors="coerce") * 100.0
_render_card_custom(r3c1, titles[6], dfs[6], "watch_x100", "Watch Score", _fmt_num)

df8 = dfs[7].copy()
keep_cols = ["Company", "Ticker", "Category"]
df8 = df8[[col for col in keep_cols if col in df8.columns]]
_render_card_no_value(r3c2, titles[7], dfs[7])

with r3c3:
    st.markdown(
        """
<div class="card">
  <h3>How to interpret the four lists</h3>
  <ol style="margin-top:6px; line-height:1.5; font-size:13px;">
    <li><b>Chase List</b> — Strong positive momentum; price is more likely to push higher in the near term. Best for continuation setups—just watch position size/overextension risk.</li>
    <li><b>No Chase List</b> — Momentum looks stretched/exhausted; higher odds of a pullback or sideways consolidation. Better to wait for a reset.</li>
    <li><b>Watch List</b> — Early improvement after weakness; potential bottoming behavior. Look for higher lows, relative strength, and confirmation.</li>
    <li><b>Upcycle</b> — Downtrend appears spent and turning up; early stage of a new uptrend. Favor breakouts through resistance and pullback buys into support.</li>
  </ol>
  <div style="font-size: 12px; color: gray;">
  Tip: These are probabilistic signals, not advice. Always pair with your risk management and timeframe.
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