# 🖥️ Aldelo Data Agent - Windows Installation Guide

> **Version:** 2.0  
> **Date:** January 2026  
> **Purpose:** Extract data from Aldelo POS and send to central server

---

## 📋 Pre-Installation Checklist

Before starting, verify you have:

- [ ] **Administrator access** to the Windows machine
- [ ] **Aldelo POS installed** and working on this machine
- [ ] **Internet connection** to download Python and dependencies
- [ ] **Central server URL** (provided by your IT administrator)
- [ ] **Store ID** for this location (e.g., `santa_lucia`, `restaurant_001`)

---

## 📦 Step 1: Install Python

### 1.1 Download Python

1. Open browser and go to: **https://www.python.org/downloads/**
2. Click **"Download Python 3.12.x"** (or latest 3.x version)
3. Save the installer to Desktop

### 1.2 Run Python Installer

> ⚠️ **IMPORTANT: Check the "Add Python to PATH" option!**

1. Double-click the downloaded `.exe` file
2. ✅ Check **"Add Python to PATH"** at the bottom of the installer
3. Click **"Install Now"**
4. Wait for installation to complete
5. Click **"Close"**

### 1.3 Verify Python Installation

1. Open **Command Prompt** (search for `cmd` in Start menu)
2. Type this command and press Enter:
   ```cmd
   python --version
   ```
3. You should see something like: `Python 3.12.1`

> ❌ If you see `'python' is not recognized...`, Python was not added to PATH.  
> Uninstall Python and reinstall, making sure to check "Add Python to PATH".

---

## 📦 Step 2: Install Microsoft Access Database Engine

> This is required to connect to the Aldelo database file.

### 2.1 Download

1. Go to: **https://www.microsoft.com/en-us/download/details.aspx?id=54920**
2. Click **Download**
3. Select **AccessDatabaseEngine_X64.exe** (for 64-bit Windows)
   - If you have 32-bit Windows, select **AccessDatabaseEngine.exe**
4. Click **Download**

### 2.2 Install

1. Run the downloaded installer
2. Accept the license terms
3. Click **Install**
4. Wait for completion and click **Close**

> ⚠️ **Note:** If you get an error about Office 32-bit vs 64-bit, you may need to match the architecture of your existing Office installation.

---

## 📦 Step 3: Copy Agent Files

### 3.1 Transfer the Agent Folder

1. Copy the entire `windows-agent` folder from the USB/network share
2. Paste it to: `C:\Aldelo\windows-agent\`

Your folder structure should look like this:
```
C:\Aldelo\windows-agent\
├── agent.py
├── service.py
├── config.json           ← You will edit this
├── install_service.bat
├── uninstall_service.bat
├── test_extraction.py
├── discover_schema.py
├── check_data.py
├── requirements.txt
├── tools\
│   └── access_db.py
└── utils\
    ├── __init__.py
    ├── registry_reader.py
    └── db_connector.py
```

---

## ⚙️ Step 4: Configure the Agent

### 4.1 Edit Configuration

1. Navigate to `C:\Aldelo\windows-agent\`
2. Right-click on **config.json** → **Open with** → **Notepad**
3. Edit the following values:

```json
{
    "store_id": "YOUR_STORE_ID",
    "central_server_url": "http://YOUR_SERVER_IP:5001/api/ingest",
    "db_path": null,
    "use_registry": true,
    "connection_strategy": ["oledb", "odbc"],
    "extraction_interval_minutes": 30,
    "read_only": true,
    "retry_attempts": 3,
    "retry_delay_seconds": 60
}
```

### 4.2 Configuration Reference

| Setting | What to Enter | Example |
|---------|---------------|---------|
| `store_id` | Unique identifier for this restaurant | `"santa_lucia"` |
| `central_server_url` | URL of your central data server | `"http://192.168.1.100:5001/api/ingest"` |
| `db_path` | Leave as `null` (auto-detect) or set manually | `"C:\\Aldelo\\Live\\Data\\AFRCloud.mdb"` |
| `use_registry` | Keep as `true` to auto-detect database | `true` |
| `extraction_interval_minutes` | How often to extract (in minutes) | `30` |

4. **Save** the file (Ctrl+S) and close Notepad

---

## 📦 Step 5: Install Python Dependencies

### 5.1 Open Command Prompt as Administrator

1. Click **Start** menu
2. Type **cmd**
3. Right-click on **Command Prompt** → **Run as administrator**
4. Click **Yes** when prompted

### 5.2 Navigate to Agent Folder

```cmd
cd C:\Aldelo\windows-agent
```

### 5.3 Install Dependencies

```cmd
pip install -r requirements.txt
```

Wait for all packages to install. You should see:
```
Successfully installed pyodbc-X.X.X requests-X.X.X schedule-X.X.X pandas-X.X.X pywin32-XXX comtypes-X.X.X
```

### 5.4 Verify pywin32 Installation

```cmd
python -c "import win32serviceutil; print('pywin32 OK')"
```

If you see `pywin32 OK`, you're good!

> ❌ If you get an error, run:
> ```cmd
> python -m pywin32_postinstall -install
> ```

---

## 🧪 Step 6: Test Before Installing Service

### 6.1 Run Test Script

This verifies everything works before installing the service.

```cmd
cd C:\Aldelo\windows-agent
python test_extraction.py
```

### 6.2 Expected Output

```
============================================================
  Aldelo Database Extraction Test
