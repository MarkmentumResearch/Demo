from pathlib import Path
import base64, textwrap, os
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from urllib.parse import quote_plus

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – Overview", layout="wide")

# One Cloud-robust style block (ensures 3 rows render like localhost)
st.markdown("""
<style>
/* Keep 3-up layout from collapsing */
div[data-testid="stHorizontalBlock"] { min-width: 1100px; }
/* Center & cap max width (works across Streamlit builds) */
.main .block-container, section.main > div { max-width: 1700px; margin-left: auto; margin-right: auto; }

/* Typography + card/table shell */
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card { border:1px solid #cfcfcf; border-radius:8px; background:#fff; padding:12px 12px 8px 12px; box-shadow:0 0 0 rgba(0,0,0,0); }
.card h3 { margin:0 0 8px 0; font-size:16px; font-weight:700; color:#1a1a1a; }
.tbl { border-collapse: collapse; width: 100%; }
.tbl th, .tbl td { border:1px solid #d9d9d9; padding:6px 8px; font-size:13px; }
.tbl th { background:#f2f2f2; font-weight:700; text-align:left; }
.right { text-align:right; } .center { text-align:center; }
.company { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# Paths (repo-relative for Cloud)
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
    if not t: return ""
    return (f'<a href="?page=Deep%20Dive&ticker={quote_plus(t)}" '
            f'target="_self" rel="noopener" style="text-decoration:none; font-weight:600;">{t}</a>')

# lightweight router for Deep Dive link
qp = st.query_params
dest = (qp.get("page") or "").strip().lower()
if dest.replace("%20", " ") == "deep dive":
    t = (qp.get("ticker") or "").strip().upper()
    if t:
        st.session_state["ticker"] = t
        st.query_params.clear()
        st.query_params["ticker"] = t
    st.switch_page("pages/11_Deep_Dive_Dashboard.py")

def row_spacer(h: int = 14):
    st.markdown(f"<div style='height:{h}px'></div>", unsafe_allow_html=True)

def _image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    return pd.read_csv(path)

def _fmt_pct(v):
    try: return f"{float(v)*100:,.2f}%"
    except: return "—"

def _fmt_millions(v):
    try:
        x = float(v)
        if x > 1000: x = x/1_000_000.0
        return f"{x:,.2f} M"
    except: return "—"

def _fmt_num(v):
    try: return f"{float(v):,.0f}"
    except: return "—"

def _pick(df: pd.DataFrame, candidates: list[str], default: str | None = None):
    for c in candidates:
        if c in df.columns: return c
        for col in df.columns:
            if col.lower() == c.lower(): return col
    return default

def _table_html(title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    cmap = {c.lower(): c for c in df.columns}
    tcol = cmap.get("ticker") or "Ticker"
    ncol = cmap.get("ticker_name") or cmap.get("company") or "Company"
    ccol = cmap.get("category") or cmap.get("exposure") or "Exposure"

    rows = []
    for _, r in df.iterrows():
        rows.append(f"""
<tr>
  <td class="company">{r.get(ncol, "")}</td>
  <td class="center" style="width:74px">{_mk_ticker_link(r.get(tcol, ""))}</td>
  <td style="min-width:25ch">{r.get(ccol, "")}</td>
  <td class="right" style="width:90px">{value_fmt(r.get(value_col))}</td>
</tr>""")

    return textwrap.dedent(f"""
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
""").strip()

def render_card(slot, title: str, df: pd.DataFrame, value_col: str, value_label: str, value_fmt):
    with slot:
        if df.empty or value_col is None:
            st.markdown(f"""
            <div class="card"><h3>{title}</h3>
              <div style="color:#6b7280; font-size:13px;">No data.</div>
            </div>""", unsafe_allow_html=True)
            return
        st.markdown(_table_html(title, df, value_col, value_label, value_fmt), unsafe_allow_html=True)

# -------------------------
# Header (logo centered)
# -------------------------
if LOGO_PATH.exists():
    st.markdown(
        f"""<div style="text-align:center; margin:8px 0 16px;">
               <img src="data:image/png;base64,{_image_to_base64(LOGO_PATH)}" width="440">
            </div>""",
        unsafe_allow_html=True,
    )

# -------------------------
# Load CSVs
# -------------------------
st.cache_data.clear()

@st.cache_data(show_spinner=False)
def load_all_csvs(csv_files, data_dir: Path):
    return [load_csv(data_dir / f"qry_graph_data_{num}.csv") for num, _ in csv_files]

dfs = load_all_csvs(CSV_FILES, DATA_DIR)

# Title line under logo from CSV #26
df_date = dfs[0].copy()
date_col = next((c for c in df_date.columns if c.lower() in ("date","as_of_date","trade_date")), None)
asof = pd.to_datetime(df_date[date_col], errors="coerce").max() if (date_col and not df_date.empty) else pd.NaT
date_str = f"{asof.month}/{asof.day}/{asof.year}" if pd.notna(asof) else ""
if date_str:
    st.markdown(
        f"""<div style="text-align:center; margin:-6px 0 14px; font-size:18px; font-weight:600; color:#1a1a1a;">
               Daily Market Overview – {date_str}
            </div>""",
        unsafe_allow_html=True,
    )

# Labels
(T_PCT_GAIN, T_PCT_DECL, T_ACTIVE,
 T_GAIN, T_DECL, T_D_HIST,
 T_HI, T_LO, T_SCORE_HIST) = [label for _, label in CSV_FILES]

# -------------------------
# ROW 1 (3 cards): gainers / decliners / most active
# -------------------------
c1, c2, c3 = st.columns(3, gap="large")
df1 = dfs[0].copy(); col_pct = _pick(df1, ["Percent","daily_return_pct","percent","value"])
render_card(c1, T_PCT_GAIN, df1, col_pct, "Percent", _fmt_pct)

df2 = dfs[1].copy(); col_pct2 = _pick(df2, ["Percent","daily_return_pct","percent","value"])
render_card(c2, T_PCT_DECL, df2, col_pct2, "Percent", _fmt_pct)

df3 = dfs[2].copy(); col_shares = _pick(df3, ["Shares","Volume","shares","volume","value"])
render_card(c3, T_ACTIVE, df3, col_shares, "Shares", _fmt_millions)

row_spacer(14)

# -------------------------
# ROW 2 (3 cards): Score Change gainers/decliners + Change distribution
# -------------------------
r2c1, r2c2, r2c3 = st.columns(3, gap="large")

df7 = dfs[3].copy()
col_change_hi = _pick(df7, ["model_score_day_change","Change","change","value"])
render_card(r2c1, T_GAIN, df7, col_change_hi, "Change", _fmt_num)

df8 = dfs[4].copy()
col_change_lo = _pick(df8, ["model_score_day_change","Change","change","value"])
render_card(r2c2, T_DECL, df8, col_change_lo, "Change", _fmt_num)

with r2c3:
    df_dist = dfs[5].copy()
    if df_dist.empty:
        st.markdown(f'<div class="card"><h3>{T_D_HIST}</h3><div style="color:#6b7280; font-size:13px;">No data.</div></div>',
                    unsafe_allow_html=True)
    else:
        sb = "Score_Bin" if "Score_Bin" in df_dist.columns else ("score_bin" if "score_bin" in df_dist.columns else None)
        tc = "TickerCount" if "TickerCount" in df_dist.columns else ("ticker_count" if "ticker_count" in df_dist.columns else None)
        if sb and tc:
            table_html = df_dist[[sb, tc]].rename(columns={sb:"Score Bin", tc:"Ticker Count"}).to_html(index=False, classes="tbl", escape=False)
        else:
            table_html = df_dist.to_html(index=False, classes="tbl", escape=False)
        st.markdown(f'<div class="card"><h3>{T_D_HIST}</h3>{table_html}</div>', unsafe_allow_html=True)

row_spacer(14)

# -------------------------
# ROW 3 (3 cards): Highest/Lowest Score + Score Distribution (classification)
# -------------------------
r3c1, r3c2, r3c3 = st.columns(3, gap="large")

df4 = dfs[6].copy(); col_score_hi = _pick(df4, ["Score","model_score","value"])
render_card(r3c1, T_HI, df4, col_score_hi, "Score", _fmt_num)

df5 = dfs[7].copy(); col_score_lo = _pick(df5, ["Score","model_score","value"])
render_card(r3c2, T_LO, df5, col_score_lo, "Score", _fmt_num)

with r3c3:
    df_dist2 = dfs[8].copy()
    if df_dist2.empty:
        st.markdown('<div class="card"><h3>Markmentum Score Distribution</h3><div style="color:#6b7280; font-size:13px;">No data.</div></div>',
                    unsafe_allow_html=True)
    else:
        mapping = {"Below -100":"Strong Sell","-100 to -25":"Sell","-25 to 25":"Neutral","25 to 100":"Buy","Above 100":"Strong Buy"}
        sb2 = "Score_Bin" if "Score_Bin" in df_dist2.columns else ("score_bin" if "score_bin" in df_dist2.columns else None)
        tc2 = "TickerCount" if "TickerCount" in df_dist2.columns else ("ticker_count" if "ticker_count" in df_dist2.columns else None)
        if sb2 and tc2:
            df_dist2["Classification"] = df_dist2[sb2].map(mapping)
            df_dist2 = df_dist2[["Classification", sb2, tc2]]
            df_dist2.columns = ["Classification", "Score Bin", "Ticker Count"]
        table_html = df_dist2.to_html(index=False, classes="tbl", escape=False)
        st.markdown(f'<div class="card"><h3>Markmentum Score Distribution</h3>{table_html}</div>', unsafe_allow_html=True)




# ---------- render ----------
with st.container():
    st.markdown("## Market Read")
    docx_path = (DATA_DIR / "Market_Read_daily.docx").resolve()
    st.markdown(load_market_read_md(str(docx_path)))  # str(...) only if your helper expects a string


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