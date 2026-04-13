# 前后端分离改造方案

## 1. 目标

当前项目的后端能力主要耦合在 `frontend/apps/app/server` 中，包含：

- 鉴权与会话
- Chat / Message / Agent 执行
- Sources 管理
- 文档同步工作流
- Sandbox / Snapshot
- 上传与文件管理
- 管理后台接口
- Webhook / Bot 接入
- 统计、限流、配置管理

目标是改造成：

- `frontend/` 只保留 Nuxt 前端页面、组件、状态管理、API SDK/BFF 适配层
- `backend/` 使用 Python FastAPI 承载全部业务 API
- 智能体框架使用 `LangChain + LangGraph`
- 前后端通过 OpenAPI/JSON API 解耦
- 后续 Bot、异步任务、同步工作流统一复用 Python 服务能力

## 2. 现状判断

从代码结构看，当前是一个“单体式 Nuxt 应用”：

- Web UI 在 `frontend/apps/app/app`
- 服务端接口在 `frontend/apps/app/server/api`
- 数据模型在 `frontend/apps/app/server/db/schema.ts`
- Agent 能力在 `frontend/packages/agent`
- SDK 在 `frontend/packages/sdk`
- Sandbox 和 snapshot 逻辑在 `frontend/apps/app/server/utils/sandbox`
- 文档同步工作流在 `frontend/apps/app/server/workflows`

关键问题不是“把接口搬走”这么简单，而是服务端存在几类不同性质的能力：

1. 标准 CRUD API
2. 长连接/流式响应 API
3. 第三方集成 API
4. 异步工作流
5. Agent 编排与工具调用
6. 平台能力依赖

其中最重的耦合点有三个：

- Nuxt server route 与数据库访问直接耦合
- `@savoir/agent` 基于 TS `ai` SDK 的 agent 执行链路
- `@vercel/sandbox` / workflow / NuxtHub 的平台依赖

所以推荐采用“分阶段迁移”，而不是一次性重写。

## 3. 目标架构

建议落成如下结构：

```text
xagent/
├─ frontend/
│  ├─ apps/app
│  │  ├─ app                 # 纯前端 UI
│  │  ├─ composables         # useApi / useAuth / useChat
│  │  └─ server             # 仅保留极少量前端运行时必需代理，最终尽量清空
│  └─ packages/
│     ├─ web-sdk            # 调 backend 的 TS SDK
│     └─ shared-contracts   # OpenAPI 生成类型或手写 DTO
│
└─ backend/
   └─ app/
      ├─ web/api            # FastAPI routers
      ├─ domain             # chats / sources / sandbox / sync / admin
      ├─ agents             # LangChain / LangGraph
      ├─ integrations       # github / discord / youtube / storage
      ├─ repositories       # DB / cache / blob
      ├─ workers            # 异步任务与 workflow
      ├─ schemas            # Pydantic DTO
      └─ core               # config / auth / observability / rate limit
```

职责划分：

- Frontend
  - UI 渲染
  - 调用 backend API
  - 处理 SSE / streaming 展示
  - 不再持有业务状态真相
- Backend
  - 鉴权、RBAC、API key
  - 数据库模型和迁移
  - Agent 编排
  - 文档同步与异步任务
  - 沙箱和快照管理
  - Webhook 与 Bot 接入

## 4. 技术选型建议

### 4.1 后端主栈

- Web 框架：FastAPI
- 数据层：SQLAlchemy 2.x Async + Alembic
- 校验：Pydantic v2
- 鉴权：
  - 首选 `fastapi-users` 承接基础用户体系
  - 如需兼容现有 Better Auth，可短期通过 JWT/JWK 或 session bridge 过渡
- 缓存/会话：Redis
- 异步任务：
  - 简化版可先用 `FastAPI + asyncio.create_task + Redis 状态表`
  - 正式版建议 `Celery/RQ/Arq/Taskiq` 四选一
  - 你现有模板里已接入 RabbitMQ，可直接走 `Taskiq + RabbitMQ` 或自建 worker
- 文件存储：S3 兼容 / MinIO / Vercel Blob 二次封装
- 可观测性：保留现有 Sentry / Prometheus / OpenTelemetry

### 4.2 智能体栈

建议分层使用：

- `LangChain`
  - 模型封装
  - Prompt / Tool / Retriever / Output parser
  - 供应商抽象
- `LangGraph`
  - 多步骤 agent 编排
  - Router / Planner / Tool executor / Human interrupt
  - 有状态图执行
  - 失败重试与可恢复执行

建议原则：

- 不要用 LangChain 把所有业务都包进去
- Agent 只负责“推理与决策”
- 数据访问、权限校验、同步任务、持久化仍然用普通 service/repository 完成

## 5. 模块替换矩阵

下面是从当前 TS 服务端到 Python FastAPI 的替换建议。

### 5.1 Chat / Message

当前位置：

- `frontend/apps/app/server/api/chats*.ts`
- `frontend/apps/app/server/db/schema.ts`

现状：

- 聊天会话 CRUD
- 消息持久化
- AI 流式输出
- 标题生成
- 限流

Python 替换：

