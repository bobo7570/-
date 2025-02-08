"""工具模块。

此模块包含应用程序使用的所有工具类和函数。
"""

from .constants import (
    APP_NAME, APP_VERSION, APP_AUTHOR, APP_EMAIL,
    ROOT_DIR, CONFIG_DIR, RESOURCES_DIR, LOGS_DIR,
    RECORDINGS_DIR, REPORTS_DIR, TEST_CASES_DIR,
    DEFAULT_CONFIG_FILE, LOGGING_CONFIG_FILE, USER_CONFIG_FILE,
    STYLE_FILE,
    DEFAULT_APPIUM_HOST, DEFAULT_APPIUM_PORT, APPIUM_PORT_RANGE,
    Platform, DeviceStatus, RecordMode, Theme, LogLevel,
    DEFAULT_RECORD_INTERVAL, MIN_RECORD_INTERVAL, MAX_RECORD_INTERVAL,
    DEFAULT_DEVICE_TIMEOUT, DEFAULT_COMMAND_TIMEOUT, DEFAULT_CONNECTION_TIMEOUT,
    ANDROID_DEFAULT_CAPABILITIES, IOS_DEFAULT_CAPABILITIES,
    TestStatus, AssertType, ReportFormat
)

from .errors import (
    AppAutoToolError, DeviceError, AppiumError, RecordError,
    ConfigError, TestCaseError, AssertionError, ReportError,
    ConnectionError, TimeoutError, ValidationError,
    ResourceNotFoundError, PermissionError, EnvironmentError
)

from .helpers import (
    get_free_port,
    kill_process_by_port,
    is_port_in_use,
    ensure_dir_exists,
    load_json_file,
    save_json_file,
    load_yaml_file,
    save_yaml_file,
    get_timestamp,
    get_datetime_str,
    get_platform_name,
    get_device_info,
    validate_config,
    setup_logging,
    create_directory_structure
)

__all__ = [
    # 常量
    'APP_NAME', 'APP_VERSION', 'APP_AUTHOR', 'APP_EMAIL',
    'ROOT_DIR', 'CONFIG_DIR', 'RESOURCES_DIR', 'LOGS_DIR',
    'RECORDINGS_DIR', 'REPORTS_DIR', 'TEST_CASES_DIR',
    'DEFAULT_CONFIG_FILE', 'LOGGING_CONFIG_FILE', 'USER_CONFIG_FILE',
    'STYLE_FILE',
    'DEFAULT_APPIUM_HOST', 'DEFAULT_APPIUM_PORT', 'APPIUM_PORT_RANGE',
    'Platform', 'DeviceStatus', 'RecordMode', 'Theme', 'LogLevel',
    'DEFAULT_RECORD_INTERVAL', 'MIN_RECORD_INTERVAL', 'MAX_RECORD_INTERVAL',
    'DEFAULT_DEVICE_TIMEOUT', 'DEFAULT_COMMAND_TIMEOUT', 'DEFAULT_CONNECTION_TIMEOUT',
    'ANDROID_DEFAULT_CAPABILITIES', 'IOS_DEFAULT_CAPABILITIES',
    'TestStatus', 'AssertType', 'ReportFormat',
    
    # 异常类
    'AppAutoToolError', 'DeviceError', 'AppiumError', 'RecordError',
    'ConfigError', 'TestCaseError', 'AssertionError', 'ReportError',
    'ConnectionError', 'TimeoutError', 'ValidationError',
    'ResourceNotFoundError', 'PermissionError', 'EnvironmentError',
    
    # 辅助函数
    'get_free_port',
    'kill_process_by_port',
    'is_port_in_use',
    'ensure_dir_exists',
    'load_json_file',
    'save_json_file',
    'load_yaml_file',
    'save_yaml_file',
    'get_timestamp',
    'get_datetime_str',
    'get_platform_name',
    'get_device_info',
    'validate_config',
    'setup_logging',
    'create_directory_structure'
] 