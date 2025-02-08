"""日志工具模块。

此模块提供统一的日志记录功能。
"""

import os
import sys
import logging
import logging.config
from typing import Optional, Union
from loguru import logger
from .constants import LOGS_DIR, LOGGING_CONFIG_FILE
from .errors import ConfigError

def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    error_file: Optional[str] = None,
    config_file: Optional[str] = None
) -> None:
    """设置日志记录器。

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
        error_file: 错误日志文件路径
        config_file: 日志配置文件路径
    """
    try:
        # 确保日志目录存在
        os.makedirs(LOGS_DIR, exist_ok=True)

        # 设置默认日志文件
        if log_file is None:
            log_file = os.path.join(LOGS_DIR, "app.log")
        if error_file is None:
            error_file = os.path.join(LOGS_DIR, "error.log")
        if config_file is None:
            config_file = LOGGING_CONFIG_FILE

        # 加载日志配置
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                import json
                config = json.load(f)
                
                # 更新配置
                config["handlers"]["file"]["filename"] = log_file
                config["handlers"]["error_file"]["filename"] = error_file
                for handler in config["handlers"].values():
                    if "level" in handler:
                        handler["level"] = log_level

                # 应用配置
                logging.config.dictConfig(config)
        else:
            # 使用默认配置
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        # 配置loguru
        logger.remove()  # 移除默认处理器

        # 添加控制台处理器
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                   "<level>{message}</level>",
            level=log_level,
            colorize=True
        )

        # 添加文件处理器
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                   "{name}:{function}:{line} | {message}",
            level=log_level,
            rotation="1 day",
            retention="30 days",
            encoding="utf-8"
        )

        # 添加错误文件处理器
        logger.add(
            error_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                   "{name}:{function}:{line} | {message}",
            level="ERROR",
            rotation="1 day",
            retention="30 days",
            encoding="utf-8"
        )

        logger.info("日志系统初始化完成")

    except Exception as e:
        raise ConfigError(f"设置日志记录器失败: {e}")

def get_logger(name: Optional[str] = None) -> Union[logging.Logger, logger]:
    """获取日志记录器。

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器
    """
    if name:
        return logging.getLogger(name)
    return logger

# 导出日志级别常量
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# 导出日志函数
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception 