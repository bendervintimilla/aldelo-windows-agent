"""
Multi-Strategy Database Connector for MS Access (Aldelo)

Connection Strategies (in order of preference):
1. OLEDB via COM (pywin32) - Best performance for Access
2. ODBC without DSN (pyodbc) - Fallback option
3. ODBC with System DSN (pyodbc) - Optional if DSN configured

Features:
- Automatic fallback on connection failure
- Read-only connections to prevent POS interference
- Connection retry logic with exponential backoff
- Comprehensive error logging
"""

import logging
import platform
import time

logger = logging.getLogger("WindowsAgent.DBConnector")


class DatabaseConnectionError(Exception):
    """Raised when all connection strategies fail"""
    pass


def get_connection(db_path, strategy="auto", read_only=True, retry_attempts=3):
    """
    Get database connection using specified strategy with fallback.
    
    Args:
        db_path: Full path to Access database file
        strategy: "auto", "oledb", "odbc", or "odbc_dsn"
        read_only: If True, open in read-only mode
        retry_attempts: Number of retry attempts per strategy
        
    Returns:
        Database connection object
        
    Raises:
        DatabaseConnectionError: If all strategies fail
    """
    strategies = _determine_strategies(strategy)
    
    for attempt in range(retry_attempts):
        for strat_name in strategies:
            try:
                logger.info(f"Attempting connection via {strat_name.upper()} (attempt {attempt + 1}/{retry_attempts})")
                
                if strat_name == "oledb":
                    conn = _connect_oledb(db_path, read_only)
                elif strat_name == "odbc":
                    conn = _connect_odbc(db_path, read_only)
                elif strat_name == "odbc_dsn":
                    conn = _connect_odbc_dsn(db_path, read_only)
                else:
                    continue
                
                logger.info(f"✓ Successfully connected via {strat_name.upper()}")
                return conn
                
            except Exception as e:
                logger.warning(f"Connection via {strat_name.upper()} failed: {e}")
                continue
        
        # Wait before retry (exponential backoff)
        if attempt < retry_attempts - 1:
            wait_time = 2 ** attempt  # 1s, 2s, 4s...
            logger.info(f"Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    raise DatabaseConnectionError(
        f"Failed to connect to database after {retry_attempts} attempts using strategies: {strategies}"
    )


def _determine_strategies(strategy):
    """Determine which connection strategies to try"""
    if strategy == "auto":
        return ["oledb", "odbc", "odbc_dsn"]
    elif strategy == "oledb":
        return ["oledb"]
    elif strategy == "odbc":
        return ["odbc"]
    elif strategy == "odbc_dsn":
        return ["odbc_dsn"]
    else:
        logger.warning(f"Unknown strategy '{strategy}', falling back to auto")
        return ["oledb", "odbc", "odbc_dsn"]


def _connect_oledb(db_path, read_only=True):
    """
    Connect via OLEDB using COM (Windows only).
    Requires pywin32 package.
    """
    if platform.system() != "Windows":
        raise NotImplementedError("OLEDB connections only supported on Windows")
    
    try:
        import win32com.client
    except ImportError:
        raise ImportError("pywin32 package required for OLEDB connections")
    
    # OLEDB connection string for Access
    mode = "Read" if read_only else "Share Deny None"
    conn_str = (
        f"Provider=Microsoft.ACE.OLEDB.12.0;"
        f"Data Source={db_path};"
        f"Mode={mode};"
        "Persist Security Info=False;"
    )
    
    try:
        # Create ADODB Connection object
        conn = win32com.client.Dispatch("ADODB.Connection")
        conn.Open(conn_str)
        
        # Wrap in a custom class to provide consistent interface
        return OLEDBConnection(conn)
        
    except Exception as e:
        raise DatabaseConnectionError(f"OLEDB connection failed: {e}")


