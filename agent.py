"""
Windows Agent for Aldelo Database Extraction

Main agent that:
1. Auto-detects Aldelo database from Windows Registry
2. Connects using multi-strategy connector (OLEDB/ODBC)
3. Extracts from Orderheaders, Orderpayments, AccountInvoiceERP
4. Pushes data to central API server
5. Runs on scheduled interval (default: 30 minutes)

Can run as:
- Standalone script (python agent.py)
- Windows Service (python service.py install)
"""

import time
import json
import logging
import requests
import schedule
import os
from utils.registry_reader import get_db_path_with_fallback
from tools.access_db import extract_all_data

# Configure Logging
log_file = os.path.join(os.path.dirname(__file__), 'agent.log')
logging.basicConfig(
    filename=log_file, 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("WindowsAgent")


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            logger.info("Configuration loaded successfully")
            return config
    except FileNotFoundError:
        logger.error(f"config.json not found at {config_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config.json: {e}")
        return None


def job():
    """
    Main extraction job that runs on schedule.
    
    Steps:
    1. Load configuration
    2. Detect database path (registry or config)
    3. Extract data from all three Aldelo tables
    4. Push to central API
    """
    logger.info("="*60)
    logger.info("Starting extraction job")
    
    config = load_config()
    if not config:
        logger.error("Cannot proceed without valid configuration")
        return
    
    store_id = config.get("store_id")
    api_url = config.get("central_server_url")
    
    # 1. DETECT DATABASE PATH
    db_path = get_db_path_with_fallback(config)
    if not db_path:
        logger.error("Database path detection failed")
        return
    
    logger.info(f"Using database: {db_path}")
    
    # 2. EXTRACT DATA
    try:
        data = extract_all_data(db_path, run_date=None, config=config)
        
        if not data:
            logger.warning("No data extracted or extraction error occurred")
            return
        
        # Check if all tables are empty
        total_records = sum(len(v) for v in data.values())
        if total_records == 0:
            logger.info("No records found for today")
            return
        
        # 3. TRANSFORM & PUSH
        payload = {
            "store_id": store_id,
            "data": data,
            "extraction_time": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"Pushing {total_records} records to central API...")
        print(f"Pushing {total_records} records to central API...")
        
        # Retry logic for API push
        max_retries = config.get("retry_attempts", 3)
        retry_delay = config.get("retry_delay_seconds", 60)
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt}/{max_retries}...")
                response = requests.post(
                    api_url, 
                    json=payload,
                    timeout=300  # Increased from 30 to 300 seconds
                )
                
                if response.status_code == 200:
                    logger.info(f"✓ Successfully pushed data (HTTP {response.status_code})")
                    print(f"✓ Successfully pushed {total_records} records!")
                    logger.info("Extraction job complete")
                    return
                else:
                    logger.error(f"API Error: HTTP {response.status_code} - {response.text[:500]}")
                    print(f"API Error: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed (attempt {attempt}/{max_retries}): {e}")
                print(f"Connection error: {e}")
                
            # Wait before retry
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
        
        logger.error(f"Failed to push data after {max_retries} attempts")
        print(f"FAILED after {max_retries} attempts")
        
    except Exception as e:
        logger.error(f"Job failed with exception: {e}", exc_info=True)


def main():
    """
    Main entry point for standalone execution.
    Runs the extraction job on a schedule.
    """
    logger.info("="*60)
    logger.info("Windows Agent Service Started")
    logger.info("="*60)
    
    # Load config to get interval
    config = load_config()
    if config:
        interval = config.get("extraction_interval_minutes", 30)
        logger.info(f"Configured extraction interval: {interval} minutes")
    else:
        interval = 30
        logger.warning(f"Using default extraction interval: {interval} minutes")
    
    # Schedule logic
    schedule.every(interval).minutes.do(job)
    
    # Run once on startup
    logger.info("Running initial extraction job...")
    job()
    
    # Main loop
    logger.info(f"Entering main loop (extraction every {interval} minutes)")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Agent crashed: {e}", exc_info=True)

