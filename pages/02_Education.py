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


# --- Typography + image scaling to match About page ---
st.markdown("""
<style>
/* Mirror About page font stack */
html, body, [class^="css"], .stMarkdown, .stDataFrame, .stTable, .stText, .stButton {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
}

/* Education content container + default sizing */
.edu-wrapper {
  max-width: 900px;          /* same visual width as About’s main column */
  margin: 0 auto;
  padding: 0 6px;
  line-height: 1.5;
}
.edu-wrapper p, .edu-wrapper li { font-size: 16px; }
.edu-wrapper h1 { font-size: 28px; font-weight: 700; margin: 16px 0 8px; }
.edu-wrapper h2 { font-size: 24px; font-weight: 700; margin: 16px 0 8px; }
.edu-wrapper h3 { font-size: 21px; font-weight: 600; margin: 14px 0 8px; }

/* Make screenshots fit nicely on Cloud */
.edu-wrapper img {
  max-width: 100% !important;
  height: auto !important;
  display: block;
  margin: 8px auto;
}
</style>
""", unsafe_allow_html=True)




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
            Education - How to Use
        </div>
        """,
        unsafe_allow_html=True,
    )

st.cache_data.clear()

# ---------- Render the Education .docx as-is ----------
import io
import os
from pathlib import Path
import streamlit as st

DOCX_PATH = DATA_DIR / "Educational Page v2.docx"

def render_docx_as_html(docx_path: Path):
    """Render a .docx as HTML and offer a Download-as-PDF button."""
    # ---- Load Mammoth (docx -> HTML) ----
    try:
        import mammoth
    except Exception:
        st.error('Missing dependency: **mammoth**. Add `mammoth==1.11.0` to requirements.txt and redeploy.')
        if docx_path.exists():
            with open(docx_path, "rb") as f:
                st.download_button("Download the Education doc (DOCX)", f, file_name=docx_path.name)
        return

    if not docx_path.exists():
        st.error(f"Couldn't find: `{docx_path}`")
        return

    with open(docx_path, "rb") as f:
        html_body = mammoth.convert_to_html(f).value  # images are inlined as data: URIs

    # ---- Scoped page styles (match About; scale screenshots) ----
    scoped_css = """
    <style>
      .edu-wrapper {
        max-width: 900px;
        margin: 0 auto;
        padding: 0 6px;
        line-height: 1.5;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      }
      .edu-wrapper p, .edu-wrapper li { font-size: 16px; }
      .edu-wrapper h1 { font-size: 28px; font-weight: 700; margin: 16px 0 8px; }
      .edu-wrapper h2 { font-size: 24px; font-weight: 700; margin: 16px 0 8px; text-align:center; }
      .edu-wrapper h3 { font-size: 21px; font-weight: 600; margin: 14px 0 8px; }
      .edu-wrapper ul { margin-left: 1.2rem; }
      .edu-wrapper li { margin: 6px 0; }
      .edu-wrapper img { max-width: 100% !important; height: auto !important; display: block; margin: 8px auto; }
    </style>
    """

    # Render HTML inline
    st.markdown(scoped_css + f'<div class="edu-wrapper">{html_body}</div>', unsafe_allow_html=True)

    # ---- Build PDF from the same HTML (uses xhtml2pdf) ----
    try:
        from xhtml2pdf import pisa
    except Exception:
        st.warning('PDF generator not installed. Add `xhtml2pdf==0.2.12` (and `reportlab`, `Pillow`) to requirements.txt.')
        return

    # Minimal full HTML for xhtml2pdf (prefers inline CSS)
    full_html_for_pdf = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12pt; }}
        .edu-wrapper {{ width: 7.0in; margin: 0 auto; }}
        .edu-wrapper h1 {{ font-size: 20pt; }}
        .edu-wrapper h2 {{ font-size: 16pt; text-align:center; }}
        .edu-wrapper h3 {{ font-size: 14pt; }}
        .edu-wrapper p, .edu-wrapper li {{ font-size: 12pt; line-height: 1.4; }}
        .edu-wrapper img {{ max-width: 100%; height: auto; }}
      </style>
    </head>
    <body>
      <div class="edu-wrapper">
        {html_body}
      </div>
    </body>
    </html>
    """

    pdf_buf = io.BytesIO()
    # xhtml2pdf expects a file-like; encode to bytes
    pisa.CreatePDF(src=full_html_for_pdf, dest=pdf_buf, encoding="utf-8")
    pdf_buf.seek(0)

    st.download_button(
        "📄 Download Education as PDF",
        data=pdf_buf,
        file_name="Markmentum_Education.pdf",
        mime="application/pdf",
        type="primary",
    )
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