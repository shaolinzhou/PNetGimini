import sys
import os
import time
import logging
import datetime
import argparse
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Importing modular components from the project structure
from src.core.config_parser import ConfigParser
from src.core.device_manager import DeviceManager
from src.core.async_engine import AsyncDeploymentEngine
from src.core.result_handler import ResultHandler
from src.utils.logger import setup_logger
from src.plugins.eve_iac_connector import EveIacConnector

# Project directory definitions
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
OUTPUTS_DIR = BASE_DIR / "outputs"

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="PNetGimini: Enterprise-Grade High-Concurrency Network Automation Deployment System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=str(BASE_DIR / "configs" / "devices.yaml"),
        help="Path to devices.yaml configuration file (ignored if --eve-lab is provided)"
    )
    parser.add_argument(
        "--engine",
        choices=["async", "thread"],
        default="async",
        help="Concurrency execution engine ('async' for asyncio coroutines, 'thread' for ThreadPoolExecutor)"
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=10,
        help="Maximum concurrent device provisioning connections"
    )
    parser.add_argument(
        "--eve-lab",
        dest="eve_lab",
        default=None,
        help="EVE IaC lab ID/name for dynamic inventory discovery (e.g., dc_spine_leaf.unl)"
    )
    parser.add_argument(
        "--eve-url",
        dest="eve_url",
        default=None,
        help="EVE IaC API server URL (overrides EVE_IAC_URL env variable)"
    )
    parser.add_argument(
        "--eve-token",
        dest="eve_token",
        default=None,
        help="EVE IaC Bearer Token (overrides EVE_IAC_TOKEN env variable)"
    )
    parser.add_argument(
        "--intent",
        dest="intent",
        default=None,
        help="Path to intent configuration file or directory to pair with discovered lab devices"
    )
    parser.add_argument(
        "--no-wait-console",
        dest="wait_console",
        action="store_false",
        default=True,
        help="Disable waiting for console prompt readiness synchronization"
    )
    parser.add_argument(
        "--offline",
        dest="offline",
        action="store_true",
        default=False,
        help="Enable offline simulation mode for EVE IaC connector without connecting to real server"
    )
    return parser.parse_args()

def main():
    """
    Main entry point for the network automation deployment system.
    Features: Asyncio / Multi-threading, Intelligent Diff-based Rollbacks, and Snapshots.
    """
    args = parse_arguments()

    # Load environment variables from .env if present
    ConfigParser.load_dotenv()

    # Initialize necessary directories
    LOGS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    
    # Initialize logger (with integrated MaskingFilter for desensitization)
    setup_logger(LOGS_DIR)
    
    # Start the execution timer
    start_timestamp = datetime.datetime.now()
    start_time = time.time()
    
    logging.info("=" * 60)
    logging.info(f"PNetGimini System Started at: {start_timestamp}")
    logging.info(f"Active Engine: {args.engine.upper()} | Concurrency limit: {args.concurrency}")
    if args.eve_lab:
        logging.info(f"Target Mode: EVE IaC Dynamic Discovery | Lab: '{args.eve_lab}'")
    else:
        logging.info(f"Target Mode: Static YAML Inventory | File: '{args.config}'")
    logging.info("=" * 60)

    connector = None
    try:
        if args.eve_lab:
            logging.info(f"Engaging EVE IaC Connector for lab project: '{args.eve_lab}'")
            connector = EveIacConnector(
                url=args.eve_url,
                token=args.eve_token,
                offline_mode=args.offline
            )
            current_outputs_dir = (
                Path(args.intent).parent if args.intent and Path(args.intent).is_file() else OUTPUTS_DIR
            )
            devices_config = connector.load_lab_devices(
                lab_id=args.eve_lab,
                intent_path=args.intent,
                wait_readiness=args.wait_console
            )
            logging.info(f"EVE IaC Discovery: Successfully prepared {len(devices_config)} devices for deployment.")
        else:
            config_path = Path(args.config)
            if not config_path.exists():
                logging.error(f"Critical Error: Configuration file '{config_path}' not found.")
                sys.exit(1)

            # Use the config file's directory for output snapshots/reports
            current_outputs_dir = config_path.parent
            
            logging.info(f"Parsing configuration: {config_path}")
            parser = ConfigParser(config_path)
            devices_config = parser.parse()
            logging.info(f"Successfully identified {len(devices_config)} target devices.")

        if not devices_config:
            logging.warning("No valid devices found to process. Exiting.")
            sys.exit(0)

        results = []

        if args.engine == "async":
            logging.info(f"Engaging AsyncDeploymentEngine with semaphore limit {args.concurrency}...")
            engine = AsyncDeploymentEngine(
                devices=devices_config,
                outputs_dir=current_outputs_dir,
                concurrency=args.concurrency
            )
            results = asyncio.run(engine.run())

        else:
            # Classic ThreadPoolExecutor fallback
            max_workers = min(args.concurrency, len(devices_config))
            logging.info(f"Spawning {max_workers} worker threads for parallel deployment.")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_device = {
                    executor.submit(DeviceManager(device_info, current_outputs_dir).deploy_commands): device_info.ip
                    for device_info in devices_config
                }
                
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

        # Phase 3 (v3.3): If EVE IaC chaos tests are defined, execute digital twin chaos experiments
        if args.eve_lab and connector and hasattr(connector, "chaos_tests") and connector.chaos_tests:
            logging.info("=" * 60)
            logging.info(f"Engaging ChaosOrchestrator for {len(connector.chaos_tests)} digital twin chaos experiment(s)...")
            from src.plugins.chaos_orchestrator import ChaosOrchestrator
            orchestrator = ChaosOrchestrator(connector)
            chaos_results = orchestrator.run_suite(args.eve_lab, connector.chaos_tests)
            logging.info(f"Chaos Experiments Complete: {len(chaos_results)} executed.")
            logging.info("=" * 60)
        
        # Calculate final execution time
        end_time = time.time()
        duration = end_time - start_time
        minutes, seconds = divmod(duration, 60)

        configured_count = sum(1 for r in results if r.get("status") == "CONFIGURED")
        rolled_back_count = sum(1 for r in results if r.get("rollback_applied"))
        error_count = sum(1 for r in results if r.get("status") == "ERROR")

        logging.info("=" * 60)
        logging.info("DEPLOYMENT SUMMARY")
        logging.info(f"Engine: {args.engine.upper()} | Concurrency: {args.concurrency}")
        logging.info(f"Total Devices Processed: {len(devices_config)}")
        logging.info(f"Successfully Configured: {configured_count}")
        logging.info(f"Rolled Back (Self-Healed): {rolled_back_count}")
        logging.info(f"Errors: {error_count}")
        logging.info(f"Total Execution Time: {int(minutes)}m {seconds:.2f}s")
        logging.info(f"System Finished at: {datetime.datetime.now()}")
        logging.info("=" * 60)

    except Exception as e:
        logging.critical(f"FATAL SYSTEM ERROR: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()