- 新建 `backend/app/domain/chats/`
  - `service.py`
  - `repository.py`
  - `schemas.py`
- 新建 `backend/app/web/api/chats/views.py`
- 流式输出改为：
  - FastAPI `StreamingResponse`
  - SSE 或 chunked response

接口映射建议：

- `GET /api/chats` -> `GET /api/v1/chats`
- `POST /api/chats` -> `POST /api/v1/chats`
- `GET /api/chats/{id}` -> `GET /api/v1/chats/{id}`
- `POST /api/chats/{id}` -> `POST /api/v1/chats/{id}/messages:stream`
- `DELETE /api/chats/{id}` -> `DELETE /api/v1/chats/{id}`
- `PATCH /api/chats/{id}/share` -> `PATCH /api/v1/chats/{id}/share`

替换重点：

- 前端 `useChat` 改成调用 FastAPI SSE
- 消息表结构迁移到 SQLAlchemy
- 标题生成从 TS `generateTitle` 改成 Python LLM helper

### 5.2 Agent / Router

当前位置：

- `frontend/packages/agent`
- `frontend/apps/app/server/api/chats/[id].post.ts`

现状：

- Router 判断复杂度
- 动态模型选择
- Tool loop agent
- admin/source 两类 agent

Python 替换：

- 新建 `backend/app/agents/`
  - `graph/`
  - `nodes/`
  - `tools/`
  - `prompts/`
  - `runtime/`

推荐 LangGraph 拆分：

1. `router_node`
   - 判断问题复杂度
   - 决定模型、最大步数、是否允许 web search / sandbox
2. `context_node`
   - 拉取 chat history、agent config、source metadata
3. `planner_node`
   - 生成执行计划
4. `tool_node`
   - 执行工具
5. `judge_node`
   - 判断是否继续
6. `respond_node`
   - 产出最终回答
7. `admin_tool_node`
   - 仅 admin 模式开放

为什么这样替换：

- TS 版本现在是偏“单 agent tool loop”
- Python 迁移时正好借 LangGraph 把路由、工具执行、终止判断显式化
- 后续更容易插入审批、中断恢复、异步任务

### 5.3 Agent Config

当前位置：

- `frontend/apps/app/server/api/agent-config/*`
- `agent_config` 表

Python 替换：

- `backend/app/domain/agent_config/`
- `backend/app/web/api/agent_config/views.py`

保留字段：

- `additional_prompt`
- `response_style`
- `language`
- `default_model`
- `max_steps_multiplier`
- `temperature`
- `search_instructions`
- `citation_format`
- `is_active`

替换建议：

- 表结构基本可原样迁移
- 前端管理页面直接改调 Python API
- Agent graph 在每次执行时读取 active config

### 5.4 Sources 管理

当前位置：

- `frontend/apps/app/server/api/sources/*`
- `sources` 表

现状：

- GitHub / YouTube / File source CRUD
- OCR / 文件列表管理

Python 替换：

- `backend/app/domain/sources/`
- `backend/app/web/api/sources/views.py`
- `backend/app/integrations/github/`
- `backend/app/integrations/youtube/`
- `backend/app/integrations/storage/`

建议：

- Source CRUD 先完全平移
- source type 用 Python `Enum`
- 文件型 source 单独抽象 storage backend

### 5.5 文档同步 Sync Workflow

当前位置：

- `frontend/apps/app/server/api/sync/*`
- `frontend/apps/app/server/workflows/sync-docs/*`
- `frontend/apps/app/server/utils/sandbox/source-sync.ts`

现状：

- 从 GitHub/YouTube 拉内容
- 写入 sandbox 文件系统
- push 到 snapshot repo
- 再创建 snapshot

Python 替换：

- `backend/app/domain/sync/`
- `backend/app/workers/sync_docs/`
- `backend/app/integrations/sandbox/`

建议拆成三层：

1. `SyncService`
   - 接收同步请求
   - 校验 source
   - 创建任务记录
2. `SyncWorker`
   - 真正执行 clone / transcript / file write / cleanup
3. `SnapshotService`
   - push repo
   - create snapshot
   - 更新 current snapshot

如果你准备继续使用 Vercel Sandbox：

- Python 需要重新封装 Vercel Sandbox API
- 不建议继续依赖 Nuxt/Vercel workflow
- 改成 Python worker + 任务状态表

如果你准备弱化平台依赖：

- 直接用容器/临时工作目录替代 snapshot sandbox
- 用 Git worktree 或临时目录同步 docs
- snapshot 变为“已同步产物版本号”而不是 Vercel snapshot

这是整个迁移里最需要先定方向的模块。

### 5.6 Sandbox / Shell

当前位置：

- `frontend/apps/app/server/api/sandbox/*`
- `frontend/apps/app/server/utils/sandbox/*`
- `frontend/packages/sdk`

现状：

- 维护 active sandbox session
- 从 snapshot 恢复 sandbox
- 暴露 shell/batch shell 给 agent 使用

Python 替换：

- `backend/app/domain/sandbox/`
- `backend/app/web/api/sandbox/views.py`
- `backend/app/agents/tools/sandbox.py`

