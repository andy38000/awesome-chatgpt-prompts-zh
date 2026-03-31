import { spawn } from 'child_process';
import type { ToolDefinition, ToolResult } from '../../types/tool.js';

const DESCRIPTION = `Executes a given command in a shell session with optional timeout.
Use this tool to run system commands and scripts. The shell is stateful across calls - working directory and environment variables persist.

Important:
- Do not use this tool for file reading (use FileReadTool) or file editing (use FileEditTool/FileWriteTool)
- Commands that take longer than the timeout will be terminated
- For long-running processes, consider using background execution`;

export const BashTool: ToolDefinition = {
  name: 'BashTool',
  description: DESCRIPTION,
  inputSchema: {
    type: 'object',
    properties: {
      command: {
        type: 'string',
        description: 'The command to execute in the shell',
      },
      timeout: {
        type: 'number',
        description: 'Timeout in milliseconds (default: 30000)',
        default: 30000,
      },
    },
    required: ['command'],
  },
  isEnabled: () => true,
  execute: async (input, context): Promise<ToolResult> => {
    const command = input.command as string;
    const timeout = (input.timeout as number) || 30000;
    const cwd = context.cwd;

    return new Promise((resolve) => {
      const chunks: Buffer[] = [];
      const errChunks: Buffer[] = [];

      const proc = spawn('bash', ['-c', command], {
        cwd,
        env: { ...process.env },
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      const timer = setTimeout(() => {
        proc.kill('SIGTERM');
        setTimeout(() => proc.kill('SIGKILL'), 2000);
      }, timeout);

      proc.stdout?.on('data', (chunk: Buffer) => chunks.push(chunk));
      proc.stderr?.on('data', (chunk: Buffer) => errChunks.push(chunk));

      proc.on('close', (code) => {
        clearTimeout(timer);
        const stdout = Buffer.concat(chunks).toString();
        const stderr = Buffer.concat(errChunks).toString();
        const combined = [
          stdout && `${stdout}`,
          stderr && `stderr:\n${stderr}`,
          `Exit code: ${code ?? 'unknown'}`,
        ].filter(Boolean).join('\n');

        resolve({
          output: combined,
          isError: code !== 0,
        });
      });

      proc.on('error', (err) => {
        clearTimeout(timer);
        resolve({
          output: `Error executing command: ${err.message}`,
          isError: true,
        });
      });
    });
  },
};
