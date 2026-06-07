// ===================================================
// app.js — Veronica Advanced Neural Interface
// ===================================================

const API = 'http://127.0.0.1:5000/api';
let serverOnline  = false;
let lastLogCount  = 0;
let isListening   = false;
let cmdCount      = 0;
let voiceCount    = 0;
let textCount     = 0;
let sessionStart  = Date.now();

// ============ BOOT SEQUENCE ============
const BOOT_LINES = [
  'BIOS v4.2.1 ... OK',
  'Initializing neural core...',
  'Loading speech recognition module...',
  'Binding gTTS audio engine...',
  'Connecting to Ollama AI backend...',
  'Loading Llama3 model weights...',
  'Starting Flask API server...',
  'CORS policy applied...',
  'Wake word detector armed: "VERONICA"',
  'Fact-check engine loaded...',
  'Recipe database linked...',
  'Wikipedia connector ready...',
  'All systems nominal.',
  '>>> VERONICA ONLINE <<<',
];

function runBoot() {
  const linesEl = document.getElementById('boot-lines');
  const barEl   = document.getElementById('boot-bar');
  const pctEl   = document.getElementById('boot-pct');

  let i = 0;
  const total = BOOT_LINES.length;

  const tick = () => {
    if (i >= total) {
      // Finish boot
      setTimeout(() => {
        document.getElementById('boot-screen').classList.add('fade-out');
        setTimeout(() => {
          document.getElementById('boot-screen').style.display = 'none';
          document.getElementById('main-ui').classList.add('visible');
        }, 800);
      }, 400);
      return;
    }
    const div = document.createElement('div');
    div.textContent = '> ' + BOOT_LINES[i];
    if (BOOT_LINES[i].includes('<<<')) div.style.color = 'var(--cyan)';
    linesEl.appendChild(div);
    linesEl.scrollTop = linesEl.scrollHeight;

    const pct = Math.round(((i+1)/total)*100);
    barEl.style.width = pct + '%';
    pctEl.textContent = pct + '%';
    i++;
    setTimeout(tick, 100 + Math.random()*120);
  };
  tick();
}

// ============ PARTICLE BACKGROUND ============
function initParticles() {
  const canvas = document.getElementById('bg-canvas');
  const ctx    = canvas.getContext('2d');
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random()*W,
      y: Math.random()*H,
      r: Math.random()*1.2 + 0.3,
      vx: (Math.random()-0.5)*0.3,
      vy: (Math.random()-0.5)*0.3,
      a: Math.random()*0.5 + 0.1,
    });
  }

  function drawFrame() {
    ctx.clearRect(0,0,W,H);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
      ctx.fillStyle = `rgba(0,229,255,${p.a})`;
      ctx.fill();
    });

    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i+1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx+dy*dy);
        if (dist < 100) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(0,229,255,${0.06*(1-dist/100)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(drawFrame);
  }
  drawFrame();
}

// ============ TICK RING ============
function buildTickRing() {
  const ring = document.getElementById('tick-ring');
  const ticks = 36;
  for (let i = 0; i < ticks; i++) {
    const tick = document.createElement('div');
    const angle = (i / ticks) * 360;
    const isMajor = i % 9 === 0;
    tick.style.cssText = `
      position:absolute;
      width:${isMajor?2:1}px;
      height:${isMajor?8:4}px;
      background:rgba(0,229,255,${isMajor?0.5:0.2});
      top:0; left:50%;
      transform-origin: 50% 87px;
      transform: translateX(-50%) rotate(${angle}deg);
    `;
    ring.appendChild(tick);
  }
}

// ============ WAVEFORM ============
function buildWaveform() {
  const wf = document.getElementById('waveform');
  const hs = [4,7,12,18,26,34,40,44,40,34,28,22,30,38,42,38,30,22,14,8,5];
  hs.forEach((h,i) => {
    const b = document.createElement('div');
    b.className = 'wave-bar';
    b.style.setProperty('--h', h+'px');
    b.style.setProperty('--d', (0.5+Math.random()*0.7)+'s');
    b.style.setProperty('--delay', (i*0.055)+'s');
    wf.appendChild(b);
  });
}

