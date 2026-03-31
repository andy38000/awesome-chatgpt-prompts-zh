import type { ToolDefinition } from '../types/tool.js';
import { BashTool } from './BashTool/BashTool.js';
import { FileReadTool } from './FileReadTool/FileReadTool.js';
import { FileWriteTool } from './FileWriteTool/FileWriteTool.js';
import { FileEditTool } from './FileEditTool/FileEditTool.js';
import { GlobTool } from './GlobTool/GlobTool.js';
import { GrepTool } from './GrepTool/GrepTool.js';
import { WebFetchTool } from './WebFetchTool/WebFetchTool.js';
import { TodoWriteTool } from './TodoWriteTool/TodoWriteTool.js';

export function getAllTools(): ToolDefinition[] {
  return [
    BashTool,
    FileReadTool,
    FileWriteTool,
    FileEditTool,
    GlobTool,
    GrepTool,
    WebFetchTool,
    TodoWriteTool,
  ].filter(t => t.isEnabled());
}

export function findToolByName(name: string): ToolDefinition | undefined {
  return getAllTools().find(t =>
    t.name === name || t.name.toLowerCase() === name.toLowerCase()
  );
}

export function getToolsForAPI(): Array<{
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}> {
  return getAllTools().map(t => ({
    name: t.name,
    description: t.description,
    input_schema: t.inputSchema as unknown as Record<string, unknown>,
  }));
}
