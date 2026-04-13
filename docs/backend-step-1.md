# Backend Step 1

## 1. Step 1 的定位

`frontend-backend-separation-plan.md` 已经说明，后端迁移不能从最复杂的 Chat Streaming、LangGraph runtime、Sandbox、Sync、Auth 统一开始，而要先做一个最小可验证闭环。

对当前仓库来说，Step 1 的目标不是“把所有接口搬到 Python”，而是先完成下面这 4 件事：

1. 在现有 `backend/` FastAPI 模板骨架上建立真实业务边界
2. 把前端 TS 侧核心数据模型映射到 Python ORM
3. 先迁移 `sources` 和 `agent-config` 两组接口
4. 让前端至少有一批页面改为直接消费 Python API

一句话概括：

先把 `backend/` 从“模板工程”升级成“能够接住第一批真实业务”的 Python 基座。

## 2. Step 1 为什么只做 `sources` 和 `agent-config`

这两个模块适合作为第一步，原因很明确：

- 都是标准 CRUD / 配置型接口
- 不依赖流式协议
- 不依赖 `@savoir/agent` 到 `LangGraph` 的执行语义迁移
- 能直接服务现有管理后台页面
- 能验证 ORM、DTO、权限校验、缓存、前端 SDK 调用链是否成立

反过来看，第一步明确不做：

- 不做 Chat Streaming 迁移
- 不做 LangGraph runtime
- 不做 Sandbox API 全量迁移
- 不做 Sync Workflow 迁移
- 不做 Upload / Bot / Webhook 全量迁移
- 不做 Auth 统一重构

## 3. 当前仓库事实

### 3.1 现有 backend 不是空目录

当前 `backend/` 已经有 FastAPI 模板骨架，包含：

- `backend/app/web/api` 路由体系
- `backend/app/db/models`、`backend/app/db/migrations`
- `backend/app/settings.py`
- Redis、RabbitMQ、monitoring 等模板能力

因此 Step 1 不是新建一个全新工程，而是：

- 复用现有 FastAPI 启动、配置、迁移、测试基础设施
- 在此之上补齐业务域结构
- 让第一批真实业务开始落在 Python 侧

### 3.2 Step 1 对应的现有前端服务端代码

Step 1 直接涉及的现有 Nuxt server 代码是：

- 数据模型
  - `frontend/apps/app/server/db/schema.ts`
- Sources 接口
  - `frontend/apps/app/server/api/sources/index.get.ts`
  - `frontend/apps/app/server/api/sources/index.post.ts`
  - `frontend/apps/app/server/api/sources/[id].put.ts`
  - `frontend/apps/app/server/api/sources/[id].delete.ts`
  - `frontend/apps/app/server/api/sources/[id]/files.get.ts`
  - `frontend/apps/app/server/api/sources/[id]/files.put.ts`
  - `frontend/apps/app/server/api/sources/[id]/files.delete.ts`
  - `frontend/apps/app/server/api/sources/ocr.post.ts`
- Agent Config 接口
  - `frontend/apps/app/server/api/agent-config/index.get.ts`
  - `frontend/apps/app/server/api/agent-config/index.put.ts`
  - `frontend/apps/app/server/api/agent-config/public.get.ts`
  - `frontend/apps/app/server/api/agent-config/reset.post.ts`
- 相关业务辅助逻辑
  - `frontend/apps/app/server/utils/agent-config.ts`
  - `frontend/apps/app/server/utils/admin.ts`
  - `frontend/apps/app/server/utils/sandbox/snapshot-config.ts`
  - `frontend/apps/app/server/utils/sandbox/types.ts`

## 4. Step 1 需要建立的 backend 目录

建议在当前 `backend/app` 结构上做增量式落地：

```text
backend/app/
├─ core/
│  ├─ auth/
│  ├─ cache/
│  └─ config/
├─ domain/
│  ├─ sources/
│  │  ├─ schemas.py
│  │  ├─ service.py
│  │  └─ repository.py
│  ├─ agent_config/
│  │  ├─ schemas.py
│  │  ├─ service.py
│  │  └─ repository.py
│  ├─ chats/
│  └─ agents/
├─ web/
│  └─ api/
│     ├─ router.py
│     └─ v1/
│        ├─ sources/
│        │  └─ views.py
│        └─ agent_config/
│           └─ views.py
├─ db/
│  ├─ models/
│  └─ migrations/
└─ services/
   ├─ redis/
   ├─ rabbit/
   └─ storage/
```

