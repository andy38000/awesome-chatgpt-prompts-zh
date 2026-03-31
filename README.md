# Claude Code - Reconstructed

A fully functional reconstruction of the Claude Code CLI, based on architecture analysis of `@anthropic-ai/claude-code` v2.1.88.

Recreates the core architecture — **React/Ink terminal UI**, **QueryEngine agentic loop**, **8 tools**, **8 slash commands** — as a compilable and runnable TypeScript application.

---

## 下载到本地 + 安装 + 使用（完整步骤）

### 第零步：前置条件

| 依赖 | 最低版本 | 检查命令 |
|------|---------|---------|
| Node.js | >= 18 | `node -v` |
| npm | >= 8 | `npm -v` |
| Git | 任意 | `git --version` |
| Anthropic API Key | — | 从 https://console.anthropic.com/settings/keys 获取 |

> **没有 Node.js？** 安装最简单的方式：
> - macOS: `brew install node`
> - Ubuntu/Debian: `curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs`
> - Windows: 下载 https://nodejs.org/

---

### 第一步：克隆仓库

```bash
git clone https://github.com/andy38000/awesome-chatgpt-prompts-zh.git claude-code
cd claude-code
git checkout cursor/claude-code-src-3019
```

---

### 第二步：安装依赖 + 自动构建

```bash
npm install
```

> `npm install` 会自动触发 `postinstall` 脚本编译 TypeScript → `dist/`。
> 如果你看到 `tsc` 编译输出并且没有报错，说明构建成功。

手动构建（可选）：

```bash
npm run build
```

---

### 第三步：设置 API Key

**Linux / macOS：**

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-你的密钥"
```

写入 shell 配置以持久化：

```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-你的密钥"' >> ~/.bashrc
source ~/.bashrc
```

> zsh 用户请将 `~/.bashrc` 替换为 `~/.zshrc`

**Windows (PowerShell)：**

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-api03-你的密钥"
```

永久设置：

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-api03-你的密钥", "User")
```

---

### 第四步：运行

有三种运行方式：

#### 方式 A：开发模式（推荐，免编译热运行）

```bash
npm run dev
```

等同于：

```bash
npx tsx src/entrypoints/cli.tsx
```

#### 方式 B：编译后运行

```bash
npm run build
npm start
```

等同于：

```bash
node dist/entrypoints/cli.js
```

#### 方式 C：全局安装（系统任意位置使用 `claude` 命令）

```bash
npm link
```

然后在任何目录：

```bash
claude
```

---

### 第五步：使用

#### 交互模式（默认）

直接运行，进入 React/Ink 终端 UI：

```bash
npm run dev
```

你会看到：

```
  ╔═══════════════════════════════════════╗
  ║         Claude Code v2.1.88           ║
  ╚═══════════════════════════════════════╝
  Model: Sonnet • Type /help for commands • Ctrl+C to cancel

❯ _
```

直接输入自然语言，Claude 会自动调用工具（读文件、执行命令、编辑代码等）来完成任务。

#### 一次性提问模式（非交互）

```bash
# 直接提问，输出后退出
npx tsx src/entrypoints/cli.tsx -p "用Python写一个快速排序"

# 指定模型
npx tsx src/entrypoints/cli.tsx -m opus -p "分析当前目录的代码结构"

# 详细模式（显示工具调用详情）
npx tsx src/entrypoints/cli.tsx --verbose -p "帮我修复 bug"
```

#### 交互模式下的斜杠命令

| 命令 | 功能 |
|------|------|
| `/help` | 显示所有可用命令和工具 |
| `/model` | 查看当前模型 / 切换模型（sonnet / opus / haiku） |
| `/model opus` | 切换到 Opus 模型 |
| `/model haiku` | 切换到 Haiku 模型 |
| `/cost` | 查看本次会话的 token 用量和花费 |
| `/compact` | 压缩对话历史以减少上下文占用 |
| `/config` | 查看/修改配置 |
| `/config thinking on` | 开启扩展思考 |
| `/config thinking off` | 关闭扩展思考 |
| `/clear` | 清空对话历史 |
| `/version` | 显示版本号 |
| `/exit` | 退出 |

#### CLI 参数

```
Usage: claude [options]

