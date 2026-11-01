"""Plotly figure builders with one shared dark theme. No Streamlit imports here."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import config

TEAL, CYAN, AMBER, ROSE = "#2DD4BF", "#38BDF8", "#F2B04C", "#FB7185"
INK, MUTED, GRID = "#E8EEF7", "#8393AB", "rgba(131,147,171,0.14)"
PALETTE = [TEAL, CYAN, AMBER, "#A78BFA", ROSE, "#86EFAC", "#F9A8D4", "#FDBA74"]
FONT = "IBM Plex Sans, Segoe UI, system-ui, sans-serif"
MAX_PLOT_POINTS = 60_000


def _theme(fig: go.Figure, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=INK, size=12), margin=dict(l=8, r=8, t=28, b=8),
        hoverlabel=dict(bgcolor="#0B1424", bordercolor="rgba(45,212,191,0.5)", font=dict(family=FONT, color=INK)),
        showlegend=legend, legend=dict(orientation="h", y=1.08, x=0, font=dict(color=MUTED)),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED))
    return fig


def empty_figure(message: str, height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(color=MUTED, size=14))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _theme(fig, height, legend=False)


# ----------------------------------------------------------------------------- trend
def trend_chart(trend: pd.DataFrame, agg: str, y_title: str, show_ma: bool = False, window: int = 7) -> go.Figure:
    fig = go.Figure()
    custom = np.stack([trend["observations"], trend["regions"]], axis=-1)
    fmt = {"daily": "%d %b %Y", "monthly": "%b %Y", "annual": "%Y"}[agg.lower()]
    common = dict(x=trend["period"], customdata=custom)
    if agg.lower() == "daily" and len(trend) > 2500:
        fig.add_trace(go.Scattergl(**common, y=trend["rainfall"], mode="lines", name="Rainfall",
                                   line=dict(color=TEAL, width=1.2),
                                   hovertemplate="%{x|" + fmt + "}<br>%{y:,.1f} mm<br>%{customdata[0]} obs<extra></extra>"))
    elif agg.lower() == "annual":
        fig.add_trace(go.Bar(**common, y=trend["rainfall"], name="Rainfall", marker_color=TEAL, marker_line_width=0,
                             hovertemplate="%{x|" + fmt + "}<br>%{y:,.1f} mm<br>%{customdata[0]} obs<extra></extra>"))
    else:
        fig.add_trace(go.Scatter(**common, y=trend["rainfall"], mode="lines", name="Rainfall",
                                 line=dict(color=TEAL, width=1.6, shape="spline" if agg.lower() == "monthly" else "linear", smoothing=0.5),
                                 fill="tozeroy", fillcolor="rgba(45,212,191,0.08)",
                                 hovertemplate="%{x|" + fmt + "}<br>%{y:,.1f} mm<br>%{customdata[0]} obs<extra></extra>"))
    if show_ma and "moving_average" in trend:
        fig.add_trace(go.Scatter(x=trend["period"], y=trend["moving_average"], mode="lines",
                                 name=f"Moving average ({window})", line=dict(color=AMBER, width=2),
                                 hovertemplate="%{x|" + fmt + "}<br>MA %{y:,.1f} mm<extra></extra>"))
    fig.update_yaxes(title=y_title)
    buttons = [dict(count=6, label="6M", step="month", stepmode="backward"),
               dict(count=1, label="1Y", step="year", stepmode="backward"),
               dict(count=5, label="5Y", step="year", stepmode="backward"), dict(step="all", label="All")]
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06, bgcolor="rgba(11,20,36,0.6)"),
                     rangeselector=dict(buttons=buttons, bgcolor="rgba(11,20,36,0.8)", activecolor="rgba(45,212,191,0.35)",
                                        font=dict(color=INK), y=1.12))
    return _theme(fig, 440)


# ----------------------------------------------------------------------------- distribution
def distribution_chart(values: np.ndarray, unit: str, log_counts: bool = False, wet_only: bool = False) -> go.Figure:
    v = np.asarray(values, float)
    v = v[~np.isnan(v)]
    if wet_only:
        v = v[v >= config.WET_OBSERVATION_MM]
    if v.size == 0:
        return empty_figure("No observations to display")
    counts, edges = np.histogram(v, bins=min(60, max(10, int(np.sqrt(v.size)))))
    centres = (edges[:-1] + edges[1:]) / 2
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.04)
    fig.add_trace(go.Bar(x=centres, y=counts, width=np.diff(edges), marker_color=TEAL, marker_line_width=0, opacity=0.85,
                         name="Observations", hovertemplate="%{x:,.1f} " + unit + "<br>%{y:,} observations<extra></extra>"), 1, 1)
    sample = v if v.size <= MAX_PLOT_POINTS else np.random.default_rng(0).choice(v, MAX_PLOT_POINTS, replace=False)
    fig.add_trace(go.Box(x=sample, orientation="h", name="", marker_color=CYAN, line_color=CYAN, boxpoints="outliers",
                         marker=dict(size=3, opacity=0.5, color=AMBER), hoverinfo="x", showlegend=False), 2, 1)
    for q, dash in ((50, "dot"), (90, "dash"), (95, "dash"), (99, "dash")):
        x = float(np.percentile(v, q))
        fig.add_vline(x=x, line=dict(color=MUTED if q == 50 else AMBER, width=1, dash=dash), row=1, col=1,
                      annotation_text=f"P{q}", annotation_font=dict(color=MUTED, size=10), annotation_position="top")
    if log_counts:
        fig.update_yaxes(type="log", row=1, col=1)
    fig.update_yaxes(title="Observations", row=1, col=1)
    fig.update_yaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(title=unit, row=2, col=1)
    return _theme(fig, 400, legend=False)


# ----------------------------------------------------------------------------- map & ranking
def _map_trace(**kw):
    if hasattr(go, "Scattermap"):
        return go.Scattermap(**kw), "map"
    return go.Scattermapbox(**kw), "mapbox"


def regional_map(summary: pd.DataFrame, metric: str = "total", geojson: dict | None = None,
                 selected: str | None = None) -> tuple[go.Figure | None, str]:
    """Return (figure, note). Figure is None when no real geography is available."""
    from .data_loader import normalise_region_key

    labels = {"total": "Total rainfall", "average": "Average rainfall", "maximum": "Maximum rainfall"}
    hover = ("<b>%{customdata[0]}</b><br>Total: %{customdata[1]:,.1f} mm<br>Average: %{customdata[2]:,.2f} mm"
             "<br>Maximum: %{customdata[3]:,.1f} mm<br>Observations: %{customdata[4]:,}<extra></extra>")
    cols = ["region", "total", "average", "maximum", "observations"]

    if geojson is not None and not summary.empty:
        s = summary.copy()
        s["key"] = s["region"].map(normalise_region_key)
        ids = {f["id"] for f in geojson["features"]}
        matched = s[s["key"].isin(ids)]
        if len(matched):
            Choro = go.Choroplethmap if hasattr(go, "Choroplethmap") else go.Choroplethmapbox
            fig = go.Figure(Choro(geojson=geojson, locations=matched["key"], z=matched[metric],
                                  customdata=matched[cols].to_numpy(), hovertemplate=hover,
                                  colorscale=[[0, "#0B1F33"], [0.5, "#0E7C86"], [1, TEAL]], marker_opacity=0.85,
                                  marker_line_color="rgba(232,238,247,0.35)", marker_line_width=0.5,
                                  colorbar=dict(title=dict(text=f"{labels[metric]} (mm)", font=dict(color=MUTED)),
                                                tickfont=dict(color=MUTED), thickness=10, len=0.7)))
            fig.update_layout(**{"map" if hasattr(go, "Choroplethmap") else "mapbox": dict(style="carto-darkmatter", center=dict(lat=22.5, lon=79), zoom=3.1)})
            note = f"Choropleth: {len(matched)} of {len(s)} regions matched to the supplied boundary file."
            return _theme(fig, 520, legend=False), note

    if {"latitude", "longitude"}.issubset(summary.columns):
        s = summary.dropna(subset=["latitude", "longitude"])
        if len(s):
            vals = s[metric].to_numpy(float)
            span = (vals.max() - vals.min()) or 1.0
            size = 9 + 22 * (vals - vals.min()) / span
            trace, key = _map_trace(lat=s["latitude"], lon=s["longitude"], mode="markers",
                                    marker=dict(size=size, color=vals, colorscale=[[0, "#164E63"], [0.5, CYAN], [1, TEAL]],
                                                opacity=0.85, showscale=True,
                                                colorbar=dict(title=dict(text=f"{labels[metric]} (mm)", font=dict(color=MUTED)),
                                                              tickfont=dict(color=MUTED), thickness=10, len=0.7)),
                                    customdata=s[cols].to_numpy(), hovertemplate=hover)
            fig = go.Figure(trace)
            if selected is not None and (s["region"] == selected).any():
                sel = s[s["region"] == selected]
                t2, _ = _map_trace(lat=sel["latitude"], lon=sel["longitude"], mode="markers", hoverinfo="skip",
                                   marker=dict(size=34, color="rgba(0,0,0,0)"), showlegend=False)
                t3, _ = _map_trace(lat=sel["latitude"], lon=sel["longitude"], mode="markers+text", text=sel["region"],
                                   textposition="top center", textfont=dict(color=AMBER, size=13), hoverinfo="skip",
                                   marker=dict(size=14, color=AMBER), showlegend=False)
                fig.add_traces([t2, t3])
            lat_span = max(s["latitude"].max() - s["latitude"].min(), 0.5)
            lon_span = max(s["longitude"].max() - s["longitude"].min(), 0.5)
            zoom = float(np.clip(np.log2(360 / max(lat_span * 1.6, lon_span * 1.2)), 2, 9.5))
            fig.update_layout(**{key: dict(style="carto-darkmatter", zoom=zoom,
                                           center=dict(lat=float(s["latitude"].mean()), lon=float(s["longitude"].mean())))})
            return _theme(fig, 520, legend=False), "Markers placed at coordinates supplied with the dataset or reference file."
    return None, ""


def ranking_bar(summary: pd.DataFrame, metric: str, n: int = 10, ascending: bool = False,
                highlight: str | None = None, height: int | None = None) -> go.Figure:
    if summary.empty:
        return empty_figure("No regions to rank")
    s = summary.sort_values(metric, ascending=ascending).head(n).iloc[::-1]
    base = CYAN if ascending else TEAL
    colors = [AMBER if r == highlight else base for r in s["region"]]
    fig = go.Figure(go.Bar(x=s[metric], y=s["region"], orientation="h", marker_color=colors, marker_line_width=0,
                           text=[f"{v:,.0f}" if metric == "total" else f"{v:,.1f}" for v in s[metric]], textposition="outside",
                           textfont=dict(color=MUTED, size=11), cliponaxis=False,
                           hovertemplate="<b>%{y}</b><br>%{x:,.1f} mm<extra></extra>"))
    fig.update_xaxes(title=f"{metric.capitalize()} rainfall (mm)")
    fig.update_yaxes(automargin=True)
    return _theme(fig, height or max(260, 34 * len(s) + 70), legend=False)


# ----------------------------------------------------------------------------- seasonal
def monthly_chart(monthly: pd.DataFrame) -> go.Figure:
    if monthly.empty:
        return empty_figure("Monthly analysis not available")
    peak, low = monthly["mean_total"].idxmax(), monthly["mean_total"].idxmin()
    colors = [AMBER if i == peak else (CYAN if i == low else TEAL) for i in monthly.index]
    fig = go.Figure(go.Bar(
        x=monthly["month_name"].str[:3], y=monthly["mean_total"], marker_color=colors, marker_line_width=0,
        error_y=dict(type="data", array=monthly["std"], color="rgba(232,238,247,0.35)", thickness=1),
        text=[f"{p:.0f}%" for p in monthly["contribution_pct"]], textposition="outside", textfont=dict(color=MUTED, size=11),
        customdata=np.stack([monthly["contribution_pct"], monthly["minimum"], monthly["maximum"], monthly["n_years"]], axis=-1),
        hovertemplate="<b>%{x}</b><br>Typical total: %{y:,.1f} mm<br>Share of annual: %{customdata[0]:.1f}%"
                      "<br>Range across years: %{customdata[1]:,.0f}\u2013%{customdata[2]:,.0f} mm<br>Years: %{customdata[3]}<extra></extra>"))
    fig.update_yaxes(title="Mean monthly total (mm)")
    fig.add_annotation(text="Amber = peak month, blue = lowest month. Labels show share of annual total; whiskers \u00b11 SD across years.",
                       xref="paper", yref="paper", x=0, y=-0.16, showarrow=False, font=dict(color=MUTED, size=11))
    return _theme(fig, 400, legend=False)


def month_year_heatmap(matrix: pd.DataFrame) -> go.Figure:
    if matrix.empty:
        return empty_figure("Heatmap not available")
    fig = go.Figure(go.Heatmap(z=matrix.to_numpy(), x=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                               y=matrix.index.astype(str), colorscale=[[0, "#0A1628"], [0.5, "#0E7C86"], [1, TEAL]],
                               colorbar=dict(title=dict(text="mm", font=dict(color=MUTED)), tickfont=dict(color=MUTED), thickness=10),
                               hovertemplate="%{y} %{x}<br>%{z:,.1f} mm<extra></extra>", xgap=1, ygap=1))
    fig.update_yaxes(type="category", autorange="reversed")
    return _theme(fig, max(300, 22 * len(matrix) + 90), legend=False)


def seasonal_chart(season_year: pd.DataFrame) -> go.Figure:
    if season_year.empty:
        return empty_figure("Seasonal analysis not available")
    fig = go.Figure()
    for i, (season, g) in enumerate(season_year.groupby("season", observed=True)):
        fig.add_trace(go.Bar(x=g["year"], y=g["rainfall"], name=str(season), marker_color=PALETTE[i % len(PALETTE)],
                             hovertemplate="%{x}<br>" + str(season) + ": %{y:,.1f} mm<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="Season total (mm)")
    fig.update_xaxes(type="category")
    return _theme(fig, 400)


# ----------------------------------------------------------------------------- comparison
def comparison_bars(summary: pd.DataFrame) -> go.Figure:
    metrics = [("total", "Total rainfall (mm)"), ("average", "Average per observation (mm)"),
               ("maximum", "Maximum observation (mm)"), ("variability_cv", "Variability (coeff. of variation)")]
    fig = make_subplots(rows=1, cols=4, subplot_titles=[m[1] for m in metrics], horizontal_spacing=0.06)
    for c, (m, _) in enumerate(metrics, start=1):
        fig.add_trace(go.Bar(x=summary["region"], y=summary[m], marker_color=[PALETTE[i % len(PALETTE)] for i in range(len(summary))],
                             marker_line_width=0, hovertemplate="<b>%{x}</b><br>%{y:,.2f}<extra></extra>"), 1, c)
    fig.update_annotations(font=dict(size=11, color=MUTED))
    return _theme(fig, 340, legend=False)


def comparison_lines(df: pd.DataFrame, x: str, y: str, x_title: str, y_title: str, month_ticks: bool = False) -> go.Figure:
    if df.empty:
        return empty_figure("Not enough data to compare")
    fig = go.Figure()
    for i, (region, g) in enumerate(df.groupby("region")):
        fig.add_trace(go.Scatter(x=g[x], y=g[y], mode="lines+markers", name=str(region), line=dict(color=PALETTE[i % len(PALETTE)], width=2),
                                 marker=dict(size=6), hovertemplate="<b>" + str(region) + "</b><br>%{x}: %{y:,.1f} mm<extra></extra>"))
    fig.update_xaxes(title=x_title)
    fig.update_yaxes(title=y_title)
    if month_ticks:
        fig.update_xaxes(tickmode="array", tickvals=list(range(1, 13)),
                         ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    else:
        fig.update_xaxes(dtick=1)
    return _theme(fig, 380)


# ----------------------------------------------------------------------------- events & anomalies
def events_timeseries(df: pd.DataFrame, events: pd.DataFrame, threshold: float, unit: str) -> go.Figure:
    if df.empty:
        return empty_figure("No observations")
    d = df
    if len(d) > MAX_PLOT_POINTS:
        d = d.sample(MAX_PLOT_POINTS, random_state=0).sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=d["date"], y=d["rainfall"], mode="markers", name="Observations",
                               marker=dict(size=3, color=MUTED, opacity=0.45), customdata=d["region"].astype(str),
                               hovertemplate="%{x|%d %b %Y}<br>%{customdata}<br>%{y:,.1f} " + unit + "<extra></extra>"))
    if len(events):
        fig.add_trace(go.Scattergl(x=events["date"], y=events["rainfall"], mode="markers", name="Above threshold",
                                   marker=dict(size=7, color=AMBER, line=dict(color="#060A12", width=0.5)),
                                   customdata=events["region"], hovertemplate="%{x|%d %b %Y}<br>%{customdata}<br>%{y:,.1f} " + unit + "<extra></extra>"))
    fig.add_hline(y=threshold, line=dict(color=AMBER, dash="dash", width=1), annotation_text=f"threshold {threshold:,.1f}",
                  annotation_font=dict(color=AMBER, size=11), annotation_position="top left")
    fig.update_yaxes(title=unit)
    return _theme(fig, 400)


def events_by_month(events: pd.DataFrame) -> go.Figure:
    if events.empty:
        return empty_figure("No observations above the threshold")
    counts = events.groupby(events["date"].dt.month).size().reindex(range(1, 13), fill_value=0)
    fig = go.Figure(go.Bar(x=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], y=counts.values,
                           marker_color=AMBER, marker_line_width=0, hovertemplate="%{x}: %{y} observations<extra></extra>"))
    fig.update_yaxes(title="Flagged observations")
    return _theme(fig, 400, legend=False)


def deviation_chart(df: pd.DataFrame, flagged: pd.DataFrame, k: float, unit: str) -> go.Figure:
    d = df.dropna(subset=["deviation_from_rolling"])
    if d.empty:
        return empty_figure("Not enough history to compute a rolling baseline")
    if len(d) > MAX_PLOT_POINTS:
        d = d.sample(MAX_PLOT_POINTS, random_state=0).sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=d["date"], y=d["deviation_from_rolling"], mode="markers", name="Deviation",
                               marker=dict(size=3, color=MUTED, opacity=0.45), customdata=d["region"].astype(str),
                               hovertemplate="%{x|%d %b %Y}<br>%{customdata}<br>%{y:+,.1f} " + unit + "<extra></extra>"))
    if len(flagged):
        fig.add_trace(go.Scattergl(x=flagged["date"], y=flagged["deviation_from_rolling"], mode="markers",
                                   name=f"|z| \u2265 {k:g}", marker=dict(size=7, color=ROSE), customdata=flagged["region"].astype(str),
                                   hovertemplate="%{x|%d %b %Y}<br>%{customdata}<br>%{y:+,.1f} " + unit + "<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=GRID, width=1))
    fig.update_yaxes(title=f"Deviation from rolling baseline ({unit})")
    return _theme(fig, 400)
