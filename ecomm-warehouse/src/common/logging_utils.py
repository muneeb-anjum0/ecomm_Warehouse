# src/common/logging_utils.py
"""Logging utilities for pipeline"""

import logging
import os
from datetime import datetime


def setup_logger(name: str, log_level: str = None) -> logging.Logger:
    """Setup a logger with consistent formatting"""
    
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # Console handler with formatting
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def log_pipeline_start(logger: logging.Logger, dag_id: str, run_date: str) -> None:
    """Log pipeline start"""
    logger.info(f"{'='*60}")
    logger.info(f"Pipeline Start: {dag_id} for {run_date}")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"{'='*60}")


def log_pipeline_end(logger: logging.Logger, dag_id: str, status: str, 
                     duration_seconds: int = None) -> None:
    """Log pipeline end"""
    logger.info(f"{'='*60}")
    logger.info(f"Pipeline End: {dag_id} - Status: {status}")
    if duration_seconds:
        logger.info(f"Duration: {duration_seconds} seconds")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"{'='*60}")


def log_task_start(logger: logging.Logger, task_name: str) -> None:
    """Log task start"""
    logger.info(f"\n>>> Starting task: {task_name}")


def log_task_end(logger: logging.Logger, task_name: str, 
                 record_count: int = None, status: str = "SUCCESS") -> None:
    """Log task end"""
    msg = f"<<< Completed task: {task_name} - Status: {status}"
    if record_count is not None:
        msg += f" (Records: {record_count})"
    logger.info(msg)
