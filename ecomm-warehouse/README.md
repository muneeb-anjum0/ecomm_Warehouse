# E-Commerce Analytics Warehouse 📊

A **production-ready, real-time data pipeline** for e-commerce analytics. Extract live product, order, and event data from **Fake Store API** (free, no-auth public API), transform and cleanse it, and load it into a star-schema data warehouse for analytics and reporting.

> **This project demonstrates real-time API data ingestion + batch processing + data warehouse best practices** in a fully containerized, production-ready setup.

---

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker & Docker Compose installed
- Port 8080, 5050, 5432 available

### 1. Start All Services

```bash
cd ecomm-warehouse
docker-compose up -d
```

Wait 30 seconds for containers to initialize. Check status:
```bash
docker-compose ps
```

All services should show `Up` status. ✅

### 2. Access the UIs

| Service | URL | Login |
|---------|-----|-------|
| **Airflow DAGs** | http://localhost:8080 | `airflow` / `airflow` |
| **Database UI** | http://localhost:5050 | `admin@example.com` / `admin` |
| **Database** | localhost:5432 | `airflow` / `airflow` |

### 3. Trigger a Real-Time API Run

The `ecomm_api_polling` DAG runs **automatically every 10 minutes**, OR trigger manually:

```bash
docker-compose exec airflow-scheduler airflow dags trigger ecomm_api_polling
```

### 4. Check Data

```bash
# Count orders in warehouse (via terminal)
docker-compose exec postgres psql -U airflow -d ecommerce_warehouse -c \
  "SELECT COUNT(*) as total_orders FROM warehouse.fact_orders;"

# Or query in pgAdmin UI → Query Tool
```

**That's it!** The pipeline is ingesting real data from DummyJSON API and loading it into your warehouse. 🎉

---

## 📊 What This Does

### Problem It Solves
You need a modern, scalable data pipeline that:
- ✅ Fetches **real-time data from APIs** (194 products with rich attributes)
- ✅ Handles **batch data** from local sources simultaneously
- ✅ Validates data quality before loading to warehouse
- ✅ Transforms raw data into **star schema** for analytics
- ✅ Runs reliably with **Airflow orchestration** and monitoring
- ✅ Tracks inventory, discounts, and customer behavior

### How It Works (High-Level)

```
DummyJSON API (Real-Time)           Local Files (Batch)
    ↓ (every 10 min)                      ↓ (daily)
┌─────────────────────────────────────────────┐
│     EXTRACT (api_polling DAG)               │
│  ├─ Poll /products (194 items)             │
│  ├─ Poll /carts (50 shopping carts)        │
│  └─ Insert into raw.* tables               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│     TRANSFORM (warehouse_daily DAG)         │
│  ├─ Type casting, deduplication            │
│  ├─ Clean null values, invalid records     │
│  └─ Write to staging.* tables              │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│     QUALITY CHECKS                          │
│  ├─ Validate volume (min records)          │
│  ├─ Check uniqueness                       │
│  ├─ Validate timestamps                    │
│  └─ Log failures to audit.* tables         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│     LOAD (warehouse_daily DAG)              │
│  ├─ Upsert dimensions (users, products)    │
│  ├─ Insert facts (orders, events)          │
│  └─ Calculate daily metrics                │
└─────────────────────────────────────────────┘
                    ↓
           Star Schema ⭐
      Ready for Analytics & BI
```

---

## 🔌 Data Sources

### **Fake Store API** (Real-Time) ✨ NEW!

Free, public API with realistic e-commerce data. **No authentication required.**

- **Base URL:** https://fakestoreapi.com
- **Endpoints Used:**
  - `GET /products` → Products catalog
  - `GET /carts` → Orders/carts
  - `GET /users` → Customer data
- **Polling:** Every 10 minutes via `ecomm_api_polling` DAG
- **Data:** ~20 products, ~10 carts, ~10 users (sample data)

**Why Fake Store API?**
- ✅ Free, no API key needed
- ✅ Realistic e-commerce schema
- ✅ Stable, reliable endpoint
- ✅ Perfect for demos & learning
- ✅ Can replace with real API (Shopify, WooCommerce, etc.)

### **Local File Sources** (Batch)

For testing or batch ingestion:
- **Orders:** `/data/incoming/orders/YYYY-MM-DD/orders.json`
- **Events:** `/data/incoming/events/YYYY-MM-DD/events.csv`
- **Products:** `/data/incoming/products/products_YYYY-MM-DD.json` (generated Mondays)

