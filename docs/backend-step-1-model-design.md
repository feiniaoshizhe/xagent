# Backend Step 1 Model Design

## 1. 文档目标

这份文档聚焦 Step 1 的模型设计，不讨论排期，不展开前端页面改造细节，重点回答：

- Python 侧应该建哪些模型
- 数据库模型、DTO、服务对象如何分层
- `sources` 和 `agent-config` 的边界是什么
- 哪些信息在数据库，哪些在缓存，哪些在对象存储

## 2. 设计原则

Step 1 的模型设计遵循 6 个原则：

1. 先对齐现有 PostgreSQL schema，不先重构表结构
2. 数据库模型与 API DTO 分离
3. 业务语义进 service，不堆在 ORM model 上
4. `file source` 的文件内容不入库
5. `agent-config` 的默认值语义不依赖数据库单独承担
6. 为后续 chat、stats、sync 扩展保留空间

## 3. 模型分层

Step 1 建议明确分 4 层：

### 3.1 ORM 层

职责：

- 对应 PostgreSQL 表
- 提供 SQLAlchemy 映射

建议位置：

- `backend/app/db/models/`

### 3.2 DTO 层

职责：

- 对外 API 输入输出
- 与 ORM 解耦

建议位置：

- `backend/app/domain/sources/schemas.py`
- `backend/app/domain/agent_config/schemas.py`

### 3.3 Repository 层

职责：

- 数据库查询和写入
- 不承载默认值和业务规则

### 3.4 Service 层

职责：

- 处理默认值
- 类型校验
- 聚合返回
- 缓存处理
- 存储服务协调

## 4. Step 1 核心模型

Step 1 最少需要稳定建好两个核心业务模型：

- `Source`
- `AgentConfig`

同时建议补建后续会直接依赖的扩展模型：

- `Chat`
- `Message`
- `ApiUsage`
- `UsageStats`

## 5. `Source` 模型设计

## 5.1 业务定位

`Source` 表示“知识来源配置”，而不是同步后的文档内容。

它描述的是：

- 来源类型
- 来源定位参数
- 同步产物将被放到哪

它不负责保存：

- file source 的原始文件内容
- GitHub 拉下来的 markdown
- YouTube transcript

## 5.2 ORM 建议

建议模型名：

- `SourceModel`

建议枚举：

```python
class SourceType(str, Enum):
    GITHUB = "github"
    YOUTUBE = "youtube"
    FILE = "file"
```

建议字段：

```python
id: str
type: SourceType
label: str
base_path: str | None
repo: str | None
branch: str | None
content_path: str | None
output_path: str | None
readme_only: bool | None
channel_id: str | None
handle: str | None
max_videos: int | None
created_at: datetime
updated_at: datetime
```

## 5.3 字段语义

### `id`

- source 主键
- 当前 TS 侧使用 UUID 字符串

### `type`

- 来源类型
- 决定后续校验逻辑、同步方式和可用字段

### `label`

- 管理后台显示名称
- 用于用户识别 source

### `base_path`

- 同步到文档树时的根路径
- 当前典型值：
  - GitHub: `/docs`
  - YouTube: `/youtube`
  - File: `/files`

### `repo`

- GitHub 仓库标识
- 格式必须是 `owner/repo`

### `branch`

- GitHub 分支名
- 当前默认值为 `main`

### `content_path`

- GitHub 仓库内文档目录
- 例如 `docs`、`docs/content`

### `output_path`

- 同步产物最终落到的目录名
- 前端当前一般会基于 label 生成 slug 再提交

### `readme_only`

- GitHub 类型专用
- 为真时只抓 README

### `channel_id`

- YouTube 频道 ID
- 必须是 `UC...` 格式

### `handle`

- YouTube handle
- 示例：`@TheAlexLichter`

### `max_videos`

- YouTube 最多同步视频数
- 当前默认 50

## 5.4 类型相关约束

### GitHub source

要求：

- `repo` 必填
- `branch` 默认 `main`
- `base_path` 默认 `/docs`

可用字段：

- `repo`
- `branch`
- `content_path`
- `output_path`
- `readme_only`

### YouTube source

要求：

- `channel_id` 必填
- `max_videos` 默认 50
- `base_path` 默认 `/youtube`

可用字段：

- `channel_id`
- `handle`
- `max_videos`
- `output_path`

### File source

要求：

- `label` 必填
- `base_path` 默认 `/files`

