# E-commerce Analytics Warehouse

A production-grade data pipeline for E-commerce analytics built with **Python + Apache Airflow + PostgreSQL + Docker**.

Ingests raw order & event data daily, cleans it through staging layers, loads to a star schema warehouse, validates data quality, and produces analytics-ready tables.

## 🏗️ Architecture

```
Data Sources
    ├── Orders (JSON, daily)
    ├── Events (CSV, daily)
    └── Products (API, weekly)
           ↓
    ┌──────────────────┐
    │  Raw Layer       │  (immutable)
    │  - raw.orders    │
    │  - raw.events    │
    │  - raw.products  │
    └──────────────────┘
           ↓
    ┌──────────────────┐
    │  Staging Layer   │  (cleaned)
    │  - staging.*     │
    └──────────────────┘
           ↓
    ┌──────────────────────────┐
    │  Quality Checks          │  (validate)
    │  - Volume rules          │
    │  - Uniqueness            │
    │  - Revenue validation    │
    │  - Future timestamps     │
    └──────────────────────────┘
           ↓
    ┌──────────────────┐
    │  Warehouse       │  (star schema)
    │  ├─ Dimensions   │
    │  │  ├─ dim_date  │
    │  │  ├─ dim_user  │
    │  │  └─ dim_product│
    │  └─ Facts        │
    │     ├─ fact_orders│
    │     └─ fact_events│
    └──────────────────┘
           ↓
    ┌──────────────────┐
    │  Analytics       │
    │  - daily_metrics │
    │  - audit logs    │
    └──────────────────┘
```

### Data Layers

1. **Raw Layer** (`raw` schema)
   - Immutable, never updated
   - Stores exact data as received
   - Tables: `raw.orders_json`, `raw.events_csv`, `raw.products_json`

2. **Staging Layer** (`staging` schema)
   - Cleaned, validated, deduplicated
   - Ready for analytics
   - Tables: `staging.orders_clean`, `staging.events_clean`, `staging.products_clean`

3. **Warehouse Layer** (`warehouse` schema)
   - Star schema with dimensions and facts
   - Optimized for BI/analytics queries
   - Dimensions: `dim_date`, `dim_user`, `dim_product`
   - Facts: `fact_orders`, `fact_events`
   - Metrics: `daily_metrics`

4. **Audit Layer** (`audit` schema)
   - Quality check results
   - Pipeline run logs
   - Bad record quarantine
   - Tables: `audit.pipeline_runs`, `audit.dq_failures`, `audit.bad_records`

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 4GB RAM minimum (8GB recommended)
- Ports available: 5432 (Postgres), 8080 (Airflow), 5050 (pgAdmin)

### 1. Clone & Setup
```bash
cd ecomm-warehouse

# Generate 7 days of sample data
python data/generators/generate_sample_data.py 2025-12-13 7

# Build and start containers
docker-compose up -d

# Wait for containers to be healthy
sleep 30

# Verify all containers are running
docker-compose ps
```

### 2. Access Services
- **Airflow UI**: http://localhost:8080
  - Username: `admin`
  - Password: `admin`
  
- **pgAdmin**: http://localhost:5050
  - Email: `admin@example.com`
  - Password: `admin`

### 3. Trigger a Pipeline Run
```bash
# Via Airflow UI
# Navigate to Dags > ecomm_warehouse_daily > Trigger DAG

# Or via command line
docker-compose exec airflow-scheduler airflow dags trigger ecomm_warehouse_daily
```

### 4. Monitor & Validate
```bash
# View scheduler logs
docker-compose logs -f airflow-scheduler

# Connect to Postgres
docker-compose exec postgres psql -U airflow -d ecommerce_warehouse

# Sample query: Check daily metrics
SELECT * FROM warehouse.daily_metrics ORDER BY run_date DESC LIMIT 1;

# Sample query: Revenue by category
SELECT 
    dp.category,
    DATE(fo.order_ts) as order_date,
    COUNT(*) as order_count,
    SUM(fo.revenue) as total_revenue
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
GROUP BY dp.category, DATE(fo.order_ts)
ORDER BY order_date DESC, total_revenue DESC;
```

## 📊 Project Structure

