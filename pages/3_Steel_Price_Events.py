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
st.caption("Steel price proxy (via Yahoo Finance) with an editable event timeline + optional Fed rate-change overlay.")

st.markdown(
    """
<div class="card">
  <div class="muted">
    This page aligns <b>context events</b> with a steel price trend.
    It is not designed to “prove” causality — the intent is to support calm discussion about
    regime shifts, volatility changes, and timing.
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    st.subheader("Settings")

    steel_ticker = st.text_input(
        "Steel price ticker (Yahoo Finance)",
        value="HRC=F",
        help="Default: HRC=F (CME HRC futures proxy on Yahoo Finance).",
    )

    lookback = st.selectbox("Lookback", ["6mo", "1y", "2y", "5y", "10y", "max"], index=3)
    normalize = st.toggle("Normalize to 100", value=False)

    st.divider()
    st.caption("Event overlays")
    show_manual_events = st.toggle("Show manual event markers", value=True)
    show_manual_labels = st.toggle("Label manual events", value=True)

    show_fed_events = st.toggle("Overlay Fed rate changes", value=True)
    show_fed_labels = st.toggle("Label Fed changes (can clutter)", value=False)

    fed_min_year = st.slider("Fed overlay: start year", 2008, 2026, 2018)

# ----------------------------
# Price series loading
# ----------------------------
@st.cache_data(ttl=3600)
def load_series(ticker: str, period: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()

    if "Close" in df.columns:
        out = df[["Close"]].copy()
        out.columns = ["Price"]
    else:
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
# Fed rate-change overlay (authoritative series from FRED)
# DFEDTARU = Federal Funds Target Range - Upper Limit (daily)
# ----------------------------
@st.cache_data(ttl=3600)
def load_fed_target_range_changes(min_year: int) -> pd.DataFrame:
    """
    Pull FRED DFEDTARU (upper limit of target range) and return rows where the value changes.
    Uses FRED CSV download endpoint (no extra deps).
    """
    # This endpoint returns a CSV with columns: DATE, DFEDTARU
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU"
    fred = pd.read_csv(url)

    fred["DATE"] = pd.to_datetime(fred["DATE"], errors="coerce")
    fred = fred.dropna(subset=["DATE"])
    fred = fred.rename(columns={"DATE": "Date", "DFEDTARU": "Upper"})
    fred["Upper"] = pd.to_numeric(fred["Upper"], errors="coerce")
    fred = fred.dropna(subset=["Upper"]).sort_values("Date")

    fred = fred[fred["Date"].dt.year >= min_year].copy()
    if fred.empty:
        return pd.DataFrame(columns=["Date", "Event", "Category", "Why it matters"])

    # Detect changes
    fred["Prev"] = fred["Upper"].shift(1)
    changes = fred[fred["Upper"] != fred["Prev"]].copy()

    # Format events
    def _fmt_change(row):
        prev = row["Prev"]
        cur = row["Upper"]
        if pd.isna(prev):
            return f"Fed target range upper limit set to {cur:.2f}%"
        direction = "↑" if cur > prev else "↓"
        return f"Fed target range upper limit {direction} to {cur:.2f}%"

    changes["Event"] = changes.apply(_fmt_change, axis=1)
    changes["Category"] = "Monetary policy (Fed)"
    changes["Why it matters"] = "Policy rate changes affect financing conditions, demand, and risk appetite."

    return changes[["Date", "Event", "Category", "Why it matters"]]

fed_events = load_fed_target_range_changes(fed_min_year) if show_fed_events else pd.DataFrame(
    columns=["Date", "Event", "Category", "Why it matters"]
)

# ----------------------------
# Default manual events (editable)
# Keep these as “headline anchors”; user can edit dates/text.
# ----------------------------
default_events = pd.DataFrame(
    [
        {
            "Date": pd.to_datetime("2018-03-08").date(),
            "Event": "US Section 232 steel tariffs announced (Trump)",
            "Category": "Policy / Tariffs",
            "Why it matters": "Trade policy shock; can change import economics and expectations.",
        },
        {
            "Date": pd.to_datetime("2020-03-11").date(),
            "Event": "COVID-19 declared a pandemic (WHO)",
            "Category": "Demand / Macro",
            "Why it matters": "Demand shock + supply disruption; major regime shift for industry and logistics.",
        },
        {
            "Date": pd.to_datetime("2021-03-11").date(),
            "Event": "China 14th Five-Year Plan endorsed (2021–2025)",
            "Category": "China / Policy",
            "Why it matters": "Signals priorities around industry, energy, and longer-run structure.",
        },
        {
            "Date": pd.to_datetime("2022-02-24").date(),
            "Event": "Russia invades Ukraine",
            "Category": "Geopolitics",
            "Why it matters": "Energy and commodity shock; changes freight, power, and risk premia.",
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
st.subheader("Manual event timeline (editable)")

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
            options=[
                "Policy / Tariffs",
                "China / Policy",
                "Geopolitics",
                "Demand / Macro",
                "Supply / Energy",
                "Other",
            ],
            width="medium",
        ),
        "Why it matters": st.column_config.TextColumn("Why it matters", width="large"),
    },
)
st.session_state.steel_events = events

manual_events = events.copy()
manual_events["Date"] = pd.to_datetime(manual_events["Date"], errors="coerce")
manual_events = manual_events.dropna(subset=["Date"]).sort_values("Date")

# Combine for plotting (manual + fed)
plot_events = pd.concat([manual_events, fed_events], ignore_index=True)
plot_events["Date"] = pd.to_datetime(plot_events["Date"], errors="coerce")
plot_events = plot_events.dropna(subset=["Date"]).sort_values("Date")

# ----------------------------
# Plot
# ----------------------------
st.write("")
st.subheader("Steel price trend")

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
subtitle = f"Lookback: {lookback} | Manual events: {'on' if show_manual_events else 'off'} | Fed overlay: {'on' if show_fed_events else 'off'}"

fig = px.line(plot_df, x="Date", y="Price", title=title)
fig.update_traces(hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.2f}</b><extra></extra>")
fig = style_plotly(fig, THEME, title=title, subtitle=subtitle)
fig.update_yaxes(title=y_title)
fig.update_xaxes(title="")

# Event markers (Plotly-safe: vline + separate annotations)
min_d = plot_df["Date"].min()
max_d = plot_df["Date"].max()

if not plot_events.empty:
    for _, r in plot_events.iterrows():
        d = r["Date"]
        if d < min_d or d > max_d:
            continue

        # Respect toggles
        is_fed = (r.get("Category", "") == "Monetary policy (Fed)")
        if is_fed and not show_fed_events:
            continue
        if (not is_fed) and not show_manual_events:
            continue

        x_val = pd.to_datetime(d).to_pydatetime()
        fig.add_vline(x=x_val, line_width=1, line_dash="dot", opacity=0.55)

        label_on = (show_fed_labels if is_fed else show_manual_labels)
        if label_on:
            fig.add_annotation(
                x=x_val,
                y=1.02 if not is_fed else 1.06,   # small separation to reduce collisions
                xref="x",
                yref="paper",
                text=r["Event"],
                showarrow=False,
                align="left",
                xanchor="left",
                font=dict(size=11),
                opacity=0.85,
            )

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# Quick before/after window
# ----------------------------
st.write("")
st.subheader("Quick before/after check (optional)")

if not manual_events.empty:
    event_options = manual_events["Event"].tolist()
    selected_event = st.selectbox("Pick a manual event to inspect", event_options, index=0)
    window_days = st.slider("Window (days before/after)", 7, 180, 60)

    d0 = manual_events.loc[manual_events["Event"] == selected_event, "Date"].iloc[0]
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
        fig_w.add_vline(x=pd.to_datetime(d0).to_pydatetime(), line_width=2, line_dash="solid", opacity=0.7)

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
This is a **time alignment tool**: it helps you inspect whether steel prices change *around* events that may matter for
trade policy, energy risk, supply chains, or demand sentiment.

### Why add Fed rate changes?
Fed policy shifts financing conditions and demand sensitivity across the economy.
It often changes the “background regime” that industrial demand sits inside. The overlay is derived from the Fed target
range series published on FRED (upper limit). :contentReference[oaicite:1]{index=1}

### What it is *not* doing
This does **not** prove causality. Steel prices reflect overlapping drivers:
demand cycles, capacity, inventories, freight, policy, and energy.

The intent is disciplined discussion, not “proof”.
""")
