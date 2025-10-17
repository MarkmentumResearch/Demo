

import base64
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import os
import streamlit.components.v1 as components


# --- NO-REDIRECT LANDING GUARD (place at the top of 01_About.py) ---
# 1) Absolute safe mode (via secret or ?safe=1) — never leave About.
safe_mode = bool(st.secrets.get("SAFE_MODE", False)) or st.query_params.get("safe", ["0"])[0] == "1"
if safe_mode:
    # Pin the session to About and clear params that some routers use
    st.session_state["_disable_redirects"] = True
    st.session_state["_last_route"] = "about"
    if st.query_params:
        st.query_params.clear()
    # Optional: a tiny note while testing (remove if you like)
    st.caption("Safe mode: redirects disabled on landing.")
    # Stop here so nothing else can trigger a reroute
    st.stop()

# 2) For normal visitors, still pin the initial route to 'about' and normalize params.
#    This doesn't stop the page; it just makes your routers idempotent.
if not st.session_state.get("_last_route"):
    st.session_state["_last_route"] = "about"
# If you use a query-param router elsewhere, neutralize it on About:
if st.query_params:
    st.query_params.clear()
# -------------------------------------------------------------------



# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – About", layout="wide", initial_sidebar_state="expanded")

# Always expand sidebar on page load (safe: only clicks if collapsed control is present)
components.html("""
<script>
(function () {
  function tryOpen() {
    const doc = window.parent.document;
    const ctrl = doc.querySelector('div[data-testid="stSidebarCollapsedControl"] button');
    if (ctrl) { ctrl.click(); return true; }  // only present when sidebar is collapsed
    return false;
  }
  let n = 0;
  const t = setInterval(() => { if (tryOpen() || n++ > 10) clearInterval(t); }, 100);
})();
</script>
""", height=0, width=0)


st.markdown(
    """
<style>
div[data-testid="stHorizontalBlock"] { min-width: 1100px; }
section.main > div { max-width: 1700px; margin-left: auto; margin-right: auto; }
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}
.card {
  border: 1px solid #cfcfcf;
  border-radius: 8px;
  background: #fff;
  padding: 14px 14px 10px 14px;
}
.card h3 { margin: 0 0 10px 0; font-size: 16px; font-weight: 700; color:#1a1a1a; }
.small { font-size:12px; color:#666; }

/* keep the selector compact (≈36 chars) */
div[data-baseweb="select"] {
  max-width: 36ch !important;
}
</style>
""",
    unsafe_allow_html=True,
)

def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

EXCEL_BLUE   = "#4472C4"
EXCEL_ORANGE = "#FFC000"
EXCEL_GRAY   = "#A6A6A6"
DEFAULT_TICKER = "SPY"

# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"



