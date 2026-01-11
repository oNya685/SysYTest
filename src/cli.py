"""
命令行接口模块
"""
import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from .config import get_config
from .discovery import TestDiscovery
from .models import TestResult, TestStatus
from .multi_runner import compile_testers, test_multi
from .tester import CompilerTester
from .utils import format_duration
from .zip_compilers import discover_zip_compilers, extract_zip_instance


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


def run_cli(
    project: Path,
    show_cycle: bool = False,
    show_time: bool = False,
    match: Optional[List[str]] = None,
    compilers: Optional[List[str]] = None,
) -> int:
    """命令行模式：编译并运行所有测试，日志输出到控制台"""
    config = get_config()
    test_dir = Path(__file__).parent.parent.resolve()
    project_path = Path(project).resolve()

    print(LOGO)
    print(_format_output("INFO", f"使用路径: {project_path}"))

    if not project_path.exists():
        print(_format_output("ERROR", "路径不存在"))
        return 1

    testers: List[CompilerTester] = []
    selected_names: Optional[List[str]] = [c.strip() for c in (compilers or []) if c and c.strip()] or None

    # 兼容：--project <zip_dir> / <zip> / <旧工程目录>
    if project_path.is_file() and project_path.suffix.lower() == ".zip":
        zip_dir = project_path.parent
        instances = discover_zip_compilers(zip_dir)
        inst = next((i for i in instances if i.zip_path.resolve() == project_path), None)
        if inst is None:
            print(_format_output("ERROR", f"未能识别 zip: {project_path.name}"))
            return 1
        extracted = extract_zip_instance(inst, test_dir / ".tmp" / "zip_sources")
        testers = [CompilerTester(extracted, test_dir, instance_name=inst.name)]
    elif project_path.is_dir():
        zips = [p for p in project_path.iterdir() if p.is_file() and p.suffix.lower() == ".zip"]
        if zips:
            instances = discover_zip_compilers(project_path)
            if selected_names:
                wanted = {w.lower() for w in selected_names}
                instances = [i for i in instances if i.name.lower() in wanted or i.zip_path.name.lower() in wanted]
            instances = [i for i in instances if i.valid]
            if not instances:
                print(_format_output("ERROR", "未找到可用的编译器 zip（或选择为空）"))
                return 1
            for inst in instances:
                extracted = extract_zip_instance(inst, test_dir / ".tmp" / "zip_sources")
                testers.append(CompilerTester(extracted, test_dir, instance_name=inst.name))
        else:
            testers = [CompilerTester(project_path, test_dir, instance_name=project_path.name)]
    else:
        print(_format_output("ERROR", "参数必须为目录或 zip 文件"))
        return 1

    for t in testers:
        lang = t.get_compiler_language().upper()
        print(_format_output("INFO", f"编译器实例: {t.instance_name} ({lang})"))

    compile_results = compile_testers(testers, max_workers=config.parallel.max_workers)
    ok_testers: List[CompilerTester] = []
    for t in testers:
        ok, msg = compile_results.get(t.instance_name, (False, "编译失败"))
        print(_format_output("INFO" if ok else "ERROR", f"[{t.instance_name}] {msg}"))
        if ok:
            ok_testers.append(t)

    if not ok_testers:
        return 1

    testcases_dir = test_dir / "testcases"
    libs = TestDiscovery.discover_test_libs(testcases_dir)
    cases: List = []
    for lib in libs:
        rel = lib.relative_to(testcases_dir)
        for case in TestDiscovery.discover_in_dir(lib):
            if str(rel) == ".":
                case.name = case.name
            else:
                case.name = f"{rel}/{case.name}"
            cases.append(case)

    if match:
        lowered = [m.lower() for m in match if m]
        if lowered:
            cases = [c for c in cases if any(m in c.name.lower() for m in lowered)]

    if not cases:
        print(_format_output("WARN", "未发现测试用例"))
        return 0
    
    print(_format_output("INFO", f"发现 {len(libs)} 个测试库，共 {len(cases)} 个用例"))
    print(_format_output("INFO", f"并行线程: {config.parallel.max_workers}"))
    print(_format_output("INFO", f"编译器实例: {len(ok_testers)} 个"))
    
    passed = 0
    failed = 0
    total = len(cases) * len(ok_testers)
    per_compiler = {t.instance_name: [0, 0] for t in ok_testers}  # passed, failed
    
    def on_result(tester: CompilerTester, case, result, completed, total_tasks):
        nonlocal passed, failed
        if result.passed:
            passed += 1
            per_compiler[tester.instance_name][0] += 1
            extra_parts = []
            if show_time and result.compile_time_ms is not None:
                extra_parts.append(f"compile={result.compile_time_ms}ms")
            if show_cycle and result.cycle is not None:
                extra_parts.append(f"cycle={result.cycle}")
            suffix = f" ({', '.join(extra_parts)})" if extra_parts else ""
            print(_format_output("PASS", f"[{tester.instance_name}] {case.name}{suffix}"), flush=True)
        else:
            failed += 1
            per_compiler[tester.instance_name][1] += 1
            _print_failure_detail(f"[{tester.instance_name}] {case.name}", result)
        progress = completed / total_tasks * 100 if total_tasks else 100.0
        print(_format_output("INFO", f"进度: {passed + failed}/{total} ({progress:.1f}%)"), flush=True)
    
    run_started = time.perf_counter()
    test_multi(ok_testers, cases, max_workers=config.parallel.max_workers, callback=on_result)
    run_elapsed = time.perf_counter() - run_started
    print(_format_output("INFO", f"总运行时长: {format_duration(run_elapsed)}"), flush=True)
    
    print(_format_output("INFO", f"完成: {passed} 通过, {failed} 失败, 共 {total}"))
    for name, (p, f) in per_compiler.items():
        print(_format_output("INFO", f"  - {name}: {p} 通过, {f} 失败"), flush=True)
    return 0 if failed == 0 else 1


def main(argv=None):
    """主入口 - CLI/GUI 选择"""
    parser = argparse.ArgumentParser(description="SysY 编译器测试框架")
    parser.add_argument(
        "--project",
        type=str,
        help="zip 目录 / 单个 zip / （兼容）编译器项目目录。指定后在命令行模式下编译并运行测试"
    )
    parser.add_argument(
        "--compiler",
        action="append",
        help="只选择指定的编译器实例（zip 文件名去扩展名，或完整 zip 文件名；可重复指定）",
    )
    parser.add_argument(
        "--match",
        action="append",
        help="只运行用例名包含该子串的用例（可重复指定，如 --match agent_regression）",
    )
    parser.add_argument(
        "--show-cycle",
        action="store_true",
        help="在 PASS 行显示 FinalCycle（若可用）",
    )
    parser.add_argument(
        "--show-time",
        action="store_true",
        help="在 PASS 行显示编译耗时（ms）",
    )
    args = parser.parse_args(argv)

    if args.project:
        exit_code = run_cli(
            args.project,
            show_cycle=args.show_cycle,
            show_time=args.show_time,
            match=args.match,
            compilers=args.compiler,
        )
        sys.exit(exit_code)

    print(LOGO)
    from .gui import run_gui  # 延迟导入，避免无头环境下加载 Tk
    run_gui()


if __name__ == "__main__":
    main()
