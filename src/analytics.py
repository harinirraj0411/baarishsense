"""ANALYTICAL layer: deterministic, dataset-driven calculations and summaries.

Every number shown in the dashboard is produced here from the loaded data.
Summaries are plain Python string templates - no language model is involved.
"""
from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

from . import config

FREQ_RANK = {"daily": 0, "monthly": 1, "annual": 2}
THRESHOLD_METHODS = {"P90": 90, "P95": 95, "P99": 99}


# ----------------------------------------------------------------------------- labels
def unit_label(freq: str) -> str:
    return {"daily": f"{config.RAINFALL_UNIT}/day", "monthly": f"{config.RAINFALL_UNIT}/month",
            "annual": f"{config.RAINFALL_UNIT}/year"}.get(freq, config.RAINFALL_UNIT)


def observation_noun(freq: str, plural: bool = True) -> str:
    base = {"daily": "day", "monthly": "month", "annual": "year"}.get(freq, "period")
    return base + ("s" if plural else "")


def available_aggregations(freq: str) -> list[str]:
    """Aggregation levels no finer than the dataset's native resolution."""
    if freq in FREQ_RANK:
        return [a for a, r in (("Daily", 0), ("Monthly", 1), ("Annual", 2)) if r >= FREQ_RANK[freq]]
    return ["Monthly", "Annual"]


def fmt_date(ts) -> str:
    return pd.Timestamp(ts).strftime("%d %b %Y")


def fmt_mm(v: float, digits: int = 1) -> str:
    return f"{v:,.{digits}f} {config.RAINFALL_UNIT}"


