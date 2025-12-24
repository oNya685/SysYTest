"""
Agent Client - 连接 LLM 与 MCP 工具
"""
import json
import asyncio
from typing import Callable, Optional, AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

from .server import SysYToolServer, ToolResult


@dataclass
class AgentConfig:
    """Agent 配置"""
    base_url: str
    api_key: str
    model: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AgentConfig':
        return cls(
            base_url=data.get("base_url", "https://api.anthropic.com"),
            api_key=data.get("api_key", ""),
            model=data.get("model", "claude-sonnet-4-20250514")
        )


@dataclass
class Message:
    """消息"""
    role: str  # user, assistant, system, tool_call, tool_result
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None


class AgentClient:
    """Agent 客户端"""
    
    SYSTEM_PROMPT = """你是一个 SysY 编译器测试用例生成助手。你的任务是帮助用户生成符合 SysY 文法的测试用例。

## 你的工作模式

1. **构造测试用例**：用户描述需求，你按 SysY 文法生成测试代码
2. **改写其他语言代码**：用户提供 C/C++/Java 等代码，你将其改写为符合 SysY 文法的代码。如果无法改写（如使用了不支持的特性），则调用 discard_case 放弃

## SysY 语言规范（严格遵守）

### 类型系统
- 只支持 `int` 类型
- 只支持一维 `int[]` 数组
- 数组长度必须是编译期可计算的常量（如字面量、const 变量、const 表达式）
- 不支持指针、浮点数、字符、字符串、结构体等

### 函数
- 函数参数可以是 `int` 或 `int[]`（数组名作为参数传递）
- 返回值只能是 `int` 或 `void`
- 支持多参数函数调用，包括 16 个以上甚至无限个参数
- **int 函数的函数体最后一条语句必须是 return 语句，即使逻辑上不可达**
- 没有单独的函数声明（即没有无函数体的前向声明）

### 程序结构（顺序固定）
1. 全局变量声明（如果有）
2. 函数定义（如果有）
3. main 函数（必须有，返回 int）

### 控制流
- 只支持 `for` 循环，**不支持 `while` 和 `do-while`**
- 支持 `if-else` 条件语句
- 支持 `break` 和 `continue`

### 运算符
- 算术运算：`+` `-` `*` `/` `%`
- 关系运算：`<` `>` `<=` `>=` `==` `!=`
- 逻辑运算：`!` `&&` `||`
- **重要**：`&&` 和 `||` 只能出现在 `if` 和 `for` 的条件表达式中，且必须在最外层（不能被小括号包裹在表达式内部）
- **不支持**：三元运算符 `? :`、位运算、逗号运算符

### 内置函数
- `printf(格式串, ...);` - 输出，必须单独作为一条语句，无返回值
- `int getint()` - 读取一个整数并返回

### 修饰符
- 支持 `const` 修饰 int 和 int[]
- 支持 `static` 修饰 int 和 int[]

### 输入文件格式
- input 文件中每行一个整数，供 getint() 读取

## 可用工具

1. `generate_testfile` - 生成 SysY 源代码文件
2. `generate_input` - 生成输入数据文件（每行一个整数）
3. `run_compiler` - 编译并运行，检查词法/语法/语义错误
4. `save_testcase` - 保存测试用例到指定测试库
5. `discard_case` - 放弃当前用例（无法改写时使用）

## 工作流程

1. 分析用户需求或代码
2. 生成/改写为符合 SysY 文法的代码
3. 调用 `run_compiler` 检查错误
4. 如果有错误，根据编译器输出修改代码，重新编译
5. 编译通过后，询问用户是否保存
6. 根据用户指示保存或放弃

## 注意事项

- 生成代码前仔细检查是否符合所有 SysY 规范
- 如果用户代码使用了不支持的特性（如 while、指针、浮点数、字符变量等），首先尝试改写SysY，实在无法改写的话说明原因后放弃
- 编译错误时仔细阅读编译器输出，针对性修改
- 用中文回复用户"""

    def __init__(self, config: AgentConfig, tool_server: SysYToolServer):
        self.config = config
        self.tool_server = tool_server
        self.messages = []
        self._stop_flag = False
    
    def stop(self):
        """停止当前执行"""
        self._stop_flag = True
    
    def reset(self):
        """重置对话"""
        self.messages = []
        self._stop_flag = False
    
    async def chat(self, user_message: str, 
                   on_message: Callable[[Message], None]) -> None:
        """
        发送消息并处理响应
        
        Args:
            user_message: 用户消息
            on_message: 消息回调函数
        """
        if httpx is None:
            on_message(Message("system", "错误: 请安装 httpx 库 (pip install httpx)"))
            return
        
        if not self.config.api_key:
            on_message(Message("system", "错误: 请在配置中设置 API Key"))
            return
        
        self._stop_flag = False
        
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_message
        })
        on_message(Message("user", user_message))
        
        # Agent 循环
        while not self._stop_flag:
            try:
                response = await self._call_api()
            except Exception as e:
                on_message(Message("system", f"API 调用失败: {e}"))
                break
            
            if response is None:
                break
            
            # 处理响应
            assistant_content = []
            tool_calls = []
            
            for block in response.get("content", []):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        on_message(Message("assistant", text))
                        assistant_content.append(block)
                
                elif block.get("type") == "tool_use":
                    tool_calls.append(block)
                    assistant_content.append(block)
            
            # 保存助手消息
            if assistant_content:
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })
            
            # 检查是否结束
            if response.get("stop_reason") != "tool_use":
                break
            
            # 处理工具调用
            tool_results = []
            for tool_call in tool_calls:
                if self._stop_flag:
                    break
                
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("input", {})
                tool_id = tool_call.get("id", "")
                
                # 显示工具调用
                on_message(Message("tool_call", f"调用 {tool_name}", 
                                   tool_name=tool_name, tool_args=tool_args))
                
                # 执行工具
                result = self.tool_server.call_tool(tool_name, tool_args)
                
                # 显示结果
                on_message(Message("tool_result", result.message,
                                   tool_name=tool_name))
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result.message
                })
            
            # 添加工具结果到消息
            if tool_results:
                self.messages.append({
                    "role": "user",
                    "content": tool_results
                })
    
    async def _call_api(self) -> Optional[dict]:
        """调用 API"""
        url = f"{self.config.base_url.rstrip('/')}/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.config.model,
            "max_tokens": 4096,
            "system": self.SYSTEM_PROMPT,
            "messages": self.messages,
            "tools": self.tool_server.get_tools_schema()
        }
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_text = response.text
                raise Exception(f"HTTP {response.status_code}: {error_text}")
            
            return response.json()
