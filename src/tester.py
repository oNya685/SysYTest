"""
编译器测试器模块 - 支持多线程测试和多语言编译器
"""
import subprocess
import shutil
import json
import os
import hashlib
from pathlib import Path
from typing import Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import threading

from .config import get_config
from .models import TestCase, TestResult, TestStatus
from .utils import read_file_safe, compare_outputs


SUPPORTED_LANGUAGES = {"java", "c", "cpp"}


@dataclass
class CompilerConfig:
    """编译器项目配置 (从config.json读取)"""
    language: str = "java"
    object_code: str = "mips"


@dataclass
class TestTask:
    """测试任务"""
    case: TestCase
    worker_id: int


class CompilerTester:
    """编译器测试器 - 支持多线程和多语言"""
    
    def __init__(self, project_dir: Path, test_dir: Path):
        self.config = get_config()
        self.project_dir = Path(project_dir).resolve()
        self.test_dir = Path(test_dir).resolve()
        
        # Mars.jar 在 src/ 目录下
        self.mars_jar = (Path(__file__).parent / "Mars.jar").resolve()
        
        # 编译器项目源码目录
        self.project_src_dir = self.project_dir / "src"
        
        # 主工作目录
        self.work_dir = self.test_dir / ".tmp"
        
        # 编译器配置和可执行文件路径
        self.compiler_config = self._load_compiler_config()
        self.compiler_jar = self.work_dir / "Compiler.jar"  # Java
        self.compiler_exe = self.work_dir / "Compiler.exe"  # C/C++
        
        # 线程本地存储
        self._local = threading.local()
    
    def _load_compiler_config(self) -> CompilerConfig:
        """从编译器项目读取config.json"""
        config_path = self.project_dir / "src" / "config.json"
        if not config_path.exists():
            # 尝试项目根目录
            config_path = self.project_dir / "config.json"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                lang = data.get("programming language", "java").lower()
                obj_code = data.get("object code", "mips").lower()
                return CompilerConfig(language=lang, object_code=obj_code)
            except Exception as e:
                print(f"读取config.json失败: {e}，使用默认Java")
        
        return CompilerConfig()
    
    def get_compiler_language(self) -> str:
        """获取编译器语言"""
        return self.compiler_config.language
    
    def _get_worker_dir(self, worker_id: int) -> Path:
        """获取工作线程的独立目录"""
        worker_dir = self.work_dir / f"worker_{worker_id}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        return worker_dir
    
    def compile_project(self) -> Tuple[bool, str]:
        """根据语言编译项目"""
        lang = self.compiler_config.language
        if lang not in SUPPORTED_LANGUAGES:
            return False, f"不支持的编程语言: {lang}，仅支持: {', '.join(SUPPORTED_LANGUAGES)}"
        
        if lang == "java":
            return self.compile_java_project()
        elif lang in ("c", "cpp"):
            return self.compile_c_cpp_project()
        
        return False, f"未知语言: {lang}"
    
    def compile_java_project(self) -> Tuple[bool, str]:
        """编译Java编译器项目为jar包"""
        if not self.project_src_dir.exists():
            return False, f"找不到源码目录: {self.project_src_dir}"
        
        java_files = list(self.project_src_dir.rglob("*.java"))
        if not java_files:
            return False, "找不到Java源文件"
        
        # 创建临时编译目录
        build_dir = self.work_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        
        tools = self.config.tools
        
        try:
            # 1. 编译 Java 文件
            cmd = [tools.get_javac(), "-encoding", "UTF-8", "-d", str(build_dir)] + [str(f) for f in java_files]
            result = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace",
                timeout=self.config.timeout.java_compile
            )
            if result.returncode != 0:
                return False, f"编译失败:\n{result.stderr}"
            
            # 2. 创建 MANIFEST.MF
            manifest_path = build_dir / "MANIFEST.MF"
            manifest_path.write_text("Main-Class: Compiler\n", encoding='utf-8')
            
            # 3. 打包为 jar
            jar_cmd = [tools.get_jar(), "cfm", str(self.compiler_jar), str(manifest_path), "-C", str(build_dir), "."]
            jar_result = subprocess.run(jar_cmd, capture_output=True, text=True, errors="replace", timeout=30)
            if jar_result.returncode != 0:
                return False, f"打包jar失败:\n{jar_result.stderr}"
            
            return True, f"[Java] 成功编译 {len(java_files)} 个文件 -> Compiler.jar"
        
        except subprocess.TimeoutExpired:
            return False, "编译超时"
        except FileNotFoundError as e:
            return False, f"找不到命令: {e.filename}，请确保已安装JDK并配置PATH或在config.yaml中指定路径"
        except Exception as e:
            return False, str(e)
    
    def compile_c_cpp_project(self) -> Tuple[bool, str]:
        """编译C/C++编译器项目为可执行文件"""
        if not self.project_src_dir.exists():
            return False, f"找不到源码目录: {self.project_src_dir}"
        
        lang = self.compiler_config.language
        tools = self.config.tools
        cmake_lists = None
        for p in [self.project_dir / "CMakeLists.txt", self.project_src_dir / "CMakeLists.txt"]:
            if p.exists():
                cmake_lists = p
                break
        
        if cmake_lists is not None:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            project_key = hashlib.md5(str(self.project_dir).encode("utf-8")).hexdigest()[:8]
            build_dir = self.work_dir / f"cmake_build_{project_key}"
            build_dir.mkdir(parents=True, exist_ok=True)
            cache_path = build_dir / "CMakeCache.txt"
            
            cmake = tools.get_cmake()
            cmake_exists = False
            try:
                cmake_path = Path(cmake)
                if cmake_path.is_absolute() or (("\\" in cmake) or ("/" in cmake)):
                    cmake_exists = cmake_path.exists()
                else:
                    cmake_exists = shutil.which(cmake) is not None
            except Exception:
                cmake_exists = False
            
            if not cmake_exists:
                return False, f"找不到命令: {cmake}，请确保已安装CMake并配置PATH或在config.yaml中指定路径"
            
            configured_gcc_path = getattr(tools, "gcc_path", "")
            if hasattr(tools, "_normalize"):
                configured_gcc_path = tools._normalize(configured_gcc_path)
            cxx = tools.get_gcc()
            use_cxx_compiler = bool(configured_gcc_path)
            cxx_for_cmake = configured_gcc_path
            
            guessed_c_compiler = None
            if use_cxx_compiler:
                try:
                    cxx_path = Path(cxx_for_cmake)
                    if cxx_path.is_absolute() and cxx_path.exists():
                        lower_name = cxx_path.name.lower()
                        if lower_name in ("g++.exe", "g++"):
                            gcc_name = "gcc.exe" if lower_name.endswith(".exe") else "gcc"
                            gcc_path = cxx_path.with_name(gcc_name)
                            if gcc_path.exists():
                                guessed_c_compiler = str(gcc_path)
                except Exception:
                    guessed_c_compiler = None
            
            if guessed_c_compiler is None and use_cxx_compiler and cxx_for_cmake.lower() in ("g++", "g++.exe"):
                guessed_c_compiler = "gcc"
            
            generator = None
            if not cache_path.exists() and shutil.which("ninja") is not None:
                generator = "Ninja"
            
            configure_cmd = [cmake]
            if generator:
                configure_cmd += ["-G", generator]
            configure_cmd += ["-S", str(cmake_lists.parent), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"]
            if use_cxx_compiler:
                configure_cmd.append(f"-DCMAKE_CXX_COMPILER={cxx_for_cmake}")
            if guessed_c_compiler:
                configure_cmd.append(f"-DCMAKE_C_COMPILER={guessed_c_compiler}")
            
            add_utf8_flag = False
            if os.name == "nt":
                if not use_cxx_compiler:
                    add_utf8_flag = True
                else:
                    try:
                        compiler_name = Path(cxx_for_cmake).name.lower()
                    except Exception:
                        compiler_name = str(cxx_for_cmake).lower()
                    if compiler_name in ("cl.exe", "cl", "clang-cl.exe", "clang-cl"):
                        add_utf8_flag = True
            
            if add_utf8_flag:
                utf8_flags = "/utf-8 /source-charset:utf-8 /execution-charset:utf-8"
                configure_cmd.append(f"-DCMAKE_C_FLAGS={utf8_flags}")
                configure_cmd.append(f"-DCMAKE_CXX_FLAGS={utf8_flags}")
                configure_cmd.append(f"-DCMAKE_C_FLAGS_RELEASE={utf8_flags}")
                configure_cmd.append(f"-DCMAKE_CXX_FLAGS_RELEASE={utf8_flags}")
            
            try:
                env = None
                if add_utf8_flag and os.name == "nt":
                    env = os.environ.copy()
                    existing_cl = env.get("CL", "")
                    if "/utf-8" not in existing_cl.lower():
                        env["CL"] = (existing_cl + f" {utf8_flags}").strip() if existing_cl else utf8_flags
                
                if not cache_path.exists():
                    configure_result = subprocess.run(
                        configure_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=self.config.timeout.cmake_configure, env=env
                    )
                    if configure_result.returncode != 0:
                        combined = f"{configure_result.stderr}\n{configure_result.stdout}"
                        combined_lower = combined.lower()
                        needs_compiler = (
                            "no cmake_c_compiler could be found" in combined_lower
                            or "no cmake_cxx_compiler could be found" in combined_lower
                            or "the c compiler identification is unknown" in combined_lower
                            or "the cxx compiler identification is unknown" in combined_lower
                        )
                        if os.name == "nt" and needs_compiler:
                            fallback_cxx = configured_gcc_path if configured_gcc_path else cxx
                            fallback_cc = None
                            try:
                                cxx_path = Path(fallback_cxx)
                                cxx_ok = cxx_path.exists() if (cxx_path.is_absolute() or (("\\" in fallback_cxx) or ("/" in fallback_cxx))) else (shutil.which(fallback_cxx) is not None)
                            except Exception:
                                cxx_ok = False
                            
                            if not cxx_ok:
                                return False, (
                                    "CMake配置失败: 未找到可用的 C/C++ 编译器。\n"
                                    "当前环境下 CMake 也无法自动定位 MSVC（通常是未安装 VS 的 C++ 工作负载）。\n\n"
                                    f"{combined}"
                                )
                            
                            try:
                                cxx_path = Path(fallback_cxx)
                                if cxx_path.is_absolute() and cxx_path.exists():
                                    lower_name = cxx_path.name.lower()
                                    if lower_name in ("g++.exe", "g++"):
                                        gcc_name = "gcc.exe" if lower_name.endswith(".exe") else "gcc"
                                        gcc_path = cxx_path.with_name(gcc_name)
                                        if gcc_path.exists():
                                            fallback_cc = str(gcc_path)
                            except Exception:
                                fallback_cc = None
                            
                            if fallback_cc is None and str(fallback_cxx).lower() in ("g++", "g++.exe"):
                                fallback_cc = "gcc"
                            
                            retry_generator = None
                            if shutil.which("ninja") is not None:
                                retry_generator = "Ninja"
                            elif shutil.which("mingw32-make") is not None or shutil.which("make") is not None:
                                retry_generator = "MinGW Makefiles"
                            
                            if retry_generator is None:
                                return False, (
                                    "CMake配置失败: 未找到可用的 C/C++ 编译器（MSVC 未就绪），且未找到可用的构建工具（ninja/make）。\n"
                                    "请安装 Visual Studio 的 “使用 C++ 的桌面开发” 工作负载，或安装 Ninja/MinGW 并确保 g++ 在 PATH。\n\n"
                                    f"{combined}"
                                )
                            
                            try:
                                if build_dir.exists():
                                    shutil.rmtree(build_dir)
                            except Exception:
                                pass
                            build_dir.mkdir(parents=True, exist_ok=True)
                            cache_path = build_dir / "CMakeCache.txt"
                            
                            retry_configure_cmd = [
                                cmake,
                                "-G", retry_generator,
                                "-S", str(cmake_lists.parent),
                                "-B", str(build_dir),
                                "-DCMAKE_BUILD_TYPE=Release",
                                f"-DCMAKE_CXX_COMPILER={fallback_cxx}",
                            ]
                            if fallback_cc:
                                retry_configure_cmd.append(f"-DCMAKE_C_COMPILER={fallback_cc}")
                            
                            retry_configure = subprocess.run(
                                retry_configure_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=self.config.timeout.cmake_configure
                            )
                            if retry_configure.returncode != 0:
                                return False, f"CMake配置失败:\n{retry_configure.stderr}\n{retry_configure.stdout}"
                            
                        else:
                            return False, f"CMake配置失败:\n{combined}"
                
                build_cmd = [cmake, "--build", str(build_dir), "--config", "Release"]
                try:
                    parallel = int(getattr(self.config.parallel, "max_workers", 0) or 0)
                except Exception:
                    parallel = 0
                if parallel > 1:
                    build_cmd += ["--parallel", str(parallel)]
                build_result = subprocess.run(
                    build_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=self.config.timeout.cmake_build, env=env
                )
                if build_result.returncode != 0:
                    return False, f"CMake构建失败:\n{build_result.stderr}\n{build_result.stdout}"
                
                exes = [
                    p for p in build_dir.rglob("*.exe")
                    if "CMakeFiles" not in p.parts and p.is_file()
                ]
                if not exes:
                    return False, f"CMake构建完成但未找到可执行文件: {build_dir}"
                
                preferred = [p for p in exes if p.name.lower() in ("compiler.exe", "compiler")]
                if preferred:
                    chosen = preferred[0]
                elif len(exes) == 1:
                    chosen = exes[0]
                else:
                    chosen = max(exes, key=lambda p: p.stat().st_mtime)
                
                shutil.copy2(chosen, self.compiler_exe)
                return True, f"[{lang.upper()}] CMake构建成功 -> {chosen.name}"
            
            except subprocess.TimeoutExpired:
                return False, "编译超时"
            except FileNotFoundError as e:
                missing = e.filename if e.filename else cmake
                return False, f"找不到命令: {missing}，请确保已安装CMake并配置PATH或在config.yaml中指定路径"
            except Exception as e:
                return False, str(e)
        
        ext = ".c" if lang == "c" else ".cpp"
        source_files = list(self.project_src_dir.rglob(f"*{ext}"))
        
        # 如果是cpp也包含.c文件
        if lang == "cpp":
            source_files.extend(self.project_src_dir.rglob("*.c"))
        
        if not source_files:
            return False, f"找不到{lang.upper()}源文件"
        
        self.work_dir.mkdir(parents=True, exist_ok=True)
        gcc = tools.get_gcc()
        
        try:
            # 编译
            cmd = [gcc, "-o", str(self.compiler_exe)] + [str(f) for f in source_files]
            if lang == "cpp":
                cmd.insert(1, "-std=c++17")
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace",
                timeout=self.config.timeout.gcc_compile
            )
            if result.returncode != 0:
                return False, f"编译失败:\n{result.stderr}"
            
            return True, f"[{lang.upper()}] 成功编译 {len(source_files)} 个文件 -> Compiler.exe"
        
        except subprocess.TimeoutExpired:
            return False, "编译超时"
        except FileNotFoundError as e:
            return False, f"找不到命令: {e.filename}，请确保已安装GCC并配置PATH或在config.yaml中指定路径"
        except Exception as e:
            return False, str(e)

    def _run_compiler(self, source_file: Path, worker_dir: Path) -> Tuple[bool, str]:
        """运行编译器生成MIPS代码"""
        testfile_path = worker_dir / "testfile.txt"
        mips_path = worker_dir / "mips.txt"
        
        # 写入 testfile.txt
        content = read_file_safe(source_file)
        with open(testfile_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        
        # 清理旧的 mips.txt
        if mips_path.exists():
            mips_path.unlink()
        
        # 根据语言选择运行方式
        lang = self.compiler_config.language
        tools = self.config.tools
        
        if lang == "java":
            if not self.compiler_jar.exists():
                return False, "Compiler.jar不存在，请先编译项目"
            cmd = [tools.get_java(), "-jar", str(self.compiler_jar)]
        else:  # c/cpp
            if not self.compiler_exe.exists():
                return False, "Compiler.exe不存在，请先编译项目"
            cmd = [str(self.compiler_exe)]
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace",
                timeout=self.config.timeout.compile, cwd=str(worker_dir)
            )
            if result.returncode != 0:
                return False, f"编译器错误:\n{result.stderr}\n{result.stdout}"
            if not mips_path.exists():
                return False, "编译器未生成mips.txt"
            return True, ""
        except subprocess.TimeoutExpired:
            return False, "编译超时"
        except Exception as e:
            return False, str(e)
    
    def _run_mars(self, input_file: Optional[Path], worker_dir: Path) -> Tuple[Optional[str], str]:
        """运行Mars模拟器"""
        mips_path = worker_dir / "mips.txt"
        tools = self.config.tools
        cmd = [tools.get_java(), "-jar", str(self.mars_jar), "nc", str(mips_path)]
        
        input_data = ""
        if input_file and input_file.exists():
            input_data = read_file_safe(input_file)
        
        try:
            result = subprocess.run(
                cmd, input=input_data, capture_output=True, text=True, errors="replace",
                timeout=self.config.timeout.mars, cwd=str(worker_dir)
            )
            return result.stdout, ""
        except subprocess.TimeoutExpired:
            return None, "Mars执行超时"
        except Exception as e:
            return None, str(e)
    
    def _run_gcc(self, source_file: Path, input_file: Optional[Path], worker_dir: Path) -> Tuple[Optional[str], str]:
        """使用g++编译运行获取期望结果"""
        tmp_src = worker_dir / "tmp_test.c"
        tmp_exe = worker_dir / "tmp_test.exe"
        
        source_code = read_file_safe(source_file)
        full_code = self.config.c_header + source_code
        
        tools = self.config.tools
        gcc = tools.get_gcc()
        
        try:
            with open(tmp_src, "w", encoding="utf-8", newline="\n") as f:
                f.write(full_code)
            
            # 编译
            compile_result = subprocess.run(
                [gcc, str(tmp_src), "-o", str(tmp_exe)],
                capture_output=True, text=True, errors="replace",
                timeout=self.config.timeout.gcc_compile
            )
            
            if compile_result.returncode != 0:
                return None, f"g++编译失败:\n{compile_result.stderr}"
            
            # 运行
            input_data = ""
            if input_file and input_file.exists():
                input_data = read_file_safe(input_file)
            
            run_result = subprocess.run(
                [str(tmp_exe)], input=input_data, capture_output=True, text=True, errors="replace",
                timeout=self.config.timeout.gcc_run
            )
            
            return run_result.stdout, ""
            
        except subprocess.TimeoutExpired:
            return None, "g++执行超时"
        except FileNotFoundError:
            return None, f"找不到{gcc}，请确保已安装或在config.yaml中配置路径"
        except Exception as e:
            return None, str(e)
        finally:
            # 清理临时文件
            for f in [tmp_src, tmp_exe]:
                if f.exists():
                    try:
                        f.unlink()
                    except:
                        pass

    def _is_compiler_ready(self) -> bool:
        """检查编译器是否已编译"""
        lang = self.compiler_config.language
        if lang == "java":
            return self.compiler_jar.exists()
        else:
            return self.compiler_exe.exists()

    def test(self, testfile: Path, input_file: Optional[Path] = None, worker_id: int = 0) -> TestResult:
        """测试单个用例 (强制使用g++对拍)"""
        if not testfile.exists():
            return TestResult(TestStatus.SKIPPED, f"找不到测试文件: {testfile}")
        
        # 检查编译器是否已编译
        if not self._is_compiler_ready():
            return TestResult(TestStatus.SKIPPED, "请先编译项目")
        
        # 获取工作目录
        worker_dir = self._get_worker_dir(worker_id)
        
        # 1. 编译
        success, msg = self._run_compiler(testfile, worker_dir)
        if not success:
            return TestResult(TestStatus.COMPILE_ERROR, msg)
        
        # 2. 运行Mars
        mars_out, mars_err = self._run_mars(input_file, worker_dir)
        if mars_out is None:
            return TestResult(TestStatus.RUNTIME_ERROR, f"Mars运行失败: {mars_err}")
        
        # 3. 使用g++获取期望结果
        gcc_out, gcc_err = self._run_gcc(testfile, input_file, worker_dir)
        if gcc_out is None:
            return TestResult(TestStatus.SKIPPED, f"g++运行失败: {gcc_err}")
        
        # 4. 比较结果
        if compare_outputs(mars_out, gcc_out):
            return TestResult(TestStatus.PASSED)
        else:
            return TestResult(
                TestStatus.FAILED, "输出不匹配",
                actual_output=mars_out, expected_output=gcc_out
            )
    
    def test_parallel(
        self,
        cases: List[TestCase],
        max_workers: int = 4,
        callback=None,
        ramp_up_time: float = 5.0,
        ramp_up_threshold: int = 64
    ) -> List[Tuple[TestCase, TestResult]]:
        """
        并行测试多个用例
        
        Args:
            cases: 测试用例列表
            max_workers: 最大并行数
            callback: 回调函数 callback(case, result, progress)
            ramp_up_time: 渐进启动总时间（秒）
            ramp_up_threshold: 测试用例数量阈值，低于此值立即全部启动
        
        Returns:
            [(case, result), ...]
        """
        import time
        
        if not self._is_compiler_ready():
            return [(c, TestResult(TestStatus.SKIPPED, "请先编译项目")) for c in cases]
        
        results = []
        total = len(cases)
        completed = 0
        lock = threading.Lock()
        
        def run_test(task: TestTask) -> Tuple[TestCase, TestResult]:
            result = self.test(task.case.testfile, task.case.input_file, task.worker_id)
            return task.case, result
        
        # 分配 worker_id
        tasks = [TestTask(case, i % max_workers) for i, case in enumerate(cases)]
        
        # 决定是否渐进启动
        use_ramp_up = total >= ramp_up_threshold
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            if use_ramp_up:
                # 渐进式启动：在 ramp_up_time 秒内均匀提交所有任务
                interval = ramp_up_time / total if total > 0 else 0
                for i, task in enumerate(tasks):
                    futures[executor.submit(run_test, task)] = task
                    if i < total - 1:  # 最后一个不需要等待
                        time.sleep(interval)
            else:
                # 立即全部启动
                futures = {executor.submit(run_test, task): task for task in tasks}
            
            for future in as_completed(futures):
                case, result = future.result()
                with lock:
                    results.append((case, result))
                    completed += 1
                
                if callback:
                    callback(case, result, completed / total * 100)
        
        return results
    
    def cleanup_workers(self):
        """清理所有工作目录"""
        if self.work_dir.exists():
            for item in self.work_dir.iterdir():
                if item.is_dir() and item.name.startswith("worker_"):
                    try:
                        shutil.rmtree(item)
                    except:
                        pass
