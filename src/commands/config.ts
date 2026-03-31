import type { Command } from '../types/command.js';

export const configCommand: Command = {
  name: '/config',
  description: 'View or modify configuration',
  execute: async (args, context) => {
    if (args.trim() === 'thinking on') {
      context.setAppState(prev => ({ ...prev, thinkingEnabled: true }));
      return { output: 'Extended thinking enabled.' };
    }
    if (args.trim() === 'thinking off') {
      context.setAppState(prev => ({ ...prev, thinkingEnabled: false }));
      return { output: 'Extended thinking disabled.' };
    }
    if (args.trim() === 'verbose on') {
      context.setAppState(prev => ({ ...prev, verboseMode: true }));
      return { output: 'Verbose mode enabled.' };
    }
    if (args.trim() === 'verbose off') {
      context.setAppState(prev => ({ ...prev, verboseMode: false }));
      return { output: 'Verbose mode disabled.' };
    }

    const output = [
      'Current configuration:',
      `  Model:     ${context.appState.model}`,
      `  CWD:       ${context.appState.cwd}`,
      `  Thinking:  ${context.appState.thinkingEnabled ? 'on' : 'off'}`,
      `  Verbose:   ${context.appState.verboseMode ? 'on' : 'off'}`,
      `  Permission: ${context.appState.permissionMode}`,
      '',
      'Usage: /config <option>',
      '  thinking on/off    - Toggle extended thinking',
      '  verbose on/off     - Toggle verbose mode',
    ].join('\n');

    return { output };
  },
};
