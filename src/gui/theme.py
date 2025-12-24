"""
现代化主题配置 - 浅色主题
"""
import tkinter as tk
from tkinter import ttk


# 颜色方案 - 清新浅色主题
COLORS = {
    # 背景色
    'bg_primary': '#ffffff',
    'bg_secondary': '#f8f9fa',
    'bg_tertiary': '#e9ecef',
    'bg_card': '#ffffff',
    
    # 前景色
    'fg_primary': '#212529',
    'fg_secondary': '#495057',
    'fg_muted': '#868e96',
    
    # 强调色 - 蓝色系
    'accent': '#4263eb',
    'accent_hover': '#5c7cfa',
    'accent_light': '#edf2ff',
    
    # 状态色
    'success': '#2f9e44',
    'success_bg': '#ebfbee',
    'error': '#e03131',
    'error_bg': '#fff5f5',
    'warning': '#f59f00',
    'warning_bg': '#fff9db',
    'info': '#1c7ed6',
    'info_bg': '#e7f5ff',
    
    # 边框
    'border': '#dee2e6',
    'border_light': '#e9ecef',
    'border_focus': '#4263eb',
    
    # 按钮
    'btn_bg': '#f1f3f4',
    'btn_hover': '#e8eaed',
    'btn_active': '#dadce0',
    
    # 输入框
    'input_bg': '#ffffff',
    'input_border': '#ced4da',
    
    # 选中
    'select_bg': '#e7f5ff',
    'select_fg': '#1c7ed6',
}


