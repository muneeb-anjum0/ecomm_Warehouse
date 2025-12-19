# Star Schema Diagram

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIMENSION TABLES                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   dim_date       │      │   dim_user       │      │  dim_product     │
├──────────────────┤      ├──────────────────┤      ├──────────────────┤
│ date_id (PK) ⦿   │      │ user_id (PK) ⦿   │      │ product_id (PK) ⦿│
│ date             │      │ city             │      │ product_name     │
│ day              │      │ signup_date      │      │ category         │
│ week             │      │ marketing_source │      │ brand            │
│ month            │      │ created_at       │      │ current_price    │
│ quarter          │      │ updated_at       │      │ effective_from   │
│ year             │      │ -                │      │ effective_to     │
│ day_of_week      │      │ -                │      │ created_at       │
│ day_name         │      │ -                │      │ updated_at       │
│ is_weekend       │      └──────────────────┘      └──────────────────┘
│ created_at       │               ↑                         ↑
│ updated_at       │               │                         │
└──────────────────┘               │                         │
         ↑                         │                         │
         │                    FK   │                    FK   │
         │                         │                         │
┌────────┴──────────────────────────┴──────────────────────────────┐
│                      FACT TABLES                                 │
└──────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────┐    ┌──────────────────────────┐
│      fact_orders                  │    │     fact_events          │
├───────────────────────────────────┤    ├──────────────────────────┤
│ fact_orders_id (PK)               │    │ fact_events_id (PK)      │
│ order_id (UNIQUE)                 │    │ event_id (UNIQUE)        │
│ user_id (FK) → dim_user     ────→ │    │ user_id (FK)       ────→ │
│ product_id (FK) → dim_product ──→ │    │ product_id (FK)    ────→ │
│ date_id (FK) → dim_date     ────→ │    │ date_id (FK)       ────→ │
│ quantity                          │    │ event_type               │
│ revenue                           │    │ event_ts                 │
│ order_ts                          │    │ load_date (PARTITION)    │
│ status                            │    │ created_at               │
│ load_date (PARTITION)             │    └──────────────────────────┘
│ created_at                        │
│ INDEXES:                          │
│ - idx_date_id                     │
│ - idx_user_id                     │
│ - idx_product_id                  │
│ - idx_load_date                   │
└───────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                 METRICS TABLE                                    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              warehouse.daily_metrics                             │
├──────────────────────────────────────────────────────────────────┤
│ daily_metrics_id                                                 │
│ run_date (UNIQUE)                                                │
│ raw_orders_count, staging_orders_count, fact_orders_count       │
│ raw_events_count, staging_events_count, fact_events_count       │
│ dq_failed_count                                                  │
│ runtime_seconds                                                  │
│ created_at, updated_at                                           │
└──────────────────────────────────────────────────────────────────┘
```

## Schema Details

### Dimension Tables

#### dim_date
- **Purpose**: Provides temporal attributes for date-based analysis
- **Granularity**: One row per calendar day
- **Pre-populated**: 3-year range (past 1 year + future 2 years)
- **Usage**: Join on `date_id` for filtering by fiscal year, quarter, week, day of week

```sql
-- Example: Orders by day of week
SELECT 
    dd.day_name,
    COUNT(*) as order_count,
    SUM(fo.revenue) as revenue
FROM warehouse.fact_orders fo
JOIN warehouse.dim_date dd ON fo.date_id = dd.date_id
GROUP BY dd.day_name
ORDER BY dd.day_of_week;
```

#### dim_user
- **Purpose**: User attributes for customer analysis
- **Type**: Slowly Changing Dimension Type 1 (current values only)
- **Updates**: On each new user or signup date change
- **Usage**: Join on `user_id` for customer segmentation

```sql
-- Example: Users by marketing source
SELECT 
    marketing_source,
    COUNT(*) as user_count,
    COUNT(DISTINCT order_count) as users_with_orders
