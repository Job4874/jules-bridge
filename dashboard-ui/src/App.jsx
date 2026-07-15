import { useState, useEffect, useMemo, useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import {
  DEFAULT_STATUS,
  buildEventRows,
  buildOpsChecklist,
  buildTopology,
  clampPercent,
  collisionKey,
  formatTimestamp,
  gateTone,
  impactedReposLabel,
  maskEndpoint,
  normalizeDashboardPayload,
  toneForStatus,
  workerKey
} from './dashboardModel';
import './index.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
);

const BRIDGE = import.meta.env.VITE_BRIDGE_URL || 'http://127.0.0.1:5000';
const TOKEN = import.meta.env.VITE_BRIDGE_TOKEN || '';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: 'overview' },
  { id: 'fleet', label: 'Fleet', icon: 'fleet' },
  { id: 'repo', label: 'Repo', icon: 'repo' },
  { id: 'workers', label: 'Workers', icon: 'workers' },
  { id: 'comms', label: 'Comms', icon: 'comms' }
];

const FILTERS = ['ALL', 'WARN', 'ERROR'];

const ICONS = {
  overview: (
    <>
      <path d="M4 5h16" />
      <path d="M4 12h10" />
      <path d="M4 19h16" />
    </>
  ),
  fleet: (
    <>
      <path d="M6 7h12v10H6z" />
      <path d="M9 7V4h6v3" />
      <path d="M9 17v3" />
      <path d="M15 17v3" />
    </>
  ),
  repo: (
    <>
      <path d="M12 3 5 6v6c0 4 3 7 7 9 4-2 7-5 7-9V6z" />
      <path d="M9 12l2 2 4-5" />
    </>
  ),
  workers: (
    <>
      <path d="M5 7h14v10H5z" />
      <path d="M8 10h3" />
      <path d="M8 14h8" />
      <path d="M7 20h10" />
    </>
  ),
  comms: (
    <>
      <path d="M5 6h14v10H8l-3 3z" />
      <path d="M8 10h8" />
      <path d="M8 13h5" />
    </>
  ),
  pause: (
    <>
      <path d="M8 5v14" />
      <path d="M16 5v14" />
    </>
  ),
  play: <path d="M8 5v14l11-7z" />,
  send: (
    <>
      <path d="M4 12 20 4l-5 16-3-7z" />
      <path d="m12 13 8-9" />
    </>
  ),
  close: (
    <>
      <path d="M6 6l12 12" />
      <path d="M18 6 6 18" />
    </>
  )
};

const trendOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  scales: {
    x: { display: false },
    y: {
      min: 0,
      max: 100,
      border: { display: false },
      grid: { color: 'rgba(149, 164, 181, 0.1)' },
      ticks: {
        stepSize: 25,
        color: 'rgba(210, 218, 228, 0.45)',
        font: { size: 10, family: "'JetBrains Mono', monospace" }
      }
    }
  },
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  elements: { point: { radius: 0 }, line: { tension: 0.36, borderWidth: 2 } }
};

const ringOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '76%',
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  animation: { duration: 300 }
};

function Icon({ name }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
      {ICONS[name] || ICONS.overview}
    </svg>
  );
}