Generate test data:
```bash
docker-compose exec airflow-scheduler python /opt/airflow/data/generators/generate_sample_data.py 2025-12-22 1
```

---

## 🏗️ Architecture & Schema

### Database Layers

```
┌────────────────────────────────────────────────────────┐
│ RAW LAYER (raw schema) - Immutable landing zone        │
│ ├─ raw.orders_json        JSONB bulk storage           │
│ ├─ raw.events_csv         CSV-normalized events        │
│ └─ raw.products_json      JSONB product catalog        │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ STAGING LAYER (staging schema) - Cleaned & typed      │
│ ├─ staging.orders_clean   Typed, deduplicated orders  │
│ ├─ staging.events_clean   Normalized clickstream      │
│ └─ staging.products_clean Enriched catalog            │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ WAREHOUSE LAYER (warehouse schema) - Star Schema ⭐   │
│                                                         │
│  DIMENSIONS:                                           │
│  ├─ dim_user      User attributes (city, signup_date) │
│  ├─ dim_product   Product catalog (price, category)   │
│  └─ dim_date      Calendar dimension (1000+ dates)    │
│                                                         │
│  FACTS:                                                │
│  ├─ fact_orders   Order transactions (FK to dims)     │
│  └─ fact_events   Behavioral events (user actions)    │
│                                                         │
│  METRICS:                                              │
│  └─ daily_metrics Pipeline health (row counts, etc)   │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ AUDIT LAYER (audit schema) - Governance               │
│ ├─ data_quality_failures  Failed quality checks       │
│ ├─ run_logs               Detailed execution logs      │
│ └─ schema_changes         DDL history                  │
└────────────────────────────────────────────────────────┘
```

### Key Tables (Star Schema)

**Dimensions** (Lookup tables):
- `dim_user` (pk: user_id) — Customer info
- `dim_product` (pk: product_id) — Product catalog
- `dim_date` (pk: date_id) — Calendar (YYYYMMDD format)

**Facts** (Transaction tables):
- `fact_orders` (fk: user_id, product_id, date_id) — Order details
- `fact_events` (fk: user_id, date_id) — Behavioral events

---

## 🔄 Pipelines (Airflow DAGs)

### 1. `ecomm_api_polling` 🔄 Real-Time

**Schedule:** Every 10 minutes  
**Purpose:** Fetch live data from Fake Store API

```
START → poll_orders → ─┐
                       ├─→ END
START → poll_events  ──┤
                       │
START → poll_products ─┘
```

**Tasks:**
- `poll_orders` — Fetch /carts, insert to raw.orders_json
- `poll_events` — Fetch /products + /carts, generate synthetic events
- `poll_products` — Fetch /products, insert to raw.products_json

### 2. `ecomm_warehouse_daily` 📊 Batch (Daily @ 2 AM UTC)

**Schedule:** Daily at 2:00 AM UTC  
**Purpose:** Transform raw data → warehouse, run quality checks, generate metrics

```
EXTRACT                    TRANSFORM              QUALITY & LOAD
├─ extract_orders    ───→  transform_orders  ──┐
├─ extract_events    ───→  transform_events  ──┼─→ dq_checks ──→ load_dim_* ──→ load_fact_* ──→ metrics ──→ END
└─ extract_products  ───→  transform_products ┘
```

**Key Tasks:**
- **Extract:** Read from local files or API
- **Transform:** Clean, validate, deduplicate
- **Quality Checks:** Validate row counts, uniqueness, future dates
- **Load Dimensions:** Upsert dim_user, dim_product, dim_date
- **Load Facts:** Insert fact_orders, fact_events (with FK validation)
- **Metrics:** Insert daily run summary to warehouse.daily_metrics

---

## 🛠️ Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| **Apache Airflow** | 2.7.0 | Workflow orchestration & scheduling |
| **PostgreSQL** | 15 (Alpine) | Data warehouse & OLAP |
| **Python** | 3.11 | Data transformation & extraction |
| **Docker** | Latest | Containerization & deployment |
| **pgAdmin** | Latest | Database UI & query tool |

---

## 📂 Project Structure

