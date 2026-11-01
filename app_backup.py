"""BAARISHSENSE - Rainfall Intelligence & Environmental Analytics (Streamlit entry point)."""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

st.set_page_config(page_title="BAARISHSENSE \u2022 Rainfall Intelligence", layout="wide", initial_sidebar_state="expanded")

from src import analytics as A  # noqa: E402
from src import config, data_loader, ui_components as ui  # noqa: E402
from src.data_processing import DatasetSchemaError, clean_data, save_processed  # noqa: E402
from src.pages import (Context, render_anomaly, render_compare, render_data, render_events,  # noqa: E402
                       render_location, render_overview, render_seasonal)

log = logging.getLogger("BAARISHSENSE")
PAGES = {"Overview": render_overview, "Location": render_location, "Compare": render_compare,
         "Seasonal": render_seasonal, "Event screening": render_events, "Anomaly view": render_anomaly,
         "Data & methodology": render_data}


@st.cache_data(show_spinner=False)
def load_dataset(path: str, mtime: float):
    """RAW -> PROCESSED -> ANALYTICAL, cached on file path + modification time."""
    from pathlib import Path
    res = clean_data(data_loader.load_raw_data(Path(path)))
    save_processed(res.df)
    analytical = A.add_analytical_features(res.df, res.frequency)
    return analytical, res.quality, res.schema, res.frequency


@st.cache_data(show_spinner=False)
def load_reference(mtime_a: float, mtime_b: float):
    return data_loader.load_region_coordinates(), data_loader.load_geojson()


def _mtime(p) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _reset_filters() -> None:
    for k in [k for k in st.session_state if k.startswith("f_")]:
        del st.session_state[k]


ui.inject_css()
ui.render_header()

path = data_loader.find_dataset_path()
if path is None:
    ui.state_card("DATASET NOT FOUND", "<p>Place the rainfall CSV inside:</p><p><code>data/raw/</code></p>"
                  "<p>Name it <code>rainfall.csv</code>. Required columns: a date, a rainfall value and a location "
                  "(or a YEAR + JAN\u2013DEC table). See README.md for details.</p>")
    ui.render_footer()
    st.stop()

try:
    with st.spinner("Loading and validating dataset\u2026"):
        df_all, quality, schema, freq = load_dataset(str(path), _mtime(path))
except DatasetSchemaError as exc:
    ui.state_card("DATASET COULD NOT BE READ", f"<p>{ui.esc(exc)}</p><p>Check the column requirements in README.md "
                  "or set <code>COLUMN_OVERRIDES</code> in <code>src/config.py</code>.</p>")
    ui.render_footer()
    st.stop()
except Exception:  # never show raw tracebacks
    log.exception("Dataset load failed")
    ui.state_card("DATASET COULD NOT BE PROCESSED", "<p>The file could not be read as a CSV. Confirm it is a valid, "
                  "UTF-8 or Latin-1 encoded CSV and try again.</p>")
    ui.render_footer()
    st.stop()

coords, geojson = load_reference(_mtime(config.REGION_COORDS_PATH), _mtime(config.GEOJSON_PATH))
has_state = "state" in df_all
region_label = schema.region_label

# ------------------------------------------------------------------ sidebar filters
with st.sidebar:
    st.markdown("##### FILTERS")
    state = None
    if has_state:
        states = sorted(df_all["state"].astype(str).unique())
        pick = st.selectbox("State", ["All states"] + states, key="f_state")
        state = None if pick == "All states" else pick
    pool = df_all if state is None else df_all[df_all["state"] == state]
    region_opts = sorted(pool["region"].astype(str).unique())
    loc_pick = st.selectbox(f"Search location ({region_label.lower()})", ["All regions"] + region_opts,
                            key=f"f_loc_{state}", help="Type to search. Only locations present in the dataset are listed.")
    location = None if loc_pick == "All regions" else loc_pick

    dmin, dmax = df_all["date"].min().date(), df_all["date"].max().date()
    drange = st.date_input("Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax, key="f_dates")
    years = sorted(df_all["year"].unique().tolist())
    year_pick = st.selectbox("Year", ["All years"] + [str(y) for y in years], key="f_year")
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    month_pick = st.selectbox("Month", ["All months"] + month_names, key="f_month",
                              disabled=freq == "annual")
    season_pick = st.selectbox("Season", ["All seasons"] + list(config.SEASON_MONTHS), key="f_season",
                               disabled=freq == "annual", help=config.SEASON_DEFINITION_NAME)
    st.button("Reset filters", on_click=_reset_filters, width="stretch")
    st.caption(f"{len(df_all):,} valid observations \u2022 {quality['regions']} regions \u2022 {freq} data")

if not (isinstance(drange, (tuple, list)) and len(drange) == 2):
    st.info("Select an end date to apply the date range.")
    st.stop()
start, end = drange

kw = dict(states=[state] if state else None, start=start, end=end,
          years=[int(year_pick)] if year_pick != "All years" else None,
          months=[month_names.index(month_pick) + 1] if month_pick != "All months" else None,
          seasons=[season_pick] if season_pick != "All seasons" else None)
df_context = A.apply_filters(df_all, **kw)
df_scope = A.apply_filters(df_all, regions=[location] if location else None, **kw)

active = []
if state:
    active.append(f"State: {state}")
if location:
    active.append(f"Location: {location}")
if (start, end) != (dmin, dmax):
    active.append(f"{start:%d %b %Y} \u2192 {end:%d %b %Y}")
if year_pick != "All years":
    active.append(f"Year: {year_pick}")
if month_pick != "All months":
    active.append(f"Month: {month_pick}")
if season_pick != "All seasons":
    active.append(f"Season: {season_pick}")

if year_pick != "All years":
    period_label = year_pick
elif not df_scope.empty:
    period_label = f"{A.fmt_date(df_scope['date'].min())} to {A.fmt_date(df_scope['date'].max())}"
else:
    period_label = f"{start:%d %b %Y} to {end:%d %b %Y}"
if location:
    scope_label = location + (f" ({state})" if state else "")
elif state:
    scope_label = f"all {df_scope['region'].nunique()} {region_label.lower()}(s) in {state}" if not df_scope.empty else state
else:
    scope_label = f"all {df_scope['region'].nunique()} region(s)" if not df_scope.empty else "the selection"

ctx = Context(df_all=df_all, df_context=df_context, df_scope=df_scope, freq=freq, location=location,
              state=state or (str(df_scope["state"].iloc[0]) if location and has_state and not df_scope.empty else None),
              scope_label=scope_label, period_label=period_label, active_filters=active, coords=coords, geojson=geojson,
              quality=quality, schema=schema, region_label=region_label)

# ------------------------------------------------------------------ navigation + page
page = st.segmented_control("Section", list(PAGES), default="Overview", key="page", label_visibility="collapsed")
page = page or "Overview"
ui.filter_chips(active)
try:
    PAGES[page](ctx)
except Exception:
    log.exception("Page render failed: %s", page)
    ui.state_card("THIS VIEW COULD NOT BE RENDERED", "<p>Try changing the filters or reloading the page. "
                  "Details were written to the application log.</p>")
ui.render_footer()
