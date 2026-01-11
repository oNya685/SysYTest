# SysY 编译器测试框架

> 欢迎窥探 2025 秋编译课程的评测机项目，欢迎 Fork 并用于二次开发，当然如果后来的同学想接手本仓库，也欢迎联系 YumoJiang@buaa.edu.cn 。

> 2026 年 1 月 11 日的考题为：新增`cin << LVal;` 这一 Stmt，等效为给左值赋值 `getint()`，有缺少分号的错误处理；新增 `a–>b` 运算，与 MulExp 同优先级，意为从 a, a+1, a+2,... 累加到 b 的总和。

> 本项目的核心贡献者均坠机于 Testcase 13 和 Testcase 14 的 RuntimeError 上，这可能说明本项目的测试用例仍有不足之处，后人鉴之。

一个用于测试 SysY 编译器的自动化测试框架，支持多线程并行测试、GUI 界面、多语言编译器（Java/C/C++）。

## 快速开始

### 环境要求

- Python 3.8+
- JDK 8+（用于运行 Mars 模拟器）
- g++（用于生成期望输出）
- （GUI）Tkinter（多数 Python 发行版自带；若无 GUI/无 Tk 可使用命令行模式）

### 安装依赖

```bash
python3 -m pip install pyyaml httpx
```

### 目录结构

```
YourCodesFolder/
└── SysYTest/              # 本测试框架
    ├── zips/              # 你的编译器源码 zip（可多个）
    │   ├── A.zip
    │   └── B.zip
    ├── config.yaml
    ├── main.py
    ├── src/               # 框架代码（CLI/GUI/Runner/Discovery）
    └── testcases/         # 测试用例库（可多层嵌套；叶子目录为一个用例目录）
```

### 运行

不带参数默认启动 GUI：

```bash
python3 main.py
```

### 命令行模式

指定 `--project` 参数可以在命令行环境下直接编译+测试，适合 CI/CD 或无 GUI 环境：

```bash
python3 main.py --project zips/
```

如需只测试部分 zip，可多次指定 `--compiler`（zip 文件名去扩展名，或完整 zip 文件名）：

```bash
python3 main.py --project zips/ --compiler A --compiler B.zip
```

运行时会实时打印 `PASS`/`FAIL` 结果和进度，失败时显示实际/期望输出对比。

**常用参数：**
- `--match <子串>` - 只运行用例名包含该子串的用例（可多次指定）
- `--show-cycle` - 显示运行周期数（需 Mars 支持）
- `--show-time` - 显示编译耗时

运行 `python3 main.py --help` 查看完整参数列表。

## 同步更新测试用例

### 从远程仓库获取最新测试用例

```bash
git pull origin main
```

### 如果你 Fork 了仓库，同步上游更新

```bash
# 首次：添加上游仓库
git remote add upstream https://github.com/原仓库/SysYTest.git

# 获取上游更新
git fetch upstream

# 合并到你的本地分支
git checkout main
git merge upstream/main

# 推送到你的 Fork
git push origin main
```

## 贡献测试用例

欢迎提交你的测试用例！

### 方法一：通过 Pull Request（推荐）

1. **Fork 本仓库**
   
   点击 GitHub 页面右上角的 Fork 按钮

2. **克隆你的 Fork**
   ```bash
   git clone https://github.com/你的用户名/SysYTest.git
   cd SysYTest
   ```

3. **创建新分支**
   ```bash
   git checkout -b add-testcases-你的昵称
   ```

4. **添加测试用例**
   
   在 `testcases/` 下创建你的测试库文件夹，添加用例目录（支持任意深度嵌套；叶子目录直接包含 `testfile.txt` 即会被识别为一个用例）：
   ```
   testcases/你的测试库名/
   └── testcase1/
       ├── testfile.txt   # 源代码
       ├── in.txt         # 输入（可选）
       └── ans.txt        # 期望输出（可选）
   ```

5. **提交更改**
   ```bash
   git add testcases/你的测试库名/
   git commit -m "添加测试用例：你的测试库名"
   git push origin add-testcases-你的昵称
   ```

6. **创建 Pull Request**
   
   - 打开你的 Fork 仓库页面
   - 点击 "Compare & pull request"
   - 填写 PR 描述，说明你的测试用例覆盖了哪些场景
   - 点击 "Create pull request"

### 方法二：通过邮件发送

将你的测试用例文件夹打包发送到：**oNya685@outlook.com**

## 配置说明

编辑 `config.yaml` 配置测试框架：

```yaml
# zip_dir：编译器源码压缩包目录（相对于本框架目录）
compiler_project_dir: "zips/"

# 工具路径（留空使用环境变量）
tools:
  jdk_home: ""      # JDK安装目录，如 "C:/Program Files/Java/jdk-17"
  gcc_path: ""      # g++路径
  cmake_path: ""    # cmake 路径（C/C++ 项目可选）

# 并行测试
parallel:
  max_workers: 8    # 并行线程数
```

### 编译器配置

在你的 zip 包**顶层**放置 `config.json`：

```json
{
  "programming language": "java",
  "object code": "mips"
}
```

支持的语言：`java`、`c`、`cpp`

### 编译器源码 zip 格式

- zip 包顶层必须包含 `config.json`
- `java`：入口为 `Compiler.java` 的 `main` 方法；提交时请将 `Compiler.java` 放在 zip 顶层（不要再嵌套一层 `src/` 目录）
- `cpp`：若使用 CMake，zip 顶层包含 `CMakeLists.txt`，且需 `project(Compiler)` 以确保输出可执行文件名为 `Compiler`；不要提交构建产物/临时文件
- `c/cpp`：若不使用 CMake，默认按 C++17 用 `g++` 编译 zip 中的 `.c/.cpp/.h`
- macOS 压缩可能带 `__MACOSX/`、`.DS_Store` 等额外文件，请删除后再提交

