import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  ArcElement,
  Filler,
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import './index.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  ArcElement,
  Filler,
);

const BRIDGE = import.meta.env.VITE_BRIDGE_URL || 'http://127.0.0.1:5000';
const TOKEN = import.meta.env.VITE_BRIDGE_TOKEN || '';
const HISTORY_POINTS = 48;

const DEFAULT_PROVIDERS = {
  gemini: { status: 'no_key' },
  openrouter: { status: 'no_key' },
  vm_worker: { status: 'offline' },
};

const NAV_ITEMS = ['Overview', 'Agents', 'Logs', 'Comm'];
const NAV_TARGETS = {
  Overview: 'dashboard-overview',
  Agents: 'dashboard-agents',
  Logs: 'dashboard-logs',
  Comm: 'dashboard-comm',
};
const PROVIDER_KEYS = [
  ['gemini', 'Gemini'],
  ['openrouter', 'OpenRouter'],
  ['vm_worker', 'VM Worker'],
];

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

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  scales: {
    x: { display: false },
    y: {
      min: 0,
      max: 100,
      border: { display: false },
      grid: { color: 'rgba(148, 163, 184, 0.1)' },
      ticks: {
        stepSize: 25,
        color: '#6b7280',
        font: { size: 10, family: 'JetBrains Mono, Consolas, monospace' },
      },
    },
  },
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  elements: { point: { radius: 0 }, line: { tension: 0.35, borderWidth: 2 } },
};

const ringOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '76%',
  animation: false,
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
};

function clampPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(100, n));
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
  if (['error', 'failed', 'offline', 'exception', 'invalid_key'].includes(normalized)) return 'bad';
  if (['no_key', 'unknown', 'provisioning', 'planning', 'in progress'].includes(normalized)) return 'warn';
  return 'neutral';
}

function providerStatus(snapshot, key) {
  return snapshot.providers?.[key]?.status || DEFAULT_PROVIDERS[key]?.status || 'unknown';
}

function providerLabel(status) {
  if (status === 'no_key') return 'NO KEY';
  if (status === 'invalid_key') return 'INVALID KEY';
  return String(status || 'unknown').replaceAll('_', ' ').toUpperCase();
}

function routeLabel(snapshot) {
  if (providerStatus(snapshot, 'gemini') === 'ok') return 'Gemini primary';
  if (providerStatus(snapshot, 'openrouter') === 'ok') return 'OpenRouter route';
  if (providerStatus(snapshot, 'vm_worker') === 'ok') return 'VM fallback';
  return 'No chat route';
}

