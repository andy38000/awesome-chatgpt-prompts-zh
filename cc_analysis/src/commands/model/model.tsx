import chalk from 'chalk'
import * as React from 'react'
import type { CommandResultDisplay } from '../../commands.js'
import { type OptionWithDescription, Select } from '../../components/CustomSelect/index.js'
import { Spinner } from '../../components/Spinner.js'
import { Pane } from '../../components/design-system/Pane.js'
import { COMMON_HELP_ARGS, COMMON_INFO_ARGS } from '../../constants/xml.js'
import { Box, Text } from '../../ink.js'
import { useAppState, useSetAppState } from '../../state/AppState.js'
import type { LocalJSXCommandCall } from '../../types/command.js'
import { isBilledAsExtraUsage } from '../../utils/extraUsage.js'
import {
  clearFastModeCooldown,
  isFastModeEnabled,
  isFastModeSupportedByModel,
} from '../../utils/fastMode.js'
import { MODEL_ALIASES } from '../../utils/model/aliases.js'
import { checkOpus1mAccess, checkSonnet1mAccess } from '../../utils/model/check1mAccess.js'
import {
  activateInferenceProviderModel,
  clearActiveInferenceProvider,
  fetchInferenceProviderModels,
  formatProviderModelLabel,
  getActiveInferenceProviderConfig,
  getInferenceProvider,
  getInferenceProviders,
  removeInferenceProvider,
  saveInferenceProvider,
  updateInferenceProviderModels,
  type InferenceProviderConfig,
  type InferenceProviderFormat,
} from '../../utils/model/customProviders.js'
import {
  getDefaultMainLoopModelSetting,
  isOpus1mMergeEnabled,
  renderDefaultModelSetting,
  renderModelName,
} from '../../utils/model/model.js'
import { isModelAllowed } from '../../utils/model/modelAllowlist.js'
import { validateModel } from '../../utils/model/validateModel.js'

type DoneFn = (
  result?: string,
  options?: {
    display?: CommandResultDisplay
  },
) => void

type Stage =
  | 'menu'
  | 'format'
  | 'name'
  | 'base-url'
  | 'api-key'
  | 'pick-model'
  | 'manual-model'
  | 'refresh'
  | 'remove'

type DraftProvider = {
  format: InferenceProviderFormat
  name: string
  baseUrl: string
  apiKey: string
  fetchedModels: string[]
  fetchSource?: string
}

const MENU_ADD = '__menu_add__'
const MENU_REFRESH = '__menu_refresh__'
const MENU_REMOVE = '__menu_remove__'
const MENU_DEFAULT = '__menu_default__'
const MENU_CANCEL = '__menu_cancel__'
const PICK_MANUAL = '__pick_manual__'
const PICK_BACK = '__pick_back__'
const FORMAT_BACK = '__format_back__'
const REFRESH_BACK = '__refresh_back__'
const REMOVE_BACK = '__remove_back__'
const INPUT_SUBMIT = '__input_submit__'
const INPUT_BACK = '__input_back__'

function createEmptyDraft(): DraftProvider {
  return {
    format: 'anthropic',
    name: '',
    baseUrl: '',
    apiKey: '',
    fetchedModels: [],
  }
}

function getCurrentModelLabel(
  mainLoopModel: string | null,
  mainLoopModelForSession: string | null,
): string {
  if (mainLoopModelForSession) {
    return renderModelName(mainLoopModelForSession)
  }

  if (mainLoopModel) {
    return renderModelName(mainLoopModel)
  }

  const activeProvider = getActiveInferenceProviderConfig()
  if (activeProvider) {
    return formatProviderModelLabel(
      activeProvider.provider.name,
      activeProvider.model,
    )
  }

  return `${renderDefaultModelSetting(getDefaultMainLoopModelSetting())} (default)`
}

function isKnownAlias(model: string): boolean {
  return (MODEL_ALIASES as readonly string[]).includes(model.toLowerCase().trim())
}

function isOpus1mUnavailable(model: string): boolean {
  const normalized = model.toLowerCase()
  return (
    !checkOpus1mAccess() &&
    !isOpus1mMergeEnabled() &&
    normalized.includes('opus') &&
    normalized.includes('[1m]')
  )
}

function isSonnet1mUnavailable(model: string): boolean {
  const normalized = model.toLowerCase()
  return (
    !checkSonnet1mAccess() &&
    (normalized.includes('sonnet[1m]') ||
      normalized.includes('sonnet-4-6[1m]'))
  )
}

