import { request } from "./client";

export type ProviderModel = { id: string; name: string };

export type GroqUsage = {
  model: string;
  limit_tokens: number | null;
  remaining_tokens: number | null;
  reset_tokens: string | null;
  limit_requests: number | null;
  remaining_requests: number | null;
  reset_requests: string | null;
  session_requests: number;
  session_tokens: number;
  has_header_data: boolean;
  low_budget: boolean;
  rate_limited_until: number | null;
  warning: string;
};

export type ProviderOptions = {
  gemini_model: string;
  groq_configured: boolean;
  openrouter_configured: boolean;
  groq_models: ProviderModel[];
  openrouter_models: ProviderModel[];
  openrouter_requests_per_day: number;
  openrouter_requests_per_minute: number;
  low_budget_fraction: number;
  groq_usage: GroqUsage[];
  catalog_error: string;
};

export const getProviderOptions = (signal?: AbortSignal) =>
  request<ProviderOptions>("/api/providers/options", { signal });
