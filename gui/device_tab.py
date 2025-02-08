from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QProgressBar, QHeaderView, QTableWidget,
    QTableWidgetItem, QSplitter, QStyle
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QIcon, QColor, QPalette
from loguru import logger
from core.device_manager import DeviceManager
from utils.helpers import get_free_port
import time
import threading

class DeviceTab(QWidget):
    # 定义信号
    device_selected = Signal(dict)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setObjectName("device_tab")
        self.config = config
        self.device_manager = None
        self.connected_devices = {}  # 存储已连接的设备信息
        self.current_platform = 'android'
        self.connection_lock = threading.Lock()  # 添加连接状态锁
        self.init_device_manager()
        self.init_ui()
        
        # 启动定时刷新（10秒刷新一次设备列表）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(10000)
        
        # 启动Appium服务状态刷新（3秒刷新一次）
        self.appium_status_timer = QTimer()
        self.appium_status_timer.timeout.connect(self.refresh_appium_status)
        self.appium_status_timer.start(3000)
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 设备列表区域
        device_frame = self._create_device_frame()
        splitter.addWidget(device_frame)
        
        # Appium服务管理区域
        appium_frame = self._create_appium_frame()
        splitter.addWidget(appium_frame)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _create_device_frame(self):
        """创建设备列表区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题和刷新按钮
        header_layout = QHBoxLayout()
        title = QLabel("设备管理")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
        """)
        
        refresh_btn = QPushButton("刷新设备列表")
        refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_devices)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # 设备列表
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["", "设备ID", "型号", "系统版本", "状态", "操作"])
        self.device_tree.setAlternatingRowColors(True)
        self.device_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QTreeWidget::item {
                padding: 8px 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-right: 1px solid #dcdcdc;
                border-bottom: 1px solid #dcdcdc;
                font-weight: bold;
            }
        """)
        
        # 设置列宽
        header = self.device_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 复选框列
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        # 设置最小列宽
        self.device_tree.setColumnWidth(0, 30)  # 复选框列
        self.device_tree.setColumnWidth(3, 100)  # 系统版本列
        self.device_tree.setColumnWidth(4, 80)   # 状态列
        self.device_tree.setColumnWidth(5, 100)  # 操作列
        
        layout.addWidget(self.device_tree)
        frame.setLayout(layout)
        return frame
    
    def _create_appium_frame(self):
        """创建Appium服务管理区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题和关闭按钮
        header_layout = QHBoxLayout()
        title = QLabel("Appium服务管理")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
        """)
        
        stop_all_btn = QPushButton("关闭所有服务")
        stop_all_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserStop))
        stop_all_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
        """)
        stop_all_btn.clicked.connect(self.stop_all_appium_servers)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(stop_all_btn)
        layout.addLayout(header_layout)
        
        # Appium服务列表
        self.appium_table = QTableWidget()
        self.appium_table.setColumnCount(4)
        self.appium_table.setHorizontalHeaderLabels(["主机", "端口", "运行时间", "状态"])
        self.appium_table.setAlternatingRowColors(True)
        self.appium_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #dcdcdc;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QTableWidget::item {
                padding: 8px 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-right: 1px solid #dcdcdc;
                border-bottom: 1px solid #dcdcdc;
                font-weight: bold;
            }
        """)
        
        # 设置列宽
        header = self.appium_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # 设置最小列宽
        self.appium_table.setColumnWidth(1, 80)   # 端口列
        self.appium_table.setColumnWidth(2, 100)  # 运行时间列
        self.appium_table.setColumnWidth(3, 80)   # 状态列
        
        layout.addWidget(self.appium_table)
        frame.setLayout(layout)
        return frame
    
    def refresh_devices(self):
        """刷新设备列表"""
        try:
            self.device_tree.clear()
            self.devices = self.device_manager.get_devices()  # 保存设备列表到实例变量
            
            for device in self.devices:
                item = QTreeWidgetItem()
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)
                
                device_id = device['id']
                # 设置设备信息
                item.setText(1, device_id)
                item.setText(2, device.get('model', 'Unknown'))
                item.setText(3, device.get('platform_version', 'Unknown'))
                
                # 检查设备是否已连接到Appium
                is_connected = device_id in self.connected_devices
                status = "已连接到Appium" if is_connected else "未连接"
                item.setText(4, status)
                
                # 设置状态颜色
                status_color = QColor("#4CAF50") if is_connected else QColor("#f44336")
                item.setForeground(4, status_color)
                
                # 如果设备已连接，自动勾选
                if is_connected:
                    item.setCheckState(0, Qt.CheckState.Checked)
                
                # 添加操作按钮
                btn_text = "断开Appium" if is_connected else "连接到Appium"
                btn_style = """
                    QPushButton {
                        padding: 3px 12px;
                        background-color: %s;
                        color: white;
                        border: none;
                        border-radius: 2px;
                        min-width: 80px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: %s;
                    }
                    QPushButton:pressed {
                        background-color: %s;
                    }
                """ % (
                    ('#f44336' if is_connected else '#4CAF50'),
                    ('#e53935' if is_connected else '#45a049'),
                    ('#d32f2f' if is_connected else '#3d8b40')
                )
                
                connect_button = QPushButton(btn_text)
                connect_button.setStyleSheet(btn_style)
                connect_button.clicked.connect(lambda checked, d=device: self.toggle_device_connection(d))
                
                self.device_tree.addTopLevelItem(item)
                self.device_tree.setItemWidget(item, 5, connect_button)
            
            logger.info(f"设备列表已刷新，共发现 {len(self.devices)} 个设备")
        except Exception as e:
            logger.error(f"刷新设备列表失败: {e}")
            QMessageBox.critical(self, "错误", f"刷新设备列表失败: {str(e)}")
    
    def refresh_appium_status(self):
        """刷新Appium服务状态"""
        try:
            servers = self.device_manager.get_appium_servers()
            self.appium_table.setRowCount(len(servers))
            
            current_time = time.time()
            for i, server in enumerate(servers):
                # 设置表格项
                host_item = QTableWidgetItem(server['host'])
                port_item = QTableWidgetItem(str(server['port']))
                
                # 计算运行时间
                start_time = server.get('start_time', current_time)
                running_time = current_time - start_time
                if running_time < 60:
                    time_str = f"{int(running_time)}秒"
                elif running_time < 3600:
                    time_str = f"{int(running_time / 60)}分钟"
                else:
                    time_str = f"{int(running_time / 3600)}小时{int((running_time % 3600) / 60)}分钟"
                
                time_item = QTableWidgetItem(time_str)
                status_item = QTableWidgetItem(server['status'])
                
                # 设置状态颜色
                status_color = QColor("#4CAF50") if server['status'] == 'running' else QColor("#f44336")
                status_item.setForeground(status_color)
                
                # 设置为只读
                for item in (host_item, port_item, time_item, status_item):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                self.appium_table.setItem(i, 0, host_item)
                self.appium_table.setItem(i, 1, port_item)
                self.appium_table.setItem(i, 2, time_item)
                self.appium_table.setItem(i, 3, status_item)
        except Exception as e:
            logger.error(f"刷新Appium服务状态失败: {e}")
    
    def toggle_device_connection(self, device: dict):
        """切换设备连接状态"""
        try:
            device_id = device['id']
            logger.debug(f"切换设备 {device_id} 的连接状态")
            logger.debug(f"当前设备信息: {device}")
            logger.debug(f"已连接设备列表: {self.connected_devices}")
            
            if device_id in self.connected_devices:
                logger.debug(f"设备 {device_id} 已连接，准备断开连接")
                self.disconnect_device(device_id)
            else:
                logger.debug(f"设备 {device_id} 未连接，准备连接")
                self.connect_device(device)
            self.refresh_devices()
        except Exception as e:
            logger.error(f"切换设备连接状态失败: {e}")
            QMessageBox.critical(self, "错误", f"切换设备连接状态失败: {str(e)}")
    
    def connect_device(self, device: dict):
        """连接设备"""
        try:
            device_id = device['id']
            logger.debug(f"开始连接设备: {device_id}")
            
            # 使用锁确保线程安全
            with self.connection_lock:
                # 检查设备是否已连接
                if device_id in self.connected_devices:
                    msg = QMessageBox()
                    msg.setParent(self)  # 设置父窗口
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle("警告")
                    msg.setText(f"设备 {device_id} 已连接")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.setWindowModality(Qt.WindowModality.NonModal)
                    msg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 关闭时自动删除
                    msg.show()
                    return
                
                # 获取空闲端口
                port = get_free_port()
                if not port:
                    msg = QMessageBox()
                    msg.setParent(self)
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setWindowTitle("错误")
                    msg.setText("无法获取可用端口")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.setWindowModality(Qt.WindowModality.NonModal)
                    msg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                    msg.show()
                    return
                
                logger.debug(f"获取到空闲端口: {port}")
                
                # 启动Appium服务
                logger.debug(f"正在启动Appium服务，端口: {port}")
                if not self.device_manager._start_appium_server_internal('127.0.0.1', port):
                    msg = QMessageBox()
                    msg.setParent(self)
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setWindowTitle("错误")
                    msg.setText(f"启动Appium服务失败，端口: {port}")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg.setWindowModality(Qt.WindowModality.NonModal)
                    msg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                    msg.show()
                    return
                
                logger.debug(f"Appium服务启动成功，端口: {port}")
                
                # 更新连接状态
                self.connected_devices[device_id] = {
                    'port': port,
                    'status': 'connected',
                    'connect_time': time.time()
                }
                
                # 立即更新UI
                self.refresh_devices()
                self.refresh_appium_status()
                
                # 发送设备选择信号
                self.device_selected.emit(device)
                
                # 显示连接成功提示（使用非模态对话框）
                success_msg = QMessageBox()
                success_msg.setParent(self)
                success_msg.setIcon(QMessageBox.Icon.Information)
                success_msg.setWindowTitle("连接成功")
                success_msg.setText(f"设备 {device_id} 已成功连接到Appium服务")
                success_msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                success_msg.setWindowModality(Qt.WindowModality.NonModal)
                success_msg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                
                # 设置定时自动关闭（3秒）
                QTimer.singleShot(3000, success_msg.close)
                success_msg.show()
                
                logger.info(f"设备 {device_id} 已连接到Appium服务，使用端口 {port}")
        
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            msg = QMessageBox()
            msg.setParent(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("错误")
            msg.setText(f"连接设备失败: {str(e)}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowModality(Qt.WindowModality.NonModal)
            msg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            msg.show()
            # 确保清理资源
            if 'port' in locals():
                self.device_manager.stop_appium_server(port)
    
    def disconnect_device(self, device_id: str):
        """断开设备连接"""
        try:
            logger.debug(f"开始断开设备 {device_id} 的连接")
            
            # 使用锁确保线程安全
            with self.connection_lock:
                # 检查设备是否在已连接列表中
                if device_id not in self.connected_devices:
                    logger.warning(f"设备 {device_id} 未连接")
                    return
                
                # 获取设备信息
                device_info = self.connected_devices[device_id]
                port = device_info['port']
                
                logger.debug(f"设备当前使用的Appium端口: {port}")
                
                # 停止Appium服务
                logger.debug(f"正在停止端口 {port} 的Appium服务")
                self.device_manager.stop_appium_server(port)
                
                # 从已连接设备列表中移除
                del self.connected_devices[device_id]
                
                # 立即更新UI
                self.refresh_devices()
                self.refresh_appium_status()
                
                logger.info(f"设备 {device_id} 已断开连接")
                
                # 显示断开成功提示
                QMessageBox.information(self, "断开成功", f"设备 {device_id} 已断开连接")
        
        except Exception as e:
            logger.error(f"断开设备连接失败: {e}")
            QMessageBox.critical(self, "错误", f"断开设备连接失败: {str(e)}")
    
    def stop_all_appium_servers(self):
        """关闭所有Appium服务"""
        try:
            if not self.connected_devices:
                QMessageBox.information(self, "提示", "当前没有运行中的Appium服务")
                return
            
            reply = QMessageBox.question(
                self, "确认",
                "确定要关闭所有Appium服务吗？\n这将断开所有已连接的设备。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 显示进度
                progress = QProgressBar(self)
                progress.setRange(0, len(self.connected_devices))
                progress.setValue(0)
                progress.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #dcdcdc;
                        border-radius: 2px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #f44336;
                    }
                """)
                
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setText("正在关闭所有Appium服务...")
                msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
                layout = msg.layout()
                layout.addWidget(progress, 1, 1)
                msg.show()
                
                # 断开所有设备
                for i, device_id in enumerate(list(self.connected_devices.keys())):
                    self.disconnect_device(device_id)
                    progress.setValue(i + 1)
                
                msg.close()
                self.refresh_devices()
                QMessageBox.information(self, "成功", "所有Appium服务已关闭")
        except Exception as e:
            logger.error(f"关闭所有Appium服务失败: {e}")
            QMessageBox.critical(self, "错误", f"关闭所有Appium服务失败: {str(e)}")
    
    def set_platform(self, platform: str):
        """设置平台类型"""
        try:
            self.current_platform = platform
            self.device_manager.set_platform(platform)
            self.refresh_devices()
        except Exception as e:
            logger.error(f"设置平台失败: {e}")
            QMessageBox.critical(self, "错误", f"设置平台失败: {str(e)}")
    
    def init_device_manager(self):
        """初始化设备管理器"""
        try:
            self.device_manager = DeviceManager()
            logger.info("设备管理器初始化成功")
        except Exception as e:
            logger.error(f"初始化设备管理器失败: {e}")
            QMessageBox.critical(self, "错误", f"初始化设备管理器失败: {str(e)}")
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
            if hasattr(self, 'appium_status_timer'):
                self.appium_status_timer.stop()
            
            # 断开所有设备连接
            for device_id in list(self.connected_devices.keys()):
                try:
                    self.disconnect_device(device_id)
                except Exception as e:
                    logger.error(f"清理设备 {device_id} 失败: {e}")
            
            logger.info("设备管理器资源已清理")
        except Exception as e:
            logger.error(f"清理资源失败: {e}") 