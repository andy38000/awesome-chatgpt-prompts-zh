import type { Command } from '../types/command.js';
import { formatCost, formatTokens } from '../utils/cost.js';

export const costCommand: Command = {
  name: '/cost',
  description: 'Show token usage and cost for this session',
  execute: async (_args, context) => {
    const { appState } = context;
    const output = [
      '📊 Session Cost Summary',
      `  Model: ${appState.model}`,
      `  Input tokens:  ${formatTokens(appState.totalInputTokens)}`,
      `  Output tokens: ${formatTokens(appState.totalOutputTokens)}`,
      `  Total cost:    ${formatCost(appState.totalCost)}`,
      `  Messages:      ${appState.messages.length}`,
    ].join('\n');

    return { output };
  },
};
