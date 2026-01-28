import streamlit as st

def inject_css(theme: str):
    if theme == "dark":
        bg = "#0b0b0f"
        panel = "rgba(255,255,255,0.06)"
        border = "rgba(255,255,255,0.10)"
        text = "rgba(255,255,255,0.92)"
        mutetext = "rgba(255,255,255,0.68)"
        shadow = "0 1px 2px rgba(0,0,0,0.35)"
        metric_bg = "rgba(255,255,255,0.06)"
        exp_bg = "rgba(255,255,255,0.05)"
    else:
        bg = "#ffffff"
        panel = "rgba(245,245,247,0.75)"
        border = "rgba(0,0,0,0.06)"
        text = "rgba(0,0,0,0.92)"
        mutetext = "rgba(0,0,0,0.65)"
        shadow = "0 1px 2px rgba(0,0,0,0.06)"
        metric_bg = "rgba(245,245,247,0.85)"
        exp_bg = "rgba(245,245,247,0.55)"

    st.markdown(
        f"""
        <style>
        .stApp {{
          background: {bg};
          color: {text};
        }}
        .block-container {{
          padding-top: 1.2rem;
          padding-bottom: 2rem;
          max-width: 1200px;
        }}
        h1, h2, h3 {{ letter-spacing: -0.02em; }}
        .muted {{ color: {mutetext}; }}

        .card {{
          background: {panel};
          border: 1px solid {border};
          border-radius: 16px;
          padding: 16px 18px;
          box-shadow: {shadow};
        }}

        [data-testid="stMetric"] {{
          background: {metric_bg};
          border: 1px solid {border};
          border-radius: 16px;
          padding: 14px 14px;
          box-shadow: {shadow};
        }}

        details {{
          border-radius: 14px;
          border: 1px solid {border};
          background: {exp_bg};
          padding: 6px 10px;
        }}

        hr {{
          border: none;
          border-top: 1px solid {border};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def style_plotly(fig, theme: str, title: str | None = None, subtitle: str | None = None):
    if theme == "dark":
        font_color = "rgba(255,255,255,0.90)"
        sub_color = "rgba(255,255,255,0.65)"
        grid_color = "rgba(255,255,255,0.10)"
        axis_line = "rgba(255,255,255,0.18)"
        hover_bg = "rgba(20,20,26,0.95)"
        hover_border = "rgba(255,255,255,0.12)"
    else:
        font_color = "rgba(0,0,0,0.90)"
        sub_color = "rgba(0,0,0,0.60)"
        grid_color = "rgba(0,0,0,0.06)"
        axis_line = "rgba(0,0,0,0.12)"
        hover_bg = "rgba(255,255,255,0.95)"
        hover_border = "rgba(0,0,0,0.10)"

    fig.update_layout(
        template="plotly_white",
        title=dict(text=title or fig.layout.title.text, x=0.0, xanchor="left"),
        font=dict(
            family="Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial",
            size=13,
            color=font_color,
        ),
        # Key fix: legend below the plot, subtitle above plot, no overlap.
        margin=dict(l=10, r=10, t=90, b=70),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title_text="",
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="left",
            x=0,
            font=dict(color=font_color),
        ),
        hoverlabel=dict(
            bgcolor=hover_bg,
            bordercolor=hover_border,
            font=dict(color=font_color),
        ),
    )

    fig.update_xaxes(showgrid=True, gridcolor=grid_color, zeroline=False, showline=False, linecolor=axis_line)
    fig.update_yaxes(showgrid=False, zeroline=False, showline=False, linecolor=axis_line)

    if subtitle:
        fig.update_layout(
            annotations=[
                dict(
                    text=subtitle,
                    x=0, y=1.07,
                    xref="paper", yref="paper",
                    showarrow=False,
                    align="left",
                    font=dict(size=12, color=sub_color),
                )
            ]
        )

    return fig