function formatClock(value) {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function timeAgo(value) {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  return `${Math.floor(minutes / 60)}h ago`;
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

  if (next.fleet.completed !== previous.fleet.completed || next.fleet.pending !== previous.fleet.pending) {
    events.push({
      id: eventId('fleet'),
      tone: next.fleet.pending === 0 && next.fleet.completed > 0 ? 'good' : 'neutral',
      title: 'Jules fleet progress updated',
      detail: `${next.fleet.completed} complete, ${next.fleet.pending} pending`,
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
  if (/error|fail|exception/i.test(message)) level = 'ERROR';
  else if (/warn|blocked|stale|invalid/i.test(message)) level = 'WARN';
  return {
    time: match ? match[1] : '',
    level,
    message,
  };
}

function makeLineData(values, color) {
  return {
    labels: values.map((_, index) => String(index)),
    datasets: [
      {
        data: values,
        borderColor: color,
        backgroundColor: `${color}22`,
        fill: true,
      },
    ],
  };
}

function MetricTile({ label, value, detail, tone = 'neutral', sparkline }) {
  return (
    <section className={`metric-tile ${tone}`}>
      <div className="tile-kicker">{label}</div>
      <div className="tile-value">{value}</div>
      <div className="tile-detail">{detail}</div>
      {sparkline && <div className="tile-chart">{sparkline}</div>}
    </section>
  );
}

function Panel({ title, action, className = '', id, children }) {
  return (
    <section className={`panel ${className}`} id={id}>
      <div className="panel-header">
        <h2>{title}</h2>
        {action && <div className="panel-action">{action}</div>}
      </div>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function ProviderMatrix({ snapshot }) {
  return (
    <div className="provider-grid">
      {PROVIDER_KEYS.map(([key, label]) => {
        const provider = snapshot.providers?.[key] || {};
        const status = provider.status || 'unknown';
        const detail = provider.error_type || provider.http_status || provider.model || routeLabel(snapshot);
        return (
          <div className={`provider-row ${statusTone(status)}`} key={key}>
            <div>
              <div className="row-title">{label}</div>
              <div className="row-subtitle">{String(detail || '--')}</div>
            </div>
            <span className="status-pill">{providerLabel(status)}</span>
          </div>
        );
      })}
    </div>
  );
}

function FleetBoard({ fleet }) {
  const total = Math.max(fleet.launched, fleet.completed + fleet.pending + fleet.failed);
  const completePct = percent(fleet.completed, total);
  const pendingPct = percent(fleet.pending, total);
  const failedPct = percent(fleet.failed, total);
  const activePct = Math.max(0, 100 - completePct - pendingPct - failedPct);

  return (
    <div className="fleet-board">
      <div className="fleet-rings">
        <div className="ring-wrap">
          <Doughnut
            data={{
              datasets: [
                {
                  data: [fleet.completed, Math.max(1, total - fleet.completed)],
                  backgroundColor: ['#38c172', 'rgba(148, 163, 184, 0.12)'],
                  borderWidth: 0,
                },
              ],
            }}
            options={ringOptions}
          />
          <div className="ring-center">
            <strong>{fleet.completed}</strong>
            <span>done</span>
          </div>
        </div>
        <div className="fleet-numbers">
          <div><strong>{fleet.launched}</strong><span>launched</span></div>
          <div><strong>{fleet.inProgress}</strong><span>active</span></div>
          <div><strong>{fleet.pending}</strong><span>pending</span></div>
          <div><strong>{fleet.failed}</strong><span>failed</span></div>
        </div>
      </div>
      <div className="fleet-bar" aria-label="Fleet status distribution">
        <span className="bar-complete" style={{ width: `${completePct}%` }} />
        <span className="bar-active" style={{ width: `${activePct}%` }} />
        <span className="bar-pending" style={{ width: `${pendingPct}%` }} />
        <span className="bar-failed" style={{ width: `${failedPct}%` }} />
      </div>
    </div>
  );
}

function WorkerTopology({ cloud }) {
  if (!cloud.vms.length) {
    return <div className="empty-state">No cloud workers reported.</div>;
  }

  return (
    <div className="worker-topology">
      {cloud.vms.map((vm, index) => {
        const status = vm.status || 'unknown';
        const key = `${vm.provider || 'worker'}-${vm.name || vm.ip || index}`;
        return (
          <div className={`worker-node ${vm.reachable ? 'good' : 'warn'}`} key={key}>
            <div className="node-head">
              <span className="node-provider">{vm.provider || 'Cloud'}</span>
              <span className={`live-dot ${vm.reachable ? '' : 'warn'}`} />
            </div>
            <div className="node-name" title={vm.name || ''}>{vm.name || '--'}</div>
            <div className="node-meta">
              <span>{String(status).toUpperCase()}</span>
              <span>{vm.ip || '--'}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EventStream({ events }) {
  if (!events.length) return <div className="empty-state">Awaiting live changes.</div>;
  return (
    <div className="event-stream">
      {events.slice(0, 12).map((event) => (
        <div className={`event-row ${event.tone}`} key={event.id}>
          <span className="event-rail" />
          <div>
            <div className="event-title">{event.title}</div>
            <div className="event-detail">{event.detail}</div>
          </div>
          <time>{formatClock(event.at)}</time>
        </div>
      ))}
    </div>
  );
}

function TerminalStream({ logs, filter, onFilterChange }) {
  const parsed = logs.map(parseLogLine);
  const filtered = filter === 'ALL' ? parsed : parsed.filter((line) => line.level === filter);

  return (
    <>
      <div className="segmented-control">
        {['ALL', 'INFO', 'WARN', 'ERROR'].map((item) => (
          <button
            className={filter === item ? 'active' : ''}
            key={item}
            onClick={() => onFilterChange(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </div>
      <div className="terminal-stream">
        {filtered.length === 0 ? (
          <div className="empty-state">No matching log lines.</div>
        ) : (
          filtered.slice(-80).map((line, index) => (
            <div className={`terminal-line ${line.level}`} key={`${line.time}-${index}`}>
              <span className="terminal-time">{line.time}</span>
              <span className="terminal-level">{line.level}</span>
              <span className="terminal-message">{line.message}</span>
            </div>
          ))
        )}
      </div>
    </>
  );
}

function ChatPanel({ route, model, setModel }) {
  const [messages, setMessages] = useState([
    { role: 'system', content: 'Comm link ready. Bridge-backed chat responses appear here.' },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [pendingImage, setPendingImage] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const chatBoxRef = useRef(null);

  useEffect(() => {
    if (chatBoxRef.current) chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
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
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message || '[visual attachment]', img: image?.src },
    ]);
    setIsThinking(true);

    try {
      const payload = { message: message || 'Analyze this visual data.', model };
      if (image) payload.image_base64 = image.base64;

      const response = await fetch(`${BRIDGE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${TOKEN}`,
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      const meta = data.model_used ? `${data.model_used} / ${data.elapsed_ms || 0}ms` : '';
      setMessages((prev) => [
        ...prev,
        { role: response.ok ? 'ai' : 'system', content: data.response || data.error || 'No response.', meta },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
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
    <aside className="comm-panel" id="dashboard-comm">
      <div className="comm-header">
        <div>
          <h2>Comm Link</h2>
          <p>{route}</p>
        </div>
        <select value={model} onChange={(event) => setModel(event.target.value)} aria-label="Chat model">
          <option value="fast">fast</option>
          <option value="smart">smart</option>
        </select>
      </div>

      <div className="chat-feed" ref={chatBoxRef}>
        {messages.map((message, index) => (
          <div className={`message ${message.role}`} key={`${message.role}-${index}`}>
            <div>{message.content}</div>
            {message.img && <img src={message.img} alt="Attached visual" />}
            {message.meta && <span>{message.meta}</span>}
          </div>
        ))}
        {isThinking && <div className="message ai thinking">Receiving...</div>}
      </div>

      <div className="chat-composer">
        {pendingImage && (
          <div className="attachment-strip">
            <img src={pendingImage.src} alt="Pending visual" />
            <span>Visual attached</span>
            <button type="button" onClick={() => setPendingImage(null)} aria-label="Remove attachment">x</button>
          </div>
        )}
        <div className="composer-row">
          <textarea
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Message the bridge..."
            rows={1}
          />
          <button type="button" onClick={sendChat} disabled={isThinking} aria-label="Send message">
            Send
          </button>
        </div>
      </div>
    </aside>
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
  const [activeNav, setActiveNav] = useState('Overview');
  const [logFilter, setLogFilter] = useState('ALL');
  const [model, setModel] = useState('fast');

  const controllerRef = useRef(null);
  const inFlightRef = useRef(false);

  const applySnapshot = useCallback((raw, latencyMs) => {
    const next = normalizeDashboard(raw);
    setSnapshot((previous) => {
      const diffEvents = createEvents(next, previous);
      if (diffEvents.length) {
        setEvents((prev) => [...diffEvents, ...prev].slice(0, 60));
      }
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
        setConnection((previous) => (
          previous.loading ? { ...previous, loading: false } : previous
        ));
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

  const cpuData = useMemo(() => makeLineData(cpuHistory, '#58a6ff'), [cpuHistory]);
  const memData = useMemo(() => makeLineData(memHistory, '#38c172'), [memHistory]);
  const route = routeLabel(snapshot);
  const providerFailures = PROVIDER_KEYS.filter(([key]) => statusTone(providerStatus(snapshot, key)) === 'bad').length;
  const fleetTotal = Math.max(snapshot.fleet.launched, snapshot.fleet.completed + snapshot.fleet.pending + snapshot.fleet.failed);
  const fleetProgress = percent(snapshot.fleet.completed, fleetTotal);
  const selectNav = (item) => {
    setActiveNav(item);
    window.requestAnimationFrame(() => {
      document.getElementById(NAV_TARGETS[item])?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  };

  return (
    <div className="app-shell">
      <nav className="nav-rail" aria-label="Dashboard navigation">
        <div className="brand-mark">JN</div>
        {NAV_ITEMS.map((item) => (
          <button
            className={activeNav === item ? 'active' : ''}
            key={item}
            onClick={() => selectNav(item)}
            type="button"
          >
            {item}
          </button>
        ))}
      </nav>

      <main className="dashboard-shell">
        <header className="command-bar">
          <div>
            <div className="eyebrow">Jules Nexus</div>
            <h1>Real-time bridge command center</h1>
          </div>
          <div className="command-status">
            <span className={`live-dot ${connection.online ? '' : 'bad'}`} />
            <span>{connection.online ? 'Live' : 'Offline'}</span>
            <span>Sync {formatClock(connection.lastUpdated)}</span>
            <span>{timeAgo(connection.lastUpdated)}</span>
            <span>{connection.latencyMs}ms</span>
            <span>Cache {snapshot.cacheAge}s</span>
          </div>
          <div className="command-actions">
            <button type="button" onClick={() => setConnection((prev) => ({ ...prev, paused: !prev.paused }))}>
              {connection.paused ? 'Resume' : 'Pause'}
            </button>
            <button type="button" onClick={() => fetchStatus(true)} disabled={connection.loading}>
              {connection.loading ? 'Refreshing' : 'Refresh'}
            </button>
          </div>
        </header>

        {connection.error && <div className="sync-error">{connection.error}</div>}

        <section className="metric-strip" id="dashboard-overview">
          <MetricTile
            label="Bridge"
            value={snapshot.bridge.status.toUpperCase()}
            detail={`Uptime ${snapshot.bridge.uptime}`}
            tone={connection.online ? 'good' : 'bad'}
          />
          <MetricTile
            label="Tunnel"
            value={snapshot.bridge.tunnelActive ? 'ACTIVE' : 'OFFLINE'}
            detail={snapshot.bridge.tunnelUrl || 'No public route'}
            tone={snapshot.bridge.tunnelActive ? 'good' : 'bad'}
          />
          <MetricTile
            label="Providers"
            value={`${3 - providerFailures}/3`}
            detail={route}
            tone={providerFailures ? 'warn' : 'good'}
          />
          <MetricTile
            label="Fleet"
            value={`${fleetProgress}%`}
            detail={`${snapshot.fleet.completed} done / ${snapshot.fleet.pending} pending`}
            tone={snapshot.fleet.failed ? 'bad' : 'neutral'}
          />
          <MetricTile
            label="Cloud"
            value={`${snapshot.cloud.online}/${snapshot.cloud.total}`}
            detail="workers online"
            tone={snapshot.cloud.online > 0 ? 'good' : 'warn'}
          />
          <MetricTile
            label="Pressure"
            value={snapshot.resource.maxedOut ? 'HIGH' : snapshot.resource.status.toUpperCase()}
            detail={`CPU ${snapshot.resource.cpu.toFixed(1)} / MEM ${snapshot.resource.memory.toFixed(1)}`}
            tone={snapshot.resource.maxedOut ? 'bad' : 'good'}
          />
        </section>

        <div className="workspace-grid">
          <section className="center-stack">
            <div className="focus-grid">
              <Panel title="Provider Readiness" action={<span className="route-label">{route}</span>}>
                <ProviderMatrix snapshot={snapshot} />
              </Panel>

              <Panel title="Resource Telemetry">
                <div className="telemetry-grid">
                  <div>
                    <div className="chart-label">CPU {snapshot.resource.cpu.toFixed(1)}%</div>
                    <div className="chart-box"><Line data={cpuData} options={lineOptions} /></div>
                  </div>
                  <div>
                    <div className="chart-label">Memory {snapshot.resource.memory.toFixed(1)}%</div>
                    <div className="chart-box"><Line data={memData} options={lineOptions} /></div>
                  </div>
                </div>
                <div className="reason-list">
                  {snapshot.resource.reasons.length ? snapshot.resource.reasons.map((reason) => (
                    <span key={reason}>{reason}</span>
                  )) : <span>No pressure reasons reported</span>}
                </div>
              </Panel>
            </div>

            <div className="operations-grid">
              <Panel title="Fleet Runway" id="dashboard-agents">
                <FleetBoard fleet={snapshot.fleet} />
              </Panel>

              <Panel title="Cloud Topology" action={<span>{snapshot.cloud.online}/{snapshot.cloud.total} online</span>}>
                <WorkerTopology cloud={snapshot.cloud} />
              </Panel>
            </div>

            <div className="operations-grid tall">
              <Panel title="Live Event Stream">
                <EventStream events={events} />
              </Panel>

              <Panel title="Terminal Stream" id="dashboard-logs" action={<span>{snapshot.logs.length} lines</span>}>
                <TerminalStream logs={snapshot.logs} filter={logFilter} onFilterChange={setLogFilter} />
              </Panel>
            </div>
          </section>

          <ChatPanel route={route} model={model} setModel={setModel} />
        </div>
      </main>
    </div>
  );
}

export default App;
