import os
import json
import logging
from utils.db_connector import get_connection
from utils.registry_reader import get_db_path_with_fallback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataCheck")

def check_dates():
    config_path = 'config.json'
    if not os.path.exists(config_path):
        print("config.json not found")
        return

    with open(config_path, 'r') as f:
        config = json.load(f)
    
    db_path = get_db_path_with_fallback(config)
    if not db_path:
        print("Database path detection failed")
        return

    print(f"Connecting to: {db_path}")
    try:
        conn = get_connection(db_path, strategy="oledb", read_only=True)
        cursor = conn.cursor()
        
        queries = {
            'Orderheaders': "SELECT MIN(OrderDateTime), MAX(OrderDateTime), COUNT(*) FROM Orderheaders",
            'Orderpayments': "SELECT MIN(PaymentDateTime), MAX(PaymentDateTime), COUNT(*) FROM Orderpayments",
            'AccountInvoiceERP': "SELECT MIN(FechaEntrega), MAX(FechaEntrega), COUNT(*) FROM AccountInvoiceERP"
        }
        
        for table, sql in queries.items():
            print(f"\n--- Data in {table} ---")
            try:
                cursor.execute(sql)
                rows = cursor.fetchall()
                if rows:
                    min_date, max_date, count = rows[0]
                    print(f"Total Rows: {count}")
                    print(f"Oldest Record: {min_date}")
                    print(f"Newest Record: {max_date}")
                else:
                    print("Table is empty")
            except Exception as e:
                print(f"Error checking {table}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_dates()
