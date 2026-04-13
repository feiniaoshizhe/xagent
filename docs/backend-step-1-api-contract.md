# Backend Step 1 API Contract

## 1. 文档目标

这份文档定义 Step 1 的 API 合同，覆盖两类能力：

- `sources`
- `agent-config`

用途：

- 后端实现接口
- 前端联调
- 后续 OpenAPI 落地

原则：

- 优先兼容现有前端页面和 SDK
- 新接口统一走 `/api/v1`
- 尽量保持现有字段命名为 camelCase

## 1.1 Step 1 API List

当前 Step 1 需要处理的 API 范围如下。

### Sources

- `GET /api/v1/sources`
- `POST /api/v1/sources`
- `PUT /api/v1/sources/{id}`
- `DELETE /api/v1/sources/{id}`
- `GET /api/v1/sources/{id}/files`
- `PUT /api/v1/sources/{id}/files`
- `DELETE /api/v1/sources/{id}/files`

### Agent Config

- `GET /api/v1/agent-config`
- `PUT /api/v1/agent-config`
- `POST /api/v1/agent-config/reset`
- `GET /api/v1/agent-config/public`

### 本 Step 明确不处理

- `POST /api/sources/ocr`
- chat 相关接口
- sync 相关接口
- sandbox 相关接口
- upload 相关接口
- webhook / bot 相关接口

### 对应旧接口映射

| 旧接口 | Step 1 新接口 |
|---|---|
| `GET /api/sources` | `GET /api/v1/sources` |
| `POST /api/sources` | `POST /api/v1/sources` |
| `PUT /api/sources/{id}` | `PUT /api/v1/sources/{id}` |
| `DELETE /api/sources/{id}` | `DELETE /api/v1/sources/{id}` |
| `GET /api/sources/{id}/files` | `GET /api/v1/sources/{id}/files` |
| `PUT /api/sources/{id}/files` | `PUT /api/v1/sources/{id}/files` |
| `DELETE /api/sources/{id}/files` | `DELETE /api/v1/sources/{id}/files` |
| `GET /api/agent-config` | `GET /api/v1/agent-config` |
| `PUT /api/agent-config` | `PUT /api/v1/agent-config` |
| `POST /api/agent-config/reset` | `POST /api/v1/agent-config/reset` |
| `GET /api/agent-config/public` | `GET /api/v1/agent-config/public` |

## 2. 通用约定

## 2.1 Base Path

Step 1 新接口统一挂到：

```text
/api/v1
```

## 2.2 认证与权限

Step 1 的权限约定如下：

- `admin`
  - 需要管理员角色
- `authenticated`
  - 需要登录用户

## 2.3 时间字段格式

所有时间字段对外返回 ISO 8601 字符串，例如：

```json
"2026-04-13T10:00:00.000Z"
```

## 2.4 错误响应

建议统一错误响应结构：

```json
{
  "statusCode": 400,
  "message": "Validation error",
  "error": "Bad Request",
  "data": {
    "why": "repo is required for github source",
    "fix": "Provide repo in owner/repo format"
  }
}
```

其中：

- `statusCode` 必填
- `message` 必填
- `error` 可选
- `data.why` 可选
- `data.fix` 可选

## 2.5 成功响应

删除类接口保持简单返回：

```json
{
  "success": true
}
```

## 3. Sources API

## 3.1 数据结构

### SourceType

```ts
type SourceType = 'github' | 'youtube' | 'file'
```

### SourceItem

```ts
interface SourceItem {
  id: string
  type: 'github' | 'youtube' | 'file'
  label: string
  repo: string | null
  branch: string | null
  contentPath: string | null
  outputPath: string | null
  readmeOnly: boolean | null
  channelId: string | null
  handle: string | null
  maxVideos: number | null
  basePath: string | null
  createdAt: string
  updatedAt: string
}
```

### SourceFileItem

```ts
interface SourceFileItem {
  pathname: string
  filename: string
  size: number
  uploadedAt: string
}
```

### SourcesGroupedResponse

