# WEPClaude

[English](./README.md) | 简体中文

`WEPClaude` 是一个基于恢复版 Claude Code 代码继续魔改出来的 CLI 分支，并重新整理成了可正常使用 npm 构建的项目。

这个分支的目标不是“尽量还原官方”，而是做成一个更适合自己改造、分发、继续扩展的私有化 CLI：

- 自定义品牌
- 自定义欢迎页
- 独立本地配置存储
- CLI 内管理 provider / 模型
- 支持 Anthropic 格式 provider
- 支持 OpenAI 兼容格式 provider

当前版本：`0.0.1`

## 项目定位

这不是官方上游源码仓库。

这是一个适合下面这些用途的魔改分支：

- 本地开发
- CLI 界面和品牌改造
- provider / 模型接入实验
- 源码级调试和功能扩展

## 当前已经做好的东西

- 可用 npm 正常安装依赖并构建
- 可直接从构建产物启动
- 全局 CLI 命令名已经改为 `wepclaude`
- `/model` 已改造成 provider 管理入口
- 可在 CLI 内完成 provider 添加流程：
  - 选择 `Anthropic` 或 `OpenAI format`
  - 输入 base URL
  - 输入 API key
  - 从 `/models` 拉模型列表，或手动输入模型
  - 直接激活 provider / model
- 模型显示格式改为 `提供商名/模型`
- 默认配置命名空间已经和原版默认路径分离

## 本地存储

这个魔改版默认使用独立本地路径：

- 配置目录：`~/.wepscli`
- 全局配置文件：`~/.wepscli.json`
- Windows / Linux 下的凭据回退文件：`~/.wepscli/.credentials.json`

这意味着在默认情况下，`WEPClaude` 和原版 Claude CLI 可以在同一台设备上并存，并且不会共用同一套本地配置文件。

需要注意：

- 如果你手动设置了 `CLAUDE_CONFIG_DIR`，仍然可以把两者指到同一个目录。
- macOS 的 keychain 服务名目前还没有完全重新隔离，所以在 macOS 上还不能算 100% 凭据彻底分离。

## 环境要求

- Node.js `>= 18`
- npm `>= 9`

## 快速开始

```bash
npm install
npm run build
node dist/cli.js --help
node dist/cli.js --version
```

## 启动方式

直接运行构建产物：

```bash
node dist/cli.js
```

查看版本：

```bash
node dist/cli.js --version
```

通过 npm 启动：

```bash
npm start
```

## 安装成命令行工具

在项目根目录执行：

```bash
npm install -g .
```

之后即可直接使用：

```bash
wepclaude --help
wepclaude --version
```

开发阶段也可以使用：

```bash
npm link
```

## 构建与打包

构建：

```bash
npm run build
```

打成可分发 npm 包：

```bash
npm pack
```

生成示例：

```text
wepclaude-0.0.1.tgz
```

## 常用命令

```bash
npm install
npm run build
npm run clean
npm pack
node dist/cli.js --version
wepclaude --version
```

## 目录结构

```text
.
|-- package.json
|-- package-lock.json
|-- scripts/
|   `-- build.mjs
|-- src/
|-- vendor/
`-- dist/
```

## 已知限制

- 还有一部分界面文案和帮助信息保留了原来的 Claude 品牌字样。
- 代码里仍然存在一些依赖远程服务的功能，如果你想做成完全自有分支，还需要继续清理。
- macOS keychain 还没完全做独立隔离。
- 这类恢复源码项目本身不保证与上游行为 100% 完全一致。

## 建议继续魔改的方向

- 完成全局品牌替换
- 继续移除或禁用依赖远程服务的功能
- 补齐 macOS 凭据命名空间隔离
- 继续优化 provider 管理体验
- 清理 CLI 内遗留的 `claude` 命令和帮助文案

## 源码分发建议

如果你要把源码发给别人参谋，最小建议清单是：

- `src/`
- `scripts/`
- `vendor/`
- `package.json`
- `package-lock.json`
- `README.md`

不要把你本机的配置文件、provider key、凭据文件一起发出去。
