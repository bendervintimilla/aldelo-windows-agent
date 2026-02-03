"""
Test script for manual extraction testing on Windows.

This script allows you to test the extraction functionality before
installing as a service.

Usage:
    python test_extraction.py
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pprint import pprint

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from utils.registry_reader import get_aldelo_db_path, get_db_path_with_fallback
from utils.db_connector import get_connection, test_connection
from tools.access_db import extract_all_data


def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def main():
    print_section("Aldelo Database Extraction Test")
    
    # Optional date argument
    run_date = None
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
        if date_arg.lower() == 'yesterday':
            run_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            run_date = date_arg
        print(f"Testing for specific date: {run_date}")
    
    # 1. Load config
    print("\n1. Loading configuration...")
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        print("✓ Configuration loaded")
        pprint(config, indent=2)
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return
    
    # 2. Detect database path
    print_section("Database Path Detection")
    db_path = get_db_path_with_fallback(config)
    
    if not db_path:
        print("✗ Database path detection failed")
        print("\nTroubleshooting:")
        print("- Is Aldelo installed on this machine?")
        print("- Check if Registry keys exist:")
        print("  HKLM\\SOFTWARE\\Aldelo Systems\\Aldelo For Restaurants")
        print("- Or set 'db_path' manually in config.json")
        return
    
    print(f"✓ Database found: {db_path}")
    
    # 3. Test connection
    print_section("Database Connection Test")
    print("Testing connection strategies...")
    
    result = test_connection(db_path, strategy="auto")
    pprint(result, indent=2)
    
    if not result["success"]:
        print("\n✗ Connection failed")
        print(f"Error: {result['error']}")
        print("\nTroubleshooting:")
        print("- Is Microsoft Access Database Engine installed?")
        print("- Download from: https://www.microsoft.com/en-us/download/details.aspx?id=54920")
        print("- Check if database file is accessible")
        return
    
    print("\n✓ Connection successful")
    
    # 4. Test extraction
    print_section("Data Extraction Test")
    print("Extracting data from Aldelo tables...")
    
    try:
        data = extract_all_data(db_path, run_date=run_date, config=config)
        
        if not data:
            print("✗ Extraction failed or returned no data")
            return
        
        print("\n✓ Extraction successful!")
        print("\nRecords found:")
        print(f"  - Orderheaders:      {len(data['orderheaders']):4d} records")
        print(f"  - Orderpayments:     {len(data['orderpayments']):4d} records")
        print(f"  - AccountInvoiceERP: {len(data['account_invoice_erp']):4d} records")
        print(f"  - Total:             {sum(len(v) for v in data.values()):4d} records")
        
        # Show sample data
        if data['orderheaders']:
            print("\nSample Orderheader:")
            pprint(data['orderheaders'][0], indent=2)
        
        if data['orderpayments']:
            print("\nSample Orderpayment:")
            pprint(data['orderpayments'][0], indent=2)
        
        if data['account_invoice_erp']:
            print("\nSample Account Invoice:")
            pprint(data['account_invoice_erp'][0], indent=2)
        
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. Summary
    print_section("Test Summary")
    print("✓ All tests passed!")
    print("\nNext steps:")
    print("1. Review the extracted data above")
    print("2. Verify central API endpoint is accessible")
    print("3. Install as Windows Service: install_service.bat")


if __name__ == "__main__":
    main()
