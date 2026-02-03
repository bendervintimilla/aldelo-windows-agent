import os
import sys
import json
import socket
import logging
import requests
import datetime
import traceback
from typing import Dict, Any, List

# Setup simple logging to both file and console
log_file = 'agent_doctor.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AgentDoctor")

def print_section(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def load_config() -> Dict[str, Any]:
    print_section("1. CONFIGURATION CHECK")
    config_path = 'config.json'
    
    if not os.path.exists(config_path):
        logger.error("❌ config.json NOT FOUND!")
        logger.error(f"Looking in: {os.getcwd()}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info("✅ config.json is valid JSON")
        
        # Check required fields
        required = ['store_id', 'central_server_url', 'db_path']
        missing = [k for k in required if k not in config]
        
        if missing:
            logger.error(f"❌ Missing required fields: {', '.join(missing)}")
            return None
        
        logger.info(f"Store ID: {config.get('store_id')}")
        logger.info(f"DB Path: {config.get('db_path')}")
        logger.info(f"URL: {config.get('central_server_url')}")
        return config
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ config.json INVALID JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error reading config: {e}")
        return None

def check_db_file(db_path: str) -> bool:
    print_section("2. DATABASE FILE CHECK")
    
    if not os.path.exists(db_path):
        logger.error(f"❌ Database file NOT FOUND at: {db_path}")
        
        # Try to suggest common locations
        common_paths = [
            r"C:\ProgramData\Aldelo\Aldelo For Restaurants\Databases\Live",
            r"C:\Aldelo\Data"
        ]
        
        logger.info("  Searching common locations...")
        for base in common_paths:
            if os.path.exists(base):
                logger.info(f"  Found directory: {base}")
                try:
                    files = [f for f in os.listdir(base) if f.lower().endswith('.mdb')]
                    if files:
                        logger.info(f"  Available .mdb files: {files}")
                except:
                    pass
        return False
        
    logger.info("✅ Database file exists")
    
    # Check permissions
    try:
        with open(db_path, 'rb') as f:
            header = f.read(10)
        logger.info("✅ Database file is readable")
        return True
    except PermissionError:
        logger.error("❌ PERMISSION DENIED: Cannot read database file. Try running as Administrator.")
        return False
    except Exception as e:
        logger.error(f"❌ Error reading file: {e}")
        return False

def check_connectivity(url: str):
    print_section("3. CONNECTIVITY CHECK")
    
    # 1. Internet Check
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        logger.info("✅ Internet connection active")
    except OSError:
        logger.error("❌ NO INTERNET CONNECTION")
        return False

    # 2. DNS Resolution
    try:
        hostname = url.split("//")[-1].split("/")[0]
        ip = socket.gethostbyname(hostname)
        logger.info(f"✅ DNS Resolved {hostname} -> {ip}")
    except Exception as e:
        logger.error(f"❌ DNS FAILED for {url}: {e}")
        return False
        
    # 3. HTTP Check
    try:
        # Check health endpoint if possible, else root
        base_url = url.rsplit('/api', 1)[0]
        health_url = f"{base_url}/api/health"
        
        logger.info(f"  Pinging {health_url}...")
        resp = requests.get(health_url, timeout=10)
        
        if resp.status_code == 200:
            logger.info(f"✅ API Health Check PASSED (200 OK)")
            return True
        else:
            logger.warning(f"⚠️ API returned status {resp.status_code}")
            return True # Still reachable
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ CONNECTION REFUSED - Server might be down or blocked by firewall")
        return False
    except Exception as e:
        logger.error(f"❌ API Check Failed: {e}")
        return False

def test_db_connection(db_path: str):
    print_section("4. ODBC/OLEDB DRIVER CHECK")
    
    conn_str_oledb = f"Provider=Microsoft.Jet.OLEDB.4.0;Data Source={db_path};"
    conn_str_odbc = f"Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_path};"
    
    success = False
    
    # Try pyodbc if available
    try:
        import pyodbc
        logger.info("✅ pyodbc library installed")
        
        # Test ODBC
        try:
            conn = pyodbc.connect(conn_str_odbc)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Orderheaders")
            count = cursor.fetchone()[0]
            logger.info(f"✅ ODBC Connection SUCCESS! (OrderHeaders: {count})")
            conn.close()
            success = True
        except Exception as e:
            logger.error(f"❌ ODBC Connection FAILED: {e}")
            
    except ImportError:
        logger.warning("⚠️ pyodbc not installed")

    # Try win32com (ADODB) if available - this is what we use in production usually
    if not success:
        try:
            import win32com.client
            logger.info("✅ pywin32 library installed")
            
            try:
                conn = win32com.client.Dispatch('ADODB.Connection')
                conn.Open(conn_str_oledb)
                rs = win32com.client.Dispatch('ADODB.Recordset')
                rs.Open("SELECT COUNT(*) FROM Orderheaders", conn)
                count = rs.Fields(0).Value
                logger.info(f"✅ OLEDB (ADODB) Connection SUCCESS! (OrderHeaders: {count})")
                success = True
                conn.Close()
            except Exception as e:
                logger.error(f"❌ OLEDB Connection FAILED: {e}")
                
        except ImportError:
            logger.warning("⚠️ pywin32 not installed")
            
    if success:
        logger.info("✅ DATABASE ACCESS CONFIRMED")
    else:
        logger.error("❌ CRITICAL: NO WORKING DATABASE DRIVER FOUND")

def main():
    print("*"*60)
    print("   ALDELO AGENT DOCTOR v1.0   ")
    print("   Diagnosing connection & configuration issues")
    print("*"*60)
    
    config = load_config()
    if not config:
        print("\n❌ ABORTING: Invalid Configuration")
        input("Press Enter to exit...")
        return

    db_path = config.get('db_path')
    url = config.get('central_server_url')
    
    # Run Checks
    db_file_ok = check_db_file(db_path)
    if db_file_ok:
        test_db_connection(db_path)
        
    check_connectivity(url)
    
    print_section("DIAGNOSIS COMPLETE")
    print(f"Log saved to: {os.path.abspath(log_file)}")
    print("Please send this log file to support if issues persist.")
    input("Press Enter to close...")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        input("Crashed. Press Enter...")
