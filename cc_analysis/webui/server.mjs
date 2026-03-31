import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3456;

const MIME = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

const CONFIG_DIR = path.join(process.env.HOME || process.env.USERPROFILE || '', '.wepscli');
const PROVIDERS_FILE = path.join(CONFIG_DIR, 'providers.json');

function ensureConfigDir() {
  if (!fs.existsSync(CONFIG_DIR)) fs.mkdirSync(CONFIG_DIR, { recursive: true });
}

function loadProviders() {
  ensureConfigDir();
  if (!fs.existsSync(PROVIDERS_FILE)) return [];
  try { return JSON.parse(fs.readFileSync(PROVIDERS_FILE, 'utf8')); } catch { return []; }
}

function saveProviders(list) {
  ensureConfigDir();
  fs.writeFileSync(PROVIDERS_FILE, JSON.stringify(list, null, 2));
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/api/providers') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(loadProviders()));
    return;
  }

  if (req.method === 'POST' && req.url === '/api/providers') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const provider = JSON.parse(body);
        provider.id = Date.now().toString(36);
        const list = loadProviders();
        list.push(provider);
        saveProviders(list);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(provider));
      } catch (e) {
        res.writeHead(400);
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  if (req.method === 'DELETE' && req.url?.startsWith('/api/providers/')) {
    const id = req.url.split('/').pop();
    let list = loadProviders();
    list = list.filter(p => p.id !== id);
    saveProviders(list);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  let filePath = path.join(__dirname, 'public', req.url === '/' ? 'index.html' : req.url);
  const ext = path.extname(filePath);
  if (!fs.existsSync(filePath)) {
    res.writeHead(404);
    res.end('Not Found');
    return;
  }
  res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
  fs.createReadStream(filePath).pipe(res);
});

const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
  ws.on('message', async (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.type === 'chat') {
      const { provider, messages, maxTokens } = msg;
      if (!provider?.baseUrl || !provider?.apiKey || !provider?.model) {
        ws.send(JSON.stringify({ type: 'error', content: 'Provider not configured' }));
        return;
      }

      try {
        const isAnthropic = provider.format === 'anthropic';
        const url = isAnthropic
          ? `${provider.baseUrl.replace(/\/$/, '')}/v1/messages`
          : `${provider.baseUrl.replace(/\/$/, '')}/chat/completions`;

        const headers = {
          'Content-Type': 'application/json',
          ...(isAnthropic
            ? { 'x-api-key': provider.apiKey, 'anthropic-version': '2023-06-01' }
            : { 'Authorization': `Bearer ${provider.apiKey}` }),
        };

        const apiMessages = messages.map(m => ({
          role: m.role,
          content: m.content,
        }));

        const body = isAnthropic
          ? JSON.stringify({
              model: provider.model,
              max_tokens: maxTokens || 4096,
              stream: true,
              messages: apiMessages,
            })
          : JSON.stringify({
              model: provider.model,
              max_tokens: maxTokens || 4096,
              stream: true,
              messages: [{ role: 'system', content: 'You are a helpful coding assistant.' }, ...apiMessages],
            });

        const resp = await fetch(url, { method: 'POST', headers, body });

        if (!resp.ok) {
          const errText = await resp.text();
          ws.send(JSON.stringify({ type: 'error', content: `API Error ${resp.status}: ${errText}` }));
          return;
        }

        ws.send(JSON.stringify({ type: 'stream_start' }));

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6).trim();
            if (data === '[DONE]') continue;

            try {
              const parsed = JSON.parse(data);
              let text = '';
              if (isAnthropic) {
                if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
                  text = parsed.delta.text;
                }
              } else {
                text = parsed.choices?.[0]?.delta?.content || '';
              }
              if (text) {
                ws.send(JSON.stringify({ type: 'stream_delta', content: text }));
              }
            } catch {}
          }
        }

        ws.send(JSON.stringify({ type: 'stream_end' }));
      } catch (e) {
        ws.send(JSON.stringify({ type: 'error', content: e.message }));
      }
    }
  });
});

server.listen(PORT, () => {
  console.log(`\n  🚀 WEPClaude Web UI running at:\n`);
  console.log(`     http://localhost:${PORT}\n`);
  console.log(`  Open the URL above in your browser.\n`);
});