function validateBaseUrl(baseUrl: string): string {
  const normalized = baseUrl.trim().replace(/\/+$/, '')
  new URL(normalized)
  return normalized
}

function formatBuiltInDefaultLabel(): string {
  return `${renderDefaultModelSetting(getDefaultMainLoopModelSetting())} (built-in default)`
}

function buildSelectionMessage({
  model,
  displayLabel,
  fastMode,
}: {
  model: string | null
  displayLabel: string
  fastMode: boolean
}): {
  message: string
  nextFastMode: boolean
} {
  let message =
    model === null
      ? `Using ${chalk.bold(displayLabel)}`
      : `Set model to ${chalk.bold(displayLabel)}`

  let nextFastMode = fastMode
  if (isFastModeEnabled()) {
    clearFastModeCooldown()
    if (!isFastModeSupportedByModel(model) && fastMode) {
      nextFastMode = false
      message += ' · Fast mode OFF'
    }
  }

  if (
    model !== null &&
    isBilledAsExtraUsage(model, nextFastMode, isOpus1mMergeEnabled())
  ) {
    message += ' · Billed as extra usage'
  }

  return { message, nextFastMode }
}

function applyBuiltInModelSelection(
  setAppState: ReturnType<typeof useSetAppState>,
  fastMode: boolean,
  model: string | null,
): string {
  clearActiveInferenceProvider()
  const displayLabel =
    model === null ? formatBuiltInDefaultLabel() : renderModelName(model)
  const { message, nextFastMode } = buildSelectionMessage({
    model,
    displayLabel,
    fastMode,
  })

  setAppState(prev => ({
    ...prev,
    mainLoopModel: model,
    mainLoopModelForSession: null,
    fastMode: nextFastMode,
  }))

  return message
}

function applyProviderSelection(
  setAppState: ReturnType<typeof useSetAppState>,
  fastMode: boolean,
  provider: InferenceProviderConfig,
  model: string,
): string {
  activateInferenceProviderModel(provider.id, model)
  const displayLabel = formatProviderModelLabel(provider.name, model)
  const { message, nextFastMode } = buildSelectionMessage({
    model,
    displayLabel,
    fastMode,
  })

  setAppState(prev => ({
    ...prev,
    mainLoopModel: model,
    mainLoopModelForSession: null,
    fastMode: nextFastMode,
  }))

  return message
}

function Header({
  title,
  subtitle,
}: {
  title: string
  subtitle: string
}): React.ReactNode {
  return (
    <Box flexDirection="column" marginBottom={1}>
      <Text color="remember" bold>
        {title}
      </Text>
      <Text dimColor>{subtitle}</Text>
    </Box>
  )
}

function InputStage({
  title,
  subtitle,
  error,
  label,
  placeholder,
  value,
  onValueChange,
  onSubmit,
  onBack,
}: {
  title: string
  subtitle: string
  error?: string | null
  label: string
  placeholder: string
  value: string
  onValueChange: (value: string) => void
  onSubmit: () => void
  onBack: () => void
}): React.ReactNode {
  const options: OptionWithDescription<string>[] = [
    {
      type: 'input',
      value: INPUT_SUBMIT,
      label,
      placeholder,
      initialValue: value,
      onChange: onValueChange,
      allowEmptySubmitToCancel: false,
      showLabelWithValue: true,
      labelValueSeparator: ': ',
      resetCursorOnUpdate: true,
    },
    {
      value: INPUT_BACK,
      label: 'Back',
    },
  ]

  return (
    <Pane color="permission">
      <Header title={title} subtitle={subtitle} />
      {error && (
        <Box marginBottom={1}>
          <Text color="error">{error}</Text>
        </Box>
      )}
      <Select
        options={options}
        defaultFocusValue={INPUT_SUBMIT}
        onChange={value => {
          if (value === INPUT_BACK) {
            onBack()
            return
          }
          onSubmit()
        }}
        onCancel={onBack}
      />
    </Pane>
  )
}

