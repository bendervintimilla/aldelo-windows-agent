"""
Test script to verify the complete product extraction and send pipeline.
This will extract products for ONE DAY and send them to the server.
"""
import os
import sys
import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(message)s')

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils.db_connector import get_connection
from utils.registry_reader import get_db_path_with_fallback
from tools.access_db import extract_orderheaders, extract_orderpayments, extract_orderdetails

def main():
    print("\n" + "="*60)
    print("  TEST: Extract Products and Send to Server")
    print("="*60)
    
    # Load config
    config_path = os.path.join(script_dir, 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    db_path = get_db_path_with_fallback(config)
    store_id = config.get('store_id', 'molldelrio')
    server_url = config.get('central_server_url')
    
    print(f"\nDatabase: {db_path}")
    print(f"Store ID: {store_id}")
    print(f"Server: {server_url}")
    
    # Test with December 2025 data (we know this exists)
    test_date = "2024-12-01"
    end_date = "2024-12-31"
    
    print(f"\n[1] Connecting to database...")
    conn = get_connection(db_path, strategy="oledb", read_only=True)
    
    print(f"\n[2] Extracting data for {test_date} to {end_date}...")
    
    orderheaders = extract_orderheaders(conn, test_date, end_date)
    print(f"    Orders: {len(orderheaders)}")
    
    orderpayments = extract_orderpayments(conn, test_date, end_date)
    print(f"    Payments: {len(orderpayments)}")
    
    orderdetails = extract_orderdetails(conn, test_date, end_date)
    print(f"    Products: {len(orderdetails)}")
    
    conn.close()
    
    if len(orderdetails) == 0:
        print("\n⚠️ NO PRODUCTS EXTRACTED!")
        print("The SQL query might still have issues.")
        print("\nLet me try a simpler query...")
        
        # Try simpler query without date filter
        conn = get_connection(db_path, strategy="oledb", read_only=True)
        cursor = conn.cursor()
        try:
            sql = """
            SELECT TOP 20
                ot.OrderID,
                mi.MenuItemText,
                ot.Quantity,
                ot.ExtendedPrice,
                mc.MenuCategoryText
            FROM OrderTransactions ot
            LEFT JOIN MenuItems mi ON ot.MenuItemID = mi.MenuItemID
            LEFT JOIN MenuCategories mc ON mi.MenuCategoryID = mc.MenuCategoryID
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            print(f"\nSimple query without date filter: {len(rows)} rows")
            for row in rows[:5]:
                print(f"  {row[1]} - {row[3]}")
        except Exception as e:
            print(f"Error: {e}")
        conn.close()
        return
    
    # Show sample
    print(f"\n[3] Sample products:")
    for item in orderdetails[:5]:
        print(f"    - {item['item_name']}: ${item['price']:.2f} x{item['quantity']}")
    
    # Prepare payload
    print(f"\n[4] Preparing payload...")
    payload = {
        "store_id": store_id,
        "data": {
            "orderheaders": orderheaders,
            "orderpayments": orderpayments,
            "orderdetails": orderdetails,
            "account_invoice_erp": []
        }
    }
    
    print(f"    Payload size: {len(json.dumps(payload)):,} bytes")
    
    # Send to server
    print(f"\n[5] Sending to server...")
    try:
        response = requests.post(
            server_url,
            json=payload,
            timeout=120
        )
        print(f"    Status: {response.status_code}")
        print(f"    Response: {response.text[:500]}")
        
        if response.ok:
            print("\n✅ SUCCESS! Data sent to server.")
            print("\nNow check the dashboard at:")
            print("https://aldelo-bi-production.up.railway.app")
        else:
            print("\n❌ FAILED to send data.")
    except Exception as e:
        print(f"    Error: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