建议方案：

- 对外 API 保留类似能力：
  - `POST /api/v1/sandbox/shell`
  - `POST /api/v1/sandbox/snapshot`
  - `GET /api/v1/sandbox/status`
- SDK 升级为前端/第三方统一调用 Python API

工具层建议：

- Agent 不直接操作底层 sandbox client
- 通过 LangChain Tool 调 `SandboxService.execute_readonly(...)`
- 服务层统一做：
  - allowlist 校验
  - 命令审计
  - session 复用
  - 超时控制

### 5.7 Upload / Blob

当前位置：

- `frontend/apps/app/server/api/upload/*`
- 依赖 `@vercel/blob`

Python 替换：

- `backend/app/domain/files/`
- `backend/app/web/api/files/views.py`
- `backend/app/integrations/storage/`

建议：

- 抽象 `StorageService`
  - `put_file`
  - `delete_prefix`
  - `list_files`
  - `sign_upload_url`
- 存储实现可先兼容 Vercel Blob，后续再切到 S3/MinIO

前端改造：

- 上传流程从 Nuxt server route 改成：
  - 前端先请求 Python 获取上传 URL
  - 再直传对象存储

### 5.8 鉴权与权限

当前位置：

- `frontend/apps/app/server/auth.config.ts`
- Better Auth

这是迁移中的第二大风险点。

推荐两阶段：

#### 阶段 A：过渡兼容

- 前端登录暂时保留现有 Better Auth
- Nuxt 作为登录入口
- Nuxt 调 Python API 时带上后端可验证的 JWT / internal token
- Python 先只认：
  - internal signed token
  - API key

优点：

- 前端登录体系不必第一阶段重做
- 能先把聊天、sources、sync 搬走

缺点：

- 短期存在双鉴权体系

#### 阶段 B：统一到 Python

- 用户体系改到 `fastapi-users`
- 前端直接对接 Python auth
- Nuxt server 只做 SSR 与静态资源

如果你希望改造成本最低，建议先走阶段 A。

### 5.9 Admin 模块

当前位置：

- `frontend/apps/app/server/api/admin/*`
- `frontend/apps/app/server/utils/chat/admin-tools/*`

Python 替换：

- `backend/app/domain/admin/`
- `backend/app/web/api/admin/views.py`
- `backend/app/agents/tools/admin/`

拆分原则：

- 管理后台 API 是普通后端接口
- Admin agent tools 是 agent 专用工具，不要复用 HTTP controller 直接调用数据库
- tools 调 service，service 再调 repository

### 5.10 Stats / Rate Limit / Logs

当前位置：

- `frontend/apps/app/server/api/stats/*`
- `frontend/apps/app/server/utils/rate-limit.ts`
- `evlog`

Python 替换：

- `backend/app/domain/stats/`
- `backend/app/core/rate_limit.py`
- `backend/app/core/logging.py`

建议：

- rate limit 用 Redis
- usage stats 入库保留
- agent/tool 执行链路统一打 tracing span

### 5.11 Webhook / Bot

当前位置：

- `frontend/apps/app/server/api/webhooks/[platform].post.ts`
- `frontend/apps/app/server/api/discord/gateway.get.ts`
- `frontend/apps/app/server/utils/bot/*`

Python 替换：

- `backend/app/web/api/webhooks/views.py`
- `backend/app/integrations/github_bot/`
- `backend/app/integrations/discord_bot/`

建议：

- Bot 入口全部迁到 Python
- 共享同一套 LangGraph runtime
- 不要保留一套 TS bot、一套 Python bot

## 6. 数据层迁移方案

当前核心表：

- `chats`
- `messages`
- `sources`
- `agent_config`
- `api_usage`
- `usage_stats`

建议：

1. 先保持 PostgreSQL 不变
2. 用 SQLAlchemy 重建 ORM model
3. 用 Alembic 创建“对齐现有 schema”的 baseline migration
4. 再增加 Python 专属表

建议新增表：

- `sync_jobs`
- `sync_job_logs`
- `sandbox_sessions`
- `snapshots`
- `agent_runs`
- `agent_steps`
- `uploaded_files`

原因：

- 当前很多运行态信息存在 KV/平台态里
- Python 后端要可观测、可恢复、可审计，必须把关键状态显式化

## 7. LangChain + LangGraph 设计建议

### 7.1 图结构

推荐至少拆成两张图：

1. `chat_graph`
   - 面向用户聊天
2. `admin_graph`
   - 面向管理员操作

可选第三张：

3. `sync_assistant_graph`
   - 面向知识同步排障和半自动运维

### 7.2 State 设计

建议统一 state：

```python
class AgentState(TypedDict, total=False):
    request_id: str
    user_id: str
    chat_id: str
    mode: str
    messages: list
    source_ids: list[str]
    router: dict
    agent_config: dict
    plan: list[str]
    tool_results: list[dict]
    final_response: str
    terminate: bool
```

### 7.3 Tool 设计

建议工具按边界分组：

- knowledge tools
  - `list_sources`
  - `get_source_files`
  - `search_docs`