Options:
  -v, --version                   显示版本号
  -m, --model <model>             选择模型 (默认: claude-sonnet-4-20250514)
  -p, --prompt <text>             一次性提问（非交互模式）
  --cwd <dir>                     工作目录 (默认: 当前目录)
  --print                         打印模式
  --dangerously-skip-permissions  自动批准所有工具调用（危险！）
  --verbose                       详细输出
  -h, --help                      显示帮助
```

---

## 内置工具

Claude 会根据你的请求自动选择和调用以下工具：

| 工具 | 功能 | 示例用途 |
|------|------|---------|
| **BashTool** | 执行 Shell 命令 | 运行测试、安装包、git 操作 |
| **FileReadTool** | 读取文件内容（带行号） | 查看源码、配置文件 |
| **FileWriteTool** | 创建/写入文件 | 生成新文件 |
| **FileEditTool** | 精确字符串替换编辑 | 修改代码、修 bug |
| **GlobTool** | 按模式搜索文件名 | 查找 `*.tsx` 文件 |
| **GrepTool** | 按正则搜索文件内容 | 查找函数定义、引用 |
| **WebFetchTool** | 抓取 URL 内容 | 查阅文档、下载参考 |
| **TodoWriteTool** | 管理任务列表 | 规划复杂任务 |

---

## 架构说明

### QueryEngine 核心循环

```
用户输入
    ↓
构建 System Prompt（工具列表 + Git 上下文）
    ↓
发送到 Anthropic API（流式）
    ↓
┌─→ 接收响应
│       ↓
│   包含 tool_use？
│       │
│     是 → 依次执行每个工具 (BashTool, FileReadTool, …)
│       │       ↓
│       │   收集工具执行结果
│       │       ↓
│       └── 将结果发回 API（继续循环）───┐
│                                       │
│   否 → 返回最终文本回复              │
│       ↓                               │
│   更新 token 计数和费用              │
│       ↓                               │
    显示给用户
```

### 项目结构

```
src/
├── entrypoints/
│   ├── cli.tsx              # CLI 入口（Commander.js + Ink）
│   └── nonInteractive.ts    # 一次性提问模式
├── QueryEngine.ts           # 核心：API 调用 → tool_use 循环 → 响应
├── components/              # React/Ink 终端 UI 组件
├── screens/                 # 交互屏幕
├── commands/                # 斜杠命令系统
├── tools/                   # 工具系统（8 个工具）
├── services/api/            # Anthropic SDK 客户端 + 系统提示
├── state/                   # 全局状态管理
├── types/                   # TypeScript 类型定义
├── constants/               # 模型配置、版本号
└── utils/                   # 费用计算、Git、CWD 工具函数
```

---

## 与原版的区别

这是基于架构分析的全新重写，不是源码拷贝。

| 特性 | 原版 | 本版本 |
|------|------|--------|
| 构建系统 | Bun bundler + `feature()` 宏 | 标准 TypeScript + tsx |
| React 运行时 | React Compiler（自动 memoization） | 标准 React 18 |
| MCP 支持 | 完整 Model Context Protocol | 未包含 |
| Agent/Task | 子 agent 派生、worktree | 未包含 |
| 认证 | OAuth 流程、API Key 管理 | 简单环境变量 |
| 插件 | 插件加载器、市场 | 未包含 |
| 语音 | 音频采集、语音转文字 | 未包含 |
| Bridge/Remote | 远程会话管理 | 未包含 |
| 安全 | 沙箱、权限、路径验证 | 简化 |

---

## 常见问题

### Q: 报错 `ANTHROPIC_API_KEY not set`
设置环境变量：`export ANTHROPIC_API_KEY="你的密钥"`

### Q: 报错 `Cannot find module`
运行 `npm install` 重新安装依赖，然后 `npm run build` 重新编译。

### Q: 如何切换模型？
交互模式下输入 `/model opus` 或 `/model haiku`，或启动时 `--model opus`。

### Q: 支持哪些模型？
- `claude-sonnet-4-20250514` (默认，性价比最高)
- `claude-opus-4-20250514` (最强)
- `claude-3-5-haiku-20241022` (最快最便宜)

### Q: Windows 能用吗？
能。需要 Node.js >= 18 和 PowerShell/CMD。BashTool 在 Windows 上需要 WSL 或 Git Bash。

---

## Disclaimer

This is a research/educational project. The original Claude Code's architecture, copyright, and trademarks belong to Anthropic.
