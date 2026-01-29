# ----------------------------
# Plot (robust)
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
subtitle = f"Lookback: {lookback} | Markers: {'on' if show_events else 'off'}"

fig = px.line(plot_df, x="Date", y="Price", title=title)
fig.update_traces(hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.2f}</b><extra></extra>")
fig = style_plotly(fig, THEME, title=title, subtitle=subtitle)
fig.update_yaxes(title=y_title)
fig.update_xaxes(title="")

# Event markers (safe: vline + separate annotation)
if show_events and not events_clean.empty:
    min_d = plot_df["Date"].min()
    max_d = plot_df["Date"].max()

    for _, r in events_clean.iterrows():
        d = r["Date"]
        if d < min_d or d > max_d:
            continue

        x_val = pd.to_datetime(d).to_pydatetime()

        fig.add_vline(
            x=x_val,
            line_width=1,
            line_dash="dot",
            opacity=0.6,
        )

        if show_event_labels:
            fig.add_annotation(
                x=x_val,
                y=1.02,
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
