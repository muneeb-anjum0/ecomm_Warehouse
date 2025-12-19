# Analytics Queries

This document contains production-ready SQL queries for common analytics use cases.

## 1. Revenue Analytics

### Total Revenue by Date
```sql
SELECT 
    dd.date as order_date,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.revenue) as daily_revenue,
    ROUND(AVG(fo.revenue), 2) as avg_order_value,
    MAX(fo.revenue) as max_order_value,
    MIN(fo.revenue) as min_order_value
FROM warehouse.fact_orders fo
JOIN warehouse.dim_date dd ON fo.date_id = dd.date_id
WHERE fo.status = 'paid'
AND dd.date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY dd.date
ORDER BY dd.date DESC;
```

### Revenue by Category
```sql
SELECT 
    dp.category,
    dd.year,
    dd.month,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.revenue) as category_revenue,
    ROUND(AVG(fo.revenue), 2) as avg_order_value,
    ROUND(100.0 * SUM(fo.revenue) / SUM(SUM(fo.revenue)) OVER (PARTITION BY dd.year, dd.month), 2) as revenue_pct
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
JOIN warehouse.dim_date dd ON fo.date_id = dd.date_id
WHERE fo.status = 'paid'
AND dd.year = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY dp.category, dd.year, dd.month
ORDER BY dd.month DESC, category_revenue DESC;
```

### Revenue by Brand
```sql
SELECT 
    dp.brand,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.quantity) as units_sold,
    SUM(fo.revenue) as total_revenue,
    ROUND(AVG(fo.revenue), 2) as avg_order_value,
    ROUND(AVG(fo.quantity), 2) as avg_units_per_order
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
WHERE fo.status = 'paid'
AND fo.date_id >= (SELECT TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INT)
GROUP BY dp.brand
ORDER BY total_revenue DESC;
```

## 2. Customer Analytics

### Top Customers by Spending
```sql
SELECT 
    fo.user_id,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.revenue) as total_spent,
    ROUND(AVG(fo.revenue), 2) as avg_order_value,
    MIN(fo.order_ts) as first_order_date,
    MAX(fo.order_ts) as last_order_date,
    (MAX(fo.order_ts)::DATE - MIN(fo.order_ts)::DATE) as customer_lifespan_days,
    ROUND(SUM(fo.revenue) / NULLIF((MAX(fo.order_ts)::DATE - MIN(fo.order_ts)::DATE), 0), 2) as revenue_per_day
FROM warehouse.fact_orders fo
WHERE fo.status = 'paid'
GROUP BY fo.user_id
HAVING COUNT(DISTINCT fo.order_id) >= 1
ORDER BY total_spent DESC
LIMIT 50;
```

### Repeat Customers
```sql
WITH customer_orders AS (
    SELECT 
        fo.user_id,
        COUNT(DISTINCT fo.order_id) as order_count,
        SUM(fo.revenue) as total_spent,
        MIN(fo.order_ts) as first_order_date,
        MAX(fo.order_ts) as last_order_date
    FROM warehouse.fact_orders fo
    WHERE fo.status = 'paid'
    GROUP BY fo.user_id
    HAVING COUNT(DISTINCT fo.order_id) >= 2
)
SELECT 
    COUNT(*) as repeat_customers,
    SUM(total_spent) as repeat_customer_revenue,
    ROUND(AVG(order_count), 2) as avg_orders_per_customer,
    ROUND(AVG(total_spent), 2) as avg_lifetime_value
FROM customer_orders;
```

### Customer Segmentation by Tenure
```sql
SELECT 
    CASE 
        WHEN CURRENT_DATE - du.signup_date < INTERVAL '30 days' THEN '0-30 days'
        WHEN CURRENT_DATE - du.signup_date < INTERVAL '60 days' THEN '31-60 days'
        WHEN CURRENT_DATE - du.signup_date < INTERVAL '90 days' THEN '61-90 days'
        WHEN CURRENT_DATE - du.signup_date < INTERVAL '180 days' THEN '91-180 days'
        WHEN CURRENT_DATE - du.signup_date < INTERVAL '1 year' THEN '181-365 days'
        ELSE '1+ years'
    END as tenure_bucket,
    COUNT(DISTINCT du.user_id) as user_count,
    COUNT(DISTINCT fo.order_id) as total_orders,
    ROUND(AVG(fo.revenue), 2) as avg_order_value,
    SUM(fo.revenue) as segment_revenue
FROM warehouse.dim_user du
LEFT JOIN warehouse.fact_orders fo ON du.user_id = fo.user_id AND fo.status = 'paid'
GROUP BY tenure_bucket
ORDER BY AVG(CURRENT_DATE - du.signup_date);
```

