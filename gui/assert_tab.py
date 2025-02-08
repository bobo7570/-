from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QLineEdit,
    QTextEdit, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QDialog, QFormLayout, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, Signal
from loguru import logger
from core.assertion_manager import AssertionManager

class CreateAssertDialog(QDialog):
    """创建断言对话框"""
    def __init__(self, modules, parent=None):
        super().__init__(parent)
        self.modules = modules
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("创建断言")
        self.setModal(True)
        
        layout = QFormLayout()
        
        # 模块选择
        self.module_combo = QComboBox()
        self.module_combo.addItems(self.modules)
        layout.addRow("选择模块:", self.module_combo)
        
        # 断言名称
        self.name_edit = QLineEdit()
        layout.addRow("断言名称:", self.name_edit)
        
        # 断言描述
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        layout.addRow("断言描述:", self.desc_edit)
        
        # 定位方式
        self.locator_type_combo = QComboBox()
        self.locator_type_combo.addItems([
            "accessibility_id",
            "id",
            "xpath",
            "class_name",
            "name",
            "android_uiautomator",
            "ios_predicate"
        ])
        layout.addRow("定位方式:", self.locator_type_combo)
        
        # 定位值
        self.locator_value_edit = QLineEdit()
        layout.addRow("定位值:", self.locator_value_edit)
        
        # 断言类型
        type_layout = QHBoxLayout()
        self.type_group = QButtonGroup()
        
        self.exists_radio = QRadioButton("存在断言")
        self.exists_radio.setChecked(True)
        self.type_group.addButton(self.exists_radio)
        type_layout.addWidget(self.exists_radio)
        
        self.text_radio = QRadioButton("文本断言")
        self.type_group.addButton(self.text_radio)
        type_layout.addWidget(self.text_radio)
        
        layout.addRow("断言类型:", type_layout)
        
        # 期望文本
        self.expected_text_edit = QLineEdit()
        self.expected_text_edit.setEnabled(False)
        layout.addRow("期望文本:", self.expected_text_edit)
        
        # 连接信号
        self.text_radio.toggled.connect(
            lambda checked: self.expected_text_edit.setEnabled(checked)
        )
        
        # 按钮布局
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
        
        layout.addRow("", button_layout)
        
        self.setLayout(layout)
    
    def get_data(self):
        """获取输入的数据"""
        return {
            'module': self.module_combo.currentText(),
            'name': self.name_edit.text(),
            'description': self.desc_edit.toPlainText(),
            'locator_type': self.locator_type_combo.currentText(),
            'locator_value': self.locator_value_edit.text(),
            'assertion_type': 'exists' if self.exists_radio.isChecked() else 'text',
            'expected_text': self.expected_text_edit.text() if self.text_radio.isChecked() else None
        }

class AssertTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.assertion_manager = AssertionManager(config)
        self.current_device = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 创建断言管理区域
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        control_layout = QVBoxLayout()
        
        # 添加标题
        title_label = QLabel("断言管理")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
                padding: 10px;
            }
        """)
        control_layout.addWidget(title_label)
        
        # 创建断言管理按钮
        button_layout = QHBoxLayout()
        
        self.create_button = QPushButton("创建断言")
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
        self.create_button.clicked.connect(self.create_assertion)
        
        self.debug_button = QPushButton("调试断言")
        self.debug_button.setEnabled(False)
        self.debug_button.setStyleSheet("""
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
        self.debug_button.clicked.connect(self.debug_assertion)
        
        button_layout.addWidget(self.create_button)
        button_layout.addWidget(self.debug_button)
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
        
        # 创建断言列表区域
        list_frame = QFrame()
        list_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        list_layout = QVBoxLayout()
        
        # 添加标题
        list_title = QLabel("断言列表")
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
        self.assertion_tree = QTreeWidget()
        self.assertion_tree.setHeaderLabels(["名称", "描述", "类型", "创建时间"])
        self.assertion_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        list_layout.addWidget(self.assertion_tree)
        
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
        self.delete_button.clicked.connect(self.delete_assertion)
        
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
        self.edit_button.clicked.connect(self.edit_assertion)
        
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
        
        # 加载断言列表
        self.load_assertions()
    
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
            self.debug_button.setEnabled(True)
        else:
            self.device_info.setText("未选择设备")
            self.debug_button.setEnabled(False)
    
    def create_assertion(self):
        """创建断言"""
        try:
            # 显示创建对话框
            dialog = CreateAssertDialog(self.config['test']['modules'])
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                
                # 创建断言
                if self.assertion_manager.create_assertion(
                    data['module'],
                    data['name'],
                    data['description'],
                    data['locator_type'],
                    data['locator_value'],
                    data['assertion_type'],
                    data['expected_text']
                ):
                    QMessageBox.information(self, "提示", "断言创建成功")
                    # 刷新列表
                    self.load_assertions()
                else:
                    QMessageBox.critical(self, "错误", "创建断言失败")
        
        except Exception as e:
            logger.error(f"创建断言失败: {e}")
            QMessageBox.critical(self, "错误", f"创建断言失败: {str(e)}")
    
    def debug_assertion(self):
        """调试断言"""
        try:
            # 获取选中的断言
            current_item = self.assertion_tree.currentItem()
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "警告", "请选择要调试的断言")
                return
            
            if not self.current_device:
                QMessageBox.warning(self, "警告", "请先选择设备")
                return
            
            # 获取断言数据
            module = current_item.parent().text(0)
            assertion_name = current_item.text(0)
            assertions = self.assertion_manager.get_assertions(module)
            assertion = next(
                (a for a in assertions if a['name'] == assertion_name),
                None
            )
            
            if not assertion:
                QMessageBox.warning(self, "警告", "未找到断言数据")
                return
            
            # 验证断言
            passed, message = self.assertion_manager.verify_assertion(
                self.current_device,
                assertion
            )
            
            # 显示结果
            icon = QMessageBox.Icon.Information if passed else QMessageBox.Icon.Warning
            QMessageBox.information(
                self,
                "调试结果",
                f"断言验证{'通过' if passed else '失败'}: {message}"
            )
        
        except Exception as e:
            logger.error(f"调试断言失败: {e}")
            QMessageBox.critical(self, "错误", f"调试断言失败: {str(e)}")
    
    def load_assertions(self):
        """加载断言列表"""
        try:
            self.assertion_tree.clear()
            
            # 获取所有断言
            assertions = self.assertion_manager.get_assertions()
            
            # 按模块分组
            modules = {}
            for assertion in assertions:
                module = assertion['module']
                if module not in modules:
                    modules[module] = []
                modules[module].append(assertion)
            
            # 添加到树形列表
            for module, module_assertions in modules.items():
                # 创建模块节点
                module_item = QTreeWidgetItem([module])
                self.assertion_tree.addTopLevelItem(module_item)
                
                # 添加断言节点
                for assertion in module_assertions:
                    assertion_item = QTreeWidgetItem([
                        assertion['name'],
                        assertion['description'],
                        assertion['assertion_type'],
                        assertion['created_at']
                    ])
                    module_item.addChild(assertion_item)
            
            # 展开所有节点
            self.assertion_tree.expandAll()
        
        except Exception as e:
            logger.error(f"加载断言列表失败: {e}")
    
    def delete_assertion(self):
        """删除断言"""
        try:
            # 获取选中的断言
            current_item = self.assertion_tree.currentItem()
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "警告", "请选择要删除的断言")
                return
            
            # 获取模块和断言名称
            module = current_item.parent().text(0)
            assertion_name = current_item.text(0)
            
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除断言 {assertion_name} 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 删除断言
                if self.assertion_manager.delete_assertion(module, assertion_name):
                    QMessageBox.information(self, "提示", "断言已删除")
                    # 刷新列表
                    self.load_assertions()
                else:
                    QMessageBox.critical(self, "错误", "删除断言失败")
        
        except Exception as e:
            logger.error(f"删除断言失败: {e}")
            QMessageBox.critical(self, "错误", f"删除断言失败: {str(e)}")
    
    def edit_assertion(self):
        """编辑断言"""
        try:
            # 获取选中的断言
            current_item = self.assertion_tree.currentItem()
            if not current_item or not current_item.parent():
                QMessageBox.warning(self, "警告", "请选择要编辑的断言")
                return
            
            # 获取断言数据
            module = current_item.parent().text(0)
            assertion_name = current_item.text(0)
            assertions = self.assertion_manager.get_assertions(module)
            assertion = next(
                (a for a in assertions if a['name'] == assertion_name),
                None
            )
            
            if not assertion:
                QMessageBox.warning(self, "警告", "未找到断言数据")
                return
            
            # 显示编辑对话框
            dialog = CreateAssertDialog(self.config['test']['modules'])
            dialog.module_combo.setCurrentText(module)
            dialog.name_edit.setText(assertion['name'])
            dialog.desc_edit.setText(assertion['description'])
            dialog.locator_type_combo.setCurrentText(assertion['locator_type'])
            dialog.locator_value_edit.setText(assertion['locator_value'])
            
            if assertion['assertion_type'] == 'exists':
                dialog.exists_radio.setChecked(True)
            else:
                dialog.text_radio.setChecked(True)
                dialog.expected_text_edit.setText(assertion['expected_text'])
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_data = dialog.get_data()
                
                # 删除原断言
                self.assertion_manager.delete_assertion(module, assertion_name)
                
                # 创建新断言
                if self.assertion_manager.create_assertion(
                    new_data['module'],
                    new_data['name'],
                    new_data['description'],
                    new_data['locator_type'],
                    new_data['locator_value'],
                    new_data['assertion_type'],
                    new_data['expected_text']
                ):
                    QMessageBox.information(self, "提示", "断言已更新")
                    # 刷新列表
                    self.load_assertions()
                else:
                    QMessageBox.critical(self, "错误", "更新断言失败")
        
        except Exception as e:
            logger.error(f"编辑断言失败: {e}")
            QMessageBox.critical(self, "错误", f"编辑断言失败: {str(e)}") 