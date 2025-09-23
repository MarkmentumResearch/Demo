# mr_vol_spreads.py — Volatility Spreads page
# (Row 1: 3 cards; Row 2: 3 columns where: left = Downside card, middle = interpretation text, right = blank card)
# :contentReference[oaicite:0]{index=0}

from pathlib import Path
import base64
import textwrap
import pandas as pd
import streamlit as st
import sys
from urllib.parse import quote_plus

# -------------------------
# Page & shared style (same as Overview)
# -------------------------
st.set_page_config(page_title="Markmentum – Volatility Spreads", layout="wide")

st.markdown("""
<style>
/* ---------- Responsive grid: 3-up desktop, 2-up laptop, 1-up narrow ---------- */
div[data-testid="stHorizontalBlock"]{
  display:flex;
  flex-wrap: wrap;               /* allow wrapping; we control per breakpoint */
  gap: 28px;
}

/* Each Streamlit column behaves like a grid item */
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
  flex: 1 1 32%;                 /* target ~3-up by default */
  min-width: 360px;              /* don't collapse too small */
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
}
.card h3 { margin: 0 0 8px 0; font-size: 16px; font-weight: 700; color:#1a1a1a; }

/* Table */
.tbl { border-collapse: collapse; width: 100%; table-layout: fixed; }
.tbl th, .tbl td { border: 1px solid #d9d9d9; padding: 6px 8px; font-size: 13px; overflow:hidden; text-overflow:ellipsis; }
.tbl th { background: #f2f2f2; font-weight: 700; text-align: left; }
.center { text-align: center; }
.right  { text-align: right; white-space: nowrap; }

/* --- Column widths & no-wrap (override any inline styles) --- */
/* Company (col 1): 11–39ch, no wrap */
.tbl thead th:nth-child(1), .tbl tbody td:nth-child(1){
  white-space: nowrap; min-width:11ch !important; width:39ch !important; max-width:39ch !important;
}
/* Ticker (col 2): fixed width */
.tbl thead th:nth-child(2), .tbl tbody td:nth-child(2){ width:74px !important; }
/* Exposure (col 3): 6–22ch, no wrap */
.tbl thead th:nth-child(3), .tbl tbody td:nth-child(3){
  white-space: nowrap; min-width:6ch !important; width:22ch !important; max-width:22ch !important;
}
/* Value (col 4): keep compact (most cards use %/score; shares not used here) */
.tbl thead th:nth-child(4), .tbl tbody td:nth-child(4){ width:90px; }

/* ---------- Breakpoints ---------- */
/* Big desktop (>=1500px): force 3-up */
@media (min-width: 1500px){
  div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex-basis: 32%; }
}
/* Laptop / standard desktops (1000–1499px): go 2-up, gently shrink text cols */
@media (max-width: 1499.98px){
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 48%; }
  .tbl thead th:nth-child(1), .tbl tbody td:nth-child(1){ width:32ch !important; max-width:32ch !important; }
  .tbl thead th:nth-child(3), .tbl tbody td:nth-child(3){ width:18ch !important; max-width:18ch !important; }
}
/* Narrow (<1000px): single column; loosen table widths a bit */
@media (max-width: 999.98px){
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{ flex:1 1 100%; }
  .tbl thead th:nth-child(1), .tbl tbody td:nth-child(1){ width:36ch !important; max-width:36ch !important; }
  .tbl thead th:nth-child(3), .tbl tbody td:nth-child(3){ width:22ch !important; max-width:22ch !important; }
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Paths (same pattern as Overview)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

# CSVs for this page
CSV_FILES = [
    (40, "Most Crowded Shorts"),
    (41, "Most Crowded Longs"),
    (42, "Most Mean Reversion Upside Bias"),
    (43, "Most Mean Reversion Downside Bias"),
]

# -------------------------
# Helpers (same approach as Overview)
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

def _pick(df: pd.DataFrame, candidates: list[str], default: str | None = None):
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

def _table_html(title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    # tolerant mapping for standard names used in your CSVs
    cmap = {c.lower(): c for c in df.columns}
    tcol = cmap.get("ticker") or "Ticker"
    ncol = cmap.get("ticker_name") or cmap.get("company") or "Company"
    ccol = cmap.get("category") or cmap.get("exposure") or "Exposure"

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
        <th style="min-width:25ch">Exposure</th>
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

# ---- Centered sub-title: "Volatility Spreads – {asof}" (date from CSV #40)
def _pretty_mdY(ts) -> str:
    try:
        ts = pd.to_datetime(ts)
    except Exception:
        return ""
    # no leading zeros; Windows needs %#m/%#d, unix uses %-m/%-d
    fmt = "%#m/%#d/%Y" if sys.platform.startswith("win") else "%-m/%-d/%Y"
    return ts.strftime(fmt)

asof_text = ""
try:
    df40 = load_csv(DATA_DIR / "qry_graph_data_40.csv")
    date_col = _pick(df40, ["Date", "date", "AsOf", "asof"])
    if date_col:
        # use max in case multiple rows/dates are present
        asof_text = _pretty_mdY(pd.to_datetime(df40[date_col]).max())
except Exception:
    pass

st.markdown(
    f"""
    <div style="text-align:center; margin: -6px 0 12px; font-size:18px; font-weight:600;">
        Volatility Spreads{f" – {asof_text}" if asof_text else ""}
    </div>
    """,
    unsafe_allow_html=True,
)
# -------------------------
# ROW 1 (3 cards): Shorts / Longs / Upside
# -------------------------
c1, c2, c3 = st.columns(3, gap="large")

df_short = dfs[0].copy()
df_long  = dfs[1].copy()
df_up    = dfs[2].copy()

# Normalize "Category" -> "Exposure"
for d in (df_short, df_long, df_up):
    if "Category" in d.columns and "Exposure" not in d.columns:
        d.rename(columns={"Category": "Exposure"}, inplace=True)

col_s = _pick(df_short, ["Spread_Score"])
col_l = _pick(df_long,  ["Spread_Score"])
col_u = _pick(df_up,    ["Spread_Score"])

render_card(c1, CSV_FILES[0][1], df_short, col_s, "Score", _fmt_1dec)
render_card(c2, CSV_FILES[1][1], df_long,  col_l, "Score", _fmt_1dec)
render_card(c3, CSV_FILES[2][1], df_up,    col_u, "Score", _fmt_1dec)

row_spacer(14)

# -------------------------
# ROW 2 (3 columns): Downside card | Interpretation text | blank card
# -------------------------
r2c1, r2c2, r2c3 = st.columns(3, gap="large")

# Left: Downside card (same width as others)
df_down = dfs[3].copy()
if "Category" in df_down.columns and "Exposure" not in df_down.columns:
    df_down.rename(columns={"Category": "Exposure"}, inplace=True)
col_d = _pick(df_down, ["Spread_Score"])
render_card(r2c1, CSV_FILES[3][1], df_down, col_d, "Score", _fmt_1dec)

# Middle: interpretation text only (inside a card)
with r2c2:
    st.markdown(
        """
<div class="card">
  <h3>How to interpret the four lists</h3>
  <ol style="margin-top:6px; line-height:1.5; font-size:13px;">
    <li><b>Most Crowded Shorts</b> — Wide Implied-Volatility (IV) <b>premium</b> with an elevated 30-Day Volatility Z-Score.
        Often indicates crowding on the short side; price may be due for a <i>bounce</i>.</li>
    <li><b>Most Crowded Longs</b> — Wide IV <b>discount</b> with a depressed 30-Day Volatility Z-Score.
        Often indicates crowding on the long side; price may be due for a <i>correction</i>.</li>
    <li><b>Most Mean Reversion Upside Bias</b> — Wide IV <b>premium</b> with a <i>depressed</i> 30-Day Volatility Z-Score.
        Not always actionable in the moment, but can be a sign of “climbing a wall of worry.”</li>
    <li><b>Most Mean Reversion Downside Bias</b> — Wide IV <b>discount</b> with an <i>elevated</i> 30-Day Volatility Z-Score.
        Also not always actionable immediately; can coincide with bottoming processes.</li>
  </ol>
</div>
""",
        unsafe_allow_html=True,
    )

# Right: blank card (placeholder to keep 3-up rhythm)
#with r2c3:
#    st.markdown('<div class="card" style="min-height: 120px;"></div>', unsafe_allow_html=True)

# -------------------------
# Footer disclaimer (same wording as other pages)
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