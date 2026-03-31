import type { Message } from './message.js';

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: ToolInputSchema;
  isEnabled: () => boolean;
  isReadOnly?: () => boolean;
  execute: (input: Record<string, unknown>, context: ToolContext) => Promise<ToolResult>;
  prompt?: () => string;
}

export interface ToolInputSchema {
  type: 'object';
  properties: Record<string, {
    type: string;
    description: string;
    enum?: string[];
    default?: unknown;
  }>;
  required?: string[];
}

export interface ToolContext {
  cwd: string;
  abortSignal?: AbortSignal;
  messages: Message[];
}

export interface ToolResult {
  output: string;
  isError?: boolean;
}
