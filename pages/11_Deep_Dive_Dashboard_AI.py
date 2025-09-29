# mr_deep_dive

import base64
from pathlib import Path
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
#rcParams["figure.dpi"] = 110
#rcParams["savefig.dpi"] = 110
#from matplotlib import pyplot as plt
#from matplotlib import rcParams
#import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import os
from matplotlib.ticker import StrMethodFormatter
import math  # (near your other imports, once)
import numpy as np
#plt.rcParams.update({
#    "figure.dpi": 110,
#    "figure.figsize": (9.2, 3.4),   # good aspect for the 3-up rows
#})

# >>> ADD: OpenAI + utils
import json, re

try:
    from openai import OpenAI
    _OPENAI_READY = True
except Exception:
    _OPENAI_READY = False

# -------------------------
# Page & shared style
# -------------------------
st.set_page_config(page_title="Markmentum – Ranking", layout="wide")
st.markdown("""
<style>
/* Make the content wider on desktops while keeping nice margins */
[data-testid="stAppViewContainer"] .main .block-container{
  max-width: 1900px;   /* was smaller; gives you more width on 27" */
  padding-left: 1.2rem;
  padding-right: 1.2rem;
}

""", unsafe_allow_html=True)

st.markdown(
    """
<style>
div[data-testid="stHorizontalBlock"] { min-width: 1100px; }
section.main > div { max-width: 1900px; margin-left: auto; margin-right: auto; }
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
  max-width: 65ch !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("""
<style>
/* ===== Scoped centering for Stat Box and Graph 1 only ===== */

/* STAT BOX row (immediately after the #stat-center marker) */
#stat-center + div[data-testid="stHorizontalBlock"]{
  display:flex !important; justify-content:center !important; gap:0 !important;
}
#stat-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
#stat-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3){
  flex:1 1 0 !important; min-width:0 !important;      /* symmetric side gutters */
}
#stat-center + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2){
  flex:0 0 auto !important; min-width:0 !important;   /* middle column = shrink-to-fit */
}



/* GRAPH 1 row (immediately after the #g1-center marker) */
/* GRAPH 1 row (2/3 page wide, centered) */
#g1-wide + div[data-testid="stHorizontalBlock"]{
  display:flex !important; justify-content:center !important; gap:24px !important;
}
#g1-wide + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1),
#g1-wide + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3){
  flex:1 1 0 !important; min-width:0 !important;   /* side gutters */
}
#g1-wide + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2){
  flex:4 1 0 !important; min-width:0 !important;   /* ~66.7% width for Graph 1 */
}

/* Make the st.pyplot WRAPPER fill the 2/3 middle column */
#g1-wide + div[data-testid="stHorizontalBlock"] [data-testid="stImage"]{
  width: 100% !important;
  max-width: 100% !important;
  display: block !important;
}

/* Ensure the figure/img inside also stretches to the wrapper */
#g1-wide + div[data-testid="stHorizontalBlock"] [data-testid="stImage"] > figure,
#g1-wide + div[data-testid="stHorizontalBlock"] [data-testid="stImage"] img{
  width: 100% !important;
  max-width: 100% !important;
  height: auto !important;
}

/* Keep canvas covered too (some themes render via canvas) */
#g1-wide + div[data-testid="stHorizontalBlock"] [data-testid="stImage"] canvas{
  width: 100% !important;
  max-width: 100% !important;
}

/* Tighten vertical space between Stat Box and Graph 1 */
#stat-center + div[data-testid="stHorizontalBlock"]{
  margin-bottom: 2px !important;      /* reduce bottom margin of the Stat Box row */
}
#g1-wide + div[data-testid="stHorizontalBlock"]{
  margin-top: 2px !important;         /* reduce top margin of the Graph 1 row */
}

/* Ensure pyplot wrapper itself has no extra top margin */
#g1-wide + div[data-testid="stHorizontalBlock"] [data-testid="stImage"]{
  margin-top: 0 !important;
}            

</style>
""", unsafe_allow_html=True)

def _image_b64(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()

EXCEL_BLUE   = "#4472C4"
EXCEL_ORANGE = "#FFC000"
EXCEL_GRAY   = "#A6A6A6"
EXCEL_BLACK= "#000000"
#DEFAULT_TICKER = "SPY"

# -------------------------
# Paths
# -------------------------
_here = Path(__file__).resolve().parent
APP_DIR = _here if _here.name != "pages" else _here.parent

DATA_DIR  = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
LOGO_PATH  = ASSETS_DIR / "markmentum_logo.png"


FILE_STATS = DATA_DIR / "qry_graph_data_25.csv"   # stat box
FILE_G1    = DATA_DIR / "qry_graph_data_01.csv"   # Graph 1: Probable Ranges
FILE_G2 = DATA_DIR / "qry_graph_data_02.csv"   # Trend Lines
FILE_G3 = DATA_DIR / "qry_graph_data_03.csv"   # Price + Probable Anchors
FILE_G4 = DATA_DIR / "qry_graph_data_04.csv"   # Gap to LT Anchor (with bands)
FILE_G5 = DATA_DIR / "qry_graph_data_05.csv"   # Z-Score + bands
FILE_G6 = DATA_DIR / "qry_graph_data_06.csv"   # Z-Score Percentile Rank
FILE_G7 = DATA_DIR / "qry_graph_data_07.csv"   # Rvol + bands
FILE_G8  = DATA_DIR / "qry_graph_data_08.csv"   # Sharpe Ratio 30d + bands
FILE_G9  = DATA_DIR / "qry_graph_data_09.csv"   # Sharpe Ratio Percentile Rank
FILE_G10 = DATA_DIR / "qry_graph_data_10.csv"   # Ivol Prem/Disc 30d + bands
FILE_G11 = DATA_DIR / "qry_graph_data_11.csv"   # Signal Score + Close
FILE_G12 = DATA_DIR / "qry_graph_data_12.csv"   # Scatter: Z-Score vs Ivol Prem/Disc (two dates per ticker)
FILE_G13 = DATA_DIR / "qry_graph_data_13.csv"  # Daily Returns % + bands
FILE_G14 = DATA_DIR / "qry_graph_data_14.csv"  # Daily Range + bands
FILE_G15 = DATA_DIR / "qry_graph_data_15.csv"  # Daily Volume + bands
FILE_G16 = DATA_DIR / "qry_graph_data_16.csv"  # Weekly Returns % + bands
FILE_G17 = DATA_DIR / "qry_graph_data_17.csv"  # Weekly Range + bands
FILE_G18 = DATA_DIR / "qry_graph_data_18.csv"  # Weekly Volume + bands
FILE_G19 = DATA_DIR / "qry_graph_data_19.csv"  # Monthly Returns % + bands
FILE_G20 = DATA_DIR / "qry_graph_data_20.csv"  # Monthly Range + bands
FILE_G21 = DATA_DIR / "qry_graph_data_21.csv"  # Monthly Volume + bands
FILE_G22 = DATA_DIR / "qry_graph_data_22.csv"  # Short-Term Trend + bands
FILE_G23 = DATA_DIR / "qry_graph_data_23.csv"  # Mid-Term Trend + bands
FILE_G24 = DATA_DIR / "qry_graph_data_24.csv"  # Long-Term Trend + bands

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


# ---- Centered page title under the logo (uses date from CSV #25) ----
try:
    # read only date-like columns, tolerant to different names
    df_title = pd.read_csv(
        FILE_STATS,
        usecols=lambda c: str(c).lower() in ("date", "as_of_date", "trade_date")
    )
except Exception:
    df_title = pd.DataFrame()

date_col = next((c for c in df_title.columns
                 if c.lower() in ("date", "as_of_date", "trade_date")), None)

if date_col is not None and not df_title.empty:
    asof = pd.to_datetime(df_title[date_col], errors="coerce").max()
else:
    asof = pd.NaT

date_str = f"{asof.month}/{asof.day}/{asof.year}" if pd.notna(asof) else ""

if date_str:
    st.markdown(
        f"""
        <div style="text-align:center; margin:-6px 0 14px;
                    font-size:18px; font-weight:600; color:#1a1a1a;">
            Deep Dive Dashboard – {date_str}
        </div>
        """,
        unsafe_allow_html=True,
    )




# --- watermark helper (Matplotlib) ---
from matplotlib.axes import Axes

def add_mpl_watermark(
    ax,
    text: str = "Markmentum",
    alpha: float = 0.12,
    rotation: int = 30,
    fontsize: int = 36,   # fixed, moderate size
):
    """
    Faint diagonal watermark across a Matplotlib Axes.
    Call after plotting, before st.pyplot(fig).
    """
    ax.text(
        0.5, 0.5, text,
        transform=ax.transAxes,
        ha="center", va="center",
        rotation=rotation,
        color="gray", alpha=alpha,
        fontsize=fontsize,
        zorder=0,    # stay behind the plot
        clip_on=True # don’t expand the layout
    )


# ==============================
# HELPERS
# ==============================
def _image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def fmt_px(v):
    try: return f"{float(v):,.1f}"
    except: return "—"

def fmt_pct(v):
    try:
        x = float(v)
        if abs(x) <= 1.0: x *= 100.0
        return f"{x:,.1f}%"
    except: return "—"

#def _rr(v):
#    try: return f"{v:,.2f}"
#    except: return "—"

def fmt_score(v):
    try: return f"{float(v):,.2f}"
    except: return "—"

def fmt_date_long(dt_val) -> str:
    try: return pd.to_datetime(dt_val).strftime("%m/%d/%Y")
    except: return ""

def range_start(end_date: pd.Timestamp, label: str) -> pd.Timestamp | None:
    if label == "3M":
        return end_date - pd.DateOffset(months=3)
    if label == "6M":
        return end_date - pd.DateOffset(months=6)
    if label == "YTD":
        return pd.Timestamp(end_date.year, 1, 1)
    if label == "1Y":
        return end_date - pd.DateOffset(years=1)
    return None  # All

def apply_window_with_gutter(df: pd.DataFrame, label: str, date_col: str = "date", gutter_days: int = 5) -> pd.DataFrame:
    if df.empty: 
        return df
    end = pd.to_datetime(df[date_col]).max()
    start_raw = range_start(end, label)
    if start_raw is None:
        start = df[date_col].min() - pd.Timedelta(days=gutter_days)
        end = end + pd.Timedelta(days=gutter_days)
    else:
        start = max(df[date_col].min(), start_raw - pd.Timedelta(days=gutter_days))
        end   = end + pd.Timedelta(days=gutter_days)
    m = (df[date_col] >= start) & (df[date_col] <= end)
    return df.loc[m].copy()

def _window_by_label_with_gutter(df: pd.DataFrame, label: str, date_col: str) -> pd.DataFrame:
    return apply_window_with_gutter(df, label, date_col=date_col, gutter_days=5)

rcParams["font.family"] = ["sans-serif"]
rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans", "Liberation Sans", "sans-serif"]

def _read_openai_key():
    s = st.secrets
    # 1) root-level key in Streamlit Secrets UI
    if "OPENAI_API_KEY" in s and s["OPENAI_API_KEY"]:
        return str(s["OPENAI_API_KEY"])
    # 2) optional [openai] table if you ever use it
    if "openai" in s and isinstance(s["openai"], dict):
        v = s["openai"].get("api_key") or s["openai"].get("API_KEY") or s["openai"].get("key")
        if v: return str(v)
    # 3) env var (local dev)
    return os.getenv("OPENAI_API_KEY")

# >>> ADD: System prompt that bans advice and forces evidence-backed insights


SYSTEM_PROMPT_DEEPDIVE = """
You are an analyst for Markmentum Research. Your job is to explain the current Model Score in plain English.

Do not reveal formulas, math, or implementation details. Instead, explain only the context and drivers that are already visible on the page. 
Always include the disclaimer: 
⚠️ The Markmentum Score is for informational purposes only and not intended as investment advice. Please consult with your financial advisor before making investment decisions.

---
##### fields passed to the model and normalized name:
ivol = Ivol (Implied Volatility)
rvol= Rvol (Realized Volatility)
prem_disc = Implied Volatility Premium or Discount (Ivol/Rvol)
sharpe_rank = Sharpe Ratio Rank
trend_short = Short-Term Trend
trend_mid = Mid-Term Trend
month_rr = Monthly Risk/Reward
month_low = Monthly probable low
month_high = Monthly probable high
zscore_rank = Rvol 30Day Z-Score Rank
last_price = Close
Long Term Anchor = anchor_val
anchor_gap_pct = ((anchor_val / last_price) - 1); Long Term Anchor to Close expressed as a percentage
month_breach = last_price is outside either Monthly probable low or Monthly probable high
Long Term Anchor to Close = (anchor_val - last_price)
---

### What the Model Score reflects (conceptual components):
- **Implied Volatility Premium/Discount**:  Implied Volatility Premium or Discount. If implied volatility (Ivol) is higher than realized volatility (Rvol), this is Implied Volatility Premium and is generally a positive driver (market is pricing in higher risk premium). 
    If Ivol is lower than Rvol, this is Implied Volatility Discount and is a negative driver (market is not pricing in higher risk premium, sign of complancency).
