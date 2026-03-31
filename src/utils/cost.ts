import { MODEL_PRICING } from '../constants/models.js';
import type { MessageUsage } from '../types/message.js';

export function calculateCost(model: string, usage: MessageUsage): number {
  const pricing = MODEL_PRICING[model];
  if (!pricing) return 0;

  let cost = 0;
  cost += (usage.inputTokens / 1_000_000) * pricing.inputPer1M;
  cost += (usage.outputTokens / 1_000_000) * pricing.outputPer1M;
  if (usage.cacheCreationInputTokens && pricing.cacheWritePer1M) {
    cost += (usage.cacheCreationInputTokens / 1_000_000) * pricing.cacheWritePer1M;
  }
  if (usage.cacheReadInputTokens && pricing.cacheReadPer1M) {
    cost += (usage.cacheReadInputTokens / 1_000_000) * pricing.cacheReadPer1M;
  }

  return cost;
}

export function formatCost(cost: number): string {
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}k`;
  return `${tokens}`;
}
