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
  allianceTone,
  buildAllianceLanes,
  buildEventRows,
  buildOpsChecklist,
  buildTopology,
  clampPercent,
  cloudSyncLabel,
  cloudSyncTone,
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
  { id: 'tiu', label: 'TIU', icon: 'tiu' },
  { id: 'alliance', label: 'Alliance', icon: 'alliance' },
  { id: 'sync', label: 'Sync', icon: 'sync' },
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
  tiu: (
    <>
      <path d="M5 5h14v5H5z" />
      <path d="M5 14h6v5H5z" />
      <path d="M15 14h4v5h-4z" />
      <path d="M8 10v4" />
      <path d="M17 10v4" />
    </>
  ),
  alliance: (
    <>
      <path d="M7 6h4v4H7z" />
      <path d="M13 14h4v4h-4z" />
      <path d="M11 8h3.5a2.5 2.5 0 0 1 0 5H10a2.5 2.5 0 0 0 0 5h3" />
      <path d="M17 9l2-2-2-2" />
      <path d="M7 19l-2-2 2-2" />
    </>
  ),
  sync: (
    <>
      <path d="M20 7h-8a4 4 0 0 0-4 4v1" />
      <path d="m17 4 3 3-3 3" />
      <path d="M4 17h8a4 4 0 0 0 4-4v-1" />
      <path d="m7 20-3-3 3-3" />
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

const ALLIANCE_FILTERS = ['ALL', 'READY', 'ATTENTION'];

const TIU_SCOPES = [
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'model_bridge', label: 'Model Bridge' },
  { value: 'cloud_sync', label: 'Cloud Sync' },
  { value: 'full_bridge', label: 'Full Bridge' }
];

const TIU_LANES = [
  { value: 'alliance', label: 'Alliance' },
  { value: 'antigravity_cli', label: 'Antigravity' },
  { value: 'gemini_cli', label: 'Gemini CLI' },
  { value: 'jules_only', label: 'Jules Only' }
];

const TIU_MODES = [
  { value: 'design_review', label: 'Design Review' },
  { value: 'implementation', label: 'Implementation' },
  { value: 'verification', label: 'Verification' },
  { value: 'publish_gate', label: 'Publish Gate' }
];

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

