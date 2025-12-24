"""
自定义组件
"""
import tkinter as tk
from tkinter import ttk
from .theme import COLORS


class AnimatedProgressBar(ttk.Frame):
    """带动画效果的进度条"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        
        self._value = 0
        self._target = 0
        self._animating = False
        
        # 进度条容器
        self.container = tk.Canvas(
            self, height=6, bg=COLORS['bg_tertiary'],
            highlightthickness=0, bd=0
        )
        self.container.pack(fill=tk.X, padx=1, pady=1)
        
        # 进度条填充
        self.fill = self.container.create_rectangle(
            0, 0, 0, 6, fill=COLORS['accent'], outline=''
        )
        
        self.bind('<Configure>', self._on_resize)
    
    def _on_resize(self, event=None):
        """调整大小时更新"""
        self._update_fill()
    
    def _update_fill(self):
        """更新填充"""
        width = self.container.winfo_width()
        fill_width = int(width * self._value / 100)
        self.container.coords(self.fill, 0, 0, fill_width, 6)
    
    def set(self, value: float):
        """设置进度值（带动画）"""
        self._target = max(0, min(100, value))
        if not self._animating:
            self._animate()
    
    def _animate(self):
        """动画更新"""
        if abs(self._value - self._target) < 0.5:
            self._value = self._target
            self._update_fill()
            self._animating = False
            return
        
        self._animating = True
        diff = self._target - self._value
        self._value += diff * 0.2  # 缓动
        self._update_fill()
        self.after(16, self._animate)  # ~60fps


class IconButton(ttk.Button):
    """带图标的按钮"""
    
    ICONS = {
        'play': '▶',
        'stop': '■',
        'refresh': '↻',
        'folder': '📁',
        'save': '💾',
        'clear': '🗑',
        'check': '✓',
        'cross': '✗',
        'plus': '+',
        'settings': '⚙',
    }
    
    def __init__(self, parent, icon: str = None, text: str = '', **kwargs):
        display_text = ''
        if icon and icon in self.ICONS:
            display_text = self.ICONS[icon]
        if text:
            display_text = f"{display_text} {text}" if display_text else text
        
        super().__init__(parent, text=display_text, **kwargs)


class StatusBadge(ttk.Frame):
    """状态徽章"""
    
    def __init__(self, parent, text: str = '', status: str = 'info'):
        super().__init__(parent)
        
        colors = {
            'success': COLORS['success'],
            'error': COLORS['error'],
            'warning': COLORS['warning'],
            'info': COLORS['info'],
        }
        
        self.label = ttk.Label(
            self, text=text,
            foreground=colors.get(status, COLORS['fg_primary']),
            font=('微软雅黑', 9, 'bold')
        )
        self.label.pack(padx=8, pady=2)
    
    def set_text(self, text: str):
        self.label.configure(text=text)
    
    def set_status(self, status: str):
        colors = {
            'success': COLORS['success'],
            'error': COLORS['error'],
            'warning': COLORS['warning'],
            'info': COLORS['info'],
        }
        self.label.configure(foreground=colors.get(status, COLORS['fg_primary']))


class Card(ttk.Frame):
    """卡片容器"""
    
    def __init__(self, parent, title: str = None, **kwargs):
        super().__init__(parent, style='Card.TFrame', **kwargs)
        
        if title:
            title_label = ttk.Label(
                self, text=title,
                style='Card.TLabel',
                font=('微软雅黑', 10, 'bold')
            )
            title_label.pack(anchor=tk.W, padx=12, pady=(12, 8))
            
            sep = ttk.Separator(self, orient=tk.HORIZONTAL)
            sep.pack(fill=tk.X, padx=12)
        
        self.content = ttk.Frame(self, style='Card.TFrame')
        self.content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
