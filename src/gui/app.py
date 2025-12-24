"""
主应用类 - 现代化GUI
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional

from ..config import get_config
from .theme import apply_modern_theme, COLORS
from .test_tab import TestTab
from .editor_tab import EditorTab
from .agent_tab import AgentTab


class TestApp:
    """测试应用GUI - 现代化设计"""
    
    def __init__(self):
        self.config = get_config()
        self.root = tk.Tk()
        self.root.title("SysY 编译器测试框架")
        self.root.geometry(f"{self.config.gui.window_width}x{self.config.gui.window_height}")
        self.root.minsize(900, 650)
        
        # 应用现代主题
        self.style = apply_modern_theme(self.root)
        
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
        
        # 共享状态
        self.test_dir = Path(__file__).parent.parent.parent.resolve()
        self.project_dir: Optional[Path] = None
        
        # 标签页引用
        self.test_tab: Optional[TestTab] = None
        self.editor_tab: Optional[EditorTab] = None
        self.agent_tab: Optional[AgentTab] = None
        
        # 构建界面
        self._build_ui()
        self._setup()
        
        # 定时检查消息队列
        self.root.after(50, self._process_queue)
        
        # 窗口居中
        self._center_window()
    
    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')
    
    def _build_ui(self):
        """构建界面"""
        # 主容器
        main_container = ttk.Frame(self.root, padding=8)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 标题栏
        self._build_header(main_container)
        
        # 创建Notebook（标签页）
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        
        # 标签页1: 测试运行
        test_frame = ttk.Frame(self.notebook)
        self.notebook.add(test_frame, text="  🧪 测试运行  ")
        self.test_tab = TestTab(test_frame, self)
        self.test_tab.build()
        
        # 标签页2: 用例编写
        editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(editor_frame, text="  ✏️ 用例编写  ")
        self.editor_tab = EditorTab(editor_frame, self)
        self.editor_tab.build()
        
        # 标签页3: AI 生成
        agent_frame = ttk.Frame(self.notebook)
        self.notebook.add(agent_frame, text="  🤖 AI 生成  ")
        self.agent_tab = AgentTab(agent_frame, self)
        self.agent_tab.build()
        
        # 状态栏
        self._build_statusbar(main_container)
    
    def _build_header(self, parent):
        """构建标题栏"""
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 4))
        
        # 标题
        title = ttk.Label(
            header, 
            text="SysY 编译器测试框架",
            style='Title.TLabel'
        )
        title.pack(side=tk.LEFT)
        
        # 版本信息
        version = ttk.Label(
            header,
            text="v2.0",
            style='Status.TLabel'
        )
        version.pack(side=tk.LEFT, padx=(8, 0))
    
    def _build_statusbar(self, parent):
        """构建状态栏"""
        statusbar = ttk.Frame(parent)
        statusbar.pack(fill=tk.X, pady=(8, 0))
        
        # 左侧：项目路径
        self.project_status = ttk.Label(
            statusbar,
            text="未选择项目",
            style='Status.TLabel'
        )
        self.project_status.pack(side=tk.LEFT)
        
        # 右侧：时间
        self.time_label = ttk.Label(
            statusbar,
            text="",
            style='Status.TLabel'
        )
        self.time_label.pack(side=tk.RIGHT)
        self._update_time()
    
    def _update_time(self):
        """更新时间显示"""
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=now)
        self.root.after(1000, self._update_time)
    
    def update_project_status(self, path: Optional[Path] = None):
        """更新项目状态"""
        if path:
            self.project_status.configure(text=f"📁 {path.name}")
        else:
            self.project_status.configure(text="未选择项目")
    
    def _setup(self):
        """初始化设置"""
        self.test_tab.setup_default_project()
        self.editor_tab.refresh_libs(set_default=True)
    
    def _process_queue(self):
        """处理消息队列"""
        if self.test_tab:
            self.test_tab.process_queue()
        if self.agent_tab:
            self.agent_tab.process_queue()
        self.root.after(50, self._process_queue)
    
    def run(self):
        """运行应用"""
        self.root.mainloop()


def run_gui():
    """启动GUI"""
    app = TestApp()
    app.run()