原则只有两个：

- 新业务一律走新结构
- 老模板能力先复用，不在 Step 1 做大规模清理

## 5. 数据模型迁移规格

Step 1 必须把前端 `schema.ts` 中与后续迁移直接相关的核心表，在 Python 侧建立清晰的 ORM 映射。即使第一步只先落 `sources` 和 `agent_config`，也要把相关表的含义和边界写清楚。

## 5.1 总体迁移原则

- 数据库先继续复用现有 PostgreSQL
- 不在 Step 1 先做结构重设计
- 优先保证 Python ORM 与现有表结构对齐
- 所有后续 schema 变更统一走 Alembic
- `file` 类型 source 的文件内容不在 `sources` 表里，而是在对象存储里
- `agent-config` 当前存在 KV 缓存语义，Python 侧也要保留

## 5.2 表：`sources`

### 表含义

`sources` 表表示“知识来源配置”，而不是同步产物本身。

它描述的是：

- 要同步哪类来源
- 来源的定位信息
- 同步后内容应该落到 snapshot / docs 树中的哪个路径

它不保存：

- file source 的文件内容
- GitHub 拉取下来的文档内容
- YouTube transcript 结果

这些都属于运行态或存储层，不属于 `sources` 主表。

### 当前字段定义与语义

| 字段             | 类型               | 含义                                                           |
| -------------- | ---------------- | ------------------------------------------------------------ |
| `id`           | text PK          | source 唯一标识，UUID                                             |
| `type`         | enum text        | 来源类型，当前为 `github` / `youtube` / `file`                       |
| `label`        | text             | 管理后台显示名，也是用户理解该来源的名称                                         |
| `base_path`    | text             | 同步产物根目录，当前默认 GitHub `/docs`，YouTube `/youtube`，File `/files` |
| `repo`         | text nullable    | GitHub 仓库名，格式 `owner/repo`                                   |
| `branch`       | text nullable    | GitHub 分支，默认 `main`                                          |
| `content_path` | text nullable    | GitHub 仓库内部文档目录，如 `docs`、`docs/content`                      |
| `output_path`  | text nullable    | 最终同步到 snapshot/docs 的子目录名                                    |
| `readme_only`  | boolean nullable | GitHub 模式下是否只同步 README                                       |
| `channel_id`   | text nullable    | YouTube 频道 ID，格式 `UC...`                                     |
| `handle`       | text nullable    | YouTube 频道 handle，例如 `@xxx`                                  |
| `max_videos`   | integer nullable | YouTube 最大同步视频数，默认 50                                        |
| `created_at`   | timestamp        | 创建时间                                                         |
| `updated_at`   | timestamp        | 更新时间                                                         |

### 业务约束

- `type=github` 时，`repo` 应有值，`branch` 默认 `main`
- `type=youtube` 时，`channel_id` 应有值，`max_videos` 默认 50
- `type=file` 时，主表仅保存元数据；文件内容通过对象存储按 `sources/{id}/{filename}` 管理
- `output_path` 为空时，前端当前会基于 `label` 生成 slug 后提交，因此 Python 侧可以要求显式传值，也可以保留兼容兜底

### Python 模型建议

Python 侧建议定义：

- `SourceType` 枚举
  - `github`
  - `youtube`
  - `file`
- `Source` ORM model

字段命名建议：

- ORM 属性使用 Python 风格，例如 `base_path`、`content_path`
- Pydantic DTO 对外 JSON 字段保持与当前前端一致的 camelCase，避免前端联调再改一轮

### 与现有 TS model 的对应关系

