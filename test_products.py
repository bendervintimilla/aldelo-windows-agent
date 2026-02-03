"""
Complete Aldelo Schema Analyzer
Shows EXACT column names and sample data for product-related tables.
"""
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from utils.db_connector import get_connection
from utils.registry_reader import get_db_path_with_fallback

def analyze_table(cursor, table_name, limit=3):
    """Analyze a single table - show all columns and sample data."""
    print(f"\n{'='*70}")
    print(f"TABLE: {table_name}")
    print('='*70)
    
    try:
        cursor.execute(f"SELECT TOP 1 * FROM [{table_name}]")
        
        if cursor.recordset:
            rs = cursor.recordset
            cols = []
            print(f"\nCOLUMNS ({rs.Fields.Count}):")
            for i in range(rs.Fields.Count):
                col = rs.Fields(i).Name
                cols.append(col)
                print(f"  {i+1:2}. {col}")
            
            # Get count
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            if cursor.recordset and not cursor.recordset.EOF:
                count = cursor.recordset.Fields(0).Value
                print(f"\nTOTAL ROWS: {count:,}")
            
            # Get sample data
            cursor.execute(f"SELECT TOP {limit} * FROM [{table_name}]")
            rows = cursor.fetchall()
            if rows:
                print(f"\nSAMPLE DATA ({len(rows)} rows):")
                for i, row in enumerate(rows):
                    print(f"\n  Row {i+1}:")
                    for j, val in enumerate(row):
                        if j < len(cols):
                            val_str = str(val)[:50] if val is not None else 'NULL'
                            print(f"    {cols[j]}: {val_str}")
            
            return cols
    except Exception as e:
        print(f"ERROR: {e}")
        return []

def main():
    """Main analysis function."""
    config_path = os.path.join(script_dir, 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    db_path = get_db_path_with_fallback(config)
    
    print("\n" + "="*70)
    print("  ALDELO COMPLETE SCHEMA ANALYZER")
    print("="*70)
    print(f"Database: {db_path}\n")
    
    conn = get_connection(db_path, strategy="oledb", read_only=True)
    cursor = conn.cursor()
    
    # Analyze key tables for products
    tables = [
        'OrderTransactions',  # Line items
        'OrderHeaders',       # Orders
        'MenuItems',          # Products
        'MenuCategories',     # Categories
    ]
    
    all_columns = {}
    for table in tables:
        cols = analyze_table(cursor, table)
        all_columns[table] = cols
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY - KEY COLUMNS FOR EXTRACTION")
    print("="*70)
    
    print("\n📦 OrderTransactions columns:")
    if 'OrderTransactions' in all_columns:
        for c in all_columns['OrderTransactions']:
            print(f"    - {c}")
    
    print("\n🍔 MenuItems columns:")
    if 'MenuItems' in all_columns:
        for c in all_columns['MenuItems'][:15]:  # First 15
            print(f"    - {c}")
        if len(all_columns['MenuItems']) > 15:
            print(f"    ... +{len(all_columns['MenuItems'])-15} more")
    
    # Test a simple join
    print("\n" + "="*70)
    print("  TEST JOIN QUERY")
    print("="*70)
    
    try:
        sql = """
        SELECT TOP 5
            ot.OrderID,
            ot.MenuItemID,
            ot.Quantity,
            ot.ExtendedPrice,
            mi.MenuItemText
        FROM OrderTransactions ot
        LEFT JOIN MenuItems mi ON ot.MenuItemID = mi.MenuItemID
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        print(f"\nJoin result: {len(rows)} rows")
        for row in rows:
            print(f"  OrderID={row[0]}, MenuItemID={row[1]}, Qty={row[2]}, Price={row[3]}, Name={row[4]}")
    except Exception as e:
        print(f"JOIN ERROR: {e}")
    
    conn.close()
    print("\n" + "="*70)
    print("  ANALYSIS COMPLETE - Copy this output and share it!")
    print("="*70)

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