注意：

- 文件内容不保存在 `SourceModel`

## 5.5 DTO 建议

建议 DTO 分成：

- `SourceItem`
- `CreateSourceRequest`
- `UpdateSourceRequest`
- `SourceListResponse`
- `SourceFileItem`

这样可以避免：

- ORM 字段名直接暴露到接口
- 不必要字段被外部更新

## 5.6 Repository 设计

建议 `SourceRepository` 提供：

- `list_all()`
- `get_by_id(source_id)`
- `create(source_data)`
- `update(source_id, patch_data)`
- `delete(source_id)`

Repository 不应负责：

- source 类型校验
- 文件上传限制
- grouped response 聚合

## 5.7 Service 设计

建议拆成两个 service：

### `SourceService`

职责：

- 创建和更新时做类型校验
- 补默认值
- 删除 source 时决定是否联动存储删除

### `SourceQueryService`

职责：

- 组装 `GET /sources` 响应
- 读取 `lastSyncAt`
- 读取 snapshot repo config
- 读取 feature flags

## 6. `Source` 附件存储设计

## 6.1 为什么不建 `source_files` 表

当前代码里，file source 的附件是存在对象存储中，而不是数据库里。

存储路径规则：

```text
sources/{sourceId}/{filename}
```

因此 Step 1 不建议马上引入 `source_files` 数据表。

原因：

- 当前事实来源是对象存储，不是数据库
- 立即双写数据库 + 存储会增加迁移复杂度
- Step 1 目标是先平移现有能力，而不是重构存储模型

## 6.2 存储层抽象

建议定义 `StorageService`：

```python
class StorageService:
    async def list_files(self, prefix: str) -> list[StoredFile]: ...
    async def put_file(self, path: str, content: bytes | str, content_type: str) -> None: ...
    async def delete_file(self, path: str) -> None: ...
    async def delete_prefix(self, prefix: str) -> None: ...
```

建议定义 `StoredFile`：

```python
class StoredFile(BaseModel):
    pathname: str
    filename: str
    size: int
    uploaded_at: datetime
```

## 6.3 Source 附件业务规则

上传规则：

- 只允许：
  - `.md`
  - `.mdx`
  - `.txt`
  - `.yml`
  - `.yaml`
  - `.json`
- 单文件上限 8MB

删除规则：

- `pathname` 必须属于该 source 的 prefix

## 7. `AgentConfig` 模型设计

## 7.1 业务定位

`AgentConfig` 表示系统当前激活的 Agent 行为配置。

它影响：

- 回复语言
- 回复风格
- 默认模型
- 最大步数倍率
- 温度
- 搜索偏好
- citation 格式

它的典型消费方：

- 管理后台
- 聊天 runtime
- bot / SDK

## 7.2 ORM 建议

建议模型名：

- `AgentConfigModel`

建议枚举：

```python
class ResponseStyle(str, Enum):
    CONCISE = "concise"
    DETAILED = "detailed"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"

class CitationFormat(str, Enum):
    INLINE = "inline"
    FOOTNOTE = "footnote"
    NONE = "none"
```

建议字段：

```python
id: str
name: str
additional_prompt: str | None
response_style: ResponseStyle | None
language: str | None
default_model: str | None
max_steps_multiplier: float | None
temperature: float | None
search_instructions: str | None
citation_format: CitationFormat | None
is_active: bool
created_at: datetime
updated_at: datetime
```

## 7.3 字段语义

### `name`

- 当前配置名字
- 当前代码默认使用 `default`

### `additional_prompt`

- 管理员附加给系统 prompt 的文本

### `response_style`

- 控制回答风格
- 当前取值：
  - `concise`
  - `detailed`
  - `technical`
  - `friendly`

### `language`

- 回复语言
- 当前典型值：`en`、`zh`

### `default_model`

- 指定默认模型
- `null` 表示让路由或 runtime 自动决定

### `max_steps_multiplier`

- 对 router 决定的步数做乘法修正
- 当前默认值 1.0

### `temperature`

- 模型温度
- 当前默认值 0.7

### `search_instructions`

- 搜索偏好或搜索规则补充

### `citation_format`

- 源引用展示方式
- 当前值：
  - `inline`
  - `footnote`
  - `none`

### `is_active`

- 是否当前激活配置
- 当前代码只取第一条 `is_active = true`

## 7.4 默认配置模型

这里需要两个概念分开：

- 数据库模型
- 默认业务配置

