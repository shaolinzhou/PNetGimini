import sys
import os
import time
import logging
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importing modular components from the project structure
from src.core.config_parser import ConfigParser
from src.core.device_manager import DeviceManager
from src.core.result_handler import ResultHandler
from src.utils.logger import setup_logger

# Project directory definitions
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUTPUTS_DIR = BASE_DIR / "outputs"

def main():
    """
    Main entry point for the network automation deployment system.
    Features: Multi-threading, Automated Backups, and Execution Timing.
    """
    # Initialize necessary directories
    LOGS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    
    # Initialize logger
    setup_logger(LOGS_DIR)
    
    # Start the execution timer
    start_timestamp = datetime.datetime.now()
    start_time = time.time()
    
    logging.info("=" * 50)
    logging.info(f"SENTINEL System Started at: {start_timestamp}")
    logging.info("=" * 50)

    # Configuration file path selection
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        logging.info("No config specified. Using default: configs/devices.yaml")
        config_path = BASE_DIR / "configs" / "devices.yaml"

    if not config_path.exists():
        logging.error(f"Critical Error: Configuration file '{config_path}' not found.")
        sys.exit(1)

    try:
        # Use the config file's directory for output snapshots/reports
        current_outputs_dir = config_path.parent
        
        logging.info(f"Parsing configuration: {config_path}")
        parser = ConfigParser(config_path)
        devices_config = parser.parse()
        logging.info(f"Successfully identified {len(devices_config)} target devices.")

        # Determine optimal thread pool size
        max_workers = 5
        logging.info(f"Spawning {max_workers} worker threads for parallel deployment.")
        
        results = []
        # Multi-threaded execution block
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Dispatching deployment tasks
            future_to_device = {
                executor.submit(DeviceManager(device_info, current_outputs_dir).deploy_commands): device_info.ip
                for device_info in devices_config
            }
            
            # Monitoring task completion
            for future in as_completed(future_to_device):
                device_ip = future_to_device[future]
                try:
                    result = future.result()
                    results.append(result)
                    logging.info(f"DONE: Deployment for {device_ip} completed.")
                except Exception as e:
                    logging.error(f"FAILED: Deployment for {device_ip} encountered an error: {e}")
                    results.append({
                        "device": device_ip,
                        "status": "ERROR",
                        "error_message": str(e)
                    })

        # Generate final reports (Summary JSON and Consolidated TXT)
        handler = ResultHandler(current_outputs_dir)
        handler.generate_summary_report(results)
        handler.generate_consolidated_txt_report(results)
        
        # Calculate final execution time
        end_time = time.time()
        duration = end_time - start_time
        minutes, seconds = divmod(duration, 60)

        logging.info("=" * 50)
        logging.info("DEPLOYMENT SUMMARY")
        logging.info(f"Total Devices Processed: {len(devices_config)}")
        logging.info(f"Total Execution Time: {int(minutes)}m {seconds:.2f}s")
        logging.info(f"System Finished at: {datetime.datetime.now()}")
        logging.info("=" * 50)

    except Exception as e:
        logging.critical(f"FATAL SYSTEM ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()