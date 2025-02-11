from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QProgressBar, QHeaderView, QTableWidget,
    QTableWidgetItem, QSplitter, QStyle, QMenu, QComboBox,
    QSpacerItem, QSizePolicy, QLineEdit, QCheckBox,
    QFileDialog, QScrollArea, QToolButton, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QPoint
from PySide6.QtGui import QIcon, QColor, QPalette, QTextCursor, QAction
from loguru import logger
from core.recorder import ActionRecorder
import time
import os
import json
import asyncio
from typing import Dict, Optional, List
from utils.errors import RecordError
from utils.constants import DeviceStatus
from utils.helpers import format_time, format_size
from .dialogs.step_editor import StepEditorDialog

class RecordTab(QWidget):
    # 信号定义
    recording_started = Signal()  # 录制开始信号
    recording_stopped = Signal()  # 录制停止信号
    recording_paused = Signal()   # 录制暂停信号
    recording_resumed = Signal()  # 录制继续信号
    
    def __init__(self, config: Dict, parent=None):
        """初始化录制标签页
        
        Args:
            config: 配置字典
            parent: 父窗口
        """
        super().__init__(parent)
        self.setObjectName("record_tab")
        
        # 初始化成员变量
        self.config = config
        self._device_info = None  # 设备信息
        self.is_recording = False  # 录制状态
        self.is_paused = False    # 暂停状态
        self.record_events = []   # 录制事件列表
        self.start_time = 0       # 开始时间
        self.elapsed_time = 0     # 已录制时间
        
        # 初始化UI
        self.init_ui()
        
        # 启动状态更新定时器
        self._start_status_timer()
        
        logger.info("录制标签页初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 设备信息区域
        device_frame = QFrame()
        device_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        device_layout = QVBoxLayout()
        
        # 设备标签
        self.device_label = QLabel("设备: 未连接")
        self.device_label.setStyleSheet("color: #F44336;")  # 红色表示未连接
        device_layout.addWidget(self.device_label)
        
        device_frame.setLayout(device_layout)
        main_layout.addWidget(device_frame)
        
        # 录制控制区域
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        control_layout = QVBoxLayout()
        
        # 录制控制标题
        control_title = QLabel("录制控制")
        control_title.setObjectName("title")
        control_layout.addWidget(control_title)
        
        # 录制信息输入区域
        info_layout = QGridLayout()
        
        # 模块输入
        info_layout.addWidget(QLabel("模块:"), 0, 0)
        self.module_edit = QLineEdit()
        self.module_edit.setPlaceholderText("请输入模块名称")
        info_layout.addWidget(self.module_edit, 0, 1)
        
        # 操作名称输入
        info_layout.addWidget(QLabel("操作名称:"), 1, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入操作名称")
        info_layout.addWidget(self.name_edit, 1, 1)
        
        # 操作描述输入
        info_layout.addWidget(QLabel("描述:"), 2, 0)
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("请输入操作描述")
        info_layout.addWidget(self.desc_edit, 2, 1)
        
        control_layout.addLayout(info_layout)
        
        # 录制选项区域
        options_layout = QHBoxLayout()
        
        # 录制类型选项
        self.click_check = QCheckBox("点击")
        self.click_check.setChecked(True)
        options_layout.addWidget(self.click_check)
        
        self.swipe_check = QCheckBox("滑动")
        self.swipe_check.setChecked(True)
        options_layout.addWidget(self.swipe_check)
        
        self.text_check = QCheckBox("文本")
        self.text_check.setChecked(True)
        options_layout.addWidget(self.text_check)
        
        self.key_check = QCheckBox("按键")
        self.key_check.setChecked(True)
        options_layout.addWidget(self.key_check)
        
        control_layout.addLayout(options_layout)
        
        # 录制控制按钮
        buttons_layout = QHBoxLayout()
        
        # 开始/停止录制按钮
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.record_btn.setEnabled(False)
        self.record_btn.clicked.connect(self.toggle_recording)
        buttons_layout.addWidget(self.record_btn)
        
        # 暂停/继续按钮
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        buttons_layout.addWidget(self.pause_btn)
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_recording)
        buttons_layout.addWidget(self.save_btn)
        
        # 清空按钮
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self.clear_recording)
        buttons_layout.addWidget(self.clear_btn)
        
        control_layout.addLayout(buttons_layout)
        
        # 状态显示
        status_layout = QHBoxLayout()
        
        # 录制状态
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        
        # 录制时长
        self.duration_label = QLabel("00:00:00")
        status_layout.addWidget(self.duration_label)
        
        # 事件计数
        self.count_label = QLabel("0 个事件")
        status_layout.addWidget(self.count_label)
        
        control_layout.addLayout(status_layout)
        
        control_frame.setLayout(control_layout)
        main_layout.addWidget(control_frame)
        
        # 录制事件列表区域
        events_frame = QFrame()
        events_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        events_layout = QVBoxLayout()
        
        # 事件列表标题
        events_title = QLabel("录制事件")
        events_title.setObjectName("title")
        events_layout.addWidget(events_title)
        
        # 事件列表
        self.events_table = QTableWidget()
        self.events_table.setColumnCount(5)
        self.events_table.setHorizontalHeaderLabels([
            "时间", "类型", "目标", "动作", "参数"
        ])
        self.events_table.setAlternatingRowColors(True)
        events_layout.addWidget(self.events_table)
        
        events_frame.setLayout(events_layout)
        main_layout.addWidget(events_frame)
        
        self.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 5px;
            }
            QLabel#title {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                padding: 5px 0;
            }
            QPushButton {
                padding: 5px 10px;
                border-radius: 3px;
                border: 1px solid #ddd;
                background-color: #f5f5f5;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
    
    def toggle_recording(self):
        """切换录制状态"""
        try:
            if not self.is_recording:
                # 检查必填项
                if not self.module_edit.text().strip():
                    self._show_error("错误", "请输入模块名称")
                    return
                if not self.name_edit.text().strip():
                    self._show_error("错误", "请输入操作名称")
                    return
                
                # 开始录制
                asyncio.create_task(self.start_recording())
            else:
                # 停止录制
                asyncio.create_task(self.stop_recording())
        
        except Exception as e:
            logger.error(f"切换录制状态失败: {e}")
            self._show_error("错误", f"切换录制状态失败: {e}")
    
    async def start_recording(self):
        """开始录制"""
        try:
            if not self._device_info:
                raise ValueError("未连接设备")
            
            logger.info("开始录制")
            self.is_recording = True
            self.is_paused = False
            self.start_time = time.time()
            self.record_events.clear()
            
            # 更新UI状态
            self._update_record_button()
            self.pause_btn.setEnabled(True)
            self.clear_btn.setEnabled(False)
            
            # 发送录制开始信号
            self.recording_started.emit()
            
            # 添加录制开始日志
            self._append_log("开始录制")
            
        except Exception as e:
            logger.error(f"开始录制失败: {e}")
            self._show_error("错误", f"开始录制失败: {e}")
            self.is_recording = False
            self._update_record_button()
    
    async def stop_recording(self):
        """停止录制"""
        try:
            if not self.is_recording:
                return
            
            logger.info("停止录制")
            self.is_recording = False
            self.is_paused = False
            
            # 更新UI状态
            self._update_record_button()
            self.pause_btn.setEnabled(False)
            self.save_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
            
            # 更新状态显示
            self.status_label.setText("已停止")
            
            # 发送录制停止信号
            self.recording_stopped.emit()
            
            # 添加录制停止日志
            self._append_log("停止录制")
            
        except Exception as e:
            logger.error(f"停止录制失败: {e}")
            self._show_error("错误", f"停止录制失败: {e}")
        finally:
            if self.recorder:
                self.recorder = None
    
    def save_recording(self):
        """保存录制结果"""
        try:
            if not self.record_events:
                self._show_error("错误", "没有可保存的录制结果")
                return
            
            # 获取保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存录制结果",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # 禁用保存按钮
            self.save_btn.setEnabled(False)
            
            # 准备保存数据
            save_data = {
                'module': self.module_edit.text().strip(),
                'name': self.name_edit.text().strip(),
                'description': self.desc_edit.text().strip(),
                'device': self._device_info,
                'events': self.record_events,
                'start_time': self.start_time,
                'end_time': time.time(),
                'duration': time.time() - self.start_time
            }
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            
            # 添加保存日志
            self._append_log(f"录制结果已保存至: {file_path}")
            logger.info(f"录制结果已保存: {file_path}")
            
            # 显示成功消息
            QMessageBox.information(
                self,
                "成功",
                f"录制结果已保存至:\n{file_path}"
            )
            
        except Exception as e:
            logger.error(f"保存录制结果失败: {e}")
            self._show_error("错误", f"保存录制结果失败: {e}")
        finally:
            # 恢复保存按钮状态
            self.save_btn.setEnabled(True)
    
    def clear_recording(self):
        """清空录制结果"""
        try:
            if not self.record_events:
                return
            
            # 显示确认对话框
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要清空录制结果吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            # 清空录制数据
            self.record_events.clear()
            self.events_table.setRowCount(0)
            self.count_label.setText("0 个事件")
            self.duration_label.setText("00:00:00")
            
            # 清空输入框
            self.module_edit.clear()
            self.name_edit.clear()
            self.desc_edit.clear()
            
            # 更新按钮状态
            self.save_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            
            # 添加清空日志
            self._append_log("录制结果已清空")
            logger.info("录制结果已清空")
            
        except Exception as e:
            logger.error(f"清空录制结果失败: {e}")
            self._show_error("错误", f"清空录制结果失败: {e}")
    
    def _append_log(self, message: str):
        """添加日志记录"""
        try:
            # 获取当前时间
            current_time = time.strftime("%H:%M:%S")
            
            # 在事件表格中添加一行
            row = self.events_table.rowCount()
            self.events_table.insertRow(row)
            
            # 设置单元格内容
            self.events_table.setItem(row, 0, QTableWidgetItem(current_time))
            self.events_table.setItem(row, 1, QTableWidgetItem("LOG"))
            self.events_table.setItem(row, 2, QTableWidgetItem("-"))
            self.events_table.setItem(row, 3, QTableWidgetItem(message))
            self.events_table.setItem(row, 4, QTableWidgetItem("-"))
            
            # 滚动到最新行
            self.events_table.scrollToBottom()
            
        except Exception as e:
            logger.error(f"添加日志记录失败: {e}")
    
    def _start_status_timer(self):
        """启动状态更新定时器"""
        try:
            self._status_timer = QTimer()
            self._status_timer.timeout.connect(self._update_status)
            self._status_timer.start(1000)  # 每秒更新一次
            logger.debug("状态更新定时器已启动")
        except Exception as e:
            logger.error(f"启动状态更新定时器失败: {e}")
    
    def _update_status(self):
        """更新状态显示"""
        try:
            if not self.is_recording:
                return
            
            # 更新录制时长
            elapsed = time.time() - self.start_time
            self.duration_label.setText(time.strftime("%H:%M:%S", time.gmtime(elapsed)))
            
            # 更新事件计数
            event_count = len(self.record_events)
            self.count_label.setText(f"{event_count} 个事件")
            
            # 更新状态文本
            if self.is_paused:
                self.status_label.setText("已暂停")
            else:
                self.status_label.setText("录制中")
            
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")
    
    def _update_record_button(self):
        """更新录制按钮状态"""
        try:
            # 根据设备连接状态和录制状态更新按钮
            if self._device_info:
                self.record_btn.setEnabled(True)
                if self.is_recording:
                    self.record_btn.setText("停止录制")
                    self.record_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
                else:
                    self.record_btn.setText("开始录制")
                    self.record_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            else:
                self.record_btn.setEnabled(False)
                self.record_btn.setText("开始录制")
                self.record_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            
        except Exception as e:
            logger.error(f"更新录制按钮状态失败: {e}")
    
    def _show_error(self, title: str, message: str):
        """显示错误对话框"""
        QMessageBox.critical(
            self,
            title,
            message,
            QMessageBox.StandardButton.Ok
        )
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, '_status_timer') and self._status_timer is not None:
                self._status_timer.stop()
            if hasattr(self, 'is_recording') and self.is_recording:
                if hasattr(self, 'recorder') and self.recorder is not None:
                    asyncio.create_task(self.stop_recording())
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
    
    def _handle_error(self, error_msg: str):
        """处理错误"""
        try:
            # 显示错误消息
            QMessageBox.critical(self, "错误", error_msg)
            self._append_log(f"错误: {error_msg}")
            
            # 重置状态
            self.is_recording = False
            self._update_record_button()
        
        except Exception as e:
            logger.error(f"处理错误失败: {e}")
    
    def set_device(self, device_info: Dict):
        """设置设备信息
        
        Args:
            device_info: 设备信息字典
        """
        try:
            logger.info(f"设置设备信息: {device_info}")
            self._device_info = device_info.copy()
            
            # 更新设备信息显示
            if device_info:
                device_name = f"{device_info.get('model', 'Unknown')} ({device_info.get('id', 'Unknown')})"
                self.device_label.setText(f"设备: {device_name}")
                self.device_label.setStyleSheet("color: #4CAF50;")  # 绿色表示已连接
            else:
                self.device_label.setText("设备: 未连接")
                self.device_label.setStyleSheet("color: #F44336;")  # 红色表示未连接
            
            # 更新按钮状态
            self._update_record_button()
            
        except Exception as e:
            logger.error(f"设置设备信息失败: {e}")
            self._show_error("错误", f"设置设备信息失败: {e}")
    
    def toggle_pause(self):
        """切换暂停状态"""
        try:
            if not self.is_recording:
                return
            
            if not self.is_paused:
                # 暂停录制
                self.is_paused = True
                self.pause_btn.setText("继续")
                self.status_label.setText("已暂停")
                self.recording_paused.emit()
                logger.info("录制已暂停")
            else:
                # 继续录制
                self.is_paused = False
                self.pause_btn.setText("暂停")
                self.status_label.setText("录制中")
                self.recording_resumed.emit()
                logger.info("录制已继续")
        
        except Exception as e:
            logger.error(f"切换暂停状态失败: {e}")
            self._handle_error(str(e))
    
    def export_script(self):
        """导出录制脚本"""
        try:
            if not self.recorder or not self.recorder.actions:
                raise ValueError("没有可导出的录制内容")
            
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出脚本",
                os.path.join(os.getcwd(), "scripts"),
                "Python Files (*.py);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # 生成脚本内容
            script_content = self.recorder.generate_script(
                self.module_combo.currentText(),
                self.name_edit.text(),
                self.desc_edit.text()
            )
            
            # 保存脚本
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            logger.info(f"脚本已导出: {file_path}")
            QMessageBox.information(self, "提示", "脚本导出成功")
        
        except Exception as e:
            logger.error(f"导出脚本失败: {e}")
            self._handle_error(str(e))
    
    def edit_steps(self):
        """编辑录制步骤"""
        try:
            if not self.recorder or not self.recorder.actions:
                raise ValueError("没有可编辑的录制内容")
            
            # 创建步骤编辑对话框
            dialog = StepEditorDialog(self.recorder.actions, self)
            
            # 连接信号
            dialog.steps_updated.connect(self._on_steps_updated)
            
            # 显示对话框
            dialog.exec()
            
            logger.info("打开步骤编辑对话框")
        
        except Exception as e:
            logger.error(f"编辑步骤失败: {e}")
            self._handle_error(str(e))
    
    def _on_steps_updated(self, steps: List[Dict]):
        """步骤更新处理"""
        try:
            if self.recorder:
                # 更新录制器中的步骤
                self.recorder.actions = steps
                
                # 更新事件列表
                self._update_event_list()
                
                logger.info(f"步骤已更新，共 {len(steps)} 个步骤")
        
        except Exception as e:
            logger.error(f"更新步骤失败: {e}")
            self._handle_error(str(e))
    
    def _show_event_context_menu(self, pos: QPoint):
        """显示事件右键菜单"""
        item = self.event_tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        # 编辑事件
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self._edit_event(item))
        menu.addAction(edit_action)
        
        # 删除事件
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_event(item))
        menu.addAction(delete_action)
        
        menu.exec_(self.event_tree.viewport().mapToGlobal(pos))
    
    def _edit_event(self, item: QTreeWidgetItem):
        """编辑事件"""
        try:
            # TODO: 实现事件编辑对话框
            logger.info(f"编辑事件: {item.text(0)}")
        
        except Exception as e:
            logger.error(f"编辑事件失败: {e}")
            self._handle_error(str(e))
    
    def _delete_event(self, item: QTreeWidgetItem):
        """删除事件"""
        try:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要删除该事件吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                index = self.event_tree.indexOfTopLevelItem(item)
                if index >= 0:
                    self.event_tree.takeTopLevelItem(index)
                    if self.recorder:
                        self.recorder.actions.pop(index)
                    logger.info(f"事件已删除: {item.text(0)}")
        
        except Exception as e:
            logger.error(f"删除事件失败: {e}")
            self._handle_error(str(e))
    
    def _update_event_list(self):
        """更新事件列表"""
        try:
            if not self.recorder:
                return
            
            # 清空列表
            self.event_tree.clear()
            
            # 添加事件
            for action in self.recorder.actions:
                item = QTreeWidgetItem(self.event_tree)
                item.setText(0, action.get('time', ''))
                item.setText(1, action.get('type', ''))
                item.setText(2, action.get('target', ''))
                item.setText(3, action.get('action', ''))
                item.setText(4, str(action.get('params', {})))
                
                # 设置图标
                action_type = action.get('type', '').lower()
                if action_type == 'click':
                    item.setIcon(1, self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
                elif action_type == 'swipe':
                    item.setIcon(1, self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
                elif action_type == 'text':
                    item.setIcon(1, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                elif action_type == 'key':
                    item.setIcon(1, self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
            
            # 滚动到最新项
            if self.event_tree.topLevelItemCount() > 0:
                self.event_tree.scrollToItem(
                    self.event_tree.topLevelItem(
                        self.event_tree.topLevelItemCount() - 1
                    )
                )
        
        except Exception as e:
            logger.error(f"更新事件列表失败: {e}")
    
    def update_config(self, config: Dict) -> None:
        """更新配置
        
        Args:
            config: 新的配置字典
        """
        try:
            self.config.update(config)
            
            # 更新录制选项
            if 'record' in config:
                record_config = config['record']
                self.refresh_interval = record_config.get('refresh_interval', 5000)
                
                # 更新过滤选项
                filter_options = record_config.get('filter_options', {})
                self.click_check.setChecked(filter_options.get('click', True))
                self.swipe_check.setChecked(filter_options.get('swipe', True))
                self.text_check.setChecked(filter_options.get('text', True))
                self.key_check.setChecked(filter_options.get('key', True))
            
            logger.info("录制标签页配置已更新")
        
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            self._handle_error(str(e)) 