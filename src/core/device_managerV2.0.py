import logging
import subprocess
import os
from pathlib import Path
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import datetime
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
        Connects to the device and deploys all commands with a rollback mechanism.
        """
        self.logger.info(f"Starting deployment for device: {self.device.ip}:{self.device.port}")
        result = {
            "device": str(self.device),
            "status": "ERROR",
            "details": [],
            "error_message": None
        }

        # Initialize net_connect outside the try block for cleanup in case of connection failure
        net_connect = None
        initial_config = ""
        
        try:
            # Step 1: Establish connection and save current config for rollback
            net_connect = ConnectHandler(**self._create_connection_info())
            result["status"] = "CONNECTED"
            self.logger.info(f"Successfully connected to device: {self.device.ip}")
            net_connect.enable()
            self.logger.info(f"Successfully entered privileged EXEC mode.")
            
            # Save current running-config for rollback
            self.logger.info("Saving current running configuration for rollback purposes...")
            initial_config = net_connect.send_command('show running-config')
            
            # Generate a unique backup filename using IP, Port, and Timestamp
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
                    raise

            self.logger.info("--- Device live output ended ---")
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
            
            # Rollback Mechanism: Step 3 - Rollback if an error occurs
            # Rollback Mechanism: 故障触发回滚
def trigger_rollback(self, device_config):
    current_ip = device_config.get('ip')
    try:
        # 1. 激活转换脚本
        import subprocess
        subprocess.run(["python", "config_to_yaml.py"], check=True)

        # 2. 读取 YAML
        recovery_file = Path("configs/latest_recovery.yaml")
        with open(recovery_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 3. 匹配并执行
        for dev_data in data.get('devices', []):
            if dev_data['ip'] == current_ip:
                # 注意：这里要建立一个全新的连接实例
                rb_conn = ConnectHandler(**self._create_connection_info(device_config))
                rb_conn.enable()
                rb_conn.send_config_set(dev_data['commands']['config'])
                rb_conn.disconnect()
                self.logger.info(f"设备 {current_ip} 连接中断后回滚成功。")
                break
    except Exception as e:
        self.logger.error(f"回滚尝试失败: {e}")

def deploy_commands(self, device_config):
    try:
        # 主部署流程...
        pass
    except (EOFError, NetmikoTimeoutException):
        # 仅在此类错误下调用回滚
        self.trigger_rollback(device_config)
    except Exception as e:
        # 其他错误仅记录
        self.logger.error(f"常规错误，不触发回滚: {e}")
