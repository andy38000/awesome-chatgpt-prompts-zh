import { VERSION } from '../../constants/version.js';
import { getGitStatus } from '../../utils/git.js';
import { getCwd } from '../../utils/cwd.js';
import type { ToolDefinition } from '../../types/tool.js';

export async function buildSystemPrompt(tools: ToolDefinition[]): Promise<string> {
  const cwd = getCwd();
  const gitStatus = await getGitStatus();
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });

  const toolDescriptions = tools.map(t =>
    `- ${t.name}: ${t.description.split('\n')[0]}`
  ).join('\n');

  const parts: string[] = [
    `You are Claude Code (v${VERSION}), an AI coding assistant created by Anthropic.`,
    `You are a coding agent that helps users with software engineering tasks.`,
    '',
    `Today's date: ${today}`,
    `Working directory: ${cwd}`,
    '',
    'You have access to the following tools:',
    toolDescriptions,
    '',
    'Guidelines:',
    '- Use the appropriate tools to help the user accomplish their task.',
    '- Read files before editing them to understand context.',
    '- Use BashTool for running commands, not for reading/editing files.',
    '- Prefer FileEditTool over FileWriteTool when editing existing files.',
    '- Use GlobTool and GrepTool to find files and search code.',
    '- Be concise but thorough in your responses.',
    '- When making code changes, preserve existing style and conventions.',
    '- Do not add unnecessary comments that just narrate what the code does.',
  ];

  if (gitStatus) {
    parts.push('', 'Git repository information:', gitStatus);
  }

  return parts.join('\n');
}
