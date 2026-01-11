"""
测试运行标签页 - 现代化设计
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING, Tuple
import threading
import queue
import subprocess
import time

from .base import BaseTab, OutputMixin
from .theme import COLORS, create_styled_listbox, create_styled_text
from .widgets import AnimatedProgressBar, IconButton
from ..discovery import TestDiscovery
from ..multi_runner import compile_testers, test_multi
from ..tester import CompilerTester
from ..utils import format_duration
from ..zip_compilers import ZipCompilerInstance, discover_zip_compilers, extract_zip_instance

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
        self.zip_instances: List[ZipCompilerInstance] = []
        self._stop_event = threading.Event()
    
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
        
        # zip 目录
        path_frame = ttk.Frame(config_frame)
        path_frame.pack(fill=tk.X)
        
        ttk.Label(path_frame, text="源码 zip 目录", style='Card.TLabel').pack(side=tk.LEFT)
        
        self.project_var = tk.StringVar()
        self.project_entry = ttk.Entry(
            path_frame, textvariable=self.project_var,
            font=(self.config.gui.get_font(), 10)
        )
        self.project_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(12, 8))
        
        IconButton(path_frame, icon='folder', text='浏览', 
                   command=self._browse_project).pack(side=tk.LEFT, padx=(0, 4))
        IconButton(path_frame, icon='play', text='编译选中', 
                   command=self._compile_project, style='Accent.TButton').pack(side=tk.LEFT)

        # 编译器实例选择
        inst_frame = ttk.Frame(config_frame)
        inst_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        inst_header = ttk.Frame(inst_frame)
        inst_header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(inst_header, text="📦 编译器实例（zip）", style='Card.TLabel',
                  font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        self.inst_count_label = ttk.Label(inst_header, text="", style='Status.TLabel')
        self.inst_count_label.pack(side=tk.RIGHT)
        IconButton(inst_header, icon='refresh', text='刷新实例',
                   command=self.refresh_compilers).pack(side=tk.RIGHT, padx=(0, 8))

        inst_container = ttk.Frame(inst_frame)
        inst_container.pack(fill=tk.BOTH, expand=True)
        self.inst_listbox = create_styled_listbox(
            inst_container,
            selectmode=tk.EXTENDED,
            exportselection=False,
            font=(self.config.gui.get_font(), self.config.gui.font_size),
            height=4,
        )
        inst_scroll = ttk.Scrollbar(inst_container, orient=tk.VERTICAL, command=self.inst_listbox.yview)
        self.inst_listbox.configure(yscrollcommand=inst_scroll.set)
        self.inst_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inst_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.inst_listbox.bind('<<ListboxSelect>>', lambda e: self._update_compiler_info())
        
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
            self.app.zip_dir = default_path
            self.app.update_project_status(default_path)
        self.refresh_lists()
    
    def _update_compiler_info(self):
        """更新编译器信息"""
        valid = [i for i in self.zip_instances if i.valid]
        selection = self.inst_listbox.curselection() if hasattr(self, "inst_listbox") else ()
        selected = [valid[i] for i in selection if 0 <= i < len(valid)] if selection else valid

        if not selected:
            self.compiler_info.configure(text="🔧 未发现可用编译器实例（请检查 zip_dir 与压缩包内容）")
            return

        if not selection:
            msg_prefix = f"🔧 已发现 {len(valid)} 个实例（未选择时默认全部）"
        else:
            msg_prefix = f"🔧 已选择 {len(selected)}/{len(valid)} 个实例"

        langs = sorted({(i.language or "unknown").upper() for i in selected})
        self.compiler_info.configure(text=f"{msg_prefix} | 语言: {', '.join(langs)}")
    
    def _browse_project(self):
        """浏览选择 zip 目录"""
        path = filedialog.askdirectory(title="选择源码 zip 目录")
        if path:
            self.project_var.set(path)
            self.app.zip_dir = Path(path)
            self.app.update_project_status(Path(path))
            self.refresh_compilers()
    
    def _compile_project(self):
        """编译选中的编译器实例（zip）"""
        zip_dir = self._get_zip_dir()
        if not zip_dir:
            messagebox.showerror("错误", "请先选择 zip 目录")
            return

        selected = self._get_selected_instances()
        if not selected:
            messagebox.showerror("错误", "未找到可用的编译器实例（zip）")
            return

        self._clear_output()
        self._stop_event.clear()
        self._log(f"⚙️ 正在编译 {len(selected)} 个编译器实例...", 'info')
        self.status_var.set("正在编译...")

        def compile_task():
            testers: List[CompilerTester] = []
            for inst in selected:
                try:
                    extracted = extract_zip_instance(inst, self.test_dir / ".tmp" / "zip_sources")
                    testers.append(CompilerTester(extracted, self.test_dir, instance_name=inst.name))
                except Exception as e:
                    self.message_queue.put(("compile_instance", inst.name, False, f"解包失败: {e}"))

            def on_compile(tester: CompilerTester, ok: bool, msg: str):
                self.message_queue.put(("compile_instance", tester.instance_name, ok, msg))

            compile_testers(testers, max_workers=self.config.parallel.max_workers, stop_event=self._stop_event, callback=on_compile)
            self.message_queue.put(("compile_all_done",))

        threading.Thread(target=compile_task, daemon=True).start()
    
    def refresh_lists(self):
        """刷新测试库列表"""
        self.lib_listbox.delete(0, tk.END)
        self.case_listbox.delete(0, tk.END)
        
        testcases_dir = self.test_dir / "testcases"
        libs = TestDiscovery.discover_test_libs(testcases_dir)
        
        total_cases = 0
        for lib in libs:
            rel_path = lib.relative_to(testcases_dir)
            cases = TestDiscovery.discover_in_dir(lib)
            total_cases += len(cases)
            self.lib_listbox.insert(tk.END, f"{rel_path} ({len(cases)})")
        
        self.lib_count_label.configure(text=f"{len(libs)} 个库")
        self._log(f"📚 发现 {len(libs)} 个测试库，共 {total_cases} 个用例", 'info')
        self.refresh_compilers()

    def _get_zip_dir(self) -> Optional[Path]:
        zip_dir, _ = self._get_zip_dir_and_preferred_zip()
        return zip_dir

    def _resolve_project_path(self) -> Optional[Path]:
        raw = (self.project_var.get() or "").strip()
        if not raw:
            return self.app.zip_dir
        p = Path(raw)
        if not p.is_absolute():
            p = (self.test_dir / p).resolve()
        return p

    def _get_zip_dir_and_preferred_zip(self) -> Tuple[Optional[Path], Optional[Path]]:
        """从输入框解析 zip_dir，并在输入为单个 zip 时返回其路径用于默认选择。"""
        project_path = self._resolve_project_path()
        if not project_path:
            return None, None

        if project_path.exists() and project_path.is_file():
            if project_path.suffix.lower() == ".zip":
                return project_path.parent.resolve(), project_path.resolve()
            return project_path.parent.resolve(), None

        if project_path.exists() and project_path.is_dir():
            return project_path.resolve(), None

        return None, None

    def refresh_compilers(self):
        """刷新 zip_dir 下的编译器实例列表。"""
        if threading.current_thread() is not threading.main_thread():
            self.parent.after(0, self.refresh_compilers)
            return

        zip_dir, preferred_zip = self._get_zip_dir_and_preferred_zip()

        # 保留刷新前的选择（按 zip_path 匹配），避免刷新后丢失。
        previously_selected: set[Path] = set()
        if hasattr(self, "inst_listbox"):
            prev_valid = [i for i in self.zip_instances if i.valid]
            for idx in self.inst_listbox.curselection() or ():
                if 0 <= idx < len(prev_valid):
                    previously_selected.add(prev_valid[idx].zip_path.resolve())

        if zip_dir:
            self.app.zip_dir = zip_dir
            self.app.update_project_status(zip_dir)
            self.zip_instances = discover_zip_compilers(zip_dir, recursive=True)
        else:
            self.zip_instances = []

        valid = [i for i in self.zip_instances if i.valid]
        invalid = [i for i in self.zip_instances if not i.valid]

        if hasattr(self, "inst_listbox"):
            self.inst_listbox.delete(0, tk.END)
            for inst in valid:
                lang = (inst.language or "unknown").upper()
                obj = (inst.object_code or "?").lower()
                self.inst_listbox.insert(tk.END, f"{inst.name}  ({lang}, {obj})")

            # 恢复选择：优先单 zip 输入，其次按旧选择恢复。
            selected_any = False
            if preferred_zip:
                for idx, inst in enumerate(valid):
                    if inst.zip_path.resolve() == preferred_zip:
                        self.inst_listbox.selection_set(idx)
                        self.inst_listbox.activate(idx)
                        self.inst_listbox.see(idx)
                        selected_any = True
                        break
            if not selected_any and previously_selected:
                for idx, inst in enumerate(valid):
                    if inst.zip_path.resolve() in previously_selected:
                        self.inst_listbox.selection_set(idx)
                        selected_any = True
                if selected_any:
                    self.inst_listbox.see(self.inst_listbox.curselection()[0])

        if hasattr(self, "inst_count_label"):
            self.inst_count_label.configure(text=f"{len(valid)} 可用 / {len(self.zip_instances)} 总计")

        if invalid:
            for inst in invalid:
                self._log(f"⚠️ 忽略无效实例 {inst.zip_path.name}: {inst.reason}", "warning")

        self._update_compiler_info()

    def _get_selected_instances(self) -> List[ZipCompilerInstance]:
        valid = [i for i in self.zip_instances if i.valid]
        if not valid:
            return []
        selection = self.inst_listbox.curselection() if hasattr(self, "inst_listbox") else ()
        if not selection:
            _, preferred_zip = self._get_zip_dir_and_preferred_zip()
            if preferred_zip:
                inst = next((i for i in valid if i.zip_path.resolve() == preferred_zip), None)
                return [inst] if inst else []
            return valid
        selected: List[ZipCompilerInstance] = []
        for idx in selection:
            if 0 <= idx < len(valid):
                selected.append(valid[idx])
        return selected
    
    def _on_lib_select(self, event):
        """选择测试库时更新用例列表"""
        selection = self.lib_listbox.curselection()
        if not selection:
            return
        
        self.case_listbox.delete(0, tk.END)
        lib_name = self.lib_listbox.get(selection[0]).split(' (')[0]
        self.current_lib_path = self.test_dir / "testcases" / lib_name
        
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
            messagebox.showinfo("提示", "该用例没有 in.txt")
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
            self.case_menu.add_command(label="用记事本打开 in.txt", command=self._open_selected_input_in_notepad)
        
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
        testcases_dir = self.test_dir / "testcases"
        libs = TestDiscovery.discover_test_libs(testcases_dir)
        
        all_cases = []
        for lib in libs:
            cases = TestDiscovery.discover_in_dir(lib)
            rel = lib.relative_to(testcases_dir)
            for case in cases:
                if str(rel) == ".":
                    case.name = case.name
                else:
                    case.name = f"{rel}/{case.name}"
            all_cases.extend(cases)
        
        self._run_tests(all_cases, f"运行所有测试 ({len(all_cases)} 个)")
    
    def _run_tests(self, cases: list, title: str):
        """运行测试"""
        if self.is_running:
            messagebox.showwarning("提示", "测试正在运行中")
            return

        zip_dir = self._get_zip_dir()
        if not zip_dir:
            messagebox.showerror("错误", "请先选择 zip 目录")
            return

        selected = self._get_selected_instances()
        if not selected:
            messagebox.showerror("错误", "未找到可用的编译器实例（zip）")
            return
        
        self.is_running = True
        self.stop_btn.configure(state=tk.NORMAL)
        self._clear_output()
        self.progress.set(0)
        self.result_label.configure(text="")
        self._stop_event.clear()
        
        max_workers = self.config.parallel.max_workers
        self._log(f"🚀 {title}", 'header')
        self._log(f"   并行线程: {max_workers}", 'dim')
        self._log(f"   编译器实例: {len(selected)}", 'dim')
        
        def test_task():
            testers: List[CompilerTester] = []
            for inst in selected:
                try:
                    extracted = extract_zip_instance(inst, self.test_dir / ".tmp" / "zip_sources")
                    testers.append(CompilerTester(extracted, self.test_dir, instance_name=inst.name))
                except Exception as e:
                    self.message_queue.put(("compile_instance", inst.name, False, f"解包失败: {e}"))

            self.message_queue.put(("status", f"正在编译 {len(testers)} 个实例..."))

            compile_results = compile_testers(
                testers,
                max_workers=max_workers,
                stop_event=self._stop_event,
                callback=lambda t, ok, msg: self.message_queue.put(("compile_instance", t.instance_name, ok, msg)),
            )
            ok_testers = [t for t in testers if compile_results.get(t.instance_name, (False, ""))[0]]
            if not ok_testers:
                self.message_queue.put(("compile_failed", "所有编译器实例编译失败"))
                return

            self.message_queue.put(("compile_done", True, f"编译完成: {len(ok_testers)}/{len(testers)}"))

            if not self.is_running or self._stop_event.is_set():
                self.message_queue.put(("stopped", 0, 0, len(ok_testers) * len(cases)))
                return

            passed, failed = 0, 0
            total_tasks = len(ok_testers) * len(cases)

            def on_result(tester: CompilerTester, case, result, completed, total):
                nonlocal passed, failed
                if not self.is_running or self._stop_event.is_set():
                    return
                if result.passed:
                    passed += 1
                    self.message_queue.put(("result", tester.instance_name, case.name, result, True))
                else:
                    failed += 1
                    self.message_queue.put(("result", tester.instance_name, case.name, result, False))
                progress = completed / total * 100 if total else 100.0
                self.message_queue.put(("progress", progress, f"{passed + failed}/{total_tasks}"))

            try:
                run_started = time.perf_counter()
                test_multi(ok_testers, cases, max_workers=max_workers, stop_event=self._stop_event, callback=on_result)
            except Exception as e:
                self.message_queue.put(("error", str(e)))
                return
            run_elapsed = time.perf_counter() - run_started
            self.message_queue.put(("runtime", run_elapsed))

            if self.is_running and not self._stop_event.is_set():
                self.message_queue.put(("done", passed, failed, total_tasks))
            else:
                self.message_queue.put(("stopped", passed, failed, total_tasks))
        
        threading.Thread(target=test_task, daemon=True).start()
    
    def _stop_test(self):
        """停止测试"""
        self.is_running = False
        self._stop_event.set()
    
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
                    self.status_var.set("编译完成")
                
                elif msg[0] == 'compile_failed':
                    _, error_msg = msg
                    self._log(f"✗ 编译失败: {error_msg}", 'error')
                    self._finish_test(0, 0, stopped=True)

                elif msg[0] == "compile_instance":
                    _, name, ok, text = msg
                    icon = "✓" if ok else "✗"
                    self._log(f"{icon} [{name}] {text}", "pass" if ok else "error")

                elif msg[0] == "compile_all_done":
                    self.status_var.set("编译完成")

                elif msg[0] == 'progress':
                    _, progress, status = msg
                    self.progress.set(progress)
                    self.status_var.set(f"测试中... {status}")
                
                elif msg[0] == 'result':
                    _, inst_name, case_name, result, passed = msg
                    if passed:
                        self._log(f"✓ [{inst_name}] {case_name}", 'pass')
                    else:
                        self._log_failure(
                            name=f"[{inst_name}] {case_name}",
                            status=result.status.value,
                            message=result.message or "",
                            actual=result.actual_output,
                            expected=result.expected_output
                        )
                
                elif msg[0] == 'error':
                    _, error_msg = msg
                    self._log(f"✗ 错误: {error_msg}", 'error')
                    self._finish_test(0, 0, stopped=True)

                elif msg[0] == "runtime":
                    _, elapsed = msg
                    self._log(f"总运行时长: {format_duration(elapsed)}", "info")
                
                elif msg[0] == 'done':
                    _, passed, failed, total = msg
                    self._finish_test(passed, failed, total=total)
                
                elif msg[0] == 'stopped':
                    _, passed, failed, total = msg
                    self._log("⏹ 测试已停止", 'warning')
                    self._finish_test(passed, failed, total=total, stopped=True)
                
        except:
            pass
    
    def _finish_test(self, passed: int, failed: int, total: Optional[int] = None, stopped: bool = False):
        """完成测试"""
        self.is_running = False
        self.stop_btn.configure(state=tk.DISABLED)
        self.progress.set(100)
        
        total = int(total if total is not None else (passed + failed))
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