| TS 字段         | Python ORM 字段  | API DTO 字段     |
| ------------- | -------------- | -------------- |
| `id`          | `id`           | `id`           |
| `type`        | `type`         | `type`         |
| `label`       | `label`        | `label`        |
| `basePath`    | `base_path`    | `base_path`    |
| `repo`        | `repo`         | `repo`         |
| `branch`      | `branch`       | `branch`       |
| `contentPath` | `content_path` | `content_path` |
| `outputPath`  | `output_path`  | `output_path`  |
| `readmeOnly`  | `readme_only`  | `readme_only`  |
| `channelId`   | `channel_id`   | `channel_id`   |
| `handle`      | `handle`       | `handle`       |
| `maxVideos`   | `max_videos`   | `max_videos`   |
| `createdAt`   | `created_at`   | `created_at`   |
| `updatedAt`   | `updated_at`   | `updated_at`   |

## 5.3 表：`agent_config`

### 表含义

`agent_config` 表表示“管理员定义的当前 Agent 行为配置”，它影响：

- 默认语言
- 默认模型
- 回复风格
- 搜索指令
- citation 格式
- 推理步数倍率

它不是用户级配置，也不是一次会话临时参数，而是当前系统级生效配置。

### 当前字段定义与语义

| 字段                     | 类型            | 含义                                                     |
| ---------------------- | ------------- | ------------------------------------------------------ |
| `id`                   | text PK       | 配置主键，UUID                                              |
| `name`                 | text          | 配置名，当前默认 `default`                                     |
| `additional_prompt`    | text nullable | 追加系统提示词                                                |
| `response_style`       | enum text     | 回复风格：`concise` / `detailed` / `technical` / `friendly` |
| `language`             | text          | 回复语言，如 `en`、`zh`                                       |
| `default_model`        | text nullable | 默认模型，空表示自动                                             |
| `max_steps_multiplier` | float         | 路由层步数倍率，当前默认 1.0                                       |
| `temperature`          | float         | 模型温度，默认 0.7                                            |
| `search_instructions`  | text nullable | 搜索偏好或检索约束                                              |
| `citation_format`      | enum text     | 引用格式：`inline` / `footnote` / `none`                    |
| `is_active`            | boolean       | 是否当前激活配置                                               |
| `created_at`           | timestamp     | 创建时间                                                   |
| `updated_at`           | timestamp     | 更新时间                                                   |

### 当前业务语义

- 当前代码只读取 `is_active = true` 的那一条配置
- 如果数据库没有配置，服务会返回内置默认值，而不是报错
- 当前存在 KV 缓存，键为 `agent:config-cache`
- 更新和重置配置后，会主动清缓存

### 默认值语义

当前默认配置等价于：

```json
{
  "id": "default",
  "name": "default",
  "additionalPrompt": null,
  "responseStyle": "concise",
  "language": "en",
  "defaultModel": null,
  "maxStepsMultiplier": 1.0,
  "temperature": 0.7,
  "searchInstructions": null,
  "citationFormat": "inline",
  "isActive": true
}
```

Python 侧必须保留这个“无数据时返回默认配置”的行为，否则会破坏现有前端和 SDK。

### 与现有 TS model 的对应关系

| TS 字段                | Python ORM 字段          | API DTO 字段             |
| -------------------- | ---------------------- | ---------------------- |
| `id`                 | `id`                   | `id`                   |
| `name`               | `name`                 | `name`                 |
| `additionalPrompt`   | `additional_prompt`    | `additional_prompt`    |
| `responseStyle`      | `response_style`       | `response_style`       |
| `language`           | `language`             | `language`             |
| `defaultModel`       | `default_model`        | `default_model`        |
| `maxStepsMultiplier` | `max_steps_multiplier` | `max_steps_multiplier` |
| `temperature`        | `temperature`          | `temperature`          |
| `searchInstructions` | `search_instructions`  | `search_instructions`  |
| `citationFormat`     | `citation_format`      | `citation_format`      |
| `isActive`           | `is_active`            | `is_active`            |
| `createdAt`          | `created_at`           | `created_at`           |
| `updatedAt`          | `updated_at`           | `updated_at`           |

## 5.4 Step 1 建议同步建模但可以暂不开放接口的表

虽然 Step 1 的接口只先迁 `sources` 和 `agent-config`，但建议同步把下列表在 Python ORM 侧至少建立模型，以减少后续返工：

### `chats`

表含义：

- 聊天会话元数据
- 是否公开分享
- 当前模式是 `chat` 还是 `admin`

关键字段：

- `id`
- `title`
- `user_id`
- `mode`
- `is_public`
- `share_token`
- `created_at`

