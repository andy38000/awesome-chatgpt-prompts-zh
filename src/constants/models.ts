export const DEFAULT_MODEL = 'claude-sonnet-4-20250514';

export const AVAILABLE_MODELS = [
  'claude-sonnet-4-20250514',
  'claude-opus-4-20250514',
  'claude-3-5-haiku-20241022',
] as const;

export type ModelName = typeof AVAILABLE_MODELS[number];

export const MODEL_PRICING: Record<string, { inputPer1M: number; outputPer1M: number; cacheWritePer1M?: number; cacheReadPer1M?: number }> = {
  'claude-sonnet-4-20250514': { inputPer1M: 3, outputPer1M: 15, cacheWritePer1M: 3.75, cacheReadPer1M: 0.30 },
  'claude-opus-4-20250514': { inputPer1M: 15, outputPer1M: 75, cacheWritePer1M: 18.75, cacheReadPer1M: 1.50 },
  'claude-3-5-haiku-20241022': { inputPer1M: 0.80, outputPer1M: 4, cacheWritePer1M: 1, cacheReadPer1M: 0.08 },
};

export function getModelDisplayName(model: string): string {
  if (model.includes('opus')) return 'Opus';
  if (model.includes('sonnet')) return 'Sonnet';
  if (model.includes('haiku')) return 'Haiku';
  return model;
}
