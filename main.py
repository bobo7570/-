import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QSplashScreen, QProgressBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QIcon
from loguru import logger
from utils.helpers import load_config, check_environment
from gui import (
    PlatformTab,
    DeviceTab,
    RecordTab,
    AssertTab,
    TestCaseTab,
    ReportTab
)

# 配置日志
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}"
)

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.current_device = None
        self.init_ui()
        self.init_tabs()
        self.connect_signals()
        
    def connect_signals(self):
        """连接所有信号"""
        try:
            # 连接设备选择信号
            self.device_tab.device_selected.connect(self.on_device_selected)
            logger.info("设备选择信号已连接到主窗口")
            
            # 连接平台切换信号
            self.platform_tab.platform_changed.connect(self.device_tab.set_platform)
            logger.info("平台切换信号已连接")
            
            # 连接标签页切换信号
            self.tabs.currentChanged.connect(self.on_tab_changed)
            logger.info("标签页切换信号已连接")
            
        except Exception as e:
            logger.error(f"连接信号失败: {e}")
            QMessageBox.critical(self, "错误", f"连接信号失败: {e}")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('App自动化工具')
        self.setMinimumSize(800, 600)
        
        # 设置应用图标
        self.setWindowIcon(QIcon('resources/icon.png'))
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 设置样式
        self.set_style()
        
        # 设置自动保存定时器
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(300000)  # 每5分钟自动保存
        
        # 记录最后活动时间
        self.last_activity = None
        self.update_activity_time()
    
    def init_tabs(self):
        """初始化所有选项卡"""
        try:
            # 创建平台切换选项卡
            self.platform_tab = PlatformTab()
            self.tabs.addTab(self.platform_tab, "平台切换")
            
            # 创建设备管理选项卡
            self.device_tab = DeviceTab(self.config)
            self.tabs.addTab(self.device_tab, "设备管理")
            
            # 创建操作录制选项卡
            self.record_tab = RecordTab(self.config)
            self.tabs.addTab(self.record_tab, "操作录制")
            
            # 创建断言管理选项卡
            self.assert_tab = AssertTab(self.config)
            self.tabs.addTab(self.assert_tab, "断言管理")
            
            # 创建用例管理选项卡
            self.testcase_tab = TestCaseTab(self.config)
            self.tabs.addTab(self.testcase_tab, "用例管理")
            
            # 创建测试报告选项卡
            self.report_tab = ReportTab(self.config)
            self.tabs.addTab(self.report_tab, "测试报告")
            
            logger.info("所有选项卡初始化完成")
        
        except Exception as e:
            logger.error(f"初始化选项卡失败: {e}")
            QMessageBox.critical(self, "错误", f"初始化选项卡失败: {e}")
    
    def set_style(self):
        """设置全局样式"""
        try:
            style_file = os.path.join('resources', 'style.qss')
            if os.path.exists(style_file):
                with open(style_file, 'r', encoding='utf-8') as f:
                    style = f.read()
                    self.setStyleSheet(style)
                    logger.info("样式设置完成")
            else:
                logger.warning("样式文件不存在，使用默认样式")
        except Exception as e:
            logger.error(f"设置样式失败: {e}")
    
    def on_device_selected(self, device_info: dict):
        """
        处理设备选择事件
        :param device_info: 设备信息
        """
        try:
            logger.debug(f"主窗口收到设备选择信号，设备信息: {device_info}")
            
            # 保存当前设备信息
            self.current_device = device_info.copy()
            logger.debug("已保存当前设备信息")
            
            # 更新各个选项卡的设备信息
            logger.debug("开始更新各选项卡的设备信息")
            
            try:
                logger.debug("更新录制标签页")
                self.record_tab.set_device(device_info)
            except Exception as e:
                logger.error(f"更新录制标签页失败: {e}")
            
            try:
                logger.debug("更新断言标签页")
                self.assert_tab.set_device(device_info)
            except Exception as e:
                logger.error(f"更新断言标签页失败: {e}")
            
            try:
                logger.debug("更新测试用例标签页")
                self.testcase_tab.set_device(device_info)
            except Exception as e:
                logger.error(f"更新测试用例标签页失败: {e}")
            
            logger.info(f"设备信息更新完成: {device_info}")
        
        except Exception as e:
            logger.error(f"处理设备选择事件失败: {e}")
            QMessageBox.warning(
                self,
                "警告",
                f"设置设备信息失败: {e}",
                QMessageBox.StandardButton.Ok
            )
    
    def on_tab_changed(self, index: int):
        """
        处理选项卡切换事件
        :param index: 选项卡索引
        """
        try:
            current_tab = self.tabs.widget(index)
            if hasattr(current_tab, 'refresh'):
                current_tab.refresh()
            
            self.update_activity_time()
            
            logger.debug(f"切换到选项卡: {self.tabs.tabText(index)}")
        
        except Exception as e:
            logger.error(f"切换选项卡失败: {e}")
    
    def update_activity_time(self):
        """更新最后活动时间"""
        from datetime import datetime
        self.last_activity = datetime.now()
    
    def auto_save(self):
        """自动保存数据"""
        try:
            # 保存各个选项卡的数据
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if hasattr(tab, 'save_data'):
                    tab.save_data()
            
            logger.debug("自动保存完成")
        
        except Exception as e:
            logger.error(f"自动保存失败: {e}")
    
    def closeEvent(self, event):
        """
        处理窗口关闭事件
        :param event: 关闭事件
        """
        try:
            reply = QMessageBox.question(
                self,
                '确认退出',
                "是否要退出程序？\n未保存的数据可能会丢失。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 保存所有数据
                self.auto_save()
                event.accept()
            else:
                event.ignore()
        
        except Exception as e:
            logger.error(f"处理关闭事件失败: {e}")
            event.accept()

def show_splash_screen():
    """显示启动画面"""
    try:
        splash_pix = QPixmap('resources/splash.png')
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        
        # 添加进度条
        progress = QProgressBar(splash)
        progress.setGeometry(splash.width() * 0.1, splash.height() - 30,
                           splash.width() * 0.8, 20)
        progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                width: 10px;
                margin: 0.5px;
            }
        """)
        
        splash.show()
        
        return splash, progress
    
    except Exception as e:
        logger.error(f"显示启动画面失败: {e}")
        return None, None

def main():
    try:
        # 创建应用程序实例
        app = QApplication(sys.argv)
        
        # 加载配置
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
            config = load_config(config_path)
            logger.info("配置加载成功")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            QMessageBox.critical(None, "错误", f"加载配置失败: {e}")
            return
        
        # 设置应用程序样式
        app.setStyle('Fusion')
        
        # 显示启动画面
        splash, progress = show_splash_screen()
        if splash and progress:
            # 模拟加载过程
            for i in range(1, 101):
                progress.setValue(i)
                app.processEvents()
                QTimer.singleShot(20, lambda: None)
        
        # 创建主窗口
        window = MainWindow(config)
        
        # 关闭启动画面
        if splash:
            splash.finish(window)
        
        # 显示主窗口
        window.show()
        
        # 运行应用程序
        sys.exit(app.exec())
    
    except Exception as e:
        logger.error(f"程序启动失败: {e}")
        if 'app' in locals():
            QMessageBox.critical(None, "错误", f"程序启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 