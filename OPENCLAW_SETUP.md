# OpenClaw + Telegram Bot 本地运行指南

## 前置条件

1. **Node.js** >= 18（OpenClaw 依赖 Node.js）
2. **Ollama** 已安装并运行（提供本地 AI 模型）
3. **OpenClaw CLI** 已安装

## 一、安装 OpenClaw

```bash
npm install -g openclaw
```

验证安装：
```bash
openclaw --version
# 应输出 2026.2.14 或更高版本
```

## 二、配置文件位置

OpenClaw 配置文件位于：

| 系统    | 路径                                 |
|---------|--------------------------------------|
| Windows | `C:\Users\<用户名>\.openclaw\openclaw.json` |
| macOS   | `~/.openclaw/openclaw.json`          |
| Linux   | `~/.openclaw/openclaw.json`          |

将本仓库的 `openclaw.json` 复制到上述位置即可。

## 三、确保 Ollama 运行

```bash
# 启动 Ollama 服务
ollama serve

# 另一个终端，拉取千问3模型（如果还没有的话）
ollama pull qwen3:8b
```

确认 Ollama 在 `http://127.0.0.1:11434` 运行。

### 千问3 可用模型尺寸

根据你的显存/内存选择合适的版本：

| 模型 | 参数量 | 推荐显存 | 适合场景 |
|------|--------|----------|----------|
| `qwen3:1.7b` | 1.7B | 2GB+ | 轻量快速，简单对话 |
| `qwen3:4b` | 4B | 4GB+ | 日常对话，性价比高 |
| `qwen3:8b` | 8B | 6GB+ | **默认推荐**，平衡质量和速度 |
| `qwen3:14b` | 14B | 12GB+ | 高质量回复 |
| `qwen3:32b` | 32B | 24GB+ | 最强能力 |

切换模型只需一条命令：
```bash
openclaw config set agents.defaults.model.primary "ollama/qwen3:32b"
```

## 四、启动 OpenClaw Gateway

### 方式 1：前台运行（推荐调试时使用）

```bash
openclaw gateway run --verbose
```

你应该看到类似输出：
```
[gateway] agent model: ollama/qwen3:8b
[gateway] listening on ws://127.0.0.1:18789
[telegram] [default] starting provider (@andy3800bot)
```

### 方式 2：后台服务运行

```bash
# 安装为系统服务
openclaw gateway install

# 启动服务
openclaw gateway start

# 查看状态
openclaw gateway status
```

## 五、使用 Telegram Bot

1. 在 Telegram 中搜索 **@andy3800bot**
2. 点击 **开始** 或发送 `/start`
3. 直接发送消息，Bot 会通过 Ollama 模型回复你

## 六、常用命令

```bash
# 查看所有配置的 channel
openclaw channels list

# 查看 channel 状态
openclaw channels status

# 查看 gateway 状态
openclaw gateway status

# 查看日志
openclaw channels logs

# 运行诊断
openclaw doctor --fix

# 查看完整配置
openclaw config get
```

## 七、配置说明

当前 `openclaw.json` 关键配置：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `channels.telegram.botToken` | `7999315279:AAE-...` | Telegram Bot Token |
| `channels.telegram.enabled` | `true` | 启用 Telegram |
| `channels.telegram.dmPolicy` | `pairing` | 私聊策略 |
| `channels.telegram.groupPolicy` | `allowlist` | 群聊策略（白名单） |
| `channels.telegram.streamMode` | `partial` | 流式输出模式 |
| `models.providers.ollama.baseUrl` | `http://127.0.0.1:11434/v1` | Ollama API 地址 |
| `agents.defaults.model.primary` | `ollama/qwen3:8b` | 默认使用千问3 8B模型 |
| `gateway.port` | `18789` | Gateway 端口 |

## 八、故障排查

### Bot 没有响应？
1. 确认 Ollama 在运行：`curl http://127.0.0.1:11434/v1/models`
2. 确认 Gateway 在运行：`openclaw gateway status`
3. 查看日志：`openclaw channels logs`

### Token 相关错误？
确认 `openclaw.json` 中的 `botToken` 正确，或重新设置：
```bash
openclaw config set channels.telegram.botToken "你的TOKEN"
```

### Gateway 端口被占用？
```bash
openclaw gateway run --force
```
