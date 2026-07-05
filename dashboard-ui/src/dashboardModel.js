export const EMPTY_REPO_CONTEXT = {
  status: 'unknown',
  summary: { repo_count: 0, collision_count: 0, collision_severity_counts: {} },
  collisions: [],
  guardrails: []
};

export const EMPTY_CODEBASE_ANALYSIS = {
  status: 'unknown',
  root_name: '',
  summary: {
    file_count: 0,
    route_count: 0,
    module_count: 0,
    test_count: 0,
    frontend_dependency_count: 0,
    integration_ready_count: 0,
    truncated: false
  },
  frontend: { present: false, package_name: '', app_entry_present: false },
  integrations: [],
  findings: []
};

export const EMPTY_CLOUD = { total: 0, online: 0, vms: [] };

export const EMPTY_CLOUD_SYNC = {
  status: 'unknown',
  state: 'unknown',
  branch: '',
  upstream: '',
  remote_host: '',
  remote_label: '',
  ahead: 0,
  behind: 0,
  dirty_count: 0,
  staged_count: 0,
  unstaged_count: 0,
  untracked_count: 0,
  github_authenticated: false,
  github_account: '',
  publish_ready: false,
  synced: false,
  blockers: [],
  warnings: [],
  cache_age_s: 0
};

export const EMPTY_ALLIANCE = {
  status: 'unknown',
  summary: '',
  mode: 'unconfigured',
  creator: 'jules',
  implementer: 'unassigned',
  implementer_selection: '',
  ready_to_execute_alliance: false,
  simultaneous_two_agent_mode: false,
  safe_to_launch_live_work: false,
  required_blocker_count: 0,
  partial_caveat_count: 0,
  gate_pass_count: 0,
  gate_total_count: 0,
  packet_count: 0,
  workflow_step_count: 0,
  state_age_s: null,
  lanes: []
};

