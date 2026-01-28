import pandas as pd
import streamlit as st
import plotly.express as px
import yfinance as yf
from common_ui import inject_css, style_plotly

st.set_page_config(page_title="Markets & Energy", layout="wide")
THEME = st.session_state.get("theme", "light")
inject_css(THEME)

st.title("📈 Markets & energy transition context")
st.caption("Market proxies via Yahoo Finance + oil production via EIA (weekly).")

st.markdown("""
<div class="card">
  <div class="muted">
    This dashboard is a compact “macro context” view: relative performance of major risk / hedge proxies and
    a basic supply-side signal (oil production). It’s designed as context — not as a trading system.
  </div>
</div>
""", unsafe_allow_html=True)

st.write("")

with st.sidebar:
    st.subheader("Market proxies")
    # Proxies (editable)
    default = {
        "S&P 500 (SPY)": "SPY",
        "Nasdaq 100 (QQQ)": "QQQ",
        "Gold (GLD)": "GLD",
        "China exposure (FXI)": "FXI",
    }
    lookback = st.selectbox("Lookback", ["6mo", "1y", "2y", "5y"], index=1)
    normalize = st.toggle("Normalize to 100", value=True)
    show_corr = st.toggle("Show rolling correlation (SPY vs GLD)", value=False)
    window = st.slider("Rolling window (days)", 20, 120, 60)

def fetch_prices(tickers: list[str], period: str) -> pd.DataFrame:
    # yfinance supports batched downloads
    data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"].copy()
    else:
        prices = data.rename(columns={"Close": tickers[0]})[tickers[0]].to_frame()
    prices = prices.dropna(how="all")
    return prices

@st.cache_data(ttl=3600)
def load_markets(period: str, mapping: dict) -> pd.DataFrame:
    tickers = list(mapping.values())
    prices = fetch_prices(tickers, period)
    prices = prices.rename(columns={v: k for k, v in mapping.items()})
    return prices

prices = load_markets(lookback, default)

if normalize:
    norm = (prices / prices.iloc[0]) * 100.0
    plot_df = norm.reset_index().melt("Date", var_name="Series", value_name="Index (Start=100)")
    fig = px.line(plot_df, x="Date", y="Index (Start=100)", color="Series", title="Relative performance (normalized)")
    fig = style_plotly(fig, THEME, title="Relative performance (normalized)", subtitle=f"Lookback: {lookback}")
else:
    plot_df = prices.reset_index().melt("Date", var_name="Series", value_name="Price")
    fig = px.line(plot_df, x="Date", y="Price", color="Series", title="Price series")
    fig = style_plotly(fig, THEME, title="Price series", subtitle=f"Lookback: {lookback}")

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# Optional rolling correlation (simple, credible)
if show_corr and ("S&P 500 (SPY)" in prices.columns) and ("Gold (GLD)" in prices.columns):
    corr = prices["S&P 500 (SPY)"].pct_change().rolling(window).corr(prices["Gold (GLD)"].pct_change())
    corr_df = corr.dropna().reset_index().rename(columns={0: "Correlation"})
    corr_df["Correlation"] = corr_df.iloc[:, 1]  # safe rename if needed

    fig_corr = px.line(corr_df, x="Date", y=corr_df.columns[1], title="Rolling correlation: SPY vs GLD")
    fig_corr = style_plotly(fig_corr, THEME, title="Rolling correlation: SPY vs GLD", subtitle=f"Window: {window} trading days")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.plotly_chart(fig_corr, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ----------------------------
# Oil production (EIA weekly)
# ----------------------------
st.subheader("Oil production (EIA weekly)")

st.markdown("""
<div class="card">
  <div class="muted">
    EIA publishes U.S. crude oil field production as a weekly series (thousand bbl/day). This is not “daily production”,
    but it gives a stable supply-side trend indicator. Source: EIA Petroleum & Other Liquids.
  </div>
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def load_eia_weekly_production() -> pd.DataFrame:
    # EIA DNAV weekly page: Weekly U.S. Field Production of Crude Oil (Thousand Barrels per Day)
    # We parse the HTML table; EIA also offers API options via its open data program.
    url = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s=WCRFPUS2"
    tables = pd.read_html(url)
    # The first table is usually the data grid
    t = tables[0].copy()
    # EIA table is "Year-Month" + repeating "End Date / Value" columns
    # We'll reshape it into a simple long time series.
    t = t.rename(columns={t.columns[0]: "YearMonth"})
    date_cols = [c for c in t.columns if "End Date" in str(c)]
    val_cols = [c for c in t.columns if "Value" in str(c)]

    rows = []
    for _, r in t.iterrows():
        for dc, vc in zip(date_cols, val_cols):
            end_date = r.get(dc)
            val = r.get(vc)
            if pd.isna(end_date) or pd.isna(val):
                continue
            rows.append((pd.to_datetime(end_date), float(str(val).replace(",", ""))))

    out = pd.DataFrame(rows, columns=["Date", "Thousand bbl/day"]).sort_values("Date")
    out = out.drop_duplicates("Date")
    out["Million bbl/day"] = out["Thousand bbl/day"] / 1000.0
    return out

oil = load_eia_weekly_production()

fig_oil = px.line(oil, x="Date", y="Million bbl/day", title="U.S. crude oil field production (weekly)")
fig_oil = style_plotly(fig_oil, THEME, title="U.S. crude oil field production (weekly)", subtitle="EIA series WCRFPUS2 (field production)")

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig_oil, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

with st.expander("Data notes / assumptions"):
    st.markdown("""
- Market series are ETF proxies (SPY, QQQ, GLD, FXI) via Yahoo Finance (`yfinance`). :contentReference[oaicite:3]{index=3}
- Oil production is from EIA’s weekly field production series page (WCRFPUS2). :contentReference[oaicite:4]{index=4}
- “Daily oil production” is typically not published as an official daily measurement series; weekly is the standard public cadence.
""")