### `messages`

表含义：

- 单条消息内容
- assistant 消息的模型统计信息

关键字段：

- `id`
- `chat_id`
- `role`
- `parts`
- `feedback`
- `model`
- `input_tokens`
- `output_tokens`
- `duration_ms`
- `source`
- `created_at`

### `api_usage`

表含义：

- 外部入口或 SDK 的调用计费/使用统计

### `usage_stats`

表含义：

- 按日期、用户、来源、模型聚合后的用量统计

这些表不是 Step 1 的接口重点，但最好在 Python ORM 中有定义，否则后面做 `stats`、`chat` 时还要回头补模型。

## 6. 存储与缓存迁移要求

## 6.1 `file` 类型 source 的文件存储

当前实现中，`file` 类型 source 的文件不在数据库里，而在对象存储中：

- 上传路径：`sources/{sourceId}/{filename}`
- 列表接口通过对象存储 prefix 枚举
- 删除 source 时，会同步清理该 prefix 下文件
- 全量 sync 或单 source sync 后，这批 blob 可能会被清理

这意味着 Python 侧不要把 `files` 误建成 `sources` 表里的 JSON 字段。

Step 1 对存储层的正确抽象应该是：

- `Source` 管理来源元数据
- `StorageService` 管理 file source 附件对象

建议最小接口：

- `list_files(source_id)`
- `put_file(source_id, filename, content, content_type)`
- `delete_file(pathname)`
- `delete_prefix(prefix)`

## 6.2 `agent-config` 缓存

当前缓存键：

- `agent:config-cache`

当前行为：

- 读取 active config 前先查 KV
- 更新配置或 reset 后主动清除缓存
- 默认 TTL 为 60 秒

Python 侧建议保留同等行为：

- `get_active_agent_config()` 先查 Redis
- `update_active_agent_config()` / `reset_agent_config()` 后删缓存
- 没有 active config 时返回默认值

## 6.3 `sources` 页面依赖的额外状态

`GET /api/sources` 当前不仅返回 sources 列表，还拼了两类额外状态：

- `lastSyncAt`
  - 读取 KV：`sources:last-sync`
- snapshot repo 配置
  - `snapshotRepo`
  - `snapshotBranch`
  - `snapshotRepoUrl`

这说明 `sources` 列表接口不是简单查表接口，而是“来源配置 + 同步状态 + 仓库配置”的聚合查询。

Python 侧需要决定：

- 要么 Step 1 完整兼容这个聚合返回
- 要么拆成多个接口，同时改前端页面

如果要降低前端改造成本，Step 1 更适合先兼容原聚合返回。

## 7. Step 1 需要迁移的接口清单

Step 1 应迁移的接口，不仅要列 URL，还要明确谁在调用、做了什么业务逻辑、Python 侧怎么落。

## 7.1 Sources 接口

### 1. `GET /api/sources`

当前文件：

- `frontend/apps/app/server/api/sources/index.get.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/index.vue`
- `frontend/apps/app/app/pages/admin/new.vue`

当前业务逻辑：

- 查询 `sources` 表所有记录，按 `label` 排序
- 读取 `KV_KEYS.LAST_SOURCE_SYNC`
- 读取 snapshot repo 配置
- 判断当前环境是否启用了 YouTube API key
- 按 `github` / `youtube` / `file` 分组返回
- 构造 `snapshotRepoUrl`

当前返回结构：

```ts
{
  total,
  lastSyncAt,
  youtubeEnabled,
  snapshotRepo,
  snapshotBranch,
  snapshotRepoUrl,
  github: { count, sources },
  youtube: { count, sources },
  file: { count, sources }
}
```

Python 迁移建议：

- 新接口：`GET /api/v1/sources`
- 保持当前分组返回结构，减少前端改动
- 在 service 层聚合：
  - `SourceRepository.list_all()`
  - `SyncStateService.get_last_sync_at()`
  - `SnapshotConfigService.get_snapshot_repo_config()`
  - `FeatureFlagService.is_youtube_enabled()`

### 2. `POST /api/sources`

当前文件：

- `frontend/apps/app/server/api/sources/index.post.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/new.vue`
- `frontend/apps/app/app/components/SourceModal.vue`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 校验 body
- 插入 `sources` 表
- 写入 `createdAt` / `updatedAt`
- 直接返回插入后的 source