- **Sharpe Ratio Rank**: Measures return vs risk free asset. Low Sharpe percentile ranks are positive (better entry potential), high Sharpe percentile ranks are negative (crowded / stretched momentum). Middle range (~40–60) is neutral.
- **Rvol 30Day Z-Score Rank**: Measures recent volatility to historical volatility. A higher Z-Score rank is positive as realized volatility may subside, a lower Z-Score rank is negative as realized volatility may emerge.
- **Trend Mix (Short vs Mid)**: trend_short and trend_mid to converge and diverge on a cyclical basis.  trend_short less than trend_mid is considered positive; trend_short higher than trend_mid is considered negative. 
- **Monthly Risk/Reward**: Risk/Reward ratio based on the close in relation to Monthly Probable Low (month_low) and Monthly Probable High (month_high). 
Prices closer to the lower band are positive (more upside than downside), closer to the upper band are negative. Outside the band, this tilt is replaced by a placement penalty/damping.
- **Long Term Anchor to Close**:  A positive number indicates stock price could rally to the long term anchor; A negative number indicates stock price could correct.

---

### Direction rules to follow:
- Ivol > Rvol → **Positive**.  
- Ivol < Rvol → **Negative**.  
- Rvol 30Day Z-Score Rank < 80 → **Positive**.
- Rvol 30Day Z-Score Rank < 20 → **Negative**.
- Rvol 30Day Z-Score Rank between 40 and 60  → **Neutral**.
- Sharpe Ratio Rank > 80 → **Negative**; crowded and/or stretched momentum and not a good entry point.
- Sharpe Ratio Rank < 20 → **Positive**; better entry potential and downward pressure could subside.  
- Sharpe Ratio Rank between 40 and 60 → **Neutral**.
- Close vs Anchor: 
  - If anchor_val > last_price → say “Positive - Close is BELOW the long-term anchor” (reversion potential).
  - If anchor_val < last_price → say “Negative - Close is ABOVE the long-term anchor" (overextension risk).
  - Use the numeric comparison of anchor_val and last_price only (do not infer from percentages).
- Trend mix (Short vs Mid): 
  - if trend_short > trend_mid → “Negative - Short-term trend is ABOVE the Mid-term trend”.
  - if trend_short < trend_mid → “Positive - Short-term trend is BELOW the Mid-term trend”.
- Monthly Risk/Reward > 0 → **Positive**; positive number means the reward outweighs the risk.
- Monthly Risk/Reward < 0 → **Negative**; negative number means the risk outweights the reward.  

---

### Output format:
Return only strict JSON in this structure:
{
  "score_context": {
    "summary": "One sentence summary of whether the score is positive/negative and the main reasons",
    "drivers": [
      {
        "driver": "Driver name (e.g., Implied vs Realized Volatility)",
        "assessment": "positive | negative | neutral",
        "why": "One plain-English explanation (no math, no formulas)",
        "numbers": ["Key numbers if useful, written in user-friendly format (e.g., 'IV 18%, Rvol 12%')"]
      }
      // Only include all drivers
    ]
  }
}

---

### Rules:
- Use **plain English**. Never output formulas, equations, coefficients, or implementation details.  
- Focus on **what the numbers mean**, not how they are calculated.  
- Summaries must highlight **why the score is positive or negative**.  
- Keep explanations concise, intuitive, and user-facing.
"""

MODEL_NAME_PRIMARY = "gpt-5-mini"
MODEL_NAME_FALLBACK = "gpt-4o-mini"  # tried only if the first one errors

# Simple regex guard (server-side belt & suspenders)
_ADVICE_RE = re.compile(r"\b(buy|sell|cover|allocate|should|stop[- ]?loss|take profit|position|hedge)\b", re.I)

def _scrub_advice(text: str) -> str:
    """Replace any advicey verbs with neutral phrasing."""
    return _ADVICE_RE.sub("**(removed: advicey verb)**", text)

def _default_insights():
    """Fallback if API fails — very small, neutral."""
    return {
        "salient_signals": [{"insight": "No AI insight available; showing default message.", "evidence": []}],
        "context_and_implications": [],
        "risk_and_caveats": [],
        "followup_questions": ["Try again or adjust the ticker/date."]
    }

def _extract_output_text(resp) -> str | None:
    """
    Works across OpenAI SDK shapes. Returns a plain string or None.
    """
    # 1) Modern convenience
    txt = getattr(resp, "output_text", None)
    if isinstance(txt, str) and txt.strip():
        return txt

    # 2) Object-style 'output' -> [ { content: [ { text: ... } ] } ]
    out = getattr(resp, "output", None)
    if isinstance(out, list) and out:
        first = out[0]
        content = getattr(first, "content", None)
        if isinstance(content, list) and content:
            node = content[0]
            # node may be pydantic object or dict
            val = getattr(node, "text", None)
            if not val and isinstance(node, dict):
                val = node.get("text") or node.get("value")
            if isinstance(val, str) and val.strip():
                return val

    # 3) Dict-style responses
    if isinstance(resp, dict):
        if isinstance(resp.get("output_text"), str):
            return resp["output_text"]
        out = resp.get("output")
        if isinstance(out, list) and out:
            content = (out[0] or {}).get("content")
            if isinstance(content, list) and content:
                node = content[0] or {}
                val = node.get("text") or node.get("value")
                if isinstance(val, str) and val.strip():
                    return val

    return None


@st.cache_data(show_spinner=False, hash_funcs={dict: lambda d: json.dumps(d, sort_keys=True)})
def get_ai_insights(context: dict, depth: str = "Standard") -> dict:
    """
    Calls OpenAI once per (ticker, as_of, depth, context-hash).
    Expects the compact context dict you already build on-screen.
    Always returns at least one bullet per section (neutral if needed).
    """

    # Depth tuning (rough bullet budget)
    max_bullets = 7

    # Bail early if SDK/key isn't ready
    if not _OPENAI_READY:
        return _default_insights()

    api_key = _read_openai_key()
    if not api_key:
        # st.error("OPENAI_API_KEY not found")  # optional
        return _default_insights()

    client = OpenAI(api_key=api_key)

    # --- Guidance so the model uses your metrics, bands, and flags ---
    rules = """
