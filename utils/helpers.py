"""辅助函数模块。

此模块包含应用程序使用的所有辅助函数。
"""

import os
import sys
import json
import yaml
import subprocess
import platform
import socket
import psutil
import logging
import datetime
import time
from typing import Dict, List, Optional, Union
from loguru import logger
from shutil import which

from .constants import (
    ROOT_DIR, CONFIG_DIR, LOGS_DIR, RECORDINGS_DIR,
    REPORTS_DIR, TEST_CASES_DIR, DEFAULT_CONFIG_FILE,
    LOGGING_CONFIG_FILE, APPIUM_PORT_RANGE
)
from .errors import (
    ConfigError, ResourceNotFoundError, EnvironmentError,
    ValidationError
)

def check_environment(config: dict = None) -> list:
    """检查环境配置
    
    Args:
        config: 配置字典
        
    Returns:
        缺失组件的列表
    """
    import subprocess
    import platform
    import os
    
    missing_components = []
    
    try:
        # 检查Node.js
        try:
            # 使用 where/which 命令找到可执行文件的完整路径
            node_path = which('node')
            if node_path:
                subprocess.check_output([node_path, '--version'], shell=True)
            else:
                missing_components.append('Node.js')
        except Exception:
            missing_components.append('Node.js')
        
        # 检查npm
        try:
            npm_path = which('npm')
            if npm_path:
                subprocess.check_output([npm_path, '--version'], shell=True)
            else:
                missing_components.append('npm')
        except Exception:
            missing_components.append('npm')
        
        # 检查Appium
        try:
            # 首先检查全局安装的appium
            appium_path = which('appium')
            if appium_path:
                subprocess.check_output([appium_path, '--version'], shell=True)
            else:
                # 如果全局未找到，检查本地安装的appium
                npm_path = which('npm')
                if npm_path:
                    try:
                        subprocess.check_output(['npm', 'list', '-g', 'appium'], shell=True)
                    except subprocess.CalledProcessError:
                        missing_components.append('Appium')
                else:
                    missing_components.append('Appium')
        except Exception:
            missing_components.append('Appium')
        
        # 检查adb
        try:
            adb_path = which('adb')
            if adb_path:
                subprocess.check_output([adb_path, 'version'], shell=True)
            else:
                missing_components.append('adb')
        except Exception:
            missing_components.append('adb')
        
        # 检查Android环境变量
        android_home = os.environ.get('ANDROID_HOME')
        if not android_home or not os.path.exists(android_home):
            # 尝试检查ANDROID_SDK_ROOT
            android_sdk_root = os.environ.get('ANDROID_SDK_ROOT')
            if not android_sdk_root or not os.path.exists(android_sdk_root):
                missing_components.append('ANDROID_HOME')
        
        # 检查Java环境变量
        java_home = os.environ.get('JAVA_HOME')
        if not java_home or not os.path.exists(java_home):
            # 尝试直接检查java命令
            if not which('java'):
                missing_components.append('JAVA_HOME')
        
        # 在macOS上检查Xcode
        if platform.system() == 'Darwin':
            try:
                subprocess.check_output(['xcode-select', '-p'])
            except Exception:
                missing_components.append('Xcode')
        
        return missing_components
        
    except Exception as e:
        logger.error(f"环境检查失败: {e}")
        return ['检查失败']

def load_config(config_path: str) -> Dict:
    """
    加载配置文件
    :param config_path: 配置文件路径
    :return: 配置信息字典
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                return yaml.safe_load(f)
            elif config_path.endswith('.json'):
                return json.load(f)
            else:
                raise ValueError("不支持的配置文件格式")
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)

def save_json(data: Union[Dict, List], file_path: str, ensure_dir: bool = True) -> bool:
    """
    保存数据到JSON文件
    :param data: 要保存的数据
    :param file_path: 文件路径
    :param ensure_dir: 是否确保目录存在
    :return: 是否保存成功
    """
    try:
        if ensure_dir:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    
    except Exception as e:
        logger.error(f"保存JSON文件失败: {e}")
        return False

def load_json(file_path: str) -> Optional[Union[Dict, List]]:
    """
    从JSON文件加载数据
    :param file_path: 文件路径
    :return: 加载的数据，失败返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件失败: {e}")
        return None

