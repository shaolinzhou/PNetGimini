import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.plugins.eve_iac_connector import EveIacConnector
from src.models.device import Device
from src.models.command import Command


class TestEveIacConnector(unittest.TestCase):
    """
    Test suite for Phase 2 (v3.2) EveIacConnector plugin.
    Verifies dynamic inventory discovery, wait_console readiness, intent binding,
    and offline mock fallback.
    """

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_init_defaults_and_env(self):
        """Test connector initialization and environment variable fallback."""
        with patch.dict(os.environ, {"EVE_IAC_URL": "http://eve.test:9000", "EVE_IAC_TOKEN": "env-token-xyz"}):
            connector = EveIacConnector()
            self.assertEqual(connector.url, "http://eve.test:9000")
            self.assertEqual(connector.token, "env-token-xyz")
            self.assertFalse(connector.offline_mode)

    def test_offline_mode_mock_consoles(self):
        """Test offline simulation mode returns structured mock consoles."""
        connector = EveIacConnector(offline_mode=True)
        consoles = connector.list_consoles("lab_datacenter.unl")
        self.assertEqual(len(consoles), 3)
        self.assertEqual(consoles[0]["name"], "Spine-01")
        self.assertEqual(consoles[0]["port"], 30001)
        self.assertEqual(consoles[1]["name"], "Leaf-01")
        self.assertEqual(consoles[2]["name"], "Huawei-Core")

    def test_detect_device_type(self):
        """Test intelligent device type detection based on node naming."""
        connector = EveIacConnector()
        # Cisco default
        self.assertEqual(connector.detect_device_type("R1_Cisco_Spine", "telnet"), "cisco_ios_telnet")
        self.assertEqual(connector.detect_device_type("R1_Cisco_Spine", "ssh"), "cisco_ios")
        # Huawei
        self.assertEqual(connector.detect_device_type("Core_Huawei_VRP", "telnet"), "huawei_vrp_telnet")
        self.assertEqual(connector.detect_device_type("Core_Huawei_VRP", "ssh"), "huawei_vrp")
        # Arista
        self.assertEqual(connector.detect_device_type("Leaf_Arista_EOS", "telnet"), "arista_eos_telnet")
        # Juniper
        self.assertEqual(connector.detect_device_type("Edge_Juniper_Junos", "telnet"), "juniper_junos_telnet")

    def test_authenticate_with_token(self):
        """Test authentication succeeds immediately if token is already set."""
        connector = EveIacConnector(token="existing-bearer-token")
        self.assertTrue(connector.authenticate())

    def test_authenticate_login_http(self):
        """Test HTTP REST authentication flow via login."""
        connector = EveIacConnector(
            url="http://eve.test:8080",
            username="admin",
            password="eve-password"
        )
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps({"token": "jwt-token-12345"}).encode("utf-8")
        fake_response.__enter__.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=fake_response) as mock_urlopen:
            success = connector.authenticate()
            self.assertTrue(success)
            self.assertEqual(connector.token, "jwt-token-12345")
            self.assertTrue(mock_urlopen.called)

    def test_list_consoles_rest_api(self):
        """Test REST API query to /api/v1/projects/{lab}/consoles."""
        connector = EveIacConnector(url="http://eve.test:8080", token="jwt-token")
        mock_payload = {
            "consoles": [
                {
                    "node": "n_1",
                    "name": "Edge-Router-1",
                    "status": "running",
                    "protocol": "telnet",
                    "host": "10.0.0.50",
                    "port": 32001
                }
            ]
        }
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        fake_response.__enter__.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=fake_response):
            consoles = connector.list_consoles("project_alpha")
            self.assertEqual(len(consoles), 1)
            self.assertEqual(consoles[0]["name"], "Edge-Router-1")
            self.assertEqual(consoles[0]["port"], 32001)

    def test_wait_console_rest_api(self):
        """Test REST API wait_console probe to EVE IaC server."""
        connector = EveIacConnector(url="http://eve.test:8080", token="jwt-token")
        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps({"status": "ready"}).encode("utf-8")
        fake_response.status = 200
        fake_response.__enter__.return_value = fake_response

        with patch("urllib.request.urlopen", return_value=fake_response):
            ready = connector.wait_console("project_alpha", "n_1", timeout=5)
            self.assertTrue(ready)

    def test_load_lab_devices_mock(self):
        """Test load_lab_devices converts console records directly into Device objects."""
        connector = EveIacConnector(offline_mode=True)
        devices = connector.load_lab_devices("lab_dc.unl", wait_readiness=True)
        self.assertEqual(len(devices), 3)

        dev_names = [d.name for d in devices]
        self.assertIn("Spine-01", dev_names)
        self.assertIn("Leaf-01", dev_names)
        self.assertIn("Huawei-Core", dev_names)

        # Check Huawei device type correctly inferred
        huawei_dev = next(d for d in devices if d.name == "Huawei-Core")
        self.assertEqual(huawei_dev.device_type, "huawei_vrp_telnet")
        self.assertEqual(huawei_dev.port, 30003)

    def test_bind_intent_from_file(self):
        """Test binding commands to discovered devices from a YAML intent file."""
        intent_file = self.tmp_path / "lab_intent.yaml"
        intent_content = """
Spine-01:
  config:
    - hostname Spine-01
    - router ospf 1
    - network 10.0.0.0 0.255.255.255 area 0
  show:
    - show ip ospf neighbor
  verify:
    - ping 10.0.0.2

Leaf-01:
  config:
    - hostname Leaf-01
    - interface GigabitEthernet0/1
    - no shutdown
"""
        intent_file.write_text(intent_content.strip(), encoding="utf-8")

        connector = EveIacConnector(offline_mode=True)
        devices = connector.load_lab_devices("lab_dc.unl", intent_path=str(intent_file), wait_readiness=False)

        spine = next(d for d in devices if d.name == "Spine-01")
        self.assertEqual(len(spine.commands), 3)  # config, show, verify
        self.assertEqual(spine.commands[0].category, "config")
        self.assertIn("router ospf 1", spine.commands[0].commands)

        leaf = next(d for d in devices if d.name == "Leaf-01")
        self.assertEqual(len(leaf.commands), 1)
        self.assertEqual(leaf.commands[0].category, "config")

    def test_bind_intent_from_directory(self):
        """Test binding commands from individual per-node configuration snippet files."""
        intent_dir = self.tmp_path / "intent_dir"
        intent_dir.mkdir()

        (intent_dir / "Spine-01.cfg").write_text("hostname Spine-01\ninterface Loopback0\nip address 1.1.1.1 255.255.255.255\n", encoding="utf-8")
        (intent_dir / "Leaf-01.txt").write_text("hostname Leaf-01\ninterface Loopback0\nip address 2.2.2.2 255.255.255.255\n", encoding="utf-8")

        connector = EveIacConnector(offline_mode=True)
        devices = connector.load_lab_devices("lab_dc.unl", intent_path=str(intent_dir), wait_readiness=False)

        spine = next(d for d in devices if d.name == "Spine-01")
        self.assertEqual(len(spine.commands), 1)
        self.assertEqual(spine.commands[0].category, "config")
        self.assertIn("hostname Spine-01", spine.commands[0].commands)
        self.assertIn("ip address 1.1.1.1 255.255.255.255", spine.commands[0].commands)

    @patch("main.AsyncDeploymentEngine")
    @patch("main.asyncio.run")
    @patch("main.ResultHandler")
    def test_main_cli_with_eve_lab(self, mock_result_handler, mock_asyncio_run, mock_engine_cls):
        """Test main.py CLI with --eve-lab in offline simulation mode."""
        from main import main as cli_main

        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_asyncio_run.return_value = [
            {"device": "127.0.0.1", "status": "CONFIGURED", "rollback_applied": False}
        ]

        test_args = [
            "main.py",
            "--eve-lab", "spine_leaf_dc.unl",
            "--offline",
            "--no-wait-console"
        ]
        with patch.object(sys, "argv", test_args):
            cli_main()
            self.assertTrue(mock_asyncio_run.called)


if __name__ == "__main__":
    unittest.main()

