import { useState, useEffect, useRef } from 'react';
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

const EMPTY_REPO_CONTEXT = {
  status: 'unknown',
  summary: { repo_count: 0, collision_count: 0, collision_severity_counts: {} },
  collisions: [],
  guardrails: []
};

const EMPTY_CLOUD = { total: 0, online: 0, vms: [] };

const clampPercent = value => Math.max(0, Math.min(100, Number(value) || 0));

const toneForStatus = status => {
  const value = String(status || '').toLowerCase();
  if (['ready', 'ok', 'online', 'running', 'normal', 'pass'].includes(value)) return 'success';
  if (['partial', 'stale', 'warning', 'warn', 'provisioning'].includes(value)) return 'warn';
  if (['error', 'offline', 'failed', 'fail', 'danger'].includes(value)) return 'danger';
  return 'info';
};

const maskEndpoint = value => {
  const text = String(value || '').trim();
  if (!text || text === 'unknown') return 'not configured';
  const parts = text.split('.');
  if (parts.length === 4 && parts.every(part => /^\d+$/.test(part))) {
    return `${parts[0]}.${parts[1]}.x.x`;
  }
  return 'configured';
};

const impactedReposLabel = collision => {
  const names = Array.isArray(collision?.repo_names) ? collision.repo_names : [];
  const count = names.length || Number(collision?.repo_count || collision?.affected_repo_count || 0);
  return count > 0 ? `${count} repo refs` : 'refs hidden';
};

function SignalTile({ label, value, detail, tone = 'info' }) {
  return (
    <div className={`signal-tile ${tone}`}>
      <div className="signal-label">{label}</div>
      <div className="signal-value">{value}</div>
      <div className="signal-detail">{detail}</div>
    </div>
  );
}

function PhaseBar({ fleet }) {
  const launched = Number(fleet?.launched || 0);
  const completed = Number(fleet?.completed || 0);
  const failed = Number(fleet?.failed || 0);
  const inProgress = Number(fleet?.in_progress || 0);
  const pending = Number(fleet?.pending || 0);
  const total = Math.max(launched, completed + failed + inProgress + pending, 1);
  const segments = [
    ['complete', completed],
    ['active', inProgress],
    ['failed', failed],
    ['pending', pending],
  ];

  return (
    <div className="phase-wrap" aria-label="Fleet phase distribution">
      <div className="phase-bar">
        {segments.map(([name, count]) => (
          <span
            key={name}
            className={`phase-segment ${name}`}
            style={{ width: `${Math.max((count / total) * 100, count > 0 ? 4 : 0)}%` }}
            title={`${name}: ${count}`}
          />
        ))}
      </div>
      <div className="phase-legend">
        <span>DONE {completed}</span>
        <span>ACTIVE {inProgress}</span>
        <span>FAILED {failed}</span>
        <span>PENDING {pending}</span>
      </div>
    </div>
  );
}

function WorkerRow({ vm }) {
  const tone = vm?.reachable ? 'success' : toneForStatus(vm?.status);
  return (
    <div className="worker-row">
      <span className={`worker-led ${tone}`} />
      <span className="worker-provider">{vm?.provider || 'worker'}</span>
      <span className="worker-name">{vm?.name || 'unnamed'}</span>
      <span className="worker-endpoint">{maskEndpoint(vm?.ip)}</span>
      <span className={`worker-state ${tone}`}>{vm?.status || 'unknown'}</span>
    </div>
  );
}

// Chart common options
const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  scales: {
    x: { display: false },
    y: {
      min: 0,
      max: 100,
      border: { display: false },
      grid: { color: 'rgba(255,255,255,0.05)' },
      ticks: { stepSize: 25, font: { size: 10, family: "'JetBrains Mono', monospace" } }
    }
  },
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  elements: { point: { radius: 0 }, line: { tension: 0.4, borderWidth: 2 } }
};

const ringOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '80%',
  plugins: { legend: { display: false }, tooltip: { enabled: false } },
  animation: { animateScale: true }
};