def apply_modern_theme(root: tk.Tk):
    """应用现代化浅色主题"""
    style = ttk.Style()
    
    # 使用 clam 主题作为基础
    style.theme_use('clam')
    
    # 全局配置
    root.configure(bg=COLORS['bg_secondary'])
    
    # Frame
    style.configure('TFrame', background=COLORS['bg_secondary'])
    style.configure('Card.TFrame', background=COLORS['bg_card'])
    
    # LabelFrame
    style.configure('TLabelframe', 
                    background=COLORS['bg_card'],
                    bordercolor=COLORS['border'],
                    relief='solid',
                    borderwidth=1)
    style.configure('TLabelframe.Label', 
                    background=COLORS['bg_card'],
                    foreground=COLORS['fg_primary'],
                    font=('微软雅黑', 10, 'bold'))
    
    # Label
    style.configure('TLabel',
                    background=COLORS['bg_secondary'],
                    foreground=COLORS['fg_primary'],
                    font=('微软雅黑', 9))
    style.configure('Card.TLabel',
                    background=COLORS['bg_card'],
                    foreground=COLORS['fg_primary'])
    style.configure('Title.TLabel',
                    background=COLORS['bg_secondary'],
                    foreground=COLORS['accent'],
                    font=('微软雅黑', 14, 'bold'))
    style.configure('Status.TLabel',
                    background=COLORS['bg_secondary'],
                    foreground=COLORS['fg_muted'],
                    font=('微软雅黑', 9))
    style.configure('Success.TLabel',
                    background=COLORS['bg_secondary'],
                    foreground=COLORS['success'],
                    font=('微软雅黑', 10, 'bold'))
    style.configure('Error.TLabel',
                    background=COLORS['bg_secondary'],
                    foreground=COLORS['error'],
                    font=('微软雅黑', 10, 'bold'))
    
    # Button - 普通按钮
    style.configure('TButton',
                    background=COLORS['btn_bg'],
                    foreground=COLORS['fg_primary'],
                    bordercolor=COLORS['border'],
                    focuscolor=COLORS['accent'],
                    font=('微软雅黑', 9),
                    padding=(12, 6))
    style.map('TButton',
              background=[('active', COLORS['btn_hover']), 
                         ('pressed', COLORS['btn_active'])],
              foreground=[('disabled', COLORS['fg_muted'])])
    
    # Accent Button - 主要操作按钮
    style.configure('Accent.TButton',
                    background=COLORS['accent'],
                    foreground='#ffffff',
                    font=('微软雅黑', 9, 'bold'))
    style.map('Accent.TButton',
              background=[('active', COLORS['accent_hover']),
                         ('pressed', COLORS['accent'])])
    
    # Danger Button - 危险操作按钮
    style.configure('Danger.TButton',
                    background=COLORS['error'],
                    foreground='#ffffff',
                    font=('微软雅黑', 9, 'bold'))
    style.map('Danger.TButton',
              background=[('active', '#c92a2a'),
                         ('pressed', COLORS['error'])])
    
    # Entry
    style.configure('TEntry',
                    fieldbackground=COLORS['input_bg'],
                    foreground=COLORS['fg_primary'],
                    bordercolor=COLORS['input_border'],
                    insertcolor=COLORS['fg_primary'],
                    padding=6)
    style.map('TEntry',
              bordercolor=[('focus', COLORS['border_focus'])])
    
    # Combobox
    style.configure('TCombobox',
                    fieldbackground=COLORS['input_bg'],
                    background=COLORS['btn_bg'],
                    foreground=COLORS['fg_primary'],
                    bordercolor=COLORS['input_border'],
                    arrowcolor=COLORS['fg_secondary'],
                    padding=6)
    style.map('TCombobox',
              fieldbackground=[('readonly', COLORS['input_bg'])],
              bordercolor=[('focus', COLORS['border_focus'])])
    
    # Notebook (标签页) - 修复选中时大小变化问题
    style.configure('TNotebook',
                    background=COLORS['bg_secondary'],
                    bordercolor=COLORS['border'],
                    tabmargins=[4, 4, 4, 0])
    style.configure('TNotebook.Tab',
                    background=COLORS['bg_tertiary'],
                    foreground=COLORS['fg_secondary'],
                    padding=[16, 8],
                    font=('微软雅黑', 10))
    style.map('TNotebook.Tab',
              background=[('selected', COLORS['bg_card'])],
              foreground=[('selected', COLORS['accent'])],
              padding=[('selected', [16, 8])])  # 保持相同的padding
    
    # Progressbar
    style.configure('TProgressbar',
                    background=COLORS['accent'],
                    troughcolor=COLORS['bg_tertiary'],
                    bordercolor=COLORS['border'],
                    lightcolor=COLORS['accent'],
                    darkcolor=COLORS['accent'],
                    thickness=6)
    
    # Scrollbar
    style.configure('TScrollbar',
                    background=COLORS['bg_tertiary'],
                    troughcolor=COLORS['bg_secondary'],
                    bordercolor=COLORS['bg_secondary'],
                    arrowcolor=COLORS['fg_muted'])
    style.map('TScrollbar',
              background=[('active', COLORS['border'])])
    
    # PanedWindow
    style.configure('TPanedwindow',
                    background=COLORS['bg_secondary'])
    
    # Separator
    style.configure('TSeparator',
                    background=COLORS['border'])
    
    return style


def create_styled_listbox(parent, **kwargs) -> tk.Listbox:
    """创建样式化的Listbox"""
    default_config = {
        'bg': COLORS['input_bg'],
        'fg': COLORS['fg_primary'],
        'selectbackground': COLORS['select_bg'],
        'selectforeground': COLORS['select_fg'],
        'borderwidth': 1,
        'highlightthickness': 1,
        'highlightbackground': COLORS['border'],
        'highlightcolor': COLORS['border_focus'],
        'relief': 'solid',
        'activestyle': 'none',
    }
    default_config.update(kwargs)
    return tk.Listbox(parent, **default_config)


def create_styled_text(parent, **kwargs) -> tk.Text:
    """创建样式化的Text"""
    default_config = {
        'bg': COLORS['input_bg'],
        'fg': COLORS['fg_primary'],
        'insertbackground': COLORS['fg_primary'],
        'selectbackground': COLORS['select_bg'],
        'selectforeground': COLORS['select_fg'],
        'borderwidth': 1,
        'highlightthickness': 1,
        'highlightbackground': COLORS['border'],
        'highlightcolor': COLORS['border_focus'],
        'relief': 'solid',
        'padx': 8,
        'pady': 8,
    }
    default_config.update(kwargs)
    return tk.Text(parent, **default_config)