```ts
interface SourcesGroupedResponse {
  total: number
  lastSyncAt: number | null
  youtubeEnabled: boolean
  snapshotRepo: string | null
  snapshotBranch: string | null
  snapshotRepoUrl: string | null
  github: {
    count: number
    sources: SourceItem[]
  }
  youtube: {
    count: number
    sources: SourceItem[]
  }
  file: {
    count: number
    sources: SourceItem[]
  }
}
```

### CreateSourceRequest

```ts
interface CreateSourceRequest {
  type: 'github' | 'youtube' | 'file'
  label: string
  basePath?: string
  repo?: string
  branch?: string
  contentPath?: string
  outputPath?: string
  readmeOnly?: boolean
  channelId?: string
  handle?: string
  maxVideos?: number
}
```

### UpdateSourceRequest

```ts
interface UpdateSourceRequest {
  label?: string
  basePath?: string
  repo?: string
  branch?: string
  contentPath?: string
  outputPath?: string
  readmeOnly?: boolean
  channelId?: string
  handle?: string
  maxVideos?: number
}
```

### DeleteSourceFileRequest

```ts
interface DeleteSourceFileRequest {
  pathname: string
}
```

## 3.2 `GET /api/v1/sources`

用途：

- 获取 sources 管理页数据

权限：

- `authenticated` 或 `admin`

说明：

- 如果完全兼容现有管理页，建议要求已登录
- 如果要与当前行为完全一致，页面本身是 admin 页面，实际可直接要求 `admin`

请求体：

- 无

响应：

```json
{
  "total": 3,
  "lastSyncAt": 1713000000000,
  "youtubeEnabled": true,
  "snapshotRepo": "owner/repo",
  "snapshotBranch": "main",
  "snapshotRepoUrl": "https://github.com/owner/repo",
  "github": {
    "count": 1,
    "sources": []
  },
  "youtube": {
    "count": 1,
    "sources": []
  },
  "file": {
    "count": 1,
    "sources": []
  }
}
```

错误：

- `401` 未登录
- `403` 无权限

## 3.3 `POST /api/v1/sources`

用途：

- 创建 source

权限：

- `admin`

请求体：

```json
{
  "type": "github",
  "label": "nuxt",
  "basePath": "/docs",
  "repo": "nuxt/nuxt",
  "branch": "main",
  "contentPath": "docs",
  "outputPath": "nuxt",
  "readmeOnly": false
}
```

响应：

- `200` 或 `201`
- body 为创建后的 `SourceItem`

类型校验要求：

- `type=github`
  - `repo` 必须存在
- `type=youtube`
  - `channelId` 必须存在
- `type=file`
  - 至少应有 `label`

错误：

- `400` 参数错误
- `401` 未登录
- `403` 非 admin

## 3.4 `PUT /api/v1/sources/{id}`

用途：

- 更新 source

权限：

- `admin`

路径参数：

- `id: string`

请求体：

```json
{
  "label": "nuxt docs",
  "outputPath": "nuxt-docs"
}
```

响应：

- `200`
- body 为更新后的 `SourceItem`

错误：

- `400` 参数错误
- `404` source 不存在
- `403` 非 admin

## 3.5 `DELETE /api/v1/sources/{id}`

用途：

- 删除 source

权限：

- `admin`

路径参数：

- `id: string`

响应：

```json
{
  "success": true
}
```

说明：

- 若是 `file` 类型 source，需要同步删除存储中的 `sources/{id}/` 前缀内容

错误：

- `404` source 不存在

## 3.6 `GET /api/v1/sources/{id}/files`

用途：

- 列出 file source 的当前附件

权限：

- `admin`

路径参数：

- `id: string`

响应：

```json
{
  "files": [
    {
      "pathname": "sources/123/readme.md",
      "filename": "readme.md",
      "size": 1204,
      "uploadedAt": "2026-04-13T10:00:00.000Z"
    }
  ]
}
```

错误：

- `404` source 不存在
- `400` source 不是 file 类型

## 3.7 `PUT /api/v1/sources/{id}/files`

用途：

- 向 file source 上传附件

权限：

- `admin`

路径参数：

- `id: string`

Content-Type：

- `multipart/form-data`

表单字段：

- `files`
  - 可多次出现

允许文件后缀：

- `.md`
- `.mdx`
- `.txt`
- `.yml`
- `.yaml`
- `.json`

单文件大小限制：

- 8MB

