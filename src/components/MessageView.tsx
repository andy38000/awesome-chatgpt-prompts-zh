import React from 'react';
import { Text, Box } from 'ink';
import type { Message } from '../types/message.js';

interface MessageViewProps {
  message: Message;
}

export function MessageView({ message }: MessageViewProps): React.ReactElement {
  if (message.type === 'user') {
    return (
      <Box marginY={0}>
        <Text bold color="blue">{'❯ '}</Text>
        <Text>{message.content}</Text>
      </Box>
    );
  }

  if (message.type === 'system') {
    return (
      <Box marginY={0}>
        <Text dimColor italic>{'⚙ '}{message.content}</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" marginY={0}>
      {message.thinking && (
        <Box>
          <Text dimColor italic>{'💭 '}{message.thinking.slice(0, 200)}...</Text>
        </Box>
      )}
      {message.toolUse?.map((tool, i) => (
        <Box key={i} flexDirection="column" marginLeft={2}>
          <Text color="yellow">{'🔧 '}{tool.name}</Text>
          {tool.output && (
            <Box marginLeft={2}>
              <Text dimColor>
                {tool.output.length > 300
                  ? tool.output.slice(0, 300) + '...'
                  : tool.output}
              </Text>
            </Box>
          )}
        </Box>
      ))}
      {message.content && (
        <Box>
          <Text color="green">{'◆ '}</Text>
          <Text>{message.content}</Text>
        </Box>
      )}
    </Box>
  );
}
