import type { Message } from '../types/message.js';

export interface AppState {
  cwd: string;
  model: string;
  messages: Message[];
  isLoading: boolean;
  thinkingEnabled: boolean;
  verboseMode: boolean;
  totalCost: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  sessionId: string;
  permissionMode: PermissionMode;
  additionalWorkingDirectories: Set<string>;
}

export type PermissionMode = 'default' | 'acceptEdits' | 'dangerousAutoApprove';

export function createInitialState(cwd: string, model: string): AppState {
  return {
    cwd,
    model,
    messages: [],
    isLoading: false,
    thinkingEnabled: true,
    verboseMode: false,
    totalCost: 0,
    totalInputTokens: 0,
    totalOutputTokens: 0,
    sessionId: crypto.randomUUID(),
    permissionMode: 'default',
    additionalWorkingDirectories: new Set(),
  };
}
