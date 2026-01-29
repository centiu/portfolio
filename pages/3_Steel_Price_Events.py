import sys
from pathlib import Path

# --- ensure repo root on path (so common_ui imports work) ---
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

st.set_page_config(page_title="Steel price vs events", layout="wide")

THEME = st.session_state.get("theme", "light")
inject_css(THEME)

# ----------------------------
# Framing
# ----------------------------
st.title("🧭 Steel price trends vs major events")
st.caption("Steel price proxy (CME HRC futures via Yahoo Finance) with an event timeline overlay.")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This page overlays <b>notable macro / policy / geopolitical events</b> on a steel price time series.
    It is not meant to “prove” causality. The goal is to support calm, defensible discussion:
    <ul>
      <li>What regime was the market in before/after an event?</li>
      <li>Did volatility increase? Did the trend break?</li>
      <li>Which events align with structural changes vs short-lived noise?</li>
    </ul>
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

    steel_ticker = st.text_input(
        "Steel price ticker (Yahoo Finance)",
        value="HRC=F",  # U.S. Midwest Domestic Hot-Rolled Coil Steel futures (proxy)
        help="Default is HRC=F (CME HRC futures proxy on Yahoo Finance).",
    )

    lookback = st.selectbox("Lookback", ["6mo", "1y", "2y", "5y", "10y", "max"], index=3)
    normalize = st.toggle("Normalize to 100", value=False)
    show_events = st.toggle("Show event markers", value=True)
    show_event_labels = st.toggle("Show event labels", value=True)

# ----------------------------
# Data loading
# ----------------------------
@st.cache_data(ttl=3600)
def load_series(ticker: str, period: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    # Keep a simple 2-col frame
    out = df[["Close"]].copy()
    out = out.rename(columns={"Close": "Price"})
    out = out.dropna()
    out.index.name = "Date"
    return out

series = load_series(steel_ticker, lookback)

if series.empty:
    st.error("No data returned for this ticker / lookback. Try a different lookback or ticker.")
    st.stop()

# Optional normalization (useful for long history)
plot_series = series.copy()
if normalize:
    plot_series["Price"] = (plot_series["Price"] / plot_series["Price"].iloc[0]) * 100.0

# ----------------------------
# Default event set (editable)
# ----------------------------
# NOTE: These are "anchor" events. You can refine wording/dates in the editor below.
default_events = pd.DataFrame(
    [
        {
            "Date": "2018-03-08",
            "Event": "US Section 232 steel tariffs announced (Trump)",
            "Category": "Policy / Tariffs",
            "Why it matters": "Trade policy shock; changes import economics and market expectations.",
        },
        {
            "Date": "2021-03-11",
            "Event": "China 14th Five-Year Plan endorsed (2021–2025)",
            "Category": "China / Policy",
            "Why it matters": "Signals priorities around industry, energy, and long-run growth structure.",
        },
        {
            "Date": "2024-04-13",
            "Event": "Iran launches direct attack on Israel (missiles/drones)",
            "Category": "Geopolitics",
            "Why it matters": "Risk premium + energy/logistics uncertainty; global inflation sensitivity.",
        },
        {
            "Date": "2025-06-13",
            "Event": "Israel strikes Iran; escalation risk (broader conflict concerns)",
            "Category": "Geopolitics",
            "Why it matters": "Supply risk + energy shock risk; sentiment and freight impacts.",
        },
        {
            "Date": "2026-01-07",
            "Event": "Venezuela: Maduro ousted / detained (reported early Jan 2026)",
            "Category": "Geopolitics",
            "Why it matters": "Oil/political risk narrative shift (mostly context, not direct steel driver).",
        },
    ]
)

# Persist editable events in session
if "steel_events" not in st.session_state:
    st.session_state.steel_events = default_events

st.write("")
st.subheader("Event timeline (editable)")

events = st.data_editor(
    st.session_state.steel_events,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Event": st.column_config.TextColumn(width="large"),
        "Category": st.column_config.SelectboxColumn(
            options=["Policy / Tariffs", "China / Policy", "Geopolitics", "Demand / Macro", "Supply / Energy", "Other"],
            width="medium",
        ),
        "Why it matters": st.column_config.TextColumn(width="large"),
    },
)

