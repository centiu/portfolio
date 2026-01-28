import sys
from pathlib import Path

# Ensure repo root is on Python path so "common_ui.py" can be imported from pages/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import plotly.express as px
import yfinance as yf

from common_ui import inject_css, style_plotly

st.set_page_config(page_title="Markets & Energy", layout="wide")

THEME = st.session_state.get("theme", "light")
inject_css(THEME)

st.title("📈 Markets & energy context")
st.caption("Live market proxies (Yahoo Finance). Designed as context — not a trading system.")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This page provides a lightweight “context layer” for industrial / decarbonisation discussions.
    It compares relative performance of broad risk assets and common hedges, using ETF proxies.
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
    lookback = st.selectbox("Lookback", ["6mo", "1y", "2y", "5y"], index=1)
    normalize = st.toggle("Normalize to 100", value=True)
    show_returns = st.toggle("Show snapshot returns", value=True)

SERIES = {
    "S&P 500 (SPY)": "SPY",
    "Nasdaq 100 (QQQ)": "QQQ",
    "Gold (GLD)": "GLD",
    "China exposure (FXI)": "FXI",
}

@st.cache_data(ttl=3600)
def load_prices(period: str) -> pd.DataFrame:
    tickers = list(SERIES.values())
    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)

    # yfinance returns MultiIndex cols when multiple tickers
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"].copy()
    else:
        prices = data[["Close"]].copy()

    prices = prices.rename(columns={v: k for k, v in SERIES.items()})
    prices = prices.dropna(how="all")
    return prices

prices = load_prices(lookback)

if prices.empty:
    st.error("No price data returned. Check connectivity or tickers.")
    st.stop()

# ----------------------------
# Main chart
# ----------------------------
if normalize:
    norm = (prices / prices.iloc[0]) * 100.0
    plot_df = norm.reset_index().melt("Date", var_name="Series", value_name="Index (Start=100)")
    fig = px.line(plot_df, x="Date", y="Index (Start=100)", color="Series", title="Relative performance (normalized)")
    fig = style_plotly(fig, THEME, title="Relative performance (normalized)", subtitle=f"Lookback: {lookback}")
else:
    plot_df = prices.reset_index().melt("Date", var_name="Series", value_name="Price")
    fig = px.line(plot_df, x="Date", y="Price", color="Series", title="Price series")
    fig = style_plotly(fig, THEME, title="Price series", subtitle=f"Lookback: {lookback}")

st.write("")
st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Snapshot returns (credible, decision-ish)
# ----------------------------
if show_returns:
    st.write("")
    st.subheader("Snapshot returns")

    last = prices.dropna().iloc[-1]
    first = prices.dropna().iloc[0]

    returns = ((last / first) - 1.0) * 100.0
    out = returns.sort_values(ascending=False).to_frame(name=f"Return over {lookback} (%)")
    out.index.name = "Series"
    out = out.reset_index()

    # Display as a simple bar (not a table) for cleaner visual
    fig_ret = px.bar(out, x=f"Return over {lookback} (%)", y="Series", orientation="h", title="Period return by series")
    fig_ret.update_traces(marker_line_width=0, opacity=0.95)
    fig_ret.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>")
    fig_ret = style_plotly(fig_ret, THEME, title="Period return by series", subtitle="Simple snapshot of relative movement")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.plotly_chart(fig_ret, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with st.expander("Notes / assumptions"):
    st.markdown("""
- Uses ETF proxies: SPY (S&P 500), QQQ (Nasdaq 100), GLD (Gold), FXI (China large-cap exposure).
- Normalised view answers: “what moved more” over the selected window.
- This is framing context for industrial / energy-transition discussions, not a trading recommendation.
""")
