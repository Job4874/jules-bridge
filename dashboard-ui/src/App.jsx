import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './index.css';

const BRIDGE = import.meta.env.VITE_BRIDGE_URL || 'http://127.0.0.1:5000';
const TOKEN = import.meta.env.VITE_BRIDGE_TOKEN || '';
const HISTORY_POINTS = 42;

const NAV_ITEMS = [
  ['Home', 'HM'],
  ['Providers', 'PV'],
  ['Artifacts', 'AR'],
  ['Scratch', 'SC'],
  ['Integrations', 'IN'],
  ['Alerts', 'AL'],
  ['Settings', 'ST'],
];

const PROVIDER_KEYS = [
  ['gemini', 'Gemini'],
  ['openrouter', 'OpenRouter'],
  ['vm_worker', 'VM Worker'],
];

const DEFAULT_PROVIDERS = {
  gemini: { status: 'no_key' },
  openrouter: { status: 'no_key' },
  vm_worker: { status: 'offline' },
};

const REQUIRED_PROVIDER_KEYS = ['vm_worker'];

function isRequiredProvider(key) {
  return REQUIRED_PROVIDER_KEYS.includes(key);
}

function providerStateLabel(snapshot, key, tone) {
  if (tone === 'good') return 'Ready';
  if (isRequiredProvider(key)) return tone === 'bad' ? 'Blocker' : 'Watch';
  if (providerStatus(snapshot, 'vm_worker') === 'ok') return 'Bypassed';
  return tone === 'bad' ? 'Watch' : 'Optional';
}

function countProviderFailures(snapshot) {
  return PROVIDER_KEYS.filter(([key]) => (
    isRequiredProvider(key) && statusTone(providerStatus(snapshot, key)) === 'bad'
  )).length;
}

const emptySnapshot = {
  ok: false,
  timestamp: '',
  cacheAge: 0,
  bridge: {
    status: 'offline',
    uptime: '--',
    uptimeSeconds: 0,
    localUrl: BRIDGE,
    tunnelUrl: '',
    tunnelActive: false,
  },
  resource: {
    status: 'unknown',
    cpu: 0,
    memory: 0,
    maxedOut: false,
    reasons: [],
  },
  fleet: {
    launched: 0,
    completed: 0,
    pending: 0,
    failed: 0,
    inProgress: 0,
    allComplete: false,
    sessionsTracked: 0,
  },
  cloud: {
    total: 0,
    online: 0,
    vms: [],
  },
  providers: DEFAULT_PROVIDERS,
  logs: [],
  envKeysPresent: [],
};

function clampPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(0, Math.min(100, number));
}

function normalizeDashboard(raw) {
  const bridge = raw?.bridge || {};
  const pressure = raw?.resource_pressure || {};
  const fleet = raw?.jules_fleet || {};
  const cloud = raw?.cloud || {};
  const tunnelUrl = bridge.tunnel_url || bridge.ngrok_url || '';

  return {
    ok: Boolean(raw?.ok),
    timestamp: raw?.timestamp || new Date().toISOString(),
    cacheAge: Number(raw?.cache_age_s || 0),
    bridge: {
      status: bridge.status || 'unknown',
      uptime: bridge.uptime_human || '--',
      uptimeSeconds: Number(bridge.uptime_s || 0),
      localUrl: bridge.local_url || BRIDGE,
      tunnelUrl,
      tunnelActive: Boolean(tunnelUrl),
    },
    resource: {
      status: pressure.status || 'unknown',
      cpu: clampPercent(pressure.cpu_percent),
      memory: clampPercent(pressure.memory_percent),
      maxedOut: Boolean(pressure.maxed_out),
      reasons: Array.isArray(pressure.reasons) ? pressure.reasons : [],
    },
    fleet: {
      launched: Number(fleet.launched || 0),
      completed: Number(fleet.completed || 0),
      pending: Number(fleet.pending || 0),
      failed: Number(fleet.failed || 0),
      inProgress: Number(fleet.in_progress || 0),
      allComplete: Boolean(fleet.all_complete),
      sessionsTracked: Number(fleet.sessions_tracked || 0),
    },
    cloud: {
      total: Number(cloud.total || 0),
      online: Number(cloud.online || 0),
      vms: Array.isArray(cloud.vms) ? cloud.vms : [],
    },
    providers: { ...DEFAULT_PROVIDERS, ...(raw?.providers || {}) },
    logs: Array.isArray(raw?.recent_logs) ? raw.recent_logs : [],
    envKeysPresent: Array.isArray(raw?.env_keys_present) ? raw.env_keys_present : [],
  };
}

