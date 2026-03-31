import { execFile } from 'child_process';
import { promisify } from 'util';
import { resolve } from 'path';
import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const execFileAsync = promisify(execFile);

const DESCRIPTION = `Search for text patterns in files using ripgrep (rg).
Supports regex patterns. Results show matching file paths and line content.
Use the glob parameter to filter by file type.`;

export const GrepTool: ToolDefinition = {
  name: 'GrepTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      pattern: {
        type: 'string',
        description: 'The regex pattern to search for',
      },
      path: {
        type: 'string',
        description: 'File or directory to search in (defaults to cwd)',
      },
      glob: {
        type: 'string',
        description: 'Glob pattern to filter files (e.g., "*.ts")',
      },
    },
    required: ['pattern'],
  },
  isEnabled: () => true,
  isReadOnly: () => true,
  execute: async (input, context): Promise<ToolResult> => {
    const pattern = input.pattern as string;
    const searchPath = resolve(context.cwd, (input.path as string) || '.');
    const fileGlob = input.glob as string | undefined;

    const args = ['--color=never', '--line-number', '--no-heading'];
    if (fileGlob) {
      args.push('--glob', fileGlob);
    }
    args.push('--', pattern, searchPath);

    try {
      const { stdout } = await execFileAsync('rg', args, {
        maxBuffer: 1024 * 1024 * 10,
      });
      const lines = stdout.trim().split('\n');
      if (lines.length > 500) {
        return { output: lines.slice(0, 500).join('\n') + `\n... (${lines.length - 500} more matches)` };
      }
      return { output: stdout.trim() || 'No matches found.' };
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'code' in err && err.code === 1) {
        return { output: 'No matches found.' };
      }
      try {
        const args2 = ['-rn', '--color=never'];
        if (fileGlob) args2.push('--include', fileGlob);
        args2.push(pattern, searchPath);
        const { stdout } = await execFileAsync('grep', args2, { maxBuffer: 1024 * 1024 * 10 });
        return { output: stdout.trim() || 'No matches found.' };
      } catch {
        return { output: 'No matches found.' };
      }
    }
  },
};
