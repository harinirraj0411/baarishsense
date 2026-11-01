"""PROCESSED data layer: schema detection, cleaning, validation, data-quality report.

Design rules
------------
* Nothing is dropped silently. Every excluded row is counted by reason and
  reported in the data-quality dictionary.
* Nothing is invented. Coordinates are used only if the file contains them.
* Supported layouts: long (one row per region/date) and the wide monthly layout
  used by many public IMD tables (YEAR + JAN..DEC columns).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config

log = logging.getLogger(__name__)

MONTH_ALIASES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

DATE_CANDIDATES = ["date", "datetime", "observation_date", "obs_date", "date_time", "timestamp", "time", "day_date"]
RAIN_CANDIDATES = ["rainfall", "rainfall_mm", "rain", "rain_mm", "precipitation", "precipitation_mm",
                   "precip", "prcp", "rf", "rainfall_mm_day", "actual_rainfall", "rainfall_actual", "actual"]
REGION_CANDIDATES = ["district", "district_name", "location", "location_name", "station", "station_name",
                     "station_id", "station_code", "site", "city",
                     "region", "subdivision", "sub_division", "meteorological_subdivision", "area", "place", "name", "state", "state_name"]
STATE_CANDIDATES = ["state", "state_name", "state_ut", "province", "st_nm"]
YEAR_CANDIDATES = ["year", "yr"]
MONTH_CANDIDATES = ["month", "mon"]
DAY_CANDIDATES = ["day", "dom"]
LAT_CANDIDATES = ["latitude", "lat"]
LON_CANDIDATES = ["longitude", "lon", "lng", "long"]

REGION_LABELS = {
    "district": "District", "district_name": "District", "location": "Location", "location_name": "Location",
    "station": "Station", "station_name": "Station", "station_id": "Station", "station_code": "Station",
    "site": "Site", "city": "City", "region": "Region", "subdivision": "Subdivision",
    "sub_division": "Subdivision", "meteorological_subdivision": "Subdivision", "area": "Area",
    "place": "Place", "name": "Location", "state": "State", "state_name": "State",
}


class DatasetSchemaError(Exception):
    """Raised when the CSV does not contain the columns BAARISHSENSE needs."""


@dataclass
class Schema:
    layout: str                      # "long" | "wide_monthly"
    rainfall_col: str | None = None
    date_col: str | None = None
    year_col: str | None = None
    month_col: str | None = None
    day_col: str | None = None
    region_col: str | None = None
    state_col: str | None = None
    lat_col: str | None = None
    lon_col: str | None = None
    month_cols: dict = field(default_factory=dict)   # {1: "jan", ...}
    region_label: str = "Region"


@dataclass
class CleanResult:
    df: pd.DataFrame
    quality: dict
    schema: Schema
    frequency: str                   # daily | monthly | annual | irregular


# ----------------------------------------------------------------------------- schema
def normalise_name(name) -> str:
    return re.sub(r"[^0-9a-z]+", "_", str(name).strip().lower()).strip("_")


def _first(cols: list[str], candidates: list[str], exclude: set[str] | None = None) -> str | None:
    exclude = exclude or set()
    for cand in candidates:
        if cand in cols and cand not in exclude:
            return cand
    return None


def detect_schema(cols: list[str], overrides: dict | None = None) -> Schema:
    """Identify date / rainfall / geography columns from normalised column names."""
    ov = {k: normalise_name(v) for k, v in (overrides or {}).items()}
    for key, col in ov.items():
        if col not in cols:
            raise DatasetSchemaError(f"COLUMN_OVERRIDES['{key}'] points to '{col}', which is not in the CSV.")

    region = ov.get("region") or _first(cols, REGION_CANDIDATES)
    state = ov.get("state") or _first(cols, STATE_CANDIDATES, exclude={region} if region else None)
    lat, lon = _first(cols, LAT_CANDIDATES), _first(cols, LON_CANDIDATES)
    region_label = REGION_LABELS.get(region or "", "Region")
    geo = dict(region_col=region, state_col=state, lat_col=lat, lon_col=lon, region_label=region_label)

    # Wide monthly layout: YEAR + twelve month columns
    month_cols = {}
    for c in cols:
        if c in MONTH_ALIASES and MONTH_ALIASES[c] not in month_cols:
            month_cols[MONTH_ALIASES[c]] = c
    year = ov.get("year") or _first(cols, YEAR_CANDIDATES)
    if len(month_cols) == 12 and year and "rainfall" not in ov:
        return Schema(layout="wide_monthly", year_col=year, month_cols=month_cols, **geo)

    # Long layout
    rain = ov.get("rainfall") or _first(cols, RAIN_CANDIDATES)
    if rain is None:
        fuzzy = [c for c in cols if "rain" in c or "precip" in c]
        rain = fuzzy[0] if fuzzy else None
    date = ov.get("date") or _first(cols, DATE_CANDIDATES)
    month = ov.get("month") or _first(cols, MONTH_CANDIDATES)
    day = ov.get("day") or _first(cols, DAY_CANDIDATES)

    problems = []
    if rain is None:
        problems.append("a rainfall column (e.g. 'rainfall_mm')")
    if date is None and not (year and month):
        problems.append("a date column (e.g. 'date') or year + month columns")
    if problems:
        raise DatasetSchemaError(
            "The CSV is missing " + " and ".join(problems) + ". Columns found: " + ", ".join(cols[:25])
            + (" ..." if len(cols) > 25 else "")
        )
    return Schema(layout="long", rainfall_col=rain, date_col=date, year_col=year,
                  month_col=month, day_col=day, **geo)


# ----------------------------------------------------------------------------- parsing
def parse_dates(series: pd.Series) -> pd.Series:
    """Parse mixed-format dates; ISO first, then pick day-first vs month-first by yield."""
    s = series.astype("string").str.strip()
    out = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    rest = out.isna() & s.notna()
    if rest.any():
        sub = s[rest]
        cand_a = pd.to_datetime(sub, errors="coerce", dayfirst=True, format="mixed")
        cand_b = pd.to_datetime(sub, errors="coerce", dayfirst=False, format="mixed")
        out[rest] = cand_a if cand_a.notna().sum() >= cand_b.notna().sum() else cand_b
    return out


def to_rainfall_numbers(series: pd.Series) -> pd.Series:
    """Convert rainfall values to float, accepting text such as '1,234.5'.

    Values that still cannot be read become NaN and are counted as
    non-numeric by clean_data().
    """
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").astype("float64")
    text = series.astype("string").str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="coerce").astype("float64")


def _melt_wide(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    keep = [c for c in (schema.year_col, schema.region_col, schema.state_col, schema.lat_col, schema.lon_col) if c]
    long = df.melt(id_vars=list(dict.fromkeys(keep)), value_vars=list(schema.month_cols.values()),
                   var_name="_month_col", value_name="_rain_raw")
    inv = {v: k for k, v in schema.month_cols.items()}
    month = long["_month_col"].map(inv)
    year = pd.to_numeric(long[schema.year_col], errors="coerce")
    date = pd.to_datetime(pd.DataFrame({"year": year, "month": month, "day": 1}), errors="coerce")
    return _assemble(long, date, long["_rain_raw"], schema)


def _assemble(frame: pd.DataFrame, date: pd.Series, rain_raw: pd.Series, schema: Schema) -> pd.DataFrame:
    out = pd.DataFrame({"date": date.values, "rainfall_raw": rain_raw.values}, index=frame.index)
    out["region"] = frame[schema.region_col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True) \
        if schema.region_col else "All records"
    if schema.state_col:
        out["state"] = frame[schema.state_col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    if schema.lat_col and schema.lon_col:
        out["latitude"] = pd.to_numeric(frame[schema.lat_col], errors="coerce")
        out["longitude"] = pd.to_numeric(frame[schema.lon_col], errors="coerce")
    return out


def _build_long(df: pd.DataFrame, schema: Schema) -> pd.DataFrame:
    if schema.date_col:
        date = parse_dates(df[schema.date_col])
    else:
        y = pd.to_numeric(df[schema.year_col], errors="coerce")
        m = df[schema.month_col]
        # Text months ("Jan", "June") are mapped to numbers. Checking for a
        # numeric dtype works on every pandas version, unlike dtype == object.
        if not pd.api.types.is_numeric_dtype(m):
            m = m.map(lambda v: MONTH_ALIASES.get(normalise_name(v), v))
        m = pd.to_numeric(m, errors="coerce")
        d = pd.to_numeric(df[schema.day_col], errors="coerce") if schema.day_col else 1
        date = pd.to_datetime(pd.DataFrame({"year": y, "month": m, "day": d}), errors="coerce")
    return _assemble(df, date, df[schema.rainfall_col], schema)


# ----------------------------------------------------------------------------- features
def season_for_month(month: int) -> str | None:
    for name, months in config.SEASON_MONTHS.items():
        if month in months:
            return name
    return None


def detect_frequency(df: pd.DataFrame) -> str:
    """Native temporal resolution from the median gap between consecutive observations."""
    if df.empty:
        return "irregular"
    d = df[["region", "date"]].sort_values(["region", "date"])
    gaps = d.groupby("region", observed=True)["date"].diff().dt.days.dropna()
    if gaps.empty:
        return "irregular"
    med = float(gaps.groupby(d["region"].loc[gaps.index], observed=True).median().median())
    if med <= 1.5:
        return "daily"
    if 27 <= med <= 32:
        return "monthly"
    if med >= 360:
        return "annual"
    return "irregular"


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df["year"] = df["date"].dt.year.astype("int16")
    df["month"] = df["date"].dt.month.astype("int8")
    df["month_name"] = pd.Categorical.from_codes(df["month"].to_numpy() - 1, categories=MONTH_NAMES, ordered=True)
    season_map = {m: season_for_month(m) for m in range(1, 13)}
    season_order = list(config.SEASON_MONTHS.keys())
    df["season"] = pd.Categorical(df["month"].map(season_map), categories=season_order, ordered=True)
    return df


# ----------------------------------------------------------------------------- cleaning
def clean_data(raw: pd.DataFrame, overrides: dict | None = None) -> CleanResult:
    """RAW -> PROCESSED. Returns the processed table plus a full quality report."""
    notes: list[str] = []
    df = raw.copy()
    df.columns = [normalise_name(c) for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).duplicated()]
    schema = detect_schema(list(df.columns), overrides if overrides is not None else config.COLUMN_OVERRIDES)

    if schema.region_col is None:
        notes.append("No geographic column found - all rows are treated as one region ('All records').")
    if schema.layout == "wide_monthly":
        notes.append("Wide monthly layout detected (YEAR + 12 month columns); converted to one row per region-month.")
        work = _melt_wide(df, schema)
        rainfall_field = "JAN-DEC columns"
    else:
        work = _build_long(df, schema)
        rainfall_field = schema.rainfall_col

    total_records = int(len(work))
    rain_num = to_rainfall_numbers(work["rainfall_raw"])
    missing = int(work["rainfall_raw"].isna().sum())
    non_numeric = int((work["rainfall_raw"].notna() & rain_num.isna()).sum())
    negative = int((rain_num < 0).sum())
    rain_num = rain_num.where(rain_num >= 0)
    bad_date = work["date"].isna()
    bad_region = work["region"].isna() | (work["region"].astype("string").str.len() == 0)

    valid_mask = rain_num.notna() & ~bad_date & ~bad_region
    work = work.assign(rainfall=rain_num).loc[valid_mask].drop(columns=["rainfall_raw"])
    excluded = total_records - int(valid_mask.sum())

    before = len(work)
    work = work.drop_duplicates(subset=["region", "date"], keep="first")
    duplicates_removed = before - len(work)

    if duplicates_removed and schema.region_col is None:
        notes.append(
            f"{duplicates_removed:,} rows shared a date and were dropped because no "
            "location column was recognised. Rename your station/district column to "
            "'station' or 'district' if the file has several locations."
        )

    work["region"] = work["region"].astype("category")
    if "state" in work:
        work["state"] = work["state"].fillna("Unspecified").astype("category")
    work = work.sort_values(["region", "date"]).reset_index(drop=True)
    work = add_time_features(work)
    frequency = detect_frequency(work)

    if total_records and excluded / total_records > 0.05:
        notes.append(f"{excluded / total_records:.1%} of records were excluded - review the source file.")
    if "latitude" in work:
        notes.append("Latitude/longitude columns found and will be used for the geographic map.")

    quality = {
        "total_records": total_records,
        "valid_records": int(len(work)),
        "excluded_records": int(excluded),
        "missing_rainfall": missing,
        "non_numeric_rainfall": non_numeric,
        "negative_rainfall": negative,
        "invalid_dates": int(bad_date.sum()),
        "missing_region": int(bad_region.sum()),
        "duplicates_removed": int(duplicates_removed),
        "regions": int(work["region"].nunique()) if len(work) else 0,
        "date_min": work["date"].min() if len(work) else None,
        "date_max": work["date"].max() if len(work) else None,
        "last_observation": work["date"].max() if len(work) else None,
        "rainfall_field": rainfall_field,
        "region_field": schema.region_col or "(none)",
        "state_field": schema.state_col or "(none)",
        "layout": schema.layout,
        "frequency": frequency,
        "notes": notes,
    }
    if work.empty:
        raise DatasetSchemaError("No valid rainfall observations remain after validation. Check dates and rainfall values.")
    return CleanResult(df=work, quality=quality, schema=schema, frequency=frequency)


def save_processed(df: pd.DataFrame) -> None:
    """Best-effort write of the processed table (data/processed/). Failure is non-fatal."""
    try:
        config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(config.PROCESSED_DIR / "rainfall_processed.csv", index=False)
    except OSError as exc:
        log.warning("Could not write processed data: %s", exc)