```
ecomm-warehouse/
├── dags/
│   └── ecomm_warehouse_daily.py       # Main Airflow DAG
├── src/
│   ├── common/
│   │   ├── db_utils.py               # Database connection utilities
│   │   └── logging_utils.py          # Logging setup
│   ├── extract/
│   │   ├── orders.py                 # Extract orders from JSON
│   │   ├── events.py                 # Extract events from CSV
│   │   └── products.py               # Extract products from API
│   ├── transform/
│   │   ├── orders.py                 # Clean orders
│   │   ├── events.py                 # Clean events
│   │   └── products.py               # Clean products
│   ├── load/
│   │   ├── dimensions.py             # Load dimension tables
│   │   ├── facts.py                  # Load fact tables
│   │   └── metrics.py                # Load metrics
│   └── quality/
│       └── dq_checks.py              # Data quality validations
├── sql/
│   ├── 00_schemas.sql               # Create schemas
│   ├── 01_raw_tables.sql            # Create raw layer tables
│   ├── 02_staging_tables.sql        # Create staging tables
│   ├── 03_warehouse_tables.sql      # Create warehouse tables
│   ├── 04_audit_tables.sql          # Create audit tables
│   └── 05_dim_date_seed.sql         # Seed date dimension
├── data/
│   └── incoming/
│       ├── orders/YYYY-MM-DD/       # Order JSON files
│       ├── events/YYYY-MM-DD/       # Event CSV files
│       └── products/                # Products JSON files (weekly)
├── scripts/
│   └── init-db.sh                   # Database initialization
├── docs/
│   ├── ARCHITECTURE.md              # Architecture details
│   ├── SCHEMA_DIAGRAM.md           # Database schema
│   └── QUERIES.md                   # Sample analytics queries
├── docker-compose.yml               # Docker service definitions
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables
├── Makefile                         # Useful commands
└── README.md                        # This file
```

## 🔄 DAG Workflow

The `ecomm_warehouse_daily` DAG runs daily at 2 AM UTC:

```
start
  ├─→ extract_orders
  ├─→ extract_events
  ├─→ extract_products (weekly, Monday only)
  │
  ├─→ transform_orders_to_staging
  ├─→ transform_events_to_staging
  ├─→ transform_products_to_staging
  │
  └─→ dq_checks (quality validation)
      ├─→ load_dim_date
      ├─→ load_dim_product
      ├─→ load_dim_user
      │
      ├─→ load_fact_orders
      ├─→ load_fact_events
      │
      └─→ compute_daily_metrics
          └─→ end
```

### Task Details

| Task | Purpose | Input | Output |
|------|---------|-------|--------|
| `extract_*` | Read from source files/API | JSON, CSV, HTTP | Raw layer tables |
| `transform_*` | Clean and validate | Raw tables | Staging tables |
| `dq_checks` | Quality validation | Staging data | Pass/Fail + audit logs |
| `load_dim_*` | Populate dimensions | Staging data | Dimension tables (upsert) |
| `load_fact_*` | Populate facts | Staging + dimensions | Fact tables (idempotent) |
| `compute_metrics` | Summary statistics | All layers | daily_metrics table |

## 📋 Key Features

### ✅ Idempotent Design
- **Safe reruns**: Each load task deletes then inserts for its load_date
- **No duplicates**: UPSERT logic with unique constraints
- **Catchup-ready**: Can backfill multiple days without conflicts

### 📊 Data Quality
Automated checks:
- **Volume rules**: Orders 100-500K/day, events 500-2M/day
- **Uniqueness**: No duplicate order_ids or event_ids
- **Range validation**: Revenue > 0, timestamps not in future
- **Referential integrity**: Products/users must exist in dimensions

Bad records are:
- Logged to `audit.bad_records` with reason
- Pipeline fails if critical rules violated
- Can be reviewed and reprocessed

### 🔍 Audit Trail
Every run is logged:
- Task execution times and status
- Record counts at each layer
- Data quality failures
- Pipeline runtime

### 🚨 Error Handling
- **Retries**: 2 attempts with 5-min backoff
- **Timeouts**: Task-specific execution limits
- **Graceful degradation**: Failures logged, bad records quarantined

## 📈 Sample Analytics Queries

### Revenue by Category (Daily)
```sql
SELECT 
    dp.category,
    DATE(fo.order_ts) as order_date,
    COUNT(*) as order_count,
    SUM(fo.revenue) as total_revenue,
    AVG(fo.revenue) as avg_order_value
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
WHERE DATE(fo.order_ts) >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dp.category, DATE(fo.order_ts)
ORDER BY order_date DESC, total_revenue DESC;
```

