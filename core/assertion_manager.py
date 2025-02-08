import os
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from loguru import logger

class AssertionManager:
    def __init__(self, config: Dict):
        """
        初始化断言管理器
        :param config: 配置信息
        """
        self.config = config
        self.assertions = {}
        self._executor = ThreadPoolExecutor(max_workers=4)
        self.load_assertions()
    
    @staticmethod
    def _validate_assertion(assertion: Dict) -> bool:
        """
        验证断言格式是否正确
        :param assertion: 断言数据
        :return: 是否有效
        """
        required_fields = ['name', 'description', 'locator_type', 'locator_value', 'assertion_type']
        if not all(field in assertion for field in required_fields):
            return False
        
        if assertion['assertion_type'] == 'text' and 'expected_text' not in assertion:
            return False
        
        return True
    
    def _load_single_assertion(self, file_path: str) -> Optional[Dict]:
        """
        加载单个断言文件
        :param file_path: 文件路径
        :return: 断言数据或None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                assertion = json.load(f)
                if self._validate_assertion(assertion):
                    return assertion
                else:
                    logger.warning(f"断言格式无效: {file_path}")
                    return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载断言失败 {file_path}: {e}")
            return None
    
    def load_assertions(self):
        """
        加载所有已保存的断言
        """
        try:
            assert_dir = self.config['assert']['save_dir']
            if not os.path.exists(assert_dir):
                os.makedirs(assert_dir, exist_ok=True)
                return
            
            # 遍历所有模块目录
            for module in os.listdir(assert_dir):
                module_path = os.path.join(assert_dir, module)
                if os.path.isdir(module_path):
                    self.assertions[module] = []
                    # 并行加载模块下的所有断言文件
                    assertion_files = [
                        os.path.join(module_path, f)
                        for f in os.listdir(module_path)
                        if f.endswith('.json')
                    ]
                    
                    # 使用线程池并行加载
                    futures = [
                        self._executor.submit(self._load_single_assertion, file_path)
                        for file_path in assertion_files
                    ]
                    
                    # 收集结果
                    for future in futures:
                        assertion = future.result()
                        if assertion:
                            self.assertions[module].append(assertion)
            
            logger.info(f"断言加载完成，共加载 {sum(len(assertions) for assertions in self.assertions.values())} 个断言")
        
        except Exception as e:
            logger.error(f"加载断言失败: {e}")
    
    def create_assertion(self, module: str, name: str, description: str,
                        locator_type: str, locator_value: str,
                        assertion_type: str, expected_text: str = None,
                        timeout: int = None) -> bool:
        """
        创建新的断言
        :param module: 模块名称
        :param name: 断言名称
        :param description: 断言描述
        :param locator_type: 定位方式
        :param locator_value: 定位值
        :param assertion_type: 断言类型（exists/text/attribute/enabled/displayed）
        :param expected_text: 期望的文本值（仅text类型断言需要）
        :param timeout: 超时时间（可选，默认使用配置值）
        :return: 是否创建成功
        """
        try:
            # 验证参数
            if not all([module, name, description, locator_type, locator_value, assertion_type]):
                raise ValueError("必填参数不能为空")
            
            valid_assertion_types = ['exists', 'text', 'attribute', 'enabled', 'displayed']
            if assertion_type not in valid_assertion_types:
                raise ValueError(f"断言类型必须是以下之一: {', '.join(valid_assertion_types)}")
            
            if assertion_type == 'text' and not expected_text:
                raise ValueError("文本断言必须提供期望的文本值")
            
            # 检查是否已存在
            if self.get_assertion(module, name):
                raise ValueError(f"断言已存在: {module}/{name}")
            
            # 准备断言数据
            assertion = {
                'name': name,
                'description': description,
                'locator_type': locator_type,
                'locator_value': locator_value,
                'assertion_type': assertion_type,
                'expected_text': expected_text if assertion_type == 'text' else None,
                'timeout': timeout or self.config['assert']['timeout'],
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'active'
            }
            
            # 创建保存目录
            save_dir = os.path.join(self.config['assert']['save_dir'], module)
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名并保存
            filename = f"{int(time.time())}_{name.replace(' ', '_')}.json"
            file_path = os.path.join(save_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(assertion, f, ensure_ascii=False, indent=2)
            
            # 更新内存中的断言列表
            if module not in self.assertions:
                self.assertions[module] = []
            self.assertions[module].append(assertion)
            
            # 清除缓存
            self.get_assertion.cache_clear()
            
            logger.info(f"断言创建成功: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"创建断言失败: {e}")
            return False
    
    @lru_cache(maxsize=128)
    def get_assertion(self, module: str, name: str) -> Optional[Dict]:
        """
        获取指定的断言
        :param module: 模块名称
        :param name: 断言名称
        :return: 断言数据或None
        """
        try:
            assertions = self.assertions.get(module, [])
            return next((a for a in assertions if a['name'] == name), None)
        except Exception as e:
            logger.error(f"获取断言失败: {e}")
            return None
    
    def update_assertion(self, module: str, name: str, updates: Dict) -> bool:
        """
        更新断言
        :param module: 模块名称
        :param name: 断言名称
        :param updates: 更新的内容
        :return: 是否更新成功
        """
        try:
            # 获取现有断言
            assertion = self.get_assertion(module, name)
            if not assertion:
                raise FileNotFoundError(f"未找到断言: {module}/{name}")
            
            # 验证更新内容
            invalid_fields = [k for k in updates.keys() if k not in assertion]
            if invalid_fields:
                raise ValueError(f"无效的更新字段: {invalid_fields}")
            
            # 更新断言内容
            assertion.update(updates)
            assertion['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存到文件
            module_dir = os.path.join(self.config['assert']['save_dir'], module)
            for filename in os.listdir(module_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(module_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_assertion = json.load(f)
                        if current_assertion['name'] == name:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(assertion, f, ensure_ascii=False, indent=2)
                            
                            # 更新内存中的断言
                            for i, a in enumerate(self.assertions[module]):
                                if a['name'] == name:
                                    self.assertions[module][i] = assertion
                                    break
                            
                            # 清除缓存
                            self.get_assertion.cache_clear()
                            
                            logger.info(f"断言已更新: {file_path}")
                            return True
            
            raise FileNotFoundError(f"未找到断言文件: {module}/{name}")
        
        except Exception as e:
            logger.error(f"更新断言失败: {e}")
            return False
    
    def delete_assertion(self, module: str, name: str) -> bool:
        """
        删除断言
        :param module: 模块名称
        :param name: 断言名称
        :return: 是否删除成功
        """
        try:
            # 检查断言是否存在
            if not self.get_assertion(module, name):
                raise FileNotFoundError(f"未找到断言: {module}/{name}")
            
            module_dir = os.path.join(self.config['assert']['save_dir'], module)
            for filename in os.listdir(module_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(module_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data['name'] == name:
                            # 创建备份
                            backup_dir = os.path.join(self.config['assert']['save_dir'], '_deleted')
                            os.makedirs(backup_dir, exist_ok=True)
                            backup_path = os.path.join(backup_dir, f"{module}_{filename}")
                            os.rename(file_path, backup_path)
                            
                            # 从内存中移除
                            self.assertions[module] = [
                                a for a in self.assertions[module]
                                if a['name'] != name
                            ]
                            
                            # 清除缓存
                            self.get_assertion.cache_clear()
                            
                            logger.info(f"断言已删除并备份: {backup_path}")
                            return True
            
            raise FileNotFoundError(f"未找到断言文件: {module}/{name}")
        
        except Exception as e:
            logger.error(f"删除断言失败: {e}")
            return False
    
    def get_assertions(self, module: str = None, status: str = None) -> List[Dict]:
        """
        获取断言列表
        :param module: 模块名称（可选）
        :param status: 断言状态（可选）
        :return: 断言列表
        """
        try:
            assertions = self.assertions.get(module, []) if module else [
                a for assertions in self.assertions.values() for a in assertions
            ]
            
            if status:
                assertions = [a for a in assertions if a.get('status') == status]
            
            return sorted(assertions, key=lambda x: x['updated_at'], reverse=True)
        
        except Exception as e:
            logger.error(f"获取断言列表失败: {e}")
            return []
    
    def verify_assertion(self, driver: webdriver.Remote, assertion: Dict) -> Tuple[bool, str]:
        """
        验证断言
        :param driver: Appium WebDriver实例
        :param assertion: 断言信息
        :return: (是否通过, 错误信息)
        """
        try:
            if not self._validate_assertion(assertion):
                raise ValueError("无效的断言格式")
            
            # 设置等待时间
            wait = WebDriverWait(driver, assertion.get('timeout', self.config['assert']['timeout']))
            
            # 获取定位方式和值
            locator_type = assertion['locator_type']
            locator_value = assertion['locator_value']
            
            # 尝试定位元素
            try:
                element = wait.until(
                    EC.presence_of_element_located((getattr(AppiumBy, locator_type.upper()), locator_value))
                )
            except TimeoutException:
                return False, f"未找到元素: {locator_type}={locator_value}"
            except Exception as e:
                return False, f"定位元素失败: {e}"
            
            # 根据断言类型进行验证
            try:
                if assertion['assertion_type'] == 'exists':
                    return True, "元素存在"
                
                elif assertion['assertion_type'] == 'text':
                    actual_text = element.text.strip()
                    expected_text = assertion['expected_text'].strip()
                    
                    if actual_text == expected_text:
                        return True, f"文本匹配: {actual_text}"
                    else:
                        return False, f"文本不匹配: 期望={expected_text}, 实际={actual_text}"
                
                elif assertion['assertion_type'] == 'enabled':
                    is_enabled = element.is_enabled()
                    return is_enabled, f"元素{'已启用' if is_enabled else '已禁用'}"
                
                elif assertion['assertion_type'] == 'displayed':
                    is_displayed = element.is_displayed()
                    return is_displayed, f"元素{'可见' if is_displayed else '不可见'}"
                
                elif assertion['assertion_type'] == 'attribute':
                    attribute_name = assertion.get('attribute_name')
                    expected_value = assertion.get('expected_value')
                    
                    if not attribute_name or not expected_value:
                        return False, "属性断言缺少必要参数"
                    
                    actual_value = element.get_attribute(attribute_name)
                    if actual_value == expected_value:
                        return True, f"属性匹配: {attribute_name}={actual_value}"
                    else:
                        return False, f"属性不匹配: {attribute_name}, 期望={expected_value}, 实际={actual_value}"
                
                else:
                    return False, f"不支持的断言类型: {assertion['assertion_type']}"
            
            except StaleElementReferenceException:
                return False, "元素状态已改变，请重试"
            except Exception as e:
                return False, f"验证断言时发生错误: {e}"
        
        except Exception as e:
            return False, f"执行断言失败: {e}"
    
    def generate_assertion_code(self, assertion: Dict) -> str:
        """
        生成断言代码
        :param assertion: 断言信息
        :return: 生成的代码
        """
        try:
            if not self._validate_assertion(assertion):
                raise ValueError("无效的断言格式")
            
            code_lines = []
            
            # 添加定位代码
            code_lines.extend([
                "try:",
                f"    element = WebDriverWait(driver, {assertion.get('timeout', self.config['assert']['timeout'])}).until(",
                f"        EC.presence_of_element_located((AppiumBy.{assertion['locator_type'].upper()}, "
                f"'{assertion['locator_value']}'))",
                "    )"
            ])
            
            # 添加断言代码
            if assertion['assertion_type'] == 'exists':
                code_lines.append("    assert element is not None, '元素不存在'")
            
            elif assertion['assertion_type'] == 'text':
                code_lines.extend([
                    "    actual_text = element.text.strip()",
                    f"    expected_text = '{assertion['expected_text']}'.strip()",
                    "    assert actual_text == expected_text, "
                    "        f'文本不匹配: 期望={expected_text}, 实际={actual_text}'"
                ])
            
            elif assertion['assertion_type'] == 'enabled':
                code_lines.append(
                    "    assert element.is_enabled(), '元素未启用'"
                )
            
            elif assertion['assertion_type'] == 'displayed':
                code_lines.append(
                    "    assert element.is_displayed(), '元素不可见'"
                )
            
            elif assertion['assertion_type'] == 'attribute':
                code_lines.extend([
                    f"    actual_value = element.get_attribute('{assertion['attribute_name']}')",
                    f"    expected_value = '{assertion['expected_value']}'",
                    "    assert actual_value == expected_value, "
                    "        f'属性不匹配: 期望={expected_value}, 实际={actual_value}'"
                ])
            
            # 添加异常处理
            code_lines.extend([
                "except TimeoutException:",
                f"    raise AssertionError('未找到元素: {assertion['locator_type']}={assertion['locator_value']}')",
                "except StaleElementReferenceException:",
                "    raise AssertionError('元素状态已改变，请重试')",
                "except Exception as e:",
                "    raise AssertionError(f'断言执行失败: {e}')"
            ])
            
            return '\n'.join(['    ' + line for line in code_lines])
        
        except Exception as e:
            logger.error(f"生成断言代码失败: {e}")
            return ""
    
    def __del__(self):
        """
        清理资源
        """
        self._executor.shutdown(wait=True) 