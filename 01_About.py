

import base64
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import os

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – About", layout="wide", initial_sidebar_state="expanded")

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
Markets + Momentum = Markmentum Research.  The formula to redefine successful investing.
</p>

<p style="font-weight:600; margin:12px 0 18px;">
We deliver volatility-adjusted probable ranges, algorithmic model scoring, and actionable signals across major market tickers and indices—through a sleek, modern portal. Actionable data. Focused signals. Zero noise.
</p>

<p style="font-weight:600; margin:12px 0 18px;">We don't steer the ship. We provide the captain the coordinates. Let us help you navigate markets with clarity and confidence.</p>

<h3>Preview</h3>
<ul>
  <li><b>Demo</b> –  This is a limited preview of Markmentum Research for informational and educational use. It runs the full product experience with production-grade features and data. The full production site is coming soon.</li>
</ul>

<h3>What we publish</h3>
<ul>
  <li><b>Probable Ranges &amp; Anchors</b> – Forward ranges that frame upside/downside by day, week, and month, plus long-term anchor levels to gauge extension and mean-reversion risk.</li>
  <li><b>Trends &amp; Regimes</b> – Short, mid, and long-term trend lines with regime cues (trend, chop, mean-reversion).</li>
  <li><b>Volatility Stats</b> – Implied (IVOL) vs. realized (RVOL) spreads, percentile ranks, and z-scores to spot crowding and regime shifts.</li>
  <li><b>Markmentum Score</b> – an AI-powered, volatility-adjusted risk–reward algo score — your compass for navigating markets with clarity and confidence.</li>
  <li><b>Ranks &amp; Screens</b> – Daily leaders/laggards, filters, signals, and category rankings to surface opportunity and risk fast.</li>
  <li><b>Updates</b> – Nightly refresh after market close (typically 10–11 pm ET).</li>
</ul>

<h3>How to use the app</h3>
<ul>
  <li><b>Daily Market Overview</b> – One-screen summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score distribution, and top-10 highest/lowest Markmentum Scores.</li>
  <li><b>Weekly Market Overview</b> – One-screen week-to-date summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Scores changes.</li>
  <li><b>Monthly Market Overview</b> – One-screen month-to-date summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Scores changes.</li>
  <li><b>Quarterly Market Overview</b> – One-screen quarter-to-date summary of top percentage gainers/decliners, Most Active (Shares), Markmentum Score change distribution, and top-10 highest/lowest Markmentum Scores changes.</li>
  <li><b>Filters</b> – Curated screens (e.g., short-term gainers/decliners, mid-term trends) to find what matters now.</li>
  <li><b>Volatility Spreads</b> – Where IVOL vs. RVOL is stretched—and where crowding is likely.</li>
  <li><b>Signals</b> – Highest/lowest percentile and mean-reversion setups with context.</li>
  <li><b>Rankings</b> – Category dashboards (i.e., Sectors & Styles, Indices, Currencies, Rates) with a current Markmentum Score heatmap, plus an optional per-ticker current heatmap. 
  Below the heatmaps, see bar-chart rankings for each ticker in the selected category: Markmentum Score (current), Sharpe Percentile, Sharpe Ratio, and Sharpe Ratio 30-day change.</li>
  <li><b>Markmentum Heatmap</b> – At-a-glance heatmap of category Markmentum Score measured by changes in our proprietary AI-powered market model scoring algorithm. Select a category to see each ticker’s Markmentum heatmap and rankings for Daily, Week-to-Date, Month-to-Date, and Quarter-to-Date.</li>
  <li><b>Deep Dive Dashboard</b> – Full instrument view: probable ranges, anchors, trend lines, gap-to-anchor, volatility stats, Sharpe percentile ranks, Markmentum Score, and more.</li>
  <li><b>Universe</b> – Full list of instruments with ticker, name, category, last close, and day/week/month/quarter percent changes. 
  Quick filter and CSV export. Coverage includes major indices, sector/style ETFs, currencies, commodities, bonds, and yields, plus broad S&P 500 coverage and selected single names (including Bitcoin, ES, and NQ futures).</li>
  <li><b>Contact</b> – Have questions or feedback? Send us a note and we’ll get back to you as soon as possible.</li>  
</ul>

<h3>Methodology</h3>
<ul>
  <li><b>Probable Ranges</b> – Derived from historical distributions, realized volatility, and liquidity-aware smoothing across daily/weekly/monthly horizons.</li>
  <li><b>Anchors</b> – Long-term probabilistic anchors to contextualize extension and mean-reversion risk (e.g., “gap to LT anchor”).</li>
  <li><b>Trend Lines</b> – Short-, mid-, and long-term composites using price structure with volatility-adjusted factors.</li>
  <li><b>Volatility Stats</b> – 30-day z-scores, percentile ranks, IVOL/RVOL spreads, and regime flags.</li>
  <li><b>Markmentum Score</b> – Our proprietary market model score blends volatility, trend quality, mean-reversion stretch, and risk-reward into one number. A high positive score means the setup favors the long side; a negative score means it favors the short side.</li>
  <li><b>Ranks &amp; Screens</b> – Percentile and z-score ranks across full universe of instruments.</li>
</ul>

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