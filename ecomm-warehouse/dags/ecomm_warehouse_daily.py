# dags/ecomm_warehouse_daily.py
"""
E-commerce Analytics Warehouse - Daily Pipeline DAG

Ingests raw data -> Cleans in staging -> Loads to warehouse -> Quality checks -> Metrics
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
import logging
import sys
import os
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.common.logging_utils import setup_logger, log_pipeline_start, log_pipeline_end
from src.extract.orders import extract_orders
from src.extract.events import extract_events
from src.extract.products import extract_products
from src.transform.orders import transform_orders_to_staging
from src.transform.events import transform_events_to_staging
from src.transform.products import transform_products_to_staging
from src.load.dimensions import load_dim_date, load_dim_product, load_dim_user
from src.load.facts import load_fact_orders, load_fact_events
from src.load.metrics import load_daily_metrics
from src.quality.dq_checks import DataQualityChecker

logger = setup_logger(__name__)

# DAG configuration
default_args = {
    'owner': 'data-engineering',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    'ecomm_warehouse_daily',
    default_args=default_args,
    description='E-commerce Analytics Warehouse Daily Pipeline',
    schedule_interval='0 2 * * *',  # Run at 2 AM daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['warehouse', 'analytics'],
    max_active_runs=1,
)


# ============ EXTRACT TASKS ============

def task_extract_orders(**context):
    """Extract orders from daily JSON file"""
    run_date = context['ds']
    logger.info(f"Extracting orders for {run_date}")
    count = extract_orders(run_date)
    context['task_instance'].xcom_push(key='orders_count', value=count)
    return count


def task_extract_events(**context):
    """Extract events from daily CSV file"""
    run_date = context['ds']
    logger.info(f"Extracting events for {run_date}")
    count = extract_events(run_date)
    context['task_instance'].xcom_push(key='events_count', value=count)
    return count


def task_extract_products(**context):
    """Extract products from API (weekly, run on Mondays)"""
    run_date = context['ds']
    from datetime import datetime as dt
    
    # Check if today is Monday
    if dt.strptime(run_date, '%Y-%m-%d').weekday() == 0:
        logger.info(f"Extracting products for {run_date} (Monday)")
        count = extract_products(run_date)
        context['task_instance'].xcom_push(key='products_count', value=count)
        return count
    else:
        logger.info(f"Skipping products extraction (not Monday): {run_date}")
        return 0


# ============ TRANSFORM TASKS ============

def task_transform_orders(**context):
    """Transform raw orders to staging"""
    run_date = context['ds']
    logger.info(f"Transforming orders for {run_date}")
    count = transform_orders_to_staging(run_date)
    context['task_instance'].xcom_push(key='orders_staging_count', value=count)
    return count


def task_transform_events(**context):
    """Transform raw events to staging"""
    run_date = context['ds']
    logger.info(f"Transforming events for {run_date}")
    count = transform_events_to_staging(run_date)
    context['task_instance'].xcom_push(key='events_staging_count', value=count)
    return count


def task_transform_products(**context):
    """Transform raw products to staging"""
    run_date = context['ds']
    # Only run if products were extracted
    ti = context['task_instance']
    products_count = ti.xcom_pull(task_ids='extract_products', key='products_count')
    
    if products_count and products_count > 0:
        logger.info(f"Transforming products for {run_date}")
        count = transform_products_to_staging(run_date)
        ti.xcom_push(key='products_staging_count', value=count)
        return count
    else:
        logger.info("Skipping products transformation (no products extracted)")
        return 0


# ============ QUALITY CHECKS ============

def task_dq_checks(**context):
    """Run all data quality checks"""
    run_date = context['ds']
    logger.info(f"Running quality checks for {run_date}")
    
    checker = DataQualityChecker(run_date)
    passed = checker.run_all_checks()
    
    if not passed:
        raise Exception(f"Data quality checks failed for {run_date}")
    
    return True


# ============ LOAD TASKS ============

def task_load_dim_date(**context):
    """Load date dimension"""
    run_date = context['ds']
    logger.info(f"Loading dim_date for {run_date}")
    count = load_dim_date(run_date)
    return count


def task_load_dim_product(**context):
    """Load product dimension"""
    run_date = context['ds']
    logger.info(f"Loading dim_product for {run_date}")
    count = load_dim_product(run_date)
    context['task_instance'].xcom_push(key='dim_product_count', value=count)
    return count


def task_load_dim_user(**context):
    """Load user dimension"""
    run_date = context['ds']
    logger.info(f"Loading dim_user for {run_date}")
    count = load_dim_user(run_date)
    context['task_instance'].xcom_push(key='dim_user_count', value=count)
    return count


def task_load_fact_orders(**context):
    """Load orders fact table"""
    run_date = context['ds']
    logger.info(f"Loading fact_orders for {run_date}")
    count = load_fact_orders(run_date)
    context['task_instance'].xcom_push(key='fact_orders_count', value=count)
    return count


def task_load_fact_events(**context):
    """Load events fact table"""
    run_date = context['ds']
    logger.info(f"Loading fact_events for {run_date}")
    count = load_fact_events(run_date)
    context['task_instance'].xcom_push(key='fact_events_count', value=count)
    return count


# ============ METRICS ============

def task_compute_metrics(**context):
    """Compute and load daily metrics"""
    run_date = context['ds']
    logger.info(f"Computing metrics for {run_date}")
    
    # Retrieve runtime (approximate)
    start_time = context['dag_run'].start_date
    end_time = datetime.utcnow()
    runtime_seconds = int((end_time - start_time.replace(tzinfo=None)).total_seconds())
    
    load_daily_metrics(run_date, runtime_seconds)
    return True


# ============ DAG STRUCTURE ============

start = DummyOperator(
    task_id='start',
    dag=dag,
)

# Extract layer
extract_orders_task = PythonOperator(
    task_id='extract_orders',
    python_callable=task_extract_orders,
    provide_context=True,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

extract_events_task = PythonOperator(
    task_id='extract_events',
    python_callable=task_extract_events,
    provide_context=True,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

extract_products_task = PythonOperator(
    task_id='extract_products',
    python_callable=task_extract_products,
    provide_context=True,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

# Transform layer
transform_orders_task = PythonOperator(
    task_id='transform_orders_to_staging',
    python_callable=task_transform_orders,
    provide_context=True,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

transform_events_task = PythonOperator(
    task_id='transform_events_to_staging',
    python_callable=task_transform_events,
    provide_context=True,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

transform_products_task = PythonOperator(
    task_id='transform_products_to_staging',
    python_callable=task_transform_products,
    provide_context=True,
    execution_timeout=timedelta(minutes=30),
    dag=dag,
)

# Quality checks
dq_checks_task = PythonOperator(
    task_id='dq_checks',
    python_callable=task_dq_checks,
    provide_context=True,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

# Load dimensions
load_dim_date_task = PythonOperator(
    task_id='load_dim_date',
    python_callable=task_load_dim_date,
    provide_context=True,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

load_dim_product_task = PythonOperator(
    task_id='load_dim_product',
    python_callable=task_load_dim_product,
    provide_context=True,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

load_dim_user_task = PythonOperator(
    task_id='load_dim_user',
    python_callable=task_load_dim_user,
    provide_context=True,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

# Load facts
load_fact_orders_task = PythonOperator(
    task_id='load_fact_orders',
    python_callable=task_load_fact_orders,
    provide_context=True,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

load_fact_events_task = PythonOperator(
    task_id='load_fact_events',
    python_callable=task_load_fact_events,
    provide_context=True,
    execution_timeout=timedelta(minutes=20),
    dag=dag,
)

# Metrics
compute_metrics_task = PythonOperator(
    task_id='compute_daily_metrics',
    python_callable=task_compute_metrics,
    provide_context=True,
    execution_timeout=timedelta(minutes=10),
    dag=dag,
)

end = DummyOperator(
    task_id='end',
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# Set dependencies
start >> [extract_orders_task, extract_events_task, extract_products_task]

extract_orders_task >> transform_orders_task
extract_events_task >> transform_events_task
extract_products_task >> transform_products_task

[transform_orders_task, transform_events_task, transform_products_task] >> dq_checks_task

dq_checks_task >> [load_dim_date_task, load_dim_product_task, load_dim_user_task]

load_dim_date_task >> [load_fact_orders_task, load_fact_events_task]
load_dim_product_task >> [load_fact_orders_task, load_fact_events_task]
load_dim_user_task >> [load_fact_orders_task, load_fact_events_task]

[load_fact_orders_task, load_fact_events_task] >> compute_metrics_task

compute_metrics_task >> end
