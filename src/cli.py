"""
命令行接口模块
"""
import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from .config import get_config
from .discovery import TestDiscovery
from .models import TestResult, TestStatus
from .tester import CompilerTester


LOGO = r"""
   ██████ ▓██   ██▓  ██████▓██   ██▓   ▓▓▄█████▓▓█████   ██████ █▄▄█████▓
 ▒██    ▒  ▒██  ██▒▒██    ▒ ▒██  ██▒   ▓  ██▒ ▓▒▓█   ▀ ▒██    ▒ ▓  ██▒ ▓▒
 ░ ▓██▄     ▒██ ██░░ ▓██▄    ▒██ ██░   ▒ ▓██░ ▒░▒███   ░ ▓██▄   ▒ ▓██░ ▒░
   ▒   ██▒  ░ ▐██▓░  ▒   ██▒ ░ ▐██▓░   ░ ▓██▓ ░ ▒▓█  ▄   ▒   ██▒░ ▓██▓ ░ 
 ▒██████▒▒  ░ ██▒▓░▒██████▒▒ ░ ██▒▓░     ▒██▒ ░ ░▒████▒▒██████▒▒  ▒██▒ ░ 
 ▒ ▒▓▒ ▒ ░   ██▒▒▒ ▒ ▒▓▒ ▒ ░  ██▒▒▒      ▒ ░░   ░░ ▒░ ░▒ ▒▓▒ ▒ ░  ▒ ░░   
 ░ ░▒  ░ ░ ▓██ ░▒░ ░ ░▒  ░ ░▓██ ░▒░        ░     ░ ░  ░░ ░▒  ░ ░    ░    
 ░  ░  ░   ▒ ▒ ░░  ░  ░  ░  ▒ ▒ ░░       ░         ░   ░  ░  ░    ░      
       ░   ░ ░           ░  ░ ░                    ░  ░      ░           
           ░ ░              ░ ░                                          
                                      
    ╔════════════════════════════════════════════════╗
    ║     SysY Compiler Test Framework by oNya685    ║
    ║     Powered by Python + Tkinter + AI Agent     ║
    ╚════════════════════════════════════════════════╝
"""


def _format_output(label: str, message: str) -> str:
    return f"[{label}] {message}"


def _print_failure_detail(case_name: str, result: TestResult):
    print(_format_output("FAIL", f"{case_name} - {result.status.value} {result.message}".strip()), flush=True)
    if result.actual_output is not None:
        print("  实际输出:", flush=True)
        for line in (result.actual_output or "").splitlines():
            print(f"    {line}", flush=True)
    if result.expected_output is not None:
        print("  期望输出:", flush=True)
        for line in (result.expected_output or "").splitlines():
            print(f"    {line}", flush=True)


def run_cli(project: Path) -> int:
    """命令行模式：编译并运行所有测试，日志输出到控制台"""
    config = get_config()
    test_dir = Path(__file__).parent.parent.resolve()
    project_path = Path(project).resolve()

    print(LOGO)
    print(_format_output("INFO", f"使用项目: {project_path}"))

    if not project_path.exists():
        print(_format_output("ERROR", "项目路径不存在"))
        return 1

    tester = CompilerTester(project_path, test_dir)
    lang = tester.get_compiler_language().upper()
    print(_format_output("INFO", f"检测到编译器语言: {lang}"))

    success, msg = tester.compile_project()
    print(_format_output("INFO" if success else "ERROR", msg))
    if not success:
        return 1

    testfiles_dir = test_dir / "testfiles"
    libs = TestDiscovery.discover_test_libs(testfiles_dir)
    cases: List = []
    for lib in libs:
        rel = lib.relative_to(testfiles_dir)
        for case in TestDiscovery.discover_in_dir(lib):
            case.name = f"{rel}/{case.name}"
            cases.append(case)

    if not cases:
        print(_format_output("WARN", "未发现测试用例"))
        return 0
    
    print(_format_output("INFO", f"发现 {len(libs)} 个测试库，共 {len(cases)} 个用例"))
    print(_format_output("INFO", f"并行线程: {config.parallel.max_workers}"))
    
    passed = 0
    failed = 0
    total = len(cases)
    
    def on_result(case, result, progress):
        nonlocal passed, failed
        if result.passed:
            passed += 1
            print(_format_output("PASS", case.name), flush=True)
        else:
            failed += 1
            _print_failure_detail(case.name, result)
        print(_format_output("INFO", f"进度: {passed + failed}/{total} ({progress:.1f}%)"), flush=True)
    
    tester.test_parallel(cases, max_workers=config.parallel.max_workers, callback=on_result)
    
    print(_format_output("INFO", f"完成: {passed} 通过, {failed} 失败, 共 {total}"))
    return 0 if failed == 0 else 1


def main(argv=None):
    """主入口 - CLI/GUI 选择"""
    parser = argparse.ArgumentParser(description="SysY 编译器测试框架")
    parser.add_argument(
        "--project",
        type=str,
        help="编译器项目路径。指定后直接在命令行模式下编译并运行测试"
    )
    args = parser.parse_args(argv)

    if args.project:
        exit_code = run_cli(args.project)
        sys.exit(exit_code)

    print(LOGO)
    from .gui import run_gui  # 延迟导入，避免无头环境下加载 Tk
    run_gui()


if __name__ == "__main__":
    main()
