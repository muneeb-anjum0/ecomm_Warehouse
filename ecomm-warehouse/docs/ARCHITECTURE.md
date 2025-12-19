# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Sources                              │
├─────────────────────────────────────────────────────────────┤
│  • Daily Orders (JSON)    • Daily Events (CSV)              │
│  • Weekly Products API    • User Attributes (from orders)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 Airflow Orchestration                       │
│  (2 AM UTC daily, LocalExecutor, PostgreSQL backend)       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Data Pipeline (14 tasks)                      │
├─────────────────────────────────────────────────────────────┤
│  1. Extract (raw layer)                                    │
│     - Extract Orders, Events, Products                     │
│                                                             │
│  2. Transform (staging layer)                              │
│     - Clean, normalize, deduplicate                        │
│                                                             │
│  3. Quality (validation)                                   │
│     - Volume, uniqueness, range checks                     │
│                                                             │
│  4. Load Dimensions (upsert)                               │
│     - dim_date, dim_user, dim_product                      │
│                                                             │
│  5. Load Facts (idempotent)                                │
│     - fact_orders, fact_events                             │
│                                                             │
│  6. Metrics (monitoring)                                   │
│     - daily_metrics table                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Data Warehouse                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Raw Layer  │  │ Staging Layer│  │ Warehouse Layer │  │
│  ├─────────────┤  ├──────────────┤  ├──────────────────┤  │
│  │ orders_json │  │orders_clean  │  │dim_date          │  │
│  │ events_csv  │  │events_clean  │  │dim_user          │  │
│  │products_json│  │products_clean│  │dim_product       │  │
│  │ (immutable) │  │ (cleaned)    │  │fact_orders       │  │
│  │             │  │              │  │fact_events       │  │
│  │             │  │              │  │daily_metrics     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  ┌──────────────────────┐                                  │
│  │   Audit Layer        │                                  │
│  ├──────────────────────┤                                  │
│  │ pipeline_runs        │                                  │
│  │ dq_failures          │                                  │
│  │ bad_records          │                                  │
│  └──────────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Analytics & Reporting                          │
│  • BI Tools (Tableau, Looker, Power BI)                    │
│  • Direct SQL Queries                                      │
│  • Airflow UI for Pipeline Monitoring                      │
│  • pgAdmin for Database Management                         │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | Apache Airflow 2.7 | Schedule & monitor tasks |
| **Data Processing** | Python 3.11 | ETL logic & transformations |
| **Database** | PostgreSQL 15 | Data storage & analytics |
| **Containerization** | Docker & Docker Compose | Local development environment |
| **Monitoring** | pgAdmin, Airflow UI | DB & pipeline monitoring |

## Data Flow Principles

### 1. **Immutability in Raw Layer**
- Raw data never updated, only inserted
- Full audit trail of ingestion
- Can reprocess from raw anytime

### 2. **Separation of Concerns**
- Raw = data capture
- Staging = data cleaning
- Warehouse = analytics model
- Audit = quality & logging

### 3. **Idempotent Loads**
- Delete-then-insert pattern for each load_date
- Safe to rerun without duplicates
- Supports backfilling and reruns

### 4. **Quality Gates**
- Validation before warehouse load
- Failures logged to audit tables
- Pipeline stops if critical rules violated

## Scaling Considerations

### Current Design (Development)
- LocalExecutor: Single-machine execution
- Suitable for: <1M records/day

### For Production Scaling

**Executor Change**
```python
# Use CeleryExecutor or KubernetesExecutor
AIRFLOW__CORE__EXECUTOR = CeleryExecutor
# Requires: Redis, Celery workers
```

**Database Optimization**
```sql
-- Partitioning by load_date
CREATE TABLE warehouse.fact_orders (
    ...
) PARTITION BY RANGE (load_date) (
    PARTITION p_2025_01 VALUES FROM ('2025-01-01') TO ('2025-02-01'),
    PARTITION p_2025_02 VALUES FROM ('2025-02-01') TO ('2025-03-01')
);

-- Columnar storage for analytics
-- Consider: Citus, Timescale DB extensions
```

