"""
MCP Server - SysY 编译器工具定义
"""
import subprocess
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    message: str
    data: Optional[dict] = None


class SysYToolServer:
    """SysY 编译器工具服务器（本地调用版本）"""
    
    def __init__(self, test_dir: Path, compiler_jar: Path, mars_jar: Path, 
                 java_cmd: str = "java", gcc_cmd: str = "g++", c_header: str = ""):
        self.test_dir = Path(test_dir)
        self.compiler_jar = Path(compiler_jar)
        self.mars_jar = Path(mars_jar)
        self.java_cmd = java_cmd
        self.gcc_cmd = gcc_cmd
        self.c_header = c_header
        
        # 当前工作目录
        self.work_dir = self.test_dir / ".tmp" / "agent_work"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前生成的文件
        self.current_testfile: Optional[Path] = None
        self.current_input: Optional[Path] = None
    
    def get_tools_schema(self) -> list:
        """获取工具定义（Anthropic 格式）"""
        return [
            {
                "name": "generate_testfile",
                "description": "生成 SysY 源代码测试文件。将代码写入临时文件用于后续编译测试。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "SysY 源代码内容"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "generate_input",
                "description": "生成测试输入数据文件。每行一个整数，用于 getint() 函数读取。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "输入数据，每行一个整数"
                        }
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "run_compiler",
                "description": "调用编译器编译当前的 testfile，检查是否有词法、语法、语义错误。如果编译成功会生成 MIPS 代码并用 Mars 模拟器运行。",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "save_testcase",
                "description": "将当前生成的测试用例保存到指定的测试库中。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "lib_name": {
                            "type": "string",
                            "description": "测试库名称"
                        },
                        "test_number": {
                            "type": "integer",
                            "description": "测试用例编号"
                        }
                    },
                    "required": ["lib_name", "test_number"]
                }
            },
            {
                "name": "discard_case",
                "description": "放弃当前生成的测试用例，清理临时文件。",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "放弃原因"
                        }
                    },
                    "required": ["reason"]
                }
            }
        ]
    
    def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """调用工具"""
        if name == "generate_testfile":
            return self._generate_testfile(arguments.get("content", ""))
        elif name == "generate_input":
            return self._generate_input(arguments.get("content", ""))
        elif name == "run_compiler":
            return self._run_compiler()
        elif name == "save_testcase":
            return self._save_testcase(
                arguments.get("lib_name", ""),
                arguments.get("test_number", 1)
            )
        elif name == "discard_case":
            return self._discard_case(arguments.get("reason", ""))
        else:
            return ToolResult(False, f"未知工具: {name}")
    
    def _generate_testfile(self, content: str) -> ToolResult:
        """生成测试文件"""
        if not content.strip():
            return ToolResult(False, "源代码内容不能为空")
        
        self.current_testfile = self.work_dir / "testfile.txt"
        try:
            with open(self.current_testfile, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            lines = len(content.strip().split('\n'))
            return ToolResult(True, f"✓ 已生成 testfile.txt ({lines} 行)")
        except Exception as e:
            return ToolResult(False, f"写入文件失败: {e}")
    
    def _generate_input(self, content: str) -> ToolResult:
        """生成输入文件，自动解析整数并每行一个存储"""
        self.current_input = self.work_dir / "input.txt"
        
        if not content.strip():
            # 空输入
            try:
                with open(self.current_input, "w", encoding="utf-8", newline="\n") as f:
                    f.write("")
                return ToolResult(True, "✓ 已生成 input.txt (无输入)")
            except Exception as e:
                return ToolResult(False, f"写入文件失败: {e}")
        
        # 解析所有整数
        import re
        integers = []
        
        # 匹配所有整数（包括负数）
        matches = re.findall(r'-?\d+', content)
        for match in matches:
            try:
                integers.append(int(match))
            except ValueError:
                pass
        
        if not integers:
            return ToolResult(False, f"无法从输入中解析出整数: {content[:100]}")
        
        # 每行一个整数
        formatted_content = '\n'.join(str(n) for n in integers)
        
        try:
            with open(self.current_input, "w", encoding="utf-8", newline="\n") as f:
                f.write(formatted_content)
            return ToolResult(True, f"✓ 已生成 input.txt ({len(integers)} 个整数，每行一个)")
        except Exception as e:
            return ToolResult(False, f"写入文件失败: {e}")
    
    def _run_compiler(self) -> ToolResult:
        """运行编译器"""
        if not self.current_testfile or not self.current_testfile.exists():
            return ToolResult(False, "请先生成 testfile")
        
        if not self.compiler_jar.exists():
            return ToolResult(False, f"编译器不存在: {self.compiler_jar}")
        
        mips_path = self.work_dir / "mips.txt"
        if mips_path.exists():
            mips_path.unlink()
        
        # 1. 运行编译器
        compiler_output = ""
        try:
            cmd = [self.java_cmd, "-jar", str(self.compiler_jar)]
            result = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace",
                timeout=30, cwd=str(self.work_dir)
            )
            
            compiler_output = (result.stdout + result.stderr).strip()
            
            if result.returncode != 0:
                error_msg = f"编译器返回错误 (code {result.returncode})"
                if compiler_output:
                    error_msg += f"\n\n【编译器输出】\n{compiler_output}"
                return ToolResult(False, error_msg)
            
            if not mips_path.exists():
                error_msg = "编译器未生成 mips.txt"
                if compiler_output:
                    error_msg += f"\n\n【编译器输出】\n{compiler_output}"
                return ToolResult(False, error_msg)
            
        except subprocess.TimeoutExpired:
            return ToolResult(False, "编译器执行超时")
        except Exception as e:
            return ToolResult(False, f"编译器执行失败: {e}")
        
        # 2. 运行 Mars
        mars_output = ""
        try:
            input_data = ""
            if self.current_input and self.current_input.exists():
                input_data = self.current_input.read_text(encoding='utf-8')
            
            mars_cmd = [self.java_cmd, "-jar", str(self.mars_jar), "nc", str(mips_path)]
            mars_result = subprocess.run(
                mars_cmd, input=input_data, capture_output=True, text=True, errors="replace",
                timeout=10, cwd=str(self.work_dir)
            )
            
            mars_output = mars_result.stdout
            
        except subprocess.TimeoutExpired:
            return ToolResult(False, "Mars 执行超时（可能存在死循环）")
        except Exception as e:
            return ToolResult(False, f"Mars 执行失败: {e}")
        
        # 3. 运行 g++ 对比
        gcc_output = None
        try:
            tmp_src = self.work_dir / "tmp_test.c"
            tmp_exe = self.work_dir / "tmp_test.exe"
            
            source_code = self.current_testfile.read_text(encoding='utf-8')
            full_code = self.c_header + source_code
            with open(tmp_src, "w", encoding="utf-8", newline="\n") as f:
                f.write(full_code)
            
            compile_result = subprocess.run(
                [self.gcc_cmd, str(tmp_src), "-o", str(tmp_exe)],
                capture_output=True, text=True, errors="replace", timeout=30
            )
            
            if compile_result.returncode == 0:
                run_result = subprocess.run(
                    [str(tmp_exe)], input=input_data, capture_output=True, text=True, errors="replace",
                    timeout=10
                )
                gcc_output = run_result.stdout
            
            # 清理
            for f in [tmp_src, tmp_exe]:
                if f.exists():
                    f.unlink()
                    
        except Exception:
            pass
        
        # 构建结果
        result_msg = "✓ 编译成功！\n"
        
        # 显示编译器输出（如果有）
        if compiler_output:
            result_msg += f"\n【编译器输出】\n{compiler_output}\n"
        
        result_msg += f"\n【Mars 输出】\n{mars_output if mars_output else '(无输出)'}\n"
        
        if gcc_output is not None:
            result_msg += f"\n【g++ 输出】\n{gcc_output if gcc_output else '(无输出)'}\n"
            
            # 比较输出
            mars_lines = mars_output.strip().split('\n') if mars_output.strip() else []
            gcc_lines = gcc_output.strip().split('\n') if gcc_output.strip() else []
            
            if mars_lines == gcc_lines:
                result_msg += "\n✓ 输出一致！"
            else:
                result_msg += f"\n⚠ 输出不一致！Mars {len(mars_lines)} 行，g++ {len(gcc_lines)} 行"
        
        return ToolResult(True, result_msg, {
            "compiler_output": compiler_output,
            "mars_output": mars_output,
            "gcc_output": gcc_output
        })
    
    def _save_testcase(self, lib_name: str, test_number: int) -> ToolResult:
        """保存测试用例"""
        if not lib_name:
            return ToolResult(False, "测试库名称不能为空")
        
        if not self.current_testfile or not self.current_testfile.exists():
            return ToolResult(False, "没有可保存的测试文件")
        
        lib_path = self.test_dir / "testfiles" / lib_name
        lib_path.mkdir(parents=True, exist_ok=True)
        
        # 保存 testfile
        dest_testfile = lib_path / f"testfile{test_number}.txt"
        content = self.current_testfile.read_text(encoding='utf-8')
        with open(dest_testfile, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        
        # 保存 input
        if self.current_input and self.current_input.exists():
            dest_input = lib_path / f"input{test_number}.txt"
            input_content = self.current_input.read_text(encoding='utf-8')
            with open(dest_input, "w", encoding="utf-8", newline="\n") as f:
                f.write(input_content)
        
        return ToolResult(True, f"✓ 已保存到 {lib_name}/testfile{test_number}.txt")
    
    def _discard_case(self, reason: str) -> ToolResult:
        """放弃当前用例"""
        # 清理临时文件
        for f in [self.current_testfile, self.current_input]:
            if f and f.exists():
                f.unlink()
        
        self.current_testfile = None
        self.current_input = None
        
        return ToolResult(True, f"已放弃当前用例。原因: {reason}")
