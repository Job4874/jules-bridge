export const EMPTY_REPO_CONTEXT = {
  status: 'unknown',
  summary: { repo_count: 0, collision_count: 0, collision_severity_counts: {} },
  collisions: [],
  guardrails: []
};

export const EMPTY_CLOUD = { total: 0, online: 0, vms: [] };

export const DEFAULT_STATUS = {
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
  fleet: {
    launched: 0,
    completed: 0,
    pending: 0,
    failed: 0,
    in_progress: 0,
    all_complete: false,
    sessions_tracked: 0
  },
  cloud: EMPTY_CLOUD,
  repoContext: EMPTY_REPO_CONTEXT,
  secretCount: 0,
  statusTimestamp: '',
  cacheAge: 0,
  bridgeStatus: 'unknown',
  localUrl: '',
  ghostLocked: false,
  ghostHostId: '',
  logs: []
};

export const clampPercent = value => Math.max(0, Math.min(100, Number(value) || 0));

export const toneForStatus = status => {
  const value = String(status || '').toLowerCase();
  if (['ready', 'ok', 'online', 'running', 'normal', 'pass', 'live', 'healthy'].includes(value)) return 'success';
  if (['partial', 'stale', 'warning', 'warn', 'provisioning', 'local_only', 'busy'].includes(value)) return 'warn';
  if (['error', 'offline', 'failed', 'fail', 'danger', 'critical'].includes(value)) return 'danger';
  return 'info';
};

export const gateTone = status => {
  const context = status?.executionContext || '[SCHOOL_COMPUTE]';
  if (context === '[SCHOOL_COMPUTE]' && !status?.quantAllowed) return 'success';
  if ((context === '[LOCAL]' || context === '[REMOTE_VM]') && status?.quantAllowed) return 'success';
  return 'warn';
};

export const maskEndpoint = value => {
  const text = String(value || '').trim();
  if (!text || text === 'unknown') return 'not configured';
  const parts = text.split('.');
  if (parts.length === 4 && parts.every(part => /^\d+$/.test(part))) {
    return `${parts[0]}.${parts[1]}.x.x`;
  }
  return 'configured';
};

export const workerKey = (vm, index = 0) => [
  vm?.provider || 'worker',
  vm?.name || 'unnamed',
  vm?.zone || 'zone',
  index
].join(':');

export const collisionKey = (collision, index = 0) => [
  collision?.type || 'collision',
  collision?.key || 'key',
  collision?.severity || 'info',
  index
].join(':');

export const impactedReposLabel = collision => {
  const names = Array.isArray(collision?.repo_names) ? collision.repo_names : [];
  const count = names.length || Number(collision?.repo_count || collision?.affected_repo_count || 0);
  return count > 0 ? `${count} repo refs` : 'refs hidden';
};

export const formatTimestamp = value => {
  if (!value) return 'not sampled';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(date);
};

export const normalizeDashboardPayload = payload => {
  const pressure = payload.resource_pressure || {};
  const repoContext = payload.repo_context || EMPTY_REPO_CONTEXT;
  const bridge = payload.bridge || {};
  return {
    uptime: bridge.uptime_human || '--',
    online: payload.ok !== false,
    tunnel: !!bridge.ngrok_url,
    hostname: payload.hostname || '--',
    executionContext: payload.execution_context || '[SCHOOL_COMPUTE]',
    quantAllowed: !!payload.quant_allowed,
    resourceStatus: pressure.status || 'unknown',
    pressureReasons: Array.isArray(pressure.reasons) ? pressure.reasons : [],
    cpu: clampPercent(pressure.cpu_percent ?? 0),
    mem: clampPercent(pressure.memory_percent ?? 0),
    fleet: payload.jules_fleet || DEFAULT_STATUS.fleet,
    cloud: payload.cloud || EMPTY_CLOUD,
    repoContext,
    secretCount: Array.isArray(payload.env_keys_present) ? payload.env_keys_present.length : 0,
    statusTimestamp: payload.timestamp || '',
    cacheAge: payload.cache_age_s ?? 0,
    bridgeStatus: bridge.status || 'unknown',
    localUrl: bridge.local_url || '',
    ghostLocked: !!payload.ghost?.ghost_locked,
    ghostHostId: payload.ghost?.host_id || '',
    logs: Array.isArray(payload.recent_logs) ? payload.recent_logs : []
  };
};

export const parseLogLine = (line, index = 0) => {
  const text = String(line || '');
  const match = text.match(/^(\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\])\s*(.*)$/);
  const timestamp = match ? match[1] : '';
  const message = match ? match[2] : text;
  const upper = message.toUpperCase();
  let level = 'INFO';
  if (/(ERROR|FAIL|CRITICAL|TRACEBACK|EXCEPTION)/.test(upper)) level = 'ERROR';
  else if (/(WARN|WARNING|STALE|TIMEOUT|OFFLINE|MAXED|BLOCKED)/.test(upper)) level = 'WARN';
  else if (/(READY|COMPLETE|SUCCESS|ONLINE|HEALTHY|STARTED)/.test(upper)) level = 'OK';

  const sourceMatch = message.match(/^\[?([A-Z][A-Z0-9_-]{2,})\]?\s*[:|-]/);
  return {
    id: `${index}-${message.slice(0, 24)}`,
    timestamp,
    source: sourceMatch ? sourceMatch[1] : 'bridge',
    level,
    message
  };
};

