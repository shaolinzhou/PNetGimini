import sys
import os
import json
import logging
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.core.config_parser import ConfigParser
from src.core.device_manager import DeviceManager
from src.core.result_handler import ResultHandler
from src.utils.logger import setup_logger

# Define project directories
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUTPUTS_DIR = BASE_DIR / "outputs" # Note: This is a fixed directory for reports

def main():
    """
    Main entry point for the network automation script.
    """
    LOGS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    setup_logger(LOGS_DIR)
    logging.info("Network automation deployment system started...")

    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        logging.info("No config file specified, using default 'configs/devices.yaml'")
        config_path = BASE_DIR / "configs" / "devices.yaml"

    if not config_path.exists():
        logging.error(f"Config file '{config_path}' does not exist.")
        sys.exit(1)

    try:
        # Determine the output directory based on the config file's location
        outputs_dir = config_path.parent
        outputs_dir.mkdir(exist_ok=True)
        
        logging.info(f"Parsing config file: {config_path}")
        parser = ConfigParser(config_path)
        devices_config = parser.parse()
        logging.info(f"Config file parsed successfully, found {len(devices_config)} devices.")

        # Determine the number of threads for the thread pool
        max_workers = os.cpu_count() - 2
        if max_workers <= 0:
            max_workers = 1
        logging.info(f"Using a thread pool with {max_workers} worker(s) for deployment.")
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit deployment tasks to the thread pool, passing the outputs_dir to DeviceManager
            future_to_device = {
                executor.submit(DeviceManager(device_info, outputs_dir).deploy_commands): device_info.ip
                for device_info in devices_config
            }
            
            # Collect results as they are completed
            for future in as_completed(future_to_device):
                device_ip = future_to_device[future]
                try:
                    result = future.result()
                    results.append(result)
                    logging.info(f"Deployment task for device {device_ip} completed.")
                except Exception as e:
                    logging.error(f"Deployment for device {device_ip} failed: {e}")
                    results.append({
                        "device": device_ip,
                        "status": "ERROR",
                        "error_message": str(e)
                    })

        # Generate reports after all tasks are complete
        handler = ResultHandler(outputs_dir)
        handler.generate_summary_report(results)
        handler.generate_consolidated_txt_report(results)
        
        logging.info("All device configuration tasks completed.")

    except Exception as e:
        logging.critical(f"A fatal error occurred during program execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()