export const DEFAULT_STATUS = {
  uptime: '--',
  online: false,
  contract: { name: '', version: 0, transport: 'poll', sequence: 0 },
  contractOk: false,
  updateMode: 'connecting',
  streamSequence: 0,
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
  geminiCli: {
    installed: false,
    ready: false,
    version: '',
    headless_mode: '-p/--prompt',
    last_blocker: ''
  },
  antigravityCli: {
    installed: false,
    ready: false,
    version: '',
    headless_mode: '-p/--print',
    model_count: 0,
    last_blocker: ''
  },
  alliance: EMPTY_ALLIANCE,
  cloud: EMPTY_CLOUD,
  cloudSync: EMPTY_CLOUD_SYNC,
  repoContext: EMPTY_REPO_CONTEXT,
  codebase: EMPTY_CODEBASE_ANALYSIS,
  secretCount: 0,
  statusTimestamp: '',
  cacheAge: 0,
  bridgeStatus: 'unknown',
  localUrl: '',
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
  const safePayload = payload || {};
  const pressure = safePayload.resource_pressure || {};
  const repoContext = safePayload.repo_context || EMPTY_REPO_CONTEXT;
  const codebase = safePayload.codebase_analysis || EMPTY_CODEBASE_ANALYSIS;
  const alliance = safePayload.alliance || EMPTY_ALLIANCE;
  const cloudSync = safePayload.cloud_sync || EMPTY_CLOUD_SYNC;
  const bridge = safePayload.bridge || {};
  const contract = safePayload.contract || {};
  const delivery = safePayload.delivery || {};
  const sequence = Number(delivery.sequence ?? contract.sequence ?? 0);
  const transport = delivery.transport || contract.transport || 'poll';
  const contractOk = contract.name === 'jules_dashboard_status' && Number(contract.version || 0) >= 2;
  return {
    uptime: bridge.uptime_human || '--',
    online: safePayload.ok !== false,
    contract: {
      name: contract.name || '',
      version: Number(contract.version || 0),
      transport,
      sequence
    },
    contractOk,
    updateMode: transport,
    streamSequence: sequence,
    tunnel: !!bridge.ngrok_url,
    hostname: safePayload.hostname || '--',
    executionContext: safePayload.execution_context || '[SCHOOL_COMPUTE]',
    quantAllowed: !!safePayload.quant_allowed,
    resourceStatus: pressure.status || 'unknown',
    pressureReasons: Array.isArray(pressure.reasons) ? pressure.reasons : [],
    cpu: clampPercent(pressure.cpu_percent ?? 0),
    mem: clampPercent(pressure.memory_percent ?? 0),
    fleet: safePayload.jules_fleet || DEFAULT_STATUS.fleet,
    geminiCli: safePayload.gemini_cli || DEFAULT_STATUS.geminiCli,
    antigravityCli: safePayload.antigravity_cli || DEFAULT_STATUS.antigravityCli,
    alliance,
    cloud: safePayload.cloud || EMPTY_CLOUD,
    cloudSync,
    repoContext,
    codebase,
    secretCount: Array.isArray(safePayload.env_keys_present) ? safePayload.env_keys_present.length : 0,
    statusTimestamp: safePayload.timestamp || '',
    cacheAge: safePayload.cache_age_s ?? 0,
    bridgeStatus: bridge.status || 'unknown',
    localUrl: bridge.local_url || '',
    logs: Array.isArray(safePayload.recent_logs) ? safePayload.recent_logs : []
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

export const allianceTone = alliance => {
  if (!alliance || alliance.status === 'missing') return 'danger';
  if (Number(alliance.required_blocker_count || 0) > 0) return 'danger';
  if (Number(alliance.partial_caveat_count || 0) > 0 || !alliance.simultaneous_two_agent_mode) return 'warn';
  if (alliance.ready_to_execute_alliance) return 'success';
  return toneForStatus(alliance.status);
};

export const cloudSyncTone = cloudSync => {
  const sync = cloudSync || EMPTY_CLOUD_SYNC;
  if (sync.state === 'synced' || sync.publish_ready) return 'success';
  if (sync.status === 'blocked' || Number(sync.behind || 0) > 0) return 'danger';
  if (Number(sync.dirty_count || 0) > 0 || Number(sync.warnings?.length || 0) > 0) return 'warn';
  return toneForStatus(sync.status);
};

export const cloudSyncLabel = cloudSync => {
  const sync = cloudSync || EMPTY_CLOUD_SYNC;
  if (sync.publish_ready) return 'Push ready';
  if (sync.state === 'synced') return 'Synced';
  if (sync.state === 'blocked') return 'Blocked';
  if (Number(sync.behind || 0) > 0) return 'Pull needed';
  return sync.state || 'Unknown';
};

export const buildAllianceLanes = status => {
  const alliance = status.alliance || EMPTY_ALLIANCE;
  const laneRows = Array.isArray(alliance.lanes) ? alliance.lanes : [];
  const byId = new Map(laneRows.map(row => [row.id, row]));
  const cloud = status.cloud || EMPTY_CLOUD;
  const cloudSync = status.cloudSync || EMPTY_CLOUD_SYNC;
  const cloudOnline = Number(cloud.online || 0);
  const cloudTotal = Number(cloud.total || 0);

  const fromReadiness = (id, fallback) => {
    const row = byId.get(id) || {};
    const ready = !!row.ready;
    const installed = !!row.installed;
    const blocker = row.blocker || '';
    return {
      ...fallback,
      ready,
      state: ready ? 'Ready' : installed ? 'Installed' : 'Blocked',
      detail: blocker || fallback.detail,
      tone: ready ? 'success' : installed ? 'warn' : 'danger'
    };
  };

  return [
    fromReadiness('jules', {
      id: 'jules',
      label: 'Jules',
      role: 'creator',
      detail: 'Packets, patches, and ledgers ready.'
    }),
    fromReadiness('antigravity_cli', {
      id: 'antigravity_cli',
      label: 'Antigravity',
      role: 'google terminal agent',
      detail: 'Bounded implementation review ready.'
    }),
    fromReadiness('legacy_gemini_cli', {
      id: 'legacy_gemini_cli',
      label: 'Gemini CLI',
      role: 'legacy visibility',
      detail: 'Legacy skill surface visible.'
    }),
    fromReadiness('akc', {
      id: 'akc',
      label: 'AKC Context',
      role: 'checkpoint',
      detail: `${alliance.workflow_step_count || 0} workflow steps indexed.`
    }),
    fromReadiness('collaboration_proof_state', {
      id: 'collaboration_proof_state',
      label: 'Proof State',
      role: 'evidence',
      detail: `${alliance.gate_pass_count || 0}/${alliance.gate_total_count || 0} gates passing.`
    }),
    {
      id: 'sync',
      label: 'Cloud Sync',
      role: 'bridge relay',
      ready: status.online && cloudOnline > 0 && cloudSync.status !== 'blocked',
      state: cloudSyncLabel(cloudSync),
      detail: `${cloudOnline}/${cloudTotal} workers; git ${cloudSync.dirty_count || 0} dirty; ${cloudSync.ahead || 0} ahead.`,
      tone: cloudSyncTone(cloudSync)
    }
  ];
};

export const buildOpsChecklist = status => {
  const fleet = status.fleet || DEFAULT_STATUS.fleet;
  const gemini = status.geminiCli || DEFAULT_STATUS.geminiCli;
  const antigravity = status.antigravityCli || DEFAULT_STATUS.antigravityCli;
  const alliance = status.alliance || EMPTY_ALLIANCE;
  const cloud = status.cloud || EMPTY_CLOUD;
  const cloudSync = status.cloudSync || EMPTY_CLOUD_SYNC;
  const repoSummary = status.repoContext?.summary || EMPTY_REPO_CONTEXT.summary;
  const codebaseSummary = status.codebase?.summary || EMPTY_CODEBASE_ANALYSIS.summary;
  const failures = Number(fleet.failed || 0);
  const pending = Number(fleet.pending || 0);
  const inProgress = Number(fleet.in_progress || 0);
  const collisions = Number(repoSummary.collision_count || 0);
  const routeCount = Number(codebaseSummary.route_count || 0);
  const moduleCount = Number(codebaseSummary.module_count || 0);
  const testCount = Number(codebaseSummary.test_count || 0);
  const integrationReady = Number(codebaseSummary.integration_ready_count || 0);
  const workerTotal = Number(cloud.total || 0);
  const workerOnline = Number(cloud.online || 0);
  const geminiInstalled = !!gemini.installed;
  const geminiReady = !!gemini.ready;
  const agyInstalled = !!antigravity.installed;
  const agyReady = !!antigravity.ready;
  const allianceBlockers = Number(alliance.required_blocker_count || 0);
  const allianceCaveats = Number(alliance.partial_caveat_count || 0);
  const syncDirty = Number(cloudSync.dirty_count || 0);

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
      id: 'gemini',
      label: 'Gemini CLI',
      state: geminiReady ? 'Ready' : geminiInstalled ? 'Installed' : 'Missing',
      detail: gemini.version ? `v${gemini.version}; ${gemini.headless_mode || 'headless'}` : (gemini.last_blocker || 'preflight pending'),
      tone: geminiReady ? 'success' : geminiInstalled ? 'warn' : 'danger',
      progress: geminiReady ? 100 : geminiInstalled ? 65 : 0
    },
    {
      id: 'antigravity',
      label: 'Antigravity CLI',
      state: agyReady ? 'Ready' : agyInstalled ? 'Installed' : 'Missing',
      detail: antigravity.version ? `v${antigravity.version}; ${antigravity.model_count || 0} models` : (antigravity.last_blocker || 'preflight pending'),
      tone: agyReady ? 'success' : agyInstalled ? 'warn' : 'danger',
      progress: agyReady ? 100 : agyInstalled ? 70 : 0
    },
    {
      id: 'alliance',
      label: 'Alliance switchboard',
      state: alliance.ready_to_execute_alliance ? 'Ready' : alliance.status === 'missing' ? 'Missing' : 'Partial',
      detail: `${alliance.creator || 'jules'} -> ${alliance.implementer || 'unassigned'}; ${alliance.packet_count || 0} packets; live ${alliance.safe_to_launch_live_work ? 'open' : 'gated'}`,
      tone: allianceTone(alliance),
      progress: alliance.gate_total_count > 0 ? clampPercent((Number(alliance.gate_pass_count || 0) / Number(alliance.gate_total_count || 1)) * 100) : (allianceBlockers > 0 ? 0 : 55)
    },
    {
      id: 'cloud-sync',
      label: 'Cloud sync',
      state: cloudSyncLabel(cloudSync),
      detail: `${cloudSync.branch || 'branch'} -> ${cloudSync.upstream || 'no upstream'}; ${syncDirty} dirty; GitHub ${cloudSync.github_authenticated ? 'ready' : 'needs auth'}`,
      tone: cloudSyncTone(cloudSync),
      progress: cloudSync.publish_ready || cloudSync.synced ? 100 : cloudSync.status === 'blocked' ? 35 : 70
    },
    {
      id: 'context',
      label: 'Context gate',
      state: allianceCaveats > 0 ? `${allianceCaveats} caveats` : status.quantAllowed ? 'Quant allowed' : 'Quant locked',
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
    },
    {
      id: 'codebase',
      label: 'Codebase map',
      state: `${routeCount} routes`,
      detail: `${moduleCount} modules; ${testCount} tests; ${integrationReady} integrations`,
      tone: toneForStatus(status.codebase?.status),
      progress: routeCount > 0 ? 100 : 0
    }
  ];
};

