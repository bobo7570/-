from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QProgressBar, QHeaderView, QTableWidget,
    QTableWidgetItem, QSplitter, QStyle, QMenu, QComboBox,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QIcon, QColor, QPalette, QAction
from loguru import logger
from core.device_manager import DeviceManager
from utils.helpers import get_free_port, format_size, format_time
import time
import threading
import asyncio
import os

class DeviceTab(QWidget):
    # 定义信号
    device_selected = Signal(dict)  # 设备选择信号
    device_disconnected = Signal(str)  # 设备断开信号
    device_status_changed = Signal(dict)  # 设备状态变化信号
    
    def __init__(self, config, parent=None):
        """初始化设备标签页
        
        Args:
            config: 配置字典
            parent: 父窗口
        """
        super().__init__(parent)
        self.setObjectName("device_tab")
        
        # 初始化成员变量
        self.config = config
        self.device_manager = DeviceManager(config)
        self.current_platform = "android"
        self.devices_tree = None
        self.appium_table = None
        self.refresh_timer = None
        self.refresh_interval = 5000  # 刷新间隔（毫秒）
        self._selected_device = None
        
        # 初始化按钮引用
        self.refresh_btn = None
        self.start_btn = None
        self.stop_btn = None
        
        # 初始化UI
        self.init_ui()
        
        logger.info("设备标签页初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建工具栏
        toolbar_layout = QHBoxLayout()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_btn.clicked.connect(self.refresh_devices)
        toolbar_layout.addWidget(self.refresh_btn)
        
        # 启动服务按钮
        self.start_btn = QPushButton("启动服务")
        self.start_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.start_btn.clicked.connect(self.start_all_appium_servers)
        toolbar_layout.addWidget(self.start_btn)
        
        # 停止服务按钮
        self.stop_btn = QPushButton("停止服务")
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop_all_appium_servers)
        toolbar_layout.addWidget(self.stop_btn)
        
        # 添加弹性空间
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)
        
        # 创建设备列表区域
        device_frame = self._create_device_frame()
        main_layout.addWidget(device_frame)
        
        # 创建Appium服务区域
        appium_frame = self._create_appium_frame()
        main_layout.addWidget(appium_frame)
        
        self.setLayout(main_layout)
        
        # 启动刷新定时器
        self._start_refresh_timer()
    
    def _create_device_frame(self):
        """创建设备列表区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("设备列表")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 设备树形列表
        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels([
            "设备ID", "型号", "系统版本", "状态",
            "电池", "内存", "存储"
        ])
        self.devices_tree.setAlternatingRowColors(True)
        self.devices_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.devices_tree.customContextMenuRequested.connect(self._show_device_context_menu)
        self.devices_tree.itemSelectionChanged.connect(self._on_device_selected)
        
        # 设置列宽
        header = self.devices_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.devices_tree)
        frame.setLayout(layout)
        return frame
    
    def _create_appium_frame(self):
        """创建Appium服务管理区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("Appium服务")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # Appium服务表格
        self.appium_table = QTableWidget()
        self.appium_table.setColumnCount(4)
        self.appium_table.setHorizontalHeaderLabels([
            "主机", "端口", "运行时间", "状态"
        ])
        self.appium_table.setAlternatingRowColors(True)
        self.appium_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.appium_table.customContextMenuRequested.connect(self._show_appium_context_menu)
        
        # 设置列宽
        header = self.appium_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.appium_table)
        frame.setLayout(layout)
        return frame
    
    def _show_device_context_menu(self, pos):
        """显示设备右键菜单"""
        try:
            item = self.devices_tree.itemAt(pos)
            if not item:
                return
            
            # 创建右键菜单
            self.context_menu = QMenu(self)
            
            # 连接设备
            connect_action = QAction("连接设备", self)
            connect_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
            connect_action.triggered.connect(lambda: self._connect_device(item))
            self.context_menu.addAction(connect_action)
            
            # 断开设备
            disconnect_action = QAction("断开设备", self)
            disconnect_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
            disconnect_action.triggered.connect(lambda: self._disconnect_device(item))
            self.context_menu.addAction(disconnect_action)
            
            self.context_menu.addSeparator()
            
            # 启动Appium服务
            start_appium_action = QAction("启动Appium服务", self)
            start_appium_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            start_appium_action.triggered.connect(lambda: self._start_appium_for_device(item))
            self.context_menu.addAction(start_appium_action)
            
            # 停止Appium服务
            stop_appium_action = QAction("停止Appium服务", self)
            stop_appium_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
            stop_appium_action.triggered.connect(lambda: self._stop_appium_for_device(item))
            self.context_menu.addAction(stop_appium_action)
            
            self.context_menu.addSeparator()
            
            # 刷新设备信息
            refresh_action = QAction("刷新设备信息", self)
            refresh_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
            refresh_action.triggered.connect(lambda: self._refresh_device(item))
            self.context_menu.addAction(refresh_action)
            
            # 更新菜单项状态
            self._update_button_states()
            
            # 显示菜单
            self.context_menu.exec_(self.devices_tree.viewport().mapToGlobal(pos))
        
        except Exception as e:
            logger.error(f"显示右键菜单失败: {e}")
            self._show_error("错误", f"显示右键菜单失败: {e}")
    
    def _show_appium_context_menu(self, pos):
        """显示Appium服务右键菜单"""
        item = self.appium_table.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        # 停止服务
        stop_action = QAction("停止服务", self)
        stop_action.triggered.connect(lambda: self._stop_appium_server(item.row()))
        menu.addAction(stop_action)
        
        # 重启服务
        restart_action = QAction("重启服务", self)
        restart_action.triggered.connect(lambda: self._restart_appium_server(item.row()))
        menu.addAction(restart_action)
        
        menu.addSeparator()
        
        # 查看日志
        view_log_action = QAction("查看日志", self)
        view_log_action.triggered.connect(lambda: self._view_appium_log(item.row()))
        menu.addAction(view_log_action)
        
        menu.exec_(self.appium_table.viewport().mapToGlobal(pos))
    
    def _on_device_selected(self):
        """设备选择处理"""
        try:
            items = self.devices_tree.selectedItems()
            if not items:
                return
            
            item = items[0]
            device_id = item.text(0)
            device_info = self.device_manager.get_device_info(device_id)
            
            if device_info:
                self._selected_device = device_info
                self.device_selected.emit(device_info)
                logger.debug(f"已选择设备: {device_id}")
        
        except Exception as e:
            logger.error(f"设备选择处理失败: {e}")
    
    def refresh_devices(self):
        """刷新设备列表"""
        try:
            # 显示加载状态
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("正在刷新...")
            
            # 清空设备列表
            self.devices_tree.clear()
                
            # 获取设备列表
            devices = self.device_manager.get_devices()
            
            # 添加设备到树形列表
            for device in devices:
                item = QTreeWidgetItem(self.devices_tree)
                item.setText(0, device['id'])
                item.setText(1, device.get('model', 'unknown'))
                item.setText(2, device.get('platform_version', 'unknown'))
                item.setText(3, device.get('status', 'unknown'))
                item.setText(4, device.get('battery', 'unknown'))
                item.setText(5, device.get('memory', 'unknown'))
                
                # 格式化存储信息显示
                storage = device.get('storage', {})
                if isinstance(storage, dict):
                    storage_text = (
                        f"总共: {storage.get('total', 'unknown')} | "
                        f"已用: {storage.get('used', 'unknown')} | "
                        f"可用: {storage.get('free', 'unknown')}"
                    )
                else:
                    storage_text = str(storage)
                item.setText(6, storage_text)
                
                # 设置状态颜色和图标
                status = device.get('status', '').lower()
                if status == 'connected':
                    item.setForeground(3, QColor('#4CAF50'))  # 绿色
                    item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
                elif status == 'disconnected':
                    item.setForeground(3, QColor('#F44336'))  # 红色
                    item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical))
                elif status == 'error':
                    item.setForeground(3, QColor('#FF9800'))  # 橙色
                    item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
                
                # 设置提示信息
                tooltip = (
                    f"设备ID: {device['id']}\n"
                    f"型号: {device.get('model', 'unknown')}\n"
                    f"系统版本: {device.get('platform_version', 'unknown')}\n"
                    f"状态: {device.get('status', 'unknown')}"
                )
                for i in range(self.devices_tree.columnCount()):
                    item.setToolTip(i, tooltip)
                
                # 如果是当前选中的设备，保持选中状态
                if (self._selected_device and 
                    self._selected_device.get('id') == device['id']):
                    item.setSelected(True)
            
            # 恢复按钮状态
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("刷新")
            
            # 更新按钮状态
            self._update_button_states()
            
            logger.info(f"设备列表刷新完成，共 {len(devices)} 个设备")
        
        except Exception as e:
            logger.error(f"刷新设备列表失败: {e}")
            self._show_error("错误", f"刷新设备列表失败: {e}")
            
            # 恢复按钮状态
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("刷新")
    
    def _update_button_states(self):
        """更新按钮状态"""
        try:
            # 获取选中的设备
            selected_items = self.devices_tree.selectedItems()
            has_selection = len(selected_items) > 0
            
            # 获取设备和服务状态
            devices = self.device_manager.get_devices()
            servers = self.device_manager.get_appium_servers()
            
            connected_devices = sum(1 for d in devices if d.get('status', '').lower() == 'connected')
            running_servers = len(servers)
            
            # 更新启动服务按钮状态
            self.start_btn.setEnabled(connected_devices > 0 and running_servers < connected_devices)
            
            # 更新停止服务按钮状态
            self.stop_btn.setEnabled(running_servers > 0)
            
            # 更新右键菜单状态
            if hasattr(self, 'context_menu'):
                for action in self.context_menu.actions():
                    if action.text() in ['连接设备', '断开设备', '刷新设备信息']:
                        action.setEnabled(has_selection)
                    elif action.text() == '启动Appium服务':
                        action.setEnabled(has_selection and running_servers < connected_devices)
                    elif action.text() == '停止Appium服务':
                        action.setEnabled(has_selection and running_servers > 0)
        
        except Exception as e:
            logger.error(f"更新按钮状态失败: {e}")
    
    def refresh_appium_status(self):
        """刷新Appium服务状态"""
        try:
            # 获取服务列表
            servers = self.device_manager.get_appium_servers()
            
            # 更新表格
            self.appium_table.setRowCount(len(servers))
            
            for row, server in enumerate(servers):
                # 主机
                host_item = QTableWidgetItem(server.get('host', 'unknown'))
                self.appium_table.setItem(row, 0, host_item)
                
                # 端口
                port_item = QTableWidgetItem(str(server.get('port', 'unknown')))
                self.appium_table.setItem(row, 1, port_item)
                
                # 运行时间
                uptime = format_time(server.get('uptime', 0))
                uptime_item = QTableWidgetItem(uptime)
                self.appium_table.setItem(row, 2, uptime_item)
                
                # 状态
                status = "运行中"
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor('#4CAF50'))  # 绿色
                self.appium_table.setItem(row, 3, status_item)
            
            logger.debug(f"Appium服务状态刷新完成，共 {len(servers)} 个服务")
            
            # 更新按钮状态
            has_servers = len(servers) > 0
            self.stop_btn.setEnabled(has_servers)
        
        except Exception as e:
            logger.error(f"刷新Appium服务状态失败: {e}")
            self._show_error("错误", f"刷新Appium服务状态失败: {e}")
    
    def _connect_device(self, item):
        """连接设备"""
        try:
            device_id = item.text(0)
            asyncio.create_task(self.device_manager.connect_device(device_id))
            logger.info(f"正在连接设备: {device_id}")
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            self._show_error("错误", f"连接设备失败: {e}")
    
    def _disconnect_device(self, item):
        """断开设备连接"""
        try:
            device_id = item.text(0)
            asyncio.create_task(self.device_manager.disconnect_device(device_id))
            logger.info(f"正在断开设备: {device_id}")
        except Exception as e:
            logger.error(f"断开设备失败: {e}")
            self._show_error("错误", f"断开设备失败: {e}")
    
    def _start_appium_for_device(self, item):
        """为设备启动Appium服务"""
        try:
            device_id = item.text(0)
            port = get_free_port()
            asyncio.create_task(
                self.device_manager.start_appium_server_async(port=port)
            )
            logger.info(f"正在为设备 {device_id} 启动Appium服务")
        except Exception as e:
            logger.error(f"启动Appium服务失败: {e}")
            self._show_error("错误", f"启动Appium服务失败: {e}")
    
    def _stop_appium_for_device(self, item):
        """停止设备的Appium服务"""
        try:
            device_id = item.text(0)
            device_info = self.device_manager.get_device_info(device_id)
            if device_info and 'appium_port' in device_info:
                port = device_info['appium_port']
                asyncio.create_task(
                    self.device_manager.stop_appium_server_async(port)
                )
                logger.info(f"正在停止设备 {device_id} 的Appium服务")
        except Exception as e:
            logger.error(f"停止Appium服务失败: {e}")
            self._show_error("错误", f"停止Appium服务失败: {e}")
    
    def _refresh_device(self, item):
        """刷新单个设备信息"""
        try:
            device_id = item.text(0)
            device_info = self.device_manager.get_device_info(device_id)
            if device_info:
                self._update_device_item(item, device_info)
                logger.info(f"设备 {device_id} 信息已刷新")
        except Exception as e:
            logger.error(f"刷新设备信息失败: {e}")
            self._show_error("错误", f"刷新设备信息失败: {e}")
    
    def _update_device_item(self, item: QTreeWidgetItem, device_info: dict):
        """更新设备列表项"""
        try:
            item.setText(1, device_info.get('model', 'unknown'))
            item.setText(2, device_info.get('platform_version', 'unknown'))
            item.setText(3, device_info.get('status', 'unknown'))
            item.setText(4, device_info.get('battery', 'unknown'))
            item.setText(5, device_info.get('memory', 'unknown'))
            
            storage = device_info.get('storage', {})
            if isinstance(storage, dict):
                storage_text = (
                    f"总共: {storage.get('total', 'unknown')} | "
                    f"已用: {storage.get('used', 'unknown')} | "
                    f"可用: {storage.get('free', 'unknown')}"
                )
            else:
                storage_text = str(storage)
            item.setText(6, storage_text)
            
            # 更新状态颜色
            status = device_info.get('status', '').lower()
            if status == 'connected':
                item.setForeground(3, QColor('#4CAF50'))
            elif status == 'disconnected':
                item.setForeground(3, QColor('#F44336'))
            elif status == 'error':
                item.setForeground(3, QColor('#FF9800'))
        
        except Exception as e:
            logger.error(f"更新设备列表项失败: {e}")
    
    def _stop_appium_server(self, row: int):
        """停止指定的Appium服务"""
        try:
            port = int(self.appium_table.item(row, 1).text())
            asyncio.create_task(
                self.device_manager.stop_appium_server_async(port)
            )
            logger.info(f"正在停止端口 {port} 的Appium服务")
        except Exception as e:
            logger.error(f"停止Appium服务失败: {e}")
            self._show_error("错误", f"停止Appium服务失败: {e}")
    
    def _restart_appium_server(self, row: int):
        """重启指定的Appium服务"""
        try:
            port = int(self.appium_table.item(row, 1).text())
            host = self.appium_table.item(row, 0).text()
            
            async def restart():
                await self.device_manager.stop_appium_server_async(port)
                await asyncio.sleep(1)
                await self.device_manager.start_appium_server_async(
                    host=host, port=port
                )
            
            asyncio.create_task(restart())
            logger.info(f"正在重启端口 {port} 的Appium服务")
        
        except Exception as e:
            logger.error(f"重启Appium服务失败: {e}")
            self._show_error("错误", f"重启Appium服务失败: {e}")
    
    def _view_appium_log(self, row: int):
        """查看Appium服务日志"""
        try:
            port = self.appium_table.item(row, 1).text()
            log_file = f"appium_{port}.log"
            
            if os.path.exists(log_file):
                # TODO: 实现日志查看器
                logger.info(f"查看日志文件: {log_file}")
            else:
                self._show_error("错误", f"日志文件不存在: {log_file}")
        
        except Exception as e:
            logger.error(f"查看日志失败: {e}")
            self._show_error("错误", f"查看日志失败: {e}")
    
    def start_all_appium_servers(self):
        """启动所有Appium服务"""
        try:
            # 获取设备列表
            devices = self.device_manager.get_devices()
            if not devices:
                self._show_error("错误", "没有可用的设备")
                return
            
            # 创建事件循环
            loop = asyncio.new_event_loop()
            
            async def start_servers():
                tasks = []
                for device in devices:
                    # 获取空闲端口
                    port = get_free_port()
                    if not port:
                        logger.error("无法获取空闲端口")
                        continue
                    
                    # 创建启动任务
                    task = self.device_manager.start_appium_server_async(
                        host='127.0.0.1',
                        port=port
                    )
                    tasks.append(task)
                
                # 等待所有任务完成
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    # 处理结果
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"启动Appium服务失败: {result}")
                        elif not result:
                            logger.error(f"启动Appium服务失败")
                    
                    # 在主线程中刷新服务状态
                    QTimer.singleShot(0, self.refresh_appium_status)
            
            # 在新线程中运行事件循环
            def run_async():
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(start_servers())
                except Exception as e:
                    logger.error(f"启动Appium服务失败: {e}")
                finally:
                    loop.close()
            
            thread = threading.Thread(target=run_async)
            thread.daemon = True  # 设置为守护线程
            thread.start()
            
        except Exception as e:
            logger.error(f"启动所有Appium服务失败: {e}")
            self._show_error("错误", f"启动所有Appium服务失败: {e}")
    
    def stop_all_appium_servers(self):
        """停止所有Appium服务"""
        try:
            # 获取所有运行中的Appium服务
            servers = self.device_manager.get_appium_servers()
            if not servers:
                logger.info("没有运行中的Appium服务")
                return
            
            # 禁用按钮，避免重复点击
            self.stop_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            
            # 创建事件循环
            loop = asyncio.new_event_loop()
            
            async def stop_servers():
                try:
                    tasks = []
                    for server in servers:
                        # 创建停止任务
                        task = self.device_manager.stop_appium_server_async(
                            server['port']
                        )
                        tasks.append(task)
                    
                    # 等待所有任务完成
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        # 处理结果
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.error(f"停止Appium服务失败: {result}")
                            elif not result:
                                logger.error(f"停止Appium服务失败")
                except Exception as e:
                    logger.error(f"停止服务失败: {e}")
                finally:
                    # 使用QTimer在主线程中更新UI
                    QTimer.singleShot(0, self._on_stop_servers_complete)
            
            # 在新线程中运行事件循环
            def run_async():
                try:
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(stop_servers())
                except Exception as e:
                    logger.error(f"停止Appium服务失败: {e}")
                finally:
                    loop.close()
            
            thread = threading.Thread(target=run_async)
            thread.daemon = True  # 设置为守护线程
            thread.start()
            
            logger.info("正在停止所有Appium服务")
        
        except Exception as e:
            logger.error(f"停止所有Appium服务失败: {e}")
            self._show_error("错误", f"停止所有Appium服务失败: {e}")
            self.stop_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
    
    def _on_stop_servers_complete(self):
        """停止服务完成后的处理"""
        try:
            # 刷新服务状态
            self.refresh_appium_status()
            
            # 重新启用按钮
            self.stop_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            
            logger.info("所有Appium服务已停止")
        except Exception as e:
            logger.error(f"更新UI状态失败: {e}")
            self._show_error("错误", f"更新UI状态失败: {e}")
    
    def _show_error(self, title: str, message: str):
        """显示错误对话框"""
        QMessageBox.critical(
            self,
            title,
            message,
            QMessageBox.StandardButton.Ok
        )
    
    def _start_refresh_timer(self):
        """启动刷新定时器"""
        try:
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self._refresh_all)
            self.refresh_timer.start(self.refresh_interval)
            logger.info("刷新定时器已启动")
        except Exception as e:
            logger.error(f"启动刷新定时器失败: {e}")
    
    def _refresh_all(self):
        """刷新所有状态"""
        try:
            self.refresh_devices()
            self.refresh_appium_status()
        except Exception as e:
            logger.error(f"刷新状态失败: {e}")
    
    def __del__(self):
        """清理资源"""
        try:
            if self.refresh_timer:
                self.refresh_timer.stop()
            logger.info("设备标签页资源已清理")
            
        except Exception as e:
            logger.error(f"清理资源失败: {e}") 
    
    def set_platform(self, platform: str):
        """设置当前平台
        
        Args:
            platform: 平台类型 (android/ios)
        """
        try:
            if platform != self.current_platform:
                self.current_platform = platform.lower()
                # 清空设备列表
                self.devices_tree.clear()
                # 刷新设备列表
                self.refresh_devices()
                logger.info(f"已切换到 {platform} 平台")
        except Exception as e:
            logger.error(f"设置平台失败: {e}")
            self._show_error("错误", f"设置平台失败: {e}")