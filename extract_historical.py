"""
Aldelo Historical Data Extraction Script
=========================================
This script extracts ALL historical data from Aldelo POS and sends it to the cloud.

Run this ONCE to load all historical data, then use the regular agent for daily updates.

Usage:
    python extract_historical.py

Requirements:
    - Python 3.8+
    - pywin32, requests
    - Aldelo database accessible
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('historical_extraction.log')
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from tools.access_db import extract_all_data


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(script_dir, 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def get_oldest_date(db_path):
    """
    Auto-detect the oldest date in the Aldelo database.
    Queries MIN(OrderDateTime) from Orderheaders to find the earliest record.
    
    Returns:
        tuple: (year, month) of the oldest record, or (2024, 1) as fallback.
    """
    from utils.db_connector import get_connection
    
    try:
        conn = get_connection(db_path, strategy="oledb", read_only=True)
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(OrderDateTime) FROM Orderheaders WHERE OrderDateTime IS NOT NULL")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if result and result[0] and result[0][0]:
            oldest = result[0][0]
            logger.info(f"Oldest record found: {oldest}")
            return oldest.year, oldest.month
        
        logger.warning("No records found, using default 2024-01")
        return 2024, 1
        
    except Exception as e:
        logger.error(f"Could not detect oldest date: {e}")
        logger.info("Using fallback: 2024-01")
        return 2024, 1


def extract_month_data(db_path, year, month, config):
    """Extract data for a specific month."""
    # Calculate start and end dates for the month
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    # Adjust end date to last day of month
    end_dt = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=1)
    end_date = end_dt.strftime('%Y-%m-%d')
    
    logger.info(f"📅 Extracting {year}-{month:02d} ({start_date} to {end_date})")
    
    # Create a config with specific dates
    month_config = config.copy()
    month_config['start_date'] = start_date
    month_config['end_date'] = end_date
    month_config['lookback_days'] = 31  # Max for a month
    
    # Use the existing extract function with date override
    from utils.db_connector import get_connection
    
    try:
        conn = get_connection(db_path, strategy="oledb", read_only=True)
        
        # Extract orderheaders, orderpayments, AND orderdetails for this month
        from tools.access_db import extract_orderheaders, extract_orderpayments, extract_orderdetails
        
        orderheaders = extract_orderheaders(conn, start_date, end_date)
        orderpayments = extract_orderpayments(conn, start_date, end_date)
        orderdetails = extract_orderdetails(conn, start_date, end_date)  # Products!
        
        conn.close()
        
        logger.info(f"  → Orders: {len(orderheaders)}, Payments: {len(orderpayments)}, Products: {len(orderdetails)}")
        
        return {
            "orderheaders": orderheaders,
            "orderpayments": orderpayments,
            "orderdetails": orderdetails,  # Include product data!
            "account_invoice_erp": []  # Skip for historical
        }
        
    except Exception as e:
        logger.error(f"Error extracting {year}-{month:02d}: {e}")
        return None


def send_to_server(data, store_id, server_url):
    """Send extracted data to the central server."""
    if not data:
        return False
        
    total_records = len(data.get('orderheaders', []))
    if total_records == 0:
        logger.info("  → No records to send")
        return True
    
    payload = {
        "store_id": store_id,
        "data": data
    }
    
    try:
        logger.info(f"  📤 Sending {total_records} orders to server...")
        response = requests.post(
            server_url,
            json=payload,
            timeout=120  # 2 minute timeout for large batches
        )
        
        if response.ok:
            result = response.json()
            logger.info(f"  ✅ Success: {result.get('message', 'OK')}")
            return True
        else:
            logger.error(f"  ❌ Server error: {response.status_code} - {response.text}")
            return False
            
    except requests.Timeout:
        logger.error("  ❌ Request timeout - try again")
        return False
    except Exception as e:
        logger.error(f"  ❌ Send error: {e}")
        return False


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     🤖 ALDELO HISTORICAL DATA EXTRACTION                        ║
║     ─────────────────────────────────────────────────────────────║
║     This will extract ALL historical data from your Aldelo DB   ║
║     and send it to the cloud dashboard.                         ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Load config
    config = load_config()
    
    # Allow command-line override of database path
    import argparse
    parser = argparse.ArgumentParser(description='Extract historical data from Aldelo')
    parser.add_argument('--db', help='Path to specific database file to extract from')
    args = parser.parse_args()
    
    db_path = args.db if args.db else config.get('db_path')
    store_id = config.get('store_id', 'unknown')
    server_url = config.get('central_server_url')
    
    logger.info(f"Store ID: {store_id}")
    logger.info(f"Database: {db_path}")
    logger.info(f"Server: {server_url}")
    
    # Check database exists
    if not os.path.exists(db_path):
        logger.error(f"❌ Database not found: {db_path}")
        logger.error("Please update config.json with the correct db_path")
        return
    
    # Determine date range to extract
    # AUTO-DETECT: Find the oldest record in the database
    current_date = datetime.now()
    start_year, start_month = get_oldest_date(db_path)
    
    logger.info(f"\n🔄 Starting extraction from {start_year}-{start_month:02d} to {current_date.strftime('%Y-%m')}\n")
    
    # Extract month by month
    total_sent = 0
    months_processed = 0
    
    year = start_year
    month = start_month
    
    while True:
        # Check if we've gone past current date
        if year > current_date.year or (year == current_date.year and month > current_date.month):
            break
        
        # Extract this month's data
        data = extract_month_data(db_path, year, month, config)
        
        if data:
            records = len(data.get('orderheaders', []))
            total_sent += records
            
            if records > 0:
                # Send to server
                success = send_to_server(data, store_id, server_url)
                if not success:
                    logger.warning(f"  ⚠️ Will retry {year}-{month:02d} later")
            
            months_processed += 1
        
        # Move to next month
        month += 1
        if month > 12:
            month = 1
            year += 1
        
        # Small delay to avoid overwhelming the server
        time.sleep(1)
    
    # Summary
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║     ✅ EXTRACTION COMPLETE                                       ║
║     ─────────────────────────────────────────────────────────────║
║     Months processed: {months_processed:3d}                                         ║
║     Total orders sent: {total_sent:,}                                       ║
║                                                                  ║
║     🌐 View your dashboard at:                                   ║
║     https://aldelo-bi-production.up.railway.app                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
