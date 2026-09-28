import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .masking import MaskingFilter

def setup_logger(log_dir: Path):
    """配置并初始化日志系统，自动集成敏感凭据脱敏过滤器"""
    log_file_path = log_dir / "automation.log"
    log_file_path.parent.mkdir(exist_ok=True)

    # 创建一个根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 避免重复添加处理器
    if not logger.handlers:
        masking_filter = MaskingFilter()

        # 创建文件处理器，支持日志文件滚动
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(masking_filter)
        logger.addHandler(file_handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(masking_filter)
        logger.addHandler(console_handler)