function statusTone(status) {
  const normalized = String(status || '').toLowerCase();
  if (['ok', 'online', 'running', 'active', 'pass', 'complete'].includes(normalized)) return 'good';
  if (['skipped', 'optional'].includes(normalized)) return 'warn';
  if (['error', 'failed', 'offline', 'exception', 'invalid_key'].includes(normalized)) return 'bad';
  if (['no_key', 'unknown', 'provisioning', 'planning', 'blocked', 'in progress'].includes(normalized)) return 'warn';
  return 'neutral';
}

function providerStatus(snapshot, key) {
  return snapshot.providers?.[key]?.status || DEFAULT_PROVIDERS[key]?.status || 'unknown';
}

function providerLabel(status) {
  if (status === 'no_key') return 'NO KEY';
  if (status === 'skipped') return 'BYPASSED';
  if (status === 'invalid_key') return 'INVALID';
  return String(status || 'unknown').replaceAll('_', ' ').toUpperCase();
}

function routeLabel(snapshot) {
  if (providerStatus(snapshot, 'vm_worker') === 'ok') return 'VM primary';
  if (providerStatus(snapshot, 'gemini') === 'ok') return 'Gemini primary';
  if (providerStatus(snapshot, 'openrouter') === 'ok') return 'OpenRouter route';
  return 'No chat route';
}

