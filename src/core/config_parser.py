import logging
import yaml
from pathlib import Path
from ..models.device import Device
from ..models.command import Command

class ConfigParser:
    """
    解析 devices.yaml 文件，将 YAML 内容转换为结构化的设备和命令对象。
    """
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def parse(self) -> list:
        """
        主解析方法，加载 YAML 文件
        """
        devices = []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)

            # 检查根键是否为 'devices'
            if not isinstance(yaml_data, dict) or 'devices' not in yaml_data:
                self.logger.error("YAML 配置文件格式错误，根键必须为 'devices'")
                return []

            # 遍历所有设备
            for device_data in yaml_data['devices']:
                ip = device_data.get('ip')
                port = device_data.get('port')
                username = device_data.get('username')
                password = device_data.get('password')
                device_type = device_data.get('device_type')

                if not all([ip, port, username, password, device_type]):
                    self.logger.warning(f"设备信息不完整，跳过: {device_data}")
                    continue

                device = Device(ip, port, username, password, device_type)

                # 遍历命令类别和命令集
                commands_data = device_data.get('commands', {})
                for category, command_list in commands_data.items():
                    if isinstance(command_list, list) and command_list:
                        command = Command(category, command_list)
                        device.add_command(command)
                    else:
                        self.logger.warning(f"设备 {ip} 的命令类别 '{category}' 格式错误或为空，跳过。")

                devices.append(device)

        except yaml.YAMLError as e:
            self.logger.error(f"解析 YAML 文件失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"解析配置文件时发生意外错误: {e}")
            return []

        return devices