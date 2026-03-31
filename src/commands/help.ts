import type { Command } from '../types/command.js';

export const helpCommand: Command = {
  name: '/help',
  aliases: ['/h', '/?'],
  description: 'Show available commands',
  execute: async () => {
    const help = [
      'Available commands:',
      '',
      '  /help, /h         Show this help message',
      '  /clear            Clear conversation history',
      '  /compact          Summarize conversation to reduce context',
      '  /cost             Show token usage and cost',
      '  /model            Switch the AI model',
      '  /config           View or modify configuration',
      '  /exit, /quit      Exit Claude Code',
      '  /version          Show version',
      '',
      'Available tools:',
      '  BashTool           Execute shell commands',
      '  FileReadTool       Read file contents',
      '  FileWriteTool      Write files',
      '  FileEditTool       Edit files with string replacement',
      '  GlobTool           Search files by pattern',
      '  GrepTool           Search file contents by regex',
      '  WebFetchTool       Fetch URL content',
      '  TodoWriteTool      Manage task lists',
      '',
      'Keyboard shortcuts:',
      '  Ctrl+C             Cancel current request',
      '  Ctrl+D             Exit',
    ].join('\n');

    return { output: help };
  },
};
