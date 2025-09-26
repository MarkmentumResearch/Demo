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

# ---- LAYOUT & WIDTH TUNING (Cloud parity + your constraints) ----

st.markdown("""
<style>
/* ---------------- Base layout ---------------- */
div[data-testid="stHorizontalBlock"]{
  display:flex;
  flex-wrap: wrap;
  gap: 28px;
}

/* Each Streamlit column acts like a grid item */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
  flex: 1 1 32%;     /* desktop default target ~3-up */
  min-width: 300px;
}

/* App container width */
[data-testid="stAppViewContainer"] .main .block-container,
section.main > div {
  width: 95vw;
  max-width: 2100px;
  margin-left: auto;
  margin-right: auto;
}

/* Typography + card shell */
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card { 
  border:1px solid #cfcfcf; 
  border-radius:8px; 
  background:#fff; 
  padding:12px 12px 8px 12px; 
}

/* Choose a STANDARD width for all non-desktop cards */
.card { 
  max-width: 720px;      /* your “standard” card width */
  width: 100%;
}
.card h3 { margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a; }

/* Tables */
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td { border:1px solid #d9d9d9; padding:6px 8px; font-size:13px; overflow:hidden; text-overflow:ellipsis; }
.tbl th { background:#f2f2f2; font-weight:700; text-align:left; }
.center { text-align:center; }
.right  { text-align:right; white-space:nowrap; }

/* Column widths (desktop defaults) */
th.col-company, td.col-company { white-space:nowrap; min-width:11ch; width:39ch; max-width:39ch; }
th.col-category, td.col-category { white-space:nowrap; min-width:6ch;  width:22ch; max-width:22ch; }
th.col-ticker,   td.col-ticker   { width:74px; }

/* Shares column (Row 1 / Card 3) */
.shares-wide th.col-value, .shares-wide td.col-value { width:100px !important; white-space:nowrap; }

/* ---------------- Breakpoints ---------------- */

/* DESKTOP (>=1700px): force 3-up */
@media (min-width: 1700px){
  div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ 
    flex: 0 0 32%;
    min-width: 300px;
  }
  /* desktop cards can expand to their column */
  .card { max-width: none; }
}

/* NON-DESKTOP (<1900px): ALWAYS 1-up, centered, fixed standard width */
@media (max-width: 1199.98px){
  /* make each column take the full row so only one column per row */
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
    flex: 0 0 100%;
  }

  /* center every card and keep the standard width; no edge-to-edge stretching */
  .card{
    max-width: 720px;     /* same standard width as defined above */
    margin-left: auto;
    margin-right: auto;
  }
}
</style>
""", unsafe_allow_html=True)



# -------------------------
# Paths (portable for Cloud)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

# Overview CSVs
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
        return f"{v:,.2f}%"
    except Exception:
        return "—"

def _fmt_millions(val):
    try:
        v = float(val)
        #if v > 1000:
        #    v = v / 1_000_000.0
        return f"{v:,.2f} M"
    except Exception:
        return "—"

def _fmt_num(val):
    try:
        return f"{float(val):,.0f}"
    except Exception:
        return "—"

def _pick(df: pd.DataFrame, candidates: list[str], default: str | None = None):
    for c in candidates:
        if c in df.columns:
            return c
        for col in df.columns:
            if col.lower() == c.lower():
                return col
    return default

def _table_html(title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt, value_width_px: int = 90, extra_class: str = ""):
    # tolerant column mapping
    cmap = {c.lower(): c for c in df.columns}
    tcol = cmap.get("ticker") or "Ticker"
    ncol = cmap.get("ticker_name") or cmap.get("company") or "Company"
    ccol = cmap.get("category") or cmap.get("exposure") or "Exposure"

    rows = []
    for _, r in df.iterrows():
        rows.append(f"""
<tr>
  <td class="col-company">{r.get(ncol, "")}</td>
  <td class="center col-ticker">{_mk_ticker_link(r.get(tcol, ""))}</td>
  <td class="col-category">{r.get(ccol, "")}</td>
  <td class="right col-value" style="width:{value_width_px}px">{value_fmt(r.get(value_col))}</td>
</tr>""")

    return textwrap.dedent(f"""
<div class="card {extra_class}">
  <h3>{title}</h3>
  <table class="tbl">
    <thead>
      <tr>
        <th class="col-company">Company</th>
        <th class="col-ticker">Ticker</th>
        <th class="col-category">Category</th>
        <th class="right col-value" style="width:{value_width_px}px">{value_label}</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
""").strip()

def render_card(slot, title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt, value_width_px: int = 90, extra_class: str = ""):
    with slot:
        if df.empty or value_col is None:
            st.info(f"No data for {title}.")
            return
        st.markdown(_table_html(title, df, value_col, value_label, value_fmt, value_width_px, extra_class), unsafe_allow_html=True)

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
st.cache_data.clear()

@st.cache_data(show_spinner=False)
def load_all_csvs(csv_files, data_dir: Path):
    dfs_local = []
    for num, _ in csv_files:
        dfs_local.append(load_csv(data_dir / f"qry_graph_data_{num}.csv"))
    return dfs_local

dfs = load_all_csvs(CSV_FILES, DATA_DIR)