# ----------------------------------------------------------------------------- filtering
def apply_filters(df: pd.DataFrame, *, states=None, regions=None, start=None, end=None,
                  years=None, months=None, seasons=None) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if states and "state" in df:
        mask &= df["state"].isin(states)
    if regions:
        mask &= df["region"].isin(regions)
    if start is not None:
        mask &= df["date"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["date"] <= pd.Timestamp(end)
    if years:
        mask &= df["year"].isin(years)
    if months:
        mask &= df["month"].isin(months)
    if seasons:
        mask &= df["season"].isin(seasons)
    return df.loc[mask]


# ----------------------------------------------------------------------------- headline stats
def get_summary_statistics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    rain = df["rainfall"]
    imax = rain.idxmax()
    by_region = df.groupby("region", observed=True)["rainfall"].agg(["sum", "mean", "count"])
    wettest = by_region["sum"].idxmax()
    return {
        "total": float(rain.sum()),
        "mean": float(rain.mean()),
        "maximum": float(rain.max()),
        "max_date": df.at[imax, "date"],
        "max_region": str(df.at[imax, "region"]),
        "wettest_region": str(wettest),
        "wettest_total": float(by_region.loc[wettest, "sum"]),
        "obs_periods": int(df["date"].nunique()),
        "n_records": int(len(df)),
        "n_regions": int(len(by_region)),
        "uneven_coverage": bool(by_region["count"].max() > 1.1 * by_region["count"].min()) if len(by_region) > 1 else False,
    }


def calculate_regional_summary(df: pd.DataFrame, coords: pd.DataFrame | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("region", observed=True)["rainfall"]
    out = g.agg(total="sum", average="mean", maximum="max", std="std", observations="count").reset_index()
    out["std"] = out["std"].fillna(0.0)
    out["variability_cv"] = np.where(out["average"] > 0, out["std"] / out["average"], np.nan)
    if "state" in df:
        out = out.merge(df.groupby("region", observed=True)["state"].first().reset_index(), on="region", how="left")
    if "latitude" in df:
        ll = df.groupby("region", observed=True)[["latitude", "longitude"]].median().reset_index()
        out = out.merge(ll, on="region", how="left")
    elif coords is not None and not coords.empty:
        out = out.merge(coords, on="region", how="left")
    out["region"] = out["region"].astype(str)
    return out.sort_values("total", ascending=False).reset_index(drop=True)


# ----------------------------------------------------------------------------- trend
def _period_key(dates: pd.Series, freq: str) -> pd.Series:
    # Falls back to monthly for any resolution that is not daily/monthly/annual,
    # so an unusual uploaded file cannot raise a KeyError here.
    code = {"daily": "D", "monthly": "M", "annual": "Y"}.get(freq, "M")
    return dates.dt.to_period(code).dt.to_timestamp()


def calculate_rainfall_trend(df: pd.DataFrame, agg: str = "daily") -> pd.DataFrame:
    """Per-region period totals, averaged across regions when more than one is selected."""
    if df.empty:
        return pd.DataFrame(columns=["period", "rainfall", "observations", "regions"])
    key = _period_key(df["date"], agg.lower())
    tmp = pd.DataFrame({"region": df["region"], "period": key, "rainfall": df["rainfall"]})
    per_region = tmp.groupby(["region", "period"], observed=True)["rainfall"].agg(["sum", "count"]).reset_index()
    out = per_region.groupby("period").agg(rainfall=("sum", "mean"), observations=("count", "sum"),
                                           regions=("region", "nunique")).reset_index()
    return out


def calculate_rolling_average(trend: pd.DataFrame, window: int) -> pd.DataFrame:
    out = trend.copy()
    out["moving_average"] = out["rainfall"].rolling(window, min_periods=max(1, window // 2)).mean()
    return out


# ----------------------------------------------------------------------------- monthly / seasonal
def calculate_monthly_rainfall(df: pd.DataFrame) -> pd.DataFrame:
    """Typical rainfall by calendar month (mean of yearly month totals)."""
    if df.empty:
        return pd.DataFrame()
    rym = df.groupby(["region", "year", "month"], observed=True)["rainfall"].sum().reset_index()
    ym = rym.groupby(["year", "month"])["rainfall"].mean().reset_index()
    out = ym.groupby("month")["rainfall"].agg(mean_total="mean", std="std", minimum="min", maximum="max",
                                              n_years="count").reset_index()
    out["std"] = out["std"].fillna(0.0)
    out["month_name"] = out["month"].map(lambda m: calendar.month_name[int(m)])
    total = out["mean_total"].sum()
    out["contribution_pct"] = out["mean_total"] / total * 100 if total > 0 else 0.0
    return out


def calculate_month_year_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Year x month totals (mean across regions) for the heatmap."""
    if df.empty:
        return pd.DataFrame()
    rym = df.groupby(["region", "year", "month"], observed=True)["rainfall"].sum().reset_index()
    ym = rym.groupby(["year", "month"])["rainfall"].mean().reset_index()
    return ym.pivot(index="year", columns="month", values="rainfall").reindex(columns=range(1, 13))


def calculate_seasonal_rainfall(df: pd.DataFrame) -> pd.DataFrame:
    """Season total per year (mean across regions if several)."""
    if df.empty:
        return pd.DataFrame()
    rys = df.groupby(["region", "year", "season"], observed=True)["rainfall"].sum().reset_index()
    return rys.groupby(["year", "season"], observed=True)["rainfall"].mean().reset_index()


def calculate_seasonal_summary(season_year: pd.DataFrame) -> pd.DataFrame:
    if season_year.empty:
        return pd.DataFrame()
    g = season_year.groupby("season", observed=True)["rainfall"]
    out = g.agg(mean_total="mean", std="std", years="count").reset_index()
    out["std"] = out["std"].fillna(0.0)
    tot = out["mean_total"].sum()
    out["share_pct"] = out["mean_total"] / tot * 100 if tot > 0 else 0.0
    idx_hi = season_year.groupby("season", observed=True)["rainfall"].idxmax()
    idx_lo = season_year.groupby("season", observed=True)["rainfall"].idxmin()
    out["wettest_year"] = out["season"].map(lambda s: int(season_year.loc[idx_hi[s], "year"]))
    out["driest_year"] = out["season"].map(lambda s: int(season_year.loc[idx_lo[s], "year"]))
    out["season"] = out["season"].astype(str)
    return out


# ----------------------------------------------------------------------------- year over year
def _expected_obs(year: int, freq: str):
    if freq == "daily":
        return 366 if calendar.isleap(int(year)) else 365
    if freq == "monthly":
        return 12
    if freq == "annual":
        return 1
    return None


def calculate_annual_by_region(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["region", "year", "rainfall", "observations", "coverage"])
    out = df.groupby(["region", "year"], observed=True)["rainfall"].agg(rainfall="sum", observations="count").reset_index()
    exp = out["year"].map(lambda y: _expected_obs(y, freq))
    if exp.isna().any():
        # Irregular resolution (for example weekly or 10-day data): there is no
        # fixed expected count, so the fullest region-year is the reference.
        # Partial years are then flagged instead of being assumed complete.
        ref = out["observations"].max()
        out["coverage"] = out["observations"] / ref if ref > 0 else 1.0
    else:
        out["coverage"] = out["observations"] / exp
    out["region"] = out["region"].astype(str)
    return out


def calculate_year_over_year_change(df: pd.DataFrame, freq: str, min_coverage: float = 0.9) -> pd.DataFrame:
    """Annual totals with YoY change. Change is computed only between consecutive, well-covered years."""
    ann = calculate_annual_by_region(df, freq)
    if ann.empty:
        return pd.DataFrame(columns=["year", "rainfall", "coverage", "complete", "yoy_abs", "yoy_pct"])
    out = ann.groupby("year").agg(rainfall=("rainfall", "mean"), coverage=("coverage", "mean")).reset_index()
    out["complete"] = out["coverage"] >= min_coverage
    prev = out["rainfall"].shift(1)
    ok = out["complete"] & out["complete"].shift(1, fill_value=False) & (out["year"].diff() == 1)
    out["yoy_abs"] = np.where(ok, out["rainfall"] - prev, np.nan)
    out["yoy_pct"] = np.where(ok & (prev > 0), (out["rainfall"] - prev) / prev * 100, np.nan)
    return out


# ----------------------------------------------------------------------------- high-rainfall screening
def calculate_percentile_threshold(values, method: str = "P95", fixed_value: float | None = None,
                                   wet_only: bool = True) -> dict:
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        raise ValueError("No observations available to calculate a threshold.")
    if method == "FIXED":
        if fixed_value is None:
            raise ValueError("A fixed threshold value is required.")
        return {"threshold": float(fixed_value), "label": f"Fixed {fixed_value:g} {config.RAINFALL_UNIT}",
                "basis": "user-defined fixed value", "basis_n": int(v.size)}
    q = THRESHOLD_METHODS[method]
    basis = v[v >= config.WET_OBSERVATION_MM] if wet_only else v
    basis_name = f"wet observations (>= {config.WET_OBSERVATION_MM:g} {config.RAINFALL_UNIT})" if wet_only else "all observations"
    if basis.size == 0:
        basis, basis_name = v, "all observations (no wet observations found)"
    return {"threshold": float(np.percentile(basis, q)), "label": f"{q}th percentile",
            "basis": basis_name, "basis_n": int(basis.size)}


def detect_high_rainfall_events(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Observations strictly above the threshold, with context columns."""
    cols = ["date", "region"] + (["state"] if "state" in df else []) + ["rainfall"]
    if df.empty:
        return pd.DataFrame(columns=cols + ["threshold", "excess", "ratio", "percentile", "status"])
    ev = df.loc[df["rainfall"] > threshold, cols].copy()
    ref = np.sort(df["rainfall"].to_numpy())
    ev["threshold"] = threshold
    ev["excess"] = ev["rainfall"] - threshold
    ev["ratio"] = ev["rainfall"] / threshold if threshold > 0 else np.nan
    ev["percentile"] = np.searchsorted(ref, ev["rainfall"].to_numpy(), side="right") / ref.size * 100
    ev["status"] = "HIGH"
    ev["region"] = ev["region"].astype(str)
    if "state" in ev:
        ev["state"] = ev["state"].astype(str)
    return ev.sort_values("rainfall", ascending=False).reset_index(drop=True)


def explain_event(event: pd.Series, freq: str) -> dict:
    unit = unit_label(freq)
    thr, val = float(event["threshold"]), float(event["rainfall"])
    ratio = val / thr if thr > 0 else float("nan")
    reason = (f"This observation exceeds the selected high-rainfall threshold by {val - thr:,.1f} {unit}. "
              "It is flagged because it is unusually high relative to the selected data, "
              "not because of any assessment of flood risk.")
    return {
        "rainfall": f"{val:,.1f} {unit}", "threshold": f"{thr:,.1f} {unit}",
        "difference": f"+{val - thr:,.1f} {unit}",
        "relative": f"{ratio:.2f}\u00d7 threshold" if np.isfinite(ratio) else "n/a",
        "percentile": f"{float(event['percentile']):.1f}th percentile of selected observations",
        "reason": reason,
    }


# ----------------------------------------------------------------------------- anomaly metrics
def _rolling_spec(freq: str):
    return {"daily": ("time", "30D", 7), "monthly": ("obs", 12, 3), "annual": ("obs", 5, 3)}.get(freq, ("obs", 7, 3))


def baseline_description(freq: str) -> str:
    kind, win, _ = _rolling_spec(freq)
    return f"trailing {win} average of the preceding observations" if kind == "time" \
        else f"mean of the preceding {win} observations"


def add_analytical_features(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """PROCESSED -> ANALYTICAL: rolling baseline, deviations and percentile position (per region record)."""
    out = df.copy()
    kind, win, minp = _rolling_spec(freq)
    baseline = pd.Series(np.nan, index=out.index)
    for _, g in out.groupby("region", observed=True, sort=False):
        s = g.sort_values("date").set_index("date")["rainfall"]
        if kind == "time":
            r = s.rolling(win, closed="left", min_periods=minp).mean()
        else:
            r = s.shift(1).rolling(win, min_periods=minp).mean()
        baseline.loc[g.sort_values("date").index] = r.to_numpy()
    out["rolling_baseline"] = baseline
    out["deviation_from_rolling"] = out["rainfall"] - out["rolling_baseline"]
    sd = out.groupby("region", observed=True)["deviation_from_rolling"].transform("std")
    out["deviation_z"] = out["deviation_from_rolling"] / sd.replace(0, np.nan)
    month_mean = out.groupby(["region", "month"], observed=True)["rainfall"].transform("mean")
    out["seasonal_deviation"] = out["rainfall"] - month_mean
    out["percentile_position"] = out.groupby("region", observed=True)["rainfall"].rank(pct=True) * 100
    return out


# ----------------------------------------------------------------------------- summaries
def _scope_phrase(scope_label: str) -> str:
    return scope_label


def generate_analytical_summary(df: pd.DataFrame, freq: str, scope_label: str, period_label: str,
                                kind: str = "overview", **ctx) -> list[str]:
    """Deterministic, fact-only summary sentences for the selected data."""
    if df.empty:
        return ["No observations are available for the current selection."]
    unit = unit_label(freq)
    lines: list[str] = []
    stats = get_summary_statistics(df)

    if kind == "overview":
        lines.append(f"For {scope_label} during {period_label}, the dataset holds {stats['n_records']:,} observations "
                     f"across {stats['n_regions']} region(s) and {stats['obs_periods']:,} distinct {observation_noun(freq)}.")
        lines.append(f"The highest single observation was {stats['maximum']:,.1f} {unit} in {stats['max_region']} "
                     f"on {fmt_date(stats['max_date'])}. The mean observation was {stats['mean']:,.1f} {unit}.")
        if stats["n_regions"] > 1:
            lines.append(f"{stats['wettest_region']} recorded the highest total rainfall ({fmt_mm(stats['wettest_total'], 0)}).")
            if stats["uneven_coverage"]:
                lines.append("Regions have different numbers of observations, so totals are not strictly like-for-like.")
        m = calculate_monthly_rainfall(df)
        if not m.empty and m["n_years"].max() >= 1:
            peak, low = m.loc[m["mean_total"].idxmax()], m.loc[m["mean_total"].idxmin()]
            lines.append(f"{peak['month_name']} has the highest typical monthly rainfall ({fmt_mm(peak['mean_total'])}); "
                         f"{low['month_name']} has the lowest ({fmt_mm(low['mean_total'])}).")
    elif kind == "seasonal":
        m = calculate_monthly_rainfall(df)
        s = calculate_seasonal_summary(calculate_seasonal_rainfall(df))
        peak, low = m.loc[m["mean_total"].idxmax()], m.loc[m["mean_total"].idxmin()]
        lines.append(f"For {scope_label} during {period_label}, the peak rainfall month is {peak['month_name']} "
                     f"(typically {fmt_mm(peak['mean_total'])}, {peak['contribution_pct']:.1f}% of the annual total) "
                     f"and the lowest is {low['month_name']} ({fmt_mm(low['mean_total'])}).")
        if not s.empty:
            top = s.loc[s["share_pct"].idxmax()]
            lines.append(f"The {top['season']} season contributes the largest share ({top['share_pct']:.1f}%) "
                         f"under the {config.SEASON_DEFINITION_NAME} definition; its wettest year in the selection was {top['wettest_year']}.")
            var = s.assign(cv=np.where(s["mean_total"] > 0, s["std"] / s["mean_total"], np.nan)).dropna(subset=["cv"])
            if len(var) and (s["years"] > 1).any():
                v = var.loc[var["cv"].idxmax()]
                lines.append(f"Year-to-year variation is largest in the {v['season']} season "
                             f"(coefficient of variation {v['cv']:.2f}).")
    elif kind == "events":
        thr, ev, n_obs = ctx["threshold"], ctx["events"], int(len(df))
        lines.append(f"For {scope_label} during {period_label}, the selected threshold ({ctx['threshold_label']}) is "
                     f"{thr:,.1f} {unit}, based on {ctx['basis']}.")
        lines.append(f"The threshold was exceeded on {len(ev):,} of {n_obs:,} observations ({len(ev) / n_obs * 100:.1f}%).")
        if len(ev):
            top = ev.iloc[0]
            lines.append(f"The highest flagged observation was {top['rainfall']:,.1f} {unit} in {top['region']} on "
                         f"{fmt_date(top['date'])} ({top['ratio']:.2f}\u00d7 the threshold).")
            by_month = ev.groupby(ev["date"].dt.month).size()
            lines.append(f"Flagged observations are most frequent in {calendar.month_name[int(by_month.idxmax())]} "
                         f"({int(by_month.max())} observations).")
        lines.append("These are statistically unusual observations within the selected data; they do not indicate flooding.")
    elif kind == "comparison":
        rs = ctx["regional_summary"]
        hi, lo = rs.iloc[0], rs.iloc[-1]
        lines.append(f"Among the compared regions during {period_label}, {hi['region']} has the highest total rainfall "
                     f"({fmt_mm(hi['total'], 0)}) and {lo['region']} the lowest ({fmt_mm(lo['total'], 0)}).")
        mx = rs.loc[rs["maximum"].idxmax()]
        lines.append(f"The highest single observation among them was {mx['maximum']:,.1f} {unit} in {mx['region']}.")
        cv = rs.dropna(subset=["variability_cv"])
        if len(cv):
            v = cv.loc[cv["variability_cv"].idxmax()]
            lines.append(f"{v['region']} shows the greatest relative variability (coefficient of variation {v['variability_cv']:.2f}).")
        if rs["observations"].max() > 1.1 * rs["observations"].min():
            lines.append("Compared regions have different numbers of observations, so totals are not strictly like-for-like.")
    elif kind == "anomaly":
        flagged, k = ctx["flagged"], ctx["k"]
        lines.append(f"For {scope_label} during {period_label}, {len(flagged):,} of {ctx['n_scored']:,} scored observations "
                     f"deviate from their rolling baseline by at least {k:g} standard deviations of that region's deviations.")
        if len(flagged):
            top = flagged.reindex(flagged["deviation_from_rolling"].abs().sort_values(ascending=False).index).iloc[0]
            lines.append(f"The largest deviation was {top['deviation_from_rolling']:+,.1f} {unit} in {top['region']} on {fmt_date(top['date'])}.")
        lines.append("This is a statistical deviation measure on the loaded data; it is not a climate-change conclusion.")
    return lines


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def summary_to_text(title: str, lines: list[str]) -> bytes:
    return (title + "\n" + "=" * len(title) + "\n\n" + "\n\n".join(lines) + "\n").encode("utf-8")