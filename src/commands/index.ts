import type { Command } from '../types/command.js';
import { helpCommand } from './help.js';
import { clearCommand } from './clear.js';
import { costCommand } from './cost.js';
import { modelCommand } from './model.js';
import { compactCommand } from './compact.js';
import { configCommand } from './config.js';
import { versionCommand } from './version.js';
import { exitCommand } from './exit.js';

export function getAllCommands(): Command[] {
  return [
    helpCommand,
    clearCommand,
    costCommand,
    modelCommand,
    compactCommand,
    configCommand,
    versionCommand,
    exitCommand,
  ];
}

export function findCommand(input: string): { command: Command; args: string } | null {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/')) return null;

  const [cmd, ...rest] = trimmed.split(/\s+/);
  const args = rest.join(' ');
  const commands = getAllCommands();

  for (const command of commands) {
    if (command.name === cmd) return { command, args };
    if (command.aliases?.includes(cmd)) return { command, args };
  }

  return null;
}

export function isSlashCommand(input: string): boolean {
  return input.trim().startsWith('/');
}
