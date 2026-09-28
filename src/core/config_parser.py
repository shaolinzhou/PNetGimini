import logging
import os
import re
import yaml
from pathlib import Path
from ..models.device import Device
from ..models.command import Command

ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::-([^}]*))?\}")

class ConfigParser:
    """
    Parses devices.yaml file and transforms YAML content into structured Device and Command objects.
    Supports environment variable placeholder substitution (${VAR:-default}), .env loading, and SSH keys.
    """
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    @classmethod
    def load_dotenv(cls, env_path: Path = None):
        """
        Loads key-value pairs from .env file into os.environ if not already set.
        """
        targets = []
        if env_path and env_path.exists():
            targets.append(env_path)
        else:
            targets.extend([
                Path(".env"),
                Path.cwd() / ".env",
                Path(__file__).resolve().parent.parent.parent / ".env"
            ])

        for target in targets:
            if target.exists() and target.is_file():
                try:
                    with open(target, "r", encoding="utf-8") as f:
                        for line in f:
                            stripped = line.strip()
                            if not stripped or stripped.startswith("#"):
                                continue
                            if "=" in stripped:
                                key, val = stripped.split("=", 1)
                                key = key.strip()
                                val = val.strip().strip("'\"")
                                if key not in os.environ:
                                    os.environ[key] = val
                    break
                except Exception:
                    pass

    @classmethod
    def expand_env_vars(cls, text: str) -> str:
        """
        Substitutes ${VAR_NAME:-default} or ${VAR_NAME} placeholders with environment variable values.
        """
        def _replace(match):
            var_name = match.group(1)
            default_val = match.group(2)
            val = os.environ.get(var_name)
            if val is not None:
                return val
            if default_val is not None:
                return default_val
            return ""

        return ENV_VAR_PATTERN.sub(_replace, text)

    def parse(self) -> list:
        """
        Primary parsing method to load, expand environment variables, and validate YAML configuration.
        """
        # Ensure .env is checked
        self.load_dotenv(self.file_path.parent / ".env")

        devices = []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            # Dynamic environment variable interpolation
            expanded_content = self.expand_env_vars(raw_content)
            yaml_data = yaml.safe_load(expanded_content)

            # Check if root key is 'devices'
            if not isinstance(yaml_data, dict) or 'devices' not in yaml_data:
                self.logger.error("YAML configuration format error: root key must be 'devices'")
                return []

            # Iterate over all devices
            for device_data in yaml_data['devices']:
                ip = device_data.get('ip')
                port = device_data.get('port')
                device_type = device_data.get('device_type')

                # Authentication parameters
                username = device_data.get('username') or ""
                password = device_data.get('password') or ""
                secret = device_data.get('secret')
                key_file = device_data.get('key_file')
                passphrase = device_data.get('passphrase')

                # Ensure port is an integer if provided as string
                if port is not None:
                    try:
                        port = int(port)
                    except ValueError:
                        self.logger.warning(f"Invalid port value '{port}' for device {ip}, skipping.")
                        continue

                # Basic validation: IP, Port, and Device Type are mandatory
                if not (ip and port and device_type):
                    self.logger.warning(f"Incomplete device specification, skipping: {device_data}")
                    continue

                device = Device(
                    ip=str(ip),
                    port=port,
                    username=str(username),
                    password=str(password),
                    device_type=str(device_type),
                    secret=str(secret) if secret is not None else None,
                    key_file=str(key_file) if key_file else None,
                    passphrase=str(passphrase) if passphrase else None
                )

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