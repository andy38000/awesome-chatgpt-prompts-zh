const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// State
let providers = [];
let activeProvider = null;
let activeModel = '';
let chatMessages = [];
let ws = null;
let streaming = false;
let streamBuffer = '';

// Elements
const elMessages = $('#messages');
const elInput = $('#input');
const elWelcome = $('#welcome');
const elSelProvider = $('#sel-provider');
const elSelModel = $('#sel-model');
const elTopbarModel = $('#topbar-model');
const elHintProvider = $('#hint-provider');
const elTokenInfo = $('#token-info');
const elBtnSend = $('#btn-send');
const elBtnStop = $('#btn-stop');

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
      streaming = false;
      elBtnSend.classList.remove('hidden');
      elBtnStop.classList.add('hidden');
      if (streamBuffer) {
        chatMessages.push({ role: 'assistant', content: streamBuffer });
      }
      streamBuffer = '';
    } else if (msg.type === 'error') {
      streaming = false;
      elBtnSend.classList.remove('hidden');
      elBtnStop.classList.add('hidden');
      appendError(msg.content);
    }
  };
  ws.onclose = () => setTimeout(connectWS, 2000);
}

// ── Providers ──
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
  if (activeProvider) {
    elSelProvider.value = activeProvider.id;
  }
}

function renderModelSelect() {
  elSelModel.innerHTML = '<option value="">-- Select Model --</option>';
  if (!activeProvider) return;
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
  if (activeProvider && activeModel) {
    const label = `${activeProvider.name} / ${activeModel}`;
    elTopbarModel.textContent = label;
    elHintProvider.textContent = label;
  } else {
    elTopbarModel.textContent = 'No model selected';
    elHintProvider.textContent = 'none';
  }
}

elSelProvider.addEventListener('change', () => {
  activeProvider = providers.find(p => p.id === elSelProvider.value) || null;
  activeModel = '';
  renderModelSelect();
  if (activeProvider) {
    const models = (activeProvider.models || '').split(',').map(s => s.trim()).filter(Boolean);
    if (models.length === 1) {
      activeModel = models[0];
      elSelModel.value = activeModel;
    }
  }
  updateModelDisplay();
});

elSelModel.addEventListener('change', () => {
  activeModel = elSelModel.value;
  updateModelDisplay();
});

// ── Modal ──
$('#btn-add-provider').addEventListener('click', () => {
  $('#modal-overlay').classList.remove('hidden');
  $('#inp-name').value = '';
  $('#inp-url').value = '';
  $('#inp-key').value = '';
  $('#inp-models').value = '';
  $('#inp-max-tokens').value = '4096';
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

  if (!name || !baseUrl || !apiKey || !models) {
    alert('Please fill in all fields');
    return;
  }

  const resp = await fetch('/api/providers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, format, baseUrl, apiKey, models, maxTokens }),
  });
  const saved = await resp.json();
  providers.push(saved);
  activeProvider = saved;
  const modelList = models.split(',').map(s => s.trim()).filter(Boolean);
  activeModel = modelList[0] || '';
  renderProviderSelect();
  renderModelSelect();
  updateModelDisplay();
  $('#modal-overlay').classList.add('hidden');
});

$('#btn-del-provider').addEventListener('click', async () => {
  if (!activeProvider) return;
  if (!confirm(`Delete provider "${activeProvider.name}"?`)) return;
  await fetch(`/api/providers/${activeProvider.id}`, { method: 'DELETE' });
  providers = providers.filter(p => p.id !== activeProvider.id);
  activeProvider = null;
  activeModel = '';
  renderProviderSelect();
  renderModelSelect();
  updateModelDisplay();
});

// ── Chat ──
function send() {
  const text = elInput.value.trim();
  if (!text || streaming) return;
  if (!activeProvider || !activeModel) {
    alert('Please select a Provider and Model first');
    return;
  }

  elWelcome?.remove();
  appendUserMessage(text);
  chatMessages.push({ role: 'user', content: text });
  elInput.value = '';
  autoResize();

  ws.send(JSON.stringify({
    type: 'chat',
    provider: { ...activeProvider, model: activeModel },
    messages: chatMessages,
    maxTokens: activeProvider.maxTokens || 4096,
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
  div.innerHTML = `
    <div class="msg-avatar ai">◆</div>
    <div class="msg-body">
      <div class="msg-role">Assistant · ${activeProvider?.name || ''}/${activeModel || ''}</div>
      <div class="msg-content">${content
        ? renderMarkdown(content)
        : '<div class="typing-indicator"><span></span><span></span><span></span></div>'
      }</div>
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
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value;
      }
      return hljs.highlightAuto(code).value;
    },
    breaks: true,
  });
  return marked.parse(text);
}

function escapeHTML(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function scrollDown() {
  elMessages.scrollTop = elMessages.scrollHeight;
}

// ── Input ──
elInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    send();
  }
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
  streaming = false;
  elBtnSend.classList.remove('hidden');
  elBtnStop.classList.add('hidden');
  if (streamBuffer) chatMessages.push({ role: 'assistant', content: streamBuffer });
  const el = $('#streaming-msg');
  if (el) el.id = '';
});

$('#btn-new-chat').addEventListener('click', () => {
  chatMessages = [];
  elMessages.innerHTML = '';
  const w = document.createElement('div');
  w.className = 'welcome';
  w.id = 'welcome';
  w.innerHTML = `
    <div class="welcome-logo">◆</div>
    <h2>WEPClaude</h2>
    <p>Start a new conversation.</p>`;
  elMessages.appendChild(w);
});

$('#btn-toggle-sidebar').addEventListener('click', () => {
  $('#sidebar').classList.toggle('collapsed');
});

// Hints
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('hint')) {
    elInput.value = e.target.dataset.prompt;
    elInput.focus();
  }
});

// ── Init ──
connectWS();
loadProviders();