- sandbox tools
  - `run_readonly_shell`
  - `get_snapshot_status`
- admin tools
  - `query_chats`
  - `query_stats`
  - `get_agent_config`
  - `run_sql_readonly`
- external tools
  - `web_search`
  - `github_repo_fetch`

原则：

- Tool 输入输出必须结构化
- Tool 不直接暴露 ORM session
- Tool 必须显式做权限校验

### 7.4 为什么不是纯 LangChain AgentExecutor

因为你当前业务不只是一个问答 agent，而是：

- 有用户角色
- 有 admin 模式
- 有沙箱
- 有同步任务
- 有异步工作流
- 有外部平台 webhook

这种场景下，LangGraph 更适合长期维护。

## 8. 分阶段迁移计划

### Phase 0：基线梳理

目标：

- 冻结现有 `frontend/apps/app/server` 功能边界
- 列出接口、表结构、依赖平台
- 确定迁移优先级

产出：

- API inventory
- DB schema inventory
- 流式接口 inventory
- 平台依赖 inventory

### Phase 1：Python 领域骨架

目标：

- 在 `backend` 中建立正式业务目录
- 建 chats/sources/agent_config/stats/sandbox/sync 领域骨架
- 引入 OpenAPI 前缀 `/api/v1`

建议新增目录：

```text
backend/app/
├─ core/
├─ schemas/
├─ repositories/
├─ domain/
│  ├─ chats/
│  ├─ sources/
│  ├─ agent_config/
│  ├─ sandbox/
│  ├─ sync/
│  └─ stats/
├─ agents/
│  ├─ graph/
│  ├─ nodes/
│  ├─ tools/
│  └─ prompts/
└─ web/api/v1/
```

### Phase 2：先迁 CRUD，后迁流式

优先迁移：

- sources
- agent-config
- stats
- admin users/api-keys
- chats 列表与详情

原因：

- 这部分对前端改动小
- 容易验证
- 能先把 DB / auth / DTO / service 层跑通

前端改造：

- 新建 `frontend/packages/web-sdk`
- 所有页面请求改走 Python API

### Phase 3：迁移 Chat Streaming + Agent Runtime

目标：

- 用 LangGraph 替代 `@savoir/agent`
- 用 FastAPI StreamingResponse 替代 Nuxt stream route

关键动作：

- 实现 chat graph
- 实现 tool registry
- 实现消息持久化
- 实现中断/超时处理
- 对齐前端流式协议

建议：

- 流协议尽量兼容现有前端消费格式
- 先做兼容层，再优化协议

### Phase 4：迁移 Sandbox 与 SDK

目标：

- `frontend/packages/sdk` 改成调用 Python API
- 把 session / snapshot / shell 权限控制迁到 Python

注意：

- 如果 Vercel Sandbox 没有成熟 Python SDK，建议封装 REST client
- 如果平台限制太重，尽早考虑替代实现

### Phase 5：迁移 Sync Workflow

目标：

- 替换 Nuxt workflow
- 建立 Python 异步任务系统

建议：

- 同步任务不走 HTTP 长事务
- API 只负责提交任务、查询状态、取消任务

接口建议：

- `POST /api/v1/sync-jobs`
- `GET /api/v1/sync-jobs/{id}`
- `POST /api/v1/sync-jobs/{id}/cancel`

### Phase 6：迁移 Upload / Bot / Webhook / Auth

最后迁：

- 文件上传
- GitHub/Discord webhook
- 认证体系统一

原因：

- 这些模块对外部依赖最多
- 放在后面风险更可控

## 9. 前端需要怎么改

前端不是“不动”，而是要做一次边界收缩。

### 9.1 保留

- 页面
- 组件
- composables
- 本地 UI 状态
- SSR 能力

### 9.2 移除或逐步清空

- `frontend/apps/app/server/api/*`
- `frontend/apps/app/server/utils/*` 里的业务逻辑
- `frontend/packages/agent` 中直接承担后端执行的逻辑

### 9.3 新增

- `frontend/packages/web-sdk`
- `frontend/packages/shared-contracts`
- `frontend/apps/app/composables/useBackendClient.ts`

### 9.4 请求模式

统一改成：

- 浏览器 -> FastAPI
- Nuxt SSR -> FastAPI

不要再让前端页面依赖 Nuxt server route 做业务编排。

## 10. 风险与决策点

### 10.1 最大风险

1. 鉴权迁移
2. 流式协议兼容
3. Sandbox 平台依赖
4. LangGraph 替换后行为差异
5. 同步工作流从 Vercel 迁出后的稳定性

### 10.2 需要尽早拍板的决策

1. 数据库是否继续复用现有 PostgreSQL
2. 上传存储是否继续使用 Vercel Blob
3. Sandbox 是否继续使用 Vercel Sandbox
4. 鉴权是否分阶段迁移
5. 异步任务采用 RabbitMQ 还是 Redis 队列

如果这 5 个点不先定，后面的模块设计会反复返工。

## 11. 推荐实施顺序

推荐按下面顺序做，风险最低：

