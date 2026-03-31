import type { Message } from './message.js';
import type { AppState } from '../state/AppState.js';

export interface Command {
  name: string;
  aliases?: string[];
  description: string;
  isEnabled?: () => boolean;
  execute: (args: string, context: CommandContext) => Promise<CommandResult>;
}

export interface CommandContext {
  appState: AppState;
  setAppState: (fn: (prev: AppState) => AppState) => void;
  messages: Message[];
  clearMessages: () => void;
  abortController?: AbortController;
}

export interface CommandResult {
  output?: string;
  shouldContinue?: boolean;
}
