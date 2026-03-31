import type {
  BetaToolChoiceAuto,
  BetaToolChoiceTool,
  BetaToolUnion,
} from '@anthropic-ai/sdk/resources/beta/messages/messages.mjs'
import { APIUserAbortError } from '@anthropic-ai/sdk/error'
import { randomUUID } from 'crypto'
import type {
  AssistantMessage,
  UserMessage,
} from '../../types/message.js'
import {
  createAssistantAPIErrorMessage,
  createAssistantMessage,
} from '../../utils/messages.js'
import { getProxyFetchOptions } from '../../utils/proxy.js'
import type { InferenceProviderConfig } from '../../utils/config.js'
import type { SystemPrompt } from '../../utils/systemPromptType.js'

type OpenAIMessage = {
  role: 'assistant' | 'system' | 'tool' | 'user'
  content?: string | OpenAIContentPart[] | null
  name?: string
  tool_call_id?: string
  tool_calls?: OpenAIToolCall[]
}

type OpenAIContentPart =
  | {
      type: 'text'
      text: string
    }
  | {
      type: 'image_url'
      image_url: {
        url: string
      }
    }

type OpenAIToolCall = {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

type OpenAIChatCompletionResponse = {
  choices?: Array<{
    finish_reason?: string | null
    message?: {
      content?: string | Array<{ text?: string; type?: string }> | null
      tool_calls?: Array<{
        id?: string
        type?: string
        function?: {
          name?: string
          arguments?: string
        }
      }>
    }
  }>
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, '')
}

function getChatCompletionEndpoints(baseUrl: string): string[] {
  const normalized = normalizeBaseUrl(baseUrl)
  const endpoints = [`${normalized}/chat/completions`]
  if (!normalized.endsWith('/v1')) {
    endpoints.push(`${normalized}/v1/chat/completions`)
  }
  return [...new Set(endpoints)]
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof APIUserAbortError ||
    (error instanceof Error &&
      (error.name === 'AbortError' || error.message === 'The operation was aborted'))
  )
}

function extractText(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }

  if (Array.isArray(value)) {
    return value
      .map(entry => extractText(entry))
      .filter(Boolean)
      .join('\n\n')
  }

  if (!value || typeof value !== 'object') {
    return ''
  }

  if ('text' in value && typeof value.text === 'string') {
    return value.text
  }

  if ('content' in value) {
    return extractText(value.content)
  }

  return ''
}

function flushUserMessage(
  messages: OpenAIMessage[],
  parts: OpenAIContentPart[],
): void {
  if (parts.length === 0) {
    return
  }

  const textOnly = parts.every(part => part.type === 'text')
  messages.push({
    role: 'user',
    content: textOnly ? parts.map(part => part.text).join('\n\n') : parts,
  })
  parts.length = 0
}

function convertUserMessage(message: UserMessage): OpenAIMessage[] {
  const content = message.message.content
  if (typeof content === 'string') {
    return [{ role: 'user', content }]
  }

  const result: OpenAIMessage[] = []
  const parts: OpenAIContentPart[] = []

  for (const block of content) {
    switch (block.type) {
      case 'text':
        parts.push({ type: 'text', text: block.text })
        break
      case 'image':
        if (
          block.source?.type === 'base64' &&
          block.source.media_type &&
          block.source.data
        ) {
          parts.push({
            type: 'image_url',
            image_url: {
              url: `data:${block.source.media_type};base64,${block.source.data}`,
            },
          })
        }
        break
      case 'tool_result': {
        flushUserMessage(result, parts)
        result.push({
          role: 'tool',
          tool_call_id: block.tool_use_id,
          content: extractText(block.content) || (block.is_error ? 'Tool returned an error.' : ''),
        })
        break
      }
      case 'document':
        parts.push({
          type: 'text',
          text: '[Document attachment omitted for this provider.]',
        })
        break
      default:
        break
    }
  }

  flushUserMessage(result, parts)
  return result
}

function convertAssistantMessage(message: AssistantMessage): OpenAIMessage | null {
  const content = message.message.content
  if (typeof content === 'string') {
    return { role: 'assistant', content }
  }

  const textParts: string[] = []
  const toolCalls: OpenAIToolCall[] = []

  for (const block of content) {
    switch (block.type) {
      case 'text':
        textParts.push(block.text)
        break
      case 'tool_use':
        toolCalls.push({
          id: block.id,
          type: 'function',
          function: {
            name: block.name,
            arguments: JSON.stringify(block.input ?? {}),
          },
        })
        break
      default:
        break
    }
  }

  if (textParts.length === 0 && toolCalls.length === 0) {
    return null
  }

  return {
    role: 'assistant',
    content: textParts.length > 0 ? textParts.join('\n\n') : null,
    ...(toolCalls.length > 0 && { tool_calls: toolCalls }),
  }
}

function convertMessages(messages: (UserMessage | AssistantMessage)[]): OpenAIMessage[] {
  const result: OpenAIMessage[] = []

  for (const message of messages) {
    if (message.type === 'user') {
      result.push(...convertUserMessage(message))
      continue
    }

    const assistantMessage = convertAssistantMessage(message)
    if (assistantMessage) {
      result.push(assistantMessage)
    }
  }

  return result
}

function isFunctionTool(
  tool: BetaToolUnion,
): tool is BetaToolUnion & {
  description: string
  input_schema: Record<string, unknown>
  name: string
} {
  return (
    'name' in tool &&
    typeof tool.name === 'string' &&
    'description' in tool &&
    typeof tool.description === 'string' &&
    'input_schema' in tool &&
    !!tool.input_schema &&
    typeof tool.input_schema === 'object'
  )
}

