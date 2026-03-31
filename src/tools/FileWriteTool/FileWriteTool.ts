import { writeFile, mkdir } from 'fs/promises';
import { resolve, dirname } from 'path';
import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const DESCRIPTION = `Writes a file to the local filesystem. Creates parent directories if needed.
Will overwrite the existing file if there is one at the provided path.
Prefer editing existing files over creating new ones when possible.`;

export const FileWriteTool: ToolDefinition = {
  name: 'FileWriteTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'The absolute path to the file to write',
      },
      contents: {
        type: 'string',
        description: 'The contents to write to the file',
      },
    },
    required: ['path', 'contents'],
  },
  isEnabled: () => true,
  execute: async (input, context): Promise<ToolResult> => {
    const filePath = resolve(context.cwd, input.path as string);
    const contents = input.contents as string;

    try {
      await mkdir(dirname(filePath), { recursive: true });
      await writeFile(filePath, contents, 'utf-8');
      const lineCount = contents.split('\n').length;
      return { output: `Wrote ${lineCount} lines to ${filePath}` };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { output: `Error writing file: ${msg}`, isError: true };
    }
  },
};
