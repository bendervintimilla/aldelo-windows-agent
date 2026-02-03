"""
Aldelo Database Data Extraction Module

Extracts data from Aldelo For Restaurants specific tables:
- Orderheaders: Order summary information
- Orderpayments: Payment details for orders
- AccountInvoiceERP: ERP integration data

Uses cursor-based approach to avoid pandas datetime parsing issues.
"""

import logging
from datetime import datetime, timedelta
from utils.db_connector import get_connection, DatabaseConnectionError

logger = logging.getLogger("WindowsAgent.DataExtraction")


def extract_all_data(db_path, run_date=None, config=None):
    """
    Extract data from all Aldelo tables for a date range.
    
    Args:
        db_path: Full path to Access database
        run_date: Specific date to extract (YYYY-MM-DD format), or None for range
        config: Configuration dict with connection settings
                - lookback_days: Number of past days to extract (default: 30)
        
    Returns:
        dict: Dictionary with keys 'orderheaders', 'orderpayments', 'account_invoice_erp'
    """
    # Determine date range
    lookback_days = config.get("lookback_days", 30) if config else 30
    
    if run_date:
        start_date = run_date
        end_date = run_date
        logger.info(f"Extracting data for specific date: {run_date}")
    else:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        logger.info(f"Extracting data from {start_date} to {end_date} ({lookback_days} days)")
    
    logger.info(f"Database: {db_path}")
    
    # Get connection parameters from config
    read_only = config.get("read_only", True) if config else True
    strategy = config.get("connection_strategy", ["oledb", "odbc"])[0] if config else "auto"
    
    try:
        conn = get_connection(db_path, strategy=strategy, read_only=read_only)
        
        # Extract from all four tables with date range
        data = {
            "orderheaders": extract_orderheaders(conn, start_date, end_date),
            "orderpayments": extract_orderpayments(conn, start_date, end_date),
            "account_invoice_erp": extract_account_invoice_erp(conn, start_date, end_date),
            "orderdetails": extract_orderdetails(conn, start_date, end_date)
        }
        
        conn.close()
        
        # Log summary
        total_records = sum(len(v) for v in data.values())
        logger.info(f"✓ Extraction complete: {total_records} total records")
        logger.info(f"  - Orderheaders: {len(data['orderheaders'])}")
        logger.info(f"  - Orderpayments: {len(data['orderpayments'])}")
        logger.info(f"  - AccountInvoiceERP: {len(data['account_invoice_erp'])}")
        logger.info(f"  - Orderdetails: {len(data['orderdetails'])}")
        
        return data
        
    except DatabaseConnectionError as e:
        logger.error(f"Database connection failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        return None


def safe_str(value):
    """Safely convert value to string, handling None."""
    if value is None:
        return ''
    return str(value)


def safe_float(value):
    """Safely convert value to float, handling None."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except:
        return 0.0


def safe_datetime(value):
    """Safely convert datetime to ISO string."""
    if value is None:
        return None
    try:
        return str(value)
    except:
        return None


def extract_orderheaders(conn, start_date, end_date=None):
    """
    Extract from Orderheaders table with date range support.
    Uses cursor instead of pandas to avoid datetime parsing issues.
    """
    if not end_date:
        end_date = start_date
    
    sql = f"""
    SELECT 
        OrderID,
        OrderDateTime,
        DineInTableID,
        EmployeeID,
        AmountDue,
        SubTotal,
        SalesTaxAmountUsed,
        DiscountAmount,
        SurchargeAmount,
        CashGratuity,
        OrderStatus,
        OrderType,
        StationID
    FROM Orderheaders
    WHERE OrderDateTime IS NOT NULL
      AND FORMAT(OrderDateTime, 'yyyy-mm-dd') >= '{start_date}'
      AND FORMAT(OrderDateTime, 'yyyy-mm-dd') <= '{end_date}'
    ORDER BY OrderDateTime DESC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            order_dt = safe_datetime(row[1])
            time_str = order_dt.split(' ')[-1] if order_dt and ' ' in order_dt else None

            record = {
                "order_id": safe_str(row[0]),
                "order_date": order_dt,
                "order_time": time_str,
                "table_number": safe_str(row[2]),
                "server_id": safe_str(row[3]),
                "server_name": "Aldelo Server",
                "customer_name": "Customer", 
                "grand_total": safe_float(row[4]),
                "subtotal": safe_float(row[5]),
                "tax_amount": safe_float(row[6]),
                "discount_amount": safe_float(row[7]),
                "service_charge": safe_float(row[8]),
                "tip_amount": safe_float(row[9]),
                "order_status": safe_str(row[10]),
                "order_type": safe_str(row[11]),
                "terminal_id": safe_str(row[12])
            }
            records.append(record)
        
        cursor.close()
        return records
    except Exception as e:
        logger.error(f"Failed to extract orderheaders: {e}")
        return []


def extract_orderpayments(conn, start_date, end_date=None):
    """
    Extract from Orderpayments table with date range support.
    Uses cursor instead of pandas to avoid datetime parsing issues.
    """
    if not end_date:
        end_date = start_date
    
    sql = f"""
    SELECT 
        oh.OrderID,
        op.OrderPaymentID,
        op.PaymentMethod,
        op.AmountPaid,
        op.AmountTendered,
        op.EDCCardType,
        op.EDCCardLast4,
        op.PaymentDateTime
    FROM Orderpayments op
    INNER JOIN Orderheaders oh ON op.OrderID = oh.OrderID
    WHERE oh.OrderDateTime IS NOT NULL
      AND FORMAT(oh.OrderDateTime, 'yyyy-mm-dd') >= '{start_date}'
      AND FORMAT(oh.OrderDateTime, 'yyyy-mm-dd') <= '{end_date}'
    ORDER BY op.PaymentDateTime DESC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            payment_dt = safe_datetime(row[7])
            time_str = payment_dt.split(' ')[-1] if payment_dt and ' ' in payment_dt else None
            
            amount_paid = safe_float(row[3])
            amount_tendered = safe_float(row[4])

            record = {
                "order_id": safe_str(row[0]),
                "payment_id": safe_str(row[1]),
                "payment_type": safe_str(row[2]),
                "payment_amount": amount_paid,
                "tender_amount": amount_tendered,
                "change_amount": amount_tendered - amount_paid,
                "card_type": safe_str(row[5]),
                "card_number": safe_str(row[6]),
                "payment_date": payment_dt,
                "payment_time": time_str
            }
            records.append(record)
        
        cursor.close()
        return records
    except Exception as e:
        logger.error(f"Failed to extract orderpayments: {e}")
        return []


def extract_account_invoice_erp(conn, start_date, end_date=None):
    """
    Extract from AccountInvoiceERP table with date range support.
    Uses cursor instead of pandas to avoid datetime parsing issues.
    """
    if not end_date:
        end_date = start_date
    
    sql = f"""
    SELECT 
        OrderID,
        FacturaNumberERP,
        FechaEntrega,
        CustomerID,
        BaseIva + BaseIva0 + BaseNoIva
    FROM AccountInvoiceERP
    WHERE FechaEntrega IS NOT NULL
      AND FORMAT(FechaEntrega, 'yyyy-mm-dd') >= '{start_date}'
      AND FORMAT(FechaEntrega, 'yyyy-mm-dd') <= '{end_date}'
    ORDER BY FechaEntrega DESC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            inv_date = safe_datetime(row[2])

            record = {
                "invoice_id": safe_str(row[0]),
                "invoice_number": safe_str(row[1]),
                "invoice_date": inv_date,
                "account_id": safe_str(row[3]),
                "account_name": "Customer",
                "total_amount": safe_float(row[4]),
            }
            records.append(record)
        
        cursor.close()
        return records
    except Exception as e:
        logger.error(f"Failed to extract account_invoice_erp: {e}")
        return []


def extract_orderdetails(conn, start_date, end_date=None):
    """
    Extract from OrderTransactions table to get individual product sales.
    Joins with OrderHeaders for date filtering, MenuItems for product names,
    and MenuCategories for category names.
    
    Aldelo table structure (verified):
    - OrderTransactions: line items (OrderID, MenuItemID, Quantity, ExtendedPrice)
    - MenuItems: product catalog (MenuItemID, MenuItemText, MenuCategoryID)
    - MenuCategories: categories (MenuCategoryID, MenuCategoryText)
    - OrderHeaders: orders (OrderID, OrderDateTime)
    """
    if not end_date:
        end_date = start_date
    
    # MS Access requires parentheses for multiple JOINs
    sql = f"""
    SELECT 
        ot.OrderID,
        mi.MenuItemText,
        ot.Quantity,
        ot.ExtendedPrice,
        mc.MenuCategoryText
    FROM ((OrderTransactions ot
    INNER JOIN OrderHeaders oh ON ot.OrderID = oh.OrderID)
    LEFT JOIN MenuItems mi ON ot.MenuItemID = mi.MenuItemID)
    LEFT JOIN MenuCategories mc ON mi.MenuCategoryID = mc.MenuCategoryID
    WHERE oh.OrderDateTime >= #{start_date}#
      AND oh.OrderDateTime < #{end_date}# + 1
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            item_name = safe_str(row[1]) if row[1] else "Producto sin nombre"
            record = {
                "order_id": safe_str(row[0]),
                "item_name": item_name,
                "quantity": safe_float(row[2]),
                "price": safe_float(row[3]),
                "category": safe_str(row[4]) if row[4] else "Sin categoría"
            }
            records.append(record)
        
        cursor.close()
        logger.info(f"Extracted {len(records)} order transaction records (products)")
        return records
    except Exception as e:
        logger.error(f"Failed to extract order transactions: {e}")
        return []


