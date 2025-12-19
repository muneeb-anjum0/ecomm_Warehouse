-- 00_schemas.sql
-- Create all schemas for the warehouse

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;
CREATE SCHEMA IF NOT EXISTS audit;

GRANT ALL PRIVILEGES ON SCHEMA raw TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA staging TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA warehouse TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA audit TO airflow;

COMMENT ON SCHEMA raw IS 'Immutable layer - stores raw data exactly as received from sources';
COMMENT ON SCHEMA staging IS 'Cleaned and validated layer - deduplicated, typed, validated data';
COMMENT ON SCHEMA warehouse IS 'Analytics layer - star schema with dimensions and facts';
COMMENT ON SCHEMA audit IS 'Quality and logging layer - tracks runs, failures, and bad records';