def check_port_in_use(port: int) -> bool:
    """
    检查端口是否被占用
    :param port: 端口号
    :return: 是否被占用
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_by_port(port: int, max_retries: int = 3) -> bool:
    """
    通过端口号杀死进程
    :param port: 端口号
    :param max_retries: 最大重试次数
    :return: 是否成功
    """
    for attempt in range(max_retries):
        try:
            if platform.system() == 'Windows':
                # Windows系统使用netstat查找进程
                cmd = f'netstat -ano | findstr :{port}'
                result = subprocess.check_output(cmd, shell=True).decode()
                if result:
                    pid = result.strip().split()[-1]
                    try:
                        # 尝试终止进程
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                        logger.info(f"已终止使用端口 {port} 的进程 (PID: {pid})")
                        return True
                    except subprocess.CalledProcessError:
                        logger.warning(f"无法终止进程 {pid}")
            else:
                # Unix系统使用lsof查找进程
                cmd = f'lsof -i :{port} -t'
                try:
                    pid = subprocess.check_output(cmd, shell=True).decode().strip()
                    if pid:
                        # 尝试终止进程
                        subprocess.run(f'kill -9 {pid}', shell=True, check=True)
                        logger.info(f"已终止使用端口 {port} 的进程 (PID: {pid})")
                        return True
                except subprocess.CalledProcessError:
                    pass
            
            # 检查端口是否已释放
            if not check_port_in_use(port):
                return True
            
            if attempt < max_retries - 1:
                time.sleep(1)
        except Exception as e:
            logger.error(f"尝试释放端口 {port} 失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    
    logger.error(f"无法释放端口 {port}")
    return False

def get_free_port(start_port: int = 4723, end_port: int = 4823, exclude_ports: List[int] = None) -> Optional[int]:
    """
    获取空闲端口
    :param start_port: 起始端口号
    :param end_port: 结束端口号
    :param exclude_ports: 要排除的端口列表
    :return: 空闲端口号或None
    """
    if exclude_ports is None:
        exclude_ports = []
    
    for port in range(start_port, end_port + 1):
        if port in exclude_ports:
            continue
        
        try:
            # 先检查端口是否被占用
            if check_port_in_use(port):
                continue
            
            # 尝试绑定端口
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                logger.debug(f"找到空闲端口: {port}")
                return port
        except OSError:
            continue
    
    logger.error("未找到空闲端口")
    return None

def format_time(seconds: float) -> str:
    """
    格式化时间
    :param seconds: 秒数
    :return: 格式化后的时间字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"

def get_platform_name() -> str:
    """获取平台名称。

    Returns:
        平台名称
    """
    system = platform.system().lower()
    if system == 'darwin':
        return 'mac'
    elif system == 'windows':
        return 'win'
    elif system == 'linux':
        return 'linux'
    else:
        return system

def run_command(command: str, shell: bool = True, timeout: int = None) -> tuple:
    """
    执行命令行命令
    :param command: 要执行的命令
    :param shell: 是否使用shell执行
    :param timeout: 超时时间（秒）
    :return: (返回码, 输出, 错误)
    """
    try:
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
        
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr
    
    except subprocess.TimeoutExpired:
        process.kill()
        logger.error(f"命令执行超时: {command}")
        return -1, '', 'Timeout'
    except Exception as e:
        logger.error(f"执行命令失败: {e}")
        return -1, '', str(e)

