**总览**
深搜下来，这份 CLI 里所有“依赖远程”的东西可以分成两类：

- 硬依赖：不接远程就没法完成核心推理/模型调用。
- 软依赖：核心 CLI 能跑，但这些功能、同步、分析、更新、市场、远程会话会失效。

下面这份清单基本覆盖了主要出网点和服务端耦合点。

**1. 模型 / 提供商类**
- [ ] 核心模型请求链硬绑定 Anthropic SDK 和 Anthropic 风格消息流，入口在 [client.ts](/D:/cc/src/services/api/client.ts)、[claude.ts](/D:/cc/src/services/api/claude.ts)、[query.ts](/D:/cc/src/query.ts)、[QueryEngine.ts](/D:/cc/src/QueryEngine.ts)。这是真正的“心脏”，不改这里就不是通用 CLI。
- [ ] provider 选择目前只是 Anthropic 生态内部分支，不是通用适配层。判断逻辑在 [providers.ts](/D:/cc/src/utils/model/providers.ts)，支持 `firstParty / bedrock / vertex / foundry`，但底层仍走 Anthropic 客户端语义。
- [ ] Bedrock、Vertex、Foundry 都是远程依赖，鉴权和区域/项目逻辑都在 [client.ts](/D:/cc/src/services/api/client.ts)。
- [ ] 启动时还会拉“模型能力”信息，属于额外远程依赖，在 [modelCapabilities.ts](/D:/cc/src/utils/model/modelCapabilities.ts)。
- [ ] 配额/限流检测会主动发一个探测请求，在 [claudeAiLimits.ts](/D:/cc/src/services/claudeAiLimits.ts)。

**2. 账户 / OAuth / 组织信息**
- [ ] OAuth 整条链都依赖 Anthropic/Claude 服务端，核心在 [oauth.ts](/D:/cc/src/constants/oauth.ts)、[client.ts](/D:/cc/src/services/oauth/client.ts)、[index.ts](/D:/cc/src/services/oauth/index.ts)、[getOauthProfile.ts](/D:/cc/src/services/oauth/getOauthProfile.ts)。
- [ ] 账号资料、组织 UUID、订阅类型、rate limit tier、profile 等都会从远程拿，在 [client.ts](/D:/cc/src/services/oauth/client.ts)、[getOauthProfile.ts](/D:/cc/src/services/oauth/getOauthProfile.ts)、[auth.ts](/D:/cc/src/utils/auth.ts)。
- [ ] `login / logout / setup-token / upgrade` 都直接依赖远程账户体系，入口散落在 [auth.ts](/D:/cc/src/cli/handlers/auth.ts)、[login.tsx](/D:/cc/src/commands/login/login.tsx)、[upgrade.tsx](/D:/cc/src/commands/upgrade/upgrade.tsx)。
- [ ] `bootstrap` 会从服务端拉 `client_data` 和额外模型选项，在 [bootstrap.ts](/D:/cc/src/services/api/bootstrap.ts)。