FROM warehouse.dim_user du
LEFT JOIN (
    SELECT user_id, COUNT(*) as order_count 
    FROM warehouse.fact_orders 
    GROUP BY user_id
) fo ON du.user_id = fo.user_id
GROUP BY marketing_source;
```

#### dim_product
- **Purpose**: Product catalog with pricing and categorization
- **Type**: Slowly Changing Dimension Type 2 (optional with effective_from/to dates)
- **Updates**: Daily from products API
- **Usage**: Join on `product_id` for category/brand analysis

```sql
-- Example: Top products by revenue
SELECT 
    dp.product_id,
    dp.product_name,
    dp.category,
    dp.brand,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.revenue) as total_revenue,
    SUM(fo.quantity) as units_sold
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
WHERE fo.date_id >= (SELECT TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INT)
GROUP BY dp.product_id, dp.product_name, dp.category, dp.brand
ORDER BY total_revenue DESC
LIMIT 20;
```

### Fact Tables

#### fact_orders
- **Granularity**: One row per order
- **Volume**: ~1000-500K rows/day
- **Partitioning**: By `load_date` for efficient queries and maintenance
- **Foreign Keys**: References dim_date, dim_user, dim_product
- **Additive Metrics**: revenue (sum), quantity (sum), count (count)

```sql
-- Example query: Daily revenue trend
SELECT 
    dd.date as order_date,
    COUNT(*) as order_count,
    SUM(fo.revenue) as daily_revenue,
    AVG(fo.revenue) as avg_order_value,
    MAX(fo.revenue) as max_order_value
FROM warehouse.fact_orders fo
JOIN warehouse.dim_date dd ON fo.date_id = dd.date_id
WHERE dd.date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY dd.date
ORDER BY dd.date;
```

#### fact_events
- **Granularity**: One row per user event (page view, add to cart, purchase, etc.)
- **Volume**: ~5K-2M rows/day
- **Partitioning**: By `load_date`
- **Foreign Keys**: References dim_date, dim_user, dim_product (nullable for page views)
- **Semi-additive Metrics**: event count (count), unique users (count distinct)

```sql
-- Example query: Conversion funnel
SELECT 
    dd.date as event_date,
    COUNT(DISTINCT CASE WHEN fe.event_type = 'page_view' THEN fe.user_id END) as viewers,
    COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END) as cart_adds,
    COUNT(DISTINCT CASE WHEN fe.event_type = 'purchase' THEN fe.user_id END) as purchasers,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END) /
          COUNT(DISTINCT CASE WHEN fe.event_type = 'page_view' THEN fe.user_id END), 2) as cart_rate,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN fe.event_type = 'purchase' THEN fe.user_id END) /
          COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END), 2) as purchase_rate
FROM warehouse.fact_events fe
JOIN warehouse.dim_date dd ON fe.date_id = dd.date_id
WHERE dd.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dd.date
ORDER BY dd.date;
```

## Query Patterns

### Time Series Analysis
```sql
-- By day
GROUP BY dd.date

-- By week
GROUP BY dd.year, dd.week

-- By month
GROUP BY dd.year, dd.month
```

### Categorical Analysis
```sql
-- By product category
GROUP BY dp.category

-- By brand
GROUP BY dp.brand
```

### Customer Segmentation
```sql
-- By marketing source
GROUP BY du.marketing_source

-- By customer tenure
GROUP BY CASE 
    WHEN CURRENT_DATE - du.signup_date < INTERVAL '30 days' THEN 'New'
    WHEN CURRENT_DATE - du.signup_date < INTERVAL '90 days' THEN 'Growing'
    ELSE 'Established'
END
```

## Performance Considerations

### Indexing Strategy
```sql
-- Cluster indexes for most common query patterns
CLUSTER warehouse.fact_orders USING idx_fact_orders_date_id;
CLUSTER warehouse.fact_events USING idx_fact_events_date_id;

-- Composite indexes for multi-column filters
CREATE INDEX idx_fact_orders_date_user ON warehouse.fact_orders(date_id, user_id);
CREATE INDEX idx_fact_events_date_type ON warehouse.fact_events(date_id, event_type);
```

### Materialized Views for Heavy Queries
```sql
-- Pre-compute daily aggregates
CREATE MATERIALIZED VIEW mv_daily_orders_summary AS
SELECT 
    fo.date_id,
    COUNT(*) as order_count,
    SUM(fo.revenue) as daily_revenue,
    SUM(fo.quantity) as units_sold
FROM warehouse.fact_orders fo
GROUP BY fo.date_id;

-- Refresh after pipeline completion
REFRESH MATERIALIZED VIEW mv_daily_orders_summary;
```

## Cardinality Reference

| Dimension | Expected Cardinality | Notes |
|-----------|---------------------|-------|
| dim_date | 1,095 | 3 years |
| dim_user | 5K-50K | Growing with sales |
| dim_product | 100-10K | Varies by catalog size |
| fact_orders | 100K-500K/day | Partition by load_date |
| fact_events | 500K-2M/day | Partition by load_date |

## Maintenance Tasks

### Regular (Daily)
- Analyze dimension tables after updates
- Check partition bloat in fact tables

### Weekly
- VACUUM ANALYZE on all warehouse tables
- Check index usage and efficiency

### Monthly
- Partition maintenance for old data
- Materialized view refresh optimization
- Query performance review
