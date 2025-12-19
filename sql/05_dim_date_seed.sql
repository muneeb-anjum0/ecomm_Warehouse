-- 05_dim_date_seed.sql
-- Pre-populate dim_date for a 3-year range (adjust as needed)

WITH date_range AS (
    SELECT generate_series(
        CURRENT_DATE - INTERVAL '1 year',
        CURRENT_DATE + INTERVAL '2 years',
        INTERVAL '1 day'::INTERVAL
    )::DATE AS date_val
)
INSERT INTO warehouse.dim_date (
    date_id,
    date,
    day,
    week,
    month,
    quarter,
    year,
    day_of_week,
    day_name,
    is_weekend
)
SELECT
    TO_CHAR(date_val, 'YYYYMMDD')::INTEGER AS date_id,
    date_val,
    EXTRACT(DAY FROM date_val)::INTEGER,
    EXTRACT(WEEK FROM date_val)::INTEGER,
    EXTRACT(MONTH FROM date_val)::INTEGER,
    EXTRACT(QUARTER FROM date_val)::INTEGER,
    EXTRACT(YEAR FROM date_val)::INTEGER,
    EXTRACT(DOW FROM date_val)::INTEGER,
    TO_CHAR(date_val, 'Day'),
    EXTRACT(DOW FROM date_val) IN (0, 6)
FROM date_range
ON CONFLICT (date_id) DO NOTHING;

COMMENT ON VIEW NONE IS 'Populates dim_date with daily records for the next 3 years';