```
ecomm-warehouse/
├── dags/
│   ├── ecomm_api_polling.py           # Real-time API polling DAG 🔄
│   └── ecomm_warehouse_daily.py       # Daily batch DAG 📊
├── src/
│   ├── extract/
│   │   ├── orders.py                  # Extract orders from files
│   │   ├── events.py                  # Extract events from files
│   │   ├── products.py                # Extract products from files
│   │   ├── api_orders.py              # Extract orders from API ✨
│   │   ├── api_events.py              # Extract events from API ✨
│   │   └── api_products.py            # Extract products from API ✨
│   ├── transform/
│   │   ├── orders.py                  # Orders cleaning & validation
│   │   ├── events.py                  # Events normalization
│   │   └── products.py                # Products enrichment
│   ├── load/
│   │   ├── dimensions.py              # Load dim_user, dim_product, dim_date
│   │   ├── facts.py                   # Load fact_orders, fact_events
│   │   └── metrics.py                 # Calculate daily metrics
│   ├── quality/
│   │   └── dq_checks.py               # Data quality validation
│   └── common/
│       ├── db_utils.py                # Database connection & queries
│       └── logging_utils.py           # Logging setup
├── sql/
│   ├── 00_schemas.sql                 # Create schemas (raw, staging, warehouse, audit)
│   ├── 01_raw_tables.sql              # Raw layer DDL
│   ├── 02_staging_tables.sql          # Staging layer DDL
│   ├── 03_warehouse_tables.sql        # Warehouse (star schema) DDL
│   ├── 04_audit_tables.sql            # Audit layer DDL
│   └── 05_dim_date_seed.sql           # Populate dim_date with 3-year calendar
├── data/
│   ├── generators/
│   │   └── generate_sample_data.py    # Generate test orders, events, products
│   └── incoming/
│       ├── orders/                    # Daily order JSON files
│       ├── events/                    # Daily event CSV files
│       └── products/                  # Weekly product JSON files
├── docker-compose.yml                 # Docker setup (4 services)
├── requirements.txt                   # Python dependencies
├── README.md                          # This file
└── docs/
    ├── ARCHITECTURE.md                # Detailed design docs
    ├── QUERIES.md                     # Example SQL queries
    └── SCHEMA_DIAGRAM.md              # Visual schema
```

---

## 🚀 Common Tasks

### Generate Test Data & Run Pipeline

```bash
# Generate 1 day of test data (orders + events)
docker-compose exec airflow-scheduler python \
  /opt/airflow/data/generators/generate_sample_data.py 2025-12-22 1

# Trigger daily batch pipeline for that date
docker-compose exec airflow-scheduler airflow dags trigger \
  ecomm_warehouse_daily --exec-date 2025-12-22

# Watch the DAG in Airflow UI
# http://localhost:8080 → DAGs → ecomm_warehouse_daily → Graph
```

### Manually Trigger API Polling

```bash
# Run the API polling DAG now (doesn't wait for 10-min schedule)
docker-compose exec airflow-scheduler airflow dags trigger ecomm_api_polling

# It will fetch latest data from Fake Store API immediately
# Check Airflow UI for progress and logs
```

### Query the Warehouse

**Via Terminal:**
```bash
docker-compose exec postgres psql -U airflow -d ecommerce_warehouse -c \
  "SELECT COUNT(*) as total_orders FROM warehouse.fact_orders;"
```

**Via pgAdmin UI (recommended):**
1. Open http://localhost:5050
2. Login: `admin@example.com` / `admin`
3. Click **Tools** → **Query Tool**
4. Run SQL queries (see examples below)

### Example Analytics Queries

**Top Products by Revenue:**
```sql
SELECT 
  dp.product_name,
  COUNT(fo.order_id) as orders,
  SUM(fo.revenue) as revenue
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
GROUP BY dp.product_id, dp.product_name
ORDER BY revenue DESC
LIMIT 10;
```

**Daily Sales Summary:**
```sql
SELECT 
  dd.date,
  COUNT(fo.order_id) as orders,
  SUM(fo.revenue) as daily_revenue,
  AVG(fo.revenue) as avg_order_value
FROM warehouse.fact_orders fo
JOIN warehouse.dim_date dd ON fo.date_id = dd.date_id
GROUP BY dd.date_id, dd.date
ORDER BY dd.date DESC
LIMIT 30;
```

**Event Funnel (view → add to cart → order):**
```sql
SELECT 
  fe.event_type,
  COUNT(DISTINCT fe.user_id) as unique_users,
  COUNT(*) as total_events
FROM warehouse.fact_events fe
GROUP BY fe.event_type
ORDER BY total_events DESC;
```