当前 body 允许字段：

- `type`
- `label`
- `basePath`
- `repo`
- `branch`
- `contentPath`
- `outputPath`
- `readmeOnly`
- `channelId`
- `handle`
- `maxVideos`

Python 迁移建议：

- 新接口：`POST /api/v1/sources`
- 建 `CreateSourceRequest`
- service 层做类型相关校验
  - GitHub 校验 `repo`
  - YouTube 校验 `channelId`
  - file 类型至少要求 `label`

### 3. `PUT /api/sources/{id}`

当前文件：

- `frontend/apps/app/server/api/sources/[id].put.ts`

当前调用方：

- `frontend/apps/app/app/components/SourceModal.vue`

当前权限：

- 当前代码没有 `requireAdmin`

这个现状有问题。它和新增、删除、文件操作的权限模型不一致。Step 1 迁移时应显式修正，不要把这个漏洞原样搬过去。

当前业务逻辑：

- 按 ID 更新 `sources`
- 更新 `updatedAt`
- 未找到返回 404

Python 迁移建议：

- 新接口：`PUT /api/v1/sources/{id}`
- 权限应统一为 admin
- 只允许更新白名单字段
- 如果 source 不存在，返回 404

### 4. `DELETE /api/sources/{id}`

当前文件：

- `frontend/apps/app/server/api/sources/[id].delete.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/index.vue`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 删除 `sources` 表记录
- 若为 `file` 类型，删除对象存储 `sources/{id}/` 前缀下所有文件
- 返回 `{ success: true }`

Python 迁移建议：

- 新接口：`DELETE /api/v1/sources/{id}`
- service 层执行：
  - `delete_source(id)`
  - 若 `type=file`，调用 `StorageService.delete_prefix()`

### 5. `GET /api/sources/{id}/files`

当前文件：

- `frontend/apps/app/server/api/sources/[id]/files.get.ts`

当前调用方：

- 编辑 file source 时的弹层逻辑

当前权限：

- `requireAdmin`

当前业务逻辑：

- 查询 source 是否存在
- 必须要求 `type=file`
- 列出对象存储中 `sources/{id}/` 下文件
- 返回：

```ts
{
  files: [
    {
      pathname,
      filename,
      size,
      uploadedAt
    }
  ]
}
```

Python 迁移建议：

- 新接口：`GET /api/v1/sources/{id}/files`
- 这不是数据库查询，而是 source 元数据校验后再查存储

### 6. `PUT /api/sources/{id}/files`

当前文件：

- `frontend/apps/app/server/api/sources/[id]/files.put.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/new.vue`
- `frontend/apps/app/app/components/SourceModal.vue`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 校验 source 存在
- 校验 `type=file`
- 接收 multipart form-data
- 只允许后缀：
  - `.md`
  - `.mdx`
  - `.txt`
  - `.yml`
  - `.yaml`
  - `.json`
- 单文件上限 8MB
- 写入对象存储路径 `sources/{id}/{filename}`
- 返回每个文件的成功或失败信息

Python 迁移建议：

- 新接口：`PUT /api/v1/sources/{id}/files`
- 暂时兼容现有 multipart 上传
- 后续再考虑升级成签名上传 URL

### 7. `DELETE /api/sources/{id}/files`

当前文件：

- `frontend/apps/app/server/api/sources/[id]/files.delete.ts`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 校验 source 存在且为 `file`
- body 中接收 `pathname`
- 校验路径前缀必须属于 `sources/{id}/`
- 删除对象存储中的该文件
- 返回 `{ success: true }`

Python 迁移建议：

- 新接口：`DELETE /api/v1/sources/{id}/files`
- body 保持兼容：`{ pathname: string }`

### 8. `POST /api/sources/ocr`

当前文件：

- `frontend/apps/app/server/api/sources/ocr.post.ts`

说明：

这个接口与 `sources` 管理相关，但不属于 Step 1 必须迁移范围。

原因：

- 它依赖 AI 模型调用
- 主要是导入辅助能力，不是主数据闭环
- 即使暂时不迁，也不阻塞 `sources` CRUD 的 Python 化

建议：

