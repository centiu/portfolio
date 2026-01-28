import sys
from pathlib import Path

# Ensure repo root is on Python path so "common_ui.py" can be imported from pages/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

st.write("")

# ----------------------------
# KPIs
# ----------------------------

pig_col = "Pig iron produced (ttpa)"
dri_col = "DRI produced (ttpa)"

total_pig = df[pig_col].sum(skipna=True) if pig_col in df.columns else 0.0
total_dri = df[dri_col].sum(skipna=True) if dri_col in df.columns else 0.0
total_primary = total_pig + total_dri
dri_share = (total_dri / total_primary * 100) if total_primary > 0 else None
countries_any = int(df["Country"].nunique()) if "Country" in df.columns else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("BF–BOF (Pig iron)", f"{total_pig:,.0f} Mtpa")
c2.metric("DRI–EAF (DRI)", f"{total_dri:,.0f} Mtpa")
c3.metric("DRI share of primary routes", f"{dri_share:.1f}%" if dri_share is not None else "—")
c4.metric("Countries (any production)", countries_any)

st.write("")

# ----------------------------
# Top countries chart
# ----------------------------

top_n = st.slider("Top countries", 5, 25, 15)

plot_cols = ["Country"] + [c for c in ROUTE_COLS.keys() if c in df.columns]
top = (
    df[plot_cols]
    .fillna(0)
    .assign(Total=lambda x: sum(x[c] for c in ROUTE_COLS.keys() if c in x.columns))
    .sort_values("Total", ascending=False)
    .head(top_n)
)

top_long = top.melt(
    id_vars=["Country"],
    value_vars=[c for c in ROUTE_COLS.keys() if c in top.columns],
    var_name="Source column",
    value_name="Mtpa"
)
top_long["Route"] = top_long["Source column"].map(ROUTE_COLS)

fig_bar = px.bar(
    top_long,
    x="Mtpa",
    y="Country",
    color="Route",
    orientation="h",
    title="Primary steelmaking routes (Top countries)",
)
fig_bar.update_traces(marker_line_width=0, opacity=0.95)
fig_bar.update_layout(barmode="stack")
fig_bar.update_traces(hovertemplate="<b>%{y}</b><br>%{x:,.1f} Mtpa<extra></extra>")
fig_bar = style_plotly(
    fig_bar,
    THEME,
    title="Primary steelmaking routes (Top countries)",
    subtitle="BF–BOF via pig iron vs DRI–EAF via direct reduced iron (Mtpa)",
)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig_bar, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ----------------------------
# Global share donut
# ----------------------------

share_df = pd.DataFrame({
    "Route": ["BF–BOF (Pig iron)", "DRI–EAF"],
    "Production (Mtpa)": [total_pig, total_dri],
})

fig_pie = px.pie(
    share_df,
    names="Route",
    values="Production (Mtpa)",
    hole=0.42,
    title="Global primary steelmaking route split",
)

if THEME == "dark":
    fig_pie.update_traces(textfont_color="rgba(255,255,255,0.92)")
else:
    fig_pie.update_traces(textfont_color="rgba(0,0,0,0.85)")

fig_pie.update_traces(
    textposition="inside",
    textinfo="percent",
    hovertemplate="<b>%{label}</b><br>%{value:,.0f} Mtpa<br>%{percent}<extra></extra>",
)

fig_pie = style_plotly(
    fig_pie,
    THEME,
    title="Global primary steelmaking route split",
    subtitle="Share of BF–BOF vs DRI–EAF within primary routes",
)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig_pie, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ----------------------------
# Country route mix table
# ----------------------------

st.subheader("Country route mix")

show_mix = st.checkbox("Show DRI share by country (table)", value=True)
if show_mix and pig_col in df.columns and dri_col in df.columns:
    mix = df[["Country", pig_col, dri_col]].copy().fillna(0)
    mix["Total (Mtpa)"] = mix[pig_col] + mix[dri_col]
    mix["DRI share (%)"] = mix.apply(
        lambda r: (r[dri_col] / r["Total (Mtpa)"] * 100) if r["Total (Mtpa)"] > 0 else pd.NA,
        axis=1
    )
    mix = mix.sort_values("Total (Mtpa)", ascending=False)

    display_mix = mix.rename(columns={
        pig_col: "BF–BOF (Pig iron) Mtpa",
        dri_col: "DRI–EAF (DRI) Mtpa",
    })

    styled_mix = style_table(display_mix, THEME)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.dataframe(styled_mix, use_container_width=True, height=460)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ----------------------------
# Transparency / QA sections
# ----------------------------

with st.expander("🔍 Data quality notes"):
    st.markdown(f"""
- Rows loaded (raw): **{len(raw_df):,}**
- Rows after cleaning/filtering: **{len(df):,}**
- Aggregate rows removed: **Global** (if present)
- Numeric coercion: non-numeric values → **NaN**
- Units: values displayed as **Mtpa** (converted from ttpa ÷ {UNIT_DIVISOR:g})
""")

with st.expander("📊 View cleaned data"):
    st.dataframe(df, use_container_width=True)