**3. 遥测 / 数据收集 / 用户信息**
- [ ] 统一分析事件入口在 [index.ts](/D:/cc/src/services/analytics/index.ts)，真正的路由在 [sink.ts](/D:/cc/src/services/analytics/sink.ts)。
- [ ] Datadog 上报在 [datadog.ts](/D:/cc/src/services/analytics/datadog.ts)，会把允许的事件批量发到 Datadog。
- [ ] 一方事件上报在 [firstPartyEventLogger.ts](/D:/cc/src/services/analytics/firstPartyEventLogger.ts) 和 [firstPartyEventLoggingExporter.ts](/D:/cc/src/services/analytics/firstPartyEventLoggingExporter.ts)，目标是 `/api/event_logging/batch`。
- [ ] GrowthBook 远程特性开关和实验分流在 [growthbook.ts](/D:/cc/src/services/analytics/growthbook.ts)。这里会发送用户属性。
- [ ] OpenTelemetry/OTLP/Prometheus/BigQuery 指标与 tracing 在 [instrumentation.ts](/D:/cc/src/utils/telemetry/instrumentation.ts)、[bigqueryExporter.ts](/D:/cc/src/utils/telemetry/bigqueryExporter.ts)、[sessionTracing.ts](/D:/cc/src/utils/telemetry/sessionTracing.ts)、[events.ts](/D:/cc/src/utils/telemetry/events.ts)。
- [ ] `BigQueryMetricsExporter` 会把指标发到 `https://api.anthropic.com/api/claude_code/metrics`，见 [bigqueryExporter.ts](/D:/cc/src/utils/telemetry/bigqueryExporter.ts)。
- [ ] 被收集/拼装的用户元数据在 [user.ts](/D:/cc/src/utils/user.ts) 和 [metadata.ts](/D:/cc/src/services/analytics/metadata.ts)。包括 `deviceId`、`sessionId`、`email`、`organizationUuid`、`accountUuid`、`subscriptionType`、`rateLimitTier`、`firstTokenTime`、GitHub Actions 元数据，事件元数据里还会带 repo remote hash、平台、VCS、MCP 信息等。
- [ ] 如果开了 `OTEL_LOG_USER_PROMPTS`，用户 prompt 会进 tracing/event；否则会被 redact。相关逻辑在 [events.ts](/D:/cc/src/utils/telemetry/events.ts) 和 [sessionTracing.ts](/D:/cc/src/utils/telemetry/sessionTracing.ts)。
- [ ] 如果有 `CLAUDE_CODE_WORKSPACE_HOST_PATHS`，OTEL 事件还会带工作区宿主路径，在 [events.ts](/D:/cc/src/utils/telemetry/events.ts)。
- [ ] 隐私总开关在 [privacyLevel.ts](/D:/cc/src/utils/privacyLevel.ts)。`DISABLE_TELEMETRY` 和 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` 是你去远程化时最该保留/强化的现成入口。

**4. Claude.ai / 远程会话 / Web 端功能**
- [ ] 远程 session、teleport、CCR、web session 全是强服务端功能，主入口在 [api.ts](/D:/cc/src/utils/teleport/api.ts)、[RemoteSessionManager.ts](/D:/cc/src/remote/RemoteSessionManager.ts)、[SessionsWebSocket.ts](/D:/cc/src/remote/SessionsWebSocket.ts)、[sessionIngress.ts](/D:/cc/src/services/api/sessionIngress.ts)、[bridgeMain.ts](/D:/cc/src/bridge/bridgeMain.ts)。
- [ ] 环境列表和默认云环境创建都依赖远程环境服务，在 [environments.ts](/D:/cc/src/utils/teleport/environments.ts)。
- [ ] `remote-setup` 会把 GitHub token 导入后端、创建默认环境，在 [api.ts](/D:/cc/src/commands/remote-setup/api.ts)。
- [ ] 常量级别也绑了 Claude.ai / Claude Code web URL，在 [product.ts](/D:/cc/src/constants/product.ts)。
- [ ] `share / teleport / web open / bridge / remoteControl` 这一整片都可以视为可整体切掉的远程子系统，命令层汇总见 [commands.ts](/D:/cc/src/commands.ts)。

**5. 组织策略 / 同步 / 企业能力**
- [ ] 远程托管设置在 [remoteManagedSettings/index.ts](/D:/cc/src/services/remoteManagedSettings/index.ts)。
- [ ] 组织级 policy limits 在 [policyLimits/index.ts](/D:/cc/src/services/policyLimits/index.ts)。
- [ ] 用户设置同步在 [settingsSync/index.ts](/D:/cc/src/services/settingsSync/index.ts)。
- [ ] 团队记忆同步在 [teamMemorySync/index.ts](/D:/cc/src/services/teamMemorySync/index.ts)。
- [ ] Claude.ai MCP server 配置拉取在 [claudeai.ts](/D:/cc/src/services/mcp/claudeai.ts)。
- [ ] 这些都不是核心推理必需，但都强依赖 Anthropic 后端状态和组织体系。

**6. 功能性 API**
- [ ] 使用量/extra usage 查询在 [usage.ts](/D:/cc/src/services/api/usage.ts)。
- [ ] guest pass / referral 在 [referral.ts](/D:/cc/src/services/api/referral.ts)。
- [ ] overage credit grant 在 [overageCreditGrant.ts](/D:/cc/src/services/api/overageCreditGrant.ts)。
- [ ] first token date 在 [firstTokenDate.ts](/D:/cc/src/services/api/firstTokenDate.ts)。
- [ ] 隐私/Grove 配置和开关在 [grove.ts](/D:/cc/src/services/api/grove.ts) 以及命令入口 [privacy-settings.tsx](/D:/cc/src/commands/privacy-settings/privacy-settings.tsx)。
- [ ] admin request 这类组织协作功能在 [adminRequests.ts](/D:/cc/src/services/api/adminRequests.ts)。
- [ ] 文件上传/下载 API 在 [filesApi.ts](/D:/cc/src/services/api/filesApi.ts)。
- [ ] 这些都能切，但切完要同步删对应 UI 和命令。

**7. 插件 / 市场 / 更新 / 发布信息**
- [ ] 官方插件市场常量在 [officialMarketplace.ts](/D:/cc/src/utils/plugins/officialMarketplace.ts)，官方市场远程镜像/GCS 拉取在 [officialMarketplaceGcs.ts](/D:/cc/src/utils/plugins/officialMarketplaceGcs.ts)。
- [ ] marketplace 刷新、plugin autoupdate、远程安装统计都依赖网络，在 [pluginAutoupdate.ts](/D:/cc/src/utils/plugins/pluginAutoupdate.ts)、[installCounts.ts](/D:/cc/src/utils/plugins/installCounts.ts)、[fetchTelemetry.ts](/D:/cc/src/utils/plugins/fetchTelemetry.ts)。
- [ ] `release-notes` 会从 GitHub 拉 changelog，在 [releaseNotes.ts](/D:/cc/src/utils/releaseNotes.ts) 和 [release-notes.ts](/D:/cc/src/commands/release-notes/release-notes.ts)。
- [ ] `update` 和 native installer 会访问 GCS / Artifactory，在 [update.ts](/D:/cc/src/cli/update.ts) 和 [download.ts](/D:/cc/src/utils/nativeInstaller/download.ts)。
- [ ] `install-github-app`、`install-slack-app` 都是外部服务集成，在 [install-github-app.tsx](/D:/cc/src/commands/install-github-app/install-github-app.tsx) 和 [install-slack-app.ts](/D:/cc/src/commands/install-slack-app/install-slack-app.ts)。

**8. MCP / 外部服务器连接**
- [ ] MCP 客户端本身就支持远程 SSE / Streamable HTTP / WebSocket server，主干在 [client.ts](/D:/cc/src/services/mcp/client.ts)。
- [ ] MCP OAuth 和授权发现非常重，在 [auth.ts](/D:/cc/src/services/mcp/auth.ts)。
- [ ] 官方 MCP registry 拉取在 [officialRegistry.ts](/D:/cc/src/services/mcp/officialRegistry.ts)。
- [ ] Claude.ai 组织下发的 MCP connectors 在 [claudeai.ts](/D:/cc/src/services/mcp/claudeai.ts)。
- [ ] 如果你要做“纯本地版”，MCP 最好只保留 stdio/local server，远程 MCP transport 直接禁掉。

**结论**
如果你的目标是做一个“属于自己的 Claude CLI”，按裁剪优先级我建议这样看：

- 第一批必须重构： [client.ts](/D:/cc/src/services/api/client.ts)、[claude.ts](/D:/cc/src/services/api/claude.ts)、[query.ts](/D:/cc/src/query.ts)、[QueryEngine.ts](/D:/cc/src/QueryEngine.ts)。
- 第一批建议删除： [remote](/D:/cc/src/remote)、[bridge](/D:/cc/src/bridge)、[utils/teleport](/D:/cc/src/utils/teleport)、[services/api/sessionIngress.ts](/D:/cc/src/services/api/sessionIngress.ts)、[commands/remote-setup](/D:/cc/src/commands/remote-setup)。
- 第二批建议删除： [services/analytics](/D:/cc/src/services/analytics)、[utils/telemetry](/D:/cc/src/utils/telemetry)、[services/api/grove.ts](/D:/cc/src/services/api/grove.ts)、[services/api/referral.ts](/D:/cc/src/services/api/referral.ts)、[services/api/usage.ts](/D:/cc/src/services/api/usage.ts)。
- 第三批按需保留： [services/mcp](/D:/cc/src/services/mcp) 里只留本地 stdio 路径，砍掉远程 OAuth / registry / claude.ai connector。

如果你要，我下一步可以直接给你出一版“去远程化改造清单 v1”，按：
1. 必删文件
2. 必改接口
3. 可保留本地能力
4. 最小可运行自有 CLI 架构

这样你就能开始动刀了。