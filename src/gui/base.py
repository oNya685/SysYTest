"""
GUI基础组件和工具类
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import get_config, Config
from ..utils import normalize_output
from .theme import COLORS

if TYPE_CHECKING:
    from .app import TestApp


class BaseTab:
    """标签页基类"""
    
    def __init__(self, parent: ttk.Frame, app: 'TestApp'):
        self.parent = parent
        self.app = app
        self.config: Config = get_config()
        self.test_dir: Path = app.test_dir
    
    def build(self):
        """构建界面（子类实现）"""
        raise NotImplementedError


class OutputMixin:
    """输出日志功能混入"""
    
    output_text: tk.Text
    config: Config
    
    def _setup_output_tags(self):
        """设置输出文本标签样式"""
        self.output_text.tag_configure('pass', foreground=COLORS['success'])
        self.output_text.tag_configure('fail', foreground=COLORS['error'])
        self.output_text.tag_configure('info', foreground=COLORS['info'])
        self.output_text.tag_configure('warning', foreground=COLORS['warning'])
        self.output_text.tag_configure('error', foreground=COLORS['error'], 
            font=(self.config.gui.get_font(), self.config.gui.font_size - 1, 'bold'))
        self.output_text.tag_configure('header', foreground=COLORS['accent'],
            font=(self.config.gui.get_font(), self.config.gui.font_size, 'bold'))
        self.output_text.tag_configure('dim', foreground=COLORS['fg_muted'])
    
    def _log(self, text: str, tag: str = None):
        """输出日志"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text + '\n', tag if tag else ())
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def _log_failure(self, name: str, status: str, message: str, 
                     actual: str = None, expected: str = None, max_diff_lines: int = 8):
        """美观地输出失败信息"""
        self.output_text.config(state=tk.NORMAL)
        
        # 分隔线和标题
        self._log("─" * 50, 'dim')
        self._log(f"✗ {name}", 'error')
        self._log(f"  状态: {status}", 'fail')
        
        if message:
            self._log(f"  原因: {message}", 'fail')
        
        if actual is not None and expected is not None:
            actual_norm = normalize_output(actual)
            expected_norm = normalize_output(expected)
            actual_lines = actual_norm.split('\n')
            expected_lines = expected_norm.split('\n')
            
            # 输出行数统计
            self._log(f"  行数: 实际 {len(actual_lines)} | 期望 {len(expected_lines)}", 'info')
            
            # 找出差异行
            diff_lines = []
            max_len = max(len(actual_lines), len(expected_lines))
            for i in range(max_len):
                a = actual_lines[i] if i < len(actual_lines) else ""
                e = expected_lines[i] if i < len(expected_lines) else ""
                if a != e:
                    diff_lines.append((i + 1, a, e))
            
            if diff_lines:
                self._log(f"  差异: {len(diff_lines)} 处", 'warning')
                
                for idx, (line_no, actual_line, expected_line) in enumerate(diff_lines[:max_diff_lines]):
                    self._log(f"  ┌ 第 {line_no} 行", 'dim')
                    
                    # 截断过长的行
                    actual_display = actual_line[:60] + ("..." if len(actual_line) > 60 else "")
                    expected_display = expected_line[:60] + ("..." if len(expected_line) > 60 else "")
                    
                    actual_show = "<空>" if actual_line == "" else actual_display
                    expected_show = "<空>" if expected_line == "" else expected_display
                    
                    self._log(f"  │ 实际: {actual_show}", 'fail')
                    self._log(f"  └ 期望: {expected_show}", 'pass')
                
                if len(diff_lines) > max_diff_lines:
                    self._log(f"  ... 还有 {len(diff_lines) - max_diff_lines} 处差异", 'dim')
        
        self._log("", None)
        self.output_text.config(state=tk.DISABLED)
    
    def _clear_output(self):
        """清空输出"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
