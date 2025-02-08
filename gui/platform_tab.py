from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from loguru import logger

class PlatformTab(QWidget):
    # 定义信号
    platform_changed = Signal(str)  # 平台切换信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_platform = "android"  # 默认平台
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
    
    def on_platform_changed(self, platform: str):
        """
        平台选择改变时的处理
        :param platform: 选择的平台名称
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
        """
        更新平台信息显示
        """
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