1. 在 `backend` 建立业务骨架和 OpenAPI
2. 迁移 `sources` / `agent-config` / `stats` / `admin` CRUD
3. 前端引入 `web-sdk`，把上述页面改到 Python API
4. 迁移 `chat list/detail`
5. 用 LangGraph 重建 chat runtime
6. 迁移 chat streaming
7. 迁移 sandbox API 和 SDK
8. 迁移 sync workflow
9. 迁移 upload / webhook / bots
10. 最后统一 auth

## 12. 具体落地建议

如果你要快速推进，我建议下一步不是直接大面积重构，而是先做这 4 件事：

1. 在 `backend` 建立 `domain/chats`、`domain/sources`、`domain/agent_config`、`agents` 目录骨架
2. 把现有 TS `schema.ts` 转成 SQLAlchemy models
3. 先实现 `sources` 和 `agent-config` 两组 FastAPI 接口
4. 前端新增 `web-sdk`，先把管理后台改到 Python API

原因：

- 这能最快验证前后端分离架构是否跑通
- 不会一开始就卡在最复杂的 streaming agent
- 也能为后续 LangGraph 接入铺路

## 13. 结论

这次改造本质上不是“把 TS 接口翻译成 Python”，而是把当前 Nuxt 单体应用拆成：

- 一个纯前端交互层
- 一个可独立演进的 FastAPI 业务平台
- 一套基于 LangChain + LangGraph 的 agent runtime

最合理的策略是：

- 先迁标准业务模块
- 再迁 agent 与 streaming
- 最后迁平台依赖最重的 sandbox / sync / auth / bots

这样可以把风险拆开，也更容易逐阶段上线验证。

## 14. API 接口清单（实施版）

这一节把当前 `frontend/apps/app/server/api` 中的存量接口，沉淀成可直接排期的迁移清单。

口径说明：

- 当前存量 Nuxt Server API 共 `44` 个
- 建议按 `6` 个 step 迁移，而不是按技术层硬切
- 以下排期按 `1 名后端 + 1 名前端 + 1 名测试/联调` 的常规配置估算
- 其中 `Chat Streaming / Agent Runtime`、`Sandbox / Sync`、`Auth` 是主要风险项

### 14.1 工作量总览

| 工作模块 | 现有接口数 | 目标 FastAPI 模块 | 工作量 | 主要风险 |
| --- | ---: | --- | --- | --- |
| Chat / Message / Share | 8 | `domain/chats` | L | 流式协议、消息持久化、分享链路兼容 |
| Agent Config | 4 | `domain/agent_config` | S | 配置读取一致性 |
| Sources | 8 | `domain/sources` | M | 文件型 source、OCR、对象存储抽象 |
| Sync / Snapshot / Sandbox | 8 | `domain/sync` `domain/sandbox` | XL | 平台依赖、异步任务、状态可恢复 |
| Stats / Admin | 12 | `domain/stats` `domain/admin` | M | 聚合查询、权限、日志清理 |
| Upload / Webhook / Bot | 4 | `domain/files` `integrations/*` | M | 外部平台适配、上传直传改造 |
| Auth / API Key / Token Bridge | 0（隐式耦合） | `core/auth` | L | Better Auth 过渡与 Python 验签 |

### 14.2 Chat / Message / Share 模块

| 现有接口 | 目标接口 | Step | 后端模块 | 接口业务描述 |
| --- | --- | --- | --- | --- |
| `GET /api/chats` | `GET /api/v1/chats` | Step 2 | `domain/chats` | 查询当前用户聊天会话列表，按创建时间倒序返回 |
| `POST /api/chats` | `POST /api/v1/chats` | Step 2 | `domain/chats` | 创建会话并写入首条用户消息，包含 admin/chat 模式校验和限流 |
| `GET /api/chats/{id}` | `GET /api/v1/chats/{id}` | Step 2 | `domain/chats` | 查询单个会话详情及消息列表 |
| `POST /api/chats/{id}` | `POST /api/v1/chats/{id}/messages:stream` | Step 4 | `domain/chats` + `agents/runtime` | 发起流式对话，包含模型选择、Agent 执行、消息落库、标题生成 |
| `DELETE /api/chats/{id}` | `DELETE /api/v1/chats/{id}` | Step 3 | `domain/chats` + `domain/files` | 删除会话，同时清理聊天附件对象存储 |
| `PATCH /api/chats/{id}/share` | `PATCH /api/v1/chats/{id}/share` | Step 3 | `domain/chats` | 开启/关闭聊天公开分享，并生成或回收分享 token |
| `GET /api/shared/{token}` | `GET /api/v1/shared/chats/{token}` | Step 3 | `domain/chats` | 按分享 token 读取公开聊天内容，用于外部分享页展示 |
| `PATCH /api/messages/{id}/feedback` | `PATCH /api/v1/messages/{id}/feedback` | Step 3 | `domain/chats` | 为 assistant 消息写入点赞/点踩反馈 |

### 14.3 Agent Config 模块