def _connect_odbc(db_path, read_only=True):
    """
    Connect via ODBC without DSN.
    Requires pyodbc package and Microsoft Access Database Engine.
    Tries ACE driver first, then legacy Jet driver.
    """
    try:
        import pyodbc
    except ImportError:
        raise ImportError("pyodbc package required for ODBC connections")
    
    # Try drivers in order of preference
    drivers = [
        "{Microsoft Access Driver (*.mdb, *.accdb)}",  # ACE/Jet 4.0
        "{Microsoft Access Driver (*.mdb)}",           # Legacy Jet
    ]
    
    last_error = None
    for driver in drivers:
        conn_str = f"DRIVER={driver};DBQ={db_path};"
        if read_only:
            conn_str += "ReadOnly=1;"
        
        try:
            conn = pyodbc.connect(conn_str)
            logger.info(f"Connected using driver: {driver}")
            return conn
        except Exception as e:
            last_error = e
            logger.debug(f"Driver {driver} failed: {e}")
            continue
    
    raise DatabaseConnectionError(f"ODBC connection failed: {last_error}")


def _connect_odbc_dsn(db_path, read_only=True):
    """
    Connect via ODBC using System DSN.
    Requires DSN named 'AldeloPOS' to be configured.
    """
    try:
        import pyodbc
    except ImportError:
        raise ImportError("pyodbc package required for ODBC DSN connections")
    
    dsn_name = "AldeloPOS"
    
    try:
        conn = pyodbc.connect(f"DSN={dsn_name}")
        return conn
    except Exception as e:
        raise DatabaseConnectionError(f"ODBC DSN connection failed: {e}")


class OLEDBConnection:
    """
    Wrapper for OLEDB connection to provide pyodbc-like interface.
    """
    def __init__(self, adodb_conn):
        self.conn = adodb_conn
        self._closed = False
    
    def cursor(self):
        """Return a cursor-like object"""
        return OLEDBCursor(self.conn)
    
    def close(self):
        """Close the connection"""
        if not self._closed:
            try:
                self.conn.Close()
                self._closed = True
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class OLEDBCursor:
    """
    Cursor-like wrapper for OLEDB recordset.
    """
    def __init__(self, adodb_conn):
        self.conn = adodb_conn
        self.recordset = None
    
    @property
    def description(self):
        """Return column descriptions for DB-API compatibility (Pandas needs this)"""
        if not self.recordset:
            return None
        
        try:
            return [
                (self.recordset.Fields(i).Name, None, None, None, None, None, True)
                for i in range(self.recordset.Fields.Count)
            ]
        except:
            return None

    @property
    def rowcount(self):
        """Return number of rows (standard DB-API)"""
        if not self.recordset:
            return -1
        try:
            return self.recordset.RecordCount
        except:
            return -1

    def execute(self, sql):
        """Execute SQL query"""
        try:
            import win32com.client
            # Close existing recordset if any
            if self.recordset:
                try: self.recordset.Close()
                except: pass
            
            self.recordset = win32com.client.Dispatch("ADODB.Recordset")
            # 3 = adOpenStatic (allows RecordCount), 1 = adLockReadOnly
            self.recordset.Open(sql, self.conn, 3, 1)
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")
    
    def fetchall(self):
        """Fetch all results as list of tuples"""
        if not self.recordset or self.recordset.EOF:
            return []
        
        results = []
        fields = [field.Name for field in self.recordset.Fields]
        
        while not self.recordset.EOF:
            row = tuple(self.recordset.Fields[i].Value for i in range(len(fields)))
            results.append(row)
            self.recordset.MoveNext()
        
        return results
    
    def close(self):
        """Close the cursor"""
        if self.recordset:
            try:
                self.recordset.Close()
            except:
                pass


def test_connection(db_path, strategy="auto"):
    """
    Test database connection and return diagnostics.
    
    Returns:
        dict: Connection test results
    """
    result = {
        "success": False,
        "strategy_used": None,
        "error": None,
        "db_path": db_path
    }
    
    try:
        conn = get_connection(db_path, strategy=strategy, retry_attempts=1)
        result["success"] = True
        result["strategy_used"] = "auto"  # Would need to track which actually worked
        conn.close()
    except Exception as e:
        result["error"] = str(e)
    
    return result
