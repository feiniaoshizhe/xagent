# Backend Step 1 Tasklist

## 1. 文档目标

这份文档把 [backend-step-1.md](/C:/__JOB__/__CODEX__/xagent/docs/backend-step-1.md) 拆成可执行任务清单，用于：

- 排期
- 分工
- 跟踪完成状态
- 控制 Step 1 范围

Step 1 只解决两类业务：

- `sources`
- `agent-config`

同时补齐：

- Python ORM 对齐
- `/api/v1` 路由体系
- 前端最小联调闭环

## 2. 里程碑

Step 1 建议拆成 5 个里程碑：

1. 业务骨架完成
2. 数据模型完成
3. API 完成
4. 前端接入完成
5. 联调与验收完成

## 3. 任务清单

## 3.1 M1: 业务骨架

### T1. 建立 Step 1 目录骨架

目标：

- 在 `backend/app` 下建立业务目录，不再只依赖模板目录

建议产出：

- `backend/app/core/`
- `backend/app/domain/sources/`
- `backend/app/domain/agent_config/`
- `backend/app/web/api/v1/`
- `backend/app/web/api/v1/sources/`
- `backend/app/web/api/v1/agent_config/`
- `backend/app/services/storage/`

完成标准：

- 目录已存在
- 有基础 `__init__.py`
- 新业务明确归属到新目录

### T2. 建立 `/api/v1` 主路由

目标：

- 后续 Step 1 的 Python 接口全部挂到 `/api/v1`

建议产出：

- `backend/app/web/api/router.py` 接入 `v1`
- `backend/app/web/api/v1/router.py`

完成标准：

- FastAPI 中存在 `/api/v1`
- 后续新接口可从统一命名空间暴露

### T3. 建立通用依赖与基础能力

目标：

- 提前准备后续业务公共依赖

建议产出：

- `require_admin`
- `require_authenticated_user`
- cache helper
- storage service interface

完成标准：

- 控制器层不直接写散落权限判断
- 存储访问不直接散落在业务 handler 中

## 3.2 M2: 数据模型

### T4. 对齐 `sources` ORM model

目标：

- 在 Python 侧建立 `sources` 的 SQLAlchemy model

字段范围：

- `id`
- `type`
- `label`
- `base_path`
- `repo`
- `branch`
- `content_path`
- `output_path`
- `readme_only`
- `channel_id`
- `handle`
- `max_videos`
- `created_at`
- `updated_at`

完成标准：

- 字段与现有 PG schema 对齐
- 有 `SourceType` 枚举

### T5. 对齐 `agent_config` ORM model

目标：

- 在 Python 侧建立 `agent_config` 的 SQLAlchemy model

字段范围：

- `id`
- `name`
- `additional_prompt`
- `response_style`
- `language`
- `default_model`
- `max_steps_multiplier`
- `temperature`
- `search_instructions`
- `citation_format`
- `is_active`
- `created_at`
- `updated_at`

完成标准：

- 字段与现有 PG schema 对齐
- 默认值和 nullable 语义明确

### T6. 建立建议同步建模的非 Step 1 主接口表

目标：

- 预留后续 chat/stats 迁移的模型基础

建议产出：

- `chats`
- `messages`
- `api_usage`
- `usage_stats`

完成标准：

- ORM 已建
- 即使接口暂未暴露，也可供后续阶段复用

### T7. 定义 Alembic baseline 策略

目标：

- 明确 Python 侧 schema 演进方式

建议产出：

- baseline migration 方案
- 迁移说明

完成标准：

- 确认继续复用 PostgreSQL
- 新增字段和新表以后只走 Alembic

## 3.3 M3: Sources API

### T8. 定义 `sources` Pydantic DTO

目标：

- 把数据库模型和对外 JSON 合同拆开

建议产出：

- `SourceItem`
- `CreateSourceRequest`
- `UpdateSourceRequest`
- `SourceFileItem`
- `SourceListResponse`
- `DeleteSuccessResponse`

完成标准：

- DTO 与前端现有字段命名兼容
- 不把 ORM model 直接暴露给 API

### T9. 实现 `SourceRepository`

目标：

- 收口 DB 读写

建议方法：

- `list_all()`
- `get_by_id(id)`
- `create(data)`
- `update(id, data)`
- `delete(id)`

完成标准：

- controller 不再直接操作 session

### T10. 实现 `SourceFileService`

目标：

- 收口 file source 对象存储逻辑

建议方法：

- `list_files(source_id)`
- `upload_files(source_id, files)`
- `delete_file(source_id, pathname)`
- `delete_source_prefix(source_id)`

完成标准：

- 文件读写逻辑不散落在 API 层

### T11. 实现 `SourceQueryService`

目标：

- 兼容现有 `GET /api/sources` 的聚合返回

需要聚合：

- `sources` DB 数据
- `lastSyncAt`
- `snapshotRepo`
- `snapshotBranch`
- `snapshotRepoUrl`
- `youtubeEnabled`

完成标准：

- 输出结构兼容前端 `admin/index.vue`

### T12. 实现 `GET /api/v1/sources`

目标：

- 迁移现有 sources 列表接口

完成标准：

- 返回 grouped response
- 前端管理页可直接消费

### T13. 实现 `POST /api/v1/sources`

目标：

- 支持创建 source

完成标准：

- admin 权限校验生效
- GitHub / YouTube / file 类型校验到位

### T14. 实现 `PUT /api/v1/sources/{id}`

目标：

- 支持更新 source

