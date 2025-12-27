"""
配置模块 - 从YAML文件加载配置
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import tkinter.font as tkfont


@dataclass
class TimeoutConfig:
    """超时配置"""
    compile: int = 60
    mars: int = 10
    gcc_compile: int = 30
    gcc_run: int = 120
    java_compile: int = 120
    cmake_configure: int = 120
    cmake_build: int = 600


@dataclass
class ParallelConfig:
    """并行配置"""
    max_workers: int = 4


@dataclass
class ToolsConfig:
    """工具路径配置"""
    jdk_home: str = ""       # JDK安装目录，空则用PATH
    gcc_path: str = ""       # gcc/g++可执行文件路径
    cmake_path: str = ""
    
    def _normalize(self, value) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        if value.lower() in ("none", "null", "~"):
            return ""
        return value
    
    def get_java(self) -> str:
        jdk_home = self._normalize(self.jdk_home)
        if jdk_home:
            return str(Path(jdk_home) / "bin" / "java")
        return "java"
    
    def get_javac(self) -> str:
        jdk_home = self._normalize(self.jdk_home)
        if jdk_home:
            return str(Path(jdk_home) / "bin" / "javac")
        return "javac"
    
    def get_jar(self) -> str:
        jdk_home = self._normalize(self.jdk_home)
        if jdk_home:
            return str(Path(jdk_home) / "bin" / "jar")
        return "jar"
    
    def get_gcc(self) -> str:
        gcc_path = self._normalize(self.gcc_path)
        return gcc_path if gcc_path else "g++"
    
    def get_cmake(self) -> str:
        cmake_path = self._normalize(self.cmake_path)
        return cmake_path if cmake_path else "cmake"


@dataclass
class GuiConfig:
    """GUI配置"""
    window_width: int = 1000
    window_height: int = 750
    font_family: List[str] = field(default_factory=lambda: ["Consolas", "Monaco", "Courier New", "monospace"])
    font_size: int = 10
    _resolved_font: Optional[str] = field(default=None, repr=False)
    
    def get_font(self) -> str:
        """获取可用的字体（自动回落）"""
        if self._resolved_font:
            return self._resolved_font
        
        try:
            available = set(tkfont.families())
            for font in self.font_family:
                if font in available:
                    self._resolved_font = font
                    return font
        except:
            pass
        
        # 默认回落
        self._resolved_font = self.font_family[-1] if self.font_family else "TkFixedFont"
        return self._resolved_font


@dataclass
class Config:
    """全局配置"""
    compiler_project_dir: str = "../Compiler"
    mars_jar: str = "MARS2025+.jar"
    c_header: str = ""
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    parallel: ParallelConfig = field(default_factory=ParallelConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    gui: GuiConfig = field(default_factory=GuiConfig)
    
    _instance: Optional['Config'] = field(default=None, repr=False, init=False)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """加载配置文件"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        if not config_path.exists():
            print(f"配置文件不存在: {config_path}，使用默认配置")
            return cls._create_default()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            return cls._from_dict(data)
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return cls._create_default()
    
    @classmethod
    def _from_dict(cls, data: dict) -> 'Config':
        """从字典创建配置"""
        timeout_data = data.get('timeout', {})
        timeout = TimeoutConfig(
            compile=timeout_data.get('compile', 60),
            mars=timeout_data.get('mars', 5),
            gcc_compile=timeout_data.get('gcc_compile', 30),
            gcc_run=timeout_data.get('gcc_run', 120),
            java_compile=timeout_data.get('java_compile', 120),
            cmake_configure=timeout_data.get('cmake_configure', timeout_data.get('gcc_compile', 30)),
            cmake_build=timeout_data.get('cmake_build', max(timeout_data.get('gcc_compile', 30), 300))
        )
        
        gui_data = data.get('gui', {})
        font_family = gui_data.get('font_family', ["Consolas", "Monaco", "Courier New", "monospace"])
        if isinstance(font_family, str):
            font_family = [font_family]
        
        gui = GuiConfig(
            window_width=gui_data.get('window_width', 1000),
            window_height=gui_data.get('window_height', 750),
            font_family=font_family,
            font_size=gui_data.get('font_size', 10)
        )
        
        parallel_data = data.get('parallel', {})
        parallel = ParallelConfig(
            max_workers=parallel_data.get('max_workers', 4)
        )
        
        tools_data = data.get('tools', {})
        tools = ToolsConfig(
            jdk_home=tools_data.get('jdk_home', ''),
            gcc_path=tools_data.get('gcc_path', ''),
            cmake_path=tools_data.get('cmake_path', '')
        )
        
        return cls(
            compiler_project_dir=data.get('compiler_project_dir', '../Compiler'),
            mars_jar=data.get('mars_jar', 'Mars.jar'),
            c_header=data.get('c_header', cls._default_c_header()),
            timeout=timeout,
            parallel=parallel,
            tools=tools,
            gui=gui
        )
    
    @classmethod
    def _create_default(cls) -> 'Config':
        """创建默认配置"""
        return cls(
            compiler_project_dir='../Compiler',
            mars_jar='Mars.jar',
            c_header=cls._default_c_header(),
            timeout=TimeoutConfig(),
            parallel=ParallelConfig(),
            tools=ToolsConfig(),
            gui=GuiConfig()
        )
    
    @staticmethod
    def _default_c_header() -> str:
        return '''#include <stdio.h>
#include <stdlib.h>

int getint() {
    int x;
    scanf("%d", &x);
    return x;
}

'''
    
    @classmethod
    def get(cls) -> 'Config':
        """获取全局配置实例（单例）"""
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance
    
    @classmethod
    def reload(cls, config_path: Optional[Path] = None) -> 'Config':
        """重新加载配置"""
        cls._instance = cls.load(config_path)
        return cls._instance


def get_config() -> Config:
    """获取配置"""
    return Config.get()
