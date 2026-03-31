import { resolve } from 'path';

let currentCwd = process.cwd();

export function getCwd(): string {
  return currentCwd;
}

export function setCwd(dir: string): void {
  currentCwd = resolve(dir);
}
