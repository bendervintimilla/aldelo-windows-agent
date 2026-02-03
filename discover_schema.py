import os
import json
import logging
from utils.db_connector import get_connection
from utils.registry_reader import get_db_path_with_fallback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SchemaDiscovery")

def discover_schema():
    # Load config to get db_path
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print("config.json not found")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Use the same logic as the agent for consistency
    db_path = get_db_path_with_fallback(config)
    if not db_path:
        print("Database path detection failed (check registry or set db_path in config.json)")
        return

    print(f"Connecting to: {db_path}")
    try:
        conn = get_connection(db_path, strategy="oledb", read_only=True)
        cursor = conn.cursor()
        
        tables = ['Orderheaders', 'Orderpayments', 'AccountInvoiceERP']
        
        for table in tables:
            print(f"\n--- Columns in {table} ---")
            try:
                # OLEDB specific way to get columns or just a failed select to trigger error if needed, 
                # but better to use a dummy select
                cursor.execute(f"SELECT TOP 1 * FROM {table}")
                # For our OLEDB wrapper, fetchall might be needed or just inspecting the recordset
                # Our OLEDBCursor has a recordset. Let's inspect it.
                if hasattr(cursor, 'recordset'):
                    rs = cursor.recordset
                    for i in range(rs.Fields.Count):
                        print(f"- {rs.Fields(i).Name}")
                else:
                    print("Could not inspect recordset fields")
            except Exception as e:
                print(f"Error reading {table}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    discover_schema()
