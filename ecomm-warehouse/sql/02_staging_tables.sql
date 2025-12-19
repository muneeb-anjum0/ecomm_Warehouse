-- 02_staging_tables.sql
-- Staging layer - cleaned, typed, and validated data

CREATE TABLE IF NOT EXISTS staging.orders_clean (
    staging_orders_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(256) NOT NULL,
    user_id VARCHAR(256) NOT NULL,
    product_id VARCHAR(256) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    revenue DECIMAL(12, 2) NOT NULL,
    order_ts TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    load_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(order_id, load_date)
);

CREATE INDEX idx_staging_orders_load_date ON staging.orders_clean(load_date);
CREATE INDEX idx_staging_orders_order_id ON staging.orders_clean(order_id);
CREATE INDEX idx_staging_orders_user_id ON staging.orders_clean(user_id);
CREATE INDEX idx_staging_orders_product_id ON staging.orders_clean(product_id);

COMMENT ON TABLE staging.orders_clean IS 'Cleaned orders with validated types and business rules';


CREATE TABLE IF NOT EXISTS staging.events_clean (
    staging_events_id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(256) NOT NULL,
    user_id VARCHAR(256) NOT NULL,
    product_id VARCHAR(256),
    event_type VARCHAR(100) NOT NULL,
    event_ts TIMESTAMP NOT NULL,
    load_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(event_id, load_date)
);

CREATE INDEX idx_staging_events_load_date ON staging.events_clean(load_date);
CREATE INDEX idx_staging_events_event_id ON staging.events_clean(event_id);
CREATE INDEX idx_staging_events_user_id ON staging.events_clean(user_id);
CREATE INDEX idx_staging_events_product_id ON staging.events_clean(product_id);
CREATE INDEX idx_staging_events_event_type ON staging.events_clean(event_type);

COMMENT ON TABLE staging.events_clean IS 'Cleaned clickstream events with deduplicated and validated data';


CREATE TABLE IF NOT EXISTS staging.products_clean (
    staging_products_id BIGSERIAL PRIMARY KEY,
    product_id VARCHAR(256) NOT NULL,
    product_name VARCHAR(512),
    category VARCHAR(256),
    brand VARCHAR(256),
    current_price DECIMAL(10, 2),
    load_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, load_date)
);

CREATE INDEX idx_staging_products_load_date ON staging.products_clean(load_date);
CREATE INDEX idx_staging_products_product_id ON staging.products_clean(product_id);

COMMENT ON TABLE staging.products_clean IS 'Cleaned products with validated types and fields';
