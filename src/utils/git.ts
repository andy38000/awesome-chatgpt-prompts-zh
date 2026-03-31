import { execFile } from 'child_process';
import { promisify } from 'util';
import { getCwd } from './cwd.js';

const execFileAsync = promisify(execFile);

export async function getIsGit(): Promise<boolean> {
  try {
    await execFileAsync('git', ['rev-parse', '--is-inside-work-tree'], { cwd: getCwd() });
    return true;
  } catch {
    return false;
  }
}

export async function getBranch(): Promise<string> {
  try {
    const { stdout } = await execFileAsync('git', ['branch', '--show-current'], { cwd: getCwd() });
    return stdout.trim() || 'HEAD';
  } catch {
    return 'unknown';
  }
}

export async function getDefaultBranch(): Promise<string> {
  try {
    const { stdout } = await execFileAsync(
      'git', ['symbolic-ref', 'refs/remotes/origin/HEAD', '--short'],
      { cwd: getCwd() }
    );
    return stdout.trim().replace('origin/', '');
  } catch {
    return 'main';
  }
}

export async function getGitStatus(): Promise<string | null> {
  if (!await getIsGit()) return null;

  try {
    const [branch, defaultBranch, status, log, userName] = await Promise.all([
      getBranch(),
      getDefaultBranch(),
      execFileAsync('git', ['status', '--short'], { cwd: getCwd() }).then(r => r.stdout.trim()),
      execFileAsync('git', ['log', '--oneline', '-n', '5'], { cwd: getCwd() }).then(r => r.stdout.trim()),
      execFileAsync('git', ['config', 'user.name'], { cwd: getCwd() }).then(r => r.stdout.trim()).catch(() => ''),
    ]);

    return [
      `Current branch: ${branch}`,
      `Main branch: ${defaultBranch}`,
      ...(userName ? [`Git user: ${userName}`] : []),
      `Status:\n${status || '(clean)'}`,
      `Recent commits:\n${log}`,
    ].join('\n\n');
  } catch {
    return null;
  }
}
