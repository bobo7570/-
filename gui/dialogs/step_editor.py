from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem,
    QSpinBox, QComboBox, QLineEdit, QMessageBox,
    QFormLayout, QDialogButtonBox, QTabWidget,
    QWidget, QTextEdit, QCheckBox, QInputDialog,
    QMenu, QToolButton, QFileDialog, QGroupBox,
    QRadioButton
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor, QAction, QSyntaxHighlighter, QTextCharFormat
from loguru import logger
from typing import Dict, List, Optional
import json
import copy
import os
import re
import time

class PythonHighlighter(QSyntaxHighlighter):
    """Python语法高亮器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # 关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#CC7832"))
        keyword_format.setFontWeight(700)
        keywords = [
            "and", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "exec", "finally",
            "for", "from", "global", "if", "import", "in",
            "is", "lambda", "not", "or", "pass", "print",
            "raise", "return", "try", "while", "yield",
            "None", "True", "False"
        ]
        
        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((re.compile(pattern), keyword_format))
        
        # 字符串
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#6A8759"))
        self.highlighting_rules.append((re.compile("\".*\""), string_format))
        self.highlighting_rules.append((re.compile("'.*'"), string_format))
        
        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        self.highlighting_rules.append((re.compile("#[^\n]*"), comment_format))
        
        # 数字
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#6897BB"))
        self.highlighting_rules.append((re.compile("\\b[0-9]+\\b"), number_format))
        
        # 函数
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#FFC66D"))
        self.highlighting_rules.append((
            re.compile("\\b[A-Za-z0-9_]+(?=\\()"),
            function_format
        ))
    
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), format)

class ScriptPreviewDialog(QDialog):
    """脚本预览对话框"""
    def __init__(self, script_content: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("脚本预览")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # 预览区域
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlainText(script_content)
        self.preview.setFont("Consolas")
        
        # 设置语法高亮
        self.highlighter = PythonHighlighter(self.preview.document())
        
        layout.addWidget(self.preview)
        
        # 按钮区域
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

class StepEditorDialog(QDialog):
    """步骤编辑对话框"""
    
    # 定义信号
    steps_updated = Signal(list)  # 步骤更新信号
    
    def __init__(self, actions: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑录制步骤")
        self.setMinimumSize(800, 600)
        
        # 保存原始动作列表的副本
        self.original_actions = copy.deepcopy(actions)
        self.current_actions = copy.deepcopy(actions)
        
        # 模板目录
        self.template_dir = os.path.join("data", "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        
        # 初始化UI
        self.init_ui()
        
        # 加载步骤数据
        self.load_steps()
        
        logger.info("步骤编辑对话框初始化完成")
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 步骤列表标签页
        steps_tab = self._create_steps_tab()
        tab_widget.addTab(steps_tab, "步骤列表")
        
        # 步骤详情标签页
        details_tab = self._create_details_tab()
        tab_widget.addTab(details_tab, "步骤详情")
        
        layout.addWidget(tab_widget)
        
        # 按钮区域
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def _create_steps_tab(self):
        """创建步骤列表标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 添加步骤按钮
        add_btn = QPushButton("添加步骤")
        add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        add_btn.clicked.connect(self._add_step)
        toolbar.addWidget(add_btn)
        
        # 模板按钮
        template_btn = QToolButton()
        template_btn.setText("模板")
        template_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        template_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        template_menu = QMenu()
        
        # 保存为模板
        save_template_action = QAction("保存为模板", self)
        save_template_action.triggered.connect(self._save_as_template)
        template_menu.addAction(save_template_action)
        
        # 加载模板
        load_template_action = QAction("加载模板", self)
        load_template_action.triggered.connect(self._load_template)
        template_menu.addAction(load_template_action)
        
        # 管理模板
        manage_template_action = QAction("管理模板", self)
        manage_template_action.triggered.connect(self._manage_templates)
        template_menu.addAction(manage_template_action)
        
        template_btn.setMenu(template_menu)
        toolbar.addWidget(template_btn)
        
        # 添加脚本按钮
        script_btn = QToolButton()
        script_btn.setText("脚本")
        script_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        script_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        script_menu = QMenu()
        
        # 预览脚本
        preview_action = QAction("预览脚本", self)
        preview_action.triggered.connect(self._preview_script)
        script_menu.addAction(preview_action)
        
        # 导出脚本
        export_action = QAction("导出脚本", self)
        export_action.triggered.connect(self._export_script)
        script_menu.addAction(export_action)
        
        # 脚本设置
        settings_action = QAction("脚本设置", self)
        settings_action.triggered.connect(self._script_settings)
        script_menu.addAction(settings_action)
        
        script_btn.setMenu(script_menu)
        toolbar.addWidget(script_btn)
        
        # 删除步骤按钮
        delete_btn = QPushButton("删除步骤")
        delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_btn.clicked.connect(self._delete_step)
        toolbar.addWidget(delete_btn)
        
        # 上移按钮
        up_btn = QPushButton("上移")
        up_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        up_btn.clicked.connect(self._move_step_up)
        toolbar.addWidget(up_btn)
        
        # 下移按钮
        down_btn = QPushButton("下移")
        down_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        down_btn.clicked.connect(self._move_step_down)
        toolbar.addWidget(down_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 步骤列表
        self.steps_tree = QTreeWidget()
        self.steps_tree.setHeaderLabels([
            "序号", "时间", "类型", "目标", "动作", "参数"
        ])
        self.steps_tree.setAlternatingRowColors(True)
        self.steps_tree.itemSelectionChanged.connect(self._on_step_selected)
        
        # 设置列宽
        header = self.steps_tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.steps_tree)
        
        widget.setLayout(layout)
        return widget
    
    def _create_details_tab(self):
        """创建步骤详情标签页"""
        widget = QWidget()
        layout = QFormLayout()
        layout.setSpacing(10)
        
        # 步骤类型
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "click", "swipe", "text", "key", "wait",
            "assert", "scroll", "custom"
        ])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addRow("类型:", self.type_combo)
        
        # 目标元素
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("请输入目标元素的定位表达式")
        layout.addRow("目标:", self.target_edit)
        
        # 动作
        self.action_edit = QLineEdit()
        self.action_edit.setPlaceholderText("请输入要执行的动作")
        layout.addRow("动作:", self.action_edit)
        
        # 参数
        self.params_edit = QTextEdit()
        self.params_edit.setPlaceholderText("请输入动作参数 (JSON格式)")
        self.params_edit.setMaximumHeight(100)
        layout.addRow("参数:", self.params_edit)
        
        # 等待时间
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(0, 60000)
        self.wait_spin.setSuffix(" 毫秒")
        self.wait_spin.setValue(1000)
        layout.addRow("等待时间:", self.wait_spin)
        
        # 超时时间
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 60000)
        self.timeout_spin.setSuffix(" 毫秒")
        self.timeout_spin.setValue(10000)
        layout.addRow("超时时间:", self.timeout_spin)
        
        # 重试次数
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 10)
        self.retry_spin.setValue(3)
        layout.addRow("重试次数:", self.retry_spin)
        
        # 失败时继续
        self.continue_check = QCheckBox()
        layout.addRow("失败时继续:", self.continue_check)
        
        # 描述
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("请输入步骤描述")
        self.desc_edit.setMaximumHeight(100)
        layout.addRow("描述:", self.desc_edit)
        
        # 应用按钮
        apply_btn = QPushButton("应用更改")
        apply_btn.clicked.connect(self._apply_changes)
        layout.addRow("", apply_btn)
        
        widget.setLayout(layout)
        return widget
    
    def load_steps(self):
        """加载步骤数据"""
        try:
            self.steps_tree.clear()
            
            for index, action in enumerate(self.current_actions):
                item = QTreeWidgetItem(self.steps_tree)
                item.setText(0, str(index + 1))
                item.setText(1, action.get('time', ''))
                item.setText(2, action.get('type', ''))
                item.setText(3, action.get('target', ''))
                item.setText(4, action.get('action', ''))
                item.setText(5, str(action.get('params', {})))
                
                # 设置图标
                action_type = action.get('type', '').lower()
                if action_type == 'click':
                    item.setIcon(2, self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
                elif action_type == 'swipe':
                    item.setIcon(2, self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
                elif action_type == 'text':
                    item.setIcon(2, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                elif action_type == 'key':
                    item.setIcon(2, self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
            
            logger.info(f"已加载 {len(self.current_actions)} 个步骤")
        
        except Exception as e:
            logger.error(f"加载步骤数据失败: {e}")
            QMessageBox.critical(self, "错误", f"加载步骤数据失败: {str(e)}")
    
    def _add_step(self):
        """添加新步骤"""
        try:
            # 创建新步骤
            new_step = {
                'time': '',
                'type': 'click',
                'target': '',
                'action': '',
                'params': {},
                'wait': 1000,
                'timeout': 10000,
                'retry': 3,
                'continue_on_failure': False,
                'description': ''
            }
            
            # 添加到列表
            self.current_actions.append(new_step)
            
            # 更新显示
            self.load_steps()
            
            # 选中新添加的项
            last_item = self.steps_tree.topLevelItem(
                self.steps_tree.topLevelItemCount() - 1
            )
            if last_item:
                last_item.setSelected(True)
            
            logger.info("已添加新步骤")
        
        except Exception as e:
            logger.error(f"添加步骤失败: {e}")
            QMessageBox.critical(self, "错误", f"添加步骤失败: {str(e)}")
    
    def _delete_step(self):
        """删除选中的步骤"""
        try:
            items = self.steps_tree.selectedItems()
            if not items:
                return
            
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要删除选中的步骤吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                for item in items:
                    index = self.steps_tree.indexOfTopLevelItem(item)
                    if index >= 0:
                        self.current_actions.pop(index)
                
                # 更新显示
                self.load_steps()
                logger.info(f"已删除 {len(items)} 个步骤")
        
        except Exception as e:
            logger.error(f"删除步骤失败: {e}")
            QMessageBox.critical(self, "错误", f"删除步骤失败: {str(e)}")
    
    def _move_step_up(self):
        """上移选中的步骤"""
        try:
            items = self.steps_tree.selectedItems()
            if not items:
                return
            
            item = items[0]
            index = self.steps_tree.indexOfTopLevelItem(item)
            if index > 0:
                # 交换位置
                self.current_actions[index], self.current_actions[index - 1] = \
                    self.current_actions[index - 1], self.current_actions[index]
                
                # 更新显示
                self.load_steps()
                
                # 选中移动后的项
                new_item = self.steps_tree.topLevelItem(index - 1)
                if new_item:
                    new_item.setSelected(True)
                
                logger.info(f"步骤 {index + 1} 上移到 {index}")
        
        except Exception as e:
            logger.error(f"上移步骤失败: {e}")
            QMessageBox.critical(self, "错误", f"上移步骤失败: {str(e)}")
    
    def _move_step_down(self):
        """下移选中的步骤"""
        try:
            items = self.steps_tree.selectedItems()
            if not items:
                return
            
            item = items[0]
            index = self.steps_tree.indexOfTopLevelItem(item)
            if index < self.steps_tree.topLevelItemCount() - 1:
                # 交换位置
                self.current_actions[index], self.current_actions[index + 1] = \
                    self.current_actions[index + 1], self.current_actions[index]
                
                # 更新显示
                self.load_steps()
                
                # 选中移动后的项
                new_item = self.steps_tree.topLevelItem(index + 1)
                if new_item:
                    new_item.setSelected(True)
                
                logger.info(f"步骤 {index + 1} 下移到 {index + 2}")
        
        except Exception as e:
            logger.error(f"下移步骤失败: {e}")
            QMessageBox.critical(self, "错误", f"下移步骤失败: {str(e)}")
    
    def _on_step_selected(self):
        """步骤选择变化处理"""
        try:
            items = self.steps_tree.selectedItems()
            if not items:
                return
            
            item = items[0]
            index = self.steps_tree.indexOfTopLevelItem(item)
            if index >= 0:
                action = self.current_actions[index]
                
                # 更新详情页面
                self.type_combo.setCurrentText(action.get('type', ''))
                self.target_edit.setText(action.get('target', ''))
                self.action_edit.setText(action.get('action', ''))
                self.params_edit.setPlainText(
                    json.dumps(action.get('params', {}), indent=2)
                )
                self.wait_spin.setValue(action.get('wait', 1000))
                self.timeout_spin.setValue(action.get('timeout', 10000))
                self.retry_spin.setValue(action.get('retry', 3))
                self.continue_check.setChecked(
                    action.get('continue_on_failure', False)
                )
                self.desc_edit.setPlainText(action.get('description', ''))
        
        except Exception as e:
            logger.error(f"更新步骤详情失败: {e}")
            QMessageBox.critical(self, "错误", f"更新步骤详情失败: {str(e)}")
    
    def _on_type_changed(self, type_name: str):
        """步骤类型变化处理"""
        try:
            # 根据类型调整界面
            is_wait = type_name == 'wait'
            self.target_edit.setEnabled(not is_wait)
            self.action_edit.setEnabled(not is_wait)
            self.params_edit.setEnabled(not is_wait)
            
            # 更新参数提示
            if type_name == 'click':
                self.params_edit.setPlaceholderText(
                    '{\n  "offset_x": 0,\n  "offset_y": 0\n}'
                )
            elif type_name == 'swipe':
                self.params_edit.setPlaceholderText(
                    '{\n  "start_x": 0,\n  "start_y": 0,\n  '
                    '"end_x": 0,\n  "end_y": 0\n}'
                )
            elif type_name == 'text':
                self.params_edit.setPlaceholderText(
                    '{\n  "text": "要输入的文本"\n}'
                )
            else:
                self.params_edit.setPlaceholderText(
                    "请输入动作参数 (JSON格式)"
                )
        
        except Exception as e:
            logger.error(f"处理类型变化失败: {e}")
    
    def _apply_changes(self):
        """应用更改"""
        try:
            items = self.steps_tree.selectedItems()
            if not items:
                return
            
            item = items[0]
            index = self.steps_tree.indexOfTopLevelItem(item)
            if index >= 0:
                # 验证参数
                try:
                    params = json.loads(self.params_edit.toPlainText())
                except json.JSONDecodeError:
                    raise ValueError("参数格式错误，请输入有效的JSON")
                
                # 更新步骤数据
                self.current_actions[index].update({
                    'type': self.type_combo.currentText(),
                    'target': self.target_edit.text(),
                    'action': self.action_edit.text(),
                    'params': params,
                    'wait': self.wait_spin.value(),
                    'timeout': self.timeout_spin.value(),
                    'retry': self.retry_spin.value(),
                    'continue_on_failure': self.continue_check.isChecked(),
                    'description': self.desc_edit.toPlainText()
                })
                
                # 更新显示
                self.load_steps()
                
                # 选中更新的项
                new_item = self.steps_tree.topLevelItem(index)
                if new_item:
                    new_item.setSelected(True)
                
                logger.info(f"步骤 {index + 1} 更新成功")
        
        except Exception as e:
            logger.error(f"应用更改失败: {e}")
            QMessageBox.critical(self, "错误", f"应用更改失败: {str(e)}")
    
    def _save_as_template(self):
        """保存为模板"""
        try:
            # 获取选中的步骤
            items = self.steps_tree.selectedItems()
            if not items:
                QMessageBox.warning(self, "警告", "请先选择要保存的步骤")
                return
            
            # 获取模板名称
            name, ok = QInputDialog.getText(
                self, "保存模板", "请输入模板名称:",
                QLineEdit.EchoMode.Normal
            )
            
            if ok and name:
                # 收集选中的步骤
                steps = []
                for item in items:
                    index = self.steps_tree.indexOfTopLevelItem(item)
                    if index >= 0:
                        steps.append(copy.deepcopy(self.current_actions[index]))
                
                # 保存模板
                template_file = os.path.join(self.template_dir, f"{name}.json")
                with open(template_file, 'w', encoding='utf-8') as f:
                    json.dump(steps, f, ensure_ascii=False, indent=2)
                
                logger.info(f"模板已保存: {template_file}")
                QMessageBox.information(self, "提示", "模板保存成功")
        
        except Exception as e:
            logger.error(f"保存模板失败: {e}")
            QMessageBox.critical(self, "错误", f"保存模板失败: {str(e)}")
    
    def _load_template(self):
        """加载模板"""
        try:
            # 获取可用模板列表
            templates = []
            for file in os.listdir(self.template_dir):
                if file.endswith('.json'):
                    templates.append(file[:-5])  # 移除.json后缀
            
            if not templates:
                QMessageBox.information(self, "提示", "没有可用的模板")
                return
            
            # 选择模板
            name, ok = QInputDialog.getItem(
                self, "加载模板", "请选择模板:",
                templates, 0, False
            )
            
            if ok and name:
                # 加载模板
                template_file = os.path.join(self.template_dir, f"{name}.json")
                with open(template_file, 'r', encoding='utf-8') as f:
                    steps = json.load(f)
                
                # 获取插入位置
                insert_pos = 0
                items = self.steps_tree.selectedItems()
                if items:
                    insert_pos = self.steps_tree.indexOfTopLevelItem(items[0])
                
                # 插入步骤
                for step in steps:
                    self.current_actions.insert(insert_pos, copy.deepcopy(step))
                    insert_pos += 1
                
                # 更新显示
                self.load_steps()
                logger.info(f"已加载模板: {name}")
                QMessageBox.information(self, "提示", "模板加载成功")
        
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            QMessageBox.critical(self, "错误", f"加载模板失败: {str(e)}")
    
    def _manage_templates(self):
        """管理模板"""
        try:
            # 获取可用模板列表
            templates = []
            for file in os.listdir(self.template_dir):
                if file.endswith('.json'):
                    templates.append(file[:-5])  # 移除.json后缀
            
            if not templates:
                QMessageBox.information(self, "提示", "没有可用的模板")
                return
            
            # 创建模板管理对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("管理模板")
            dialog.setMinimumSize(400, 300)
            
            layout = QVBoxLayout()
            
            # 模板列表
            template_list = QTreeWidget()
            template_list.setHeaderLabels(["模板名称", "步骤数"])
            template_list.setAlternatingRowColors(True)
            
            # 加载模板信息
            for name in templates:
                template_file = os.path.join(self.template_dir, f"{name}.json")
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        steps = json.load(f)
                        item = QTreeWidgetItem(template_list)
                        item.setText(0, name)
                        item.setText(1, str(len(steps)))
                except Exception as e:
                    logger.error(f"读取模板 {name} 失败: {e}")
            
            layout.addWidget(template_list)
            
            # 按钮区域
            button_layout = QHBoxLayout()
            
            # 重命名按钮
            rename_btn = QPushButton("重命名")
            rename_btn.clicked.connect(lambda: self._rename_template(template_list))
            button_layout.addWidget(rename_btn)
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda: self._delete_template(template_list))
            button_layout.addWidget(delete_btn)
            
            # 关闭按钮
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(dialog.accept)
            button_layout.addWidget(close_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            dialog.exec()
        
        except Exception as e:
            logger.error(f"管理模板失败: {e}")
            QMessageBox.critical(self, "错误", f"管理模板失败: {str(e)}")
    
    def _rename_template(self, template_list: QTreeWidget):
        """重命名模板"""
        try:
            items = template_list.selectedItems()
            if not items:
                QMessageBox.warning(self, "警告", "请先选择要重命名的模板")
                return
            
            old_name = items[0].text(0)
            new_name, ok = QInputDialog.getText(
                self, "重命名模板", "请输入新名称:",
                QLineEdit.EchoMode.Normal, old_name
            )
            
            if ok and new_name and new_name != old_name:
                old_file = os.path.join(self.template_dir, f"{old_name}.json")
                new_file = os.path.join(self.template_dir, f"{new_name}.json")
                
                if os.path.exists(new_file):
                    raise ValueError("模板名称已存在")
                
                os.rename(old_file, new_file)
                items[0].setText(0, new_name)
                logger.info(f"模板已重命名: {old_name} -> {new_name}")
        
        except Exception as e:
            logger.error(f"重命名模板失败: {e}")
            QMessageBox.critical(self, "错误", f"重命名模板失败: {str(e)}")
    
    def _delete_template(self, template_list: QTreeWidget):
        """删除模板"""
        try:
            items = template_list.selectedItems()
            if not items:
                QMessageBox.warning(self, "警告", "请先选择要删除的模板")
                return
            
            name = items[0].text(0)
            reply = QMessageBox.question(
                self,
                "确认",
                f"确定要删除模板 {name} 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                template_file = os.path.join(self.template_dir, f"{name}.json")
                os.remove(template_file)
                template_list.takeTopLevelItem(
                    template_list.indexOfTopLevelItem(items[0])
                )
                logger.info(f"模板已删除: {name}")
        
        except Exception as e:
            logger.error(f"删除模板失败: {e}")
            QMessageBox.critical(self, "错误", f"删除模板失败: {str(e)}")
    
    def _preview_script(self):
        """预览生成的脚本"""
        try:
            if not self.current_actions:
                raise ValueError("没有可预览的步骤")
            
            # 生成脚本内容
            script_content = self._generate_script()
            
            # 显示预览对话框
            dialog = ScriptPreviewDialog(script_content, self)
            dialog.exec()
            
            logger.info("显示脚本预览")
        
        except Exception as e:
            logger.error(f"预览脚本失败: {e}")
            QMessageBox.critical(self, "错误", f"预览脚本失败: {str(e)}")
    
    def _export_script(self):
        """导出脚本"""
        try:
            if not self.current_actions:
                raise ValueError("没有可导出的步骤")
            
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出脚本",
                os.path.join(os.getcwd(), "scripts"),
                "Python Files (*.py);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # 生成并保存脚本
            script_content = self._generate_script()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            logger.info(f"脚本已导出: {file_path}")
            QMessageBox.information(self, "提示", "脚本导出成功")
        
        except Exception as e:
            logger.error(f"导出脚本失败: {e}")
            QMessageBox.critical(self, "错误", f"导出脚本失败: {str(e)}")
    
    def _script_settings(self):
        """脚本设置"""
        try:
            # 创建设置对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("脚本设置")
            dialog.setMinimumWidth(400)
            
            layout = QVBoxLayout()
            
            # 基本设置
            basic_group = QGroupBox("基本设置")
            basic_layout = QFormLayout()
            
            # 模块名称
            module_edit = QLineEdit()
            module_edit.setText(getattr(self, '_script_module', 'test_module'))
            basic_layout.addRow("模块名称:", module_edit)
            
            # 类名称
            class_edit = QLineEdit()
            class_edit.setText(getattr(self, '_script_class', 'TestCase'))
            basic_layout.addRow("类名称:", class_edit)
            
            # 方法名称
            method_edit = QLineEdit()
            method_edit.setText(getattr(self, '_script_method', 'test_case'))
            basic_layout.addRow("方法名称:", method_edit)
            
            basic_group.setLayout(basic_layout)
            layout.addWidget(basic_group)
            
            # 生成选项
            options_group = QGroupBox("生成选项")
            options_layout = QVBoxLayout()
            
            # 添加文档注释
            doc_check = QCheckBox("添加文档注释")
            doc_check.setChecked(getattr(self, '_add_docstring', True))
            options_layout.addWidget(doc_check)
            
            # 添加日志
            log_check = QCheckBox("添加日志语句")
            log_check.setChecked(getattr(self, '_add_logging', True))
            options_layout.addWidget(log_check)
            
            # 添加异常处理
            error_check = QCheckBox("添加异常处理")
            error_check.setChecked(getattr(self, '_add_error_handling', True))
            options_layout.addWidget(error_check)
            
            # 添加时间戳
            time_check = QCheckBox("添加时间戳")
            time_check.setChecked(getattr(self, '_add_timestamp', True))
            options_layout.addWidget(time_check)
            
            options_group.setLayout(options_layout)
            layout.addWidget(options_group)
            
            # 代码风格
            style_group = QGroupBox("代码风格")
            style_layout = QVBoxLayout()
            
            # 缩进风格
            indent_radio1 = QRadioButton("使用空格 (4个)")
            indent_radio2 = QRadioButton("使用制表符")
            indent_radio1.setChecked(getattr(self, '_use_spaces', True))
            indent_radio2.setChecked(not getattr(self, '_use_spaces', True))
            style_layout.addWidget(indent_radio1)
            style_layout.addWidget(indent_radio2)
            
            style_group.setLayout(style_layout)
            layout.addWidget(style_group)
            
            # 按钮
            button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            # 保存设置
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._script_module = module_edit.text()
                self._script_class = class_edit.text()
                self._script_method = method_edit.text()
                self._add_docstring = doc_check.isChecked()
                self._add_logging = log_check.isChecked()
                self._add_error_handling = error_check.isChecked()
                self._add_timestamp = time_check.isChecked()
                self._use_spaces = indent_radio1.isChecked()
                logger.info("脚本设置已更新")
        
        except Exception as e:
            logger.error(f"更新脚本设置失败: {e}")
            QMessageBox.critical(self, "错误", f"更新脚本设置失败: {str(e)}")
    
    def _generate_script(self) -> str:
        """生成脚本内容"""
        try:
            indent = "    " if getattr(self, '_use_spaces', True) else "\t"
            lines = []
            
            # 导入语句
            lines.extend([
                "import time",
                "import logging",
                "from appium import webdriver",
                "from appium.webdriver.common.appiumby import AppiumBy",
                "from selenium.webdriver.support.ui import WebDriverWait",
                "from selenium.webdriver.support import expected_conditions as EC",
                "",
                ""
            ])
            
            # 类定义
            class_name = getattr(self, '_script_class', 'TestCase')
            lines.append(f"class {class_name}:")
            
            # 文档注释
            if getattr(self, '_add_docstring', True):
                lines.extend([
                    f"{indent}\"\"\"",
                    f"{indent}自动生成的测试用例",
                    f"{indent}",
                    f"{indent}生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"{indent}步骤数量: {len(self.current_actions)}",
                    f"{indent}\"\"\"",
                    ""
                ])
            
            # 初始化方法
            lines.extend([
                f"{indent}def setUp(self):",
                f"{indent}{indent}\"\"\"初始化测试环境\"\"\"",
                f"{indent}{indent}self.driver = None",
                f"{indent}{indent}self.wait = None",
                "",
                f"{indent}def tearDown(self):",
                f"{indent}{indent}\"\"\"清理测试环境\"\"\"",
                f"{indent}{indent}if self.driver:",
                f"{indent}{indent}{indent}self.driver.quit()",
                ""
            ])
            
            # 测试方法
            method_name = getattr(self, '_script_method', 'test_case')
            lines.append(f"{indent}def {method_name}(self):")
            
            # 方法文档注释
            if getattr(self, '_add_docstring', True):
                lines.extend([
                    f"{indent}{indent}\"\"\"",
                    f"{indent}{indent}测试用例主体",
                    f"{indent}{indent}\"\"\"",
                    ""
                ])
            
            # 添加日志设置
            if getattr(self, '_add_logging', True):
                lines.extend([
                    f"{indent}{indent}# 配置日志",
                    f"{indent}{indent}logging.basicConfig(",
                    f"{indent}{indent}{indent}level=logging.INFO,",
                    f"{indent}{indent}{indent}format='%(asctime)s - %(levelname)s - %(message)s'",
                    f"{indent}{indent})",
                    f"{indent}{indent}logger = logging.getLogger(__name__)",
                    ""
                ])
            
            # 添加异常处理
            if getattr(self, '_add_error_handling', True):
                lines.append(f"{indent}{indent}try:")
                indent_level = 3
            else:
                indent_level = 2
            
            # 生成步骤代码
            for i, action in enumerate(self.current_actions, 1):
                # 添加步骤注释
                lines.append(f"{indent * indent_level}# 步骤 {i}: {action.get('description', '')}")
                
                # 添加日志
                if getattr(self, '_add_logging', True):
                    lines.append(
                        f"{indent * indent_level}logger.info("
                        f"'执行步骤 {i}: {action.get('type')} - {action.get('target')}')"
                    )
                
                # 生成步骤代码
                step_code = self._generate_step_code(action, indent * indent_level)
                lines.extend(step_code)
                
                # 添加等待
                if action.get('wait'):
                    lines.append(
                        f"{indent * indent_level}time.sleep({action['wait'] / 1000})"
                    )
                
                lines.append("")
            
            # 添加异常处理代码
            if getattr(self, '_add_error_handling', True):
                lines.extend([
                    f"{indent}{indent}except Exception as e:",
                    f"{indent}{indent}{indent}logger.error(f'测试执行失败: {{e}}')",
                    f"{indent}{indent}{indent}raise"
                ])
            
            return "\n".join(lines)
        
        except Exception as e:
            logger.error(f"生成脚本失败: {e}")
            raise
    
    def _generate_step_code(self, action: Dict, indent: str) -> List[str]:
        """生成单个步骤的代码"""
        lines = []
        action_type = action.get('type', '').lower()
        
        if action_type == 'click':
            lines.extend([
                f"{indent}element = self.wait.until(",
                f"{indent}{indent}EC.element_to_be_clickable(({action.get('by', 'id')}, {action.get('target')}))",
                f"{indent})",
                f"{indent}element.click()"
            ])
        
        elif action_type == 'input':
            lines.extend([
                f"{indent}element = self.wait.until(",
                f"{indent}{indent}EC.presence_of_element_located(({action.get('by', 'id')}, {action.get('target')}))",
                f"{indent})",
                f"{indent}element.clear()",
                f"{indent}element.send_keys({action.get('text', '')})"
            ])
        
        elif action_type == 'swipe':
            params = action.get('params', {})
            lines.extend([
                f"{indent}self.driver.swipe(",
                f"{indent}{indent}start_x={params.get('start_x', 0)},",
                f"{indent}{indent}start_y={params.get('start_y', 0)},",
                f"{indent}{indent}end_x={params.get('end_x', 0)},",
                f"{indent}{indent}end_y={params.get('end_y', 0)},",
                f"{indent}{indent}duration={params.get('duration', 500)}",
                f"{indent})"
            ])
        
        elif action_type == 'wait':
            lines.append(f"{indent}time.sleep({action.get('wait', 1000) / 1000})")
        
        elif action_type == 'assert':
            lines.extend([
                f"{indent}element = self.wait.until(",
                f"{indent}{indent}EC.presence_of_element_located(({action.get('by', 'id')}, {action.get('target')}))",
                f"{indent})",
                f"{indent}assert element.text == {action.get('expected', '')}"
            ])
        
        return lines
    
    def accept(self):
        """确认对话框"""
        try:
            # 发送更新信号
            self.steps_updated.emit(self.current_actions)
            super().accept()
            logger.info("步骤编辑完成")
        
        except Exception as e:
            logger.error(f"确认对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"确认对话框失败: {str(e)}")
    
    def reject(self):
        """取消对话框"""
        try:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要放弃更改吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                super().reject()
                logger.info("放弃步骤编辑")
        
        except Exception as e:
            logger.error(f"取消对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"取消对话框失败: {str(e)}") 