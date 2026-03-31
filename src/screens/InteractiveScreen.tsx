import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Text, Box, useInput, useApp } from 'ink';
import TextInput from 'ink-text-input';
import type { AppState } from '../state/AppState.js';
import type { Message } from '../types/message.js';
import { Logo } from '../components/Logo.js';
import { MessageView } from '../components/MessageView.js';
import { StatusLine } from '../components/StatusLine.js';
import { Spinner } from '../components/Spinner.js';
import { ToolProgress } from '../components/ToolProgress.js';
import { QueryEngine } from '../QueryEngine.js';
import { findCommand, isSlashCommand } from '../commands/index.js';

interface InteractiveScreenProps {
  appState: AppState;
  setAppState: (fn: (prev: AppState) => AppState) => void;
}

export function InteractiveScreen({ appState, setAppState }: InteractiveScreenProps): React.ReactElement {
  const { exit } = useApp();
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [currentTool, setCurrentTool] = useState<{ name: string; input?: Record<string, unknown> } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const engineRef = useRef<QueryEngine | null>(null);

  if (!engineRef.current) {
    engineRef.current = new QueryEngine({
      getAppState: () => appState,
      setAppState,
      onText: (text) => {
        setStreamingText('');
        setCurrentTool(null);
      },
      onStreamText: (delta) => {
        setStreamingText(prev => prev + delta);
      },
      onToolUse: (name, input) => {
        setCurrentTool({ name, input });
        setStreamingText('');
      },
      onToolResult: (name, output, isError) => {
        setCurrentTool(null);
        setMessages(prev => [...prev, {
          type: 'system',
          uuid: crypto.randomUUID(),
          content: `${isError ? '✗' : '✓'} ${name}${isError ? ' (error)' : ''}`,
          timestamp: Date.now(),
        }]);
      },
      onError: (err) => {
        setIsLoading(false);
        setCurrentTool(null);
        setStreamingText('');
        setMessages(prev => [...prev, {
          type: 'system',
          uuid: crypto.randomUUID(),
          content: `Error: ${err.message}`,
          timestamp: Date.now(),
        }]);
      },
    });
  }

  useEffect(() => {
    if (engineRef.current) {
      (engineRef.current as any).config.getAppState = () => appState;
    }
  }, [appState]);

  const handleSubmit = useCallback(async (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;

    setInputValue('');

    if (isSlashCommand(trimmed)) {
      const found = findCommand(trimmed);
      if (found) {
        const result = await found.command.execute(found.args, {
          appState,
          setAppState,
          messages,
          clearMessages: () => {
            setMessages([]);
            engineRef.current?.clearHistory();
          },
        });
        if (result?.output) {
          setMessages(prev => [...prev, {
            type: 'system',
            uuid: crypto.randomUUID(),
            content: result.output!,
            timestamp: Date.now(),
          }]);
        }
        return;
      }
      setMessages(prev => [...prev, {
        type: 'system',
        uuid: crypto.randomUUID(),
        content: `Unknown command: ${trimmed.split(/\s/)[0]}. Type /help for available commands.`,
        timestamp: Date.now(),
      }]);
      return;
    }

    const userMessage: Message = {
      type: 'user',
      uuid: crypto.randomUUID(),
      content: trimmed,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setStreamingText('');

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const response = await engineRef.current!.submitMessage(trimmed, abort.signal);
      setMessages(prev => [...prev, response]);
    } catch (err) {
      if (!abort.signal.aborted) {
        setMessages(prev => [...prev, {
          type: 'system',
          uuid: crypto.randomUUID(),
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
          timestamp: Date.now(),
        }]);
      }
    } finally {
      setIsLoading(false);
      setStreamingText('');
      setCurrentTool(null);
      abortRef.current = null;
    }
  }, [isLoading, appState, setAppState, messages]);

  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      if (isLoading && abortRef.current) {
        abortRef.current.abort();
        setIsLoading(false);
        setStreamingText('');
        setCurrentTool(null);
        setMessages(prev => [...prev, {
          type: 'system',
          uuid: crypto.randomUUID(),
          content: '⚠ Request cancelled by user',
          timestamp: Date.now(),
        }]);
      } else {
        exit();
      }
    }
    if (key.ctrl && input === 'd') {
      exit();
    }
  });

  const visibleMessages = messages.slice(-50);

  return (
    <Box flexDirection="column" width="100%">
      <Logo model={appState.model} />

      {visibleMessages.map((msg) => (
        <MessageView key={msg.uuid} message={msg} />
      ))}

      {isLoading && (
        <Box flexDirection="column" marginY={0}>
          {streamingText && (
            <Box>
              <Text color="green">{'◆ '}</Text>
              <Text>{streamingText}</Text>
            </Box>
          )}
          {currentTool ? (
            <ToolProgress toolName={currentTool.name} input={currentTool.input} />
          ) : (
            <Box marginLeft={2}>
              <Spinner label="Thinking..." />
            </Box>
          )}
        </Box>
      )}

      <Box marginTop={1}>
        <StatusLine
          model={appState.model}
          totalCost={appState.totalCost}
          totalInputTokens={appState.totalInputTokens}
          totalOutputTokens={appState.totalOutputTokens}
          isLoading={isLoading}
        />
      </Box>

      <Box marginTop={0}>
        <Text bold color="magenta">{'❯ '}</Text>
        <TextInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          placeholder={isLoading ? 'Processing...' : 'Type a message or /help for commands...'}
        />
      </Box>
    </Box>
  );
}
