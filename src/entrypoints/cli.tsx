#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import { Command } from 'commander';
import { VERSION } from '../constants/version.js';
import { DEFAULT_MODEL, AVAILABLE_MODELS, getModelDisplayName } from '../constants/models.js';
import { App } from '../components/App.js';
import { createInitialState } from '../state/AppState.js';
import { setCwd } from '../utils/cwd.js';
import { NonInteractiveMode } from './nonInteractive.js';

async function main(): Promise<void> {
  const program = new Command()
    .name('claude')
    .description(`Claude Code v${VERSION} - AI coding assistant`)
    .version(`${VERSION} (Claude Code)`, '-v, --version')
    .option('-m, --model <model>', 'Model to use', DEFAULT_MODEL)
    .option('-p, --prompt <text>', 'One-shot prompt (non-interactive mode)')
    .option('--cwd <dir>', 'Working directory', process.cwd())
    .option('--print', 'Print mode: output response and exit')
    .option('--dangerously-skip-permissions', 'Auto-approve all tool use')
    .option('--verbose', 'Enable verbose output')
    .parse(process.argv);

  const opts = program.opts();
  const cwd = opts.cwd as string;
  setCwd(cwd);

  const model = resolveModel(opts.model as string);

  if (opts.prompt || program.args.length > 0) {
    const prompt = opts.prompt as string || program.args.join(' ');
    const nonInteractive = new NonInteractiveMode({
      model,
      cwd,
      verbose: opts.verbose as boolean,
      dangerouslySkipPermissions: opts.dangerouslySkipPermissions as boolean,
    });
    await nonInteractive.run(prompt);
    return;
  }

  const initialState = createInitialState(cwd, model);
  if (opts.dangerouslySkipPermissions) {
    initialState.permissionMode = 'dangerousAutoApprove';
  }
  if (opts.verbose) {
    initialState.verboseMode = true;
  }

  const { waitUntilExit } = render(
    <App initialState={initialState} />,
    { exitOnCtrlC: false }
  );

  await waitUntilExit();
}

function resolveModel(input: string): string {
  if (AVAILABLE_MODELS.includes(input as any)) return input;

  const match = AVAILABLE_MODELS.find(m =>
    m.includes(input) ||
    getModelDisplayName(m).toLowerCase() === input.toLowerCase()
  );

  return match || DEFAULT_MODEL;
}

main().catch((err) => {
  console.error('Fatal error:', err.message || err);
  process.exit(1);
});