Only return the JSON key 'score_context' exactly as specified in the system instructions.
Do not output any other keys. Use human labels and units in 'numbers'; avoid raw column names.
Never include formulas, weights, or equations.
"""

    # --- OpenAI call ---
    try:
        ctx_str = json.dumps(context, separators=(",", ":"), ensure_ascii=False)

        def _call(model_name: str):
            # 1) Try the Responses API (new)
            try:
                return client.responses.create(
                    model=model_name,
                    response_format={"type": "json_object"},   # ← add this line
                    input=[
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": SYSTEM_PROMPT_DEEPDIVE + "\n\n" + rules,
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": (
                                            "Return only one JSON object with the single key: score_context.\n"
                                            "Apply the direction rules from the system message: (Ivol>Rvol → positive; Ivol<Rvol → negative).\n"
                                            "When describing anchor and trend relations, use 'close_vs_anchor' and 'Trend mix (Short vs Mid)' from the JSON context if present.\n"
                                            "Monthly Risk/Reward: Risk/Reward ratio based on the close in relation to Monthly Probable Low (month_low) and Monthly Probable High (month_high).\n"
                                            "outside band → range penalty and no RR tilt.\n"
                                            "Use ONLY this shape. Do not include any extra text outside the JSON.\n"
                                        + ctx_str
                                    ),
                                }
                            ],
                        },
                    ],
                    max_output_tokens=600,
                )
            except Exception:
                # 2) Fallback: classic Chat Completions (widely compatible)
                chat = client.chat.completions.create(
                    model=model_name,
                    response_format={"type": "json_object"},  
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_DEEPDIVE + "\n\n" + rules},
                        {
                            "role": "user",
                            "content": (
                                   "Return only one JSON object with the single key: score_context.\n"
                                    "Apply the direction rules from the system message: (Ivol>Rvol → positive; Ivol<Rvol → negative).\n"
                                    "When describing anchor and trend relations, use 'close_vs_anchor' and 'Trend mix (Short vs Mid)' from the JSON context if present.\n"
                                    "Monthly Risk/Reward: Risk/Reward ratio based on the close in relation to Monthly Probable Low (month_low) and Monthly Probable High (month_high).\n"
                                    "outside band → range penalty and no RR tilt.\n"
                                    "Use ONLY this shape. Do not include any extra text outside the JSON.\n"
                                + ctx_str
                            ),
                        },
                    ],
                    temperature=0.2,
                    max_tokens=600,
                )
                # Wrap it to look like a Responses object for _extract_output_text(...)
                return {"output_text": chat.choices[0].message.content or ""}

        try:
            resp = _call(MODEL_NAME_PRIMARY)
        except Exception:
            resp = _call(MODEL_NAME_FALLBACK)

        raw = _extract_output_text(resp)
        st.caption(f"Raw AI output (debug): {raw[:500]}")

        # Parse to JSON; clean if model leaked commas/text
        data = {}
        if raw:
            try:
                data = json.loads(raw)
            except Exception:
                # Try to extract the first valid {...} block
                m = re.search(r"\{.*\}", raw, re.S)
                if m:
                    try:
                        data = json.loads(m.group(0))
                    except Exception:
                        st.caption("AI JSON parse failed after cleanup")
                        data = {}
                else:
                    st.caption("AI response had no JSON object")

    except Exception as e:
        st.caption(f"AI call failed: {e}")
        return _default_insights()

    # --- Post-process / safety scrub ---
    def _norm_driver_list(items):
        out = []
        for it in (items or []):
            if isinstance(it, dict):
                drv = str(it.get("driver","")).strip()
                ass = str(it.get("assessment","")).strip().lower()
                why = str(it.get("why","")).strip()
                nums = it.get("numbers", [])
                if not isinstance(nums, list): nums = []
                # scrub advicey verbs from 'why'
                why = _scrub_advice(why)
                out.append({"driver": drv, "assessment": ass, "why": why, "numbers": [str(x) for x in nums]})
            elif isinstance(it, str):
                # turn a bare string into a minimal driver line
                out.append({"driver": "", "assessment": "", "why": _scrub_advice(it), "numbers": []})
        return out

    # Keep only the one section
    sc = data.get("score_context") or {}
    drivers = _norm_driver_list(sc.get("drivers"))
    summary = _scrub_advice(sc.get("summary",""))

    data = {"score_context": {"summary": summary, "drivers": drivers}}

    # Ensure at least one driver
    if not data["score_context"]["drivers"]:
        data["score_context"]["drivers"] = [{"driver":"—","assessment":"neutral","why":"No clear driver surfaced from current inputs.","numbers":[]}]

    return data



# ==============================
# LAZY LOADERS (ticker-only, CSV sorted by ticker/date)
# ==============================

last_modified = (DATA_DIR / "qry_graph_data_25.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_stats_for_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(path, chunksize=200000):
        cols = {c.lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        if tcol is None:
            df = chunk.copy()
            df.columns = [c.strip().lower() for c in df.columns]
            return df
        m = chunk[tcol] == ticker
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
    return df

last_modified = (DATA_DIR / "qry_graph_data_01.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g1_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(path, chunksize=200000):
        cols = {c.lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        m = chunk[tcol] == ticker if tcol else pd.Series([True]*len(chunk))
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_02.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g2_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 2: Trend Lines
      expected cols (case-insensitive):
        date, st_trend, mt_trend, lt_trend, [ticker]
      values may be fractions (0.12) or percentages (12); we normalize to percent.
    """
    if not Path(path).exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(path, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        mask = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if mask.any():
            part = chunk.loc[mask].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()

    df = pd.concat(out, ignore_index=True)
    # normalize names
    rename = {
        "st_trend": "st",
        "mt_trend": "mt",
        "lt_trend": "lt",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    if "date" not in df.columns or not {"st","mt","lt"}.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["st","mt","lt"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # if values look like fractions (<=1), convert to percent
    mx = pd.concat([df["st"], df["mt"], df["lt"]], axis=0).abs().max()
    if pd.notna(mx) and mx <= 1.0:
        df[["st","mt","lt"]] = df[["st","mt","lt"]] * 100.0

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_03.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g3_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 3: Price + mid/long probable anchors
      expected cols (case-insensitive):
        date, close, mt_pb_anchor, lt_pb_anchor, [ticker]
    """
    if not Path(path).exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(path, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        mask = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if mask.any():
            part = chunk.loc[mask].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()

    df = pd.concat(out, ignore_index=True)
    need = {"date","close","mt_pb_anchor","lt_pb_anchor"}
    if not need.issubset(set(df.columns)):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["close","mt_pb_anchor","lt_pb_anchor"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_04.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g4_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 4: Gap to LT probable anchor + bands
      expected cols (case-insensitive):
        date, gap_lt, gap_lt_avg, gap_lt_hi, gap_lt_lo, [ticker]
    """
    if not Path(path).exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(path, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        mask = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if mask.any():
            part = chunk.loc[mask].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()

    df = pd.concat(out, ignore_index=True)
    need = {"date","gap_lt","gap_lt_avg","gap_lt_hi","gap_lt_lo"}
    if not need.issubset(set(df.columns)):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["gap_lt","gap_lt_avg","gap_lt_hi","gap_lt_lo"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_05.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g5_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 5: Z-Score 30d with bands
      expected (case-insensitive): date, [ticker], z-score, z-score_avg, z-score_hi, z-score_lo
      also supports: zscore, zscore_avg, zscore_hi, zscore_lo
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        mask = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if mask.any():
            part = chunk.loc[mask].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    # normalize names
    rename = {
        "z-score": "z",
        "zscore": "z",
        "z-score_avg": "avg",
        "zscore_avg": "avg",
        "z-score_hi": "hi",
        "zscore_hi": "hi",
        "z-score_lo": "lo",
        "zscore_lo": "lo",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    need = {"date", "z", "avg", "hi", "lo"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["z", "avg", "hi", "lo"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_06.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g6_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 6: Z-Score Percentile Rank (0-100)
      expected: date, [ticker], z-score rank
      supports: z-score rank, zscore rank, zscore_rank, z_rank -> normalized to 'rank'
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        mask = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if mask.any():
            part = chunk.loc[mask].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    # normalize names
    for cand in ["z-score rank", "zscore rank", "zscore_rank", "z_rank", "rank"]:
        if cand in df.columns:
            df = df.rename(columns={cand: "rank"})
            break
    need = {"date", "rank"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

    # If values look 0..1, convert to 0..100
    mx = df["rank"].abs().max()
    if pd.notna(mx) and mx <= 1.0:
        df["rank"] = df["rank"] * 100.0

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_07.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g7_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 7: Rvol 30d with bands
      expected: date, [ticker], rvol, rvol_avg, rvol_hi, rvol_low
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        mask = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if mask.any():
            part = chunk.loc[mask].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    need = {"date", "rvol", "rvol_avg", "rvol_hi", "rvol_low"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["rvol", "rvol_avg", "rvol_hi", "rvol_low"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # If values look like fractions (<=1), convert to percent scale
    mx = pd.concat([df["rvol"], df["rvol_avg"], df["rvol_hi"], df["rvol_low"]], axis=0).abs().max()
    if pd.notna(mx) and mx <= 1.0:
        df[["rvol", "rvol_avg", "rvol_hi", "rvol_low"]] = df[["rvol", "rvol_avg", "rvol_hi", "rvol_low"]] * 100.0

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_08.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g8_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 8: Sharpe Ratio 30d with bands
      Accepts (case-insensitive):
        date, [ticker], sharpe OR sharpe_ratio,
        sharpe_avg, sharpe_hi, sharpe_lo/sharpe_low
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()

    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    # normalize names
    rename = {
        "sharpe_ratio": "sharpe",
        "sharpe": "sharpe",
        "sharpe_avg": "avg",
        "sharpe_hi": "hi",
        "sharpe_lo": "lo",
        "sharpe_low": "lo",   # alias from your CSV
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    need = {"date", "sharpe", "avg", "hi", "lo"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["sharpe", "avg", "hi", "lo"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_09.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g9_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 9: Sharpe Ratio Percentile Rank (0–100)
      Accepts (case-insensitive):
        date, [ticker], sharpe_rank / sharpe percentile / percentile / rank
      If values are 0..1, auto-scale to 0..100.
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()

    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    for cand in ["sharpe_rank", "sharpe percentile", "percentile", "rank"]:
        if cand in df.columns:
            df = df.rename(columns={cand: "rank"})
            break
    need = {"date", "rank"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

    mx = df["rank"].abs().max()
    if pd.notna(mx) and mx <= 1.0:
        df["rank"] = df["rank"] * 100.0

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_10.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g10_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 10: Ivol Prem/Disc 30d with bands (percent)
      Accepts (case-insensitive):
        date, [ticker],
        prem_disc, prem_disc_avg, prem_disc_hi, prem_disc_lo
        OR legacy ivol names: ivol_pd, ivol_avg, ivol_hi, ivol_lo/ivol_low
      If values are 0..1, auto-scale to percent (×100).
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()

    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    # normalize to a single schema: ivol_pd, avg, hi, lo
    rename = {
        # legacy ivol names
        "ivol_p/d": "ivol_pd",
        "ivol_pd": "ivol_pd",
        "ivol_avg": "avg",
        "ivol_hi": "hi",
        "ivol_lo": "lo",
        "ivol_low": "lo",
        # prem/discount names (your CSV)
        "prem_disc": "ivol_pd",
        "prem_disc_avg": "avg",
        "prem_disc_hi": "hi",
        "prem_disc_lo": "lo",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    need = {"date", "ivol_pd", "avg", "hi", "lo"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["ivol_pd", "avg", "hi", "lo"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # If looks like fractions (<=1), convert to percent scale
    mx = pd.concat([df["ivol_pd"], df["avg"], df["hi"], df["lo"]], axis=0).abs().max()
    if pd.notna(mx) and mx <= 1.0:
        df[["ivol_pd", "avg", "hi", "lo"]] = df[["ivol_pd", "avg", "hi", "lo"]] * 100.0

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_11.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g11_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 11: Signal Score (left axis) with Close (right axis)
      expected (case-insensitive): date, [ticker], ticker_name, exposure, category, close, model_score
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()

    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    df = df.rename(columns={"model_score": "score"})
    need = {"date", "close", "score"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"]  = pd.to_datetime(df["date"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["score"] = pd.to_numeric(df["score"], errors="coerce")

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_12.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g12_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
    """
    Graph 12: Scatter — Z-Score (x) vs Ivol Prem/Disc (y, %)
      expected (case-insensitive): date, [ticker], zscore, prem_disc
      If prem_disc is 0..1, auto-scale to percent (×100).
      File will typically have TWO rows per ticker: latest and ~30d prior.
    """
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()

    out = []
    for chunk in pd.read_csv(p, chunksize=200000):
        cols = {c.strip().lower(): c for c in chunk.columns}
        tcol = cols.get("ticker")
        m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
        if m.any():
            part = chunk.loc[m].copy()
            part.columns = [c.strip().lower() for c in part.columns]
            out.append(part)
        elif out:
            break
    if not out:
        return pd.DataFrame()
    df = pd.concat(out, ignore_index=True)

    df = df.rename(columns={"zscore": "z", "prem_disc": "pd"})
    need = {"date", "z", "pd"}
    if not need.issubset(df.columns):
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["z"]    = pd.to_numeric(df["z"], errors="coerce")
    df["pd"]   = pd.to_numeric(df["pd"], errors="coerce")

    # Convert prem/discount to % if it looks like fraction
    #mx = df["pd"].abs().max()
    #if pd.notna(mx) and mx <= 1.0:
    df["pd"] = df["pd"] * 100.0

    return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_13.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g13_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 13: Daily Returns (%) with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker],
            daily_return_pct, daily_return_avg_pct, daily_return_hi_pct, daily_return_lo_pct
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {
            "date", "daily_return_pct",
            "daily_return_avg_pct", "daily_return_hi_pct", "daily_return_lo_pct"
        }
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["daily_return_pct", "daily_return_avg_pct", "daily_return_hi_pct", "daily_return_lo_pct"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # if values look like 0..1, convert to % scale
        mx = pd.concat([
            df["daily_return_pct"],
            df["daily_return_avg_pct"],
            df["daily_return_hi_pct"],
            df["daily_return_lo_pct"]
        ]).abs().max()
        if pd.notna(mx) and mx <= 1.0:
            df[["daily_return_pct", "daily_return_avg_pct",
                "daily_return_hi_pct", "daily_return_lo_pct"]] *= 100.0

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_14.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g14_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 14: Daily Range with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], daily_range, daily_range_avg, daily_range_hi, daily_range_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "daily_range", "daily_range_avg", "daily_range_hi", "daily_range_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["daily_range", "daily_range_avg", "daily_range_hi", "daily_range_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_15.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g15_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 15: Daily Volume with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], daily_volume, daily_volume_avg, daily_volume_hi, daily_volume_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "daily_volume", "daily_volume_avg", "daily_volume_hi", "daily_volume_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["daily_volume", "daily_volume_avg", "daily_volume_hi", "daily_volume_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_16.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g16_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 16: Weekly Returns (%) with Avg/High/Low bands
        expected (case-insensitive):
            date, [ticker],
            weekly_return_pct, weekly_return_avg_pct, weekly_return_hi_pct, weekly_return_lo_pct
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {
            "date", "weekly_return_pct",
            "weekly_return_avg_pct", "weekly_return_hi_pct", "weekly_return_lo_pct"
        }
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["weekly_return_pct", "weekly_return_avg_pct", "weekly_return_hi_pct", "weekly_return_lo_pct"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # if values look like 0..1, convert to % scale
        mx = pd.concat([
            df["weekly_return_pct"],
            df["weekly_return_avg_pct"],
            df["weekly_return_hi_pct"],
            df["weekly_return_lo_pct"]
        ]).abs().max()
        if pd.notna(mx) and mx <= 1.0:
            df[["weekly_return_pct", "weekly_return_avg_pct",
                "weekly_return_hi_pct", "weekly_return_lo_pct"]] *= 100.0

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_17.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g17_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 17: Weekly Range with Avg/High/Low bands
        expected (case-insensitive):
            date, [ticker], weekly_range, weekly_range_avg, weekly_range_hi, weekly_range_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "weekly_range", "weekly_range_avg", "weekly_range_hi", "weekly_range_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["weekly_range", "weekly_range_avg", "weekly_range_hi", "weekly_range_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_18.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g18_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 18: Weekly Volume with Avg/High/Low bands
        expected (case-insensitive):
            date, [ticker], weekly_volume, weekly_volume_avg, weekly_volume_hi, weekly_volume_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "weekly_volume", "weekly_volume_avg", "weekly_volume_hi", "weekly_volume_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["weekly_volume", "weekly_volume_avg", "weekly_volume_hi", "weekly_volume_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_19.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g19_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 19: Monthly Returns (%) with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], monthly_return, monthly_return_avg, monthly_return_hi, monthly_return_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "monthly_return", "monthly_return_avg", "monthly_return_hi", "monthly_return_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["monthly_return", "monthly_return_avg", "monthly_return_hi", "monthly_return_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # If returns look like 0..1, convert to %
        mx = pd.concat([
            df["monthly_return"], df["monthly_return_avg"],
            df["monthly_return_hi"], df["monthly_return_lo"]
        ]).abs().max()
        if pd.notna(mx) and mx <= 1.0:
            df[["monthly_return", "monthly_return_avg",
                "monthly_return_hi", "monthly_return_lo"]] *= 100.0

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_20.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g20_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 20: Monthly Range with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], monthly_range, monthly_range_avg, monthly_range_hi, monthly_range_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "monthly_range", "monthly_range_avg", "monthly_range_hi", "monthly_range_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["monthly_range", "monthly_range_avg", "monthly_range_hi", "monthly_range_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_21.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g21_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 21: Monthly Volume with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], monthly_volume, monthly_volume_avg, monthly_volume_hi, monthly_volume_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "monthly_volume", "monthly_volume_avg", "monthly_volume_hi", "monthly_volume_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["monthly_volume", "monthly_volume_avg", "monthly_volume_hi", "monthly_volume_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_22.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g22_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 22: Short-Term Trend with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], st_trend, st_avg, st_hi, st_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            # case-insensitive access
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "st_trend", "st_avg", "st_hi", "st_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["st_trend", "st_avg", "st_hi", "st_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # If values look like 0..1, convert to % scale
        mx = pd.concat([df["st_trend"], df["st_avg"], df["st_hi"], df["st_lo"]]).abs().max()
        if pd.notna(mx) and mx <= 1.0:
            df[["st_trend", "st_avg", "st_hi", "st_lo"]] *= 100.0

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_23.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g23_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 23: Mid-Term Trend with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], mt_trend, mt_avg, mt_hi, mt_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "mt_trend", "mt_avg", "mt_hi", "mt_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["mt_trend", "mt_avg", "mt_hi", "mt_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        mx = pd.concat([df["mt_trend"], df["mt_avg"], df["mt_hi"], df["mt_lo"]]).abs().max()
        if pd.notna(mx) and mx <= 1.0:
            df[["mt_trend", "mt_avg", "mt_hi", "mt_lo"]] *= 100.0

        return df.sort_values("date").reset_index(drop=True)

last_modified = (DATA_DIR / "qry_graph_data_24.csv").stat().st_mtime
@st.cache_data(show_spinner=False)
def load_g24_ticker(path: Path, ticker: str,_mtime: float = last_modified) -> pd.DataFrame:
        """
        Graph 24: Long-Term Trend with Avg/High/Low bands
          expected (case-insensitive):
            date, [ticker], lt_trend, lt_avg, lt_hi, lt_lo
        """
        p = Path(path)
        if not p.exists():
            return pd.DataFrame()
        out = []
        for chunk in pd.read_csv(p, chunksize=200000):
            cols = {c.strip().lower(): c for c in chunk.columns}
            tcol = cols.get("ticker")
            m = (chunk[tcol] == ticker) if tcol else pd.Series(True, index=chunk.index)
            if m.any():
                part = chunk.loc[m].copy()
                part.columns = [c.strip().lower() for c in part.columns]
                out.append(part)
            elif out:
                break
        if not out:
            return pd.DataFrame()
        df = pd.concat(out, ignore_index=True)

        need = {"date", "lt_trend", "lt_avg", "lt_hi", "lt_lo"}
        if not need.issubset(df.columns):
            return pd.DataFrame()

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["lt_trend", "lt_avg", "lt_hi", "lt_lo"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        mx = pd.concat([df["lt_trend"], df["lt_avg"], df["lt_hi"], df["lt_lo"]]).abs().max()
        if pd.notna(mx) and mx <= 1.0:
            df[["lt_trend", "lt_avg", "lt_hi", "lt_lo"]] *= 100.0

        return df.sort_values("date").reset_index(drop=True)




# -------------------------
# Stat Box - Begin
# -------------------------

# Layout: left = stat box, middle = centered graph, right = spacer (centers graph on page)
#col_left, col_center = st.columns([3.8, 9.2], gap="small")



st.markdown('<div id="stat-center"></div>', unsafe_allow_html=True)
_, mid_stat, _ = st.columns([.9,3,1])

with mid_stat:

    # ==============================
    # Stat Box (baseline)
    # ==============================
    #import streamlit as st
    #import pandas as pd
    #from pathlib import Path

    DEFAULT_TICKER = "SPY"

    
    def _resolve_ticker():
        # 1) user’s live selection (search box / in-app nav)
        ss = st.session_state.get("active_ticker")
        if isinstance(ss, str) and ss:
            return ss.upper()
        # 2) deep link (?ticker=…)
        qp = st.query_params.get("ticker")
        if qp:
            return str(qp).upper()
        # 3) legacy (other pages might have set st.session_state["ticker"])
        legacy = st.session_state.get("ticker")
        if isinstance(legacy, str) and legacy:
            return legacy.upper()
        # 4) fresh load
        return DEFAULT_TICKER

    TICKER = _resolve_ticker()
    st.session_state["active_ticker"] = TICKER   # persist for subsequent pages
    
    # --- AI panel reset on ticker change ---
    prev = st.session_state.get("ai_prev_ticker")
    if prev != TICKER:
        # collapse the expander and forget prior text
        st.session_state["ai_open"] = False
        st.session_state["ai_last_insights"] = None
        st.session_state["ai_last_ctx"] = None
        st.session_state["ai_last_depth"] = None
        # clear only this function's cache (safe; it is @st.cache_data)
        try:
            get_ai_insights.clear()  # streamlit will no-op if not yet cached
        except Exception:
            pass
        st.session_state["ai_prev_ticker"] = TICKER


    # ---------- helpers ----------
    def _usd(x):
        try: return f"${float(x):,.2f}"
        except: return ""

    def _pct(x):
        try:
            v = float(x)
            if not math.isfinite(v):      # NaN or +/-Inf → blank
                return ""
            if abs(v) <= 1.0:
                v *= 100.0
            return f"{v:,.1f}%"
        except:
            return ""

    def _rr(x):
        try:
            v = float(x)
            return f"{v:,.2f}" if v >= 0 else f"({abs(v):,.2f})"
        except:
            return ""

    def _score(x):
        try: return f"{int(round(float(x)))}"
        except: return ""

    def _fmt_date(x):
        try: return pd.to_datetime(x).strftime("%m/%d/%Y")
        except: return ""

    # ---------- loaders ----------
    @st.cache_data(show_spinner=False)
    def load_ticker_directory(csv_path: Path) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        sym_col  = next((c for c in df.columns if c.lower() in ("ticker","tkr","symbol")), "ticker")
        name_col = next((c for c in df.columns if c.lower() in ("ticker_name","name","company_name")), "ticker_name")
        out = (df[[sym_col, name_col]]
               .rename(columns={sym_col:"ticker", name_col:"ticker_name"})
               .dropna().drop_duplicates().copy())
        out["ticker"] = out["ticker"].astype(str).str.strip().str.upper()
        out["ticker_name"] = out["ticker_name"].astype(str).str.strip().str.upper()
        out["display"] = out["ticker"] + " - " + out["ticker_name"]
        out["tkr"] = out["ticker"]; out["nam"] = out["ticker_name"]
        return out.sort_values(["ticker","ticker_name"]).reset_index(drop=True)

    @st.cache_data(show_spinner=False)
    def load_stats_for_ticker(csv_path: Path, ticker: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip().lower() for c in df.columns]
        tcol = next((c for c in df.columns if c in ("ticker","tkr","symbol")), None)
        if not tcol: return pd.DataFrame()
        sub = df[df[tcol].astype(str).str.upper() == (ticker or "").upper()].copy()
        if sub.empty: return sub
        if "date" in sub.columns:
            num_cols = sub.select_dtypes(include=[np.number]).columns
            sub[num_cols] = sub[num_cols].where(np.isfinite(sub[num_cols]), np.nan)
            try: sub = sub.sort_values("date")
            except: pass
        return sub

    # ---------- stat-box renderer ----------
    def render_stat_box_component(row: pd.Series):
        title  = f"{row.get('ticker_name', row.get('ticker',''))} - {_fmt_date(row.get('date'))}"
        ticker = (row.get("ticker","") or "").upper()
        close  = _usd(row.get("close"))
        anchor = _usd(row.get("lt_pt_sm"))
        chg    = _pct(row.get("change_pct"))

        d_low, d_high = _usd(row.get("day_pr_low")),   _usd(row.get("day_pr_high"))
        d_dn,  d_up   = _pct(row.get("day_dn")),       _pct(row.get("day_up"))
        d_rr          = _rr(row.get("day_rr_ratio"))

        w_low, w_high = _usd(row.get("week_pr_low")),  _usd(row.get("week_pr_high"))
        w_dn,  w_up   = _pct(row.get("week_dn")),      _pct(row.get("week_up"))
        w_rr          = _rr(row.get("week_rr_ratio"))

        m_low, m_high = _usd(row.get("month_pr_low")), _usd(row.get("month_pr_high"))
        m_dn,  m_up   = _pct(row.get("month_dn")),     _pct(row.get("month_up"))
        m_rr          = _rr(row.get("month_rr_ratio"))

        ivol   = _pct(row.get("ivol"))
        rvol   = _pct(row.get("rvol"))
        ivolpd = _pct(row.get("prem_disc"))

        mscore = _score(row.get("model_score"))
        rv = row.get("rating")
        rating = "" if pd.isna(rv) else str(rv).title()   # blank when null

        from streamlit.components.v1 import html as st_html
        html_doc = f"""<!doctype html>
<meta charset="utf-8">
<style>
  :root {{
    --cw: 80px;
    --border-outer: 1px solid #D7D9E0;
    --border-inner: 0.5px solid #D7D9E0;
    --pad: 6px 8px;
  }}
  .sb-card {{
    border: var(--border-outer);
    border-radius: 8px;
    background: #fff;
    padding: 10px 12px;
    width: fit-content;
    font-family: system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }}
  .sb-title {{ margin: 0 0 6px 0; font-size: 14px; font-weight: 700; color: #1a1a1a; white-space: nowrap; }}
  table.sb {{ border-collapse: collapse; table-layout: fixed; border: var(--border-outer); margin: 0; }}
  table.sb + table.sb {{ margin-top: 8px; }}
  th, td {{
    border: var(--border-inner); padding: var(--pad);
    font-size: 12px; white-space: nowrap; box-sizing: border-box; background: #fff;
  }}
  th {{ background: #F6F7FB; text-align: center; font-weight: 600; color: #3c435a; }}
  td.right  {{ text-align: right; }}  td.center {{ text-align: center; }}
  col {{ width: var(--cw); }}
</style>

<div class="sb-card">
  <div class="sb-title">{title}</div>

<div style="font-size:12px; color:#666; margin-bottom:4px;">
  Markmentum Research Stat Box:
</div>

  <table class="sb">
    <colgroup><col><col><col><col></colgroup>
    <thead><tr><th>Ticker</th><th>Close</th><th>LT Anchor</th><th>Change %</th></tr></thead>
    <tbody><tr>
      <td class="center">{ticker}</td>
      <td class="right">{close}</td>
      <td class="right">{anchor}</td>
      <td class="right">{chg}</td>
    </tr></tbody>
  </table>

  <table class="sb">
    <colgroup><col><col><col><col><col><col></colgroup>
    <thead><tr><th>Period</th><th>PR Low</th><th>PR High</th><th>↓ %</th><th>↑ %</th><th>R/R Ratio</th></tr></thead>
    <tbody>
      <tr><th>Day</th>   <td class="right">{d_low}</td> <td class="right">{d_high}</td> <td class="right">{d_dn}</td> <td class="right">{d_up}</td> <td class="right">{d_rr}</td></tr>
      <tr><th>Week</th>  <td class="right">{w_low}</td> <td class="right">{w_high}</td> <td class="right">{w_dn}</td> <td class="right">{w_up}</td> <td class="right">{w_rr}</td></tr>
      <tr><th>Month</th> <td class="right">{m_low}</td> <td class="right">{m_high}</td> <td class="right">{m_dn}</td> <td class="right">{m_up}</td> <td class="right">{m_rr}</td></tr>
    </tbody>
  </table>

  <table class="sb">
    <colgroup><col><col><col><col><col></colgroup>
    <thead><tr><th>Ivol</th><th>Rvol</th><th>Ivol P/D</th><th>MM Score</th><th>Rating</th></tr></thead>
    <tbody><tr>
      <td class="right">{ivol}</td>
      <td class="right">{rvol}</td>
      <td class="right">{ivolpd}</td>
      <td class="right">{mscore}</td>
      <td class="center">{rating}</td>
    </tr></tbody>
  </table>
</div>
"""
        st_html(html_doc, height=330, scrolling=False)

    # ---------- type-ahead above the card ----------
    def render_ticker_typeahead_above(FILE_STATS: Path):
        dir_df = load_ticker_directory(FILE_STATS)
        if "active_ticker" not in st.session_state:
            st.session_state["active_ticker"] = DEFAULT_TICKER

        SEARCH_BOX_WIDTH_PX = 515
        st.markdown(
            f"""
            <style>
              div[data-testid="stTextInput"]:has(input[aria-label="Find a ticker"]) {{
                  width: {SEARCH_BOX_WIDTH_PX}px !important;
                  max-width: {SEARCH_BOX_WIDTH_PX}px !important;
                  display: inline-block !important;
                  margin-bottom: 2px !important;
              }}
              div[data-testid="stTextInput"]:has(input[aria-label="Find a ticker"]) input {{
                  width: 100% !important; max-width: 100% !important;
              }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        try:
            default_display = dir_df.loc[dir_df["ticker"] == st.session_state["active_ticker"], "display"].iloc[0]
        except IndexError:
            default_display = st.session_state["active_ticker"]

        q = st.text_input(
            "Find a ticker", value=default_display.split(" - ")[0],
            key="sb_query", label_visibility="collapsed",
            placeholder="Type ticker or name…"
        )
        # --- typeahead suggester (drop-in) ---
        # assumes: q (text), dir_df with 'tkr','nam', and SEARCH_BOX_WIDTH_PX defined
        if "display" not in dir_df.columns:
            dir_df["display"] = dir_df["tkr"] + " - " + dir_df["nam"]

        raw = (q or "").strip()
        query = raw.upper()
        entered = (raw.split(" - ")[0].strip().upper()
               if " - " in raw else (query.split()[0] if query else ""))

        tickers = set(dir_df["tkr"])

        # 1) exact ticker -> select immediately
        if entered and entered in tickers and entered != st.session_state.get("active_ticker"):
            st.session_state["active_ticker"] = entered
            st.query_params.update({"ticker": entered})
            st.rerun()

        # 2) show suggestions when not an exact ticker
        options = []
        if query and entered not in tickers:
            # rank: ticker startswith > ticker contains > name contains
            s1 = dir_df[dir_df["tkr"].str.startswith(query, na=False)]
            s2 = dir_df[dir_df["tkr"].str.contains(query, na=False, regex=False)
                & ~dir_df.index.isin(s1.index)]
            # use RAW (not upper) for names + case-insensitive search; regex=False avoids '.' and '&' issues
            s3 = dir_df[dir_df["nam"].str.contains(raw, case=False, na=False, regex=False)
                        & ~dir_df.index.isin(s1.index.union(s2.index))]

            ranked = (pd.concat([s1, s2, s3], axis=0)
                .drop_duplicates("tkr", keep="first")
                .head(10))
            options = ranked["display"].tolist()

        # 3) render suggestion list as buttons (Google-like)
        if options:
            st.markdown(
                f"""
                <div style="border:1px solid #D7D9E0;border-radius:6px;background:#fff;
                    padding:6px 0;max-width:{SEARCH_BOX_WIDTH_PX}px;
                    max-height:280px;overflow:auto;margin-top:-2px;">
                """,
                unsafe_allow_html=True,
            )
            for i, disp in enumerate(options):
                if st.button(disp, key=f"sb_sugg_{i}", use_container_width=True):
                    chosen = disp.split(" - ")[0]  # map label -> ticker
                    st.session_state["active_ticker"] = chosen
                    st.query_params.update({"ticker": chosen})
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
# --- end typeahead ---

    if "range_sel" not in st.session_state:
        st.session_state["range_sel"] = "All"

    st.markdown(
        """
        <style>
          div[data-testid="stVerticalBlock"]{ gap:4px !important; row-gap:4px !important; }
          div[data-testid="stSegmentedControl"]{ max-width:520px; width:520px; margin:4 !important; padding:4 !important; }
          div[data-testid="stTextInput"]{
            width:520px !important; max-width:520px !important; display:inline-block !important;
            margin-top:3px !important; margin-bottom:0px !important; padding:0 !important;
          }
          div[data-testid="stTextInput"] input{ width:100% !important; max-width:100% !important; }
          div[data-testid="stIFrame"]{ margin-top:0 !important; padding-top:0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    RANGE_OPTIONS = ["3M","6M","YTD","1Y","All"]
    try:
        st.segmented_control("Range", options=RANGE_OPTIONS, key="range_sel", label_visibility="collapsed")
    except AttributeError:
        st.radio("Range", options=RANGE_OPTIONS, key="range_sel", horizontal=True, label_visibility="collapsed")

    render_ticker_typeahead_above(FILE_STATS)

    _active = (st.session_state.get("active_ticker", DEFAULT_TICKER) or DEFAULT_TICKER).upper()
    _df = load_stats_for_ticker(FILE_STATS, _active)
    if _df.empty:
        st.info("No data available for the selected ticker.")
    else:
        _row = _df.sort_values("date").iloc[-1] if "date" in _df.columns else _df.iloc[-1]
        if "ticker_name" not in _row.index:
            try:
                _dir = load_ticker_directory(FILE_STATS)
                _row.loc["ticker_name"] = _dir.loc[_dir["ticker"] == _active, "ticker_name"].iloc[0]
            except Exception:
                _row.loc["ticker_name"] = _active
        render_stat_box_component(_row)

# optional small spacer
#st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)


def _breach_flag(close, low, high):
    """Return 'below_low', 'above_high', or 'none' based on close vs range."""
    try:
        if close is None or low is None or high is None:
            return "none"
        c = float(close); lo = float(low); hi = float(high)
        if c < lo:  return "below_low"
        if c > hi:  return "above_high"
        return "none"
    except Exception:
        return "none"


# >>> ADD: Use the exact objects you already computed for the Deep Dive visuals.
def collect_deepdive_context(ticker: str, as_of: str, stat_row) -> dict:
    """Build context from the SAME row you use to render the stat box."""
    # ——— values directly from your stat box row ———
    last_price = float(stat_row.get("close"))
    anchor_val = float(stat_row.get("lt_pt_sm"))
    anchor_gap_pct= float(stat_row.get("change_pct")*100)
    day_low   = float(stat_row.get("day_pr_low"))
    day_high  = float(stat_row.get("day_pr_high"))
    day_down  = float(stat_row.get("day_dn")*100)
    day_up  = float(stat_row.get("day_up")*100)
    day_rr = float(stat_row.get("day_rr_ratio"))
    week_low  = float(stat_row.get("week_pr_low"))
    week_high = float(stat_row.get("week_pr_high"))
    week_down  = float(stat_row.get("week_dn")*100)
    week_up  = float(stat_row.get("week_up")*100)
    week_rr = float(stat_row.get("week_rr_ratio"))
    month_low = float(stat_row.get("month_pr_low"))
    month_high= float(stat_row.get("month_pr_high"))
    month_down  = float(stat_row.get("month_dn")*100)
    month_up  = float(stat_row.get("month_up")*100)
    month_rr = float(stat_row.get("month_rr_ratio"))
    ivol = float(stat_row.get("ivol")*100)
    rvol = float(stat_row.get("rvol")*100)
    ivolpd = float(stat_row.get("prem_disc")*100) 
    score_current = stat_row.get("model_score")
    rating = stat_row.get("rating")
    day_breach   = _breach_flag(last_price, day_low,   day_high)
    week_breach  = _breach_flag(last_price, week_low,  week_high)
    month_breach = _breach_flag(last_price, month_low, month_high)

    close_vs_anchor = None
    if (anchor_val is not None) and (last_price is not None):
        if float(anchor_val) > float(last_price):
            close_vs_anchor = "Positive - Close is BELOW the long-term anchor"
        elif float(anchor_val) < float(last_price):
            close_vs_anchor = "Negative - Close is ABOVE the long-term anchor"
        else:
            close_vs_anchor = "Neutral - Close equals the long-term anchor"


#----graphs -----------------
# ---- G2 (Trend lines) ----
# Requires: load_g2_ticker(...) from earlier and DATA_DIR defined.
# G2 loader returns columns normalized to: ['date','st','mt','lt'] for the selected ticker.
    try:
        g2_df = load_g2_ticker(DATA_DIR / "qry_graph_data_02.csv", ticker=ticker)
    except Exception:
        g2_df = pd.DataFrame()

    trend_short = trend_mid = trend_long = None

    if not g2_df.empty:
        # ensure datetime + pick last observation at/<= as_of
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g2_df["date"].dtype.kind != "M":
            g2_df = g2_df.assign(date=pd.to_datetime(g2_df["date"], errors="coerce"))

        g2_row = g2_df.loc[g2_df["date"] <= asof_dt].tail(1)
        if not g2_row.empty:
            r = g2_row.iloc[0]
            trend_short = float(r["st"]) if pd.notna(r["st"]) else None
            trend_mid   = float(r["mt"]) if pd.notna(r["mt"]) else None
            trend_long  = float(r["lt"]) if pd.notna(r["lt"]) else None

# ---- G4 (Gap to LT anchor + bands) ----
# Requires: load_g4_ticker(...) and DATA_DIR defined.
# G4 loader returns columns: ['date','gap_lt','gap_lt_avg','gap_lt_hi','gap_lt_lo'] for this ticker.
    try:
        g4_df = load_g4_ticker(DATA_DIR / "qry_graph_data_04.csv", ticker=ticker)
    except Exception:
        g4_df = pd.DataFrame()

        gap_lt = gap_lt_avg = gap_lt_hi = gap_lt_lo = None  # defaults

    if not g4_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g4_df["date"].dtype.kind != "M":
            g4_df = g4_df.assign(date=pd.to_datetime(g4_df["date"], errors="coerce"))

        g4_row = g4_df.loc[g4_df["date"] <= asof_dt].tail(1)
        if not g4_row.empty:
            r = g4_row.iloc[0]
            # All are numeric already; guard for NaNs
            gap_lt = float(r["gap_lt"]) if pd.notna(r["gap_lt"]) else None
            gap_lt_avg = float(r["gap_lt_avg"]) if pd.notna(r["gap_lt_avg"]) else None
            gap_lt_hi  = float(r["gap_lt_hi"])  if pd.notna(r["gap_lt_hi"])  else None
            gap_lt_lo  = float(r["gap_lt_lo"])  if pd.notna(r["gap_lt_lo"])  else None
            # simple, explicit flags the model can latch onto
            is_gap_stretched = (float(gap_lt) >= float(gap_lt_hi)) or (float(gap_lt) <= float(gap_lt_lo))

    # --- Deterministic relation labels the model MUST use ---
    trend_mix_text = None
    if (trend_short is not None) and (trend_mid is not None):
        if trend_short > trend_mid:
            trend_mix_text = "Negative - Short-term trend is ABOVE the Mid-term trend"
        elif trend_short < trend_mid:
            trend_mix_text = "Positive - Short-term trend is BELOW the Mid-term trend"
    else:
        trend_mix_text = "Neutral - Short-term equals Mid-term"
        
 
# ---- G5 (Z-Score 30D + bands) ----
# Requires: load_g5_ticker(...) and DATA_DIR defined.
# G5 loader returns columns for this ticker: ['date','z','avg','hi','lo'] (already numeric).

    try:
        g5_df = load_g5_ticker(DATA_DIR / "qry_graph_data_05.csv", ticker=ticker)
    except Exception:
        g5_df = pd.DataFrame()

    zscore = zscore_avg = zscore_hi = zscore_lo = None

    if not g5_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g5_df["date"].dtype.kind != "M":
            g5_df = g5_df.assign(date=pd.to_datetime(g5_df["date"], errors="coerce"))

        g5_row = g5_df.loc[g5_df["date"] <= asof_dt].tail(1)
        if not g5_row.empty:
            r = g5_row.iloc[0]
            zscore     = float(r["z"])   if pd.notna(r["z"])   else None
            zscore_avg = float(r["avg"]) if pd.notna(r["avg"]) else None
            zscore_hi  = float(r["hi"])  if pd.notna(r["hi"])  else None
            zscore_lo  = float(r["lo"])  if pd.notna(r["lo"])  else None

# ---- G6 (Z-Score Percentile Rank 0..100) ----
# Requires: load_g6_ticker(...) and DATA_DIR defined.
# G6 loader returns columns for this ticker: ['date','rank'] (already numeric 0..100).
    try:
        g6_df = load_g6_ticker(DATA_DIR / "qry_graph_data_06.csv", ticker=ticker)
    except Exception:
        g6_df = pd.DataFrame()

    zscore_rank = None

    if not g6_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g6_df["date"].dtype.kind != "M":
            g6_df = g6_df.assign(date=pd.to_datetime(g6_df["date"], errors="coerce"))

        g6_row = g6_df.loc[g6_df["date"] <= asof_dt].tail(1)
        if not g6_row.empty:
            r = g6_row.iloc[0]
            zscore_rank = float(r["rank"]) if pd.notna(r["rank"]) else None


# ---- G7 (Rvol 30D + bands) ----
# Requires: load_g7_ticker(...) and DATA_DIR defined.
# G7 loader returns for this ticker: ['date','rvol','rvol_avg','rvol_hi','rvol_low'] (numeric; % scaled if needed).

    try:
        g7_df = load_g7_ticker(DATA_DIR / "qry_graph_data_07.csv", ticker=ticker)
    except Exception:
        g7_df = pd.DataFrame()

    rvol_avg = rvol_hi = rvol_low = None  # defaults
    

    if not g7_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g7_df["date"].dtype.kind != "M":
            g7_df = g7_df.assign(date=pd.to_datetime(g7_df["date"], errors="coerce"))

        g7_row = g7_df.loc[g7_df["date"] <= asof_dt].tail(1)
        if not g7_row.empty:
            r = g7_row.iloc[0]
            rvol_avg = float(r["rvol_avg"]) if pd.notna(r["rvol_avg"]) else None
            rvol_hi  = float(r["rvol_hi"])  if pd.notna(r["rvol_hi"])  else None
            rvol_low = float(r["rvol_low"]) if pd.notna(r["rvol_low"]) else None


    
# ---- G8 (Sharpe Ratio 30D + bands) ----
# Requires: load_g8_ticker(...) and DATA_DIR defined.
# G8 loader returns (normalized) columns for this ticker: ['date','sharpe','avg','hi','lo'].

    try:
        g8_df = load_g8_ticker(DATA_DIR / "qry_graph_data_08.csv", ticker=ticker)
    except Exception:
        g8_df = pd.DataFrame()

    Sharpe = Sharpe_avg = Sharpe_hi = Sharpe_low = None

    if not g8_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g8_df["date"].dtype.kind != "M":
            g8_df = g8_df.assign(date=pd.to_datetime(g8_df["date"], errors="coerce"))

        g8_row = g8_df.loc[g8_df["date"] <= asof_dt].tail(1)
        if not g8_row.empty:
            r = g8_row.iloc[0]
            Sharpe     = float(r["sharpe"]) if pd.notna(r["sharpe"]) else None
            Sharpe_avg = float(r["avg"])    if pd.notna(r["avg"])    else None
            Sharpe_hi  = float(r["hi"])     if pd.notna(r["hi"])     else None
            Sharpe_low = float(r["lo"])     if pd.notna(r["lo"])     else None




# ---- G9 (Sharpe Ratio Percentile Rank 0..100) ----
# Requires: load_g9_ticker(...) and DATA_DIR defined.
# G9 loader returns for this ticker: ['date','rank'] (numeric; 0..100, auto-scaled if 0..1).

    try:
        g9_df = load_g9_ticker(DATA_DIR / "qry_graph_data_09.csv", ticker=ticker)
    except Exception:
        g9_df = pd.DataFrame()

    Sharpe_Rank = None

    if not g9_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g9_df["date"].dtype.kind != "M":
            g9_df = g9_df.assign(date=pd.to_datetime(g9_df["date"], errors="coerce"))

        g9_row = g9_df.loc[g9_df["date"] <= asof_dt].tail(1)
        if not g9_row.empty:
            v = g9_row.iloc[0]["rank"]
            Sharpe_Rank = float(v) if pd.notna(v) else None



# ---- G10 (Ivol Prem/Disc 30D + bands, percent) ----
# Requires: load_g10_ticker(...) and DATA_DIR defined.
# G10 loader returns for this ticker: ['date','ivol_pd','avg','hi','lo'] (numeric; % scaled if needed).

    try:
        g10_df = load_g10_ticker(DATA_DIR / "qry_graph_data_10.csv", ticker=ticker)
    except Exception:
        g10_df = pd.DataFrame()

    prem_disc = prem_disc_avg = prem_disc_hi = prem_disc_lo = None

    if not g10_df.empty:
        asof_dt = pd.to_datetime(as_of, errors="coerce")
        if g10_df["date"].dtype.kind != "M":
            g10_df = g10_df.assign(date=pd.to_datetime(g10_df["date"], errors="coerce"))

        g10_row = g10_df.loc[g10_df["date"] <= asof_dt].tail(1)
        if not g10_row.empty:
            r = g10_row.iloc[0]
            prem_disc     = float(r["ivol_pd"]) if pd.notna(r["ivol_pd"]) else None
            prem_disc_avg = float(r["avg"])     if pd.notna(r["avg"])     else None
            prem_disc_hi  = float(r["hi"])      if pd.notna(r["hi"])      else None
            prem_disc_lo  = float(r["lo"])      if pd.notna(r["lo"])      else None



    
    return {
        "as_of": as_of,
        "ticker": ticker,
        "price": last_price,
        "anchor_val": float(anchor_val),
        "anchor_gap_pct": anchor_gap_pct,
        "close_vs_anchor": close_vs_anchor,  
        "ranges": {
            "day":   {"low": day_low,   "high": day_high,   "breach": day_breach},
            "week":  {"low": week_low,  "high": week_high,  "breach": week_breach},
            "month": {"low": month_low, "high": month_high, "breach": month_breach},
        },       
        "vol_stats": {        
            "ivol": float(ivol) if ivol is not None else None,
            "rvol": float(rvol) if rvol is not None else None,
            "ivol_prem_disc": float(ivolpd) if ivolpd is not None else None,
        },
        "trend": {"short": trend_short, "mid": trend_mid, "long": trend_long},        
        "score": {
            "current": score_current,
            "rating": rating,
        },
        "Trend mix (Short vs Mid)": trend_mix_text,
        "day_down": day_down,
        "day_up": day_up,
        "day_rr": day_rr,
        "week_down": week_down,
        "week_up": week_up,
        "week_rr": week_rr,
        "month_down": month_down,
        "month_up": month_up,
        "month_rr": month_rr,
        "gap_lt": gap_lt,        
        "gap_lt_avg": gap_lt_avg,
        "gap_lt_hi": gap_lt_hi,
        "gap_lt_lo": gap_lt_lo,
        "Z-Score": zscore,
        "Z-Score_avg": zscore_avg,
        "Z-Score_hi": zscore_hi,
        "Z-Score_lo": zscore_lo,
        "Z-Score Rank": zscore_rank,
        "Rvol_avg": rvol_avg,
        "Rvol_hi": rvol_hi,
        "Rvol_low": rvol_low,
        "Sharpe": Sharpe,
        "Sharpe_avg": Sharpe_avg,
        "Sharpe_hi": Sharpe_hi,
        "Sharpe_low": Sharpe_low,
        "Sharpe_Rank": Sharpe_Rank,
        "prem_disc": prem_disc,
        "prem_disc_avg": prem_disc_avg,
        "prem_disc_hi": prem_disc_hi,
        "prem_disc_lo": prem_disc_lo,
        "Flags": {
            "gap_stretched": is_gap_stretched,
            "day_breach":  day_breach,         # you already compute these
            "week_breach": week_breach,
            "month_breach": month_breach,
        }
    }

#ctx = collect_deepdive_context(TICKER, AS_OF_DATE_STR, stat_row)

# ==============================
# AI Insight Panel (Deep Dive)
# ==============================

# Panel default: closed (we open it after the first run)
st.session_state.setdefault("ai_open", False)

with st.expander("🧠 Markmentum Score Explanation", expanded=st.session_state.get("ai_open", False)):
    go = st.button("Explain what stands out", use_container_width=True, key="dd_ai_go")

    st.caption(f"AI diag → sdk={_OPENAI_READY}, key={'yes' if _read_openai_key() else 'no'}")
    st.caption("⚠️ The Markmentum Score is for informational purposes only and not intended as investment advice. Please consult with your financial advisor before making investment decisions.")

    if _row is None:
        st.warning("No data available for the selected ticker.")
    else:
        if go:
            # Build context from on-screen data
            ctx = collect_deepdive_context(TICKER, date_str, _row)

            lo = ctx.get("month_pr_low"); hi = ctx.get("month_pr_high"); cl = ctx.get("close")
            try:
                if lo is not None and hi is not None and cl is not None and (hi - lo) != 0:
                        ctx["month_rr_tilt"] = ((cl - lo) - (hi - cl)) / (hi - lo)
            except Exception:
                pass
            
            # ---- Deterministic helpers for wording ----
            try:
                av = ctx.get("anchor_val")
                cp = ctx.get("last_price") or ctx.get("close")
                if av is not None and cp is not None:
                    ctx["close_vs_anchor"] = "below" if av > cp else "above" if av < cp else "equal"

                ts = ctx.get("trend_short")
                tm = ctx.get("trend_mid")
                if ts is not None and tm is not None:
                    ctx["Trend mix (Short vs Mid)"] = "Short-term Trend>Mid-term Trend" if ts > tm else "Short-term Trendt<Mid-term Trend" if ts < tm else "short=mid"
            except Exception:
                pass



            # If your context uses rvol but the model expects 'ARV', alias it here:
            if "rvol" in ctx and "ARV" not in ctx:
                ctx["ARV"] = ctx["rvol"]

            with st.spinner("Analyzing on-screen telemetry…"):
                st.session_state["ai_last_ctx"] = ctx
                st.session_state["ai_last_insights"] = get_ai_insights(ctx)
            st.session_state["ai_open"] = True

        insights = st.session_state.get("ai_last_insights")

        # -------- helpers --------
        def _is_empty_score_context(d: dict | None) -> bool:
            if not d or not isinstance(d, dict):
                return True
            sc = d.get("score_context") or {}
            if not isinstance(sc, dict):
                return True
            summary = (sc.get("summary") or "").strip()
            drivers = sc.get("drivers") or []
            return not summary and not drivers

        # -------- render --------
        if _is_empty_score_context(insights):
            st.warning("No standout AI insights were returned for this view.")
            st.markdown(
                "- The on-screen data may not show strong drivers right now.\n"
                "- You can toggle debug below to see the context the model received."
            )
            if st.checkbox("Show AI debug", value=False, key="dd_ai_debug"):
                st.write("Context snapshot:")
                st.json(st.session_state.get("ai_last_ctx", {}))
                st.write("Insights snapshot:")
                st.json(insights or {})
        else:
            sc = insights.get("score_context", {})  # <-- use insights, not 'data'
            # Title
            st.subheader("Model Score")

            # Summary
            summary = (sc.get("summary") or "").strip()
            if summary:
                st.markdown(f"- **Summary:** {summary}")

            # Drivers
            drivers = sc.get("drivers") or []
            for d in drivers:
                driver_name = (d.get("driver") or "Driver").strip()
                assessment = (d.get("assessment") or "neutral").strip()
                why = (d.get("why") or "").strip()
                st.markdown(f"- **{driver_name}** — {assessment}. {why}")

                nums = [str(n).strip() for n in (d.get("numbers") or []) if str(n).strip()]
                if nums:
                    st.caption("Key numbers: " + "; ".join(nums))


                    
# --- centered Graph 1 row ---
st.markdown('<div id="g1-wide"></div>', unsafe_allow_html=True)
left_g1, mid_g1, right_g1 = st.columns([1,4,1], gap="small")
with mid_g1:
    # ==============================
    # Graph 1 — centered, 90° dates, legend bottom-center, **5-day gutter both ends**
    # ==============================


    #st.markdown('<div style="height: 36px;"></div>', unsafe_allow_html=True)

    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _range_sel  = st.session_state.get("range_sel", "All")

    g1 = load_g1_ticker(FILE_G1, _active_tkr)
    if g1.empty:
        st.info("No data available for the selected ticker/timeframe.")
    else:
        g1 = g1.copy()
        g1["date"] = pd.to_datetime(g1["date"], errors="coerce")
        g1 = g1.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        g1w = apply_window_with_gutter(g1, _range_sel, date_col="date", gutter_days=5)

        _EXCEL_BLUE   = globals().get("EXCEL_BLUE",   "#4472C4")
        _EXCEL_ORANGE = globals().get("EXCEL_ORANGE", "#ED7D31")
        _EXCEL_GRAY   = globals().get("EXCEL_GRAY",   "#A6A6A6")
        _EXCEL_BLACK  = globals().get("EXCEL_BLACK",  "#000000")

        rcParams["font.family"] = ["sans-serif"]
        rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans", "Liberation Sans", "sans-serif"]

        # Graph #1 – bigger and a bit taller
        fig, ax = plt.subplots(figsize=(12, 5))
        fig.subplots_adjust(left=0.035, right=0.995, top=0.86, bottom=0.30)
        fig.set_facecolor("white")
        # Day PR (gray) lines
        ax.plot(g1w["date"], g1w["day_pr_low"],  color=_EXCEL_GRAY,   linewidth=1)
        ax.plot(g1w["date"], g1w["day_pr_high"], color=_EXCEL_GRAY,   linewidth=1)
        # Week PR (orange) lines
        ax.plot(g1w["date"], g1w["week_pr_low"],  color=_EXCEL_ORANGE, linewidth=1)
        ax.plot(g1w["date"], g1w["week_pr_high"], color=_EXCEL_ORANGE, linewidth=1)
        # Month PR (black) lines
        ax.plot(g1w["date"], g1w["month_pr_low"],  color=_EXCEL_BLACK, linewidth=1.2)
        ax.plot(g1w["date"], g1w["month_pr_high"], color=_EXCEL_BLACK, linewidth=1.2)
        # Close (Excel blue) — thinner
        ax.plot(g1w["date"], g1w["close"], color=_EXCEL_BLUE, linewidth=1.5)

        # Biweekly ticks with 90° rotation
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        ax.tick_params(axis="x", labelrotation=90, labelsize=8)

        # >>> FORCE 5-DAY GUTTER ON BOTH ENDS <<<
        pad = pd.Timedelta(days=5)
        dmin = g1w["date"].min()
        dmax = g1w["date"].max()
        ax.set_xlim(dmin - pad, dmax + pad)

        # Title + subtle grid
        ax.set_title(f"{_active_tkr} – Probable Ranges", fontsize=14, pad=4)
        ax.grid(True, axis="both", alpha=0.18)
        ax.tick_params(axis="y", labelsize=10)

        # Legend: bottom-centered
        handles = [
            Line2D([], [], color=_EXCEL_BLUE,   lw=1.5, label="Close"),
            Line2D([], [], color=_EXCEL_GRAY,   lw=2,   label="Day PR"),
            Line2D([], [], color=_EXCEL_ORANGE, lw=2,   label="Week PR"),
            Line2D([], [], color=_EXCEL_BLACK,  lw=2,   label="Month PR"),
        ]
        ax.legend(handles=handles, loc="upper center", ncol=4, frameon=False,
                  bbox_to_anchor=(0.5, -0.23))
        #from __future__ import annotations  # optional; if you use the | type hints above
        # ...
        add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)
        st.pyplot(fig, clear_figure=True, use_container_width=True)

# optional small spacer
st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# -------------------------
# Stat Box - End
# -------------------------

#st.markdown("""
#<style>
#/* Keep 3 charts per row as long as we reasonably can */
#div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
#  flex: 1 1 0;
#  min-width: 300px;            /* was larger; this prevents early wrapping on MBA */
#}
#</style>
#""", unsafe_allow_html=True)

#st.markdown('<div id="data-testid"></div>', unsafe_allow_html=True)

# ==============================
#  Graphs 2–4 - begin
# ==============================
_ticker = _active_tkr

def plot_g2_trend(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    ax.plot(df["date"], df["st"], label="ST Term",  linewidth=1.6, color=EXCEL_BLUE)
    ax.plot(df["date"], df["mt"], label="Mid Term", linewidth=1.6, color=EXCEL_ORANGE)
    ax.plot(df["date"], df["lt"], label="Long Term",linewidth=1.6, color="black")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Trend Lines", fontsize=12, pad=6)
    #ax.set_ylabel("Percent")
    from matplotlib.ticker import PercentFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=3, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g3_anchors(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    ax.plot(df["date"], df["close"],          label="Close",                     linewidth=1.6, color=EXCEL_BLUE)
    ax.plot(df["date"], df["mt_pb_anchor"],   label="Mid Term Probable Anchor",  linewidth=1.6, color=EXCEL_ORANGE)
    ax.plot(df["date"], df["lt_pb_anchor"],   label="Long Term Probable Anchor", linewidth=1.6, color="black")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Probable Anchors", fontsize=12, pad=6)
    #ax.set_ylabel("Price")
  
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=3, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g4_gap(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    ax.plot(df["date"], df["gap_lt"], color=EXCEL_BLUE, linewidth=1.6, label="Gap to LT Anchor")

    # Flat reference lines from the first row (mirrors your Excel behavior)
    avg_val = df["gap_lt_avg"].iloc[0]
    hi_val  = df["gap_lt_hi"].iloc[0]
    lo_val  = df["gap_lt_lo"].iloc[0]
    ax.axhline(y=avg_val, color="black", linewidth=1.6, label="Avg")
    ax.axhline(y=hi_val,  color="red",   linewidth=1.2, label="High")
    ax.axhline(y=lo_val,  color="green", linewidth=1.2, label="Low")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Price to Long Term Probable Anchor", fontsize=12, pad=6)
    #ax.set_ylabel("Gap")
    #from matplotlib.ticker import StrMethodFormatter
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    # y-limits: include bands
    yvals = pd.concat([
        df["gap_lt"], df["gap_lt_avg"], df["gap_lt_hi"], df["gap_lt_lo"]
    ], axis=0)
    y_min, y_max = float(yvals.min()), float(yvals.max())
    if y_min == y_max:
        y_min -= 1.0; y_max += 1.0
    y_pad = 0.08 * (y_max - y_min)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=4, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


# ---- Render: three columns on one row ----
col2, col3, col4 = st.columns(3, gap="small")

with col2:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df2_all = load_g2_ticker(FILE_G2, _active_tkr)
    if df2_all.empty:
        st.info("No trend data.")
    else:
        df2v = _window_by_label_with_gutter(df2_all, _rng, date_col="date")
        st.pyplot(plot_g2_trend(df2v, _active_tkr), use_container_width=True,clear_figure=True)

with col3:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df3_all = load_g3_ticker(FILE_G3, _active_tkr)
    if df3_all.empty:
        st.info("No anchor data.")
    else:
        df3v = _window_by_label_with_gutter(df3_all, _rng, date_col="date")
        st.pyplot(plot_g3_anchors(df3v, _active_tkr), use_container_width=True,clear_figure=True)

with col4:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df4_all = load_g4_ticker(FILE_G4, _active_tkr)
    if df4_all.empty:
        st.info("No gap data.")
    else:
        df4v = _window_by_label_with_gutter(df4_all, _rng, date_col="date")
        st.pyplot(plot_g4_gap(df4v, _active_tkr), use_container_width=True,clear_figure=True)


# ==============================
# Graphs 2–4 - end
# ==============================

# ==============================
# Graphs 5–7 - Begin
# ==============================
# ---- Plotters ----
def plot_g5_zscore(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    ax.plot(df["date"], df["z"], color=EXCEL_BLUE, linewidth=1.6, label="Z-Score")
    ax.axhline(y=df["avg"].iloc[0], color="black", linewidth=1.6, label="Avg")
    ax.axhline(y=df["hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
    ax.axhline(y=df["lo"].iloc[0],  color="green", linewidth=1.2, label="Low")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – 30D Rvol Z-Score", fontsize=12, pad=6)
    #ax.set_ylabel("Z-Score")
    #from matplotlib.ticker import StrMethodFormatter
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=4, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g6_rank(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    ax.plot(df["date"], df["rank"], color=EXCEL_BLUE, linewidth=1.6)
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Z-Score Percentile Rank", fontsize=12, pad=6)
    #ax.set_ylabel("Percentile")
    ax.set_ylim(0, 100)
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    fig.subplots_adjust(bottom=0.22)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g7_rvol(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.plot(df["date"], df["rvol"], color=EXCEL_BLUE, linewidth=1.6, label="Rvol 30d")
    ax.axhline(y=df["rvol_avg"].iloc[0], color="black", linewidth=1.6, label="Avg")
    ax.axhline(y=df["rvol_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
    ax.axhline(y=df["rvol_low"].iloc[0], color="green", linewidth=1.2, label="Low")

    ax.set_title(f"{_active_tkr} – Rvol 30D", fontsize=12, pad=6)
    #ax.set_ylabel("Percent")
    from matplotlib.ticker import PercentFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=4, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


# ---- Render: three columns on one row (5, 6, 7) ----
col5, col6, col7 = st.columns(3, gap="small")

with col5:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df5_all = load_g5_ticker(FILE_G5, _active_tkr)
    if df5_all.empty:
        st.info("No Z-Score data.")
    else:
        df5v = apply_window_with_gutter(df5_all, _rng, date_col="date", gutter_days=5)  
        st.pyplot(plot_g5_zscore(df5v, _active_tkr), use_container_width=True,clear_figure=True)

with col6:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df6_all = load_g6_ticker(FILE_G6, _active_tkr)
    if df6_all.empty:
        st.info("No percentile rank data.")
    else:
        df6v = apply_window_with_gutter(df6_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g6_rank(df6v, _active_tkr), use_container_width=True,clear_figure=True)

with col7:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df7_all = load_g7_ticker(FILE_G7, _active_tkr)
    if df7_all.empty:
        st.info("No rVol data.")
    else:
        df7v = apply_window_with_gutter(df7_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g7_rvol(df7v, _active_tkr), use_container_width=True,clear_figure=True)
# ==============================
# Graphs 5–7  (end)
# ==============================

# ==============================
# ===== Graphs 8, 9 & 10 
# ==============================

# ---- Plotters ----
def plot_g8_sharpe(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
    ax.plot(df["date"], df["sharpe"], color=EXCEL_BLUE, linewidth=1.6, label="Sharpe Ratio")
    ax.axhline(y=df["avg"].iloc[0], color="black", linewidth=1.6, label="Avg")
    ax.axhline(y=df["hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
    ax.axhline(y=df["lo"].iloc[0],  color="green", linewidth=1.2, label="Low")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – 30D Sharpe Ratio", fontsize=12, pad=6)
    #ax.set_ylabel("Sharpe Ratio")
    #from matplotlib.ticker import StrMethodFormatter
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.2f}"))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=4, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g9_sharpe_rank(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
    ax.plot(df["date"], df["rank"], color=EXCEL_BLUE, linewidth=1.6)
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Sharpe Ratio Percentile Rank", fontsize=12, pad=6)
    #ax.set_ylabel("Percentile")
    ax.set_ylim(0, 100)
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    fig.subplots_adjust(bottom=0.22)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g10_ivol_pd(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
    ax.plot(df["date"], df["ivol_pd"], color=EXCEL_BLUE, linewidth=1.6, label="Prem/Disc")
    ax.axhline(y=df["avg"].iloc[0], color="black", linewidth=1.6, label="Avg")
    ax.axhline(y=df["hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
    ax.axhline(y=df["lo"].iloc[0],  color="green", linewidth=1.2, label="Low")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Ivol Prem/Disc", fontsize=12, pad=6)
    #ax.set_ylabel("Percent")
    from matplotlib.ticker import PercentFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.grid(True, linewidth=0.4, alpha=0.4)

    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=4, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


# ---- Render: three columns on one row (8, 9, 10) ----
col8, col9, col10 = st.columns(3, gap="small")

with col8:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df8_all = load_g8_ticker(FILE_G8, _ticker)
    if df8_all.empty:
        st.info("No Sharpe data.")
    else:
        df8v = apply_window_with_gutter(df8_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g8_sharpe(df8v, _ticker), use_container_width=True,clear_figure=True)

with col9:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df9_all = load_g9_ticker(FILE_G9, _ticker)
    if df9_all.empty:
        st.info("No Sharpe rank data.")
    else:
        df9v = apply_window_with_gutter(df9_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g9_sharpe_rank(df9v, _ticker), use_container_width=True,clear_figure=True)

with col10:
    _active_tkr = (st.session_state.get("active_ticker", "SPY") or "SPY").upper()
    _rng    = st.session_state.get("range_sel", "All")
    df10_all = load_g10_ticker(FILE_G10, _ticker)
    if df10_all.empty:
        st.info("No Prem/Disc data.")
    else:
        df10v = apply_window_with_gutter(df10_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g10_ivol_pd(df10v, _ticker), use_container_width=True,clear_figure=True)

# ==============================
# ===== Graphs 8, 9 & 10 
# ==============================

# ==============================
# ===== Graphs 11, 12 
# ==============================

_ticker = _active_tkr
# ---- Plotters ----
def plot_g11_signal(df: pd.DataFrame, ticker: str):
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    # Left axis: Signal Score
    ax.plot(df["date"], df["score"], color=EXCEL_BLUE, linewidth=1.6, label="Markmentum Score")
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    # Right axis: Close
    ax2 = ax.twinx()
    ax2.plot(df["date"], df["close"], color="black", linewidth=1.4, label="Close")

    ax.set_title(f"{_active_tkr} – Model Score", fontsize=12, pad=6)
    ax.grid(True, linewidth=0.4, alpha=0.4)

    # X axis (biweekly Mondays) with 5-day gutter
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
    plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

    pad = pd.Timedelta(days=5)
    ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

    # Combined legend below
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=EXCEL_BLUE, linewidth=1.6, label="Model Score"),
        Line2D([0], [0], color="black",    linewidth=1.4, label="Close"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.22),
              ncol=2, frameon=False, handlelength=2.8, fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig


def plot_g12_scatter(df: pd.DataFrame, ticker: str):
    """
    Dynamic, zero-centered bounds so both points always fit.
    - Both dots Excel blue
    - Dates under each dot
    - No legend
    - Zero lines through center
    """
    fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

    # Ensure order: older first, latest last
    df = df.sort_values("date").reset_index(drop=True)
    older, latest = df.iloc[0], df.iloc[-1]

    # Plot both points
    ax.scatter([older["z"]],  [older["pd"]],  s=70, color=EXCEL_BLUE, zorder=4)
    ax.scatter([latest["z"]], [latest["pd"]], s=90, color=EXCEL_BLUE, zorder=5)
    add_mpl_watermark(ax, text="Markmentum", alpha=0.12, rotation=30)

    ax.set_title(f"{_active_tkr} – Ivol/Rvol % Spreads", fontsize=12, pad=6)
    ax.set_xlabel("Z-Score)")
    ax.set_ylabel("Ivol Prem/Disc)")

    # ----- Dynamic, zero-centered limits -----
    import math
    # X: at least ±5, otherwise expand to cover data with 10% pad and round up to 0.5 steps
    x_abs = max(5.0, abs(float(df["z"].min())), abs(float(df["z"].max())))
    x_abs = x_abs * 1.10
    x_abs = math.ceil(x_abs * 2) / 2.0  # round up to nearest 0.5
    ax.set_xlim(-x_abs, x_abs)

    # Y: at least ±100%, expand if needed with 10% pad and round up to 10%
    y_abs = max(100.0, abs(float(df["pd"].min())), abs(float(df["pd"].max())))
    y_abs = y_abs * 1.10
    y_abs = math.ceil(y_abs / 10.0) * 10.0
    ax.set_ylim(-y_abs, y_abs)

    # Zero lines through center
    ax.axhline(0.0, color="black", linewidth=1.0, zorder=1)
    ax.axvline(0.0, color="black", linewidth=1.0, zorder=1)

    # Percent y-axis
    from matplotlib.ticker import PercentFormatter
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))

    ax.grid(True, linewidth=0.4, alpha=0.4)

    # Dates under each dot
    def under_label(row):
        try:
            dt = pd.to_datetime(row["date"], errors="coerce")
            txt = dt.strftime("%m/%d/%Y") if pd.notna(dt) else str(row["date"])
            ax.annotate(
                txt, (row["z"], row["pd"]),
                xytext=(0, -12), textcoords="offset points",
                ha="center", va="top",
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9),
                zorder=6,
            )
        except Exception:
            pass

    under_label(older)
    under_label(latest)

    # Corner labels (slightly inset)
    def corner_label(text, xy_axes, color):
        ax.text(
            xy_axes[0], xy_axes[1], text,
            transform=ax.transAxes, ha="center", va="center", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, lw=1.2),
            zorder=3,
        )
    corner_label("Mean Reversion", (0.10, 0.90), "green")
    corner_label("Crowded Short",  (0.90, 0.90), "green")
    corner_label("Crowded Long",   (0.10, 0.10), "red")
    corner_label("Mean Reversion", (0.90, 0.10), "red")

    fig.subplots_adjust(bottom=0.18)
    plt.close(fig)  # 🔑 Prevents too many open figures
    return fig

# ---- Render: Notes | Graph 11 | Graph 12 ----
ncol, g11col, g12col = st.columns([1, 1, 1], gap="small")

with ncol:
    st.markdown(
        """
        <div class="calibri-text">
        <b>Note:</b><br>
        • High Line is Average plus 1 standard deviation<br>
        • Low Line is Average less 1 standard deviation<br>
        • Z-Score Rank is trailing 1 year percentile rank<br>
        • Sharpe Ratio Rank is trailing 1 year percentile rank
        </div>
        """,
        unsafe_allow_html=True
    )

with g11col:
    _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
    _rng    = st.session_state.get("range_sel", "All")
    df11_all = load_g11_ticker(FILE_G11, _ticker)
    if df11_all.empty:
        st.info("No Signal Score data.")
    else:
        df11v = apply_window_with_gutter(df11_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g11_signal(df11v, _ticker), use_container_width=True,clear_figure=True)
with g12col:
    _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
    _rng    = st.session_state.get("range_sel", "All")
    df12_all = load_g12_ticker(FILE_G12, _ticker)
    if df12_all.empty:
        st.info("No scatter data.")
    else:
        df12v = apply_window_with_gutter(df12_all, _rng, date_col="date", gutter_days=5)
        st.pyplot(plot_g12_scatter(df12v, _ticker), use_container_width=True,clear_figure=True)

# ==============================
# ===== Graphs 11 & 12 - END 
# ==============================
ticker = _active_tkr
# ==============================
# MASTER TOGGLE: Show/Hide Informational Charts (13–24)
# ==============================
if "show_informational_13_24" not in st.session_state:
    st.session_state.show_informational_13_24 = False

tL, tM, tR = st.columns([1.2, 3, 0.8])
with tM:
    st.toggle(
        "Show informational charts",
        key="show_informational_13_24",     # widget owns state
        help="Turn on to render charts 13–24.",
    )

render_info = st.session_state.show_informational_13_24
ticker = _active_tkr

if render_info:

        # ---- Plotters ----
    def plot_g13_daily_returns(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        # bar colors by sign (green positive, red negative)
        colors = ["green" if v >= 0 else "red" for v in df["daily_return_pct"]]
        ax.bar(df["date"], df["daily_return_pct"], width=1.0, color=colors, linewidth=0)

        # bands
        ax.axhline(y=df["daily_return_avg_pct"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["daily_return_hi_pct"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["daily_return_lo_pct"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Daily Returns", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        # percent formatter on y
        from matplotlib.ticker import PercentFormatter
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))

        # biweekly Monday ticks + 5-day gutter
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        # small legend centered below
        from matplotlib.lines import Line2D
        handles = [
            Line2D([0], [0], color="black", linewidth=1.2, label="Avg"),
            Line2D([0], [0], color="red",   linewidth=1.2, label="High"),
            Line2D([0], [0], color="green", linewidth=1.2, label="Low"),
        ]
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=3, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig


    def plot_g14_daily_range(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        ax.plot(df["date"], df["daily_range"], color=EXCEL_BLUE, linewidth=1.2, label="Range")
        ax.axhline(y=df["daily_range_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["daily_range_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["daily_range_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Daily Range", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig


    def plot_g15_daily_volume(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        ax.plot(df["date"], df["daily_volume"], color=EXCEL_BLUE, linewidth=1.2, label="Volume")
        ax.axhline(y=df["daily_volume_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["daily_volume_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["daily_volume_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Daily Volume", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig

    # ---- Render row horizontally (13, 14, 15) ----
    col13, col14, col15 = st.columns(3, gap="small")

    with col13:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df13_all = load_g13_ticker(FILE_G13, _ticker)
        if df13_all.empty:
            st.info("No Daily Returns data.")
        else:
            df13v = apply_window_with_gutter(df13_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g13_daily_returns(df13v, _ticker), use_container_width=True,clear_figure=True)

    with col14:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df14_all = load_g14_ticker(FILE_G14, _ticker)
        if df14_all.empty:
            st.info("No Daily Range data.")
        else:
            df14v = apply_window_with_gutter(df14_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g14_daily_range(df14v, _ticker), use_container_width=True,clear_figure=True)

    with col15:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df15_all = load_g15_ticker(FILE_G15, _ticker)
        if df15_all.empty:
            st.info("No Daily Volume data.")
        else:
            df15v = apply_window_with_gutter(df15_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g15_daily_volume(df15v, _ticker), use_container_width=True,clear_figure=True)

    # ==============================
    # ===== Graphs 13, 14 & 15 (do not modify) END =====
    # ==============================

    # ==============================
    # ===== Graphs 16, 17 & 18 START =====
    # ==============================
    # ---- Plotters ----
    def plot_g16_weekly_returns(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        # bar colors by sign
        colors = ["green" if v >= 0 else "red" for v in df["weekly_return_pct"]]
        ax.bar(df["date"], df["weekly_return_pct"], width=5.0, color=colors, linewidth=0)

        # bands
        ax.axhline(y=df["weekly_return_avg_pct"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["weekly_return_hi_pct"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["weekly_return_lo_pct"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Weekly Returns", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        from matplotlib.ticker import PercentFormatter
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))

        # show weekly ticks (Mondays) and keep the 5-day gutter helper for consistency
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        from matplotlib.lines import Line2D
        handles = [
            Line2D([0], [0], color="black", linewidth=1.2, label="Avg"),
            Line2D([0], [0], color="red",   linewidth=1.2, label="High"),
            Line2D([0], [0], color="green", linewidth=1.2, label="Low"),
        ]
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.22),
                ncol=3, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig


    def plot_g17_weekly_range(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        ax.plot(df["date"], df["weekly_range"], color=EXCEL_BLUE, linewidth=1.2, label="Range")
        ax.axhline(y=df["weekly_range_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["weekly_range_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["weekly_range_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Weekly Range", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig


    def plot_g18_weekly_volume(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        ax.plot(df["date"], df["weekly_volume"], color=EXCEL_BLUE, linewidth=1.2, label="Volume")
        ax.axhline(y=df["weekly_volume_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["weekly_volume_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["weekly_volume_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Weekly Volume", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig

    # ---- Render row horizontally (16, 17, 18) ----
    col16, col17, col18 = st.columns(3, gap="small")

    with col16:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df16_all = load_g16_ticker(FILE_G16, _ticker)
        if df16_all.empty:
            st.info("No Weekly Returns data.")
        else:
            df16v = apply_window_with_gutter(df16_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g16_weekly_returns(df16v, _ticker), use_container_width=True,clear_figure=True)

    with col17:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df17_all = load_g17_ticker(FILE_G17, _ticker)
        if df17_all.empty:
            st.info("No Weekly Range data.")
        else:
            df17v = apply_window_with_gutter(df17_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g17_weekly_range(df17v, _ticker), use_container_width=True,clear_figure=True)

    with col18:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df18_all = load_g18_ticker(FILE_G18, _ticker)
        if df18_all.empty:
            st.info("No Weekly Volume data.")
        else:
            df18v = apply_window_with_gutter(df18_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g18_weekly_volume(df18v, _ticker), use_container_width=True,clear_figure=True)

    # ==============================
    # ===== Graphs 16, 17 & 18 END 
    # ==============================

    # ==============================
    # ===== Graphs 19, 20 & 21 START
    # ==============================
    # ---- Plotters ----
    def plot_g19_monthly_returns(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
        colors = ["green" if v >= 0 else "red" for v in df["monthly_return"]]
        ax.bar(df["date"], df["monthly_return"], width=20.0, color=colors, linewidth=0)

        ax.axhline(y=df["monthly_return_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["monthly_return_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["monthly_return_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Monthly Returns", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        from matplotlib.ticker import PercentFormatter
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        from matplotlib.lines import Line2D
        handles = [
            Line2D([0], [0], color="black", linewidth=1.2, label="Avg"),
            Line2D([0], [0], color="red",   linewidth=1.2, label="High"),
            Line2D([0], [0], color="green", linewidth=1.2, label="Low"),
        ]
        ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=3, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig


    def plot_g20_monthly_range(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
        ax.plot(df["date"], df["monthly_range"], color=EXCEL_BLUE, linewidth=1.2, label="Range")
        ax.axhline(y=df["monthly_range_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["monthly_range_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["monthly_range_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Monthly Range", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig


    def plot_g21_monthly_volume(df: pd.DataFrame, ticker: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)
        ax.plot(df["date"], df["monthly_volume"], color=EXCEL_BLUE, linewidth=1.2, label="Volume")
        ax.axhline(y=df["monthly_volume_avg"].iloc[0], color="black", linewidth=1.2, label="Avg")
        ax.axhline(y=df["monthly_volume_hi"].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df["monthly_volume_lo"].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(f"{_active_tkr} – Monthly Volume", fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig

    # ---- Render row horizontally (19, 20, 21) ----
    col19, col20, col21 = st.columns(3, gap="small")

    with col19:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df19_all = load_g19_ticker(FILE_G19, _ticker)
        if df19_all.empty:
            st.info("No Monthly Returns data.")
        else:
            df19v = apply_window_with_gutter(df19_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g19_monthly_returns(df19v, _ticker), use_container_width=True,clear_figure=True)

    with col20:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df20_all = load_g20_ticker(FILE_G20, _ticker)
        if df20_all.empty:
            st.info("No Monthly Range data.")
        else:
            df20v = apply_window_with_gutter(df20_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g20_monthly_range(df20v, _ticker), use_container_width=True,clear_figure=True)

    with col21:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df21_all = load_g21_ticker(FILE_G21, _ticker)
        if df21_all.empty:
            st.info("No Monthly Volume data.")
        else:
            df21v = apply_window_with_gutter(df21_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g21_monthly_volume(df21v, _ticker), use_container_width=True,clear_figure=True)

    # ==============================
    # ===== Graphs 19, 20 & 21 (do not modify) END =====
    # ==============================

    # ==============================
    # ===== Graphs 22, 23 & 24 START =====
    # ==============================
    # ---- Plotters ----
    def _plot_trend_generic(df: pd.DataFrame, ticker: str, series_col: str,
                            avg_col: str, hi_col: str, lo_col: str, title: str):
        fig, ax = plt.subplots(figsize=(9.5, 3.9), dpi=150)

        # main series
        ax.plot(df["date"], df[series_col], color=EXCEL_BLUE, linewidth=1.6, label=title.split(" – ")[-1])

        # horizontal bands
        ax.axhline(y=df[avg_col].iloc[0], color="gray",  linewidth=1.2, label="Avg")
        ax.axhline(y=df[hi_col].iloc[0],  color="red",   linewidth=1.2, label="High")
        ax.axhline(y=df[lo_col].iloc[0],  color="green", linewidth=1.2, label="Low")

        ax.set_title(title, fontsize=12, pad=6)
        ax.grid(True, linewidth=0.4, alpha=0.4)

        # Percent axis (values are in %)
        from matplotlib.ticker import PercentFormatter
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))

        # Month ticks + a small gutter
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%y"))
        plt.setp(ax.get_xticklabels(), rotation=90, ha="center", fontsize=7)

        pad = pd.Timedelta(days=5)
        ax.set_xlim(df["date"].min() - pad, df["date"].max() + pad)

        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22),
                  ncol=4, frameon=False, handlelength=2.8, fontsize=9)
        fig.subplots_adjust(bottom=0.30)
        plt.close(fig)  # 🔑 Prevents too many open figures
        return fig

    def plot_g22_st(df: pd.DataFrame, ticker: str):
        return _plot_trend_generic(
            df=df, ticker=ticker,
            series_col="st_trend", avg_col="st_avg", hi_col="st_hi", lo_col="st_lo",
            title=f"{_active_tkr} – Short Term Trend Line"
        )

    def plot_g23_mt(df: pd.DataFrame, ticker: str):
        return _plot_trend_generic(
            df=df, ticker=ticker,
            series_col="mt_trend", avg_col="mt_avg", hi_col="mt_hi", lo_col="mt_lo",
            title=f"{_active_tkr} – Mid Term Trend Line"
        )

    def plot_g24_lt(df: pd.DataFrame, ticker: str):
        return _plot_trend_generic(
            df=df, ticker=ticker,
            series_col="lt_trend", avg_col="lt_avg", hi_col="lt_hi", lo_col="lt_lo",
            title=f"{_active_tkr} – Long Term Trend Line"
        )

    # ---- Render row horizontally (22, 23, 24) ----
    col22, col23, col24 = st.columns(3, gap="small")

    with col22:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df22_all = load_g22_ticker(FILE_G22, _ticker)
        if df22_all.empty:
            st.info("No Short-Term Trend data.")
        else:
            df22v = apply_window_with_gutter(df22_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g22_st(df22v, _ticker), use_container_width=True,clear_figure=True)

    with col23:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df23_all = load_g23_ticker(FILE_G23, _ticker)
        if df23_all.empty:
            st.info("No Mid-Term Trend data.")
        else:
            df23v = apply_window_with_gutter(df23_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g23_mt(df23v, _ticker), use_container_width=True,clear_figure=True)
    with col24:
        _ticker = st.session_state.get("active_ticker", DEFAULT_TICKER)
        _rng    = st.session_state.get("range_sel", "All")
        df24_all = load_g24_ticker(FILE_G24, _ticker)
        if df24_all.empty:
            st.info("No Long-Term Trend data.")
        else:
            df24v = apply_window_with_gutter(df24_all, _rng, date_col="date", gutter_days=5)
            st.pyplot(plot_g24_lt(df24v, _ticker), use_container_width=True,clear_figure=True)
    # ==============================
    # ===== Graphs 22, 23 & 24 END 
    # ==============================

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