export const buildEventRows = logs => logs.map((line, index) => parseLogLine(line, index));

export const buildOpsChecklist = status => {
  const fleet = status.fleet || DEFAULT_STATUS.fleet;
  const cloud = status.cloud || EMPTY_CLOUD;
  const repoSummary = status.repoContext?.summary || EMPTY_REPO_CONTEXT.summary;
  const failures = Number(fleet.failed || 0);
  const pending = Number(fleet.pending || 0);
  const inProgress = Number(fleet.in_progress || 0);
  const collisions = Number(repoSummary.collision_count || 0);
  const workerTotal = Number(cloud.total || 0);
  const workerOnline = Number(cloud.online || 0);

  return [
    {
      id: 'bridge',
      label: 'Bridge route',
      state: status.online ? (status.tunnel ? 'Tunnel live' : 'Local relay') : 'Offline',
      detail: status.online ? `${status.bridgeStatus}; cache ${status.cacheAge}s` : 'status poll failed',
      tone: status.online ? (status.tunnel ? 'success' : 'warn') : 'danger',
      progress: status.online ? 100 : 0
    },
    {
      id: 'ghost',
      label: 'Ghost mode',
      state: status.ghostLocked ? 'Locked' : 'Unlocked',
      detail: status.ghostLocked
        ? `Always-on enforced on ${status.ghostHostId || 'school host'}`
        : 'Bridge can be stopped without unlock password',
      tone: status.ghostLocked ? 'success' : 'info',
      progress: status.ghostLocked ? 100 : 35
    },
    {
      id: 'context',
      label: 'Context gate',
      state: status.quantAllowed ? 'Quant allowed' : 'Quant locked',
      detail: `${status.executionContext} on ${status.hostname}`,
      tone: gateTone(status),
      progress: 100
    },
    {
      id: 'fleet',
      label: 'Fleet queue',
      state: failures > 0 ? `${failures} failed` : `${pending} pending`,
      detail: `${fleet.completed || 0}/${fleet.launched || 0} complete; ${inProgress} active`,
      tone: failures > 0 ? 'danger' : pending > 0 || inProgress > 0 ? 'warn' : 'success',
      progress: Number(fleet.launched || 0) > 0 ? clampPercent((Number(fleet.completed || 0) / Number(fleet.launched || 1)) * 100) : 0
    },
    {
      id: 'workers',
      label: 'Worker lane',
      state: `${workerOnline}/${workerTotal} online`,
      detail: workerTotal > 0 ? 'remote compute inventory masked' : 'no workers configured',
      tone: workerTotal === 0 ? 'warn' : workerOnline > 0 ? 'success' : 'danger',
      progress: workerTotal > 0 ? clampPercent((workerOnline / workerTotal) * 100) : 0
    },
    {
      id: 'repo',
      label: 'Repo guard',
      state: `${collisions} collisions`,
      detail: `${repoSummary.repo_count || 0} repos scanned; names hidden`,
      tone: collisions > 0 ? 'warn' : toneForStatus(status.repoContext?.status),
      progress: collisions > 0 ? 55 : 100
    }
  ];
};

export const buildTopology = status => {
  const fleet = status.fleet || DEFAULT_STATUS.fleet;
  const cloud = status.cloud || EMPTY_CLOUD;
  const repoSummary = status.repoContext?.summary || EMPTY_REPO_CONTEXT.summary;
  const failures = Number(fleet.failed || 0);
  const collisions = Number(repoSummary.collision_count || 0);
  return [
    {
      id: 'bridge',
      label: 'Bridge',
      detail: status.online ? status.uptime : 'offline',
      tone: status.online ? (status.tunnel ? 'success' : 'warn') : 'danger',
      metric: status.tunnel ? 'public tunnel' : 'local relay'
    },
    {
      id: 'ghost',
      label: 'Ghost',
      detail: status.ghostLocked ? 'always-on locked' : 'unlocked',
      tone: status.ghostLocked ? 'success' : 'info',
      metric: status.ghostHostId || 'school-64gb'
    },
    {
      id: 'runtime',
      label: 'Runtime Gate',
      detail: status.executionContext,
      tone: gateTone(status),
      metric: status.quantAllowed ? 'quant enabled' : 'quant locked'
    },
    {
      id: 'fleet',
      label: 'Jules Fleet',
      detail: `${fleet.completed || 0}/${fleet.launched || 0}`,
      tone: failures > 0 ? 'danger' : Number(fleet.pending || 0) > 0 ? 'warn' : 'success',
      metric: `${fleet.pending || 0} pending`
    },
    {
      id: 'workers',
      label: 'Cloud Workers',
      detail: `${cloud.online || 0}/${cloud.total || 0}`,
      tone: Number(cloud.total || 0) === 0 ? 'warn' : Number(cloud.online || 0) > 0 ? 'success' : 'danger',
      metric: 'endpoints masked'
    },
    {
      id: 'repo',
      label: 'Repo Guard',
      detail: `${collisions}`,
      tone: collisions > 0 ? 'warn' : toneForStatus(status.repoContext?.status),
      metric: 'collision watch'
    },
    {
      id: 'comms',
      label: 'Comms',
      detail: `${status.secretCount} refs`,
      tone: status.secretCount > 0 ? 'success' : 'warn',
      metric: 'secrets hidden'
    }
  ];
};
