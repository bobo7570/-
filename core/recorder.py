import os
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.common.touch_action import TouchAction
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from loguru import logger

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
        self.start_time = None
        self.last_action_time = None
        self.current_activity = None  # 当前Activity（Android）
        self.current_window = None    # 当前Window（iOS）
    
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
    
    def start_recording(self) -> bool:
        """
        开始录制
        :return: 是否成功启动录制
        """
        try:
            if not self.device_info:
                logger.error("未设置设备信息")
                return False

            # 设置Appium配置
            platform = self.device_info.get('platform', '').lower()
            if platform not in ['android', 'ios']:
                logger.error(f"不支持的平台类型: {platform}")
                return False

            caps = self._get_android_caps() if platform == 'android' else self._get_ios_caps()
            logger.info(f"Appium capabilities配置: {caps}")
            
            # 连接Appium服务器
            appium_url = f"http://{self.config['appium']['host']}:{self.config['appium']['port']}"
            logger.info(f"正在连接Appium服务器: {appium_url}")
            
            try:
                # 使用 options 参数初始化
                from appium.options.android import UiAutomator2Options
                from appium.options.ios import XCUITestOptions
                
                if platform == 'android':
                    options = UiAutomator2Options()
                else:
                    options = XCUITestOptions()
                
                for key, value in caps.items():
                    options.set_capability(key, value)
                
                self.driver = webdriver.Remote(appium_url, options=options)
                logger.info("已成功连接到Appium服务器")
            except Exception as e:
                logger.error(f"连接Appium服务器失败: {e}")
                return False
            
            # 设置等待时间
            implicit_wait = self.config.get('appium', {}).get('implicit_wait', 10)
            self.driver.implicitly_wait(implicit_wait)
            logger.info(f"设置隐式等待时间: {implicit_wait}秒")
            
            # 初始化录制状态
            self.recording = True
            self.actions = []
            self.start_time = time.time()
            self.last_action_time = self.start_time
            
            # 记录初始状态
            try:
                if platform == 'android':
                    self.current_activity = self.driver.current_activity
                    current_package = self.driver.current_package
                    logger.info(f"当前Activity: {self.current_activity}")
                    logger.info(f"当前Package: {current_package}")
                else:
                    self.current_window = self.driver.current_window_handle
                    current_context = self.driver.current_context
                    logger.info(f"当前Window: {self.current_window}")
                    logger.info(f"当前Context: {current_context}")
            except Exception as e:
                logger.warning(f"获取初始状态信息失败: {e}")
            
            logger.info("录制已成功启动")
            return True
        
        except Exception as e:
            logger.error(f"启动录制失败: {e}")
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("已关闭Appium driver")
                except Exception as close_error:
                    logger.error(f"关闭driver失败: {close_error}")
            return False
    
    def stop_recording(self) -> List[Dict]:
        """
        停止录制
        :return: 录制的操作列表
        """
        try:
            self.recording = False
            if self.driver:
                try:
                    if self.device_info['platform'] == 'android':
                        final_activity = self.driver.current_activity
                        if final_activity != self.current_activity:
                            logger.info(f"Activity已改变: {self.current_activity} -> {final_activity}")
                    else:
                        final_window = self.driver.current_window_handle
                        if final_window != self.current_window:
                            logger.info(f"Window已改变: {self.current_window} -> {final_window}")
                except:
                    pass
                
                try:
                    self.driver.quit()
                except:
                    pass
            
            logger.info(f"录制已停止，共记录 {len(self.actions)} 个操作")
            return self.actions
        
        except Exception as e:
            logger.error(f"停止录制失败: {e}")
            return []
    
    def record_action(self, action_type: str, element: Dict = None, coordinates: Dict = None,
                     text: str = None, duration: int = None, extra_info: Dict = None):
        """
        记录一个操作
        :param action_type: 操作类型（click/input/swipe/long_press/multi_touch等）
        :param element: 元素信息
        :param coordinates: 坐标信息
        :param text: 输入文本
        :param duration: 操作持续时间
        :param extra_info: 额外信息
        """
        if not self.recording:
            return
        
        try:
            current_time = time.time()
            time_gap = current_time - self.last_action_time
            
            # 获取当前页面状态
            context_info = {}
            try:
                if self.device_info['platform'] == 'android':
                    context_info['activity'] = self.driver.current_activity
                    context_info['package'] = self.driver.current_package
                else:
                    context_info['window'] = self.driver.current_window_handle
                    context_info['context'] = self.driver.current_context
            except:
                pass
            
            action = {
                'type': action_type,
                'timestamp': current_time,
                'time_gap': time_gap,
                'context': context_info
            }
            
            if element:
                action['element'] = element
            if coordinates:
                action['coordinates'] = coordinates
            if text:
                action['text'] = text
            if duration:
                action['duration'] = duration
            if extra_info:
                action['extra_info'] = extra_info
            
            self.actions.append(action)
            self.last_action_time = current_time
            
            logger.debug(f"记录操作: {action}")
        
        except Exception as e:
            logger.error(f"记录操作失败: {e}")
    
    def save_recording(self, module: str, name: str, description: str) -> bool:
        """
        保存录制结果
        :param module: 模块名称
        :param name: 操作名称
        :param description: 操作描述
        :return: 是否保存成功
        """
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
    
    def generate_test_code(self, module: str, name: str) -> str:
        """
        生成测试用例代码
        :param module: 模块名称
        :param name: 操作名称
        :return: 生成的代码
        """
        try:
            code_lines = [
                "from appium import webdriver",
                "from appium.webdriver.common.appiumby import AppiumBy",
                "from appium.webdriver.common.touch_action import TouchAction",
                "from selenium.webdriver.support.ui import WebDriverWait",
                "from selenium.webdriver.support import expected_conditions as EC",
                "from selenium.common.exceptions import TimeoutException, NoSuchElementException",
                "import time\n",
                f"def test_{module}_{name.lower().replace(' ', '_')}(driver):",
                "    try:",
                "        wait = WebDriverWait(driver, 10)"
            ]
            
            # 添加每个操作的代码
            for i, action in enumerate(self.actions, 1):
                # 添加操作注释
                code_lines.append(f"\n        # 步骤 {i}: {action['type']}")
                
                # 根据操作类型生成代码
                if action['type'] == 'click':
                    if 'element' in action:
                        code_lines.extend(self._generate_element_action_code(action))
                elif action['type'] == 'input':
                    if 'element' in action and 'text' in action:
                        code_lines.extend(self._generate_input_action_code(action))
                elif action['type'] == 'swipe':
                    if 'coordinates' in action:
                        code_lines.extend(self._generate_swipe_action_code(action))
                elif action['type'] == 'long_press':
                    if 'element' in action or 'coordinates' in action:
                        code_lines.extend(self._generate_long_press_code(action))
                elif action['type'] == 'multi_touch':
                    if 'actions' in action.get('extra_info', {}):
                        code_lines.extend(self._generate_multi_touch_code(action))
                
                # 添加等待时间
                if action['time_gap'] > 0.5:  # 只有当间隔大于0.5秒时才添加等待
                    code_lines.append(f"        time.sleep({action['time_gap']:.1f})")
                
                # 添加上下文检查
                if 'context' in action:
                    code_lines.extend(self._generate_context_check_code(action['context']))
            
            # 添加异常处理
            code_lines.extend([
                "\n        logger.info('测试用例执行成功')",
                "        return True",
                "    except TimeoutException as e:",
                "        logger.error(f'等待元素超时: {e}')",
                "        return False",
                "    except NoSuchElementException as e:",
                "        logger.error(f'未找到元素: {e}')",
                "        return False",
                "    except Exception as e:",
                "        logger.error(f'测试执行失败: {e}')",
                "        return False"
            ])
            
            return '\n'.join(['    ' + line for line in code_lines])
        
        except Exception as e:
            logger.error(f"生成测试代码失败: {e}")
            return ""
    
    def _generate_element_action_code(self, action: Dict) -> List[str]:
        """
        生成元素操作代码
        :param action: 操作信息
        :return: 生成的代码行列表
        """
        element = action['element']
        locator_type = element.get('locator_type', 'id')
        locator_value = element.get('locator_value', '')
        
        return [
            f"element = wait.until(",
            f"    EC.presence_of_element_located((AppiumBy.{locator_type.upper()}, '{locator_value}'))",
            ")",
            "element.click()"
        ]
    
    def _generate_input_action_code(self, action: Dict) -> List[str]:
        """
        生成输入操作代码
        :param action: 操作信息
        :return: 生成的代码行列表
        """
        element = action['element']
        locator_type = element.get('locator_type', 'id')
        locator_value = element.get('locator_value', '')
        text = action['text']
        
        return [
            f"element = wait.until(",
            f"    EC.presence_of_element_located((AppiumBy.{locator_type.upper()}, '{locator_value}'))",
            ")",
            "element.clear()",
            f"element.send_keys('{text}')"
        ]
    
    def _generate_swipe_action_code(self, action: Dict) -> List[str]:
        """
        生成滑动操作代码
        :param action: 操作信息
        :return: 生成的代码行列表
        """
        coords = action['coordinates']
        duration = action.get('duration', 500)
        
        return [
            f"driver.swipe(",
            f"    {coords['start_x']}, {coords['start_y']},",
            f"    {coords['end_x']}, {coords['end_y']},",
            f"    {duration}",
            ")"
        ]
    
    def _generate_long_press_code(self, action: Dict) -> List[str]:
        """
        生成长按操作代码
        :param action: 操作信息
        :return: 生成的代码行列表
        """
        code_lines = ["actions = TouchAction(driver)"]
        
        if 'element' in action:
            element = action['element']
            locator_type = element.get('locator_type', 'id')
            locator_value = element.get('locator_value', '')
            code_lines.extend([
                f"element = wait.until(",
                f"    EC.presence_of_element_located((AppiumBy.{locator_type.upper()}, '{locator_value}'))",
                ")",
                f"actions.long_press(element, duration={action.get('duration', 1000)})"
            ])
        else:
            coords = action['coordinates']
            code_lines.append(
                f"actions.long_press(x={coords['x']}, y={coords['y']}, duration={action.get('duration', 1000)})"
            )
        
        code_lines.append("actions.perform()")
        return code_lines
    
    def _generate_multi_touch_code(self, action: Dict) -> List[str]:
        """
        生成多点触控操作代码
        :param action: 操作信息
        :return: 生成的代码行列表
        """
        touch_actions = action['extra_info']['actions']
        code_lines = []
        
        for i, touch in enumerate(touch_actions):
            code_lines.extend([
                f"action{i} = TouchAction(driver)",
                f"action{i}.press(x={touch['x']}, y={touch['y']})",
                f"action{i}.wait({touch.get('duration', 500)})",
                f"action{i}.release()"
            ])
        
        action_names = [f"action{i}" for i in range(len(touch_actions))]
        code_lines.append(f"driver.multi_action([{', '.join(action_names)}])")
        
        return code_lines
    
    def _generate_context_check_code(self, context: Dict) -> List[str]:
        """
        生成上下文检查代码
        :param context: 上下文信息
        :return: 生成的代码行列表
        """
        code_lines = []
        
        if 'activity' in context:
            code_lines.extend([
                f"# 检查当前Activity",
                f"current_activity = driver.current_activity",
                f"if current_activity != '{context['activity']}':",
                f"    logger.warning(f'Activity不匹配: 期望={context['activity']}, 实际={{current_activity}}')"
            ])
        
        if 'window' in context:
            code_lines.extend([
                f"# 检查当前Window",
                f"current_window = driver.current_window_handle",
                f"if current_window != '{context['window']}':",
                f"    logger.warning(f'Window不匹配: 期望={context['window']}, 实际={{current_window}}')"
            ])
        
        return code_lines
    
    def __del__(self):
        """
        析构函数，确保driver被正确关闭
        """
        try:
            if self.driver:
                self.driver.quit()
        except Exception as e:
            logger.error(f"关闭driver失败: {e}") 