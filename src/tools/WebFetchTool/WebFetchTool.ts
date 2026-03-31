import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const DESCRIPTION = `Fetch content from a URL and return its contents in readable text format.
Use this when you need to retrieve and analyze webpage content.
The URL must be a fully-formed, valid URL.`;

export const WebFetchTool: ToolDefinition = {
  name: 'WebFetchTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      url: {
        type: 'string',
        description: 'The URL to fetch',
      },
    },
    required: ['url'],
  },
  isEnabled: () => true,
  isReadOnly: () => true,
  execute: async (input): Promise<ToolResult> => {
    const url = input.url as string;

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);

      const response = await fetch(url, {
        signal: controller.signal,
        headers: { 'User-Agent': 'Claude-Code/2.1.88' },
      });

      clearTimeout(timeout);

      if (!response.ok) {
        return { output: `HTTP ${response.status}: ${response.statusText}`, isError: true };
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text') && !contentType.includes('json') && !contentType.includes('xml')) {
        return { output: `Cannot read binary content (${contentType})`, isError: true };
      }

      const text = await response.text();
      const truncated = text.length > 50000 ? text.slice(0, 50000) + '\n\n... (truncated)' : text;
      return { output: truncated };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      return { output: `Fetch error: ${msg}`, isError: true };
    }
  },
};