function ModelManager({
  onDone,
}: {
  onDone: DoneFn
}): React.ReactNode {
  const setAppState = useSetAppState()
  const fastMode = useAppState(state => state.fastMode ?? false)
  const mainLoopModel = useAppState(state => state.mainLoopModel)
  const mainLoopModelForSession = useAppState(
    state => state.mainLoopModelForSession,
  )
  const [stage, setStage] = React.useState<Stage>('menu')
  const [draft, setDraft] = React.useState<DraftProvider>(createEmptyDraft())
  const [draftName, setDraftName] = React.useState('')
  const [draftBaseUrl, setDraftBaseUrl] = React.useState('')
  const [draftApiKey, setDraftApiKey] = React.useState('')
  const [manualModel, setManualModel] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [providersVersion, setProvidersVersion] = React.useState(0)

  const providers = React.useMemo(
    () => getInferenceProviders(),
    [providersVersion],
  )
  const activeProvider = React.useMemo(
    () => getActiveInferenceProviderConfig(),
    [providersVersion],
  )

  function refreshProviders(): void {
    setProvidersVersion(version => version + 1)
  }

  function handleCancel(): void {
    onDone(`Kept model as ${chalk.bold(getCurrentModelLabel(mainLoopModel, mainLoopModelForSession))}`, {
      display: 'system',
    })
  }

  function goToAddProvider(): void {
    setError(null)
    setDraft(createEmptyDraft())
    setDraftName('')
    setDraftBaseUrl('')
    setDraftApiKey('')
    setManualModel('')
    setStage('format')
  }

  function finalizeProvider(model: string): void {
    const savedProvider = saveInferenceProvider({
      name: draft.name,
      format: draft.format,
      baseUrl: draft.baseUrl,
      apiKey: draft.apiKey,
      models: [...draft.fetchedModels, model],
      selectedModel: model,
      activate: true,
    })

    refreshProviders()

    onDone(applyProviderSelection(setAppState, fastMode, savedProvider, model))
  }

  async function fetchModelsAndContinue(): Promise<void> {
    setIsLoading(true)
    setError(null)

    try {
      const baseUrl = validateBaseUrl(draftBaseUrl)
      const nextDraft: DraftProvider = {
        ...draft,
        name: draftName.trim(),
        baseUrl,
        apiKey: draftApiKey.trim(),
      }

      const result = await fetchInferenceProviderModels({
        format: nextDraft.format,
        baseUrl: nextDraft.baseUrl,
        apiKey: nextDraft.apiKey,
      })

      setDraft({
        ...nextDraft,
        fetchedModels: result.models,
        fetchSource: result.endpoint,
      })
      setManualModel(result.models[0] ?? '')
      setStage('pick-model')
    } catch (stageError) {
      const nextDraft: DraftProvider = {
        ...draft,
        name: draftName.trim(),
        baseUrl: draftBaseUrl.trim(),
        apiKey: draftApiKey.trim(),
        fetchedModels: [],
      }

      setDraft(nextDraft)
      setError(
        stageError instanceof Error
          ? stageError.message
          : 'Failed to fetch models.',
      )
      setStage('manual-model')
    } finally {
      setIsLoading(false)
    }
  }

  async function refreshProvider(providerId: string): Promise<void> {
    const provider = getInferenceProvider(providerId)
    if (!provider) {
      onDone('Provider not found.', { display: 'system' })
      return
    }

    setIsLoading(true)
    try {
      const result = await fetchInferenceProviderModels(provider)
      const nextSelectedModel =
        provider.selectedModel && result.models.includes(provider.selectedModel)
          ? provider.selectedModel
          : result.models[0]
      updateInferenceProviderModels(provider.id, result.models, nextSelectedModel)
      refreshProviders()

      if (activeProvider?.provider.id === provider.id && nextSelectedModel) {
        setAppState(prev => ({
          ...prev,
          mainLoopModel: nextSelectedModel,
          mainLoopModelForSession: null,
        }))
      }

      onDone(
        `Refreshed ${chalk.bold(provider.name)} from ${result.endpoint}.`,
        {
          display: 'system',
        },
      )
    } catch (stageError) {
      onDone(
        stageError instanceof Error
          ? stageError.message
          : 'Failed to refresh provider models.',
        {
          display: 'system',
        },
      )
    } finally {
      setIsLoading(false)
    }
  }

  function removeSelectedProvider(providerId: string): void {
    const provider = getInferenceProvider(providerId)
    if (!provider) {
      onDone('Provider not found.', { display: 'system' })
      return
    }

    const wasActive = activeProvider?.provider.id === provider.id
    removeInferenceProvider(provider.id)
    refreshProviders()

    if (wasActive) {
      setAppState(prev => ({
        ...prev,
        mainLoopModel: null,
        mainLoopModelForSession: null,
      }))
    }

    onDone(`Removed provider ${chalk.bold(provider.name)}.`, {
      display: 'system',
    })
  }

  if (isLoading) {
    return (
      <Pane color="permission">
        <Header title="Model" subtitle="Loading provider data…" />
        <Box flexDirection="row" gap={1}>
          <Spinner />
          <Text dimColor>Checking the provider and fetching models…</Text>
        </Box>
      </Pane>
    )
  }

  const currentLabel = getCurrentModelLabel(
    mainLoopModel,
    mainLoopModelForSession,
  )

  if (stage === 'format') {
    const options: OptionWithDescription<string>[] = [
      {
        value: 'anthropic',
        label: 'Anthropic',
        description: 'Uses the Anthropic message protocol and can be activated immediately.',
      },
      {
        value: 'openai',
        label: 'OpenAI format',
        description: 'Uses a Chat Completions compatible endpoint and can be activated immediately.',
      },
      {
        value: FORMAT_BACK,
        label: 'Back',
      },
    ]

    return (
      <Pane color="permission">
        <Header
          title="Add Provider"
          subtitle={`Current model: ${currentLabel}`}
        />
        <Select
          options={options}
          defaultFocusValue="anthropic"
          onChange={value => {
            if (value === FORMAT_BACK) {
              setStage('menu')
              return
            }

            const format = value as InferenceProviderFormat
            setDraft(current => ({ ...current, format }))
            setDraftName('')
            setStage('name')
          }}
          onCancel={() => setStage('menu')}
        />
      </Pane>
    )
  }

  if (stage === 'name') {
    return (
      <InputStage
        title="Provider Name"
        subtitle={`Format: ${draft.format === 'anthropic' ? 'Anthropic' : 'OpenAI format'}`}
        error={error}
        label="Name"
        placeholder="e.g. OpenRouter, API2D, My gateway"
        value={draftName}
        onValueChange={setDraftName}
        onSubmit={() => {
          if (!draftName.trim()) {
            setError('Provider name cannot be empty.')
            return
          }
          setError(null)
          setStage('base-url')
        }}
        onBack={() => setStage('format')}
      />
    )
  }

  if (stage === 'base-url') {
    return (
      <InputStage
        title="Base URL"
        subtitle={`Provider: ${draftName || draft.name}`}
        error={error}
        label="Base URL"
        placeholder={
          draft.format === 'anthropic'
            ? 'https://api.anthropic.com'
            : 'https://your-openai-compatible-host'
        }
        value={draftBaseUrl}
        onValueChange={setDraftBaseUrl}
        onSubmit={() => {
          try {
            validateBaseUrl(draftBaseUrl)
            setError(null)
            setStage('api-key')
          } catch (stageError) {
            setError(
              stageError instanceof Error
                ? stageError.message
                : 'Invalid base URL.',
            )
          }
        }}
        onBack={() => setStage('name')}
      />
    )
  }

  if (stage === 'api-key') {
    return (
      <InputStage
        title="API Key"
        subtitle="Press Enter to fetch /models. If the endpoint does not expose a model list, the next step will fall back to manual input."
        error={error}
        label="API key"
        placeholder="Paste the provider key"
        value={draftApiKey}
        onValueChange={setDraftApiKey}
        onSubmit={() => {
          if (!draftApiKey.trim()) {
            setError('API key cannot be empty.')
            return
          }
          void fetchModelsAndContinue()
        }}
        onBack={() => setStage('base-url')}
      />
    )
  }

  if (stage === 'pick-model') {
    const modelOptions: OptionWithDescription<string>[] = draft.fetchedModels.map(
      model => ({
        value: model,
        label: model,
        description:
          draft.fetchSource === undefined
            ? undefined
            : `Fetched from ${draft.fetchSource}`,
      }),
    )

    modelOptions.push(
      {
        value: PICK_MANUAL,
        label: 'Enter model manually',
        description: 'Use a custom deployment or a model that did not appear in /models.',
      },
      {
        value: PICK_BACK,
        label: 'Back',
      },
    )

    return (
      <Pane color="permission">
        <Header
          title="Pick Model"
          subtitle={`Provider: ${draft.name} · ${draft.baseUrl}`}
        />
        <Select
          options={modelOptions}
          defaultFocusValue={draft.fetchedModels[0] ?? PICK_MANUAL}
          onChange={value => {
            if (value === PICK_BACK) {
              setStage('api-key')
              return
            }
            if (value === PICK_MANUAL) {
              setStage('manual-model')
              return
            }
            finalizeProvider(value)
          }}
          onCancel={() => setStage('api-key')}
        />
      </Pane>
    )
  }

  if (stage === 'manual-model') {
    return (
      <InputStage
        title="Manual Model"
        subtitle={
          error
            ? `Model list fetch failed: ${error}`
            : 'Enter the model or deployment name manually.'
        }
        error={error && draft.fetchedModels.length > 0 ? error : null}
        label="Model"
        placeholder={
          draft.format === 'anthropic'
            ? 'e.g. claude-sonnet-4-6'
            : 'e.g. gpt-4.1, deepseek-chat, your deployment id'
        }
        value={manualModel}
        onValueChange={setManualModel}
        onSubmit={() => {
          if (!manualModel.trim()) {
            setError('Model cannot be empty.')
            return
          }
          finalizeProvider(manualModel.trim())
        }}
        onBack={() => setStage(draft.fetchedModels.length > 0 ? 'pick-model' : 'api-key')}
      />
    )
  }

  if (stage === 'refresh') {
    const options: OptionWithDescription<string>[] = providers.map(provider => ({
      value: provider.id,
      label: provider.name,
      description: `${provider.format === 'anthropic' ? 'Anthropic' : 'OpenAI format'} · ${provider.baseUrl}`,
    }))
    options.push({
      value: REFRESH_BACK,
      label: 'Back',
    })

    return (
      <Pane color="permission">
        <Header
          title="Refresh Models"
          subtitle="Choose a provider and pull its latest model list from /models."
        />
        <Select
          options={options}
          defaultFocusValue={providers[0]?.id ?? REFRESH_BACK}
          onChange={value => {
            if (value === REFRESH_BACK) {
              setStage('menu')
              return
            }
            void refreshProvider(value)
          }}
          onCancel={() => setStage('menu')}
        />
      </Pane>
    )
  }

  if (stage === 'remove') {
    const options: OptionWithDescription<string>[] = providers.map(provider => ({
      value: provider.id,
      label: provider.name,
      description: `${provider.models?.length ?? 0} saved model(s)`,
    }))
    options.push({
      value: REMOVE_BACK,
      label: 'Back',
    })

    return (
      <Pane color="permission">
        <Header
          title="Remove Provider"
          subtitle="Remove a saved provider and all of its stored models."
        />
        <Select
          options={options}
          defaultFocusValue={providers[0]?.id ?? REMOVE_BACK}
          onChange={value => {
            if (value === REMOVE_BACK) {
              setStage('menu')
              return
            }
            removeSelectedProvider(value)
          }}
          onCancel={() => setStage('menu')}
        />
      </Pane>
    )
  }

  const providerOptions: OptionWithDescription<string>[] = []
  for (const provider of providers) {
    const models = provider.models ?? []
    if (models.length === 0) {
      providerOptions.push({
        value: `${provider.id}:empty`,
        label: `${provider.name} (no saved models)`,
        description: provider.baseUrl,
        disabled: true,
      })
      continue
    }

    for (const model of models) {
      providerOptions.push({
        value: `${provider.id}:${model}`,
        label: formatProviderModelLabel(provider.name, model),
        description:
          provider.format === 'anthropic'
            ? provider.baseUrl
            : `${provider.baseUrl} · OpenAI compatible`,
      })
    }
  }

  providerOptions.push(
    {
      value: MENU_ADD,
      label: 'Add provider',
      description: 'Choose Anthropic or OpenAI format, then enter base URL, key, and model.',
    },
    {
      value: MENU_REFRESH,
      label: 'Refresh provider models',
      description: 'Fetch /models again for a saved provider.',
      disabled: providers.length === 0,
    },
    {
      value: MENU_REMOVE,
      label: 'Remove provider',
      description: 'Delete a saved provider and its model list.',
      disabled: providers.length === 0,
    },
    {
      value: MENU_DEFAULT,
      label: 'Use built-in default',
      description: formatBuiltInDefaultLabel(),
    },
    {
      value: MENU_CANCEL,
      label: 'Cancel',
    },
  )

  return (
    <Pane color="permission">
      <Header
        title="Model"
        subtitle={`Current model: ${currentLabel}${
          mainLoopModelForSession ? ' (session override)' : ''
        }`}
      />
      {error && (
        <Box marginBottom={1}>
          <Text color="error">{error}</Text>
        </Box>
      )}
      <Select
        options={providerOptions}
        defaultFocusValue={
          activeProvider
            ? `${activeProvider.provider.id}:${activeProvider.model}`
            : MENU_ADD
        }
        visibleOptionCount={Math.min(12, providerOptions.length)}
        onChange={value => {
          if (value === MENU_ADD) {
            goToAddProvider()
            return
          }
          if (value === MENU_REFRESH) {
            setStage('refresh')
            return
          }
          if (value === MENU_REMOVE) {
            setStage('remove')
            return
          }
          if (value === MENU_DEFAULT) {
            onDone(applyBuiltInModelSelection(setAppState, fastMode, null))
            return
          }
          if (value === MENU_CANCEL) {
            handleCancel()
            return
          }

          const separator = value.indexOf(':')
          if (separator === -1) {
            return
          }

          const providerId = value.slice(0, separator)
          const model = value.slice(separator + 1)
          const provider = getInferenceProvider(providerId)
          if (!provider) {
            onDone('Provider not found.', { display: 'system' })
            return
          }

          onDone(applyProviderSelection(setAppState, fastMode, provider, model))
        }}
        onCancel={handleCancel}
      />
    </Pane>
  )
}

