import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3456;
const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://localhost:11434';

const MIME = {
  '.html': 'text/html', '.css': 'text/css',
  '.js': 'application/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png',
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

function parseBody(req) {
  return new Promise((resolve) => {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => { try { resolve(JSON.parse(body)); } catch { resolve(null); } });
  });
}

const server = http.createServer(async (req, res) => {
  const cors = { 'Content-Type': 'application/json' };

  // ── Provider CRUD ──
  if (req.method === 'GET' && req.url === '/api/providers') {
    res.writeHead(200, cors);
    res.end(JSON.stringify(loadProviders()));
    return;
  }
  if (req.method === 'POST' && req.url === '/api/providers') {
    const provider = await parseBody(req);
    if (!provider) { res.writeHead(400); res.end('{}'); return; }
    provider.id = Date.now().toString(36);
    const list = loadProviders();
    list.push(provider);
    saveProviders(list);
    res.writeHead(200, cors);
    res.end(JSON.stringify(provider));
    return;
  }
  if (req.method === 'DELETE' && req.url?.startsWith('/api/providers/')) {
    const id = req.url.split('/').pop();
    saveProviders(loadProviders().filter(p => p.id !== id));
    res.writeHead(200, cors);
    res.end('{"ok":true}');
    return;
  }

  // ── Ollama APIs ──
  if (req.method === 'GET' && req.url === '/api/ollama/status') {
    try {
      const r = await fetch(`${OLLAMA_HOST}/api/version`, { signal: AbortSignal.timeout(3000) });
      const v = await r.json();
      res.writeHead(200, cors);
      res.end(JSON.stringify({ running: true, version: v.version }));
    } catch {
      res.writeHead(200, cors);
      res.end(JSON.stringify({ running: false }));
    }
    return;
  }

  if (req.method === 'GET' && req.url === '/api/ollama/models') {
    try {
      const r = await fetch(`${OLLAMA_HOST}/api/tags`);
      const data = await r.json();
      const models = (data.models || []).map(m => ({
        name: m.name,
        size: m.size,
        sizeGB: (m.size / 1e9).toFixed(1) + ' GB',
        modified: m.modified_at,
        family: m.details?.family || '',
        params: m.details?.parameter_size || '',
      }));
      res.writeHead(200, cors);
      res.end(JSON.stringify(models));
    } catch (e) {
      res.writeHead(500, cors);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  if (req.method === 'POST' && req.url === '/api/ollama/pull') {
    const body = await parseBody(req);
    if (!body?.model) { res.writeHead(400, cors); res.end('{"error":"no model"}'); return; }
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
    try {
      const r = await fetch(`${OLLAMA_HOST}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: body.model, stream: true }),
      });
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split('\n').filter(Boolean)) {
          try {
            const obj = JSON.parse(line);
            res.write(`data: ${JSON.stringify(obj)}\n\n`);
          } catch {}
        }
      }
      res.write(`data: {"status":"success"}\n\n`);
    } catch (e) {
      res.write(`data: {"error":"${e.message}"}\n\n`);
    }
    res.end();
    return;
  }

  if (req.method === 'DELETE' && req.url === '/api/ollama/model') {
    const body = await parseBody(req);
    if (!body?.model) { res.writeHead(400, cors); res.end('{}'); return; }
    try {
      await fetch(`${OLLAMA_HOST}/api/delete`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: body.model }),
      });
      res.writeHead(200, cors);
      res.end('{"ok":true}');
    } catch (e) {
      res.writeHead(500, cors);
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // ── Static files ──
  let filePath = path.join(__dirname, 'public', req.url === '/' ? 'index.html' : req.url);
  if (!fs.existsSync(filePath)) { res.writeHead(404); res.end('Not Found'); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
  fs.createReadStream(filePath).pipe(res);
});

// ── WebSocket Chat ──
const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
  ws.on('message', async (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.type === 'chat') {
      const { provider, messages, maxTokens } = msg;
      if (!provider?.model) {
        ws.send(JSON.stringify({ type: 'error', content: 'No model selected' }));
        return;
      }

      try {
        const isOllama = provider.format === 'ollama';
        const isAnthropic = provider.format === 'anthropic';

        let url, headers, body;

        if (isOllama) {
          url = `${OLLAMA_HOST}/api/chat`;
          headers = { 'Content-Type': 'application/json' };
          body = JSON.stringify({
            model: provider.model,
            stream: true,
            messages: messages.map(m => ({ role: m.role, content: m.content })),
          });
        } else if (isAnthropic) {
          url = `${provider.baseUrl.replace(/\/$/, '')}/v1/messages`;
          headers = {
            'Content-Type': 'application/json',
            'x-api-key': provider.apiKey,
            'anthropic-version': '2023-06-01',
          };
          body = JSON.stringify({
            model: provider.model,
            max_tokens: maxTokens || 4096,
            stream: true,
            messages: messages.map(m => ({ role: m.role, content: m.content })),
          });
        } else {
          url = `${provider.baseUrl.replace(/\/$/, '')}/chat/completions`;
          headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${provider.apiKey}`,
          };
          body = JSON.stringify({
            model: provider.model,
            max_tokens: maxTokens || 4096,
            stream: true,
            messages: [
              { role: 'system', content: 'You are a helpful coding assistant.' },
              ...messages.map(m => ({ role: m.role, content: m.content })),
            ],
          });
        }

        const resp = await fetch(url, { method: 'POST', headers, body });
        if (!resp.ok) {
          ws.send(JSON.stringify({ type: 'error', content: `API Error ${resp.status}: ${await resp.text()}` }));
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
            if (!line.trim()) continue;

            if (isOllama) {
              try {
                const obj = JSON.parse(line);
                if (obj.message?.content) {
                  ws.send(JSON.stringify({ type: 'stream_delta', content: obj.message.content }));
                }
                if (obj.done) break;
              } catch {}
            } else {
              if (!line.startsWith('data: ')) continue;
              const data = line.slice(6).trim();
              if (data === '[DONE]') continue;
              try {
                const parsed = JSON.parse(data);
                let text = '';
                if (isAnthropic) {
                  if (parsed.type === 'content_block_delta' && parsed.delta?.text) text = parsed.delta.text;
                } else {
                  text = parsed.choices?.[0]?.delta?.content || '';
                }
                if (text) ws.send(JSON.stringify({ type: 'stream_delta', content: text }));
              } catch {}
            }
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
  console.log(`     http://localhost:${PORT}`);
  console.log(`     http://127.0.0.1:${PORT}\n`);
  console.log(`  Local models: install Ollama from https://ollama.com\n`);
});
