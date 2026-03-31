import { readFile, writeFile } from 'fs/promises';
import { resolve } from 'path';
import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const DESCRIPTION = `Performs exact string replacements in files.
Provide old_string and new_string to replace a specific occurrence. The old_string must be unique within the file or the edit will fail.
Use replace_all: true to replace all occurrences.`;

export const FileEditTool: ToolDefinition = {
  name: 'FileEditTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      path: {
        type: 'string',
        description: 'The absolute path to the file to edit',
      },
      old_string: {
        type: 'string',
        description: 'The exact text to replace',
      },
      new_string: {
        type: 'string',
        description: 'The replacement text',
      },
      replace_all: {
        type: 'string',
        description: 'If "true", replace all occurrences (default: false)',
      },
    },
    required: ['path', 'old_string', 'new_string'],
  },
  isEnabled: () => true,
  execute: async (input, context): Promise<ToolResult> => {
    const filePath = resolve(context.cwd, input.path as string);
    const oldString = input.old_string as string;
    const newString = input.new_string as string;
    const replaceAll = input.replace_all === 'true' || input.replace_all === true;

    try {
      const content = await readFile(filePath, 'utf-8');

      if (!content.includes(oldString)) {
        return {
          output: `Error: old_string not found in file. Make sure it matches exactly.`,
          isError: true,
        };
      }

      if (!replaceAll) {
        const occurrences = content.split(oldString).length - 1;
        if (occurrences > 1) {
          return {
            output: `Error: old_string appears ${occurrences} times. Provide more context to make it unique, or use replace_all.`,
            isError: true,
          };
        }
      }

      const newContent = replaceAll
        ? content.replaceAll(oldString, newString)
        : content.replace(oldString, newString);

      await writeFile(filePath, newContent, 'utf-8');
      return { output: `Successfully edited ${filePath}` };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { output: `Error editing file: ${msg}`, isError: true };
    }
  },
};
