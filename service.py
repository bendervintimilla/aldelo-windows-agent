"""
Windows Service Wrapper for Aldelo Data Extraction Agent

This module converts the agent.py into a proper Windows Service using pywin32.

Installation:
    python service.py install

Start/Stop:
    python service.py start
    python service.py stop

Remove:
    python service.py remove

Service Properties:
- Name: AldeloDataAgent
- Display Name: Aldelo Data Extraction Service
- Description: Extracts data from Aldelo POS and pushes to central server
- Start Type: Automatic (starts with Windows)
"""

import sys
import os
import time
import logging
import servicemanager
import socket

try:
    import win32serviceutil
    import win32service
    import win32event
except ImportError:
    print("ERROR: pywin32 package required for Windows Service")
    print("Install with: pip install pywin32")
    sys.exit(1)

# Add current directory to path so we can import agent
sys.path.insert(0, os.path.dirname(__file__))

from agent import job, load_config
import schedule


class AldeloDataService(win32serviceutil.ServiceFramework):
    """Windows Service implementation for Aldelo Data Agent"""
    
    _svc_name_ = "AldeloDataAgent"
    _svc_display_name_ = "Aldelo Data Extraction Service"
    _svc_description_ = "Extracts sales data from Aldelo For Restaurants database and sends to central server"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        
        # Create event to signal service stop
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        
        # Set up logging for service
        log_path = os.path.join(os.path.dirname(__file__), 'service.log')
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )
        self.logger = logging.getLogger("AldeloDataService")
        self.is_running = False
    
    def SvcStop(self):
        """Called when the service is being stopped"""
        self.logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.is_running = False
        self.logger.info("Service stopped")
    
    def SvcDoRun(self):
        """Called when the service is started"""
        self.logger.info("="*60)
        self.logger.info("Aldelo Data Extraction Service Starting")
        self.logger.info("="*60)
        
        # Log to Windows Event Viewer
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Run the main service loop
        self.main()
    
    def main(self):
        """Main service logic"""
        self.is_running = True
        
        # Load configuration
        config = load_config()
        if not config:
            self.logger.error("Failed to load configuration. Service cannot start.")
            self.SvcStop()
            return
        
        interval = config.get("extraction_interval_minutes", 30)
        self.logger.info(f"Extraction interval: {interval} minutes")
        
        # Schedule the extraction job
        schedule.every(interval).minutes.do(job)
        
        # Run once on startup
        self.logger.info("Running initial extraction job...")
        try:
            job()
        except Exception as e:
            self.logger.error(f"Initial job failed: {e}", exc_info=True)
        
        # Main service loop
        self.logger.info("Entering service main loop")
        
        while self.is_running:
            # Check if stop event is signaled
            if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                break
            
            # Run scheduled jobs
            try:
                schedule.run_pending()
            except Exception as e:
                self.logger.error(f"Scheduled job error: {e}", exc_info=True)
        
        self.logger.info("Service main loop exited")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # No arguments - show usage
        print("Aldelo Data Extraction Service")
        print("")
        print("Usage:")
        print("  Install:   python service.py install")
        print("  Start:     python service.py start")
        print("  Stop:      python service.py stop")
        print("  Remove:    python service.py remove")
        print("  Debug:     python service.py debug")
        print("")
        print("Note: Installation requires administrator privileges")
        sys.exit(0)
    
    # Handle service commands
    try:
        win32serviceutil.HandleCommandLine(AldeloDataService)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
