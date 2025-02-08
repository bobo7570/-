import os
import json
import time
from typing import Dict, List, Optional, Union
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

class TestCaseManager:
    def __init__(self, config: Dict):
        """
        初始化用例管理器
        :param config: 配置信息
        """
        self.config = config
        self.test_cases = {}
        self._executor = ThreadPoolExecutor(max_workers=4)  # 用于并行处理
        self.load_test_cases()
    
    @staticmethod
    def _validate_test_case(test_case: Dict) -> bool:
        """
        验证测试用例格式是否正确
        :param test_case: 测试用例数据
        :return: 是否有效
        """
        required_fields = ['name', 'description', 'module', 'steps', 'assertions']
        return all(field in test_case for field in required_fields)
    
    def _load_single_case(self, file_path: str) -> Optional[Dict]:
        """
        加载单个测试用例文件
        :param file_path: 文件路径
        :return: 测试用例数据或None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                test_case = json.load(f)
                if self._validate_test_case(test_case):
                    return test_case
                else:
                    logger.warning(f"测试用例格式无效: {file_path}")
                    return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载测试用例失败 {file_path}: {e}")
            return None
    
    def load_test_cases(self):
        """
        加载所有测试用例
        """
        try:
            case_dir = self.config['test']['case_dir']
            if not os.path.exists(case_dir):
                os.makedirs(case_dir, exist_ok=True)
                return
            
            # 遍历所有模块目录
            for module in os.listdir(case_dir):
                module_path = os.path.join(case_dir, module)
                if os.path.isdir(module_path):
                    self.test_cases[module] = []
                    # 并行加载模块下的所有用例文件
                    case_files = [
                        os.path.join(module_path, f)
                        for f in os.listdir(module_path)
                        if f.endswith('.json')
                    ]
                    
                    # 使用线程池并行加载
                    futures = [
                        self._executor.submit(self._load_single_case, file_path)
                        for file_path in case_files
                    ]
                    
                    # 收集结果
                    for future in futures:
                        test_case = future.result()
                        if test_case:
                            self.test_cases[module].append(test_case)
            
            logger.info(f"测试用例加载完成，共加载 {sum(len(cases) for cases in self.test_cases.values())} 个用例")
        
        except Exception as e:
            logger.error(f"加载测试用例失败: {e}")
    
    def create_test_case(self, module: str, name: str, description: str,
                        steps: List[Dict], assertions: List[Dict]) -> bool:
        """
        创建新的测试用例
        :param module: 模块名称
        :param name: 用例名称
        :param description: 用例描述
        :param steps: 测试步骤列表
        :param assertions: 断言列表
        :return: 是否创建成功
        """
        try:
            # 验证参数
            if not all([module, name, description, steps, assertions]):
                raise ValueError("必填参数不能为空")
            
            # 检查用例名称是否已存在
            if self.get_test_case(module, name):
                raise ValueError(f"测试用例已存在: {module}/{name}")
            
            # 准备测试用例数据
            test_case = {
                'name': name,
                'description': description,
                'module': module,
                'steps': steps,
                'assertions': assertions,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'active'
            }
            
            # 创建保存目录
            save_dir = os.path.join(self.config['test']['case_dir'], module)
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名并保存
            filename = f"{int(time.time())}_{name.replace(' ', '_')}.json"
            file_path = os.path.join(save_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_case, f, ensure_ascii=False, indent=2)
            
            # 更新内存中的用例列表
            if module not in self.test_cases:
                self.test_cases[module] = []
            self.test_cases[module].append(test_case)
            
            # 清除缓存
            self.get_test_case.cache_clear()
            
            logger.info(f"测试用例创建成功: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"创建测试用例失败: {e}")
            return False
    
    @lru_cache(maxsize=128)
    def get_test_case(self, module: str, name: str) -> Optional[Dict]:
        """
        获取指定的测试用例
        :param module: 模块名称
        :param name: 用例名称
        :return: 测试用例数据或None
        """
        try:
            cases = self.test_cases.get(module, [])
            return next((case for case in cases if case['name'] == name), None)
        except Exception as e:
            logger.error(f"获取测试用例失败: {e}")
            return None
    
    def update_test_case(self, module: str, name: str, updates: Dict) -> bool:
        """
        更新测试用例
        :param module: 模块名称
        :param name: 用例名称
        :param updates: 更新的内容
        :return: 是否更新成功
        """
        try:
            # 获取现有用例
            test_case = self.get_test_case(module, name)
            if not test_case:
                raise FileNotFoundError(f"未找到测试用例: {module}/{name}")
            
            # 验证更新内容
            invalid_fields = [k for k in updates.keys() if k not in test_case]
            if invalid_fields:
                raise ValueError(f"无效的更新字段: {invalid_fields}")
            
            # 更新用例内容
            test_case.update(updates)
            test_case['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存到文件
            module_dir = os.path.join(self.config['test']['case_dir'], module)
            for filename in os.listdir(module_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(module_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        current_case = json.load(f)
                        if current_case['name'] == name:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(test_case, f, ensure_ascii=False, indent=2)
                            
                            # 更新内存中的用例
                            for i, case in enumerate(self.test_cases[module]):
                                if case['name'] == name:
                                    self.test_cases[module][i] = test_case
                                    break
                            
                            # 清除缓存
                            self.get_test_case.cache_clear()
                            
                            logger.info(f"测试用例已更新: {file_path}")
                            return True
            
            raise FileNotFoundError(f"未找到测试用例文件: {module}/{name}")
        
        except Exception as e:
            logger.error(f"更新测试用例失败: {e}")
            return False
    
    def delete_test_case(self, module: str, name: str) -> bool:
        """
        删除测试用例
        :param module: 模块名称
        :param name: 用例名称
        :return: 是否删除成功
        """
        try:
            # 检查用例是否存在
            if not self.get_test_case(module, name):
                raise FileNotFoundError(f"未找到测试用例: {module}/{name}")
            
            module_dir = os.path.join(self.config['test']['case_dir'], module)
            for filename in os.listdir(module_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(module_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        test_case = json.load(f)
                        if test_case['name'] == name:
                            # 创建备份
                            backup_dir = os.path.join(self.config['test']['case_dir'], '_deleted')
                            os.makedirs(backup_dir, exist_ok=True)
                            backup_path = os.path.join(backup_dir, f"{module}_{filename}")
                            os.rename(file_path, backup_path)
                            
                            # 从内存中移除
                            self.test_cases[module] = [
                                case for case in self.test_cases[module]
                                if case['name'] != name
                            ]
                            
                            # 清除缓存
                            self.get_test_case.cache_clear()
                            
                            logger.info(f"测试用例已删除并备份: {backup_path}")
                            return True
            
            raise FileNotFoundError(f"未找到测试用例文件: {module}/{name}")
        
        except Exception as e:
            logger.error(f"删除测试用例失败: {e}")
            return False
    
    def get_test_cases(self, module: str = None, status: str = None) -> List[Dict]:
        """
        获取测试用例列表
        :param module: 模块名称（可选）
        :param status: 用例状态（可选）
        :return: 测试用例列表
        """
        try:
            cases = self.test_cases.get(module, []) if module else [
                case for cases in self.test_cases.values() for case in cases
            ]
            
            if status:
                cases = [case for case in cases if case.get('status') == status]
            
            return sorted(cases, key=lambda x: x['updated_at'], reverse=True)
        
        except Exception as e:
            logger.error(f"获取测试用例列表失败: {e}")
            return []
    
    def generate_test_code(self, test_case: Dict) -> str:
        """
        生成测试用例代码
        :param test_case: 测试用例信息
        :return: 生成的代码
        """
        try:
            if not self._validate_test_case(test_case):
                raise ValueError("无效的测试用例格式")
            
            code_lines = [
                "import pytest",
                "from appium import webdriver",
                "from appium.webdriver.common.appiumby import AppiumBy",
                "from selenium.webdriver.support.ui import WebDriverWait",
                "from selenium.webdriver.support import expected_conditions as EC",
                "from selenium.common.exceptions import TimeoutException",
                "import time\n",
                f"def test_{test_case['module']}_{test_case['name'].lower().replace(' ', '_')}(driver):",
                "    try:",
                "        wait = WebDriverWait(driver, 10)"
            ]
            
            # 添加测试步骤
            for i, step in enumerate(test_case['steps'], 1):
                if step['type'] == 'operation':
                    # 添加操作步骤代码
                    code_lines.extend([
                        f"        # 步骤 {i}: {step['description']}",
                        f"        try:",
                        f"            {step['code']}",
                        f"        except TimeoutException:",
                        f"            logger.error(f'步骤 {i} 超时: {step['description']}')",
                        f"            return False",
                        f"        except Exception as e:",
                        f"            logger.error(f'步骤 {i} 失败: {{e}}')",
                        f"            return False"
                    ])
                elif step['type'] == 'test_case':
                    # 添加调用其他测试用例的代码
                    code_lines.extend([
                        f"        # 步骤 {i}: 执行测试用例 {step['name']}",
                        f"        if not test_{step['module']}_{step['name'].lower().replace(' ', '_')}(driver):",
                        f"            logger.error('子用例执行失败: {step['name']}')",
                        f"            return False"
                    ])
            
            # 添加断言
            for i, assertion in enumerate(test_case['assertions'], 1):
                code_lines.extend([
                    f"        # 断言 {i}: {assertion['description']}",
                    f"        try:",
                    f"            {assertion['code']}",
                    f"        except AssertionError:",
                    f"            logger.error(f'断言 {i} 失败: {assertion['description']}')",
                    f"            return False",
                    f"        except Exception as e:",
                    f"            logger.error(f'断言 {i} 执行异常: {{e}}')",
                    f"            return False"
                ])
            
            # 添加成功返回
            code_lines.extend([
                "        logger.info('测试用例执行成功')",
                "        return True",
                "    except Exception as e:",
                "        logger.error(f'测试执行失败: {e}')",
                "        return False"
            ])
            
            return '\n'.join(['    ' + line for line in code_lines])
        
        except Exception as e:
            logger.error(f"生成测试代码失败: {e}")
            return ""
    
    def save_test_report(self, results: List[Dict]):
        """
        保存测试报告
        :param results: 测试结果列表
        """
        try:
            # 创建报告目录
            report_dir = self.config['test']['report_dir']
            os.makedirs(report_dir, exist_ok=True)
            
            # 生成报告数据
            report_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_cases': len(results),
                'passed_cases': len([r for r in results if r['status'] == 'passed']),
                'failed_cases': len([r for r in results if r['status'] == 'failed']),
                'total_duration': sum(r['duration'] for r in results),
                'results': results
            }
            
            # 生成报告文件名
            report_file = os.path.join(
                report_dir,
                f"report_{time.strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # 保存报告
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"测试报告已保存: {report_file}")
            
            # 清理旧报告（保留最近30个）
            self._clean_old_reports(report_dir, keep_count=30)
        
        except Exception as e:
            logger.error(f"保存测试报告失败: {e}")
    
    def _clean_old_reports(self, report_dir: str, keep_count: int = 30):
        """
        清理旧的测试报告
        :param report_dir: 报告目录
        :param keep_count: 保留的报告数量
        """
        try:
            reports = [
                os.path.join(report_dir, f)
                for f in os.listdir(report_dir)
                if f.startswith('report_') and f.endswith('.json')
            ]
            
            # 按修改时间排序
            reports.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # 删除旧报告
            for report in reports[keep_count:]:
                try:
                    os.remove(report)
                    logger.debug(f"已删除旧报告: {report}")
                except Exception as e:
                    logger.warning(f"删除旧报告失败 {report}: {e}")
        
        except Exception as e:
            logger.error(f"清理旧报告失败: {e}")
    
    def __del__(self):
        """
        清理资源
        """
        self._executor.shutdown(wait=True) 