# -------------------------
# Header: logo centered
# -------------------------
if LOGO_PATH.exists():
    st.markdown(
        f"""
        <div style="text-align:center; margin: 8px 0 16px;">
            <img src="data:image/png;base64,{_image_b64(LOGO_PATH)}" width="440">
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# Header: logo centered - end
# -------------------------

# -------------------------
# About content (hard-coded from "MR About v2")
# -------------------------
st.markdown(
    """
<div style="max-width:900px; margin: 0 auto;">

<p style="font-weight:600; margin:12px 0 18px;">
Markets + Momentum = Markmentum Research.  The equation to redefine trading, investing, and portfolio management success.
</p>

<p style="font-weight:600; margin:12px 0 18px;">
We deliver volatility-adjusted probable ranges, proprietary scoring, and AI-assisted market reads that frame growth and inflation expectations — plus probability-driven signals across major market tickers and indices—through a sleek, modern portal. Actionable data. Focused insights. Zero noise.
</p>

<p style="font-weight:600; margin:12px 0 18px;">You're the captain. We provide the coordinates. Let us help you navigate markets with clarity and confidence.</p>

<h3>Preview</h3>
<ul>
  <li><b>Demo</b> –  This is a limited preview of Markmentum Research for informational and educational use. It showcases the full feature set with production-grade data. The subscription launch is coming soon.</li>
</ul>

<h3>What we publish</h3>
<ul>
  <li><b>Probable Ranges &amp; Anchors</b> – Forward ranges that frame upside/downside by day, week, and month, plus long-term anchor levels to gauge extension and mean-reversion risk.</li>
  <li><b>Trends &amp; Regimes</b> – Short, mid, and long-term trend lines with regime cues (trend, chop, mean-reversion).</li>
  <li><b>Volatility Stats</b> – Implied (IVOL) vs. realized (RVOL) spreads, percentile ranks, and z-scores to spot crowding and regime shifts.</li>
  <li><b>Markmentum Score</b> – a rules-based, volatility-adjusted risk–reward score — the navigator allowing you, the captain, to steer the ship to your destination with clarity and confidence.</li>
  <li><b>Ranks &amp; Screens</b> – Daily leaders/laggards, filters, signals, and category rankings to surface opportunity and risk fast.</li>
  <li><b>Updates</b> – Nightly refresh after market close (typically 9–10 pm ET).</li>
</ul>

<h3>How to use the app</h3>
<ul>
  <li><b>Morning Compass</b> – Your orientation dashboard across major indices, sectors, and macro levers — with a one-click Daily / Weekly / Monthly selector. 
  Displays probable ranges, risk/reward bias, and Markmentum Scores for key macro exposures (Indices, S&P 500 sectors, Gold, USD, TLT, BTC Futures), plus top 5 gainers and laggards by % change and by Markmentum Score, 
  along with an optional category snapshot for deeper drill-downs. Auto-refreshed for a concise, data-first read on market direction and crowd positioning.</li>
  <li><b>Daily Market Overview</b> – One-screen summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Score changes, Markmentum Score distribution, and top-10 highest/lowest Markmentum Scores. 
  Includes an AI-assisted Market Read framing daily growth and inflation dynamics.</li>
  <li><b>Weekly Market Overview</b> – One-screen week-to-date summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Score changes. 
  Includes an AI-assisted Market Read summarizing weekly macro and regime shifts.</li>
  <li><b>Monthly Market Overview</b> – One-screen month-to-date summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Score changes. 
  Includes an AI-assisted Market Read contextualizing monthly growth and inflation trends.</li>
  <li><b>Quarterly Market Overview</b> – One-screen quarter-to-date summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Score changes. 
  Includes an AI-assisted Market Read distilling longer-term macro themes and regime tone.</li>
  <li><b>Performance Heatmap</b> – Multi-layered view of realized market performance across categories and tickers. Begins with key macro tickers and category-level averages, then allows a drill-down by category to explore per-ticker percentage changes. 
  Displays Daily, WTD, MTD, and QTD returns, with each timeframe independently scaled for clarity. The layout combines table and heatmap views to show where performance strength or weakness has already occurred, complementing the forward-looking insights from the Markmentum Heatmap.</li>
  <li><b>Filters</b> – Curated screens for short-term trend gainers/decliners, mid-term trend gainers/decliners, chase/no chase, watch, and up-cycle to find what matters now.</li>
  <li><b>Volatility Spreads</b> – Where IVOL vs. RVOL is stretched—and where crowding is likely.</li>
  <li><b>Signals</b> – Highest/lowest Sharpe percentile rank and mean-reversion setups with context.</li>
  <li><b>Sharpe Rank Heatmap</b> – Multi-layered view of risk-adjusted performance across categories and tickers. Begins with key macro tickers and category-level averages, then allows a drill-down by category to explore per-ticker Sharpe Percentile Ranks. 
  Displays current rank alongside Daily, WTD, MTD, and QTD changes, with each timeframe independently scaled for clarity. The layout combines table and heatmap views to highlight where relative performance strength or weakness is emerging across the market.</li>
  <li><b>Markmentum Heatmap</b> – Multi-layered view of opportunity and risk across the entire instrument universe. Begins with key macro tickers and category-level averages, then allows a drill-down by category to see detailed per-ticker positioning. 
  Displays the current score alongside Daily, WTD, MTD, and QTD changes, with each timeframe independently scaled for clarity. Together, the table and heatmap reveal where opportunity and risk are shifting over time.</li>
  <li><b>Trends</b> – Multi-timeframe dashboard visualizing short-, mid-, and long-term directional trends alongside their daily changes. Displays key macro exposures (Indices, S&P 500 sectors, Gold, USD, TLT, BTC Futures) 
  and category averages to highlight trend alignment or divergence across time horizons. 
  Includes per-ticker drill-downs by category to show how leadership and rotation are evolving beneath the surface. Color-coded for quick recognition of positive (green) and negative (red) shifts.</li>
  <li><b>Deep Dive Dashboard</b> – Full instrument view: probable ranges, anchors, trend lines, gap-to-anchor, volatility stats, Sharpe percentile ranks, Markmentum Score, and more.</li>
  <li><b>Universe</b> – Full list of instruments with ticker, name, category, last close, and day/week/month/quarter percent changes. 
  Quick filter and CSV export. Coverage includes major indices, sector/style ETFs, currencies, commodities, bonds, and yields, plus full S&P 500 coverage and selected single names (including Bitcoin, ES, and NQ futures).</li>
  <li><b>Contact</b> – Have questions or feedback? Send us a note and we’ll get back to you as soon as possible.</li>  
</ul>

<h3>Methodology</h3>
<ul>
  <li><b>Probable Ranges</b> – Calculated independently for highs and lows using: (1) the high or low price series, (2) realized volatility on that series, (3) volatility-of-volatility on that series, and (4) volume volatility. 
  These inputs generate the probable high and low across daily, weekly, and monthly horizons. By building the model on highs and lows—rather than just closes—the ranges capture more information about market behavior. </li>
  <li><b>Trends</b> – Short-, mid-, and long-term composites derived by netting the volatility-adjusted factors behind probable highs and lows, providing a directional trend signal.</li>
  <li><b>Anchors</b> – Anchor levels are extrapolated by aligning short-term trend structure with long-term trend structure, creating a probabilistic reference to gauge extension and mean-reversion risk.</li>
  <li><b>Volatility Stats</b> – 30-day z-scores, percentile ranks, IVOL/RVOL spreads, and regime flags.</li>
  <li><b>Markmentum Score</b> – A proprietary, rules-based, volatility-adjusted risk-reward score blending multiple signals into a single intuitive scale. A high positive score favors the long side; a negative score favors the short side.</li>
</ul>

<h3>Our Why</h3>
<p>
  Markmentum Research was born from a passion for markets and numbers — but it’s guided by faith. 
  All glory and honor to the Lord, who makes every step possible.
</p>
<p>
  Our mission is to deliver actionable, probability-driven insights without noise or narratives, 
  helping market participants steward their resources with confidence.
</p>
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