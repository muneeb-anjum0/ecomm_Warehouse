-- 01_raw_tables.sql
-- Raw layer - immutable storage of ingested data

CREATE TABLE IF NOT EXISTS raw.orders_json (
    raw_orders_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    file_name TEXT,
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    raw_json JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_raw_orders_run_date ON raw.orders_json(run_date);
CREATE INDEX idx_raw_orders_ingested_at ON raw.orders_json(ingested_at);

COMMENT ON TABLE raw.orders_json IS 'Raw orders data ingested from daily JSON files';
COMMENT ON COLUMN raw.orders_json.raw_json IS 'Complete raw JSON object from source file';


CREATE TABLE IF NOT EXISTS raw.events_csv (
    raw_events_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    file_name TEXT,
    ingested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    raw_line TEXT,
    event_id VARCHAR(256),
    user_id VARCHAR(256),
    product_id VARCHAR(256),
    event_type VARCHAR(100),
    event_ts TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_raw_events_run_date ON raw.events_csv(run_date);
CREATE INDEX idx_raw_events_ingested_at ON raw.events_csv(ingested_at);
CREATE INDEX idx_raw_events_event_id ON raw.events_csv(event_id);

COMMENT ON TABLE raw.events_csv IS 'Raw clickstream events ingested from daily CSV files';
COMMENT ON COLUMN raw.events_csv.raw_line IS 'Original CSV line for debugging';


CREATE TABLE IF NOT EXISTS raw.products_json (
    raw_products_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    fetched_at TIMESTAMP NOT NULL DEFAULT NOW(),
    raw_json JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_raw_products_run_date ON raw.products_json(run_date);

COMMENT ON TABLE raw.products_json IS 'Raw products data from API';