============================================================

1. Loading configuration...
✓ Configuration loaded

============================================================
  Database Path Detection
============================================================
✓ Database found: C:\Aldelo\Live\Santa Lucia\AFRCloud.mdb

============================================================
  Database Connection Test
============================================================
Testing connection strategies...
✓ Connection successful

============================================================
  Data Extraction Test
============================================================
Extracting data from Aldelo tables...

✓ Extraction successful!

Records found:
  - Orderheaders:       156 records
  - Orderpayments:      142 records
  - AccountInvoiceERP:   34 records
  - Total:              332 records

Sample Orderheader:
  {'order_id': 12345, 'order_date': '2026-01-10', 'total': 45.50}

============================================================
  Test Summary
============================================================
✓ All tests passed!

Next steps:
1. Review the extracted data above
2. Verify central API endpoint is accessible
3. Install as Windows Service: install_service.bat
```

> ⚠️ **If tests fail**, see [Troubleshooting](#-troubleshooting) section below.

---

## 🚀 Step 7: Install the Windows Service

### 7.1 Run Installation Script

1. Navigate to: `C:\Aldelo\windows-agent\`
2. **Right-click** on **install_service.bat**
3. Select **"Run as administrator"**
4. Click **Yes** when prompted

### 7.2 Verify Installation

You should see:
```
====================================
SUCCESS!
====================================

Service installed and started.

To check status:
  sc query AldeloDataAgent

To view logs:
  type service.log
```

### 7.3 Confirm Service is Running

Open Command Prompt and run:
```cmd
sc query AldeloDataAgent
```

Expected output:
```
SERVICE_NAME: AldeloDataAgent
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 4  RUNNING
                                (STOPPABLE, NOT_PAUSABLE, ACCEPTS_SHUTDOWN)
```

---

## ✅ Step 8: Verify Data Flow

### 8.1 Check Agent Logs

```cmd
type C:\Aldelo\windows-agent\agent.log
```

Look for:
```
2026-01-11 14:30:00 - INFO - Starting extraction job
2026-01-11 14:30:05 - INFO - Using database: C:\Aldelo\Live\...\AFRCloud.mdb
2026-01-11 14:30:10 - INFO - Pushing 156 records to central API...
2026-01-11 14:30:12 - INFO - ✓ Successfully pushed data (HTTP 200)
```

### 8.2 Verify on Server Side

Contact your IT administrator to confirm data is arriving at the central server.

---

## 🛠️ Troubleshooting

### ❌ "Database path detection failed"

**Cause:** Aldelo is not installed, or uses non-standard registry keys.

**Solution:** Manually set the database path in `config.json`:
```json
{
  "db_path": "C:\\Aldelo\\Live\\YourRestaurant\\AFRCloud.mdb",
  "use_registry": false
}
```

To find your database file:
1. Open File Explorer
2. Navigate to `C:\Aldelo\` or `C:\Program Files (x86)\Aldelo\`
3. Look for a folder named `Live` or `Data`
4. Find the `.mdb` file (usually `AFRCloud.mdb` or similar)

---

### ❌ "Connection via OLEDB failed"

**Cause:** Microsoft Access Database Engine not installed or wrong architecture.

**Solution:**
1. Uninstall any existing Access Database Engine
2. Reinstall matching your Windows architecture (32-bit or 64-bit)
3. Restart the computer

---

### ❌ "Service installation failed"

**Cause:** Not running as Administrator.

**Solution:**
1. Open Start menu
2. Type `cmd`
3. Right-click → **Run as administrator**
4. Navigate to folder and run manually:
   ```cmd
   cd C:\Aldelo\windows-agent
   python service.py install
   python service.py start
   ```

---

### ❌ "'python' is not recognized"

**Cause:** Python not in system PATH.

**Solution:** Reinstall Python and check **"Add Python to PATH"** during installation.

---

### ❌ "No records extracted"

**Cause:** No sales data for today, or table names differ from standard Aldelo schema.

**Solution:**
1. Run the schema discovery tool:
   ```cmd
   python discover_schema.py
   ```
2. Check if table names match expected: `Orderheaders`, `Orderpayments`
3. Try running with a date argument:
   ```cmd
   python test_extraction.py yesterday
   ```
4. Contact support if schema is different

---

### ❌ API connection errors

**Cause:** Central server not reachable from this network.

**Solution:**
1. Check if server is running
2. Verify firewall allows outbound connections on port 5001
3. Test connectivity:
   ```cmd
   ping YOUR_SERVER_IP
   ```
4. Test API manually:
   ```cmd
   curl -X POST http://YOUR_SERVER:5001/api/health
   ```

---

## 🔧 Service Management Commands

Open **Command Prompt as Administrator** for these commands:

| Action | Command |
|--------|---------|
| Check status | `sc query AldeloDataAgent` |
| Stop service | `sc stop AldeloDataAgent` |
| Start service | `sc start AldeloDataAgent` |
| Restart service | `sc stop AldeloDataAgent && sc start AldeloDataAgent` |
| View logs | `type C:\Aldelo\windows-agent\agent.log` |
| Uninstall service | Run `uninstall_service.bat` as Administrator |

---

## 🏗️ Architecture Overview

```
┌─────────────────────┐
│  Windows Service    │
│  (service.py)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Main Agent         │
│  (agent.py)         │
│  ┌───────────────┐  │
│  │ Scheduler     │  │
│  │ (30 min)      │  │
│  └───────────────┘  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│  Registry Reader                        │
│  (utils/registry_reader.py)             │
│                                         │
│  ➜ HKLM\SOFTWARE\Aldelo Systems\...     │
│  ➜ Fallback to config.json              │
└──────────┬──────────────────────────────┘
           │
           │ db_path
           ▼
