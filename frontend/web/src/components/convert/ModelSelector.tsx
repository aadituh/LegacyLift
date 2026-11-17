"use client";
import { useEffect, useState, useSyncExternalStore } from "react";
import { SegmentedControl } from "@/components/ui/SegmentedControl";
import {
  getProviderOptions,
  type GroqUsage,
  type ProviderOptions,
} from "@/lib/api/providers";
import {
  DEFAULT_SELECTION,
  readModelSelection,
  subscribeModelSelection,
  writeModelSelection,
  type ModelMode,
  type ModelSelection,
} from "@/lib/model-selection";

export function ModelSelector({ liveUsage }: { liveUsage?: GroqUsage | null }) {
  const selection = useSyncExternalStore(
    subscribeModelSelection,
    readModelSelection,
    () => DEFAULT_SELECTION,
  );
  const [options, setOptions] = useState<ProviderOptions | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getProviderOptions(controller.signal)
      .then((next) => {
        setOptions(next);
        setLoadError("");
        const current = readModelSelection();
        const groqModel = current.groqModel || next.groq_models[0]?.id || "";
        const openrouterModel =
          current.openrouterModel || next.openrouter_models[0]?.id || "";
        if (
          groqModel !== current.groqModel ||
          openrouterModel !== current.openrouterModel
        )
          writeModelSelection({ ...current, groqModel, openrouterModel });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError")
          return;
        setLoadError(
          error instanceof Error
            ? error.message
            : "The model list could not be loaded.",
        );
      });
    return () => controller.abort();
  }, []);

  function update(next: ModelSelection) {
    writeModelSelection(next);
  }

  const groqModel = selection.groqModel || options?.groq_models[0]?.id || "";
  const openrouterModel =
    selection.openrouterModel || options?.openrouter_models[0]?.id || "";
  const usage = usageFor(groqModel, liveUsage, options?.groq_usage ?? []);
  const day = options?.openrouter_requests_per_day ?? 50;
  const minute = options?.openrouter_requests_per_minute ?? 20;

  return (
    <section className="model-selector" aria-label="Translation model">
      <div className="model-selector-row">
        <SegmentedControl<ModelMode>
          label="Translation provider"
          value={selection.mode}
          onChange={(mode) => update({ ...selection, mode })}
          options={[
            { value: "auto", label: "Auto" },
            { value: "gemini", label: "Gemini" },
            { value: "groq", label: "Groq" },
            { value: "openrouter", label: "OpenRouter" },
          ]}
        />
        {selection.mode === "groq" && (
          <ModelSelect
            id="groq-model"
            label="Groq model"
            value={groqModel}
            models={options?.groq_models ?? []}
            onChange={(groqModelId) =>
              update({ ...selection, groqModel: groqModelId })
            }
          />
        )}
        {selection.mode === "openrouter" && (
          <ModelSelect
            id="openrouter-model"
            label="OpenRouter model"
            value={openrouterModel}
            models={options?.openrouter_models ?? []}
            onChange={(openrouterModelId) =>
              update({ ...selection, openrouterModel: openrouterModelId })
            }
          />
        )}
      </div>
      {selection.mode === "auto" && (
        <p className="hint">
          Auto sends a small prompt to Groq when Groq has budget, and uses
          Gemini for a large prompt. Gemini stays the fallback.
        </p>
      )}
      {selection.mode === "gemini" && (
        <p className="hint">
          Gemini {options?.gemini_model ?? "gemini-3.5-flash-lite"} reviews this
          project. This is the existing model.
        </p>
      )}
      {selection.mode === "groq" && !options?.groq_configured && (
        <p className="hint">
          Add LEGACYLIFT_GROQ_API_KEY on the API before a Groq review can be sent.
        </p>
      )}
      {(selection.mode === "groq" || selection.mode === "auto") && (
        <GroqBudget
          usage={usage}
          lowFraction={options?.low_budget_fraction ?? 0.15}
        />
      )}
      {selection.mode === "openrouter" && (
        <p className="notice" role="note">
          Maximum of {day} requests per day. Maximum of {minute} requests per
          minute. OpenRouter limits are not tracked with a progress bar.
        </p>
      )}
      {loadError && <p className="hint">{loadError}</p>}
      {options?.catalog_error && (
        <p className="hint">{options.catalog_error}</p>
      )}
    </section>
  );
}

function ModelSelect({
  id,
  label,
  value,
  models,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  models: { id: string; name: string }[];
  onChange: (id: string) => void;
}) {
  const known = models.some((model) => model.id === value);
  return (
    <div className="field model-field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {!known && value && <option value={value}>{value}</option>}
        {models.length === 0 && <option value="">No models loaded yet</option>}
        {models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function GroqBudget({
  usage,
  lowFraction,
}: {
  usage: GroqUsage | null;
  lowFraction: number;
}) {
  if (!usage || !usage.has_header_data) {
    return (
      <div className="budget-list">
        <p className="hint">No Groq usage data yet.</p>
        {usage && usage.session_requests > 0 && (
          <p className="hint">
            This session: {usage.session_requests} request
            {usage.session_requests === 1 ? "" : "s"}, {usage.session_tokens}{" "}
            tokens. Provider limits were not reported.
          </p>
        )}
      </div>
    );
  }
  return (
    <div className="budget-list">
      <BudgetMeter
        label="Tokens per minute remaining"
        remaining={usage.remaining_tokens}
        limit={usage.limit_tokens}
        reset={usage.reset_tokens}
        low={isLow(usage.remaining_tokens, usage.limit_tokens, lowFraction)}
      />
      <BudgetMeter
        label="Requests per day remaining"
        remaining={usage.remaining_requests}
        limit={usage.limit_requests}
        reset={usage.reset_requests}
        low={isLow(usage.remaining_requests, usage.limit_requests, lowFraction)}
      />
      {usage.warning && (
        <p className="notice warning" role="status">
          {usage.warning}
        </p>
      )}
      <p className="hint">
        This session: {usage.session_requests} request
        {usage.session_requests === 1 ? "" : "s"}, {usage.session_tokens}{" "}
        tokens.
      </p>
    </div>
  );
}

function BudgetMeter({
  label,
  remaining,
  limit,
  reset,
  low,
}: {
  label: string;
  remaining: number | null;
  limit: number | null;
  reset: string | null;
  low: boolean;
}) {
  const width =
    remaining != null && limit != null && limit > 0
      ? Math.max(0, Math.min(100, (remaining / limit) * 100))
      : 0;
  return (
    <div className="budget-meter">
      <div className="budget-label">
        <span>{label}</span>
        <span>
          {remaining ?? "—"} / {limit ?? "—"}
          {reset ? ` · resets in ${reset}` : ""}
        </span>
      </div>
      <div
        className="budget-track"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={limit ?? undefined}
        aria-valuenow={remaining ?? undefined}
      >
        <div
          className={low ? "budget-fill low" : "budget-fill"}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

function isLow(
  remaining: number | null,
  limit: number | null,
  fraction: number,
) {
  if (remaining == null || !limit) return false;
  return remaining / limit < fraction;
}

function usageFor(
  model: string,
  live: GroqUsage | null | undefined,
  stored: GroqUsage[],
): GroqUsage | null {
  if (live && (!model || live.model === model)) return live;
  return stored.find((item) => item.model === model) ?? null;
}
