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
st.set_page_config(page_title="Markmentum – Overview", layout="wide")

# One Cloud-robust CSS block (no duplicates)
st.markdown("""
<style>
/* Pin the app to wide, center it, and keep 3-up columns from collapsing */
.main .block-container { max-width: 1700px; margin-left: auto; margin-right: auto; }

/* Keep 3-up layout from collapsing on narrower laptops */
div[data-testid="stHorizontalBlock"] { min-width: 1100px; }

/* Optional: ensure each column has breathing room */
div[data-testid="column"] { min-width: 360px; }

/* Typography + table shell */
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card {
  border: 1px solid #cfcfcf;
  border-radius: 8px;
  background: #fff;
  padding: 12px 12px 8px 12px;
  box-shadow: 0 0 0 rgba(0,0,0,0);
}
.card h3 { margin: 0 0 8px 0; font-size: 16px; font-weight: 700; color:#1a1a1a; }
.tbl { border-collapse: collapse; width: 100%; }
.tbl th, .tbl td { border: 1px solid #d9d9d9; padding: 6px 8px; font-size: 13px; }
.tbl th { background: #f2f2f2; font-weight: 700; text-align: left; }
.right { text-align: right; }
.center { text-align: center; }
.company { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Column widths for the 3-up tables */
.col-company  { min-width: 42ch; }
.col-ticker   { width: 74px; text-align: center; }
.col-exposure { min-width: 25ch; }
.col-value    { width: 90px; text-align: right; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Paths (same as your other apps)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

# Overview CSVs (kept flexible to match your working v6)
CSV_FILES = [
    (26, "Top Ten Percentage Gainers"),
    (27, "Top Ten Percentage Decliners"),
    (28, "Most Active (Shares)"),
    (70, "Top Ten Markmentum Score Gainers"),
    (71, "Top Ten Markmentum Score Decliners"),
    (72, "Markmentum Score Change Distribution"),
    (29, "Highest Markmentum Score"),
    (30, "Lowest Markmentum Score"),
    (31, "Markmentum Score Histogram"),
]
# -------------------------
# Helpers
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

def _fmt_pct(val):
    try:
        v = float(val) * 100
        return f"{v:,2f}%"
    except Exception:
        return "—"

def _fmt_millions(val):
    try:
        v = float(val)
        if v > 1000:    # allow raw shares
            v = v / 1_000_000.0
        return f"{v:,2f} M"
    except Exception:
        return "—"

def _fmt_num(val):
    try:
        return f"{float(val):,0f}"
    except Exception:
        return "—"

def _pick(df: pd.DataFrame, candidates: list[str], default: str | None = None):
    for c in candidates:
        if c in df.columns:
            return c
        # case-insensitive fallback
        for col in df.columns:
            if col.lower() == c.lower():
                return col
    return default

def _table_html(title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    # tolerant column mapping
    cmap = {c.lower(): c for c in df.columns}
    tcol = cmap.get("ticker") or "Ticker"
    ncol = cmap.get("ticker_name") or cmap.get("company") or "Company"
    ccol = cmap.get("category") or cmap.get("exposure") or "Exposure"

    rows = []
    for _, r in df.iterrows():
        rows.append(f"""
<tr>
  <td class="company col-company">{r.get(ncol, "")}</td>
  <td class="col-ticker">{_mk_ticker_link(r.get(tcol, ""))}</td>
  <td class="col-exposure">{r.get(ccol, "")}</td>
  <td class="col-value">{value_fmt(r.get(value_col))}</td>
</tr>""")

    html = f"""
<div class="card">
  <h3>{title}</h3>
  <table class="tbl">
    <thead>
      <tr>
        <th class="col-company">Company</th>
        <th class="col-ticker">Ticker</th>
        <th class="col-exposure">Exposure</th>
        <th class="col-value right">{value_label}</th>
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
# Load CSVs (same logic as v6, but cache-clearable)
# -------------------------
# clear cache if needed
st.cache_data.clear()

@st.cache_data(show_spinner=False)
def load_all_csvs(csv_files, data_dir: Path):
    dfs_local = []
    for num, _ in csv_files:
        dfs_local.append(load_csv(data_dir / f"qry_graph_data_{num}.csv"))
    return dfs_local

# call once here so dfs is cache-managed
dfs = load_all_csvs(CSV_FILES, DATA_DIR)

# ---- Small centered title under the logo, using the date from CSV #26 ----
# (dfs[0] corresponds to qry_graph_data_26.csv)
df_date = dfs[0].copy()
date_col = next((c for c in df_date.columns if c.lower() in ("date", "as_of_date", "trade_date")), None)

if date_col is not None and not df_date.empty:
    asof = pd.to_datetime(df_date[date_col], errors="coerce").max()
else:
    asof = pd.NaT

if pd.notna(asof):
    # no leading zeros on month/day
    date_str = f"{asof.month}/{asof.day}/{asof.year}"
else:
    # graceful fallback if the date column is missing/empty
    date_str = ""

if date_str:
    st.markdown(
        f"""
        <div style="text-align:center; margin:-6px 0 14px;
                    font-size:18px; font-weight:600; color:#1a1a1a;">
            Daily Market Overview – {date_str}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Titles
(T_PCT_GAIN, T_PCT_DECL, T_ACTIVE,
 T_GAIN, T_DECL, T_D_HIST,
 T_HI, T_LO, T_SCORE_HIST) = [label for _, label in CSV_FILES]

# -------------------------
# ROW 1 (3 cards): gainers / decliners / most active
# -------------------------
c1, c2, c3 = st.columns(3, gap="large")

# Card 1: Gainers -> Percent
df1 = dfs[0].copy()
col_pct = _pick(df1, ["Percent", "daily_return_pct", "percent", "value"], default=None)
render_card(c1, T_PCT_GAIN, df1, col_pct, "Percent", _fmt_pct)

# Card 2: Decliners -> Percent
df2 = dfs[1].copy()
col_pct2 = _pick(df2, ["Percent", "daily_return_pct", "percent", "value"], default=None)
render_card(c2, T_PCT_DECL, df2, col_pct2, "Percent", _fmt_pct)

# Card 3: Most Active -> Shares
df3 = dfs[2].copy()
col_shares = _pick(df3, ["Shares", "Volume", "shares", "volume", "value"], default=None)
render_card(c3, T_ACTIVE, df3, col_shares, "Shares", _fmt_millions)

row_spacer(14)  # same spacer width used in Filters

# -------------------------
# ROW 2 (3 cards): Highest/Lowest Model Score Change / Distribution
# -------------------------
d1, d2, d3 = st.columns(3, gap="large")

# Card 4: Highest Model Score
df4 = dfs[6].copy()
col_score_hi = _pick(df4, ["Score", "model_score", "value"], default=None)
render_card(d1, T_HI, df4, col_score_hi, "Score", _fmt_num)

# Card 5: Lowest Model Score
df5 = dfs[7].copy()
col_score_lo = _pick(df5, ["Score", "model_score", "value"], default=None)
render_card(d2, T_LO, df5, col_score_lo, "Score", _fmt_num)

# Card 6: Markmentum Score Distribution
with d3:
    df_dist = dfs[8].copy()
    mapping = {
        "Below -100": "Strong Sell",
        "-100 to -25": "Sell",
        "-25 to 25": "Neutral",
        "25 to 100": "Buy",
        "Above 100": "Strong Buy",
    }
    score_bin_col = "Score_Bin" if "Score_Bin" in df_dist.columns else "score_bin"
    count_col = "TickerCount" if "TickerCount" in df_dist.columns else "ticker_count"

    if not df_dist.empty and score_bin_col in df_dist.columns and count_col in df_dist.columns:
        df_dist["Classification"] = df_dist[score_bin_col].map(mapping)
        df_dist = df_dist[["Classification", score_bin_col, count_col]]
        df_dist.columns = ["Classification", "Score Bin", "Ticker Count"]

        table_html = df_dist.to_html(index=False, classes="tbl", escape=False)
        st.markdown(
            f"""
            <div class="card">
              <h3>Markmentum Score Distribution</h3>
              {table_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No data for Markmentum Score Distribution.")

# ========= Row 3 (Market Read) =========
import os
try:
    from docx import Document  # pip install python-docx
except Exception:
    Document = None

def _is_list_paragraph(paragraph) -> bool:
    """Detect bulleted/numbered paragraphs from python-docx."""
    try:
        return paragraph._p.pPr.numPr is not None  # type: ignore[attr-defined]
    except Exception:
        return False

@st.cache_data(show_spinner=False)
def load_market_read_md(doc_path: str = "data/Market_Read_daily.docx") -> str:
    """
    Read the Market Read .docx and return a Markdown string.

    - Keeps bullets as markdown "- ..."
    - Ensures 'The model is saying:' is its own line (not glued to the date line).
    """
    if Document is None:
        return "⚠️ **Market Read**: python-docx is not installed (run: `pip install python-docx`)."
    try:
        doc = Document(doc_path)
    except Exception:
        return "⚠️ **Market Read**: Unable to open the .docx file."

    lines: list[str] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        if _is_list_paragraph(p):
            lines.append(f"- {text}")
        else:
            lines.append(text)

    # Put 'The model is saying:' on its own line if attached to the date
    for i, l in enumerate(lines):
        if l.startswith("Market Read:") and "The model is saying:" in l:
            left, right = l.split("The model is saying:", 1)
            lines[i] = left.strip()
            lines.insert(i + 1, "The model is saying:")
            if right.strip():
                lines.insert(i + 2, right.strip())
            break

    md = "\n\n".join(lines)
    return md

# ---------- render ----------
with st.container():
    st.markdown("## Market Read")
    docx_path = (DATA_DIR / "Market_Read_daily.docx").resolve()
    st.markdown(load_market_read_md(str(docx_path)))

st.markdown(
    "<div style='margin-top:6px; color:#6b7280; font-size:13px;'>"
    "Note: Indices are excluded from Highest/Lowest Markmentum Score lists."
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