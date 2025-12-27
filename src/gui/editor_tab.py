"""
用例编写标签页 - 现代化设计
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from typing import TYPE_CHECKING

from .base import BaseTab
from .theme import COLORS, create_styled_text
from .widgets import IconButton
from ..discovery import TestDiscovery

if TYPE_CHECKING:
    from .app import TestApp


class EditorTab(BaseTab):
    """用例编写标签页"""
    
    def build(self):
        """构建用例编写标签页"""
        main_frame = ttk.Frame(self.parent, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._build_toolbar(main_frame)
        self._build_editor_section(main_frame)
        self._build_status_section(main_frame)
    
    def _build_toolbar(self, parent):
        """工具栏 - 分两行显示"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 12))
        
        # 第一行：目标目录
        row1 = ttk.Frame(toolbar)
        row1.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(row1, text="📁 保存到").pack(side=tk.LEFT)
        
        self.editor_dir_var = tk.StringVar()
        self.editor_dir_combo = ttk.Combobox(
            row1, textvariable=self.editor_dir_var, 
            width=35, font=(self.config.gui.get_font(), 10)
        )
        self.editor_dir_combo.pack(side=tk.LEFT, padx=(12, 8))
        
        IconButton(row1, icon='plus', text='新建库',
                   command=self._create_new_lib).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(row1, icon='refresh', text='刷新',
                   command=self.refresh_libs).pack(side=tk.LEFT)
        
        # 第二行：编号和操作按钮
        row2 = ttk.Frame(toolbar)
        row2.pack(fill=tk.X)
        
        # 左侧：编号
        left_frame = ttk.Frame(row2)
        left_frame.pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="编号").pack(side=tk.LEFT)
        
        self.editor_num_var = tk.StringVar(value="1")
        num_entry = ttk.Entry(left_frame, textvariable=self.editor_num_var, 
                              width=5, font=(self.config.gui.get_font(), 10))
        num_entry.pack(side=tk.LEFT, padx=(8, 4))
        
        IconButton(left_frame, text='自动编号',
                   command=self._auto_number).pack(side=tk.LEFT)
        
        # 右侧：操作按钮
        right_frame = ttk.Frame(row2)
        right_frame.pack(side=tk.RIGHT)
        
        IconButton(right_frame, icon='clear', text='清空',
                   command=self._clear_editor).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(right_frame, text='保存并继续',
                   command=self._save_and_next).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(right_frame, icon='save', text='保存',
                   command=self._save_testcase, style='Accent.TButton').pack(side=tk.LEFT)
    
    def _build_editor_section(self, parent):
        """编辑区"""
        # 使用PanedWindow实现可调整大小
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：源代码编辑
        code_frame = ttk.Frame(paned)
        paned.add(code_frame, weight=3)
        
        # 代码区标题
        code_header = ttk.Frame(code_frame)
        code_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(code_header, text="📝 SysY 源代码",
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(code_header, text="testfile.txt", style='Status.TLabel').pack(side=tk.RIGHT)
        
        # 代码编辑器容器
        code_container = ttk.Frame(code_frame)
        code_container.pack(fill=tk.BOTH, expand=True)
        
        # 行号
        self.line_numbers = tk.Text(
            code_container, width=4, padx=4, pady=8,
            bg=COLORS['bg_tertiary'], fg=COLORS['fg_muted'],
            font=(self.config.gui.get_font(), self.config.gui.font_size),
            state=tk.DISABLED, borderwidth=0, highlightthickness=0
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # 代码文本框
        self.code_text = create_styled_text(
            code_container,
            font=(self.config.gui.get_font(), self.config.gui.font_size),
            wrap=tk.NONE, undo=True
        )
        code_scroll_y = ttk.Scrollbar(code_container, orient=tk.VERTICAL,
                                       command=self._sync_scroll)
        code_scroll_x = ttk.Scrollbar(code_frame, orient=tk.HORIZONTAL,
                                       command=self.code_text.xview)
        self.code_text.configure(yscrollcommand=self._on_code_scroll,
                                  xscrollcommand=code_scroll_x.set)
        
        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        code_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        code_scroll_x.pack(fill=tk.X)
        
        # 绑定事件更新行号
        self.code_text.bind('<KeyRelease>', self._update_line_numbers)
        self.code_text.bind('<MouseWheel>', self._update_line_numbers)
        
        # 右侧：输入数据编辑
        input_frame = ttk.Frame(paned)
        paned.add(input_frame, weight=1)
        
        # 输入区标题
        input_header = ttk.Frame(input_frame)
        input_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(input_header, text="📥 输入数据",
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(input_header, text="input.txt", style='Status.TLabel').pack(side=tk.RIGHT)
        
        # 输入文本框
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=tk.BOTH, expand=True)
        
        self.input_text = create_styled_text(
            input_container,
            font=(self.config.gui.get_font(), self.config.gui.font_size),
            wrap=tk.NONE, undo=True
        )
        input_scroll = ttk.Scrollbar(input_container, orient=tk.VERTICAL,
                                      command=self.input_text.yview)
        self.input_text.configure(yscrollcommand=input_scroll.set)
        
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 提示
        ttk.Label(input_frame, text="💡 每行一个整数", 
                  style='Status.TLabel').pack(anchor=tk.W, pady=(6, 0))
        
        # 初始化行号
        self._update_line_numbers()
    
    def _build_status_section(self, parent):
        """状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(12, 0))
        
        self.editor_status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(
            status_frame, textvariable=self.editor_status_var,
            style='Success.TLabel'
        )
        self.status_label.pack(side=tk.LEFT)
        
        # 字符统计
        self.char_count_var = tk.StringVar(value="0 字符")
        ttk.Label(status_frame, textvariable=self.char_count_var,
                  style='Status.TLabel').pack(side=tk.RIGHT)
        
        # 绑定更新字符统计
        self.code_text.bind('<KeyRelease>', self._update_char_count, add='+')
    
    def _sync_scroll(self, *args):
        """同步滚动"""
        self.code_text.yview(*args)
        self.line_numbers.yview(*args)
    
    def _on_code_scroll(self, *args):
        """代码滚动时同步行号"""
        self.line_numbers.yview_moveto(args[0])
        return True
    
    def _update_line_numbers(self, event=None):
        """更新行号"""
        self.line_numbers.config(state=tk.NORMAL)
        self.line_numbers.delete(1.0, tk.END)
        
        line_count = int(self.code_text.index('end-1c').split('.')[0])
        line_numbers_text = '\n'.join(str(i) for i in range(1, line_count + 1))
        self.line_numbers.insert(1.0, line_numbers_text)
        
        self.line_numbers.config(state=tk.DISABLED)
    
    def _update_char_count(self, event=None):
        """更新字符统计"""
        content = self.code_text.get(1.0, tk.END)
        char_count = len(content.strip())
        line_count = content.count('\n')
        self.char_count_var.set(f"{char_count} 字符 | {line_count} 行")

    # ========== 事件处理 ==========
    
    def refresh_libs(self, set_default: bool = False):
        """刷新测试库列表"""
        testfiles_dir = self.test_dir / "testfiles"
        libs = TestDiscovery.discover_test_libs(testfiles_dir)
        
        lib_names = [str(lib.relative_to(testfiles_dir)) for lib in libs]
        
        # 生成基于当前时间的默认目录名
        default_name = datetime.now().strftime("%Y%m%d_%H%M")
        if default_name not in lib_names:
            lib_names.insert(0, default_name)
        
        self.editor_dir_combo['values'] = lib_names
        
        if set_default or not self.editor_dir_var.get():
            self.editor_dir_combo.set(default_name)
    
    def _create_new_lib(self):
        """创建新测试库"""
        name = simpledialog.askstring("新建测试库", "请输入测试库名称:",
                                       parent=self.parent)
        if not name:
            return
        
        new_dir = self.test_dir / "testfiles" / name
        if new_dir.exists():
            messagebox.showerror("错误", f"测试库 '{name}' 已存在")
            return
        
        new_dir.mkdir(parents=True)
        self.refresh_libs()
        self.app.test_tab.refresh_lists()
        self.editor_dir_combo.set(name)
        self.editor_status_var.set(f"✓ 已创建: {name}")
    
    def _auto_number(self):
        """自动获取下一个编号"""
        lib_name = self.editor_dir_var.get()
        if not lib_name:
            messagebox.showwarning("提示", "请先选择测试库")
            return
        
        lib_path = self.test_dir / "testfiles" / lib_name
        next_num = TestDiscovery.get_next_testfile_number(lib_path)
        self.editor_num_var.set(str(next_num))
        self.editor_status_var.set(f"下一个编号: {next_num}")
    
    def _save_testcase(self) -> bool:
        """保存测试用例"""
        lib_name = self.editor_dir_var.get()
        if not lib_name:
            messagebox.showwarning("提示", "请先选择测试库")
            return False
        
        try:
            num = int(self.editor_num_var.get())
        except ValueError:
            messagebox.showerror("错误", "编号必须是数字")
            return False
        
        code = self.code_text.get(1.0, tk.END).rstrip()
        if not code:
            messagebox.showwarning("提示", "请输入源代码")
            return False
        
        lib_path = self.test_dir / "testfiles" / lib_name
        lib_path.mkdir(parents=True, exist_ok=True)
        
        # 保存testfile
        testfile_path = lib_path / f"testfile{num}.txt"
        with open(testfile_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        
        # 保存input
        input_data = self.input_text.get(1.0, tk.END).rstrip()
        input_path = lib_path / f"input{num}.txt"
        with open(input_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(input_data)
        
        self.editor_status_var.set(f"✓ 已保存: testfile{num}.txt")
        self.app.test_tab.refresh_lists()
        return True
    
    def _save_and_next(self):
        """保存并新建下一个"""
        if self._save_testcase():
            try:
                num = int(self.editor_num_var.get())
                self.editor_num_var.set(str(num + 1))
            except ValueError:
                pass
            self._clear_editor()
            self.editor_status_var.set(f"✓ 已保存，继续编写下一个")
    
    def _clear_editor(self):
        """清空编辑器"""
        self.code_text.delete(1.0, tk.END)
        self.input_text.delete(1.0, tk.END)
        self._update_line_numbers()
        self._update_char_count()
