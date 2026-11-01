"""Unit tests. Fixtures are tiny hand-built tables - test data only, not real rainfall."""
import numpy as np
import pandas as pd
import pytest

from src import analytics as A
from src.data_processing import DatasetSchemaError, clean_data, detect_schema


def _long(rows):
    return pd.DataFrame(rows, columns=["Date", "District", "Rainfall_mm"])


def test_clean_reports_every_exclusion():
    raw = _long([("2020-01-01", "X", 1.0), ("2020-01-02", "X", -5), ("2020-01-03", "X", None),
                 ("not a date", "X", 2.0), ("2020-01-01", "X", 9.0), ("2020-01-04", "X", "abc")])
    res = clean_data(raw)
    q = res.quality
    assert q["total_records"] == 6
    assert q["negative_rainfall"] == 1 and q["missing_rainfall"] == 1
    assert q["non_numeric_rainfall"] == 1 and q["invalid_dates"] == 1
    assert q["duplicates_removed"] == 1
    assert q["valid_records"] == 1


def test_wide_monthly_layout_detected_and_melted():
    cols = ["SUBDIVISION", "YEAR"] + ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    raw = pd.DataFrame([["A", 2000] + list(range(12))], columns=cols)
    res = clean_data(raw)
    assert res.frequency == "irregular" or len(res.df) == 12
    assert len(res.df) == 12 and res.schema.layout == "wide_monthly"


def test_missing_rainfall_column_raises_clear_error():
    with pytest.raises(DatasetSchemaError):
        detect_schema(["date", "district", "humidity"])


def test_percentile_threshold_and_events():
    vals = np.arange(1, 101, dtype=float)
    thr = A.calculate_percentile_threshold(vals, "P95", wet_only=False)
    assert thr["threshold"] == pytest.approx(np.percentile(vals, 95))
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=100), "region": "X", "rainfall": vals})
    ev = A.detect_high_rainfall_events(df, thr["threshold"])
    assert (ev["rainfall"] > thr["threshold"]).all() and len(ev) == 5
    assert ev.iloc[0]["rainfall"] == 100


def test_fixed_threshold_and_explanation_uses_actual_values():
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "region": "X", "rainfall": [10.0, 50.0, 100.0]})
    thr = A.calculate_percentile_threshold(df["rainfall"], "FIXED", fixed_value=40)
    ev = A.detect_high_rainfall_events(df, thr["threshold"])
    info = A.explain_event(ev.iloc[0], "daily")
    assert info["rainfall"].startswith("100.0") and info["relative"].startswith("2.50")


def test_year_over_year_only_between_complete_years():
    d1 = pd.date_range("2019-01-01", "2019-12-31")
    d2 = pd.date_range("2020-01-01", "2020-03-01")          # partial year
    df = pd.DataFrame({"date": d1.append(d2), "region": "X"})
    df["rainfall"] = 1.0
    df["year"] = df["date"].dt.year
    out = A.calculate_year_over_year_change(df, "daily")
    assert out.loc[out["year"] == 2020, "complete"].item() is False or not out.loc[out["year"] == 2020, "complete"].item()
    assert np.isnan(out.loc[out["year"] == 2020, "yoy_pct"].item())
