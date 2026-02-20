

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
st.cache_data.clear()
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


ACCOUNT_URL = "https://www.markmentumresearch.com/account"

st.title("Demo Site")
st.write("This demo site has been discontinued.")
st.write("Please visit our production site.")

# Optional manual fallback button
st.markdown(
    f'<a href="{ACCOUNT_URL}" target="_self" rel="noopener noreferrer">https://www.markmentumresearch.com</a>',
    unsafe_allow_html=True
)


# -------------------------
# Footer disclaimer
# -------------------------
st.markdown("---")
st.markdown(
    """
    <div style="font-size: 12px; color: gray;">
    © 2026 Markmentum Research LLC. <b>Disclaimer</b>: This content is for informational purposes only. 
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