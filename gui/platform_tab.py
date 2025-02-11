from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from loguru import logger
from utils.helpers import check_environment

class PlatformTab(QWidget):
    # 定义信号
    platform_changed = Signal(str)  # 平台切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_platform = "android"  # 默认平台
        self.env_status = {}  # 环境状态字典
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 创建平台选择区域
        platform_frame = QFrame()
        platform_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        platform_layout = QVBoxLayout()
        
        # 添加标题
        title_label = QLabel("平台选择")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding: 10px;
            }
        """)
        platform_layout.addWidget(title_label)
        
        # 创建平台选择组件
        platform_select_layout = QHBoxLayout()
        
        # 平台选择下拉框
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Android", "iOS"])
        self.platform_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid #999999;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        self.platform_combo.currentTextChanged.connect(self.on_platform_changed)
        
        # 添加到水平布局
        platform_select_layout.addWidget(QLabel("选择平台:"))
        platform_select_layout.addWidget(self.platform_combo)
        platform_select_layout.addStretch()
        
        # 添加到平台框架布局
        platform_layout.addLayout(platform_select_layout)
        platform_frame.setLayout(platform_layout)
        
        # 添加平台信息显示区域
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QVBoxLayout()
        
        # 添加信息标题
        info_title = QLabel("平台信息")
        info_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding: 10px;
            }
        """)
        info_layout.addWidget(info_title)
        
        # 平台信息标签
        self.platform_info = QLabel()
        self.platform_info.setWordWrap(True)
        self.platform_info.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 3px;
                line-height: 1.5;
            }
        """)
        info_layout.addWidget(self.platform_info)
        
        # 添加环境检测按钮
        check_env_btn = QPushButton("检测自动化环境")
        check_env_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        check_env_btn.clicked.connect(self.check_environment)
        info_layout.addWidget(check_env_btn)
        
        # 添加环境状态显示区域
        env_status_frame = QFrame()
        env_status_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                margin-top: 10px;
            }
        """)
        env_status_layout = QVBoxLayout()
        
        # 创建环境状态标签
        self.status_labels = {}
        for component in ['Node.js', 'npm', 'Appium', 'adb', 'ANDROID_HOME', 'JAVA_HOME']:
            status_layout = QHBoxLayout()
            
            # 组件名称
            name_label = QLabel(component)
            name_label.setMinimumWidth(120)
            name_label.setStyleSheet("font-weight: bold;")
            status_layout.addWidget(name_label)
            
            # 状态图标
            status_label = QLabel()
            status_label.setStyleSheet("""
                QLabel {
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """)
            self.status_labels[component] = status_label
            status_layout.addWidget(status_label)
            
            status_layout.addStretch()
            env_status_layout.addLayout(status_layout)
        
        env_status_frame.setLayout(env_status_layout)
        info_layout.addWidget(env_status_frame)
        
        # 设置信息框架布局
        info_frame.setLayout(info_layout)
        
        # 添加到主布局
        main_layout.addWidget(platform_frame)
        main_layout.addWidget(info_frame)
        main_layout.addStretch()
        
        # 设置主布局
        self.setLayout(main_layout)
        
        # 更新平台信息显示
        self.update_platform_info()
        
        # 初始化环境状态显示
        self.update_env_status({})
    
    def update_env_status(self, missing_components: list):
        """更新环境状态显示
        
        Args:
            missing_components: 缺失的组件列表
        """
        for component, label in self.status_labels.items():
            if component in missing_components:
                label.setText("未安装")
                label.setStyleSheet("""
                    QLabel {
                        color: white;
                        background-color: #F44336;
                        padding: 2px 5px;
                        border-radius: 3px;
                    }
                """)
            else:
                label.setText("已安装")
                label.setStyleSheet("""
                    QLabel {
                        color: white;
                        background-color: #4CAF50;
                        padding: 2px 5px;
                        border-radius: 3px;
                    }
                """)
    
    def check_environment(self):
        """检测自动化环境"""
        try:
            # 检查环境
            missing_components = check_environment()
            
            # 更新状态显示
            self.update_env_status(missing_components)
            
            if not missing_components:
                QMessageBox.information(
                    self,
                    "环境检测",
                    "自动化环境检测通过！\n\n所有必需组件都已正确安装。"
                )
            else:
                QMessageBox.warning(
                    self,
                    "环境检测",
                    f"以下组件未安装或配置不正确：\n\n{', '.join(missing_components)}\n\n请检查环境配置。"
                )
            
            logger.info(f"环境检测完成，缺失组件: {missing_components if missing_components else '无'}")
            
        except Exception as e:
            logger.error(f"环境检测失败: {e}")
            QMessageBox.critical(
                self,
                "错误",
                f"环境检测失败: {str(e)}"
            )
    
    def on_platform_changed(self, platform: str):
        """平台选择改变时的处理
        
        Args:
            platform: 选择的平台名称
        """
        try:
            # 更新当前平台
            new_platform = platform.lower()
            if new_platform != self.current_platform:
                self.current_platform = new_platform
                # 发送平台切换信号
                self.platform_changed.emit(new_platform)
                # 更新平台信息显示
                self.update_platform_info()
                logger.info(f"已切换到 {platform} 平台")
        except Exception as e:
            logger.error(f"切换平台失败: {e}")
            QMessageBox.critical(
                self,
                "错误",
                f"切换平台失败: {str(e)}"
            )
    
    def update_platform_info(self):
        """更新平台信息显示"""
        if self.current_platform == "android":
            info_text = """
                <b>Android 平台信息：</b><br>
                • 支持的自动化框架：UiAutomator2<br>
                • 设备连接方式：USB/WiFi (adb)<br>
                • 所需环境：
                  - Android SDK
                  - adb 工具
                  - Appium Server
                • 支持功能：
                  - 设备检测和管理
                  - 应用安装和启动
                  - 界面操作录制
                  - 元素定位和操作
                  - 断言验证
            """
        else:  # iOS
            info_text = """
                <b>iOS 平台信息：</b><br>
                • 支持的自动化框架：XCUITest<br>
                • 设备连接方式：USB (tidevice)<br>
                • 所需环境：
                  - tidevice 工具
                  - Appium Server
                  - iOS 开发者证书
                • 支持功能：
                  - 设备检测和管理
                  - 应用安装和启动
                  - 界面操作录制
                  - 元素定位和操作
                  - 断言验证
            """
        
        self.platform_info.setText(info_text.strip()) 