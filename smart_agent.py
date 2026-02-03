"""
Smart Windows Agent v2.0 for Aldelo Database Extraction

Enhanced ETL agent with:
- Local SQLite buffer (offline resilience)
- Exponential backoff retry logic
- Heartbeat monitoring (reports status to server)
- Structured JSON logging
- Sync status tracking
- Automatic recovery from failures

Can run as:
- Standalone script (python smart_agent.py)
- Windows Service (python service.py install)
"""

import time
import json
import logging
import sqlite3
import requests
import schedule
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from utils.registry_reader import get_db_path_with_fallback
from tools.access_db import extract_all_data

# =============================================================================
# CONFIGURATION
# =============================================================================

AGENT_VERSION = "2.0.0"
BUFFER_DB_NAME = "sync_buffer.db"
HEARTBEAT_INTERVAL_MINUTES = 5
MAX_BUFFER_AGE_DAYS = 7  # Clean old buffered data after this

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure rotating file and console logging."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatters
    file_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Root logger
    logger = logging.getLogger("SmartAgent")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# =============================================================================
# LOCAL BUFFER DATABASE (SQLite)
# =============================================================================

class SyncBuffer:
    """
    Local SQLite buffer for offline resilience.
    Stores data when API is unreachable and retries later.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / BUFFER_DB_NAME
        self.db_path = str(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize buffer database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Pending sync records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_sync (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                record_count INTEGER,
                created_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # Sync history for reporting
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                record_count INTEGER,
                synced_at TEXT NOT NULL,
                duration_seconds REAL,
                status TEXT,
                error_message TEXT
            )
        """)
        
        # Agent status
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_status (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        logger.debug("Buffer database initialized")
    
    def add_pending(self, store_id: str, payload: dict, record_count: int) -> str:
        """Add data to pending sync buffer."""
        sync_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pending_sync (id, store_id, payload, record_count, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (sync_id, store_id, json.dumps(payload), record_count, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        logger.info(f"Buffered {record_count} records (ID: {sync_id[:8]}...)")
        return sync_id
    
    def get_pending(self, limit: int = 10) -> list:
        """Get pending sync records ordered by oldest first."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, store_id, payload, record_count, retry_count
            FROM pending_sync
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "store_id": r[1],
                "payload": json.loads(r[2]),
                "record_count": r[3],
                "retry_count": r[4]
            }
            for r in results
        ]
    
    def mark_synced(self, sync_id: str, duration: float):
        """Mark a pending record as successfully synced."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get record info for history
        cursor.execute("SELECT store_id, record_count FROM pending_sync WHERE id = ?", (sync_id,))
        row = cursor.fetchone()
        
        if row:
            # Add to history
            cursor.execute("""
                INSERT INTO sync_history (id, store_id, record_count, synced_at, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, 'success')
            """, (sync_id, row[0], row[1], datetime.now().isoformat(), duration))
            
            # Remove from pending
            cursor.execute("DELETE FROM pending_sync WHERE id = ?", (sync_id,))
        
        conn.commit()
        conn.close()
    
    def mark_failed(self, sync_id: str, error: str):
        """Update retry count and error for failed sync."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE pending_sync 
            SET retry_count = retry_count + 1, last_error = ?
            WHERE id = ?
        """, (error, sync_id))
        
        conn.commit()
        conn.close()
    
    def get_stats(self) -> dict:
        """Get buffer statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(record_count) FROM pending_sync WHERE status = 'pending'")
        pending = cursor.fetchone()
        
        cursor.execute("""
            SELECT COUNT(*), SUM(record_count) 
            FROM sync_history 
            WHERE synced_at > datetime('now', '-24 hours')
        """)
        last_24h = cursor.fetchone()
        
        conn.close()
        
        return {
            "pending_batches": pending[0] or 0,
            "pending_records": pending[1] or 0,
            "synced_24h_batches": last_24h[0] or 0,
            "synced_24h_records": last_24h[1] or 0
        }
    
    def cleanup_old(self, days: int = MAX_BUFFER_AGE_DAYS):
        """Remove old pending and history records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("DELETE FROM pending_sync WHERE created_at < ?", (cutoff,))
        cursor.execute("DELETE FROM sync_history WHERE synced_at < ?", (cutoff,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old records")


# =============================================================================
# SMART AGENT
# =============================================================================

class SmartAgent:
    """
    Enhanced ETL agent with offline resilience and monitoring.
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.buffer = SyncBuffer()
        self.last_heartbeat = None
        self.last_sync = None
        self.sync_errors = 0
        
    def _load_config(self) -> dict:
        """Load configuration from config.json."""
        config_path = Path(__file__).parent / "config.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config
        except FileNotFoundError:
            logger.error(f"config.json not found at {config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config.json: {e}")
            return {}
    
    def _get_api_base(self) -> str:
        """Get base API URL from config."""
        url = self.config.get("central_server_url", "")
        # Remove /ingest if present to get base URL
        if url.endswith("/ingest"):
            return url[:-7]
        return url.rsplit("/api/", 1)[0] if "/api/" in url else url
    
    def send_heartbeat(self):
        """Send heartbeat to central server with agent status."""
        try:
            base_url = self._get_api_base()
            if not base_url:
                return
            
            stats = self.buffer.get_stats()
            
            payload = {
                "store_id": self.config.get("store_id"),
                "agent_version": AGENT_VERSION,
                "timestamp": datetime.now().isoformat(),
                "status": "healthy" if self.sync_errors < 3 else "degraded",
                "last_sync": self.last_sync,
                "pending_records": stats["pending_records"],
                "synced_24h": stats["synced_24h_records"],
                "uptime_seconds": int(time.time() - getattr(self, '_start_time', time.time()))
            }
            
            response = requests.post(
                f"{base_url}/api/agent/heartbeat",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.last_heartbeat = datetime.now()
                logger.debug("Heartbeat sent successfully")
            else:
                logger.warning(f"Heartbeat failed: HTTP {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Heartbeat error: {e}")
    
    def extract_data(self) -> tuple:
        """
        Extract data from Aldelo database.
        Returns: (data_dict, record_count) or (None, 0) on failure
        """
        db_path = get_db_path_with_fallback(self.config)
        if not db_path:
            logger.error("Database path detection failed")
            return None, 0
        
        logger.info(f"Extracting from: {db_path}")
        
        try:
            data = extract_all_data(db_path, run_date=None, config=self.config)
            
            if not data:
                logger.warning("No data extracted")
                return None, 0
            
            total_records = sum(len(v) for v in data.values())
            logger.info(f"Extracted {total_records} records")
            
            return data, total_records
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return None, 0
    
    def push_to_api(self, payload: dict, sync_id: str = None) -> bool:
        """
        Push data to central API with exponential backoff.
        Returns True on success, False on failure.
        """
        api_url = self.config.get("central_server_url")
        max_retries = self.config.get("retry_attempts", 5)
        base_delay = self.config.get("retry_delay_seconds", 30)
        
        start_time = time.time()
        
        for attempt in range(1, max_retries + 1):
            try:
                # Exponential backoff: 30s, 60s, 120s, 240s, 480s
                delay = base_delay * (2 ** (attempt - 1))
                
                logger.info(f"API push attempt {attempt}/{max_retries}")
                
                response = requests.post(
                    api_url,
                    json=payload,
                    timeout=300
                )
                
                if response.status_code == 200:
                    duration = time.time() - start_time
                    logger.info(f"✓ Successfully pushed data in {duration:.1f}s")
                    
                    if sync_id:
                        self.buffer.mark_synced(sync_id, duration)
                    
                    self.last_sync = datetime.now().isoformat()
                    self.sync_errors = 0
                    return True
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.error(f"API error: {error_msg}")
                    
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                logger.error(f"Connection error: {error_msg}")
            
            # Wait before retry (not on last attempt)
            if attempt < max_retries:
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
        
        # All retries failed
        self.sync_errors += 1
        if sync_id:
            self.buffer.mark_failed(sync_id, error_msg)
        
        return False
    
    def sync_pending(self):
        """Try to sync any pending buffered data."""
        pending = self.buffer.get_pending(limit=5)
        
        if not pending:
            return
        
        logger.info(f"Processing {len(pending)} pending sync batches")
        
        for item in pending:
            # Skip if too many retries
            if item["retry_count"] >= 10:
                logger.warning(f"Skipping {item['id'][:8]}... (too many retries)")
                continue
            
            success = self.push_to_api(item["payload"], sync_id=item["id"])
            
            if not success:
                # Stop trying pending items if API is down
                logger.warning("API unreachable, stopping pending sync")
                break
    
    def _chunk_data(self, data: dict, chunk_size: int = 5000) -> list:
        """
        Split large data into smaller chunks to avoid server timeouts.
        Returns list of (chunk_data, chunk_count) tuples.
        """
        orderheaders = data.get('orderheaders', [])
        orderpayments = data.get('orderpayments', [])
        invoices = data.get('accountinvoiceerp', [])
        
        # If data is small enough, return as single chunk
        total = len(orderheaders) + len(orderpayments) + len(invoices)
        if total <= chunk_size:
            return [(data, total)]
        
        chunks = []
        
        # Chunk orderheaders (main data)
        for i in range(0, len(orderheaders), chunk_size):
            chunk_orders = orderheaders[i:i + chunk_size]
            chunk_data = {
                'orderheaders': chunk_orders,
                'orderpayments': [],  # Will be handled separately
                'accountinvoiceerp': []
            }
            chunks.append((chunk_data, len(chunk_orders)))
        
        # Chunk orderpayments
        for i in range(0, len(orderpayments), chunk_size):
            chunk_payments = orderpayments[i:i + chunk_size]
            chunk_data = {
                'orderheaders': [],
                'orderpayments': chunk_payments,
                'accountinvoiceerp': []
            }
            chunks.append((chunk_data, len(chunk_payments)))
        
        # Chunk invoices
        for i in range(0, len(invoices), chunk_size):
            chunk_invoices = invoices[i:i + chunk_size]
            chunk_data = {
                'orderheaders': [],
                'orderpayments': [],
                'accountinvoiceerp': chunk_invoices
            }
            chunks.append((chunk_data, len(chunk_invoices)))
        
        logger.info(f"Split {total} records into {len(chunks)} chunks of max {chunk_size}")
        return chunks

    def run_extraction_job(self):
        """Main extraction and sync job with chunking for large datasets."""
        logger.info("=" * 60)
        logger.info("Starting extraction job")
        
        # 1. First, try to sync any pending data
        self.sync_pending()
        
        # 2. Extract new data
        data, record_count = self.extract_data()
        
        if not data or record_count == 0:
            logger.info("No new data to sync")
            return
        
        # 3. Chunk data if too large
        chunks = self._chunk_data(data, chunk_size=5000)
        
        success_count = 0
        failed_count = 0
        
        for idx, (chunk_data, chunk_count) in enumerate(chunks):
            logger.info(f"Processing chunk {idx + 1}/{len(chunks)} ({chunk_count} records)")
            
            # Build payload for this chunk
            payload = {
                "store_id": self.config.get("store_id"),
                "data": chunk_data,
                "extraction_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "agent_version": AGENT_VERSION,
                "chunk_info": {
                    "chunk_number": idx + 1,
                    "total_chunks": len(chunks),
                    "chunk_records": chunk_count
                }
            }
            
            # Try to push this chunk
            success = self.push_to_api(payload)
            
            if success:
                success_count += chunk_count
            else:
                failed_count += chunk_count
                # Buffer failed chunk for later
                self.buffer.add_pending(
                    self.config.get("store_id"),
                    payload,
                    chunk_count
                )
                logger.warning(f"Chunk {idx + 1} buffered for later sync")
        
        logger.info(f"Extraction complete: {success_count} synced, {failed_count} buffered")
        logger.info("Extraction job complete")
    
    def run(self):
        """Main agent loop."""
        self._start_time = time.time()
        
        logger.info("=" * 60)
        logger.info(f"Smart Agent v{AGENT_VERSION} Started")
        logger.info(f"Store ID: {self.config.get('store_id')}")
        logger.info("=" * 60)
        
        # Get interval from config
        interval = self.config.get("extraction_interval_minutes", 30)
        
        # Schedule jobs
        schedule.every(interval).minutes.do(self.run_extraction_job)
        schedule.every(HEARTBEAT_INTERVAL_MINUTES).minutes.do(self.send_heartbeat)
        schedule.every(1).days.do(self.buffer.cleanup_old)
        
        # Run initial jobs
        logger.info("Running initial extraction...")
        self.run_extraction_job()
        self.send_heartbeat()
        
        # Main loop
        logger.info(f"Entering main loop (extraction every {interval} min, heartbeat every {HEARTBEAT_INTERVAL_MINUTES} min)")
        
        while True:
            schedule.run_pending()
            time.sleep(1)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    try:
        agent = SmartAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Agent stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Agent crashed: {e}", exc_info=True)
        raise
