"""常量定义模块。

此模块定义了应用程序中使用的所有常量。
"""

import os
from enum import Enum, auto

# 应用程序信息
APP_NAME = "App自动化工具"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Your Name"
APP_EMAIL = "your.email@example.com"

# 文件路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
RESOURCES_DIR = os.path.join(ROOT_DIR, "resources")
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
RECORDINGS_DIR = os.path.join(ROOT_DIR, "recordings")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
TEST_CASES_DIR = os.path.join(ROOT_DIR, "test_cases")

# 配置文件
DEFAULT_CONFIG_FILE = os.path.join(CONFIG_DIR, "default_config.json")
LOGGING_CONFIG_FILE = os.path.join(CONFIG_DIR, "logging_config.json")
USER_CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

# 样式文件
STYLE_FILE = os.path.join(RESOURCES_DIR, "style.qss")

# Appium相关
DEFAULT_APPIUM_HOST = "127.0.0.1"
DEFAULT_APPIUM_PORT = 4723
APPIUM_PORT_RANGE = (4723, 4823)

# 设备相关
class Platform(Enum):
    """平台类型枚举。"""
    ANDROID = auto()
    IOS = auto()

class ActionType(Enum):
    """动作类型枚举。"""
    CLICK = auto()
    INPUT = auto()
    SWIPE = auto()
    STATE_CHANGE = auto()
    WAIT = auto()
    BACK = auto()
    HOME = auto()
    APP_SWITCH = auto()
    CUSTOM = auto()

class DeviceStatus(Enum):
    """设备状态枚举。"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()

# 录制相关
class RecordMode(Enum):
    """录制模式枚举。"""
    FULL = "完整模式"
    SIMPLE = "简单模式"

DEFAULT_RECORD_INTERVAL = 2  # 秒
MIN_RECORD_INTERVAL = 1
MAX_RECORD_INTERVAL = 60

# 界面相关
class Theme(Enum):
    """主题枚举。"""
    LIGHT = "浅色"
    DARK = "深色"
    SYSTEM = "跟随系统"

# 日志相关
class LogLevel(Enum):
    """日志级别枚举。"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

# 超时设置
DEFAULT_WAIT_TIMEOUT = 20  # 秒
DEFAULT_DEVICE_TIMEOUT = 30  # 秒
DEFAULT_COMMAND_TIMEOUT = 60  # 秒
DEFAULT_CONNECTION_TIMEOUT = 10  # 秒

# Android相关
ANDROID_DEFAULT_CAPABILITIES = {
    "platformName": "Android",
    "automationName": "UiAutomator2",
    "noReset": True,
    "newCommandTimeout": DEFAULT_COMMAND_TIMEOUT,
    "autoGrantPermissions": True,
    "skipServerInstallation": False,
    "skipDeviceInitialization": False
}

# iOS相关
IOS_DEFAULT_CAPABILITIES = {
    "platformName": "iOS",
    "automationName": "XCUITest",
    "noReset": True,
    "newCommandTimeout": DEFAULT_COMMAND_TIMEOUT,
    "autoAcceptAlerts": True,
    "skipServerInstallation": False
}

# 测试相关
class TestStatus(Enum):
    """测试状态枚举。"""
    PASS = auto()
    FAIL = auto()
    ERROR = auto()
    SKIP = auto()

# 断言相关
class AssertType(Enum):
    """断言类型枚举。"""
    EQUAL = auto()
    NOT_EQUAL = auto()
    CONTAINS = auto()
    NOT_CONTAINS = auto()
    EXISTS = auto()
    NOT_EXISTS = auto()
    ENABLED = auto()
    DISABLED = auto()
    VISIBLE = auto()
    INVISIBLE = auto()

# 报告相关
class ReportFormat(Enum):
    """报告格式枚举。"""
    HTML = auto()
    PDF = auto()
    XML = auto()
    JSON = auto() 