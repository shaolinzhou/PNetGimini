import json
import logging
from pathlib import Path
import datetime

class ResultHandler:
    """
    Handles command execution results and generates report files.
    """
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)

    def generate_summary_report(self, results: list):
        """Generates a summary report of all devices' statuses, saved in a single JSON file."""
        summary = {
            "timestamp": datetime.datetime.now().isoformat(),
            "total_devices": len(results),
            "summary": {
                "configured": 0,
                "error": 0,
                "disconnected": 0,
                "connected": 0
            },
            "device_results": []
        }

        for res in results:
            summary["summary"][res["status"].lower()] += 1
            summary["device_results"].append({
                "device": res["device"],
                "status": res["status"],
                "error_message": res.get("error_message")
            })

        output_file = self.output_dir / f"summary_report_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=4)

        self.logger.info(f"Generated summary report: {output_file}")
    
    def generate_consolidated_txt_report(self, results: list):
        """Generates a single, consolidated TXT report with detailed execution results for all devices."""
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        output_file_txt = self.output_dir / f"deployment_report_{timestamp}.txt"

        with open(output_file_txt, 'w', encoding='utf-8') as f:
            f.write(f"--- Network Automation Deployment Report ({datetime.datetime.now()}) ---\n\n")

            for i, res in enumerate(results):
                f.write(f"### Device {i+1} Report: {res['device']} ###\n")
                f.write(f"Status: {res['status']}\n")
                if res.get('error_message'):
                    f.write(f"Error Message: {res['error_message']}\n")
                f.write("\n--- Command Execution Details ---\n\n")

                for detail in res["details"]:
                    f.write(f"Category: {detail['category']}\n")
                    f.write(f"Status: {detail['status']}\n")
                    f.write("Commands Sent:\n")
                    for cmd in detail["commands_sent"]:
                        f.write(f"  - {cmd}\n")
                    f.write("\nDevice Output:\n")
                    f.write(detail["output"])
                    f.write("\n" + "-"*40 + "\n\n")

        self.logger.info(f"Generated consolidated TXT report: {output_file_txt}")