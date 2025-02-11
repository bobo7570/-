import argparse
import os
import sys
import yaml
import time
from datetime import datetime
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from core.device_manager import DeviceManager
from core.testcase_manager import TestCaseManager
from core.assertion_manager import AssertionManager
from utils.helpers import check_environment

# 配置日志
logger.add(
    "logs/run.log",
    rotation="500 MB",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}"
)

class TestRunner:
    def __init__(self, config_path: str):
        """
        初始化测试运行器
        :param config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.device_manager = None
        self.testcase_manager = None
        self.assertion_manager = None
        self.devices = []
        self.test_cases = []
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def _load_config(self) -> Dict:
        """
        加载配置文件
        :return: 配置信息字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info("配置文件加载成功")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            sys.exit(1)
    
    def setup(self):
        """
        设置测试环境
        """
        try:
            # 检查环境
            logger.info("开始环境检查...")
            check_result = check_environment(self.config)
            if not all(check_result.values()):
                missing = [k for k, v in check_result.items() if not v]
                raise EnvironmentError(f"环境检查失败，以下组件未安装或配置不正确：{', '.join(missing)}")
            logger.info("环境检查通过")
            
            # 初始化管理器
            self.device_manager = DeviceManager(self.config)
            self.testcase_manager = TestCaseManager(self.config)
            self.assertion_manager = AssertionManager(self.config)
            
            # 获取设备列表
            self._get_devices()
            
            # 加载测试用例
            self._load_test_cases()
            
            logger.info("测试环境设置完成")
        
        except Exception as e:
            logger.error(f"环境设置失败: {e}")
            sys.exit(1)
    
    def _get_devices(self):
        """
        获取可用设备列表
        """
        try:
            logger.info("开始检测设备...")
            self.devices = self.device_manager.get_devices()
            
            if not self.devices:
                raise DeviceError("未检测到可用设备")
            
            logger.info(f"检测到 {len(self.devices)} 个设备")
            for device in self.devices:
                logger.info(f"设备信息: {device}")
        
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            raise
    
    def _load_test_cases(self):
        """
        加载测试用例
        """
        try:
            logger.info("开始加载测试用例...")
            self.test_cases = self.testcase_manager.get_test_cases()
            
            if not self.test_cases:
                raise TestCaseError("未找到可用的测试用例")
            
            logger.info(f"加载了 {len(self.test_cases)} 个测试用例")
            for case in self.test_cases:
                logger.info(f"测试用例: {case['name']} ({case['module']})")
        
        except Exception as e:
            logger.error(f"加载测试用例失败: {e}")
            raise
    
    def run_test(self, device: Dict, test_case: Dict) -> Dict:
        """
        在指定设备上运行测试用例
        :param device: 设备信息
        :param test_case: 测试用例信息
        :return: 测试结果
        """
        result = {
            'device_id': device['id'],
            'test_case': test_case['name'],
            'module': test_case['module'],
            'status': 'failed',
            'start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': None,
            'duration': 0,
            'error': None
        }
        
        try:
            logger.info(f"在设备 {device['id']} 上运行测试用例 {test_case['name']}")
            start_time = time.time()
            
            # 执行测试用例
            exec(self.testcase_manager.generate_test_code(test_case))
            test_func = locals()[f"test_{test_case['module']}_{test_case['name'].lower().replace(' ', '_')}"]
            
            # 运行测试
            success = test_func(self.device_manager.driver)
            
            # 更新结果
            end_time = time.time()
            result.update({
                'status': 'passed' if success else 'failed',
                'end_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': round(end_time - start_time, 2)
            })
            
            logger.info(f"测试用例 {test_case['name']} 执行{'成功' if success else '失败'}")
            return result
        
        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            result.update({
                'status': 'error',
                'end_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            })
            return result
    
    def run(self):
        """
        运行测试
        """
        try:
            self.start_time = datetime.now()
            logger.info(f"开始测试执行，时间: {self.start_time}")
            
            # 设置线程池
            max_workers = min(
                self.config.get('max_concurrent_devices', 1),
                len(self.devices)
            )
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 创建测试任务
                future_to_test = {
                    executor.submit(self.run_test, device, test_case): (device, test_case)
                    for device in self.devices
                    for test_case in self.test_cases
                }
                
                # 收集结果
                for future in as_completed(future_to_test):
                    device, test_case = future_to_test[future]
                    try:
                        result = future.result()
                        self.results.append(result)
                    except Exception as e:
                        logger.error(f"测试任务失败: {e}")
                        self.results.append({
                            'device_id': device['id'],
                            'test_case': test_case['name'],
                            'module': test_case['module'],
                            'status': 'error',
                            'error': str(e)
                        })
            
            self.end_time = datetime.now()
            logger.info(f"测试执行完成，时间: {self.end_time}")
            
            # 生成报告
            self.generate_report()
        
        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            raise
    
    def generate_report(self):
        """
        生成测试报告
        """
        try:
            logger.info("开始生成测试报告...")
            
            # 统计结果
            total_cases = len(self.results)
            passed_cases = len([r for r in self.results if r['status'] == 'passed'])
            failed_cases = len([r for r in self.results if r['status'] == 'failed'])
            error_cases = len([r for r in self.results if r['status'] == 'error'])
            
            # 计算总执行时间
            total_duration = sum(r.get('duration', 0) for r in self.results)
            
            # 准备报告数据
            report_data = {
                'summary': {
                    'total_cases': total_cases,
                    'passed_cases': passed_cases,
                    'failed_cases': failed_cases,
                    'error_cases': error_cases,
                    'pass_rate': f"{(passed_cases / total_cases * 100):.2f}%",
                    'total_duration': total_duration,
                    'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': str(self.end_time - self.start_time)
                },
                'environment': {
                    'devices': [
                        {
                            'id': device['id'],
                            'platform': device['platform'],
                            'version': device['platform_version'],
                            'model': device.get('model', 'Unknown')
                        }
                        for device in self.devices
                    ],
                    'config': self.config
                },
                'results': self.results
            }
            
            # 保存报告
            report_dir = self.config['test']['report_dir']
            os.makedirs(report_dir, exist_ok=True)
            
            report_file = os.path.join(
                report_dir,
                f"report_{time.strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(report_file, 'w', encoding='utf-8') as f:
                yaml.dump(report_data, f, allow_unicode=True, indent=2)
            
            logger.info(f"测试报告已生成: {report_file}")
            
            # 打印摘要
            logger.info("\n测试执行摘要:")
            logger.info(f"总用例数: {total_cases}")
            logger.info(f"通过用例: {passed_cases}")
            logger.info(f"失败用例: {failed_cases}")
            logger.info(f"错误用例: {error_cases}")
            logger.info(f"通过率: {report_data['summary']['pass_rate']}")
            logger.info(f"总执行时间: {report_data['summary']['duration']}")
        
        except Exception as e:
            logger.error(f"生成测试报告失败: {e}")
            raise

class DeviceError(Exception):
    """设备相关错误"""
    pass

class TestCaseError(Exception):
    """测试用例相关错误"""
    pass

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='App自动化测试命令行工具')
    parser.add_argument('--config', type=str, required=True, help='配置文件路径')
    parser.add_argument('--module', type=str, help='指定要测试的模块')
    parser.add_argument('--case', type=str, help='指定要测试的用例名称')
    parser.add_argument('--device', type=str, help='指定要使用的设备ID')
    parser.add_argument('--parallel', type=int, help='并行执行的设备数量')
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = TestRunner(args.config)
    
    try:
        # 设置环境
        runner.setup()
        
        # 根据参数过滤测试用例
        if args.module:
            runner.test_cases = [
                case for case in runner.test_cases
                if case['module'] == args.module
            ]
        if args.case:
            runner.test_cases = [
                case for case in runner.test_cases
                if case['name'] == args.case
            ]
        
        # 根据参数过滤设备
        if args.device:
            runner.devices = [
                device for device in runner.devices
                if device['id'] == args.device
            ]
        
        # 设置并行数量
        if args.parallel:
            runner.config['max_concurrent_devices'] = args.parallel
        
        # 运行测试
        runner.run()
        
        # 根据测试结果设置退出码
        if any(r['status'] in ['failed', 'error'] for r in runner.results):
            sys.exit(1)
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.warning("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 