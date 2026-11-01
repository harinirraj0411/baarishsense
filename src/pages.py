"""Page renderers. Each page receives a Context built in app.py from the sidebar filters."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from . import analytics as A
from . import config
from . import ui_components as ui
from . import visualizations as V


@dataclass
class Context:
    df_all: pd.DataFrame        # full analytical table
    df_context: pd.DataFrame    # state + time filters (used for maps / rankings)
    df_scope: pd.DataFrame      # context + selected location (used for KPIs / trends)
    freq: str
    location: str | None
    state: str | None
    scope_label: str
    period_label: str
    active_filters: list
    coords: pd.DataFrame | None
    geojson: dict | None
    quality: dict
    schema: object
    region_label: str

    @property
    def unit(self) -> str:
        return A.unit_label(self.freq)


def _dl(label: str, df: pd.DataFrame, name: str, key: str) -> None:
    st.download_button(label, A.to_csv_bytes(df), file_name=name, mime="text/csv", key=key, disabled=df.empty)


def _summary_with_download(ctx: Context, kind: str, title: str, key: str, **kw) -> None:
    lines = A.generate_analytical_summary(ctx.df_scope, ctx.freq, ctx.scope_label, ctx.period_label, kind=kind, **kw)
    ui.summary_box(lines)
    st.download_button("Download summary (.txt)", A.summary_to_text(f"BAARISHSENSE - {title}", lines),
                       file_name=f"baarishsense_{kind}_summary.txt", mime="text/plain", key=key)


def _kpis(ctx: Context, df: pd.DataFrame) -> dict:
    s = A.get_summary_statistics(df)
    unit = ctx.unit
    noun = A.observation_noun(ctx.freq).upper()
    ui.kpi_row([
        dict(label="Total rainfall", value=f"{s['total']:,.0f}", unit=config.RAINFALL_UNIT,
             sub=f"Sum of {s['n_records']:,} observations"),
        dict(label="Average rainfall", value=f"{s['mean']:,.2f}", unit=unit, sub="Mean per observation"),
        dict(label="Maximum rainfall", value=f"{s['maximum']:,.1f}", unit=unit,
             sub=f"{s['max_region']} \u2022 {A.fmt_date(s['max_date'])}", hot=True),
        dict(label="Wettest region", value=s["wettest_region"],
             sub=f"{s['wettest_total']:,.0f} {config.RAINFALL_UNIT} total" if s["n_regions"] > 1 else "Single region selected"),
        dict(label=f"Observation {noun.lower()}", value=f"{s['obs_periods']:,}", sub=f"{s['n_regions']} region(s)"),
    ])
    if s["uneven_coverage"]:
        ui.note("Regions have different numbers of observations; totals are not strictly like-for-like.")
    return s


def _trend_block(ctx: Context, df: pd.DataFrame, key: str) -> None:
    ui.section_title("Rainfall Trend", "Zoom with the range slider or the 6M / 1Y / 5Y buttons. Hover for exact values.")
    opts = A.available_aggregations(ctx.freq)
    c1, c2, c3 = st.columns([1.3, 1, 1.2])
    agg = c1.radio("Aggregation", opts, horizontal=True, key=f"{key}_agg", index=min(1, len(opts) - 1) if "Daily" in opts else 0)
    show_ma = c2.toggle("Moving average", value=False, key=f"{key}_ma")
    default_w = {"Daily": 30, "Monthly": 12, "Annual": 5}[agg]
    window = c3.number_input("Window (periods)", 2, 400, default_w, key=f"{key}_win_{agg}", disabled=not show_ma)
    trend = A.calculate_rainfall_trend(df, agg)
    if show_ma:
        trend = A.calculate_rolling_average(trend, int(window))
    multi = df["region"].nunique() > 1
    y_title = f"Mean regional {agg.lower()} total (mm)" if multi else f"{agg} total (mm)"
    st.plotly_chart(V.trend_chart(trend, agg, y_title, show_ma, int(window)), width="stretch", key=f"{key}_trend")
    if multi:
        ui.note("Several regions selected: each point is the average of the regions' period totals.")
    if len(trend) and agg == "Annual":
        ui.note("Years at the edges of the selected period may be partial; hover shows the observation count.")


def _distribution_block(ctx: Context, df: pd.DataFrame, key: str) -> None:
    ui.section_title("Rainfall Distribution",
                     "Most observations are small; the long right tail holds the extreme observations. Dashed lines mark P50, P90, P95 and P99.")
    c1, c2 = st.columns(2)
    wet = c1.checkbox("Wet observations only", value=ctx.freq == "daily", key=f"{key}_wet",
                      help=f"Hides observations below {config.WET_OBSERVATION_MM:g} {config.RAINFALL_UNIT}.")
    log = c2.checkbox("Log count axis", value=False, key=f"{key}_log")
    st.plotly_chart(V.distribution_chart(df["rainfall"].to_numpy(), ctx.unit, log, wet), width="stretch", key=f"{key}_dist")


def _events_preview(ctx: Context, df: pd.DataFrame) -> None:
    ui.section_title("High-Rainfall Events", "Top observations above the 95th percentile of wet observations. Open Event Screening to change the method.")
    thr = A.calculate_percentile_threshold(df["rainfall"], "P95", wet_only=True)
    ev = A.detect_high_rainfall_events(df, thr["threshold"])
    st.caption(f"Threshold {thr['threshold']:,.1f} {ctx.unit} \u2022 {len(ev):,} observations above it")
    show = ev.head(10)[["date", "region", "rainfall", "threshold", "status"]].rename(
        columns={"date": "Date", "region": "Region", "rainfall": f"Rainfall ({ctx.unit})", "threshold": "Threshold", "status": "Status"})
    st.dataframe(show, width="stretch", hide_index=True,
                 column_config={"Date": st.column_config.DateColumn(format="DD MMM YYYY"),
                                f"Rainfall ({ctx.unit})": st.column_config.NumberColumn(format="%.1f"),
                                "Threshold": st.column_config.NumberColumn(format="%.1f")})


# ============================================================================ pages
def render_overview(ctx: Context) -> None:
    ui.section_title("National Overview", "What does rainfall look like across the selected Indian regions?")
    df = ctx.df_scope
    if df.empty:
        return ui.empty_state()
    if ctx.location:
        ui.location_banner(ctx.location, ctx.state, ctx.period_label)
    _kpis(ctx, df)

    ui.section_title("Rainfall Map", "Geographic pattern for the selected period (regions in the current state / date scope).")
    summary = A.calculate_regional_summary(ctx.df_context, ctx.coords)
    left, right = st.columns([1.7, 1])
    with left:
        metric = st.radio("Colour by", ["total", "average", "maximum"], horizontal=True, key="ov_metric",
                          format_func=str.capitalize)
        fig, note = V.regional_map(summary, metric, ctx.geojson, ctx.location)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="ov_map")
            ui.note(note)
        else:
            ui.state_card("GEOGRAPHIC MAP NEEDS COORDINATES",
                          "<p>This dataset has no latitude/longitude columns and no reference file was found, so no map is drawn "
                          "(coordinates are never guessed).</p><ul>"
                          "<li>Add <code>latitude</code> and <code>longitude</code> columns to the CSV, or</li>"
                          "<li>provide <code>data/reference/region_coordinates.csv</code> (region, latitude, longitude), or</li>"
                          "<li>provide a boundary file at <code>data/reference/regions.geojson</code> for a choropleth.</li></ul>")
    with right:
        st.markdown("**Regional ranking**")
        n = st.slider("Regions shown", 5, 25, 10, key="ov_n")
        st.plotly_chart(V.ranking_bar(summary, metric, n, False, ctx.location), width="stretch", key="ov_rank")

    _trend_block(ctx, df, "ov")
    _distribution_block(ctx, df, "ov")
    _events_preview(ctx, df)
    _summary_with_download(ctx, "overview", "Overview summary", "ov_sum")
    st.markdown("&nbsp;")
    c1, c2 = st.columns(2)
    with c1:
        _dl("Download filtered rainfall data (CSV)", df[["date", "region"] + (["state"] if "state" in df else []) + ["rainfall"]],
            "baarishsense_filtered_rainfall.csv", "ov_dl1")
    with c2:
        _dl("Download regional summary (CSV)", summary, "baarishsense_regional_summary.csv", "ov_dl2")


def render_location(ctx: Context) -> None:
    ui.section_title("Location Analysis", f"Detailed view of one {ctx.region_label.lower()}.")
    df = ctx.df_scope
    if not ctx.location:
        ui.state_card("NO LOCATION SELECTED",
                      f"<p>Use <b>Search location</b> in the sidebar to pick a {ctx.region_label.lower()}. "
                      "Until then this page shows all regions in the current scope.</p>")
    if df.empty:
        return ui.empty_state()
    name = ctx.location or "All regions"
    state = ctx.state or (str(df["state"].iloc[0]) if ctx.location and "state" in df else None)
    s = A.get_summary_statistics(df)
    ui.location_banner(name, state, ctx.period_label,
                       extra=f"{s['n_records']:,} observations \u2022 {ctx.freq} resolution")
    _kpis(ctx, df)
    _trend_block(ctx, df, "loc")

    ui.section_title("Monthly Profile", "Typical rainfall for each calendar month in the selected period.")
    monthly = A.calculate_monthly_rainfall(df)
    st.plotly_chart(V.monthly_chart(monthly), width="stretch", key="loc_month")

    ui.section_title("Year-over-Year Change", "Annual totals. Change is shown only between consecutive years with at least 90% observation coverage.")
    yoy = A.calculate_year_over_year_change(df, ctx.freq)
    if len(yoy) >= 2:
        tbl = yoy.rename(columns={"year": "Year", "rainfall": f"Annual total (mm)", "coverage": "Coverage", "complete": "Complete year",
                                  "yoy_abs": "Change (mm)", "yoy_pct": "Change (%)"})
        st.dataframe(tbl, width="stretch", hide_index=True, column_config={
            "Annual total (mm)": st.column_config.NumberColumn(format="%.1f"), "Coverage": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
            "Change (mm)": st.column_config.NumberColumn(format="%+.1f"), "Change (%)": st.column_config.NumberColumn(format="%+.1f%%")})
    else:
        ui.note("At least two years are needed for a year-over-year comparison.")
    _distribution_block(ctx, df, "loc")
    _summary_with_download(ctx, "overview", "Location summary", "loc_sum")
    st.markdown("&nbsp;")
    _dl("Download filtered rainfall data (CSV)", df[["date", "region"] + (["state"] if "state" in df else []) + ["rainfall"]],
        "baarishsense_location_rainfall.csv", "loc_dl")


def render_compare(ctx: Context) -> None:
    ui.section_title("Regional Comparison", "Choose two or more regions. Charts use the current date and state filters.")
    ctxdf = ctx.df_context
    if ctxdf.empty:
        return ui.empty_state()
    options = sorted(ctxdf["region"].astype(str).unique())
    if "cmp_regions" in st.session_state:
        st.session_state["cmp_regions"] = [r for r in st.session_state["cmp_regions"] if r in options]
    ranked = A.calculate_regional_summary(ctxdf)["region"].tolist()
    default = ([ctx.location] if ctx.location in options else []) + [r for r in ranked if r != ctx.location]
    if "cmp_regions" not in st.session_state:
        st.session_state["cmp_regions"] = default[:2]
    chosen = st.multiselect("Compare regions", options, max_selections=8, key="cmp_regions")
    if len(chosen) < 2:
        ui.state_card("SELECT AT LEAST TWO REGIONS", "<p>Pick regions above to compare totals, variability, seasonality and annual change.</p>")
    else:
        sub = ctxdf[ctxdf["region"].isin(chosen)]
        rs = A.calculate_regional_summary(sub)
        st.plotly_chart(V.comparison_bars(rs), width="stretch", key="cmp_bars")
        c1, c2 = st.columns(2)
        with c1:
            ui.section_title("Seasonal Pattern", "Typical monthly total by calendar month.")
            rows = []
            for r in chosen:
                m = A.calculate_monthly_rainfall(sub[sub["region"] == r])
                if not m.empty:
                    rows.append(m.assign(region=r))
            mm = pd.concat(rows) if rows else pd.DataFrame()
            st.plotly_chart(V.comparison_lines(mm, "month", "mean_total", "Month", "Mean monthly total (mm)", True) if len(mm)
                            else V.empty_figure("Monthly comparison needs daily or monthly data"), width="stretch", key="cmp_seas")
        with c2:
            ui.section_title("Year-over-Year", "Annual total per region.")
            ann = A.calculate_annual_by_region(sub, ctx.freq)
            st.plotly_chart(V.comparison_lines(ann, "year", "rainfall", "Year", "Annual total (mm)"), width="stretch", key="cmp_ann")
            ui.note("Partial years appear lower; check coverage in the download.")
        ui.section_title("Comparison Table")
        st.dataframe(rs.drop(columns=[c for c in ("latitude", "longitude") if c in rs]), width="stretch", hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ("total", "average", "maximum", "std", "variability_cv")})
        ui.summary_box(A.generate_analytical_summary(sub, ctx.freq, ctx.scope_label, ctx.period_label, kind="comparison", regional_summary=rs))
        st.markdown("&nbsp;")
        _dl("Download comparison (CSV)", rs, "baarishsense_comparison.csv", "cmp_dl")

    ui.section_title("Rankings", "Across all regions in the current state / date scope.")
    metric = st.radio("Rank by", ["total", "average", "maximum"], horizontal=True, key="cmp_metric", format_func=str.capitalize)
    n = st.slider("Regions per list", 3, 20, 10, key="cmp_n")
    full = A.calculate_regional_summary(ctxdf)
    a, b = st.columns(2)
    with a:
        st.markdown("**TOP RAINFALL REGIONS**")
        st.plotly_chart(V.ranking_bar(full, metric, n, False, ctx.location), width="stretch", key="cmp_top")
    with b:
        st.markdown("**LOWEST RAINFALL REGIONS**")
        st.plotly_chart(V.ranking_bar(full, metric, n, True, ctx.location), width="stretch", key="cmp_low")
    _dl("Download full regional ranking (CSV)", full.sort_values(metric, ascending=False), "baarishsense_regional_ranking.csv", "cmp_dl2")


def render_seasonal(ctx: Context) -> None:
    ui.section_title("Seasonal Intelligence", f"Monthly and seasonal rainfall. Seasons follow: {config.SEASON_DEFINITION_NAME}.")
    df = ctx.df_scope
    if df.empty:
        return ui.empty_state()
    if ctx.freq == "annual":
        return ui.state_card("SEASONAL ANALYSIS NEEDS SUB-ANNUAL DATA", "<p>This dataset has one observation per year, so monthly and seasonal patterns cannot be computed.</p>")
    if ctx.location:
        ui.location_banner(ctx.location, ctx.state, ctx.period_label)
    monthly = A.calculate_monthly_rainfall(df)
    peak, low = monthly.loc[monthly["mean_total"].idxmax()], monthly.loc[monthly["mean_total"].idxmin()]
    ui.kpi_row([dict(label="Peak rainfall month", value=peak["month_name"], sub=f"{peak['mean_total']:,.1f} mm typical \u2022 {peak['contribution_pct']:.1f}% of year", hot=True),
                dict(label="Lowest rainfall month", value=low["month_name"], sub=f"{low['mean_total']:,.1f} mm typical \u2022 {low['contribution_pct']:.1f}% of year"),
                dict(label="Years analysed", value=f"{int(monthly['n_years'].max())}", sub="Year-month combinations per month")])
    ui.section_title("Monthly Rainfall", "Typical total per calendar month with contribution to the annual total.")
    st.plotly_chart(V.monthly_chart(monthly), width="stretch", key="sea_month")
    ui.section_title("Year \u00d7 Month Heatmap", "Month totals for every year in the selection (mean across regions).")
    st.plotly_chart(V.month_year_heatmap(A.calculate_month_year_matrix(df)), width="stretch", key="sea_heat")
    ui.section_title("Seasonal Totals by Year", "Year-to-year variation within each season.")
    sy = A.calculate_seasonal_rainfall(df)
    st.plotly_chart(V.seasonal_chart(sy), width="stretch", key="sea_bar")
    ss = A.calculate_seasonal_summary(sy)
    st.dataframe(ss.rename(columns={"season": "Season", "mean_total": "Mean total (mm)", "std": "Std dev (mm)", "years": "Years",
                                    "share_pct": "Share (%)", "wettest_year": "Wettest year", "driest_year": "Driest year"}),
                 width="stretch", hide_index=True,
                 column_config={"Mean total (mm)": st.column_config.NumberColumn(format="%.1f"), "Std dev (mm)": st.column_config.NumberColumn(format="%.1f"),
                                "Share (%)": st.column_config.NumberColumn(format="%.1f")})
    _summary_with_download(ctx, "seasonal", "Seasonal summary", "sea_sum")
    st.markdown("&nbsp;")
    _dl("Download monthly profile (CSV)", monthly, "baarishsense_monthly_profile.csv", "sea_dl1")


def render_events(ctx: Context) -> None:
    ui.section_title("High-Rainfall Event Screening",
                     "Flags observations that are statistically unusual within the selected data. This is not flood prediction and does not indicate flooding.")
    df = ctx.df_scope
    if df.empty:
        return ui.empty_state()
    c1, c2, c3 = st.columns([1.2, 1, 1.2])
    method_label = c1.radio("Threshold method", ["90th percentile", "95th percentile", "99th percentile", "Fixed value"], index=1, key="ev_method")
    method = {"90th percentile": "P90", "95th percentile": "P95", "99th percentile": "P99", "Fixed value": "FIXED"}[method_label]
    fixed = c2.number_input(f"Fixed threshold ({ctx.unit})", 0.0, 5000.0, float(round(df["rainfall"].quantile(0.95), 1)), 1.0,
                            key="ev_fixed", disabled=method != "FIXED")
    wet_only = c3.checkbox("Percentile of wet observations only", value=ctx.freq == "daily", key="ev_wet", disabled=method == "FIXED",
                           help=f"Excludes observations below {config.WET_OBSERVATION_MM:g} {config.RAINFALL_UNIT} when calculating the percentile, so dry days do not pull the threshold down.")
    thr = A.calculate_percentile_threshold(df["rainfall"], method, fixed, wet_only)
    ev = A.detect_high_rainfall_events(df, thr["threshold"])
    pct = len(ev) / len(df) * 100
    ui.kpi_row([dict(label="Selected threshold", value=f"{thr['threshold']:,.1f}", unit=ctx.unit, sub=f"{thr['label']} \u2022 {thr['basis']}"),
                dict(label="High-rainfall observations", value=f"{len(ev):,}", sub=f"of {len(df):,} observations", hot=True),
                dict(label="Percent of observations", value=f"{pct:.1f}%"),
                dict(label="Maximum observation", value=f"{df['rainfall'].max():,.1f}", unit=ctx.unit)])
    if ev.empty:
        ui.state_card("NO OBSERVATIONS ABOVE THRESHOLD", "<p>Lower the percentile or fixed value to see flagged observations.</p>")
    a, b = st.columns([1.6, 1])
    with a:
        ui.section_title("Observations vs Threshold")
        st.plotly_chart(V.events_timeseries(df, ev, thr["threshold"], ctx.unit), width="stretch", key="ev_ts")
    with b:
        ui.section_title("When They Occur")
        st.plotly_chart(V.events_by_month(ev), width="stretch", key="ev_month")

    ui.section_title("Event Table", "Click a column header to sort. Select a row to see why it was flagged.")
    f1, f2 = st.columns(2)
    regs = f1.multiselect("Filter by region", sorted(ev["region"].unique()), key="ev_regs")
    min_r = f2.number_input("Minimum rainfall", 0.0, float(max(ev["rainfall"].max() if len(ev) else 1, 1)), 0.0, 1.0, key="ev_min")
    view = ev[(ev["region"].isin(regs) if regs else True) & (ev["rainfall"] >= min_r)].reset_index(drop=True)
    cols = ["date", "region"] + (["state"] if "state" in view else []) + ["rainfall", "threshold", "status"]
    tbl = view[cols]
    sel = st.dataframe(tbl, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key="ev_table",
                       column_config={"date": st.column_config.DateColumn("Date", format="DD MMM YYYY"), "region": "Region", "state": "State",
                                      "rainfall": st.column_config.NumberColumn(f"Rainfall ({ctx.unit})", format="%.1f"),
                                      "threshold": st.column_config.NumberColumn("Threshold", format="%.1f"), "status": "Status"})
    _dl("Download high-rainfall events (CSV)", view, "baarishsense_high_rainfall_events.csv", "ev_dl")

    if len(view):
        ui.section_title("Why Was This Flagged?")
        rows = sel.selection.rows if sel is not None else []
        row = view.iloc[rows[0]] if rows else view.iloc[0]
        if not rows:
            ui.note("Showing the highest observation. Select a row in the table to explain another.")
        info = A.explain_event(row, ctx.freq)
        info["where"] = f"{A.fmt_date(row['date'])} \u2022 {row['region']}"
        ui.explain_card(info)
    _summary_with_download(ctx, "events", "High-rainfall screening summary", "ev_sum",
                           threshold=thr["threshold"], threshold_label=thr["label"], basis=thr["basis"], events=ev)


def render_anomaly(ctx: Context) -> None:
    ui.section_title("Anomaly View", "Deviation of each observation from its recent rolling baseline - a statistical measure, not a climate conclusion.")
    df = ctx.df_scope
    if df.empty:
        return ui.empty_state()
    with st.expander("Methodology", expanded=False):
        st.markdown(
            f"- **Baseline**: {A.baseline_description(ctx.freq)} for the same region (the current observation is excluded).\n"
            "- **Deviation**: observation minus baseline.\n"
            "- **z-score**: deviation divided by that region's standard deviation of deviations over its full record.\n"
            "- **Seasonal deviation**: observation minus the region's mean for the same calendar month over its full record.\n"
            "- **Percentile position**: rank of the observation within the region's full record.\n"
            "- Flagged observations are statistical outliers on the loaded data only. They say nothing about climate trends or causes.")
    k = st.slider("Flag when |z| is at least", 1.5, 5.0, 3.0, 0.5, key="an_k")
    scored = df.dropna(subset=["deviation_z"])
    flagged = scored[scored["deviation_z"].abs() >= k].copy()
    flagged["region"] = flagged["region"].astype(str)
    ui.kpi_row([dict(label="Scored observations", value=f"{len(scored):,}", sub="Need baseline history"),
                dict(label="Flagged", value=f"{len(flagged):,}", sub=f"|z| \u2265 {k:g}", hot=True),
                dict(label="Largest positive deviation", value=f"{scored['deviation_from_rolling'].max():+,.1f}" if len(scored) else "n/a", unit=ctx.unit),
                dict(label="Largest negative deviation", value=f"{scored['deviation_from_rolling'].min():+,.1f}" if len(scored) else "n/a", unit=ctx.unit)])
    st.plotly_chart(V.deviation_chart(df, flagged, k, ctx.unit), width="stretch", key="an_chart")
    if len(flagged):
        tbl = flagged.sort_values("deviation_z", key=lambda s: s.abs(), ascending=False)[
            ["date", "region", "rainfall", "rolling_baseline", "deviation_from_rolling", "deviation_z", "seasonal_deviation", "percentile_position"]]
        st.dataframe(tbl, width="stretch", hide_index=True, column_config={
            "date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
            **{c: st.column_config.NumberColumn(format="%.2f") for c in tbl.columns if c not in ("date", "region")}})
        _dl("Download flagged deviations (CSV)", tbl, "baarishsense_deviations.csv", "an_dl")
    ui.summary_box(A.generate_analytical_summary(df, ctx.freq, ctx.scope_label, ctx.period_label, kind="anomaly",
                                                 flagged=flagged, k=k, n_scored=len(scored)))


def render_data(ctx: Context) -> None:
    q = ctx.quality
    ui.section_title("Data Quality", "Counts come from the validation pass over the raw file. Excluded rows are never hidden.")
    d0, d1 = q["date_min"], q["date_max"]
    warn_excl = q["excluded_records"] > 0 and q["excluded_records"] / max(q["total_records"], 1) > 0.05
    ui.info_grid([
        ("Total records", f"{q['total_records']:,}", False), ("Valid records", f"{q['valid_records']:,}", False),
        ("Excluded records", f"{q['excluded_records']:,}", warn_excl), ("Missing rainfall values", f"{q['missing_rainfall']:,}", False),
        ("Non-numeric rainfall", f"{q['non_numeric_rainfall']:,}", False), ("Negative rainfall", f"{q['negative_rainfall']:,}", q["negative_rainfall"] > 0),
        ("Invalid dates", f"{q['invalid_dates']:,}", q["invalid_dates"] > 0), ("Duplicates removed", f"{q['duplicates_removed']:,}", False),
        ("Date coverage", f"{A.fmt_date(d0)} \u2013 {A.fmt_date(d1)}", False), ("Number of regions", f"{q['regions']:,}", False),
        ("Rainfall field", str(q["rainfall_field"]), False), ("Region field", str(q["region_field"]), False),
        ("Last available observation", A.fmt_date(q["last_observation"]), False), ("Temporal resolution", q["frequency"], False)])
    for n in q["notes"]:
        ui.note(n)

    ui.section_title("Data Source & Methodology")
    nc = "NOT CONFIGURED \u2013 set in src/config.py"
    geo = f"{q['regions']} {ctx.region_label.lower()}(s)" + (f" across {ctx.df_all['state'].nunique()} state(s)" if "state" in ctx.df_all else "")
    ui.info_grid([
        ("Dataset name", config.DATASET_NAME or nc, not config.DATASET_NAME),
        ("Source organisation", config.SOURCE_ORGANIZATION or nc, not config.SOURCE_ORGANIZATION),
        ("Source URL", config.SOURCE_URL or nc, not config.SOURCE_URL),
        ("Accessed on", config.SOURCE_ACCESSED_ON or nc, not config.SOURCE_ACCESSED_ON),
        ("Date coverage", f"{A.fmt_date(d0)} \u2013 {A.fmt_date(d1)}", False), ("Geographic coverage", geo, False)])
    st.markdown("**Processing methodology**")
    st.markdown(
        "1. Column names are normalised and the date, rainfall and geography columns are detected (or taken from `COLUMN_OVERRIDES`).\n"
        "2. Dates are parsed (ISO first, then day-first vs month-first chosen by parse success). Wide JAN\u2013DEC tables are converted to one row per month.\n"
        "3. Rainfall is converted to numeric; non-numeric, missing and negative values are excluded and counted above.\n"
        "4. Duplicate region/date rows are removed (first kept) and counted. Year, month, season and rolling metrics are derived.")
    st.markdown("**Analytical methodology**")
    st.markdown(
        f"- Trend: period totals per region; the mean across regions when several are selected.\n"
        f"- Monthly profile: mean of region-year-month totals across years.\n- Seasons: {config.SEASON_DEFINITION_NAME}.\n"
        f"- High-rainfall screening: percentile (of wet observations \u2265 {config.WET_OBSERVATION_MM:g} {config.RAINFALL_UNIT} by default) or fixed threshold on the selected data; observations strictly above are flagged.\n"
        "- Year-over-year change only between consecutive years with \u226590% coverage.\n"
        "- Summaries are deterministic text templates filled from the data; no language model is used.")
    st.caption("BAARISHSENSE is an independent analytics project. It is not an official weather service, warning system or flood-prediction model.")
