import { readFile, stat } from 'fs/promises';
import { resolve } from 'path';
import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const DESCRIPTION = `Reads a file from the local filesystem. Returns the content with line numbers.
Use this tool to read source code, configuration files, or any text content.
Supports optional line offset and limit for reading portions of large files.`;

export const FileReadTool: ToolDefinition = {
  name: 'FileReadTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'The absolute path of the file to read',
      },
      offset: {
        type: 'number',
        description: 'Line number to start reading from (1-indexed)',
      },
      limit: {
        type: 'number',
        description: 'Maximum number of lines to read',
      },
    },
    required: ['path'],
  },
  isEnabled: () => true,
  isReadOnly: () => true,
  execute: async (input, context): Promise<ToolResult> => {
    const filePath = resolve(context.cwd, input.path as string);

    try {
      const fileStat = await stat(filePath);
      if (fileStat.isDirectory()) {
        return { output: `Error: ${filePath} is a directory, not a file`, isError: true };
      }

      const content = await readFile(filePath, 'utf-8');
      if (!content) {
        return { output: 'File is empty.' };
      }

      const lines = content.split('\n');
      const offset = Math.max(1, (input.offset as number) || 1);
      const limit = (input.limit as number) || lines.length;
      const selected = lines.slice(offset - 1, offset - 1 + limit);

      const numbered = selected.map((line, i) => {
        const lineNum = String(offset + i).padStart(6, ' ');
        return `${lineNum}|${line}`;
      }).join('\n');

      return { output: numbered };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { output: `Error reading file: ${msg}`, isError: true };
    }
  },
};