# Save edited version back
st.session_state.steel_events = events

# Clean event dates
events_clean = events.copy()
events_clean["Date"] = pd.to_datetime(events_clean["Date"], errors="coerce")
events_clean = events_clean.dropna(subset=["Date"]).sort_values("Date")

# ----------------------------
# Plot
# ----------------------------
st.write("")
st.subheader("Steel price trend")

plot_df = plot_series.reset_index()

y_title = "Index (Start=100)" if normalize else "Price (USD)"
title = f"Steel price proxy: {steel_ticker}"
subtitle = f"Lookback: {lookback} | Markers: {'on' if show_events else 'off'}"

fig = px.line(plot_df, x="Date", y="Price", title=title)
fig.update_traces(hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.2f}</b><extra></extra>")
fig = style_plotly(fig, THEME, title=title, subtitle=subtitle)
fig.update_yaxes(title=y_title)
fig.update_xaxes(title="")

# Add event lines + annotations
if show_events and not events_clean.empty:
    # Only draw events within plot range
    min_d = plot_df["Date"].min()
    max_d = plot_df["Date"].max()

    for _, r in events_clean.iterrows():
        d = r["Date"]
        if d < min_d or d > max_d:
            continue

        label = r["Event"] if show_event_labels else ""
        fig.add_vline(
            x=d,
            line_width=1,
            line_dash="dot",
            opacity=0.6,
            annotation_text=label,
            annotation_position="top left",
            annotation_font_size=11,
        )

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Simple “before/after” view for selected event (optional but very useful)
# ----------------------------
st.write("")
st.subheader("Quick before/after check (optional)")

if not events_clean.empty:
    event_options = events_clean["Event"].tolist()
    selected_event = st.selectbox("Pick an event to inspect", event_options, index=0)
    window_days = st.slider("Window (days before/after)", 7, 180, 60)

    d0 = events_clean.loc[events_clean["Event"] == selected_event, "Date"].iloc[0]
    start = d0 - pd.Timedelta(days=window_days)
    end = d0 + pd.Timedelta(days=window_days)

    window = plot_series.loc[(plot_series.index >= start) & (plot_series.index <= end)].copy()

    if window.empty:
        st.info("No price data in the selected window.")
    else:
        wdf = window.reset_index()
        fig_w = px.line(wdf, x="Date", y="Price", title=f"Window around event: {selected_event}")
        fig_w.update_traces(hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.2f}</b><extra></extra>")
        fig_w = style_plotly(
            fig_w,
            THEME,
            title=f"Window around event: {selected_event}",
            subtitle=f"{window_days} days before/after | Event date: {d0.date()}",
        )
        fig_w.add_vline(x=d0, line_width=2, line_dash="solid", opacity=0.7)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.plotly_chart(fig_w, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Interpretation / caveats
# ----------------------------
st.write("")
st.divider()

with st.expander("ℹ️ How to interpret this page"):
    st.markdown("""
### What this page is doing
This is a **time alignment tool**: it helps you visually inspect steel price movement around events that
may matter for trade, energy, supply chains, or demand sentiment.

It’s useful because it forces discipline:
- **What was the trend before the event?**
- **Did volatility jump?**
- **Did the level or slope shift in a sustained way?**

### What it is *not* doing
This does **not** prove that an event caused a price move.
Steel prices are influenced by many overlapping drivers: capacity, demand cycles, inventories,
freight, policy, and energy.

This page is meant to support discussion like:
> “Around this event, the market moved into a different regime — here’s what changed and why it might matter.”

### Why this belongs in an industrial portfolio
Industrial roles often require combining:
- messy real-world data
- imperfect proxies
- domain framing
- clear limits on interpretation

That is exactly the skill this page demonstrates.
""")