### User Conversion Funnel
```sql
WITH events_by_user AS (
    SELECT
        user_id,
        DATE(event_ts) as event_date,
        COUNT(CASE WHEN event_type = 'page_view' THEN 1 END) as page_views,
        COUNT(CASE WHEN event_type = 'add_to_cart' THEN 1 END) as add_to_carts,
        COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) as purchases
    FROM warehouse.fact_events
    GROUP BY user_id, DATE(event_ts)
)
SELECT
    event_date,
    COUNT(DISTINCT user_id) as users_with_page_views,
    COUNT(CASE WHEN add_to_carts > 0 THEN user_id END) as users_added_to_cart,
    COUNT(CASE WHEN purchases > 0 THEN user_id END) as users_purchased,
    ROUND(100.0 * COUNT(CASE WHEN add_to_carts > 0 THEN user_id END) / 
          COUNT(DISTINCT user_id), 2) as atc_rate,
    ROUND(100.0 * COUNT(CASE WHEN purchases > 0 THEN user_id END) / 
          COUNT(CASE WHEN add_to_carts > 0 THEN user_id END), 2) as conversion_rate
FROM events_by_user
GROUP BY event_date
ORDER BY event_date DESC;
```

### Repeat Customers
```sql
SELECT
    fo.user_id,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.revenue) as total_spent,
    MIN(fo.order_ts) as first_order_date,
    MAX(fo.order_ts) as last_order_date,
    (MAX(fo.order_ts) - MIN(fo.order_ts))::INT as days_as_customer
FROM warehouse.fact_orders fo
GROUP BY fo.user_id
HAVING COUNT(DISTINCT fo.order_id) >= 2
ORDER BY order_count DESC, total_spent DESC
LIMIT 20;
```

### Pipeline Health Dashboard
```sql
SELECT
    run_date,
    raw_orders_count,
    staging_orders_count,
    fact_orders_count,
    raw_events_count,
    staging_events_count,
    fact_events_count,
    dq_failed_count,
    runtime_seconds,
    ROUND(100.0 * fact_orders_count / NULLIF(raw_orders_count, 0), 2) as orders_completion_rate,
    ROUND(100.0 * fact_events_count / NULLIF(raw_events_count, 0), 2) as events_completion_rate
FROM warehouse.daily_metrics
ORDER BY run_date DESC
LIMIT 10;
```

## 🧪 Testing & Development

### Generate Test Data
```bash
# Generate 7 days of sample data
python data/generators/generate_sample_data.py 2025-12-13 7

# Or specific date range
python data/generators/generate_sample_data.py 2025-12-01 30
```

### Run Pipeline for Specific Date
```bash
docker-compose exec airflow-scheduler \
  airflow dags trigger ecomm_warehouse_daily \
  --exec-date 2025-12-19
```

### Check Logs
```bash
# Scheduler logs
docker-compose logs -f airflow-scheduler

# Webserver logs
docker-compose logs -f airflow-webserver

# Postgres logs
docker-compose logs -f postgres
```

### Database Debugging
```bash
# Connect to Postgres
docker-compose exec postgres psql -U airflow -d ecommerce_warehouse

# Useful commands:
\dt raw.* staging.* warehouse.* audit.*  # List tables
SELECT * FROM warehouse.daily_metrics;
SELECT * FROM audit.dq_failures;
SELECT * FROM audit.bad_records;
```

## 🛠️ Useful Make Commands

```bash
make up              # Start containers
make down            # Stop containers
make logs            # View scheduler logs
make clean           # Remove containers and volumes
make shell-postgres  # Connect to Postgres shell
make reset-airflow   # Reset Airflow database
make airflow-ui      # Print Airflow UI info
make pgadmin         # Print pgAdmin info
```

## 📦 Dependencies

See [requirements.txt](requirements.txt):
- `apache-airflow==2.7.0` - Workflow orchestration
- `psycopg2-binary==2.9.9` - Postgres driver
- `pandas==2.1.3` - Data manipulation
- `requests==2.31.0` - HTTP requests
- `python-dotenv==1.0.0` - Environment variables

## 🔐 Security Notes

⚠️ **This is a development setup. For production:**
- Change default credentials in `.env`
- Use Airflow Variables/Connections (no hardcoded passwords)
- Enable SSL/TLS for Postgres
- Set up proper authentication & RBAC
- Use secrets management (Vault, AWS Secrets Manager, etc.)
- Implement network policies and firewalls
- Enable Postgres encryption at rest
- Set up proper monitoring and alerting

## 📚 Additional Resources

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Star Schema Design](https://en.wikipedia.org/wiki/Star_schema)
- [Data Quality Best Practices](https://www.talend.com/resources/dataquality/)

## 📝 License

This project is provided as-is for educational and interview purposes.

## ✅ Checklist for Production Readiness

- [ ] Update credentials in `.env`
- [ ] Configure email notifications for failures
- [ ] Set up proper logging/monitoring (ELK, DataDog, etc.)
- [ ] Test disaster recovery procedures
- [ ] Document runbooks for common issues
- [ ] Set up backups for Postgres
- [ ] Configure network security
- [ ] Performance test with production data volumes
- [ ] Set up alerting thresholds
- [ ] Document SLA and availability targets
