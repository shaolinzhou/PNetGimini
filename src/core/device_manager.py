import logging
import os
from pathlib import Path
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import datetime
import re
from typing import List

from ..models.device import Device
from .adapters.factory import AdapterFactory
from .config_diff import ConfigDiffEngine

class DeviceManager:
    """
    Manages device connections, command deployment, and intelligent diff-based recovery.
    Supports multi-vendor abstraction (Cisco, Huawei) and structured snapshot lifecycle management.
    """
    def __init__(self, device: Device, outputs_dir: Path):
        self.device = device
        self.logger = logging.getLogger(__name__)
        self.outputs_dir = outputs_dir
        self.snapshots_dir = self.outputs_dir / "snapshots"
        self.adapter = AdapterFactory.get_adapter(self.device.device_type)

    def _create_connection_info(self) -> dict:
        """
        Creates the connection dictionary for Netmiko using vendor adapter mappings.
        """
        enable_secret = self.device.password
        netmiko_type = self.adapter.get_netmiko_device_type(self.device.device_type)
        
        return {
            "device_type": netmiko_type,
            "host": self.device.ip,
            "port": self.device.port,
            "username": self.device.username,
            "password": self.device.password,
            "secret": enable_secret,
            "timeout": 30,
            "global_delay_factor": 2,  # Increased delay factor for virtual lab stability
        }

    def deploy_commands(self) -> dict:
        """
        Connects to the device and deploys commands with an intelligent diff-based rollback mechanism.
        """
        self.logger.info(f"Starting deployment for device: {self.device.ip}:{self.device.port} ({self.device.device_type})")
        result = {
            "device": str(self.device),
            "status": "ERROR",
            "details": [],
            "error_message": None,
            "snapshot_file": None,
            "rollback_applied": False,
            "rollback_type": None
        }

        net_connect = None
        initial_config = ""
        deployed_config_commands: List[str] = []
        
        try:
            # Step 1: Establish connection
            net_connect = ConnectHandler(**self._create_connection_info())
            result["status"] = "CONNECTED"
            self.logger.info(f"Successfully connected to device: {self.device.ip}")
            
            # Enter privileged EXEC mode if applicable
            try:
                net_connect.enable()
                self.logger.info(f"Successfully entered privileged EXEC / system mode.")
            except Exception as enable_err:
                self.logger.debug(f"Enable mode skipped or not required: {enable_err}")

            # Optimization: Disable paging using vendor-specific command
            paging_cmd = self.adapter.get_disable_paging_command()
            self.logger.info(f"Disabling pagination with: '{paging_cmd}'")
            net_connect.send_command(paging_cmd)
            
            # Step 2: Save current running-config for baseline snapshot
            snapshot_cmd = self.adapter.get_snapshot_command()
            self.logger.info(f"Capturing pre-change running configuration snapshot via: '{snapshot_cmd}'")
            initial_config = net_connect.send_command(snapshot_cmd)
            
            # Ensure snapshots directory exists
            self.snapshots_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            backup_filename = f"{self.device.ip}_{self.device.port}_snapshot_{timestamp}.conf"
            backup_path = self.snapshots_dir / backup_filename
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(initial_config)
            result["snapshot_file"] = str(backup_path)
            self.logger.info(f"Pre-change snapshot archived to: {backup_path}")

            self.logger.info("--- Device live output started ---")

            # Step 3: Deploy new commands
            for command_obj in self.device.commands:
                category = command_obj.category.lower()
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
                        self.logger.info(f"Deploying configuration set ({len(commands)} commands)...")
                        # Track commands intended/attempted for precision diff rollback in case of failure
                        deployed_config_commands.extend(commands)
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

                    elif category in ("verify", "check", "assert"):
                        # Post-Check validation block: proactive verification
                        output = ""
                        for cmd in commands:
                            cmd_output = net_connect.send_command(cmd, read_timeout=45)
                            output += cmd_output + "\n"
                            self.logger.info(cmd_output)
                            
                            # Detect common network failure patterns
                            lowered = cmd_output.lower()
                            if "ping" in cmd.lower() and ("0.00% packet success" in lowered or "success rate is 0 percent" in lowered):
                                raise RuntimeError(f"Proactive Verification Failed: {cmd} reported 0% packet success.")

                    else:
                        output = f"Unsupported command category '{category}'."
                        category_result["status"] = "SKIPPED"
                        self.logger.warning(output)

                    category_result["output"] = output
                    result["details"].append(category_result)
                
                except Exception as command_e:
                    self.logger.error(f"Failed to execute {category} command: {command_e}")
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
            self.logger.critical(f"An error occurred during deployment on {self.device.ip}: {e}", exc_info=True)
            result["status"] = "ERROR"
            result["error_message"] = str(e)
            
            # Step 4: Intelligent Diff-based Rollback Mechanism
            if net_connect and initial_config:
                try:
                    self.logger.warning(f"Deployment failed on {self.device.ip}. Computing rollback strategy...")
                    net_connect.send_command(self.adapter.get_disable_paging_command())
                    
                    # Compute minimal diff-based reversal patch
                    reversal_plan = ConfigDiffEngine.compute_reversion_plan(
                        baseline_raw=initial_config,
                        deployed_commands=deployed_config_commands,
                        adapter=self.adapter
                    )

                    if reversal_plan:
                        self.logger.warning(f"Applying intelligent DIFF-BASED rollback ({len(reversal_plan)} commands): {reversal_plan}")
                        rollback_output = net_connect.send_config_set(
                            reversal_plan,
                            delay_factor=2,
                            read_timeout=60,
                            cmd_verify=False
                        )
                        result["rollback_applied"] = True
                        result["rollback_type"] = "DIFF_BASED"
                        self.logger.info(f"Diff-based rollback completed successfully on {self.device.ip}.")
                    else:
                        # Fallback to cleaned baseline if no diff could be determined
                        self.logger.warning(f"No specific diff calculated; falling back to clean baseline restore.")
                        clean_baseline = ConfigDiffEngine.get_clean_baseline_commands(initial_config, self.adapter)
                        rollback_output = net_connect.send_config_set(
                            clean_baseline,
                            delay_factor=2,
                            read_timeout=120,
                            cmd_verify=False
                        )
                        result["rollback_applied"] = True
                        result["rollback_type"] = "CLEAN_BASELINE"
                        self.logger.info(f"Clean baseline restore completed on {self.device.ip}.")

                except Exception as rollback_e:
                    self.logger.critical(f"Rollback execution failed on {self.device.ip}: {rollback_e}", exc_info=True)
                    result["error_message"] += f" | Rollback also failed: {rollback_e}"
        
        finally:
            if net_connect:
                try:
                    net_connect.disconnect()
                except Exception:
                    pass
                
        return result