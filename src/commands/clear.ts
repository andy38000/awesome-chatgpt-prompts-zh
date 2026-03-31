import type { Command } from '../types/command.js';

export const clearCommand: Command = {
  name: '/clear',
  description: 'Clear conversation history',
  execute: async (_args, context) => {
    context.clearMessages();
    return { output: 'Conversation history cleared.' };
  },
};
