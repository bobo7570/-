from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QTextEdit, QDialog, QFormLayout,
    QSplitter
)
from PySide6.QtCore import Qt
from loguru import logger
import os
import json
from datetime import datetime

class ReportDetailDialog(QDialog):
    """报告详情对话框"""
    def __init__(self, report_data, parent=None):
        super().__init__(parent)
        self.report_data = report_data
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("测试报告详情")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # 基本信息区域
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QFormLayout()
        
        # 添加基本信息
        info_layout.addRow("执行时间:", QLabel(self.report_data['timestamp']))
        info_layout.addRow("总用例数:", QLabel(str(self.report_data['total_cases'])))
        info_layout.addRow("通过用例:", QLabel(str(self.report_data['passed_cases'])))
        info_layout.addRow("失败用例:", QLabel(str(self.report_data['failed_cases'])))
        
        # 计算通过率
        pass_rate = (self.report_data['passed_cases'] / self.report_data['total_cases'] * 100
                    if self.report_data['total_cases'] > 0 else 0)
        pass_rate_label = QLabel(f"{pass_rate:.2f}%")
        pass_rate_label.setStyleSheet(f"""
            QLabel {{
                color: {'green' if pass_rate >= 80 else 'red'};
                font-weight: bold;
            }}
        """)
        info_layout.addRow("通过率:", pass_rate_label)
        
        info_frame.setLayout(info_layout)
        
        # 详细结果区域
        result_frame = QFrame()
        result_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        result_layout = QVBoxLayout()
        
        # 添加标题
        result_title = QLabel("测试结果")
        result_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
        """)
        result_layout.addWidget(result_title)
        
        # 创建结果树
        self.result_tree = QTreeWidget()
        self.result_tree.setHeaderLabels(["用例", "状态", "耗时", "错误信息"])
        self.result_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        
        # 添加结果数据
        for result in self.report_data['results']:
            item = QTreeWidgetItem([
                result['name'],
                result['status'],
                f"{result.get('duration', 0):.2f}s",
                result.get('error', '')
            ])
            
            # 设置状态列的颜色
            item.setForeground(1, Qt.GlobalColor.green if result['status'] == 'passed'
                             else Qt.GlobalColor.red)
            
            self.result_tree.addTopLevelItem(item)
        
        # 调整列宽
        self.result_tree.resizeColumnToContents(0)
        self.result_tree.resizeColumnToContents(1)
        self.result_tree.resizeColumnToContents(2)
        
        result_layout.addWidget(self.result_tree)
        result_frame.setLayout(result_layout)
        
        # 添加到主布局
        layout.addWidget(info_frame)
        layout.addWidget(result_frame)
        
        # 添加关闭按钮
        button_layout = QHBoxLayout()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class ReportTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 创建报告管理区域
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        control_layout = QVBoxLayout()
        
        # 添加标题
        title_label = QLabel("测试报告")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding: 10px;
            }
        """)
        control_layout.addWidget(title_label)
        
        # 创建报告管理按钮
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.refresh_button.clicked.connect(self.load_reports)
        
        self.delete_button = QPushButton("删除")
        self.delete_button.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
        """)
        self.delete_button.clicked.connect(self.delete_report)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        
        control_layout.addLayout(button_layout)
        
        control_frame.setLayout(control_layout)
        
        # 创建报告列表和详情区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 报告列表
        list_frame = QFrame()
        list_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        list_layout = QVBoxLayout()
        
        self.report_tree = QTreeWidget()
        self.report_tree.setHeaderLabels(["时间", "总数", "通过", "失败", "通过率"])
        self.report_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        self.report_tree.itemClicked.connect(self.show_report_detail)
        
        list_layout.addWidget(self.report_tree)
        list_frame.setLayout(list_layout)
        
        # 报告详情
        detail_frame = QFrame()
        detail_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        detail_layout = QVBoxLayout()
        
        detail_title = QLabel("报告详情")
        detail_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
        """)
        detail_layout.addWidget(detail_title)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        detail_frame.setLayout(detail_layout)
        
        # 添加到分割器
        content_splitter.addWidget(list_frame)
        content_splitter.addWidget(detail_frame)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 2)
        
        # 添加到主布局
        main_layout.addWidget(control_frame)
        main_layout.addWidget(content_splitter)
        
        # 设置主布局
        self.setLayout(main_layout)
        
        # 加载报告列表
        self.load_reports()
    
    def load_reports(self):
        """加载报告列表"""
        try:
            self.report_tree.clear()
            self.detail_text.clear()
            
            # 获取报告目录
            report_dir = self.config['test']['report_dir']
            if not os.path.exists(report_dir):
                return
            
            # 加载所有报告文件
            reports = []
            for filename in os.listdir(report_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(report_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            report = json.load(f)
                            report['file_path'] = file_path
                            reports.append(report)
                    except Exception as e:
                        logger.error(f"加载报告文件失败 {file_path}: {e}")
            
            # 按时间排序
            reports.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # 添加到树形列表
            for report in reports:
                pass_rate = (report['passed_cases'] / report['total_cases'] * 100
                           if report['total_cases'] > 0 else 0)
                
                item = QTreeWidgetItem([
                    report['timestamp'],
                    str(report['total_cases']),
                    str(report['passed_cases']),
                    str(report['failed_cases']),
                    f"{pass_rate:.2f}%"
                ])
                
                # 设置通过率列的颜色
                item.setForeground(4, Qt.GlobalColor.green if pass_rate >= 80
                                 else Qt.GlobalColor.red)
                
                # 保存报告数据
                item.setData(0, Qt.ItemDataRole.UserRole, report)
                
                self.report_tree.addTopLevelItem(item)
            
            # 调整列宽
            for i in range(self.report_tree.columnCount()):
                self.report_tree.resizeColumnToContents(i)
        
        except Exception as e:
            logger.error(f"加载报告列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载报告列表失败: {str(e)}")
    
    def show_report_detail(self, item: QTreeWidgetItem, column: int):
        """
        显示报告详情
        :param item: 选中的项
        :param column: 选中的列
        """
        try:
            # 获取报告数据
            report = item.data(0, Qt.ItemDataRole.UserRole)
            if not report:
                return
            
            # 显示详情对话框
            dialog = ReportDetailDialog(report, self)
            dialog.exec()
        
        except Exception as e:
            logger.error(f"显示报告详情失败: {e}")
            QMessageBox.critical(self, "错误", f"显示报告详情失败: {str(e)}")
    
    def delete_report(self):
        """删除报告"""
        try:
            # 获取选中的报告
            current_item = self.report_tree.currentItem()
            if not current_item:
                QMessageBox.warning(self, "警告", "请选择要删除的报告")
                return
            
            # 获取报告数据
            report = current_item.data(0, Qt.ItemDataRole.UserRole)
            if not report:
                return
            
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除 {report['timestamp']} 的报告吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 删除文件
                os.remove(report['file_path'])
                # 刷新列表
                self.load_reports()
                QMessageBox.information(self, "提示", "报告已删除")
        
        except Exception as e:
            logger.error(f"删除报告失败: {e}")
            QMessageBox.critical(self, "错误", f"删除报告失败: {str(e)}") 