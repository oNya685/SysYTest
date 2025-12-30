"""
数据模型模块
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class TestStatus(Enum):
    """测试状态"""
    PASSED = "通过"
    FAILED = "失败(WA)"
    COMPILE_ERROR = "编译错误(RE)"
    RUNTIME_ERROR = "运行错误(OCE)"
    TIMEOUT = "超时(WA or TLE)"
    SKIPPED = "跳过(Report by ISSUE or fix it and PR)"


@dataclass
class TestResult:
    """测试结果"""
    status: TestStatus
    message: str = ""
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    compile_time_ms: Optional[int] = None
    cycle: Optional[int] = None
    cycle_breakdown: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        return self.status == TestStatus.PASSED


@dataclass
class TestCase:
    """测试用例"""
    name: str
    testfile: Path
    input_file: Optional[Path]