┌─────────────────────────────────────────┐
│  Database Connector                     │
│  (utils/db_connector.py)                │
│                                         │
│  1. Try OLEDB (COM)                     │
│  2. Fallback to ODBC (no DSN)           │
│  3. Fallback to ODBC (with DSN)         │
└──────────┬──────────────────────────────┘
           │
           │ connection
           ▼
┌─────────────────────────────────────────┐
│  Data Extractor                         │
│  (tools/access_db.py)                   │
│                                         │
│  ➜ Orderheaders                         │
│  ➜ Orderpayments                        │
│  ➜ AccountInvoiceERP                    │
└──────────┬──────────────────────────────┘
           │
           │ JSON data
           ▼
┌─────────────────────────────────────────┐
│  HTTP POST                              │
│  ➜ http://central-server/api/ingest     │
└─────────────────────────────────────────┘
```

---

## 📁 File Structure

```
windows-agent/
├── agent.py                    # Main agent logic
├── service.py                  # Windows Service wrapper
├── config.json                 # Configuration
├── requirements.txt            # Python dependencies
├── install_service.bat         # Service installation script
├── uninstall_service.bat       # Service removal script
├── test_extraction.py          # Test script
├── discover_schema.py          # Schema discovery tool
├── check_data.py               # Data verification tool
├── WINDOWS_INSTALLATION_GUIDE.md # This file
├── utils/
│   ├── __init__.py
│   ├── registry_reader.py      # Windows Registry access
│   └── db_connector.py         # Multi-strategy connector
└── tools/
    └── access_db.py            # Aldelo table extractors
```

---

## 📊 What Happens After Installation?

1. **Every 30 minutes** (configurable), the agent will:
   - Connect to the Aldelo database
   - Extract new orders, payments, and ERP data
   - Send data to your central server

2. **Automatic startup**: The service starts automatically when Windows boots

3. **No user interaction required**: Once installed, it runs silently in the background

---

## 🔒 Security Considerations

- Database is opened in **read-only mode** by default to prevent accidental modifications
- Only extracts data from specific tables (`Orderheaders`, `Orderpayments`, `AccountInvoiceERP`)
- Does not store sensitive data locally (streams to central server)
- Card numbers are masked (last 4 digits only) in `Orderpayments`

---

## 📝 Quick Reference Card

```
+-------------------------------------------+
|   ALDELO DATA AGENT - QUICK REFERENCE     |
+-------------------------------------------+
| Installation Location:                    |
|   C:\Aldelo\windows-agent\                |
|                                           |
| Config File:                              |
|   C:\Aldelo\windows-agent\config.json     |
|                                           |
| Check Status:                             |
|   sc query AldeloDataAgent                |
|                                           |
| View Logs:                                |
|   type C:\Aldelo\windows-agent\agent.log  |
|                                           |
| Restart Service:                          |
|   sc stop AldeloDataAgent                 |
|   sc start AldeloDataAgent                |
+-------------------------------------------+
```

---

## 📞 Support Contact

If you encounter issues not covered in this guide:

- **IT Administrator:** [Your contact info]
- **Central Server URL:** `http://YOUR_SERVER:5001/api/ingest`
- **Log files to send:** `agent.log`, `service.log`
