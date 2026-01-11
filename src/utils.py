"""
工具函数模块
"""
from pathlib import Path
from typing import Optional


def read_file_safe(filepath: Path) -> str:
    """安全读取文件，自动处理编码和换行符"""
    if not filepath.exists():
        return ""
    
    for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
        try:
            content = filepath.read_bytes().decode(encoding)
            return content.replace('\r\n', '\n').replace('\r', '\n')
        except (UnicodeDecodeError, LookupError):
            continue
    
    content = filepath.read_bytes().decode('utf-8', errors='ignore')
    return content.replace('\r\n', '\n').replace('\r', '\n')


def normalize_output(output: Optional[str]) -> str:
    """标准化输出用于比较"""
    if output is None:
        return ""
    lines = output.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines)


def compare_outputs(actual: str, expected: str) -> bool:
    """比较两个输出是否相同"""
    return normalize_output(actual) == normalize_output(expected)


def format_duration(seconds: float) -> str:
    """格式化耗时显示（用于日志输出）。"""
    try:
        seconds_value = float(seconds)
    except (TypeError, ValueError):
        seconds_value = 0.0
    if seconds_value < 0:
        seconds_value = 0.0

    if seconds_value < 60:
        return f"{seconds_value:.3f}s"
    minutes, sec = divmod(seconds_value, 60.0)
    if minutes < 60:
        return f"{int(minutes)}m{sec:06.3f}s"
    hours, minutes = divmod(minutes, 60.0)
    return f"{int(hours)}h{int(minutes):02d}m{sec:06.3f}s"
