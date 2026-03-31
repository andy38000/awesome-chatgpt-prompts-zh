import { randomUUID } from 'crypto'
import {
  getGlobalConfig,
  saveGlobalConfig,
  type ActiveInferenceProviderSelection,
  type InferenceProviderConfig,
  type InferenceProviderFormat,
} from '../config.js'
import { getProxyFetchOptions } from '../proxy.js'
import { getAPIProvider } from './providers.js'

export type { InferenceProviderConfig, InferenceProviderFormat }

const ANTHROPIC_VERSION = '2023-06-01'

type ProviderModelFetchResult = {
  endpoint: string
  models: string[]
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, '')
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.map(value => value.trim()).filter(Boolean))]
}

function sanitizeModels(models?: string[]): string[] | undefined {
  const normalized = uniqueStrings(models ?? [])
  return normalized.length > 0 ? normalized : undefined
}

function sortProviders(
  providers: InferenceProviderConfig[],
): InferenceProviderConfig[] {
  return [...providers].sort((a, b) => a.name.localeCompare(b.name))
}

function normalizeProvider(
  provider: InferenceProviderConfig,
): InferenceProviderConfig {
  const models = sanitizeModels(provider.models)
  const selectedModel =
    provider.selectedModel && models?.includes(provider.selectedModel)
      ? provider.selectedModel
      : models?.[0]

  return {
    ...provider,
    baseUrl: normalizeBaseUrl(provider.baseUrl),
    models,
    selectedModel,
  }
}

function getFetchEndpoints(
  format: InferenceProviderFormat,
  baseUrl: string,
): string[] {
  const normalized = normalizeBaseUrl(baseUrl)
  return format === 'anthropic'
    ? [`${normalized}/v1/models`, `${normalized}/models`]
    : [`${normalized}/models`, `${normalized}/v1/models`]
}

function getFetchHeaders(
  provider: Pick<InferenceProviderConfig, 'format' | 'apiKey'>,
): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }

  if (provider.format === 'anthropic') {
    if (provider.apiKey) {
      headers['x-api-key'] = provider.apiKey
    }
    headers['anthropic-version'] = ANTHROPIC_VERSION
  } else if (provider.apiKey) {
    headers.Authorization = `Bearer ${provider.apiKey}`
  }

  return headers
}

function extractModelIds(payload: unknown): string[] {
  if (Array.isArray(payload)) {
    return uniqueStrings(
      payload.flatMap(entry => {
        if (typeof entry === 'string') {
          return [entry]
        }
        if (
          entry &&
          typeof entry === 'object' &&
          'id' in entry &&
          typeof entry.id === 'string'
        ) {
          return [entry.id]
        }
        return []
      }),
    )
  }

  if (!payload || typeof payload !== 'object') {
    return []
  }

  if ('data' in payload && Array.isArray(payload.data)) {
    return extractModelIds(payload.data)
  }

  if ('models' in payload && Array.isArray(payload.models)) {
    return extractModelIds(payload.models)
  }

  if ('id' in payload && typeof payload.id === 'string') {
    return [payload.id]
  }

  return []
}

export function getInferenceProviders(): InferenceProviderConfig[] {
  return sortProviders(
    (getGlobalConfig().inferenceProviders ?? []).map(normalizeProvider),
  )
}

export function getInferenceProvider(
  providerId: string,
): InferenceProviderConfig | undefined {
  return getInferenceProviders().find(provider => provider.id === providerId)
}

export function getActiveInferenceProviderSelection():
  | ActiveInferenceProviderSelection
  | null {
  const active = getGlobalConfig().activeInferenceProvider
  if (!active?.providerId || !active.model) {
    return null
  }

  const provider = getInferenceProvider(active.providerId)
  if (!provider) {
    return null
  }

  return {
    providerId: provider.id,
    model: active.model,
  }
}

export function getActiveInferenceProviderConfig():
  | {
      provider: InferenceProviderConfig
      model: string
    }
  | null {
  const active = getActiveInferenceProviderSelection()
  if (!active) {
    return null
  }

  const provider = getInferenceProvider(active.providerId)
  if (!provider) {
    return null
  }

  return {
    provider,
    model: active.model,
  }
}

export function getActiveAnthropicProviderConfig():
  | {
      provider: InferenceProviderConfig
      model: string
    }
  | null {
  const active = getActiveInferenceProviderConfig()
  if (!active) {
    return null
  }

  if (active.provider.format !== 'anthropic') {
    return null
  }

  if (getAPIProvider() !== 'firstParty') {
    return null
  }

  return active
}

export function getActiveOpenAIProviderConfig():
  | {
      provider: InferenceProviderConfig
      model: string
    }
  | null {
  const active = getActiveInferenceProviderConfig()
  if (!active) {
    return null
  }

  if (active.provider.format !== 'openai') {
    return null
  }

  if (getAPIProvider() !== 'firstParty') {
    return null
  }

  return active
}

export function formatProviderModelLabel(
  providerName: string,
  model: string,
): string {
  return `${providerName}/${model}`
}