function SetBuiltInModelAndClose({
  args,
  onDone,
}: {
  args: string
  onDone: DoneFn
}): React.ReactNode {
  const fastMode = useAppState(state => state.fastMode ?? false)
  const setAppState = useSetAppState()
  const model = args === 'default' ? null : args

  React.useEffect(() => {
    async function handleModelChange(): Promise<void> {
      if (model && !isModelAllowed(model)) {
        onDone(
          `Model '${model}' is not available. Your organization restricts model selection.`,
          {
            display: 'system',
          },
        )
        return
      }

      if (model && isOpus1mUnavailable(model)) {
        onDone(
          'Opus 4.6 with 1M context is not available for your account.',
          {
            display: 'system',
          },
        )
        return
      }

      if (model && isSonnet1mUnavailable(model)) {
        onDone(
          'Sonnet 4.6 with 1M context is not available for your account.',
          {
            display: 'system',
          },
        )
        return
      }

      if (!model) {
        onDone(applyBuiltInModelSelection(setAppState, fastMode, null))
        return
      }

      if (isKnownAlias(model)) {
        onDone(applyBuiltInModelSelection(setAppState, fastMode, model))
        return
      }

      try {
        const validation = await validateModel(model)
        if (!validation.valid) {
          onDone(validation.error || `Model '${model}' not found`, {
            display: 'system',
          })
          return
        }

        onDone(applyBuiltInModelSelection(setAppState, fastMode, model))
      } catch (error) {
        onDone(
          `Failed to validate model: ${
            error instanceof Error ? error.message : String(error)
          }`,
          {
            display: 'system',
          },
        )
      }
    }

    void handleModelChange()
  }, [args, fastMode, model, onDone, setAppState])

  return null
}

