import sys
from pathlib import Path
import streamlit as st

# Ensure repo root is on Python path so "common_ui.py" can be imported reliably
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common_ui import inject_css

st.set_page_config(page_title="Portfolio | Industrial Analytics", layout="wide")

# Persist theme across pages
if "theme" not in st.session_state:
    st.session_state.theme = "light"

with st.sidebar:
    st.header("Settings")
    dark_mode = st.toggle("Dark mode", value=(st.session_state.theme == "dark"))
    st.session_state.theme = "dark" if dark_mode else "light"

THEME = st.session_state.theme
inject_css(THEME)

st.title("Industrial analytics portfolio")
st.caption(
    "Public dashboards focused on operational reality: messy data, clear assumptions, and decision-oriented framing."
)

st.markdown(
    """
<div class="card">
  <div class="muted">
    This portfolio is built to reflect real industrial analytics work — not demo visuals.
    The emphasis is on <b>domain framing</b>, <b>data handling</b>, and <b>explainable outputs</b>
    that could be used in steel, mining, or energy-transition conversations.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")

# First row (2 cards)
c1, c2 = st.columns(2)

with c1:
    st.markdown(
        """
<div class="card">
  <h3>🌍 Steelmaking routes</h3>
  <div class="muted">
    Global route mix (BF–BOF vs DRI–EAF) using Global Energy Monitor data.
    Focus: route structure, interpretation, and transition readiness signals.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Steel_Routes.py", label="Open: Steelmaking routes →")

with c2:
    st.markdown(
        """
<div class="card">
  <h3>⚙️ Cost & pressure signals on steel systems</h3>
  <div class="muted">
    Proxies for system pressure: steel output signal, iron ore input signal,
    oil (energy/logistics), and a China-linked demand context proxy.
    Focus: framing conditions, not forecasting.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Markets_&_Energy.py", label="Open: Cost & pressure signals →")

st.write("")

# Second row (single wide card)
st.markdown(
    """
<div class="card">
  <h3>🧭 Steel price vs major events</h3>
  <div class="muted">
    Steel price trend (proxy) with an editable timeline of policy and geopolitical events.
    Focus: “what changed around this date?” framing — without claiming causality.
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.page_link("pages/3_Steel_Price_Events.py", label="Open: Steel price vs events →")

st.write("")

with st.expander("What to expect (and what not to expect)"):
    st.markdown(
        """
- These dashboards aim to be **useful and explainable**, not exhaustive.
- Assumptions are stated clearly; I avoid overconfident conclusions.
- Public sources are used where possible; transformations are reproducible.
- The goal is to demonstrate *how I think* about industrial data and decisions.
"""
    )
