import Anthropic from '@anthropic-ai/sdk';
import type { MessageParam, ContentBlockParam, ToolUseBlock, ToolResultBlockParam, TextBlock } from '@anthropic-ai/sdk/resources/messages.mjs';
import { getAnthropicClient } from './services/api/client.js';
import { buildSystemPrompt } from './services/api/systemPrompt.js';
import { getAllTools, findToolByName, getToolsForAPI } from './tools/index.js';
import { calculateCost, formatCost } from './utils/cost.js';
import type { Message, MessageUsage, ToolUseResult } from './types/message.js';
import type { ToolDefinition, ToolContext } from './types/tool.js';
import type { AppState } from './state/AppState.js';

export interface QueryEngineConfig {
  getAppState: () => AppState;
  setAppState: (fn: (prev: AppState) => AppState) => void;
  onText?: (text: string) => void;
  onThinking?: (text: string) => void;
  onToolUse?: (name: string, input: Record<string, unknown>) => void;
  onToolResult?: (name: string, output: string, isError: boolean) => void;
  onError?: (error: Error) => void;
  onDone?: (message: Message) => void;
  onStreamText?: (delta: string) => void;
}

export class QueryEngine {
  private config: QueryEngineConfig;
  private conversationHistory: MessageParam[] = [];

  constructor(config: QueryEngineConfig) {
    this.config = config;
  }

  clearHistory(): void {
    this.conversationHistory = [];
  }

  getHistory(): MessageParam[] {
    return [...this.conversationHistory];
  }

  async submitMessage(
    userPrompt: string,
    abortSignal?: AbortSignal,
  ): Promise<Message> {
    const { getAppState, setAppState } = this.config;
    const state = getAppState();
    const tools = getAllTools();
    const client = getAnthropicClient();

    const systemPrompt = await buildSystemPrompt(tools);

    this.conversationHistory.push({
      role: 'user',
      content: userPrompt,
    });

    let fullText = '';
    let thinkingText = '';
    const toolUseResults: ToolUseResult[] = [];
    let totalUsage: MessageUsage = { inputTokens: 0, outputTokens: 0 };

    let continueLoop = true;
    while (continueLoop) {
      if (abortSignal?.aborted) break;

      const apiTools = getToolsForAPI();

      try {
        const requestParams: Anthropic.MessageCreateParams = {
          model: state.model,
          max_tokens: 16384,
          system: systemPrompt,
          tools: apiTools as Anthropic.Tool[],
          messages: this.conversationHistory,
        };

        if (state.thinkingEnabled) {
          requestParams.model = state.model;
        }

        const stream = await client.messages.stream(requestParams);
        const response = await stream.finalMessage();

        if (response.usage) {
          totalUsage.inputTokens += response.usage.input_tokens;
          totalUsage.outputTokens += response.usage.output_tokens;
        }

        const textBlocks: string[] = [];
        const toolUseBlocks: ToolUseBlock[] = [];

        for (const block of response.content) {
          if (block.type === 'text') {
            textBlocks.push(block.text);
            this.config.onStreamText?.(block.text);
          } else if (block.type === 'tool_use') {
            toolUseBlocks.push(block);
          }
        }

        const turnText = textBlocks.join('');
        if (turnText) {
          fullText += (fullText ? '\n' : '') + turnText;
          this.config.onText?.(turnText);
        }

        this.conversationHistory.push({
          role: 'assistant',
          content: response.content,
        });

        if (toolUseBlocks.length === 0) {
          continueLoop = false;
          break;
        }

        const toolResults: ToolResultBlockParam[] = [];
        for (const toolUse of toolUseBlocks) {
          if (abortSignal?.aborted) break;

          this.config.onToolUse?.(toolUse.name, toolUse.input as Record<string, unknown>);

          const tool = findToolByName(toolUse.name);
          if (!tool) {
            const errorResult = `Error: Unknown tool ${toolUse.name}`;
            toolResults.push({
              type: 'tool_result',
              tool_use_id: toolUse.id,
              content: errorResult,
              is_error: true,
            });
            this.config.onToolResult?.(toolUse.name, errorResult, true);
            toolUseResults.push({
              id: toolUse.id,
              name: toolUse.name,
              input: toolUse.input as Record<string, unknown>,
              output: errorResult,
              isError: true,
            });
            continue;
          }

          const toolContext: ToolContext = {
            cwd: state.cwd,
            abortSignal,
            messages: [],
          };

          try {
            const result = await tool.execute(
              toolUse.input as Record<string, unknown>,
              toolContext,
            );

            const truncatedOutput = result.output.length > 100000
              ? result.output.slice(0, 100000) + '\n... (truncated)'
              : result.output;

            toolResults.push({
              type: 'tool_result',
              tool_use_id: toolUse.id,
              content: truncatedOutput,
              is_error: result.isError,
            });

            this.config.onToolResult?.(toolUse.name, truncatedOutput, result.isError ?? false);
            toolUseResults.push({
              id: toolUse.id,
              name: toolUse.name,
              input: toolUse.input as Record<string, unknown>,
              output: truncatedOutput,
              isError: result.isError,
            });
          } catch (err) {
            const errMsg = err instanceof Error ? err.message : String(err);
            toolResults.push({
              type: 'tool_result',
              tool_use_id: toolUse.id,
              content: `Error: ${errMsg}`,
              is_error: true,
            });
            this.config.onToolResult?.(toolUse.name, errMsg, true);
            toolUseResults.push({
              id: toolUse.id,
              name: toolUse.name,
              input: toolUse.input as Record<string, unknown>,
              output: errMsg,
              isError: true,
            });
          }
        }

        this.conversationHistory.push({
          role: 'user',
          content: toolResults,
        });

        if (response.stop_reason === 'end_turn') {
          continueLoop = false;
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        this.config.onError?.(error);
        continueLoop = false;

        const errMessage: Message = {
          type: 'assistant',
          uuid: crypto.randomUUID(),
          content: `Error: ${error.message}`,
          model: state.model,
          usage: totalUsage,
          timestamp: Date.now(),
        };
        return errMessage;
      }
    }

    const cost = calculateCost(state.model, totalUsage);
    setAppState(prev => ({
      ...prev,
      totalCost: prev.totalCost + cost,
      totalInputTokens: prev.totalInputTokens + totalUsage.inputTokens,
      totalOutputTokens: prev.totalOutputTokens + totalUsage.outputTokens,
    }));

    const assistantMessage: Message = {
      type: 'assistant',
      uuid: crypto.randomUUID(),
      content: fullText,
      model: state.model,
      usage: totalUsage,
      toolUse: toolUseResults.length > 0 ? toolUseResults : undefined,
      thinking: thinkingText || undefined,
      timestamp: Date.now(),
    };

    this.config.onDone?.(assistantMessage);
    return assistantMessage;
  }
}
