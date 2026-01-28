import sys
from pathlib import Path

# Ensure repo root is on Python path so "common_ui.py" can be imported from pages/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import plotly.express as px

from common_ui import inject_css, style_plotly

# Optional: fail gracefully if dependency missing (useful on Cloud)
try:
    import yfinance as yf
except ModuleNotFoundError:
    st.error("Missing dependency: yfinance. Add it to requirements.txt and redeploy.")
    st.stop()

st.set_page_config(page_title="Markets & Energy", layout="wide")

THEME = st.session_state.get("theme", "light")
inject_css(THEME)

st.title("📈 Markets & energy context")
st.caption("Live market proxies (Yahoo Finance). Designed as context — not a trading system.")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This page provides a lightweight context layer for industrial / decarbonisation discussions.
    It compares relative performance of broad risk assets and hedges using ETF proxies.
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

    data = yf.download(
        tickers,
        period=period,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True
    )

    # MultiIndex columns when multiple tickers
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"].copy()
    else:
        # single ticker case
        close = data[["Close"]].copy()
        close.columns = [tickers[0]]

    close = close.rename(columns={v: k for k, v in SERIES.items()})

    # Keep rows where at least one series exists
    close = close.dropna(how="all")

    return close

prices = load_prices(lookback)

if prices.empty:
    st.error("No price data returned (or all values missing). Try a different lookback or refresh.")
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
# Snapshot returns (robust)
# ----------------------------
def compute_period_return(series: pd.Series) -> float | None:
    """Return % change from first valid to last valid for one series."""
    s = series.dropna()
    if s.empty:
        return None
    first = s.iloc[0]
    last = s.iloc[-1]
    if first == 0 or pd.isna(first) or pd.isna(last):
        return None
    return (last / first - 1.0) * 100.0

if show_returns:
    st.write("")
    st.subheader("Snapshot returns")

    returns = []
    for col in prices.columns:
        r = compute_period_return(prices[col])
        returns.append({"Series": col, f"Return over {lookback} (%)": r})

    out = pd.DataFrame(returns)

    # Drop missing series (e.g., ticker failed)
    out = out.dropna(subset=[f"Return over {lookback} (%)"])

    if out.empty:
        st.warning("No valid returns could be computed (data missing for all series). Try refresh or another lookback.")
    else:
        out = out.sort_values(f"Return over {lookback} (%)", ascending=False)

        fig_ret = px.bar(
            out,
            x=f"Return over {lookback} (%)",
            y="Series",
            orientation="h",
            title="Period return by series",
        )
        fig_ret.update_traces(marker_line_width=0, opacity=0.95)
        fig_ret.update_traces(hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>")
        fig_ret = style_plotly(
            fig_ret,
            THEME,
            title="Period return by series",
            subtitle="Computed from first/last available value per series (handles missing tickers)",
        )

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(fig_ret, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

with st.expander("Notes / assumptions"):
    st.markdown("""
- Uses ETF proxies: SPY (S&P 500), QQQ (Nasdaq 100), GLD (Gold), FXI (China large-cap exposure).
- Normalised view answers: “what moved more” over the selected window.
- Snapshot returns are computed per-series from the first/last valid observation (robust to partial missing data).
- This is framing context for industrial / energy-transition discussions, not a trading recommendation.
""")
