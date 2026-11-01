# Data dictionary

## Input: `data/raw/rainfall.csv`

BAARISHSENSE auto-detects column names (case-insensitive; spaces/punctuation become `_`). Two layouts are supported.

### Layout A - long (one row per region and date)

| Role | Required | Accepted column names (first match wins) |
|---|---|---|
| Date | yes* | date, datetime, observation_date, obs_date, timestamp, time |
| Rainfall | yes | rainfall, rainfall_mm, rain, rain_mm, precipitation, precip, prcp, rf (or any column containing "rain"/"precip") |
| Location | recommended | district, location, station, city, region, subdivision, area, place, name, state |
| State | optional | state, state_name, province |
| Latitude / Longitude | optional | latitude, lat / longitude, lon, lng |

\*Instead of a date column you may supply `year` + `month` (+ optional `day`).

Example:

```csv
date,state,district,rainfall_mm
2024-06-01,Tamil Nadu,Chennai,12.4
2024-06-01,Tamil Nadu,Thoothukudi,0.0
```

### Layout B - wide monthly (YEAR + JAN..DEC)

One row per region and year with twelve month columns (`JAN` ... `DEC`) and a `YEAR` column, plus an optional location column (e.g. `SUBDIVISION`). Extra columns such as `ANNUAL` are ignored. Rows are converted to one observation per region-month dated the 1st of the month.

If auto-detection fails, set `COLUMN_OVERRIDES` in `src/config.py`.

## Processed table (in memory; also written to `data/processed/rainfall_processed.csv`)

| Column | Meaning |
|---|---|
| date | Parsed observation date |
| region | Location name (whitespace-normalised) |
| state | State/province, if present |
| rainfall | Numeric rainfall (mm); missing/negative/non-numeric rows are excluded and counted |
| latitude, longitude | Only if present in the file |
| year, month, month_name, season | Derived from date; seasons from `SEASON_MONTHS` in config |

## Analytical table (adds)

| Column | Meaning |
|---|---|
| rolling_baseline | Trailing mean of preceding observations in the same region (30 days for daily data; 12 observations for monthly) |
| deviation_from_rolling | rainfall - rolling_baseline |
| deviation_z | deviation divided by the region's standard deviation of deviations |
| seasonal_deviation | rainfall - region's mean for the same calendar month |
| percentile_position | Percentile rank within the region's full record |

## Optional reference files (`data/reference/`)

* `region_coordinates.csv` - columns `region, latitude, longitude`. Region names must match the dataset. Use verified coordinates from a documented source.
* `regions.geojson` - boundaries; the feature property named by `GEOJSON_NAME_PROPERTY` in config must hold the region name. Enables a choropleth.