**Pipeline Health Check:**
```sql
SELECT 
  run_date,
  raw_orders_count,
  staging_orders_count,
  fact_orders_count,
  dq_failed_count,
  runtime_seconds
FROM warehouse.daily_metrics
ORDER BY run_date DESC
LIMIT 10;
```

---

## 🔧 Configuration & Environment

### Default Credentials

```
Airflow:
  Username: airflow
  Password: airflow

pgAdmin:
  Email: admin@example.com
  Password: admin

PostgreSQL:
  User: airflow
  Password: airflow
  Database: ecommerce_warehouse
  Host: localhost (from host) / postgres (in Docker)
  Port: 5432
```

### Environment Variables

Create `.env` (optional, defaults work):
```env
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=ecommerce_warehouse
POSTGRES_PORT=5432
AIRFLOW_HOME=/opt/airflow
```

---

## 🧪 Testing & Troubleshooting

### Check Everything is Running

```bash
docker-compose ps
# All 4 services should show "Up"
```

### View Logs

```bash
# Airflow scheduler logs (DAGs execution)
docker-compose logs -f airflow-scheduler

# PostgreSQL logs
docker-compose logs -f postgres

# View a specific DAG task log
docker-compose exec airflow-scheduler airflow tasks logs \
  ecomm_api_polling poll_orders $(date -u +'%Y-%m-%dT%H:00:00+00:00')
```

### Verify Data Pipeline

```bash
# Count records at each layer
docker-compose exec postgres psql -U airflow -d ecommerce_warehouse << EOF
SELECT 
  (SELECT COUNT(*) FROM raw.orders_json) as raw_orders,
  (SELECT COUNT(*) FROM staging.orders_clean) as staging_orders,
  (SELECT COUNT(*) FROM warehouse.fact_orders) as fact_orders,
  (SELECT COUNT(*) FROM raw.events_csv) as raw_events,
  (SELECT COUNT(*) FROM warehouse.fact_events) as fact_events;
EOF
```

### Reset Everything

```bash
# Stop and remove all containers & data
docker-compose down -v

# Start fresh
docker-compose up -d
```

---

## 📈 Performance & Scaling

### Current Setup
- **Batch frequency:** Daily (can change)
- **Real-time polling:** Every 10 minutes
- **Storage:** Local PostgreSQL
- **Execution:** LocalExecutor (single machine)
- **Scale:** ~1,000+ orders/day, ~10,000+ events/day

### For Production

```
Current              →    Production
─────────────────────────────────────
LocalExecutor        →    KubernetesExecutor (distributed tasks)
Local Postgres       →    RDS / CloudSQL (managed, HA)
10-min polling       →    1-5 min polling (or event-driven)
Docker Desktop       →    Kubernetes / ECS / GCP Cloud Run
Single machine       →    Auto-scaling clusters
```

**Upgrade path:**
1. Replace `postgres` with RDS (change connection string in `docker-compose.yml`)
2. Add `KubernetesExecutor` to Airflow config
3. Deploy to EKS / GKE / AKS
4. Add caching layer (Redis) for hot data
5. Partition large tables by date for query performance

---

## 🤝 Contributing

Want to extend this project?

- Add new data sources (Shopify, Stripe, GA4, etc.)
- Implement ML transformations (anomaly detection, recommendations)
- Add BI dashboard integration (Metabase, Looker)
- Performance optimizations (partitioning, indexing)

---

## 📚 Additional Resources

- [Apache Airflow Docs](https://airflow.apache.org/docs/)
- [PostgreSQL Star Schema Modeling](https://en.wikipedia.org/wiki/Star_schema)
- [Fake Store API Docs](https://fakestoreapi.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

---

## 💡 Key Learnings

This project teaches you:
- ✅ **Real-time data ingestion** from APIs
- ✅ **Batch processing** from multiple file formats
- ✅ **Data warehousing** with star schema design
- ✅ **Airflow orchestration** and DAG design
- ✅ **Data quality** validation and monitoring
- ✅ **Container orchestration** with Docker
- ✅ **SQL** for OLAP and analytics
- ✅ **Python** for data transformation

---

## 📄 License

MIT License - Use freely for learning and commercial projects!

---

**Built with ❤️ for data engineers, analytics engineers, and Python developers.**

**Need help?** Check logs, review Airflow UI (http://localhost:8080), or query the database directly in pgAdmin.

**Happy data engineering!** 🎉
