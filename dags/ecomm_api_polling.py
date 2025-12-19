# dags/ecomm_api_polling.py
"""
Real-Time API Polling DAG
Fetches data from Fake Store API every 10 minutes
Inserts into raw layer, then triggers warehouse transformation
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.extract.api_orders import extract_orders_from_api
from src.extract.api_events import extract_events_from_api
from src.extract.api_products import extract_products_from_api
from src.common.logging_utils import setup_logger

logger = setup_logger(__name__)

default_args = {
    'owner': 'data-engineering',
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
    'email_on_failure': False,
}

dag = DAG(
    'ecomm_api_polling',
    default_args=default_args,
    description='Real-time API data ingestion from Fake Store API',
    schedule_interval='*/10 * * * *',  # Every 10 minutes
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['api', 'real-time', 'polling'],
    max_active_runs=1,
)

# ============ API POLLING TASKS ============

def task_poll_orders(**context):
    """Poll Fake Store API for carts/orders"""
    logger.info("Starting API orders polling")
    run_date = context['ds']
    count = extract_orders_from_api(run_date)
    context['task_instance'].xcom_push(key='api_orders_count', value=count)
    return count


def task_poll_events(**context):
    """Poll Fake Store API for products and generate synthetic events"""
    logger.info("Starting API events polling")
    run_date = context['ds']
    count = extract_events_from_api(run_date)
    context['task_instance'].xcom_push(key='api_events_count', value=count)
    return count


def task_poll_products(**context):
    """Poll Fake Store API for products"""
    logger.info("Starting API products polling")
    run_date = context['ds']
    count = extract_products_from_api(run_date)
    context['task_instance'].xcom_push(key='api_products_count', value=count)
    return count


# Tasks

start = BashOperator(
    task_id='start',
    bash_command='echo "Starting API polling DAG"',
    dag=dag,
)

poll_orders = PythonOperator(
    task_id='poll_orders',
    python_callable=task_poll_orders,
    provide_context=True,
    dag=dag,
)

poll_events = PythonOperator(
    task_id='poll_events',
    python_callable=task_poll_events,
    provide_context=True,
    dag=dag,
)

poll_products = PythonOperator(
    task_id='poll_products',
    python_callable=task_poll_products,
    provide_context=True,
    dag=dag,
)

end = BashOperator(
    task_id='end',
    bash_command='echo "API polling complete"',
    dag=dag,
)

# Dependencies
start >> [poll_orders, poll_events, poll_products] >> end
