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


def add_event_legend(fig, theme: str):
    """
    Add dummy traces so event line types appear in the legend.
    (Plotly shapes/vlines don't automatically create legend entries.)
    """
    # Pick subtle legend colors that work in both themes without forcing a palette
    if theme == "dark":
        manual_color = "rgba(220,220,220,0.70)"
        fed_color = "rgba(220,220,220,0.35)"
    else:
        manual_color = "rgba(60,60,60,0.55)"
        fed_color = "rgba(60,60,60,0.28)"

    # Dummy trace for manual events
    fig.add_trace(
        dict(
            type="scatter",
            x=[None],
            y=[None],
            mode="lines",
            line=dict(color=manual_color, dash="dot", width=2),
            name="Manual events (policy / geopolitics)",
            showlegend=True,
            hoverinfo="skip",
        )
    )

    # Dummy trace for Fed changes
    fig.add_trace(
        dict(
            type="scatter",
            x=[None],
            y=[None],
            mode="lines",
            line=dict(color=fed_color, dash="dot", width=2),
            name="Fed rate changes (target range upper)",
            showlegend=True,
            hoverinfo="skip",
        )
    )


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

    # enforce a single numeric series
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
# Fed rate-change overlay (robust)
# DFEDTARU = Federal Funds Target Range - Upper Limit
# ----------------------------
@st.cache_data(ttl=3600)
def load_fed_target_range_changes(min_year: int) -> tuple[pd.DataFrame, str | None]:
    """
    Return (events_df, warning_message).
    If fetch/parsing fails, returns empty df and a warning message.
    """
    urls = [
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU",
        "https://fred.stlouisfed.org/graph/fredgraph.csv?bgcolor=%23e1e9f0&chart_type=line&drp=0&fo=open%20sans&graph_bgcolor=%23ffffff&height=450&mode=fred&recession_bars=on&txtcolor=%23444444&ts=12&tts=12&width=1168&nt=0&thu=0&trc=0&show_legend=yes&show_axis_titles=yes&show_tooltip=yes&id=DFEDTARU&scale=left&cosd=2008-12-16&coed=9999-12-31&line_color=%234572a7&link_values=false&line_style=solid&mark_type=none&mw=3&lw=2&ost=-99999&oet=99999&mma=0&fml=a&fq=Daily&fam=avg&fgst=lin&fgsnd=2020-02-01&line_index=1&transformation=lin&nd=2008-12-16",
    ]

    last_error = None
    fred = None

    for url in urls:
        try:
            tmp = pd.read_csv(url)
            cols = [c.strip() for c in tmp.columns.astype(str)]
            tmp.columns = cols

            if "DATE" in tmp.columns and "DFEDTARU" in tmp.columns:
                fred = tmp.rename(columns={"DATE": "Date", "DFEDTARU": "Upper"})
                break
            if "observation_date" in tmp.columns and "DFEDTARU" in tmp.columns:
                fred = tmp.rename(columns={"observation_date": "Date", "DFEDTARU": "Upper"})
                break

            last_error = f"Unexpected columns from FRED: {tmp.columns.tolist()}"
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            continue

    if fred is None:
        empty = pd.DataFrame(columns=["Date", "Event", "Category", "Why it matters"])
        return empty, f"Fed overlay unavailable (FRED fetch/parse failed). {last_error or ''}".strip()

    fred["Date"] = pd.to_datetime(fred["Date"], errors="coerce")
    fred["Upper"] = pd.to_numeric(fred["Upper"], errors="coerce")
    fred = fred.dropna(subset=["Date", "Upper"]).sort_values("Date")
    fred = fred[fred["Date"].dt.year >= min_year].copy()

    if fred.empty:
        empty = pd.DataFrame(columns=["Date", "Event", "Category", "Why it matters"])
        return empty, None

    fred["Prev"] = fred["Upper"].shift(1)
    changes = fred[fred["Upper"] != fred["Prev"]].copy()

    def _fmt_change(row):
        prev = row["Prev"]
        cur = row["Upper"]
        if pd.isna(prev):
            return f"Fed target range upper limit set to {cur:.2f}%"
        direction = "↑" if cur > prev else "↓"
        return f"Fed target range upper limit {direction} to {cur:.2f}%"

    changes["Event"] = changes.apply(_fmt_change, axis=1)
    changes["Category"] = "Monetary policy (Fed)"
    changes["Why it matters"] = "Policy rates affect financing conditions, demand sensitivity, and risk appetite."
    return changes[["Date", "Event", "Category", "Why it matters"]], None


fed_events, fed_warning = (pd.DataFrame(columns=["Date", "Event", "Category", "Why it matters"]), None)
if show_fed_events:
    fed_events, fed_warning = load_fed_target_range_changes(fed_min_year)

# ----------------------------
# Default manual events (editable)
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
            "Why it matters": "Demand shock + supply disruption; a major regime shift for industry and logistics.",
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
            "Why it matters": "Energy and commodity shock; impacts freight, power, and risk premia.",
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
            options=["Policy / Tariffs", "China / Policy", "Geopolitics", "Demand / Macro", "Supply / Energy", "Other"],
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

# Add legend entries for event-line types (important)
add_event_legend(fig, THEME)

# Event markers (Plotly-safe: vline + separate annotations)
min_d = plot_df["Date"].min()
max_d = plot_df["Date"].max()

if not plot_events.empty:
    for _, r in plot_events.iterrows():
        d = r["Date"]
        if d < min_d or d > max_d:
            continue

        is_fed = (r.get("Category", "") == "Monetary policy (Fed)")

        if is_fed and not show_fed_events:
            continue
        if (not is_fed) and not show_manual_events:
            continue

        x_val = pd.to_datetime(d).to_pydatetime()

        # Make Fed lines visually lighter than manual events
        opacity = 0.35 if is_fed else 0.60

        fig.add_vline(x=x_val, line_width=1, line_dash="dot", opacity=opacity)

        label_on = (show_fed_labels if is_fed else show_manual_labels)
        if label_on:
            fig.add_annotation(
                x=x_val,
                y=1.02 if not is_fed else 1.06,
                xref="x",
                yref="paper",
                text=r["Event"],
                showarrow=False,
                align="left",
                xanchor="left",
                font=dict(size=11),
                opacity=0.85 if not is_fed else 0.70,
            )

st.markdown('<div class="card">', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if fed_warning:
    st.info(fed_warning)

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
It often changes the “background regime” that industrial demand sits inside.

### What it is *not* doing
This does **not** prove causality. Steel prices reflect overlapping drivers:
demand cycles, capacity, inventories, freight, policy, and energy.

The intent is disciplined discussion, not “proof”.
""")