// ============ CLOCK ============
function updateClock() {
  const now  = new Date();
  const pad  = n => String(n).padStart(2,'0');
  const time = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  const DAYS = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
  const MONS = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
  const date = `${DAYS[now.getDay()]} ${now.getDate()} ${MONS[now.getMonth()]}`;

  document.getElementById('header-time').textContent = time;
  document.getElementById('header-date').textContent = date;

  // Session timer
  const elapsed = Math.floor((Date.now()-sessionStart)/1000);
  const sh = pad(Math.floor(elapsed/3600));
  const sm = pad(Math.floor((elapsed%3600)/60));
  const ss = pad(elapsed%60);
  const sesEl = document.getElementById('session-time');
  if (sesEl) sesEl.textContent = `${sh}:${sm}:${ss}`;

  // Uptime
  const up = document.getElementById('stat-uptime');
  if (up) up.textContent = `${sm}:${ss}`;
}
setInterval(updateClock, 1000);
updateClock();

// ============ SET STATUS ============
function setStatus(status) {
  const pill    = document.getElementById('status-pill');
  const pillDot = document.getElementById('pill-dot');
  const stText  = document.getElementById('status-text');
  const display = document.getElementById('status-display');
  const orb     = document.getElementById('main-orb');
  const cStatus = document.getElementById('core-status');
  const micBtn  = document.getElementById('mic-btn');
  const bars    = document.querySelectorAll('.wave-bar');

  // Remove all state classes
  ['listening','thinking','speaking'].forEach(c => {
    pill?.classList.remove(c);
    pillDot?.classList.remove(c);
    display?.classList.remove(c);
    orb?.classList.remove(c);
  });

  const MAP = {
    idle:      { label:'STANDBY',    coreLabel:'TAP TO ACTIVATE',  dispLabel:'NEURAL INTERFACE READY' },
    listening: { label:'LISTENING',  coreLabel:'CAPTURING AUDIO',  dispLabel:'RECEIVING NEURAL INPUT...' },
    thinking:  { label:'PROCESSING', coreLabel:'ANALYZING...',     dispLabel:'PROCESSING QUERY...' },
    speaking:  { label:'RESPONDING', coreLabel:'SPEAKING...',      dispLabel:'GENERATING RESPONSE...' },
  };
  const m = MAP[status] || MAP.idle;

  stText.textContent  = m.label;
  cStatus.textContent = m.coreLabel;
  display.textContent = m.dispLabel;

  if (status !== 'idle') {
    pill?.classList.add(status);
    pillDot?.classList.add(status);
    display?.classList.add(status);
    if (status === 'listening') orb?.classList.add('active');
    if (status === 'speaking')  orb?.classList.add('speaking');
    if (status === 'thinking')  orb?.classList.add('thinking');
  }

  micBtn.className = 'action-btn mic-btn' + (status === 'listening' ? ' active' : '');
  const waveActive = status === 'listening' || status === 'speaking';
  bars.forEach(b => b.classList.toggle('active', waveActive));
}

// ============ CHAT LOG ============
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;');
}