### Marketing Source Performance
```sql
SELECT 
    du.marketing_source,
    COUNT(DISTINCT du.user_id) as users_acquired,
    COUNT(DISTINCT fo.order_id) as orders_from_source,
    SUM(fo.revenue) as revenue_from_source,
    ROUND(100.0 * COUNT(DISTINCT fo.order_id) / COUNT(DISTINCT du.user_id), 2) as conversion_rate,
    ROUND(SUM(fo.revenue) / NULLIF(COUNT(DISTINCT du.user_id), 0), 2) as revenue_per_user
FROM warehouse.dim_user du
LEFT JOIN warehouse.fact_orders fo ON du.user_id = fo.user_id AND fo.status = 'paid'
GROUP BY du.marketing_source
ORDER BY revenue_from_source DESC;
```

## 3. Product Analytics

### Product Performance
```sql
SELECT 
    dp.product_id,
    dp.product_name,
    dp.category,
    dp.brand,
    COUNT(DISTINCT fo.order_id) as order_count,
    SUM(fo.quantity) as units_sold,
    SUM(fo.revenue) as total_revenue,
    ROUND(AVG(fo.revenue), 2) as avg_order_value,
    ROUND(AVG(fo.quantity), 2) as avg_units_per_order,
    dp.current_price,
    ROUND(SUM(fo.revenue) / SUM(fo.quantity), 2) as actual_avg_price
FROM warehouse.fact_orders fo
JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
WHERE fo.status = 'paid'
AND fo.date_id >= (SELECT TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INT)
GROUP BY dp.product_id, dp.product_name, dp.category, dp.brand, dp.current_price
ORDER BY total_revenue DESC
LIMIT 50;
```

### Top Products by Category
```sql
WITH ranked_products AS (
    SELECT 
        dp.category,
        dp.product_id,
        dp.product_name,
        SUM(fo.revenue) as product_revenue,
        COUNT(DISTINCT fo.order_id) as order_count,
        ROW_NUMBER() OVER (PARTITION BY dp.category ORDER BY SUM(fo.revenue) DESC) as rank
    FROM warehouse.fact_orders fo
    JOIN warehouse.dim_product dp ON fo.product_id = dp.product_id
    WHERE fo.status = 'paid'
    AND fo.date_id >= (SELECT TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INT)
    GROUP BY dp.category, dp.product_id, dp.product_name
)
SELECT *
FROM ranked_products
WHERE rank <= 5
ORDER BY category, rank;
```

## 4. Conversion & Funnel Analytics

### Event Funnel
```sql
WITH daily_events AS (
    SELECT 
        dd.date as event_date,
        COUNT(DISTINCT CASE WHEN fe.event_type = 'page_view' THEN fe.user_id END) as page_viewers,
        COUNT(DISTINCT CASE WHEN fe.event_type = 'view_product' THEN fe.user_id END) as product_viewers,
        COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END) as cart_adds,
        COUNT(DISTINCT CASE WHEN fe.event_type = 'checkout' THEN fe.user_id END) as checkouts,
        COUNT(DISTINCT CASE WHEN fe.event_type = 'purchase' THEN fe.user_id END) as purchases
    FROM warehouse.fact_events fe
    JOIN warehouse.dim_date dd ON fe.date_id = dd.date_id
    WHERE dd.date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY dd.date
)
SELECT 
    event_date,
    page_viewers,
    product_viewers,
    cart_adds,
    checkouts,
    purchases,
    ROUND(100.0 * product_viewers / NULLIF(page_viewers, 0), 2) as view_to_product_rate,
    ROUND(100.0 * cart_adds / NULLIF(product_viewers, 0), 2) as product_to_cart_rate,
    ROUND(100.0 * checkout_rate / NULLIF(cart_adds, 0), 2) as cart_to_checkout_rate,
    ROUND(100.0 * purchases / NULLIF(checkouts, 0), 2) as checkout_to_purchase_rate,
    ROUND(100.0 * purchases / NULLIF(page_viewers, 0), 2) as overall_conversion_rate
FROM daily_events
ORDER BY event_date DESC;
```

### Product-Level Conversion
```sql
SELECT 
    dp.category,
    dp.product_id,
    dp.product_name,
    COUNT(DISTINCT CASE WHEN fe.event_type = 'view_product' THEN fe.user_id END) as product_views,
    COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END) as add_to_carts,
    COUNT(DISTINCT CASE WHEN fe.event_type = 'purchase' THEN fe.user_id END) as purchases,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END) / 
          NULLIF(COUNT(DISTINCT CASE WHEN fe.event_type = 'view_product' THEN fe.user_id END), 0), 2) as atc_rate,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN fe.event_type = 'purchase' THEN fe.user_id END) / 
          NULLIF(COUNT(DISTINCT CASE WHEN fe.event_type = 'add_to_cart' THEN fe.user_id END), 0), 2) as purchase_rate
FROM warehouse.fact_events fe
JOIN warehouse.dim_product dp ON fe.product_id = dp.product_id
WHERE fe.date_id >= (SELECT TO_CHAR(CURRENT_DATE - INTERVAL '30 days', 'YYYYMMDD')::INT)
GROUP BY dp.category, dp.product_id, dp.product_name
ORDER BY purchase_rate DESC NULLS LAST;
```

