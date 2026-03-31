import type { Command } from '../types/command.js';
import { AVAILABLE_MODELS, getModelDisplayName } from '../constants/models.js';

export const modelCommand: Command = {
  name: '/model',
  description: 'Switch the AI model',
  execute: async (args, context) => {
    if (!args.trim()) {
      const modelList = AVAILABLE_MODELS.map(m =>
        `  ${m === context.appState.model ? '→ ' : '  '}${m} (${getModelDisplayName(m)})`
      ).join('\n');
      return { output: `Current model: ${context.appState.model}\n\nAvailable models:\n${modelList}` };
    }

    const requested = args.trim();
    const match = AVAILABLE_MODELS.find(m =>
      m === requested ||
      m.includes(requested) ||
      getModelDisplayName(m).toLowerCase() === requested.toLowerCase()
    );

    if (!match) {
      return { output: `Unknown model: ${requested}\nAvailable: ${AVAILABLE_MODELS.join(', ')}` };
    }

    context.setAppState(prev => ({ ...prev, model: match }));
    return { output: `Switched to model: ${match} (${getModelDisplayName(match)})` };
  },
};