| 现有接口 | 目标接口 | Step | 后端模块 | 接口业务描述 |
| --- | --- | --- | --- | --- |
| `GET /api/agent-config` | `GET /api/v1/agent-config` | Step 2 | `domain/agent_config` | 管理端读取当前生效的 Agent 配置 |
| `PUT /api/agent-config` | `PUT /api/v1/agent-config` | Step 2 | `domain/agent_config` | 更新当前生效配置，包括 prompt、模型、温度、输出风格等 |
| `POST /api/agent-config/reset` | `POST /api/v1/agent-config/reset` | Step 2 | `domain/agent_config` | 将生效配置重置为系统默认值 |
| `GET /api/agent-config/public` | `GET /api/v1/agent-config/public` | Step 2 | `domain/agent_config` | 对 SDK/Bot 暴露当前生效配置，只读接口 |

### 14.4 Sources 模块

| 现有接口 | 目标接口 | Step | 后端模块 | 接口业务描述 |
| --- | --- | --- | --- | --- |
| `GET /api/sources` | `GET /api/v1/sources` | Step 2 | `domain/sources` | 查询全部 source，按类型聚合返回，同时补充最近同步信息 |
| `POST /api/sources` | `POST /api/v1/sources` | Step 2 | `domain/sources` | 新建 GitHub / YouTube / File source |
| `PUT /api/sources/{id}` | `PUT /api/v1/sources/{id}` | Step 2 | `domain/sources` | 更新 source 配置项，如 repo、branch、outputPath、channelId 等 |
| `DELETE /api/sources/{id}` | `DELETE /api/v1/sources/{id}` | Step 2 | `domain/sources` + `domain/files` | 删除 source；file 类型需要同时删除对象存储中的源文件 |
| `POST /api/sources/ocr` | `POST /api/v1/sources/ocr` | Step 2 | `domain/sources` + `integrations/llm` | 识别图片或配置文本中的 source 定义，抽取 GitHub/YouTube 来源 |
| `GET /api/sources/{id}/files` | `GET /api/v1/sources/{id}/files` | Step 2 | `domain/sources` + `domain/files` | 查询 file 类型 source 下已上传的文件列表 |
| `PUT /api/sources/{id}/files` | `PUT /api/v1/sources/{id}/files` | Step 2 | `domain/sources` + `domain/files` | 向 file 类型 source 上传文档文件 |
| `DELETE /api/sources/{id}/files` | `DELETE /api/v1/sources/{id}/files` | Step 2 | `domain/sources` + `domain/files` | 删除 file 类型 source 下的指定文件 |

### 14.5 Stats / Admin 模块

| 现有接口 | 目标接口 | Step | 后端模块 | 接口业务描述 |
| --- | --- | --- | --- | --- |
| `GET /api/stats` | `GET /api/v1/stats` | Step 2 | `domain/stats` | 管理端查看全局 usage、模型分布、来源分布、活跃用户、趋势统计 |
| `GET /api/stats/me` | `GET /api/v1/stats/me` | Step 2 | `domain/stats` | 当前用户查看个人消息数、token 数、模型使用情况 |
| `POST /api/stats/usage` | `POST /api/v1/stats/usage` | Step 2 | `domain/stats` | 记录 SDK / GitHub Bot / Discord Bot 等外部流量 usage |
| `GET /api/admin/users` | `GET /api/v1/admin/users` | Step 2 | `domain/admin` | 管理端查看用户列表、聊天数、消息数、最后活跃时间 |
| `PATCH /api/admin/users/{id}` | `PATCH /api/v1/admin/users/{id}` | Step 2 | `domain/admin` | 管理员修改用户角色 |
| `DELETE /api/admin/users/{id}` | `DELETE /api/v1/admin/users/{id}` | Step 2 | `domain/admin` | 管理员删除用户，同时级联清理用户聊天数据 |
| `GET /api/admin/api-keys` | `GET /api/v1/admin/api-keys` | Step 2 | `domain/admin` | 管理端查看 API Key 列表 |
| `POST /api/admin/api-keys` | `POST /api/v1/admin/api-keys` | Step 2 | `domain/admin` | 生成新的管理用 API Key |
| `DELETE /api/admin/api-keys/{id}` | `DELETE /api/v1/admin/api-keys/{id}` | Step 2 | `domain/admin` | 删除 API Key |
| `GET /api/admin/logs/count` | `GET /api/v1/admin/logs/count` | Step 2 | `domain/admin` | 查询某个时间点之前的日志数量，用于清理前预估 |
| `GET /api/admin/logs/stats` | `GET /api/v1/admin/logs/stats` | Step 2 | `domain/admin` | 日志总量、级别分布、按日趋势统计 |
| `DELETE /api/admin/logs` | `DELETE /api/v1/admin/logs` | Step 2 | `domain/admin` | 清理指定时间之前的日志数据 |

### 14.6 Sync / Snapshot / Sandbox 模块

这一组不是简单平移，建议从“同步工作流接口”升级为“任务型接口 + 状态接口”。

