import base64
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import os
import streamlit.components.v1 as components

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – Education", layout="wide")


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

st.markdown(
        f"""
        <div style="text-align:center; margin:-6px 0 14px;
                    font-size:18px; font-weight:600; color:#1a1a1a;">
            Education
        </div>
        """,
        unsafe_allow_html=True,
    )

st.cache_data.clear()

# ---------- Render the Education .docx as-is ----------
import io
import os
import streamlit as st

DOCX_PATH = DATA_DIR / "Educational Page v2.docx"

def render_docx_as_html(docx_path: Path):
    try:
        import mammoth
    except Exception:
        st.error('Missing dependency: **mammoth**. Add `mammoth==1.11.0` to requirements.txt and redeploy.')
        if Path(docx_path).exists():
            with open(docx_path, "rb") as f:
                st.download_button("Download the Education doc (DOCX)", f, file_name=Path(docx_path).name)
        return

    if not Path(docx_path).exists():
        st.error(f"Couldn't find: `{docx_path}`")
        return

    with open(docx_path, "rb") as f:
        # Default behavior already inlines images as data URIs.
        html = mammoth.convert_to_html(f).value

    wrapper = f'<div style="max-width:1100px;margin:0 auto;">{html}</div>'
    st.components.v1.html(wrapper, height=1200, scrolling=True)

# Call it
#st.markdown("### Education")
render_docx_as_html(DOCX_PATH)






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