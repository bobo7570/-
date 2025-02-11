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

def setup_logger():
    """设置日志配置"""
    # 移除默认的处理器
    logger.remove()
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # 添加文件处理器
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger.add(
        os.path.join(log_dir, "app_{time}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # 设置异常处理器
    def handle_exception(exc_type, exc_value, exc_traceback):
        """处理未捕获的异常"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Uncaught exception:")
    
    sys.excepthook = handle_exception
    
    logger.info("日志系统初始化完成")

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