function StatusPill({ tone = 'info', children }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function IconButton({ icon, label, onClick, disabled = false, pressed = false }) {
  return (
    <button
      className="icon-button"
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={pressed}
      title={label}
    >
      <Icon name={icon} />
    </button>
  );
}

function Panel({ title, meta, tone = 'info', focus, activeFocus, className = '', actions, children }) {
  const dimmed = activeFocus !== 'overview' && focus && focus !== activeFocus;
  return (
    <section className={`command-panel ${className} ${dimmed ? 'is-dimmed' : ''}`}>
      <div className="panel-titlebar">
        <div>
          <span className={`panel-indicator ${tone}`} />
          <h2>{title}</h2>
          {meta && <p>{meta}</p>}
        </div>
        {actions && <div className="panel-actions">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

function NavRail({ activeFocus, setActiveFocus }) {
  return (
    <nav className="nav-rail" aria-label="Dashboard focus">
      {NAV_ITEMS.map(item => (
        <button
          key={item.id}
          className={`rail-button ${activeFocus === item.id ? 'active' : ''}`}
          type="button"
          onClick={() => setActiveFocus(item.id)}
          title={item.label}
        >
          <Icon name={item.icon} />
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

function TopologyMap({ nodes }) {
  return (
    <div className="topology-map" aria-label="Bridge execution topology">
      {nodes.map((node, index) => (
        <div className="topology-step" key={node.id}>
          <div className={`topology-node ${node.tone}`}>
            <div className="node-label">{node.label}</div>
            <div className="node-detail">{node.detail}</div>
            <div className="node-metric">{node.metric}</div>
          </div>
          {index < nodes.length - 1 && <div className={`topology-link ${node.tone}`} />}
        </div>
      ))}
    </div>
  );
}

function MissionSummary({ sysStatus, topology }) {
  const repoSummary = sysStatus.repoContext?.summary || {};
  const fleet = sysStatus.fleet || {};
  return (
    <Panel
      title="Mission Control"
      meta={`Last sample ${formatTimestamp(sysStatus.statusTimestamp)}`}
      tone={sysStatus.online ? 'success' : 'danger'}
      className="mission-panel"
    >
      <div className="mission-body">
        <div className="mission-copy">
          <div className="call-sign">JULES NEXUS</div>
          <h1>{sysStatus.online ? 'Bridge is holding the room.' : 'Bridge status poll is offline.'}</h1>
          <p>
            {sysStatus.executionContext} on {sysStatus.hostname}; Quantower is{' '}
            {sysStatus.quantAllowed ? 'enabled for this node' : 'locked for this node'}.
          </p>
          <div className="mission-pills">
            <StatusPill tone={sysStatus.tunnel ? 'success' : 'warn'}>
              {sysStatus.tunnel ? 'Tunnel active' : 'Local relay'}
            </StatusPill>
            <StatusPill tone={sysStatus.ghostLocked ? 'success' : 'info'}>
              {sysStatus.ghostLocked ? 'Ghost locked' : 'Ghost off'}
            </StatusPill>
            <StatusPill tone={gateTone(sysStatus)}>{sysStatus.quantAllowed ? 'Quant enabled' : 'Quant locked'}</StatusPill>
            <StatusPill tone={(repoSummary.collision_count || 0) > 0 ? 'warn' : 'success'}>
              {repoSummary.collision_count || 0} collisions
            </StatusPill>
            <StatusPill tone={(fleet.failed || 0) > 0 ? 'danger' : 'info'}>
              {fleet.pending || 0} pending
            </StatusPill>
          </div>
        </div>
        <TopologyMap nodes={topology} />
      </div>
    </Panel>
  );
}

function TrendTile({ label, value, tone, history, color }) {
  const labels = useMemo(() => history.map((_, index) => index), [history]);
  const data = useMemo(
    () => ({
      labels,
      datasets: [
        {
          data: history,
          borderColor: color,
          backgroundColor: `${color}22`,
          fill: true
        }
      ]
    }),
    [color, history, labels]
  );

  return (
    <div className={`trend-tile ${tone}`}>
      <div className="trend-head">
        <span>{label}</span>
        <strong>{value.toFixed(1)}%</strong>
      </div>
      <div className="trend-chart">
        <Line data={data} options={trendOptions} />
      </div>
    </div>
  );
}

function Meter({ label, value, tone }) {
  return (
    <div className="meter-row">
      <div className="meter-label">
        <span>{label}</span>
        <strong>{value.toFixed(1)}%</strong>
      </div>
      <div className="meter-track">
        <span className={tone} style={{ width: `${clampPercent(value)}%` }} />
      </div>
    </div>
  );
}

function TelemetryPanel({ sysStatus, cpuHistory, memHistory, activeFocus }) {
  const pressureTone = sysStatus.mem > 85 || sysStatus.cpu > 85 ? 'warn' : toneForStatus(sysStatus.resourceStatus);
  return (
    <Panel
      title="Telemetry"
      meta={String(sysStatus.resourceStatus).toUpperCase()}
      tone={pressureTone}
      focus="fleet"
      activeFocus={activeFocus}
      className="telemetry-panel"
    >
      <div className="telemetry-grid">
        <TrendTile label="CPU" value={sysStatus.cpu} tone={sysStatus.cpu > 85 ? 'warn' : 'info'} history={cpuHistory} color="#61a8ff" />
        <TrendTile label="Memory" value={sysStatus.mem} tone={sysStatus.mem > 85 ? 'warn' : 'success'} history={memHistory} color="#45d483" />
      </div>
      <div className="pressure-deck">
        <Meter label="CPU pressure" value={sysStatus.cpu} tone={sysStatus.cpu > 85 ? 'warn' : 'info'} />
        <Meter label="Memory pressure" value={sysStatus.mem} tone={sysStatus.mem > 85 ? 'warn' : 'success'} />
      </div>
      {sysStatus.pressureReasons.length > 0 && (
        <div className="reason-list">
          {sysStatus.pressureReasons.slice(0, 4).map((reason, index) => (
            <span key={`${reason}-${index}`}>{reason}</span>
          ))}
        </div>
      )}
    </Panel>
  );
}

function OpsChecklist({ items, activeFocus }) {
  return (
    <Panel title="No Slop Checklist" meta="Live gates" tone="info" focus="overview" activeFocus={activeFocus} className="ops-panel">
      <div className="ops-list">
        {items.map(item => (
          <div className="ops-row" key={item.id}>
            <div className={`ops-light ${item.tone}`} />
            <div className="ops-main">
              <div>
                <strong>{item.label}</strong>
                <span>{item.state}</span>
              </div>
              <p>{item.detail}</p>
              <div className="ops-progress">
                <span className={item.tone} style={{ width: `${item.progress}%` }} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function FleetPanel({ fleet, activeFocus }) {
  const launched = Number(fleet.launched || 0);
  const completed = Number(fleet.completed || 0);
  const failed = Number(fleet.failed || 0);
  const inProgress = Number(fleet.in_progress || 0);
  const pending = Number(fleet.pending || 0);
  const rest = Math.max(launched - completed, launched === 0 ? 1 : 0);
  const data = useMemo(
    () => ({
      datasets: [
        {
          data: [completed, rest],
          backgroundColor: ['#45d483', 'rgba(255, 255, 255, 0.06)'],
          borderWidth: 0
        }
      ]
    }),
    [completed, rest]
  );

  return (
    <Panel
      title="Fleet Queue"
      meta={`${launched} launches tracked`}
      tone={failed > 0 ? 'danger' : pending > 0 || inProgress > 0 ? 'warn' : 'success'}
      focus="fleet"
      activeFocus={activeFocus}
      className="fleet-panel"
    >
      <div className="fleet-body">
        <div className="fleet-ring">
          <Doughnut data={data} options={ringOptions} />
          <div>
            <strong>{completed}</strong>
            <span>complete</span>
          </div>
        </div>
        <div className="fleet-bars">
          {[
            ['Complete', completed, 'success'],
            ['Active', inProgress, 'info'],
            ['Pending', pending, 'warn'],
            ['Failed', failed, 'danger']
          ].map(([label, count, tone]) => (
            <div className="fleet-bar-row" key={label}>
              <span>{label}</span>
              <div className="fleet-bar">
                <span className={tone} style={{ width: `${Math.max((Number(count) / Math.max(launched, 1)) * 100, Number(count) > 0 ? 8 : 0)}%` }} />
              </div>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function WorkerDirectory({ workers, cloud, selectedWorkerKey, setSelectedWorkerKey, activeFocus }) {
  return (
    <Panel
      title="Worker Directory"
      meta={`${cloud.online || 0}/${cloud.total || 0} online`}
      tone={(cloud.total || 0) === 0 ? 'warn' : (cloud.online || 0) > 0 ? 'success' : 'danger'}
      focus="workers"
      activeFocus={activeFocus}
      className="workers-panel"
    >
      <div className="worker-table">
        <div className="worker-head">
          <span>Node</span>
          <span>Provider</span>
          <span>Endpoint</span>
          <span>Status</span>
        </div>
        {workers.length === 0 ? (
          <div className="empty-state">No cloud workers configured.</div>
        ) : (
          workers.map((vm, index) => {
            const key = workerKey(vm, index);
            const tone = vm?.reachable ? 'success' : toneForStatus(vm?.status);
            return (
              <button
                className={`worker-entry ${selectedWorkerKey === key ? 'selected' : ''}`}
                type="button"
                key={key}
                onClick={() => setSelectedWorkerKey(key)}
              >
                <span className="worker-node">
                  <i className={`worker-light ${tone}`} />
                  {vm?.name || 'unnamed'}
                </span>
                <span>{vm?.provider || 'worker'}</span>
                <span>{maskEndpoint(vm?.ip)}</span>
                <span className={tone}>{vm?.status || 'unknown'}</span>
              </button>
            );
          })
        )}
      </div>
    </Panel>
  );
}

function RepoGuard({ repoContext, selectedCollisionKey, setSelectedCollisionKey, activeFocus }) {
  const summary = repoContext?.summary || {};
  const collisions = Array.isArray(repoContext?.collisions) ? repoContext.collisions : [];
  const guardrails = Array.isArray(repoContext?.guardrails) ? repoContext.guardrails : [];
  const severityCounts = summary.collision_severity_counts || {};
  const tone = (summary.collision_count || 0) > 0 ? 'warn' : toneForStatus(repoContext?.status);
  return (
    <Panel
      title="Repo Collision Matrix"
      meta={`${summary.repo_count || 0} repos scanned`}
      tone={tone}
      focus="repo"
      activeFocus={activeFocus}
      className="repo-panel"
    >
      <div className="repo-metrics">
        <div>
          <span>Collisions</span>
          <strong>{summary.collision_count || 0}</strong>
        </div>
        <div>
          <span>Warnings</span>
          <strong>{severityCounts.warning || 0}</strong>
        </div>
        <div>
          <span>Cache</span>
          <strong>{repoContext?.cache_age_s ?? 0}s</strong>
        </div>
      </div>
      <div className="guardrail-grid">
        {guardrails.length === 0 ? (
          <span>No guardrails reported</span>
        ) : (
          guardrails.slice(0, 4).map((rule, index) => <span key={`${rule}-${index}`}>{rule}</span>)
        )}
      </div>
      <div className="collision-table">
        {collisions.length === 0 ? (
          <div className="empty-state">No collisions reported.</div>
        ) : (
          collisions.slice(0, 8).map((collision, index) => {
            const key = collisionKey(collision, index);
            const severity = collision.severity || 'info';
            return (
              <button
                className={`collision-entry ${selectedCollisionKey === key ? 'selected' : ''}`}
                type="button"
                key={key}
                onClick={() => setSelectedCollisionKey(key)}
              >
                <span className={`collision-dot ${severity}`} />
                <span>{collision.type || 'collision'}</span>
                <strong>{collision.key || 'key hidden'}</strong>
                <em>{impactedReposLabel(collision)}</em>
              </button>
            );
          })
        )}
      </div>
    </Panel>
  );
}

function EventConsole({ rows, filter, setFilter, paused, togglePaused, activeFocus }) {
  const filteredRows = rows.filter(row => filter === 'ALL' || row.level === filter);
  return (
    <Panel
      title="Evidence Stream"
      meta={paused ? 'Paused' : 'Live tail'}
      tone={paused ? 'warn' : 'info'}
      focus="overview"
      activeFocus={activeFocus}
      className="stream-panel"
      actions={
        <>
          <div className="filter-cluster">
            {FILTERS.map(item => (
              <button
                className={filter === item ? 'active' : ''}
                type="button"
                key={item}
                onClick={() => setFilter(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <IconButton icon={paused ? 'play' : 'pause'} label={paused ? 'Resume stream' : 'Pause stream'} onClick={togglePaused} pressed={paused} />
        </>
      }
    >
      <div className="event-console">
        {filteredRows.length === 0 ? (
          <div className="empty-state">Awaiting telemetry.</div>
        ) : (
          filteredRows.slice(-60).map(row => (
            <div className={`event-row ${row.level}`} key={row.id}>
              <span>{row.timestamp || '--'}</span>
              <strong>{row.level}</strong>
              <em>{row.source}</em>
              <p>{row.message}</p>
            </div>
          ))
        )}
      </div>
    </Panel>
  );
}

function Inspector({ sysStatus, worker, collision }) {
  const workerTone = worker?.reachable ? 'success' : toneForStatus(worker?.status);
  const collisionTone = collision?.severity === 'critical' ? 'danger' : collision?.severity === 'warning' ? 'warn' : 'info';
  return (
    <Panel title="Inspector" meta="Selected evidence" tone="info" className="inspector-panel">
      <div className="inspector-section">
        <div className="inspector-title">
          <span className={`panel-indicator ${workerTone}`} />
          <h3>{worker ? 'Worker' : 'Worker lane'}</h3>
        </div>
        {worker ? (
          <dl className="inspector-list">
            <div>
              <dt>Name</dt>
              <dd>{worker.name || 'unnamed'}</dd>
            </div>
            <div>
              <dt>Provider</dt>
              <dd>{worker.provider || 'worker'}</dd>
            </div>
            <div>
              <dt>Zone</dt>
              <dd>{worker.zone || 'unknown'}</dd>
            </div>
            <div>
              <dt>Endpoint</dt>
              <dd>{maskEndpoint(worker.ip)}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd className={workerTone}>{worker.status || 'unknown'}</dd>
            </div>
          </dl>
        ) : (
          <p className="inspector-empty">Select a worker row.</p>
        )}
      </div>
      <div className="inspector-section">
        <div className="inspector-title">
          <span className={`panel-indicator ${collisionTone}`} />
          <h3>{collision ? 'Collision' : 'Repo guard'}</h3>
        </div>
        {collision ? (
          <dl className="inspector-list">
            <div>
              <dt>Type</dt>
              <dd>{collision.type || 'collision'}</dd>
            </div>
            <div>
              <dt>Key</dt>
              <dd>{collision.key || 'hidden'}</dd>
            </div>
            <div>
              <dt>Severity</dt>
              <dd className={collisionTone}>{collision.severity || 'info'}</dd>
            </div>
            <div>
              <dt>Impact</dt>
              <dd>{impactedReposLabel(collision)}</dd>
            </div>
          </dl>
        ) : (
          <p className="inspector-empty">No collision selected.</p>
        )}
      </div>
      <div className="inspector-section compact">
        <div className="runtime-stack">
          <span>Runtime</span>
          <strong>{sysStatus.executionContext}</strong>
          <em>{sysStatus.quantAllowed ? 'Quantower enabled' : 'Quantower locked'}</em>
        </div>
      </div>
    </Panel>
  );
}

function CommPanel({
  chatHistory,
  chatBoxRef,
  isThinking,
  model,
  setModel,
  pendingImage,
  setPendingImage,
  inputValue,
  setInputValue,
  sendChat,
  onKey
}) {
  return (
    <Panel
      title="Comm Link"
      meta="Jules channel"
      tone="info"
      focus="comms"
      activeFocus="comms"
      className="comm-panel"
      actions={
        <select className="model-select" value={model} onChange={event => setModel(event.target.value)} title="Select model">
          <option value="fast">flash fast</option>
          <option value="smart">pro smart</option>
        </select>
      }
    >
      <div className="chat-messages" ref={chatBoxRef}>
        {chatHistory.map((message, index) => (
          <div className={`msg ${message.role}`} key={`${message.role}-${index}`}>
            {message.content}
            {message.img && <img src={message.img} alt="attached visual" className="img-preview" />}
            {message.meta && <div className="msg-meta">{message.meta}</div>}
          </div>
        ))}
        {isThinking && (
          <div className="msg ai thinking">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
      <div className="chat-input-area">
        {pendingImage && (
          <div className="img-strip">
            <img src={pendingImage.src} alt="attachment thumbnail" />
            <span className="img-label">Visual attached</span>
            <IconButton icon="close" label="Remove attachment" onClick={() => setPendingImage(null)} />
          </div>
        )}
        <div className="chat-row">
          <textarea
            className="chat-input"
            placeholder="Message Jules..."
            value={inputValue}
            onChange={event => setInputValue(event.target.value)}
            onKeyDown={onKey}
            rows={1}
            title="Message input"
          />
          <IconButton icon="send" label="Send message" onClick={sendChat} disabled={isThinking} />
        </div>
      </div>
    </Panel>
  );
}

function App() {
  const [sysStatus, setSysStatus] = useState(DEFAULT_STATUS);
  const [cpuHistory, setCpuHistory] = useState(Array(36).fill(0));
  const [memHistory, setMemHistory] = useState(Array(36).fill(0));
  const [chatHistory, setChatHistory] = useState([
    { role: 'sys', content: 'JULES ONLINE. Secure channel established.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [pendingImage, setPendingImage] = useState(null);
  const [model, setModel] = useState('fast');
  const [isThinking, setIsThinking] = useState(false);
  const [activeFocus, setActiveFocus] = useState('overview');
  const [selectedWorkerKey, setSelectedWorkerKey] = useState('');
  const [selectedCollisionKey, setSelectedCollisionKey] = useState('');
  const [streamPaused, setStreamPaused] = useState(false);
  const [streamSnapshot, setStreamSnapshot] = useState([]);
  const [eventFilter, setEventFilter] = useState('ALL');
  const chatBoxRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${BRIDGE}/dashboard/status`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`status ${response.status}`);
        const payload = await response.json();
        if (!mounted) return;
        const nextStatus = normalizeDashboardPayload(payload);
        setSysStatus(nextStatus);
        setCpuHistory(previous => [...previous.slice(1), nextStatus.cpu]);
        setMemHistory(previous => [...previous.slice(1), nextStatus.mem]);
      } catch {
        if (mounted) {
          setSysStatus(previous => ({ ...previous, online: false, uptime: 'OFFLINE', bridgeStatus: 'offline' }));
        }
      }
    };

    fetchStatus();
    const timer = setInterval(fetchStatus, 2000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory, isThinking]);

  useEffect(() => {
    const handlePaste = event => {
      const items = (event.clipboardData || window.clipboardData)?.items || [];
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          event.preventDefault();
          const blob = item.getAsFile();
          const reader = new FileReader();
          reader.onload = loadEvent => {
            const src = loadEvent.target.result;
            const base64 = src.split(',')[1];
            setPendingImage({ base64, src });
          };
          reader.readAsDataURL(blob);
          break;
        }
      }
    };
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, []);

  const cloud = sysStatus.cloud || DEFAULT_STATUS.cloud;
  const workers = useMemo(() => (Array.isArray(cloud.vms) ? cloud.vms : []), [cloud]);
  const repoContext = sysStatus.repoContext || DEFAULT_STATUS.repoContext;
  const collisions = useMemo(
    () => (Array.isArray(repoContext.collisions) ? repoContext.collisions : []),
    [repoContext]
  );

  useEffect(() => {
    if (workers.length === 0) {
      setSelectedWorkerKey('');
      return;
    }
    if (!workers.some((worker, index) => workerKey(worker, index) === selectedWorkerKey)) {
      setSelectedWorkerKey(workerKey(workers[0], 0));
    }
  }, [selectedWorkerKey, workers]);

  useEffect(() => {
    if (collisions.length === 0) {
      setSelectedCollisionKey('');
      return;
    }
    if (!collisions.some((collision, index) => collisionKey(collision, index) === selectedCollisionKey)) {
      setSelectedCollisionKey(collisionKey(collisions[0], 0));
    }
  }, [collisions, selectedCollisionKey]);

  const selectedWorker = workers.find((worker, index) => workerKey(worker, index) === selectedWorkerKey);
  const selectedCollision = collisions.find((collision, index) => collisionKey(collision, index) === selectedCollisionKey);
  const topology = useMemo(() => buildTopology(sysStatus), [sysStatus]);
  const opsItems = useMemo(() => buildOpsChecklist(sysStatus), [sysStatus]);
  const eventRows = useMemo(
    () => buildEventRows(streamPaused ? streamSnapshot : sysStatus.logs),
    [streamPaused, streamSnapshot, sysStatus.logs]
  );

  const togglePaused = () => {
    if (streamPaused) {
      setStreamPaused(false);
      setStreamSnapshot([]);
      return;
    }
    setStreamSnapshot(sysStatus.logs);
    setStreamPaused(true);
  };

  const sendChat = async () => {
    const message = inputValue.trim();
    if (!message && !pendingImage) return;

    const currentImage = pendingImage;
    setInputValue('');
    setPendingImage(null);
    setChatHistory(previous => [
      ...previous,
      { role: 'user', content: message || '[screenshot]', img: currentImage?.src }
    ]);
    setIsThinking(true);

    try {
      const payload = { message: message || 'Analyze this visual data.', model };
      if (currentImage) payload.image_base64 = currentImage.base64;
      const response = await fetch(`${BRIDGE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      const reply = data.response || 'No response.';
      const meta = data.model_used ? `${data.model_used} - ${data.elapsed_ms}ms` : '';
      setChatHistory(previous => [...previous, { role: 'ai', content: reply, meta }]);
    } catch (error) {
      setChatHistory(previous => [...previous, { role: 'sys', content: `COMM LINK FAILED: ${error.message}` }]);
    } finally {
      setIsThinking(false);
    }
  };

  const onKey = event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChat();
    }
  };

  return (
    <div className="dashboard-shell" data-focus={activeFocus}>
      <header className="command-bar">
        <div className="brand-lockup">
          <span className={`live-dot ${sysStatus.online ? 'online' : 'offline'}`} />
          <div>
            <strong>Jules Bridge</strong>
            <span>{sysStatus.localUrl || BRIDGE}</span>
          </div>
        </div>
        <div className="command-status">
          <StatusPill tone={sysStatus.online ? 'success' : 'danger'}>{sysStatus.online ? 'LIVE' : 'OFFLINE'}</StatusPill>
          <StatusPill tone={sysStatus.tunnel ? 'success' : 'warn'}>{sysStatus.tunnel ? 'TUNNEL' : 'LOCAL'}</StatusPill>
          <StatusPill tone={sysStatus.ghostLocked ? 'success' : 'info'}>{sysStatus.ghostLocked ? 'GHOST LOCK' : 'GHOST OFF'}</StatusPill>
          <StatusPill tone={gateTone(sysStatus)}>{sysStatus.executionContext}</StatusPill>
          <StatusPill tone={sysStatus.quantAllowed ? 'success' : 'warn'}>{sysStatus.quantAllowed ? 'QUANT ON' : 'QUANT LOCKED'}</StatusPill>
        </div>
      </header>

      <NavRail activeFocus={activeFocus} setActiveFocus={setActiveFocus} />

      <main className="operations-grid">
        <MissionSummary sysStatus={sysStatus} topology={topology} />
        <TelemetryPanel sysStatus={sysStatus} cpuHistory={cpuHistory} memHistory={memHistory} activeFocus={activeFocus} />
        <OpsChecklist items={opsItems} activeFocus={activeFocus} />
        <FleetPanel fleet={sysStatus.fleet || DEFAULT_STATUS.fleet} activeFocus={activeFocus} />
        <WorkerDirectory
          workers={workers}
          cloud={cloud}
          selectedWorkerKey={selectedWorkerKey}
          setSelectedWorkerKey={setSelectedWorkerKey}
          activeFocus={activeFocus}
        />
        <RepoGuard
          repoContext={repoContext}
          selectedCollisionKey={selectedCollisionKey}
          setSelectedCollisionKey={setSelectedCollisionKey}
          activeFocus={activeFocus}
        />
        <EventConsole
          rows={eventRows}
          filter={eventFilter}
          setFilter={setEventFilter}
          paused={streamPaused}
          togglePaused={togglePaused}
          activeFocus={activeFocus}
        />
      </main>

      <aside className="side-column">
        <Inspector sysStatus={sysStatus} worker={selectedWorker} collision={selectedCollision} />
        <CommPanel
          chatHistory={chatHistory}
          chatBoxRef={chatBoxRef}
          isThinking={isThinking}
          model={model}
          setModel={setModel}
          pendingImage={pendingImage}
          setPendingImage={setPendingImage}
          inputValue={inputValue}
          setInputValue={setInputValue}
          sendChat={sendChat}
          onKey={onKey}
        />
      </aside>
    </div>
  );
}

export default App;