| 现有接口 | 目标接口 | Step | 后端模块 | 接口业务描述 |
| --- | --- | --- | --- | --- |
| `POST /api/sync` | `POST /api/v1/sync-jobs` | Step 5 | `domain/sync` | 提交全量 source 同步任务，可按过滤条件启动批量同步 |
| `POST /api/sync/{source}` | `POST /api/v1/sync-jobs` | Step 5 | `domain/sync` | 提交单个 source 的同步任务，请求体中传 `sourceId` |
| `-` | `GET /api/v1/sync-jobs` | Step 5 | `domain/sync` | 新增，同步任务列表查询 |
| `-` | `GET /api/v1/sync-jobs/{id}` | Step 5 | `domain/sync` | 新增，同步任务详情与日志查询 |
| `-` | `POST /api/v1/sync-jobs/{id}/cancel` | Step 5 | `domain/sync` | 新增，取消运行中的同步任务 |
| `POST /api/sandbox/shell` | `POST /api/v1/sandbox/shell` | Step 5 | `domain/sandbox` | 在沙箱环境执行只读 shell/batch shell 命令 |
| `POST /api/sandbox/snapshot` | `POST /api/v1/sandbox/snapshot` | Step 5 | `domain/sandbox` | 基于当前 snapshot 创建或恢复 sandbox session |
| `-` | `GET /api/v1/sandbox/status` | Step 5 | `domain/sandbox` | 新增，查询当前 sandbox session 与 snapshot 绑定状态 |
| `POST /api/snapshot/sync` | `POST /api/v1/snapshots/sync-current` | Step 5 | `domain/sync` + `domain/sandbox` | 将系统 current snapshot 切换到最新可用版本 |
| `GET /api/snapshot/status` | `GET /api/v1/snapshots/status` | Step 5 | `domain/sync` + `domain/sandbox` | 查询 current snapshot、latest snapshot、是否需要同步 |
| `GET /api/snapshot/config` | `GET /api/v1/snapshots/config` | Step 5 | `domain/sync` | 查询 snapshot 仓库配置 |
| `PUT /api/snapshot/config` | `PUT /api/v1/snapshots/config` | Step 5 | `domain/sync` | 更新 snapshot 仓库配置，并清理相关缓存状态 |
| `POST /api/sandbox/snapshot` | `POST /api/v1/snapshots` | Step 5 | `domain/sync` | 创建新 snapshot；建议从 sandbox 领域下沉到 snapshot/sync 领域统一管理 |

### 14.7 Upload / Webhook / Bot 模块

| 现有接口                            | 目标接口                                              | Step   | 后端模块                                                 | 接口业务描述                                       |
| ------------------------------- | ------------------------------------------------- | ------ | ---------------------------------------------------- | -------------------------------------------- |
| `PUT /api/upload/{chatId}`      | `POST /api/v1/files/chat-attachments:sign-upload` | Step 6 | `domain/files`                                       | 为聊天附件签发上传 URL，前端改为直传对象存储                     |
| `DELETE /api/upload/{pathname}` | `DELETE /api/v1/files/{pathname}`                 | Step 6 | `domain/files`                                       | 删除当前用户自己的聊天附件文件                              |
| `POST /api/webhooks/{platform}` | `POST /api/v1/webhooks/{platform}`                | Step 6 | `integrations/github_bot` `integrations/discord_bot` | 对接 GitHub / Discord 等平台 webhook 回调           |
| `GET /api/discord/gateway`      | `POST /api/v1/bots/discord/gateway:start`         | Step 6 | `integrations/discord_bot`                           | 启动 Discord gateway listener，建议从 GET 改为显式启动动作 |

## 15. 任务排期（Step 版）

### Step 1：基线冻结与后端骨架

建议周期：`1 周`

关联工作模块：

- `backend/app` 目录骨架
- SQLAlchemy Model / Alembic baseline
- `core/auth` 鉴权桥接
- OpenAPI 规范与 `frontend/packages/web-sdk`
- Python 基础设施：DB、Redis、日志、配置、异常处理

接口范围：

- 这一阶段以“可承接接口”为目标，不要求业务接口全部可用
- 需要先把 `/api/v1` 路由基座、统一鉴权依赖、DTO 规范、错误码规范建好

业务目标：

- 让后续所有模块都能在统一的 FastAPI 目录下持续迁移
- 冻结现有 TS 接口行为，避免迁移过程中前端和后端同时漂移

交付物：

- Python 项目骨架
- ORM 基线模型
- OpenAPI 初稿
- `web-sdk` 初版
- Auth bridge 方案落地

### Step 2：先迁低风险 CRUD 与后台管理

建议周期：`1.5 ~ 2 周`

关联工作模块：

- `agent_config`
- `sources`
- `stats`
- `admin`
- `chats` 的 list/detail/create 基础 CRUD

本 step 落地接口：

- `GET/PUT/POST /api/v1/agent-config*`
- `GET/POST/PUT/DELETE /api/v1/sources*`
- `GET/PUT/DELETE /api/v1/sources/{id}/files`
- `POST /api/v1/sources/ocr`
- `GET /api/v1/stats`
- `GET /api/v1/stats/me`
- `POST /api/v1/stats/usage`
- `GET/PATCH/DELETE /api/v1/admin/users*`
- `GET/POST/DELETE /api/v1/admin/api-keys*`
- `GET/DELETE /api/v1/admin/logs*`
- `GET/POST /api/v1/chats`
- `GET /api/v1/chats/{id}`

