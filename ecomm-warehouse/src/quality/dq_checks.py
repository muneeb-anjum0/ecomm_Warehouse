# src/quality/dq_checks.py
"""Data quality checks for the pipeline"""

import logging
from src.common.db_utils import DatabaseConnection
from datetime import datetime

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """Perform quality checks and log failures"""
    
    def __init__(self, run_date: str):
        self.run_date = run_date
        self.db = DatabaseConnection()
        self.failures = []
    
    def check_orders_volume(self) -> bool:
        """Check if orders volume is within expected range"""
        min_orders = 100
        max_orders = 500000
        
        count = self.db.get_scalar(
            "SELECT COUNT(*) FROM staging.orders_clean WHERE load_date = %s",
            (self.run_date,)
        )
        
        if count is None:
            count = 0
        
        if count < min_orders or count > max_orders:
            self.log_failure(
                "orders_volume",
                "volume",
                f"Orders count {count} outside range [{min_orders}, {max_orders}]",
                {"count": count, "min": min_orders, "max": max_orders}
            )
            return False
        
        logger.info(f"✓ Orders volume check passed: {count} records")
        return True
    
    def check_events_volume(self) -> bool:
        """Check if events volume is within expected range"""
        min_events = 500
        max_events = 2000000
        
        count = self.db.get_scalar(
            "SELECT COUNT(*) FROM staging.events_clean WHERE load_date = %s",
            (self.run_date,)
        )
        
        if count is None:
            count = 0
        
        if count < min_events or count > max_events:
            self.log_failure(
                "events_volume",
                "volume",
                f"Events count {count} outside range [{min_events}, {max_events}]",
                {"count": count, "min": min_events, "max": max_events}
            )
            return False
        
        logger.info(f"✓ Events volume check passed: {count} records")
        return True
    
    def check_orders_no_duplicates(self) -> bool:
        """Check for duplicate orders"""
        query = """
            SELECT COUNT(*) FROM (
                SELECT order_id FROM staging.orders_clean 
                WHERE load_date = %s
                GROUP BY order_id HAVING COUNT(*) > 1
            ) t
        """
        
        dup_count = self.db.get_scalar(query, (self.run_date,))
        
        if dup_count and dup_count > 0:
            self.log_failure(
                "orders_no_duplicates",
                "uniqueness",
                f"Found {dup_count} duplicate order IDs",
                {"duplicates": dup_count}
            )
            return False
        
        logger.info("✓ Orders uniqueness check passed")
        return True
    
    def check_events_no_duplicates(self) -> bool:
        """Check for duplicate events"""
        query = """
            SELECT COUNT(*) FROM (
                SELECT event_id FROM staging.events_clean 
                WHERE load_date = %s
                GROUP BY event_id HAVING COUNT(*) > 1
            ) t
        """
        
        dup_count = self.db.get_scalar(query, (self.run_date,))
        
        if dup_count and dup_count > 0:
            self.log_failure(
                "events_no_duplicates",
                "uniqueness",
                f"Found {dup_count} duplicate event IDs",
                {"duplicates": dup_count}
            )
            return False
        
        logger.info("✓ Events uniqueness check passed")
        return True
    
    def check_orders_revenue_valid(self) -> bool:
        """Check if all revenues are positive"""
        query = """
            SELECT COUNT(*) FROM staging.orders_clean 
            WHERE load_date = %s AND revenue < 0
        """
        
        invalid_count = self.db.get_scalar(query, (self.run_date,))
        
        if invalid_count and invalid_count > 0:
            self.log_failure(
                "orders_revenue_valid",
                "range",
                f"Found {invalid_count} orders with negative revenue",
                {"invalid_records": invalid_count}
            )
            return False
        
        logger.info("✓ Orders revenue validation passed")
        return True
    
    def check_timestamps_not_future(self) -> bool:
        """Check if timestamps are not in the future"""
        orders_future = self.db.get_scalar(
            "SELECT COUNT(*) FROM staging.orders_clean WHERE load_date = %s AND order_ts > NOW()",
            (self.run_date,)
        )
        
        events_future = self.db.get_scalar(
            "SELECT COUNT(*) FROM staging.events_clean WHERE load_date = %s AND event_ts > NOW()",
            (self.run_date,)
        )
        
        total_future = (orders_future or 0) + (events_future or 0)
        
        if total_future > 0:
            self.log_failure(
                "timestamps_not_future",
                "range",
                f"Found {total_future} records with future timestamps",
                {"orders": orders_future or 0, "events": events_future or 0}
            )
            return False
        
        logger.info("✓ Future timestamp check passed")
        return True
    
    def log_failure(self, check_name: str, check_type: str, message: str, details: dict):
        """Log a quality failure"""
        self.failures.append({
            'check_name': check_name,
            'check_type': check_type,
            'message': message,
            'details': details
        })
        logger.warning(f"✗ {message}")
    
    def run_all_checks(self) -> bool:
        """Run all quality checks"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Running Data Quality Checks for {self.run_date}")
        logger.info(f"{'='*60}\n")
        
        results = [
            self.check_orders_volume(),
            self.check_events_volume(),
            self.check_orders_no_duplicates(),
            self.check_events_no_duplicates(),
            self.check_orders_revenue_valid(),
            self.check_timestamps_not_future(),
        ]
        
        logger.info(f"\n{'='*60}")
        if all(results):
            logger.info("✓ All quality checks PASSED")
        else:
            logger.warning(f"✗ {len([r for r in results if not r])} checks FAILED")
        logger.info(f"{'='*60}\n")
        
        # Log failures to audit table
        if self.failures:
            self.save_failures()
        
        return all(results)
    
    def save_failures(self):
        """Save failures to audit.dq_failures"""
        try:
            query = """
                INSERT INTO audit.dq_failures 
                (run_date, check_name, check_type, failure_message, details)
                VALUES (%s, %s, %s, %s, %s)
            """
            
            for failure in self.failures:
                import json
                self.db.execute_update(
                    query,
                    (
                        self.run_date,
                        failure['check_name'],
                        failure['check_type'],
                        failure['message'],
                        json.dumps(failure['details'])
                    )
                )
            
            logger.info(f"Saved {len(self.failures)} failures to audit.dq_failures")
            
        except Exception as e:
            logger.error(f"Error saving failures to audit table: {e}")
            raise


if __name__ == "__main__":
    checker = DataQualityChecker("2025-12-19")
    passed = checker.run_all_checks()
    if not passed:
        raise Exception("Data quality checks failed!")
