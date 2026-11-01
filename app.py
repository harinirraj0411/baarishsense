
"""BAARISHSENSE — Rainfall Intelligence & Environmental Analytics."""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="BAARISHSENSE | Rainfall Intelligence",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src import analytics as A  # noqa: E402
from src import config, data_loader, ui_components as ui  # noqa: E402
from src.data_processing import (  # noqa: E402
    DatasetSchemaError,
    clean_data,
    save_processed,
)
from src.pages import (  # noqa: E402
    Context,
    render_anomaly,
    render_compare,
    render_data,
    render_events,
    render_location,
    render_overview,
    render_seasonal,
)

log = logging.getLogger("BAARISHSENSE")

PAGES = {
    "Overview": render_overview,
    "Location": render_location,
    "Compare": render_compare,
    "Seasonal": render_seasonal,
    "Event screening": render_events,
    "Anomaly view": render_anomaly,
    "Data & methodology": render_data,
}

PAGE_ICONS = {
    "Overview": "◈",
    "Location": "⌖",
    "Compare": "⇄",
    "Seasonal": "◷",
    "Event screening": "⚑",
    "Anomaly view": "⌁",
    "Data & methodology": "ⓘ",
}


# ---------------------------------------------------------------------
# PREMIUM UI
# ---------------------------------------------------------------------
def inject_dashboard_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bs-bg: #07111f;
            --bs-panel: #101d30;
            --bs-border: rgba(148, 183, 218, .17);
            --bs-cyan: #46e0e8;
            --bs-muted: #91a7bd;
        }

        .stApp {
            background:
                radial-gradient(ellipse at 8% 0%, rgba(22, 105, 143, .16), transparent 35%),
                radial-gradient(ellipse at 90% 10%, rgba(29, 78, 137, .13), transparent 32%),
                var(--bs-bg);
        }

        [data-testid="stHeader"] {
            background: rgba(7, 17, 31, .88);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0c192a 0%, #081321 100%);
            border-right: 1px solid var(--bs-border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.2rem;
        }

        .block-container {
            max-width: 1600px;
            padding-top: 1.7rem;
            padding-bottom: 2.5rem;
        }

        h1, h2, h3 {
            letter-spacing: -.025em;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(145deg, #13243a, #0d1a2b);
            border: 1px solid var(--bs-border);
            border-radius: 16px;
            padding: 17px 19px;
            min-height: 112px;
            box-shadow: 0 8px 28px rgba(0, 0, 0, .12);
        }

        [data-testid="stMetricLabel"] {
            color: var(--bs-muted);
        }

        [data-testid="stMetricValue"] {
            color: #f3fbff;
            font-weight: 700;
        }

        [data-testid="stMetricDelta"] {
            font-size: .8rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--bs-border);
            border-radius: 15px;
        }

        div[data-testid="stAlert"] {
            border-radius: 12px;
        }

        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 10px;
            border: 1px solid rgba(70, 224, 232, .4);
            transition: all .18s ease;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            border-color: var(--bs-cyan);
            color: var(--bs-cyan);
        }

        [data-testid="stFileUploader"] {
            border: 1px dashed rgba(70, 224, 232, .38);
            border-radius: 13px;
            padding: 8px;
            background: rgba(15, 34, 53, .4);
        }

        .bs-hero {
            padding: 25px 27px;
            border-radius: 20px;
            border: 1px solid rgba(70, 224, 232, .22);
            background:
                linear-gradient(110deg, rgba(16, 45, 67, .96), rgba(12, 27, 46, .94));
            margin: 0 0 22px 0;
        }

        .bs-eyebrow {
            color: var(--bs-cyan);
            font-size: .76rem;
            font-weight: 700;
            letter-spacing: .17em;
            text-transform: uppercase;
            margin-bottom: 9px;
        }

        .bs-title {
            color: #f3fbff;
            font-size: clamp(1.8rem, 4vw, 2.65rem);
            line-height: 1.1;
            font-weight: 750;
            margin: 0;
        }

        .bs-subtitle {
            color: #a7bbcf;
            margin-top: 10px;
            max-width: 800px;
            font-size: .98rem;
            line-height: 1.65;
        }

        .bs-status {
            display: inline-block;
            color: #9af6e7;
            border: 1px solid rgba(83, 222, 190, .3);
            background: rgba(34, 155, 130, .1);
            border-radius: 30px;
            padding: 6px 10px;
            font-size: .73rem;
            letter-spacing: .06em;
            font-weight: 650;
            margin-top: 14px;
        }

        .bs-section-label {
            color: var(--bs-muted);
            font-size: .73rem;
            letter-spacing: .15em;
            text-transform: uppercase;
            font-weight: 700;
        }

        .bs-footnote {
            color: #8298ae;
            font-size: .78rem;
            line-height: 1.6;
            border-top: 1px solid var(--bs-border);
            padding-top: 15px;
            margin-top: 28px;
        }

        @media (max-width: 700px) {
            .block-container {
                padding: 1rem .8rem 2rem .8rem;
            }
            .bs-hero {
                padding: 20px 17px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(source_label: str) -> None:
    st.markdown(
        f"""
        <section class="bs-hero">
            <div class="bs-eyebrow">Environmental intelligence platform</div>
            <h1 class="bs-title">BAARISHSENSE</h1>
            <div class="bs-subtitle">
                Explore rainfall patterns, compare locations, inspect seasonal
                behaviour and identify unusual observations through one
                integrated analytics workspace.
            </div>
            <div class="bs-status">● DATA LOADED · {source_label}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# CACHED LOCAL DATASET — ONLY THIS PATH SAVES PROCESSED DATA
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_dataset(path: str, mtime: float):
    """Load, clean, save and enrich the built-in dataset."""
    result = clean_data(data_loader.load_raw_data(Path(path)))
    save_processed(result.df)
    analytical = A.add_analytical_features(result.df, result.frequency)
    return analytical, result.quality, result.schema, result.frequency


@st.cache_data(show_spinner=False)
def load_reference(mtime_a: float, mtime_b: float):
    """Load optional map coordinates and geographic boundaries."""
    return data_loader.load_region_coordinates(), data_loader.load_geojson()


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _reset_filters() -> None:
    """Clear filter widgets while keeping the chosen data source."""
    for key in list(st.session_state.keys()):
        if key.startswith("f_"):
            del st.session_state[key]


def _show_load_error(title: str, message: str) -> None:
    st.error(title)
    st.markdown(message)
    st.info(
        "Check that your CSV has a readable date, rainfall value, "
        "and—if available—a location column."
    )


# ---------------------------------------------------------------------
# APPLICATION HEADER AND DATA SOURCE
# ---------------------------------------------------------------------
inject_dashboard_css()
ui.inject_css()
ui.render_header()

with st.sidebar:
    st.markdown("### 🌧️ BAARISHSENSE")
    st.caption("RAINFALL INTELLIGENCE WORKSPACE")
    st.divider()

    st.markdown("##### DATA SOURCE")
    dataset_mode = st.radio(
        "Choose your data",
        ["Built-in dataset", "Upload your own CSV"],
        key="dataset_mode",
    )

    uploaded_file = None
    if dataset_mode == "Upload your own CSV":
        uploaded_file = st.file_uploader(
            "Upload rainfall data",
            type=["csv"],
            key="rainfall_csv_upload",
            help=(
                "CSV files are processed in memory. "
                "Your upload is not written to the project's data folders."
            ),
        )
        st.caption(
            "Required: date + rainfall. Location is recommended. "
            "YEAR + JAN–DEC tables are also supported."
        )

source_label = "BUILT-IN DATASET"
if dataset_mode == "Upload your own CSV":
    if uploaded_file is None:
        st.markdown(
            """
            <section class="bs-hero">
                <div class="bs-eyebrow">Personal analytics workspace</div>
                <h1 class="bs-title">BAARISHSENSE</h1>
                <div class="bs-subtitle">
                    Upload a rainfall CSV to start analysing your own data.
                    Your file will be processed in memory and will not replace
                    the built-in dataset.
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.info(
            "Choose **Upload your own CSV** in the sidebar, then select your file."
        )
        ui.render_footer()
        st.stop()

    try:
        with st.spinner("Validating your uploaded rainfall data…"):
            # Read and clean in memory. Do not use save_processed() here.
            raw_uploaded = data_loader.load_uploaded_data(uploaded_file)

            # Auto-detect this file's schema rather than forcing the
            # built-in dataset's COLUMN_OVERRIDES onto another CSV.
            result = clean_data(raw_uploaded, overrides={})
            df_all = A.add_analytical_features(
                result.df, result.frequency
            )
            quality = result.quality
            schema = result.schema
            freq = result.frequency

        source_label = f"UPLOADED · {uploaded_file.name}"

    except DatasetSchemaError as exc:
        _show_load_error(
            "The uploaded CSV does not match the supported data structure.",
            f"**Details:** {ui.esc(str(exc))}",
        )
        ui.render_footer()
        st.stop()
    except Exception:
        log.exception("Uploaded dataset could not be processed")
        _show_load_error(
            "We couldn't process this uploaded file.",
            "Please confirm it is a valid CSV with readable column names and values.",
        )
        ui.render_footer()
        st.stop()

else:
    path = data_loader.find_dataset_path()
    if path is None:
        st.markdown(
            """
            <section class="bs-hero">
                <div class="bs-eyebrow">Dataset setup required</div>
                <h1 class="bs-title">BAARISHSENSE</h1>
                <div class="bs-subtitle">
                    Add your built-in rainfall CSV or switch to
                    “Upload your own CSV” in the sidebar.
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.warning("No local rainfall CSV was found in `data/raw/`.")
        st.info(
            "Place your built-in dataset in `data/raw/`, or select "
            "**Upload your own CSV** in the sidebar."
        )
        ui.render_footer()
        st.stop()

    try:
        with st.spinner("Loading and validating the rainfall dataset…"):
            df_all, quality, schema, freq = load_dataset(
                str(path), _mtime(path)
            )
    except DatasetSchemaError as exc:
        _show_load_error(
            "The built-in dataset could not be read.",
            f"**Details:** {ui.esc(str(exc))}",
        )
        ui.render_footer()
        st.stop()
    except Exception:
        log.exception("Built-in dataset load failed")
        _show_load_error(
            "The built-in dataset could not be processed.",
            "Check the CSV encoding, file structure and column configuration.",
        )
        ui.render_footer()
        st.stop()


# ---------------------------------------------------------------------
# REFERENCE GEOGRAPHY AND SIDEBAR FILTERS
# ---------------------------------------------------------------------
try:
    coords, geojson = load_reference(
        _mtime(config.REGION_COORDS_PATH),
        _mtime(config.GEOJSON_PATH),
    )
except Exception:
    log.exception("Reference geography could not be loaded")
    coords, geojson = None, None

has_state = "state" in df_all.columns
region_label = schema.region_label

with st.sidebar:
    st.divider()
    st.markdown("##### FILTERS")

    state = None
    if has_state:
        states = sorted(
            df_all["state"].dropna().astype(str).unique().tolist()
        )
        state_pick = st.selectbox(
            "State",
            ["All states"] + states,
            key="f_state",
        )
        state = None if state_pick == "All states" else state_pick

    pool = (
        df_all
        if state is None
        else df_all[df_all["state"].astype(str) == state]
    )
    region_opts = sorted(
        pool["region"].dropna().astype(str).unique().tolist()
    )
    location_pick = st.selectbox(
        f"Location ({region_label.lower()})",
        ["All regions"] + region_opts,
        key=f"f_loc_{state}",
        help="Only locations available in the selected dataset are listed.",
    )
    location = (
        None if location_pick == "All regions" else location_pick
    )

    dmin = pd.Timestamp(df_all["date"].min()).date()
    dmax = pd.Timestamp(df_all["date"].max()).date()

    date_range = st.date_input(
        "Date range",
        value=(dmin, dmax),
        min_value=dmin,
        max_value=dmax,
        key="f_dates",
    )

    years = sorted(
        int(year) for year in df_all["year"].dropna().unique()
    )
    year_pick = st.selectbox(
        "Year",
        ["All years"] + [str(year) for year in years],
        key="f_year",
    )

    month_names = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December",
    ]
    month_pick = st.selectbox(
        "Month",
        ["All months"] + month_names,
        key="f_month",
        disabled=freq == "annual",
    )
    season_pick = st.selectbox(
        "Season",
        ["All seasons"] + list(config.SEASON_MONTHS),
        key="f_season",
        disabled=freq == "annual",
        help=config.SEASON_DEFINITION_NAME,
    )

    st.button(
        "↺ Reset filters",
        on_click=_reset_filters,
        width="stretch",
    )
    st.divider()
    st.caption(f"{len(df_all):,} valid observations")
    st.caption(f"{quality['regions']:,} regions · {freq} data")

render_hero(source_label)

# ---------------------------------------------------------------------
# APPLY FILTERS
# ---------------------------------------------------------------------
if not (
    isinstance(date_range, (tuple, list))
    and len(date_range) == 2
):
    st.info("Select both a start date and an end date.")
    ui.render_footer()
    st.stop()

start, end = date_range

filter_args = {
    "states": [state] if state else None,
    "start": start,
    "end": end,
    "years": (
        [int(year_pick)] if year_pick != "All years" else None
    ),
    "months": (
        [month_names.index(month_pick) + 1]
        if month_pick != "All months"
        else None
    ),
    "seasons": (
        [season_pick] if season_pick != "All seasons" else None
    ),
}

df_context = A.apply_filters(df_all, **filter_args)
df_scope = A.apply_filters(
    df_all,
    regions=[location] if location else None,
    **filter_args,
)

active_filters = []
if state:
    active_filters.append(f"State: {state}")
if location:
    active_filters.append(f"Location: {location}")
if (start, end) != (dmin, dmax):
    active_filters.append(
        f"{start:%d %b %Y} → {end:%d %b %Y}"
    )
if year_pick != "All years":
    active_filters.append(f"Year: {year_pick}")
if month_pick != "All months":
    active_filters.append(f"Month: {month_pick}")
if season_pick != "All seasons":
    active_filters.append(f"Season: {season_pick}")

if year_pick != "All years":
    period_label = year_pick
elif not df_scope.empty:
    period_label = (
        f"{A.fmt_date(df_scope['date'].min())} to "
        f"{A.fmt_date(df_scope['date'].max())}"
    )
else:
    period_label = (
        f"{start:%d %b %Y} to {end:%d %b %Y}"
    )

if location:
    scope_label = location + (f" ({state})" if state else "")
elif state:
    scope_label = (
        f"all {df_scope['region'].nunique()} "
        f"{region_label.lower()}(s) in {state}"
        if not df_scope.empty
        else state
    )
else:
    scope_label = (
        f"all {df_scope['region'].nunique()} region(s)"
        if not df_scope.empty
        else "the selection"
    )

context_state = state
if (
    context_state is None
    and location
    and has_state
    and not df_scope.empty
):
    context_state = str(df_scope["state"].iloc[0])

ctx = Context(
    df_all=df_all,
    df_context=df_context,
    df_scope=df_scope,
    freq=freq,
    location=location,
    state=context_state,
    scope_label=scope_label,
    period_label=period_label,
    active_filters=active_filters,
    coords=coords,
    geojson=geojson,
    quality=quality,
    schema=schema,
    region_label=region_label,
)

# ---------------------------------------------------------------------
# NAVIGATION AND EXISTING ANALYTICS PAGES
# ---------------------------------------------------------------------
st.markdown('<div class="bs-section-label">ANALYTICS WORKSPACE</div>',
            unsafe_allow_html=True)

page_options = list(PAGES.keys())
page = st.segmented_control(
    "Dashboard section",
    page_options,
    default="Overview",
    key="page",
    label_visibility="collapsed",
)
page = page or "Overview"

if active_filters:
    ui.filter_chips(active_filters)

if df_scope.empty:
    st.warning(
        "No observations match these filters. Try another location, "
        "date range, year, month or season."
    )
else:
    try:
        PAGES[page](ctx)
    except Exception:
        log.exception("Page render failed: %s", page)
        st.error(
            f"The **{page}** view could not be rendered. "
            "Try changing the filters or choosing another section."
        )
        st.caption(
            "Technical details are recorded in the application log."
        )

st.markdown(
    """
    <div class="bs-footnote">
        <strong>BAARISHSENSE</strong> · Rainfall Intelligence & Environmental Analytics
        <br>
        Results depend on the quality, coverage and observation period of the
        selected dataset. Historical analysis alone is not a verified weather
        forecast or official emergency warning.
    </div>
    """,
    unsafe_allow_html=True,
)

ui.render_footer()
