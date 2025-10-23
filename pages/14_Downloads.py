# -------------------------
# Markmentum — Ranking (Model Scores + Sharpe Rank + Sharpe Ratio + Sharpe Ratio 30D Change)
# -------------------------

from pathlib import Path
import base64
import streamlit as st
import os
from datetime import datetime
from io import BytesIO
import zipfile

st.cache_data.clear()

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum - Downloads", layout="wide")


def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"

CSV_PATH  = DATA_DIR / "ticker_data.csv"   # model_score


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



st.markdown("## Downloads")

# ---------- Where CSVs live ----------
# Default to APP_DIR/output; allow override with env var
EXPORT_DIR = Path(os.getenv("MARKMENTUM_EXPORT_DIR", APP_DIR / "output")).resolve()
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

st.caption(f"Export folder: `{EXPORT_DIR}`")

# ---------- Catalog: file → (title, output name) ----------
# Matches your screenshot mapping
CATALOG = {
    "stat_box.csv":                    ("Stat Box",                          "stat_box.csv"),
    "signal_box.csv":                  ("Signal Box",                        "signal_box.csv"),
    "qry_graph_data_01.csv":           ("Probable Ranges",                   "Probable Ranges.csv"),
    "qry_graph_data_02.csv":           ("Trend Lines",                       "Trend Lines.csv"),
    "qry_graph_data_03.csv":           ("Probable Anchors",                  "Probable Anchors.csv"),
    "qry_graph_data_04.csv":           ("Price to LT Probable Anchor",       "Price to LT Probable Anchor.csv"),
    "qry_graph_data_05.csv":           ("30-Day Rvol Z-Score",               "30-Day Rvol Z-Score.csv"),
    "qry_graph_data_06.csv":           ("Z-Score Percentile Rank",           "Z-Score Percentile Rank.csv"),
    "qry_graph_data_07.csv":           ("Rvol 30-Day",                       "Rvol 30-Day.csv"),
    "qry_graph_data_08.csv":           ("30-Day Sharpe Ratio",               "30-Day Sharpe Ratio.csv"),
    "qry_graph_data_09.csv":           ("Sharpe Ratio Percentile Rank",      "Sharpe Ratio Percentile Rank.csv"),
    "qry_graph_data_10.csv":           ("IVol Prem/Disc",                    "IVol Prem/Disc.csv"),
    "qry_graph_data_11.csv":           ("MM Score",                          "MM Score.csv"),
    "qry_graph_data_12.csv":           ("IVol/RVol % Spreads",               "IVol-RVol % Spreads.csv"),
    "qry_graph_data_13.csv":           ("Daily Returns",                     "Daily Returns.csv"),
    "qry_graph_data_14.csv":           ("Daily Range",                       "Daily Range.csv"),
    "qry_graph_data_15.csv":           ("Daily Volume",                      "Daily Volume.csv"),
    "qry_graph_data_16.csv":           ("Weekly Returns",                    "Weekly Returns.csv"),
    "qry_graph_data_17.csv":           ("Weekly Range",                      "Weekly Range.csv"),
    "qry_graph_data_18.csv":           ("Weekly Volume",                     "Weekly Volume.csv"),
    "qry_graph_data_19.csv":           ("Monthly Returns",                   "Monthly Returns.csv"),
    "qry_graph_data_20.csv":           ("Monthly Range",                     "Monthly Range.csv"),
    "qry_graph_data_21.csv":           ("Monthly Volume",                    "Monthly Volume.csv"),
    "qry_graph_data_22.csv":           ("Short-Term Trend Line",             "Short-Term Trend Line.csv"),
    "qry_graph_data_23.csv":           ("Mid-Term Trend Line",               "Mid-Term Trend Line.csv"),
    "qry_graph_data_24.csv":           ("Long-Term Trend Line",              "Long-Term Trend Line.csv"),
}

# ---------- Helpers ----------
def _human_size(n: int) -> str:
    if n is None:
        return "-"
    for unit in ["B","KB","MB","GB","TB"]:
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.0f} PB"

def _read_bytes(p: Path) -> bytes:
    with open(p, "rb") as f:
        return f.read()

# ---------- Search / filter ----------
col_filter, col_zip = st.columns([3,1], vertical_alignment="center")
query = col_filter.text_input("Filter (title or filename)", "", placeholder="e.g., Sharpe, Trend, Probable")
make_zip = col_zip.checkbox("Prepare zip of visible files", value=True)

# ---------- Build rows ----------
rows = []
for fname, (title, outname) in CATALOG.items():
    fpath = EXPORT_DIR / fname
    if not fpath.exists():
        continue
    stat = fpath.stat()
    rows.append({
        "title": title,
        "filename": fname,
        "outname": outname,
        "path": fpath,
        "size": stat.st_size,
        "updated": datetime.fromtimestamp(stat.st_mtime),
    })

# Apply text filter
if query:
    q = query.lower()
    rows = [r for r in rows if q in r["title"].lower() or q in r["filename"].lower()]

if not rows:
    st.info("No files found for the current filter.")
else:
    # ---- Optional ZIP of visible files ----
    if make_zip:
        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for r in rows:
                zf.writestr(r["outname"], _read_bytes(r["path"]))
        zip_buf.seek(0)
        st.download_button(
            "Download All (visible) as .zip",
            data=zip_buf,
            file_name="markmentum_downloads.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )
        st.divider()

    # ---- Table of individual downloads ----
    st.markdown("#### Files")
    hdr = st.columns([3,3,1.3,1.3,1.4])
    hdr[0].markdown("**Title**")
    hdr[1].markdown("**File**")
    hdr[2].markdown("**Updated**")
    hdr[3].markdown("**Size**")
    hdr[4].markdown("**Download**")

    for r in rows:
        c1, c2, c3, c4, c5 = st.columns([3,3,1.3,1.3,1.4])
        c1.write(r["title"])
        c2.code(r["filename"], language=None)
        c3.write(r["updated"].strftime("%Y-%m-%d %H:%M"))
        c4.write(_human_size(r["size"]))
        with open(r["path"], "rb") as f:
            c5.download_button(
                "Download",
                data=f.read(),
                file_name=r["outname"],
                mime="text/csv",
                key=f"dl-{r['filename']}",
                use_container_width=True,
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