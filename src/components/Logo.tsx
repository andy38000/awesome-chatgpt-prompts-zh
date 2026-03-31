import React from 'react';
import { Text, Box } from 'ink';
import { VERSION } from '../constants/version.js';
import { getModelDisplayName } from '../constants/models.js';

interface LogoProps {
  model: string;
}

export function Logo({ model }: LogoProps): React.ReactElement {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text bold color="magenta">
        {'  ╔═══════════════════════════════════════╗'}
      </Text>
      <Text bold color="magenta">
        {'  ║         '}
        <Text color="white" bold>Claude Code</Text>
        <Text color="gray"> v{VERSION}</Text>
        {'           ║'}
      </Text>
      <Text bold color="magenta">
        {'  ╚═══════════════════════════════════════╝'}
      </Text>
      <Box marginTop={1}>
        <Text dimColor>
          Model: <Text color="cyan">{getModelDisplayName(model)}</Text>
          {' • '}
          Type <Text color="yellow">/help</Text> for commands
          {' • '}
          <Text color="yellow">Ctrl+C</Text> to cancel
        </Text>
      </Box>
    </Box>
  );
}
