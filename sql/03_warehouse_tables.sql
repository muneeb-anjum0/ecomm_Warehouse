-- 03_warehouse_tables.sql
-- Warehouse layer - star schema with dimensions and facts

-- DIMENSIONS

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_id INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    day INTEGER,
    week INTEGER,
    month INTEGER,
    quarter INTEGER,
    year INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(10),
    is_weekend BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dim_date_date ON warehouse.dim_date(date);

COMMENT ON TABLE warehouse.dim_date IS 'Date dimension for time-based analysis';


CREATE TABLE IF NOT EXISTS warehouse.dim_user (
    user_id VARCHAR(256) PRIMARY KEY,
    city VARCHAR(256),
    signup_date DATE,
    marketing_source VARCHAR(256),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dim_user_signup_date ON warehouse.dim_user(signup_date);
CREATE INDEX idx_dim_user_marketing_source ON warehouse.dim_user(marketing_source);

COMMENT ON TABLE warehouse.dim_user IS 'User dimension with attributes and signup source';


CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_id VARCHAR(256) PRIMARY KEY,
    product_name VARCHAR(512),
    category VARCHAR(256),
    brand VARCHAR(256),
    current_price DECIMAL(10, 2),
    effective_from DATE,
    effective_to DATE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dim_product_category ON warehouse.dim_product(category);
CREATE INDEX idx_dim_product_brand ON warehouse.dim_product(brand);
CREATE INDEX idx_dim_product_effective_dates ON warehouse.dim_product(effective_from, effective_to);

COMMENT ON TABLE warehouse.dim_product IS 'Product dimension with category, brand, and pricing';


-- FACTS

CREATE TABLE IF NOT EXISTS warehouse.fact_orders (
    fact_orders_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(256) NOT NULL,
    user_id VARCHAR(256) NOT NULL,
    product_id VARCHAR(256) NOT NULL,
    date_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    revenue DECIMAL(12, 2) NOT NULL,
    order_ts TIMESTAMP NOT NULL,
    status VARCHAR(50),
    load_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (date_id) REFERENCES warehouse.dim_date(date_id),
    FOREIGN KEY (user_id) REFERENCES warehouse.dim_user(user_id),
    FOREIGN KEY (product_id) REFERENCES warehouse.dim_product(product_id),
    UNIQUE(order_id, load_date)
);

CREATE INDEX idx_fact_orders_load_date ON warehouse.fact_orders(load_date);
CREATE INDEX idx_fact_orders_date_id ON warehouse.fact_orders(date_id);
CREATE INDEX idx_fact_orders_user_id ON warehouse.fact_orders(user_id);
CREATE INDEX idx_fact_orders_product_id ON warehouse.fact_orders(product_id);
CREATE INDEX idx_fact_orders_order_id ON warehouse.fact_orders(order_id);

COMMENT ON TABLE warehouse.fact_orders IS 'Fact table for order transactions';


CREATE TABLE IF NOT EXISTS warehouse.fact_events (
    fact_events_id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(256) NOT NULL,
    user_id VARCHAR(256) NOT NULL,
    product_id VARCHAR(256),
    date_id INTEGER NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_ts TIMESTAMP NOT NULL,
    load_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (date_id) REFERENCES warehouse.dim_date(date_id),
    FOREIGN KEY (user_id) REFERENCES warehouse.dim_user(user_id),
    UNIQUE(event_id, load_date)
);

CREATE INDEX idx_fact_events_load_date ON warehouse.fact_events(load_date);
CREATE INDEX idx_fact_events_date_id ON warehouse.fact_events(date_id);
CREATE INDEX idx_fact_events_user_id ON warehouse.fact_events(user_id);
CREATE INDEX idx_fact_events_product_id ON warehouse.fact_events(product_id);
CREATE INDEX idx_fact_events_event_type ON warehouse.fact_events(event_type);
CREATE INDEX idx_fact_events_event_id ON warehouse.fact_events(event_id);

COMMENT ON TABLE warehouse.fact_events IS 'Fact table for clickstream events';


-- METRICS

CREATE TABLE IF NOT EXISTS warehouse.daily_metrics (
    daily_metrics_id BIGSERIAL PRIMARY KEY,
    run_date DATE NOT NULL UNIQUE,
    raw_orders_count INTEGER,
    staging_orders_count INTEGER,
    fact_orders_count INTEGER,
    raw_events_count INTEGER,
    staging_events_count INTEGER,
    fact_events_count INTEGER,
    dq_failed_count INTEGER,
    runtime_seconds INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_daily_metrics_run_date ON warehouse.daily_metrics(run_date);

COMMENT ON TABLE warehouse.daily_metrics IS 'Daily pipeline metrics and counts for monitoring';