function formatClock(value) {
  if (!value) return '--:--:--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--:--:--';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function timeAgo(value) {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h`;
}

function percent(value, total) {
  if (!total) return 0;
  return Math.max(0, Math.min(100, Math.round((value / total) * 100)));
}

function eventId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createEvents(next, previous) {
  const at = next.timestamp || new Date().toISOString();
  const events = [];

  if (!previous || !previous.timestamp) {
    events.push({
      id: eventId('sync'),
      tone: 'good',
      title: 'Dashboard sync established',
      detail: `Bridge snapshot received from ${next.bridge.localUrl}`,
      at,
    });
    return events;
  }

  if (next.bridge.tunnelActive !== previous.bridge.tunnelActive) {
    events.push({
      id: eventId('tunnel'),
      tone: next.bridge.tunnelActive ? 'good' : 'bad',
      title: next.bridge.tunnelActive ? 'Tunnel came online' : 'Tunnel went offline',
      detail: next.bridge.tunnelUrl || 'No public tunnel URL reported',
      at,
    });
  }

  PROVIDER_KEYS.forEach(([key, label]) => {
    const before = providerStatus(previous, key);
    const after = providerStatus(next, key);
    if (before !== after) {
      events.push({
        id: eventId(key),
        tone: statusTone(after),
        title: `${label} changed`,
        detail: `${providerLabel(before)} -> ${providerLabel(after)}`,
        at,
      });
    }
  });

  if (next.cloud.online !== previous.cloud.online || next.cloud.total !== previous.cloud.total) {
    events.push({
      id: eventId('cloud'),
      tone: next.cloud.online > 0 ? 'good' : 'warn',
      title: 'Cloud worker census changed',
      detail: `${next.cloud.online}/${next.cloud.total} workers online`,
      at,
    });
  }

  if (next.resource.maxedOut !== previous.resource.maxedOut) {
    events.push({
      id: eventId('pressure'),
      tone: next.resource.maxedOut ? 'bad' : 'good',
      title: next.resource.maxedOut ? 'Resource pressure high' : 'Resource pressure cleared',
      detail: next.resource.reasons.join(', ') || next.resource.status,
      at,
    });
  }

  return events;
}

function parseLogLine(line) {
  const match = String(line).match(/^(\[[^\]]+\])\s?(.*)$/);
  const message = match ? match[2] : String(line);
  let level = 'INFO';
  if (/error|fail|exception|invalid/i.test(message)) level = 'ERROR';
  else if (/warn|blocked|stale|dry_run/i.test(message)) level = 'WARN';
  return {
    time: match ? match[1] : '',
    level,
    message,
  };
}

function sparkPoints(values) {
  const width = 148;
  const height = 42;
  const safeValues = values.length ? values : [0];
  return safeValues.map((value, index) => {
    const x = safeValues.length === 1 ? 0 : (index / (safeValues.length - 1)) * width;
    const y = height - (clampPercent(value) / 100) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
}

function cx(...classes) {
  return classes.filter(Boolean).join(' ');
}

function Dot({ tone = 'neutral' }) {
  return <span className={cx('dot', tone)} aria-hidden="true" />;
}

function Panel({ title, meta, className = '', children }) {
  return (
    <section className={cx('cockpit-panel', className)}>
      <header className="panel-titlebar">
        <h2>{title}</h2>
        {meta && <div className="panel-meta">{meta}</div>}
      </header>
      <div className="panel-content">{children}</div>
    </section>
  );
}

function Sidebar({ activeNav, setActiveNav, connection, snapshot }) {
  return (
    <aside className="side-rail">
      <div className="rail-logo">
        <span>JB</span>
      </div>
      <nav aria-label="Cockpit navigation">
        {NAV_ITEMS.map(([label, code]) => (
          <button
            className={activeNav === label ? 'active' : ''}
            key={label}
            onClick={() => setActiveNav(label)}
            title={label}
            type="button"
          >
            <span>{code}</span>
            <b>{label}</b>
          </button>
        ))}
      </nav>
      <div className="rail-status">
        <Dot tone={connection.online ? 'good' : 'bad'} />
        <strong>{connection.online ? 'System Operational' : 'System Offline'}</strong>
        <span>{snapshot.cloud.online}/{snapshot.cloud.total} workers</span>
        <span>Sync {timeAgo(connection.lastUpdated)} ago</span>
      </div>
    </aside>
  );
}

function TopBar({ connection, snapshot, onPause, onRefresh }) {
  return (
    <header className="top-strip">
      <div className="top-title">
        <span>JULES BRIDGE</span>
        <h1>Live operations cockpit</h1>
      </div>
      <div className="top-stats">
        <span><Dot tone={connection.online ? 'good' : 'bad'} />{connection.online ? 'LIVE' : 'OFFLINE'}</span>
        <span>Sync {formatClock(connection.lastUpdated)}</span>
        <span>{timeAgo(connection.lastUpdated)} ago</span>
        <span>{connection.latencyMs}ms</span>
        <span>Cache {snapshot.cacheAge}s</span>
      </div>
      <div className="top-actions">
        <button onClick={onPause} type="button">{connection.paused ? 'Resume' : 'Pause'}</button>
        <button disabled={connection.loading} onClick={onRefresh} type="button">
          {connection.loading ? 'Refreshing' : 'Refresh'}
        </button>
      </div>
    </header>
  );
}

function TaskTimeline({ snapshot, connection }) {
  const failures = countProviderFailures(snapshot);
  const vmReady = providerStatus(snapshot, 'vm_worker') === 'ok';
  const tasks = [
    {
      name: 'provider audit',
      owner: 'Jules-01',
      status: failures ? 'waiting feedback' : 'clear',
      tone: failures ? 'warn' : 'good',
      offset: 7,
      span: 38,
    },
    {
      name: 'VM chat route',
      owner: 'Fallback',
      status: vmReady ? 'ready' : 'erroring',
      tone: vmReady ? 'good' : 'bad',
      offset: 21,
      span: 34,
    },
    {
      name: 'public ngrok route',
      owner: 'Bridge',
      status: snapshot.bridge.tunnelActive ? 'active' : '404 / offline',
      tone: snapshot.bridge.tunnelActive ? 'good' : 'bad',
      offset: 34,
      span: 42,
    },
    {
      name: 'readiness PR',
      owner: 'Codex',
      status: connection.online ? 'live verify' : 'blocked',
      tone: connection.online ? 'blue' : 'warn',
      offset: 12,
      span: 52,
    },
    {
      name: 'dispatch queue',
      owner: 'Fleet',
      status: `${snapshot.fleet.pending} pending`,
      tone: snapshot.fleet.failed ? 'bad' : 'neutral',
      offset: 52,
      span: 28,
    },
  ];

  return (
    <div className="timeline-board">
      <div className="time-axis">
        <span>now</span>
        <span>+15m</span>
        <span>+30m</span>
        <span>+45m</span>
      </div>
      {tasks.map((task) => (
        <div className="timeline-row" key={task.name}>
          <div className="task-copy">
            <strong>{task.name}</strong>
            <span>{task.owner}</span>
          </div>
          <div className="task-track">
            <span
              className={cx('task-bar', task.tone)}
              style={{ left: `${task.offset}%`, width: `${task.span}%` }}
            >
              {task.status}
            </span>
          </div>
        </div>
      ))}
      <div className="timeline-footer">
        <span>bridge {snapshot.bridge.status}</span>
        <span>{routeLabel(snapshot)}</span>
        <span>{snapshot.bridge.tunnelUrl || snapshot.bridge.localUrl}</span>
      </div>
    </div>
  );
}

function ProviderMatrix({ snapshot }) {
  return (
    <div className="provider-matrix">
      <div className="provider-head">
        <span>Provider</span>
        <span>Auth</span>
        <span>Route</span>
        <span>State</span>
      </div>
      {PROVIDER_KEYS.map(([key, label]) => {
        const provider = snapshot.providers?.[key] || {};
        const status = provider.status || 'unknown';
        const tone = statusTone(status);
        const detail = provider.route || provider.error_type || provider.http_status || provider.model || (key === 'vm_worker' ? 'vm/jules-worker' : 'env key');
        return (
          <div className={cx('provider-line', tone)} key={key}>
            <span><Dot tone={tone} />{label}</span>
            <span>{providerLabel(status)}</span>
            <span>{String(detail || '--')}</span>
            <span>{providerStateLabel(snapshot, key, tone)}</span>
          </div>
        );
      })}
    </div>
  );
}

function Meter({ label, value, tone = 'blue' }) {
  return (
    <div className="meter-row">
      <div>
        <strong>{label}</strong>
        <span>{Math.round(value)}%</span>
      </div>
      <div className="meter-track">
        <span className={tone} style={{ width: `${clampPercent(value)}%` }} />
      </div>
    </div>
  );
}

function WorkerSystems({ snapshot, cpuHistory, memHistory }) {
  const cloudPercent = percent(snapshot.cloud.online, snapshot.cloud.total || 1);
  return (
    <div className="systems-board">
      <div className="spark-grid">
        <div className="spark-card">
          <span>CPU</span>
          <strong>{snapshot.resource.cpu.toFixed(1)}%</strong>
          <svg viewBox="0 0 148 42" role="img" aria-label="CPU history sparkline">
            <polyline points={sparkPoints(cpuHistory)} />
          </svg>
        </div>
        <div className="spark-card">
          <span>MEM</span>
          <strong>{snapshot.resource.memory.toFixed(1)}%</strong>
          <svg viewBox="0 0 148 42" role="img" aria-label="Memory history sparkline">
            <polyline points={sparkPoints(memHistory)} />
          </svg>
        </div>
      </div>
      <Meter label="Cloud workers" value={cloudPercent} tone="green" />
      <Meter label="Bridge pressure" value={snapshot.resource.maxedOut ? 86 : Math.max(snapshot.resource.cpu, snapshot.resource.memory)} tone={snapshot.resource.maxedOut ? 'red' : 'blue'} />
      <div className="mini-legend">
        <span><Dot tone="good" />live</span>
        <span><Dot tone="warn" />watch</span>
        <span><Dot tone="bad" />block</span>
      </div>
    </div>
  );
}

function EventQueue({ events, snapshot }) {
  const fallbackEvents = [
    {
      id: 'provider-baseline',
      tone: countProviderFailures(snapshot) ? 'bad' : 'good',
      title: 'Provider readiness sampled',
      detail: routeLabel(snapshot),
      at: snapshot.timestamp,
    },
    {
      id: 'tunnel-baseline',
      tone: snapshot.bridge.tunnelActive ? 'good' : 'bad',
      title: snapshot.bridge.tunnelActive ? 'Public tunnel active' : 'Public route unavailable',
      detail: snapshot.bridge.tunnelUrl || 'No tunnel URL reported',
      at: snapshot.timestamp,
    },
    {
      id: 'cloud-baseline',
      tone: snapshot.cloud.online > 0 ? 'good' : 'warn',
      title: 'Cloud worker census',
      detail: `${snapshot.cloud.online}/${snapshot.cloud.total} online`,
      at: snapshot.timestamp,
    },
  ];
  const visible = [
    ...events,
    ...fallbackEvents.filter((fallback) => !events.some((event) => event.id === fallback.id)),
  ];

  return (
    <div className="event-queue">
      {visible.slice(0, 10).map((event) => (
        <article className={cx('queue-row', event.tone)} key={event.id}>
          <span>{event.tone.toUpperCase()}</span>
          <div>
            <strong>{event.title}</strong>
            <p>{event.detail}</p>
          </div>
          <time>{formatClock(event.at)}</time>
        </article>
      ))}
    </div>
  );
}

function TerminalStream({ logs, filter, setFilter }) {
  const parsed = logs.length ? logs.map(parseLogLine) : [
    { time: '[local]', level: 'INFO', message: 'Waiting for bridge log lines.' },
    { time: '[route]', level: 'INFO', message: `Status source ${BRIDGE}/dashboard/status` },
  ];
  const filtered = filter === 'ALL' ? parsed : parsed.filter((line) => line.level === filter);

  return (
    <div className="terminal-wrap">
      <div className="terminal-tabs">
        {['ALL', 'INFO', 'WARN', 'ERROR'].map((item) => (
          <button
            className={filter === item ? 'active' : ''}
            key={item}
            onClick={() => setFilter(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </div>
      <div className="terminal-box" role="log" aria-label="Bridge terminal stream">
        {filtered.slice(-60).map((line, index) => (
          <div className={cx('terminal-line', line.level)} key={`${line.time}-${index}`}>
            <span>{line.time}</span>
            <b>{line.level}</b>
            <code>{line.message}</code>
          </div>
        ))}
      </div>
    </div>
  );
}

function FleetCloudBoard({ snapshot }) {
  const total = Math.max(snapshot.fleet.launched, snapshot.fleet.completed + snapshot.fleet.pending + snapshot.fleet.failed);
  const done = percent(snapshot.fleet.completed, total);
  const active = percent(snapshot.fleet.inProgress, total);
  const pending = percent(snapshot.fleet.pending, total);
  const failed = percent(snapshot.fleet.failed, total);

  return (
    <div className="fleet-cloud">
      <div className="fleet-stat-ring" style={{ '--done': `${done}%` }}>
        <strong>{snapshot.fleet.completed}</strong>
        <span>done</span>
      </div>
      <div className="fleet-cards">
        <span><b>{snapshot.fleet.launched}</b>launched</span>
        <span><b>{snapshot.fleet.inProgress}</b>active</span>
        <span><b>{snapshot.fleet.pending}</b>pending</span>
        <span><b>{snapshot.fleet.failed}</b>failed</span>
      </div>
      <div className="fleet-progress" aria-label="Fleet status distribution">
        <span className="green" style={{ width: `${done}%` }} />
        <span className="blue" style={{ width: `${active}%` }} />
        <span className="amber" style={{ width: `${pending}%` }} />
        <span className="red" style={{ width: `${failed}%` }} />
      </div>
      <div className="cloud-list">
        {snapshot.cloud.vms.length ? snapshot.cloud.vms.slice(0, 3).map((vm, index) => (
          <div className="cloud-node" key={`${vm.name || vm.ip || index}`}>
            <Dot tone={vm.reachable ? 'good' : 'warn'} />
            <strong>{vm.name || 'cloud worker'}</strong>
            <span>{vm.ip || vm.status || '--'}</span>
          </div>
        )) : (
          <div className="cloud-node">
            <Dot tone="warn" />
            <strong>No workers reported</strong>
            <span>waiting for VM census</span>
          </div>
        )}
      </div>
    </div>
  );
}

function CodexPanel({ route, model, setModel }) {
  const [messages, setMessages] = useState([
    { role: 'system', content: 'Comm link ready. Bridge-backed chat responses appear here.' },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [pendingImage, setPendingImage] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const feedRef = useRef(null);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [messages, isThinking]);

  useEffect(() => {
    const handlePaste = (event) => {
      const items = (event.clipboardData || window.clipboardData)?.items || [];
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          event.preventDefault();
          const blob = item.getAsFile();
          const reader = new FileReader();
          reader.onload = (readerEvent) => {
            const src = readerEvent.target.result;
            setPendingImage({ src, base64: String(src).split(',')[1] || '' });
          };
          reader.readAsDataURL(blob);
          break;
        }
      }
    };

    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, []);

  const sendChat = async () => {
    const message = inputValue.trim();
    if (!message && !pendingImage) return;

    const image = pendingImage;
    setInputValue('');
    setPendingImage(null);
    setMessages((previous) => [
      ...previous,
      { role: 'user', content: message || '[visual attachment]', img: image?.src },
    ]);
    setIsThinking(true);

    try {
      const payload = { message: message || 'Analyze this visual data.', model };
      if (image) payload.image_base64 = image.base64;
      const headers = { 'Content-Type': 'application/json' };
      if (TOKEN) headers.Authorization = `Bearer ${TOKEN}`;

      const response = await fetch(`${BRIDGE}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      const meta = data.model_used ? `${data.model_used} / ${data.elapsed_ms || 0}ms` : '';
      setMessages((previous) => [
        ...previous,
        { role: response.ok ? 'ai' : 'system', content: data.response || data.error || 'No response.', meta },
      ]);
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { role: 'system', content: `Comm link failed: ${error.message}` },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChat();
    }
  };

  return (
    <section className="cockpit-panel codex-panel">
      <header className="panel-titlebar codex-titlebar">
        <div>
          <h2>Codex</h2>
          <span>{route}</span>
        </div>
        <select value={model} onChange={(event) => setModel(event.target.value)} aria-label="Chat model">
          <option value="fast">fast</option>
          <option value="smart">smart</option>
        </select>
      </header>
      <div className="chat-feed" ref={feedRef}>
        {messages.map((message, index) => (
          <article className={cx('chat-bubble', message.role)} key={`${message.role}-${index}`}>
            <p>{message.content}</p>
            {message.img && <img src={message.img} alt="Attached visual" />}
            {message.meta && <span>{message.meta}</span>}
          </article>
        ))}
        {isThinking && <article className="chat-bubble ai"><p>Receiving...</p></article>}
      </div>
      <div className="composer">
        {pendingImage && (
          <div className="attachment">
            <img src={pendingImage.src} alt="Pending visual" />
            <span>visual attached</span>
            <button onClick={() => setPendingImage(null)} type="button">x</button>
          </div>
        )}
        <div className="composer-row">
          <textarea
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Message bridge..."
            rows={1}
            value={inputValue}
          />
          <button disabled={isThinking} onClick={sendChat} type="button">Send</button>
        </div>
      </div>
    </section>
  );
}