- Step 1 可暂留在 Nuxt
- 文档中标为“非阻塞、可后移”

## 7.2 Agent Config 接口

### 1. `GET /api/agent-config`

当前文件：

- `frontend/apps/app/server/api/agent-config/index.get.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/agent.vue`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 获取当前 active config
- 若缓存命中，直接返回缓存
- 若 DB 无 active config，返回默认配置

Python 迁移建议：

- 新接口：`GET /api/v1/agent-config`
- 行为必须保持兼容：
  - 优先返回 active config
  - 无数据时返回默认值
  - 可使用 Redis 做短 TTL 缓存

### 2. `PUT /api/agent-config`

当前文件：

- `frontend/apps/app/server/api/agent-config/index.put.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/agent.vue`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 读取当前 active config
- 如果存在则更新
- 如果不存在则创建一条默认名为 `default` 的 active config
- 写入 `updatedAt`
- 清理配置缓存
- 返回最新配置

当前允许更新字段：

- `additionalPrompt`
- `responseStyle`
- `language`
- `defaultModel`
- `maxStepsMultiplier`
- `temperature`
- `searchInstructions`
- `citationFormat`

Python 迁移建议：

- 新接口：`PUT /api/v1/agent-config`
- service 语义应保持为 upsert active config

### 3. `GET /api/agent-config/public`

当前文件：

- `frontend/apps/app/server/api/agent-config/public.get.ts`

当前调用方：

- SDK
- 外部 bot / 集成调用链

当前权限：

- `requireUserSession`

现有注释写的是“protected by API key via middleware”，但当前文件本身实际调用的是 `requireUserSession(event)`。这意味着现状和注释并不完全一致，迁移时不要照搬注释，要以真实认证链路为准。

当前业务逻辑：

- 返回当前 active config
- 若无 active config，返回默认值

Python 迁移建议：

- Step 1 可以先保留兼容接口：`GET /api/v1/agent-config/public`
- 具体认证方式在 Step 1 保守处理：
  - Web 先支持已有登录态透传
  - 外部 SDK/API key 兼容可以作为 Step 1.5 或 Step 2 处理

### 4. `POST /api/agent-config/reset`

当前文件：

- `frontend/apps/app/server/api/agent-config/reset.post.ts`

当前调用方：

- `frontend/apps/app/app/pages/admin/agent.vue`

当前权限：

- `requireAdmin`

当前业务逻辑：

- 取默认配置
- 若已有 active config，则重置字段到默认值
- 若无 active config，则创建一条默认配置
- 清缓存
- 返回重置后的配置

Python 迁移建议：

- 新接口：`POST /api/v1/agent-config/reset`
- 保持幂等

## 8. Step 1 的接口映射建议

为减少前端改造成本，推荐先保持“旧接口语义兼容，新接口命名规范化”。

| 当前接口                             | Python 新接口                          | Step 1 是否必须 |
| -------------------------------- | ----------------------------------- | ----------- |
| `GET /api/sources`               | `GET /api/v1/sources`               | 是           |
| `POST /api/sources`              | `POST /api/v1/sources`              | 是           |
| `PUT /api/sources/{id}`          | `PUT /api/v1/sources/{id}`          | 是           |
| `DELETE /api/sources/{id}`       | `DELETE /api/v1/sources/{id}`       | 是           |
| `GET /api/sources/{id}/files`    | `GET /api/v1/sources/{id}/files`    | 是           |
| `PUT /api/sources/{id}/files`    | `PUT /api/v1/sources/{id}/files`    | 是           |
| `DELETE /api/sources/{id}/files` | `DELETE /api/v1/sources/{id}/files` | 是           |
| `POST /api/sources/ocr`          | 暂不迁移或后续 `POST /api/v1/sources/ocr`  | 否           |
| `GET /api/agent-config`          | `GET /api/v1/agent-config`          | 是           |
| `PUT /api/agent-config`          | `PUT /api/v1/agent-config`          | 是           |
| `GET /api/agent-config/public`   | `GET /api/v1/agent-config/public`   | 建议保留        |
| `POST /api/agent-config/reset`   | `POST /api/v1/agent-config/reset`   | 是           |

## 9. Step 1 的业务逻辑拆分建议

