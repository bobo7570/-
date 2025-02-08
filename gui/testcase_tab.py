from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QLineEdit,
    QTextEdit, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QDialog, QFormLayout, QListWidget, QListWidgetItem,
    QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from loguru import logger
from core.testcase_manager import TestCaseManager

class CreateTestCaseDialog(QDialog):
    """创建测试用例对话框"""
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.steps = []
        self.assertions = []
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("创建测试用例")
        self.setModal(True)
        self.resize(600, 800)
        
        layout = QVBoxLayout()
        
        # 基本信息区域
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        info_layout = QFormLayout()
        
        # 模块选择
        self.module_combo = QComboBox()
        self.module_combo.addItems(self.config['test']['modules'])
        info_layout.addRow("选择模块:", self.module_combo)
        
        # 用例名称
        self.name_edit = QLineEdit()
        info_layout.addRow("用例名称:", self.name_edit)
        
        # 用例描述
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        info_layout.addRow("用例描述:", self.desc_edit)
        
        info_frame.setLayout(info_layout)
        
        # 步骤列表区域
        step_frame = QFrame()
        step_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        step_layout = QVBoxLayout()
        
        step_title = QLabel("测试步骤")
        step_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
        """)
        step_layout.addWidget(step_title)
        
        # 步骤列表
        self.step_list = QListWidget()
        self.step_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.step_list.customContextMenuRequested.connect(self.show_step_menu)
        step_layout.addWidget(self.step_list)
        
        # 步骤操作按钮
        step_button_layout = QHBoxLayout()
        
        self.add_operation_button = QPushButton("添加操作")
        self.add_operation_button.clicked.connect(self.add_operation)
        self.add_operation_button.setStyleSheet("""
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
        
        self.add_case_button = QPushButton("添加用例")
        self.add_case_button.clicked.connect(self.add_case)
        self.add_case_button.setStyleSheet("""
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
        
        step_button_layout.addWidget(self.add_operation_button)
        step_button_layout.addWidget(self.add_case_button)
        step_button_layout.addStretch()
        
        step_layout.addLayout(step_button_layout)
        step_frame.setLayout(step_layout)
        
        # 断言列表区域
        assertion_frame = QFrame()
        assertion_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        assertion_layout = QVBoxLayout()
        
        assertion_title = QLabel("断言列表")
        assertion_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
        """)
        assertion_layout.addWidget(assertion_title)
        
        # 断言列表
        self.assertion_list = QListWidget()
        self.assertion_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.assertion_list.customContextMenuRequested.connect(self.show_assertion_menu)
        assertion_layout.addWidget(self.assertion_list)
        
        # 断言操作按钮
        assertion_button_layout = QHBoxLayout()
        
        self.add_assertion_button = QPushButton("添加断言")
        self.add_assertion_button.clicked.connect(self.add_assertion)
        self.add_assertion_button.setStyleSheet("""
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
        
        assertion_button_layout.addWidget(self.add_assertion_button)
        assertion_button_layout.addStretch()
        
        assertion_layout.addLayout(assertion_button_layout)
        assertion_frame.setLayout(assertion_layout)
        
        # 对话框按钮
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("""
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
        
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.accept)
        self.save_button.setStyleSheet("""
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
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        # 添加所有组件到主布局
        layout.addWidget(info_frame)
        layout.addWidget(step_frame)
        layout.addWidget(assertion_frame)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def show_step_menu(self, position):
        """显示步骤右键菜单"""
        menu = QMenu()
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_step)
        menu.addAction(delete_action)
        menu.exec(self.step_list.mapToGlobal(position))
    
    def show_assertion_menu(self, position):
        """显示断言右键菜单"""
        menu = QMenu()
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_assertion)
        menu.addAction(delete_action)
        menu.exec(self.assertion_list.mapToGlobal(position))
    
    def add_operation(self):
        """添加操作步骤"""
        # 显示操作选择对话框
        operations = []  # TODO: 从录制管理器获取操作列表
        operation, ok = QInputDialog.getItem(
            self,
            "选择操作",
            "请选择要添加的操作:",
            operations,
            0,
            False
        )
        
        if ok and operation:
            # 添加到步骤列表
            step = {
                'type': 'operation',
                'name': operation,
                'description': f"执行操作: {operation}"
            }
            self.steps.append(step)
            self.step_list.addItem(step['description'])
    
    def add_case(self):
        """添加测试用例"""
        # 显示用例选择对话框
        cases = []  # TODO: 从用例管理器获取用例列表
        case, ok = QInputDialog.getItem(
            self,
            "选择用例",
            "请选择要添加的用例:",
            cases,
            0,
            False
        )
        
        if ok and case:
            # 添加到步骤列表
            step = {
                'type': 'test_case',
                'name': case,
                'description': f"执行用例: {case}"
            }
            self.steps.append(step)
            self.step_list.addItem(step['description'])
    
    def add_assertion(self):
        """添加断言"""
        # 显示断言选择对话框
        assertions = []  # TODO: 从断言管理器获取断言列表
        assertion, ok = QInputDialog.getItem(
            self,
            "选择断言",
            "请选择要添加的断言:",
            assertions,
            0,
            False
        )
        
        if ok and assertion:
            # 添加到断言列表
            self.assertions.append(assertion)
            self.assertion_list.addItem(assertion)
    
    def delete_step(self):
        """删除步骤"""
        current_row = self.step_list.currentRow()
        if current_row >= 0:
            self.step_list.takeItem(current_row)
            self.steps.pop(current_row)
    
    def delete_assertion(self):
        """删除断言"""
        current_row = self.assertion_list.currentRow()
        if current_row >= 0:
            self.assertion_list.takeItem(current_row)
            self.assertions.pop(current_row)
    
    def get_data(self):
        """获取输入的数据"""
        return {
            'module': self.module_combo.currentText(),
            'name': self.name_edit.text(),
            'description': self.desc_edit.toPlainText(),
            'steps': self.steps,
            'assertions': self.assertions
        }

class TestCaseTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.testcase_manager = TestCaseManager(config)
        self.current_device = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 创建用例管理区域
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        control_layout = QVBoxLayout()
        
        # 添加标题
        title_label = QLabel("用例管理")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding: 10px;
            }
        """)
        control_layout.addWidget(title_label)
        
        # 创建用例管理按钮
        button_layout = QHBoxLayout()
        
        self.create_button = QPushButton("创建用例")
        self.create_button.setStyleSheet("""
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
        self.create_button.clicked.connect(self.create_testcase)
        
        self.run_button = QPushButton("运行用例")
        self.run_button.setEnabled(False)
        self.run_button.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.run_button.clicked.connect(self.run_testcase)
        
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.run_button)
        button_layout.addStretch()
        
        control_layout.addLayout(button_layout)
        
        # 添加设备信息显示
        self.device_info = QLabel("未选择设备")
        self.device_info.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 3px;
            }
        """)
        control_layout.addWidget(self.device_info)
        
        control_frame.setLayout(control_layout)
        
        # 创建用例列表区域
        list_frame = QFrame()
        list_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        list_layout = QVBoxLayout()
        
        # 添加标题
        list_title = QLabel("用例列表")
        list_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding: 10px;
            }
        """)
        list_layout.addWidget(list_title)
        
        # 创建树形列表
        self.testcase_tree = QTreeWidget()
        self.testcase_tree.setHeaderLabels(["名称", "描述", "步骤数", "创建时间"])
        self.testcase_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        list_layout.addWidget(self.testcase_tree)
        
        # 创建操作按钮
        operation_button_layout = QHBoxLayout()
        
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
        self.delete_button.clicked.connect(self.delete_testcase)
        
        self.edit_button = QPushButton("编辑")
        self.edit_button.setStyleSheet("""
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
        self.edit_button.clicked.connect(self.edit_testcase)
        
        operation_button_layout.addWidget(self.delete_button)
        operation_button_layout.addWidget(self.edit_button)
        operation_button_layout.addStretch()
        
        list_layout.addLayout(operation_button_layout)
        
        list_frame.setLayout(list_layout)
        
        # 添加到主布局
        main_layout.addWidget(control_frame)
        main_layout.addWidget(list_frame)
        
        # 设置主布局
        self.setLayout(main_layout)
        
        # 加载用例列表
        self.load_testcases()
    
    def set_device(self, device_info: dict):
        """
        设置当前设备
        :param device_info: 设备信息
        """
        self.current_device = device_info
        if device_info:
            self.device_info.setText(
                f"当前设备: {device_info['model']} ({device_info['id']})"
            )
            self.run_button.setEnabled(True)
        else:
            self.device_info.setText("未选择设备")
            self.run_button.setEnabled(False)
    
    def create_testcase(self):
        """创建测试用例"""
        try:
            # 显示创建对话框
            dialog = CreateTestCaseDialog(self.config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                
                # 创建用例
                if self.testcase_manager.create_test_case(
                    data['module'],
                    data['name'],
                    data['description'],
                    data['steps'],
                    data['assertions']
                ):
                    QMessageBox.information(self, "提示", "测试用例创建成功")
                    # 刷新列表
                    self.load_testcases()
                else:
                    QMessageBox.critical(self, "错误", "创建测试用例失败")
        
        except Exception as e:
            logger.error(f"创建测试用例失败: {e}")
            QMessageBox.critical(self, "错误", f"创建测试用例失败: {str(e)}")
    
    def run_testcase(self):
        """运行测试用例"""
        try:
            # 获取选中的用例
            current_item = self.testcase_tree.currentItem()
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "警告", "请选择要运行的用例")
                return
            
            if not self.current_device:
                QMessageBox.warning(self, "警告", "请先选择设备")
                return
            
            # 获取用例数据
            module = current_item.parent().text(0)
            testcase_name = current_item.text(0)
            testcases = self.testcase_manager.get_test_cases(module)
            testcase = next(
                (t for t in testcases if t['name'] == testcase_name),
                None
            )
            
            if not testcase:
                QMessageBox.warning(self, "警告", "未找到用例数据")
                return
            
            # TODO: 实现用例执行逻辑
            QMessageBox.information(self, "提示", "用例执行完成")
        
        except Exception as e:
            logger.error(f"运行测试用例失败: {e}")
            QMessageBox.critical(self, "错误", f"运行测试用例失败: {str(e)}")
    
    def load_testcases(self):
        """加载用例列表"""
        try:
            self.testcase_tree.clear()
            
            # 获取所有用例
            testcases = self.testcase_manager.get_test_cases()
            
            # 按模块分组
            modules = {}
            for testcase in testcases:
                module = testcase['module']
                if module not in modules:
                    modules[module] = []
                modules[module].append(testcase)
            
            # 添加到树形列表
            for module, module_testcases in modules.items():
                # 创建模块节点
                module_item = QTreeWidgetItem([module])
                self.testcase_tree.addTopLevelItem(module_item)
                
                # 添加用例节点
                for testcase in module_testcases:
                    testcase_item = QTreeWidgetItem([
                        testcase['name'],
                        testcase['description'],
                        str(len(testcase['steps'])),
                        testcase['created_at']
                    ])
                    module_item.addChild(testcase_item)
            
            # 展开所有节点
            self.testcase_tree.expandAll()
        
        except Exception as e:
            logger.error(f"加载用例列表失败: {e}")
    
    def delete_testcase(self):
        """删除测试用例"""
        try:
            # 获取选中的用例
            current_item = self.testcase_tree.currentItem()
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "警告", "请选择要删除的用例")
                return
            
            # 获取模块和用例名称
            module = current_item.parent().text(0)
            testcase_name = current_item.text(0)
            
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除用例 {testcase_name} 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 删除用例
                if self.testcase_manager.delete_test_case(module, testcase_name):
                    QMessageBox.information(self, "提示", "用例已删除")
                    # 刷新列表
                    self.load_testcases()
                else:
                    QMessageBox.critical(self, "错误", "删除用例失败")
        
        except Exception as e:
            logger.error(f"删除测试用例失败: {e}")
            QMessageBox.critical(self, "错误", f"删除测试用例失败: {str(e)}")
    
    def edit_testcase(self):
        """编辑测试用例"""
        try:
            # 获取选中的用例
            current_item = self.testcase_tree.currentItem()
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "警告", "请选择要编辑的用例")
                return
            
            # 获取用例数据
            module = current_item.parent().text(0)
            testcase_name = current_item.text(0)
            testcases = self.testcase_manager.get_test_cases(module)
            testcase = next(
                (t for t in testcases if t['name'] == testcase_name),
                None
            )
            
            if not testcase:
                QMessageBox.warning(self, "警告", "未找到用例数据")
                return
            
            # 显示编辑对话框
            dialog = CreateTestCaseDialog(self.config)
            dialog.module_combo.setCurrentText(module)
            dialog.name_edit.setText(testcase['name'])
            dialog.desc_edit.setText(testcase['description'])
            
            # 添加步骤
            for step in testcase['steps']:
                dialog.steps.append(step)
                dialog.step_list.addItem(step['description'])
            
            # 添加断言
            for assertion in testcase['assertions']:
                dialog.assertions.append(assertion)
                dialog.assertion_list.addItem(assertion)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_data = dialog.get_data()
                
                # 更新用例
                if self.testcase_manager.update_test_case(
                    module,
                    testcase_name,
                    {
                        'name': new_data['name'],
                        'description': new_data['description'],
                        'steps': new_data['steps'],
                        'assertions': new_data['assertions']
                    }
                ):
                    QMessageBox.information(self, "提示", "用例已更新")
                    # 刷新列表
                    self.load_testcases()
                else:
                    QMessageBox.critical(self, "错误", "更新用例失败")
        
        except Exception as e:
            logger.error(f"编辑测试用例失败: {e}")
            QMessageBox.critical(self, "错误", f"编辑测试用例失败: {str(e)}") 