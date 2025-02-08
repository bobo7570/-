"""自定义异常类模块。

此模块定义了应用程序中使用的所有自定义异常类。
"""

class AppAutoToolError(Exception):
    """应用程序基础异常类。"""
    pass

class DeviceError(AppAutoToolError):
    """设备相关异常。"""
    pass

class AppiumError(AppAutoToolError):
    """Appium服务相关异常。"""
    pass

class RecordError(AppAutoToolError):
    """录制相关异常。"""
    pass

class ConfigError(AppAutoToolError):
    """配置相关异常。"""
    pass

class TestCaseError(AppAutoToolError):
    """测试用例相关异常。"""
    pass

class AssertionError(AppAutoToolError):
    """断言相关异常。"""
    pass

class ReportError(AppAutoToolError):
    """报告相关异常。"""
    pass

class ConnectionError(AppAutoToolError):
    """连接相关异常。"""
    def __init__(self, message: str, device_id: str = None, port: int = None):
        self.device_id = device_id
        self.port = port
        super().__init__(message)

class TimeoutError(AppAutoToolError):
    """超时相关异常。"""
    def __init__(self, message: str, timeout: int = None):
        self.timeout = timeout
        super().__init__(message)

class ValidationError(AppAutoToolError):
    """验证相关异常。"""
    def __init__(self, message: str, field: str = None, value: str = None):
        self.field = field
        self.value = value
        super().__init__(message)

class ResourceNotFoundError(AppAutoToolError):
    """资源未找到异常。"""
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message)

class PermissionError(AppAutoToolError):
    """权限相关异常。"""
    def __init__(self, message: str, permission: str = None):
        self.permission = permission
        super().__init__(message)

class EnvironmentError(AppAutoToolError):
    """环境相关异常。"""
    def __init__(self, message: str, component: str = None):
        self.component = component
        super().__init__(message) 