# ---- Date under the logo from CSV #26 ----
df_date = dfs[0].copy()
date_col = next((c for c in df_date.columns if c.lower() in ("date", "as_of_date", "trade_date")), None)
asof = pd.to_datetime(df_date[date_col], errors="coerce").max() if (date_col and not df_date.empty) else pd.NaT
date_str = f"{asof.month}/{asof.day}/{asof.year}" if pd.notna(asof) else ""
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
c1, c2, c3 = st.columns([1,1,1], gap="large")

df1 = dfs[0].copy()
col_pct = _pick(df1, ["Percent", "daily_return_pct", "percent", "value"], default=None)
render_card(c1, T_PCT_GAIN, df1, col_pct, "Percent", _fmt_pct)

df2 = dfs[1].copy()
col_pct2 = _pick(df2, ["Percent", "daily_return_pct", "percent", "value"], default=None)
render_card(c2, T_PCT_DECL, df2, col_pct2, "Percent", _fmt_pct)

df3 = dfs[2].copy()
col_shares = _pick(df3, ["Shares", "Volume", "shares", "volume", "value"], default=None)
# Wider value column, no wrap
render_card(c3, T_ACTIVE, df3, col_shares, "Shares", _fmt_millions, value_width_px=120, extra_class="shares-wide")

row_spacer(14)

# ------------- Helper for plain table-in-card -------------
def render_table_card(container, title: str, df):
    with container:
        table_html = df.to_html(index=False, classes="tbl", escape=False)
        st.markdown(
            f"""
            <div class="card">
              <h3>{title}</h3>
              {table_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

# -------------------------
# ROW 2 (3 cards): Top Score Gainers / Decliners / Score Change Dist
# -------------------------
d1, d2, d3 = st.columns([1,1,1], gap="large")

df7 = dfs[3].copy()
col_change_hi = _pick(df7, ["model_score_day_change", "Change", "change", "value"], default=None)
render_card(d1, T_GAIN, df7, col_change_hi, "Change", _fmt_num)

df8 = dfs[4].copy()
col_change_lo = _pick(df8, ["model_score_day_change", "Change", "change", "value"], default=None)
render_card(d2, T_DECL, df8, col_change_lo, "Change", _fmt_num)

with d3:
    df_dist = dfs[5].copy()
    score_bin_col = "Score_Bin" if "Score_Bin" in df_dist.columns else "score_bin"
    count_col = "TickerCount" if "TickerCount" in df_dist.columns else "ticker_count"
    df_dist = df_dist[[score_bin_col, count_col]].copy()
    df_dist.columns = ["Score Bin", "Ticker Count"]
    table_html = df_dist.to_html(index=False, classes="tbl", escape=False)
    st.markdown(
        f"""
        <div class="card">
          <h3>{T_D_HIST}</h3>
          {table_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

row_spacer(14)

# -------------------------
# ROW 3 (3 cards): Highest Score / Lowest Score / Distribution
# -------------------------
e1, e2, e3 = st.columns([1,1,1], gap="large")

df4 = dfs[6].copy()
col_score_hi = _pick(df4, ["Score", "model_score", "value"], default=None)
render_card(e1, T_HI, df4, col_score_hi, "Score", _fmt_num)

df5 = dfs[7].copy()
col_score_lo = _pick(df5, ["Score", "model_score", "value"], default=None)
render_card(e2, T_LO, df5, col_score_lo, "Score", _fmt_num)

with e3:
    df_dist2 = dfs[8].copy()
    mapping = {
        "Below -100": "Strong Sell",
        "-100 to -25": "Sell",
        "-25 to 25": "Neutral",
        "25 to 100": "Buy",
        "Above 100": "Strong Buy",
    }
    score_bin_col = "Score_Bin" if "Score_Bin" in df_dist2.columns else "score_bin"
    count_col = "TickerCount" if "TickerCount" in df_dist2.columns else "ticker_count"

    df_dist2["Classification"] = df_dist2[score_bin_col].map(mapping)
    df_dist2 = df_dist2[["Classification", score_bin_col, count_col]]
    df_dist2.columns = ["Classification", "Score Bin", "Ticker Count"]

    table_html = df_dist2.to_html(index=False, classes="tbl", escape=False)
    st.markdown(
        f"""
        <div class="card">
          <h3>Markmentum Score Distribution</h3>
          {table_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ========= Market Read (unchanged) =========
import os
try:
    from docx import Document  # pip install python-docx
except Exception:
    Document = None

def _is_list_paragraph(paragraph) -> bool:
    try:
        return paragraph._p.pPr.numPr is not None
    except Exception:
        return False

@st.cache_data(show_spinner=False)
def load_market_read_md(doc_path: str = "data/Market_Read_daily.docx") -> str:
    if Document is None:
        return "⚠️ **Market Read**: python-docx is not installed (run: `pip install python-docx`)."
    if not os.path.exists(doc_path):
        return f"⚠️ **Market Read** file not found: `{doc_path}`"
    try:
        doc = Document(doc_path)
    except Exception as e:
        return f"⚠️ Could not open **Market Read** file `{doc_path}`: {e}"
    lines: list[str] = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        lines.append(f"- {text}" if _is_list_paragraph(p) else text)
    for i, l in enumerate(lines):
        if l.startswith("Market Read:") and "The model is saying:" in l:
            left, right = l.split("The model is saying:", 1)
            lines[i] = left.strip()
            lines.insert(i + 1, "The model is saying:")
            if right.strip():
                lines.insert(i + 2, right.strip())
            break
    return "\n\n".join(lines)

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