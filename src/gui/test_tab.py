"""
测试运行标签页 - 现代化设计
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import threading
import queue
import subprocess

from .base import BaseTab, OutputMixin
from .theme import COLORS, create_styled_listbox, create_styled_text
from .widgets import AnimatedProgressBar, IconButton
from ..discovery import TestDiscovery
from ..tester import CompilerTester

if TYPE_CHECKING:
    from .app import TestApp


class TestTab(BaseTab, OutputMixin):
    """测试运行标签页"""
    
    def __init__(self, parent: ttk.Frame, app: 'TestApp'):
        super().__init__(parent, app)
        self.tester: Optional[CompilerTester] = None
        self.is_running = False
        self.message_queue = queue.Queue()
        self.current_lib_path: Optional[Path] = None
        self.case_menu: Optional[tk.Menu] = None
    
    def build(self):
        """构建测试运行标签页"""
        main_frame = ttk.Frame(self.parent, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上部：配置和选择
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        self._build_config_section(top_frame)
        self._build_selection_section(top_frame)
        
        # 分隔线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)
        
        # 下部：控制和输出
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        self._build_control_section(bottom_frame)
        self._build_output_section(bottom_frame)
    
    def _build_config_section(self, parent):
        """项目配置区"""
        config_frame = ttk.Frame(parent)
        config_frame.pack(fill=tk.X, pady=(0, 12))
        
        # 项目路径
        path_frame = ttk.Frame(config_frame)
        path_frame.pack(fill=tk.X)
        
        ttk.Label(path_frame, text="编译器项目", style='Card.TLabel').pack(side=tk.LEFT)
        
        self.project_var = tk.StringVar()
        self.project_entry = ttk.Entry(
            path_frame, textvariable=self.project_var,
            font=(self.config.gui.get_font(), 10)
        )
        self.project_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 8))
        
        IconButton(path_frame, icon='folder', text='浏览', 
                   command=self._browse_project).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(path_frame, icon='play', text='编译', 
                   command=self._compile_project, style='Accent.TButton').pack(side=tk.LEFT)
        
        # 编译器信息
        self.compiler_info = ttk.Label(
            config_frame, text="", style='Status.TLabel'
        )
        self.compiler_info.pack(anchor=tk.W, pady=(8, 0))
    
    def _build_selection_section(self, parent):
        """测试选择区"""
        select_frame = ttk.Frame(parent)
        select_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：测试库列表
        left_frame = ttk.Frame(select_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        
        # 标题栏
        left_header = ttk.Frame(left_frame)
        left_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(left_header, text="📚 测试库", style='Card.TLabel',
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        self.lib_count_label = ttk.Label(left_header, text="", style='Status.TLabel')
        self.lib_count_label.pack(side=tk.RIGHT)
        
        # 列表框容器
        lib_container = ttk.Frame(left_frame)
        lib_container.pack(fill=tk.BOTH, expand=True)
        
        self.lib_listbox = create_styled_listbox(
            lib_container, selectmode=tk.SINGLE, exportselection=False,
            font=(self.config.gui.get_font(), self.config.gui.font_size)
        )
        lib_scroll = ttk.Scrollbar(lib_container, orient=tk.VERTICAL, 
                                    command=self.lib_listbox.yview)
        self.lib_listbox.configure(yscrollcommand=lib_scroll.set)
        
        self.lib_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lib_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.lib_listbox.bind('<<ListboxSelect>>', self._on_lib_select)
        
        # 右侧：测试用例列表
        right_frame = ttk.Frame(select_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        
        # 标题栏
        right_header = ttk.Frame(right_frame)
        right_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(right_header, text="📝 测试用例", style='Card.TLabel',
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        self.case_count_label = ttk.Label(right_header, text="", style='Status.TLabel')
        self.case_count_label.pack(side=tk.RIGHT)
        IconButton(right_header, text='记事本打开',
                   command=self._open_selected_testfile_in_notepad).pack(side=tk.RIGHT, padx=(0, 6))
        
        # 列表框容器
        case_container = ttk.Frame(right_frame)
        case_container.pack(fill=tk.BOTH, expand=True)
        
        self.case_listbox = create_styled_listbox(
            case_container, selectmode=tk.EXTENDED, exportselection=False,
            font=(self.config.gui.get_font(), self.config.gui.font_size)
        )
        case_scroll = ttk.Scrollbar(case_container, orient=tk.VERTICAL,
                                     command=self.case_listbox.yview)
        self.case_listbox.configure(yscrollcommand=case_scroll.set)
        
        self.case_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        case_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.case_listbox.bind('<Double-Button-1>', lambda e: self._open_selected_testfile_in_notepad())
        self.case_listbox.bind('<Button-3>', self._show_case_context_menu)

    def _build_control_section(self, parent):
        """控制区"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 12))
        
        # 左侧按钮组
        left_btns = ttk.Frame(control_frame)
        left_btns.pack(side=tk.LEFT)
        
        IconButton(left_btns, icon='refresh', text='刷新',
                   command=self.refresh_lists).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(left_btns, icon='check', text='全选',
                   command=self._select_all_cases).pack(side=tk.LEFT, padx=(0, 4))
        
        ttk.Separator(left_btns, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        
        IconButton(left_btns, icon='play', text='运行选中',
                   command=self._run_selected).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(left_btns, icon='play', text='运行当前库',
                   command=self._run_current_lib).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(left_btns, icon='play', text='运行全部',
                   command=self._run_all, style='Accent.TButton').pack(side=tk.LEFT)
        
        # 右侧：停止按钮和状态
        right_btns = ttk.Frame(control_frame)
        right_btns.pack(side=tk.RIGHT)
        
        self.result_label = ttk.Label(right_btns, text="", style='Status.TLabel')
        self.result_label.pack(side=tk.LEFT, padx=(0, 12))
        
        self.stop_btn = IconButton(right_btns, icon='stop', text='停止',
                                    command=self._stop_test, style='Danger.TButton')
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn.configure(state=tk.DISABLED)
        
        # 进度条
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.progress = AnimatedProgressBar(progress_frame)
        self.progress.pack(fill=tk.X)
        
        # 状态文本
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                       style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)
    
    def _build_output_section(self, parent):
        """输出日志区"""
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题栏
        header = ttk.Frame(output_frame)
        header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(header, text="📋 输出日志", style='Card.TLabel',
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        IconButton(header, icon='save', text='导出',
                   command=self._export_log).pack(side=tk.RIGHT, padx=(0, 4))
        IconButton(header, icon='clear', text='清空',
                   command=self._clear_output).pack(side=tk.RIGHT)
        
        # 输出文本框
        text_container = ttk.Frame(output_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = create_styled_text(
            text_container,
            font=(self.config.gui.get_font(), self.config.gui.font_size - 1),
            wrap=tk.WORD, state=tk.DISABLED
        )
        output_scroll = ttk.Scrollbar(text_container, orient=tk.VERTICAL,
                                       command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=output_scroll.set)
        
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 设置标签样式
        self._setup_output_tags()
    
    def _export_log(self):
        content = self.output_text.get("1.0", tk.END)
        if not content.strip():
            messagebox.showinfo("提示", "当前没有可导出的日志")
            return
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"log_{ts}.txt"
        
        file_path = filedialog.asksaveasfilename(
            title="导出日志",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
            return
        
        self._log(f"✓ 已导出日志: {file_path}", "pass")
    
    # ========== 事件处理 ==========
    
    def setup_default_project(self):
        """设置默认项目路径"""
        default_path = (self.test_dir / self.config.compiler_project_dir).resolve()
        if default_path.exists():
            self.project_var.set(str(default_path))
            self.app.project_dir = default_path
            self.app.update_project_status(default_path)
            self._update_compiler_info()
        self.refresh_lists()
    
    def _update_compiler_info(self):
        """更新编译器信息"""
        if self.app.project_dir:
            tester = CompilerTester(self.app.project_dir, self.test_dir)
            lang = tester.get_compiler_language().upper()
            self.compiler_info.configure(text=f"🔧 检测到 {lang} 编译器")
    
    def _browse_project(self):
        """浏览选择项目目录"""
        path = filedialog.askdirectory(title="选择编译器项目目录")
        if path:
            self.project_var.set(path)
            self.app.project_dir = Path(path)
            self.app.update_project_status(Path(path))
            self._update_compiler_info()
    
    def _compile_project(self):
        """编译项目"""
        if not self.app.project_dir:
            messagebox.showerror("错误", "请先选择项目目录")
            return
        
        self.tester = CompilerTester(self.app.project_dir, self.test_dir)
        lang = self.tester.get_compiler_language().upper()
        self._log(f"⚙️ 正在编译 {lang} 项目...", 'info')
        self.status_var.set(f"正在编译 {lang} 项目...")
        
        def compile_task():
            success, msg = self.tester.compile_project()
            self.message_queue.put(('compile_done', success, msg))
        
        threading.Thread(target=compile_task, daemon=True).start()
    
    def refresh_lists(self):
        """刷新测试库列表"""
        self.lib_listbox.delete(0, tk.END)
        self.case_listbox.delete(0, tk.END)
        
        testfiles_dir = self.test_dir / "testfiles"
        libs = TestDiscovery.discover_test_libs(testfiles_dir)
        
        total_cases = 0
        for lib in libs:
            rel_path = lib.relative_to(testfiles_dir)
            cases = TestDiscovery.discover_in_dir(lib)
            total_cases += len(cases)
            self.lib_listbox.insert(tk.END, f"{rel_path} ({len(cases)})")
        
        self.lib_count_label.configure(text=f"{len(libs)} 个库")
        self._log(f"📚 发现 {len(libs)} 个测试库，共 {total_cases} 个用例", 'info')
    
    def _on_lib_select(self, event):
        """选择测试库时更新用例列表"""
        selection = self.lib_listbox.curselection()
        if not selection:
            return
        
        self.case_listbox.delete(0, tk.END)
        lib_name = self.lib_listbox.get(selection[0]).split(' (')[0]
        self.current_lib_path = self.test_dir / "testfiles" / lib_name
        
        cases = TestDiscovery.discover_in_dir(self.current_lib_path)
        for case in cases:
            self.case_listbox.insert(tk.END, case.name)
        
        self.case_count_label.configure(text=f"{len(cases)} 个用例")
    
    def _select_all_cases(self):
        """全选测试用例"""
        self.case_listbox.select_set(0, tk.END)
    
    def _get_current_lib_path(self) -> Optional[Path]:
        """获取当前测试库路径"""
        return self.current_lib_path
    
    def _get_selected_case(self):
        lib_path = self._get_current_lib_path()
        if not lib_path:
            return None
        
        selection = self.case_listbox.curselection()
        if not selection:
            return None
        
        all_cases = TestDiscovery.discover_in_dir(lib_path)
        idx = selection[0]
        if idx < 0 or idx >= len(all_cases):
            return None
        
        return all_cases[idx]
    
    def _open_in_notepad(self, file_path: Path):
        if not file_path.exists():
            messagebox.showerror("错误", f"文件不存在: {file_path}")
            return
        
        try:
            subprocess.Popen(["notepad.exe", str(file_path)])
        except Exception as e:
            messagebox.showerror("错误", f"打开失败: {e}")
    
    def _open_selected_testfile_in_notepad(self):
        case = self._get_selected_case()
        if not case:
            messagebox.showinfo("提示", "请先选择一个测试用例")
            return
        self._open_in_notepad(case.testfile)
    
    def _open_selected_input_in_notepad(self):
        case = self._get_selected_case()
        if not case:
            messagebox.showinfo("提示", "请先选择一个测试用例")
            return
        if not case.input_file:
            messagebox.showinfo("提示", "该用例没有 input 文件")
            return
        self._open_in_notepad(case.input_file)
    
    def _show_case_context_menu(self, event):
        idx = self.case_listbox.nearest(event.y)
        if idx < 0:
            return
        
        current = self.case_listbox.curselection()
        if not current or idx not in current:
            self.case_listbox.selection_clear(0, tk.END)
            self.case_listbox.selection_set(idx)
            self.case_listbox.activate(idx)
        
        if self.case_menu is None:
            self.case_menu = tk.Menu(self.parent, tearoff=0)
        
        self.case_menu.delete(0, tk.END)
        self.case_menu.add_command(label="用记事本打开 testfile", command=self._open_selected_testfile_in_notepad)
        case = self._get_selected_case()
        if case and case.input_file:
            self.case_menu.add_command(label="用记事本打开 input", command=self._open_selected_input_in_notepad)
        
        try:
            self.case_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.case_menu.grab_release()

    # ========== 测试运行 ==========
    
    def _run_selected(self):
        """运行选中的测试用例"""
        lib_path = self._get_current_lib_path()
        if not lib_path:
            messagebox.showwarning("提示", "请先选择测试库")
            return
        
        case_selection = self.case_listbox.curselection()
        if not case_selection:
            messagebox.showwarning("提示", "请选择要运行的测试用例")
            return
        
        all_cases = TestDiscovery.discover_in_dir(lib_path)
        selected_cases = [all_cases[i] for i in case_selection]
        self._run_tests(selected_cases, f"运行 {len(selected_cases)} 个选中测试")
    
    def _run_current_lib(self):
        """运行当前测试库的所有测试"""
        lib_path = self._get_current_lib_path()
        if not lib_path:
            messagebox.showwarning("提示", "请先选择测试库")
            return
        
        cases = TestDiscovery.discover_in_dir(lib_path)
        self._run_tests(cases, f"运行测试库: {lib_path.name}")
    
    def _run_all(self):
        """运行所有测试"""
        testfiles_dir = self.test_dir / "testfiles"
        libs = TestDiscovery.discover_test_libs(testfiles_dir)
        
        all_cases = []
        for lib in libs:
            cases = TestDiscovery.discover_in_dir(lib)
            for case in cases:
                case.name = f"{lib.name}/{case.name}"
            all_cases.extend(cases)
        
        self._run_tests(all_cases, f"运行所有测试 ({len(all_cases)} 个)")
    
    def _run_tests(self, cases: list, title: str):
        """运行测试"""
        if self.is_running:
            messagebox.showwarning("提示", "测试正在运行中")
            return
        
        if not self.app.project_dir:
            messagebox.showerror("错误", "请先选择项目目录")
            return
        
        self.is_running = True
        self.stop_btn.configure(state=tk.NORMAL)
        self._clear_output()
        self.progress.set(0)
        self.result_label.configure(text="")
        
        max_workers = self.config.parallel.max_workers
        self._log(f"🚀 {title}", 'header')
        self._log(f"   并行线程: {max_workers}", 'dim')
        
        def test_task():
            self.tester = CompilerTester(self.app.project_dir, self.test_dir)
            lang = self.tester.get_compiler_language().upper()
            self.message_queue.put(('status', f"正在编译 {lang} 项目..."))
            
            success, msg = self.tester.compile_project()
            if not success:
                self.message_queue.put(('compile_failed', msg))
                return
            
            self.message_queue.put(('compile_done', True, msg))
            
            if not self.is_running:
                self.message_queue.put(('stopped', 0, 0))
                return
            
            passed, failed = 0, 0
            
            def on_result(case, result, progress):
                nonlocal passed, failed
                if not self.is_running:
                    return
                
                if result.passed:
                    passed += 1
                    self.message_queue.put(('result', case.name, result, True))
                else:
                    failed += 1
                    self.message_queue.put(('result', case.name, result, False))
                
                self.message_queue.put(('progress', progress, f"{passed + failed}/{len(cases)}"))
            
            try:
                self.tester.test_parallel(cases, max_workers, callback=on_result)
            except Exception as e:
                self.message_queue.put(('error', str(e)))
                return
            
            if self.is_running:
                self.message_queue.put(('done', passed, failed))
            else:
                self.message_queue.put(('stopped', passed, failed))
        
        threading.Thread(target=test_task, daemon=True).start()
    
    def _stop_test(self):
        """停止测试"""
        self.is_running = False
    
    # ========== 消息处理 ==========
    
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                msg = self.message_queue.get_nowait()
                
                if msg[0] == 'status':
                    _, status = msg
                    self.status_var.set(status)
                    self._log(f"⏳ {status}", 'info')
                
                elif msg[0] == 'compile_done':
                    _, success, text = msg
                    icon = '✓' if success else '✗'
                    self._log(f"{icon} {text}", 'pass' if success else 'error')
                    self.status_var.set("编译完成，开始测试...")
                
                elif msg[0] == 'compile_failed':
                    _, error_msg = msg
                    self._log(f"✗ 编译失败: {error_msg}", 'error')
                    self._finish_test(0, 0, stopped=True)
                
                elif msg[0] == 'progress':
                    _, progress, status = msg
                    self.progress.set(progress)
                    self.status_var.set(f"测试中... {status}")
                
                elif msg[0] == 'result':
                    _, name, result, passed = msg
                    if passed:
                        self._log(f"✓ {name}", 'pass')
                    else:
                        self._log_failure(
                            name=name,
                            status=result.status.value,
                            message=result.message or "",
                            actual=result.actual_output,
                            expected=result.expected_output
                        )
                
                elif msg[0] == 'error':
                    _, error_msg = msg
                    self._log(f"✗ 错误: {error_msg}", 'error')
                    self._finish_test(0, 0, stopped=True)
                
                elif msg[0] == 'done':
                    _, passed, failed = msg
                    self._finish_test(passed, failed)
                
                elif msg[0] == 'stopped':
                    _, passed, failed = msg
                    self._log("⏹ 测试已停止", 'warning')
                    self._finish_test(passed, failed, stopped=True)
                
        except:
            pass
    
    def _finish_test(self, passed: int, failed: int, stopped: bool = False):
        """完成测试"""
        self.is_running = False
        self.stop_btn.configure(state=tk.DISABLED)
        self.progress.set(100)
        
        total = passed + failed
        self.status_var.set("已停止" if stopped else "完成")
        
        if failed == 0 and total > 0:
            self.result_label.configure(text=f"✓ 全部通过 ({passed}/{total})", 
                                         style='Success.TLabel')
            self._log(f"\n🎉 全部通过 {passed}/{total}", 'pass')
        elif total > 0:
            self.result_label.configure(text=f"✗ {failed} 失败 ({passed}/{total})",
                                         style='Error.TLabel')
            self._log(f"\n📊 结果: {passed} 通过, {failed} 失败", 'fail')
        else:
            self.result_label.configure(text="无测试运行", style='Status.TLabel')
