import sys
import os
import asyncio
import threading
from queue import Queue
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QApplication, QMenuBar, QMenu,
    QStatusBar, QLabel, QProgressBar, QToolBar,
    QStyle, QHeaderView, QActionGroup
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QIcon
from loguru import logger

from .device_tab import DeviceTab
from .record_tab import RecordTab
from .playback_tab import PlaybackTab
from .config_tab import ConfigTab
from .report_tab import ReportTab
from core.device_manager import DeviceManager
from core.config_manager import ConfigManager
from utils.helpers import load_stylesheet

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化成员变量
        self.config_manager = ConfigManager()
        self.device_manager = DeviceManager(self.config_manager.get_config())
        self.tabs = {}  # 标签页字典
        self._update_queue = Queue()  # UI更新队列
        self._update_timer = None  # UI更新定时器
        self._update_interval = 50  # UI更新间隔（毫秒）
        self._last_update_time = 0  # 上次更新时间
        self._update_lock = threading.Lock()  # UI更新锁
        self._update_batch_size = 10  # UI更新批处理大小
        
        # 初始化UI
        self.init_ui()
        
        # 加载样式表
        self.load_styles()
        
        # 启动UI更新定时器
        self._start_update_timer()
        
        # 启动设备监控
        asyncio.create_task(self.device_manager.start_monitoring())
        
        logger.info("主窗口初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        try:
            # 设置窗口属性
            self.setWindowTitle('App自动化工具')
            self.setGeometry(100, 100, 1200, 800)
            self.setMinimumSize(800, 600)
            
            # 创建菜单栏
            self._create_menu_bar()
            
            # 创建工具栏
            self._create_tool_bar()
            
            # 创建中心部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 创建布局
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(5)
            central_widget.setLayout(layout)
            
            # 创建标签页
            self.tab_widget = QTabWidget()
            self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
            self.tab_widget.setMovable(True)  # 允许拖动标签页
            self.tab_widget.setTabsClosable(False)  # 不允许关闭标签页
            layout.addWidget(self.tab_widget)
            
            # 初始化各个标签页
            self._init_tabs()
            
            # 创建状态栏
            self._create_status_bar()
            
            # 连接信号
            self._connect_signals()
            
            logger.info("UI初始化完成")
        
        except Exception as e:
            logger.error(f"UI初始化失败: {e}")
            QMessageBox.critical(self, "错误", "UI初始化失败，请检查日志")
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        # 导入配置
        import_action = QAction('导入配置', self)
        import_action.setStatusTip('导入配置文件')
        import_action.triggered.connect(self._import_config)
        file_menu.addAction(import_action)
        
        # 导出配置
        export_action = QAction('导出配置', self)
        export_action.setStatusTip('导出配置文件')
        export_action.triggered.connect(self._export_config)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction('退出', self)
        exit_action.setStatusTip('退出应用程序')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        # 工具栏显示切换
        toggle_toolbar = QAction('显示工具栏', self, checkable=True)
        toggle_toolbar.setChecked(True)
        toggle_toolbar.triggered.connect(self.toolbar.setVisible)
        view_menu.addAction(toggle_toolbar)
        
        # 状态栏显示切换
        toggle_statusbar = QAction('显示状态栏', self, checkable=True)
        toggle_statusbar.setChecked(True)
        toggle_statusbar.triggered.connect(self.statusBar().setVisible)
        view_menu.addAction(toggle_statusbar)
        
        # 平台菜单
        platform_menu = menubar.addMenu('平台')
        
        # Android平台
        android_action = QAction('Android', self, checkable=True)
        android_action.setChecked(True)
        android_action.triggered.connect(lambda: self._switch_platform('android'))
        platform_menu.addAction(android_action)
        
        # iOS平台
        ios_action = QAction('iOS', self, checkable=True)
        ios_action.triggered.connect(lambda: self._switch_platform('ios'))
        platform_menu.addAction(ios_action)
        
        # 设置互斥
        platform_group = QActionGroup(self)
        platform_group.addAction(android_action)
        platform_group.addAction(ios_action)
        platform_group.setExclusive(True)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        # 关于
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_tool_bar(self):
        """创建工具栏"""
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # 刷新按钮
        refresh_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload),
            '刷新',
            self
        )
        refresh_action.setStatusTip('刷新设备列表和状态')
        refresh_action.triggered.connect(self._refresh_all)
        self.toolbar.addAction(refresh_action)
        
        self.toolbar.addSeparator()
        
        # 启动服务按钮
        start_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay),
            '启动服务',
            self
        )
        start_action.setStatusTip('启动Appium服务')
        start_action.triggered.connect(self._start_services)
        self.toolbar.addAction(start_action)
        
        # 停止服务按钮
        stop_action = QAction(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop),
            '停止服务',
            self
        )
        stop_action.setStatusTip('停止所有Appium服务')
        stop_action.triggered.connect(self._stop_services)
        self.toolbar.addAction(stop_action)
    
    def _create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # 设备状态标签
        self.device_status_label = QLabel("设备: 0 在线")
        status_bar.addWidget(self.device_status_label)
        
        # 添加分隔符
        status_bar.addPermanentWidget(QLabel("|"))
        
        # Appium服务状态标签
        self.appium_status_label = QLabel("Appium服务: 0 运行中")
        status_bar.addPermanentWidget(self.appium_status_label)
        
        # 添加分隔符
        status_bar.addPermanentWidget(QLabel("|"))
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.hide()
        status_bar.addPermanentWidget(self.progress_bar)
    
    def _init_tabs(self):
        """初始化标签页"""
        try:
            # 设备标签页
            device_tab = DeviceTab(self.config_manager.get_config())
            self.tab_widget.addTab(device_tab, "设备管理")
            self.tabs['device'] = device_tab
            
            # 录制标签页
            record_tab = RecordTab(self.config_manager.get_config())
            self.tab_widget.addTab(record_tab, "录制")
            self.tabs['record'] = record_tab
            
            # 回放标签页
            playback_tab = PlaybackTab(self.config_manager.get_config())
            self.tab_widget.addTab(playback_tab, "回放")
            self.tabs['playback'] = playback_tab
            
            # 配置标签页
            config_tab = ConfigTab(self.config_manager)
            self.tab_widget.addTab(config_tab, "配置")
            self.tabs['config'] = config_tab
            
            # 报告标签页
            report_tab = ReportTab()
            self.tab_widget.addTab(report_tab, "报告")
            self.tabs['report'] = report_tab
            
            # 连接信号
            device_tab.device_selected.connect(record_tab.set_device)
            device_tab.device_selected.connect(playback_tab.set_device)
            config_tab.config_changed.connect(self._on_config_changed)
            
            # 设置默认平台
            device_tab.set_platform('android')
            
            logger.info("标签页初始化完成")
        
        except Exception as e:
            logger.error(f"初始化标签页失败: {e}")
            raise
    
    def _connect_signals(self):
        """连接信号"""
        try:
            # 标签页切换信号
            self.tab_widget.currentChanged.connect(self._on_tab_changed)
            
            # 设备相关信号
            device_tab = self.tabs.get('device')
            if device_tab:
                device_tab.device_selected.connect(self._on_device_selected)
                device_tab.device_disconnected.connect(self._on_device_disconnected)
            
            # 录制相关信号
            record_tab = self.tabs.get('record')
            if record_tab:
                record_tab.recording_started.connect(self._on_recording_started)
                record_tab.recording_stopped.connect(self._on_recording_stopped)
            
            # 回放相关信号
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                playback_tab.playback_started.connect(self._on_playback_started)
                playback_tab.playback_stopped.connect(self._on_playback_stopped)
            
            logger.info("信号连接完成")
        
        except Exception as e:
            logger.error(f"连接信号失败: {e}")
            raise
    
    def load_styles(self):
        """加载样式表"""
        try:
            style_file = os.path.join("resources", "style.qss")
            if os.path.exists(style_file):
                with open(style_file, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
                logger.info("样式表加载成功")
            else:
                logger.warning("样式表文件不存在")
        
        except Exception as e:
            logger.error(f"加载样式表失败: {e}")
    
    def _refresh_all(self):
        """刷新所有状态"""
        try:
            # 显示进度条
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            
            # 刷新设备列表
            device_tab = self.tabs.get('device')
            if device_tab:
                device_tab.refresh_devices()
            
            # 更新状态栏信息
            self._update_status_bar()
            
            # 隐藏进度条
            self.progress_bar.hide()
            
            # 显示刷新完成消息
            self.statusBar().showMessage("刷新完成", 3000)
        
        except Exception as e:
            logger.error(f"刷新失败: {e}")
            QMessageBox.warning(self, "警告", "刷新失败，请检查日志")
    
    def _update_status_bar(self):
        """更新状态栏信息"""
        try:
            # 更新设备状态
            devices = self.device_manager.get_devices()
            device_count = len(devices)
            connected_count = sum(1 for d in devices if d.get('status', '').lower() == 'connected')
            self.device_status_label.setText(f"设备: {connected_count}/{device_count} 在线")
            
            # 更新Appium服务状态
            servers = self.device_manager.get_appium_servers()
            appium_count = len(servers)
            self.appium_status_label.setText(f"Appium服务: {appium_count} 运行中")
            
            # 更新工具栏按钮状态
            if hasattr(self, 'toolbar'):
                for action in self.toolbar.actions():
                    if action.text() == '启动服务':
                        action.setEnabled(connected_count > 0 and appium_count < connected_count)
                    elif action.text() == '停止服务':
                        action.setEnabled(appium_count > 0)
        
        except Exception as e:
            logger.error(f"更新状态栏失败: {e}")
            self.statusBar().showMessage(f"状态更新失败: {e}", 3000)
    
    def _import_config(self):
        """导入配置"""
        # TODO: 实现配置导入功能
        pass
    
    def _export_config(self):
        """导出配置"""
        # TODO: 实现配置导出功能
        pass
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "App自动化工具 v1.0.0\n\n"
            "一个强大的移动应用自动化测试工具\n\n"
            "支持Android和iOS平台\n"
            "© 2024 All Rights Reserved"
        )
    
    def _start_services(self):
        """启动服务"""
        try:
            # 显示加载状态
            self.statusBar().showMessage("正在启动Appium服务...", 0)
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
            
            # 禁用工具栏按钮
            for action in self.toolbar.actions():
                action.setEnabled(False)
            
            # 启动服务
            device_tab = self.tabs.get('device')
            if device_tab:
                device_tab.start_all_appium_servers()
            
            # 启动完成后的处理在device_tab中通过信号完成
        
        except Exception as e:
            logger.error(f"启动服务失败: {e}")
            self.statusBar().showMessage(f"启动服务失败: {e}", 3000)
            self.progress_bar.hide()
            
            # 重新启用工具栏按钮
            self._update_status_bar()
    
    def _stop_services(self):
        """停止服务"""
        try:
            # 显示加载状态
            self.statusBar().showMessage("正在停止Appium服务...", 0)
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
            
            # 禁用工具栏按钮
            for action in self.toolbar.actions():
                action.setEnabled(False)
            
            # 停止服务
            device_tab = self.tabs.get('device')
            if device_tab:
                device_tab.stop_all_appium_servers()
            
            # 停止完成后的处理在device_tab中通过信号完成
        
        except Exception as e:
            logger.error(f"停止服务失败: {e}")
            self.statusBar().showMessage(f"停止服务失败: {e}", 3000)
            self.progress_bar.hide()
            
            # 重新启用工具栏按钮
            self._update_status_bar()
    
    def _on_tab_changed(self, index: int):
        """标签页切换处理"""
        try:
            current_tab = self.tab_widget.widget(index)
            if current_tab:
                # 显示加载状态
                self.statusBar().showMessage(f"正在加载{self.tab_widget.tabText(index)}...", 1000)
                self.progress_bar.setRange(0, 0)
                self.progress_bar.show()
                
                # 使用QTimer延迟执行，确保UI更新
                QTimer.singleShot(100, lambda: self._complete_tab_change(current_tab, index))
            
            logger.debug(f"切换到标签页: {index}")
        
        except Exception as e:
            logger.error(f"标签页切换处理失败: {e}")
            self.statusBar().showMessage(f"标签页切换失败: {e}", 3000)
            self.progress_bar.hide()
    
    def _complete_tab_change(self, tab: QWidget, index: int):
        """完成标签页切换"""
        try:
            # 激活标签页
            self.queue_ui_update(tab.on_tab_activated)
            
            # 更新状态
            self._update_status_bar()
            
            # 隐藏进度条
            self.progress_bar.hide()
            
            # 显示完成消息
            self.statusBar().showMessage(f"{self.tab_widget.tabText(index)}已加载", 1000)
        
        except Exception as e:
            logger.error(f"完成标签页切换失败: {e}")
            self.statusBar().showMessage(f"标签页加载失败: {e}", 3000)
            self.progress_bar.hide()
    
    def _on_device_selected(self, device_info: Dict):
        """设备选择处理"""
        try:
            # 显示加载状态
            self.statusBar().showMessage("正在更新设备信息...", 1000)
            self.progress_bar.setRange(0, 0)
            self.progress_bar.show()
            
            # 通知其他标签页
            record_tab = self.tabs.get('record')
            if record_tab:
                self.queue_ui_update(record_tab.set_device, device_info)
            
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                self.queue_ui_update(playback_tab.set_device, device_info)
            
            # 更新状态栏
            self._update_status_bar()
            
            # 隐藏进度条
            self.progress_bar.hide()
            
            # 显示成功消息
            self.statusBar().showMessage(
                f"已选择设备: {device_info.get('model', '')} ({device_info.get('id', '')})",
                3000
            )
            
            logger.info(f"设备已选择: {device_info.get('id')}")
        
        except Exception as e:
            logger.error(f"设备选择处理失败: {e}")
            self.statusBar().showMessage(f"设备选择失败: {e}", 3000)
            self.progress_bar.hide()
    
    def _on_device_disconnected(self, device_id: str):
        """设备断开处理"""
        try:
            # 通知其他标签页
            record_tab = self.tabs.get('record')
            if record_tab:
                self.queue_ui_update(record_tab.clear_device_info)
            
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                self.queue_ui_update(playback_tab.clear_device_info)
            
            logger.info(f"设备已断开: {device_id}")
        
        except Exception as e:
            logger.error(f"设备断开处理失败: {e}")
    
    def _on_recording_started(self):
        """录制开始处理"""
        try:
            # 禁用其他标签页
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                self.queue_ui_update(playback_tab.setEnabled, False)
            
            logger.info("录制已开始")
        
        except Exception as e:
            logger.error(f"录制开始处理失败: {e}")
    
    def _on_recording_stopped(self):
        """录制停止处理"""
        try:
            # 启用其他标签页
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                self.queue_ui_update(playback_tab.setEnabled, True)
            
            logger.info("录制已停止")
        
        except Exception as e:
            logger.error(f"录制停止处理失败: {e}")
    
    def _on_playback_started(self):
        """回放开始处理"""
        try:
            # 禁用其他标签页
            record_tab = self.tabs.get('record')
            if record_tab:
                self.queue_ui_update(record_tab.setEnabled, False)
            
            logger.info("回放已开始")
        
        except Exception as e:
            logger.error(f"回放开始处理失败: {e}")
    
    def _on_playback_stopped(self):
        """回放停止处理"""
        try:
            # 启用其他标签页
            record_tab = self.tabs.get('record')
            if record_tab:
                self.queue_ui_update(record_tab.setEnabled, True)
            
            logger.info("回放已停止")
        
        except Exception as e:
            logger.error(f"回放停止处理失败: {e}")
    
    def _on_config_changed(self, config):
        """配置变化处理"""
        try:
            # 更新设备管理器中的配置
            self.device_manager.update_config(config)
            
            # 通知其他标签页
            record_tab = self.tabs.get('record')
            if record_tab:
                self.queue_ui_update(record_tab.update_config, config)
            
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                self.queue_ui_update(playback_tab.update_config, config)
            
            logger.info("配置已更新")
        
        except Exception as e:
            logger.error(f"配置变化处理失败: {e}")
    
    def _switch_platform(self, platform: str):
        """切换平台
        
        Args:
            platform: 平台类型 (android/ios)
        """
        try:
            device_tab = self.tabs.get('device')
            if device_tab:
                device_tab.set_platform(platform)
                self.statusBar().showMessage(f"已切换到 {platform.upper()} 平台", 3000)
        except Exception as e:
            logger.error(f"切换平台失败: {e}")
            QMessageBox.critical(self, "错误", f"切换平台失败: {e}")
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        try:
            reply = QMessageBox.question(
                self,
                '确认退出',
                "确定要退出程序吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 停止所有服务
                device_tab = self.tabs.get('device')
                if device_tab:
                    device_tab.stop_all_appium_servers()
                
                # 停止设备监控
                asyncio.create_task(self.device_manager.stop_monitoring())
                
                # 保存配置
                self.config_manager.save_config()
                
                event.accept()
            else:
                event.ignore()
        
        except Exception as e:
            logger.error(f"关闭窗口失败: {e}")
            event.accept()

def main():
    """主函数"""
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 