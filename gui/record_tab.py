from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QMessageBox,
    QProgressBar, QSpinBox, QComboBox, QCheckBox,
    QFileDialog, QScrollArea, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QIcon, QColor, QPalette, QTextCursor
from loguru import logger
from core.recorder import ActionRecorder
import time
import os

class RecordTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setObjectName("record_tab")
        self.config = config
        self.recorder = None
        self.recording = False
        self.current_device = None  # 添加设备信息属性
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        
        # 录制控制区域
        control_frame = self._create_control_frame()
        splitter.addWidget(control_frame)
        
        # 录制日志区域
        log_frame = self._create_log_frame()
        splitter.addWidget(log_frame)
        
        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _create_control_frame(self):
        """创建录制控制区域"""
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
        
        # 标题
        title = QLabel("录制控制")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
        """)
        layout.addWidget(title)
        
        # 录制设置
        settings_layout = QHBoxLayout()
        
        # 录制间隔设置
        interval_layout = QVBoxLayout()
        interval_label = QLabel("录制间隔(秒):")
        interval_label.setStyleSheet("color: #666666;")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(2)
        self.interval_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
            }
            QSpinBox:hover {
                border-color: #4CAF50;
            }
        """)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        settings_layout.addLayout(interval_layout)
        
        # 录制模式选择
        mode_layout = QVBoxLayout()
        mode_label = QLabel("录制模式:")
        mode_label.setStyleSheet("color: #666666;")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["完整模式", "简单模式"])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background: white;
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
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        settings_layout.addLayout(mode_layout)
        
        # 保存设置
        save_layout = QVBoxLayout()
        save_label = QLabel("保存设置:")
        save_label.setStyleSheet("color: #666666;")
        self.auto_save_check = QCheckBox("自动保存")
        self.auto_save_check.setStyleSheet("""
            QCheckBox {
                color: #666666;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #dcdcdc;
                background: white;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #4CAF50;
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        save_layout.addWidget(save_label)
        save_layout.addWidget(self.auto_save_check)
        settings_layout.addLayout(save_layout)
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        # 开始录制按钮
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.record_btn.clicked.connect(self.toggle_recording)
        
        # 保存按钮
        self.save_btn = QPushButton("保存记录")
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.save_btn.clicked.connect(self.save_recording)
        
        # 清除按钮
        self.clear_btn = QPushButton("清除记录")
        self.clear_btn.setEnabled(False)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_recording)
        
        control_layout.addWidget(self.record_btn)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.clear_btn)
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        # 录制进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dcdcdc;
                border-radius: 2px;
                text-align: center;
                background-color: #f5f5f5;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        frame.setLayout(layout)
        return frame
    
    def _create_log_frame(self):
        """创建录制日志区域"""
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
        
        # 标题
        title = QLabel("录制日志")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
        """)
        layout.addWidget(title)
        
        # 日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dcdcdc;
                border-radius: 3px;
                background-color: #fafafa;
                padding: 5px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_text)
        
        frame.setLayout(layout)
        return frame
    
    def toggle_recording(self):
        """切换录制状态"""
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """开始录制"""
        try:
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # 初始化录制器
            interval = self.interval_spin.value()
            mode = "full" if self.mode_combo.currentText() == "完整模式" else "simple"
            
            self.recorder = ActionRecorder(
                interval=interval,
                mode=mode,
                auto_save=self.auto_save_check.isChecked()
            )
            
            # 开始录制
            if self.recorder.start_recording():
                self.recording = True
                self.record_btn.setText("停止录制")
                self.record_btn.setStyleSheet("""
                    QPushButton {
                        padding: 8px 20px;
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-weight: bold;
                        min-width: 100px;
                    }
                    QPushButton:hover {
                        background-color: #e53935;
                    }
                    QPushButton:pressed {
                        background-color: #d32f2f;
                    }
                """)
                
                # 禁用设置控件
                self.interval_spin.setEnabled(False)
                self.mode_combo.setEnabled(False)
                self.auto_save_check.setEnabled(False)
                
                # 更新日志
                self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 开始录制...")
                self.log_text.append(f"录制间隔: {interval}秒")
                self.log_text.append(f"录制模式: {mode}")
                self.log_text.append(f"自动保存: {'是' if self.auto_save_check.isChecked() else '否'}")
                
                # 启动进度更新定时器
                self.progress_timer = QTimer()
                self.progress_timer.timeout.connect(self.update_progress)
                self.progress_timer.start(1000)  # 每秒更新一次
            else:
                raise Exception("启动录制失败")
        
        except Exception as e:
            logger.error(f"开始录制失败: {e}")
            self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"开始录制失败: {str(e)}")
            self.progress_bar.setVisible(False)
    
    def stop_recording(self):
        """停止录制"""
        try:
            if self.recorder:
                self.recorder.stop_recording()
                self.recording = False
                
                # 停止进度更新
                if hasattr(self, 'progress_timer'):
                    self.progress_timer.stop()
                self.progress_bar.setValue(100)
                
                # 更新按钮状态
                self.record_btn.setText("开始录制")
                self.record_btn.setStyleSheet("""
                    QPushButton {
                        padding: 8px 20px;
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-weight: bold;
                        min-width: 100px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                """)
                
                # 启用设置控件
                self.interval_spin.setEnabled(True)
                self.mode_combo.setEnabled(True)
                self.auto_save_check.setEnabled(True)
                
                # 启用保存和清除按钮
                self.save_btn.setEnabled(True)
                self.clear_btn.setEnabled(True)
                
                # 更新日志
                self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 停止录制")
                
                # 如果设置了自动保存，则自动保存录制结果
                if self.auto_save_check.isChecked():
                    self.save_recording()
        
        except Exception as e:
            logger.error(f"停止录制失败: {e}")
            self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"停止录制失败: {str(e)}")
    
    def update_progress(self):
        """更新进度条"""
        if self.recording and self.recorder:
            try:
                progress = self.recorder.get_progress()
                self.progress_bar.setValue(int(progress))
                
                # 更新日志
                if hasattr(self.recorder, 'last_action'):
                    action = self.recorder.last_action
                    if action:
                        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 记录: {action}")
                        # 滚动到底部
                        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
            except Exception as e:
                logger.error(f"更新进度失败: {e}")
    
    def save_recording(self):
        """保存录制结果"""
        try:
            if not self.recorder:
                return
            
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存录制结果",
                os.path.join(os.getcwd(), "recordings"),
                "Python Files (*.py);;All Files (*)"
            )
            
            if file_path:
                # 显示保存进度
                progress = QProgressBar(self)
                progress.setRange(0, 100)
                progress.setValue(0)
                progress.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #dcdcdc;
                        border-radius: 2px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #2196F3;
                    }
                """)
                
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setText("正在保存录制结果...")
                msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
                layout = msg.layout()
                layout.addWidget(progress, 1, 1)
                msg.show()
                
                # 保存文件
                progress.setValue(30)
                self.recorder.save_recording(file_path)
                
                progress.setValue(100)
                msg.close()
                
                # 更新日志
                self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 录制结果已保存到: {file_path}")
                QMessageBox.information(self, "成功", "录制结果已保存")
        
        except Exception as e:
            logger.error(f"保存录制结果失败: {e}")
            self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存录制结果失败: {str(e)}")
    
    def clear_recording(self):
        """清除录制结果"""
        try:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要清除所有录制内容吗？\n此操作无法撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.recorder:
                    self.recorder.clear_recording()
                    self.log_text.clear()
                    self.progress_bar.setValue(0)
                    self.save_btn.setEnabled(False)
                    self.clear_btn.setEnabled(False)
                    self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 录制内容已清除")
        
        except Exception as e:
            logger.error(f"清除录制内容失败: {e}")
            self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 错误: {str(e)}")
            QMessageBox.critical(self, "错误", f"清除录制内容失败: {str(e)}")
    
    def set_device(self, device_info: dict):
        """设置当前设备信息。

        Args:
            device_info: 设备信息字典
        """
        try:
            self.current_device = device_info
            # 更新UI状态
            has_device = device_info is not None
            self.record_btn.setEnabled(has_device)
            if not has_device:
                self.record_btn.setText("开始录制")
                self.record_btn.setStyleSheet("""
                    QPushButton {
                        padding: 8px 20px;
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-weight: bold;
                        min-width: 100px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:pressed {
                        background-color: #3d8b40;
                    }
                    QPushButton:disabled {
                        background-color: #cccccc;
                    }
                """)
            
            # 更新日志
            if has_device:
                self.log_text.append(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"已选择设备: {device_info.get('model', 'Unknown')} "
                    f"({device_info.get('id', 'Unknown')})"
                )
            else:
                self.log_text.append(
                    f"[{time.strftime('%H:%M:%S')}] 设备已断开连接"
                )
            
            logger.info(f"录制标签页设备信息已更新: {device_info}")
        
        except Exception as e:
            logger.error(f"设置设备信息失败: {e}")
            self.log_text.append(f"[{time.strftime('%H:%M:%S')}] 错误: {str(e)}")
    
    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
            if self.recording:
                self.stop_recording()
        except Exception as e:
            logger.error(f"清理资源失败: {e}") 