业务目标：

- 先打通“前端页面 -> Python API -> PostgreSQL”的主路径
- 先把管理后台和 source 管理迁过去，降低后续同步、Agent 迁移的耦合度

交付物：

- 管理后台切到 Python API
- Sources 全量 CRUD 可用
- Agent Config 可从 Python 读取
- Stats / Admin 聚合接口可联调

### Step 3：补齐聊天非流式能力

建议周期：`1 周`

关联工作模块：

- `chats`
- `messages`
- `files`
- `shared`

本 step 落地接口：

- `DELETE /api/v1/chats/{id}`
- `PATCH /api/v1/chats/{id}/share`
- `GET /api/v1/shared/chats/{token}`
- `PATCH /api/v1/messages/{id}/feedback`

业务目标：

- 把聊天域中除 streaming 之外的剩余读写能力全部切到 Python
- 提前消化消息反馈、公开分享、附件清理等边缘能力

交付物：

- 聊天列表/详情/分享/反馈全部由 FastAPI 承接
- 前端 chat 页面只剩流式发送链路仍走 TS

### Step 4：迁移 Chat Streaming 与 Agent Runtime

建议周期：`2 周`

关联工作模块：

- `agents/runtime`
- `domain/chats`
- `LangChain + LangGraph`
- 流式协议兼容层

本 step 落地接口：

- `POST /api/v1/chats/{id}/messages:stream`

业务目标：

- 用 Python 接管当前最核心的对话执行链路
- 完成 Router、Planner、Tool、Respond 的 LangGraph 重建
- 对齐现有前端消息流协议，避免 UI 大改

交付物：

- Chat Streaming 跑在 FastAPI
- 消息持久化、标题生成、限流、审计切到 Python
- `frontend/packages/agent` 停止承担主执行逻辑

### Step 5：迁移 Sandbox / Snapshot / Sync Workflow

建议周期：`1.5 ~ 2 周`

关联工作模块：

- `domain/sandbox`
- `domain/sync`
- `workers/sync_docs`
- `integrations/sandbox`
- `snapshots`

本 step 落地接口：

- `POST /api/v1/sync-jobs`
- `GET /api/v1/sync-jobs`
- `GET /api/v1/sync-jobs/{id}`
- `POST /api/v1/sync-jobs/{id}/cancel`
- `POST /api/v1/sandbox/shell`
- `POST /api/v1/sandbox/snapshot`
- `GET /api/v1/sandbox/status`
- `POST /api/v1/snapshots`
- `POST /api/v1/snapshots/sync-current`
- `GET /api/v1/snapshots/status`
- `GET/PUT /api/v1/snapshots/config`

业务目标：

- 把当前最重的平台依赖从 Nuxt workflow 中剥离出来
- 让同步任务具备“可提交、可查询、可取消、可审计”的完整后端能力

交付物：

- Python 异步同步任务体系
- snapshot 与 sandbox 状态表
- source sync 不再依赖 Nuxt workflow 作为主执行器

### Step 6：迁移 Upload / Webhook / Bot，并收口 Auth

建议周期：`1 周`

关联工作模块：

- `domain/files`
- `integrations/github_bot`
- `integrations/discord_bot`
- `core/auth`

本 step 落地接口：

- `POST /api/v1/files/chat-attachments:sign-upload`
- `DELETE /api/v1/files/{pathname}`
- `POST /api/v1/webhooks/{platform}`
- `POST /api/v1/bots/discord/gateway:start`

业务目标：

- 完成对象存储、机器人入口、平台 webhook 的最终收口
- 清理 Nuxt server route 的残余业务职责
- 评估是否从 Better Auth 过渡到 Python 统一鉴权

交付物：

- 文件上传切为后端签名 + 前端直传
- Bot 与 Webhook 使用同一套 Python runtime
- `frontend/apps/app/server/api` 基本清空，仅保留必要 BFF 代理

## 16. 推荐排产与里程碑

按风险和收益排序，推荐这样拆里程碑：

1. 里程碑 M1：Step 1 完成，Python 骨架、OpenAPI、ORM、Auth bridge 全部就位
2. 里程碑 M2：Step 2 完成，管理后台、Sources、Agent Config、Stats 全部改走 Python
3. 里程碑 M3：Step 3 完成，聊天非流式能力全部迁移，TS 只剩 streaming 主链路
4. 里程碑 M4：Step 4 完成，聊天主链路切换到 FastAPI + LangGraph
5. 里程碑 M5：Step 5 完成，同步工作流、snapshot、sandbox 全部切到 Python
6. 里程碑 M6：Step 6 完成，上传、Webhook、Bot、Auth 收口，前后端分离基本闭环

如果要压缩首批上线范围，最小闭环建议只做到 `M2 + M3`：

- 管理后台先切 Python
- Sources 与 Agent Config 先切 Python
- 聊天列表/详情/分享/反馈先切 Python
- Chat Streaming、Sandbox、Sync 放到下一迭代

这样既能快速验证架构，又不会一开始就卡死在最重的 streaming 与 workflow 模块上。
