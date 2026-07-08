export const EMPTY_REPO_CONTEXT = {
  status: 'unknown',
  generated_at_utc: '',
  summary: {
    repo_count: 0,
    collision_count: 0,
    collision_severity_counts: {},
    roots_scanned_count: 0,
    roots_missing_count: 0,
    scan_truncated: false
  },
  collisions: [],
  guardrails: [],
  cache_age_s: 0
};

export const normalizeRepoContext = context => {
  const source = context && typeof context === 'object' ? context : {};
  const summary = source.summary && typeof source.summary === 'object' ? source.summary : {};
  return {
    ...EMPTY_REPO_CONTEXT,
    ...source,
    summary: {
      ...EMPTY_REPO_CONTEXT.summary,
      ...summary,
      collision_severity_counts: {
        ...EMPTY_REPO_CONTEXT.summary.collision_severity_counts,
        ...(summary.collision_severity_counts || {})
      }
    },
    collisions: Array.isArray(source.collisions) ? source.collisions : [],
    guardrails: Array.isArray(source.guardrails) ? source.guardrails : []
  };
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

export const normalizeCodebaseAnalysis = analysis => {
  const source = analysis && typeof analysis === 'object' ? analysis : {};
  const summary = source.summary && typeof source.summary === 'object' ? source.summary : {};
  const frontend = source.frontend && typeof source.frontend === 'object' ? source.frontend : {};
  return {
    ...EMPTY_CODEBASE_ANALYSIS,
    ...source,
    root_name: source.root_name || source.root?.name || EMPTY_CODEBASE_ANALYSIS.root_name,
    summary: {
      ...EMPTY_CODEBASE_ANALYSIS.summary,
      ...summary
    },
    frontend: {
      ...EMPTY_CODEBASE_ANALYSIS.frontend,
      ...frontend
    },
    integrations: Array.isArray(source.integrations) ? source.integrations : [],
    findings: Array.isArray(source.findings) ? source.findings : []
  };
};

export const EMPTY_CLOUD = { total: 0, online: 0, vms: [] };

export const EMPTY_VM_RELAY_STATUS = {
  online: false,
  uptime_s: 0,
  tasks_completed: 0,
  tasks_running: 0,
  recent: [],
  browser_model_loop: false,
  sampled_at_utc: ''
};

export const normalizeVmRelayStatus = status => {
  const source = status && typeof status === 'object' ? status : {};
  return {
    ...EMPTY_VM_RELAY_STATUS,
    ...source,
    online: source.online === true,
    uptime_s: Math.max(0, Number(source.uptime_s || 0)),
    tasks_completed: Math.max(0, Number(source.tasks_completed || 0)),
    tasks_running: Math.max(0, Number(source.tasks_running || 0)),
    recent: Array.isArray(source.recent) ? source.recent : [],
    browser_model_loop: source.browser_model_loop === true,
    sampled_at_utc: source.sampled_at_utc || ''
  };
};

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

export const EMPTY_COLLABORATION_PROOF = {
  status: 'unknown',
  summary: '',
  generated_at_utc: '',
  gates: [],
  blockers: [],
  legacy_caveats: [],
  agents: {},
  proof_policy: {},
  completion_assessment: { safe_to_mark_goal_complete: false },
  evidence: {},
  pass_count: 0,
  gate_count: 0,
  required_pass_count: 0,
  required_gate_count: 0,
  blocker_count: 0,
  caveat_count: 0
};

export const normalizeCollaborationProof = proof => {
  const source = proof && typeof proof === 'object' ? proof : {};
  const gates = Array.isArray(source.gates) ? source.gates : [];
  const blockers = Array.isArray(source.blockers) ? source.blockers : [];
  const legacyCaveats = Array.isArray(source.legacy_caveats) ? source.legacy_caveats : [];
  const requiredGates = gates.filter(gate => gate?.required !== false);
  return {
    ...EMPTY_COLLABORATION_PROOF,
    ...source,
    gates,
    blockers,
    legacy_caveats: legacyCaveats,
    agents: source.agents && typeof source.agents === 'object' ? source.agents : {},
    proof_policy: source.proof_policy && typeof source.proof_policy === 'object' ? source.proof_policy : {},
    completion_assessment: source.completion_assessment && typeof source.completion_assessment === 'object'
      ? source.completion_assessment
      : EMPTY_COLLABORATION_PROOF.completion_assessment,
    evidence: source.evidence && typeof source.evidence === 'object' ? source.evidence : {},
    pass_count: gates.filter(gate => gate?.status === 'pass').length,
    gate_count: gates.length,
    required_pass_count: requiredGates.filter(gate => gate?.status === 'pass').length,
    required_gate_count: requiredGates.length,
    blocker_count: blockers.length,
    caveat_count: legacyCaveats.length
  };
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

export const offlineDashboardStatusSnapshot = (previousStatus = DEFAULT_STATUS) => ({
  ...(previousStatus || DEFAULT_STATUS),
  online: false,
  uptime: 'OFFLINE',
  bridgeStatus: 'offline',
  updateMode: 'offline'
});

export const clampPercent = value => Math.max(0, Math.min(100, Number(value) || 0));

export const toneForStatus = status => {
  const value = String(status || '').toLowerCase();
  if (['ready', 'ok', 'online', 'running', 'normal', 'pass', 'live', 'healthy'].includes(value)) return 'success';
  if (['partial', 'stale', 'warning', 'warn', 'provisioning', 'local_only', 'busy'].includes(value)) return 'warn';
  if (['error', 'offline', 'failed', 'fail', 'danger', 'critical'].includes(value)) return 'danger';
  return 'info';
};

export const summarizeControlAudit = audit => {
  if (!audit) {
    return {
      controlCoveragePercent: 0,
      controlRiskCount: 0,
      nonControlRiskCount: 0,
      headline: 'Run a local control audit',
      summary: 'Run a local control audit to separate button proof from runtime risks.'
    };
  }
  const riskRows = Array.isArray(audit.riskRows) ? audit.riskRows : [];
  const controlCount = Math.max(0, Number(audit.controlCount || audit.provableCount || 0));
  const provenCount = Math.max(0, Number(audit.provenCount || 0));
  const unprovenCount = Math.max(0, Number.isFinite(Number(audit.unprovenCount))
    ? Number(audit.unprovenCount)
    : controlCount - provenCount);
  const riskCount = Math.max(0, Number(audit.riskCount || riskRows.length || 0));
  const controlRiskCount = riskRows.filter(row => row?.controlId || row?.provable || String(row?.id || '').startsWith('control-')).length;
  const nonControlRiskCount = Math.max(0, riskCount - controlRiskCount);
  const controlCoveragePercent = controlCount > 0
    ? clampPercent(Math.round((provenCount / controlCount) * 100))
    : clampPercent(audit.score);
  const controlLabel = `${provenCount}/${controlCount} controls proven`;
  const systemLabel = nonControlRiskCount === 1 ? '1 system/runtime risk' : `${nonControlRiskCount} system/runtime risks`;
  const controlRiskLabel = controlRiskCount === 1 ? '1 control risk' : `${controlRiskCount} control risks`;

  if (unprovenCount > 0) {
    return {
      controlCoveragePercent,
      controlRiskCount,
      nonControlRiskCount,
      headline: `${unprovenCount} controls still need proof`,
      summary: `${controlLabel}; ${controlRiskLabel} remain; ${systemLabel} also remain.`
    };
  }
  if (nonControlRiskCount > 0) {
    return {
      controlCoveragePercent,
      controlRiskCount,
      nonControlRiskCount,
      headline: `Controls proven; ${systemLabel} remain`,
      summary: `${controlLabel}; button proof is clear, but ${systemLabel} still need review.`
    };
  }
  return {
    controlCoveragePercent,
    controlRiskCount,
    nonControlRiskCount,
    headline: 'Controls are proven for this snapshot',
    summary: `${controlLabel}; no control or system audit risks remain.`
  };
};

const uniqueItems = items => [...new Set(items.filter(Boolean))];

export const PROOF_JOURNAL_VERSION = 1;
export const PROOF_JOURNAL_MAX_AGE_MS = 12 * 60 * 60 * 1000;
export const PROOF_JOURNAL_MAX_COMMANDS = 160;
const PROOF_JOURNAL_FUTURE_SKEW_MS = 5 * 60 * 1000;

const proofJournalFingerprint = controlIds => uniqueItems(controlIds.map(item => String(item || '').trim()))
  .sort()
  .join('|');

const proofJournalTimeMs = value => {
  const ms = value instanceof Date ? value.getTime() : new Date(value).getTime();
  return Number.isFinite(ms) ? ms : NaN;
};

const proofJournalRowIsFresh = (row, nowMs, maxAgeMs) => {
  const rowMs = proofJournalTimeMs(row?.time);
  if (!Number.isFinite(rowMs)) return false;
  if (rowMs - nowMs > PROOF_JOURNAL_FUTURE_SKEW_MS) return false;
  return nowMs - rowMs <= maxAgeMs;
};

const compactEvidenceText = (value, maxLength = 180) => String(value || '')
  .replace(/\s+/g, ' ')
  .trim()
  .slice(0, maxLength);

const TUNNEL_LOG_RE = /\b(ngrok|tunnel)\b/i;
const TUNNEL_DANGER_RE = /\b(fatal|cannot self-heal|failed|failure|offline|error|closed|unavailable|timeout|timed out)\b/i;
const TUNNEL_WARN_RE = /\b(warn|warning|retry|stale|blocked|disconnected|missing|not configured)\b/i;

const eventRowText = row => `${row?.source || ''} ${row?.message || ''}`;

const buildTunnelHealthBlocker = eventRows => {
  const tunnelRows = (Array.isArray(eventRows) ? eventRows : [])
    .filter(row => TUNNEL_LOG_RE.test(eventRowText(row)));
  const newestRisk = [...tunnelRows].reverse().find(row => (
    row?.level === 'ERROR'
    || row?.level === 'WARN'
    || TUNNEL_DANGER_RE.test(eventRowText(row))
    || TUNNEL_WARN_RE.test(eventRowText(row))
  ));
  if (!newestRisk) return null;

  const isDanger = newestRisk.level === 'ERROR' || TUNNEL_DANGER_RE.test(eventRowText(newestRisk));
  const riskLabel = isDanger ? 'Bridge tunnel needs recovery' : 'Bridge tunnel needs review';
  return {
    id: 'tunnel-health',
    label: 'Tunnel Health',
    headline: riskLabel,
    detail: `${newestRisk.level || 'INFO'} from ${newestRisk.source || 'bridge'}: ${compactEvidenceText(newestRisk.message, 180)}`,
    tone: isDanger ? 'danger' : 'warn',
    focus: 'overview',
    controlId: 'bridge-probe',
    priority: 25,
    action: 'Run Live Bridge Probe and keep remote-Jules claims local-only until tunnel evidence is explained.',
    exitCriteria: 'Run Live Bridge Probe after tunnel recovery or explicitly record local-only mode; no tunnel/ngrok warning or fatal rows remain in the current evidence window.',
    evidence: tunnelRows.slice(-4).map(row => `${row.level || 'INFO'} / ${row.source || 'bridge'} / ${compactEvidenceText(row.message, 160)}`)
  };
};

const shortStableHash = value => {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
};

export const buildEvidenceReviewSignature = (rows, options = {}) => {
  const sourceRows = Array.isArray(rows) ? rows : [];
  const maxRows = Math.max(1, Number(options.maxRows || 12));
  const riskRows = sourceRows.filter(row => row?.level === 'ERROR' || row?.level === 'WARN');
  const windowRows = (riskRows.length ? riskRows : sourceRows).slice(-maxRows);
  const warningCount = sourceRows.filter(row => row?.level === 'WARN').length;
  const errorCount = sourceRows.filter(row => row?.level === 'ERROR').length;
  const stableRows = windowRows
    .map((row, index) => [
      index,
      compactEvidenceText(row?.timestamp, 80),
      compactEvidenceText(row?.level, 20),
      compactEvidenceText(row?.source, 80),
      compactEvidenceText(row?.message, 260)
    ].join('\u001f'))
    .join('\u001e');
  const fingerprint = shortStableHash([
    sourceRows.length,
    warningCount,
    errorCount,
    stableRows
  ].join('\u001f'));
  const signature = windowRows.length
    ? `evidence:v1:${sourceRows.length}:${warningCount}:${errorCount}:${fingerprint}`
    : '';
  return {
    signature,
    rowCount: sourceRows.length,
    windowSize: windowRows.length,
    warningCount,
    errorCount,
    riskCount: riskRows.length,
    label: `${windowRows.length} reviewed rows / ${errorCount} errors / ${warningCount} warnings`
  };
};

export const buildEvidenceIssueWindow = (rows, options = {}) => {
  const sourceRows = Array.isArray(rows) ? rows : [];
  const maxRows = Math.max(1, Number(options.maxRows || 12));
  const riskRows = sourceRows.filter(row => row?.level === 'ERROR' || row?.level === 'WARN');
  const windowRows = (riskRows.length ? riskRows : sourceRows).slice(-maxRows);
  const warningCount = sourceRows.filter(row => row?.level === 'WARN').length;
  const errorCount = sourceRows.filter(row => row?.level === 'ERROR').length;
  const newestIssue = riskRows[riskRows.length - 1] || null;
  const basis = riskRows.length ? 'risk' : 'recent';
  return {
    rows: windowRows,
    basis,
    rowCount: sourceRows.length,
    windowSize: windowRows.length,
    warningCount,
    errorCount,
    riskCount: riskRows.length,
    newestIssue,
    headline: riskRows.length
      ? `${riskRows.length} warning/error evidence rows`
      : sourceRows.length
        ? 'No warning/error rows in the current evidence tail'
        : 'No evidence rows available',
    label: `${windowRows.length} ${basis === 'risk' ? 'risk' : 'recent'} rows / ${errorCount} errors / ${warningCount} warnings`
  };
};

const sanitizeProofCommand = (row, controlSet) => {
  if (!row || typeof row !== 'object') return null;
  const controlIds = uniqueItems([
    row.controlId,
    ...(Array.isArray(row.controlIds) ? row.controlIds : [])
  ].map(item => String(item || '').trim())).filter(item => controlSet.has(item));
  if (controlIds.length === 0) return null;
  const evidenceSignature = compactEvidenceText(row.evidenceSignature, 220);
  const evidenceMeta = evidenceSignature
    ? {
      evidenceSignature,
      evidenceKind: compactEvidenceText(row.evidenceKind || 'window', 40),
      evidenceRiskCount: Number(row.evidenceRiskCount || 0)
    }
    : {};
  return {
    id: String(row.id || `${row.time || 'stored'}-${controlIds[0]}`),
    time: String(row.time || new Date(0).toISOString()),
    title: String(row.title || 'Stored control proof').slice(0, 120),
    detail: String(row.detail || '').slice(0, 260),
    tone: ['success', 'warn', 'danger', 'info'].includes(row.tone) ? row.tone : 'info',
    controlId: controlIds[0],
    controlIds,
    ...evidenceMeta
  };
};

export const serializePersistentCommandJournal = (commands, controlIds, options = {}) => {
  const contractIds = uniqueItems((Array.isArray(controlIds) ? controlIds : [])
    .map(item => String(item || '').trim()));
  const controlSet = new Set(contractIds);
  const savedAt = options.now instanceof Date
    ? options.now.toISOString()
    : options.now
      ? new Date(options.now).toISOString()
      : new Date().toISOString();
  const nowMs = proofJournalTimeMs(savedAt);
  const maxAgeMs = Number(options.maxAgeMs || PROOF_JOURNAL_MAX_AGE_MS);
  const storedCommands = (Array.isArray(commands) ? commands : [])
    .map(row => sanitizeProofCommand(row, controlSet))
    .filter(Boolean)
    .filter(row => proofJournalRowIsFresh(row, nowMs, maxAgeMs))
    .slice(0, PROOF_JOURNAL_MAX_COMMANDS);
  return {
    version: PROOF_JOURNAL_VERSION,
    savedAt,
    contractFingerprint: proofJournalFingerprint(contractIds),
    commands: storedCommands
  };
};

export const restorePersistentCommandJournal = (rawPayload, controlIds, options = {}) => {
  const payload = typeof rawPayload === 'string'
    ? (() => {
      try {
        return JSON.parse(rawPayload);
      } catch {
        return null;
      }
    })()
    : rawPayload;
  if (!payload || typeof payload !== 'object') return [];
  if (payload.version !== PROOF_JOURNAL_VERSION) return [];

  const contractIds = uniqueItems((Array.isArray(controlIds) ? controlIds : [])
    .map(item => String(item || '').trim()));
  if (payload.contractFingerprint !== proofJournalFingerprint(contractIds)) return [];

  const nowMs = proofJournalTimeMs(options.now || new Date());
  const savedMs = proofJournalTimeMs(payload.savedAt);
  const maxAgeMs = Number(options.maxAgeMs || PROOF_JOURNAL_MAX_AGE_MS);
  if (!Number.isFinite(nowMs) || !Number.isFinite(savedMs)) return [];
  if (savedMs - nowMs > PROOF_JOURNAL_FUTURE_SKEW_MS) return [];
  if (nowMs - savedMs > maxAgeMs) return [];

  const controlSet = new Set(contractIds);
  return (Array.isArray(payload.commands) ? payload.commands : [])
    .map(row => sanitizeProofCommand(row, controlSet))
    .filter(Boolean)
    .filter(row => proofJournalRowIsFresh(row, nowMs, maxAgeMs))
    .slice(0, PROOF_JOURNAL_MAX_COMMANDS);
};

export const isLocalPacketIntelligenceCommand = row => {
  const title = String(row?.title || '').trim().toLowerCase();
  if (!title) return false;
  return title === 'local packet intelligence'
    || title === 'packet intelligence prompt prepared'
    || title === 'local comms review staged'
    || title.includes('packet intelligence staged');
};

export const isSuccessfulControlProofCommand = row => {
  const controlIds = [
    row?.controlId,
    ...(Array.isArray(row?.controlIds) ? row.controlIds : [])
  ].filter(Boolean);
  if (controlIds.length === 0) return false;
  return String(row?.tone || '').toLowerCase() === 'success';
};

export const ensureUniqueCommandIds = rows => {
  const seen = new Set();
  return (Array.isArray(rows) ? rows : []).map((row, index) => {
    const source = row && typeof row === 'object' ? row : {};
    const baseId = String(
      source.id
      || `${source.time || 'command'}-${source.controlId || source.title || index}`
    ).slice(0, 180);
    let id = baseId || `command-${index}`;
    let suffix = 1;
    while (seen.has(id)) {
      id = `${baseId || 'command'}-${index}-${suffix}`;
      suffix += 1;
    }
    seen.add(id);
    return source.id === id ? source : { ...source, id };
  });
};

const commandJournalIdentity = row => [
  row?.id || '',
  row?.time || '',
  row?.title || '',
  row?.detail || '',
  row?.controlId || '',
  ...(Array.isArray(row?.controlIds) ? row.controlIds : [])
].map(item => String(item || '')).join('\u001f');

export const mergeCommandJournalRows = (...rowGroups) => {
  const seen = new Set();
  const merged = [];
  rowGroups.flatMap(group => (Array.isArray(group) ? group : []))
    .filter(row => row && typeof row === 'object')
    .forEach(row => {
      const key = commandJournalIdentity(row);
      if (seen.has(key)) return;
      seen.add(key);
      merged.push(row);
    });
  return ensureUniqueCommandIds(merged);
};

export const toneForActionStatus = (statusOrResult, resultDetails = {}) => {
  const result = (statusOrResult && typeof statusOrResult === 'object')
    ? statusOrResult
    : { ...resultDetails, status: statusOrResult };
  const status = String(result.status || '').toLowerCase();
  const state = String(result.plan_state || result.state || '').toLowerCase();
  const blockers = Array.isArray(result.blockers) ? result.blockers.filter(Boolean) : [];
  const warnings = Array.isArray(result.warnings) ? result.warnings.filter(Boolean) : [];
  if (status === 'error' || state === 'error' || status === 'failed' || state === 'failed') return 'danger';
  if (status === 'blocked' || state.includes('blocked') || blockers.length > 0) return 'warn';
  if (status === 'ready_with_warnings' || state === 'ready_with_warnings' || warnings.length > 0) return 'warn';
  if (!status && !state) return 'info';
  return toneForStatus(status || state);
};

export const evaluateCommsSendGate = ({
  draftText = '',
  hasImage = false,
  isThinking = false
} = {}) => {
  const hasDraft = String(draftText || '').trim().length > 0 || Boolean(hasImage);
  if (isThinking) {
    return {
      allowed: false,
      receiptTitle: 'Comms blocked',
      reason: 'Wait for the current Comms response before sending.',
      tone: 'warn',
      chatMessage: ''
    };
  }
  if (!hasDraft) {
    return {
      allowed: false,
      receiptTitle: 'Comms blocked',
      reason: 'Press Send blocked because there is no draft content to send.',
      tone: 'warn',
      chatMessage: 'COMM LINK WAIT: type a message or attach an image first.'
    };
  }
  return {
    allowed: true,
    receiptTitle: '',
    reason: '',
    tone: 'success',
    chatMessage: ''
  };
};

export const buildBlockedControlReceipt = ({
  reason = '',
  label = 'Control blocked'
} = {}) => ({
  title: label,
  detail: String(reason || 'This control cannot run right now.').trim(),
  tone: 'warn'
});

export const buildRouteNotImplementedReceipt = ({
  route = '',
  label = 'Route not implemented'
} = {}) => ({
  title: label,
  detail: route
    ? `${route} is not wired on the bridge yet.`
    : 'This control is not wired on the bridge yet.',
  tone: 'warn'
});

const PACKET_BLOCKER_FIELD_RE = /(?:^|\n)\s*(?:[-*]\s*)?(?:sync_)?blockers?\s*:\s*([^\n]+)/gi;
const PACKET_STATE_FIELD_RE = /(?:^|\n)\s*(?:[-*]\s*)?(?:status|state|plan_state)\s*:\s*([^\n]+)/gi;
const PACKET_BLOCKED_ROW_RE = /(?:^|\n)\s*(?:[-*]\s*)?BLOCKED\s*:\s*([^\n]+)/gi;
const PACKET_BLOCKER_TOKEN_RE = /\b(dirty_worktree|github_auth_required|no_upstream|no_remote|behind_remote|cloud_sync_blocked|sync_status_error|publish_packet_error|tiu_workbench_error|contract drift|publish_blocked|preview_blocked)\b/gi;
const PACKET_EMPTY_ISSUES = new Set(['', 'none', 'no', '0', 'false', 'n/a', 'na', 'not applicable', 'no blockers', 'not blocked']);

const cleanPacketIssueToken = value => String(value || '')
  .replace(/[`*[\](){}]/g, '')
  .replace(/\.$/, '')
  .trim()
  .toLowerCase();

const packetIssueIsEmpty = value => PACKET_EMPTY_ISSUES.has(cleanPacketIssueToken(value));

const packetIssueParts = value => String(value || '')
  .split(/[,;|]/)
  .map(cleanPacketIssueToken)
  .filter(item => !packetIssueIsEmpty(item));

const packetIssueBaseToken = value => cleanPacketIssueToken(value).split(':').pop();

const addPacketBlocker = (blockers, value) => {
  const clean = cleanPacketIssueToken(value);
  if (!clean || packetIssueIsEmpty(clean)) return;
  const baseToken = packetIssueBaseToken(clean);
  if (clean.includes(':')) {
    blockers.delete(baseToken);
  } else if ([...blockers].some(item => item === clean || item.endsWith(`:${clean}`))) {
    return;
  }
  blockers.add(clean);
};

export const extractPacketBlockers = text => {
  const packet = String(text || '');
  const blockers = new Set();

  const addParts = value => {
    const parts = packetIssueParts(value);
    parts.forEach(item => addPacketBlocker(blockers, item));
  };

  for (const match of packet.matchAll(PACKET_BLOCKER_FIELD_RE)) {
    addParts(match[1]);
  }
  for (const match of packet.matchAll(PACKET_BLOCKED_ROW_RE)) {
    addParts(match[1]);
  }
  for (const match of packet.matchAll(PACKET_STATE_FIELD_RE)) {
    const value = cleanPacketIssueToken(match[1]);
    if (blockers.size === 0 && value.includes('blocked') && !packetIssueIsEmpty(value)) {
      addPacketBlocker(blockers, value);
    }
  }
  for (const match of packet.matchAll(PACKET_BLOCKER_TOKEN_RE)) {
    addPacketBlocker(blockers, match[1]);
  }

  return [...blockers].slice(0, 8);
};

export const buildPacketIntelligence = (text, title = 'Staged packet') => {
  const packet = String(text || '').trim();
  const lower = packet.toLowerCase();
  const blockers = extractPacketBlockers(packet);
  const evidence = packet.match(/\b(evidence|verified|verification|screenshot|pytest|lint|build|console|overflow)\b/gi) || [];
  const protectedActions = packet.match(/\b(push|publish|launch|dispatch|worker|protected route|live worker|send)\b/gi) || [];
  const reviewSignals = packet.match(/\b(reviewed_risks|unreviewed_risks|audit_risks|risk triage|control audit)\b/gi) || [];
  const missingSignals = [
    evidence.length === 0 ? 'no_evidence_terms' : '',
    lower.includes('unreviewed_risks: none') ? '' : lower.includes('unreviewed_risks') ? 'unreviewed_risks_present' : '',
    lower.includes('protected route') && !lower.includes('token-backed') ? 'protected_route_context_missing' : '',
    lower.includes('publish') && blockers.length > 0 ? 'publish_blocked' : ''
  ].filter(Boolean);
  const focus = lower.includes('sync') || lower.includes('publish') || lower.includes('remote')
    ? 'sync'
    : lower.includes('worker') || lower.includes('fleet') || lower.includes('dispatch')
      ? 'workers'
      : lower.includes('codebase') || lower.includes('repo')
        ? 'codebase'
        : lower.includes('evidence') || lower.includes('contract')
          ? 'evidence'
          : 'comms';
  const score = clampPercent(100 - blockers.length * 9 - missingSignals.length * 12 - Math.max(0, protectedActions.length - evidence.length) * 4);
  const tone = blockers.length > 0 || missingSignals.length > 0
    ? 'warn'
    : protectedActions.length > evidence.length
      ? 'warn'
      : 'success';
  const verdict = blockers.length > 0
    ? 'Blocked until the named gates are resolved or explained.'
    : missingSignals.length > 0
      ? 'Needs more evidence before it can support a claim.'
      : protectedActions.length > evidence.length
        ? 'Action-heavy packet; verify evidence before sending.'
        : 'Packet has enough local review signal for a verify prompt.';
  const nextAction = focus === 'sync'
    ? 'Open Sync and compare blockers against the current cloud gate before any publish claim.'
    : focus === 'workers'
      ? 'Open Workers/Fleet and verify live-worker state before dispatch.'
      : focus === 'codebase'
        ? 'Open Codebase/Repo and inspect the linked finding before changing files.'
        : focus === 'evidence'
          ? 'Open Evidence and attach the newest relevant event/window.'
          : 'Keep this in Comms and ask for a scoped review.';
  const verdictPacket = [
    '# Local Packet Intelligence Verdict',
    '',
    `- packet: ${title}`,
    `- score: ${score}`,
    `- tone: ${tone}`,
    `- recommended_focus: ${focus}`,
    `- blockers_detected: ${blockers.length}`,
    `- evidence_terms: ${evidence.length}`,
    `- protected_action_terms: ${protectedActions.length}`,
    `- review_signals: ${reviewSignals.length}`,
    `- missing_signals: ${missingSignals.length ? missingSignals.join(', ') : 'none'}`,
    '',
    '## Verdict',
    verdict,
    '',
    '## Next Safe Action',
    nextAction
  ].join('\n');
  return {
    source: packet,
    title,
    score,
    tone,
    verdict,
    focus,
    nextAction,
    blockers,
    evidenceCount: evidence.length,
    protectedActionCount: protectedActions.length,
    reviewSignalCount: reviewSignals.length,
    missingSignals,
    verdictPacket
  };
};

export const buildLocalSyncGate = syncInput => {
  const sync = syncInput || EMPTY_CLOUD_SYNC;
  const dirty = Number(sync.dirty_count || 0);
  const ahead = Number(sync.ahead || 0);
  const behind = Number(sync.behind || 0);
  const remoteHost = String(sync.remote_host || '').toLowerCase();
  const explicitBlockers = Array.isArray(sync.blockers) ? sync.blockers : [];
  const blockers = uniqueItems([
    ...explicitBlockers,
    dirty > 0 ? 'dirty_worktree' : '',
    behind > 0 ? 'behind_remote' : '',
    !sync.upstream ? 'no_upstream' : '',
    !remoteHost ? 'no_remote' : '',
    remoteHost === 'github.com' && !sync.github_authenticated ? 'github_auth_required' : ''
  ]);
  if (blockers.length === 0 && (sync.status === 'blocked' || sync.state === 'blocked')) {
    blockers.push('cloud_sync_blocked');
  }
  const warnings = uniqueItems(Array.isArray(sync.warnings) ? sync.warnings : []);
  const hasWarnings = warnings.length > 0;
  const publishReady = blockers.length === 0 && !hasWarnings && !!sync.publish_ready;
  const synced = blockers.length === 0 && !hasWarnings && !!(sync.synced || sync.state === 'synced');
  return {
    dirty,
    ahead,
    behind,
    blockers,
    warnings,
    publishReady,
    synced,
    status: blockers.length > 0
      ? 'blocked'
      : hasWarnings
        ? 'ready_with_warnings'
        : publishReady || synced
          ? 'ready'
          : sync.status || 'unknown',
    state: blockers.length > 0
      ? 'preview_blocked'
      : hasWarnings
        ? 'preview_warning'
        : publishReady
          ? 'preview_ready'
          : synced
            ? 'preview_clean'
            : 'preview_waiting'
  };
};

const CLOUD_SYNC_ISSUE_DETAILS = {
  cloud_sync_blocked: 'The compact sync status reports a blocked cloud gate without a more specific blocker.',
  dirty_worktree: 'Review, stage, and commit intended changes before cloud publish.',
  behind_remote: 'Pull or reconcile the tracked remote before publishing local work.',
  no_upstream: 'Set an upstream tracking branch before claiming cloud sync ready.',
  no_remote: 'Set or repair the tracked remote before claiming cloud sync ready.',
  github_auth_required: 'Authenticate GitHub CLI before preparing cloud publish.',
  remote_tracking_not_sampled: 'Remote tracking freshness was not sampled in this snapshot.',
  remote_tracking_stale: 'Refresh remote tracking before relying on publish readiness.',
  generated_or_noisy_files_present: 'Generated evidence files need separate review before staging.'
};

export const cloudSyncIssueLabel = item => String(item || 'sync_gate').replaceAll('_', ' ');

export const cloudSyncIssueDetail = item => CLOUD_SYNC_ISSUE_DETAILS[item] || 'Resolve this sync gate before marking cloud sync complete.';

export const summarizeCloudSyncGate = syncInput => {
  const sync = syncInput || EMPTY_CLOUD_SYNC;
  const gate = buildLocalSyncGate(sync);
  const staged = Math.max(0, Number(sync.staged_count || 0));
  const unstaged = Math.max(0, Number(sync.unstaged_count || 0));
  const untracked = Math.max(0, Number(sync.untracked_count || 0));
  const dirty = Math.max(gate.dirty, staged + unstaged + untracked);
  const remoteHost = String(sync.remote_host || '').trim();
  const remoteLabel = String(sync.remote_label || remoteHost || 'no remote').trim();
  const branch = String(sync.branch || 'branch').trim();
  const upstream = String(sync.upstream || 'no upstream').trim();
  const dirtyBreakdown = dirty > 0
    ? `${dirty} dirty (${staged} staged / ${unstaged} unstaged / ${untracked} untracked)`
    : 'clean worktree';
  const remoteStatus = remoteHost === 'github.com'
    ? `GitHub ${sync.github_authenticated ? 'authenticated' : 'auth missing'}${sync.github_account ? ` as ${sync.github_account}` : ''}`
    : remoteHost
      ? `${remoteHost} remote configured`
      : 'no remote proven';
  const driftStatus = `${gate.ahead} ahead / ${gate.behind} behind`;
  const blockerText = gate.blockers.length
    ? gate.blockers.map(cloudSyncIssueLabel).join(', ')
    : 'none';
  const warningText = gate.warnings.length
    ? gate.warnings.map(cloudSyncIssueLabel).join(', ')
    : 'none';
  const packetLines = [
    `branch: ${branch}`,
    `upstream: ${upstream}`,
    `remote: ${remoteLabel}`,
    `worktree: ${dirtyBreakdown}`,
    `drift: ${driftStatus}`,
    `blockers: ${blockerText}`,
    `warnings: ${warningText}`
  ];

  if (gate.blockers.length > 0) {
    const headline = dirty > 0
      ? `${dirty} dirty files block publish`
      : `${gate.blockers.length} sync blocker${gate.blockers.length === 1 ? '' : 's'} block publish`;
    return {
      gate,
      headline,
      detail: `${dirtyBreakdown}; ${driftStatus}; ${branch} -> ${upstream}; ${remoteStatus}; blockers ${blockerText}.`,
      action: dirty > 0
        ? 'Build the publish review packet, inspect git status/diff, then stage and commit only reviewed files before push.'
        : 'Resolve the named sync blockers, then rerun Break Test before any push claim.',
      exitCriteria: 'Rerun Break Test after the publish packet is reviewed and the compact sync gate has no danger blockers.',
      packetLines,
      tone: 'danger'
    };
  }

  if (gate.warnings.length > 0) {
    return {
      gate,
      headline: `${gate.warnings.length} sync warning${gate.warnings.length === 1 ? '' : 's'} need review`,
      detail: `${dirtyBreakdown}; ${driftStatus}; ${branch} -> ${upstream}; ${remoteStatus}; warnings ${warningText}.`,
      action: 'Refresh or explain the sync warnings before using Sync as readiness evidence.',
      exitCriteria: 'Rerun Break Test after the warnings are refreshed or staged with evidence.',
      packetLines,
      tone: 'warn'
    };
  }

  return {
    gate,
    headline: gate.publishReady ? 'Cloud publish candidate is ready' : gate.synced ? 'Cloud sync is clean' : 'Cloud sync needs a fresh readiness sample',
    detail: `${dirtyBreakdown}; ${driftStatus}; ${branch} -> ${upstream}; ${remoteStatus}.`,
    action: gate.publishReady
      ? 'Review and push the ahead commits through the protected publish path.'
      : gate.synced
        ? 'Use Sync as supporting readiness evidence.'
        : 'Refresh Sync or build a local preview before making a publish claim.',
    exitCriteria: 'Sync remains warning-free and blocker-free on the next Break Test run.',
    packetLines,
    tone: gate.publishReady || gate.synced ? 'success' : 'info'
  };
};

export const buildBridgeProbeCommsReceipt = row => {
  if (!row || row.id !== 'chat-test') return null;
  const detail = [
    'Live Bridge Probe model loop',
    row.path || '/chat/test',
    compactEvidenceText(row.detail || 'no detail recorded', 220),
    row.latencyMs ? `${row.latencyMs}ms` : ''
  ].filter(Boolean).join(' / ');
  const base = {
    detail,
    controlId: 'comms-actions',
    controlIds: ['bridge-probe', 'comms-actions']
  };
  if (row.tone === 'success' && row.state === 'pass') {
    return {
      ...base,
      title: 'Comms response received',
      tone: 'success'
    };
  }
  if (row.tone === 'danger') {
    return {
      ...base,
      title: 'Comms failed',
      tone: 'danger'
    };
  }
  return {
    ...base,
    title: 'Comms degraded',
    tone: 'warn'
  };
};

export const buildLiveBlockerQueue = ({
  sync,
  eventRows,
  commandJournal
} = {}) => {
  const rows = [];
  const syncGate = buildLocalSyncGate(sync || EMPTY_CLOUD_SYNC);
  const syncDiagnosis = summarizeCloudSyncGate(sync || EMPTY_CLOUD_SYNC);
  const syncNeedsAction = syncGate.blockers.length > 0
    || syncGate.warnings.length > 0
    || (!syncGate.publishReady && !syncGate.synced);
  if (syncNeedsAction) {
    rows.push({
      id: 'sync-gate',
      label: 'Cloud Sync',
      headline: syncDiagnosis.headline,
      detail: syncDiagnosis.detail,
      tone: syncDiagnosis.tone === 'success' ? 'info' : syncDiagnosis.tone,
      focus: 'sync',
      controlId: 'sync-packet',
      priority: 10,
      action: syncGate.blockers.length > 0
        ? 'Open Sync and build or stage the publish review packet.'
        : syncGate.warnings.length > 0
          ? 'Open Sync and explain the warnings before readiness claims.'
          : 'Open Sync and refresh or preview readiness.',
      exitCriteria: syncDiagnosis.exitCriteria,
      evidence: syncDiagnosis.packetLines
    });
  }

  const issueWindow = buildEvidenceIssueWindow(eventRows);
  if (issueWindow.riskCount > 0 || issueWindow.rowCount === 0) {
    const newestIssue = issueWindow.newestIssue;
    rows.push({
      id: 'evidence-health',
      label: 'Evidence Stream',
      headline: issueWindow.headline,
      detail: newestIssue
        ? `${issueWindow.label}; newest ${newestIssue.level} from ${newestIssue.source}: ${compactEvidenceText(newestIssue.message, 160)}`
        : issueWindow.rowCount === 0
          ? 'No evidence rows are available, so health claims need a fresh stream sample.'
          : issueWindow.label,
      tone: issueWindow.errorCount > 0 ? 'danger' : 'warn',
      focus: 'evidence',
      controlId: 'evidence-actions',
      priority: 20,
      action: issueWindow.riskCount > 0
        ? 'Open Evidence and stage the current issue window.'
        : 'Open Evidence and wait for or stage a fresh evidence tail.',
      exitCriteria: issueWindow.riskCount > 0
        ? 'Stage the current issue window, inspect the related lane, then rerun Break Test with the issue explained or resolved.'
        : 'Collect a fresh evidence tail, stage it for review, then rerun Break Test with evidence rows present.',
      evidence: issueWindow.rows.slice(-4).map(row => `${row.level || 'INFO'} / ${row.source || 'bridge'} / ${compactEvidenceText(row.message, 160)}`)
    });
  }

  const tunnelBlocker = buildTunnelHealthBlocker(eventRows);
  if (tunnelBlocker) rows.push(tunnelBlocker);

  const journal = Array.isArray(commandJournal) ? commandJournal : [];
  const latestCommsRow = journal.find(row => (
    row?.title === 'Comms failed'
    || row?.title === 'Comms degraded'
    || row?.title === 'Comms response received'
  ));
  const latestLocalPacketIntelligenceRow = journal.find(isLocalPacketIntelligenceCommand);
  if (!latestLocalPacketIntelligenceRow) {
    rows.push({
      id: 'local-packet-intelligence',
      label: 'Local Packet Intelligence',
      headline: 'No local packet-intelligence proof recorded',
      detail: 'No Local Review or packet-intelligence verdict has been recorded for the current dashboard proof window.',
      tone: 'warn',
      focus: 'comms',
      controlId: 'comms-actions',
      safeActionId: 'comms-local-review',
      priority: 40,
      action: 'Open Comms and run Local Review on a staged packet before claiming local reasoning support.',
      exitCriteria: 'Run Local Review, build a packet-intelligence verdict, or run the Comms local safe check so the journal records local packet intelligence proof.',
      evidence: []
    });
  }
  if (!latestCommsRow || latestCommsRow.title !== 'Comms response received') {
    rows.push({
      id: 'comms-loop',
      label: 'Comms Model Loop',
      headline: latestCommsRow ? 'Model loop is not clean' : 'No model-loop proof recorded',
      detail: latestCommsRow
        ? `${latestCommsRow.title}: ${latestCommsRow.detail || 'no detail recorded'}`
        : 'Probe Model has not produced a successful response receipt in this session.',
      tone: latestCommsRow?.title === 'Comms failed' ? 'danger' : 'warn',
      focus: 'comms',
      controlId: 'comms-actions',
      safeActionId: 'comms-model-probe',
      priority: 30,
      action: 'Open Comms and press Probe Model; keep degraded or offline state visibly marked.',
      exitCriteria: 'Run Probe Model until the latest Comms journal row is a successful response, or keep the degraded/offline reason visible.',
      evidence: latestCommsRow ? [`${latestCommsRow.title}: ${latestCommsRow.detail || ''}`] : []
    });
  }

  const toneRank = { danger: 0, warn: 1, info: 2, success: 3 };
  return rows.sort((left, right) => (
    (toneRank[left.tone] ?? 4) - (toneRank[right.tone] ?? 4)
    || (left.priority ?? 100) - (right.priority ?? 100)
    || left.label.localeCompare(right.label)
  ));
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
  const repoContext = normalizeRepoContext(safePayload.repo_context);
  const codebase = normalizeCodebaseAnalysis(safePayload.codebase_analysis);
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
  if (/(ERROR|FAIL|FATAL|CRITICAL|TRACEBACK|EXCEPTION)/.test(upper)) level = 'ERROR';
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

export const buildCommandIntelligence = ({
  status,
  activeFocus,
  worker,
  collision,
  rows,
  journal
}) => {
  const safeStatus = status || DEFAULT_STATUS;
  const sync = safeStatus.cloudSync || EMPTY_CLOUD_SYNC;
  const syncGate = buildLocalSyncGate(sync);
  const syncBlocked = syncGate.blockers.length > 0;
  const syncTone = cloudSyncTone(sync);
  const syncLabel = syncBlocked
    ? `${syncGate.blockers.length} sync blocker${syncGate.blockers.length === 1 ? '' : 's'}`
    : cloudSyncLabel(sync);
  const syncBlockerText = syncBlocked ? syncGate.blockers.join(', ') : 'none';
  const alliance = safeStatus.alliance || EMPTY_ALLIANCE;
  const codebase = safeStatus.codebase || EMPTY_CODEBASE_ANALYSIS;
  const fleet = safeStatus.fleet || DEFAULT_STATUS.fleet;
  const gemini = safeStatus.geminiCli || DEFAULT_STATUS.geminiCli;
  const antigravity = safeStatus.antigravityCli || DEFAULT_STATUS.antigravityCli;
  const repoSummary = safeStatus.repoContext?.summary || EMPTY_REPO_CONTEXT.summary;
  const eventRows = Array.isArray(rows) ? rows : [];
  const history = Array.isArray(journal) ? journal : [];
  const errors = eventRows.filter(row => row.level === 'ERROR').length;
  const warnings = eventRows.filter(row => row.level === 'WARN').length;
  const dirty = Number(sync.dirty_count || 0);
  const pending = Number(fleet.pending || 0);
  const activeFleet = pending + Number(fleet.in_progress || 0);
  const modelLaneReady = !!(antigravity.ready || gemini.ready);
  const streamHealthy = !!(safeStatus.contractOk && safeStatus.updateMode === 'sse');
  const collisionCount = Number(repoSummary.collision_count || 0);
  const priority = errors > 0 || syncBlocked
    ? 'intervention'
    : warnings > 0 || pending > 0 || !alliance.safe_to_launch_live_work
      ? 'watch'
      : 'clear';
  const priorityTone = priority === 'intervention' ? 'danger' : priority === 'watch' ? 'warn' : 'success';
  const rawHealthScore = clampPercent(
    (streamHealthy ? 20 : 4)
    + (syncGate.publishReady || syncGate.synced ? 18 : syncBlocked ? 5 : 12)
    + (alliance.ready_to_execute_alliance ? 18 : alliance.status === 'missing' ? 3 : 10)
    + (modelLaneReady ? 16 : antigravity.installed || gemini.installed ? 9 : 2)
    + (errors === 0 ? 14 : Math.max(0, 8 - errors * 2))
    + (collisionCount === 0 ? 14 : Math.max(2, 10 - collisionCount))
  );
  const healthScore = priority === 'intervention'
    ? Math.min(rawHealthScore, 64)
    : priority === 'watch'
      ? Math.min(rawHealthScore, 82)
      : rawHealthScore;
  const activeSubject = collision
    ? `Repo collision: ${collision.type || 'unknown'}`
    : worker
      ? `Worker: ${worker.name || worker.provider || 'selected'}`
      : `${activeFocus || 'overview'} lane`;
  const headline = priority === 'clear'
    ? 'Bridge sync gates are clear for reviewed work.'
    : priority === 'intervention'
      ? 'Bridge needs operator review before publish or launch.'
      : 'Bridge is live, with gated work queued for review.';
  const summary = [
    `${codebase.summary?.route_count || 0} routes`,
    `${codebase.summary?.module_count || 0} modules`,
    `${codebase.summary?.test_count || 0} tests`,
    `${syncGate.state || sync.state || 'sync unknown'} sync`,
    `${pending} fleet pending`
  ].join(' / ');
  const signals = [
    {
      label: 'Contract',
      value: safeStatus.contractOk ? `v${safeStatus.contract?.version || 0}` : 'drift',
      tone: safeStatus.contractOk ? 'success' : 'danger'
    },
    {
      label: 'Stream',
      value: safeStatus.updateMode === 'sse' ? `SSE ${safeStatus.streamSequence || 0}` : safeStatus.updateMode || 'poll',
      tone: safeStatus.updateMode === 'sse' ? 'success' : safeStatus.updateMode === 'offline' ? 'danger' : 'warn'
    },
    {
      label: 'Alliance',
      value: alliance.ready_to_execute_alliance ? 'ready' : alliance.status || 'unknown',
      tone: allianceTone(alliance)
    },
    {
      label: 'Sync',
      value: syncBlocked ? syncLabel : dirty > 0 ? `${dirty} dirty` : cloudSyncLabel(sync),
      tone: syncTone
    },
    {
      label: 'Events',
      value: `${warnings} warn / ${errors} err`,
      tone: errors > 0 ? 'danger' : warnings > 0 ? 'warn' : 'success'
    },
    {
      label: 'Subject',
      value: activeSubject,
      tone: collision ? collision.severity === 'critical' ? 'danger' : 'warn' : worker ? 'success' : 'info'
    }
  ];
  const scenarios = [
    {
      id: 'publish',
      label: syncBlocked ? 'Publish blocked' : syncGate.publishReady ? 'Push candidate' : 'Publish clean',
      metric: `${syncGate.dirty} dirty / ${syncGate.ahead} ahead`,
      detail: syncBlocked
        ? `Resolve sync blockers first: ${syncBlockerText}.`
        : syncGate.publishReady
          ? 'Local commits are ahead and ready for an operator-reviewed packet.'
          : 'Local and upstream state are not asking for a publish.',
      tone: syncTone,
      focus: 'sync'
    },
    {
      id: 'worker',
      label: alliance.ready_to_execute_alliance ? 'Alliance ready' : 'Alliance gated',
      metric: `${alliance.gate_pass_count || 0}/${alliance.gate_total_count || 0} gates`,
      detail: alliance.safe_to_launch_live_work
        ? 'Live work gates are open for the selected alliance lane.'
        : 'Use packets and review gates before live worker activity.',
      tone: allianceTone(alliance),
      focus: 'alliance'
    },
    {
      id: 'model',
      label: modelLaneReady ? 'Model lane ready' : 'Model lane waiting',
      metric: antigravity.ready ? `agy ${antigravity.model_count || 0} models` : gemini.installed ? 'legacy installed' : 'not ready',
      detail: antigravity.ready
        ? 'Supported Google terminal-agent lane is available.'
        : gemini.installed
          ? 'Legacy Gemini CLI is installed but not the preferred execution gate.'
          : 'No local Google terminal model lane is proven ready.',
      tone: modelLaneReady ? 'success' : antigravity.installed || gemini.installed ? 'warn' : 'danger',
      focus: 'alliance'
    },
    {
      id: 'evidence',
      label: errors > 0 ? 'Evidence blocked' : streamHealthy ? 'Evidence live' : 'Evidence degraded',
      metric: streamHealthy ? `SSE ${safeStatus.streamSequence || 0}` : safeStatus.updateMode || 'poll',
      detail: errors > 0
        ? 'Error events require attention before claiming the bridge is healthy.'
        : warnings > 0
          ? 'Warnings are present but the stream is still usable.'
          : 'Contract stream and event tail support current diagnosis.',
      tone: errors > 0 ? 'danger' : warnings > 0 || !streamHealthy ? 'warn' : 'success',
      focus: 'evidence'
    }
  ];
  const decisionTrace = [
    {
      id: 'contract',
      label: 'Contract gate',
      detail: safeStatus.contractOk ? `v${safeStatus.contract?.version || 0} on ${safeStatus.updateMode || 'poll'}` : 'waiting for v2 contract',
      tone: safeStatus.contractOk ? 'success' : 'danger'
    },
    {
      id: 'sync',
      label: 'Sync gate',
      detail: `${syncGate.state || sync.state || 'unknown'} with ${syncGate.dirty} dirty, ${syncGate.ahead} ahead, ${syncGate.behind} behind; blockers ${syncBlockerText}`,
      tone: syncTone
    },
    {
      id: 'alliance',
      label: 'Agent gate',
      detail: `${alliance.creator || 'jules'} -> ${alliance.implementer || 'agent'}; live ${alliance.safe_to_launch_live_work ? 'open' : 'gated'}`,
      tone: allianceTone(alliance)
    },
    {
      id: 'fleet',
      label: 'Fleet gate',
      detail: `${activeFleet} active/pending, ${fleet.completed || 0} complete, ${fleet.failed || 0} failed`,
      tone: Number(fleet.failed || 0) > 0 ? 'danger' : activeFleet > 0 ? 'warn' : 'success'
    }
  ];
  const recommendedActions = [
    {
      id: 'focus-sync',
      label: syncBlocked ? 'Review sync gate' : 'Confirm sync packet',
      detail: syncBlocked ? `Resolve or stage blockers: ${syncBlockerText}.` : 'Generate a clean publish packet for the current state.',
      focus: 'sync',
      tone: syncTone
    },
    {
      id: 'focus-tiu',
      label: 'Draft next worker packet',
      detail: `${alliance.creator || 'jules'} -> ${alliance.implementer || 'agent'} with ${alliance.gate_pass_count || 0}/${alliance.gate_total_count || 0} gates.`,
      focus: 'tiu',
      tone: allianceTone(alliance)
    },
    {
      id: 'focus-evidence',
      label: errors > 0 || warnings > 0 ? 'Inspect evidence tail' : 'Audit live stream',
      detail: `${warnings} warnings, ${errors} errors, stream ${safeStatus.updateMode || 'poll'}.`,
      focus: 'evidence',
      tone: errors > 0 ? 'danger' : warnings > 0 ? 'warn' : 'success'
    },
    {
      id: 'stage-brief',
      label: 'Stage intelligence brief',
      detail: 'Send the current diagnosis to Comms for Jules or the model loop.',
      focus: 'comms',
      tone: priorityTone,
      packet: [
        '# Dashboard Intelligence Brief',
        '',
        `- priority: ${priority}`,
        `- focus: ${activeFocus || 'overview'}`,
        `- subject: ${activeSubject}`,
        `- summary: ${summary}`,
        `- sync: ${syncGate.state || sync.state || 'unknown'} (${syncGate.dirty} dirty, ${syncGate.ahead} ahead, ${syncGate.behind} behind)`,
        `- sync_blockers: ${syncBlockerText}`,
        `- alliance: ${alliance.mode || 'unknown'} (${alliance.gate_pass_count || 0}/${alliance.gate_total_count || 0} gates)`,
        `- evidence: ${warnings} warning events, ${errors} error events`,
        `- health_score: ${healthScore}`,
        '',
        '## Recommended Next Move',
        syncBlocked
          ? 'Open Cloud Sync and resolve blockers before claiming publish readiness.'
          : 'Use the TIU workbench to prepare the next safe worker packet.'
      ].join('\n')
    }
  ];
  return {
    priority,
    priorityTone,
    headline,
    summary,
    healthScore,
    signals,
    scenarios,
    decisionTrace,
    recommendedActions,
    recentActions: history.slice(0, 6)
  };
};

export const allianceTone = alliance => {
  if (!alliance || alliance.status === 'missing') return 'danger';
  if (Number(alliance.required_blocker_count || 0) > 0) return 'danger';
  if (Number(alliance.partial_caveat_count || 0) > 0 || !alliance.simultaneous_two_agent_mode) return 'warn';
  if (alliance.ready_to_execute_alliance) return 'success';
  return toneForStatus(alliance.status);
};

export const cloudSyncTone = cloudSync => {
  const sync = cloudSync || EMPTY_CLOUD_SYNC;
  const syncGate = buildLocalSyncGate(sync);
  if (syncGate.blockers.length > 0) return 'danger';
  if (syncGate.warnings.length > 0) return 'warn';
  if (syncGate.publishReady || syncGate.synced) return 'success';
  return toneForStatus(sync.status);
};

export const cloudSyncLabel = cloudSync => {
  const sync = cloudSync || EMPTY_CLOUD_SYNC;
  const syncGate = buildLocalSyncGate(sync);
  if (syncGate.blockers.length > 0) return 'Blocked';
  if (syncGate.warnings.length > 0) return 'Needs review';
  if (syncGate.publishReady) return 'Push ready';
  if (syncGate.synced) return 'Synced';
  return sync.state || 'Unknown';
};

export const buildAllianceLanes = status => {
  const alliance = status.alliance || EMPTY_ALLIANCE;
  const laneRows = Array.isArray(alliance.lanes) ? alliance.lanes : [];
  const byId = new Map(laneRows.map(row => [row.id, row]));
  const cloud = status.cloud || EMPTY_CLOUD;
  const cloudSync = status.cloudSync || EMPTY_CLOUD_SYNC;
  const syncGate = buildLocalSyncGate(cloudSync);
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
      ready: status.online && cloudOnline > 0 && syncGate.blockers.length === 0,
      state: cloudSyncLabel(cloudSync),
      detail: `${cloudOnline}/${cloudTotal} workers; git ${syncGate.dirty} dirty; ${syncGate.ahead} ahead; blockers ${syncGate.blockers.length}.`,
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
  const syncGate = buildLocalSyncGate(cloudSync);
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
  const syncDirty = syncGate.dirty;

  return [
    {
      id: 'bridge',
      label: 'Bridge route',
      state: status.online ? (status.tunnel ? 'Tunnel live' : 'Local relay') : 'Offline',
      detail: status.online ? `${status.bridgeStatus}; cache ${status.cacheAge}s` : 'status poll failed',
      tone: status.online ? (status.tunnel ? 'success' : 'warn') : 'danger',
      progress: status.online ? 100 : 0,
      focus: 'overview'
    },
    {
      id: 'gemini',
      label: 'Gemini CLI',
      state: geminiReady ? 'Ready' : geminiInstalled ? 'Installed' : 'Missing',
      detail: gemini.version ? `v${gemini.version}; ${gemini.headless_mode || 'headless'}` : (gemini.last_blocker || 'preflight pending'),
      tone: geminiReady ? 'success' : geminiInstalled ? 'warn' : 'danger',
      progress: geminiReady ? 100 : geminiInstalled ? 65 : 0,
      focus: 'alliance'
    },
    {
      id: 'antigravity',
      label: 'Antigravity CLI',
      state: agyReady ? 'Ready' : agyInstalled ? 'Installed' : 'Missing',
      detail: antigravity.version ? `v${antigravity.version}; ${antigravity.model_count || 0} models` : (antigravity.last_blocker || 'preflight pending'),
      tone: agyReady ? 'success' : agyInstalled ? 'warn' : 'danger',
      progress: agyReady ? 100 : agyInstalled ? 70 : 0,
      focus: 'alliance'
    },
    {
      id: 'alliance',
      label: 'Alliance switchboard',
      state: alliance.ready_to_execute_alliance ? 'Ready' : alliance.status === 'missing' ? 'Missing' : 'Partial',
      detail: `${alliance.creator || 'jules'} -> ${alliance.implementer || 'unassigned'}; ${alliance.packet_count || 0} packets; live ${alliance.safe_to_launch_live_work ? 'open' : 'gated'}`,
      tone: allianceTone(alliance),
      progress: alliance.gate_total_count > 0 ? clampPercent((Number(alliance.gate_pass_count || 0) / Number(alliance.gate_total_count || 1)) * 100) : (allianceBlockers > 0 ? 0 : 55),
      focus: 'alliance'
    },
    {
      id: 'cloud-sync',
      label: 'Cloud sync',
      state: cloudSyncLabel(cloudSync),
      detail: `${cloudSync.branch || 'branch'} -> ${cloudSync.upstream || 'no upstream'}; ${syncDirty} dirty; GitHub ${cloudSync.github_authenticated ? 'ready' : 'needs auth'}; blockers ${syncGate.blockers.length}`,
      tone: cloudSyncTone(cloudSync),
      progress: syncGate.publishReady || syncGate.synced ? 100 : syncGate.blockers.length > 0 ? 35 : 70,
      focus: 'sync'
    },
    {
      id: 'context',
      label: 'Context gate',
      state: allianceCaveats > 0 ? `${allianceCaveats} caveats` : status.quantAllowed ? 'Quant allowed' : 'Quant locked',
      detail: `${status.executionContext} on ${status.hostname}`,
      tone: gateTone(status),
      progress: 100,
      focus: 'overview'
    },
    {
      id: 'fleet',
      label: 'Fleet queue',
      state: failures > 0 ? `${failures} failed` : `${pending} pending`,
      detail: `${fleet.completed || 0}/${fleet.launched || 0} complete; ${inProgress} active`,
      tone: failures > 0 ? 'danger' : pending > 0 || inProgress > 0 ? 'warn' : 'success',
      progress: Number(fleet.launched || 0) > 0 ? clampPercent((Number(fleet.completed || 0) / Number(fleet.launched || 1)) * 100) : 0,
      focus: 'fleet'
    },
    {
      id: 'workers',
      label: 'Worker lane',
      state: `${workerOnline}/${workerTotal} online`,
      detail: workerTotal > 0 ? 'remote compute inventory masked' : 'no workers configured',
      tone: workerTotal === 0 ? 'warn' : workerOnline > 0 ? 'success' : 'danger',
      progress: workerTotal > 0 ? clampPercent((workerOnline / workerTotal) * 100) : 0,
      focus: 'workers'
    },
    {
      id: 'repo',
      label: 'Repo guard',
      state: `${collisions} collisions`,
      detail: `${repoSummary.repo_count || 0} repos scanned; names hidden`,
      tone: collisions > 0 ? 'warn' : toneForStatus(status.repoContext?.status),
      progress: collisions > 0 ? 55 : 100,
      focus: 'repo'
    },
    {
      id: 'codebase',
      label: 'Codebase map',
      state: `${routeCount} routes`,
      detail: `${moduleCount} modules; ${testCount} tests; ${integrationReady} integrations`,
      tone: toneForStatus(status.codebase?.status),
      progress: routeCount > 0 ? 100 : 0,
      focus: 'codebase'
    }
  ];
};

export const buildTopology = status => {
  const fleet = status.fleet || DEFAULT_STATUS.fleet;
  const gemini = status.geminiCli || DEFAULT_STATUS.geminiCli;
  const antigravity = status.antigravityCli || DEFAULT_STATUS.antigravityCli;
  const alliance = status.alliance || EMPTY_ALLIANCE;
  const cloudSync = status.cloudSync || EMPTY_CLOUD_SYNC;
  const syncGate = buildLocalSyncGate(cloudSync);
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
      metric: status.tunnel ? 'public tunnel' : 'local relay',
      focus: 'overview'
    },
    {
      id: 'runtime',
      label: 'Runtime Gate',
      detail: status.executionContext,
      tone: gateTone(status),
      metric: status.quantAllowed ? 'quant enabled' : 'quant locked',
      focus: 'overview'
    },
    {
      id: 'gemini',
      label: 'Gemini CLI',
      detail: gemini.ready ? 'ready' : gemini.installed ? 'installed' : 'missing',
      tone: gemini.ready ? 'success' : gemini.installed ? 'warn' : 'danger',
      metric: gemini.version || gemini.last_blocker || 'preflight',
      focus: 'alliance'
    },
    {
      id: 'antigravity',
      label: 'Antigravity CLI',
      detail: antigravity.ready ? 'ready' : antigravity.installed ? 'installed' : 'missing',
      tone: antigravity.ready ? 'success' : antigravity.installed ? 'warn' : 'danger',
      metric: antigravity.version || antigravity.last_blocker || 'preflight',
      focus: 'alliance'
    },
    {
      id: 'alliance',
      label: 'Alliance',
      detail: alliance.mode || 'unconfigured',
      tone: allianceTone(alliance),
      metric: `${alliance.creator || 'jules'} -> ${alliance.implementer || 'agent'}`,
      focus: 'alliance'
    },
    {
      id: 'sync',
      label: 'Cloud Sync',
      detail: cloudSyncLabel(cloudSync),
      tone: cloudSyncTone(cloudSync),
      metric: syncGate.blockers.length > 0
        ? `${syncGate.blockers.length} blockers`
        : `${syncGate.ahead} ahead / ${syncGate.dirty} dirty`,
      focus: 'sync'
    },
    {
      id: 'fleet',
      label: 'Jules Fleet',
      detail: `${fleet.completed || 0}/${fleet.launched || 0}`,
      tone: failures > 0 ? 'danger' : Number(fleet.pending || 0) > 0 ? 'warn' : 'success',
      metric: `${fleet.pending || 0} pending`,
      focus: 'fleet'
    },
    {
      id: 'workers',
      label: 'Cloud Workers',
      detail: `${cloud.online || 0}/${cloud.total || 0}`,
      tone: Number(cloud.total || 0) === 0 ? 'warn' : Number(cloud.online || 0) > 0 ? 'success' : 'danger',
      metric: 'endpoints masked',
      focus: 'workers'
    },
    {
      id: 'repo',
      label: 'Repo Guard',
      detail: `${collisions}`,
      tone: collisions > 0 ? 'warn' : toneForStatus(status.repoContext?.status),
      metric: 'collision watch',
      focus: 'repo'
    },
    {
      id: 'codebase',
      label: 'Codebase',
      detail: `${codebaseSummary.route_count || 0} routes`,
      tone: toneForStatus(status.codebase?.status),
      metric: `${codebaseSummary.module_count || 0} modules`,
      focus: 'codebase'
    },
    {
      id: 'comms',
      label: 'Comms',
      detail: `${status.secretCount} refs`,
      tone: status.secretCount > 0 ? 'success' : 'warn',
      metric: 'secrets hidden',
      focus: 'comms'
    }
  ];
};

export const EMPTY_DASHBOARD_COMMAND = {
  commandId: '',
  workflowId: '',
  traceId: '',
  type: 'route_probe',
  status: 'admitted',
  createdAt: '',
  updatedAt: '',
  requestedBy: 'dashboard',
  route: '',
  summary: '',
  blockReason: null,
  result: {},
  evidenceRefs: []
};

export const EMPTY_DASHBOARD_LAST_REPLAY = {
  status: '',
  checkedAt: '',
  summary: '',
  blockReason: null,
  evidenceRefs: []
};

export const EMPTY_DASHBOARD_REPLAY_STATUS = {
  verified: 0,
  missing_evidence: 0,
  evidence_mismatch: 0,
  never_replayed: 0
};

export const EMPTY_DASHBOARD_WORKFLOW = {
  workflowId: '',
  title: '',
  status: 'ready',
  commandIds: [],
  latestCommandId: '',
  traceIds: [],
  summary: '',
  nextSafeAction: '',
  requiredOperatorAction: null
};

export const EMPTY_DASHBOARD_PROJECTION = {
  ok: false,
  contract: { name: 'jules_dashboard_projection', version: 1, generated_at_utc: '' },
  bridgeHealth: { ok: false, online: false },
  commands: [],
  workflows: [],
  dashboardCache: { cache_age_s: 0, transport: 'poll' },
  cloudSyncPreview: {},
  collaborationProof: {},
  blockers: [],
  nextSafeAction: '',
  currentWorkflowId: '',
  commandWorker: {
    ok: false,
    workerId: '',
    enabled: false,
    mode: 'manual_tick',
    pendingCount: 0,
    runningCount: 0,
    terminalCount: 0,
    lastTickAt: null,
    lastCommandId: null,
    running: false,
    poll_interval_s: 1
  },
  latestEvidence: [],
  replayStatus: { ...EMPTY_DASHBOARD_REPLAY_STATUS }
};

export const EMPTY_DASHBOARD_EVIDENCE = {
  evidenceId: '',
  commandId: '',
  workflowId: '',
  traceId: '',
  type: '',
  status: '',
  summary: '',
  createdAt: '',
  redactionStatus: 'redacted'
};

const COMMAND_STATUS_TONES = {
  succeeded: 'success',
  failed: 'danger',
  blocked: 'warn',
  cancelled: 'warn',
  not_implemented: 'warn',
  running: 'info',
  admitted: 'info'
};

export const toneForCommandStatus = status => COMMAND_STATUS_TONES[String(status || '').trim()] || 'info';

export const toneForReplayStatus = status => {
  const value = String(status || '').trim();
  if (value === 'verified') return 'success';
  if (value === 'missing_evidence') return 'warn';
  if (value === 'evidence_mismatch') return 'danger';
  return 'info';
};

export const replayStatusLabel = status => {
  const value = String(status || '').trim();
  if (value === 'verified') return 'Verified';
  if (value === 'missing_evidence') return 'Missing evidence';
  if (value === 'evidence_mismatch') return 'Hash mismatch';
  if (value === 'never_replayed') return 'Never replayed';
  return value || 'Unknown';
};

export const normalizeDashboardLastReplay = replay => {
  const source = replay && typeof replay === 'object' ? replay : null;
  if (!source || !source.status) return null;
  return {
    ...EMPTY_DASHBOARD_LAST_REPLAY,
    status: String(source.status || ''),
    checkedAt: source.checkedAt || '',
    summary: source.summary || '',
    blockReason: source.blockReason ?? null,
    evidenceRefs: Array.isArray(source.evidenceRefs) ? source.evidenceRefs.map(String) : []
  };
};

export const normalizeReplayStatusCounts = counts => {
  const source = counts && typeof counts === 'object' ? counts : {};
  return {
    verified: Number(source.verified || 0),
    missing_evidence: Number(source.missing_evidence || 0),
    evidence_mismatch: Number(source.evidence_mismatch || 0),
    never_replayed: Number(source.never_replayed || 0)
  };
};

export const normalizeDashboardCommand = command => {
  const source = command && typeof command === 'object' ? command : {};
  return {
    ...EMPTY_DASHBOARD_COMMAND,
    ...source,
    commandId: source.commandId || EMPTY_DASHBOARD_COMMAND.commandId,
    workflowId: source.workflowId || EMPTY_DASHBOARD_COMMAND.workflowId,
    traceId: source.traceId || EMPTY_DASHBOARD_COMMAND.traceId,
    type: source.type || EMPTY_DASHBOARD_COMMAND.type,
    status: source.status || EMPTY_DASHBOARD_COMMAND.status,
    route: source.route || '',
    summary: source.summary || '',
    blockReason: source.blockReason ?? null,
    result: source.result && typeof source.result === 'object' ? source.result : {},
    evidenceRefs: Array.isArray(source.evidenceRefs) ? source.evidenceRefs : [],
    lastReplay: normalizeDashboardLastReplay(source.lastReplay)
  };
};

export const normalizeDashboardWorkflow = workflow => {
  const source = workflow && typeof workflow === 'object' ? workflow : {};
  return {
    ...EMPTY_DASHBOARD_WORKFLOW,
    ...source,
    workflowId: source.workflowId || EMPTY_DASHBOARD_WORKFLOW.workflowId,
    title: source.title || EMPTY_DASHBOARD_WORKFLOW.title,
    status: source.status || EMPTY_DASHBOARD_WORKFLOW.status,
    commandIds: Array.isArray(source.commandIds) ? source.commandIds.map(String) : [],
    latestCommandId: source.latestCommandId || '',
    traceIds: Array.isArray(source.traceIds) ? source.traceIds.map(String) : [],
    summary: source.summary || '',
    nextSafeAction: source.nextSafeAction || '',
    requiredOperatorAction: source.requiredOperatorAction ?? null
  };
};

export const normalizeDashboardCommandsPayload = payload => {
  const source = payload && typeof payload === 'object' ? payload : {};
  const commands = Array.isArray(source.commands) ? source.commands.map(normalizeDashboardCommand) : [];
  return {
    ok: Boolean(source.ok),
    commands,
    count: Number(source.count || commands.length || 0),
    command: source.command ? normalizeDashboardCommand(source.command) : null,
    workflow: source.workflow ? normalizeDashboardWorkflow(source.workflow) : null,
    error: source.error || ''
  };
};

export const normalizeDashboardCommandWorker = worker => {
  const source = worker && typeof worker === 'object' ? worker : {};
  return {
    ...EMPTY_DASHBOARD_PROJECTION.commandWorker,
    ...source,
    workerId: source.workerId || '',
    enabled: Boolean(source.enabled),
    mode: source.mode === 'background' ? 'background' : 'manual_tick',
    pendingCount: Number(source.pendingCount || 0),
    runningCount: Number(source.runningCount || 0),
    terminalCount: Number(source.terminalCount || 0),
    lastTickAt: source.lastTickAt || null,
    lastCommandId: source.lastCommandId || null,
    running: Boolean(source.running),
    poll_interval_s: Number(source.poll_interval_s || 1)
  };
};

export const normalizeDashboardEvidenceSummary = evidence => {
  const source = evidence && typeof evidence === 'object' ? evidence : {};
  return {
    ...EMPTY_DASHBOARD_EVIDENCE,
    ...source,
    evidenceId: source.evidenceId || '',
    commandId: source.commandId || '',
    workflowId: source.workflowId || '',
    traceId: source.traceId || '',
    type: source.type || '',
    status: source.status || '',
    summary: source.summary || '',
    createdAt: source.createdAt || '',
    redactionStatus: source.redactionStatus || 'redacted'
  };
};

export const normalizeDashboardProjection = payload => {
  const source = payload && typeof payload === 'object' ? payload : {};
  const contract = source.contract && typeof source.contract === 'object' ? source.contract : {};
  return {
    ...EMPTY_DASHBOARD_PROJECTION,
    ...source,
    contract: {
      ...EMPTY_DASHBOARD_PROJECTION.contract,
      ...contract
    },
    bridgeHealth: {
      ...EMPTY_DASHBOARD_PROJECTION.bridgeHealth,
      ...(source.bridgeHealth && typeof source.bridgeHealth === 'object' ? source.bridgeHealth : {})
    },
    commands: Array.isArray(source.commands) ? source.commands.map(normalizeDashboardCommand) : [],
    workflows: Array.isArray(source.workflows) ? source.workflows.map(normalizeDashboardWorkflow) : [],
    dashboardCache: {
      ...EMPTY_DASHBOARD_PROJECTION.dashboardCache,
      ...(source.dashboardCache && typeof source.dashboardCache === 'object' ? source.dashboardCache : {})
    },
    cloudSyncPreview: source.cloudSyncPreview && typeof source.cloudSyncPreview === 'object' ? source.cloudSyncPreview : {},
    collaborationProof: source.collaborationProof && typeof source.collaborationProof === 'object' ? source.collaborationProof : {},
    blockers: Array.isArray(source.blockers) ? source.blockers : [],
    nextSafeAction: source.nextSafeAction || '',
    currentWorkflowId: source.currentWorkflowId || '',
    commandWorker: normalizeDashboardCommandWorker(source.commandWorker),
    latestEvidence: Array.isArray(source.latestEvidence)
      ? source.latestEvidence.map(normalizeDashboardEvidenceSummary)
      : [],
    replayStatus: normalizeReplayStatusCounts(source.replayStatus)
  };
};

export const commandReceiptTitle = command => {
  const normalized = normalizeDashboardCommand(command);
  if (normalized.status === 'blocked') return 'Command blocked';
  if (normalized.status === 'not_implemented') return 'Route not implemented';
  if (normalized.status === 'failed') return 'Command failed';
  if (normalized.status === 'cancelled') return 'Command cancelled';
  if (normalized.status === 'succeeded') return 'Command succeeded';
  return 'Command admitted';
};

export const commandReceiptDetail = command => {
  const normalized = normalizeDashboardCommand(command);
  if (normalized.blockReason) return String(normalized.blockReason);
  if (normalized.summary) return String(normalized.summary);
  if (normalized.route) return normalized.route;
  return normalized.type;
};

export const dashboardCommandToJournalRow = (command, meta = {}) => {
  const normalized = normalizeDashboardCommand(command);
  const controlIds = [
    meta.controlId,
    ...(Array.isArray(meta.controlIds) ? meta.controlIds : [])
  ].filter(Boolean);
  return {
    id: normalized.commandId,
    time: normalized.updatedAt || normalized.createdAt || new Date().toISOString(),
    title: commandReceiptTitle(normalized),
    detail: commandReceiptDetail(normalized),
    tone: toneForCommandStatus(normalized.status),
    ...(controlIds.length > 0 ? { controlId: controlIds[0], controlIds } : {}),
    commandType: normalized.type,
    commandStatus: normalized.status,
    workflowId: normalized.workflowId,
    traceId: normalized.traceId,
    route: normalized.route,
    blockReason: normalized.blockReason,
    backendCommand: true
  };
};

export const buildCommandAdmissionPayload = ({
  type,
  route = '',
  summary = '',
  blockReason = null,
  result = {},
  workflowId = '',
  traceId = ''
} = {}) => ({
  type,
  route,
  summary,
  blockReason,
  result,
  ...(workflowId ? { workflowId } : {}),
  ...(traceId ? { traceId } : {}),
  requestedBy: 'dashboard'
});

