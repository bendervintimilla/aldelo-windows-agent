r"""
Windows Registry Reader for Aldelo Database Path Detection

This module reads the Windows Registry to automatically detect the location of
the Aldelo For Restaurants database file (.mdb or .accdb).

Registry Locations:
- HKEY_LOCAL_MACHINE\SOFTWARE\Aldelo Systems\Aldelo For Restaurants
- HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Aldelo Systems\Aldelo For Restaurants

Keys searched (in order):
1. LiveDatabasePath
2. DatabasePath
3. DataPath
4. InstallPath (will append default database name)
"""

import os
import logging
import platform

logger = logging.getLogger("WindowsAgent.RegistryReader")

# Registry paths to check
REGISTRY_PATHS = [
    r"SOFTWARE\Aldelo Systems\Aldelo For Restaurants",
    r"SOFTWARE\WOW6432Node\Aldelo Systems\Aldelo For Restaurants"
]

# Keys to check in priority order
REGISTRY_KEYS = [
    "LiveDatabasePath",
    "DatabasePath",
    "DataPath",
    "InstallPath"
]

# Default database filenames to try if only path is found
DEFAULT_DB_NAMES = [
    "AldeloPOS.mdb",
    "AldeloPOS.accdb",
    "Aldelo.mdb",
    "Aldelo.accdb"
]

# Common filesystem paths to check if registry fails
COMMON_PATHS = [
    r"C:\ProgramData\Aldelo\Aldelo For Restaurants\Databases\Live",
    r"C:\Program Files (x86)\Aldelo\Aldelo For Restaurants\Data",
    r"C:\Aldelo For Restaurants\Data"
]


def get_aldelo_db_path():
    """
    Automatically detect Aldelo database path from Windows Registry.
    
    Returns:
        str: Full path to Aldelo database file, or None if not found
    """
    system = platform.system()
    
    if system != "Windows":
        logger.warning(f"Registry reading only supported on Windows. Current OS: {system}")
        return None
    
    try:
        import winreg
    except ImportError:
        logger.error("winreg module not available. This feature requires Windows.")
        return None
    
    # Try each registry path
    for reg_path in REGISTRY_PATHS:
        logger.info(f"Checking registry path: HKLM\\{reg_path}")
        
        try:
            # Open registry key
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                reg_path,
                0,
                winreg.KEY_READ
            )
            
            # Try each registry value in priority order
            for value_name in REGISTRY_KEYS:
                try:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    logger.info(f"Found registry key '{value_name}': {value}")
                    
                    # Validate the path
                    db_path = _validate_db_path(value, value_name)
                    if db_path:
                        winreg.CloseKey(key)
                        logger.info(f"✓ Detected Aldelo database at: {db_path}")
                        return db_path
                        
                except FileNotFoundError:
                    logger.debug(f"Registry value '{value_name}' not found in {reg_path}")
                    continue
            
            winreg.CloseKey(key)
            
        except FileNotFoundError:
            logger.debug(f"Registry path not found: {reg_path}")
            continue
        except PermissionError:
            logger.error(f"Permission denied reading registry: {reg_path}")
            continue
        except Exception as e:
            logger.error(f"Error reading registry path {reg_path}: {e}")
            continue
    
    logger.error("Could not detect Aldelo database path from registry")
    
    # Heuristic Fallback: Check common filesystem paths
    logger.info("Attempting fallback to common filesystem paths...")
    for path in COMMON_PATHS:
        if os.path.exists(path):
            db_path = _validate_db_path(path, "CommonPath")
            if db_path:
                logger.info(f"✓ Detected Aldelo database in common path: {db_path}")
                return db_path
                
    return None


def _validate_db_path(path, key_name):
    """
    Validate that the path exists and points to a valid database file.
    
    Args:
        path: Path from registry
        key_name: Name of the registry key (for logic decisions)
        
    Returns:
        str: Valid database path or None
    """
    if not path:
        return None
    
    # If it's a direct database path, check if file exists
    if path.lower().endswith(('.mdb', '.accdb')):
        if os.path.isfile(path):
            return path
        else:
            logger.warning(f"Database file not found: {path}")
            return None
    
    # If it's a directory (DataPath, InstallPath), try default filenames
    if os.path.isdir(path):
        logger.info(f"Path is directory, searching for database files: {path}")
        
        # 1. Try generic default names first
        for db_name in DEFAULT_DB_NAMES:
            full_path = os.path.join(path, db_name)
            if os.path.isfile(full_path):
                logger.info(f"Found database file (default name): {full_path}")
                return full_path
        
        # 2. Heuristic: Search for ANY .mdb/.accdb file in the directory
        # This handles custom names like "SANTA LUCIA 2020.mdb"
        try:
            candidates = []
            for f in os.listdir(path):
                if f.lower().endswith(('.mdb', '.accdb')):
                    # Exclude backups or temp files
                    if "backup" in f.lower() or f.startswith("~"):
                        continue
                    full_path = os.path.join(path, f)
                    if os.path.isfile(full_path):
                        size = os.path.getsize(full_path)
                        candidates.append((full_path, size))
            
            if candidates:
                # Pick the largest file, assuming it's the live DB
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_match = candidates[0][0]
                logger.info(f"Found database file (heuristic match): {best_match}")
                return best_match
        except Exception as e:
            logger.warning(f"Error scanning directory {path}: {e}")

        # 3. Repeat checks in 'Data' subdirectory
        data_path = os.path.join(path, "Data")
        if os.path.isdir(data_path):
            # Recurse one level into Data folder
            res = _validate_db_path(data_path, "DataSubdir")
            if res:
                return res
        
        # 4. Recursive Heuristic: Check one level of subdirectories
        # This handles structure like Databases\Live\StoreName\Database.mdb
        logger.info(f"Searching subdirectories of: {path}")
        try:
            for item in os.listdir(path):
                sub_path = os.path.join(path, item)
                if os.path.isdir(sub_path):
                    # Skip folders we already checked or that are unlikely to hold the live DB
                    if item.lower() in ["data", "backup", "logs", "temp", "backups", "export", "images"]:
                        continue
                        
                    # Search for any .mdb in this subfolder
                    for f in os.listdir(sub_path):
                        if f.lower().endswith(('.mdb', '.accdb')):
                            if "backup" in f.lower() or f.startswith("~"):
                                continue
                            full_path = os.path.join(sub_path, f)
                            if os.path.isfile(full_path):
                                logger.info(f"Found database file in subfolder '{item}': {full_path}")
                                return full_path
        except Exception as e:
            logger.warning(f"Error scanning subdirectories of {path}: {e}")
    
    logger.warning(f"Could not validate database path from {key_name}: {path}")
    return None


def get_db_path_with_fallback(config):
    """
    Get database path with registry detection and config fallback.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        str: Database path or None
    """
    # 1. Try registry if enabled
    if config.get("use_registry", True):
        db_path = get_aldelo_db_path()
        if db_path:
            return db_path
        logger.warning("Registry detection failed, falling back to config")
    
    # 2. Fall back to config.json
    config_path = config.get("db_path")
    if config_path and os.path.isfile(config_path):
        logger.info(f"Using database path from config: {config_path}")
        return config_path
    
    logger.error("No valid database path found (registry or config)")
    return None
