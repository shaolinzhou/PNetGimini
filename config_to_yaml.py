import os
import sys
import yaml
import logging
import re
from pathlib import Path
from datetime import datetime

from src.core.adapters.cisco import CiscoAdapter
from src.core.adapters.huawei import HuaweiAdapter

# 设置基础日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_filename_info(filename):
    """
    使用正则表达式解析文件名: IP_Port_snapshot_Time.conf
    例如: 192.168.239.134_30003_snapshot_20251001220536.conf
    """
    pattern = r"(\d+\.\d+\.\d+\.\d+)_(\d+)_snapshot_(\d+)\.conf"
    match = re.match(pattern, filename)
    if match:
        return {
            "ip": match.group(1),
            "port": int(match.group(2)),
            "timestamp": match.group(3)
        }
    return None

def parse_config_file(file_path: Path) -> list:
    """解析配置文件并提取干净的命令列表，使用适配器剔除注释和系统标记行"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # 默认使用 Cisco 适配器清理逻辑
        adapter = CiscoAdapter()
        cleaned_lines = adapter.clean_raw_config(raw_content)
        return cleaned_lines
    except Exception as e:
        logging.error(f"解析文件 {file_path} 出错: {e}")
        return []

def main():
    logging.info("启动配置转换与逆向工程工具：基于快照最新时间戳生成 recovery 配置。")
    BASE_DIR = Path(__file__).resolve().parent
    CONFIGS_DIR = BASE_DIR / "configs"
    OUTPUTS_DIR = BASE_DIR / "outputs"
    
    # 1. 查找所有 .conf 文件 (优先支持 snapshots/ 子目录，同时向下兼容根目录)
    search_dirs = [
        CONFIGS_DIR / "snapshots",
        CONFIGS_DIR,
        OUTPUTS_DIR / "snapshots",
        OUTPUTS_DIR
    ]
    
    all_conf_files = []
    for d in search_dirs:
        if d.exists():
            all_conf_files.extend(list(d.glob('*.conf')))

    # 去重
    all_conf_files = list(set(all_conf_files))

    if not all_conf_files:
        logging.warning("未找到任何 .conf 快照文件。")
        return

    # 2. 筛选每个设备最新的快照
    # 字典结构: {(ip, port): (timestamp, file_path)}
    latest_configs = {}

    for file_path in all_conf_files:
        info = parse_filename_info(file_path.name)
        if info:
            key = (info['ip'], info['port'])
            timestamp = info['timestamp']
            
            if key not in latest_configs or timestamp > latest_configs[key][0]:
                latest_configs[key] = (timestamp, file_path)
        else:
            logging.debug(f"File name does not match snapshot format, skipping: {file_path.name}")

    if not latest_configs:
        logging.error("No valid snapshot files could be parsed.")
        return

    all_devices = []
    for (ip, port), (ts, path) in sorted(latest_configs.items()):
        logging.info(f"Processing latest snapshot: {path.name} (timestamp: {ts})")
        config_commands = parse_config_file(path)
        
        device_entry = {
            'ip': ip,
            'port': port,
            'username': 'admin',
            'password': 'admin',
            'device_type': 'cisco_ios_telnet',
            'commands': {
                'config': config_commands,
                'show': []
            }
        }
        all_devices.append(device_entry)

    # 3. Write YAML recovery file
    if all_devices:
        final_data = {'devices': all_devices}
        output_path_fixed = CONFIGS_DIR / "latest_recovery.yaml"
        
        class MyDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(MyDumper, self).increase_indent(flow, False)

        with open(output_path_fixed, 'w', encoding='utf-8') as f:
            yaml.dump(final_data, f, Dumper=MyDumper, sort_keys=False, indent=2)
            
        logging.info(f"Disaster recovery template successfully updated: {output_path_fixed}")
    else:
        logging.warning("No convertible device data available; YAML file was not generated.")

if __name__ == "__main__":
    main()