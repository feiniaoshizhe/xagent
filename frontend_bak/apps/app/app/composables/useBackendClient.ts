export type SourceType = 'github' | 'youtube' | 'file'

export interface SourceItem {
  id: string
  type: SourceType
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

export interface SourcesGroupedResponse {
  total: number
  lastSyncAt: number | null
  youtubeEnabled: boolean
  snapshotRepo: string | null
  snapshotBranch: string | null
  snapshotRepoUrl: string | null
  github: { count: number, sources: SourceItem[] }
  youtube: { count: number, sources: SourceItem[] }
  file: { count: number, sources: SourceItem[] }
}

export interface AgentConfig {
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

interface CreateSourceRequest {
  type: SourceType
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

interface UpdateSourceRequest extends Partial<CreateSourceRequest> {}

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const runtimeConfig = useRuntimeConfig()
  const url = `${runtimeConfig.public.backendBaseUrl.replace(/\/$/, '')}${path}`
  return await $fetch<T>(url as any, init as any)
}

export function useBackendClient() {
  return {
    getSources: () => request<SourcesGroupedResponse>('/api/v1/sources/'),
    createSource: (body: CreateSourceRequest) => request<SourceItem>('/api/v1/sources/', {
      method: 'POST',
      body: body as any,
    }),
    updateSource: (id: string, body: UpdateSourceRequest) => request<SourceItem>(`/api/v1/sources/${id}`, {
      method: 'PUT',
      body: body as any,
    }),
    deleteSource: (id: string) => request<{ success: true }>(`/api/v1/sources/${id}`, {
      method: 'DELETE',
    }),
    uploadSourceFiles: (id: string, body: FormData) => request(`/api/v1/sources/${id}/files`, {
      method: 'PUT',
      body,
    }),
    getAgentConfig: () => request<AgentConfig>('/api/v1/agent-config/'),
    updateAgentConfig: (body: UpdateAgentConfigRequest) => request<AgentConfig>('/api/v1/agent-config/', {
      method: 'PUT',
      body: body as any,
    }),
    resetAgentConfig: () => request<AgentConfig>('/api/v1/agent-config/reset', {
      method: 'POST',
    }),
  }
}
