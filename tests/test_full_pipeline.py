import unittest
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config_parser import ConfigParser
from src.core.result_handler import ResultHandler
from src.core.device_manager import DeviceManager
from src.models.device import Device
from src.models.command import Command
import config_to_yaml

class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.yaml_file = Path(self.temp_dir) / "test_devices.yaml"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_valid_yaml(self):
        content = """
        devices:
          - ip: 192.168.10.1
            port: 30001
            username: admin
            password: password123
            device_type: cisco_ios_telnet
            commands:
              config:
                - hostname R1
                - interface e0/0
              show:
                - show ip int brief
              verify:
                - ping 192.168.10.254
        """
        self.yaml_file.write_text(content, encoding="utf-8")
        parser = ConfigParser(self.yaml_file)
        devices = parser.parse()

        self.assertEqual(len(devices), 1)
        device = devices[0]
        self.assertEqual(device.ip, "192.168.10.1")
        self.assertEqual(device.port, 30001)
        self.assertEqual(len(device.commands), 3)

    def test_parse_invalid_yaml_missing_fields(self):
        content = """
        devices:
          - ip: 192.168.10.1
            # Missing port, username, password
            device_type: cisco_ios_telnet
        """
        self.yaml_file.write_text(content, encoding="utf-8")
        parser = ConfigParser(self.yaml_file)
        devices = parser.parse()
        self.assertEqual(len(devices), 0)

class TestResultHandler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.handler = ResultHandler(self.output_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_summary_and_txt_reports(self):
        results = [
            {
                "device": "192.168.1.1:30001:admin:***:cisco_ios_telnet",
                "status": "CONFIGURED",
                "details": [
                    {
                        "category": "config",
                        "commands_sent": ["hostname R1"],
                        "output": "R1(config)#hostname R1",
                        "status": "SUCCESS"
                    }
                ],
                "error_message": None
            },
            {
                "device": "192.168.1.2:30002:admin:***:cisco_ios_telnet",
                "status": "ERROR",
                "details": [],
                "error_message": "Connection refused"
            }
        ]

        self.handler.generate_summary_report(results)
        self.handler.generate_consolidated_txt_report(results)

        json_files = list(self.output_dir.glob("summary_report_*.json"))
        txt_files = list(self.output_dir.glob("deployment_report_*.txt"))

        self.assertEqual(len(json_files), 1)
        self.assertEqual(len(txt_files), 1)

        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["total_devices"], 2)
            self.assertEqual(data["summary"]["configured"], 1)
            self.assertEqual(data["summary"]["error"], 1)

class TestDeviceManagerExecution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)
        self.device = Device("10.0.0.1", 30001, "admin", "admin", "cisco_ios_telnet")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.core.device_manager.ConnectHandler")
    def test_successful_deployment(self, mock_connect):
        mock_handler = MagicMock()
        mock_connect.return_value = mock_handler
        mock_handler.send_command.return_value = "hostname R1\ninterface e0/0\n"
        mock_handler.send_config_set.return_value = "Applied OK"

        self.device.add_command(Command("config", ["interface e0/0", "no shutdown"]))
        self.device.add_command(Command("show", ["show ip int brief"]))

        mgr = DeviceManager(self.device, self.output_dir)
        result = mgr.deploy_commands()

        self.assertEqual(result["status"], "CONFIGURED")
        self.assertFalse(result["rollback_applied"])
        self.assertTrue((self.output_dir / "snapshots").exists())

    @patch("src.core.device_manager.ConnectHandler")
    def test_failed_deployment_triggers_diff_rollback(self, mock_connect):
        mock_handler = MagicMock()
        mock_connect.return_value = mock_handler
        mock_handler.send_command.return_value = "hostname R1\n"
        
        # Simulate config command raising an error
        mock_handler.send_config_set.side_effect = [
            RuntimeError("Syntax error at % Invalid input"),
            "Rollback OK"
        ]

        self.device.add_command(Command("config", ["router ospf 100", "invalid command"]))

        mgr = DeviceManager(self.device, self.output_dir)
        result = mgr.deploy_commands()

        self.assertEqual(result["status"], "ERROR")
        self.assertTrue(result["rollback_applied"])
        self.assertEqual(result["rollback_type"], "DIFF_BASED")

class TestConfigToYamlTool(unittest.TestCase):
    def test_parse_filename_info(self):
        valid_name = "192.168.1.100_30001_snapshot_20260908120000.conf"
        info = config_to_yaml.parse_filename_info(valid_name)
        self.assertIsNotNone(info)
        self.assertEqual(info["ip"], "192.168.1.100")
        self.assertEqual(info["port"], 30001)
        self.assertEqual(info["timestamp"], "20260908120000")

        invalid_name = "random_text.txt"
        self.assertIsNone(config_to_yaml.parse_filename_info(invalid_name))

if __name__ == "__main__":
    unittest.main()
