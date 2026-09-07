import logging
import os
from pathlib import Path
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import datetime
import re
from ..models.device import Device

class DeviceManager:
    """
    Manages device connections and command execution, supporting various connection methods like Telnet and SSH.
    """
    def __init__(self, device: Device, outputs_dir: Path):
        self.device = device
        self.logger = logging.getLogger(__name__)
        self.outputs_dir = outputs_dir

    def _get_netmiko_device_type(self, device_type: str) -> str:
        """
        Maps the custom device type to the appropriate Netmiko device type.
        """
        telnet_mapping = {
            "cisco_ios_telnet": "cisco_ios_telnet",
            "cisco_ios": "cisco_ios_telnet",
            "huawei_router_telnet": "huawei_telnet",
        }
        
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
        """
        Creates the connection dictionary for Netmiko.
        """
        enable_secret = self.device.password
        
        return {
            "device_type": self._get_netmiko_device_type(self.device.device_type),
            "host": self.device.ip,
            "port": self.device.port,
            "username": self.device.username,
            "password": self.device.password,
            "secret": enable_secret,
            "timeout": 30,
            "global_delay_factor": 2,  # Increased delay factor for virtual lab stability
            # "session_log": "netmiko_session.log", # Uncomment this to debug login/prompt issues
        }

    def deploy_commands(self) -> dict:
        """
        Connects to the device and deploys all commands with a rollback mechanism.
        """
        self.logger.info(f"Starting deployment for device: {self.device.ip}:{self.device.port}")
        result = {
            "device": str(self.device),
            "status": "ERROR",
            "details": [],
            "error_message": None
        }

        net_connect = None
        initial_config = ""
        
        try:
            # Step 1: Establish connection
            net_connect = ConnectHandler(**self._create_connection_info())
            result["status"] = "CONNECTED"
            self.logger.info(f"Successfully connected to device: {self.device.ip}")
            
            # Enter privileged EXEC mode
            net_connect.enable()
            self.logger.info(f"Successfully entered privileged EXEC mode.")

            # Optimization: Disable paging. This is crucial before capturing config or sending long command sets.
            self.logger.info("Setting 'terminal length 0' to avoid pagination issues.")
            net_connect.send_command("terminal length 0")
            
            # Save current running-config for rollback purposes
            self.logger.info("Saving current running configuration for backup...")
            initial_config = net_connect.send_command('show running-config')
            
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            backup_filename = f"{self.device.ip}_{self.device.port}_snapshot_{timestamp}.conf"
            backup_path = self.outputs_dir / backup_filename
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(initial_config)
            self.logger.info(f"Initial configuration saved to {backup_path}")

            self.logger.info("--- Device live output started ---")

            # Step 2: Deploy new commands
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
                        self.logger.info(f"Deploying configuration set...")
                        # FIX: Do NOT manually call config_mode(). 
                        # send_config_set automatically handles 'conf t' and 'end'.
                        output = net_connect.send_config_set(
                            commands, 
                            delay_factor=2, 
                            read_timeout=30, 
                            cmd_verify=False
                        )
                        self.logger.info(output)
                    elif category == "show":
                        output = ""
                        for cmd in commands:
                            if "ping" in cmd.lower():
                                self.logger.info(f"Executing ping with extended timeout: {cmd}")
                                cmd_output = net_connect.send_command(cmd, read_timeout=60)
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
                    raise

            self.logger.info("--- Device live output ended ---")
            result["status"] = "CONFIGURED"

        except (NetmikoAuthenticationException, NetmikoTimeoutException) as e:
            self.logger.error(f"Connection or authentication failed: {e}")
            result["status"] = "ERROR"
            result["error_message"] = f"Connection or authentication failed: {e}"
        except Exception as e:
            self.logger.critical(f"An unknown error occurred during deployment: {e}", exc_info=True)
            result["status"] = "ERROR"
            result["error_message"] = str(e)
            
            # Step 3: Rollback Mechanism
            if net_connect and initial_config:
                try:
                    self.logger.warning("Deployment failed. Attempting to roll back...")
                    # Ensure paging is disabled for rollback process
                    net_connect.send_command("terminal length 0")
                    # Use a large timeout for rolling back the entire config
                    rollback_output = net_connect.send_config_set(
                        initial_config.splitlines(), 
                        read_timeout=120
                    )
                    self.logger.info("Rollback successful. Device restored to initial configuration.")
                except Exception as rollback_e:
                    self.logger.critical(f"Rollback failed: {rollback_e}", exc_info=True)
                    result["error_message"] += f" | Rollback also failed: {rollback_e}"
        
        finally:
            if net_connect:
                net_connect.disconnect()
                
        return result