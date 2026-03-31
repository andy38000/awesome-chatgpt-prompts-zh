import type { ToolDefinition, ToolResult } from '../../types/tool.js';

interface TodoItem {
  id: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
}

const todos: Map<string, TodoItem> = new Map();

const DESCRIPTION = `Manage a structured task list for the current coding session.
Create, update, and track progress on coding tasks.`;

export const TodoWriteTool: ToolDefinition = {
  name: 'TodoWriteTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      todos: {
        type: 'string',
        description: 'JSON array of todo items: [{id, content, status}]',
      },
      merge: {
        type: 'string',
        description: 'If "true", merge with existing todos; if "false", replace all',
      },
    },
    required: ['todos'],
  },
  isEnabled: () => true,
  execute: async (input): Promise<ToolResult> => {
    try {
      const items: TodoItem[] = typeof input.todos === 'string'
        ? JSON.parse(input.todos)
        : input.todos as TodoItem[];
      const merge = input.merge === 'true' || input.merge === true;

      if (!merge) {
        todos.clear();
      }

      for (const item of items) {
        todos.set(item.id, item);
      }

      const output = Array.from(todos.values())
        .map(t => `[${t.status}] ${t.id}: ${t.content}`)
        .join('\n');

      return { output: `Updated todos:\n${output}` };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { output: `Error updating todos: ${msg}`, isError: true };
    }
  },
};
