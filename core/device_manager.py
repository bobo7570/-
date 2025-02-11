import os
import subprocess
import platform
from typing import List, Dict, Optional, Tuple
import adbutils
from tidevice import Device as TiDevice
from loguru import logger
import time
import requests
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from utils.helpers import get_free_port, is_port_in_use
from utils.errors import (
    DeviceError, AppiumError, ConnectionError,
    TimeoutError, ResourceNotFoundError
)
import aiohttp

class DeviceCache:
    """设备缓存管理类"""
    def __init__(self, timeout: float = 5.0):
        self._cache = {}
        self._timeout = timeout
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Dict]:
        with self._lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if time.time() - timestamp <= self._timeout:
                    return data
                del self._cache[key]
            return None
    
    def set(self, key: str, value: Dict) -> None:
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def clean_expired(self) -> None:
        current_time = time.time()
        with self._lock:
            expired_keys = [
                k for k, (_, t) in self._cache.items()
                if current_time - t > self._timeout
            ]
            for k in expired_keys:
                del self._cache[k]

class DeviceManager:
    def __init__(self, config: Dict):
        """初始化设备管理器"""
        self.config = config
        self.devices = {}  # 设备字典
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=3)
        self._refresh_thread = None
        self._stop_event = threading.Event()
        self._device_status_cache = {}
        self._last_refresh_time = 0
        self._refresh_interval = config.get('refresh_interval', 2.0)  # 刷新间隔
        self._cache_timeout = config.get('cache_timeout', 5.0)  # 缓存超时时间
        self._platform = "android"
        self._devices_cache = {}
        self._cache_time = 0
        self._cache_lock = threading.Lock()
        self._appium_servers = {}
        self._server_lock = threading.Lock()
        self.max_retries = config.get('max_retries', 3)
        self.retry_interval = config.get('retry_interval', 2)
        self.appium_start_timeout = config.get('appium_start_timeout', 30)
        
        # 初始化日志
        logger.info("设备管理器初始化完成")
    
    @property
    def platform(self) -> str:
        return self._platform
    
    def set_platform(self, platform_type: str) -> None:
        """设置平台类型"""
        if platform_type.lower() not in ("android", "ios"):
            raise ValueError("不支持的平台类型")
        logger.info(f"切换平台类型为: {platform_type}")
        self._platform = platform_type.lower()
        self.clear_cache()
    
    def clear_cache(self) -> None:
        """清除设备缓存"""
        with self._cache_lock:
            self._devices_cache.clear()
            self._cache_time = 0
    
    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """获取设备信息"""
        try:
            with self._lock:
                return self.devices.get(device_id, {}).copy()
        
        except Exception as e:
            logger.error(f"获取设备信息失败: {device_id}, 错误: {e}")
            return None
    
    def update_config(self, config: Dict) -> None:
        """更新配置
        
        Args:
            config: 新的配置字典
        """
        try:
            with self._lock:
                self.config.update(config)
                self._refresh_interval = config.get('refresh_interval', 2.0)
                self._cache_timeout = config.get('cache_timeout', 5.0)
                self.max_retries = config.get('max_retries', 3)
                self.retry_interval = config.get('retry_interval', 2)
                self.appium_start_timeout = config.get('appium_start_timeout', 30)
                logger.info("设备管理器配置已更新")
        
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            raise
    
    def get_devices(self) -> List[Dict]:
        """获取设备列表（带缓存）"""
        current_time = time.time()
        
        with self._cache_lock:
            # 检查缓存是否有效
            if (current_time - self._cache_time) < self._cache_timeout and self._devices_cache:
                return list(self._devices_cache.values())
        
        try:
            devices = self._get_devices_internal()
            
            # 更新缓存
            with self._cache_lock:
                self._devices_cache = {d['id']: d for d in devices}
                self._cache_time = current_time
            
            return devices
        
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            raise DeviceError(f"获取设备列表失败: {e}")
    
    def _get_devices_internal(self) -> List[Dict]:
        """内部方法：获取设备列表
        
        Returns:
            List[Dict]: 设备列表，每个设备包含详细信息
        """
        try:
            # 获取设备ID列表
            device_ids = self._get_device_ids()
            if not device_ids:
                return []
            
            # 获取每个设备的详细信息
            devices = []
            for device_id in device_ids:
                try:
                    device_info = (
                        self._get_android_device_info(device_id)
                        if self._platform == "android"
                        else self._get_ios_device_info(device_id)
                    )
                    if device_info:
                        devices.append(device_info)
                except Exception as e:
                    logger.error(f"获取设备 {device_id} 信息失败: {e}")
                    continue
            
            return devices
            
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            return []
    
    async def start_appium_server_async(self, host: str = '127.0.0.1', port: int = 4723) -> bool:
        """异步启动Appium服务器"""
        try:
            logger.info(f"正在启动Appium服务器: {host}:{port}")
            
            # 检查端口是否被占用
            if is_port_in_use(port):
                logger.warning(f"端口 {port} 已被占用")
                return False
            
            # 准备Appium命令
            base_path = os.path.expanduser("~/.appium")
            log_file = os.path.abspath(f"appium_{port}.log")
            
            appium_cmd = (
                f"appium "
                f"--address {host} "
                f"--port {port} "
                f"--base-path /wd/hub "
                f"--session-override "
                f"--log-timestamp "
                f"--local-timezone "
                f"--log {log_file} "
                f"--use-drivers uiautomator2,xcuitest"
            )
            
            logger.debug(f"Appium启动命令: {appium_cmd}")
            
            # 在新进程中启动Appium
            if platform.system() == 'Windows':
                process = await asyncio.create_subprocess_shell(
                    appium_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    appium_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
            
            # 等待服务器启动
            start_time = time.time()
            while time.time() - start_time < self.appium_start_timeout:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"http://{host}:{port}/wd/hub/status") as response:
                            if response.status == 200:
                                logger.info(f"Appium服务器启动成功: {host}:{port}")
                                with self._server_lock:
                                    self._appium_servers[port] = {
                                        'host': host,
                                        'port': port,
                                        'process': process,
                                        'start_time': time.time()
                                    }
                                return True
                except Exception:
                    await asyncio.sleep(1)
                    continue
            
            # 超时处理
            logger.error(f"Appium服务器启动超时: {host}:{port}")
            await self._kill_process(process)
            return False
            
        except Exception as e:
            logger.error(f"启动Appium服务器失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
            return False
    
    async def stop_appium_server_async(self, port: int) -> None:
        """异步停止Appium服务器"""
        try:
            logger.info(f"正在停止Appium服务器: 端口 {port}")
            
            with self._server_lock:
                server_info = self._appium_servers.get(port)
                if not server_info:
                    logger.warning(f"未找到端口 {port} 对应的Appium服务器")
                    return
                
                process = server_info['process']
                
                # 尝试优雅关闭
                try:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                        logger.info(f"Appium服务器已优雅关闭: 端口 {port}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Appium服务器优雅关闭超时，强制终止: 端口 {port}")
                        await self._kill_process(process)
                except Exception as e:
                    logger.warning(f"关闭Appium服务器过程中出现错误: {e}")
                    await self._kill_process(process)
                
                # 清理服务器记录
                del self._appium_servers[port]
            
        except Exception as e:
            logger.error(f"停止Appium服务器失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
    
    async def _kill_process(self, process) -> None:
        """强制终止进程"""
        try:
            process.kill()
            await process.wait()
        except Exception as e:
            logger.error(f"强制终止进程失败: {e}")
    
    def get_appium_servers(self) -> List[Dict]:
        """获取所有运行中的Appium服务器信息"""
        with self._server_lock:
            return [
                {
                    'host': info['host'],
                    'port': info['port'],
                    'uptime': time.time() - info['start_time']
                }
                for info in self._appium_servers.values()
            ]
    
    def check_environment(self) -> Dict[str, bool]:
        """检查环境配置"""
        env_status = {
            'node': False,
            'npm': False,
            'appium': False,
            'adb': False,
            'xcode': False,
            'android_home': False,
            'java_home': False
        }
        
        try:
            # 检查Node.js
            try:
                subprocess.check_output(['node', '--version'])
                env_status['node'] = True
            except Exception as e:
                logger.warning(f"Node.js未安装或配置错误: {e}")
            
            # 检查npm
            try:
                subprocess.check_output(['npm', '--version'])
                env_status['npm'] = True
            except Exception as e:
                logger.warning(f"npm未安装或配置错误: {e}")
            
            # 检查Appium
            try:
                subprocess.check_output(['appium', '--version'])
                env_status['appium'] = True
            except Exception as e:
                logger.warning(f"Appium未安装或配置错误: {e}")
            
            # 检查adb
            try:
                subprocess.check_output(['adb', 'version'])
                env_status['adb'] = True
            except Exception as e:
                logger.warning(f"adb未安装或配置错误: {e}")
            
            # 检查Android环境变量
            android_home = os.environ.get('ANDROID_HOME')
            if android_home and os.path.exists(android_home):
                env_status['android_home'] = True
            else:
                logger.warning("ANDROID_HOME环境变量未设置或路径不存在")
            
            # 检查Java环境变量
            java_home = os.environ.get('JAVA_HOME')
            if java_home and os.path.exists(java_home):
                env_status['java_home'] = True
            else:
                logger.warning("JAVA_HOME环境变量未设置或路径不存在")
            
            # 在macOS上检查Xcode
            if platform.system() == 'Darwin':
                try:
                    subprocess.check_output(['xcode-select', '-p'])
                    env_status['xcode'] = True
                except Exception as e:
                    logger.warning(f"Xcode未安装或配置错误: {e}")
            
            return env_status
            
        except Exception as e:
            logger.error(f"检查环境配置失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
            return env_status
    
    def install_appium(self) -> bool:
        """
        安装Appium
        :return: 安装是否成功
        """
        try:
            logger.info("开始安装Appium...")
            subprocess.check_call(['npm', 'install', '-g', 'appium'])
            logger.info("Appium安装成功")
            return True
        except Exception as e:
            logger.error(f"Appium安装失败: {e}")
            return False
    
    def _retry_operation(self, operation, *args, **kwargs):
        """
        带重试机制的操作执行
        :param operation: 要执行的操作函数
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 操作结果
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                result = operation(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"操作失败，尝试重试 ({attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_interval)
        
        raise last_error

    def start_appium_server(self, host: str = '127.0.0.1', port: int = 4723) -> bool:
        """启动Appium服务"""
        return self._retry_operation(self._start_appium_server_internal, host, port)

    def _start_appium_server_internal(self, host: str, port: int) -> bool:
        """内部Appium服务启动实现"""
        try:
            # 检查端口占用
            if self._is_port_in_use(port):
                logger.warning(f"端口 {port} 已被占用")
                # 尝试关闭占用的进程
                from utils.helpers import kill_process_by_port
                if not kill_process_by_port(port):
                    logger.error(f"无法释放端口 {port}")
                    return False
            
            # 启动Appium服务
            cmd = f'appium -a {host} -p {port} --log appium_{port}.log --log-timestamp --relaxed-security'
            if platform.system() == 'Windows':
                process = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                process = subprocess.Popen(
                    cmd.split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            # 等待服务启动
            start_time = time.time()
            while time.time() - start_time < self.appium_start_timeout:
                try:
                    response = requests.get(f'http://{host}:{port}/status', timeout=2)
                    if response.status_code == 200:
                        # 保存进程和端口信息
                        self._appium_servers[port] = process
                        logger.info(f"Appium服务已启动: {host}:{port}")
                        return True
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                    time.sleep(1)
                    continue
            
            # 如果启动失败，清理进程
            process.terminate()
            logger.error(f"Appium服务启动超时: {host}:{port}")
            return False
        
        except Exception as e:
            logger.error(f"启动Appium服务失败: {str(e)}")
            return False
    
    def stop_appium_server(self, port: int = None):
        """
        停止Appium服务
        :param port: 指定要停止的端口，如果为None则停止所有服务
        """
        try:
            if port is not None:
                # 停止指定端口的服务
                if port in self._appium_servers:
                    process = self._appium_servers[port]
                    # 先尝试正常终止进程
                    process.terminate()
                    # 等待进程结束
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果进程没有及时结束，强制结束
                        process.kill()
                    
                    # 确保端口被释放
                    if self._is_port_in_use(port):
                        from utils.helpers import kill_process_by_port
                        kill_process_by_port(port)
                    
                    del self._appium_servers[port]
                    logger.info(f"Appium服务已停止: 端口 {port}")
            else:
                # 停止所有服务
                for port, process in list(self._appium_servers.items()):
                    try:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        
                        if self._is_port_in_use(port):
                            from utils.helpers import kill_process_by_port
                            kill_process_by_port(port)
                        
                        logger.info(f"Appium服务已停止: 端口 {port}")
                    except Exception as e:
                        logger.error(f"停止端口 {port} 的Appium服务失败: {e}")
                
                self._appium_servers.clear()
        
        except Exception as e:
            logger.error(f"停止Appium服务失败: {e}")
    
    def _is_port_in_use(self, port: int) -> bool:
        """
        检查端口是否被占用
        :param port: 端口号
        :return: 是否被占用
        """
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def _get_device_ids(self) -> List[str]:
        """获取设备ID列表"""
        try:
            if self._platform == "android":
                try:
                    # 使用adbutils获取Android设备列表
                    adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
                    logger.debug("成功创建ADB客户端")
                    
                    # 获取设备列表
                    devices = adb.device_list()
                    logger.debug(f"ADB设备列表: {devices}")
                    
                    # 获取设备ID列表
                    device_ids = [d.serial for d in devices]
                    logger.debug(f"设备ID列表: {device_ids}")
                    
                    if not device_ids:
                        logger.warning("没有检测到Android设备")
                        return []
                    
                    # 验证每个设备的状态
                    valid_devices = []
                    for device_id in device_ids:
                        try:
                            device = adb.device(device_id)
                            # 尝试执行一个简单的shell命令来验证设备是否可用
                            result = device.shell("echo test")
                            logger.debug(f"设备 {device_id} 测试结果: {result}")
                            
                            if result.strip() == "test":
                                valid_devices.append(device_id)
                                logger.debug(f"设备 {device_id} 验证通过")
                            else:
                                logger.warning(f"设备 {device_id} 响应异常: {result}")
                        except Exception as e:
                            logger.warning(f"设备 {device_id} 验证失败: {e}")
                    
                    if not valid_devices:
                        logger.warning("没有检测到可用的Android设备")
                    else:
                        logger.info(f"检测到 {len(valid_devices)} 个可用的Android设备")
                    
                    return valid_devices
                
                except Exception as e:
                    logger.error(f"获取Android设备列表失败: {e}")
                    return []
            else:
                try:
                    # 使用tidevice获取iOS设备列表
                    devices = TiDevice.list_devices()
                    logger.debug(f"iOS设备列表: {devices}")
                    
                    device_ids = [d.udid for d in devices]
                    logger.debug(f"iOS设备ID列表: {device_ids}")
                    
                    if not device_ids:
                        logger.warning("没有检测到iOS设备")
                        return []
                    
                    # 验证每个设备的状态
                    valid_devices = []
                    for device_id in device_ids:
                        try:
                            device = TiDevice(device_id)
                            info = device.info()
                            if info:
                                valid_devices.append(device_id)
                                logger.debug(f"设备 {device_id} 验证通过")
                            else:
                                logger.warning(f"设备 {device_id} 无法获取信息")
                        except Exception as e:
                            logger.warning(f"设备 {device_id} 验证失败: {e}")
                    
                    if not valid_devices:
                        logger.warning("没有检测到可用的iOS设备")
                    else:
                        logger.info(f"检测到 {len(valid_devices)} 个可用的iOS设备")
                    
                    return valid_devices
                
                except Exception as e:
                    logger.error(f"获取iOS设备列表失败: {e}")
                    return []
        
        except Exception as e:
            logger.error(f"获取设备ID列表失败: {e}")
            return []
    
    def _get_android_device_info(self, device_id: str) -> Dict:
        """获取Android设备详细信息"""
        try:
            logger.debug(f"开始获取Android设备信息: {device_id}")
            
            def get_prop(prop: str) -> str:
                try:
                    return subprocess.check_output(
                        f"adb -s {device_id} shell getprop {prop}",
                        shell=True, text=True
                    ).strip()
                except Exception as e:
                    logger.warning(f"获取属性 {prop} 失败: {e}")
                    return "unknown"
            
            # 基本设备信息
            device_info = {
                'id': device_id,
                'platform': 'android',
                'status': 'connected',
                'platform_version': get_prop('ro.build.version.release'),
                'model': get_prop('ro.product.model'),
                'brand': get_prop('ro.product.brand'),
                'manufacturer': get_prop('ro.product.manufacturer'),
                'sdk_version': get_prop('ro.build.version.sdk'),
                'serial': get_prop('ro.serialno'),
                'cpu_abi': get_prop('ro.product.cpu.abi'),
                'device_name': get_prop('ro.product.name')
            }
            
            # 获取分辨率
            try:
                size = subprocess.check_output(
                    f"adb -s {device_id} shell wm size",
                    shell=True, text=True
                ).strip()
                if 'Physical size:' in size:
                    device_info['resolution'] = size.split(':')[1].strip()
            except Exception as e:
                logger.warning(f"获取分辨率失败: {e}")
                device_info['resolution'] = 'unknown'
            
            # 获取电池信息
            try:
                battery = subprocess.check_output(
                    f"adb -s {device_id} shell dumpsys battery",
                    shell=True, text=True
                )
                for line in battery.splitlines():
                    if 'level' in line:
                        level = line.split(':')[1].strip()
                        device_info['battery'] = f"{level}%"
                        break
            except Exception as e:
                logger.warning(f"获取电池信息失败: {e}")
                device_info['battery'] = 'unknown'
            
            # 获取内存信息
            try:
                meminfo = subprocess.check_output(
                    f"adb -s {device_id} shell cat /proc/meminfo",
                    shell=True, text=True
                )
                for line in meminfo.splitlines():
                    if 'MemTotal' in line:
                        total = int(line.split(':')[1].strip().split()[0])
                        device_info['memory'] = f"{total // 1024}MB"
                        break
            except Exception as e:
                logger.warning(f"获取内存信息失败: {e}")
                device_info['memory'] = 'unknown'
            
            # 获取存储信息
            try:
                storage = subprocess.check_output(
                    f"adb -s {device_id} shell df /data",
                    shell=True, text=True
                ).splitlines()[-1]
                total = int(storage.split()[1]) // 1024  # KB to MB
                used = int(storage.split()[2]) // 1024
                device_info['storage'] = {
                    'total': f"{total}MB",
                    'used': f"{used}MB",
                    'free': f"{total - used}MB"
                }
            except Exception as e:
                logger.warning(f"获取存储信息失败: {e}")
                device_info['storage'] = 'unknown'
            
            logger.info(f"成功获取Android设备信息: {device_info}")
            return device_info
            
        except Exception as e:
            logger.error(f"获取Android设备信息失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
            raise DeviceError(f"获取Android设备信息失败: {e}")
    
    def _get_ios_device_info(self, device_id: str) -> Dict:
        """获取iOS设备详细信息"""
        try:
            logger.debug(f"开始获取iOS设备信息: {device_id}")
            device = TiDevice(device_id)
            
            # 获取基本信息
            info = device.info()
            if not info:
                raise DeviceError(f"无法获取iOS设备信息: {device_id}")
            
            device_info = {
                'id': device_id,
                'platform': 'ios',
                'status': 'connected',
                'platform_version': info.get('ProductVersion', 'unknown'),
                'model': info.get('ProductType', 'unknown'),
                'name': info.get('DeviceName', 'unknown'),
                'udid': info.get('UniqueDeviceID', device_id),
                'serial': info.get('SerialNumber', 'unknown'),
                'cpu_architecture': info.get('CPUArchitecture', 'unknown'),
                'device_class': info.get('DeviceClass', 'unknown')
            }
            
            # 获取电池信息
            try:
                battery_info = device.get_io_power()
                if battery_info:
                    device_info['battery'] = f"{battery_info.get('BatteryCurrentCapacity', 'unknown')}%"
            except Exception as e:
                logger.warning(f"获取电池信息失败: {e}")
                device_info['battery'] = 'unknown'
            
            # 获取存储信息
            try:
                storage_info = device.get_disk_usage()
                if storage_info:
                    device_info['storage'] = {
                        'total': f"{storage_info['disk_size'] // (1024*1024)}MB",
                        'used': f"{storage_info['disk_used'] // (1024*1024)}MB",
                        'free': f"{storage_info['disk_free'] // (1024*1024)}MB"
                    }
            except Exception as e:
                logger.warning(f"获取存储信息失败: {e}")
                device_info['storage'] = 'unknown'
            
            logger.info(f"成功获取iOS设备信息: {device_info}")
            return device_info
            
        except Exception as e:
            logger.error(f"获取iOS设备信息失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
            raise DeviceError(f"获取iOS设备信息失败: {e}")

    async def start_monitoring(self) -> bool:
        """启动设备监控"""
        try:
            if not self._stop_event.is_set():
                logger.warning("监控已在运行")
                return True
            
            self._stop_event.clear()
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("设备监控已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动设备监控失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
            return False
    
    async def stop_monitoring(self) -> bool:
        """停止设备监控"""
        try:
            if self._stop_event.is_set():
                logger.warning("监控已停止")
                return True
            
            self._stop_event.set()
            if hasattr(self, '_monitor_task'):
                await self._monitor_task
            logger.info("设备监控已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止设备监控失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
            return False
    
    async def _monitor_loop(self):
        """设备监控循环"""
        try:
            while not self._stop_event.is_set():
                try:
                    await self._refresh_devices()
                    await asyncio.sleep(self._refresh_interval)
                except Exception as e:
                    logger.error(f"设备刷新失败: {e}")
                    logger.debug(f"错误详情: ", exc_info=True)
                    await asyncio.sleep(self._refresh_interval)
            
        except Exception as e:
            logger.error(f"监控循环异常退出: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
    
    async def _refresh_devices(self):
        """刷新设备状态"""
        try:
            current_devices = set()
            
            if self._platform == "android":
                # 获取Android设备列表
                try:
                    adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
                    for device in adb.devices():
                        current_devices.add(device.serial)
                        await self._update_device_status(device.serial)
                except Exception as e:
                    logger.error(f"获取Android设备列表失败: {e}")
            else:
                # 获取iOS设备列表
                try:
                    for device in TiDevice.list_devices():
                        current_devices.add(device)
                        await self._update_device_status(device)
                except Exception as e:
                    logger.error(f"获取iOS设备列表失败: {e}")
            
            # 清理已断开的设备
            cached_devices = set(
                device_id for device_id, info in self._device_cache._cache.items()
                if info[0].get('status') != 'disconnected'
            )
            
            disconnected_devices = cached_devices - current_devices
            for device_id in disconnected_devices:
                await self._handle_device_disconnected(device_id)
            
            logger.debug(f"设备状态刷新完成: {len(current_devices)} 个设备在线")
            
        except Exception as e:
            logger.error(f"刷新设备状态失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
    
    async def _update_device_status(self, device_id: str):
        """更新设备状态"""
        try:
            # 获取设备当前状态
            current_info = self.get_device_info(device_id)
            if not current_info:
                return
            
            # 获取缓存的状态
            cached_info = self._device_cache.get(device_id)
            
            if not cached_info:
                # 新设备
                current_info['status'] = 'available'
                current_info['last_seen'] = time.time()
                self._device_cache.set(device_id, current_info)
                logger.info(f"发现新设备: {device_id}")
                return
            
            # 更新设备状态
            current_info['status'] = cached_info.get('status', 'available')
            current_info['last_seen'] = time.time()
            if 'appium_port' in cached_info:
                current_info['appium_port'] = cached_info['appium_port']
            
            self._device_cache.set(device_id, current_info)
            
        except Exception as e:
            logger.error(f"更新设备 {device_id} 状态失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
    
    async def _handle_device_disconnected(self, device_id: str):
        """处理设备断开连接"""
        try:
            logger.info(f"设备已断开连接: {device_id}")
            
            # 获取设备信息
            device_info = self._device_cache.get(device_id)
            if not device_info:
                return
            
            # 停止相关服务
            if 'appium_port' in device_info:
                await self.stop_appium_server_async(device_info['appium_port'])
            
            # 更新设备状态
            device_info['status'] = 'disconnected'
            device_info['last_seen'] = time.time()
            self._device_cache.set(device_id, device_info)
            
        except Exception as e:
            logger.error(f"处理设备 {device_id} 断开连接失败: {e}")
            logger.debug(f"错误详情: ", exc_info=True)
    
    def get_all_devices(self) -> List[Dict]:
        """获取所有设备信息"""
        try:
            with self._lock:
                return [device.copy() for device in self.devices.values()]
        
        except Exception as e:
            logger.error(f"获取所有设备信息失败: {e}")
            return [] 