**Increased Parallelism**
```python
# Increase parallelism in DAG
dag = DAG(..., max_active_runs=5)
# Process multiple days simultaneously
```

**External Storage**
```python
# Move raw/staging files to S3
# Use COPY from S3 for faster bulk loads
# Keep warehouse in Postgres, reporting data in external DW
```

## Disaster Recovery

### Backup Strategy
```bash
# Nightly backups
pg_dump -Fc ecommerce_warehouse > backup_$(date +%Y%m%d).dump

# Restore from backup
pg_restore -d ecommerce_warehouse backup_20251219.dump
```

### Reprocessing
```python
# Full reprocess from raw
airflow dags backfill ecomm_warehouse_daily \
  --start-date 2025-01-01 \
  --end-date 2025-12-19 \
  --reset-dagruns  # Clear existing runs
```

### Data Validation After Restore
```sql
-- Check consistency
SELECT 
    COUNT(*) as raw_count,
    (SELECT COUNT(*) FROM staging.orders_clean) as staging_count,
    (SELECT COUNT(*) FROM warehouse.fact_orders) as fact_count
FROM raw.orders_json;
```

## Performance Optimization

### Indexing Strategy
```sql
-- Fact tables need clustering for queries
CLUSTER warehouse.fact_orders USING idx_fact_orders_date_id;
CLUSTER warehouse.fact_events USING idx_fact_events_date_id;

-- Regular ANALYZE for query planner
ANALYZE warehouse.fact_orders;
```

### Query Performance Tips
```sql
-- Use date_id for filtering (integer vs timestamp)
EXPLAIN ANALYZE
SELECT * FROM warehouse.fact_orders 
WHERE date_id BETWEEN 20251201 AND 20251219;

-- Use materialized views for complex aggregates
CREATE MATERIALIZED VIEW mv_daily_revenue AS
SELECT DATE(order_ts) as order_date,
       SUM(revenue) as daily_revenue
FROM warehouse.fact_orders
GROUP BY DATE(order_ts);

REFRESH MATERIALIZED VIEW mv_daily_revenue;
```

## Monitoring & Alerting

### Key Metrics to Monitor
- **Pipeline runtime**: Should stay < 1 hour
- **Record throughput**: Orders/events per second
- **Quality failure rate**: % of runs with failed DQ checks
- **Database size**: Raw layer growth rate

### Sample Alerts
```sql
-- Alert if pipeline took >90 minutes
SELECT * FROM warehouse.daily_metrics
WHERE runtime_seconds > 5400
AND run_date >= CURRENT_DATE - INTERVAL '7 days';

-- Alert if quality failures increasing
SELECT run_date, dq_failed_count
FROM warehouse.daily_metrics
WHERE dq_failed_count > 100
ORDER BY run_date DESC LIMIT 7;

-- Alert if volume drops below threshold
SELECT run_date, raw_orders_count
FROM warehouse.daily_metrics
WHERE raw_orders_count < 100
AND run_date >= CURRENT_DATE - INTERVAL '7 days';
```

## Compliance & Auditing

### Data Lineage
```sql
-- Track data from source to warehouse
SELECT 
    ro.raw_orders_id as source,
    ro.run_date,
    ro.ingested_at,
    oc.staging_orders_id as staging_id,
    fo.fact_orders_id as warehouse_id,
    ro.raw_json ->> 'order_id' as order_id
FROM raw.orders_json ro
LEFT JOIN staging.orders_clean oc ON ro.run_date = oc.load_date
LEFT JOIN warehouse.fact_orders fo ON oc.order_id = fo.order_id
WHERE ro.run_date = CURRENT_DATE;
```

### Change Tracking
```sql
-- See when records were updated in staging
SELECT 
    order_id,
    created_at,
    updated_at,
    (SELECT COUNT(*) FROM raw.orders_json 
     WHERE DATE(ingested_at) = DATE(oc.updated_at)) as raw_records_that_day
FROM staging.orders_clean oc
ORDER BY updated_at DESC;
```