即使数据库中没有 active config，也必须返回默认配置对象。

建议在 service 层提供：

```python
DEFAULT_AGENT_CONFIG = {
    "id": "default",
    "name": "default",
    "additionalPrompt": None,
    "responseStyle": "concise",
    "language": "en",
    "defaultModel": None,
    "maxStepsMultiplier": 1.0,
    "temperature": 0.7,
    "searchInstructions": None,
    "citationFormat": "inline",
    "isActive": True,
}
```

## 7.5 DTO 建议

建议 DTO：

- `AgentConfigResponse`
- `UpdateAgentConfigRequest`

说明：

- 对外仍使用 camelCase
- controller 层不要直接返回 ORM model

## 7.6 Repository 设计

建议 `AgentConfigRepository` 提供：

- `get_active()`
- `create_active(data)`
- `update_active(config_id, patch_data)`

Repository 不应负责：

- 默认值兜底
- cache invalidate
- reset 逻辑

## 7.7 Service 设计

建议 `AgentConfigService` 提供：

- `get_active_or_default()`
- `update_active(request)`
- `reset_active()`
- `invalidate_cache()`

职责：

- 查 Redis 缓存
- 查 active config
- 无配置时生成默认值
- 更新或 reset 后删除缓存

## 8. `AgentConfig` 缓存设计

## 8.1 当前语义

当前前端实现使用 KV 缓存，语义如下：

- cache key: `agent:config-cache`
- TTL: 60 秒
- 命中则直接返回
- 更新和 reset 后清缓存

## 8.2 Python 侧建议

建议 Redis 中保持同一语义：

- key: `agent:config-cache`
- TTL: 60s

接口约定：

- `get_active_or_default()`
  - 先查缓存
  - 缓存 miss 再查 DB
  - 无 active config 返回默认配置
- `update_active()`
  - 成功后删缓存
- `reset_active()`
  - 成功后删缓存

## 9. 建议同步建模的扩展模型

## 9.1 `ChatModel`

建议字段：

```python
id: str
title: str | None
user_id: str
mode: str
is_public: bool
share_token: str | None
created_at: datetime
```

用途：

- 后续 chat list/detail
- share 能力

## 9.2 `MessageModel`

建议字段：

```python
id: str
chat_id: str
role: str
parts: dict | list | None
feedback: str | None
model: str | None
input_tokens: int | None
output_tokens: int | None
duration_ms: int | None
source: str | None
created_at: datetime
```

用途：

- 后续消息持久化
- stats 统计

## 9.3 `ApiUsageModel`

建议字段：

```python
id: str
source: str
source_id: str | None
model: str | None
input_tokens: int | None
output_tokens: int | None
duration_ms: int | None
metadata: dict | None
created_at: datetime
```

用途：

- SDK / bot 统计

## 9.4 `UsageStatsModel`

建议字段：

```python
id: str
date: str
user_id: str | None
source: str
model: str
message_count: int
total_input_tokens: int
total_output_tokens: int
total_duration_ms: int
created_at: datetime
```

用途：

- 每日聚合统计

## 10. 命名规范建议

建议统一：

### ORM / Python 属性

- snake_case

例如：

- `base_path`
- `updated_at`
- `max_steps_multiplier`

### API DTO 字段

- camelCase

例如：

- `basePath`
- `updatedAt`
- `maxStepsMultiplier`

### 路由命名

- kebab-case 或资源风格

例如：

- `/api/v1/agent-config`
- `/api/v1/sources/{id}/files`

## 11. Step 1 模型边界总结

可以这样理解 Step 1 的模型边界：

- `SourceModel`
  - 管“来源元数据”
- `StorageService`
  - 管“file source 附件对象”
- `AgentConfigModel`
  - 管“系统当前激活配置”
- `Redis`
  - 管“agent config 短期缓存”
- `SourceQueryService`
  - 管“sources 聚合视图”

这几个边界如果先立住，后面接 chat、sync、sandbox 时不会再把模型职责搅混。

## 12. 最终结论

Step 1 的模型设计本质上是在做三件事：

1. 把前端 TS 表结构翻译成 Python ORM
2. 把数据库、缓存、对象存储的职责边界拆清
3. 把“当前能跑”设计成“后续还能扩”

如果这一步的模型层设计清晰，后面的 API、service、前端联调都会轻很多；如果这一步偷懒，后面每迁一个模块都会返工一次。
