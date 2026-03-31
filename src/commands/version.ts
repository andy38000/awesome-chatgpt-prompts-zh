import type { Command } from '../types/command.js';
import { VERSION } from '../constants/version.js';

export const versionCommand: Command = {
  name: '/version',
  aliases: ['/v'],
  description: 'Show version',
  execute: async () => {
    return { output: `Claude Code v${VERSION}` };
  },
};
