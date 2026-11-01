"""Central configuration for BAARISHSENSE.

Edit this file to describe YOUR dataset. Nothing here is fetched from the
network, and no value is claimed to be verified until you verify it.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

# Input dataset. Override with the BAARISHSENSE_DATA environment variable if needed.
RAW_DATA_PATH = Path(os.environ.get("BAARISHSENSE_DATA", RAW_DIR / "rainfall.csv"))

# Optional geographic references (never shipped with the repo, never invented).
#   region_coordinates.csv : columns  region, latitude, longitude
#   regions.geojson        : boundary file whose feature property below holds the region name
REGION_COORDS_PATH = REFERENCE_DIR / "region_coordinates.csv"
GEOJSON_PATH = REFERENCE_DIR / "regions.geojson"
GEOJSON_NAME_PROPERTY = "NAME"

# --- Data source metadata (shown in the Data Source & Methodology panel) -------
# Leave blank until you have verified them. Blank values are displayed as
# "NOT CONFIGURED" - the app never invents a source.
DATASET_NAME = ""
SOURCE_ORGANIZATION = ""   # e.g. the organisation that published your file
SOURCE_URL = ""            # paste the verified download/landing page URL here
SOURCE_ACCESSED_ON = ""    # e.g. "2026-07-15"

# --- Units and thresholds ------------------------------------------------------
RAINFALL_UNIT = "mm"
WET_OBSERVATION_MM = 0.1   # observations >= this count as "wet" for percentile thresholds

# Optional manual column mapping if auto-detection fails, e.g.
# COLUMN_OVERRIDES = {"date": "obs_date", "rainfall": "rf_mm", "region": "district", "state": "state_name"}
    
COLUMN_OVERRIDES: dict[str, str] = {
    "date": "Date",
    "rainfall": "Daily Actual",
    "region": "District",
    "state": "State",
}


# --- Season definition ---------------------------------------------------------
# Conventional India Meteorological Department (IMD) four-season split.
# Edit if your analysis needs a different definition.
SEASON_DEFINITION_NAME = "Conventional IMD seasons (calendar months)"
SEASON_MONTHS: dict[str, list[int]] = {
    "Winter": [1, 2],
    "Pre-monsoon": [3, 4, 5],
    "Southwest monsoon": [6, 7, 8, 9],
    "Post-monsoon": [10, 11, 12],
}

# --- Presentation --------------------------------------------------------------
APP_NAME = "BAARISHSENSE"
APP_TAGLINE = "RAINFALL INTELLIGENCE & ENVIRONMENTAL ANALYTICS"
APP_META = "INDIA  \u2022  METEOROLOGICAL DATA  \u2022  ANALYTICS PLATFORM"
FOOTER_TEXT = "BAARISHSENSE \u2022 Independent Environmental Analytics Project"