function App() {
  const [sysStatus, setSysStatus] = useState({
    uptime: '--',
    online: false,
    tunnel: false,
    hostname: '--',
    executionContext: '[SCHOOL_COMPUTE]',
    quantAllowed: false,
    resourceStatus: 'unknown',
    pressureReasons: [],
    cpu: 0,
    mem: 0,
    fleet: { launched: 0, completed: 0, pending: 0 },
    cloud: EMPTY_CLOUD,
    repoContext: EMPTY_REPO_CONTEXT,
    secretCount: 0,
    statusTimestamp: '',
    cacheAge: 0,
    logs: []
  });

  const [cpuHistory, setCpuHistory] = useState(Array(30).fill(0));
  const [memHistory, setMemHistory] = useState(Array(30).fill(0));

  const [chatHistory, setChatHistory] = useState([
    { role: 'sys', content: 'JULES ONLINE. Secure channel established.' }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [pendingImage, setPendingImage] = useState(null);
  const [model, setModel] = useState('fast');
  const [isThinking, setIsThinking] = useState(false);
  
  const chatBoxRef = useRef(null);
  const logFeedRef = useRef(null);

  // Polling
  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${BRIDGE}/dashboard/status`, { cache: 'no-store' });
        if (!res.ok) throw new Error('Bad response');
        const d = await res.json();
        
        if (!mounted) return;

        const cpu = clampPercent(d.resource_pressure?.cpu_percent ?? 0);
        const mem = clampPercent(d.resource_pressure?.memory_percent ?? 0);
        const pressure = d.resource_pressure || {};

        setSysStatus({
          uptime: d.bridge?.uptime_human || '--',
          online: true,
          tunnel: !!d.bridge?.ngrok_url,
          hostname: d.hostname || '--',
          executionContext: d.execution_context || '[SCHOOL_COMPUTE]',
          quantAllowed: !!d.quant_allowed,
          resourceStatus: pressure.status || 'unknown',
          pressureReasons: Array.isArray(pressure.reasons) ? pressure.reasons : [],
          cpu,
          mem,
          fleet: d.jules_fleet || { launched: 0, completed: 0, pending: 0 },
          cloud: d.cloud || EMPTY_CLOUD,
          repoContext: d.repo_context || EMPTY_REPO_CONTEXT,
          secretCount: Array.isArray(d.env_keys_present) ? d.env_keys_present.length : 0,
          statusTimestamp: d.timestamp || '',
          cacheAge: d.cache_age_s ?? 0,
          logs: d.recent_logs || []
        });

        setCpuHistory(prev => {
          const next = [...prev, cpu];
          next.shift();
          return next;
        });
        setMemHistory(prev => {
          const next = [...prev, mem];
          next.shift();
          return next;
        });

      } catch {
        if (mounted) {
          setSysStatus(s => ({ ...s, online: false, uptime: 'OFFLINE' }));
        }
      }
    };

    const timer = setInterval(fetchStatus, 2000);
    fetchStatus(); // initial
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  // Auto-scroll logs and chat
  useEffect(() => {
    if (logFeedRef.current) {
      logFeedRef.current.scrollTop = logFeedRef.current.scrollHeight;
    }
  }, [sysStatus.logs]);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory, isThinking]);

  // Handle paste
  useEffect(() => {
    const handlePaste = (e) => {
      const items = (e.clipboardData || window.clipboardData).items;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const blob = item.getAsFile();
          const reader = new FileReader();
          reader.onload = (ev) => {
            const b64 = ev.target.result.split(',')[1];
            setPendingImage({ base64: b64, src: ev.target.result });
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
    const msg = inputValue.trim();
    if (!msg && !pendingImage) return;

    const currentImg = pendingImage;
    setInputValue('');
    setPendingImage(null);

    const newUserMsg = { role: 'user', content: msg || '[screenshot]', img: currentImg?.src };
    setChatHistory(prev => [...prev, newUserMsg]);
    setIsThinking(true);

    try {
      const payload = { message: msg || 'Analyze this visual data.', model };
      if (currentImg) payload.image_base64 = currentImg.base64;
      
      const res = await fetch(`${BRIDGE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      const reply = data.response || 'No response.';
      const meta = data.model_used ? `${data.model_used} · ${data.elapsed_ms}ms` : '';
      setChatHistory(prev => [...prev, { role: 'ai', content: reply, meta }]);
    } catch (e) {
      setChatHistory(prev => [...prev, { role: 'sys', content: 'COMM LINK FAILED: ' + e.message }]);
    } finally {
      setIsThinking(false);
    }
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  };

  const repoContext = sysStatus.repoContext || {};
  const repoSummary = repoContext.summary || {};
  const repoCollisions = repoContext.collisions || [];
  const guardrails = Array.isArray(repoContext.guardrails) ? repoContext.guardrails : [];
  const severityCounts = repoSummary.collision_severity_counts || {};
  const cloud = sysStatus.cloud || EMPTY_CLOUD;
  const workers = Array.isArray(cloud.vms) ? cloud.vms : [];
  const fleet = sysStatus.fleet || {};
  const bridgeTone = sysStatus.online ? (sysStatus.tunnel ? 'success' : 'warn') : 'danger';
  const runtimeTone = sysStatus.quantAllowed ? 'success' : 'danger';
  const repoTone = (repoSummary.collision_count ?? 0) > 0 ? 'warn' : toneForStatus(repoContext.status);
  const pressureTone = sysStatus.mem > 85 || sysStatus.cpu > 85 ? 'warn' : toneForStatus(sysStatus.resourceStatus);

  return (
    <div className="dashboard-container">
      <div className="header">
        <h1>
          <div className={`status-dot ${!sysStatus.online ? 'offline' : ''}`} />
          JULES NEXUS
        </h1>
        <div className="header-metrics">
          <div className={`badge ${sysStatus.online ? '' : 'danger'}`}>
            SYS_UP: {sysStatus.uptime}
          </div>
          <div className={`badge ${sysStatus.tunnel ? 'success' : 'danger'}`}>
            TUNNEL: {sysStatus.tunnel ? 'ACTIVE' : 'OFFLINE'}
          </div>
          <div className={`badge ${sysStatus.quantAllowed ? 'success' : 'danger'}`}>
            CTX: {sysStatus.executionContext} / QUANT: {sysStatus.quantAllowed ? 'ENABLED' : 'LOCKED'}
          </div>
        </div>
      </div>

      <div className="mission-strip">
        <SignalTile
          label="Bridge"
          value={sysStatus.online ? 'LIVE' : 'OFFLINE'}
          detail={sysStatus.tunnel ? 'tunnel active' : `cache ${sysStatus.cacheAge}s`}
          tone={bridgeTone}
        />
        <SignalTile
          label="Runtime Gate"
          value={sysStatus.executionContext}
          detail={`${sysStatus.quantAllowed ? 'Quantower allowed' : 'Quantower locked'} on ${sysStatus.hostname}; ${sysStatus.secretCount} key refs`}
          tone={runtimeTone}
        />
        <SignalTile
          label="Fleet Queue"
          value={`${fleet.completed ?? 0}/${fleet.launched ?? 0}`}
          detail={`${fleet.pending ?? 0} pending, ${fleet.failed ?? 0} failed`}
          tone={(fleet.failed ?? 0) > 0 ? 'danger' : (fleet.pending ?? 0) > 0 ? 'warn' : 'success'}
        />
        <SignalTile
          label="Repo Guard"
          value={`${repoSummary.collision_count ?? 0} collisions`}
          detail={`${repoSummary.repo_count ?? 0} repos scanned`}
          tone={repoTone}
        />
      </div>

      <div className="main-content">
        {/* Left Side: Telemetry & Logs */}
        <div className="left-panel">
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-label">CPU Utilization</div>
              <div className="metric-value blue">{sysStatus.cpu.toFixed(1)}%</div>
              <div className="chart-container">
                <Line
                  data={{
                    labels: Array(30).fill(''),
                    datasets: [{
                      data: cpuHistory,
                      borderColor: '#58a6ff',
                      backgroundColor: 'rgba(88, 166, 255, 0.1)',
                      fill: true,
                    }]
                  }}
                  options={lineOptions}
                />
              </div>
            </div>
            
            <div className="metric-card">
              <div className="metric-label">Memory Utilization</div>
              <div className="metric-value green">{sysStatus.mem.toFixed(1)}%</div>
              <div className="chart-container">
                <Line
                  data={{
                    labels: Array(30).fill(''),
                    datasets: [{
                      data: memHistory,
                      borderColor: '#3fb950',
                      backgroundColor: 'rgba(63, 185, 80, 0.1)',
                      fill: true,
                    }]
                  }}
                  options={lineOptions}
                />
              </div>
            </div>
          </div>

          <div className="panel" style={{ height: '140px', flex: 'none', marginBottom: '1rem' }}>
            <div className="panel-header">Fleet Status</div>
            <div className="panel-content fleet-content">
              <div className="fleet-rings">
                <div className="ring-wrap">
                  <Doughnut
                    data={{
                      datasets: [{
                        data: [sysStatus.fleet.launched, sysStatus.fleet.pending === 0 && sysStatus.fleet.launched === 0 ? 1 : sysStatus.fleet.pending],
                        backgroundColor: ['#58a6ff', 'rgba(255,255,255,0.05)'],
                        borderWidth: 0
                      }]
                    }}
                    options={ringOptions}
                  />
                  <div className="ring-label">
                    <div>{sysStatus.fleet.launched}</div>
                    <span>LAUNCHED</span>
                  </div>
                </div>
              
                <div className="ring-wrap">
                  <Doughnut
                    data={{
                      datasets: [{
                        data: [sysStatus.fleet.completed, sysStatus.fleet.launched > sysStatus.fleet.completed ? sysStatus.fleet.launched - sysStatus.fleet.completed : (sysStatus.fleet.completed === 0 ? 1 : 0)],
                        backgroundColor: ['#3fb950', 'rgba(255,255,255,0.05)'],
                        borderWidth: 0
                      }]
                    }}
                    options={ringOptions}
                  />
                  <div className="ring-label green">
                    <div>{sysStatus.fleet.completed}</div>
                    <span>COMPLETED</span>
                  </div>
                </div>
              </div>
              <PhaseBar fleet={sysStatus.fleet} />
            </div>
          </div>

          <div className="panel worker-panel">
            <div className="panel-header">
              <span>Cloud Workers</span>
              <span className={`badge ${cloud.online > 0 ? 'success' : 'danger'}`}>
                {cloud.online ?? 0}/{cloud.total ?? 0} ONLINE
              </span>
            </div>
            <div className="panel-content worker-list">
              {workers.length === 0 ? (
                <div className="worker-empty">No cloud workers configured</div>
              ) : (
                workers.slice(0, 4).map((vm, i) => <WorkerRow vm={vm} key={`${vm.provider}-${vm.name}-${i}`} />)
              )}
            </div>
          </div>

          <div className="panel" style={{ height: '230px', flex: 'none', marginBottom: '1rem' }}>
            <div className="panel-header">
              <span>Repo Context Guard</span>
              <span className={`badge ${repoContext.status === 'ready' ? 'success' : repoContext.status === 'error' ? 'danger' : ''}`}>
                {(repoContext.status || 'unknown').toUpperCase()}
              </span>
            </div>
            <div className="panel-content repo-guard">
              <div className="repo-stats">
                <div className="repo-stat">
                  <span>Repos</span>
                  <strong>{repoSummary.repo_count ?? 0}</strong>
                </div>
                <div className="repo-stat">
                  <span>Collisions</span>
                  <strong className={(repoSummary.collision_count ?? 0) > 0 ? 'warn' : ''}>
                    {repoSummary.collision_count ?? 0}
                  </strong>
                </div>
                <div className="repo-stat">
                  <span>Warn</span>
                  <strong className={(severityCounts.warning ?? 0) > 0 ? 'warn' : ''}>
                    {severityCounts.warning ?? 0}
                  </strong>
                </div>
                <div className="repo-stat">
                  <span>Cache</span>
                  <strong>{repoContext.cache_age_s ?? 0}s</strong>
                </div>
              </div>
              <div className="guardrail-strip">
                {guardrails.slice(0, 2).map((rule, i) => (
                  <span key={`${rule}-${i}`}>{rule}</span>
                ))}
              </div>
              <div className="collision-list">
                {repoCollisions.length === 0 ? (
                  <div className="collision-empty">No collisions reported</div>
                ) : (
                  repoCollisions.slice(0, 5).map((collision, i) => (
                    <div className="collision-row" key={`${collision.type}-${collision.key}-${i}`}>
                      <span className={`collision-severity ${collision.severity || 'info'}`} />
                      <span className="collision-main">
                        <strong>{collision.type}</strong>
                        <em>{collision.key}</em>
                      </span>
                      <span className="collision-repos">{impactedReposLabel(collision)}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="panel" style={{ flex: 1 }}>
            <div className="panel-header">
              <span>Terminal Stream</span>
              <span className={`badge ${pressureTone}`}>{String(sysStatus.resourceStatus).toUpperCase()}</span>
            </div>
            <div className="panel-content log-feed" ref={logFeedRef}>
              {sysStatus.pressureReasons.length > 0 && (
                <div className="pressure-reasons">
                  {sysStatus.pressureReasons.slice(0, 3).map((reason, i) => (
                    <span key={`${reason}-${i}`}>{reason}</span>
                  ))}
                </div>
              )}
              {sysStatus.logs.length === 0 ? (
                <div style={{ color: 'var(--text-dim)' }}>Awaiting telemetry...</div>
              ) : (
                sysStatus.logs.slice(-50).map((line, i) => {
                  const match = line.match(/^(\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\]) (.*)/);
                  let ts = '', msg = line, lvl = 'INFO';
                  if (match) { ts = match[1]; msg = match[2]; }
                  if (msg.includes('ERROR') || msg.includes('FAIL')) lvl = 'ERROR';
                  else if (msg.includes('WARN')) lvl = 'WARN';
                  
                  return (
                    <div className="log-line" key={i}>
                      <span className="log-ts">{ts}</span>
                      <span className={`log-lvl ${lvl}`}>[{lvl}]</span>
                      <span className="log-msg">{msg}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Chat */}
        <div className="panel right-panel">
          <div className="panel-header">
            <span>Comm Link</span>
            <select
              value={model}
              onChange={e => setModel(e.target.value)}
              title="Select LLM model"
              style={{
                background: 'transparent',
                color: 'var(--accent-blue)',
                border: 'none',
                outline: 'none',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                cursor: 'pointer'
              }}
            >
              <option value="fast">flash (fast)</option>
              <option value="smart">pro (smart)</option>
            </select>
          </div>
          <div className="panel-content chat-messages" ref={chatBoxRef}>
            {chatHistory.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.content}
                {m.img && <img src={m.img} alt="clip" className="img-preview" />}
                {m.meta && <div className="msg-meta">{m.meta}</div>}
              </div>
            ))}
            {isThinking && (
              <div className="msg ai" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-dim)', animation: 'bounce 0.6s infinite alternate' }}></span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-dim)', animation: 'bounce 0.6s infinite alternate 0.2s' }}></span>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--text-dim)', animation: 'bounce 0.6s infinite alternate 0.4s' }}></span>
              </div>
            )}
          </div>
          
          <div className="chat-input-area">
            {pendingImage && (
              <div className="img-strip">
                <img src={pendingImage.src} alt="thumbnail" />
                <span className="img-label">Visual data attached</span>
                <button className="btn-clear" onClick={() => setPendingImage(null)} title="Remove attachment">✕</button>
              </div>
            )}
            <div className="chat-row">
              <textarea
                className="chat-input"
                placeholder="Enter command or paste image..."
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={onKey}
                rows={1}
                title="Message Input"
              />
              <button 
                className="btn-send"
                onClick={sendChat}
                disabled={isThinking}
                title="Send Message"
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
