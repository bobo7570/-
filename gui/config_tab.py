from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QFileDialog, QScrollArea, QFormLayout,
    QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor
from loguru import logger
import json
import os

class ConfigTab(QWidget):
    # 定义信号
    config_changed = Signal(dict)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setObjectName("config_tab")
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 创建配置选项卡
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background: white;
                padding: 10px;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dcdcdc;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background: #e9ecef;
            }
        """)
        
        # 基本设置
        basic_tab = self._create_basic_tab()
        tab_widget.addTab(basic_tab, "基本设置")
        
        # 设备设置
        device_tab = self._create_device_tab()
        tab_widget.addTab(device_tab, "设备设置")
        
        # 录制设置
        record_tab = self._create_record_tab()
        tab_widget.addTab(record_tab, "录制设置")
        
        # 高级设置
        advanced_tab = self._create_advanced_tab()
        tab_widget.addTab(advanced_tab, "高级设置")
        
        main_layout.addWidget(tab_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        save_btn.clicked.connect(self.save_config)
        
        # 重置按钮
        reset_btn = QPushButton("重置设置")
        reset_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
        """)
        reset_btn.clicked.connect(self.reset_config)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 加载配置
        self.load_config()
    
    def _create_basic_tab(self):
        """创建基本设置选项卡"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # 工作目录
        self.work_dir_edit = QLineEdit()
        self.work_dir_edit.setReadOnly(True)
        self.work_dir_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        
        work_dir_layout = QHBoxLayout()
        work_dir_layout.addWidget(self.work_dir_edit)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        browse_btn.clicked.connect(self.browse_work_dir)
        work_dir_layout.addWidget(browse_btn)
        
        layout.addRow("工作目录:", work_dir_layout)
        
        # 日志级别
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
        """)
        layout.addRow("日志级别:", self.log_level_combo)
        
        # 自动保存
        self.auto_save_check = QCheckBox()
        self.auto_save_check.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #dcdcdc;
                background: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addRow("自动保存:", self.auto_save_check)
        
        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色", "跟随系统"])
        self.theme_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
        """)
        layout.addRow("主题:", self.theme_combo)
        
        widget.setLayout(layout)
        return widget
    
    def _create_device_tab(self):
        """创建设备设置选项卡"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # Android SDK路径
        self.android_sdk_edit = QLineEdit()
        self.android_sdk_edit.setReadOnly(True)
        self.android_sdk_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        
        android_sdk_layout = QHBoxLayout()
        android_sdk_layout.addWidget(self.android_sdk_edit)
        
        browse_android_btn = QPushButton("浏览")
        browse_android_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        browse_android_btn.clicked.connect(lambda: self.browse_path(self.android_sdk_edit))
        android_sdk_layout.addWidget(browse_android_btn)
        
        layout.addRow("Android SDK路径:", android_sdk_layout)
        
        # iOS开发者证书
        self.ios_cert_edit = QLineEdit()
        self.ios_cert_edit.setReadOnly(True)
        self.ios_cert_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        
        ios_cert_layout = QHBoxLayout()
        ios_cert_layout.addWidget(self.ios_cert_edit)
        
        browse_ios_btn = QPushButton("浏览")
        browse_ios_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        browse_ios_btn.clicked.connect(lambda: self.browse_path(self.ios_cert_edit))
        ios_cert_layout.addWidget(browse_ios_btn)
        
        layout.addRow("iOS开发者证书:", ios_cert_layout)
        
        # 设备超时时间
        self.device_timeout_spin = QSpinBox()
        self.device_timeout_spin.setRange(5, 300)
        self.device_timeout_spin.setSuffix(" 秒")
        self.device_timeout_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QSpinBox:hover {
                border-color: #4CAF50;
            }
        """)
        layout.addRow("设备超时时间:", self.device_timeout_spin)
        
        # 自动重连
        self.auto_reconnect_check = QCheckBox()
        self.auto_reconnect_check.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #dcdcdc;
                background: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addRow("自动重连:", self.auto_reconnect_check)
        
        widget.setLayout(layout)
        return widget
    
    def _create_record_tab(self):
        """创建录制设置选项卡"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # 录制间隔
        self.record_interval_spin = QSpinBox()
        self.record_interval_spin.setRange(1, 60)
        self.record_interval_spin.setSuffix(" 秒")
        self.record_interval_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QSpinBox:hover {
                border-color: #4CAF50;
            }
        """)
        layout.addRow("录制间隔:", self.record_interval_spin)
        
        # 录制模式
        self.record_mode_combo = QComboBox()
        self.record_mode_combo.addItems(["完整模式", "简单模式"])
        self.record_mode_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
        """)
        layout.addRow("录制模式:", self.record_mode_combo)
        
        # 保存目录
        self.save_dir_edit = QLineEdit()
        self.save_dir_edit.setReadOnly(True)
        self.save_dir_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: #f8f9fa;
            }
        """)
        
        save_dir_layout = QHBoxLayout()
        save_dir_layout.addWidget(self.save_dir_edit)
        
        browse_save_btn = QPushButton("浏览")
        browse_save_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        browse_save_btn.clicked.connect(lambda: self.browse_path(self.save_dir_edit, True))
        save_dir_layout.addWidget(browse_save_btn)
        
        layout.addRow("保存目录:", save_dir_layout)
        
        # 自动保存
        self.record_auto_save_check = QCheckBox()
        self.record_auto_save_check.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #dcdcdc;
                background: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addRow("自动保存:", self.record_auto_save_check)
        
        widget.setLayout(layout)
        return widget
    
    def _create_advanced_tab(self):
        """创建高级设置选项卡"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # Appium设置
        appium_group = QFrame()
        appium_group.setStyleSheet("""
            QFrame {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 10px;
                background: white;
            }
        """)
        appium_layout = QFormLayout()
        
        # Appium主机
        self.appium_host_edit = QLineEdit()
        self.appium_host_edit.setPlaceholderText("127.0.0.1")
        self.appium_host_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QLineEdit:hover {
                border-color: #4CAF50;
            }
        """)
        appium_layout.addRow("主机:", self.appium_host_edit)
        
        # Appium端口
        self.appium_port_spin = QSpinBox()
        self.appium_port_spin.setRange(1024, 65535)
        self.appium_port_spin.setValue(4723)
        self.appium_port_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QSpinBox:hover {
                border-color: #4CAF50;
            }
        """)
        appium_layout.addRow("端口:", self.appium_port_spin)
        
        appium_group.setLayout(appium_layout)
        layout.addRow("Appium服务器:", appium_group)
        
        # 代理设置
        proxy_group = QFrame()
        proxy_group.setStyleSheet("""
            QFrame {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                padding: 10px;
                background: white;
            }
        """)
        proxy_layout = QFormLayout()
        
        # 启用代理
        self.enable_proxy_check = QCheckBox()
        self.enable_proxy_check.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #dcdcdc;
                background: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        proxy_layout.addRow("启用代理:", self.enable_proxy_check)
        
        # 代理主机
        self.proxy_host_edit = QLineEdit()
        self.proxy_host_edit.setPlaceholderText("127.0.0.1")
        self.proxy_host_edit.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QLineEdit:hover {
                border-color: #4CAF50;
            }
        """)
        proxy_layout.addRow("主机:", self.proxy_host_edit)
        
        # 代理端口
        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setRange(1024, 65535)
        self.proxy_port_spin.setValue(8888)
        self.proxy_port_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QSpinBox:hover {
                border-color: #4CAF50;
            }
        """)
        proxy_layout.addRow("端口:", self.proxy_port_spin)
        
        proxy_group.setLayout(proxy_layout)
        layout.addRow("代理设置:", proxy_group)
        
        widget.setLayout(layout)
        return widget
    
    def browse_work_dir(self):
        """浏览工作目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择工作目录",
            self.work_dir_edit.text() or os.getcwd()
        )
        if dir_path:
            self.work_dir_edit.setText(dir_path)
    
    def browse_path(self, line_edit, is_dir=False):
        """浏览文件/目录路径"""
        if is_dir:
            path = QFileDialog.getExistingDirectory(
                self,
                "选择目录",
                line_edit.text() or os.getcwd()
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "选择文件",
                line_edit.text() or os.getcwd()
            )
        
        if path:
            line_edit.setText(path)
    
    def load_config(self):
        """加载配置"""
        try:
            # 基本设置
            self.work_dir_edit.setText(self.config.get('work_dir', os.getcwd()))
            self.log_level_combo.setCurrentText(self.config.get('log_level', 'INFO'))
            self.auto_save_check.setChecked(self.config.get('auto_save', False))
            self.theme_combo.setCurrentText(self.config.get('theme', '浅色'))
            
            # 设备设置
            device_config = self.config.get('device', {})
            self.android_sdk_edit.setText(device_config.get('android_sdk', ''))
            self.ios_cert_edit.setText(device_config.get('ios_cert', ''))
            self.device_timeout_spin.setValue(device_config.get('timeout', 30))
            self.auto_reconnect_check.setChecked(device_config.get('auto_reconnect', True))
            
            # 录制设置
            record_config = self.config.get('record', {})
            self.record_interval_spin.setValue(record_config.get('interval', 2))
            self.record_mode_combo.setCurrentText(record_config.get('mode', '完整模式'))
            self.save_dir_edit.setText(record_config.get('save_dir', os.path.join(os.getcwd(), 'recordings')))
            self.record_auto_save_check.setChecked(record_config.get('auto_save', False))
            
            # 高级设置
            advanced_config = self.config.get('advanced', {})
            # Appium设置
            appium_config = advanced_config.get('appium', {})
            self.appium_host_edit.setText(appium_config.get('host', '127.0.0.1'))
            self.appium_port_spin.setValue(appium_config.get('port', 4723))
            # 代理设置
            proxy_config = advanced_config.get('proxy', {})
            self.enable_proxy_check.setChecked(proxy_config.get('enabled', False))
            self.proxy_host_edit.setText(proxy_config.get('host', '127.0.0.1'))
            self.proxy_port_spin.setValue(proxy_config.get('port', 8888))
            
            logger.info("配置加载成功")
        
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            QMessageBox.critical(self, "错误", f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        try:
            # 基本设置
            self.config['work_dir'] = self.work_dir_edit.text()
            self.config['log_level'] = self.log_level_combo.currentText()
            self.config['auto_save'] = self.auto_save_check.isChecked()
            self.config['theme'] = self.theme_combo.currentText()
            
            # 设备设置
            self.config['device'] = {
                'android_sdk': self.android_sdk_edit.text(),
                'ios_cert': self.ios_cert_edit.text(),
                'timeout': self.device_timeout_spin.value(),
                'auto_reconnect': self.auto_reconnect_check.isChecked()
            }
            
            # 录制设置
            self.config['record'] = {
                'interval': self.record_interval_spin.value(),
                'mode': self.record_mode_combo.currentText(),
                'save_dir': self.save_dir_edit.text(),
                'auto_save': self.record_auto_save_check.isChecked()
            }
            
            # 高级设置
            self.config['advanced'] = {
                'appium': {
                    'host': self.appium_host_edit.text(),
                    'port': self.appium_port_spin.value()
                },
                'proxy': {
                    'enabled': self.enable_proxy_check.isChecked(),
                    'host': self.proxy_host_edit.text(),
                    'port': self.proxy_port_spin.value()
                }
            }
            
            # 保存到文件
            config_file = os.path.join(os.getcwd(), 'config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            logger.info("配置保存成功")
            QMessageBox.information(self, "成功", "配置已保存")
            
            # 发送配置更改信号
            self.config_changed.emit(self.config)
        
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
    
    def reset_config(self):
        """重置配置"""
        try:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要重置所有设置吗？\n此操作将恢复默认设置且无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 恢复默认配置
                self.config = {
                    'work_dir': os.getcwd(),
                    'log_level': 'INFO',
                    'auto_save': False,
                    'theme': '浅色',
                    'device': {
                        'android_sdk': '',
                        'ios_cert': '',
                        'timeout': 30,
                        'auto_reconnect': True
                    },
                    'record': {
                        'interval': 2,
                        'mode': '完整模式',
                        'save_dir': os.path.join(os.getcwd(), 'recordings'),
                        'auto_save': False
                    },
                    'advanced': {
                        'appium': {
                            'host': '127.0.0.1',
                            'port': 4723
                        },
                        'proxy': {
                            'enabled': False,
                            'host': '127.0.0.1',
                            'port': 8888
                        }
                    }
                }
                
                # 重新加载配置
                self.load_config()
                
                logger.info("配置已重置")
                QMessageBox.information(self, "成功", "设置已重置为默认值")
                
                # 发送配置更改信号
                self.config_changed.emit(self.config)
        
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            QMessageBox.critical(self, "错误", f"重置配置失败: {str(e)}") 