function addEntry(role, text) {
  const log   = document.getElementById('chat-log');
  const div   = document.createElement('div');
  const now   = new Date();
  const time  = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

  div.className = `chat-entry ${role === 'user' ? 'user' : 've'}`;
  div.innerHTML = `
    <div class="entry-meta">${role === 'user' ? 'YOU' : 'VERONICA'} · ${time}</div>
    <div class="entry-text">${esc(text)}</div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;

  // Update log count
  const cnt = document.getElementById('log-count');
  if (cnt) cnt.textContent = log.children.length;
}

// ============ POLL SERVER ============
async function pollStatus() {
  try {
    const res  = await fetch(`${API}/status`, {
      signal: AbortSignal.timeout(2000),
      cache: 'no-store'
    });
    if (!res.ok) throw new Error('bad');
    const data = await res.json();

    document.getElementById('conn-error').classList.remove('show');
    serverOnline = true;

    setStatus(data.status || 'idle');

    if (data.last_response) {
      document.getElementById('last-response').textContent = data.last_response;
    }

    if (data.log && data.log.length > lastLogCount) {
      data.log.slice(lastLogCount).forEach(e => addEntry(e.role, e.text));
      lastLogCount = data.log.length;
    }

    // AI status
    const ai     = document.getElementById('ai-status');
    const aiMon  = document.getElementById('ai-mon-val');
    const aiBar  = document.getElementById('ai-bar');
    const aiCap  = document.getElementById('ai-cap');
    const aiOnline = Boolean(data.ai_available);

    ai.textContent     = aiOnline ? 'ONLINE' : 'OFFLINE';
    ai.style.color     = aiOnline ? 'var(--green)' : 'var(--red)';
    if (aiMon) { aiMon.textContent = aiOnline ? 'ONLINE' : 'OFFLINE'; aiMon.style.color = aiOnline ? 'var(--green)' : 'var(--red)'; }
    if (aiBar) { aiBar.style.width = aiOnline ? '100%' : '25%'; aiBar.style.background = aiOnline ? 'var(--green)' : 'var(--red)'; }
    if (aiCap) {
      aiCap.classList.toggle('online', aiOnline);
      aiCap.querySelector('.cap-dot').style.background = aiOnline ? 'var(--green)' : 'var(--red)';
    }

  } catch {
    document.getElementById('conn-error').classList.add('show');
    serverOnline = false;
    setStatus('idle');

    const ai = document.getElementById('ai-status');
    ai.textContent = 'OFFLINE';
    ai.style.color = 'var(--red)';
  }
}

setInterval(pollStatus, 600);
pollStatus();

// ============ COMMANDS ============
async function submitCommand() {
  const input   = document.getElementById('cmd-input');
  const command = input.value.trim();
  if (!command) return;
  input.value = '';
  textCount++;
  document.getElementById('stat-text').textContent = textCount;
  await sendCommand(command);
}

async function sendCommand(command) {
  if (!serverOnline) {
    addEntry('veronica', '⚠ Server offline. Open VS Code and run: python server.py');
    return;
  }

  addEntry('user', command);
  cmdCount++;
  document.getElementById('cmd-count').textContent  = cmdCount;
  document.getElementById('stat-queries').textContent = cmdCount;

  try {
    await fetch(`${API}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command })
    });
  } catch(e) {
    addEntry('veronica', 'Connection failed. Check server.');
  }
}

async function triggerListen() {
  if (!serverOnline) {
    addEntry('veronica', '⚠ Server offline. Open VS Code and run: python server.py');
    return;
  }
  if (isListening) return;
  isListening = true;
  voiceCount++;
  document.getElementById('stat-voice').textContent = voiceCount;

  try {
    await fetch(`${API}/listen`, { method: 'POST' });
  } catch(e) {
    addEntry('veronica', 'Mic trigger failed.');
  }
  setTimeout(() => { isListening = false; }, 3000);
}

// ============ STOP ============
async function stopVeronica() {
  const btn = document.getElementById('stop-btn');
  btn.classList.add('active');

  try {
    await fetch(`${API}/stop`, { method: 'POST' });
    // Reset UI immediately
    setStatus('idle');
    addEntry('veronica', '⏹ Stopped. Say "Veronica" to wake me again.');
    document.getElementById('last-response').textContent = 'Stopped. Say Veronica to wake me again.';
  } catch(e) {
    addEntry('veronica', 'Stop command failed — check server.');
  }

  setTimeout(() => btn.classList.remove('active'), 1200);
}

async function clearLog() {
  const log = document.getElementById('chat-log');
  log.innerHTML = `
    <div class="chat-entry entry-boot">
      <div class="entry-meta">SYSTEM · LOG CLEARED</div>
      <div class="entry-text">Neural log cleared. Ready for new session.</div>
    </div>`;
  lastLogCount = 0;
  document.getElementById('log-count').textContent = '1';
  try { await fetch(`${API}/clear_log`, { method: 'POST' }); } catch{}
}

// ============ ENTER KEY ============
document.getElementById('cmd-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') submitCommand();
});

// ============ CUSTOM CURSOR TRACKING ============
document.addEventListener('mousemove', e => {
  document.body.style.setProperty('--mx', e.clientX + 'px');
  document.body.style.setProperty('--my', e.clientY + 'px');
});

// ============ INIT ============
window.addEventListener('DOMContentLoaded', () => {
  buildTickRing();
  buildWaveform();
  initParticles();
  runBoot();
});