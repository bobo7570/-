import os
import subprocess
import platform
from typing import List, Dict
import adbutils
from tidevice import Device as TiDevice
from loguru import logger
import time
import requests

class DeviceManager:
    def __init__(self):
        """初始化设备管理器"""
        self.platform_type = 'android'  # 默认为android
        self.devices = []
        self.appium_processes = {}  # 存储所有启动的 Appium 进程
        self.appium_ports = {}  # 存储所有使用的端口
        self.max_retries = 3  # 最大重试次数
        self.retry_interval = 2  # 重试间隔（秒）
        self.appium_start_timeout = 30  # Appium启动超时时间（秒）
        
        # 初始化日志
        logger.info("设备管理器初始化完成")
    
    def set_platform(self, platform_type: str):
        """
        设置平台类型
        :param platform_type: 平台类型 (android/ios)
        """
        if platform_type not in ['android', 'ios']:
            raise ValueError("平台类型必须是 'android' 或 'ios'")
        logger.info(f"切换平台类型为: {platform_type}")
        self.platform_type = platform_type
        self.devices = []  # 切换平台时清空设备列表
    
    def check_environment(self) -> Dict[str, bool]:
        """
        检查运行环境
        :return: 环境检查结果
        """
        results = {
            'node': False,
            'npm': False,
            'appium': False,
            'adb': False,
            'tidevice': False
        }
        
        try:
            # 检查Node.js
            try:
                node_version = subprocess.check_output('node -v', stderr=subprocess.STDOUT, shell=True)
                results['node'] = True
                logger.info(f"Node.js版本: {node_version.decode().strip()}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Node.js检查失败: {e.output.decode().strip()}")
            
            # 检查npm
            try:
                npm_version = subprocess.check_output('npm -v', stderr=subprocess.STDOUT, shell=True)
                results['npm'] = True
                logger.info(f"npm版本: {npm_version.decode().strip()}")
            except subprocess.CalledProcessError as e:
                logger.error(f"npm检查失败: {e.output.decode().strip()}")
            
            # 检查Appium
            try:
                appium_version = subprocess.check_output('appium -v', stderr=subprocess.STDOUT, shell=True)
                results['appium'] = True
                logger.info(f"Appium版本: {appium_version.decode().strip()}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Appium检查失败: {e.output.decode().strip()}")
            
            # 检查adb
            try:
                adb_version = subprocess.check_output('adb version', stderr=subprocess.STDOUT, shell=True)
                results['adb'] = True
                logger.info(f"ADB版本: {adb_version.decode().strip()}")
            except subprocess.CalledProcessError as e:
                logger.error(f"ADB检查失败: {e.output.decode().strip()}")

            # 检查tidevice
            try:
                tidevice_version = subprocess.check_output('tidevice version', stderr=subprocess.STDOUT, shell=True)
                results['tidevice'] = True
                logger.info(f"tidevice版本: {tidevice_version.decode().strip()}")
            except subprocess.CalledProcessError as e:
                logger.error(f"tidevice检查失败: {e.output.decode().strip()}")
        
        except Exception as e:
            logger.error(f"环境检查失败: {e}")
        
        return results
    
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
        for attempt in range(self.max_retries):
            try:
                result = operation(*args, **kwargs)
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"操作失败，{self.retry_interval}秒后重试: {str(e)}")
                    time.sleep(self.retry_interval)
                else:
                    logger.error(f"操作失败，已达到最大重试次数: {str(e)}")
                    raise

    def get_devices(self) -> List[Dict]:
        """获取已连接的设备列表"""
        return self._retry_operation(self._get_devices_internal)

    def _get_devices_internal(self) -> List[Dict]:
        """内部设备检测实现"""
        self.devices = []
        
        try:
            if self.platform_type == 'android':
                # 启动ADB服务
                try:
                    subprocess.run('adb start-server', shell=True, check=True)
                    logger.info("ADB服务已启动")
                except subprocess.CalledProcessError:
                    logger.warning("ADB服务启动失败，尝试继续检测设备")

                # 使用adbutils获取设备列表
                adb = adbutils.AdbClient(host="127.0.0.1", port=5037)
                device_list = adb.device_list()
                
                for device in device_list:
                    try:
                        device_id = device.serial
                        # 获取设备属性
                        props = {
                            'model': device.prop.get('ro.product.model', 'Unknown'),
                            'brand': device.prop.get('ro.product.brand', 'Unknown'),
                            'version': device.prop.get('ro.build.version.release', 'Unknown'),
                            'sdk': device.prop.get('ro.build.version.sdk', 'Unknown')
                        }
                        
                        device_info = {
                            'id': device_id,
                            'platform': 'android',
                            'platform_version': props['version'],
                            'model': f"{props['brand']} {props['model']}",
                            'sdk_version': props['sdk'],
                            'status': 'device'
                        }
                        self.devices.append(device_info)
                        logger.info(f"找到Android设备: {device_info}")
                    except Exception as e:
                        logger.error(f"获取设备 {device_id} 信息失败: {str(e)}")
            
            elif self.platform_type == 'ios':
                if platform.system() == 'Darwin':  # macOS
                    # 使用libimobiledevice工具获取设备信息
                    try:
                        devices_output = subprocess.check_output(
                            'idevice_id -l',
                            stderr=subprocess.STDOUT,
                            shell=True
                        ).decode().strip()
                        
                        device_ids = [d for d in devices_output.split('\n') if d.strip()]
                        for device_id in device_ids:
                            try:
                                # 获取设备详细信息
                                info = subprocess.check_output(
                                    f'ideviceinfo -u {device_id}',
                                    shell=True
                                ).decode()
                                
                                # 解析设备信息
                                info_dict = {}
                                for line in info.split('\n'):
                                    if ':' in line:
                                        key, value = line.split(':', 1)
                                        info_dict[key.strip()] = value.strip()
                                
                                device_info = {
                                    'id': device_id,
                                    'platform': 'ios',
                                    'platform_version': info_dict.get('ProductVersion', 'Unknown'),
                                    'model': info_dict.get('ProductType', 'Unknown'),
                                    'name': info_dict.get('DeviceName', 'Unknown'),
                                    'status': 'device'
                                }
                                self.devices.append(device_info)
                                logger.info(f"找到iOS设备: {device_info}")
                            except Exception as e:
                                logger.error(f"获取iOS设备 {device_id} 信息失败: {str(e)}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"获取iOS设备列表失败: {e.output.decode().strip()}")
                else:
                    # Windows下使用tidevice
                    try:
                        devices_output = subprocess.check_output(
                            'tidevice list',
                            stderr=subprocess.STDOUT,
                            shell=True
                        ).decode()
                        
                        for line in devices_output.split('\n'):
                            if line.strip():
                                try:
                                    parts = line.strip().split()
                                    if len(parts) >= 1:
                                        device_id = parts[0]
                                        # 获取设备信息
                                        info_output = subprocess.check_output(
                                            f'tidevice info -u {device_id}',
                                            shell=True
                                        ).decode()
                                        
                                        # 解析设备信息
                                        info_dict = {}
                                        for info_line in info_output.split('\n'):
                                            if ':' in info_line:
                                                key, value = info_line.split(':', 1)
                                                info_dict[key.strip()] = value.strip()
                                        
                                        device_info = {
                                            'id': device_id,
                                            'platform': 'ios',
                                            'platform_version': info_dict.get('ProductVersion', 'Unknown'),
                                            'model': info_dict.get('ProductType', 'Unknown'),
                                            'name': info_dict.get('DeviceName', parts[1] if len(parts) > 1 else 'Unknown'),
                                            'status': 'device'
                                        }
                                        self.devices.append(device_info)
                                        logger.info(f"找到iOS设备: {device_info}")
                                except Exception as e:
                                    logger.error(f"获取iOS设备信息失败: {str(e)}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"获取iOS设备列表失败: {e.output.decode().strip()}")
            
            logger.info(f"设备检测完成，共找到 {len(self.devices)} 个设备")
            return self.devices
        
        except Exception as e:
            logger.error(f"设备检测失败: {str(e)}")
            return []
    
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
                        self.appium_processes[port] = process
                        self.appium_ports[port] = {
                            'host': host,
                            'status': 'running',
                            'start_time': time.time()
                        }
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
                if port in self.appium_processes:
                    process = self.appium_processes[port]
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
                    
                    del self.appium_processes[port]
                    del self.appium_ports[port]
                    logger.info(f"Appium服务已停止: 端口 {port}")
            else:
                # 停止所有服务
                for port, process in list(self.appium_processes.items()):
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
                
                self.appium_processes.clear()
                self.appium_ports.clear()
        
        except Exception as e:
            logger.error(f"停止Appium服务失败: {e}")
    
    def get_appium_servers(self) -> List[Dict]:
        """
        获取所有Appium服务的状态
        :return: 服务状态列表
        """
        servers = []
        for port, info in self.appium_ports.items():
            try:
                # 检查服务是否仍在运行
                response = requests.get(f"http://{info['host']}:{port}/status", timeout=2)
                status = 'running' if response.status_code == 200 else 'error'
            except:
                status = 'error'
                # 如果服务不可用，尝试清理
                if port in self.appium_processes:
                    self.stop_appium_server(port)
            
            if status == 'running':
                servers.append({
                    'host': info['host'],
                    'port': port,
                    'status': status,
                    'start_time': info.get('start_time', time.time())
                })
        
        return servers
    
    def _is_port_in_use(self, port: int) -> bool:
        """
        检查端口是否被占用
        :param port: 端口号
        :return: 是否被占用
        """
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def __del__(self):
        """
        析构函数，确保所有Appium服务被关闭
        """
        self.stop_appium_server() 