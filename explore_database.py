"""
Aldelo Database Schema Explorer v3
Simple and robust - just queries the database directly.
"""
import os
import json
import logging
from utils.db_connector import get_connection
from utils.registry_reader import get_db_path_with_fallback

logging.basicConfig(level=logging.INFO)

def explore_all_tables():
    """List ALL tables in the Aldelo database."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    
    if not os.path.exists(config_path):
        print("ERROR: config.json not found")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    db_path = get_db_path_with_fallback(config)
    if not db_path:
        print("ERROR: Database path not found")
        return
    
    print("=" * 70)
    print("  ALDELO DATABASE SCHEMA EXPLORER v3")
    print("=" * 70)
    print(f"\nDatabase: {db_path}\n")
    
    try:
        conn = get_connection(db_path, strategy="oledb", read_only=True)
        cursor = conn.cursor()
        
        # Get tables using ADOX with the raw ADODB connection
        print("Discovering all tables...\n")
        
        try:
            import win32com.client
            cat = win32com.client.Dispatch("ADOX.Catalog")
            # Access the raw ADODB connection from our wrapper
            cat.ActiveConnection = conn.conn  # The internal conn attribute
            
            user_tables = []
            for table in cat.Tables:
                if table.Type == "TABLE":
                    user_tables.append(table.Name)
            
            print(f"Found {len(user_tables)} tables!\n")
            print("-" * 40)
            
            # First just list all tables
            for i, table_name in enumerate(sorted(user_tables), 1):
                print(f"  {i:2}. {table_name}")
            
            print("\n" + "=" * 70)
            print("  DETAILED TABLE INFO")
            print("=" * 70)
            
            # Then get details for each
            for table_name in sorted(user_tables):
                print(f"\n{'─'*60}")
                print(f"📁 {table_name}")
                print("─"*60)
                
                try:
                    cursor.execute(f"SELECT TOP 1 * FROM [{table_name}]")
                    
                    if hasattr(cursor, 'recordset') and cursor.recordset:
                        rs = cursor.recordset
                        columns = []
                        for i in range(rs.Fields.Count):
                            columns.append(rs.Fields(i).Name)
                        
                        print(f"Columns: {', '.join(columns[:8])}")
                        if len(columns) > 8:
                            print(f"         ... +{len(columns)-8} more")
                        
                        # Count rows
                        try:
                            cursor.execute(f"SELECT COUNT(*) AS cnt FROM [{table_name}]")
                            if cursor.recordset and not cursor.recordset.EOF:
                                count = cursor.recordset.Fields(0).Value
                                print(f"Rows: {count:,}")
                        except:
                            pass
                            
                except Exception as e:
                    print(f"  Error: {e}")
            
            # Identify key tables for products
            print("\n" + "=" * 70)
            print("  🔍 TABLES FOR PRODUCT DATA")
            print("=" * 70)
            
            keywords = ['detail', 'item', 'product', 'order', 'sales', 'menu']
            found = [t for t in user_tables if any(k in t.lower() for k in keywords)]
            
            if found:
                print("\nThese tables likely contain product/order item data:")
                for t in found:
                    print(f"  ✅ {t}")
            else:
                print("\nNo obvious product tables found by name.")
                print("Check the full list above.")
                
        except Exception as e:
            print(f"ADOX Error: {e}")
            print("\nTrying alternative method...")
            
            # Fallback: check common Aldelo table names
            common_tables = [
                'Orderheaders', 'OrderDetails', 'OrderItems', 'SalesDetails',
                'Products', 'MenuItems', 'Items', 'Employees', 'Customers',
                'Categories', 'Stations', 'Tables', 'Orderpayments'
            ]
            
            print("\nChecking common Aldelo tables:")
            for table in common_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) AS c FROM [{table}]")
                    if cursor.recordset and not cursor.recordset.EOF:
                        count = cursor.recordset.Fields(0).Value
                        print(f"  ✅ {table} ({count:,} rows)")
                except:
                    print(f"  ❌ {table} (not found)")
        
        conn.close()
        
    except Exception as e:
        print(f"Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_all_tables()
    input("\nPress Enter to exit...")
