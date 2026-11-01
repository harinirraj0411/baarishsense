"""RAW data layer: locate and read rainfall files. No cleaning happens here."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from . import config


def find_dataset_path() -> Path | None:
    """Return the configured rainfall CSV path, or find a CSV in data/raw/."""
    if config.RAW_DATA_PATH.is_file():
        return config.RAW_DATA_PATH

    if not config.RAW_DIR.exists():
        return None

    candidates = sorted(
        path for path in config.RAW_DIR.glob("*.csv") if path.is_file()
    )
    return candidates[0] if candidates else None


def _read_csv_with_fallback(source, filename: str) -> pd.DataFrame:
    """Read a CSV using common encodings and delimiters, without cleaning data."""
    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            if hasattr(source, "seek"):
                source.seek(0)

            df = pd.read_csv(
                source,
                encoding=encoding,
                low_memory=False,
            )

            # A single column whose header contains ; tab or | means the
            # file used a different delimiter than a comma. Re-read it.
            if df.shape[1] == 1:
                header = str(df.columns[0])
                for sep in (";", "\t", "|"):
                    if sep in header:
                        if hasattr(source, "seek"):
                            source.seek(0)
                        df = pd.read_csv(
                            source,
                            encoding=encoding,
                            sep=sep,
                            low_memory=False,
                        )
                        break

            return df

        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError as exc:
            raise ValueError(
                f"{filename} is empty or does not contain a readable CSV header."
            ) from exc
        except pd.errors.ParserError as exc:
            raise ValueError(
                f"{filename} has an invalid CSV structure. "
                "Check its delimiters, quotes, and rows."
            ) from exc

    raise ValueError(
        f"Could not decode {filename} using the supported text encodings."
    ) from last_error


def load_raw_data(path: Path) -> pd.DataFrame:
    """Read an existing CSV file without cleaning or normalising its columns."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Rainfall dataset not found: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError("Please provide a CSV file.")

    try:
        return _read_csv_with_fallback(path, path.name)
    except PermissionError as exc:
        raise ValueError(
            f"Cannot read {path.name}. Check whether another program is using it."
        ) from exc


def load_uploaded_data(uploaded_file) -> pd.DataFrame:
    """Read a Streamlit uploaded CSV directly into memory.

    The uploaded file is not saved to disk. Data cleaning belongs to
    src.data_processing, not this raw data layer.
    """
    if uploaded_file is None:
        raise ValueError("Please upload a rainfall CSV file.")

    filename = getattr(uploaded_file, "name", "uploaded_file.csv")

    if Path(filename).suffix.lower() != ".csv":
        raise ValueError("Unsupported file type. Please upload a .csv file.")

    # Streamlit UploadedFile is file-like and supports seek().
    # This keeps the uploaded contents in memory.
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)

        df = _read_csv_with_fallback(uploaded_file, filename)

    except (ValueError, pd.errors.ParserError):
        raise
    except Exception as exc:
        raise ValueError(
            f"Could not read {filename}. Please check that it is a valid CSV."
        ) from exc

    if df.empty or len(df.columns) == 0:
        raise ValueError("The uploaded CSV contains no usable data.")

    return df


def load_data(path: Path | None = None):
    """Load and clean the local dataset, returning a CleanResult."""
    from .data_processing import clean_data

    path = path or find_dataset_path()

    if path is None:
        raise FileNotFoundError(
            "No rainfall CSV found in data/raw/. "
            "Upload a dataset or add a local CSV."
        )

    return clean_data(load_raw_data(path))


def load_uploaded_dataset(uploaded_file):
    """Load and clean an uploaded CSV using the existing processing pipeline.

    overrides={} makes the cleaner auto-detect this file's columns instead of
    applying the built-in dataset's COLUMN_OVERRIDES.
    """
    from .data_processing import clean_data

    return clean_data(load_uploaded_data(uploaded_file), overrides={})


def normalise_region_key(name: str) -> str:
    """Create a normalised key for matching region names to map boundaries."""
    return re.sub(r"[^0-9a-z]+", "", str(name).lower())


def load_region_coordinates() -> pd.DataFrame | None:
    """Load optional region coordinates from the configured reference file."""
    path = config.REGION_COORDS_PATH

    if not path.is_file():
        return None

    try:
        df = pd.read_csv(path)
        df.columns = [str(column).strip().lower() for column in df.columns]

        needed = {"region", "latitude", "longitude"}
        if not needed.issubset(df.columns):
            return None

        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

        df = df.dropna(subset=["latitude", "longitude"])
        df = df[
            df["latitude"].between(-90, 90)
            & df["longitude"].between(-180, 180)
        ]

        return df[["region", "latitude", "longitude"]].drop_duplicates("region")

    except (OSError, ValueError, pd.errors.ParserError):
        return None


def load_geojson() -> dict | None:
    """Load optional boundaries and add normalised IDs to named features."""
    path = config.GEOJSON_PATH

    if not path.is_file():
        return None

    try:
        with path.open(encoding="utf-8") as file:
            geojson = json.load(file)

        features = geojson.get("features", [])
        kept = []

        for feature in features:
            properties = feature.get("properties") or {}
            name = properties.get(config.GEOJSON_NAME_PROPERTY)

            if name is None:
                continue

            feature["id"] = normalise_region_key(name)
            kept.append(feature)

        if not kept:
            return None

        geojson["features"] = kept
        return geojson

    except (OSError, ValueError, TypeError):
        return None