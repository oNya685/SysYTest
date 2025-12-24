"""
AI Agent 测试用例生成标签页
"""
import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
import queue
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .base import BaseTab
from .theme import COLORS, create_styled_text
from .widgets import IconButton
from ..agent.server import SysYToolServer
from ..agent.client import AgentClient, AgentConfig, Message

if TYPE_CHECKING:
    from .app import TestApp


class AgentTab(BaseTab):
    """AI Agent 测试用例生成标签页"""
    
    def __init__(self, parent: ttk.Frame, app: 'TestApp'):
        super().__init__(parent, app)
        self.agent_client: Optional[AgentClient] = None
        self.tool_server: Optional[SysYToolServer] = None
        self.message_queue = queue.Queue()
        self.is_running = False
        self.agent_config: Optional[AgentConfig] = None
    
    def build(self):
        """构建界面"""
        main_frame = ttk.Frame(self.parent, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._build_config_section(main_frame)
        self._build_chat_section(main_frame)
        self._build_input_section(main_frame)
        
        # 加载配置
        self._load_agent_config()
    
    def _build_config_section(self, parent):
        """配置区"""
        config_frame = ttk.Frame(parent)
        config_frame.pack(fill=tk.X, pady=(0, 12))
        
        # 第一行：API 配置
        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(row1, text="Base URL").pack(side=tk.LEFT)
        self.base_url_var = tk.StringVar(value="https://api.anthropic.com")
        ttk.Entry(row1, textvariable=self.base_url_var, width=40).pack(side=tk.LEFT, padx=(8, 16))
        
        ttk.Label(row1, text="Model").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="claude-sonnet-4-20250514")
        ttk.Entry(row1, textvariable=self.model_var, width=25).pack(side=tk.LEFT, padx=(8, 16))
        
        IconButton(row1, text='保存配置', command=self._save_agent_config).pack(side=tk.RIGHT)
        
        # 第二行：API Key
        row2 = ttk.Frame(config_frame)
        row2.pack(fill=tk.X)
        
        ttk.Label(row2, text="API Key").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(row2, textvariable=self.api_key_var, width=60, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=(8, 8), fill=tk.X, expand=True)
        
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2, text="显示", variable=self.show_key_var,
                        command=self._toggle_key_visibility).pack(side=tk.LEFT)
    
    def _build_chat_section(self, parent):
        """聊天区"""
        chat_frame = ttk.Frame(parent)
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        # 标题栏
        header = ttk.Frame(chat_frame)
        header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(header, text="🤖 AI 对话", font=('微软雅黑', 10, 'bold')).pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(header, text="", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=(12, 0))
        
        IconButton(header, icon='clear', text='清空对话',
                   command=self._clear_chat).pack(side=tk.RIGHT)
        
        # 聊天显示区
        chat_container = ttk.Frame(chat_frame)
        chat_container.pack(fill=tk.BOTH, expand=True)
        
        self.chat_text = create_styled_text(
            chat_container,
            font=(self.config.gui.get_font(), self.config.gui.font_size),
            wrap=tk.WORD, state=tk.DISABLED
        )
        chat_scroll = ttk.Scrollbar(chat_container, orient=tk.VERTICAL,
                                     command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=chat_scroll.set)
        
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 配置标签样式
        self._setup_chat_tags()
    
    def _build_input_section(self, parent):
        """输入区"""
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X)
        
        # 输入框
        self.input_text = create_styled_text(
            input_frame,
            font=(self.config.gui.get_font(), self.config.gui.font_size),
            wrap=tk.WORD, height=3
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        # 绑定快捷键
        self.input_text.bind('<Return>', self._on_enter)
        self.input_text.bind('<Shift-Return>', lambda e: None)  # 允许 Shift+Enter 换行
        
        # 按钮
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.send_btn = IconButton(btn_frame, icon='play', text='发送',
                                    command=self._send_message, style='Accent.TButton')
        self.send_btn.pack(pady=(0, 4))
        
        self.stop_btn = IconButton(btn_frame, icon='stop', text='停止',
                                    command=self._stop_agent, style='Danger.TButton')
        self.stop_btn.pack()
        self.stop_btn.configure(state=tk.DISABLED)
    
    def _setup_chat_tags(self):
        """设置聊天标签样式"""
        self.chat_text.tag_configure('user', foreground=COLORS['info'],
                                      font=(self.config.gui.get_font(), self.config.gui.font_size, 'bold'))
        self.chat_text.tag_configure('assistant', foreground=COLORS['fg_primary'])
        self.chat_text.tag_configure('system', foreground=COLORS['fg_muted'],
                                      font=(self.config.gui.get_font(), self.config.gui.font_size - 1))
        self.chat_text.tag_configure('tool_call', foreground=COLORS['warning'],
                                      font=(self.config.gui.get_font(), self.config.gui.font_size - 1))
        self.chat_text.tag_configure('tool_result', foreground=COLORS['success'],
                                      background=COLORS['bg_tertiary'])
        self.chat_text.tag_configure('error', foreground=COLORS['error'])
    
    def _toggle_key_visibility(self):
        """切换 API Key 可见性"""
        if self.show_key_var.get():
            self.api_key_entry.configure(show="")
        else:
            self.api_key_entry.configure(show="*")
    
    def _load_agent_config(self):
        """加载 Agent 配置"""
        config_path = self.test_dir / "agent_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.base_url_var.set(data.get("base_url", "https://api.anthropic.com"))
                self.api_key_var.set(data.get("api_key", ""))
                self.model_var.set(data.get("model", "claude-sonnet-4-20250514"))
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def _save_agent_config(self):
        """保存 Agent 配置"""
        config_path = self.test_dir / "agent_config.json"
        data = {
            "base_url": self.base_url_var.get(),
            "api_key": self.api_key_var.get(),
            "model": self.model_var.get()
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self._append_chat("system", "✓ 配置已保存")
        except Exception as e:
            self._append_chat("error", f"保存配置失败: {e}")
    
    def _clear_chat(self):
        """清空对话"""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state=tk.DISABLED)
        
        if self.agent_client:
            self.agent_client.reset()
    
    def _append_chat(self, tag: str, text: str):
        """添加聊天消息"""
        self.chat_text.config(state=tk.NORMAL)
        
        prefix = ""
        if tag == "user":
            prefix = "👤 你: "
        elif tag == "assistant":
            prefix = "🤖 AI: "
        elif tag == "system":
            prefix = "⚙️ "
        elif tag == "tool_call":
            prefix = "🔧 "
        elif tag == "tool_result":
            prefix = "📋 "
        elif tag == "error":
            prefix = "❌ "
        
        self.chat_text.insert(tk.END, prefix, tag)
        self.chat_text.insert(tk.END, text + "\n\n", tag)
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def _on_enter(self, event):
        """回车发送"""
        if not event.state & 0x1:  # 没有按 Shift
            self._send_message()
            return "break"
    
    def _send_message(self):
        """发送消息"""
        if self.is_running:
            return
        
        message = self.input_text.get(1.0, tk.END).strip()
        if not message:
            return
        
        # 清空输入框
        self.input_text.delete(1.0, tk.END)
        
        # 初始化
        self._init_agent()
        
        if not self.agent_client:
            return
        
        # 开始运行
        self.is_running = True
        self.send_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.status_label.configure(text="思考中...")
        
        # 在后台线程运行
        def run_agent():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    self.agent_client.chat(message, self._on_agent_message)
                )
            except Exception as e:
                self.message_queue.put(("error", str(e)))
            finally:
                self.message_queue.put(("done", None))
                loop.close()
        
        threading.Thread(target=run_agent, daemon=True).start()
    
    def _init_agent(self):
        """初始化 Agent"""
        # 检查配置
        if not self.api_key_var.get():
            messagebox.showerror("错误", "请先配置 API Key")
            return
        
        # 创建配置
        self.agent_config = AgentConfig(
            base_url=self.base_url_var.get(),
            api_key=self.api_key_var.get(),
            model=self.model_var.get()
        )
        
        # 创建工具服务器
        compiler_jar = self.test_dir / ".tmp" / "Compiler.jar"
        mars_jar = Path(__file__).parent.parent / "Mars.jar"
        
        java_cmd = self.config.tools.get_java()
        gcc_cmd = self.config.tools.get_gcc()
        
        self.tool_server = SysYToolServer(
            test_dir=self.test_dir,
            compiler_jar=compiler_jar,
            mars_jar=mars_jar,
            java_cmd=java_cmd,
            gcc_cmd=gcc_cmd,
            c_header=self.config.c_header
        )
        
        # 创建客户端（如果不存在或配置变化）
        if not self.agent_client:
            self.agent_client = AgentClient(self.agent_config, self.tool_server)
        else:
            self.agent_client.config = self.agent_config
            self.agent_client.tool_server = self.tool_server
    
    def _on_agent_message(self, msg: Message):
        """Agent 消息回调"""
        self.message_queue.put(("message", msg))
    
    def _stop_agent(self):
        """停止 Agent"""
        if self.agent_client:
            self.agent_client.stop()
        self.status_label.configure(text="已停止")
    
    def process_queue(self):
        """处理消息队列"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "message":
                    msg: Message = data
                    if msg.role == "user":
                        self._append_chat("user", msg.content)
                    elif msg.role == "assistant":
                        self._append_chat("assistant", msg.content)
                    elif msg.role == "system":
                        self._append_chat("system", msg.content)
                    elif msg.role == "tool_call":
                        args_str = json.dumps(msg.tool_args, ensure_ascii=False, indent=2) if msg.tool_args else ""
                        self._append_chat("tool_call", f"{msg.content}\n{args_str}")
                    elif msg.role == "tool_result":
                        self._append_chat("tool_result", msg.content)
                
                elif msg_type == "error":
                    self._append_chat("error", f"错误: {data}")
                
                elif msg_type == "done":
                    self.is_running = False
                    self.send_btn.configure(state=tk.NORMAL)
                    self.stop_btn.configure(state=tk.DISABLED)
                    self.status_label.configure(text="")
                    
                    # 刷新测试列表
                    if hasattr(self.app, 'test_tab') and self.app.test_tab:
                        self.app.test_tab.refresh_lists()
        except queue.Empty:
            pass
