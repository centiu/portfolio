import streamlit as st
from common_ui import inject_css

st.set_page_config(page_title="Portfolio | Industrial Analytics", layout="wide")

# Persist theme across pages
if "theme" not in st.session_state:
    st.session_state.theme = "light"

with st.sidebar:
    st.header("Settings")
    dark = st.toggle("Dark mode", value=(st.session_state.theme == "dark"))
    st.session_state.theme = "dark" if dark else "light"

inject_css(st.session_state.theme)

st.title("Industrial analytics portfolio")
st.caption("Public dashboards focused on real-world data, and decision-oriented insights.")

st.markdown("""
<div class="card">
  <div class="muted">
    This portfolio is built to reflect real industrial analytics work: imperfect data, clear assumptions,
    and outputs that a plant, operations, or decarbonisation team could actually use.
  </div>
</div>
""", unsafe_allow_html=True)

st.write("")

c1, c2 = st.columns(2)

with c1:
    st.markdown("""
<div class="card">
  <h3>🌍 Steelmaking routes</h3>
  <div class="muted">
    Global production by route (BF–BOF vs DRI–EAF) using Global Energy Monitor data.
    Focus on route mix, interpretation, and transition signals.
  </div>
</div>
""", unsafe_allow_html=True)
    st.page_link("pages/1_Steel_Routes.py", label="Open: Steelmaking routes →")

with c2:
    st.markdown("""
<div class="card">
  <h3>📈 Markets & energy transition</h3>
  <div class="muted">
    Live market proxies (S&P 500, Nasdaq, Gold, China exposure) alongside oil production trend (EIA).
    Focus on context, correlation regimes, and “what changed” framing.
  </div>
</div>
""", unsafe_allow_html=True)
    st.page_link("pages/2_Markets_&_Energy.py", label="Open: Markets & energy →")

st.write("")
with st.expander("About the approach"):
    st.markdown("""
- Minimal hype; explicit assumptions and validation checks.
- Prefer stable public sources and reproducible transformations.
- Visuals aim for clarity (not maximal interactivity).
""")