function TiuWorkbench({ sysStatus, activeFocus, onStagePacket }) {
  const [objective, setObjective] = useState('Build the next polished dashboard and model-bridge UI slice.');
  const [scope, setScope] = useState('dashboard');
  const [modelLane, setModelLane] = useState('alliance');
  const [mode, setMode] = useState('design_review');
  const [requireCloudSync, setRequireCloudSync] = useState(true);
  const [includeLiveChecks, setIncludeLiveChecks] = useState(false);
  const [writePacket, setWritePacket] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState(null);

  const sync = sysStatus.cloudSync || DEFAULT_STATUS.cloudSync;
  const codebaseSummary = sysStatus.codebase?.summary || {};
  const resultTone = result?.status === 'ready' ? 'success' : result?.status === 'blocked' ? 'warn' : result?.status === 'error' ? 'danger' : 'info';
  const blockers = Array.isArray(result?.blockers) ? result.blockers : [];
  const warnings = Array.isArray(result?.warnings) ? result.warnings : [];

  const runWorkbench = async () => {
    const cleanObjective = objective.trim();
    if (!cleanObjective) return;
    setIsRunning(true);
    try {
      if (!TOKEN) {
        throw new Error('protected route token is not configured for this dashboard session');
      }
      const response = await fetch(`${BRIDGE}/tiu/workbench`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
        body: JSON.stringify({
          objective: cleanObjective,
          scope,
          model_lane: modelLane,
          mode,
          require_cloud_sync: requireCloudSync,
          include_live_checks: includeLiveChecks,
          write_packet: writePacket,
          timeout_s: includeLiveChecks ? 18 : 8
        })
      });
      const data = await response.json();
      if (!response.ok && !data.status) {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      setResult(data);
    } catch (error) {
      setResult({
        status: 'error',
        plan_state: 'error',
        blockers: ['tiu_route_unreachable'],
        warnings: [],
        packet: '',
        error: error.message,
        artifacts: { packet_written: false, packet_path: '' }
      });
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <Panel
      title="TIU Workbench"
      meta={`${scope} - ${modelLane}`}
      tone={result ? resultTone : 'info'}
      focus="tiu"
      activeFocus={activeFocus}
      className="tiu-panel"
      actions={
        <button className="primary-action" type="button" onClick={runWorkbench} disabled={isRunning}>
          {isRunning ? 'Building' : 'Generate Packet'}
        </button>
      }
    >
      <div className="tiu-readiness-grid">
        <div>
          <span>Alliance</span>
          <strong>{sysStatus.alliance?.ready_to_execute_alliance ? 'Ready' : sysStatus.alliance?.status || 'Unknown'}</strong>
        </div>
        <div>
          <span>Codebase</span>
          <strong>{codebaseSummary.route_count || 0} routes</strong>
        </div>
        <div>
          <span>Sync Gate</span>
          <strong>{cloudSyncLabel(sync)}</strong>
        </div>
        <div>
          <span>Mode</span>
          <strong>{mode.replaceAll('_', ' ')}</strong>
        </div>
      </div>
      <div className="tiu-controls">
        <label className="tiu-objective">
          <span>Objective</span>
          <textarea value={objective} onChange={event => setObjective(event.target.value)} rows={3} />
        </label>
        <label>
          <span>Scope</span>
          <select value={scope} onChange={event => setScope(event.target.value)}>
            {TIU_SCOPES.map(item => <option value={item.value} key={item.value}>{item.label}</option>)}
          </select>
        </label>
        <label>
          <span>Lane</span>
          <select value={modelLane} onChange={event => setModelLane(event.target.value)}>
            {TIU_LANES.map(item => <option value={item.value} key={item.value}>{item.label}</option>)}
          </select>
        </label>
        <label>
          <span>Mode</span>
          <select value={mode} onChange={event => setMode(event.target.value)}>
            {TIU_MODES.map(item => <option value={item.value} key={item.value}>{item.label}</option>)}
          </select>
        </label>
      </div>
      <div className="tiu-switches">
        {[
          ['Cloud gate', requireCloudSync, setRequireCloudSync],
          ['Live checks', includeLiveChecks, setIncludeLiveChecks],
          ['Save packet', writePacket, setWritePacket]
        ].map(([label, checked, setter]) => (
          <label className="switch-row" key={label}>
            <input type="checkbox" checked={checked} onChange={event => setter(event.target.checked)} />
            <span>{label}</span>
          </label>
        ))}
      </div>
      {result && (
        <div className={`tiu-result ${resultTone}`}>
          <div className="tiu-result-head">
            <StatusPill tone={resultTone}>{result.plan_state || result.status}</StatusPill>
            <span>{result.artifacts?.packet_written ? 'Saved locally' : result.error || 'Packet staged in dashboard'}</span>
          </div>
          {(blockers.length > 0 || warnings.length > 0) && (
            <div className="tiu-issues">
              {[...blockers.map(item => ['danger', item]), ...warnings.map(item => ['warn', item])].slice(0, 6).map(([tone, item]) => (
                <span className={tone} key={`${tone}-${item}`}>{String(item).replaceAll('_', ' ')}</span>
              ))}
            </div>
          )}
          {result.packet && <pre>{result.packet}</pre>}
          {result.packet && (
            <button className="secondary-action" type="button" onClick={() => onStagePacket(result.packet)}>
              Stage To Comms
            </button>
          )}
        </div>
      )}
    </Panel>
  );
}

function AllianceControl({ sysStatus, activeFocus }) {
  const [filter, setFilter] = useState('ALL');
  const [selectedLaneId, setSelectedLaneId] = useState('jules');
  const alliance = sysStatus.alliance || DEFAULT_STATUS.alliance;
  const lanes = useMemo(() => buildAllianceLanes(sysStatus), [sysStatus]);
  const visibleLanes = lanes.filter(lane => {
    if (filter === 'READY') return lane.tone === 'success';
    if (filter === 'ATTENTION') return lane.tone !== 'success';
    return true;
  });
  const selectedLane = lanes.find(lane => lane.id === selectedLaneId) || visibleLanes[0] || lanes[0];
  const tone = allianceTone(alliance);

  useEffect(() => {
    if (lanes.length > 0 && !lanes.some(lane => lane.id === selectedLaneId)) {
      setSelectedLaneId(lanes[0].id);
    }
  }, [lanes, selectedLaneId]);

  return (
    <Panel
      title="Alliance Control"
      meta={`${alliance.mode || 'unconfigured'} - ${alliance.packet_count || 0} packets`}
      tone={tone}
      focus="alliance"
      activeFocus={activeFocus}
      className="alliance-panel"
      actions={
        <div className="filter-cluster alliance-filters">
          {ALLIANCE_FILTERS.map(item => (
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
      }
    >
      <div className="alliance-summary-grid">
        <div>
          <span>Creator</span>
          <strong>{alliance.creator || 'jules'}</strong>
        </div>
        <div>
          <span>Implementer</span>
          <strong>{alliance.implementer || 'unassigned'}</strong>
        </div>
        <div>
          <span>Gates</span>
          <strong>{alliance.gate_pass_count || 0}/{alliance.gate_total_count || 0}</strong>
        </div>
        <div>
          <span>Live Work</span>
          <strong>{alliance.safe_to_launch_live_work ? 'Open' : 'Gated'}</strong>
        </div>
      </div>
      <div className="alliance-ribbon">
        <StatusPill tone={tone}>
          {alliance.ready_to_execute_alliance ? 'ALLIANCE READY' : alliance.status === 'missing' ? 'ALLIANCE MISSING' : 'ALLIANCE PARTIAL'}
        </StatusPill>
        <span>{alliance.summary || 'Switchboard snapshot unavailable.'}</span>
      </div>
      <div className="alliance-lanes">
        {visibleLanes.map(lane => (
          <button
            className={`alliance-lane ${lane.tone} ${selectedLane?.id === lane.id ? 'selected' : ''}`}
            type="button"
            key={lane.id}
            onClick={() => setSelectedLaneId(lane.id)}
          >
            <span className={`worker-light ${lane.tone}`} />
            <div>
              <strong>{lane.label}</strong>
              <em>{lane.role}</em>
            </div>
            <b>{lane.state}</b>
          </button>
        ))}
      </div>
      {selectedLane && (
        <div className={`alliance-detail ${selectedLane.tone}`}>
          <div>
            <span>{selectedLane.label}</span>
            <strong>{selectedLane.state}</strong>
          </div>
          <p>{selectedLane.detail}</p>
        </div>
      )}
    </Panel>
  );
}

function CloudSyncPanel({ cloudSync, activeFocus, onStagePacket }) {
  const sync = cloudSync || DEFAULT_STATUS.cloudSync;
  const [writePacket, setWritePacket] = useState(true);
  const [isBuilding, setIsBuilding] = useState(false);
  const [publishPacket, setPublishPacket] = useState(null);
  const blockers = Array.isArray(sync.blockers) ? sync.blockers : [];
  const warnings = Array.isArray(sync.warnings) ? sync.warnings : [];
  const tone = cloudSyncTone(sync);
  const packetTone = publishPacket?.status === 'ready' ? 'success' : publishPacket?.status === 'blocked' ? 'warn' : publishPacket?.status === 'error' ? 'danger' : 'info';
  const packetFamilies = Array.isArray(publishPacket?.change_families) ? publishPacket.change_families : [];
  const packetCommands = Array.isArray(publishPacket?.commands) ? publishPacket.commands : [];

  const buildPublishPacket = async () => {
    setIsBuilding(true);
    try {
      if (!TOKEN) {
        throw new Error('protected route token is not configured for this dashboard session');
      }
      const response = await fetch(`${BRIDGE}/sync/publish-packet`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
        body: JSON.stringify({
          objective: 'Publish and synchronize the current Jules Bridge dashboard/model-agent work.',
          timeout_s: 8,
          use_cache: false,
          write_packet: writePacket
        })
      });
      const data = await response.json();
      if (!response.ok && !data.status) {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      setPublishPacket(data);
    } catch (error) {
      setPublishPacket({
        status: 'error',
        state: 'error',
        blockers: ['sync_publish_packet_unreachable'],
        warnings: [],
        change_families: [],
        commands: [],
        packet: '',
        error: error.message,
        artifacts: { packet_written: false, packet_path: '' }
      });
    } finally {
      setIsBuilding(false);
    }
  };

  return (
    <Panel
      title="Cloud Sync"
      meta={`${sync.remote_host || 'remote'} - ${sync.cache_age_s || 0}s cache`}
      tone={tone}
      focus="sync"
      activeFocus={activeFocus}
      className="cloud-sync-panel"
      actions={
        <button className="primary-action" type="button" onClick={buildPublishPacket} disabled={isBuilding}>
          {isBuilding ? 'Reviewing' : 'Build Publish Packet'}
        </button>
      }
    >
      <div className="sync-summary-grid">
        <div>
          <span>Branch</span>
          <strong>{sync.branch || 'unknown'}</strong>
        </div>
        <div>
          <span>Upstream</span>
          <strong>{sync.upstream || 'not set'}</strong>
        </div>
        <div>
          <span>Ahead / Behind</span>
          <strong>{sync.ahead || 0} / {sync.behind || 0}</strong>
        </div>
        <div>
          <span>Worktree</span>
          <strong>{sync.dirty_count || 0} dirty</strong>
        </div>
      </div>
      <div className="sync-ribbon">
        <StatusPill tone={tone}>{cloudSyncLabel(sync)}</StatusPill>
        <span>
          {sync.github_authenticated ? `GitHub ready${sync.github_account ? ` as ${sync.github_account}` : ''}` : 'GitHub auth not proven'}
        </span>
      </div>
      <div className="sync-meter-grid">
        {[
          ['Staged', sync.staged_count || 0, 'info'],
          ['Unstaged', sync.unstaged_count || 0, (sync.unstaged_count || 0) > 0 ? 'warn' : 'success'],
          ['Untracked', sync.untracked_count || 0, (sync.untracked_count || 0) > 0 ? 'warn' : 'success']
        ].map(([label, count, itemTone]) => (
          <div className="sync-meter" key={label}>
            <div>
              <span>{label}</span>
              <strong>{count}</strong>
            </div>
            <div className="meter-track">
              <span className={itemTone} style={{ width: `${Math.min(Number(count) * 14, 100)}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="sync-issue-list">
        {blockers.length === 0 && warnings.length === 0 ? (
          <div className="finding-row success">
            <strong>{sync.publish_ready ? 'Publish ready' : 'Cloud clean'}</strong>
            <span>{sync.publish_ready ? 'Local commits can be pushed intentionally.' : 'Local branch matches the tracked remote.'}</span>
          </div>
        ) : (
          [...blockers.map(item => ['danger', item]), ...warnings.map(item => ['warn', item])].slice(0, 5).map(([itemTone, item]) => (
            <div className={`finding-row ${itemTone}`} key={`${itemTone}-${item}`}>
              <strong>{String(item).replaceAll('_', ' ')}</strong>
              <span>{item === 'dirty_worktree' ? 'Review, stage, and commit intended changes before cloud publish.' : 'Resolve this sync gate before marking cloud sync complete.'}</span>
            </div>
          ))
        )}
      </div>
      <label className="sync-save-row">
        <input type="checkbox" checked={writePacket} onChange={event => setWritePacket(event.target.checked)} />
        <span>Save publish packet locally</span>
      </label>
      {publishPacket && (
        <div className={`publish-review ${packetTone}`}>
          <div className="publish-review-head">
            <StatusPill tone={packetTone}>{publishPacket.state || publishPacket.status}</StatusPill>
            <span>
              {publishPacket.artifacts?.packet_written ? 'Saved locally' : publishPacket.error || `${publishPacket.include_candidate_count || 0} publish candidates`}
            </span>
          </div>
          {packetFamilies.length > 0 && (
            <div className="publish-family-grid">
              {packetFamilies.slice(0, 8).map(row => (
                <div key={row.family}>
                  <span>{row.label || row.family}</span>
                  <strong>{row.count}</strong>
                </div>
              ))}
            </div>
          )}
          {packetCommands.length > 0 && (
            <div className="publish-command-list">
              {packetCommands.slice(0, 5).map(row => (
                <code key={`${row.label}-${row.command}`}>{row.cwd ? `${row.cwd}> ` : ''}{row.command}</code>
              ))}
            </div>
          )}
          {publishPacket.packet && (
            <button className="secondary-action" type="button" onClick={() => onStagePacket(publishPacket.packet)}>
              Stage To Comms
            </button>
          )}
        </div>
      )}
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

function CodebaseIntelligence({ codebase, activeFocus }) {
  const summary = codebase?.summary || {};
  const integrations = Array.isArray(codebase?.integrations) ? codebase.integrations : [];
  const findings = Array.isArray(codebase?.findings) ? codebase.findings : [];
  const tone = toneForStatus(codebase?.status);
  return (
    <Panel
      title="Codebase Intelligence"
      meta={`${codebase?.root_name || 'bridge root'} local snapshot`}
      tone={tone}
      focus="repo"
      activeFocus={activeFocus}
      className="codebase-panel"
    >
      <div className="codebase-metrics">
        {[
          ['Files', summary.file_count || 0],
          ['Routes', summary.route_count || 0],
          ['Modules', summary.module_count || 0],
          ['Tests', summary.test_count || 0]
        ].map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <div className="integration-grid">
        {integrations.length === 0 ? (
          <span className="empty-state">No integration snapshot reported.</span>
        ) : (
          integrations.slice(0, 8).map(item => (
            <span className={`integration-chip ${item.ready ? 'success' : 'warn'}`} key={item.id || item.label}>
              <i className={`worker-light ${item.ready ? 'success' : 'warn'}`} />
              {item.label || item.id}
            </span>
          ))
        )}
      </div>
      <div className="finding-list">
        {findings.length === 0 ? (
          <div className="empty-state">Analyzer has not emitted findings.</div>
        ) : (
          findings.slice(0, 4).map(item => (
            <div className={`finding-row ${item.tone || 'info'}`} key={`${item.title}-${item.detail}`}>
              <strong>{item.title}</strong>
              <span>{item.detail}</span>
            </div>
          ))
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
    let pollTimer = null;
    let startupTimer = null;
    let eventSource = null;
    let streamReceived = false;

    const applyStatusPayload = (payload, fallbackMode) => {
      if (!mounted) return;
      const nextStatus = normalizeDashboardPayload(payload);
      const mode = nextStatus.contractOk ? (nextStatus.updateMode || fallbackMode) : 'contract-drift';
      setSysStatus({ ...nextStatus, updateMode: mode });
      setCpuHistory(previous => [...previous.slice(1), nextStatus.cpu]);
      setMemHistory(previous => [...previous.slice(1), nextStatus.mem]);
    };

    const markOffline = () => {
      if (mounted) {
        setSysStatus(previous => ({
          ...previous,
          online: false,
          uptime: 'OFFLINE',
          bridgeStatus: 'offline',
          updateMode: 'offline'
        }));
      }
    };

    const stopPolling = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
    };

    const fetchStatus = async (mode = 'poll') => {
      try {
        const response = await fetch(`${BRIDGE}/dashboard/status`, { cache: 'no-store' });
        if (!response.ok) throw new Error(`status ${response.status}`);
        const payload = await response.json();
        applyStatusPayload(payload, mode);
      } catch {
        markOffline();
      }
    };

    const startPolling = (mode = 'poll') => {
      stopPolling();
      fetchStatus(mode);
      pollTimer = setInterval(() => fetchStatus(mode), 2000);
    };

    if (typeof window !== 'undefined' && 'EventSource' in window) {
      eventSource = new EventSource(`${BRIDGE}/dashboard/status?stream=1&interval_s=1`);
      setSysStatus(previous => ({ ...previous, updateMode: 'connecting' }));

      const handleStreamMessage = event => {
        try {
          streamReceived = true;
          if (startupTimer) {
            clearTimeout(startupTimer);
            startupTimer = null;
          }
          applyStatusPayload(JSON.parse(event.data), 'sse');
        } catch {
          setSysStatus(previous => ({ ...previous, updateMode: 'contract-drift' }));
        }
      };

      eventSource.addEventListener('dashboard-status', handleStreamMessage);
      eventSource.onmessage = handleStreamMessage;
      eventSource.onerror = () => {
        if (!mounted) return;
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        startPolling(streamReceived ? 'poll-fallback' : 'poll');
      };
      startupTimer = setTimeout(() => {
        if (!streamReceived) {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
          }
          startPolling('poll');
        }
      }, 5000);
    } else {
      startPolling('poll');
    }

    return () => {
      mounted = false;
      stopPolling();
      if (startupTimer) clearTimeout(startupTimer);
      if (eventSource) eventSource.close();
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
  const codebase = sysStatus.codebase || DEFAULT_STATUS.codebase;
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

  const stagePacketForComms = packet => {
    setInputValue(packet);
    setActiveFocus('comms');
  };
  let streamTone = 'warn';
  if (sysStatus.updateMode === 'sse') {
    streamTone = 'success';
  } else if (sysStatus.updateMode === 'offline' || sysStatus.updateMode === 'contract-drift') {
    streamTone = 'danger';
  }
  const streamLabel = {
    sse: `STREAM ${sysStatus.streamSequence || 0}`,
    connecting: 'STREAM ...',
    'poll-fallback': 'POLL FALLBACK',
    'contract-drift': 'CONTRACT DRIFT',
    offline: 'OFFLINE'
  }[sysStatus.updateMode] || 'POLLING';

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
          <StatusPill tone={streamTone}>{streamLabel}</StatusPill>
          <StatusPill tone={sysStatus.contractOk ? 'success' : 'danger'}>
            {sysStatus.contractOk ? `CONTRACT V${sysStatus.contract.version}` : 'CONTRACT WAIT'}
          </StatusPill>
          <StatusPill tone={sysStatus.tunnel ? 'success' : 'warn'}>{sysStatus.tunnel ? 'TUNNEL' : 'LOCAL'}</StatusPill>
          <StatusPill tone={sysStatus.geminiCli?.ready ? 'success' : sysStatus.geminiCli?.installed ? 'warn' : 'danger'}>
            {sysStatus.geminiCli?.ready ? 'GEMINI READY' : sysStatus.geminiCli?.installed ? 'GEMINI INSTALLED' : 'GEMINI MISSING'}
          </StatusPill>
          <StatusPill tone={sysStatus.antigravityCli?.ready ? 'success' : sysStatus.antigravityCli?.installed ? 'warn' : 'danger'}>
            {sysStatus.antigravityCli?.ready ? 'AGY READY' : sysStatus.antigravityCli?.installed ? 'AGY INSTALLED' : 'AGY MISSING'}
          </StatusPill>
          <StatusPill tone={allianceTone(sysStatus.alliance)}>
            {sysStatus.alliance?.ready_to_execute_alliance ? 'ALLIANCE READY' : 'ALLIANCE WATCH'}
          </StatusPill>
          <StatusPill tone={cloudSyncTone(sysStatus.cloudSync)}>
            {cloudSyncLabel(sysStatus.cloudSync)}
          </StatusPill>
          <StatusPill tone={gateTone(sysStatus)}>{sysStatus.executionContext}</StatusPill>
          <StatusPill tone={sysStatus.quantAllowed ? 'success' : 'warn'}>{sysStatus.quantAllowed ? 'QUANT ON' : 'QUANT LOCKED'}</StatusPill>
        </div>
      </header>

      <NavRail activeFocus={activeFocus} setActiveFocus={setActiveFocus} />

      <main className="operations-grid">
        <MissionSummary sysStatus={sysStatus} topology={topology} />
        <TiuWorkbench sysStatus={sysStatus} activeFocus={activeFocus} onStagePacket={stagePacketForComms} />
        <AllianceControl sysStatus={sysStatus} activeFocus={activeFocus} />
        <CloudSyncPanel
          cloudSync={sysStatus.cloudSync || DEFAULT_STATUS.cloudSync}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
        />
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
        <CodebaseIntelligence codebase={codebase} activeFocus={activeFocus} />
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
