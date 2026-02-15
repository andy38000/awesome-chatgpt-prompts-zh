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

# 另一个终端，拉取模型（如果还没有的话）
ollama pull gpt-oss:20b
```

确认 Ollama 在 `http://127.0.0.1:11434` 运行。

## 四、启动 OpenClaw Gateway

### 方式 1：前台运行（推荐调试时使用）

```bash
openclaw gateway run --verbose
```

你应该看到类似输出：
```
[gateway] agent model: ollama/gpt-oss:20b
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
| `agents.defaults.model.primary` | `ollama/gpt-oss:20b` | 默认使用的模型 |
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
