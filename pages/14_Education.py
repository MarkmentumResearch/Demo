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
st.set_page_config(page_title="Markmentum – Education", layout="wide")


# -------------------------
# Paths (portable for Cloud)
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR   = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

# -------------------------
# Header (logo centered)
# -------------------------
def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

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

# ---------- Render the Education .docx as-is ----------
import io
import os
import streamlit as st

DOCX_PATH = DATA_DIR / "Educational Page v2.docx"

def render_docx_as_html(docx_path: os.PathLike):
    try:
        import mammoth  # add "mammoth" to requirements.txt
    except Exception:
        st.error(
            'Missing dependency: "mammoth". Add `mammoth` to requirements.txt and redeploy.'
        )
        return

    if not DOCX_PATH.exists():
        st.error(f"Couldn't find: {DOCX_PATH}")
        return

    with open(docx_path, "rb") as f:
        # Inline images are embedded as base64 <img> tags
        html = mammoth.convert_to_html(
            f,
            convert_image=mammoth.images.inline(
                mammoth.images.base64_src_format
            ),
        ).value

    # Light wrapper so it fills the width nicely
    wrapper = f"""
    <div style="max-width: 1100px; margin: 0 auto;">
        {html}
    </div>
    """
    st.components.v1.html(wrapper, height=1200, scrolling=True)

# Call it
st.markdown("### Education")
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