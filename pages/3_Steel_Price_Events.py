import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import plotly.express as px

from common_ui import inject_css, style_plotly

try:
    import yfinance as yf
except ModuleNotFoundError:
    st.error("Missing dependency: yfinance. Add it to requirements.txt and redeploy.")
    st.stop()

st.set_page_config(page_title="Steel price vs events", layout="wide")

THEME = st.session_state.get("theme", "light")
inject_css(THEME)

st.title("🧭 Steel price trends vs major events")
st.caption("Steel price proxy (via Yahoo Finance) with an editable event timeline overlay.")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This page overlays <b>macro / policy / geopolitical events</b> onto a steel price trend.
    It is not designed to “prove” causality — the goal is to support calm, defensible discussion about
    timing, regime shifts, and volatility changes.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Settings")
    steel_ticker = st.text_input("Steel price ticker (Yahoo Finance)", value="HRC=F")
    lookback = st.selectbox("Lookback", ["6mo", "1y", "2y", "5y", "10y", "max"], index=3)
    normalize = st.toggle("Normalize to 100", value=False)
    show_events = st.toggle("Show event markers", value=True)
    show_event_labels = st.toggle("Show event labels", value=True)

@st.cache_data(ttl=3600)
def load_series(ticker: str, period: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()

    # Some tickers come back with odd columns; enforce a single numeric series
    if "Close" in df.columns:
        out = df[["Close"]].copy()
        out.columns = ["Price"]
    else:
        # fallback: pick the last column that looks numeric
        out = df.select_dtypes(include="number").copy()
        if out.empty:
            return pd.DataFrame()
        out = out.iloc[:, [-1]].copy()
        out.columns = ["Price"]

    out = out.dropna()
    out.index = pd.to_datetime(out.index, errors="coerce")
    out = out.dropna()
    out.index.name = "Date"

    return out

series = load_series(steel_ticker, lookback)

if series.empty:
    st.error("No usable data returned. Try a different ticker or lookback.")
    st.stop()

plot_series = series.copy()
if normalize:
    plot_series["Price"] = (plot_series["Price"] / plot_series["Price"].iloc[0]) * 100.0

# ----------------------------
# Default events (Date must be date-like for data_editor)
# ----------------------------
default_events = pd.DataFrame(
    [
        {
            "Date": pd.to_datetime("2018-03-08").date(),
            "Event": "US Section 232 steel tariffs announced (Trump)",
            "Category": "Policy / Tariffs",
            "Why it matters": "Trade policy shock; changes import economics and expectations.",
        },
        {
            "Date": pd.to_datetime("2021-03-11").date(),
            "Event": "China 14th Five-Year Plan endorsed (2021–2025)",
            "Category": "China / Policy",
            "Why it matters": "Signals priorities around industry, energy, and long-run structure.",
        },
        {
            "Date": pd.to_datetime("2024-04-13").date(),
            "Event": "Iran direct attack on Israel (missiles/drones)",
            "Category": "Geopolitics",
            "Why it matters": "Energy and risk premium context; freight/logistics uncertainty.",
        },
    ]
)

if "steel_events" not in st.session_state:
    st.session_state.steel_events = default_events

st.write("")
st.subheader("Event timeline (editable)")

events_df = st.session_state.steel_events.copy()
events_df["Date"] = pd.to_datetime(events_df["Date"], errors="coerce").dt.date

events = st.data_editor(
    events_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
        "Event": st.column_config.TextColumn("Event", width="large"),
        "Category": st.column_config.SelectboxColumn(
            "Category",
            options=["Policy / Tariffs", "China / Policy", "Geopolitics", "Demand / Macro", "Supply / Energy", "Other"],
            width="medium",
        ),
        "Why it matters": st.column_config.TextColumn("Why it matters", width="large"),
    },
)
st.session_state.steel_events = events

events_clean = events.copy()
events_clean["Date"] = pd.to_datetime(events_clean["Date"], errors="coerce")
events_clean = events_clean.dropna(subset=["Date"]).sort_values("Date")

# ----------------------------
# Plot (robust)
# ----------------------------
st.write("")
st.subheader("Steel price trend")

# Make index + columns explicit and Plotly-safe
plot_series = plot_series.copy()
plot_series.index = pd.to_datetime(plot_series.index, errors="coerce")
plot_series = plot_series.dropna()

plot_df = plot_series.reset_index()
plot_df = plot_df.rename(columns={plot_df.columns[0]: "Date"})
plot_df["Date"] = pd.to_datetime(plot_df["Date"], errors="coerce")
plot_df["Price"] = pd.to_numeric(plot_df["Price"], errors="coerce")
plot_df = plot_df.dropna(subset=["Date", "Price"]).sort_values("Date")

if plot_df.empty:
    st.error("Price series became empty after cleaning. Try another ticker or lookback.")
    st.stop()

y_title = "Index (Start=100)" if normalize else "Price"
title = f"Steel price proxy: {steel_ticker}"
subtitle = f"Lookback: {lookback} | Markers: {'on' if show_events else 'off'}"

fig = px.line(plot_df, x="Date", y="Price", title=title)
fig.update_traces(hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.2f}</b><extra></extra>")
fig = style_plotly(fig, THEME, title=title, subtitle=subtitle)
fig.update_yaxes(title=y_title)
fig.update_xaxes(title="")

if show_events and not events_clean.empty:
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
# Before/after window
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
        wdf = window.reset_index().rename(columns={window.reset_index().columns[0]: "Date"})
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

st.write("")
st.divider()

with st.expander("ℹ️ How to interpret this page"):
    st.markdown("""
### What this page is doing
This is a **time alignment tool**: it helps you inspect whether steel prices change *around* events that may matter
for trade policy, energy risk, supply chains, or demand sentiment.

### What it is *not* doing
This does **not** prove causality. Steel prices reflect many overlapping drivers (demand cycles, capacity, inventories,
freight, policy, and energy).

### Why it’s meaningful
Industrial roles often require combining imperfect proxies and real-world context, while being explicit about limits.
That is the skill this page demonstrates.
""")
