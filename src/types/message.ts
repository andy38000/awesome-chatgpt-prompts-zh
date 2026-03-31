export interface UserMessage {
  type: 'user';
  uuid: string;
  content: string;
  timestamp: number;
}

export interface AssistantMessage {
  type: 'assistant';
  uuid: string;
  content: string;
  model: string;
  usage?: MessageUsage;
  toolUse?: ToolUseResult[];
  thinking?: string;
  timestamp: number;
}

export interface SystemMessage {
  type: 'system';
  uuid: string;
  content: string;
  timestamp: number;
}

export interface ToolUseResult {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: string;
  isError?: boolean;
}

export interface MessageUsage {
  inputTokens: number;
  outputTokens: number;
  cacheCreationInputTokens?: number;
  cacheReadInputTokens?: number;
}

export type Message = UserMessage | AssistantMessage | SystemMessage;

export interface StreamEvent {
  type: 'text' | 'thinking' | 'tool_use' | 'tool_result' | 'done' | 'error';
  content?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  toolUseId?: string;
}
