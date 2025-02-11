import os
import time
import json
import asyncio
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple, Any
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.common.touch_action import TouchAction
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, WebDriverException
)
from loguru import logger

from utils.errors import RecordError
from utils.constants import ActionType, DEFAULT_WAIT_TIMEOUT

class ActionRecorder:
    def __init__(self, device_info: Dict, config: Dict):
        """
        初始化录制器
        :param device_info: 设备信息
        :param config: 配置信息
        """
        self.device_info = device_info
        self.config = config
        self.driver = None
        self.recording = False
        self.actions = []
        self._action_queue = Queue()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._record_thread = None
        self._process_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._last_action_time = 0
        self._batch_size = config.get('batch_size', 10)
        self._batch_timeout = config.get('batch_timeout', 1.0)
        self._max_retries = config.get('max_retries', 3)
        self._retry_interval = config.get('retry_interval', 1.0)
        self._wait_timeout = config.get('wait_timeout', DEFAULT_WAIT_TIMEOUT)
        self.start_time = None
        self.last_action_time = None
        self.current_activity = None  # 当前Activity（Android）
        self.current_window = None    # 当前Window（iOS）
        self._error_count = 0
        self._max_errors = config.get('max_errors', 5)
        
        logger.info("录制器初始化完成")
    
    def _get_android_caps(self) -> Dict:
        """
        获取Android设备的Capabilities配置
        :return: Capabilities配置
        """
        caps = {
            'platformName': 'Android',
            'platformVersion': str(self.device_info['platform_version']),
            'deviceName': str(self.device_info['id']),
            'automationName': 'UiAutomator2',
            'noReset': True,
            'autoGrantPermissions': True,
            'newCommandTimeout': 300,
            'adbExecTimeout': 60000,
            'uiautomator2ServerInstallTimeout': 60000,
            'androidInstallTimeout': 90000,
            'skipServerInstallation': False,
            'skipDeviceInitialization': False,
            'systemPort': 8201,  # 添加systemPort配置
            'uiautomator2ServerLaunchTimeout': 60000,  # 添加启动超时配置
            'uiautomator2ServerReadTimeout': 60000,   # 添加读取超时配置
            'adbExecTimeout': 60000,                 # ADB执行超时
            'androidDeviceReadyTimeout': 60000,      # 设备准备超时
            'avdLaunchTimeout': 60000,              # AVD启动超时
            'avdReadyTimeout': 60000,               # AVD准备超时
            'ignoreUnimportantViews': True,         # 忽略不重要的视图
            'disableAndroidWatchers': True,         # 禁用Android观察器
            'skipLogcatCapture': True,              # 跳过日志捕获
            'ensureWebviewsHavePages': True,        # 确保Webview有页面
            'skipDeviceInitialization': False,      # 不跳过设备初始化
            'skipServerInstallation': False,        # 不跳过服务器安装
        }

        # 从配置文件中获取应用信息
        android_config = self.config.get('devices', {}).get('android', [{}])[0]
        if android_config:
            if 'app_package' in android_config:
                caps['appPackage'] = android_config['app_package']
            if 'app_activity' in android_config:
                caps['appActivity'] = android_config['app_activity']
            if 'system_port' in android_config:
                caps['systemPort'] = android_config['system_port']
            if 'no_reset' in android_config:
                caps['noReset'] = android_config['no_reset']

        # 如果没有设置应用包名和Activity,使用默认值
        if 'appPackage' not in caps:
            caps['appPackage'] = 'com.android.settings'
            caps['appActivity'] = '.Settings'

        return caps
    
    def _get_ios_caps(self) -> Dict:
        """
        获取iOS设备的Capabilities配置
        :return: Capabilities配置
        """
        caps = {
            'platformName': 'iOS',
            'platformVersion': str(self.device_info['platform_version']),
            'deviceName': str(self.device_info['id']),
            'automationName': 'XCUITest',
            'noReset': True,
            'newCommandTimeout': 300,
            'webviewConnectTimeout': 90000,
            'simpleIsVisibleCheck': True
        }

        # 从配置文件中获取应用信息
        ios_config = self.config.get('devices', {}).get('ios', [{}])[0]
        if ios_config:
            if 'bundle_id' in ios_config:
                caps['bundleId'] = ios_config['bundle_id']
            if 'wda_local_port' in ios_config:
                caps['wdaLocalPort'] = ios_config['wda_local_port']
            if 'no_reset' in ios_config:
                caps['noReset'] = ios_config['no_reset']

        return caps
    
    async def start_recording_async(self) -> bool:
        """异步启动录制"""
        try:
            if self.recording:
                logger.warning("录制已在进行中")
                return False
            
            # 重置状态
            self._reset_state()
            
            # 启动录制
            success = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._start_recording_sync
            )
            
            if not success:
                raise RecordError("启动录制失败")
            
            # 启动录制线程
            self._record_thread = threading.Thread(
                target=self._record_loop,
                name="RecordThread",
                daemon=True
            )
            self._record_thread.start()
            
            # 启动处理线程
            self._process_thread = threading.Thread(
                target=self._process_loop,
                name="ProcessThread",
                daemon=True
            )
            self._process_thread.start()
            
            logger.info("录制已启动")
            return True
        
        except Exception as e:
            logger.error(f"启动录制失败: {e}")
            self._cleanup()
            return False
    
    async def stop_recording_async(self) -> List[Dict]:
        """异步停止录制"""
        try:
            if not self.recording:
                logger.warning("录制未在进行")
                return []
            
            # 停止录制
            self.recording = False
            self._stop_event.set()
            
            # 等待线程结束
            if self._record_thread:
                self._record_thread.join(timeout=5.0)
            if self._process_thread:
                self._process_thread.join(timeout=5.0)
            
            # 处理剩余动作
            self._process_remaining_actions()
            
            # 停止WebDriver
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._stop_recording_sync
            )
            
            logger.info(f"录制已停止，共记录 {len(self.actions)} 个动作")
            return self.actions
        
        except Exception as e:
            logger.error(f"停止录制失败: {e}")
            self._cleanup()
            return []
    
    def _reset_state(self):
        """重置状态"""
        self.recording = True
        self.actions = []
        self._stop_event.clear()
        self._error_count = 0
        self._last_action_time = time.time()
        self.start_time = time.time()
        self.last_action_time = self.start_time
        
        # 清空队列
        while not self._action_queue.empty():
            try:
                self._action_queue.get_nowait()
            except Empty:
                break
    
    def _cleanup(self):
        """清理资源"""
        try:
            self.recording = False
            self._stop_event.set()
            
            # 关闭WebDriver
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.error(f"关闭WebDriver失败: {e}")
                finally:
                    self.driver = None
            
            # 清空队列
            while not self._action_queue.empty():
                try:
                    self._action_queue.get_nowait()
                except Empty:
                    break
            
            logger.info("录制器资源已清理")
        
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def _record_loop(self):
        """录制循环"""
        try:
            while not self._stop_event.is_set():
                try:
                    # 获取当前界面状态
                    current_state = self._get_current_state()
                    
                    # 检测变化并记录动作
                    if self._should_record_action(current_state):
                        action = self._create_action(current_state)
                        if action:
                            self._action_queue.put(action)
                            logger.debug(f"记录动作: {action['type']}")
                    
                    # 控制录制频率
                    time.sleep(self.config.get('record_interval', 0.5))
                
                except Exception as e:
                    logger.error(f"录制过程发生错误: {e}")
                    self._error_count += 1
                    if self._error_count >= self._max_errors:
                        logger.error("错误次数过多，停止录制")
                        break
                    time.sleep(self._retry_interval)
        
        except Exception as e:
            logger.error(f"录制线程异常退出: {e}")
        finally:
            self.recording = False
    
    def _process_loop(self):
        """处理循环"""
        try:
            batch = []
            last_process_time = time.time()
            
            while not self._stop_event.is_set() or not self._action_queue.empty():
                try:
                    # 获取动作（带超时）
                    try:
                        action = self._action_queue.get(timeout=0.1)
                        if action:
                            batch.append(action)
                    except Empty:
                        pass
                    
                    current_time = time.time()
                    should_process = (
                        len(batch) >= self._batch_size or
                        (batch and current_time - last_process_time >= self._batch_timeout) or
                        (self._stop_event.is_set() and batch)
                    )
                    
                    if should_process:
                        self._process_batch(batch)
                        batch = []
                        last_process_time = current_time
                
                except Exception as e:
                    logger.error(f"处理动作时发生错误: {e}")
                    time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"处理线程异常退出: {e}")
    
    def _process_batch(self, batch: List[Dict]):
        """批量处理动作"""
        if not batch:
            return
        
        try:
            with self._lock:
                # 优化动作序列
                optimized = self._optimize_actions(batch)
                
                # 添加到动作列表
                if optimized:
                    self.actions.extend(optimized)
                    
                    # 如果动作列表过长，清理旧的动作
                    max_actions = self.config.get('max_actions', 1000)
                    if len(self.actions) > max_actions:
                        self.actions = self.actions[-max_actions:]
                    
                    logger.debug(f"处理 {len(optimized)} 个动作")
        
        except Exception as e:
            logger.error(f"处理动作批次失败: {e}")
    
    def _optimize_actions(self, actions: List[Dict]) -> List[Dict]:
        """优化动作序列"""
        if not actions:
            return []
        
        try:
            optimized = []
            for action in actions:
                if not optimized:
                    optimized.append(action)
                    continue
                
                # 尝试合并动作
                if self._can_merge_actions(optimized[-1], action):
                    optimized[-1] = self._merge_actions(optimized[-1], action)
                else:
                    optimized.append(action)
            
            return optimized
        
        except Exception as e:
            logger.error(f"优化动作序列失败: {e}")
            return actions
    
    def _can_merge_actions(self, action1: Dict, action2: Dict) -> bool:
        """判断两个动作是否可以合并"""
        try:
            # 相同类型的动作
            if action1.get('type') != action2.get('type'):
                return False
            
            # 时间间隔小于阈值
            time_gap = action2.get('timestamp', 0) - action1.get('timestamp', 0)
            if time_gap > self.config.get('merge_threshold', 0.5):
                return False
            
            # 特定类型的动作合并规则
            action_type = action1.get('type')
            if action_type == ActionType.CLICK.value:
                # 相同位置的点击
                return (
                    abs(action1.get('x', 0) - action2.get('x', 0)) < 5 and
                    abs(action1.get('y', 0) - action2.get('y', 0)) < 5
                )
            elif action_type == ActionType.INPUT.value:
                # 连续的输入
                return True
            elif action_type == ActionType.SWIPE.value:
                # 相似的滑动
                return (
                    abs(action1.get('start_x', 0) - action2.get('start_x', 0)) < 10 and
                    abs(action1.get('start_y', 0) - action2.get('start_y', 0)) < 10 and
                    abs(action1.get('end_x', 0) - action2.get('end_x', 0)) < 10 and
                    abs(action1.get('end_y', 0) - action2.get('end_y', 0)) < 10
                )
            
            return False
        
        except Exception as e:
            logger.error(f"判断动作是否可合并时发生错误: {e}")
            return False
    
    def _merge_actions(self, action1: Dict, action2: Dict) -> Dict:
        """合并两个动作"""
        try:
            merged = action1.copy()
            
            # 更新时间戳
            merged['timestamp'] = action2.get('timestamp', 0)
            merged['time_gap'] = action2.get('time_gap', 0)
            
            # 特定类型的动作合并逻辑
            action_type = action1.get('type')
            if action_type == ActionType.CLICK.value:
                # 增加点击次数
                merged['clicks'] = merged.get('clicks', 1) + 1
            elif action_type == ActionType.INPUT.value:
                # 合并输入文本
                merged['text'] = merged.get('text', '') + action2.get('text', '')
            elif action_type == ActionType.SWIPE.value:
                # 使用最新的坐标
                merged.update({
                    'start_x': action2.get('start_x', 0),
                    'start_y': action2.get('start_y', 0),
                    'end_x': action2.get('end_x', 0),
                    'end_y': action2.get('end_y', 0)
                })
            
            return merged
        
        except Exception as e:
            logger.error(f"合并动作失败: {e}")
            return action1
    
    def _process_remaining_actions(self):
        """处理剩余的动作"""
        try:
            remaining = []
            while not self._action_queue.empty():
                try:
                    action = self._action_queue.get_nowait()
                    if action:
                        remaining.append(action)
                except Empty:
                    break
            
            if remaining:
                self._process_batch(remaining)
        
        except Exception as e:
            logger.error(f"处理剩余动作失败: {e}")
    
    def _get_current_state(self) -> Dict:
        """获取当前界面状态"""
        try:
            if not self.driver:
                return {}
            
            state = {}
            
            # 获取平台特定信息
            try:
                if self.device_info['platform'] == 'android':
                    state.update({
                        'activity': self.driver.current_activity,
                        'package': self.driver.current_package
                    })
                else:
                    state.update({
                        'window': self.driver.current_window_handle,
                        'context': self.driver.current_context
                    })
            except WebDriverException:
                pass
            
            # 获取界面元素
            try:
                source = self.driver.page_source
                state['source_hash'] = hash(source)
            except WebDriverException:
                pass
            
            # 获取屏幕方向
            try:
                state['orientation'] = self.driver.orientation
            except WebDriverException:
                pass
            
            return state
        
        except Exception as e:
            logger.error(f"获取当前状态失败: {e}")
            return {}
    
    def _should_record_action(self, current_state: Dict) -> bool:
        """判断是否应该记录动作"""
        try:
            if not current_state:
                return False
            
            # 检查状态变化
            if self.current_activity != current_state.get('activity'):
                return True
            if self.current_window != current_state.get('window'):
                return True
            
            # 检查时间间隔
            current_time = time.time()
            if current_time - self._last_action_time >= self.config.get('min_action_interval', 0.1):
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"判断是否应该记录动作时发生错误: {e}")
            return False
    
    def _create_action(self, current_state: Dict) -> Optional[Dict]:
        """创建动作"""
        try:
            if not current_state:
                return None
            
            current_time = time.time()
            action = {
                'type': ActionType.STATE_CHANGE.value,
                'timestamp': current_time,
                'time_gap': current_time - self._last_action_time,
                'state': current_state
            }
            
            self._last_action_time = current_time
            return action
        
        except Exception as e:
            logger.error(f"创建动作失败: {e}")
            return None
    
    def save_recording(self, module: str, name: str, description: str = "") -> bool:
        """保存录制结果"""
        try:
            # 创建保存目录
            save_dir = os.path.join(self.config['record']['save_dir'], module)
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名
            filename = f"{int(time.time())}_{name.replace(' ', '_')}.json"
            filepath = os.path.join(save_dir, filename)
            
            # 准备保存数据
            data = {
                'name': name,
                'description': description,
                'module': module,
                'platform': self.device_info['platform'],
                'device_info': {
                    'id': self.device_info['id'],
                    'platform_version': self.device_info['platform_version'],
                    'model': self.device_info.get('model', 'Unknown')
                },
                'app_info': {
                    'package': self.config['devices'][self.device_info['platform']][0].get('app_package', ''),
                    'activity': self.config['devices'][self.device_info['platform']][0].get('app_activity', ''),
                    'bundle_id': self.config['devices'][self.device_info['platform']][0].get('bundle_id', '')
                },
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': time.time() - self.start_time,
                'action_count': len(self.actions),
                'actions': self.actions
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"录制结果已保存: {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"保存录制结果失败: {e}")
            return False
    
    def __del__(self):
        """析构函数"""
        self._cleanup() 