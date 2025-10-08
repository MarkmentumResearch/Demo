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
    """Render a .docx (with screenshots) as HTML inside a 900px column."""
    try:
        import mammoth  # ensure mammoth is in requirements.txt (e.g., mammoth==1.11.0)
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
        html_body = mammoth.convert_to_html(f).value  # images are inlined as data URIs by default

    # Scoped styles so this block matches About page typography and scales screenshots
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
      .edu-wrapper h2 { font-size: 24px; font-weight: 700; margin: 16px 0 8px; }
      .edu-wrapper h3 { font-size: 21px; font-weight: 600; margin: 14px 0 8px; }
      .edu-wrapper img {
        max-width: 100% !important;
        height: auto !important;
        display: block;
        margin: 8px auto;
      }
    </style>
    """

    wrapped = f'{scoped_css}<div class="edu-wrapper">{html_body}</div>'
    st.components.v1.html(wrapped, height=1200, scrolling=True)
# Call it
#st.markdown("### Education")
render_docx_as_html(DOCX_PATH)

st.components.v1.html("""
<button id="mm-save-pdf"
        style="display:block;margin:18px auto 8px;padding:10px 14px;
               border:1px solid #ccc;border-radius:8px;background:#f7f7f9;
               cursor:pointer;font-family:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  📄 Save this Education page as PDF
</button>

<style>
/* Print-optimized styles */
@media print {
  /* Use Letter with comfortable margins (change to A4 if needed) */
  @page { size: Letter; margin: 0.5in; }

  /* Hide Streamlit chrome */
  [data-testid="stSidebar"], header, footer { display: none !important; }

  /* Keep the content centered and readable width */
  .edu-wrapper { width: 7.0in !important; margin: 0 auto !important; }

  /* Avoid awkward breaks */
  img, figure, table { page-break-inside: avoid; }
  h1, h2, h3 { page-break-after: avoid; }
}
</style>

<script>
  const btn = document.getElementById("mm-save-pdf");
  if (btn) btn.addEventListener("click", () => window.print());
</script>
""", height=70)




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