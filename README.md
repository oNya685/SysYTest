# SysY 编译器测试框架

一个用于测试 SysY 编译器的自动化测试框架，支持多线程并行测试、GUI 界面、多语言编译器（Java/C/C++）。

## 快速开始

### 环境要求

- Python 3.8+
- JDK 8+（用于运行 Mars 模拟器）
- g++（用于生成期望输出）

### 安装依赖

```bash
pip install pyyaml httpx
```

### 目录结构

```
YourCodesFolder/
├── Compiler/              # 你的编译器项目
│   └── src/
│       ├── Compiler.java  # 或 .c/.cpp
│       └── config.json    # 编译器配置
└── SysYTest/              # 本测试框架
    ├── config.yaml
    ├── main.py
    └── testfiles/         # 测试用例
```

### 运行

```bash
python main.py
```

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
   
   在 `testfiles/` 下创建你的测试库文件夹，添加测试文件：
   ```
   testfiles/你的测试库名/
   ├── testfile1.txt
   ├── input1.txt
   ├── testfile2.txt
   └── ...
   ```

5. **提交更改**
   ```bash
   git add testfiles/你的测试库名/
   git commit -m "添加测试用例：你的测试库名"
   git push origin add-testcases-你的昵称
   ```

6. **创建 Pull Request**
   
   - 打开你的 Fork 仓库页面
   - 点击 "Compare & pull request"
   - 填写 PR 描述，说明你的测试用例覆盖了哪些场景
   - 点击 "Create pull request"

### 方法二：通过邮件发送

将你的测试用例文件夹打包发送到：**YumoJiang@buaa.edu.cn**

## 配置说明

编辑 `config.yaml` 配置测试框架：

```yaml
# 编译器项目路径（相对于本框架目录）
compiler_project_dir: "../Compiler"

# 工具路径（留空使用环境变量）
tools:
  jdk_home: ""      # JDK安装目录，如 "C:/Program Files/Java/jdk-17"
  gcc_path: ""      # g++路径

# 并行测试
parallel:
  max_workers: 8    # 并行线程数
```

### 编译器配置

在你的编译器项目 `src/config.json` 中配置：

```json
{
  "programming language": "java",
  "object code": "mips"
}
```

支持的语言：`java`、`c`、`cpp`

## 使用指南

### 🧪 测试运行

1. 启动程序后，在「测试运行」标签页选择编译器项目目录
2. 点击「编译」编译你的编译器
3. 在左侧选择测试库，右侧会显示该库的测试用例
4. 点击「运行全部」运行所有测试，或选择特定用例运行

### 🐛 调试失败的测试

当测试失败时，输出日志会显示：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ 测试库名/testfile3
  状态: FAILED
  原因: 输出不匹配
  行数: 实际 5 | 期望 5
  差异: 1 处
  ┌ 第 3 行
  │ 实际: 42
  └ 期望: 24
```

**找到对应的测试文件进行调试：**

1. 根据日志中的路径 `测试库名/testfile3`，找到文件：
   ```
   testfiles/测试库名/testfile3.txt   # 源代码
   testfiles/测试库名/input3.txt      # 输入数据
   ```

2. 将 `testfile3.txt` 的内容复制到你编译器项目的 `testfile.txt`

3. 将 `input3.txt` 的内容作为 Mars 模拟器的输入

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
pip install httpx
```

### 测试用例格式

```
testfiles/
└── 你的测试库/
    ├── testfile1.txt    # 第1个测试的源代码
    ├── input1.txt       # 第1个测试的输入（可选）
    ├── testfile2.txt    # 第2个测试的源代码
    ├── input2.txt       # 第2个测试的输入（可选）
    └── ...
```

## 测试原理

1. **编译**：将你的编译器编译为可执行文件（JAR/EXE）
2. **运行编译器**：用你的编译器将 SysY 源码编译为 MIPS 汇编
3. **运行 Mars**：用 Mars 模拟器执行 MIPS 代码，获取实际输出
4. **运行 g++**：用 g++ 编译运行同一份源码，获取期望输出
5. **对比**：比较实际输出和期望输出

## 常见问题

### Q: 提示找不到 java/javac/jar

确保已安装 JDK 并添加到 PATH，或在 `config.yaml` 中配置 `jdk_home`。

### Q: 提示找不到 g++

确保已安装 MinGW 或其他 GCC 工具链并添加到 PATH，或在 `config.yaml` 中配置 `gcc_path`。

### Q: 测试很慢

调整 `config.yaml` 中的 `parallel.max_workers` 增加并行线程数（注意不要超过 CPU 核心数太多）。

### Q: 如何只测试特定用例

在 GUI 中选择测试库后，在右侧用例列表中按住 Ctrl 多选，然后点击「运行选中」。

<!-- AI 写测评机，拿 AI 生成的测试用例，测 AI 写的代码让 AI debug，新时代的原汤化原食 -->