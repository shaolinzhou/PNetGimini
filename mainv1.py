import sys
import os
import json
import logging
import datetime
from pathlib import Path
from src.core.config_parser import ConfigParser
from core.device_managerv1 import DeviceManager
from src.core.result_handler import ResultHandler
from src.utils.logger import setup_logger

# 获取项目根目录，无论从何处调用脚本
# Path(__file__).resolve() 获取当前文件（main.py）的绝对路径
# .parent 获取该文件所在的目录（PnetGimini）
BASE_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = BASE_DIR / "configs"
LOGS_DIR = BASE_DIR / "logs"
OUTPUTS_DIR = BASE_DIR / "outputs"

def main():
    """
    主程序入口
    """
    # 确保目录存在
    LOGS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)

    # 初始化日志
    setup_logger(LOGS_DIR) # 注意：这里也需要传递日志目录
    logging.info("网络自动化部署系统启动...")

    # 获取配置文件路径
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1])
    else:
        logging.info("未指定配置文件，使用默认文件 'configs/devices.yaml'")
        config_path = CONFIGS_DIR / "devices.yaml"

    if not config_path.exists():
        logging.error(f"配置文件 '{config_path}' 不存在。")
        sys.exit(1)
        
    try:
        # 1. 解析配置文件
        logging.info(f"正在解析配置文件: {config_path}")
        parser = ConfigParser(config_path)
        devices_config = parser.parse()
        logging.info(f"配置文件解析完成，共发现 {len(devices_config)} 个设备。")

        # 2. 自动化部署
        results = []
        for device_info in devices_config:
            device_manager = DeviceManager(device_info)
            device_results = device_manager.deploy_commands()
            results.append(device_results)

        # 3. 生成报告
        handler = ResultHandler(OUTPUTS_DIR)
        handler.generate_summary_report(results)
        handler.generate_consolidated_txt_report(results)    
        logging.info("All device configuration tasks completed.")

    except Exception as e:
        logging.critical(f"程序运行出现致命错误: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()