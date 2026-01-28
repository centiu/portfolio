import pandas as pd
import streamlit as st
import plotly.express as px
import pathlib
from io import StringIO

from common_ui import inject_css, style_plotly, style_table

st.set_page_config(page_title="Steelmaking routes", layout="wide")

THEME = st.session_state.get("theme", "light")
inject_css(THEME)

# ----------------------------
# Data loading / cleaning
# ----------------------------

ROUTE_COLS = {
    "Pig iron produced (ttpa)": "BF–BOF (Pig iron)",
    "DRI produced (ttpa)": "DRI–EAF",
}
UNIT_DIVISOR = 1000.0  # ttpa -> Mtpa


@st.cache_data
def load_data():
    path = pathlib.Path("./steel_routes.csv")

    raw_bytes = path.read_bytes()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = raw_bytes.decode("cp1252", errors="replace")

    cleaned_lines = [line.rstrip().rstrip(";") for line in raw_text.splitlines()]
    cleaned_text = "\n".join(cleaned_lines)

    raw_df = pd.read_csv(StringIO(cleaned_text), sep=",", engine="python")
    df = raw_df.copy()

    df = df.replace("unknown", pd.NA)

    expected = ["Country", *ROUTE_COLS.keys()]
    present = [c for c in expected if c in df.columns]
    df = df[present]

    for col in ROUTE_COLS.keys():
        if col not in df.columns:
            continue
        df[col] = (
            df[col]
            .astype(str)
            .str.strip()
            .str.replace(".", "", regex=False)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Country" in df.columns and "Global" in df["Country"].astype(str).values:
        df = df[df["Country"] != "Global"]

    numeric_cols = [c for c in ROUTE_COLS.keys() if c in df.columns]
    df[numeric_cols] = df[numeric_cols] / UNIT_DIVISOR

    return raw_df, df


raw_df, df = load_data()

# ----------------------------
# UI Header / framing
# ----------------------------

st.title("🌍 Global primary steelmaking routes")
st.caption("Source: Global Energy Monitor – Global Iron & Steel Tracker")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This dashboard compares <b>primary steelmaking routes</b>:
    <ul>
      <li><b>BF–BOF</b> via pig iron production (blast furnace → basic oxygen furnace)</li>
      <li><b>DRI–EAF</b> via direct reduced iron production (DRI → electric arc furnace)</li>
    </ul>
    The intent is not to forecast output, but to highlight <b>structural differences</b> relevant to
    energy use, emissions intensity, and decarbonisation pathways.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.wr
