import sys
from pathlib import Path

# --- ensure repo root on path ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import plotly.express as px

from common_ui import inject_css, style_plotly

# yfinance dependency
try:
    import yfinance as yf
except ModuleNotFoundError:
    st.error("Missing dependency: yfinance. Add it to requirements.txt and redeploy.")
    st.stop()

st.set_page_config(page_title="Steel system cost & pressure context", layout="wide")

THEME = st.session_state.get("theme", "light")
inject_css(THEME)

# ----------------------------
# Page framing
# ----------------------------

st.title("⚙️ Cost & pressure signals on steel systems")
st.caption("Physical inputs, outputs, and macro context using public market proxies.")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This page provides a <b>context layer</b> for steel and mining discussions.
    It focuses on <b>inputs, outputs, and system pressures</b> rather than market timing.
    All series are proxies — the intent is framing, not forecasting.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Controls
# ----------------------------

with st.sidebar:
    st.subheader("Settings")
    lookback = st.selectbox("Lookback window", ["6mo", "1y", "2y", "5y"], index=1)
    normalize = st.toggle("Normalize to 100", value=True)
    show_snapshot = st.toggle("Show snapshot comparison", value=True)

# ----------------------------
# Series definition (industrial logic)
# ----------------------------

SERIES = {
    "Steel price (HRC proxy)": "SLX",          # Steel producers ETF (output signal proxy)
    "Iron ore price (proxy)": "BHP",            # Mining-heavy proxy; imperfect but defensible
    "Oil price (Brent proxy)": "BZ=F",           # Brent crude futures
    "China-linked demand proxy": "FXI",          # Large-cap China equity exposure
}

SERIES_NOTES = {
    "Steel price (HRC proxy)": "Equity proxy for steel price and margin conditions",
    "Iron ore price (proxy)": "Mining-linked equity proxy (not a spot index)",
    "Oil price (Brent proxy)": "Energy and logistics cost pressure",
    "China-linked demand proxy": "Market sentiment toward China-related demand",
}

# ----------------------------
# Data loading
# ----------------------------

@st.cache_data(ttl=3600)
def load_prices(period: str) -> pd.DataFrame:
    tickers = list(SERIES.values())
    data = yf.download(
        tickers,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        close = data[["Close"]].copy()
        close.columns = [tickers[0]]

    close = close.rename(columns={v: k for k, v in SERIES.items()})
    close = close.dropna(how="all")

    return close

prices = load_prices(lookback)

if prices.empty:
    st.error("No data returned. Try another lookback window.")
    st.stop()

# ----------------------------
# Main chart
# ----------------------------

if normalize:
    norm = (prices / prices.iloc[0]) * 100.0
    plot_df = norm.reset_index().melt(
        "Date", var_name="Series", value_name="Index (Start = 100)"
    )
    fig = px.line(
        plot_df,
        x="Date",
        y="Index (Start = 100)",
        color="Series",
        title="Relative movement of cost & pressure signals",
    )
    fig = style_plotly(
        fig,
        THEME,
        title="Relative movement of cost & pressure signals",
        subtitle=f"Normalized comparison | Lookback: {lookback}",
    )
else:
    plot_df = prices.reset_index().melt(
        "Date", var_name="Series", value_name="Price"
    )
    fig = px.line(
        plot_df,
        x="Date",
        y="Price",
        color="Series",
        title="Price series (raw scale)",
    )
    fig = style_plotly(
        fig,
        THEME,
        title="Price series (raw scale)",
        subtitle=f"Unnormalized | Lookback: {lookback}",
    )

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------
# Snapshot comparison (robust)
# ----------------------------

def period_return(series: pd.Series) -> float | None:
    s = series.dropna()
    if s.empty:
        return None
    first, last = s.iloc[0], s.iloc[-1]
    if first == 0 or pd.isna(first) or pd.isna(last):
        return None
    return (last / first - 1.0) * 100.0

if show_snapshot:
    st.write("")
    st.subheader("Snapshot comparison")

    rows = []
    for col in prices.columns:
        r = period_return(prices[col])
        rows.append({
            "Signal": col,
            f"Change over {lookback} (%)": r,
            "Interpretation": SERIES_NOTES.get(col, ""),
        })

    snap = pd.DataFrame(rows).dropna(subset=[f"Change over {lookback} (%)"])
    snap = snap.sort_values(f"Change over {lookback} (%)", ascending=False)

    fig_snap = px.bar(
        snap,
        x=f"Change over {lookback} (%)",
        y="Signal",
        orientation="h",
        title="Relative change over selected window",
    )
    fig_snap.update_traces(marker_line_width=0, opacity=0.95)
    fig_snap.update_traces(
        hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>"
    )

    fig_snap = style_plotly(
        fig_snap,
        THEME,
        title="Relative change over selected window",
        subtitle="Simple first-to-last comparison (not a forecast)",
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.plotly_chart(fig_snap, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------
# Explanation / interpretation layer
# ----------------------------

st.write("")
st.divider()

with st.expander("ℹ️ How to interpret this page"):
    st.markdown("""
### Why these signals?
This page focuses on **pressures acting on steel systems**, not financial performance in isolation.

- **Steel price (output signal)** reflects demand strength and margin conditions.
- **Iron ore price (input signal)** affects integrated BF–BOF cost structures.
- **Oil price** influences mining, logistics, and energy-intensive operations.
- **China-linked equity exposure** provides context on demand sentiment and trade sensitivity.

Together, these give a rough picture of whether conditions are becoming
more or less favourable for steelmaking and mining operations.

---

### What does “normalized” mean here?
Normalizing all series to a common starting value (100) removes price-scale differences
and highlights **relative movement** instead of absolute prices.

This helps answer:
> “Which pressures are increasing faster, and which are easing?”

---

### What this analysis does *not* do
- It does **not** forecast prices or demand  
- It does **not** estimate margins or emissions  
- It does **not** replace site-level cost models  

It is intended as a **discussion aid** — a way to frame conversations about
operating pressure, investment timing, and transition readiness.
""")