为了避免把 Nuxt 的 route handler 直接翻译成 Python controller，Step 1 应当显式做服务分层。

## 9.1 Sources

建议拆成：

- `SourceRepository`
  - 负责数据库读写
- `SourceService`
  - 负责 source 类型校验
  - 负责 create / update / delete 业务规则
- `SourceFileService`
  - 负责 file source 的对象存储操作
- `SourceQueryService`
  - 负责 `GET /sources` 聚合返回

## 9.2 Agent Config

建议拆成：

- `AgentConfigRepository`
  - 查询 active config
  - upsert active config
- `AgentConfigService`
  - 负责默认配置逻辑
  - 负责 reset 逻辑
  - 负责 cache invalidate

## 9.3 权限

当前权限语义需要抽成 Python 依赖项，而不是散落在 controller 里：

- `require_admin`
  - 对应 Nuxt `requireAdmin`
- `require_authenticated_user`
  - 对应 `requireUserSession`

注意一点：

当前 `PUT /api/sources/{id}` 没有做 admin 校验，这应视为现状缺陷，不应在 Python 侧延续。

## 10. Step 1 的前端联调要求

Step 1 不仅要求 Python API 存在，还要求前端至少完成最小闭环。

## 10.1 优先改造页面

优先改造：

- `frontend/apps/app/app/pages/admin/index.vue`
- `frontend/apps/app/app/pages/admin/new.vue`
- `frontend/apps/app/app/pages/admin/agent.vue`
- `frontend/apps/app/app/components/SourceModal.vue`

## 10.2 最小兼容要求

如果前端不想在 Step 1 大改页面逻辑，Python API 应尽量兼容现有返回：

- `GET /sources` 保持 grouped response
- `GET /agent-config` 保持单对象返回
- `PUT /agent-config` 仍是“更新 active config”，不是要求传 config id
- `reset` 仍是单独动作接口

## 10.3 `web-sdk` 最小范围

Step 1 中 `frontend/packages/web-sdk` 至少封装：

- `getSources()`
- `createSource()`
- `updateSource()`
- `deleteSource()`
- `listSourceFiles()`
- `uploadSourceFiles()`
- `deleteSourceFile()`
- `getAgentConfig()`
- `updateAgentConfig()`
- `resetAgentConfig()`

## 11. Alembic 与迁移策略

Step 1 必须定下 schema 演进方式，否则很快会返工。

建议流程：

1. 以当前 PostgreSQL 结构为准
2. 在 Python ORM 中对齐建模
3. 生成一版 baseline migration 或手工对齐迁移
4. 后续所有字段变更只走 Alembic

特别注意：

- `sources`、`agent_config` 优先保证字段对齐
- `file source` 的文件内容不要尝试迁入数据库
- `agent_config` 的默认值逻辑属于 service 层，不是数据库层单独承担

## 12. Step 1 完成标准

满足下面条件，Step 1 才算完成：

1. Python 侧存在业务化目录，而不再只是模板结构
2. `sources`、`agent_config` 的 ORM model 已建立
3. 字段映射、默认值、缓存与存储语义已明确落地
4. `/api/v1/sources` 及其 files 子接口可用
5. `/api/v1/agent-config`、`/reset`、`/public` 可用
6. 前端管理页至少有一部分已切到 Python API
7. 旧 Nuxt server route 不再是这两组能力的唯一业务真相来源

如果只是创建了目录，或者只写了 ORM 没有联调，都不算完成。

## 13. Step 1 的最终结论

backend 的第一步，本质上是把现有前端单体里的两块“最容易平移的业务”拆出来，建立第一条真实可运行的前后端分离链路。

这一步真正要证明的是三件事：

- Python 侧已经能承接真实数据模型
- Python 侧已经能表达真实业务逻辑，而不是只做 controller 转发
- 前端已经能开始绕过 Nuxt server route，直接消费 Python API

因此 Step 1 最合理的执行顺序是：

1. 建业务目录骨架
2. 建 `sources` / `agent_config` ORM model
3. 明确字段映射、缓存、对象存储边界
4. 落地接口与 service
5. 前端通过 `web-sdk` 接入

只要这一步打稳，后续再迁 chat、streaming、LangGraph、sandbox、sync，成本才是可控的。
