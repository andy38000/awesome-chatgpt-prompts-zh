import React from 'react';
import { Text, Box } from 'ink';
import { Spinner } from './Spinner.js';

interface ToolProgressProps {
  toolName: string;
  input?: Record<string, unknown>;
}

export function ToolProgress({ toolName, input }: ToolProgressProps): React.ReactElement {
  let label = toolName;
  if (toolName === 'BashTool' && input?.command) {
    const cmd = String(input.command);
    label = `Running: ${cmd.length > 60 ? cmd.slice(0, 60) + '...' : cmd}`;
  } else if (toolName === 'FileReadTool' && input?.path) {
    label = `Reading: ${input.path}`;
  } else if (toolName === 'FileWriteTool' && input?.path) {
    label = `Writing: ${input.path}`;
  } else if (toolName === 'FileEditTool' && input?.path) {
    label = `Editing: ${input.path}`;
  } else if (toolName === 'GlobTool' && input?.pattern) {
    label = `Searching: ${input.pattern}`;
  } else if (toolName === 'GrepTool' && input?.pattern) {
    label = `Grep: ${input.pattern}`;
  } else if (toolName === 'WebFetchTool' && input?.url) {
    label = `Fetching: ${input.url}`;
  }

  return (
    <Box marginLeft={2}>
      <Spinner label={label} />
    </Box>
  );
}
