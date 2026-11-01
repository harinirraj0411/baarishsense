# Methodology

## Scope and integrity
BAARISHSENSE is an independent environmental-analytics project. It is **not** an official weather service, a government system, a flood-warning authority, or a validated flood-prediction model. All figures are computed from the loaded CSV; nothing is simulated or hard-coded.

## Pipeline
1. **Raw** - `data_loader.load_raw_data` reads the CSV as published.
2. **Processed** - `data_processing.clean_data` normalises columns, detects the schema, parses dates (ISO first, then day-first vs month-first by parse success), converts rainfall to numeric, excludes missing / non-numeric / negative / unparseable rows, removes duplicate region-date rows (first kept), and derives year, month and season. Every exclusion is counted in the Data Quality panel.
3. **Analytical** - `analytics.add_analytical_features` adds rolling-baseline metrics; the other `analytics` functions aggregate for each view.

## Aggregation rules
* **Trend**: period totals per region; when several regions are selected, the mean of regions' totals.
* **Monthly profile**: region-year-month totals, averaged across regions, then across years. Contribution % = month mean / sum of month means.
* **Seasons**: calendar-month groups from `SEASON_MONTHS` (default: conventional IMD split). Each season total is computed within a calendar year.
* **Year-over-year**: annual totals; change reported only between consecutive years whose observation coverage is >= 90%.
* **Resolution**: the dataset's native resolution is detected from the median gap between observations; finer aggregations are disabled.

## High-rainfall event screening
* Threshold: 90th/95th/99th percentile of the selected observations, or a fixed value. By default (daily data) the percentile is taken over wet observations (>= `WET_OBSERVATION_MM`, 0.1 mm) so dry days do not lower the threshold. This can be switched off.
* Observations strictly above the threshold are flagged `HIGH`.
* The result is statistical unusualness **within the selected data**. It does not establish that flooding occurs or will occur.

## Anomaly view
Deviation of each observation from a trailing rolling baseline of the same region (current observation excluded), standardised by that region's deviation spread. Flagged points are statistical outliers on the loaded data and carry no climate-science interpretation.

## Summaries
Plain Python string templates filled with values computed from the selected data. No language model is used.

## Known limitations
* Region-level aggregates assume each region's observations are comparable; uneven coverage is flagged but not corrected.
* Rolling baselines assume reasonably regular sampling; gaps shorten the effective window.
* Seasonal definitions are conventional and may not suit every region (for example, the October-December rains matter most in parts of southeast India).
* A map needs coordinates or boundaries supplied with the data; none are bundled.
