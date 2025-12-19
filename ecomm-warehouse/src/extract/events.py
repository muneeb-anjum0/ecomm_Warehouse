# src/extract/events.py
"""Extract events from daily CSV files"""

import csv
import hashlib
from datetime import datetime
from pathlib import Path
import logging
from src.common.db_utils import DatabaseConnection

logger = logging.getLogger(__name__)


def extract_events(run_date: str, data_dir: str = "/opt/airflow/data") -> int:
    """
    Extract events from CSV file for a given run_date.
    
    Args:
        run_date: Date in format YYYY-MM-DD
        data_dir: Root data directory path
        
    Returns:
        Number of records inserted into raw layer
    """
    logger.info(f"Starting events extraction for {run_date}")
    
    # Construct file path: data/incoming/events/YYYY-MM-DD/events.csv
    events_file = Path(data_dir) / "incoming" / "events" / run_date / "events.csv"
    
    if not events_file.exists():
        logger.warning(f"Events file not found: {events_file}")
        return 0
    
    try:
        db = DatabaseConnection()
        query = """
            INSERT INTO raw.events_csv 
            (run_date, file_name, ingested_at, raw_line, event_id, user_id, product_id, event_type, event_ts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        records = []
        with open(events_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_line = ','.join(row.values())
                
                # Create event_id if not present (hash of row)
                event_id = row.get('event_id') or hashlib.md5(raw_line.encode()).hexdigest()
                
                record = (
                    run_date,
                    str(events_file),
                    datetime.now(),
                    raw_line,
                    event_id,
                    row.get('user_id'),
                    row.get('product_id'),
                    row.get('event_type'),
                    row.get('event_ts')
                )
                records.append(record)
        
        if records:
            inserted = db.execute_batch(query, records)
            logger.info(f"Inserted {inserted} events into raw.events_csv")
            return inserted
        else:
            logger.warning(f"No events found in {events_file}")
            return 0
            
    except Exception as e:
        logger.error(f"Error extracting events: {e}")
        raise


if __name__ == "__main__":
    # Test extraction
    extract_events("2025-12-19")
