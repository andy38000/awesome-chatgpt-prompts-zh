# WEPClaude

English | [Simplified Chinese](./README.zh-CN.md)

`WEPClaude` is a custom CLI fork based on a recovered Claude Code codebase and rebuilt as a normal npm project.

This fork is aimed at local customization:

- custom branding
- custom welcome UI
- independent local config storage
- in-CLI provider management
- Anthropic-format provider support
- OpenAI-compatible provider support

Current package version: `0.0.1`

## Positioning

This is not the official upstream source repository.

It is a fork intended for:

- local development
- UI and CLI customization
- provider and model integration experiments
- source-level debugging and extension work

## Current Features

- Buildable with npm
- Runs directly from source output
- Global CLI command name: `wepclaude`
- Custom provider management in `/model`
- Add provider inside the CLI:
  - choose `Anthropic` or `OpenAI format`
  - enter base URL
  - enter API key
  - fetch `/models` or enter model manually
  - activate provider/model directly
- Model display uses `provider/model`
- Custom config namespace separated from the original default Claude CLI paths

## Local Storage

By default, this fork stores its local data under its own namespace:

- config directory: `~/.wepscli`
- global config file: `~/.wepscli.json`
- credential file on Windows/Linux fallback: `~/.wepscli/.credentials.json`

This means `WEPClaude` and the original Claude CLI can generally coexist on the same device without sharing the same local config files.

Note:

- If you manually set `CLAUDE_CONFIG_DIR`, you can still force them to share a directory.
- On macOS, keychain naming is not yet fully re-isolated, so full credential separation is not guaranteed there.

## Requirements

- Node.js `>= 18`
- npm `>= 9`

## Quick Start

```bash
npm install
npm run build
node dist/cli.js --help
node dist/cli.js --version
```

## Run

Run the built CLI directly:

```bash
node dist/cli.js
```

Show version:

```bash
node dist/cli.js --version
```

Run via npm:

```bash
npm start
```

## Install as a CLI

Install globally from the project root:

```bash
npm install -g .
```

Then use:

```bash
wepclaude --help
wepclaude --version
```

For local linking during development:

```bash
npm link
```

## Build and Package

Build:

```bash
npm run build
```

Create a distributable npm tarball:

```bash
npm pack
```

Example output:

```text
wepclaude-0.0.1.tgz
```

## Common Commands

```bash
npm install
npm run build
npm run clean
npm pack
node dist/cli.js --version
wepclaude --version
```

## Project Structure

```text
.
|-- package.json
|-- package-lock.json
|-- scripts/
|   `-- build.mjs
|-- src/
|-- vendor/
`-- dist/
```

## Known Limitations

- Some internal strings still retain original Claude branding.
- Some original remote-service features are still present in the codebase and may need further cleanup if you want a fully self-owned fork.
- macOS keychain isolation is not fully separated yet.
- Recovered-source projects are not guaranteed to match upstream behavior exactly.

## Recommended Next Fork Tasks

- finish full branding replacement
- remove or disable remaining remote-service-only features
- finish storage and credential namespace isolation on macOS
- continue improving provider UX
- clean old `claude` command/help/update strings

## Source Distribution

If you want to share the source for review, the minimum useful set is:

- `src/`
- `scripts/`
- `vendor/`
- `package.json`
- `package-lock.json`
- `README.md`

Do not distribute your local config, provider keys, or credential files.