function ShowModelAndClose({
  onDone,
}: {
  onDone: DoneFn
}): React.ReactNode {
  const mainLoopModel = useAppState(state => state.mainLoopModel)
  const mainLoopModelForSession = useAppState(
    state => state.mainLoopModelForSession,
  )

  React.useEffect(() => {
    const current = getCurrentModelLabel(mainLoopModel, mainLoopModelForSession)
    if (mainLoopModelForSession) {
      onDone(
        `Current model: ${chalk.bold(
          renderModelName(mainLoopModelForSession),
        )} (session override)\nBase model: ${current}`,
      )
      return
    }

    onDone(`Current model: ${current}`)
  }, [mainLoopModel, mainLoopModelForSession, onDone])

  return null
}

export const call: LocalJSXCommandCall = async (onDone, _context, args) => {
  const normalizedArgs = args?.trim() || ''

  if (COMMON_INFO_ARGS.includes(normalizedArgs)) {
    return <ShowModelAndClose onDone={onDone} />
  }

  if (COMMON_HELP_ARGS.includes(normalizedArgs)) {
    onDone(
      'Run /model to manage providers and saved models. Use /model default to clear the custom provider and return to the built-in default model.',
      {
        display: 'system',
      },
    )
    return
  }

  if (normalizedArgs) {
    return <SetBuiltInModelAndClose args={normalizedArgs} onDone={onDone} />
  }

  return <ModelManager onDone={onDone} />
}
