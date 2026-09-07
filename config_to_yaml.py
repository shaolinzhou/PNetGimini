import os
import sys
import yaml
import logging
import re
from pathlib import Path
from datetime import datetime

# 设置基础日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_filename_info(filename):
    """
    使用正则表达式解析文件名: IP_Port_snapshot_Time.conf
    例如: 192.168.239.134_30003_snapshot_20251001220536.conf
    """
    # 匹配格式: (IP)_(Port)_snapshot_(Time).conf
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
    """解析配置文件并提取干净的命令列表"""
    commands_list = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            stripped_line = line.strip()
            # 过滤掉注释和系统生成的非命令行
            if stripped_line and not stripped_line.startswith('!') and \
               not stripped_line.lower().startswith('building') and \
               not stripped_line.lower().startswith('current'):
                commands_list.append(stripped_line)
    except Exception as e:
        logging.error(f"解析文件 {file_path} 出错: {e}")
    return commands_list

def main():
    logging.info("启动配置转换工具：基于最新时间戳过滤。")
    BASE_DIR = Path(__file__).resolve().parent
    CONFIGS_DIR = BASE_DIR / "configs"
    
    # 1. 查找所有 .conf 文件
    all_conf_files = list(CONFIGS_DIR.glob('*.conf'))
    if not all_conf_files:
        logging.warning("未找到任何 .conf 文件。")
        return

    # 2. 筛选每个设备最新的文件
    # 字典结构: {(ip, port): (timestamp, file_path)}
    latest_configs = {}

    for file_path in all_conf_files:
        info = parse_filename_info(file_path.name)
        if info:
            key = (info['ip'], info['port'])
            timestamp = info['timestamp']
            
            # 如果是第一次发现该设备，或者当前文件的时间戳比已记录的更晚
            if key not in latest_configs or timestamp > latest_configs[key][0]:
                latest_configs[key] = (timestamp, file_path)
        else:
            logging.warning(f"文件名格式不符合预期，跳过: {file_path.name}")

    if not latest_configs:
        logging.error("没有解析到有效的设备信息。")
        return

    all_devices = []
    for (ip, port), (ts, path) in latest_configs.items():
        logging.info(f"处理最新备份: {path.name} (时间戳: {ts})")
        config_commands = parse_config_file(path)
        
        device_entry = {
            'ip': ip,
            'port': port,
            'username': 'admin',   # 默认值，可在生成的yaml中修改
            'password': 'admin',   # 默认值
            'device_type': 'cisco_ios_telnet',
            'commands': {
                'config': config_commands,
                'show': []
            }
        }
        all_devices.append(device_entry)

    # 3. 写入 YAML 文件
    if all_devices:
        final_data = {'devices': all_devices}
        
        # 定义固定输出路径
        BASE_DIR = Path(__file__).resolve().parent
        CONFIGS_DIR = BASE_DIR / "configs"
        if not CONFIGS_DIR.exists():
            CONFIGS_DIR.mkdir(parents=True)
            
        output_path_fixed = CONFIGS_DIR / "latest_recovery.yaml"
        
        # 写入文件
        class MyDumper(yaml.Dumper):
            def increase_indent(self, flow=False, indentless=False):
                return super(MyDumper, self).increase_indent(flow, False)

        with open(output_path_fixed, 'w', encoding='utf-8') as f:
            yaml.dump(final_data, f, Dumper=MyDumper, sort_keys=False, indent=2)
            
        logging.info(f"回滚专用文件已同步更新: {output_path_fixed}")
    else:
        logging.warning("没有可转换的设备数据，未生成 YAML。")

if __name__ == "__main__":
    main()