import logging
from netmiko import ConnectHandler
from ..models.device import Device
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

class DeviceManager:
    """
    Manages device connections and command execution, supporting various connection methods like Telnet and SSH.
    """
    def __init__(self, device: Device):
        self.device = device
        self.logger = logging.getLogger(__name__)

    def _get_netmiko_device_type(self, device_type: str) -> str:
        """
        Maps the custom device type to the appropriate Netmiko device type.
        This can be extended in the future to support more devices and protocols (e.g., SSH, Console).
        """
        # Telnet device type mapping
        telnet_mapping = {
            "cisco_ios_telnet": "cisco_ios_telnet",
            "cisco_ios": "cisco_ios_telnet",
            "huawei_router_telnet": "huawei_telnet",
        }
        
        # SSH device type mapping (reserved for future extension)
        ssh_mapping = {
            "cisco_ios_ssh": "cisco_ios",
            "huawei_router_ssh": "huawei",
        }

        if "_telnet" in device_type:
            return telnet_mapping.get(device_type, "cisco_ios_telnet")
        elif "_ssh" in device_type:
            return ssh_mapping.get(device_type, "cisco_ios")
        
        self.logger.warning(f"Device type '{device_type}' does not specify a protocol; defaulting to Telnet.")
        return telnet_mapping.get(device_type, "cisco_ios_telnet")

    def _create_connection_info(self) -> dict:
        """Creates the connection dictionary for Netmiko."""
        # Assumes the enable password is the same as the login password for simplicity
        enable_secret = self.device.password
        
        return {
            "device_type": self._get_netmiko_device_type(self.device.device_type),
            "host": self.device.ip,
            "port": self.device.port,
            "username": self.device.username,
            "password": self.device.password,
            "secret": enable_secret,
            "timeout": 30,
            "global_delay_factor": 2,
        }

    def deploy_commands(self) -> dict:
        """
        Connects to the device and deploys all commands.
        """
        self.logger.info(f"Starting deployment for device: {self.device.ip}:{self.device.port}")
        result = {
            "device": str(self.device),
            "status": "ERROR",
            "details": [],
            "error_message": None
        }

        try:
            net_connect = ConnectHandler(**self._create_connection_info())
            
            result["status"] = "CONNECTED"
            self.logger.info(f"Successfully connected to device: {self.device.ip}")
            net_connect.enable()
            self.logger.info(f"Successfully entered privileged EXEC mode.")
            self.logger.info("--- Device live output started ---")
            
            for command_obj in self.device.commands:
                category = command_obj.category
                commands = command_obj.commands
                
                self.logger.info(f"  --- Executing command category: {category} ---")
                category_result = {
                    "category": category,
                    "commands_sent": commands,
                    "output": "",
                    "status": "SUCCESS"
                }
                
                try:
                    if category == "config":
                        self.logger.info(f"Entering configuration mode...")
                        net_connect.config_mode()
                        output = net_connect.send_config_set(commands, delay_factor=3)
                        self.logger.info(output)
                        net_connect.exit_config_mode()
                        self.logger.info(f"Exiting configuration mode.")
                    elif category == "show":
                        output = ""
                        for cmd in commands:
                            if cmd.strip().startswith("ping"):
                                self.logger.info(f"Executing ping command, using extended timeout: {cmd}")
                                cmd_output = net_connect.send_command(cmd, read_timeout=60)
                                output += cmd_output + "\n"
                                self.logger.info(cmd_output)
                            else:
                                cmd_output = net_connect.send_command(cmd)
                                output += cmd_output + "\n"
                                self.logger.info(cmd_output)
                    else:
                        output = "Unsupported command category."
                        category_result["status"] = "SKIPPED"
                        self.logger.warning(output)

                    category_result["output"] = output
                    result["details"].append(category_result)
                
                except Exception as command_e:
                    self.logger.error(f"Failed to execute command: {command_e}")
                    category_result["status"] = "ERROR"
                    category_result["output"] = str(command_e)
                    result["details"].append(category_result)

            self.logger.info("--- Device live output ended ---")
            net_connect.disconnect()
            result["status"] = "CONFIGURED"
            self.logger.info(f"Device {self.device.ip} configuration task completed.")

        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            self.logger.error(f"Connection or authentication failed: {e}")
            result["status"] = "ERROR"
            result["error_message"] = f"Connection or authentication failed: {e}"
        except Exception as e:
            self.logger.critical(f"An unknown error occurred during deployment: {e}", exc_info=True)
            result["status"] = "ERROR"
            result["error_message"] = str(e)
            
        return result