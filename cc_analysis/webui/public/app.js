const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// State
let providers = [];
let activeProvider = null;
let activeModel = '';
let activeFormat = '';
let chatMessages = [];
let ws = null;
let streaming = false;
let streamBuffer = '';
let ollamaRunning = false;

// Elements
const elMessages = $('#messages');
const elInput = $('#input');
const elWelcome = $('#welcome');
const elSelProvider = $('#sel-provider');
const elSelModel = $('#sel-model');
const elTopbarModel = $('#topbar-model');
const elHintProvider = $('#hint-provider');
const elBtnSend = $('#btn-send');
const elBtnStop = $('#btn-stop');

// ── Tabs ──
$$('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach(t => t.classList.remove('active'));
    $$('.tab-content').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    $(`#tab-${tab.dataset.tab}`).classList.add('active');
  });
});

// ── WebSocket ──
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}`);
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'stream_start') {
      streaming = true;
      streamBuffer = '';
      elBtnSend.classList.add('hidden');
      elBtnStop.classList.remove('hidden');
      appendAIMessage('');
    } else if (msg.type === 'stream_delta') {
      streamBuffer += msg.content;
      updateLastAIMessage(streamBuffer);
    } else if (msg.type === 'stream_end') {
      finishStream();
    } else if (msg.type === 'error') {
      streaming = false;
      elBtnSend.classList.remove('hidden');
      elBtnStop.classList.add('hidden');
      appendError(msg.content);
    }
  };
  ws.onclose = () => setTimeout(connectWS, 2000);
}

function finishStream() {
  streaming = false;
  elBtnSend.classList.remove('hidden');
  elBtnStop.classList.add('hidden');
  const el = $('#streaming-msg');
  if (el) el.id = '';
  if (streamBuffer) chatMessages.push({ role: 'assistant', content: streamBuffer });
  streamBuffer = '';
}

// ── Ollama ──
async function checkOllama() {
  try {
    const r = await fetch('/api/ollama/status');
    const data = await r.json();
    ollamaRunning = data.running;
    const el = $('#ollama-status');
    if (data.running) {
      el.innerHTML = `<span class="dot green"></span> Ollama running (v${data.version})`;
      loadOllamaModels();
    } else {
      el.innerHTML = '<span class="dot red"></span> Ollama not detected';
    }
  } catch {
    ollamaRunning = false;
  }
}

async function loadOllamaModels() {
  try {
    const r = await fetch('/api/ollama/models');
    const models = await r.json();
    const list = $('#local-model-list');
    if (!models.length) {
      list.innerHTML = '<div class="empty-hint">No models installed yet — click a button below to download</div>';
      return;
    }
    list.innerHTML = models.map(m => `
      <div class="model-item${activeFormat === 'ollama' && activeModel === m.name ? ' active' : ''}" data-model="${m.name}">
        <span class="model-name">${m.name}</span>
        <span class="model-meta">${m.params || m.sizeGB}</span>
        <button class="model-del" data-del="${m.name}" title="Delete">✕</button>
      </div>
    `).join('');

    list.querySelectorAll('.model-item').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target.classList.contains('model-del')) return;
        selectOllamaModel(el.dataset.model);
      });
    });
    list.querySelectorAll('.model-del').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const name = btn.dataset.del;
        if (!confirm(`Delete model "${name}"?`)) return;
        await fetch('/api/ollama/model', {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: name }),
        });
        loadOllamaModels();
      });
    });
  } catch {}
}

function selectOllamaModel(name) {
  activeFormat = 'ollama';
  activeModel = name;
  activeProvider = { format: 'ollama', model: name, name: 'Ollama' };
  updateModelDisplay();
  $$('#local-model-list .model-item').forEach(el => {
    el.classList.toggle('active', el.dataset.model === name);
  });
}

async function pullModel(modelName) {
  if (!ollamaRunning) { alert('Ollama is not running! Please install and start Ollama first.\nhttps://ollama.com'); return; }
  const prog = $('#pull-progress');
  prog.classList.remove('hidden');
  prog.innerHTML = `Downloading ${modelName}...\n<div class="bar"><div class="bar-fill" style="width:0%"></div></div>`;

  try {
    const r = await fetch('/api/ollama/pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName }),
    });
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const obj = JSON.parse(line.slice(6));
          if (obj.status === 'success') {
            prog.innerHTML = `✅ ${modelName} downloaded successfully!`;
            setTimeout(() => prog.classList.add('hidden'), 3000);
            loadOllamaModels();
            selectOllamaModel(modelName);
            return;
          }
          if (obj.error) {
            prog.innerHTML = `❌ Error: ${obj.error}`;
            return;
          }
          let pct = 0;
          if (obj.total && obj.completed) pct = Math.round(obj.completed / obj.total * 100);
          const status = obj.status || 'downloading';
          prog.innerHTML = `${status}${pct ? ` ${pct}%` : ''}\n<div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>`;
        } catch {}
      }
    }
    prog.innerHTML = `✅ ${modelName} ready!`;
    setTimeout(() => prog.classList.add('hidden'), 3000);
    loadOllamaModels();
    selectOllamaModel(modelName);
  } catch (e) {
    prog.innerHTML = `❌ ${e.message}`;
  }
}

$$('.model-chip').forEach(btn => {
  btn.addEventListener('click', () => pullModel(btn.dataset.model));
});

$('#btn-pull-model').addEventListener('click', () => {
  const name = $('#inp-pull-model').value.trim();
  if (name) pullModel(name);
});
$('#inp-pull-model').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); $('#btn-pull-model').click(); }
});

// ── Cloud Providers ──
async function loadProviders() {
  const resp = await fetch('/api/providers');
  providers = await resp.json();
  renderProviderSelect();
}

function renderProviderSelect() {
  elSelProvider.innerHTML = '<option value="">-- Select Provider --</option>';
  providers.forEach((p) => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.name;
    elSelProvider.appendChild(opt);
  });
  if (activeProvider && activeProvider.id) elSelProvider.value = activeProvider.id;
}

function renderModelSelect() {
  elSelModel.innerHTML = '<option value="">-- Select Model --</option>';
  if (!activeProvider || activeProvider.format === 'ollama') return;
  const models = (activeProvider.models || '').split(',').map(s => s.trim()).filter(Boolean);
  models.forEach((m) => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    elSelModel.appendChild(opt);
  });
  if (activeModel) elSelModel.value = activeModel;
}

function updateModelDisplay() {
  const label = activeModel
    ? `${activeProvider?.name || 'Ollama'} / ${activeModel}`
    : 'No model selected';
  elTopbarModel.textContent = label;
  elHintProvider.textContent = activeModel ? label : 'none';
  if (activeModel) {
    elTopbarModel.style.background = activeFormat === 'ollama' ? '#1a3a2a' : '#2a2a4a';
  }
}

elSelProvider.addEventListener('change', () => {
  const p = providers.find(p => p.id === elSelProvider.value);
  if (!p) return;
  activeProvider = p;
  activeFormat = p.format || 'openai';
  activeModel = '';
  renderModelSelect();
  const models = (p.models || '').split(',').map(s => s.trim()).filter(Boolean);
  if (models.length === 1) { activeModel = models[0]; elSelModel.value = activeModel; }
  updateModelDisplay();
});

elSelModel.addEventListener('change', () => {
  activeModel = elSelModel.value;
  updateModelDisplay();
});

// Quick add provider
$$('.provider-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    $('#modal-overlay').classList.remove('hidden');
    $('#inp-name').value = chip.dataset.name;
    $('#inp-url').value = chip.dataset.url;
    $('#inp-models').value = chip.dataset.models;
    $('#inp-key').value = '';
    $('#inp-max-tokens').value = '4096';
    $('input[name="format"][value="openai"]').checked = true;
    $('#inp-key').focus();
  });
});

// Modal
$('#btn-add-provider').addEventListener('click', () => {
  $('#modal-overlay').classList.remove('hidden');
  $('#inp-name').value = ''; $('#inp-url').value = ''; $('#inp-key').value = '';
  $('#inp-models').value = ''; $('#inp-max-tokens').value = '4096';
  $('input[name="format"][value="openai"]').checked = true;
  $('#inp-name').focus();
});
$('#btn-close-modal').addEventListener('click', () => $('#modal-overlay').classList.add('hidden'));
$('#btn-cancel-modal').addEventListener('click', () => $('#modal-overlay').classList.add('hidden'));

$('#btn-save-provider').addEventListener('click', async () => {
  const name = $('#inp-name').value.trim();
  const baseUrl = $('#inp-url').value.trim();
  const apiKey = $('#inp-key').value.trim();
  const models = $('#inp-models').value.trim();
  const maxTokens = parseInt($('#inp-max-tokens').value) || 4096;
  const format = $('input[name="format"]:checked').value;
  if (!name || !baseUrl || !apiKey || !models) { alert('Please fill all fields'); return; }

  const resp = await fetch('/api/providers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, format, baseUrl, apiKey, models, maxTokens }),
  });
  const saved = await resp.json();
  providers.push(saved);
  activeProvider = saved;
  activeFormat = format;
  const ml = models.split(',').map(s => s.trim()).filter(Boolean);
  activeModel = ml[0] || '';
  renderProviderSelect();
  renderModelSelect();
  updateModelDisplay();
  $('#modal-overlay').classList.add('hidden');
});

$('#btn-del-provider').addEventListener('click', async () => {
  if (!activeProvider || !activeProvider.id) return;
  if (!confirm(`Delete "${activeProvider.name}"?`)) return;
  await fetch(`/api/providers/${activeProvider.id}`, { method: 'DELETE' });
  providers = providers.filter(p => p.id !== activeProvider.id);
  activeProvider = null; activeModel = ''; activeFormat = '';
  renderProviderSelect(); renderModelSelect(); updateModelDisplay();
});

// ── Chat ──
function send() {
  const text = elInput.value.trim();
  if (!text || streaming) return;
  if (!activeModel) { alert('Please select a model first'); return; }

  elWelcome?.remove();
  appendUserMessage(text);
  chatMessages.push({ role: 'user', content: text });
  elInput.value = '';
  autoResize();

  ws.send(JSON.stringify({
    type: 'chat',
    provider: activeFormat === 'ollama'
      ? { format: 'ollama', model: activeModel }
      : { ...activeProvider, model: activeModel },
    messages: chatMessages,
    maxTokens: activeProvider?.maxTokens || 4096,
  }));
}

function appendUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'msg';
  div.innerHTML = `
    <div class="msg-avatar user">👤</div>
    <div class="msg-body">
      <div class="msg-role">You</div>
      <div class="msg-content">${escapeHTML(text)}</div>
    </div>`;
  elMessages.appendChild(div);
  scrollDown();
}

function appendAIMessage(content) {
  const div = document.createElement('div');
  div.className = 'msg';
  div.id = 'streaming-msg';
  const modelLabel = activeModel ? `${activeProvider?.name || 'Ollama'}/${activeModel}` : '';
  div.innerHTML = `
    <div class="msg-avatar ai">◆</div>
    <div class="msg-body">
      <div class="msg-role">Assistant · ${modelLabel}</div>
      <div class="msg-content">${content ? renderMarkdown(content)
        : '<div class="typing-indicator"><span></span><span></span><span></span></div>'}</div>
    </div>`;
  elMessages.appendChild(div);
  scrollDown();
}

function updateLastAIMessage(content) {
  const el = $('#streaming-msg');
  if (!el) return;
  el.querySelector('.msg-content').innerHTML = renderMarkdown(content);
  scrollDown();
}

function appendError(text) {
  const div = document.createElement('div');
  div.className = 'msg';
  div.innerHTML = `
    <div class="msg-avatar ai" style="background:#5a1d1d">⚠</div>
    <div class="msg-body">
      <div class="msg-role">Error</div>
      <div class="msg-content msg-error">${escapeHTML(text)}</div>
    </div>`;
  elMessages.appendChild(div);
  scrollDown();
}

function renderMarkdown(text) {
  marked.setOptions({
    highlight: (code, lang) => {
      if (lang && hljs.getLanguage(lang)) return hljs.highlight(code, { language: lang }).value;
      return hljs.highlightAuto(code).value;
    },
    breaks: true,
  });
  return marked.parse(text);
}

function escapeHTML(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function scrollDown() { elMessages.scrollTop = elMessages.scrollHeight; }

elInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
elInput.addEventListener('input', autoResize);
function autoResize() {
  elInput.style.height = 'auto';
  elInput.style.height = Math.min(elInput.scrollHeight, 200) + 'px';
}

$('#btn-send').addEventListener('click', send);
$('#btn-stop').addEventListener('click', () => {
  if (ws) ws.close();
  connectWS();
  finishStream();
});

$('#btn-new-chat').addEventListener('click', () => {
  chatMessages = [];
  elMessages.innerHTML = `
    <div class="welcome" id="welcome">
      <div class="welcome-logo">◆</div>
      <h2>WEPClaude</h2>
      <p>Start a new conversation.</p>
    </div>`;
});

$('#btn-toggle-sidebar').addEventListener('click', () => {
  $('#sidebar').classList.toggle('collapsed');
});

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('hint')) {
    elInput.value = e.target.dataset.prompt;
    elInput.focus();
  }
});

// ── Init ──
connectWS();
loadProviders();
checkOllama();
setInterval(checkOllama, 15000);