## 5. Pipeline Health Monitoring

### Daily Metrics Dashboard
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
    ROUND(100.0 * fact_orders_count / NULLIF(raw_orders_count, 0), 2) as orders_completion_pct,
    ROUND(100.0 * fact_events_count / NULLIF(raw_events_count, 0), 2) as events_completion_pct,
    CASE 
        WHEN dq_failed_count = 0 THEN '✓ PASS'
        ELSE '✗ FAIL'
    END as dq_status
FROM warehouse.daily_metrics
WHERE run_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY run_date DESC;
```

### Quality Failures Trend
```sql
SELECT 
    DATE_TRUNC('week', run_date)::DATE as week_start,
    check_name,
    check_type,
    COUNT(*) as failure_count,
    ARRAY_AGG(DISTINCT failure_message) as messages
FROM audit.dq_failures
WHERE run_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY DATE_TRUNC('week', run_date), check_name, check_type
ORDER BY week_start DESC, failure_count DESC;
```

### Bad Records Audit
```sql
SELECT 
    source_table,
    failure_reason,
    COUNT(*) as bad_record_count,
    ARRAY_AGG(DISTINCT record_id LIMIT 5) as sample_ids
FROM audit.bad_records
WHERE run_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY source_table, failure_reason
ORDER BY bad_record_count DESC;
```

## 6. Advanced Time Series

### Week-over-Week Growth
```sql
WITH weekly_metrics AS (
    SELECT 
        dd.year,
        dd.week,
        SUM(fo.revenue) as weekly_revenue,
        COUNT(DISTINCT fo.order_id) as weekly_orders
    FROM warehouse.fact_orders fo
    JOIN warehouse.dim_date dd ON fo.date_id = dd.date_id
    WHERE fo.status = 'paid'
    GROUP BY dd.year, dd.week
)
SELECT 
    week,
    weekly_revenue,
    weekly_orders,
    LAG(weekly_revenue) OVER (ORDER BY year, week) as prev_week_revenue,
    ROUND(100.0 * (weekly_revenue - LAG(weekly_revenue) OVER (ORDER BY year, week)) / 
          NULLIF(LAG(weekly_revenue) OVER (ORDER BY year, week), 0), 2) as revenue_growth_pct,
    LAG(weekly_orders) OVER (ORDER BY year, week) as prev_week_orders,
    ROUND(100.0 * (weekly_orders - LAG(weekly_orders) OVER (ORDER BY year, week)) / 
          NULLIF(LAG(weekly_orders) OVER (ORDER BY year, week), 0), 2) as orders_growth_pct
FROM weekly_metrics
WHERE year = EXTRACT(YEAR FROM CURRENT_DATE)
ORDER BY week DESC;
```

### Day-of-Week Seasonality
```sql
SELECT 
    dd.day_name,
    dd.day_of_week,
    COUNT(DISTINCT dd.date) as num_days,
    ROUND(AVG(daily_revenue), 2) as avg_daily_revenue,
    ROUND(AVG(daily_orders), 2) as avg_daily_orders
FROM warehouse.dim_date dd
JOIN (
    SELECT 
        fo.date_id,
        COUNT(*) as daily_orders,
        SUM(fo.revenue) as daily_revenue
    FROM warehouse.fact_orders fo
    WHERE fo.status = 'paid'
    GROUP BY fo.date_id
) daily ON dd.date_id = daily.date_id
WHERE dd.date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY dd.day_name, dd.day_of_week
ORDER BY dd.day_of_week;
```

## Performance Optimization Tips

1. **Always filter by date_id**: Integer comparisons are faster
   ```sql
   WHERE fo.date_id >= 20251119  -- Good
   WHERE fo.order_ts >= '2025-11-19'  -- Slower
   ```

2. **Use materialized views for complex queries**:
   ```sql
   CREATE MATERIALIZED VIEW mv_daily_summary AS ...;
   REFRESH MATERIALIZED VIEW mv_daily_summary;
   ```

3. **Limit results for exploratory queries**:
   ```sql
   LIMIT 100  -- Always during development
   ```

4. **Use EXPLAIN ANALYZE to optimize**:
   ```sql
   EXPLAIN ANALYZE SELECT ...;
   ```

5. **Aggregate at the fact table level first**, then join dimensions