function convertTools(tools: BetaToolUnion[]): Array<{
  type: 'function'
  function: {
    description: string
    name: string
    parameters: Record<string, unknown>
    strict?: boolean
  }
}> {
  return tools.filter(isFunctionTool).map(tool => ({
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.input_schema,
      ...('strict' in tool && tool.strict ? { strict: true } : {}),
    },
  }))
}

function convertToolChoice(
  toolChoice: BetaToolChoiceAuto | BetaToolChoiceTool | undefined,
):
  | 'auto'
  | {
      type: 'function'
      function: {
        name: string
      }
    }
  | undefined {
  if (!toolChoice || toolChoice.type === 'auto') {
    return toolChoice ? 'auto' : undefined
  }

  if (toolChoice.type === 'tool') {
    return {
      type: 'function',
      function: {
        name: toolChoice.name,
      },
    }
  }

  return undefined
}

function parseToolArguments(argumentsText: string | undefined): Record<string, unknown> {
  if (!argumentsText) {
    return {}
  }

  try {
    const parsed = JSON.parse(argumentsText) as unknown
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

function getResponseText(
  content: OpenAIChatCompletionResponse['choices'][number]['message']['content'],
): string {
  if (typeof content === 'string') {
    return content
  }

  if (!Array.isArray(content)) {
    return ''
  }

  return content
    .map(part => (part?.type === 'text' && typeof part.text === 'string' ? part.text : ''))
    .filter(Boolean)
    .join('\n\n')
}

function createProviderErrorMessage(
  provider: Pick<InferenceProviderConfig, 'name'>,
  status: number,
  detail: string,
): AssistantMessage {
  if (status === 401 || status === 403) {
    return createAssistantAPIErrorMessage({
      error: 'authentication_failed',
      content: `Check your /model provider settings. ${detail}`,
    })
  }

  if (status === 404) {
    return createAssistantAPIErrorMessage({
      error: 'invalid_request',
      content: `The selected model or endpoint is unavailable on ${provider.name}. Check the base URL and model in /model.`,
    })
  }

  return createAssistantAPIErrorMessage({
    error: 'unknown',
    content: `${provider.name} request failed (${status}). ${detail}`,
  })
}

export async function queryOpenAICompatibleModel({
  provider,
  model,
  messages,
  systemPrompt,
  tools,
  toolChoice,
  signal,
  maxOutputTokens,
  temperature,
}: {
  provider: InferenceProviderConfig
  model: string
  messages: (UserMessage | AssistantMessage)[]
  systemPrompt: SystemPrompt
  tools: BetaToolUnion[]
  toolChoice?: BetaToolChoiceAuto | BetaToolChoiceTool
  signal: AbortSignal
  maxOutputTokens: number
  temperature?: number
}): Promise<AssistantMessage> {
  const openAIMessages: OpenAIMessage[] = []
  const systemText = systemPrompt.join('\n\n').trim()
  if (systemText) {
    openAIMessages.push({
      role: 'system',
      content: systemText,
    })
  }
  openAIMessages.push(...convertMessages(messages))

  const requestBody = {
    model,
    messages: openAIMessages,
    max_tokens: maxOutputTokens,
    ...(temperature !== undefined ? { temperature } : {}),
    ...(tools.length > 0 ? { tools: convertTools(tools) } : {}),
    ...(toolChoice ? { tool_choice: convertToolChoice(toolChoice) } : {}),
    stream: false,
  }

  let lastErrorMessage = 'No chat completion endpoint responded successfully.'

  for (const endpoint of getChatCompletionEndpoints(provider.baseUrl)) {
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          Authorization: `Bearer ${provider.apiKey ?? ''}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal,
        ...(getProxyFetchOptions() as RequestInit),
      })

      if (!response.ok) {
        const text = await response.text()
        const detail = text.trim().slice(0, 400) || 'No additional error details were returned.'
        lastErrorMessage = `POST ${endpoint} failed with ${response.status}: ${detail}`
        if (response.status !== 404) {
          return createProviderErrorMessage(provider, response.status, detail)
        }
        continue
      }

      const payload = (await response.json()) as OpenAIChatCompletionResponse
      const message = payload.choices?.[0]?.message
      if (!message) {
        return createAssistantAPIErrorMessage({
          error: 'unknown',
          content: `${provider.name} returned no assistant message.`,
        })
      }

      const blocks: Array<
        | {
            type: 'text'
            text: string
          }
        | {
            type: 'tool_use'
            id: string
            name: string
            input: Record<string, unknown>
          }
      > = []

      const responseText = getResponseText(message.content)
      if (responseText) {
        blocks.push({
          type: 'text',
          text: responseText,
        })
      }

      for (const toolCall of message.tool_calls ?? []) {
        if (!toolCall?.function?.name) {
          continue
        }

        blocks.push({
          type: 'tool_use',
          id: toolCall.id || `toolu_${randomUUID()}`,
          name: toolCall.function.name,
          input: parseToolArguments(toolCall.function.arguments),
        })
      }

      return createAssistantMessage({
        content: blocks.length > 0 ? (blocks as never) : '',
      })
    } catch (error) {
      if (isAbortError(error) || signal.aborted) {
        throw new APIUserAbortError()
      }

      lastErrorMessage =
        error instanceof Error
          ? `POST ${endpoint} failed: ${error.message}`
          : `POST ${endpoint} failed`
    }
  }

  return createAssistantAPIErrorMessage({
    error: 'unknown',
    content: lastErrorMessage,
  })
}