## 使用指南

### 🧪 测试运行

1. 启动程序后，在「测试运行」标签页选择 `zip_dir`（如 `zips/`）
2. 在「编译器实例（zip）」列表中多选需要测试的编译器（不选则默认全部）
3. 点击「编译选中」编译所选编译器实例
3. 在左侧选择测试库，右侧会显示该库的测试用例
4. 点击「运行全部」运行所有测试，或选择特定用例运行

### 🐛 调试失败的测试

当测试失败时，输出日志会显示：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ 测试库名/某个用例
  状态: FAILED
  原因: 输出不匹配
  行数: 实际 5 | 期望 5
  差异: 1 处
  ┌ 第 3 行
  │ 实际: 42
  └ 期望: 24
```

**找到对应的测试文件进行调试：**

1. 根据日志中的路径 `测试库名/某个用例`，找到文件：
   ```
   testcases/测试库名/某个用例目录/    # 用例目录（例如 testcase3/ 或 A/）
   ├── testfile.txt                 # 源代码
   └── in.txt                       # 输入（可选）
   ```

2. 将该用例目录下的 `testfile.txt` 内容复制到你编译器项目的 `testfile.txt`

3. 将 `in.txt` 的内容作为 Mars 模拟器的输入（若存在）

4. 运行你的编译器和 Mars 进行调试

### ✏️ 编写测试用例

1. 切换到「用例编写」标签页
2. 选择或新建一个测试库
3. 在左侧编写 SysY 源代码
4. 在右侧编写输入数据（每行一个整数）
5. 点击「保存」或「保存并继续」

### 🤖 AI 自动生成测试用例

本框架支持使用 AI 自动生成符合 SysY 文法的测试用例。

**配置步骤：**

1. 切换到「AI 生成」标签页
2. 配置 API：
   - Base URL：API 地址（默认 `https://api.anthropic.com`，支持兼容 API）
   - Model：模型名称（如 `claude-sonnet-4-20250514`）
   - API Key：你的 API 密钥
3. 点击「保存配置」

**使用方法：**

1. 先在「测试运行」标签页编译你的编译器
2. 在输入框描述你想要的测试用例，例如：
   - "生成一个测试递归函数的用例"
   - "生成一个测试数组边界的用例"
   - "生成一个包含复杂 for 循环嵌套的用例"
3. AI 会自动：
   - 生成 SysY 源代码
   - 调用你的编译器检查语法错误
   - 如果有错误，自动修改代码
   - 编译通过后询问是否保存

**安装额外依赖：**

```bash
python3 -m pip install httpx
```

### 测试用例格式

测试用例从 `testcases/` 下发现：任意深度嵌套目录中，**直接包含 `testfile.txt` 的叶子目录**会被识别为一个用例目录（case directory）。

```
testcases/
└── 01_language_basics/
    ├── testcase1/
    │   ├── testfile.txt
    │   ├── in.txt
    │   └── ans.txt
    └── getint_for_matrix/
        └── testcase1/
            ├── testfile.txt
            ├── in.txt
            └── ans.txt
```

单个用例目录常见文件：
- `testfile.txt`: SysY 源码（必需）
- `in.txt`: 输入（可选；按行提供整数）
- `ans.txt`: 期望输出（可选）
- `compile_only` / `compile_only.txt` / `.compile_only`: 仅编译检查（可选）

## 测试原理

1. **编译**：将你的编译器编译为可执行文件（JAR/EXE）
2. **运行编译器**：用你的编译器将 SysY 源码编译为 MIPS 汇编
3. **运行 Mars**：用 Mars 模拟器执行 MIPS 代码，获取实际输出
4. **获取期望输出**：优先使用用例目录内的 `ans.txt`（若提供）；否则可用 g++ 编译运行同一份源码生成参考输出
5. **对比**：比较实际输出和期望输出

## 常见问题

### Q: 提示找不到 java/javac/jar

确保已安装 JDK 并添加到 PATH，或在 `config.yaml` 中配置 `jdk_home`。

### Q: 提示找不到 g++/g++编译错误

确保已安装 MinGW 或其他 GCC 工具链并添加到 PATH，或在 `config.yaml` 中配置 `gcc_path`（如果配置到 `config.yaml` 后仍然报错，请考虑将其 `bin` 目录添加到环境变量，例如 "`C:\Program Files\mingw64\bin\`"）。

### Q: 测试很慢

调整 `config.yaml` 中的 `parallel.max_workers` 增加并行线程数（注意不要超过 CPU 核心数太多）。

### Q: 如何只测试特定用例

在 GUI 中选择测试库后，在右侧用例列表中按住 Ctrl 多选，然后点击「运行选中」。

在命令行中可使用 `--match` 过滤（可多次指定）：

```bash
python3 main.py --project zips/ --match loop --match recursion
```

如需只测试部分编译器 zip，可多次指定 `--compiler`：

```bash
python3 main.py --project zips/ --compiler A --compiler B.zip
```

### Q: Mars 运行超时
可能是死循环，也可能是优化不够导致的 TLE，后者可以在 `config.yaml` 中增加 Mars 执行超时时间。

### Q: 测试时某些用例卡住约 30 秒

这是 Windows Defender（或火绒等杀毒软件）在扫描新生成的 exe 文件。解决方法：

1. **推荐**：将 `.tmp` 目录添加到杀毒软件的排除列表

2. **临时方案**：测试期间暂时关闭实时防护

<!-- AI 写测评机，拿 AI 生成的测试用例，测 AI 写的代码让 AI debug，新时代的原汤化原食 -->
