# BAARISHSENSE

**Rainfall Intelligence & Environmental Analytics**

> India-focused rainfall intelligence and environmental analytics dashboard built with Python, Streamlit, Pandas and Plotly.

BAARISHSENSE is an independent analytics project. It is not an official weather service, government system, flood-warning authority or validated flood-prediction model.

## Overview
An interactive dashboard for exploring public rainfall data: national overview, location drill-down, regional comparison, seasonal analysis, statistical screening of unusually high rainfall observations, and a deviation view. Every number is computed from the dataset you supply.

## Problem statement
Public rainfall tables are large and hard to inspect quickly. Analysts need to move from a national picture to a single location, compare regions, see seasonal structure, and understand why an observation stands out - while keeping data quality visible.

## Objectives
* Build a reproducible pipeline: raw CSV -> validated table -> analytical metrics.
* Provide transparent, explainable statistics (every flagged observation can be explained).
* Keep the project honest: report excluded data, never invent coordinates, sources or results.

## Features
* **Overview**: KPIs, regional map (when geography is available), ranking, trend, distribution, event preview
* **Location search**: only locations present in the dataset; State -> Location -> Year -> Month -> Season filters and date range
* **Trend**: daily / monthly / annual aggregation, moving average, zoom and range selector
* **Compare**: 2-8 regions; totals, averages, maxima, variability, seasonal pattern, year-over-year; top and lowest rankings
* **Seasonal Intelligence**: monthly profile with contribution, year x month heatmap, seasonal totals
* **High-Rainfall Event Screening**: P90 / P95 / P99 or fixed threshold, sortable event table, "Why was this flagged?" explanation
* **Anomaly view**: rolling-baseline deviation, z-score, seasonal deviation, percentile position (with methodology)
* **Data quality + source panels**, deterministic analytical summaries, CSV/TXT downloads
* Polished empty, error and missing-dataset states; cached loading

## Architecture
```
app.py                 entry point: loading, sidebar filters, navigation
src/config.py          paths, source metadata, season definition
src/data_loader.py     RAW layer (read CSV, optional coordinates / GeoJSON)
src/data_processing.py PROCESSED layer (schema detection, cleaning, quality report)
src/analytics.py       ANALYTICAL layer (statistics, thresholds, summaries)
src/visualizations.py  Plotly figures + shared dark theme
src/ui_components.py   CSS theme and HTML components
src/pages.py           page renderers
tests/                 pytest unit tests
docs/                  methodology and data dictionary
```

## Technology stack
Python 3.11+, Streamlit, Pandas, NumPy, Plotly (maps via Plotly's map traces), pytest, Git.

## Data source
Place a verified public rainfall CSV at `data/raw/rainfall.csv` (India Meteorological Department / Government of India open data are preferred sources). **No dataset is bundled and no source URL is assumed.** Record yours in `src/config.py` (`DATASET_NAME`, `SOURCE_ORGANIZATION`, `SOURCE_URL`, `SOURCE_ACCESSED_ON`); until then the app shows "NOT CONFIGURED". Check the publisher's licence before committing the data to GitHub.

Accepted formats are described in [docs/data_dictionary.md](docs/data_dictionary.md): a long table (`date`, `rainfall`, location, optional state/lat/lon) or a wide YEAR + JAN-DEC table.

## Data processing
Column detection, date parsing, numeric conversion, exclusion of missing / non-numeric / negative / invalid-date rows, duplicate removal, derived year/month/season, rolling metrics. All exclusions are counted in the Data Quality panel. Details: [docs/methodology.md](docs/methodology.md).

## Analytics methodology
Percentile or fixed-threshold screening, rolling-baseline deviation, monthly/seasonal aggregation, year-over-year change on complete years only. High-rainfall screening identifies statistically unusual observations **within the selected data**; it does not predict floods.

## Dashboard screenshots
Capture your own after loading real data - see [screenshots/README.md](screenshots/README.md).

## Installation
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Running locally
```bash
streamlit run app.py
pytest            # optional: run unit tests
```

## Project limitations
* Maps require coordinates in the CSV, `data/reference/region_coordinates.csv`, or a GeoJSON boundary file; none are bundled.
* Aggregates assume comparable regions; uneven coverage is flagged, not corrected.
* Seasons follow a conventional definition that may not fit every region.
* Rolling baselines assume reasonably regular sampling.
* Not validated for operational or safety use.

## Future improvements
Gridded data ingestion, station-quality flags, exceedance-return-period estimates, optional satellite-derived precipitation as a *separate, clearly labelled* data source, report export.

## Author
Harini R - M.Sc. Computer Science.