注意：

- 权限应为 admin
- 不继承前端现有漏校验问题

完成标准：

- 白名单字段更新
- 404 语义明确

### T15. 实现 `DELETE /api/v1/sources/{id}`

目标：

- 删除 source 及 file source 关联存储内容

完成标准：

- 删除 DB 记录
- file source 删除对象存储 prefix

### T16. 实现 `GET /api/v1/sources/{id}/files`

目标：

- 列出 file source 的附件

完成标准：

- 非 file source 返回 400
- 不存在 source 返回 404

### T17. 实现 `PUT /api/v1/sources/{id}/files`

目标：

- 支持 multipart 上传

完成标准：

- 后缀校验
- 单文件 8MB 限制
- 路径写入 `sources/{id}/{filename}`

### T18. 实现 `DELETE /api/v1/sources/{id}/files`

目标：

- 删除 file source 的单个附件

完成标准：

- 校验 pathname 必须属于 source 前缀

### T19. 明确 `POST /api/sources/ocr` 暂不迁移

目标：

- 防止范围失控

完成标准：

- 在任务排期中标记为后移项

## 3.4 M4: Agent Config API

### T20. 定义 `agent-config` Pydantic DTO

建议产出：

- `AgentConfigResponse`
- `UpdateAgentConfigRequest`

完成标准：

- 字段命名兼容当前前端和 SDK

### T21. 实现 `AgentConfigRepository`

目标：

- 收口 active config 查询和写入

建议方法：

- `get_active()`
- `create_active(data)`
- `update_active(id, data)`

完成标准：

- active config 逻辑不写在 controller 层

### T22. 实现 `AgentConfigService`

目标：

- 承担默认值、upsert、reset、cache invalidate 逻辑

建议方法：

- `get_active_or_default()`
- `update_active(data)`
- `reset_active()`
- `invalidate_cache()`

完成标准：

- 无 active config 时可返回默认值
- 更新和 reset 后会删缓存

### T23. 实现 `GET /api/v1/agent-config`

目标：

- 给 admin 页面读取当前配置

完成标准：

- admin 鉴权
- 返回 active config 或默认配置

### T24. 实现 `PUT /api/v1/agent-config`

目标：

- 支持更新 active config

完成标准：

- 语义是 upsert active config
- 与现有前端保存逻辑兼容

### T25. 实现 `POST /api/v1/agent-config/reset`

目标：

- 恢复默认配置

完成标准：

- 幂等
- 与现有管理页重置按钮兼容

### T26. 实现 `GET /api/v1/agent-config/public`

目标：

- 给 SDK / 机器人调用链保留兼容接口

完成标准：

- 至少保证 web 内部调用可用
- API key 全兼容可以视为后续增强项

## 3.5 M5: 前端接入与验收

### T27. 新建 `frontend/packages/web-sdk`

目标：

- 建立前端到 Python API 的统一调用层

完成标准：

- 不再让页面直接散用 `$fetch('/api/...')` 指向 Nuxt server route

### T28. 封装 Sources SDK 方法

建议产出：

- `getSources`
- `createSource`
- `updateSource`
- `deleteSource`
- `listSourceFiles`
- `uploadSourceFiles`
- `deleteSourceFile`

### T29. 封装 Agent Config SDK 方法

建议产出：

- `getAgentConfig`
- `updateAgentConfig`
- `resetAgentConfig`

### T30. 改造 `admin/index.vue`

目标：

- sources 列表页走 Python API

完成标准：

- 列表、删除、sync 提示信息不回退到 Nuxt sources route

### T31. 改造 `admin/new.vue`

目标：

- 新建 source 走 Python API

完成标准：

- 创建 source
- file source 上传附件

### T32. 改造 `SourceModal.vue`

目标：

- 编辑 source 走 Python API

完成标准：

- 编辑 source
- file source 补传附件

### T33. 改造 `admin/agent.vue`

目标：

- 读取、保存、重置 agent config 走 Python API

完成标准：

- 页面不再依赖 Nuxt `agent-config` server route

### T34. 联调验收

验收范围：

- `sources` 列表加载成功
- 创建 GitHub source 成功
- 创建 file source 成功
- file source 上传文件成功
- 编辑 source 成功
- 删除 source 成功
- `agent-config` 读取成功
- `agent-config` 保存成功
- `agent-config` reset 成功

## 4. 风险点

### R1. `GET /sources` 不是单纯查表

风险：

- 它还依赖 sync 状态、snapshot 配置、YouTube feature flag

处理：

- 不要只迁 DB CRUD，必须迁聚合逻辑

### R2. `file source` 不是数据库文件表

风险：

- 很容易误建表保存 files 列表

处理：

- 文件存储保持在对象存储层

### R3. `agent-config` 有默认值与缓存语义

风险：

- 如果 Python 侧只做“查 active row”，前端会在空配置时出错

处理：

- 必须保留 `get_active_or_default()`

### R4. 权限模型不一致

风险：

- 现有 `PUT /api/sources/{id}` 未校验 admin

处理：

- Python 侧明确修正为 admin-only

## 5. 推荐执行顺序

1. T1-T3
2. T4-T7
3. T8-T18
4. T20-T26
5. T27-T33
6. T34

## 6. 完成定义

Step 1 只有在下面全部成立时才算完成：

- backend 新目录已建立
- `sources` / `agent_config` ORM 与 DTO 已完成
- `/api/v1` 下接口可用
- 前端管理页至少已切走这两组能力
- 联调通过
