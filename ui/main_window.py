from typing import Dict, Optional
import sys
import asyncio
import threading
from queue import Queue
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMessageBox, QApplication, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from loguru import logger

from .device_tab import DeviceTab
from .record_tab import RecordTab
from .playback_tab import PlaybackTab
from core.device_manager import DeviceManager
from core.config_manager import ConfigManager

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
        
        # 初始化UI
        self.init_ui()
        
        # 启动UI更新定时器
        self._start_update_timer()
        
        # 启动设备监控
        asyncio.create_task(self.device_manager.start_monitoring())
    
    def init_ui(self):
        """初始化UI"""
        try:
            # 设置窗口属性
            self.setWindowTitle('App自动化工具')
            self.setGeometry(100, 100, 800, 600)
            
            # 创建中心部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 创建布局
            layout = QVBoxLayout()
            central_widget.setLayout(layout)
            
            # 创建标签页
            self.tab_widget = QTabWidget()
            layout.addWidget(self.tab_widget)
            
            # 初始化各个标签页
            self._init_tabs()
            
            # 连接信号
            self._connect_signals()
            
            logger.info("UI初始化完成")
        
        except Exception as e:
            logger.error(f"UI初始化失败: {e}")
            QMessageBox.critical(self, "错误", "UI初始化失败，请检查日志")
    
    def _init_tabs(self):
        """初始化标签页"""
        try:
            # 设备标签页
            device_tab = DeviceTab(self.device_manager)
            self.tab_widget.addTab(device_tab, "设备管理")
            self.tabs['device'] = device_tab
            
            # 录制标签页
            record_tab = RecordTab()
            self.tab_widget.addTab(record_tab, "录制")
            self.tabs['record'] = record_tab
            
            # 回放标签页
            playback_tab = PlaybackTab()
            self.tab_widget.addTab(playback_tab, "回放")
            self.tabs['playback'] = playback_tab
        
        except Exception as e:
            logger.error(f"初始化标签页失败: {e}")
            raise
    
    def _connect_signals(self):
        """连接信号"""
        try:
            # 标签页切换信号
            self.tab_widget.currentChanged.connect(self._on_tab_changed)
            
            # 设备标签页信号
            device_tab = self.tabs.get('device')
            if device_tab:
                device_tab.device_selected.connect(self._on_device_selected)
                device_tab.device_disconnected.connect(self._on_device_disconnected)
            
            # 录制标签页信号
            record_tab = self.tabs.get('record')
            if record_tab:
                record_tab.recording_started.connect(self._on_recording_started)
                record_tab.recording_stopped.connect(self._on_recording_stopped)
            
            # 回放标签页信号
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                playback_tab.playback_started.connect(self._on_playback_started)
                playback_tab.playback_stopped.connect(self._on_playback_stopped)
            
            logger.info("信号连接完成")
        
        except Exception as e:
            logger.error(f"连接信号失败: {e}")
            raise
    
    def _start_update_timer(self):
        """启动UI更新定时器"""
        try:
            self._update_timer = QTimer()
            self._update_timer.timeout.connect(self._process_update_queue)
            self._update_timer.start(self._update_interval)
            logger.info("UI更新定时器已启动")
        
        except Exception as e:
            logger.error(f"启动UI更新定时器失败: {e}")
    
    def _process_update_queue(self):
        """处理UI更新队列"""
        try:
            with self._update_lock:
                while not self._update_queue.empty():
                    try:
                        update_func, args, kwargs = self._update_queue.get_nowait()
                        update_func(*args, **kwargs)
                    except Queue.Empty:
                        break
                    except Exception as e:
                        logger.error(f"处理UI更新失败: {e}")
        
        except Exception as e:
            logger.error(f"处理UI更新队列失败: {e}")
    
    def queue_ui_update(self, update_func, *args, **kwargs):
        """将UI更新添加到队列"""
        try:
            self._update_queue.put((update_func, args, kwargs))
        except Exception as e:
            logger.error(f"添加UI更新到队列失败: {e}")
    
    def _on_tab_changed(self, index: int):
        """标签页切换处理"""
        try:
            current_tab = self.tab_widget.widget(index)
            if current_tab:
                current_tab.on_tab_activated()
            logger.debug(f"切换到标签页: {index}")
        
        except Exception as e:
            logger.error(f"标签页切换处理失败: {e}")
    
    def _on_device_selected(self, device_info: Dict):
        """设备选择处理"""
        try:
            # 通知其他标签页
            record_tab = self.tabs.get('record')
            if record_tab:
                self.queue_ui_update(record_tab.update_device_info, device_info)
            
            playback_tab = self.tabs.get('playback')
            if playback_tab:
                self.queue_ui_update(playback_tab.update_device_info, device_info)
            
            logger.info(f"设备已选择: {device_info.get('id')}")
        
        except Exception as e:
            logger.error(f"设备选择处理失败: {e}")
    
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
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            # 停止UI更新定时器
            if self._update_timer:
                self._update_timer.stop()
            
            # 停止设备监控
            asyncio.create_task(self.device_manager.stop_monitoring())
            
            # 清理资源
            self.device_manager.__del__()
            
            # 接受关闭事件
            event.accept()
            logger.info("应用程序正常退出")
        
        except Exception as e:
            logger.error(f"应用程序退出时发生错误: {e}")
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