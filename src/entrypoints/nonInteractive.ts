import chalk from 'chalk';
import { QueryEngine } from '../QueryEngine.js';
import { createInitialState, type AppState } from '../state/AppState.js';
import { formatCost, formatTokens } from '../utils/cost.js';
import { getModelDisplayName } from '../constants/models.js';

interface NonInteractiveOptions {
  model: string;
  cwd: string;
  verbose?: boolean;
  dangerouslySkipPermissions?: boolean;
}

export class NonInteractiveMode {
  private options: NonInteractiveOptions;
  private appState: AppState;

  constructor(options: NonInteractiveOptions) {
    this.options = options;
    this.appState = createInitialState(options.cwd, options.model);
    if (options.dangerouslySkipPermissions) {
      this.appState.permissionMode = 'dangerousAutoApprove';
    }
    if (options.verbose) {
      this.appState.verboseMode = true;
    }
  }

  async run(prompt: string): Promise<void> {
    console.log(chalk.magenta(`\nClaude Code v2.1.88 • ${getModelDisplayName(this.options.model)}\n`));
    console.log(chalk.blue('❯ ') + prompt);
    console.log();

    const engine = new QueryEngine({
      getAppState: () => this.appState,
      setAppState: (fn) => { this.appState = fn(this.appState); },
      onText: (text) => {
        // Final text handled at end
      },
      onStreamText: (delta) => {
        process.stdout.write(delta);
      },
      onToolUse: (name, input) => {
        if (this.options.verbose) {
          console.log(chalk.yellow(`\n🔧 ${name}`));
          if (name === 'BashTool' && input.command) {
            console.log(chalk.dim(`   $ ${input.command}`));
          } else if (input.path) {
            console.log(chalk.dim(`   ${input.path}`));
          }
        } else {
          process.stdout.write(chalk.yellow(`\n🔧 ${name} `));
        }
      },
      onToolResult: (name, output, isError) => {
        if (this.options.verbose && output) {
          const preview = output.length > 500 ? output.slice(0, 500) + '...' : output;
          console.log(chalk.dim(preview));
        }
        console.log(isError ? chalk.red('✗') : chalk.green('✓'));
      },
      onError: (err) => {
        console.error(chalk.red(`\nError: ${err.message}`));
      },
    });

    const response = await engine.submitMessage(prompt);

    if (response.content) {
      console.log('\n' + response.content);
    }

    console.log(chalk.dim(`\n─────────────────────────────────`));
    console.log(chalk.dim(
      `${getModelDisplayName(this.options.model)} • ` +
      `↑${formatTokens(this.appState.totalInputTokens)} ↓${formatTokens(this.appState.totalOutputTokens)} • ` +
      `${formatCost(this.appState.totalCost)}`
    ));
  }
}
