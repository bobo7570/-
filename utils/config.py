"""配置管理模块。

此模块提供配置的加载、保存和验证功能。
"""

import os
from typing import Dict, Optional
from .constants import (
    ROOT_DIR, CONFIG_DIR, DEFAULT_CONFIG_FILE,
    USER_CONFIG_FILE, RECORDINGS_DIR, LOGS_DIR
)
from .errors import ConfigError
from .logger import logger

class Config:
    """配置管理类。"""

    def __init__(self, config_file: Optional[str] = None):
        """初始化配置管理器。

        Args:
            config_file: 配置文件路径，如果为None则使用默认配置文件
        """
        self.config_file = config_file or USER_CONFIG_FILE
        self.config = {}
        self.load_config()

    def load_config(self) -> None:
        """加载配置。

        如果用户配置文件不存在，则从默认配置文件加载。
        """
        try:
            # 如果用户配置文件不存在，则从默认配置文件加载
            if not os.path.exists(self.config_file):
                if not os.path.exists(DEFAULT_CONFIG_FILE):
                    raise ConfigError(f"默认配置文件不存在: {DEFAULT_CONFIG_FILE}")
                import shutil
                shutil.copy2(DEFAULT_CONFIG_FILE, self.config_file)
                logger.info(f"已创建用户配置文件: {self.config_file}")

            # 加载配置文件
            import json
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            # 验证并补充配置
            self._validate_config()
            self._supplement_config()

            logger.info("配置加载成功")

        except Exception as e:
            raise ConfigError(f"加载配置失败: {e}")

    def save_config(self) -> None:
        """保存配置。"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            # 保存配置
            import json
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

            logger.info("配置保存成功")

        except Exception as e:
            raise ConfigError(f"保存配置失败: {e}")

    def get(self, key: str, default: Optional[object] = None) -> object:
        """获取配置项。

        Args:
            key: 配置项键名，支持使用点号访问嵌套配置
            default: 默认值

        Returns:
            配置项值
        """
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: object) -> None:
        """设置配置项。

        Args:
            key: 配置项键名，支持使用点号访问嵌套配置
            value: 配置项值
        """
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def update(self, config: Dict) -> None:
        """更新配置。

        Args:
            config: 新的配置数据
        """
        def deep_update(d: Dict, u: Dict) -> Dict:
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        self.config = deep_update(self.config, config)

    def reset(self) -> None:
        """重置配置为默认值。"""
        try:
            if not os.path.exists(DEFAULT_CONFIG_FILE):
                raise ConfigError(f"默认配置文件不存在: {DEFAULT_CONFIG_FILE}")

            import json
            with open(DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            self._supplement_config()
            self.save_config()

            logger.info("配置已重置为默认值")

        except Exception as e:
            raise ConfigError(f"重置配置失败: {e}")

    def _validate_config(self) -> None:
        """验证配置的完整性和正确性。"""
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
                    raise ConfigError(f"缺少必需的配置项: {path + key}")
                if isinstance(value_type, dict):
                    if not isinstance(data[key], dict):
                        raise ConfigError(f"配置项类型错误: {path + key}")
                    validate_dict(data[key], value_type, f"{path}{key}.")
                elif not isinstance(data[key], value_type):
                    raise ConfigError(
                        f"配置项类型错误: {path + key}，"
                        f"期望类型: {value_type.__name__}，"
                        f"实际类型: {type(data[key]).__name__}"
                    )

        validate_dict(self.config, required_fields)

    def _supplement_config(self) -> None:
        """补充配置的默认值。"""
        # 设置工作目录
        if not self.config['work_dir']:
            self.config['work_dir'] = ROOT_DIR

        # 设置日志级别
        if not self.config['log_level']:
            self.config['log_level'] = 'INFO'

        # 设置录制目录
        if not self.config['record']['save_dir']:
            self.config['record']['save_dir'] = RECORDINGS_DIR

        # 设置Android SDK路径
        if not self.config['device']['android_sdk']:
            android_home = os.environ.get('ANDROID_HOME')
            if android_home:
                self.config['device']['android_sdk'] = android_home

        # 确保目录存在
        for dir_path in [
            self.config['work_dir'],
            self.config['record']['save_dir'],
            LOGS_DIR
        ]:
            os.makedirs(dir_path, exist_ok=True) 