响应：

```json
{
  "files": [
    {
      "filename": "doc.md",
      "pathname": "sources/123/doc.md",
      "size": 1024
    },
    {
      "filename": "bad.exe",
      "error": "File type not allowed. Accepted: .md, .mdx, .txt, .yml, .yaml, .json"
    }
  ]
}
```

错误：

- `404` source 不存在
- `400` source 不是 file 类型
- `400` form-data 缺失

## 3.8 `DELETE /api/v1/sources/{id}/files`

用途：

- 删除 file source 的某个附件

权限：

- `admin`

路径参数：

- `id: string`

请求体：

```json
{
  "pathname": "sources/123/doc.md"
}
```

响应：

```json
{
  "success": true
}
```

校验要求：

- `pathname` 必须以 `sources/{id}/` 开头

错误：

- `404` source 不存在
- `400` source 不是 file 类型
- `403` pathname 不属于该 source

## 4. Agent Config API

## 4.1 数据结构

### AgentConfigResponse

```ts
interface AgentConfigResponse {
  id: string
  name: string
  additionalPrompt: string | null
  responseStyle: 'concise' | 'detailed' | 'technical' | 'friendly'
  language: string
  defaultModel: string | null
  maxStepsMultiplier: number
  temperature: number
  searchInstructions: string | null
  citationFormat: 'inline' | 'footnote' | 'none'
  isActive: boolean
}
```

### UpdateAgentConfigRequest

```ts
interface UpdateAgentConfigRequest {
  additionalPrompt?: string | null
  responseStyle?: 'concise' | 'detailed' | 'technical' | 'friendly'
  language?: string
  defaultModel?: string | null
  maxStepsMultiplier?: number
  temperature?: number
  searchInstructions?: string | null
  citationFormat?: 'inline' | 'footnote' | 'none'
}
```

## 4.2 `GET /api/v1/agent-config`

用途：

- 后台读取当前 active agent config

权限：

- `admin`

请求体：

- 无

响应：

- `200`
- body 为 `AgentConfigResponse`

说明：

- 如果数据库中没有 active config，仍应返回默认配置

## 4.3 `PUT /api/v1/agent-config`

用途：

- 更新当前 active config

权限：

- `admin`

请求体：

```json
{
  "additionalPrompt": "Be precise",
  "responseStyle": "technical",
  "language": "zh",
  "defaultModel": null,
  "maxStepsMultiplier": 1.2,
  "temperature": 0.5,
  "searchInstructions": "Prefer official docs",
  "citationFormat": "inline"
}
```

响应：

- `200`
- body 为更新后的 `AgentConfigResponse`

语义要求：

- 若存在 active config，则更新
- 若不存在 active config，则创建一条 active config

校验要求：

- `maxStepsMultiplier` 范围建议 `0.5 - 3.0`
- `temperature` 范围建议 `0 - 2`

## 4.4 `POST /api/v1/agent-config/reset`

用途：

- 将当前 active config 重置为默认值

权限：

- `admin`

请求体：

- 无

响应：

- `200`
- body 为重置后的 `AgentConfigResponse`

说明：

- 幂等
- 即使数据库中没有 active config，也应创建或返回默认态配置

## 4.5 `GET /api/v1/agent-config/public`

用途：

- 提供给 SDK / bot / 外部调用链读取当前配置

权限：

- Step 1 先保守定义为 `authenticated`

请求体：

- 无

响应：

- `200`
- body 为 `AgentConfigResponse`

说明：

- 若后续要支持 API key，可在 Step 1 之后补充认证方式

## 5. 默认值约定

## 5.1 Agent Config 默认值

当数据库没有 active config 时，返回：

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

## 5.2 Sources 默认行为

建议默认值：

- `branch`
  - `main`
- `basePath`
  - `github` -> `/docs`
  - `youtube` -> `/youtube`
  - `file` -> `/files`
- `readmeOnly`
  - `false`
- `maxVideos`
  - `50`

## 6. 明确不在本合同中的接口

Step 1 不纳入本合同的接口：

- `POST /api/sources/ocr`
- chat 系列接口
- sync 系列接口
- sandbox 系列接口
- upload 系列接口

这些能力不应混入 Step 1 的交付范围。
