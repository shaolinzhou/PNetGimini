import unittest
import os
import tempfile
import json
import logging
from pathlib import Path
from src.core.config_parser import ConfigParser
from src.models.device import Device
from src.models.command import Command
from src.core.device_manager import DeviceManager
from src.core.result_handler import ResultHandler
from src.utils.masking import mask_sensitive_data, MaskingFilter

class TestV31SecurityAndEnv(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_expand_env_vars_with_default(self):
        # Variable not in environment, default provided
        text = "host: ${UNSET_TEST_VAR_XYZ:-192.168.1.100}, port: ${UNSET_PORT_XYZ:-30001}"
        expanded = ConfigParser.expand_env_vars(text)
        self.assertEqual(expanded, "host: 192.168.1.100, port: 30001")

        # Variable not in environment, no default provided
        text_no_def = "pass: ${UNSET_PASS_NO_DEF}"
        expanded_no_def = ConfigParser.expand_env_vars(text_no_def)
        self.assertEqual(expanded_no_def, "pass: ")

    def test_expand_env_vars_with_environment_override(self):
        os.environ["PNET_TEST_IP"] = "10.200.1.1"
        os.environ["PNET_TEST_PASS"] = "SuperSecretPass999!"
        try:
            text = "ip: ${PNET_TEST_IP:-127.0.0.1}\npassword: ${PNET_TEST_PASS:-admin}"
            expanded = ConfigParser.expand_env_vars(text)
            self.assertEqual(expanded, "ip: 10.200.1.1\npassword: SuperSecretPass999!")
        finally:
            del os.environ["PNET_TEST_IP"]
            del os.environ["PNET_TEST_PASS"]

    def test_load_dotenv_file(self):
        env_file = self.output_dir / ".env"
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("# Sample env\nEVE_TEST_KEY_ALPHA=secret_token_12345\nEVE_TEST_KEY_BETA='quoted_value'\n")

        ConfigParser.load_dotenv(env_file)
        self.assertEqual(os.environ.get("EVE_TEST_KEY_ALPHA"), "secret_token_12345")
        self.assertEqual(os.environ.get("EVE_TEST_KEY_BETA"), "quoted_value")

        # Clean up
        if "EVE_TEST_KEY_ALPHA" in os.environ:
            del os.environ["EVE_TEST_KEY_ALPHA"]
        if "EVE_TEST_KEY_BETA" in os.environ:
            del os.environ["EVE_TEST_KEY_BETA"]

    def test_config_parser_full_yaml_with_env(self):
        yaml_file = self.output_dir / "devices_env_test.yaml"
        yaml_content = """
devices:
  - ip: "${MOCK_EVE_IP:-10.50.0.1}"
    port: ${MOCK_EVE_PORT:-32769}
    username: "${MOCK_EVE_USER:-admin}"
    password: "${MOCK_EVE_PASS:-Cisco123!}"
    secret: "${MOCK_EVE_SEC:-EnableSecret!}"
    key_file: "${MOCK_EVE_KEY:-/home/user/.ssh/id_rsa}"
    device_type: cisco_ios_telnet
    commands:
      config:
        - hostname Lab_R1
"""
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        parser = ConfigParser(yaml_file)
        devices = parser.parse()

        self.assertEqual(len(devices), 1)
        dev = devices[0]
        self.assertEqual(dev.ip, "10.50.0.1")
        self.assertEqual(dev.port, 32769)
        self.assertEqual(dev.username, "admin")
        self.assertEqual(dev.password, "Cisco123!")
        self.assertEqual(dev.secret, "EnableSecret!")
        self.assertEqual(dev.key_file, "/home/user/.ssh/id_rsa")

    def test_mask_sensitive_data_patterns(self):
        samples = [
            ("enable password MySecretPassword1", "enable password ********"),
            ("username admin secret 5 $1$mERr$hp5p8Q0", "username admin secret 5 ********"),
            ("snmp-server community MySnmpComm RO", "snmp-server community ******** RO"),
            ("pre-shared-key HighlySensitivePresharedKey", "pre-shared-key ********"),
            ("key-string AuthKey99", "key-string ********"),
            ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "Authorization: Bearer ********"),
            ("token: 'xyz987token'", "token: ********"),
        ]

        for original, expected in samples:
            sanitized = mask_sensitive_data(original)
            self.assertEqual(sanitized, expected, f"Failed for input: {original}")

    def test_masking_filter_in_logger(self):
        logger = logging.getLogger("test_masking_logger")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        log_capture = []
        class CaptureHandler(logging.Handler):
            def emit(self, record):
                log_capture.append(self.format(record))

        handler = CaptureHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.addFilter(MaskingFilter())
        logger.addHandler(handler)

        logger.info("Executing: enable secret MySecretPassword")
        logger.info("Connecting with token: my_secret_token_123")

        self.assertEqual(len(log_capture), 2)
        self.assertNotIn("MySecretPassword", log_capture[0])
        self.assertIn("enable secret ********", log_capture[0])
        self.assertNotIn("my_secret_token_123", log_capture[1])
        self.assertIn("token: ********", log_capture[1])

    def test_device_manager_ssh_key_connection_info(self):
        dev = Device(
            ip="192.168.1.1",
            port=22,
            username="admin",
            device_type="cisco_ios_ssh",
            key_file="/path/to/private_key.pem",
            passphrase="key_passphrase_here"
        )
        mgr = DeviceManager(dev, self.output_dir)
        conn_dict = mgr._create_connection_info()

        self.assertTrue(conn_dict.get("use_keys"))
        self.assertEqual(conn_dict.get("key_file"), "/path/to/private_key.pem")
        self.assertEqual(conn_dict.get("passphrase"), "key_passphrase_here")

    def test_result_handler_desensitization(self):
        handler = ResultHandler(self.output_dir)
        results = [
            {
                "device": "10.0.0.1",
                "status": "ERROR",
                "error_message": "Failed when applying password ClearTextPassword123!",
                "details": [
                    {
                        "category": "config",
                        "status": "ERROR",
                        "commands_sent": ["enable password SecretPass"],
                        "output": "Error: Rejected password SecretPass"
                    }
                ]
            }
        ]

        handler.generate_summary_report(results)
        handler.generate_consolidated_txt_report(results)

        # Inspect JSON summary
        json_files = list(self.output_dir.glob("summary_report_*.json"))
        self.assertEqual(len(json_files), 1)
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
            err_msg = data["device_results"][0]["error_message"]
            self.assertNotIn("ClearTextPassword123!", err_msg)
            self.assertIn("password ********", err_msg)

        # Inspect TXT report
        txt_files = list(self.output_dir.glob("deployment_report_*.txt"))
        self.assertEqual(len(txt_files), 1)
        with open(txt_files[0], "r", encoding="utf-8") as f:
            txt_content = f.read()
            self.assertNotIn("ClearTextPassword123!", txt_content)
            self.assertNotIn("SecretPass", txt_content)
            self.assertIn("password ********", txt_content)

if __name__ == "__main__":
    unittest.main()