function App() {
  const [snapshot, setSnapshot] = useState(emptySnapshot);
  const [events, setEvents] = useState([]);
  const [cpuHistory, setCpuHistory] = useState(Array(HISTORY_POINTS).fill(0));
  const [memHistory, setMemHistory] = useState(Array(HISTORY_POINTS).fill(0));
  const [connection, setConnection] = useState({
    online: false,
    loading: false,
    paused: false,
    latencyMs: 0,
    lastUpdated: '',
    error: '',
  });
  const [activeNav, setActiveNav] = useState('Home');
  const [logFilter, setLogFilter] = useState('ALL');
  const [model, setModel] = useState('fast');
  const controllerRef = useRef(null);
  const inFlightRef = useRef(false);

  const applySnapshot = useCallback((raw, latencyMs) => {
    const next = normalizeDashboard(raw);
    setSnapshot((previous) => {
      const diffEvents = createEvents(next, previous);
      if (diffEvents.length) setEvents((prev) => [...diffEvents, ...prev].slice(0, 60));
      return next;
    });
    setCpuHistory((previous) => [...previous.slice(1), next.resource.cpu]);
    setMemHistory((previous) => [...previous.slice(1), next.resource.memory]);
    setConnection((previous) => ({
      ...previous,
      online: true,
      loading: false,
      latencyMs,
      lastUpdated: next.timestamp,
      error: '',
    }));
  }, []);

  const fetchStatus = useCallback(async (bypassCache = false) => {
    if (inFlightRef.current) {
      if (!bypassCache) return;
      controllerRef.current?.abort();
    }

    const controller = new AbortController();
    controllerRef.current = controller;
    inFlightRef.current = true;
    const started = performance.now();
    setConnection((previous) => ({ ...previous, loading: bypassCache ? true : previous.loading }));

    try {
      const suffix = bypassCache ? '?bypass_cache=true' : '';
      const response = await fetch(`${BRIDGE}/dashboard/status${suffix}`, {
        cache: 'no-store',
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      applySnapshot(data, Math.round(performance.now() - started));
    } catch (error) {
      if (error.name === 'AbortError') return;
      setConnection((previous) => ({
        ...previous,
        online: false,
        loading: false,
        error: error.message,
      }));
      setEvents((previous) => [
        {
          id: eventId('offline'),
          tone: 'bad',
          title: 'Dashboard sync failed',
          detail: error.message,
          at: new Date().toISOString(),
        },
        ...previous,
      ].slice(0, 60));
    } finally {
      if (controllerRef.current === controller) {
        inFlightRef.current = false;
        controllerRef.current = null;
        setConnection((previous) => (previous.loading ? { ...previous, loading: false } : previous));
      }
    }
  }, [applySnapshot]);

  useEffect(() => {
    fetchStatus(false);
    if (connection.paused) return undefined;
    const timer = window.setInterval(() => fetchStatus(false), 10000);
    return () => {
      window.clearInterval(timer);
      controllerRef.current?.abort();
    };
  }, [connection.paused, fetchStatus]);

  const route = useMemo(() => routeLabel(snapshot), [snapshot]);

  return (
    <div className="app-shell">
      <Sidebar
        activeNav={activeNav}
        connection={connection}
        setActiveNav={setActiveNav}
        snapshot={snapshot}
      />
      <main className="cockpit-shell">
        <TopBar
          connection={connection}
          onPause={() => setConnection((previous) => ({ ...previous, paused: !previous.paused }))}
          onRefresh={() => fetchStatus(true)}
          snapshot={snapshot}
        />
        {connection.error && <div className="sync-error">{connection.error}</div>}
        <section className="cockpit-grid" aria-label={`${activeNav} operations dashboard`}>
          <Panel className="timeline-panel" meta={<span>View all</span>} title="Next Tasks Live">
            <TaskTimeline connection={connection} snapshot={snapshot} />
          </Panel>
          <Panel className="provider-panel" meta={<span>{route}</span>} title="Provider Matrix">
            <ProviderMatrix snapshot={snapshot} />
          </Panel>
          <Panel className="system-panel" meta={<span>Live backend health</span>} title="Worker Systems">
            <WorkerSystems cpuHistory={cpuHistory} memHistory={memHistory} snapshot={snapshot} />
          </Panel>
          <Panel className="events-panel" meta={<span>{events.length || 3} events</span>} title="Event Queue">
            <EventQueue events={events} snapshot={snapshot} />
          </Panel>
          <Panel className="terminal-panel" meta={<span>{snapshot.logs.length} lines</span>} title="Terminal Stream">
            <TerminalStream filter={logFilter} logs={snapshot.logs} setFilter={setLogFilter} />
          </Panel>
          <Panel className="fleet-panel" meta={<span>{snapshot.cloud.online}/{snapshot.cloud.total} online</span>} title="Fleet + Cloud">
            <FleetCloudBoard snapshot={snapshot} />
          </Panel>
          <CodexPanel model={model} route={route} setModel={setModel} />
        </section>
      </main>
    </div>
  );
}

export default App;
