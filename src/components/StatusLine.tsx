import React from 'react';
import { Text, Box } from 'ink';
import { getModelDisplayName } from '../constants/models.js';
import { formatCost, formatTokens } from '../utils/cost.js';

interface StatusLineProps {
  model: string;
  totalCost: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  isLoading: boolean;
}

export function StatusLine({
  model,
  totalCost,
  totalInputTokens,
  totalOutputTokens,
  isLoading,
}: StatusLineProps): React.ReactElement {
  return (
    <Box>
      <Text dimColor>
        {isLoading ? '⏳ ' : ''}
        <Text color="cyan">{getModelDisplayName(model)}</Text>
        {' • '}
        <Text color="green">↑{formatTokens(totalInputTokens)}</Text>
        {' '}
        <Text color="yellow">↓{formatTokens(totalOutputTokens)}</Text>
        {' • '}
        <Text color="magenta">{formatCost(totalCost)}</Text>
      </Text>
    </Box>
  );
}
