from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QProgressBar, QHeaderView, QTableWidget,
    QTableWidgetItem, QSplitter, QStyle, QMenu, QComboBox,
    QSpacerItem, QSizePolicy, QLineEdit, QCheckBox,
    QFileDialog, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPoint
from PySide6.QtGui import QIcon, QColor, QPalette, QAction
from loguru import logger
import time
import os
import json
import asyncio
from typing import Dict, Optional, List
from utils.errors import PlaybackError
from utils.constants import DeviceStatus
from utils.helpers import format_time, format_size

class PlaybackTab(QWidget):
    # 定义信号
    playback_started = Signal()  # 回放开始信号
    playback_stopped = Signal()  # 回放停止信号
    playback_paused = Signal()   # 回放暂停信号
    playback_resumed = Signal()  # 回放继续信号
    
    def __init__(self, config: Dict, parent=None):
        """初始化回放标签页
        
        Args:
            config: 配置字典
            parent: 父窗口
        """
        super().__init__(parent)
        self.setObjectName("playback_tab")
        
        # 初始化成员变量
        self.config = config
        self.current_device = None
        self.is_playing = False
        self.is_paused = False
        self.current_script = None
        self.refresh_interval = 5000  # 刷新间隔（毫秒）
        self.max_retries = 3  # 最大重试次数
        self.retry_interval = 2  # 重试间隔（秒）
        
        # 初始化UI
        self.init_ui()
        
        logger.info("回放标签页初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建设备信息区域
        device_frame = self._create_device_frame()
        main_layout.addWidget(device_frame)
        
        # 创建脚本控制区域
        control_frame = self._create_control_frame()
        main_layout.addWidget(control_frame)
        
        # 创建回放状态区域
        status_frame = self._create_status_frame()
        main_layout.addWidget(status_frame)
        
        self.setLayout(main_layout)
    
    def _create_device_frame(self):
        """创建设备信息区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("设备信息")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 设备信息表格
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(2)
        self.device_table.setHorizontalHeaderLabels(["属性", "值"])
        self.device_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.device_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.device_table.setAlternatingRowColors(True)
        layout.addWidget(self.device_table)
        
        frame.setLayout(layout)
        return frame
    
    def _create_control_frame(self):
        """创建脚本控制区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("脚本控制")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 脚本选择区域
        script_layout = QHBoxLayout()
        
        script_label = QLabel("脚本:")
        script_layout.addWidget(script_label)
        
        self.script_path = QLineEdit()
        self.script_path.setReadOnly(True)
        script_layout.addWidget(self.script_path)
        
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self._browse_script)
        script_layout.addWidget(browse_btn)
        
        layout.addLayout(script_layout)
        
        # 控制按钮区域
        btn_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("开始回放")
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.clicked.connect(self.toggle_playback)
        btn_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop_playback)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        # 回放选项
        options_layout = QHBoxLayout()
        
        retry_label = QLabel("重试次数:")
        options_layout.addWidget(retry_label)
        
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(self.max_retries)
        options_layout.addWidget(self.retry_spin)
        
        interval_label = QLabel("重试间隔(秒):")
        options_layout.addWidget(interval_label)
        
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 30)
        self.interval_spin.setValue(self.retry_interval)
        options_layout.addWidget(self.interval_spin)
        
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        frame.setLayout(layout)
        return frame
    
    def _create_status_frame(self):
        """创建回放状态区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题
        title = QLabel("回放状态")
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 状态信息
        status_layout = QHBoxLayout()
        
        status_label = QLabel("状态:")
        status_layout.addWidget(status_label)
        
        self.status_text = QLabel("就绪")
        status_layout.addWidget(self.status_text)
        
        status_layout.addStretch()
        
        progress_label = QLabel("进度:")
        status_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)
        
        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        frame.setLayout(layout)
        return frame
    
    def update_config(self, config: Dict) -> None:
        """更新配置
        
        Args:
            config: 新的配置字典
        """
        try:
            self.config.update(config)
            
            # 更新回放选项
            if 'playback' in config:
                playback_config = config['playback']
                self.refresh_interval = playback_config.get('refresh_interval', 5000)
                
                # 更新重试选项
                retry_options = playback_config.get('retry_options', {})
                self.max_retries = retry_options.get('max_retries', 3)
                self.retry_interval = retry_options.get('retry_interval', 2)
                
                # 更新UI控件
                self.retry_spin.setValue(self.max_retries)
                self.interval_spin.setValue(self.retry_interval)
            
            logger.info("回放标签页配置已更新")
        
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            self._handle_error(str(e))
    
    def _browse_script(self):
        """浏览脚本文件"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择脚本文件",
                "",
                "JSON文件 (*.json);;所有文件 (*.*)"
            )
            
            if file_path:
                self.script_path.setText(file_path)
                self.current_script = self._load_script(file_path)
                if self.current_script:
                    self.play_btn.setEnabled(True)
                    self._append_log(f"已加载脚本: {os.path.basename(file_path)}")
        
        except Exception as e:
            logger.error(f"浏览脚本文件失败: {e}")
            self._handle_error(str(e))
    
    def _load_script(self, file_path: str) -> Optional[Dict]:
        """加载脚本文件
        
        Args:
            file_path: 脚本文件路径
            
        Returns:
            脚本数据字典或None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            # TODO: 验证脚本格式
            
            return script_data
        
        except Exception as e:
            logger.error(f"加载脚本文件失败: {e}")
            self._handle_error(str(e))
            return None
    
    def toggle_playback(self):
        """切换回放状态"""
        if not self.is_playing:
            self.start_playback()
        else:
            self.stop_playback()
    
    def start_playback(self):
        """开始回放"""
        try:
            if not self.current_device:
                raise PlaybackError("未选择设备")
            
            if not self.current_script:
                raise PlaybackError("未加载脚本")
            
            self.is_playing = True
            self.is_paused = False
            
            # 更新UI状态
            self.play_btn.setText("停止回放")
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            
            # 发送信号
            self.playback_started.emit()
            
            # 开始回放任务
            self._start_playback_task()
            
            self._append_log("开始回放")
            
        except Exception as e:
            logger.error(f"开始回放失败: {e}")
            self._handle_error(str(e))
    
    def stop_playback(self):
        """停止回放"""
        try:
            self.is_playing = False
            self.is_paused = False
            
            # 更新UI状态
            self.play_btn.setText("开始回放")
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            
            # 发送信号
            self.playback_stopped.emit()
            
            self._append_log("停止回放")
            
        except Exception as e:
            logger.error(f"停止回放失败: {e}")
            self._handle_error(str(e))
    
    def toggle_pause(self):
        """切换暂停状态"""
        try:
            if not self.is_playing:
                return
            
            self.is_paused = not self.is_paused
            
            # 更新UI状态
            if self.is_paused:
                self.pause_btn.setText("继续")
                self.pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
                self.playback_paused.emit()
                self._append_log("暂停回放")
            else:
                self.pause_btn.setText("暂停")
                self.pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
                self.playback_resumed.emit()
                self._append_log("继续回放")
            
        except Exception as e:
            logger.error(f"切换暂停状态失败: {e}")
            self._handle_error(str(e))
    
    def _start_playback_task(self):
        """启动回放任务"""
        try:
            # TODO: 实现回放任务
            pass
            
        except Exception as e:
            logger.error(f"启动回放任务失败: {e}")
            self._handle_error(str(e))
    
    def update_device_info(self, device_info: Dict):
        """更新设备信息
        
        Args:
            device_info: 设备信息字典
        """
        try:
            self.current_device = device_info
            
            # 更新设备信息表格
            self.device_table.setRowCount(0)
            for key, value in device_info.items():
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                self.device_table.setItem(row, 0, QTableWidgetItem(str(key)))
                self.device_table.setItem(row, 1, QTableWidgetItem(str(value)))
            
            # 启用控制按钮
            self.play_btn.setEnabled(bool(self.current_script))
            
            logger.info(f"设备信息已更新: {device_info.get('id')}")
            
        except Exception as e:
            logger.error(f"更新设备信息失败: {e}")
            self._handle_error(str(e))
    
    def clear_device_info(self):
        """清除设备信息"""
        try:
            self.current_device = None
            self.device_table.setRowCount(0)
            
            # 禁用控制按钮
            self.play_btn.setEnabled(False)
            
            logger.info("设备信息已清除")
            
        except Exception as e:
            logger.error(f"清除设备信息失败: {e}")
            self._handle_error(str(e))
    
    def _handle_error(self, error_msg: str):
        """处理错误
        
        Args:
            error_msg: 错误信息
        """
        QMessageBox.critical(self, "错误", error_msg)
    
    def _append_log(self, message: str):
        """添加日志
        
        Args:
            message: 日志消息
        """
        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    def on_tab_activated(self):
        """标签页激活处理"""
        pass
    
    def closeEvent(self, event):
        """关闭事件处理"""
        try:
            if self.is_playing:
                reply = QMessageBox.question(
                    self,
                    "确认",
                    "回放正在进行中，确定要关闭吗？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.stop_playback()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
            
        except Exception as e:
            logger.error(f"关闭事件处理失败: {e}")
            event.accept() 