def ensure_dir(directory: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    :param directory: 目录路径
    :return: 是否成功
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败: {e}")
        return False

def clean_directory(directory: str, file_pattern: str = None) -> bool:
    """
    清理目录中的文件
    :param directory: 目录路径
    :param file_pattern: 文件匹配模式（可选）
    :return: 是否成功
    """
    try:
        if not os.path.exists(directory):
            return True
        
        import glob
        if file_pattern:
            files = glob.glob(os.path.join(directory, file_pattern))
        else:
            files = [os.path.join(directory, f) for f in os.listdir(directory)]
        
        for file_path in files:
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                logger.warning(f"删除文件失败 {file_path}: {e}")
        
        return True
    
    except Exception as e:
        logger.error(f"清理目录失败: {e}")
        return False

def get_timestamp() -> int:
    """获取当前时间戳。

    Returns:
        当前时间戳（毫秒）
    """
    return int(datetime.datetime.now().timestamp() * 1000)

def get_datetime_str(timestamp: Optional[int] = None, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取格式化的日期时间字符串。

    Args:
        timestamp: 时间戳（毫秒），如果为None则使用当前时间
        format: 日期时间格式

    Returns:
        格式化的日期时间字符串
    """
    if timestamp is None:
        dt = datetime.datetime.now()
    else:
        dt = datetime.datetime.fromtimestamp(timestamp / 1000)
    return dt.strftime(format)

def validate_json_schema(data: Dict, schema: Dict) -> bool:
    """
    验证JSON数据是否符合schema
    :param data: JSON数据
    :param schema: JSON schema
    :return: 是否符合schema
    """
    try:
        from jsonschema import validate
        validate(instance=data, schema=schema)
        return True
    except Exception as e:
        logger.error(f"JSON数据验证失败: {e}")
        return False

def is_port_in_use(port: int) -> bool:
    """
    检查端口是否被占用
    :param port: 端口号
    :return: 是否被占用
    """
    try:
        # 尝试连接端口
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0
    except:
        return True

def ensure_dir_exists(path: str) -> None:
    """确保目录存在，如果不存在则创建。

    Args:
        path: 目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)

def load_json_file(file_path: str) -> Dict:
    """加载JSON文件。

    Args:
        file_path: 文件路径

    Returns:
        JSON数据

    Raises:
        ResourceNotFoundError: 文件不存在
        ConfigError: 文件格式错误
    """
    try:
        if not os.path.exists(file_path):
            raise ResourceNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON格式错误: {e}")

def save_json_file(data: Dict, file_path: str) -> None:
    """保存JSON文件。

    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    ensure_dir_exists(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_yaml_file(file_path: str) -> Dict:
    """加载YAML文件。

    Args:
        file_path: 文件路径

    Returns:
        YAML数据

    Raises:
        ResourceNotFoundError: 文件不存在
        ConfigError: 文件格式错误
    """
    try:
        if not os.path.exists(file_path):
            raise ResourceNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"YAML格式错误: {e}")

def save_yaml_file(data: Dict, file_path: str) -> None:
    """保存YAML文件。

    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    ensure_dir_exists(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

def validate_config(config: Dict) -> None:
    """验证配置。

    Args:
        config: 配置数据

    Raises:
        ValidationError: 配置验证失败
    """
    required_fields = {
        'work_dir': str,
        'log_level': str,
        'device': {
            'android_sdk': str,
            'ios_cert': str,
            'timeout': int
        },
        'record': {
            'interval': int,
            'mode': str,
            'save_dir': str
        },
        'advanced': {
            'appium': {
                'host': str,
                'port': int
            }
        }
    }

    def validate_dict(data: Dict, schema: Dict, path: str = '') -> None:
        for key, value_type in schema.items():
            if key not in data:
                raise ValidationError(f"缺少必需的配置项: {path + key}")
            if isinstance(value_type, dict):
                if not isinstance(data[key], dict):
                    raise ValidationError(f"配置项类型错误: {path + key}")
                validate_dict(data[key], value_type, f"{path}{key}.")
            elif not isinstance(data[key], value_type):
                raise ValidationError(
                    f"配置项类型错误: {path + key}",
                    field=path + key,
                    value=str(data[key])
                )

    validate_dict(config, required_fields)

def setup_logging(config: Dict) -> None:
    """设置日志。

    Args:
        config: 配置数据
    """
    # 确保日志目录存在
    ensure_dir_exists(LOGS_DIR)

    # 加载日志配置
    log_config = load_json_file(LOGGING_CONFIG_FILE)

    # 设置日志级别
    log_level = config.get('log_level', 'INFO')
    log_config['handlers']['console']['level'] = log_level
    log_config['loggers']['']['level'] = log_level

    # 设置日志文件路径
    log_config['handlers']['file']['filename'] = os.path.join(LOGS_DIR, 'app.log')
    log_config['handlers']['error_file']['filename'] = os.path.join(LOGS_DIR, 'error.log')

    # 配置logging
    logging.config.dictConfig(log_config)

    # 配置loguru
    logger.remove()  # 移除默认处理器
    logger.add(
        os.path.join(LOGS_DIR, 'app.log'),
        rotation="1 day",
        retention="30 days",
        level=log_level,
        encoding='utf-8'
    )
    logger.add(
        os.path.join(LOGS_DIR, 'error.log'),
        rotation="1 day",
        retention="30 days",
        level='ERROR',
        encoding='utf-8'
    )

def create_directory_structure() -> None:
    """创建目录结构。"""
    dirs = [
        CONFIG_DIR,
        LOGS_DIR,
        RECORDINGS_DIR,
        REPORTS_DIR,
        TEST_CASES_DIR
    ]
    for dir_path in dirs:
        ensure_dir_exists(dir_path)

def get_device_info(device_id: str, platform: str) -> Dict:
    """获取设备信息。

    Args:
        device_id: 设备ID
        platform: 平台类型（android/ios）

    Returns:
        设备信息

    Raises:
        DeviceError: 获取设备信息失败
    """
    try:
        if platform == 'android':
            # 使用adb命令获取Android设备信息
            cmd = f'adb -s {device_id} shell getprop'
            output = subprocess.check_output(cmd, shell=True).decode()
            props = {}
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip('[] ')
                    value = value.strip('[] ')
                    props[key] = value
            return {
                'id': device_id,
                'platform': 'android',
                'model': props.get('ro.product.model', 'Unknown'),
                'brand': props.get('ro.product.brand', 'Unknown'),
                'version': props.get('ro.build.version.release', 'Unknown'),
                'sdk': props.get('ro.build.version.sdk', 'Unknown')
            }
        elif platform == 'ios':
            # 使用ideviceinfo命令获取iOS设备信息
            if get_platform_name() == 'mac':
                cmd = f'ideviceinfo -u {device_id}'
                output = subprocess.check_output(cmd, shell=True).decode()
                props = {}
                for line in output.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        props[key.strip()] = value.strip()
                return {
                    'id': device_id,
                    'platform': 'ios',
                    'model': props.get('ProductType', 'Unknown'),
                    'name': props.get('DeviceName', 'Unknown'),
                    'version': props.get('ProductVersion', 'Unknown')
                }
            else:
                # Windows下使用tidevice
                cmd = f'tidevice -u {device_id} info'
                output = subprocess.check_output(cmd, shell=True).decode()
                props = {}
                for line in output.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        props[key.strip()] = value.strip()
                return {
                    'id': device_id,
                    'platform': 'ios',
                    'model': props.get('ProductType', 'Unknown'),
                    'name': props.get('DeviceName', 'Unknown'),
                    'version': props.get('ProductVersion', 'Unknown')
                }
        else:
            raise ValueError(f"不支持的平台类型: {platform}")
    except Exception as e:
        raise EnvironmentError(f"获取设备信息失败: {e}")

def check_appium_service(host: str, port: int, timeout: int = 5) -> bool:
    """
    检查Appium服务是否正常运行
    :param host: 主机地址
    :param port: 端口号
    :param timeout: 超时时间（秒）
    :return: 服务是否正常
    """
    import requests
    try:
        response = requests.get(f"http://{host}:{port}/status", timeout=timeout)
        return response.status_code == 200
    except:
        return False

def clean_appium_processes():
    """
    清理所有Appium相关进程
    """
    try:
        if platform.system() == 'Windows':
            # 在Windows上查找并终止node.exe进程
            cmd = 'wmic process where "name=\'node.exe\'" get commandline,processid'
            try:
                output = subprocess.check_output(cmd, shell=True).decode()
                for line in output.splitlines():
                    if 'appium' in line.lower():
                        try:
                            pid = line.strip().split()[-1]
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                            logger.info(f"已终止Appium进程 (PID: {pid})")
                        except:
                            continue
            except:
                # 如果wmic命令失败，尝试直接终止所有node.exe进程
                subprocess.run('taskkill /F /IM node.exe', shell=True, capture_output=True)
        else:
            # 在Unix系统上使用pkill
            subprocess.run('pkill -f appium', shell=True, capture_output=True)
        
        logger.info("已清理所有Appium进程")
        return True
    except Exception as e:
        logger.error(f"清理Appium进程失败: {e}")
        return False

def wait_for_port_release(port: int, timeout: int = 30) -> bool:
    """
    等待端口释放
    :param port: 端口号
    :param timeout: 超时时间（秒）
    :return: 端口是否已释放
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not check_port_in_use(port):
            return True
        time.sleep(1)
    return False

def format_size(size_in_bytes: int) -> str:
    """格式化文件大小
    
    Args:
        size_in_bytes: 字节大小
        
    Returns:
        格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.1f}{unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.1f}PB" 