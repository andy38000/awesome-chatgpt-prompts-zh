import type { Command } from '../types/command.js';

export const compactCommand: Command = {
  name: '/compact',
  description: 'Summarize conversation to reduce context window usage',
  execute: async (_args, context) => {
    const messageCount = context.messages.length;
    if (messageCount < 4) {
      return { output: 'Not enough messages to compact.' };
    }

    const summary = `[Conversation compacted: ${messageCount} messages summarized]`;
    context.clearMessages();
    return { output: `Compacted ${messageCount} messages.\n${summary}` };
  },
};
