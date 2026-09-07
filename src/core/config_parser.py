import logging
import yaml
from pathlib import Path
from ..models.device import Device
from ..models.command import Command

class ConfigParser:
    """
    Parses devices.yaml file and transforms YAML content into structured Device and Command objects.
    """
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def parse(self) -> list:
        """
        Primary parsing method to load and validate YAML configuration.
        """
        devices = []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            # Check if root key is 'devices'
            if not isinstance(yaml_data, dict) or 'devices' not in yaml_data:
                self.logger.error("YAML configuration format error: root key must be 'devices'")
                return []

            # Iterate over all devices
            for device_data in yaml_data['devices']:
                ip = device_data.get('ip')
                port = device_data.get('port')
                username = device_data.get('username')
                password = device_data.get('password')
                device_type = device_data.get('device_type')

                if not all([ip, port, username, password, device_type]):
                    self.logger.warning(f"Incomplete device specification, skipping: {device_data}")
                    continue

                device = Device(ip, port, username, password, device_type)

                # Iterate through command categories and commands
                commands_data = device_data.get('commands', {})
                for category, command_list in commands_data.items():
                    if isinstance(command_list, list) and command_list:
                        command = Command(category, command_list)
                        device.add_command(command)
                    else:
                        self.logger.warning(f"Device {ip} command category '{category}' is invalid or empty, skipping.")

                devices.append(device)

        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse YAML file: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error while parsing configuration: {e}")
            return []

        return devices