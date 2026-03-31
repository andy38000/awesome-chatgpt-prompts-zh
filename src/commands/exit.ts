import type { Command } from '../types/command.js';

export const exitCommand: Command = {
  name: '/exit',
  aliases: ['/quit', '/q'],
  description: 'Exit Claude Code',
  execute: async () => {
    process.exit(0);
  },
};
