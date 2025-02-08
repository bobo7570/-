class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
        
        # 连接设备选择信号
        self.device_tab = self.findChild(QWidget, "device_tab")
        self.record_tab = self.findChild(QWidget, "record_tab")
        if self.device_tab and self.record_tab:
            self.device_tab.device_selected.connect(self.record_tab.set_device)
            logger.info("设备选择信号已连接到录制标签页")
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('App自动化工具')
        self.setMinimumSize(800, 600)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # 添加设备管理标签页
        self.device_tab = DeviceTab(self.config, self)
        self.tab_widget.addTab(self.device_tab, "设备管理")
        
        # 添加录制标签页
        self.record_tab = RecordTab(self.config, self)
        self.record_tab.setObjectName("record_tab")
        self.tab_widget.addTab(self.record_tab, "操作录制")

        # ... existing code ... 