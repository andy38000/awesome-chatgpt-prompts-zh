import { glob } from 'glob';
import { resolve } from 'path';
import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const DESCRIPTION = `Search for files matching a glob pattern. Returns matching file paths sorted by modification time.
Use this when you need to find files by name patterns.
Patterns not starting with "**/" are automatically prepended with "**/" for recursive searching.`;

export const GlobTool: ToolDefinition = {
  name: 'GlobTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      pattern: {
        type: 'string',
        description: 'The glob pattern to match files against (e.g., "*.ts", "**/*.tsx")',
      },
      path: {
        type: 'string',
        description: 'Directory to search in (defaults to cwd)',
      },
    },
    required: ['pattern'],
  },
  isEnabled: () => true,
  isReadOnly: () => true,
  execute: async (input, context): Promise<ToolResult> => {
    let pattern = input.pattern as string;
    const searchDir = resolve(context.cwd, (input.path as string) || '.');

    if (!pattern.startsWith('**/') && !pattern.startsWith('/')) {
      pattern = `**/${pattern}`;
    }

    try {
      const matches = await glob(pattern, {
        cwd: searchDir,
        nodir: false,
        ignore: ['**/node_modules/**', '**/.git/**'],
      });

      if (matches.length === 0) {
        return { output: 'No files matched the pattern.' };
      }

      const result = matches.slice(0, 200).join('\n');
      const suffix = matches.length > 200 ? `\n... and ${matches.length - 200} more` : '';
      return { output: `${result}${suffix}` };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { output: `Error searching files: ${msg}`, isError: true };
    }
  },
};
