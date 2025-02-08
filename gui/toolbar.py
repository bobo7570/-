from PySide6.QtWidgets import (
    QToolBar, QAction, QLabel, QComboBox,
    QWidget, QHBoxLayout, QSpacerItem,
    QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon
from loguru import logger
import os

class Toolbar(QToolBar):
    # 定义信号
    platform_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("main_toolbar")
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 设置工具栏样式
        self.setStyleSheet("""
            QToolBar {
                background: #f8f9fa;
                border: none;
                border-bottom: 1px solid #dcdcdc;
                padding: 5px;
            }
            QToolBar::separator {
                width: 1px;
                background: #dcdcdc;
                margin: 5px;
            }
        """)
        
        # 设置图标大小
        self.setIconSize(QSize(24, 24))
        
        # 添加平台选择
        platform_widget = QWidget()
        platform_layout = QHBoxLayout()
        platform_layout.setContentsMargins(0, 0, 0, 0)
        platform_layout.setSpacing(5)
        
        platform_label = QLabel("平台:")
        platform_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-weight: bold;
            }
        """)
        platform_layout.addWidget(platform_label)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Android", "iOS"])
        self.platform_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(resources/icons/down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        self.platform_combo.currentTextChanged.connect(self._on_platform_changed)
        platform_layout.addWidget(self.platform_combo)
        
        platform_widget.setLayout(platform_layout)
        self.addWidget(platform_widget)
        
        # 添加分隔符
        self.addSeparator()
        
        # 添加刷新按钮
        refresh_action = QAction(QIcon("resources/icons/refresh.png"), "刷新", self)
        refresh_action.setStatusTip("刷新设备列表")
        refresh_action.triggered.connect(self._on_refresh)
        self.addAction(refresh_action)
        
        # 添加设置按钮
        settings_action = QAction(QIcon("resources/icons/settings.png"), "设置", self)
        settings_action.setStatusTip("打开设置")
        settings_action.triggered.connect(self._on_settings)
        self.addAction(settings_action)
        
        # 添加帮助按钮
        help_action = QAction(QIcon("resources/icons/help.png"), "帮助", self)
        help_action.setStatusTip("查看帮助")
        help_action.triggered.connect(self._on_help)
        self.addAction(help_action)
        
        # 添加关于按钮
        about_action = QAction(QIcon("resources/icons/about.png"), "关于", self)
        about_action.setStatusTip("关于软件")
        about_action.triggered.connect(self._on_about)
        self.addAction(about_action)
        
        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addWidget(spacer)
    
    def _on_platform_changed(self, platform: str):
        """平台切换处理"""
        try:
            # 发送平台切换信号
            self.platform_changed.emit(platform.lower())
            logger.info(f"平台切换为: {platform}")
        except Exception as e:
            logger.error(f"平台切换失败: {e}")
            QMessageBox.critical(self, "错误", f"平台切换失败: {str(e)}")
    
    def _on_refresh(self):
        """刷新按钮处理"""
        try:
            # 触发主窗口的刷新方法
            self.parent().refresh_devices()
            logger.info("手动刷新设备列表")
        except Exception as e:
            logger.error(f"刷新失败: {e}")
            QMessageBox.critical(self, "错误", f"刷新失败: {str(e)}")
    
    def _on_settings(self):
        """设置按钮处理"""
        try:
            # 打开设置对话框
            self.parent().show_settings()
            logger.info("打开设置对话框")
        except Exception as e:
            logger.error(f"打开设置失败: {e}")
            QMessageBox.critical(self, "错误", f"打开设置失败: {str(e)}")
    
    def _on_help(self):
        """帮助按钮处理"""
        try:
            # 显示帮助信息
            help_text = """
            <h3>使用帮助</h3>
            <p><b>基本操作：</b></p>
            <ul>
                <li>选择平台（Android/iOS）</li>
                <li>连接设备</li>
                <li>开始录制</li>
                <li>停止录制</li>
                <li>保存录制结果</li>
            </ul>
            <p><b>快捷键：</b></p>
            <ul>
                <li>Ctrl+R：刷新设备列表</li>
                <li>Ctrl+S：保存录制结果</li>
                <li>Ctrl+Q：退出程序</li>
            </ul>
            <p><b>注意事项：</b></p>
            <ul>
                <li>请确保已正确安装Appium和相关驱动</li>
                <li>Android设备需要开启USB调试</li>
                <li>iOS设备需要正确配置开发者证书</li>
            </ul>
            """
            
            QMessageBox.information(self, "使用帮助", help_text)
            logger.info("显示帮助信息")
        except Exception as e:
            logger.error(f"显示帮助失败: {e}")
            QMessageBox.critical(self, "错误", f"显示帮助失败: {str(e)}")
    
    def _on_about(self):
        """关于按钮处理"""
        try:
            # 显示关于信息
            about_text = """
            <h3>App自动化工具</h3>
            <p>版本：1.0.0</p>
            <p>一个基于Appium的移动应用自动化测试工具，支持：</p>
            <ul>
                <li>Android/iOS设备管理</li>
                <li>操作录制和回放</li>
                <li>测试用例生成</li>
                <li>批量执行测试</li>
            </ul>
            <p>作者：Your Name</p>
            <p>Copyright © 2024</p>
            """
            
            QMessageBox.about(self, "关于", about_text)
            logger.info("显示关于信息")
        except Exception as e:
            logger.error(f"显示关于信息失败: {e}")
            QMessageBox.critical(self, "错误", f"显示关于信息失败: {str(e)}")
    
    def set_platform(self, platform: str):
        """设置当前平台"""
        try:
            index = self.platform_combo.findText(platform.capitalize())
            if index >= 0:
                self.platform_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"设置平台失败: {e}")
            QMessageBox.critical(self, "错误", f"设置平台失败: {str(e)}") 