export const buildTopology = status => {
  const fleet = status.fleet || DEFAULT_STATUS.fleet;
  const gemini = status.geminiCli || DEFAULT_STATUS.geminiCli;
  const antigravity = status.antigravityCli || DEFAULT_STATUS.antigravityCli;
  const alliance = status.alliance || EMPTY_ALLIANCE;
  const cloudSync = status.cloudSync || EMPTY_CLOUD_SYNC;
  const cloud = status.cloud || EMPTY_CLOUD;
  const repoSummary = status.repoContext?.summary || EMPTY_REPO_CONTEXT.summary;
  const codebaseSummary = status.codebase?.summary || EMPTY_CODEBASE_ANALYSIS.summary;
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
      id: 'runtime',
      label: 'Runtime Gate',
      detail: status.executionContext,
      tone: gateTone(status),
      metric: status.quantAllowed ? 'quant enabled' : 'quant locked'
    },
    {
      id: 'gemini',
      label: 'Gemini CLI',
      detail: gemini.ready ? 'ready' : gemini.installed ? 'installed' : 'missing',
      tone: gemini.ready ? 'success' : gemini.installed ? 'warn' : 'danger',
      metric: gemini.version || gemini.last_blocker || 'preflight'
    },
    {
      id: 'antigravity',
      label: 'Antigravity CLI',
      detail: antigravity.ready ? 'ready' : antigravity.installed ? 'installed' : 'missing',
      tone: antigravity.ready ? 'success' : antigravity.installed ? 'warn' : 'danger',
      metric: antigravity.version || antigravity.last_blocker || 'preflight'
    },
    {
      id: 'alliance',
      label: 'Alliance',
      detail: alliance.mode || 'unconfigured',
      tone: allianceTone(alliance),
      metric: `${alliance.creator || 'jules'} -> ${alliance.implementer || 'agent'}`
    },
    {
      id: 'sync',
      label: 'Cloud Sync',
      detail: cloudSyncLabel(cloudSync),
      tone: cloudSyncTone(cloudSync),
      metric: `${cloudSync.ahead || 0} ahead / ${cloudSync.dirty_count || 0} dirty`
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
      id: 'codebase',
      label: 'Codebase',
      detail: `${codebaseSummary.route_count || 0} routes`,
      tone: toneForStatus(status.codebase?.status),
      metric: `${codebaseSummary.module_count || 0} modules`
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