export function getActiveProviderModelLabel(model?: string | null): string | null {
  if (!model) {
    return null
  }

  const active = getActiveInferenceProviderConfig()
  if (!active || active.model !== model) {
    return null
  }

  return formatProviderModelLabel(active.provider.name, active.model)
}

export function saveInferenceProvider(
  provider: Omit<InferenceProviderConfig, 'id'> & {
    id?: string
    activate?: boolean
  },
): InferenceProviderConfig {
  const normalizedProvider = normalizeProvider({
    id: provider.id ?? randomUUID(),
    name: provider.name.trim(),
    format: provider.format,
    baseUrl: provider.baseUrl,
    apiKey: provider.apiKey?.trim() || undefined,
    models: provider.models,
    selectedModel: provider.selectedModel?.trim() || undefined,
  })

  saveGlobalConfig(current => {
    const existingProviders = current.inferenceProviders ?? []
    const filtered = existingProviders.filter(
      entry => entry.id !== normalizedProvider.id,
    )
    const updatedProviders = sortProviders([...filtered, normalizedProvider])
    const nextActive =
      provider.activate && normalizedProvider.selectedModel
        ? {
            providerId: normalizedProvider.id,
            model: normalizedProvider.selectedModel,
          }
        : current.activeInferenceProvider

    return {
      ...current,
      inferenceProviders: updatedProviders,
      activeInferenceProvider: nextActive,
    }
  })

  return normalizedProvider
}

export function activateInferenceProviderModel(
  providerId: string,
  model: string,
): void {
  saveGlobalConfig(current => {
    const providers = (current.inferenceProviders ?? []).map(provider =>
      provider.id === providerId
        ? normalizeProvider({
            ...provider,
            models: uniqueStrings([...(provider.models ?? []), model]),
            selectedModel: model,
          })
        : provider,
    )

    return {
      ...current,
      inferenceProviders: providers,
      activeInferenceProvider: {
        providerId,
        model,
      },
    }
  })
}

export function updateInferenceProviderModels(
  providerId: string,
  models: string[],
  selectedModel?: string,
): void {
  const normalizedModels = uniqueStrings(models)
  saveGlobalConfig(current => {
    const providers = (current.inferenceProviders ?? []).map(provider => {
      if (provider.id !== providerId) {
        return provider
      }

      const nextSelectedModel =
        selectedModel && normalizedModels.includes(selectedModel)
          ? selectedModel
          : provider.selectedModel && normalizedModels.includes(provider.selectedModel)
            ? provider.selectedModel
            : normalizedModels[0]

      return normalizeProvider({
        ...provider,
        models: normalizedModels,
        selectedModel: nextSelectedModel,
      })
    })

    const active = current.activeInferenceProvider
    const activeNeedsUpdate = active?.providerId === providerId
    const nextActive =
      activeNeedsUpdate && normalizedModels.length > 0
        ? {
            providerId,
            model:
              selectedModel && normalizedModels.includes(selectedModel)
                ? selectedModel
                : normalizedModels.includes(active.model)
                  ? active.model
                  : normalizedModels[0]!,
          }
        : active

    return {
      ...current,
      inferenceProviders: providers,
      activeInferenceProvider: nextActive,
    }
  })
}

export function clearActiveInferenceProvider(): void {
  saveGlobalConfig(current => ({
    ...current,
    activeInferenceProvider: undefined,
  }))
}

export function removeInferenceProvider(providerId: string): void {
  saveGlobalConfig(current => {
    const providers = (current.inferenceProviders ?? []).filter(
      provider => provider.id !== providerId,
    )
    const active =
      current.activeInferenceProvider?.providerId === providerId
        ? undefined
        : current.activeInferenceProvider

    return {
      ...current,
      inferenceProviders: providers,
      activeInferenceProvider: active,
    }
  })
}

export async function fetchInferenceProviderModels(
  provider: Pick<InferenceProviderConfig, 'format' | 'baseUrl' | 'apiKey'>,
  signal?: AbortSignal,
): Promise<ProviderModelFetchResult> {
  let lastError = 'No model endpoint responded successfully.'

  for (const endpoint of getFetchEndpoints(provider.format, provider.baseUrl)) {
    try {
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: getFetchHeaders(provider),
        signal,
        ...(getProxyFetchOptions() as RequestInit),
      })

      if (!response.ok) {
        const text = await response.text()
        lastError = `GET ${endpoint} failed with ${response.status}${
          text ? `: ${text.slice(0, 200)}` : ''
        }`
        continue
      }

      const payload = (await response.json()) as unknown
      const models = extractModelIds(payload)
      if (models.length === 0) {
        lastError = `GET ${endpoint} succeeded but returned no model ids.`
        continue
      }

      return {
        endpoint,
        models,
      }
    } catch (error) {
      lastError =
        error instanceof Error
          ? `GET ${endpoint} failed: ${error.message}`
          : `GET ${endpoint} failed`
    }
  }

  throw new Error(lastError)
}
