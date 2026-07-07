import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
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
  buildBridgeProbeCommsReceipt,
  buildCommandIntelligence,
  buildEvidenceIssueWindow,
  buildEvidenceReviewSignature,
  buildEventRows,
  buildLiveBlockerQueue,
  buildLocalSyncGate,
  buildPacketIntelligence,
  buildOpsChecklist,
  buildTopology,
  clampPercent,
  cloudSyncIssueDetail,
  cloudSyncIssueLabel,
  cloudSyncLabel,
  cloudSyncTone,
  collisionKey,
  ensureUniqueCommandIds,
  formatTimestamp,
  gateTone,
  impactedReposLabel,
  isLocalPacketIntelligenceCommand,
  isSuccessfulControlProofCommand,
  maskEndpoint,
  mergeCommandJournalRows,
  normalizeCodebaseAnalysis,
  normalizeCollaborationProof,
  normalizeDashboardPayload,
  normalizeRepoContext,
  normalizeVmRelayStatus,
  offlineDashboardStatusSnapshot,
  PROOF_JOURNAL_MAX_COMMANDS,
  restorePersistentCommandJournal,
  serializePersistentCommandJournal,
  summarizeCloudSyncGate,
  summarizeControlAudit,
  toneForActionStatus,
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
const CLOUD_PUBLISH_OBJECTIVE = 'Publish and synchronize the current Jules Bridge dashboard/model-agent work.';
const jsonHeaders = () => (TOKEN
  ? { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` }
  : { 'Content-Type': 'application/json' });
const COMMS_DEGRADED_RESPONSE_RE = /\b(no llm available|rate[- ]limited|provider exhaustion|providers? exhausted|openrouter free models failed|model loop unavailable|offline fallback)\b/i;
const COMMAND_JOURNAL_STORAGE_KEY = 'jules.dashboard.commandJournal.v1';

const commsDegradedReason = (reply, errors = []) => {
  const errorText = errors.filter(Boolean).join(' / ');
  if (errorText && COMMS_DEGRADED_RESPONSE_RE.test(errorText)) return errors.find(Boolean);
  if (COMMS_DEGRADED_RESPONSE_RE.test(String(reply || ''))) return String(reply || '').slice(0, 160);
  return '';
};

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: 'overview' },
  { id: 'tiu', label: 'TIU', icon: 'tiu' },
  { id: 'alliance', label: 'Alliance', icon: 'alliance' },
  { id: 'sync', label: 'Sync', icon: 'sync' },
  { id: 'fleet', label: 'Fleet', icon: 'fleet' },
  { id: 'repo', label: 'Repo', icon: 'repo' },
  { id: 'codebase', label: 'Codebase', icon: 'codebase' },
  { id: 'workers', label: 'Workers', icon: 'workers' },
  { id: 'comms', label: 'Comms', icon: 'comms' }
];

const FILTERS = ['ALL', 'WARN', 'ERROR'];
const CODEBASE_MODES = ['SUMMARY', 'FINDINGS', 'INTEGRATIONS'];

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
  codebase: (
    <>
      <path d="M5 5h14v14H5z" />
      <path d="M9 5v14" />
      <path d="M5 10h14" />
      <path d="M12 14h4" />
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

const DASHBOARD_CONTROL_CONTRACTS = [
  { id: 'nav-rail', surface: 'Navigation rail', action: 'Open dashboard lanes', kind: 'focus', focus: 'overview', target: 'Press any rail item such as Sync, Codebase, Workers, or Comms.', expected: 'The active rail changes and the matching dashboard lane scrolls into view.', evidence: 'Rail buttons route to focus targets and trigger scroll.' },
  { id: 'mission-open', surface: 'Mission Control', action: 'Open Lane', kind: 'focus', focus: 'overview', target: 'Select a topology node, then press Open Lane.', expected: 'The selected node stays highlighted and the linked lane receives focus.', evidence: 'Topology nodes select a route and open its linked lane.' },
  { id: 'mission-stage', surface: 'Mission Control', action: 'Stage Brief', kind: 'packet', focus: 'comms', target: 'Select a topology node, then press Stage Brief.', expected: 'Comms switches to Packet mode with a mission-route packet.', evidence: 'Topology brief is staged into Comms.' },
  { id: 'intelligence-stage', surface: 'Command Intelligence', action: 'Stage Scenario', kind: 'packet', focus: 'comms', target: 'Select a scenario card, then press Stage Scenario.', expected: 'Comms packet review receives a Dashboard Scenario Brief.', evidence: 'Scenario brief is staged into Comms.' },
  { id: 'intelligence-audit', surface: 'Command Intelligence', action: 'Run/Stage/Open Audit', kind: 'audit', focus: 'overview', target: 'Open Audit mode, then press Run Audit or Stage Audit.', expected: 'Audit rows, proof counts, and staged audit packets update from the current snapshot.', evidence: 'Audit mode inspects local controls and opens risk lanes.' },
  { id: 'action-receipt', surface: 'Action Receipt', action: 'Trace/Stage latest click outcome and next proof target', kind: 'packet+focus', focus: 'overview', target: 'Use Trace Journal, Stage Receipt, Open Next Proof, or Stage Next Proof from the Action Receipt card.', expected: 'Evidence mode opens to the command journal, Comms receives an action receipt, or the next unproven control is opened/staged for proof.', evidence: 'Action receipts turn button clicks into visible recent outcome records and route the next proof gap.' },
  { id: 'button-sweep', surface: 'Button Sweep', action: 'Measure rendered button health', kind: 'audit', focus: 'overview', target: 'Press Run Sweep, then inspect rendered button count, button risks, disabled controls, and Stage Sweep output.', expected: 'The dashboard measures actual visible buttons, flags rendered hitbox, label, viewport, and disabled-reason risks, and can stage a Button Sweep packet.', evidence: 'Button Sweep reads the live DOM after render instead of trusting source wiring.' },
  { id: 'break-test-lab', surface: 'Break Test Lab', action: 'Run/Open/Stage adversarial readiness checks', kind: 'audit', focus: 'overview', target: 'Press Run Break Test, inspect the weakest failure, then use Open Weakest or Stage Break Test.', expected: 'The dashboard combines rendered button health, control proof debt, sync, evidence, model, contract, and comms checks into a scored failure report.', evidence: 'Break Test Lab tries to disprove readiness with current DOM and bridge state before staging evidence.' },
  { id: 'bridge-probe', surface: 'Live Bridge Probe', action: 'Probe public bridge/model routes', kind: 'audit', focus: 'overview', target: 'Press Run Probe, inspect route latency/status rows, then Stage Probe if the result should go to Comms.', expected: 'The dashboard calls public local bridge routes, reports pass/fail/latency without leaking raw secrets, and stages a route-health packet.', evidence: 'Live Bridge Probe verifies backend and model-loop reachability through actual HTTP responses, not static dashboard labels.' },
  { id: 'proof-replay-lab', surface: 'Proof Replay Lab', action: 'Run/Open/Stage safe interaction proof replay', kind: 'audit', focus: 'overview', target: 'Press Run Replay, inspect the safe control rows, then open the next unproven target or stage the replay packet.', expected: 'The dashboard exercises a bounded set of safe local controls, records explicit proof IDs, and routes the next unproven target.', evidence: 'Proof Replay turns rendered/audit/break-test handlers into a visible session proof trail instead of a static source audit.' },
  { id: 'proof-sweep', surface: 'Control Proof Sweep', action: 'Group/Open/Stage proof coverage', kind: 'packet+focus', focus: 'overview', target: 'Run Audit, select a proof group, then press Open Group or Stage Sweep.', expected: 'The selected group updates the current target, opens its lane, or stages a Dashboard Proof Sweep packet.', evidence: 'Proof sweep groups control coverage by action kind and stages the next real target queue.' },
  { id: 'control-pulse', surface: 'Control Pulse', action: 'Start/Open/Stage proof sprint', kind: 'packet+focus', focus: 'overview', target: 'Use Start Pulse, Open Next, Stage Pulse, or Audit View from the Control Pulse card.', expected: 'The sprint selects the next unproven control, opens its lane, or stages a Control Pulse packet.', evidence: 'Control Pulse translates audit proof gaps into an actionable next-button sprint.' },
  { id: 'proof-runner', surface: 'Proof Runner', action: 'Start/Open/Advance/Batch/Stage real-control proof run', kind: 'packet+focus', focus: 'overview', target: 'Start a proof run, run the safe batch for local dashboard controllers, open the active target, then press target controls for remaining proof.', expected: 'The runner records bounded local-controller proof separately from queued target proof and advances only after target controls emit their own events.', evidence: 'Proof Runner separates safe controller checks, guidance clicks, and target proof so coverage cannot be inflated by one helper action.' },
  { id: 'command-brain', surface: 'Command Brain', action: 'Rank/Open/Stage next move', kind: 'packet+focus', focus: 'overview', target: 'Select a brain move, then press Open Move, Check Move, or Stage Move.', expected: 'The brain selection changes, opens the target lane, or stages a Command Brain Move packet.', evidence: 'Brain queue ranks next moves from live sync, evidence, and control proof state.' },
  { id: 'simulation-deck', surface: 'Decision Simulator', action: 'Toggle/Stage what-if gate plan', kind: 'packet+focus', focus: 'overview', target: 'Toggle an assumption or press Apply Brain, Open Gate, or Stage Sim.', expected: 'Projected score/priority changes, a gate lane opens, or a simulation packet is staged.', evidence: 'What-if deck changes projected score and stages an assumption packet.' },
  { id: 'runbook-operator', surface: 'Operator Runbook', action: 'Start/Open/Complete/Hold/Stage runbook steps', kind: 'packet+focus', focus: 'overview', target: 'Use Start, Open Step, Complete, Hold, Stage Book, or Reset.', expected: 'Runbook state changes between active/done/held/queued and packet mode receives the runbook.', evidence: 'Runbook advances active/done/held steps from live dashboard gates and stages execution packets.' },
  { id: 'telemetry-actions', surface: 'Telemetry', action: 'Stage/Open pressure lanes', kind: 'packet+focus', focus: 'fleet', target: 'Select a telemetry mode, then press Stage Pressure, Open Fleet, or Open Sync.', expected: 'Telemetry pressure is staged or the Fleet/Sync lane receives focus.', evidence: 'Pressure brief stages and Fleet/Sync actions move focus.' },
  { id: 'ops-plan', surface: 'No Slop Checklist', action: 'Plan Step', kind: 'packet', focus: 'comms', target: 'Select a checklist gate, then press Plan Step.', expected: 'Comms packet review receives a Smart Gate Step packet.', evidence: 'Selected gate stages a Smart Gate packet.' },
  { id: 'tiu-workbench', surface: 'TIU Workbench', action: 'Generate/Preview Packet', kind: 'protected-or-preview', focus: 'tiu', target: 'Set scope/lane/mode, then press Generate Packet for token-backed output or Local Preview for safe local review.', expected: 'The workbench shows protected-route output or a local preview packet with honest blockers.', evidence: 'Uses protected route when token-backed, and an explicit local preview path when the operator wants safe review.' },
  { id: 'alliance-actions', surface: 'Alliance Control', action: 'Stage/Open lanes', kind: 'packet+focus', focus: 'alliance', target: 'Select an alliance lane, then press Open Workbench or Stage Lane.', expected: 'The workbench opens for the lane or Comms receives an alliance lane brief.', evidence: 'Lane briefs stage and workbench buttons move focus.' },
  { id: 'sync-packet', surface: 'Cloud Sync', action: 'Build/Preview Publish Packet', kind: 'protected-or-preview', focus: 'sync', target: 'Open Sync and press Build Publish Packet for token-backed review or Local Preview for safe local review.', expected: 'Publish review state appears with blockers, families, commands, and a stageable packet.', evidence: 'Uses protected route when token-backed, and an explicit local preview path when the operator wants safe review.' },
  { id: 'fleet-actions', surface: 'Fleet Queue', action: 'Stage/Open queue lanes', kind: 'packet+focus', focus: 'fleet', target: 'Select a queue bucket, then press Stage Fleet, Open Workers, or Open TIU.', expected: 'The selected fleet bucket is staged or focus moves to Workers/TIU.', evidence: 'Queue selection stages a fleet packet and opens Workers/TIU.' },
  { id: 'workers-actions', surface: 'Worker Directory', action: 'Refresh/Stage/Open worker lanes', kind: 'packet+focus', focus: 'workers', target: 'Select a worker, press Refresh Worker Status, then Stage Worker, Open Fleet, or Open Comms.', expected: 'The panel samples GET /vm/status, renders live relay status, stages masked worker evidence, or moves focus to the target lane.', evidence: 'Worker Directory calls the public VM relay status route and keeps dispatch separate from read-only health checks.' },
  { id: 'repo-actions', surface: 'Repo Guard', action: 'Run/Stage/Open repo lanes', kind: 'protected-or-preview', focus: 'repo', target: 'Press Run Guard for a token-backed repo context refresh, select a guard/collision row, then press Stage Repo, Open Codebase, or Open Sync.', expected: 'The panel refreshes from GET /repo/context-guard when armed, or shows an honest token gate; Repo guard context is staged or focus moves to Codebase/Sync.', evidence: 'Repo Guard can call the protected local context guard route and render/stage the refreshed collision map.' },
  { id: 'codebase-actions', surface: 'Codebase Intelligence', action: 'Run/Stage/Open codebase lanes', kind: 'protected-or-preview', focus: 'codebase', target: 'Press Run Analysis for a token-backed local analyzer refresh, switch Summary/Findings/Integrations, then press Stage Brief or Open Repo.', expected: 'The panel refreshes from POST /codebase/analyze when armed, or shows an honest token gate; Codebase brief is staged or Repo Guard receives focus.', evidence: 'Codebase Intelligence can call the protected local analyzer route and render/stage the refreshed result.' },
  { id: 'evidence-actions', surface: 'Evidence Stream', action: 'Stage/Open evidence source', kind: 'packet+focus', focus: 'evidence', target: 'Select an event, then press Stage Event, Stage Window, or Open Source.', expected: 'Evidence packet/window is staged or the inferred source lane opens.', evidence: 'Selected event/window stages evidence and opens inferred source.' },
  { id: 'inspector-actions', surface: 'Inspector', action: 'Stage runtime/worker/collision', kind: 'packet+focus', focus: 'workers', target: 'Select a worker/collision/runtime object, then press an Inspector action.', expected: 'The selected object stages masked evidence or opens its related lane.', evidence: 'Inspector stages selected object or runtime packet.' },
  { id: 'comms-actions', surface: 'Comm Link', action: 'Probe/Review/Verify/Handoff/Clear', kind: 'draft', focus: 'comms', target: 'Press Probe Model or switch Comms to Packet mode and press a review, verify, verdict, restore, or clear action.', expected: 'The model loop returns an honest live response, or the draft/packet review state changes without launching workers or bypassing gates.', evidence: 'Probe Model sends a bounded live chat proof; Packet mode rewrites review prompts without launching workers.' },
  { id: 'header-strip', surface: 'Header status strip', action: 'Open status lanes', kind: 'focus', focus: 'evidence', target: 'Press a top status pill such as STREAM, CONTRACT, GEMINI, AGY, or BLOCKED.', expected: 'The corresponding lane opens and a Header status opened event is recorded.', evidence: 'Status pills route to contract, model, sync, runtime, or evidence lanes.' }
];

const DASHBOARD_CONTROL_IDS = DASHBOARD_CONTROL_CONTRACTS.map(control => control.id);
const CONTROL_ID_SET = new Set(DASHBOARD_CONTROL_IDS);
const CONTROL_BY_ID = new Map(DASHBOARD_CONTROL_CONTRACTS.map(control => [control.id, control]));
const COMMAND_JOURNAL_MAX_ROWS = PROOF_JOURNAL_MAX_COMMANDS + 1;

const normalizeControlIdList = value => String(value || '')
  .split(/[\s,|]+/)
  .map(item => item.trim())
  .filter(item => CONTROL_ID_SET.has(item));

const SAFE_PROOF_BATCH_CONTROL_IDS = [
  'nav-rail',
  'mission-open',
  'mission-stage',
  'intelligence-stage',
  'intelligence-audit',
  'action-receipt',
  'button-sweep',
  'break-test-lab',
  'bridge-probe',
  'proof-replay-lab',
  'proof-sweep',
  'control-pulse',
  'proof-runner',
  'command-brain',
  'simulation-deck',
  'runbook-operator',
  'telemetry-actions',
  'ops-plan',
  'tiu-workbench',
  'alliance-actions',
  'sync-packet',
  'fleet-actions',
  'workers-actions',
  'repo-actions',
  'codebase-actions',
  'evidence-actions',
  'inspector-actions',
  'comms-actions',
  'header-strip'
];

const BRIDGE_PROBE_ENDPOINTS = [
  {
    id: 'ping',
    label: 'Bridge ping',
    path: '/ping',
    focus: 'overview',
    pass: data => String(data?.status || '').includes('Jules Bridge Online'),
    detail: data => `${data?.status || 'unknown'} / ${data?.identity || data?.hostname || 'identity hidden'}`
  },
  {
    id: 'health',
    label: 'Health route',
    path: '/health',
    focus: 'overview',
    pass: data => data?.status === 'ok',
    detail: data => `${data?.status || 'unknown'} / ${data?.execution_context || 'context unknown'} / uptime ${Math.round(Number(data?.uptime_s || 0))}s`
  },
  {
    id: 'dashboard-status',
    label: 'Dashboard contract',
    path: '/dashboard/status',
    focus: 'evidence',
    pass: data => data?.contract?.name === 'jules_dashboard_status' && Number(data?.contract?.version || 0) >= 2,
    detail: data => `v${data?.contract?.version || 0} / ${data?.delivery?.transport || data?.contract?.transport || 'unknown'} / seq ${data?.delivery?.sequence || data?.contract?.sequence || 0}`
  },
  {
    id: 'vm-status',
    label: 'VM worker relay',
    path: '/vm/status',
    focus: 'workers',
    pass: data => data?.online === true,
    detail: data => `online=${data?.online === true} / completed ${Number(data?.tasks_completed || 0)} / running ${Number(data?.tasks_running || 0)}`
  },
  {
    id: 'chat-test',
    label: 'Model loop test',
    path: '/chat/test',
    focus: 'comms',
    pass: data => data?.healthy === true || Object.values(data?.providers || {}).some(row => row?.status === 'ok'),
    detail: data => {
      const providers = Object.entries(data?.providers || {})
        .map(([name, row]) => `${name}:${row?.status || 'unknown'}${row?.ms ? ` ${row.ms}ms` : ''}`);
      return `${data?.healthy ? 'healthy' : 'degraded'} / ${providers.join(', ') || 'no providers reported'}`;
    }
  }
];

const commandHasControl = (row, controlId) => {
  if (!controlId) return false;
  if (row.controlId === controlId) return true;
  return Array.isArray(row.controlIds) && row.controlIds.includes(controlId);
};

const CONTROL_PROOF_RULES = DASHBOARD_CONTROL_CONTRACTS.map(control => ({
  id: control.id,
  matches: row => commandHasControl(row, control.id) && isSuccessfulControlProofCommand(row)
}));

const buildControlProofMap = commands => {
  const normalized = (Array.isArray(commands) ? commands : []).map(row => ({
    ...row,
    title: String(row.title || ''),
    detail: String(row.detail || ''),
    titleLower: String(row.title || '').toLowerCase(),
    detailLower: String(row.detail || '').toLowerCase()
  }));
  const proofMap = CONTROL_PROOF_RULES.reduce((nextProofMap, rule) => {
    const proof = normalized.find(rule.matches);
    if (proof) nextProofMap.set(rule.id, proof);
    return nextProofMap;
  }, new Map());
  return proofMap;
};

const buildBootCommand = (title = 'Dashboard booted', detail = 'Awaiting live contract stream', tone = 'info') => ({
  id: 'boot',
  time: new Date().toISOString(),
  title,
  detail,
  tone
});

const loadInitialCommandJournal = () => {
  if (typeof window === 'undefined') return [buildBootCommand()];
  let restored = [];
  try {
    restored = restorePersistentCommandJournal(
      window.localStorage?.getItem(COMMAND_JOURNAL_STORAGE_KEY),
      DASHBOARD_CONTROL_IDS
    );
  } catch {
    restored = [];
  }
  if (!restored.length) return [buildBootCommand()];
  return [
    buildBootCommand(
      'Proof ledger restored',
      `${buildControlProofMap(restored).size}/${DASHBOARD_CONTROL_IDS.length} persistent control proofs loaded`,
      'success'
    ),
    ...ensureUniqueCommandIds(restored)
  ].slice(0, COMMAND_JOURNAL_MAX_ROWS);
};

const loadStoredCommandJournalProofs = () => {
  if (typeof window === 'undefined') return [];
  try {
    return restorePersistentCommandJournal(
      window.localStorage?.getItem(COMMAND_JOURNAL_STORAGE_KEY),
      DASHBOARD_CONTROL_IDS
    );
  } catch {
    return [];
  }
};

const CONTROL_KIND_ORDER = ['focus', 'packet', 'packet+focus', 'protected-or-preview', 'draft', 'audit'];
const CONTROL_KIND_LABELS = {
  audit: 'Audit',
  draft: 'Draft/review',
  focus: 'Focus',
  packet: 'Packet',
  'packet+focus': 'Packet + focus',
  'protected-or-preview': 'Protected preview'
};

const controlKindLabel = kind => CONTROL_KIND_LABELS[kind] || String(kind || 'control').replaceAll('-', ' ');

const controlKindRank = kind => {
  const index = CONTROL_KIND_ORDER.indexOf(kind);
  return index === -1 ? CONTROL_KIND_ORDER.length : index;
};

const buildProofCoverageRows = rows => {
  const buckets = new Map();
  (Array.isArray(rows) ? rows : [])
    .filter(row => row.provable)
    .forEach(row => {
      const key = row.kind || 'control';
      const bucket = buckets.get(key) || {
        id: key,
        label: controlKindLabel(key),
        total: 0,
        proven: 0,
        unproven: 0,
        preview: 0,
        rows: []
      };
      bucket.total += 1;
      bucket.proven += row.proof ? 1 : 0;
      bucket.unproven += row.proof ? 0 : 1;
      bucket.preview += row.state?.includes('preview-backed') ? 1 : 0;
      bucket.rows.push(row);
      buckets.set(key, bucket);
    });
  return [...buckets.values()]
    .sort((left, right) => controlKindRank(left.id) - controlKindRank(right.id) || left.label.localeCompare(right.label))
    .map(bucket => {
      const percent = bucket.total > 0 ? Math.round((bucket.proven / bucket.total) * 100) : 0;
      const nextRow = bucket.rows.find(row => !row.proof) || bucket.rows[0];
      return {
        ...bucket,
        percent,
        nextRow,
        tone: bucket.unproven > 0 ? 'warn' : 'success'
      };
    });
};

const REMEDIATION_FOCUS_OWNERS = {
  alliance: 'Alliance lane',
  codebase: 'Codebase lane',
  comms: 'Comms lane',
  evidence: 'Evidence lane',
  fleet: 'Fleet lane',
  overview: 'Mission Control',
  repo: 'Repo Guard',
  sync: 'Cloud Sync',
  workers: 'Worker lane'
};

const CONTROL_PROOF_SAFE_BATCH_ACTION_ID = 'control-proof-safe-batch';

const REMEDIATION_SAFE_ACTION_IDS = {
  'rendered-buttons': ['button-sweep'],
  'control-dom-coverage': ['button-sweep'],
  'disabled-reasons': ['button-sweep'],
  'control-proof': [CONTROL_PROOF_SAFE_BATCH_ACTION_ID],
  'sync-gate': ['sync-packet'],
  'evidence-health': ['evidence-actions'],
  'tunnel-health': ['bridge-probe'],
  'model-lane': ['alliance-actions'],
  'contract-stream': ['header-strip', 'inspector-actions'],
  'local-packet-intelligence': ['comms-actions'],
  'comms-loop': ['comms-actions']
};

const remediationExitCriteria = row => ({
  'rendered-buttons': 'Run Button Sweep again and verify zero rendered button risks.',
  'control-dom-coverage': 'Run Button Sweep again and verify every tracked control has a rendered target tag.',
  'disabled-reasons': 'Run Button Sweep again and verify every disabled control has a visible reason.',
  'control-proof': 'Run Audit or Proof Runner until every tracked control has explicit proof.',
  'sync-gate': 'Open Sync, build/review the publish packet, and rerun Break Test with no sync danger row.',
  'evidence-health': 'Open Evidence, stage the newest warning/error window, and rerun Break Test after the evidence tail is explained.',
  'tunnel-health': 'Run Live Bridge Probe after tunnel recovery or explicitly record local-only mode, then rerun Break Test with no tunnel fatal rows.',
  'model-lane': 'Open Alliance and verify the supported model lane before relying on autonomous model work.',
  'contract-stream': 'Refresh dashboard status and verify contract v2 over the expected stream/poll transport.',
  'local-packet-intelligence': 'Open Comms, stage a packet, run Local Review, and rerun Break Test with local packet intelligence recorded.',
  'comms-loop': 'Open Comms, run a harmless proof prompt, and verify the result is either a real response or an honest degraded state.'
}[row?.id] || `Rerun Break Test until ${row?.label || 'this check'} reports pass.`);

const buildRemediationRows = report => (report?.rows || [])
  .filter(row => row && row.tone !== 'success')
  .map((row, index) => ({
    ...row,
    priority: row.tone === 'danger' ? 'P1' : 'P2',
    owner: REMEDIATION_FOCUS_OWNERS[row.focus] || 'Dashboard lane',
    exitCriteria: row.exitCriteria || remediationExitCriteria(row),
    sequence: index + 1
  }));

const formatActionTime = value => new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit'
}).format(new Date(value));

const compactControlLabel = value => String(value || '')
  .replace(/\s+/g, ' ')
  .trim();

const dashboardStatusHasSample = status => !!(
  status?.statusTimestamp
  || status?.contractOk
  || status?.online
);

const dashboardStatusNeedsRefresh = status => (
  !dashboardStatusHasSample(status)
  && status?.updateMode === 'connecting'
);

const breakTestReportNeedsStatusRefresh = report => (
  Array.isArray(report?.rows)
  && report.rows.some(row => (
    row?.state === 'wait'
    && ['sync-gate', 'model-lane', 'contract-stream'].includes(row.id)
  ))
);

const localPreviewSaveWarning = writePacket => (writePacket
  ? 'packet_save_requires_protected_route'
  : 'local_preview_only');

const buildLocalTiuPreview = ({
  objective,
  scope,
  modelLane,
  mode,
  requireCloudSync,
  includeLiveChecks,
  writePacket,
  sysStatus
}) => {
  const sync = sysStatus.cloudSync || DEFAULT_STATUS.cloudSync;
  const syncGate = buildLocalSyncGate(sync);
  const alliance = sysStatus.alliance || DEFAULT_STATUS.alliance;
  const codebaseSummary = sysStatus.codebase?.summary || {};
  const blocked = requireCloudSync && syncGate.blockers.length > 0;
  const packet = [
    '# TIU Workbench Packet',
    '',
    `- objective: ${objective}`,
    `- scope: ${scope}`,
    `- lane: ${modelLane}`,
    `- mode: ${mode}`,
    `- generated_by: dashboard local preview`,
    `- route_count: ${codebaseSummary.route_count || 0}`,
    `- module_count: ${codebaseSummary.module_count || 0}`,
    `- sync_state: ${sync.state || 'unknown'}`,
    `- sync_blockers: ${syncGate.blockers.length ? syncGate.blockers.join(', ') : 'none'}`,
    `- alliance_mode: ${alliance.mode || 'unknown'}`,
    `- live_checks_requested: ${includeLiveChecks ? 'yes' : 'no'}`,
    `- packet_write_requested: ${writePacket ? 'yes' : 'no'}`,
    '',
    '## Guardrails',
    '- Do not launch live workers from this packet.',
    '- Use protected bridge routes only after token-backed operator review.',
    '- Keep cloud publish blocked until dirty work is reviewed and committed.',
    '',
    '## Next Action',
    blocked
      ? 'Resolve cloud sync blockers or turn off the cloud gate for a design-only packet.'
      : 'Review this packet in Comms, then run the protected TIU route when token-backed actions are available.'
  ].join('\n');
  return {
    status: blocked ? 'blocked' : 'ready_with_warnings',
    plan_state: blocked ? 'publish_blocked' : 'local_preview',
    blockers: blocked ? syncGate.blockers.map(item => `cloud_sync:${item}`) : [],
    warnings: [...new Set([
      'protected_route_not_called',
      ...syncGate.warnings.map(item => `cloud_sync:${item}`),
      localPreviewSaveWarning(writePacket)
    ])],
    packet,
    artifacts: { packet_written: false, packet_path: '' }
  };
};

const buildLocalPublishPreview = (sync, writePacket) => {
  const syncGate = buildLocalSyncGate(sync);
  const syncDiagnosis = summarizeCloudSyncGate(sync);
  const blocked = syncGate.blockers.length > 0;
  const gateMessage = blocked
    ? syncDiagnosis.action
    : syncGate.publishReady
      ? 'Local commits are ahead and the compact sync gate is publish-ready.'
      : syncGate.synced
        ? 'No cloud publish is needed; local and tracked remote state are clean.'
        : 'Publish readiness is not proven from the compact status snapshot. Use the protected route before claiming sync complete.';
  const packet = [
    '# Cloud Publish Review Packet',
    '',
    `- branch: ${sync.branch || 'unknown'}`,
    `- upstream: ${sync.upstream || 'not set'}`,
    `- state: ${sync.state || 'unknown'}`,
    `- status: ${sync.status || 'unknown'}`,
    `- publish_ready: ${syncGate.publishReady ? 'yes' : 'no'}`,
    `- ahead: ${syncGate.ahead}`,
    `- behind: ${syncGate.behind}`,
    `- dirty_count: ${syncGate.dirty}`,
    `- dirty_breakdown: ${syncDiagnosis.packetLines.find(line => line.startsWith('worktree: '))?.replace('worktree: ', '') || 'unknown'}`,
    `- blockers: ${syncGate.blockers.length ? syncGate.blockers.join(', ') : 'none'}`,
    `- warnings: ${syncGate.warnings.length ? syncGate.warnings.join(', ') : 'none'}`,
    `- generated_by: dashboard local preview`,
    `- packet_write_requested: ${writePacket ? 'yes' : 'no'}`,
    '',
    '## Review Commands',
    '- git status --short',
    '- git diff --stat',
    '- python -m pytest tests -q',
    '- npm run lint',
    '- npm run build',
    '',
    '## Guardrails',
    '- protected_routes_called: no',
    '- chat_send_called: no',
    '- publish_or_dispatch_called: no',
    '- local_preview_only: yes',
    '',
    '## Publish Gate',
    syncDiagnosis.detail,
    '',
    '## Next Safe Action',
    gateMessage
  ].join('\n');
  return {
    status: syncGate.status,
    state: syncGate.state,
    blockers: syncGate.blockers,
    warnings: [...new Set([
      'protected_route_not_called',
      ...syncGate.warnings,
      !syncGate.publishReady && !blocked ? 'publish_not_ready' : '',
      localPreviewSaveWarning(writePacket)
    ].filter(Boolean))],
    include_candidate_count: syncGate.publishReady ? syncGate.ahead : syncGate.dirty,
    change_families: [
      { family: 'worktree', label: 'Worktree', count: syncGate.dirty },
      { family: 'ahead', label: 'Ahead', count: syncGate.ahead },
      { family: 'behind', label: 'Behind', count: syncGate.behind },
      { family: 'blockers', label: 'Blockers', count: syncGate.blockers.length }
    ],
    commands: [
      { label: 'status', command: 'git status --short' },
      { label: 'diff', command: 'git diff --stat' },
      { label: 'tests', command: 'python -m pytest tests -q' }
    ],
    packet,
    artifacts: { packet_written: false, packet_path: '' }
  };
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

function StatusPill({ tone = 'info', children, onClick, title, controlId }) {
  if (onClick) {
    return (
      <button
        className={`status-pill status-action ${tone}`}
        type="button"
        onClick={onClick}
        title={title}
        data-control-id={controlId}
      >
        {children}
      </button>
    );
  }
  return <span className={`status-pill ${tone}`} title={title}>{children}</span>;
}

function IconButton({ icon, label, onClick, disabled = false, pressed = false, disabledReason = '', controlId = '' }) {
  const inactiveReason = disabled && disabledReason ? disabledReason : undefined;
  return (
    <button
      className="icon-button"
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={pressed}
      data-control-id={controlId || undefined}
      data-disabled-reason={inactiveReason}
      title={inactiveReason || label}
    >
      <Icon name={icon} />
    </button>
  );
}

function ActionReceiptDock({
  latestCommand,
  commandJournal,
  activeFocus,
  lastClickTrace,
  sync,
  eventRows,
  blockers = [],
  selectedBlockerId = '',
  blockerRun,
  onOpenFocus,
  onOpenBlocker,
  onRunBlocker,
  onStageBlocker
}) {
  const proofMap = buildControlProofMap(commandJournal);
  const syncGate = buildLocalSyncGate(sync);
  const errorCount = eventRows.filter(row => row.level === 'ERROR').length;
  const warningCount = eventRows.filter(row => row.level === 'WARN').length;
  const nextControl = DASHBOARD_CONTROL_CONTRACTS.find(control => !proofMap.has(control.id));
  const topBlocker = blockers[0] || null;
  const activeBlocker = blockers.find(row => row.id === selectedBlockerId) || topBlocker;
  const selectedNonTopBlocker = !!activeBlocker && activeBlocker.id !== topBlocker?.id;
  const tone = activeBlocker?.tone || latestCommand?.tone || (syncGate.blockers.length > 0 || errorCount > 0 ? 'warn' : 'info');
  const title = latestCommand?.title || 'Dashboard ready for proof';
  const detail = latestCommand?.detail || 'Press any tagged control to create a visible receipt and proof trace.';
  const proofLabel = `${proofMap.size}/${DASHBOARD_CONTROL_CONTRACTS.length}`;
  const nextLabel = nextControl ? `${nextControl.surface}: ${nextControl.action}` : 'All tracked controls proven';
  const queueLabel = activeBlocker ? `${activeBlocker.label}: ${activeBlocker.headline}` : nextLabel;
  const queueDetail = activeBlocker ? activeBlocker.action : nextControl ? nextControl.target : 'Keep using Break Test and Evidence to guard runtime claims.';
  const blockerLabel = selectedNonTopBlocker ? 'Selected Blocker' : 'Top Blocker';
  const openBlockerLabel = selectedNonTopBlocker ? 'Open Selected' : 'Open Top';
  const runBlockerLabel = selectedNonTopBlocker ? 'Run Selected Check' : 'Run Top Check';
  const stageBlockerLabel = selectedNonTopBlocker ? 'Stage Selected' : 'Stage Top';
  const noBlockerReason = 'No live blocker is available from the receipt dock.';

  return (
    <div className={`action-receipt-dock ${tone}`} aria-live="polite">
      <div className="action-receipt-dock-main">
        <span>Latest Action</span>
        <strong>{title}</strong>
        <em>{detail}</em>
      </div>
      <div className="action-receipt-dock-grid">
        <span><strong>{activeFocus || 'overview'}</strong> lane</span>
        <span><strong>{proofLabel}</strong> proof</span>
        <span><strong>{blockers.length}</strong> live blockers</span>
        <span><strong>{errorCount}/{warningCount}</strong> err/warn</span>
      </div>
      {lastClickTrace && (
        <div className={`action-receipt-click-trace ${lastClickTrace.controlId ? 'linked' : 'unlinked'}`}>
          <span>Last Click</span>
          <strong>{lastClickTrace.label}</strong>
          <em>{lastClickTrace.intent}</em>
          <b>{lastClickTrace.controlId || 'unlinked'}</b>
        </div>
      )}
      <div className="action-receipt-next">
        <span>{activeBlocker ? blockerLabel : 'Next Target'}</span>
        <strong>{queueLabel}</strong>
        <em>{queueDetail}</em>
      </div>
      <div className="action-receipt-dock-actions">
        <button className="secondary-action" type="button" data-control-id="action-receipt" onClick={() => onOpenFocus('comms')}>
          Open Comms
        </button>
        <button className="secondary-action" type="button" data-control-id="action-receipt" onClick={() => onOpenFocus('evidence')}>
          Open Evidence
        </button>
        <button
          className="secondary-action"
          type="button"
          data-control-id="action-receipt"
          onClick={() => onOpenBlocker(activeBlocker)}
          disabled={!activeBlocker}
          data-disabled-reason={!activeBlocker ? noBlockerReason : undefined}
          title={!activeBlocker ? noBlockerReason : undefined}
        >
          {openBlockerLabel}
        </button>
        <button
          className="secondary-action"
          type="button"
          data-control-id="action-receipt"
          onClick={() => onRunBlocker(activeBlocker)}
          disabled={!activeBlocker}
          data-disabled-reason={!activeBlocker ? noBlockerReason : undefined}
          title={!activeBlocker ? noBlockerReason : undefined}
        >
          {runBlockerLabel}
        </button>
        <button
          className="secondary-action"
          type="button"
          data-control-id="action-receipt"
          onClick={() => onStageBlocker(activeBlocker)}
          disabled={!activeBlocker}
          data-disabled-reason={!activeBlocker ? noBlockerReason : undefined}
          title={!activeBlocker ? noBlockerReason : undefined}
        >
          {stageBlockerLabel}
        </button>
      </div>
      <div className="action-receipt-blocker-list">
        {blockers.length > 0 ? blockers.slice(0, 5).map(row => (
          <button
            className={`action-receipt-blocker ${row.tone || 'warn'} ${row.id === activeBlocker?.id ? 'selected' : ''}`}
            type="button"
            key={row.id}
            data-control-id="action-receipt"
            aria-pressed={row.id === activeBlocker?.id}
            onClick={() => onOpenBlocker(row)}
          >
            <span>{row.label}</span>
            <strong>{row.headline}</strong>
            <em>{row.focus}</em>
          </button>
        )) : (
          <span className="action-receipt-blocker success">
            <span>Live Queue</span>
            <strong>No blocker rows in this snapshot</strong>
            <em>Run Break Test for deeper pressure.</em>
          </span>
        )}
      </div>
      {blockerRun && (
        <div className={`action-receipt-run ${blockerRun.tone || 'info'}`}>
          <div>
            <span>Resolution Check</span>
            <strong>{blockerRun.label}</strong>
            <em>{blockerRun.summary}</em>
          </div>
          <div className="action-receipt-run-rows">
            {blockerRun.rows.slice(0, 3).map(row => (
              <span className={row.tone || 'info'} key={row.id}>
                <strong>{row.label}</strong>
                <em>{row.observed}</em>
              </span>
            ))}
          </div>
          <p>{blockerRun.exitCriteria}</p>
        </div>
      )}
    </div>
  );
}

function Panel({ title, meta, tone = 'info', focus, activeFocus, className = '', actions, children }) {
  const dimmed = activeFocus !== 'overview' && focus && focus !== activeFocus;
  return (
    <section
      className={`command-panel ${className} ${dimmed ? 'is-dimmed' : ''}`}
      data-panel-focus={focus || undefined}
      tabIndex={focus ? -1 : undefined}
    >
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

const FOCUS_SCROLL_PADDING = 12;

const findFocusScrollContainer = target => {
  let parent = target?.parentElement;
  while (parent && parent !== document.body && parent !== document.documentElement) {
    const style = window.getComputedStyle(parent);
    const scrollable = /(auto|scroll|overlay)/.test(style.overflowY);
    if (scrollable && parent.scrollHeight > parent.clientHeight + 1) {
      return parent;
    }
    parent = parent.parentElement;
  }
  return document.scrollingElement || document.documentElement;
};

const scrollFocusPanelIntoView = target => {
  if (!target || typeof window === 'undefined') return;
  const scroller = findFocusScrollContainer(target);
  const targetRect = target.getBoundingClientRect();
  const scrollTop = Math.max(0, Math.round(
    scroller === document.documentElement || scroller === document.body
      ? window.scrollY + targetRect.top - FOCUS_SCROLL_PADDING
      : scroller.scrollTop + targetRect.top - scroller.getBoundingClientRect().top - FOCUS_SCROLL_PADDING
  ));

  if (scroller === document.documentElement || scroller === document.body) {
    window.scrollTo({ top: scrollTop, behavior: 'auto' });
  } else {
    scroller.scrollTo({ top: scrollTop, behavior: 'auto' });
  }
  target.focus({ preventScroll: true });
};

function NavRail({ activeFocus, onFocusChange }) {
  return (
    <nav className="nav-rail" aria-label="Dashboard focus">
      {NAV_ITEMS.map(item => (
        <button
          key={item.id}
          className={`rail-button ${activeFocus === item.id ? 'active' : ''}`}
          type="button"
          data-control-id="nav-rail"
          onClick={() => onFocusChange(item.id, { controlId: 'nav-rail' })}
          aria-current={activeFocus === item.id ? 'page' : undefined}
          title={item.label}
        >
          <Icon name={item.icon} />
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}

function TopologyMap({ nodes, selectedNodeId, onNodeSelect }) {
  return (
    <div className="topology-map" aria-label="Bridge execution topology">
      {nodes.map((node, index) => (
        <div className="topology-step" key={node.id}>
          <button
            className={`topology-node ${node.tone} ${selectedNodeId === node.id ? 'selected' : ''}`}
            type="button"
            aria-pressed={selectedNodeId === node.id}
            data-control-id="mission-open"
            data-control-intent={`Select ${node.label} topology route`}
            onClick={() => onNodeSelect(node)}
          >
            <div className="node-label">{node.label}</div>
            <div className="node-detail">{node.detail}</div>
            <div className="node-metric">{node.metric}</div>
          </button>
          {index < nodes.length - 1 && <div className={`topology-link ${node.tone}`} />}
        </div>
      ))}
    </div>
  );
}

function MissionSummary({ sysStatus, topology, selectedNode, activeFocus, onNodeSelect, onOpenNode, onStageNode }) {
  const repoSummary = sysStatus.repoContext?.summary || {};
  const fleet = sysStatus.fleet || {};
  const activeNode = selectedNode || topology[0];
  return (
    <Panel
      title="Mission Control"
      meta={`Last sample ${formatTimestamp(sysStatus.statusTimestamp)}`}
      tone={sysStatus.online ? 'success' : 'danger'}
      focus="overview"
      activeFocus={activeFocus}
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
        <div className="mission-topology-deck">
          <TopologyMap nodes={topology} selectedNodeId={activeNode?.id} onNodeSelect={onNodeSelect} />
          {activeNode && (
            <div className={`mission-focus-detail ${activeNode.tone || 'info'}`}>
              <div>
                <span>Selected route</span>
                <strong>{activeNode.label}</strong>
                <em>{activeNode.detail}</em>
              </div>
              <p>{activeNode.metric}</p>
              <div className="mission-focus-actions">
                <button className="secondary-action" type="button" data-control-id="mission-open" onClick={() => onOpenNode(activeNode)}>
                  Open Lane
                </button>
                <button className="secondary-action" type="button" data-control-id="mission-stage" onClick={() => onStageNode(activeNode)}>
                  Stage Brief
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}

function IntelligencePanel({
  sysStatus,
  activeFocus,
  selectedWorker,
  selectedCollision,
  eventRows,
  commandJournal,
  safeShellActions = [],
  onStagePacket,
  onCommandEvent,
  onFocusChange,
  onRefreshStatus = null
}) {
  const [mode, setMode] = useState('diagnose');
  const [scenarioId, setScenarioId] = useState('publish');
  const [controlAudit, setControlAudit] = useState(null);
  const [auditFilter, setAuditFilter] = useState('risks');
  const [selectedAuditRowId, setSelectedAuditRowId] = useState('');
  const [reviewedAuditRowIds, setReviewedAuditRowIds] = useState([]);
  const [selectedBrainId, setSelectedBrainId] = useState('');
  const [simulationDraft, setSimulationDraft] = useState({
    sync: false,
    evidence: false,
    controls: false,
    model: false
  });
  const [runbookState, setRunbookState] = useState({
    activeId: '',
    completed: [],
    held: []
  });
  const [buttonSweep, setButtonSweep] = useState(null);
  const [breakTest, setBreakTest] = useState(null);
  const [remediationRun, setRemediationRun] = useState(null);
  const [bridgeProbe, setBridgeProbe] = useState(null);
  const [proofReplay, setProofReplay] = useState(null);
  const [proofBatch, setProofBatch] = useState(null);
  const [proofRunner, setProofRunner] = useState({
    startedAt: '',
    queueIds: [],
    activeId: '',
    skippedIds: []
  });
  const remediationRunRef = useRef(null);
  const proofBatchRef = useRef(null);
  const controlAuditActiveRef = useRef(false);
  const brief = useMemo(
    () => buildCommandIntelligence({
      status: sysStatus,
      activeFocus,
      worker: selectedWorker,
      collision: selectedCollision,
      rows: eventRows,
      journal: commandJournal
    }),
    [activeFocus, commandJournal, eventRows, selectedCollision, selectedWorker, sysStatus]
  );
  const activeScenario = brief.scenarios.find(row => row.id === scenarioId) || brief.scenarios[0];
  const modes = [
    ['diagnose', 'Diagnose'],
    ['plan', 'Plan'],
    ['evidence', 'Evidence'],
    ['audit', 'Audit']
  ];
  const modeCopy = {
    diagnose: activeScenario?.detail || brief.headline,
    plan: activeScenario ? `${activeScenario.label}: ${activeScenario.metric}` : brief.summary,
    evidence: `${brief.summary}; ${brief.recentActions.length} local commands recorded.`,
    audit: controlAudit
      ? controlAudit.summary
      : 'Run a local control audit to prove focus, packet, and evidence actions are wired.'
  }[mode];
  const auditRows = controlAudit?.rows || [];
  const visibleAuditRows = auditRows.filter(row => {
    if (auditFilter === 'all') return true;
    if (auditFilter === 'packets') return row.kind?.includes('packet') || row.focus === 'comms';
    if (auditFilter === 'focus') return !!row.focus && row.focus !== 'comms';
    if (auditFilter === 'proof') return row.provable && !row.proof;
    return row.tone === 'danger' || row.tone === 'warn';
  });
  const selectedAuditRow = auditRows.find(row => row.id === selectedAuditRowId)
    || controlAudit?.riskRows?.[0]
    || auditRows[0];
  const reviewedAuditSet = new Set(reviewedAuditRowIds);
  const reviewedRiskCount = controlAudit?.riskRows.filter(row => reviewedAuditSet.has(row.id)).length || 0;
  const unreviewedRiskRows = controlAudit?.riskRows.filter(row => !reviewedAuditSet.has(row.id)) || [];
  const selectedAuditReviewed = !!(selectedAuditRow && reviewedAuditSet.has(selectedAuditRow.id));
  const controlProofEvents = commandJournal.filter(row => row.controlId || row.controlIds?.length);
  const latestCommand = commandJournal[0];
  const latestCommandControlIds = latestCommand
    ? [...new Set([
      latestCommand.controlId,
      ...(Array.isArray(latestCommand.controlIds) ? latestCommand.controlIds : [])
    ].filter(Boolean))]
    : [];
  const actionReceiptTone = latestCommand?.tone || 'info';
  const actionReceiptProofLabel = latestCommandControlIds.length ? latestCommandControlIds.join(', ') : 'untracked';
  const actionReceiptTrail = commandJournal.slice(0, 4);
  const actionReceiptProofMap = buildControlProofMap(commandJournal);
  const actionReceiptProvenCount = actionReceiptProofMap.size;
  const actionReceiptTotalCount = DASHBOARD_CONTROL_CONTRACTS.length;
  const actionReceiptNextControl = DASHBOARD_CONTROL_CONTRACTS.find(control => !actionReceiptProofMap.has(control.id));
  const actionReceiptProgressLabel = `${actionReceiptProvenCount}/${actionReceiptTotalCount}`;
  const unprovenControlRows = auditRows.filter(row => row.provable && !row.proof);
  const proofCoverageRows = buildProofCoverageRows(auditRows);
  const weakestCoverage = proofCoverageRows.find(row => row.unproven > 0) || proofCoverageRows[0];
  const drillTargetRow = selectedAuditRow?.provable && !selectedAuditRow.proof
    ? selectedAuditRow
    : unprovenControlRows[0];
  const drillProgress = controlAudit?.provableCount
    ? Math.round((controlAudit.provenCount / controlAudit.provableCount) * 100)
    : 0;
  const drillQueueRows = unprovenControlRows
    .filter(row => row.id !== drillTargetRow?.id)
    .slice(0, 4);
  const latestProofEvent = controlProofEvents[0];
  const drillGuideRows = drillTargetRow ? [
    ['Press', drillTargetRow.target || `Use ${drillTargetRow.label}.`],
    ['Expect', drillTargetRow.expected || drillTargetRow.evidence || drillTargetRow.detail],
    ['Proof', `Command journal event tagged ${drillTargetRow.controlId || drillTargetRow.id}.`]
  ] : [
    ['Status', latestProofEvent ? latestProofEvent.detail : 'All tracked controls have proof or no audit has run.']
  ];
  const proofTrailRows = controlProofEvents.slice(0, 4);
  const controlPulseProgress = controlAudit?.provableCount
    ? Math.round((controlAudit.provenCount / controlAudit.provableCount) * 100)
    : 0;
  const controlPulseTone = !controlAudit
    ? 'warn'
    : controlAudit.unprovenCount > 0
      ? 'warn'
      : 'success';
  const controlPulseTarget = drillTargetRow || unprovenControlRows[0];
  const controlPulseQueue = unprovenControlRows
    .filter(row => row.id !== controlPulseTarget?.id)
    .slice(0, 3);
  const controlPulseSummary = controlAudit
    ? `${controlAudit.provenCount}/${controlAudit.provableCount} proven; ${controlAudit.unprovenCount} still need real interaction.`
    : 'Audit not run; start the pulse to choose the next proof target.';
  const controlPulseInstruction = controlPulseTarget
    ? `${controlPulseTarget.target || controlPulseTarget.label} Expect: ${controlPulseTarget.expected || controlPulseTarget.evidence || controlPulseTarget.detail}`
    : latestProofEvent
      ? latestProofEvent.detail
      : 'Run a pulse to build a button-proof queue.';
  const proofRunnerQueueRows = proofRunner.queueIds.length
    ? proofRunner.queueIds.map(controlId => auditRows.find(row => row.controlId === controlId)).filter(Boolean)
    : unprovenControlRows.slice(0, 6);
  const proofRunnerUnprovenRows = proofRunnerQueueRows.filter(row => row.provable && !row.proof);
  const proofRunnerActiveRow = proofRunnerUnprovenRows.find(row => row.controlId === proofRunner.activeId)
    || proofRunnerUnprovenRows[0]
    || null;
  const proofRunnerDoneCount = proofRunnerQueueRows.filter(row => row.proof).length;
  const proofRunnerSkippedSet = new Set(proofRunner.skippedIds);
  const proofRunnerProgress = proofRunnerQueueRows.length
    ? Math.round((proofRunnerDoneCount / proofRunnerQueueRows.length) * 100)
    : 0;
  const proofRunnerTone = !controlAudit
    ? 'warn'
    : proofRunnerUnprovenRows.length > 0
      ? 'warn'
      : 'success';
  const proofRunnerSummary = controlAudit
    ? proofRunnerQueueRows.length > 0
      ? `${proofRunnerDoneCount}/${proofRunnerQueueRows.length} queued targets proven; ${proofRunnerUnprovenRows.length} active gaps.`
      : 'No proof-run targets remain in this audit snapshot.'
    : 'Start a proof run to build a bounded real-control queue.';
  const proofRunnerInstruction = proofRunnerActiveRow
    ? `${proofRunnerActiveRow.target || proofRunnerActiveRow.label} Expect: ${proofRunnerActiveRow.expected || proofRunnerActiveRow.evidence || proofRunnerActiveRow.detail}`
    : controlAudit
      ? 'The runner is clear; rerun Audit to confirm no proof gaps remain.'
      : 'Start Run selects the next controls, Open Target only navigates, and the real control click must emit proof.';
  const proofRunnerNextActiveId = proofRunnerUnprovenRows[0]?.controlId || '';
  const proofBatchTone = !proofBatch
    ? 'info'
    : proofBatch.failureCount > 0
      ? 'warn'
      : proofBatch.warningCount > 0
        ? 'warn'
        : 'success';
  const proofBatchSummary = proofBatch
    ? `${proofBatch.successCount}/${proofBatch.totalCount} safe checks exercised; ${proofBatch.warningCount || 0} warnings; ${proofBatch.shellRouteCount || 0} shell routes; ${proofBatch.localPreviewCount || 0} local previews; ${proofBatch.localPanelActionCount || 0} local panel actions; ${proofBatch.localCommsReviewCount || 0} local Comms reviews; ${proofBatch.packetStageCount || 0} local packet stages; projected proof ${proofBatch.afterProvenCount}/${DASHBOARD_CONTROL_CONTRACTS.length}.`
    : 'Safe Batch exercises shell routes, local dashboard controllers, local preview builders, local panel actions, local Comms review, local packet stages, and public bridge probes; it does not publish, dispatch workers, or send chat.';
  const buttonSweepTone = buttonSweep?.tone || 'warn';
  const buttonSweepSummary = buttonSweep
    ? `${buttonSweep.total} rendered buttons; ${buttonSweep.issueCount} button risks; ${buttonSweep.controlLinkedButtonCount}/${buttonSweep.total} linked buttons; ${buttonSweep.taggedControlCount}/${buttonSweep.contractControlCount} control targets`
    : 'Run a rendered DOM sweep to prove button labels, hitboxes, disabled reasons, and overflow.';
  const buttonSweepHeadline = buttonSweep
    ? buttonSweep.issueCount > 0
      ? `${buttonSweep.issueCount} rendered button risks need repair.`
      : buttonSweep.untaggedControlCount > 0
        ? `${buttonSweep.untaggedControlCount} control contracts need DOM targets.`
        : buttonSweep.unlinkedButtonCount > 0
          ? `${buttonSweep.unlinkedButtonCount} visible buttons need control trace IDs.`
          : 'Rendered buttons have sane labels, hitboxes, disabled reasons, and control targets.'
    : 'No rendered button sweep yet.';
  const buttonSweepCoverageRow = buttonSweep
    ? {
      label: buttonSweep.untaggedControlCount > 0 ? 'Control contract gaps' : 'Control contract coverage',
      section: 'Button Sweep',
      detail: buttonSweep.untaggedControlCount > 0
        ? `${buttonSweep.taggedControlCount}/${buttonSweep.contractControlCount} tracked controls are tagged; missing ${buttonSweep.untaggedControls.map(row => row.id).join(', ')}.`
        : `${buttonSweep.taggedControlCount}/${buttonSweep.contractControlCount} tracked controls have rendered target tags.`,
      tone: buttonSweep.untaggedControlCount > 0 ? 'warn' : 'success'
    }
    : null;
  const buttonSweepTraceRow = buttonSweep
    ? {
      label: buttonSweep.unlinkedButtonCount > 0 ? 'Button trace gaps' : 'Button trace coverage',
      section: 'Button Sweep',
      detail: buttonSweep.unlinkedButtonCount > 0
        ? `${buttonSweep.controlLinkedButtonCount}/${buttonSweep.total} rendered buttons have control IDs; first gaps: ${buttonSweep.unlinkedButtons.map(row => row.label).slice(0, 4).join(', ')}.`
        : `${buttonSweep.controlLinkedButtonCount}/${buttonSweep.total} rendered buttons are linked to a dashboard control ID.`,
      tone: buttonSweep.unlinkedButtonCount > 0 ? 'warn' : 'success'
    }
    : null;
  const buttonSweepRows = buttonSweep?.issues?.length
    ? [...buttonSweep.issues.slice(0, 3), buttonSweepCoverageRow, buttonSweepTraceRow]
    : buttonSweep?.untaggedControls?.length
      ? buttonSweep.untaggedControls.slice(0, 4).map(row => ({
        label: row.id,
        section: row.surface,
        issue: `missing rendered target tag for ${row.action}`,
        size: `${buttonSweep.taggedControlCount}/${buttonSweep.contractControlCount}`,
        tone: 'warn'
      }))
      : buttonSweep?.unlinkedButtons?.length
        ? [buttonSweepCoverageRow, buttonSweepTraceRow, ...buttonSweep.unlinkedButtons.slice(0, 3).map(row => ({
          label: row.label,
          section: row.section,
          detail: `missing control trace id / ${row.size}`,
          tone: 'warn'
        }))]
      : buttonSweep?.disabled?.length
        ? [buttonSweepCoverageRow, buttonSweepTraceRow, ...buttonSweep.disabled.slice(0, 3)]
        : buttonSweep
          ? [buttonSweepCoverageRow, buttonSweepTraceRow, ...buttonSweep.sections.slice(0, 3)]
          : [];
  const breakTestTone = breakTest?.tone || 'warn';
  const breakTestSummary = breakTest
    ? `${breakTest.score}% resilience; ${breakTest.failCount} failures; ${breakTest.warnCount} warnings`
    : 'Run an adversarial readiness check that tries to disprove the dashboard is actually usable.';
  const breakTestHeadline = breakTest
    ? breakTest.failCount > 0
      ? `${breakTest.failCount} break-test failures need evidence before any ready claim.`
      : breakTest.warnCount > 0
        ? `${breakTest.warnCount} warning gates remain after break testing.`
        : 'Break test found no current readiness failures.'
    : 'No adversarial break test has run yet.';
  const breakTestRows = breakTest?.rows
    ? [
      ...breakTest.rows.slice(0, 4),
      breakTest.rows.find(row => row.id === 'control-dom-coverage')
    ].filter((row, index, rows) => row && rows.findIndex(candidate => candidate.id === row.id) === index)
    : [];
  const breakTestRemediationRows = buildRemediationRows(breakTest);
  const remediationTone = breakTestRemediationRows.some(row => row.tone === 'danger')
    ? 'danger'
    : breakTestRemediationRows.length > 0
      ? 'warn'
      : breakTest
        ? 'success'
        : 'info';
  const remediationSummary = breakTest
    ? breakTestRemediationRows.length > 0
      ? `${breakTestRemediationRows.length} remediation targets ranked from the latest break test.`
      : 'No remediation rows remain in the latest break test.'
    : 'Run Break Test to build a ranked remediation queue.';
  const remediationRunTone = remediationRun?.tone || 'info';
  const remediationRunIsPlan = remediationRun?.targetId === 'safe-plan';
  const remediationRunSummary = remediationRun
    ? `${remediationRun.targetLabel}; ${remediationRun.successCount}/${remediationRun.totalCount} safe rows; ${remediationRun.reviewedPacketCount} packet reviews; ${remediationRun.gatedTargetCount || 0} manual gates; live actions skipped.`
    : 'Run a safe step to prepare the first remediation target without publishing, dispatching workers, or sending chat.';
  const scheduleRemediationReceiptScroll = useCallback(() => {
    if (typeof window === 'undefined') return;
    const scrollReceipt = () => {
      remediationRunRef.current?.scrollIntoView({ block: 'center', inline: 'nearest' });
    };
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(scrollReceipt);
      });
    }
    [120, 360, 720].forEach(delay => {
      window.setTimeout(scrollReceipt, delay);
    });
  }, []);
  useEffect(() => {
    if (!remediationRun) return;
    scheduleRemediationReceiptScroll();
  }, [remediationRun, scheduleRemediationReceiptScroll]);
  const bridgeProbeTone = bridgeProbe?.tone || 'warn';
  const bridgeProbeSummary = bridgeProbe
    ? `${bridgeProbe.passCount}/${bridgeProbe.totalCount} live routes passed; ${bridgeProbe.failCount} failed; avg ${bridgeProbe.averageMs}ms.`
    : 'Run a live route probe to verify bridge, dashboard contract, VM relay, and model-loop reachability.';
  const bridgeProbeHeadline = bridgeProbe
    ? bridgeProbe.failCount > 0
      ? `${bridgeProbe.failCount} live route probes failed.`
      : bridgeProbe.warnCount > 0
        ? `${bridgeProbe.warnCount} live route probes need review.`
        : 'Bridge routes and model loop responded to live HTTP probes.'
    : 'No live bridge probe has run yet.';
  const bridgeProbeRows = bridgeProbe?.rows?.slice(0, 5) || [];
  const proofReplayTone = proofReplay?.tone || 'warn';
  const proofReplaySummary = proofReplay
    ? `${proofReplay.exercisedCount} safe checks observed; ${proofReplay.nextQueueCount} proof targets remain`
    : 'Run a safe interaction replay to create explicit proof events before claiming the controls work.';
  const proofReplayHeadline = proofReplay
    ? proofReplay.dangerCount > 0
      ? `${proofReplay.dangerCount} replay checks still found hard blockers.`
      : proofReplay.warnCount > 0
        ? `${proofReplay.warnCount} replay checks need follow-up.`
        : 'Safe replay created fresh session proof.'
    : 'No proof replay has run yet.';
  const proofReplayRows = proofReplay?.rows?.slice(0, 5) || [];
  const selectedRiskRecommendation = selectedAuditRow ? (() => {
    if (selectedAuditRow.provable && !selectedAuditRow.proof) {
      return 'Open the linked lane and use the named surface action; proof is recorded only from that control event.';
    }
    if (selectedAuditRow.focus === 'sync') {
      return 'Open Sync, review blockers, and stage a publish packet before any push claim.';
    }
    if (selectedAuditRow.focus === 'evidence') {
      return 'Open Evidence, select the newest warning/error, and stage an evidence window.';
    }
    if (selectedAuditRow.focus === 'comms') {
      return 'Open Comms, review the staged packet, and prepare a verify prompt before sending.';
    }
    if (selectedAuditRow.focus === 'fleet' || selectedAuditRow.focus === 'workers') {
      return 'Open the worker lane, inspect live status, and stage bounded worker evidence before dispatch.';
    }
    if (selectedAuditRow.focus === 'repo' || selectedAuditRow.focus === 'codebase') {
      return 'Open the repo/codebase lane and stage a narrow guard packet before changing files.';
    }
    return 'Open the linked lane, inspect its evidence, and stage the narrowest packet that proves the next move.';
  })() : '';
  const syncSignal = brief.signals.find(row => row.label === 'Sync') || {};
  const eventSignal = brief.signals.find(row => row.label === 'Events') || {};
  const modelScenario = brief.scenarios.find(row => row.id === 'model');
  const syncScenario = brief.scenarios.find(row => row.id === 'publish');
  const evidenceScenario = brief.scenarios.find(row => row.id === 'evidence');
  const warningEventCount = eventRows.filter(row => row.level === 'WARN').length;
  const errorEventCount = eventRows.filter(row => row.level === 'ERROR').length;
  const evidenceReviewWindow = buildEvidenceReviewSignature(eventRows);
  const latestEvidenceWindowReview = evidenceReviewWindow.signature
    ? commandJournal.find(row => row.evidenceKind === 'window' && row.evidenceSignature === evidenceReviewWindow.signature)
    : null;
  const evidenceIssuesReviewed = !!latestEvidenceWindowReview;
  const evidenceIssueTone = errorEventCount > 0
    ? evidenceIssuesReviewed ? 'warn' : 'danger'
    : warningEventCount > 0
      ? evidenceIssuesReviewed ? 'success' : 'warn'
      : 'success';
  const unprovenControls = controlAudit ? controlAudit.unprovenCount : DASHBOARD_CONTROL_CONTRACTS.length;
  const brainItems = [
    {
      id: 'prove-controls',
      label: 'Prove live controls',
      state: controlAudit ? `${controlAudit.provenCount}/${controlAudit.provableCount} proven` : 'audit not run',
      tone: unprovenControls > 0 ? 'warn' : 'success',
      urgency: unprovenControls > 0 ? 96 : 52,
      confidence: controlAudit ? (unprovenControls > 0 ? 82 : 96) : 58,
      focus: 'overview',
      mode: 'audit',
      auditFilter: 'proof',
      detail: unprovenControls > 0
        ? `${unprovenControls} controls still need explicit interaction proof.`
        : 'All tracked controls have proof in this session.',
      reasons: [
        'The user asked for buttons that actually work.',
        'The audit only trusts explicit control events.',
        'A real proof trail is stronger than visual presence.'
      ],
      steps: ['Run the audit', 'Open the next target', 'Use the named control', 'Stage a drill packet if the target remains unproven']
    },
    {
      id: 'sync-blocker',
      label: syncScenario?.label || 'Review sync gate',
      state: syncSignal.value || 'sync unknown',
      tone: syncSignal.tone || 'warn',
      urgency: syncSignal.tone === 'danger' ? 92 : syncSignal.tone === 'warn' ? 72 : 30,
      confidence: syncSignal.tone === 'danger' ? 91 : 74,
      focus: 'sync',
      mode: 'plan',
      scenarioId: 'publish',
      detail: syncScenario?.detail || 'Inspect cloud sync before claiming publish readiness.',
      reasons: [
        'Publish safety depends on dirty/ahead/behind gates.',
        'Cloud sync state affects worker handoff quality.',
        'The dashboard should explain blockers before offering a publish step.'
      ],
      steps: ['Open Sync', 'Read visible blockers', 'Build a publish review packet', 'Keep push blocked until the packet is reviewed']
    },
    {
      id: 'evidence-health',
      label: evidenceScenario?.label || 'Inspect evidence tail',
      state: eventSignal.value || `${warningEventCount} warn / ${errorEventCount} err`,
      tone: evidenceIssueTone,
      urgency: errorEventCount > 0 ? evidenceIssuesReviewed ? 66 : 88 : warningEventCount > 0 ? evidenceIssuesReviewed ? 38 : 68 : 34,
      confidence: eventRows.length > 0 ? 86 : 45,
      focus: 'evidence',
      mode: 'evidence',
      scenarioId: 'evidence',
      detail: evidenceIssuesReviewed
        ? `Current issue window staged for review: ${evidenceReviewWindow.label}.`
        : evidenceScenario?.detail || 'Use the event tail as current bridge evidence.',
      reasons: [
        'Health claims need log evidence.',
        'Warnings and errors should route to a visible source lane.',
        'Evidence packets keep model/worker review bounded.'
      ],
      steps: ['Open Evidence', 'Select the newest warning or error', 'Stage the event/window', 'Use the packet in Comms review']
    },
    {
      id: 'model-alliance',
      label: modelScenario?.label || 'Check model alliance',
      state: modelScenario?.metric || 'model lane',
      tone: modelScenario?.tone || 'info',
      urgency: modelScenario?.tone === 'success' ? 54 : 76,
      confidence: modelScenario?.tone === 'success' ? 84 : 62,
      focus: 'alliance',
      mode: 'plan',
      scenarioId: 'model',
      detail: modelScenario?.detail || 'Confirm the local model/agent lane before relying on autonomous work.',
      reasons: [
        'The intelligence surface should expose which agent lane is actually ready.',
        'Gemini/Antigravity state changes what kind of handoff is safe.',
        'Model readiness is separate from UI reachability.'
      ],
      steps: ['Open Alliance', 'Check implementer readiness', 'Stage the relevant lane brief', 'Return to Comms with a bounded prompt']
    }
  ].sort((left, right) => right.urgency - left.urgency);
  const activeBrain = brainItems.find(row => row.id === selectedBrainId) || brainItems[0];
  const simulationRows = [
    {
      id: 'sync',
      label: 'Clear sync gate',
      state: syncSignal.value || 'sync unknown',
      tone: syncSignal.tone || 'info',
      needsWork: syncSignal.tone === 'danger' || syncSignal.tone === 'warn',
      impact: syncSignal.tone === 'danger' ? 18 : syncSignal.tone === 'warn' ? 11 : 3,
      focus: 'sync',
      detail: syncScenario?.detail || 'Resolve dirty/ahead/behind/auth gates before publish claims.',
      sequence: 'Open Sync, build or review the publish packet, and keep push blocked until reviewed.'
    },
    {
      id: 'evidence',
      label: 'Stabilize evidence',
      state: `${warningEventCount} warn / ${errorEventCount} err`,
      tone: evidenceIssueTone,
      needsWork: (errorEventCount > 0 || warningEventCount > 0) && !evidenceIssuesReviewed,
      impact: errorEventCount > 0 ? 16 : warningEventCount > 0 ? 9 : 3,
      focus: 'evidence',
      detail: evidenceIssuesReviewed
        ? `Current issue window staged for review: ${evidenceReviewWindow.label}.`
        : evidenceScenario?.detail || 'Use the event tail before claiming bridge health.',
      sequence: 'Open Evidence, stage the newest event/window, and attach it to the next handoff.'
    },
    {
      id: 'controls',
      label: 'Prove controls',
      state: controlAudit ? `${controlAudit.provenCount}/${controlAudit.provableCount} proven` : 'audit not run',
      tone: unprovenControls > 0 ? 'warn' : 'success',
      needsWork: unprovenControls > 0,
      impact: unprovenControls > 0 ? Math.min(18, Math.max(8, unprovenControls)) : 4,
      focus: 'overview',
      detail: unprovenControls > 0
        ? `${unprovenControls} controls still need explicit dashboard proof.`
        : 'The tracked controls are proven in this session.',
      sequence: 'Run the audit, open the next target, and use the named control instead of counting helper clicks.'
    },
    {
      id: 'model',
      label: 'Confirm model lane',
      state: modelScenario?.metric || 'model lane',
      tone: modelScenario?.tone || 'info',
      needsWork: modelScenario?.tone !== 'success',
      impact: modelScenario?.tone === 'success' ? 3 : 12,
      focus: 'alliance',
      detail: modelScenario?.detail || 'Confirm the local model/agent lane before autonomous work.',
      sequence: 'Open Alliance, verify the implementer lane, and stage the relevant model/agent brief.'
    }
  ];
  const activeSimulationRows = simulationRows.filter(row => simulationDraft[row.id]);
  const projectedScore = clampPercent(
    brief.healthScore + activeSimulationRows.reduce((total, row) => total + row.impact, 0)
  );
  const remainingDangerCount = simulationRows.filter(row => row.needsWork && row.tone === 'danger' && !simulationDraft[row.id]).length;
  const remainingWarnCount = simulationRows.filter(row => row.needsWork && row.tone !== 'danger' && !simulationDraft[row.id]).length;
  const projectedPriority = remainingDangerCount > 0
    ? 'intervention'
    : remainingWarnCount > 0
      ? 'watch'
      : 'clear';
  const projectedTone = projectedPriority === 'intervention' ? 'danger' : projectedPriority === 'watch' ? 'warn' : 'success';
  const suggestedSimulationId = {
    'prove-controls': 'controls',
    'sync-blocker': 'sync',
    'evidence-health': 'evidence',
    'model-alliance': 'model'
  }[activeBrain?.id] || 'sync';
  const simulationSequence = (activeSimulationRows.length > 0
    ? [...activeSimulationRows].sort((left, right) => right.impact - left.impact)
    : simulationRows.filter(row => row.needsWork).sort((left, right) => right.impact - left.impact)
  ).slice(0, 4);
  const projectionDelta = projectedScore - brief.healthScore;
  const runbookGateRows = (simulationRows.some(row => row.needsWork || simulationDraft[row.id])
    ? simulationRows.filter(row => row.needsWork || simulationDraft[row.id])
    : [simulationRows[0], simulationRows[3]].filter(Boolean)
  ).sort((left, right) => right.impact - left.impact);
  const runbookRows = [
    ...runbookGateRows.map(row => ({
      id: `${row.id}-runbook`,
      sourceId: row.id,
      label: row.label,
      state: simulationDraft[row.id] ? 'assumed in simulation' : row.state,
      tone: row.tone || 'info',
      focus: row.focus || 'overview',
      metric: `impact +${row.impact}`,
      detail: row.detail,
      intent: row.sequence
    })),
    {
      id: 'comms-runbook',
      sourceId: 'comms',
      label: 'Handoff packet',
      state: 'packet review',
      tone: projectedTone,
      focus: 'comms',
      metric: `${projectedPriority} / ${projectedScore}`,
      detail: 'Stage the current verdict, runbook state, and evidence sequence for review before protected actions.',
      intent: 'Open Comms, review the staged packet, and keep launch/publish actions gated until evidence is reviewed.'
    }
  ];
  const runbookIds = runbookRows.map(row => row.id).join('|');
  const firstRunbookId = runbookRows[0]?.id || '';
  const completedRunbookSet = new Set(runbookState.completed);
  const heldRunbookSet = new Set(runbookState.held);
  const activeRunbookStep = runbookRows.find(row => row.id === runbookState.activeId)
    || runbookRows.find(row => !completedRunbookSet.has(row.id) && !heldRunbookSet.has(row.id))
    || runbookRows[0];
  const runbookDoneCount = runbookRows.filter(row => completedRunbookSet.has(row.id)).length;
  const runbookHeldCount = runbookRows.filter(row => heldRunbookSet.has(row.id)).length;
  const runbookProgress = runbookRows.length ? Math.round((runbookDoneCount / runbookRows.length) * 100) : 0;
  const runbookTone = runbookHeldCount > 0
    ? 'warn'
    : runbookDoneCount === runbookRows.length && runbookRows.length > 0
      ? 'success'
      : activeRunbookStep?.tone || 'info';

  useEffect(() => {
    if (!brief.scenarios.some(row => row.id === scenarioId)) {
      setScenarioId(brief.scenarios[0]?.id || 'publish');
    }
  }, [brief.scenarios, scenarioId]);

  useEffect(() => {
    if (brainItems.length > 0 && !brainItems.some(row => row.id === selectedBrainId)) {
      setSelectedBrainId(brainItems[0].id);
    }
  }, [brainItems, selectedBrainId]);

  useEffect(() => {
    controlAuditActiveRef.current = !!controlAudit;
  }, [controlAudit]);

  useEffect(() => {
    const currentIds = new Set(runbookIds.split('|').filter(Boolean));
    setRunbookState(previous => {
      if (currentIds.size === 0) {
        return previous;
      }
      const completed = previous.completed.filter(id => currentIds.has(id));
      const held = previous.held.filter(id => currentIds.has(id));
      const activeId = currentIds.has(previous.activeId) ? previous.activeId : firstRunbookId;
      if (activeId === previous.activeId && completed.length === previous.completed.length && held.length === previous.held.length) {
        return previous;
      }
      return { activeId, completed, held };
    });
  }, [firstRunbookId, runbookIds]);

  const createControlAudit = useCallback(() => {
    const focusTargets = new Set(['overview', 'tiu', 'alliance', 'sync', 'fleet', 'repo', 'codebase', 'workers', 'comms', 'evidence', 'telemetry']);
    const proofMap = buildControlProofMap(commandJournal);
    const scenarioRows = brief.scenarios.map(scenario => {
      const wired = !!scenario.focus && focusTargets.has(scenario.focus);
      return {
        id: `scenario-${scenario.id}`,
        label: `Scenario: ${scenario.label}`,
        state: wired ? 'focus wired' : 'missing focus',
        detail: wired ? `${scenario.focus} lane responds to Open scenario lane.` : 'Scenario has no known focus target.',
        tone: wired ? scenario.tone || 'success' : 'danger',
        focus: scenario.focus || 'overview'
      };
    });
    const actionRows = brief.recommendedActions.map(action => {
      const packetAction = !!action.packet;
      const wired = packetAction || (!!action.focus && focusTargets.has(action.focus));
      return {
        id: `action-${action.id}`,
        label: `Action: ${action.label}`,
        state: packetAction ? 'packet action' : wired ? 'focus action' : 'unwired',
        detail: packetAction ? 'Stages a bounded packet into Comms.' : action.detail,
        tone: wired ? action.tone || 'success' : 'danger',
        focus: action.focus || (packetAction ? 'comms' : 'overview')
      };
    });
    const contractRow = {
      id: 'system-contract',
      label: 'System: status contract',
      state: sysStatus.contractOk ? `v${sysStatus.contract?.version || 0}` : 'contract drift',
      detail: `${sysStatus.updateMode || 'unknown'} transport; stream ${sysStatus.streamSequence || 0}.`,
      tone: sysStatus.contractOk ? 'success' : 'danger',
      focus: 'evidence'
    };
    const commandRow = {
      id: 'system-command-journal',
      label: 'System: command journal',
      state: `${brief.recentActions.length} recent`,
      detail: brief.recentActions.length > 0 ? 'Local actions are being recorded.' : 'No button activity has been recorded in this session.',
      tone: brief.recentActions.length > 0 ? 'success' : 'warn',
      focus: 'comms'
    };
    const evidenceRow = {
      id: 'system-evidence-tail',
      label: 'System: evidence tail',
      state: `${eventRows.length} rows`,
      detail: eventRows.length > 0 ? 'Evidence Stream has selectable rows and staging actions.' : 'No log evidence is available to inspect.',
      tone: eventRows.length > 0 ? 'success' : 'warn',
      focus: 'evidence'
    };
    const subjectRow = {
      id: 'system-selected-subject',
      label: 'System: selected subject',
      state: selectedWorker ? 'worker selected' : selectedCollision ? 'collision selected' : activeFocus,
      detail: selectedWorker
        ? `${selectedWorker.name || selectedWorker.provider || 'worker'} is active in Inspector.`
        : selectedCollision
          ? `${selectedCollision.type || 'collision'} is active in Inspector.`
          : 'No worker or collision context is selected; lane-level actions still work.',
      tone: selectedWorker || selectedCollision ? 'success' : 'info',
      focus: selectedWorker ? 'workers' : selectedCollision ? 'repo' : activeFocus || 'overview'
    };
    const controlRows = DASHBOARD_CONTROL_CONTRACTS.map(control => {
      const focusOk = !control.focus || focusTargets.has(control.focus);
      const previewRoute = control.kind === 'protected-or-preview' && !TOKEN;
      const packetLike = control.kind.includes('packet');
      const proof = proofMap.get(control.id);
      const proofDetail = proof ? ` Recent proof: ${proof.title} (${proof.detail}).` : ' Awaiting live interaction proof in this session.';
      return {
        id: `control-${control.id}`,
        label: `${control.surface}: ${control.action}`,
        state: !focusOk ? 'missing focus' : proof ? 'recent proof' : previewRoute ? 'preview-backed / unproven' : `${control.kind} / unproven`,
        detail: `${control.evidence}${proofDetail}`,
        tone: !focusOk ? 'danger' : proof ? 'success' : 'warn',
        focus: control.focus || 'overview',
        kind: control.kind,
        packetLike,
        provable: true,
        controlId: control.id,
        surface: control.surface,
        action: control.action,
        target: control.target,
        expected: control.expected,
        proof
      };
    });
    const rows = [contractRow, commandRow, evidenceRow, subjectRow, ...controlRows, ...scenarioRows, ...actionRows];
    const riskRows = rows.filter(row => row.tone === 'danger' || row.tone === 'warn');
    const passCount = rows.length - riskRows.length;
    const score = rows.length > 0 ? Math.round((passCount / rows.length) * 100) : 0;
    const packetCount = rows.filter(row => row.packetLike || row.kind?.includes('packet') || row.focus === 'comms').length;
    const focusCount = rows.filter(row => row.focus && row.focus !== 'comms').length;
    const audit = {
      ranAt: new Date().toISOString(),
      rows,
      riskRows,
      score,
      passCount,
      riskCount: riskRows.length,
      controlCount: controlRows.length,
      packetCount,
      focusCount,
      provenCount: controlRows.filter(row => row.proof).length,
      provableCount: controlRows.length,
      unprovenCount: controlRows.filter(row => row.provable && !row.proof).length,
      previewCount: controlRows.filter(row => row.state.includes('preview-backed')).length,
      tone: riskRows.some(row => row.tone === 'danger') ? 'danger' : riskRows.length > 0 ? 'warn' : 'success',
      headline: riskRows.length > 0 ? `${riskRows.length} control risks remain` : 'Controls are wired for this snapshot'
    };
    const auditSummary = summarizeControlAudit(audit);
    return {
      ...audit,
      ...auditSummary
    };
  }, [
    activeFocus,
    brief.recommendedActions,
    brief.recentActions.length,
    brief.scenarios,
    commandJournal,
    eventRows.length,
    selectedCollision,
    selectedWorker,
    sysStatus.contract?.version,
    sysStatus.contractOk,
    sysStatus.streamSequence,
    sysStatus.updateMode
  ]);

  const runControlAudit = () => {
    const nextAudit = createControlAudit();
    setControlAudit(nextAudit);
    setSelectedAuditRowId((nextAudit.riskRows[0] || nextAudit.rows[0])?.id || '');
    setReviewedAuditRowIds([]);
    onCommandEvent('Control audit run', `${nextAudit.score}% coverage / ${nextAudit.riskCount} risks`, nextAudit.tone, { controlId: 'intelligence-audit' });
    return nextAudit;
  };

  const buildRenderedButtonSweep = () => {
    const ranAt = new Date().toISOString();
    if (typeof document === 'undefined') {
      return {
        ranAt,
        total: 0,
        issueCount: 1,
        disabledCount: 0,
        sectionCount: 0,
        tone: 'danger',
        issues: [{ label: 'Document unavailable', issue: 'rendered DOM could not be inspected', section: 'Runtime', size: '0x0' }],
        disabled: [],
        sections: []
      };
    }

    const clientWidth = document.documentElement.clientWidth || window.innerWidth || 0;
    const oversizedWidthThreshold = Math.min(960, Math.max(760, clientWidth - 96));
    const visible = element => {
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const sectionTitle = element => {
      if (element.closest?.('.nav-rail')) return 'Navigation rail';
      if (element.closest?.('.command-bar')) return 'Header status strip';
      let parent = element;
      while (parent && parent !== document.body) {
        const title = parent.querySelector?.('h1,h2,h3,.panel-titlebar h2,.lane-head strong,.mission-copy h1');
        if (title?.textContent?.trim()) {
          return title.textContent.trim().replace(/\s+/g, ' ').slice(0, 80);
        }
        parent = parent.parentElement;
      }
      return 'Dashboard';
    };
    const buttons = [...document.querySelectorAll('button')].filter(visible).map((button, index) => {
      const rect = button.getBoundingClientRect();
      const text = button.textContent.trim().replace(/\s+/g, ' ');
      const label = String(button.getAttribute('aria-label') || text || button.getAttribute('title') || '').trim();
      const disabledReason = (button.getAttribute('data-disabled-reason') || '').trim();
      const controlIds = [
        ...normalizeControlIdList(button.getAttribute('data-control-id')),
        ...normalizeControlIdList(button.getAttribute('data-control-ids'))
      ];
      return {
        index,
        label: label || '',
        text: text || '',
        section: sectionTitle(button),
        controlIds,
        disabled: button.disabled || button.getAttribute('aria-disabled') === 'true',
        disabledReason,
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        right: Math.round(rect.right)
      };
    });

    const sections = [...buttons.reduce((nextMap, button) => {
      const current = nextMap.get(button.section) || { section: button.section, total: 0, disabled: 0 };
      current.total += 1;
      current.disabled += button.disabled ? 1 : 0;
      nextMap.set(button.section, current);
      return nextMap;
    }, new Map()).values()].sort((left, right) => right.total - left.total);

    const issues = buttons.flatMap(button => {
      const flags = [];
      if (!button.label) flags.push('missing accessible label');
      if (button.disabled && !button.disabledReason) flags.push('disabled control missing reason');
      if (button.height > 240 || button.width > oversizedWidthThreshold) flags.push(`oversized hitbox ${button.width}x${button.height}`);
      if (!button.disabled && (button.width < 28 || button.height < 28)) flags.push(`tiny hitbox ${button.width}x${button.height}`);
      if (button.right > clientWidth + 1) flags.push(`overflows viewport by ${button.right - clientWidth}px`);
      return flags.length ? [{
        label: button.label || button.text || `button ${button.index + 1}`,
        section: button.section,
        issue: flags.join('; '),
        size: `${button.width}x${button.height}`
      }] : [];
    });
    const disabled = buttons
      .filter(button => button.disabled)
      .map(button => ({
        label: button.label || button.text || `button ${button.index + 1}`,
        section: button.section,
        reason: button.disabledReason || 'MISSING data-disabled-reason: explain the prerequisite state.',
        size: `${button.width}x${button.height}`
      }));
    const unlinkedButtons = buttons
      .filter(button => button.controlIds.length === 0)
      .map(button => ({
        label: button.label || button.text || `button ${button.index + 1}`,
        section: button.section,
        size: `${button.width}x${button.height}`
      }));
    const taggedControlIds = new Set(buttons.flatMap(button => button.controlIds));
    const taggedControls = DASHBOARD_CONTROL_CONTRACTS
      .filter(control => taggedControlIds.has(control.id))
      .map(control => ({ id: control.id, surface: control.surface, action: control.action, focus: control.focus }));
    const untaggedControls = DASHBOARD_CONTROL_CONTRACTS
      .filter(control => !taggedControlIds.has(control.id))
      .map(control => ({ id: control.id, surface: control.surface, action: control.action, focus: control.focus }));
    const taggedControlCount = taggedControls.length;
    const contractControlCount = DASHBOARD_CONTROL_CONTRACTS.length;
    const contractCoveragePercent = contractControlCount > 0
      ? Math.round((taggedControlCount / contractControlCount) * 100)
      : 0;

    return {
      ranAt,
      total: buttons.length,
      issueCount: issues.length,
      disabledCount: disabled.length,
      sectionCount: sections.length,
      controlLinkedButtonCount: buttons.length - unlinkedButtons.length,
      unlinkedButtonCount: unlinkedButtons.length,
      contractControlCount,
      taggedControlCount,
      untaggedControlCount: untaggedControls.length,
      contractCoveragePercent,
      tone: issues.length > 0 ? 'danger' : untaggedControls.length > 0 || unlinkedButtons.length > 0 || buttons.length === 0 ? 'warn' : 'success',
      issues: issues.slice(0, 12),
      disabled: disabled.slice(0, 8),
      unlinkedButtons: unlinkedButtons.slice(0, 12),
      sections: sections.slice(0, 8),
      taggedControls,
      untaggedControls
    };
  };

  const runButtonSweep = () => {
    const nextSweep = buildRenderedButtonSweep();
    setButtonSweep(nextSweep);
    onCommandEvent(
      'Button sweep run',
      `${nextSweep.total} rendered buttons / ${nextSweep.issueCount} button risks / ${nextSweep.taggedControlCount}/${nextSweep.contractControlCount} tagged controls`,
      nextSweep.tone,
      { controlId: 'button-sweep' }
    );
    return nextSweep;
  };

  const openButtonSweepAudit = () => {
    const nextSweep = buttonSweep || runButtonSweep();
    const audit = controlAudit || runControlAudit();
    setMode('audit');
    setAuditFilter(nextSweep.issueCount > 0 ? 'risks' : 'proof');
    setSelectedAuditRowId((audit.riskRows[0] || audit.rows.find(row => row.controlId === 'button-sweep') || audit.rows[0])?.id || '');
    onCommandEvent(
      'Button sweep audit opened',
      `${nextSweep.total} rendered buttons / ${audit.unprovenCount} unproven controls`,
      nextSweep.tone,
      { controlId: 'button-sweep' }
    );
  };

  const stageButtonSweep = () => {
    const sweep = buttonSweep || runButtonSweep();
    const packet = [
      '# Dashboard Button Sweep',
      '',
      `- ran_at: ${sweep.ranAt}`,
      `- rendered_buttons: ${sweep.total}`,
      `- button_risks: ${sweep.issueCount}`,
      `- disabled_buttons: ${sweep.disabledCount}`,
      `- sections_seen: ${sweep.sectionCount}`,
      `- control_linked_buttons: ${sweep.controlLinkedButtonCount}/${sweep.total}`,
      `- unlinked_buttons: ${sweep.unlinkedButtonCount}`,
      `- tagged_controls: ${sweep.taggedControlCount}/${sweep.contractControlCount}`,
      `- missing_control_tags: ${sweep.untaggedControlCount ? sweep.untaggedControls.map(row => row.id).join(', ') : 'none'}`,
      `- active_focus: ${activeFocus || 'overview'}`,
      '',
      '## Button Risks',
      ...(sweep.issues.length
        ? sweep.issues.map(row => `- ${row.section}: ${row.label} / ${row.issue} / ${row.size}`)
        : ['- No missing labels, missing disabled reasons, oversized hitboxes, tiny active controls, or viewport overflow detected.']),
      '',
      '## Disabled Controls',
      ...(sweep.disabled.length
        ? sweep.disabled.map(row => `- ${row.section}: ${row.label} / ${row.reason} / ${row.size}`)
        : ['- No disabled controls in the current rendered snapshot.']),
      '',
      '## Unlinked Buttons',
      ...(sweep.unlinkedButtons.length
        ? sweep.unlinkedButtons.map(row => `- ${row.section}: ${row.label} / ${row.size}`)
        : ['- Every visible button is linked to a dashboard control id.']),
      '',
      '## Section Coverage',
      ...(sweep.sections.length
        ? sweep.sections.map(row => `- ${row.section}: ${row.total} buttons, ${row.disabled} disabled`)
        : ['- No visible button sections measured.']),
      '',
      '## Control Contract Coverage',
      `- coverage: ${sweep.contractCoveragePercent}%`,
      ...(sweep.untaggedControls.length
        ? sweep.untaggedControls.map(row => `- MISSING / ${row.id} / ${row.surface} / ${row.action}`)
        : ['- All tracked dashboard controls have rendered data-control-id targets.']),
      '',
      '## Operator Intent',
      'Use this as rendered button-health proof. Contract audits prove intended wiring; this sweep proves the browser surface has usable labels, hitboxes, and viewport fit.'
    ].join('\n');
    onStagePacket(packet, 'Button sweep staged', { controlId: 'button-sweep' });
  };

  const buildBreakTestReport = (statusOverride = sysStatus) => {
    const reportStatus = statusOverride || sysStatus || DEFAULT_STATUS;
    const sweep = buildRenderedButtonSweep();
    const audit = createControlAudit();
    const sync = reportStatus.cloudSync || DEFAULT_STATUS.cloudSync;
    const syncGate = buildLocalSyncGate(sync);
    const syncDiagnosis = summarizeCloudSyncGate(sync);
    const statusLoaded = dashboardStatusHasSample(reportStatus);
    const statusPending = !statusLoaded && reportStatus.updateMode === 'connecting';
    const statusOffline = !statusPending && !reportStatus.online;
    const modelReady = !!(reportStatus.antigravityCli?.ready || reportStatus.geminiCli?.ready);
    const modelInstalled = !!(reportStatus.antigravityCli?.installed || reportStatus.geminiCli?.installed);
    const latestCommsRow = commandJournal.find(row => (
      row.title === 'Comms failed'
      || row.title === 'Comms degraded'
      || row.title === 'Comms response received'
    ));
    const latestLocalPacketIntelligenceRow = commandJournal.find(isLocalPacketIntelligenceCommand);
    const disabledReasonDebt = [
      ...sweep.issues.filter(row => String(row.issue || '').includes('disabled control missing reason')),
      ...sweep.disabled.filter(row => String(row.reason || '').startsWith('MISSING'))
    ].length;
    const missingControlTarget = sweep.untaggedControls[0];
    const nextControlTarget = audit.rows.find(row => row.provable && !row.proof) || audit.riskRows[0] || audit.rows[0];
    const rows = [
      {
        id: 'rendered-buttons',
        label: 'Rendered button surface',
        state: sweep.total === 0 ? 'fail' : sweep.issueCount > 0 ? 'fail' : 'pass',
        tone: sweep.total === 0 || sweep.issueCount > 0 ? 'danger' : 'success',
        focus: 'overview',
        mode: 'diagnose',
        detail: `${sweep.total} visible buttons, ${sweep.issueCount} rendered button risks, ${sweep.disabledCount} disabled.`,
        action: sweep.issueCount > 0 ? 'Repair the Button Sweep issues before claiming the UI is usable.' : 'Keep Button Sweep as browser-surface proof.'
      },
      {
        id: 'control-dom-coverage',
        label: 'Control DOM coverage',
        state: sweep.untaggedControlCount === 0 ? 'pass' : 'warn',
        tone: sweep.untaggedControlCount === 0 ? 'success' : 'warn',
        focus: missingControlTarget?.focus || 'overview',
        mode: 'diagnose',
        detail: `${sweep.taggedControlCount}/${sweep.contractControlCount} tracked controls have rendered data-control-id targets.`,
        action: missingControlTarget
          ? `Tag or expose a rendered target for ${missingControlTarget.id}: ${missingControlTarget.action}.`
          : 'Every tracked control contract has a rendered target tag.'
      },
      {
        id: 'disabled-reasons',
        label: 'Disabled-control explanations',
        state: disabledReasonDebt > 0 ? 'fail' : 'pass',
        tone: disabledReasonDebt > 0 ? 'danger' : 'success',
        focus: 'overview',
        mode: 'diagnose',
        detail: disabledReasonDebt > 0
          ? `${disabledReasonDebt} disabled controls are missing operator-facing reasons.`
          : `${sweep.disabledCount} disabled controls expose a reason.`,
        action: disabledReasonDebt > 0 ? 'Add data-disabled-reason or enable the blocked control.' : 'Disabled controls explain their prerequisites.'
      },
      {
        id: 'control-proof',
        label: 'Explicit control proof',
        state: audit.unprovenCount === 0 ? 'pass' : audit.provenCount === 0 ? 'fail' : 'warn',
        tone: audit.unprovenCount === 0 ? 'success' : audit.provenCount === 0 ? 'danger' : 'warn',
        focus: 'overview',
        mode: 'audit',
        auditFilter: 'proof',
        auditRowId: nextControlTarget?.id,
        detail: `${audit.provenCount}/${audit.provableCount} tracked controls have explicit proof; ${audit.unprovenCount} remain.`,
        action: nextControlTarget ? `Open and press: ${nextControlTarget.target || nextControlTarget.label}` : 'No control-proof debt remains.'
      },
      {
        id: 'sync-gate',
        label: 'Cloud sync gate',
        state: statusPending ? 'wait' : statusOffline ? 'fail' : syncGate.blockers.length > 0 ? 'fail' : syncGate.warnings.length > 0 ? 'warn' : 'pass',
        tone: statusPending ? 'warn' : statusOffline || syncGate.blockers.length > 0 ? 'danger' : syncGate.warnings.length > 0 ? 'warn' : 'success',
        focus: 'sync',
        mode: 'plan',
        detail: statusPending
          ? 'Waiting for the first dashboard status sample; sync gate has not been measured yet.'
          : statusOffline
            ? 'Dashboard status is offline; sync gate cannot be trusted.'
            : syncGate.blockers.length > 0
              ? syncDiagnosis.detail
              : syncGate.warnings.length > 0
                ? syncDiagnosis.detail
                : syncDiagnosis.detail || `${cloudSyncLabel(sync)} with no local blocker.`,
        action: statusPending
          ? 'Wait for the first status sample, then rerun Break Test.'
          : statusOffline || syncGate.blockers.length > 0
            ? syncDiagnosis.action
            : syncDiagnosis.action,
        exitCriteria: syncDiagnosis.exitCriteria,
        packetLines: syncDiagnosis.packetLines
      },
      {
        id: 'evidence-health',
        label: 'Evidence stream health',
        state: errorEventCount > 0
          ? evidenceIssuesReviewed ? 'warn' : 'fail'
          : warningEventCount > 0
            ? evidenceIssuesReviewed ? 'pass' : 'warn'
            : eventRows.length === 0 ? 'warn' : 'pass',
        tone: errorEventCount > 0
          ? evidenceIssuesReviewed ? 'warn' : 'danger'
          : warningEventCount > 0
            ? evidenceIssuesReviewed ? 'success' : 'warn'
            : eventRows.length === 0 ? 'warn' : 'success',
        focus: 'evidence',
        mode: 'evidence',
        detail: evidenceIssuesReviewed
          ? `${eventRows.length} evidence rows, ${warningEventCount} warnings, ${errorEventCount} errors. Current issue window staged at ${formatTimestamp(latestEvidenceWindowReview.time)}.`
          : `${eventRows.length} evidence rows, ${warningEventCount} warnings, ${errorEventCount} errors.`,
        action: errorEventCount > 0
          ? evidenceIssuesReviewed ? 'Errors remain; use the staged evidence window in Comms review or wait for a new log window.' : 'Open Evidence and stage the newest error window.'
          : warningEventCount > 0
            ? evidenceIssuesReviewed ? 'Current warning window is staged; rerun after new logs arrive.' : 'Stage warning evidence before health claims.'
            : 'Evidence stream supports the current state.'
      },
      {
        id: 'model-lane',
        label: 'Model alliance lane',
        state: statusPending ? 'wait' : modelReady ? 'pass' : modelInstalled ? 'warn' : 'fail',
        tone: statusPending ? 'warn' : modelReady ? 'success' : modelInstalled ? 'warn' : 'danger',
        focus: 'alliance',
        mode: 'plan',
        detail: statusPending
          ? 'Waiting for the first dashboard status sample; model readiness has not been measured yet.'
          : reportStatus.antigravityCli?.ready
          ? `Antigravity ready with ${reportStatus.antigravityCli.model_count || 0} models.`
          : reportStatus.geminiCli?.ready
            ? `Gemini CLI ready${reportStatus.geminiCli.version ? ` at ${reportStatus.geminiCli.version}` : ''}.`
            : modelInstalled
              ? 'A model lane is installed but not ready.'
              : 'No local model lane is proven ready.',
        action: statusPending ? 'Wait for the first status sample, then rerun Break Test.' : modelReady ? 'Use the ready model lane with bounded packets.' : 'Open Alliance and stage the model-lane blocker.'
      },
      {
        id: 'contract-stream',
        label: 'Status contract stream',
        state: statusPending ? 'wait' : reportStatus.contractOk && reportStatus.updateMode === 'sse' ? 'pass' : reportStatus.contractOk ? 'warn' : 'fail',
        tone: statusPending ? 'warn' : reportStatus.contractOk && reportStatus.updateMode === 'sse' ? 'success' : reportStatus.contractOk ? 'warn' : 'danger',
        focus: 'evidence',
        mode: 'evidence',
        detail: statusPending
          ? 'Waiting for the first dashboard status sample.'
          : `${reportStatus.contractOk ? `v${reportStatus.contract?.version || 0}` : 'contract drift'} over ${reportStatus.updateMode || 'unknown'} transport.`,
        action: statusPending ? 'Wait for the first status sample, then rerun Break Test.' : reportStatus.contractOk ? 'Keep stream state in the evidence ledger.' : 'Do not trust dashboard state until the contract is restored.'
      },
      {
        id: 'local-packet-intelligence',
        label: 'Local packet intelligence',
        state: latestLocalPacketIntelligenceRow ? 'pass' : 'warn',
        tone: latestLocalPacketIntelligenceRow ? 'success' : 'warn',
        focus: 'comms',
        mode: 'evidence',
        detail: latestLocalPacketIntelligenceRow
          ? `${latestLocalPacketIntelligenceRow.title}: ${latestLocalPacketIntelligenceRow.detail}`
          : 'No local packet-intelligence proof has been recorded in this session.',
        action: latestLocalPacketIntelligenceRow
          ? 'Use this as bounded local review evidence; real model-loop proof remains separate.'
          : 'Open Comms and run Local Review on a staged packet before claiming local reasoning support.'
      },
      {
        id: 'comms-loop',
        label: 'Comms model loop honesty',
        state: !latestCommsRow ? 'warn' : latestCommsRow.title === 'Comms response received' ? 'pass' : 'fail',
        tone: !latestCommsRow ? 'warn' : latestCommsRow.title === 'Comms response received' ? 'success' : 'danger',
        focus: 'comms',
        mode: 'evidence',
        detail: latestCommsRow ? `${latestCommsRow.title}: ${latestCommsRow.detail}` : 'No Comms response proof has been recorded in this session.',
        action: latestCommsRow?.title === 'Comms response received'
          ? 'Use Comms as supporting evidence.'
          : 'Open Comms and press Probe Model; keep degraded/offline responses visibly marked.'
      }
    ];
    const toneRank = { danger: 0, warn: 1, info: 2, success: 3 };
    const sortedRows = [...rows].sort((left, right) => (
      (toneRank[left.tone] ?? 4) - (toneRank[right.tone] ?? 4)
      || left.label.localeCompare(right.label)
    ));
    const failCount = rows.filter(row => row.tone === 'danger').length;
    const warnCount = rows.filter(row => row.tone === 'warn').length;
    const passCount = rows.filter(row => row.tone === 'success').length;
    const score = clampPercent(100 - failCount * 14 - warnCount * 7);
    const weakestRow = sortedRows.find(row => row.tone === 'danger') || sortedRows.find(row => row.tone === 'warn') || sortedRows[0];
    return {
      ranAt: new Date().toISOString(),
      score,
      failCount,
      warnCount,
      passCount,
      rowCount: rows.length,
      tone: failCount > 0 ? 'danger' : warnCount > 0 ? 'warn' : 'success',
      headline: failCount > 0 ? `${failCount} adversarial checks failed` : warnCount > 0 ? `${warnCount} checks need review` : 'Break test passed this snapshot',
      weakestRow,
      rows: sortedRows,
      buttonSweep: sweep,
      audit
    };
  };

  const ensureFreshBreakTestStatus = async () => {
    if (!dashboardStatusNeedsRefresh(sysStatus) || typeof onRefreshStatus !== 'function') {
      return sysStatus;
    }
    onCommandEvent(
      'Break test status refresh',
      'Fetching current dashboard status before scoring.',
      'info',
      { controlId: 'break-test-lab' }
    );
    const refreshedStatus = await onRefreshStatus('break-test');
    return refreshedStatus || sysStatus;
  };

  const runBreakTest = async () => {
    const statusForReport = await ensureFreshBreakTestStatus();
    const report = buildBreakTestReport(statusForReport);
    setBreakTest(report);
    setButtonSweep(report.buttonSweep);
    setControlAudit(report.audit);
    setSelectedAuditRowId(report.weakestRow?.auditRowId || (report.audit.riskRows[0] || report.audit.rows[0])?.id || '');
    onCommandEvent(
      'Break test run',
      `${report.score}% resilience / ${report.failCount} failures / ${report.warnCount} warnings`,
      report.tone,
      { controlId: 'break-test-lab' }
    );
    return report;
  };

  const ensureBreakTestReport = async () => {
    if (breakTest && !breakTestReportNeedsStatusRefresh(breakTest)) return breakTest;
    return runBreakTest();
  };

  const openBreakTestWeakest = async () => {
    const report = await ensureBreakTestReport();
    const target = report.weakestRow;
    if (!target) return;
    if (target.mode) setMode(target.mode);
    if (target.auditFilter) setAuditFilter(target.auditFilter);
    if (target.auditRowId) setSelectedAuditRowId(target.auditRowId);
    if (target.focus) onFocusChange(target.focus);
    onCommandEvent(
      'Break test weakest opened',
      `${target.label} -> ${target.focus || 'overview'}`,
      target.tone || 'info',
      { controlId: 'break-test-lab' }
    );
  };

  const openRemediationRow = async row => {
    const report = await ensureBreakTestReport();
    const target = row || buildRemediationRows(report)[0];
    if (!target) return;
    if (target.mode) setMode(target.mode);
    if (target.auditFilter) setAuditFilter(target.auditFilter);
    if (target.auditRowId) setSelectedAuditRowId(target.auditRowId);
    if (target.focus) onFocusChange(target.focus);
    onCommandEvent(
      'Remediation target opened',
      `${target.priority || 'P2'} ${target.label} -> ${target.focus || 'overview'}`,
      target.tone || 'warn',
      { controlId: 'break-test-lab' }
    );
  };

  const stageRemediationQueue = async () => {
    const report = await ensureBreakTestReport();
    const rows = buildRemediationRows(report);
    const packet = [
      '# Dashboard Remediation Queue',
      '',
      `- source: Break Test Lab`,
      `- ran_at: ${report.ranAt}`,
      `- score: ${report.score}`,
      `- failures: ${report.failCount}`,
      `- warnings: ${report.warnCount}`,
      `- remediation_targets: ${rows.length}`,
      `- active_focus: ${activeFocus || 'overview'}`,
      `- protected_routes_called: no`,
      `- chat_send_called: no`,
      '',
      '## Ranked Targets',
      ...(rows.length
        ? rows.map(row => `- ${row.priority} / ${row.label} / owner ${row.owner} / state ${row.state} / focus ${row.focus || 'overview'} / detail: ${row.detail} / next: ${row.action} / exit: ${row.exitCriteria}`)
        : ['- No remediation rows remain in the latest break test.']),
      '',
      '## Current Gate Trace',
      ...brief.decisionTrace.map(row => `- ${row.label}: ${row.detail}`),
      '',
      '## Operator Intent',
      'Use this queue to repair dashboard readiness one gate at a time. Open the target lane, gather evidence, rerun Break Test, and keep protected routes/manual live work gated until the exit criteria pass.'
    ].join('\n');
    onStagePacket(packet, 'Remediation queue staged', { controlId: 'break-test-lab' });
  };

  const stageBreakTest = async () => {
    const report = await ensureBreakTestReport();
    const packet = [
      '# Dashboard Break Test',
      '',
      `- ran_at: ${report.ranAt}`,
      `- score: ${report.score}`,
      `- failures: ${report.failCount}`,
      `- warnings: ${report.warnCount}`,
      `- passes: ${report.passCount}/${report.rowCount}`,
      `- weakest_check: ${report.weakestRow?.label || 'none'}`,
      `- weakest_action: ${report.weakestRow?.action || 'none'}`,
      `- active_focus: ${activeFocus || 'overview'}`,
      '',
      '## Adversarial Checks',
      ...report.rows.map(row => `- ${row.tone.toUpperCase()} / ${row.label} / ${row.state} / ${row.detail} / next: ${row.action}`),
      ...report.rows.flatMap(row => (Array.isArray(row.packetLines) && row.packetLines.length
        ? [`  - ${row.label} trace: ${row.packetLines.join(' | ')}`]
        : [])),
      '',
      '## Rendered Button Probe',
      `- rendered_buttons: ${report.buttonSweep.total}`,
      `- button_risks: ${report.buttonSweep.issueCount}`,
      `- disabled_buttons: ${report.buttonSweep.disabledCount}`,
      `- sections_seen: ${report.buttonSweep.sectionCount}`,
      `- tagged_controls: ${report.buttonSweep.taggedControlCount}/${report.buttonSweep.contractControlCount}`,
      `- missing_control_tags: ${report.buttonSweep.untaggedControlCount ? report.buttonSweep.untaggedControls.map(row => row.id).join(', ') : 'none'}`,
      '',
      '## Control Proof Probe',
      `- interaction_proof: ${report.audit.provenCount}/${report.audit.provableCount}`,
      `- unproven_controls: ${report.audit.unprovenCount}`,
      `- audit_risks: ${report.audit.riskCount}`,
      '',
      '## Gate Trace',
      ...brief.decisionTrace.map(row => `- ${row.label}: ${row.detail}`),
      '',
      '## Operator Intent',
      'Use this packet as adversarial dashboard QA. A ready claim should survive these checks with no danger rows and explained warning rows.'
    ].join('\n');
    onStagePacket(packet, 'Break test staged', { controlId: 'break-test-lab' });
  };

  const buildLocalPacketReviewArtifact = (sourcePacket, sourceTitle = 'Dashboard packet') => {
    const verdict = buildPacketIntelligence(sourcePacket, sourceTitle);
    const packet = [
      '# Local Remediation Packet Review',
      '',
      `- source_packet: ${sourceTitle}`,
      `- score: ${verdict.score}`,
      `- tone: ${verdict.tone}`,
      `- recommended_focus: ${verdict.focus}`,
      `- blockers_detected: ${verdict.blockers.length}`,
      `- missing_signals: ${verdict.missingSignals.length ? verdict.missingSignals.join(', ') : 'none'}`,
      '- protected_routes_called: no',
      '- chat_send_called: no',
      '- publish_or_dispatch_called: no',
      '',
      '## Verdict',
      verdict.verdict,
      '',
      '## Next Safe Action',
      verdict.nextAction,
      '',
      '## Local Verdict Packet',
      verdict.verdictPacket,
      '',
      '## Packet Under Review',
      sourcePacket
    ].join('\n');
    return { verdict, packet };
  };

  const remediationActionIdsForTarget = target => {
    const actionIds = new Set(REMEDIATION_SAFE_ACTION_IDS[target?.id] || []);
    if (target?.id === 'control-proof') {
      return [...actionIds];
    }
    return [...actionIds];
  };

  const runSafeDashboardAction = async (action, controlById, options = {}) => {
    const control = controlById.get(action.id);
    try {
      const result = await action.run(options);
      const explicitTone = ['success', 'warn', 'danger', 'info'].includes(result?.tone) ? result.tone : '';
      const resultTone = explicitTone || toneForActionStatus(result);
      const proofTone = action.source === 'local-panel-action' && resultTone === 'danger' ? 'warn' : resultTone;
      const tone = action.id === 'bridge-probe'
        || action.source === 'local-preview-builder'
        || action.source === 'local-panel-action'
        || action.source === 'local-comms-review'
        ? proofTone
        : proofTone === 'info' ? 'warn' : proofTone;
      return {
        result,
        row: {
          id: action.id,
          label: action.label,
          state: tone === 'danger'
            ? 'failed'
            : tone === 'success'
              ? 'exercised'
              : tone === 'warn'
                ? 'exercised_with_warnings'
                : 'observed_without_proof',
          tone,
          source: action.source || 'local-dashboard-controller',
          expected: control?.expected || 'Local dashboard state updates and command journal records proof.',
          observed: action.summarize ? action.summarize(result) : 'Control handler returned without throwing and emitted its own proof event.',
          focus: control?.focus || 'overview'
        }
      };
    } catch (error) {
      return {
        result: null,
        row: {
          id: action.id,
          label: action.label,
          state: 'failed',
          tone: 'danger',
          source: action.source || 'local-dashboard-controller',
          expected: String(error?.message || error),
          observed: 'The handler threw before the proof event could be trusted.',
          focus: control?.focus || 'overview'
        }
      };
    }
  };

  const runRemediationSafeStep = async (row = null) => {
    const report = await ensureBreakTestReport();
    const target = row || buildRemediationRows(report)[0];
    if (!target) {
      const emptyRun = {
        ranAt: new Date().toISOString(),
        targetLabel: 'No remediation target',
        targetId: 'none',
        targetPriority: 'P0',
        targetFocus: 'overview',
        rows: [],
        totalCount: 0,
        successCount: 0,
        warningCount: 0,
        failureCount: 0,
        reviewedPacketCount: 0,
        tone: 'success',
        nextAction: 'No safe remediation step is needed for the latest Break Test.'
      };
      setRemediationRun(emptyRun);
      onCommandEvent('Remediation safe step skipped', 'No remediation rows remain in the latest Break Test.', 'success', { controlId: 'break-test-lab' });
      return emptyRun;
    }

    const controlById = new Map(DASHBOARD_CONTROL_CONTRACTS.map(control => [control.id, control]));
    const safeActions = buildRemediationSafeActions();
    const safeActionById = new Map(safeActions.map(action => [action.id, action]));
    const actions = remediationActionIdsForTarget(target)
      .map(actionId => safeActionById.get(actionId))
      .filter(Boolean);

    if (actions.length === 0) {
      const gatedRun = {
        ranAt: new Date().toISOString(),
        targetLabel: target.label,
        targetId: target.id,
        targetPriority: target.priority || 'P2',
        targetFocus: target.focus || 'overview',
        rows: [{
          id: target.id,
          label: target.label,
          state: 'manual_required',
          tone: 'warn',
          source: 'remediation-router',
          expected: target.action,
          observed: 'No safe local automation is mapped for this remediation row.',
          focus: target.focus || 'overview'
        }],
        totalCount: 1,
        successCount: 0,
        warningCount: 1,
        failureCount: 0,
        reviewedPacketCount: 0,
        tone: 'warn',
        nextAction: target.action
      };
      setRemediationRun(gatedRun);
      await openRemediationRow(target);
      onCommandEvent('Remediation safe step gated', `${target.label} needs manual review`, 'warn', { controlId: 'break-test-lab' });
      return gatedRun;
    }

    const rows = [];
    let reviewedPacketCount = 0;
    for (const action of actions) {
      const { row: actionRow, result } = await runSafeDashboardAction(action, controlById);
      rows.push(actionRow);
      if (result?.packet) {
        const { verdict, packet } = buildLocalPacketReviewArtifact(
          result.packet,
          result.packetTitle || result.detail || action.label
        );
        onStagePacket(packet, `${action.label} packet intelligence staged`, { controlId: 'break-test-lab' });
        reviewedPacketCount += 1;
        rows.push({
          id: `${action.id}-packet-review`,
          label: `${action.label} packet intelligence`,
          state: `${verdict.score}% / ${verdict.focus}`,
          tone: verdict.tone,
          source: 'local-packet-intelligence',
          expected: 'Generate a local verdict from the packet that the safe action just staged.',
          observed: `${verdict.verdict} Next: ${verdict.nextAction}`,
          focus: verdict.focus || actionRow.focus
        });
      }
    }

    const failureCount = rows.filter(item => item.tone === 'danger').length;
    const warningCount = rows.filter(item => item.tone === 'warn').length;
    const successCount = rows.length - failureCount;
    const run = {
      ranAt: new Date().toISOString(),
      targetLabel: target.label,
      targetId: target.id,
      targetPriority: target.priority || 'P2',
      targetFocus: target.focus || 'overview',
      targetAction: target.action,
      targetExitCriteria: target.exitCriteria,
      rows,
      totalCount: rows.length,
      successCount,
      warningCount,
      failureCount,
      reviewedPacketCount,
      tone: failureCount > 0 ? 'danger' : warningCount > 0 ? 'warn' : 'success',
      nextAction: 'Rerun Break Test after React records the staged proof and review packet.'
    };
    setRemediationRun(run);
    scheduleRemediationReceiptScroll();
    if (target.focus) onFocusChange(target.focus, { controlId: 'break-test-lab' });
    onCommandEvent(
      'Remediation safe step run',
      `${target.label}: ${successCount}/${rows.length} safe steps; ${reviewedPacketCount} packet reviews`,
      run.tone,
      { controlId: 'break-test-lab' }
    );
    return run;
  };

  const runRemediationSafePlan = async () => {
    const report = await ensureBreakTestReport();
    const targets = buildRemediationRows(report);
    if (targets.length === 0) {
      const emptyRun = {
        ranAt: new Date().toISOString(),
        targetLabel: 'No remediation plan',
        targetId: 'safe-plan',
        targetPriority: 'P0',
        targetFocus: 'overview',
        targetCount: 0,
        automatedTargetCount: 0,
        gatedTargetCount: 0,
        rows: [],
        totalCount: 0,
        successCount: 0,
        warningCount: 0,
        failureCount: 0,
        reviewedPacketCount: 0,
        tone: 'success',
        nextAction: 'No safe remediation plan is needed for the latest Break Test.'
      };
      setRemediationRun(emptyRun);
      onCommandEvent('Remediation safe plan skipped', 'No remediation rows remain in the latest Break Test.', 'success', { controlId: 'break-test-lab' });
      return emptyRun;
    }

    const controlById = new Map(DASHBOARD_CONTROL_CONTRACTS.map(control => [control.id, control]));
    const safeActions = buildRemediationSafeActions();
    const safeActionById = new Map(safeActions.map(action => [action.id, action]));
    const rows = [];
    let reviewedPacketCount = 0;
    let automatedTargetCount = 0;
    let gatedTargetCount = 0;

    for (const target of targets) {
      const actions = remediationActionIdsForTarget(target)
        .map(actionId => safeActionById.get(actionId))
        .filter(Boolean);

      if (actions.length === 0) {
        gatedTargetCount += 1;
        rows.push({
          id: `${target.id}-manual`,
          label: target.label,
          state: 'manual_required',
          tone: 'warn',
          source: 'remediation-router',
          expected: target.action,
          observed: 'No safe local automation is mapped for this remediation row.',
          focus: target.focus || 'overview'
        });
        continue;
      }

      automatedTargetCount += 1;
      for (const action of actions) {
        const { row: actionRow, result } = await runSafeDashboardAction(action, controlById, { keepFocus: true });
        rows.push({
          ...actionRow,
          id: `${target.id}-${actionRow.id}`,
          label: `${target.label}: ${actionRow.label}`,
          expected: `${target.exitCriteria || target.action} ${actionRow.expected || ''}`.trim()
        });
        if (result?.packet) {
          const { verdict, packet } = buildLocalPacketReviewArtifact(
            result.packet,
            result.packetTitle || result.detail || action.label
          );
          onStagePacket(packet, `${action.label} packet intelligence staged`, { controlId: 'break-test-lab', keepFocus: true });
          reviewedPacketCount += 1;
          rows.push({
            id: `${target.id}-${action.id}-packet-review`,
            label: `${target.label}: packet intelligence`,
            state: `${verdict.score}% / ${verdict.focus}`,
            tone: verdict.tone,
            source: 'local-packet-intelligence',
            expected: 'Generate a local verdict from the packet that the safe plan just staged.',
            observed: `${verdict.verdict} Next: ${verdict.nextAction}`,
            focus: verdict.focus || target.focus || 'overview'
          });
        }
      }
    }

    const failureCount = rows.filter(item => item.tone === 'danger').length;
    const warningCount = rows.filter(item => item.tone === 'warn').length;
    const successCount = rows.length - failureCount;
    const run = {
      ranAt: new Date().toISOString(),
      targetLabel: `${automatedTargetCount}/${targets.length} targets sampled`,
      targetId: 'safe-plan',
      targetPriority: failureCount > 0 ? 'P1' : warningCount > 0 ? 'P2' : 'P0',
      targetFocus: targets[0]?.focus || 'overview',
      targetAction: 'Run safe local steps for every mapped Break Test remediation row.',
      targetExitCriteria: 'Rerun Break Test after the safe plan records local proof, staged evidence, and packet-intelligence reviews.',
      targetCount: targets.length,
      automatedTargetCount,
      gatedTargetCount,
      rows,
      totalCount: rows.length,
      successCount,
      warningCount,
      failureCount,
      reviewedPacketCount,
      tone: failureCount > 0 ? 'danger' : warningCount > 0 ? 'warn' : 'success',
      nextAction: gatedTargetCount > 0
        ? 'Open the manual-gated targets, then rerun Break Test after the safe plan records local proof.'
        : 'Rerun Break Test after React records the safe plan proof and review packets.'
    };
    setRemediationRun(run);
    scheduleRemediationReceiptScroll();
    onCommandEvent(
      'Remediation safe plan run',
      `${automatedTargetCount}/${targets.length} targets sampled; ${successCount}/${rows.length} safe rows; ${reviewedPacketCount} packet reviews`,
      run.tone,
      { controlId: 'break-test-lab' }
    );
    return run;
  };

  const stageRemediationRun = async () => {
    const run = remediationRun || await runRemediationSafeStep();
    const isPlan = run.targetId === 'safe-plan';
    const packet = [
      `# Dashboard Remediation ${isPlan ? 'Safe Plan' : 'Safe Step'}`,
      '',
      `- ran_at: ${run.ranAt}`,
      `- target: ${run.targetLabel}`,
      `- target_id: ${run.targetId}`,
      `- priority: ${run.targetPriority}`,
      `- target_focus: ${run.targetFocus}`,
      `- safe_rows: ${run.successCount}/${run.totalCount}`,
      `- safe_steps: ${run.successCount}/${run.totalCount}`,
      `- targets_sampled: ${run.automatedTargetCount || (isPlan ? 0 : 1)}/${run.targetCount || (isPlan ? 0 : 1)}`,
      `- manual_gates: ${run.gatedTargetCount || 0}`,
      `- warnings: ${run.warningCount}`,
      `- failures: ${run.failureCount}`,
      `- packet_reviews: ${run.reviewedPacketCount}`,
      '- protected_routes_called: no',
      '- chat_send_called: no',
      '- publish_or_dispatch_called: no',
      '',
      '## Safe Step Rows',
      ...(run.rows.length
        ? run.rows.map(item => `- ${item.tone.toUpperCase()} / ${item.id} / ${item.label} / ${item.state} / source: ${item.source} / observed: ${item.observed}`)
        : ['- No remediation rows remain in the latest Break Test.']),
      '',
      '## Exit Criteria',
      `- ${run.targetExitCriteria || run.nextAction}`,
      '',
      '## Next Action',
      run.nextAction
    ].join('\n');
    onStagePacket(packet, isPlan ? 'Remediation safe plan staged' : 'Remediation safe step staged', { controlId: 'break-test-lab' });
  };

  const probeEndpoint = async endpoint => {
    const startedAt = performance.now();
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 6000);
    try {
      const response = await fetch(`${BRIDGE}${endpoint.path}`, {
        cache: 'no-store',
        signal: controller.signal
      });
      let data = {};
      try {
        data = await response.json();
      } catch {
        data = {};
      }
      const latencyMs = Math.round(performance.now() - startedAt);
      const passed = response.ok && endpoint.pass(data);
      return {
        id: endpoint.id,
        label: endpoint.label,
        path: endpoint.path,
        focus: endpoint.focus,
        status: response.status,
        latencyMs,
        state: response.ok ? (passed ? 'pass' : 'review') : 'fail',
        tone: response.ok ? (passed ? 'success' : 'warn') : 'danger',
        detail: response.ok
          ? endpoint.detail(data)
          : `HTTP ${response.status}`,
        action: passed
          ? 'Use this route as current backend evidence.'
          : `Open ${endpoint.focus || 'overview'} and inspect the corresponding dashboard lane.`
      };
    } catch (error) {
      const latencyMs = Math.round(performance.now() - startedAt);
      return {
        id: endpoint.id,
        label: endpoint.label,
        path: endpoint.path,
        focus: endpoint.focus,
        status: 0,
        latencyMs,
        state: 'fail',
        tone: 'danger',
        detail: error?.name === 'AbortError' ? 'Timed out after 6000ms' : String(error?.message || error),
        action: `Open ${endpoint.focus || 'overview'} and verify the bridge route manually.`
      };
    } finally {
      window.clearTimeout(timeoutId);
    }
  };

  const runLiveBridgeProbe = async () => {
    const rows = await Promise.all(BRIDGE_PROBE_ENDPOINTS.map(probeEndpoint));
    const failCount = rows.filter(row => row.tone === 'danger').length;
    const warnCount = rows.filter(row => row.tone === 'warn').length;
    const passCount = rows.filter(row => row.tone === 'success').length;
    const totalCount = rows.length;
    const averageMs = totalCount
      ? Math.round(rows.reduce((sum, row) => sum + row.latencyMs, 0) / totalCount)
      : 0;
    const weakestRow = rows.find(row => row.tone === 'danger')
      || rows.find(row => row.tone === 'warn')
      || rows[0]
      || null;
    const probe = {
      ranAt: new Date().toISOString(),
      rows,
      totalCount,
      passCount,
      warnCount,
      failCount,
      averageMs,
      weakestRow,
      tone: failCount > 0 ? 'danger' : warnCount > 0 ? 'warn' : 'success'
    };
    setBridgeProbe(probe);
    onCommandEvent(
      'Live bridge probe run',
      `${passCount}/${totalCount} routes passed; ${failCount} failed; avg ${averageMs}ms`,
      probe.tone,
      { controlId: 'bridge-probe' }
    );
    const commsReceipt = buildBridgeProbeCommsReceipt(rows.find(row => row.id === 'chat-test'));
    if (commsReceipt) {
      onCommandEvent(
        commsReceipt.title,
        commsReceipt.detail,
        commsReceipt.tone,
        { controlId: commsReceipt.controlId, controlIds: commsReceipt.controlIds }
      );
    }
    return probe;
  };

  const openBridgeProbeWeakest = () => {
    const target = bridgeProbe?.weakestRow;
    if (!target) return;
    if (target.focus === 'evidence') {
      setMode('evidence');
    }
    onFocusChange(target.focus || 'overview', { controlId: 'bridge-probe' });
    onCommandEvent(
      'Live bridge probe weakest opened',
      `${target.label} -> ${target.focus || 'overview'}`,
      target.tone || 'info',
      { controlId: 'bridge-probe' }
    );
  };

  const stageBridgeProbe = async () => {
    const probe = bridgeProbe || await runLiveBridgeProbe();
    const packet = [
      '# Live Bridge Probe',
      '',
      `- ran_at: ${probe.ranAt}`,
      `- bridge_url: ${BRIDGE}`,
      `- routes_passed: ${probe.passCount}/${probe.totalCount}`,
      `- warnings: ${probe.warnCount}`,
      `- failures: ${probe.failCount}`,
      `- average_latency_ms: ${probe.averageMs}`,
      `- protected_routes_called: no`,
      `- mutations_performed: no`,
      '',
      '## Route Results',
      ...probe.rows.map(row => `- ${row.tone.toUpperCase()} / ${row.label} / ${row.path} / HTTP ${row.status} / ${row.latencyMs}ms / ${row.detail}`),
      '',
      '## Weakest Route',
      probe.weakestRow
        ? `- ${probe.weakestRow.label}: ${probe.weakestRow.action}`
        : '- No weakest route found.',
      '',
      '## Operator Intent',
      'Use this as live backend evidence for the dashboard. The probe calls only public local bridge routes and reports compact sanitized fields.'
    ].join('\n');
    onStagePacket(packet, 'Live bridge probe staged', { controlId: 'bridge-probe' });
  };

  const runProofReplay = async () => {
    const report = await ensureBreakTestReport();
    const audit = report.audit;
    const proofMapBefore = buildControlProofMap(commandJournal);
    const observedControlIds = ['button-sweep', 'intelligence-audit', 'break-test-lab', 'nav-rail', 'proof-replay-lab'];
    const replayProofIds = ['proof-replay-lab'];
    const projectedProofIds = new Set([...proofMapBefore.keys(), ...replayProofIds]);
    const newlyProvenCount = replayProofIds.filter(controlId => !proofMapBefore.has(controlId)).length;
    const projectedProvenCount = Math.min(audit.provableCount, audit.provenCount + newlyProvenCount);
    const projectedUnprovenCount = Math.max(0, audit.provableCount - projectedProvenCount);
    const nextControlAfterReplay = DASHBOARD_CONTROL_CONTRACTS.find(control => (
      !projectedProofIds.has(control.id)
    ));
    const nextTarget = audit.rows.find(row => row.controlId === nextControlAfterReplay?.id)
      || audit.rows.find(row => row.provable && !row.proof)
      || audit.riskRows[0]
      || audit.rows[0];
    const rows = [
      {
        controlId: 'button-sweep',
        label: 'Rendered button sweep',
        state: report.buttonSweep.issueCount > 0 ? 'observed risks' : 'observed clean',
        tone: report.buttonSweep.issueCount > 0 ? 'danger' : 'success',
        detail: `${report.buttonSweep.total} visible buttons measured; press Run Sweep separately for Button Sweep proof.`
      },
      {
        controlId: 'intelligence-audit',
        label: 'Control audit replay',
        state: `${projectedProvenCount}/${audit.provableCount} projected proven`,
        tone: projectedUnprovenCount > 0 ? 'warn' : 'success',
        detail: `${projectedUnprovenCount} controls remain; replay only proves the Proof Replay Lab control.`
      },
      {
        controlId: 'break-test-lab',
        label: 'Adversarial break test replay',
        state: `${report.score}% resilience`,
        tone: report.failCount > 0 || report.warnCount > 0 ? 'warn' : 'success',
        detail: `${report.failCount} failures and ${report.warnCount} warnings were observed; press Run Break Test for Break Test proof.`
      },
      {
        controlId: 'nav-rail',
        label: 'Focus router replay',
        state: nextTarget?.focus || 'overview',
        tone: 'success',
        detail: `Target lane prepared for ${nextTarget?.label || 'the current dashboard proof queue'} without claiming nav proof.`
      },
      {
        controlId: 'proof-replay-lab',
        label: 'Proof replay controller',
        state: 'session proof recorded',
        tone: 'success',
        detail: 'Recorded the replay controller as proof and kept observed checks separate from target proof.'
      }
    ];
    const dangerCount = rows.filter(row => row.tone === 'danger').length;
    const warnCount = rows.filter(row => row.tone === 'warn').length;
    const replay = {
      ranAt: new Date().toISOString(),
      rows,
      exercisedCount: rows.length,
      dangerCount,
      warnCount,
      nextTarget,
      nextQueueCount: projectedUnprovenCount,
      projectedProvenCount,
      projectedUnprovenCount,
      observedControlIds,
      replayProofIds,
      tone: dangerCount > 0 ? 'danger' : warnCount > 0 ? 'warn' : 'success',
      report,
      audit
    };

    setProofReplay(replay);
    setButtonSweep(report.buttonSweep);
    setBreakTest(report);
    setControlAudit(audit);
    setMode('audit');
    setAuditFilter('proof');
    setSelectedAuditRowId(nextTarget?.id || (audit.riskRows[0] || audit.rows[0])?.id || '');
    setReviewedAuditRowIds([]);
    if (nextTarget?.focus) {
      onFocusChange(nextTarget.focus);
    }
    onCommandEvent(
      'Proof replay run',
      `${rows.length} safe checks observed; next target ${nextTarget?.label || 'none'}`,
      replay.tone,
      { controlId: 'proof-replay-lab' }
    );
    return replay;
  };

  const openProofReplayTarget = async () => {
    const replay = proofReplay || await runProofReplay();
    const target = replay.nextTarget;
    if (!target) return;
    setMode(target.mode || 'audit');
    setAuditFilter(target.auditFilter || 'proof');
    setSelectedAuditRowId(target.id || target.auditRowId || '');
    if (target.focus) {
      onFocusChange(target.focus, { controlId: 'proof-replay-lab' });
    }
    onCommandEvent(
      'Proof replay target opened',
      `${target.label} -> ${target.focus || 'overview'}`,
      target.tone || 'info',
      { controlId: 'proof-replay-lab' }
    );
  };

  const stageProofReplay = async () => {
    const replay = proofReplay || await runProofReplay();
    const packet = [
      '# Dashboard Proof Replay',
      '',
      `- ran_at: ${replay.ranAt}`,
      `- active_focus_before_stage: ${activeFocus || 'overview'}`,
      `- safe_checks_observed: ${replay.exercisedCount}`,
      `- replay_warnings: ${replay.warnCount}`,
      `- replay_failures: ${replay.dangerCount}`,
      `- next_target: ${replay.nextTarget?.label || 'none'}`,
      `- next_target_action: ${replay.nextTarget?.target || 'none'}`,
      '',
      '## Safe Replay Rows',
      ...replay.rows.map(row => `- ${row.tone.toUpperCase()} / ${row.controlId} / ${row.label} / ${row.state} / ${row.detail}`),
      '',
      '## Break-Test Snapshot',
      `- score: ${replay.report.score}`,
      `- failures: ${replay.report.failCount}`,
      `- warnings: ${replay.report.warnCount}`,
      `- weakest: ${replay.report.weakestRow?.label || 'none'}`,
      '',
      '## Control Proof Queue',
      `- proven_before_replay: ${replay.audit.provenCount}/${replay.audit.provableCount}`,
      `- unproven_before_replay: ${replay.audit.unprovenCount}`,
      `- projected_proven_after_replay: ${replay.projectedProvenCount}/${replay.audit.provableCount}`,
      `- projected_unproven_after_replay: ${replay.projectedUnprovenCount}`,
      `- proof_control_ids: ${replay.replayProofIds.join(', ')}`,
      `- observed_handler_ids: ${replay.observedControlIds.join(', ')}`,
      '',
      '## Operator Intent',
      'This replay is bounded local proof for the replay controller only. It can observe safe handlers and route the next target, but queued controls require their own real interaction proof.'
    ].join('\n');
    onStagePacket(packet, 'Proof replay staged', { controlId: 'proof-replay-lab' });
  };

  useEffect(() => {
    if (!controlAuditActiveRef.current) return;
    const nextAudit = createControlAudit();
    setControlAudit(nextAudit);
    setSelectedAuditRowId(current => (
      nextAudit.rows.some(row => row.id === current)
        ? current
        : (nextAudit.riskRows[0] || nextAudit.rows[0])?.id || ''
    ));
  }, [commandJournal, createControlAudit]);

  useEffect(() => {
    if (!proofRunner.startedAt || !controlAudit) return;
    const nextActiveId = proofRunnerNextActiveId;
    if (nextActiveId === proofRunner.activeId) return;
    setProofRunner(previous => ({
      ...previous,
      activeId: nextActiveId
    }));
  }, [controlAudit, proofRunner.activeId, proofRunner.startedAt, proofRunnerNextActiveId]);

  const selectMode = nextMode => {
    setMode(nextMode);
    if (nextMode === 'audit') {
      const nextAudit = controlAudit || createControlAudit();
      setControlAudit(nextAudit);
      setSelectedAuditRowId(current => (nextAudit.rows.some(row => row.id === current) ? current : (nextAudit.riskRows[0] || nextAudit.rows[0])?.id || ''));
      onCommandEvent('Control audit opened', `${nextAudit.score}% coverage / ${nextAudit.riskCount} risks`, nextAudit.tone, { controlId: 'intelligence-audit' });
      return;
    }
    const modeControlId = nextMode === 'plan'
      ? 'command-brain'
      : nextMode === 'evidence'
        ? 'action-receipt'
        : 'intelligence-stage';
    onCommandEvent('Intelligence mode changed', nextMode, 'info', { controlId: modeControlId });
  };

  const selectScenario = scenario => {
    setScenarioId(scenario.id);
    onCommandEvent('Scenario selected', `${scenario.label} - ${scenario.metric}`, scenario.tone || 'info', { controlId: 'intelligence-stage' });
  };

  const focusScenario = scenario => {
    setScenarioId(scenario.id);
    if (scenario.focus) {
      onFocusChange(scenario.focus);
    }
    onCommandEvent('Scenario focus requested', scenario.label, scenario.tone || 'info', { controlId: 'intelligence-stage' });
  };

  const stageScenario = (meta = {}) => {
    if (!activeScenario) return;
    const packet = [
      '# Dashboard Scenario Brief',
      '',
      `- scenario: ${activeScenario.label}`,
      `- metric: ${activeScenario.metric}`,
      `- priority: ${brief.priority}`,
      `- health_score: ${brief.healthScore}`,
      `- focus: ${activeScenario.focus || activeFocus}`,
      `- detail: ${activeScenario.detail}`,
      '',
      '## Gate Trace',
      ...brief.decisionTrace.map(row => `- ${row.label}: ${row.detail}`),
      '',
      '## Recent Commands',
      ...(brief.recentActions.length
        ? brief.recentActions.map(row => `- ${row.title}: ${row.detail}`)
        : ['- No local commands recorded.'])
    ].join('\n');
    onStagePacket(packet, `${activeScenario.label} staged`, { controlId: 'intelligence-stage', ...meta });
  };

  const runBriefAction = action => {
    if (action.packet) {
      onStagePacket(action.packet, action.label, { controlId: 'intelligence-stage' });
      return;
    }
    if (action.focus) {
      onFocusChange(action.focus);
      onCommandEvent(action.label, action.detail, action.tone || 'info', { controlId: 'command-brain' });
    }
  };

  const openActionReceiptJournal = () => {
    setMode('evidence');
    onCommandEvent(
      'Action receipt trace opened',
      latestCommand ? `${latestCommand.title} -> command journal` : 'command journal opened',
      actionReceiptTone,
      { controlId: 'action-receipt' }
    );
  };

  const stageActionReceipt = (meta = {}) => {
    const receipt = latestCommand || {
      title: 'No action recorded',
      detail: 'No dashboard action has been recorded yet.',
      tone: 'info',
      time: new Date().toISOString()
    };
    const packet = [
      '# Dashboard Action Receipt',
      '',
      `- action: ${receipt.title}`,
      `- detail: ${receipt.detail}`,
      `- tone: ${receipt.tone || 'info'}`,
      `- time: ${receipt.time}`,
      `- active_focus: ${activeFocus || 'overview'}`,
      `- proof_ids: ${actionReceiptProofLabel}`,
      `- journal_depth: ${commandJournal.length}`,
      '',
      '## Recent Action Trail',
      ...(commandJournal.length
        ? commandJournal.slice(0, 10).map(row => `- ${row.title}: ${row.detail}${row.controlId ? ` / proof ${row.controlId}` : ''}`)
        : ['- No local commands recorded.']),
      '',
      '## Operator Intent',
      'Use this as a click receipt. A button is considered useful only when it leaves a visible state change, packet, focus change, or explicit proof event.'
    ].join('\n');
    onStagePacket(packet, 'Action receipt staged', { controlId: 'action-receipt', ...meta });
  };

  const openActionReceiptNextProof = () => {
    if (!actionReceiptNextControl) {
      onCommandEvent('Action receipt proof queue clear', 'All tracked dashboard controls have explicit proof in this session.', 'success', { controlId: 'action-receipt' });
      return;
    }
    if (actionReceiptNextControl.focus) {
      onFocusChange(actionReceiptNextControl.focus, { controlId: 'action-receipt' });
    }
    onCommandEvent(
      'Action receipt next proof opened',
      `${actionReceiptNextControl.surface}: ${actionReceiptNextControl.action}`,
      'info',
      { controlId: 'action-receipt' }
    );
  };

  const stageActionReceiptNextProof = () => {
    const control = actionReceiptNextControl;
    const packet = [
      '# Dashboard Next Proof Target',
      '',
      `- proof_progress: ${actionReceiptProgressLabel}`,
      `- tracked_controls: ${actionReceiptTotalCount}`,
      `- active_focus: ${activeFocus || 'overview'}`,
      control ? `- control_id: ${control.id}` : '- control_id: none',
      control ? `- surface: ${control.surface}` : '- surface: none',
      control ? `- action: ${control.action}` : '- action: none',
      control ? `- focus: ${control.focus || 'overview'}` : '- focus: overview',
      '',
      '## Press',
      control ? control.target : 'All tracked dashboard controls have explicit proof in this session.',
      '',
      '## Expect',
      control ? control.expected : 'No unproven target remains.',
      '',
      '## Recent Receipt',
      latestCommand
        ? `- ${latestCommand.title}: ${latestCommand.detail}${latestCommand.controlId ? ` / proof ${latestCommand.controlId}` : ''}`
        : '- No local command recorded.',
      '',
      '## Operator Intent',
      'Use this as the next-click proof card. Open the target, press the named control, then confirm Action Receipt and Audit both record the explicit proof event.'
    ].join('\n');
    onStagePacket(packet, control ? `${control.surface} proof target staged` : 'Proof queue clear staged', { controlId: 'action-receipt' });
  };

  const stageControlAudit = () => {
    const audit = controlAudit || runControlAudit();
    const packet = [
      '# Dashboard Control Audit',
      '',
      `- ran_at: ${audit.ranAt}`,
      `- active_focus: ${activeFocus}`,
      `- score: ${audit.score}`,
      `- passed: ${audit.passCount}/${audit.rows.length}`,
      `- risks: ${audit.riskCount}`,
      `- control_rows: ${audit.controlCount}`,
      `- packet_or_comms_paths: ${audit.packetCount}`,
      `- focus_paths: ${audit.focusCount}`,
      `- interaction_proof: ${audit.provenCount}/${audit.provableCount}`,
      `- unproven_controls: ${audit.unprovenCount}`,
      `- proof_source: explicit dashboard control events`,
      `- preview_backed_routes: ${audit.previewCount}`,
      `- reviewed_risks: ${reviewedRiskCount}/${audit.riskCount}`,
      `- headline: ${audit.headline}`,
      '',
      '## Control Rows',
      ...audit.rows.map(row => `- ${row.tone.toUpperCase()} / ${row.label} / ${row.state} / ${row.detail}`),
      '',
      '## Recent Interaction Proof',
      ...audit.rows
        .filter(row => row.provable)
        .map(row => `- ${row.proof ? 'PROVEN' : 'UNPROVEN'} / ${row.label}${row.proof ? ` / ${row.proof.title}: ${row.proof.detail}` : ''}`),
      '',
      '## Operator Intent',
      audit.riskCount > 0
        ? 'Open the first risk, inspect the linked lane, and do not claim the dashboard complete until the risky controls are explained or fixed.'
        : 'Use this snapshot as evidence that the current dashboard controls are wired and producing reviewable state.'
    ].join('\n');
    onStagePacket(packet, 'Control audit staged', { controlId: 'intelligence-audit' });
  };

  const openAuditRow = row => {
    if (!row?.focus) return;
    setSelectedAuditRowId(row.id);
    onFocusChange(row.focus);
    onCommandEvent('Control audit row opened', `${row.label} -> ${row.focus}`, row.tone || 'info', { controlId: 'intelligence-audit' });
  };

  const markAuditRowReviewed = () => {
    if (!selectedAuditRow) return;
    setReviewedAuditRowIds(previous => (
      previous.includes(selectedAuditRow.id) ? previous : [...previous, selectedAuditRow.id]
    ));
    onCommandEvent('Control audit row reviewed', selectedAuditRow.label, selectedAuditRow.tone || 'info', { controlId: 'intelligence-audit' });
  };

  const openNextAuditRisk = () => {
    const audit = controlAudit || runControlAudit();
    const reviewed = new Set(reviewedAuditRowIds);
    const nextRisk = audit.riskRows.find(row => row.id !== selectedAuditRow?.id && !reviewed.has(row.id))
      || audit.riskRows.find(row => row.id !== selectedAuditRow?.id)
      || audit.riskRows[0]
      || audit.rows[0];
    if (!nextRisk) return;
    setSelectedAuditRowId(nextRisk.id);
    if (nextRisk.focus) {
      onFocusChange(nextRisk.focus);
    }
    onCommandEvent('Next audit risk opened', `${nextRisk.label} -> ${nextRisk.focus || 'overview'}`, nextRisk.tone || 'info', { controlId: 'intelligence-audit' });
  };

  const openSelectedControl = () => {
    const target = selectedAuditRow;
    if (!target?.focus) return;
    setSelectedAuditRowId(target.id);
    onFocusChange(target.focus);
    onCommandEvent('Control target opened', `${target.label} -> ${target.focus}`, target.tone || 'info', { controlId: 'intelligence-audit' });
  };

  const selectDrillTarget = row => {
    if (!row) return;
    setSelectedAuditRowId(row.id);
    setAuditFilter('proof');
    onCommandEvent('Audit drill target selected', `${row.label} -> ${row.focus || 'overview'}`, row.tone || 'warn', { controlId: 'intelligence-audit' });
  };

  const startAuditDrill = () => {
    const audit = controlAudit || runControlAudit();
    const target = audit.rows.find(row => row.provable && !row.proof) || audit.rows[0];
    if (!target) return;
    setAuditFilter('proof');
    setSelectedAuditRowId(target.id);
    onCommandEvent('Audit drill started', `${audit.unprovenCount} unproven controls / ${audit.provenCount} proven`, audit.unprovenCount > 0 ? 'warn' : 'success', { controlId: 'intelligence-audit' });
  };

  const openDrillTarget = () => {
    const target = drillTargetRow;
    if (!target?.focus) return;
    setSelectedAuditRowId(target.id);
    onFocusChange(target.focus);
    onCommandEvent('Audit drill target opened', `${target.label} -> ${target.focus}`, target.tone || 'warn', { controlId: 'intelligence-audit' });
  };

  const applyProofCoverageSelection = row => {
    const target = row?.nextRow;
    if (!target) return null;
    setAuditFilter('proof');
    setSelectedAuditRowId(target.id);
    return target;
  };

  const selectProofCoverage = row => {
    const target = applyProofCoverageSelection(row);
    if (!target) return;
    onCommandEvent('Proof sweep group selected', `${row.label} -> ${target.label}`, row.tone || 'info', { controlId: 'proof-sweep' });
  };

  const openProofCoverage = row => {
    const target = applyProofCoverageSelection(row);
    if (!target) return;
    if (target.focus) {
      onFocusChange(target.focus);
    }
    onCommandEvent('Proof sweep group opened', `${row.label} -> ${target.focus || 'overview'}`, row.tone || 'info', { controlId: 'proof-sweep' });
  };

  const showUnprovenControls = () => {
    setAuditFilter('proof');
    onCommandEvent('Proof sweep filter opened', `${controlAudit?.unprovenCount || 0} unproven controls`, controlAudit?.unprovenCount > 0 ? 'warn' : 'success', { controlId: 'proof-sweep' });
  };

  const startControlPulse = () => {
    const audit = controlAudit || runControlAudit();
    const target = audit.rows.find(row => row.provable && !row.proof) || audit.rows[0];
    setMode('audit');
    setAuditFilter('proof');
    if (target) {
      setSelectedAuditRowId(target.id);
    }
    onCommandEvent(
      'Control pulse started',
      target ? `${audit.provenCount}/${audit.provableCount} proven -> ${target.label}` : 'No control target available',
      audit.unprovenCount > 0 ? 'warn' : 'success',
      { controlId: 'control-pulse' }
    );
  };

  const openControlPulseTarget = () => {
    const audit = controlAudit || runControlAudit();
    const target = controlPulseTarget || audit.rows.find(row => row.provable && !row.proof) || audit.rows[0];
    setMode('audit');
    setAuditFilter('proof');
    if (target) {
      setSelectedAuditRowId(target.id);
    }
    if (target?.focus) {
      onFocusChange(target.focus);
    }
    onCommandEvent(
      'Control pulse target opened',
      target ? `${target.label} -> ${target.focus || 'overview'}` : 'No target available',
      target?.tone || audit.tone || 'info',
      { controlId: 'control-pulse' }
    );
  };

  const openControlPulseAudit = () => {
    const audit = controlAudit || runControlAudit();
    setMode('audit');
    setAuditFilter('proof');
    setSelectedAuditRowId(current => (
      audit.rows.some(row => row.id === current)
        ? current
        : (audit.rows.find(row => row.provable && !row.proof) || audit.rows[0])?.id || ''
    ));
    onCommandEvent('Control pulse audit opened', `${audit.unprovenCount} unproven controls`, audit.tone || 'info', { controlId: 'control-pulse' });
  };

  const stageControlPulse = () => {
    const audit = controlAudit || runControlAudit();
    const target = controlPulseTarget || audit.rows.find(row => row.provable && !row.proof) || audit.rows[0];
    const queueRows = audit.rows.filter(row => row.provable && !row.proof).slice(0, 8);
    const packet = [
      '# Dashboard Control Pulse',
      '',
      `- ran_at: ${audit.ranAt}`,
      `- proof_progress: ${audit.provenCount}/${audit.provableCount}`,
      `- proof_percent: ${audit.provableCount ? Math.round((audit.provenCount / audit.provableCount) * 100) : 0}`,
      `- unproven_controls: ${audit.unprovenCount}`,
      `- active_focus: ${activeFocus}`,
      `- latest_proof: ${latestProofEvent ? `${latestProofEvent.title}: ${latestProofEvent.detail}` : 'none'}`,
      '',
      '## Active Target',
      target
        ? `- ${target.label} / ${target.state} / focus ${target.focus || 'overview'}`
        : '- No target available.',
      target ? `- press: ${target.target || target.label}` : '- press: none',
      target ? `- expected_result: ${target.expected || target.evidence || target.detail}` : '- expected_result: none',
      target ? `- proof_event: command journal metadata ${target.controlId || target.id}` : '- proof_event: none',
      '',
      '## Sprint Queue',
      ...(queueRows.length
        ? queueRows.map((row, index) => `- ${index + 1}. ${row.label} / ${row.focus || 'overview'} / press: ${row.target || row.label}`)
        : ['- No unproven controls remain in this audit snapshot.']),
      '',
      '## Recent Proof Events',
      ...(controlProofEvents.length
        ? controlProofEvents.slice(0, 8).map(row => `- ${row.title}: ${row.detail}`)
        : ['- No explicit control proof events recorded yet.']),
      '',
      '## Operator Intent',
      'Use this pulse as the next-button proof sprint. Open the target, press the real named control, then re-run the pulse; helper clicks do not prove the target control.'
    ].join('\n');
    onStagePacket(packet, 'Control pulse staged', { controlId: 'control-pulse' });
  };

  const startProofRunner = () => {
    const audit = controlAudit || runControlAudit();
    const queueRows = audit.rows.filter(row => row.provable && !row.proof).slice(0, 6);
    const active = queueRows[0] || null;
    setMode('audit');
    setAuditFilter('proof');
    if (active) {
      setSelectedAuditRowId(active.id);
    }
    setProofRunner({
      startedAt: new Date().toISOString(),
      queueIds: queueRows.map(row => row.controlId),
      activeId: active?.controlId || '',
      skippedIds: []
    });
    onCommandEvent(
      'Proof runner started',
      active ? `${queueRows.length} queued; active target ${active.label}` : 'No unproven controls remain',
      queueRows.length > 0 ? 'warn' : 'success',
      { controlId: 'proof-runner' }
    );
  };

  const openProofRunnerTarget = () => {
    const audit = controlAudit || runControlAudit();
    const target = proofRunnerActiveRow || audit.rows.find(row => row.provable && !row.proof) || audit.rows[0];
    if (!target) return;
    setMode('audit');
    setAuditFilter('proof');
    setSelectedAuditRowId(target.id);
    if (target.focus) {
      onFocusChange(target.focus);
    }
    setProofRunner(previous => ({
      startedAt: previous.startedAt || new Date().toISOString(),
      queueIds: previous.queueIds.length ? previous.queueIds : audit.rows.filter(row => row.provable && !row.proof).slice(0, 6).map(row => row.controlId),
      activeId: target.controlId || previous.activeId,
      skippedIds: previous.skippedIds
    }));
    onCommandEvent(
      'Proof runner target opened',
      `${target.label} -> ${target.focus || 'overview'}; press the real target control for proof`,
      target.tone || 'warn',
      { controlId: 'proof-runner' }
    );
  };

  const advanceProofRunnerTarget = () => {
    const audit = controlAudit || runControlAudit();
    const queuedRows = proofRunner.queueIds.length
      ? proofRunner.queueIds.map(controlId => audit.rows.find(row => row.controlId === controlId)).filter(Boolean)
      : audit.rows.filter(row => row.provable && !row.proof).slice(0, 6);
    const activeIndex = queuedRows.findIndex(row => row.controlId === proofRunner.activeId);
    const remainingQueue = queuedRows.slice(Math.max(0, activeIndex + 1)).filter(row => row.provable && !row.proof);
    const outsideQueue = audit.rows.find(row => (
      row.provable
      && !row.proof
      && !queuedRows.some(queued => queued.controlId === row.controlId)
    ));
    const nextTarget = remainingQueue[0] || outsideQueue || queuedRows.find(row => row.provable && !row.proof) || null;
    setProofRunner(previous => {
      const skippedIds = previous.activeId && nextTarget?.controlId !== previous.activeId && !previous.skippedIds.includes(previous.activeId)
        ? [...previous.skippedIds, previous.activeId]
        : previous.skippedIds;
      const queueIds = previous.queueIds.length
        ? previous.queueIds
        : queuedRows.map(row => row.controlId);
      const withOutsideTarget = nextTarget && !queueIds.includes(nextTarget.controlId)
        ? [...queueIds, nextTarget.controlId]
        : queueIds;
      return {
        startedAt: previous.startedAt || new Date().toISOString(),
        queueIds: withOutsideTarget,
        activeId: nextTarget?.controlId || '',
        skippedIds
      };
    });
    if (nextTarget) {
      setSelectedAuditRowId(nextTarget.id);
    }
    onCommandEvent(
      'Proof runner advanced',
      nextTarget ? `Next target ${nextTarget.label}; skipped targets still require proof` : 'Proof runner queue has no remaining unproven target',
      nextTarget ? 'warn' : 'success',
      { controlId: 'proof-runner' }
    );
  };

  const stageProofRunner = () => {
    const audit = controlAudit || runControlAudit();
    const queueRows = proofRunner.queueIds.length
      ? proofRunner.queueIds.map(controlId => audit.rows.find(row => row.controlId === controlId)).filter(Boolean)
      : audit.rows.filter(row => row.provable && !row.proof).slice(0, 6);
    const active = proofRunnerActiveRow || queueRows.find(row => row.provable && !row.proof) || null;
    const skippedSet = new Set(proofRunner.skippedIds);
    const packet = [
      '# Dashboard Proof Runner',
      '',
      `- started_at: ${proofRunner.startedAt || 'not_started'}`,
      `- staged_at: ${new Date().toISOString()}`,
      `- proof_progress: ${audit.provenCount}/${audit.provableCount}`,
      `- runner_queue_size: ${queueRows.length}`,
      `- runner_done: ${queueRows.filter(row => row.proof).length}`,
      `- runner_skipped: ${proofRunner.skippedIds.length}`,
      `- active_target: ${active?.label || 'none'}`,
      `- active_focus: ${active?.focus || activeFocus || 'overview'}`,
      '',
      '## Active Target',
      active
        ? `- press: ${active.target || active.label}`
        : '- press: none',
      active
        ? `- expected_result: ${active.expected || active.evidence || active.detail}`
        : '- expected_result: no unproven target remains',
      active
        ? `- required_proof_event: ${active.controlId}`
        : '- required_proof_event: none',
      '',
      '## Runner Queue',
      ...(queueRows.length
        ? queueRows.map(row => {
          const state = row.proof
            ? 'PROVEN'
            : row.controlId === active?.controlId
              ? 'ACTIVE'
              : skippedSet.has(row.controlId)
                ? 'SKIPPED'
                : 'QUEUED';
          return `- ${state} / ${row.controlId} / ${row.label} / focus ${row.focus || 'overview'} / press: ${row.target || row.label}`;
        })
        : ['- No runner queue is active.']),
      '',
      '## Proof Discipline',
      '- Runner buttons guide, open, advance, and stage. They do not prove the queued target.',
      '- A queued target is proven only when the command journal records that target controlId from its own control surface.'
    ].join('\n');
    onStagePacket(packet, 'Proof runner staged', { controlId: 'proof-runner' });
  };

  const stageProofSweep = (meta = {}) => {
    const audit = controlAudit || runControlAudit();
    const coverageRows = buildProofCoverageRows(audit.rows);
    const nextTargets = audit.rows.filter(row => row.provable && !row.proof).slice(0, 12);
    const packet = [
      '# Dashboard Proof Sweep',
      '',
      `- ran_at: ${audit.ranAt}`,
      `- proof_progress: ${audit.provenCount}/${audit.provableCount}`,
      `- proof_percent: ${audit.provableCount ? Math.round((audit.provenCount / audit.provableCount) * 100) : 0}`,
      `- unproven_controls: ${audit.unprovenCount}`,
      `- proof_source: explicit dashboard control events`,
      `- weakest_group: ${coverageRows.find(row => row.unproven > 0)?.label || 'none'}`,
      '',
      '## Coverage By Kind',
      ...(coverageRows.length
        ? coverageRows.map(row => `- ${row.tone.toUpperCase()} / ${row.label}: ${row.proven}/${row.total} proven (${row.percent}%) / unproven ${row.unproven}${row.preview ? ` / preview ${row.preview}` : ''}${row.nextRow ? ` / next ${row.nextRow.label}` : ''}`)
        : ['- No proof coverage rows available.']),
      '',
      '## Next Target Queue',
      ...(nextTargets.length
        ? nextTargets.map(row => `- ${row.label} / focus ${row.focus || 'overview'} / press: ${row.target || row.label} / expected: ${row.expected || row.evidence || row.detail} / proof_event: ${row.controlId || row.id}`)
        : ['- No unproven controls remain in this audit snapshot.']),
      '',
      '## Recent Proof Events',
      ...(controlProofEvents.length
        ? controlProofEvents.slice(0, 10).map(row => `- ${row.title}: ${row.detail}`)
        : ['- No explicit control proof events recorded yet.']),
      '',
      '## Operator Intent',
      'Use this sweep as a coverage plan. Select a group, open its lane, and press the real target control; do not count this packet as proof for the queued controls.'
    ].join('\n');
    onStagePacket(packet, 'Proof sweep staged', { controlId: 'proof-sweep', ...meta });
  };

  const stageAuditDrill = () => {
    const audit = controlAudit || runControlAudit();
    const target = drillTargetRow || audit.rows.find(row => row.provable && !row.proof) || audit.rows[0];
    const packet = [
      '# Dashboard Control Drill',
      '',
      `- ran_at: ${audit.ranAt}`,
      `- proof_progress: ${audit.provenCount}/${audit.provableCount}`,
      `- proof_percent: ${audit.provableCount ? Math.round((audit.provenCount / audit.provableCount) * 100) : 0}`,
      `- unproven_controls: ${audit.unprovenCount}`,
      `- proof_source: explicit dashboard control events`,
      '',
      '## Current Target',
      target
        ? `- ${target.label} / ${target.state} / focus ${target.focus || 'overview'} / ${target.detail}`
        : '- No target available.',
      '',
      '## Execution Guide',
      target ? `- press: ${target.target || target.label}` : '- press: none',
      target ? `- expected_result: ${target.expected || target.evidence || target.detail}` : '- expected_result: none',
      target ? `- proof_event: command journal metadata ${target.controlId || target.id}` : '- proof_event: none',
      '',
      '## Next Queue',
      ...(audit.rows
        .filter(row => row.provable && !row.proof && row.id !== target?.id)
        .slice(0, 8)
        .map(row => `- ${row.label} / ${row.state} / focus ${row.focus || 'overview'}`)),
      ...(audit.rows.filter(row => row.provable && !row.proof && row.id !== target?.id).length ? [] : ['- No additional unproven controls.']),
      '',
      '## Recent Proof Events',
      ...(controlProofEvents.length
        ? controlProofEvents.slice(0, 8).map(row => `- ${row.title}: ${row.detail}`)
        : ['- No explicit control proof events recorded yet.']),
      '',
      '## Operator Intent',
      'Use Open Target to navigate to the real surface, then press the actual named control. Do not count this drill packet itself as proof for another control.'
    ].join('\n');
    onStagePacket(packet, 'Control drill staged', { controlId: 'intelligence-audit' });
  };

  const stageAuditRisk = () => {
    const audit = controlAudit || runControlAudit();
    const target = selectedAuditRow || audit.riskRows[0] || audit.rows[0];
    if (!target) return;
    const packet = [
      '# Dashboard Risk Triage',
      '',
      `- ran_at: ${audit.ranAt}`,
      `- risk: ${target.label}`,
      `- tone: ${target.tone || 'info'}`,
      `- state: ${target.state}`,
      `- focus: ${target.focus || 'overview'}`,
      `- detail: ${target.detail}`,
      `- audit_score: ${audit.score}`,
      `- audit_risks: ${audit.riskCount}`,
      `- reviewed_risks: ${reviewedRiskCount}/${audit.riskCount}`,
      `- unreviewed_risks: ${unreviewedRiskRows.length ? unreviewedRiskRows.slice(0, 8).map(row => row.label).join(' | ') : 'none'}`,
      '',
      '## Recommended Next Action',
      selectedRiskRecommendation,
      '',
      '## Evidence Discipline',
      '- Open the linked lane before making a claim.',
      '- Stage the lane packet or evidence window that proves the next move.',
      '- Keep protected routes token-backed and live worker actions gated.'
    ].join('\n');
    onStagePacket(packet, `${target.label} risk staged`, { controlId: 'intelligence-audit' });
  };

  const openAuditRisk = () => {
    const audit = controlAudit || runControlAudit();
    const target = selectedAuditRow || audit.riskRows[0] || audit.rows[0];
    if (!target?.focus) return;
    setSelectedAuditRowId(target.id);
    onFocusChange(target.focus);
    onCommandEvent('Control audit risk opened', `${target.label} -> ${target.focus}`, target.tone || 'info', { controlId: 'intelligence-audit' });
  };

  const selectBrainMove = item => {
    if (!item) return;
    setSelectedBrainId(item.id);
    if (item.scenarioId) setScenarioId(item.scenarioId);
    onCommandEvent('Command brain move selected', `${item.label} -> ${item.focus}`, item.tone || 'info', { controlId: 'command-brain' });
  };

  const applyBrainCheck = item => {
    if (!item) return null;
    if (item.scenarioId) setScenarioId(item.scenarioId);
    if (item.mode) setMode(item.mode);
    if (item.id === 'prove-controls') {
      const audit = controlAudit || runControlAudit();
      const target = audit.rows.find(row => row.provable && !row.proof) || audit.riskRows[0] || audit.rows[0];
      setAuditFilter(item.auditFilter || 'proof');
      if (target) setSelectedAuditRowId(target.id);
      return target;
    }
    return null;
  };

  const openBrainMove = () => {
    if (!activeBrain) return;
    const target = applyBrainCheck(activeBrain);
    onFocusChange(target?.focus || activeBrain.focus || 'overview');
    onCommandEvent('Command brain opened move', `${activeBrain.label} -> ${target?.focus || activeBrain.focus || 'overview'}`, activeBrain.tone || 'info', { controlId: 'command-brain' });
  };

  const checkBrainMove = () => {
    if (!activeBrain) return;
    const target = applyBrainCheck(activeBrain);
    onCommandEvent('Command brain check applied', target ? `${activeBrain.label}: ${target.label}` : activeBrain.detail, activeBrain.tone || 'info', { controlId: 'command-brain' });
  };

  const stageBrainMove = () => {
    if (!activeBrain) return;
    const packet = [
      '# Command Brain Move',
      '',
      `- selected_move: ${activeBrain.label}`,
      `- state: ${activeBrain.state}`,
      `- tone: ${activeBrain.tone || 'info'}`,
      `- confidence: ${activeBrain.confidence}`,
      `- urgency: ${activeBrain.urgency}`,
      `- target_focus: ${activeBrain.focus || 'overview'}`,
      `- intelligence_priority: ${brief.priority}`,
      `- health_score: ${brief.healthScore}`,
      `- active_dashboard_focus: ${activeFocus}`,
      '',
      '## Why This Move',
      ...activeBrain.reasons.map(reason => `- ${reason}`),
      '',
      '## Steps',
      ...activeBrain.steps.map((step, index) => `- ${index + 1}. ${step}`),
      '',
      '## Gate Trace',
      ...brief.decisionTrace.map(row => `- ${row.label}: ${row.detail}`),
      '',
      '## Recent Commands',
      ...(brief.recentActions.length
        ? brief.recentActions.slice(0, 8).map(row => `- ${row.title}: ${row.detail}`)
        : ['- No local commands recorded.']),
      '',
      '## Operator Intent',
      'Use this as a ranked next-move packet. Open the target lane and verify evidence before any protected route, publish action, or worker dispatch.'
    ].join('\n');
    onStagePacket(packet, `${activeBrain.label} brain staged`, { controlId: 'command-brain' });
  };

  const toggleSimulationGate = row => {
    if (!row) return;
    setSimulationDraft(previous => ({ ...previous, [row.id]: !previous[row.id] }));
    onCommandEvent(
      'Simulation gate toggled',
      `${row.label} -> ${simulationDraft[row.id] ? 'off' : 'on'}`,
      row.tone || 'info',
      { controlId: 'simulation-deck' }
    );
  };

  const applySuggestedSimulation = () => {
    const row = simulationRows.find(item => item.id === suggestedSimulationId) || simulationRows[0];
    if (!row) return;
    setSimulationDraft(previous => ({ ...previous, [row.id]: true }));
    onCommandEvent('Simulation assumption applied', row.label, row.tone || 'info', { controlId: 'simulation-deck' });
  };

  const resetSimulation = () => {
    setSimulationDraft({
      sync: false,
      evidence: false,
      controls: false,
      model: false
    });
    onCommandEvent('Simulation reset', 'all assumptions cleared', 'warn', { controlId: 'simulation-deck' });
  };

  const openSimulationLane = () => {
    const target = activeSimulationRows[0] || simulationRows.find(row => row.needsWork) || simulationRows[0];
    if (!target) return;
    onFocusChange(target.focus || 'overview');
    onCommandEvent('Simulation lane opened', `${target.label} -> ${target.focus || 'overview'}`, target.tone || 'info', { controlId: 'simulation-deck' });
  };

  const stageSimulationPlan = () => {
    const packet = [
      '# Dashboard Decision Simulation',
      '',
      `- current_priority: ${brief.priority}`,
      `- projected_priority: ${projectedPriority}`,
      `- current_score: ${brief.healthScore}`,
      `- projected_score: ${projectedScore}`,
      `- score_delta: ${projectionDelta >= 0 ? '+' : ''}${projectionDelta}`,
      `- active_assumptions: ${activeSimulationRows.length ? activeSimulationRows.map(row => row.id).join(', ') : 'none'}`,
      `- remaining_danger_gates: ${remainingDangerCount}`,
      `- remaining_warning_gates: ${remainingWarnCount}`,
      '',
      '## Assumption Ledger',
      ...simulationRows.map(row => `- ${simulationDraft[row.id] ? 'ON' : 'OFF'} / ${row.label} / ${row.state} / impact ${row.impact} / ${row.detail}`),
      '',
      '## Recommended Sequence',
      ...(simulationSequence.length
        ? simulationSequence.map((row, index) => `- ${index + 1}. ${row.sequence}`)
        : ['- No simulated or open gates selected.']),
      '',
      '## Gate Trace',
      ...brief.decisionTrace.map(row => `- ${row.label}: ${row.detail}`),
      '',
      '## Operator Intent',
      'Use this as a what-if plan only. Verify each assumption in its dashboard lane before claiming the bridge is ready, publishing, or dispatching workers.'
    ].join('\n');
    onStagePacket(packet, 'Decision simulation staged', { controlId: 'simulation-deck' });
  };

  const selectRunbookStep = row => {
    if (!row) return;
    setRunbookState(previous => ({ ...previous, activeId: row.id }));
    onCommandEvent('Runbook step selected', `${row.label} -> ${row.focus || 'overview'}`, row.tone || 'info', { controlId: 'runbook-operator' });
  };

  const startRunbook = () => {
    const nextStep = runbookRows.find(row => !completedRunbookSet.has(row.id) && !heldRunbookSet.has(row.id)) || runbookRows[0];
    if (!nextStep) return;
    setRunbookState(previous => ({ ...previous, activeId: nextStep.id }));
    onCommandEvent('Runbook started', `${nextStep.label} / ${runbookProgress}% complete`, nextStep.tone || 'info', { controlId: 'runbook-operator' });
  };

  const openRunbookStep = () => {
    if (!activeRunbookStep) return;
    if (activeRunbookStep.sourceId === 'controls') {
      const audit = controlAudit || runControlAudit();
      const target = audit.rows.find(row => row.provable && !row.proof) || audit.riskRows[0] || audit.rows[0];
      setMode('audit');
      setAuditFilter('proof');
      if (target) setSelectedAuditRowId(target.id);
    } else if (activeRunbookStep.sourceId === 'evidence') {
      setMode('evidence');
      setScenarioId('evidence');
    } else if (activeRunbookStep.sourceId === 'model') {
      setMode('plan');
      setScenarioId('model');
    } else if (activeRunbookStep.sourceId === 'sync') {
      setMode('plan');
      setScenarioId('publish');
    }
    onFocusChange(activeRunbookStep.focus || 'overview');
    onCommandEvent('Runbook step opened', `${activeRunbookStep.label} -> ${activeRunbookStep.focus || 'overview'}`, activeRunbookStep.tone || 'info', { controlId: 'runbook-operator' });
  };

  const completeRunbookStep = () => {
    if (!activeRunbookStep) return;
    const activeId = activeRunbookStep.id;
    const nextCompleted = [...new Set([...runbookState.completed, activeId])];
    const nextHeldSet = new Set(runbookState.held.filter(id => id !== activeId));
    const nextStep = runbookRows.find(row => row.id !== activeId && !nextCompleted.includes(row.id) && !nextHeldSet.has(row.id));
    setRunbookState({
      activeId: nextStep?.id || activeId,
      completed: nextCompleted,
      held: [...nextHeldSet]
    });
    onCommandEvent('Runbook step completed', activeRunbookStep.label, 'success', { controlId: 'runbook-operator' });
  };

  const holdRunbookStep = () => {
    if (!activeRunbookStep) return;
    const activeId = activeRunbookStep.id;
    const alreadyHeld = heldRunbookSet.has(activeId);
    const nextHeld = alreadyHeld
      ? runbookState.held.filter(id => id !== activeId)
      : [...new Set([...runbookState.held, activeId])];
    const nextHeldSet = new Set(nextHeld);
    const nextActive = alreadyHeld
      ? activeId
      : runbookRows.find(row => row.id !== activeId && !completedRunbookSet.has(row.id) && !nextHeldSet.has(row.id))?.id || activeId;
    setRunbookState(previous => ({
      ...previous,
      activeId: nextActive,
      held: nextHeld
    }));
    onCommandEvent(alreadyHeld ? 'Runbook step resumed' : 'Runbook step held', activeRunbookStep.label, alreadyHeld ? 'info' : 'warn', { controlId: 'runbook-operator' });
  };

  const stageRunbookPacket = () => {
    const packet = [
      '# Operator Runbook',
      '',
      `- priority: ${brief.priority}`,
      `- projected_priority: ${projectedPriority}`,
      `- score: ${brief.healthScore} -> ${projectedScore}`,
      `- progress: ${runbookDoneCount}/${runbookRows.length}`,
      `- held_steps: ${runbookHeldCount}`,
      `- active_step: ${activeRunbookStep?.label || 'none'}`,
      `- active_focus: ${activeRunbookStep?.focus || activeFocus}`,
      '',
      '## Steps',
      ...runbookRows.map(row => {
        const status = completedRunbookSet.has(row.id)
          ? 'DONE'
          : heldRunbookSet.has(row.id)
            ? 'HELD'
            : row.id === activeRunbookStep?.id
              ? 'ACTIVE'
              : 'QUEUED';
        return `- ${status} / ${row.label} / ${row.state} / ${row.metric} / focus ${row.focus} / ${row.intent}`;
      }),
      '',
      '## Simulation Assumptions',
      ...simulationRows.map(row => `- ${simulationDraft[row.id] ? 'ON' : 'OFF'} / ${row.label} / ${row.detail}`),
      '',
      '## Gate Trace',
      ...brief.decisionTrace.map(row => `- ${row.label}: ${row.detail}`),
      '',
      '## Operator Intent',
      'Use this as the live dashboard execution queue. Open each active step, collect evidence in its lane, and keep publish/worker actions gated until Comms review is complete.'
    ].join('\n');
    onStagePacket(packet, 'Operator runbook staged', { controlId: 'runbook-operator' });
  };

  const resetRunbook = () => {
    setRunbookState({
      activeId: runbookRows[0]?.id || '',
      completed: [],
      held: []
    });
    onCommandEvent('Runbook reset', 'active/done/held state cleared', 'warn', { controlId: 'runbook-operator' });
  };

  const buildSafeDashboardActions = () => {
    const safeActions = [
      ...safeShellActions,
      {
        id: 'intelligence-stage',
        label: 'Stage Scenario Packet',
        source: 'local-packet-stage',
        run: (options = {}) => {
          if (!activeScenario) throw new Error('No active scenario is available to stage.');
          stageScenario({ keepFocus: options.keepFocus });
          return { tone: 'success', detail: activeScenario.label };
        },
        summarize: result => `Dashboard Scenario Brief staged for ${result?.detail || 'the active scenario'}`
      },
      { id: 'intelligence-audit', label: 'Run Control Audit', run: runControlAudit },
      {
        id: 'action-receipt',
        label: 'Stage Action Receipt',
        source: 'local-packet-stage',
        run: (options = {}) => {
          stageActionReceipt({ keepFocus: options.keepFocus });
          return { tone: 'success', detail: latestCommand?.title || 'current command journal' };
        },
        summarize: result => `Action receipt staged from ${result?.detail || 'the command journal'}`
      },
      { id: 'button-sweep', label: 'Run Button Sweep', run: runButtonSweep },
      { id: 'break-test-lab', label: 'Run Break Test', run: runBreakTest },
      {
        id: 'bridge-probe',
        label: 'Run Live Bridge Probe',
        source: 'public-route-probe',
        run: runLiveBridgeProbe,
        summarize: result => `${result?.passCount || 0}/${result?.totalCount || 0} public routes passed; avg ${result?.averageMs || 0}ms`
      },
      { id: 'proof-replay-lab', label: 'Run Proof Replay', run: runProofReplay },
      {
        id: 'proof-sweep',
        label: 'Stage Proof Sweep',
        source: 'local-packet-stage',
        run: (options = {}) => {
          stageProofSweep({ keepFocus: options.keepFocus });
          return { tone: 'success', detail: `${proofCoverageRows.length || 'current'} proof groups` };
        },
        summarize: result => `Dashboard Proof Sweep packet staged from ${result?.detail || 'current audit coverage'}`
      },
      { id: 'control-pulse', label: 'Start Control Pulse', run: startControlPulse },
      { id: 'proof-runner', label: 'Start Proof Runner', run: startProofRunner },
      { id: 'command-brain', label: 'Check Brain Move', run: checkBrainMove },
      { id: 'simulation-deck', label: 'Apply Simulation Brain', run: applySuggestedSimulation },
      { id: 'runbook-operator', label: 'Start Runbook', run: startRunbook }
    ].filter(action => SAFE_PROOF_BATCH_CONTROL_IDS.includes(action.id));
    return safeActions;
  };

  const buildRemediationSafeActions = () => [
    ...buildSafeDashboardActions(),
    {
      id: CONTROL_PROOF_SAFE_BATCH_ACTION_ID,
      label: 'Run Proof Safe Batch',
      source: 'local-proof-batch',
      run: async () => {
        const batch = await runProofRunnerSafeBatch();
        return {
          tone: batch.failureCount > 0 ? 'danger' : batch.warningCount > 0 ? 'warn' : 'success',
          detail: `${batch.afterProvenCount}/${DASHBOARD_CONTROL_CONTRACTS.length} projected controls`,
          batch
        };
      },
      summarize: result => {
        const batch = result?.batch || {};
        return `Proof Runner Safe Batch projected ${batch.afterProvenCount || 0}/${DASHBOARD_CONTROL_CONTRACTS.length} controls with ${batch.successCount || 0}/${batch.totalCount || 0} safe checks.`;
      }
    }
  ];

  const runProofRunnerSafeBatch = async () => {
    const beforeProofMap = buildControlProofMap(commandJournal);
    const controlById = new Map(DASHBOARD_CONTROL_CONTRACTS.map(control => [control.id, control]));
    const safeActions = buildSafeDashboardActions();
    const rows = [];
    for (const action of safeActions) {
      const { row } = await runSafeDashboardAction(action, controlById);
      rows.push(row);
    }
    const successRows = rows.filter(row => row.tone === 'success');
    const successCount = successRows.length;
    const warningCount = rows.filter(row => row.tone === 'warn' || row.tone === 'info').length;
    const failureCount = rows.filter(row => row.tone === 'danger').length;
    const projectedProofIds = new Set(beforeProofMap.keys());
    successRows
      .forEach(row => projectedProofIds.add(row.id));
    const publicRouteRows = rows.filter(row => row.source === 'public-route-probe');
    const packetStageRows = rows.filter(row => row.source === 'local-packet-stage');
    const shellRouteRows = rows.filter(row => row.source === 'local-shell-route');
    const localPreviewRows = rows.filter(row => row.source === 'local-preview-builder');
    const localPanelRows = rows.filter(row => row.source === 'local-panel-action');
    const localCommsRows = rows.filter(row => row.source === 'local-comms-review');
    const batch = {
      ranAt: new Date().toISOString(),
      rows,
      totalCount: rows.length,
      successCount,
      warningCount,
      failureCount,
      beforeProvenCount: beforeProofMap.size,
      afterProvenCount: projectedProofIds.size,
      newProofIds: successRows.filter(row => !beforeProofMap.has(row.id)).map(row => row.id),
      publicRouteCount: publicRouteRows.length,
      packetStageCount: packetStageRows.length,
      shellRouteCount: shellRouteRows.length,
      localPreviewCount: localPreviewRows.length,
      localPanelActionCount: localPanelRows.length,
      localCommsReviewCount: localCommsRows.length,
      safeControlIds: rows.map(row => row.id)
    };
    setProofBatch(batch);
    setMode('audit');
    setAuditFilter('proof');
    onCommandEvent(
      'Proof runner safe batch',
      `${successCount}/${rows.length} safe checks exercised; shell routes ${shellRouteRows.length}; local previews ${localPreviewRows.length}; local panel actions ${localPanelRows.length}; local Comms reviews ${localCommsRows.length}; public probes ${publicRouteRows.length}; local packet stages ${packetStageRows.length}; protected routes skipped`,
      failureCount > 0 || warningCount > 0 ? 'warn' : 'success',
      { controlId: 'proof-runner' }
    );
    if (packetStageRows.length > 0 || shellRouteRows.length > 0 || localPreviewRows.length > 0 || localPanelRows.length > 0 || localCommsRows.length > 0) {
      onFocusChange('overview', { controlId: 'proof-runner' });
    }
    if (typeof window !== 'undefined') {
      window.setTimeout(() => {
        proofBatchRef.current?.scrollIntoView({ block: 'start', inline: 'nearest' });
      }, 420);
    }
    return batch;
  };

  const stageProofBatchPacket = async () => {
    const batch = proofBatch || await runProofRunnerSafeBatch();
    const packet = [
      '# Dashboard Safe Proof Batch',
      '',
      `- ran_at: ${batch.ranAt}`,
      `- safe_controls: ${batch.successCount}/${batch.totalCount}`,
      `- warnings: ${batch.warningCount || 0}`,
      `- failures: ${batch.failureCount}`,
      `- before_proven_controls: ${batch.beforeProvenCount}/${DASHBOARD_CONTROL_CONTRACTS.length}`,
      `- projected_proven_controls: ${batch.afterProvenCount}/${DASHBOARD_CONTROL_CONTRACTS.length}`,
      `- newly_proven_controls: ${batch.newProofIds.length ? batch.newProofIds.join(', ') : 'none'}`,
      `- protected_routes_called: no`,
      `- public_routes_called: ${batch.publicRouteCount > 0 ? BRIDGE_PROBE_ENDPOINTS.map(endpoint => endpoint.path).join(', ') : 'no'}`,
      `- local_packet_stages: ${batch.packetStageCount || 0}`,
      `- local_shell_routes: ${batch.shellRouteCount || 0}`,
      `- local_preview_builders: ${batch.localPreviewCount || 0}`,
      `- local_panel_actions: ${batch.localPanelActionCount || 0}`,
      `- local_comms_reviews: ${batch.localCommsReviewCount || 0}`,
      `- chat_send_called: no`,
      `- focus_restored: overview`,
      '',
      '## Exercised Controls',
      ...batch.rows.map(row => `- ${row.tone.toUpperCase()} / ${row.id} / ${row.label} / ${row.state} / source: ${row.source} / observed: ${row.observed} / expect: ${row.expected}`),
      '',
      '## Guardrail',
      '- This batch only exercises local dashboard controllers that already emit explicit controlId proof events.',
      '- Shell routes are limited to local focus changes and review-packet staging from existing dashboard handlers.',
      '- Local preview builders create review packets from current dashboard state without calling protected routes.',
      '- Local panel actions stage bounded review packets from child-panel state without launching workers or sending chat.',
      '- Local Comms reviews create packet-intelligence verdict packets without sending chat.',
      '- Local packet stages only write review packets into Comms and then return focus to the intelligence lane.',
      '- The bridge probe calls public, non-mutating routes only; no protected route, publish action, worker dispatch, or chat send is executed.',
      '- It does not prove queued target controls that require manual selection, protected live routes, worker dispatch, publish, or chat send.',
      '- Remaining proof gaps still require direct interaction with the named target controls.'
    ].join('\n');
    onStagePacket(packet, 'Safe proof batch staged', { controlId: 'proof-runner' });
  };

  return (
    <Panel
      title="Command Intelligence"
      meta={`${brief.priority} - ${activeFocus}`}
      tone={brief.priorityTone}
      focus="overview"
      activeFocus={activeFocus}
      className="intelligence-panel"
      actions={
        <div className="filter-cluster intelligence-modes">
          {modes.map(([value, label]) => (
            <button
              className={mode === value ? 'active' : ''}
              type="button"
              key={value}
              data-control-ids={
                value === 'plan'
                  ? 'command-brain intelligence-audit'
                  : value === 'evidence'
                    ? 'action-receipt intelligence-audit'
                    : value === 'audit'
                      ? 'intelligence-audit proof-sweep'
                      : 'intelligence-stage intelligence-audit'
              }
              data-control-intent={`Switch Command Intelligence to ${label}`}
              onClick={() => selectMode(value)}
            >
              {label}
            </button>
          ))}
        </div>
      }
    >
      <div className={`intelligence-body mode-${mode}`}>
        <div className="intelligence-brief">
          <div className="intelligence-score">
            <StatusPill tone={brief.priorityTone}>{brief.priority}</StatusPill>
            <strong>{brief.healthScore}</strong>
            <span>score</span>
          </div>
          <strong>{brief.headline}</strong>
          <p>{brief.summary}</p>
          <em>{modeCopy}</em>
          <button className="secondary-action scenario-stage" type="button" data-control-id="intelligence-stage" onClick={stageScenario}>
            Stage Scenario
          </button>
          <div className={`action-receipt ${actionReceiptTone}`}>
            <div className="action-receipt-head">
              <div>
                <span>Action Receipt</span>
                <strong>{latestCommand?.title || 'No action recorded'}</strong>
                <em>{latestCommand?.detail || 'Use a dashboard control to create a visible receipt.'}</em>
              </div>
              <StatusPill tone={actionReceiptTone}>{actionReceiptTone}</StatusPill>
            </div>
            <div className="action-receipt-grid">
              <span><strong>{activeFocus || 'overview'}</strong> lane</span>
              <span><strong>{actionReceiptProofLabel}</strong> proof</span>
              <span><strong>{latestCommand ? formatActionTime(latestCommand.time) : '--'}</strong> time</span>
              <span><strong>{actionReceiptProgressLabel}</strong> proven</span>
            </div>
            <div className={`action-receipt-coach ${actionReceiptNextControl ? 'warn' : 'success'}`}>
              <div>
                <span>Next Proof Target</span>
                <strong>{actionReceiptNextControl ? `${actionReceiptNextControl.surface}: ${actionReceiptNextControl.action}` : 'All tracked controls proven'}</strong>
                <em>{actionReceiptNextControl ? actionReceiptNextControl.target : 'No unproven dashboard control remains in this session.'}</em>
              </div>
              <p>{actionReceiptNextControl ? actionReceiptNextControl.expected : 'The command journal has explicit proof events for every tracked control contract.'}</p>
            </div>
            <div className="action-receipt-trail">
              {actionReceiptTrail.map(row => (
                <span className={row.tone || 'info'} key={row.id}>
                  <strong>{row.title}</strong>
                  <em>{row.detail}</em>
                </span>
              ))}
            </div>
            <div className="action-receipt-actions">
              <button className="secondary-action" type="button" data-control-id="action-receipt" onClick={openActionReceiptJournal}>
                Trace Journal
              </button>
              <button className="secondary-action" type="button" data-control-id="action-receipt" onClick={stageActionReceipt}>
                Stage Receipt
              </button>
              <button className="secondary-action" type="button" data-control-id="action-receipt" onClick={openActionReceiptNextProof}>
                Open Next Proof
              </button>
              <button className="secondary-action" type="button" data-control-id="action-receipt" onClick={stageActionReceiptNextProof}>
                Stage Next Proof
              </button>
            </div>
          </div>
          <div className={`button-sweep ${buttonSweepTone}`}>
            <div className="button-sweep-head">
              <div>
                <span>Button Sweep</span>
                <strong>{buttonSweepHeadline}</strong>
                <em>{buttonSweepSummary}</em>
              </div>
              <StatusPill tone={buttonSweepTone}>{buttonSweep ? buttonSweepTone : 'run'}</StatusPill>
            </div>
            <div className="button-sweep-grid">
              <span><strong>{buttonSweep?.total ?? '--'}</strong> buttons</span>
              <span><strong>{buttonSweep?.issueCount ?? '--'}</strong> risks</span>
              <span><strong>{buttonSweep?.disabledCount ?? '--'}</strong> disabled</span>
              <span><strong>{buttonSweep?.sectionCount ?? '--'}</strong> sections</span>
            </div>
            <div className="button-sweep-list">
              {buttonSweep ? (
                buttonSweepRows.map((row, index) => (
                  <span className={row.tone || (row.issue ? 'danger' : row.reason ? 'warn' : 'info')} key={`${row.section}-${row.label || row.total}-${row.reason || row.issue || row.detail || index}`}>
                    <strong>{row.label || row.section}</strong>
                    <em>{row.detail || (row.issue ? `${row.section} / ${row.issue} / ${row.size}` : row.reason ? `${row.section} / ${row.reason} / ${row.size}` : `${row.total} buttons / ${row.disabled} disabled`)}</em>
                  </span>
                ))
              ) : (
                <span className="info">
                  <strong>Rendered surface not measured</strong>
                  <em>Run Sweep reads visible buttons after layout and reports label, hitbox, viewport, and disabled-reason risks.</em>
                </span>
              )}
            </div>
            <div className="button-sweep-actions">
              <button className="secondary-action" type="button" data-control-id="button-sweep" onClick={runButtonSweep}>
                Run Sweep
              </button>
              <button className="secondary-action" type="button" data-control-id="button-sweep" onClick={openButtonSweepAudit}>
                Open Audit
              </button>
              <button className="secondary-action" type="button" data-control-id="button-sweep" onClick={stageButtonSweep}>
                Stage Sweep
              </button>
            </div>
          </div>
          <div className={`break-test-lab ${breakTestTone}`}>
            <div className="break-test-head">
              <div>
                <span>Break Test Lab</span>
                <strong>{breakTestHeadline}</strong>
                <em>{breakTestSummary}</em>
              </div>
              <StatusPill tone={breakTestTone}>{breakTest ? `${breakTest.score}%` : 'run'}</StatusPill>
            </div>
            <div className="break-test-grid">
              <span><strong>{breakTest?.failCount ?? '--'}</strong> fail</span>
              <span><strong>{breakTest?.warnCount ?? '--'}</strong> warn</span>
              <span><strong>{breakTest?.passCount ?? '--'}</strong> pass</span>
              <span><strong>{breakTest?.weakestRow?.state || '--'}</strong> weakest</span>
            </div>
            <div className={`break-test-weakest ${breakTest?.weakestRow?.tone || 'info'}`}>
              <div>
                <span>Weakest check</span>
                <strong>{breakTest?.weakestRow?.label || 'No break test run'}</strong>
                <em>{breakTest?.weakestRow?.detail || 'Run Break Test to generate an adversarial readiness report.'}</em>
              </div>
              <p>{breakTest?.weakestRow?.action || 'The lab will choose the first failure or warning and route you to the responsible dashboard lane.'}</p>
            </div>
            <div className="break-test-list">
              {breakTestRows.length > 0 ? (
                breakTestRows.map(row => (
                  <span className={row.tone || 'info'} key={row.id}>
                    <strong>{row.label}</strong>
                    <em>{row.state} / {row.detail}</em>
                  </span>
                ))
              ) : (
                <span className="info">
                  <strong>Adversarial report pending</strong>
                  <em>Run Break Test to combine DOM, control-proof, sync, evidence, model, contract, and Comms checks.</em>
                </span>
              )}
            </div>
            <div className={`remediation-queue ${remediationTone}`}>
              <div className="remediation-head">
                <div>
                  <span>Remediation queue</span>
                  <strong>{breakTestRemediationRows.length ? `${breakTestRemediationRows.length} live targets` : breakTest ? 'No open targets' : 'Not built'}</strong>
                  <em>{remediationSummary}</em>
                </div>
                <StatusPill tone={remediationTone}>{breakTest ? remediationTone : 'run'}</StatusPill>
              </div>
              <div className="remediation-list">
                {breakTestRemediationRows.length > 0 ? (
                  breakTestRemediationRows.slice(0, 5).map(row => (
                    <button
                      className={`remediation-row ${row.tone || 'warn'}`}
                      type="button"
                      key={row.id}
                      data-control-id="break-test-lab"
                      data-control-intent={`Open ${row.label} remediation target`}
                      onClick={() => { void openRemediationRow(row); }}
                    >
                      <span>{row.priority} / {row.owner}</span>
                      <strong>{row.label}</strong>
                      <em>{row.action}</em>
                      <b>{row.exitCriteria}</b>
                    </button>
                  ))
                ) : (
                  <span className={breakTest ? 'success' : 'info'}>
                    <strong>{breakTest ? 'No remediation rows' : 'Queue pending'}</strong>
                    <em>{breakTest ? 'The latest Break Test has no failed or warning rows.' : 'Run Break Test to rank sync, evidence, controls, model, contract, and Comms blockers.'}</em>
                  </span>
                )}
              </div>
              <div className="remediation-actions">
                <button className="secondary-action" type="button" data-control-id="break-test-lab" onClick={() => { void runBreakTest(); }}>
                  Build Queue
                </button>
                <button
                  className="secondary-action"
                  type="button"
                  data-control-id="break-test-lab"
                  onClick={() => { void openRemediationRow(breakTestRemediationRows[0]); }}
                  disabled={breakTestRemediationRows.length === 0}
                  data-disabled-reason={breakTestRemediationRows.length === 0 ? 'Run Break Test and keep at least one failed or warning row before opening a remediation target.' : undefined}
                  title={breakTestRemediationRows.length === 0 ? 'Run Break Test and keep at least one failed or warning row before opening a remediation target.' : undefined}
                >
                  Open First
                </button>
                <button
                  className="secondary-action"
                  type="button"
                  data-control-id="break-test-lab"
                  onClick={() => { void runRemediationSafeStep(breakTestRemediationRows[0]); }}
                  disabled={breakTestRemediationRows.length === 0}
                  data-disabled-reason={breakTestRemediationRows.length === 0 ? 'Run Break Test and keep at least one failed or warning row before running a safe remediation step.' : undefined}
                  title={breakTestRemediationRows.length === 0 ? 'Run Break Test and keep at least one failed or warning row before running a safe remediation step.' : undefined}
                >
                  Run Safe Step
                </button>
                <button
                  className="secondary-action"
                  type="button"
                  data-control-id="break-test-lab"
                  onClick={() => { void runRemediationSafePlan(); }}
                  disabled={breakTestRemediationRows.length === 0}
                  data-disabled-reason={breakTestRemediationRows.length === 0 ? 'Run Break Test and keep at least one failed or warning row before running a safe remediation plan.' : undefined}
                  title={breakTestRemediationRows.length === 0 ? 'Run Break Test and keep at least one failed or warning row before running a safe remediation plan.' : undefined}
                >
                  Run Safe Plan
                </button>
                <button className="secondary-action" type="button" data-control-id="break-test-lab" onClick={() => { void stageRemediationQueue(); }}>
                  Stage Queue
                </button>
              </div>
              {remediationRun && (
                <div className={`remediation-run ${remediationRunTone}`} ref={remediationRunRef}>
                  <div className="remediation-run-head">
                    <div>
                      <span>{remediationRunIsPlan ? 'Safe plan receipt' : 'Safe step receipt'}</span>
                      <strong>{remediationRun.targetPriority} / {remediationRun.targetLabel}</strong>
                      <em>{remediationRunSummary}</em>
                    </div>
                    <StatusPill tone={remediationRunTone}>{remediationRunTone}</StatusPill>
                  </div>
                  <div className="remediation-run-list">
                    {remediationRun.rows.slice(0, 4).map(row => (
                      <span className={row.tone || 'info'} key={row.id}>
                        <strong>{row.label}</strong>
                        <em>{row.state} / {row.observed}</em>
                      </span>
                    ))}
                  </div>
                  <div className="remediation-run-actions">
                    <button className="secondary-action" type="button" data-control-id="break-test-lab" onClick={() => { void stageRemediationRun(); }}>
                      {remediationRunIsPlan ? 'Stage Safe Plan' : 'Stage Safe Step'}
                    </button>
                    <button className="secondary-action" type="button" data-control-id="break-test-lab" onClick={() => { void runBreakTest(); }}>
                      Rerun Break Test
                    </button>
                  </div>
                </div>
              )}
            </div>
            <div className="break-test-actions">
              <button className="secondary-action" type="button" data-control-id="break-test-lab" onClick={() => { void runBreakTest(); }}>
                Run Break Test
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="break-test-lab"
                onClick={() => { void openBreakTestWeakest(); }}
                disabled={!breakTest}
                data-disabled-reason={!breakTest ? 'Run Break Test before opening the weakest readiness check.' : undefined}
                title={!breakTest ? 'Run Break Test before opening the weakest readiness check.' : undefined}
              >
                Open Weakest
              </button>
              <button className="secondary-action" type="button" data-control-id="break-test-lab" onClick={() => { void stageBreakTest(); }}>
                Stage Break Test
              </button>
            </div>
          </div>
          <div className={`bridge-probe ${bridgeProbeTone}`}>
            <div className="bridge-probe-head">
              <div>
                <span>Live Bridge Probe</span>
                <strong>{bridgeProbeHeadline}</strong>
                <em>{bridgeProbeSummary}</em>
              </div>
              <StatusPill tone={bridgeProbeTone}>{bridgeProbe ? `${bridgeProbe.passCount}/${bridgeProbe.totalCount}` : 'run'}</StatusPill>
            </div>
            <div className="bridge-probe-grid">
              <span><strong>{bridgeProbe?.passCount ?? '--'}</strong> pass</span>
              <span><strong>{bridgeProbe?.warnCount ?? '--'}</strong> warn</span>
              <span><strong>{bridgeProbe?.failCount ?? '--'}</strong> fail</span>
              <span><strong>{bridgeProbe?.averageMs ?? '--'}</strong> avg ms</span>
            </div>
            <div className={`bridge-probe-weakest ${bridgeProbe?.weakestRow?.tone || 'info'}`}>
              <div>
                <span>Weakest live route</span>
                <strong>{bridgeProbe?.weakestRow?.label || 'No probe run'}</strong>
                <em>{bridgeProbe?.weakestRow?.detail || 'Run Probe to test the bridge, dashboard contract, VM relay, and model-loop diagnostic routes.'}</em>
              </div>
              <p>{bridgeProbe?.weakestRow?.action || 'Only public safe routes are probed; protected routes and mutating actions stay untouched.'}</p>
            </div>
            <div className="bridge-probe-list">
              {bridgeProbeRows.length > 0 ? (
                bridgeProbeRows.map(row => (
                  <span className={row.tone || 'info'} key={row.id}>
                    <strong>{row.label}</strong>
                    <em>{row.state} / HTTP {row.status} / {row.latencyMs}ms / {row.detail}</em>
                  </span>
                ))
              ) : (
                <span className="info">
                  <strong>Live route evidence pending</strong>
                  <em>Run Probe calls /ping, /health, /dashboard/status, /vm/status, and /chat/test in parallel.</em>
                </span>
              )}
            </div>
            <div className="bridge-probe-actions">
              <button className="secondary-action" type="button" data-control-id="bridge-probe" onClick={() => { void runLiveBridgeProbe(); }}>
                Run Probe
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="bridge-probe"
                onClick={openBridgeProbeWeakest}
                disabled={!bridgeProbe}
                data-disabled-reason={!bridgeProbe ? 'Run Live Bridge Probe before opening the weakest route.' : undefined}
                title={!bridgeProbe ? 'Run Live Bridge Probe before opening the weakest route.' : undefined}
              >
                Open Weakest
              </button>
              <button className="secondary-action" type="button" data-control-id="bridge-probe" onClick={() => { void stageBridgeProbe(); }}>
                Stage Probe
              </button>
            </div>
          </div>
          <div className={`proof-replay ${proofReplayTone}`}>
            <div className="proof-replay-head">
              <div>
                <span>Proof Replay Lab</span>
                <strong>{proofReplayHeadline}</strong>
                <em>{proofReplaySummary}</em>
              </div>
              <StatusPill tone={proofReplayTone}>{proofReplay ? `${proofReplay.exercisedCount} checks` : 'run'}</StatusPill>
            </div>
            <div className="proof-replay-grid">
              <span><strong>{proofReplay?.exercisedCount ?? '--'}</strong> safe</span>
              <span><strong>{proofReplay?.dangerCount ?? '--'}</strong> fail</span>
              <span><strong>{proofReplay?.warnCount ?? '--'}</strong> warn</span>
              <span><strong>{proofReplay?.nextQueueCount ?? '--'}</strong> queued</span>
            </div>
            <div className={`proof-replay-target ${proofReplay?.nextTarget?.tone || 'info'}`}>
              <div>
                <span>Next proof target</span>
                <strong>{proofReplay?.nextTarget?.label || 'No replay run'}</strong>
                <em>{proofReplay?.nextTarget?.target || 'Run Replay to choose the next unproven control and open its lane.'}</em>
              </div>
              <p>{proofReplay?.nextTarget?.expected || 'Safe replay records only bounded local proof, then leaves the remaining target for direct interaction.'}</p>
            </div>
            <div className="proof-replay-list">
              {proofReplayRows.length > 0 ? (
                proofReplayRows.map(row => (
                  <span className={row.tone || 'info'} key={row.controlId}>
                    <strong>{row.label}</strong>
                    <em>{row.state} / {row.detail}</em>
                  </span>
                ))
              ) : (
                <span className="info">
                  <strong>Replay proof pending</strong>
                  <em>Run Replay performs safe local handlers and records explicit control IDs in the command journal.</em>
                </span>
              )}
            </div>
            <div className="proof-replay-actions">
              <button className="secondary-action" type="button" data-control-id="proof-replay-lab" onClick={() => { void runProofReplay(); }}>
                Run Replay
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="proof-replay-lab"
                onClick={() => { void openProofReplayTarget(); }}
                disabled={!proofReplay}
                data-disabled-reason={!proofReplay ? 'Run Replay before opening the next proof target.' : undefined}
                title={!proofReplay ? 'Run Replay before opening the next proof target.' : undefined}
              >
                Open Target
              </button>
              <button className="secondary-action" type="button" data-control-id="proof-replay-lab" onClick={() => { void stageProofReplay(); }}>
                Stage Replay
              </button>
            </div>
          </div>
          {activeBrain && (
            <div className={`command-brain ${activeBrain.tone || 'info'}`}>
              <div className="command-brain-head">
                <span>Command Brain</span>
                <strong>{activeBrain.label}</strong>
                <em>{activeBrain.detail}</em>
              </div>
              <div className="brain-meter" aria-label="Command brain confidence">
                <span style={{ width: `${activeBrain.confidence}%` }} />
              </div>
              <div className="brain-queue">
                {brainItems.slice(0, 4).map(item => (
                  <button
                    className={`brain-move ${item.tone || 'info'} ${activeBrain.id === item.id ? 'selected' : ''}`}
                    type="button"
                    key={item.id}
                    data-control-id="command-brain"
                    data-control-intent={`Select ${item.label} brain move`}
                    onClick={() => selectBrainMove(item)}
                  >
                    <span>{item.state}</span>
                    <strong>{item.label}</strong>
                  </button>
                ))}
              </div>
              <div className="brain-reasons">
                {activeBrain.reasons.slice(0, 3).map(reason => (
                  <span key={reason}>{reason}</span>
                ))}
              </div>
              <div className="brain-actions">
                <button className="secondary-action" type="button" data-control-id="command-brain" onClick={openBrainMove}>
                  Open Move
                </button>
                <button className="secondary-action" type="button" data-control-id="command-brain" onClick={checkBrainMove}>
                  Check Move
                </button>
                <button className="secondary-action" type="button" data-control-id="command-brain" onClick={stageBrainMove}>
                  Stage Move
                </button>
              </div>
            </div>
          )}
          <div className={`control-pulse ${controlPulseTone}`}>
            <div className="control-pulse-head">
              <div>
                <span>Control Pulse</span>
                <strong>{controlPulseSummary}</strong>
                <em>{controlPulseInstruction}</em>
              </div>
              <StatusPill tone={controlPulseTone}>
                {controlAudit ? `${controlPulseProgress}%` : 'start'}
              </StatusPill>
            </div>
            <div className="control-pulse-meter" aria-label="Control pulse proof progress">
              <span style={{ width: `${controlPulseProgress}%` }} />
            </div>
            <div className="control-pulse-target">
              <div>
                <span>Next button proof</span>
                <strong>{controlPulseTarget?.label || 'No target selected'}</strong>
                <em>{controlPulseTarget ? `${controlPulseTarget.focus || 'overview'} / ${controlPulseTarget.state}` : 'Run the pulse to build a queue.'}</em>
              </div>
              <p>{controlPulseTarget?.detail || latestProofEvent?.detail || 'The dashboard will only count explicit control events as proof.'}</p>
            </div>
            <div className="control-pulse-queue">
              {controlPulseQueue.length === 0 ? (
                <span>{controlAudit ? 'No queued target after the current control.' : 'No pulse queue yet.'}</span>
              ) : (
                controlPulseQueue.map(row => (
                  <button
                    className={`pulse-queue-row ${row.tone || 'warn'}`}
                    type="button"
                    key={row.id}
                    data-control-id="control-pulse"
                    data-control-intent={`Select ${row.label} pulse proof target`}
                    onClick={() => selectDrillTarget(row)}
                  >
                    <span>{row.focus || 'overview'}</span>
                    <strong>{row.label}</strong>
                  </button>
                ))
              )}
            </div>
            <div className="control-pulse-actions">
              <button className="secondary-action" type="button" data-control-id="control-pulse" onClick={startControlPulse}>
                Start Pulse
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="control-pulse"
                onClick={openControlPulseTarget}
                disabled={!controlPulseTarget && !controlAudit}
                data-disabled-reason={!controlPulseTarget && !controlAudit ? 'Run Start Pulse or Audit View before opening the next proof target.' : undefined}
                title={!controlPulseTarget && !controlAudit ? 'Run Start Pulse or Audit View before opening the next proof target.' : undefined}
              >
                Open Next
              </button>
              <button className="secondary-action" type="button" data-control-id="control-pulse" onClick={stageControlPulse}>
                Stage Pulse
              </button>
              <button className="secondary-action" type="button" data-control-id="control-pulse" onClick={openControlPulseAudit}>
                Audit View
              </button>
            </div>
          </div>
          <div className={`control-pulse proof-runner ${proofRunnerTone}`}>
            <div className="control-pulse-head">
              <div>
                <span>Proof Runner</span>
                <strong>{proofRunnerSummary}</strong>
                <em>{proofRunnerInstruction}</em>
              </div>
              <StatusPill tone={proofRunnerTone}>
                {controlAudit ? `${proofRunnerProgress}%` : 'queue'}
              </StatusPill>
            </div>
            <div className="control-pulse-meter" aria-label="Proof runner progress">
              <span style={{ width: `${proofRunnerProgress}%` }} />
            </div>
            <div className="control-pulse-target">
              <div>
                <span>Active proof target</span>
                <strong>{proofRunnerActiveRow?.label || 'No active proof target'}</strong>
                <em>{proofRunnerActiveRow ? `${proofRunnerActiveRow.focus || 'overview'} / required proof ${proofRunnerActiveRow.controlId}` : 'Start Run builds a six-control queue.'}</em>
              </div>
              <p>{proofRunnerActiveRow?.detail || latestProofEvent?.detail || 'Open Target only moves the dashboard. The target button itself must emit the matching proof event.'}</p>
            </div>
            <div className="control-pulse-queue proof-runner-queue">
              {proofRunnerQueueRows.length === 0 ? (
                <span>{controlAudit ? 'No unproven controls are queued.' : 'No runner queue yet.'}</span>
              ) : (
                proofRunnerQueueRows.map(row => {
                  const state = row.proof
                    ? 'proven'
                    : row.controlId === proofRunnerActiveRow?.controlId
                      ? 'active'
                      : proofRunnerSkippedSet.has(row.controlId)
                        ? 'skipped'
                        : 'queued';
                  const tone = row.proof ? 'success' : state === 'active' ? 'warn' : row.tone || 'warn';
                  return (
                    <button
                      className={`pulse-queue-row ${tone}`}
                      type="button"
                      key={row.controlId}
                      data-control-id="proof-runner"
                      data-control-intent={`Select ${row.label} proof runner target`}
                      onClick={() => selectDrillTarget(row)}
                    >
                      <span>{state} / {row.focus || 'overview'}</span>
                      <strong>{row.label}</strong>
                    </button>
                  );
                })
              )}
            </div>
            <div className={`proof-batch ${proofBatchTone}`} ref={proofBatchRef}>
              <div>
                <span>Safe proof batch</span>
                <strong>{proofBatch ? `${proofBatch.successCount}/${proofBatch.totalCount} safe checks` : 'Not run'}</strong>
                <em>{proofBatchSummary}</em>
              </div>
              <div className="proof-batch-list">
                {proofBatch ? (
                  proofBatch.rows.map(row => (
                    <span className={row.tone} key={row.id} title={`${row.label}: ${row.observed}`}>
                      <strong>{row.id}</strong>
                      <em>{row.state} / {row.source}</em>
                    </span>
                  ))
                ) : (
                  <span className="info">
                    <strong>Guarded local batch</strong>
                    <em>Nav, mission, TIU/Sync local previews, Comms local review, scenario packet, audit, receipt, sweep, break test, public bridge probe, replay, proof sweep, pulse, runner, brain, simulator, runbook, gate plan, and header strip only.</em>
                  </span>
                )}
              </div>
            </div>
            <div className="control-pulse-actions">
              <button className="secondary-action" type="button" data-control-id="proof-runner" onClick={startProofRunner}>
                Start Run
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="proof-runner"
                onClick={openProofRunnerTarget}
                disabled={!proofRunnerActiveRow && !controlAudit}
                data-disabled-reason={!proofRunnerActiveRow && !controlAudit ? 'Start a proof run or run Audit before opening a target.' : undefined}
                title={!proofRunnerActiveRow && !controlAudit ? 'Start a proof run or run Audit before opening a target.' : undefined}
              >
                Open Target
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="proof-runner"
                onClick={advanceProofRunnerTarget}
                disabled={!proofRunnerActiveRow && !controlAudit}
                data-disabled-reason={!proofRunnerActiveRow && !controlAudit ? 'Start a proof run before advancing targets.' : undefined}
                title={!proofRunnerActiveRow && !controlAudit ? 'Start a proof run before advancing targets.' : undefined}
              >
                Next Target
              </button>
              <button className="secondary-action" type="button" data-control-id="proof-runner" onClick={stageProofRunner}>
                Stage Run
              </button>
              <button className="secondary-action" type="button" data-control-id="proof-runner" onClick={() => { void runProofRunnerSafeBatch(); }}>
                Safe Batch
              </button>
              <button className="secondary-action" type="button" data-control-id="proof-runner" onClick={() => { void stageProofBatchPacket(); }}>
                Stage Batch
              </button>
            </div>
          </div>
          <div className={`decision-simulator ${projectedTone}`}>
            <div className="simulator-head">
              <div>
                <span>Decision simulator</span>
                <strong>{brief.healthScore}{' -> '}{projectedScore}</strong>
                <em>{brief.priority}{' -> '}{projectedPriority}; delta {projectionDelta >= 0 ? '+' : ''}{projectionDelta}</em>
              </div>
              <StatusPill tone={projectedTone}>{projectedPriority}</StatusPill>
            </div>
            <div className="simulation-toggle-grid">
              {simulationRows.map(row => (
                <button
                  className={`simulation-toggle ${row.tone || 'info'} ${simulationDraft[row.id] ? 'selected' : ''}`}
                  type="button"
                  key={row.id}
                  aria-pressed={simulationDraft[row.id]}
                  data-control-id="simulation-deck"
                  data-control-intent={`Toggle ${row.label} simulation gate`}
                  onClick={() => toggleSimulationGate(row)}
                >
                  <span>{simulationDraft[row.id] ? 'assumed' : row.state}</span>
                  <strong>{row.label}</strong>
                  <em>{row.needsWork ? row.detail : 'Already green; keep as verification evidence.'}</em>
                  <b>{simulationDraft[row.id] ? `+${row.impact}` : 'off'}</b>
                </button>
              ))}
            </div>
            <div className="simulation-sequence">
              <span>Next sequence</span>
              {simulationSequence.length === 0 ? (
                <strong>No open gates selected.</strong>
              ) : (
                simulationSequence.map((row, index) => (
                  <strong key={row.id}>{index + 1}. {row.label}: {row.sequence}</strong>
                ))
              )}
            </div>
            <div className="simulation-actions">
              <button className="secondary-action" type="button" data-control-id="simulation-deck" onClick={applySuggestedSimulation}>
                Apply Brain
              </button>
              <button className="secondary-action" type="button" data-control-id="simulation-deck" onClick={openSimulationLane}>
                Open Gate
              </button>
              <button className="secondary-action" type="button" data-control-id="simulation-deck" onClick={stageSimulationPlan}>
                Stage Sim
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="simulation-deck"
                onClick={resetSimulation}
                disabled={activeSimulationRows.length === 0}
                data-disabled-reason={activeSimulationRows.length === 0 ? 'Toggle an assumption or apply the brain suggestion before reset.' : undefined}
                title={activeSimulationRows.length === 0 ? 'Toggle an assumption or apply the brain suggestion before reset.' : undefined}
              >
                Reset
              </button>
            </div>
          </div>
          <div className={`operator-runbook ${runbookTone}`}>
            <div className="runbook-head">
              <div>
                <span>Operator runbook</span>
                <strong>{activeRunbookStep?.label || 'No step selected'}</strong>
                <em>{runbookDoneCount}/{runbookRows.length} done; {runbookHeldCount} held; {runbookProgress}% complete</em>
              </div>
              <StatusPill tone={runbookTone}>{runbookTone}</StatusPill>
            </div>
            <div className="runbook-progress" aria-label="Operator runbook progress">
              <span style={{ width: `${runbookProgress}%` }} />
            </div>
            <div className="runbook-step-list">
              {runbookRows.map(row => {
                const status = completedRunbookSet.has(row.id)
                  ? 'done'
                  : heldRunbookSet.has(row.id)
                    ? 'held'
                    : row.id === activeRunbookStep?.id
                      ? 'active'
                      : 'queued';
                return (
                  <button
                    className={`runbook-step ${row.tone || 'info'} ${status}`}
                    type="button"
                    key={row.id}
                    aria-pressed={row.id === activeRunbookStep?.id}
                    data-control-id="runbook-operator"
                    data-control-intent={`Select ${row.label} runbook step`}
                    onClick={() => selectRunbookStep(row)}
                  >
                    <span>{status}</span>
                    <strong>{row.label}</strong>
                    <em>{row.state} / {row.metric}</em>
                  </button>
                );
              })}
            </div>
            <div className={`runbook-active ${activeRunbookStep?.tone || 'info'}`}>
              <div>
                <span>Active step</span>
                <strong>{activeRunbookStep?.label || 'No active step'}</strong>
                <em>{activeRunbookStep?.focus || 'overview'}</em>
              </div>
              <p>{activeRunbookStep?.detail || 'Start the runbook to select the next dashboard gate.'}</p>
              <b>{activeRunbookStep?.intent || 'Open a step, collect evidence, then stage the runbook packet.'}</b>
            </div>
            <div className="runbook-actions">
              <button className="secondary-action" type="button" data-control-id="runbook-operator" onClick={startRunbook}>
                Start
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="runbook-operator"
                onClick={openRunbookStep}
                disabled={!activeRunbookStep}
                data-disabled-reason={!activeRunbookStep ? 'Start the runbook before opening the active step.' : undefined}
                title={!activeRunbookStep ? 'Start the runbook before opening the active step.' : undefined}
              >
                Open Step
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="runbook-operator"
                onClick={completeRunbookStep}
                disabled={!activeRunbookStep || completedRunbookSet.has(activeRunbookStep.id)}
                data-disabled-reason={!activeRunbookStep
                  ? 'Start the runbook before completing a step.'
                  : completedRunbookSet.has(activeRunbookStep.id)
                    ? 'Select a queued or active runbook step before marking another completion.'
                    : undefined}
                title={!activeRunbookStep
                  ? 'Start the runbook before completing a step.'
                  : completedRunbookSet.has(activeRunbookStep.id)
                    ? 'Select a queued or active runbook step before marking another completion.'
                    : undefined}
              >
                Complete
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="runbook-operator"
                onClick={holdRunbookStep}
                disabled={!activeRunbookStep}
                data-disabled-reason={!activeRunbookStep ? 'Start the runbook before holding a step.' : undefined}
                title={!activeRunbookStep ? 'Start the runbook before holding a step.' : undefined}
              >
                {activeRunbookStep && heldRunbookSet.has(activeRunbookStep.id) ? 'Resume' : 'Hold'}
              </button>
              <button className="secondary-action" type="button" data-control-id="runbook-operator" onClick={stageRunbookPacket}>
                Stage Book
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="runbook-operator"
                onClick={resetRunbook}
                disabled={runbookDoneCount === 0 && runbookHeldCount === 0}
                data-disabled-reason={runbookDoneCount === 0 && runbookHeldCount === 0 ? 'Complete or hold a runbook step before reset.' : undefined}
                title={runbookDoneCount === 0 && runbookHeldCount === 0 ? 'Complete or hold a runbook step before reset.' : undefined}
              >
                Reset
              </button>
            </div>
          </div>
        </div>
        <div className="intelligence-stage">
          {mode === 'diagnose' && (
            <div className="scenario-grid">
              {brief.scenarios.map(scenario => (
                <button
                  className={`scenario-card ${scenario.tone || 'info'} ${activeScenario?.id === scenario.id ? 'selected' : ''}`}
                  type="button"
                  key={scenario.id}
                  data-control-id="intelligence-stage"
                  data-control-intent={`Select ${scenario.label} scenario`}
                  onClick={() => selectScenario(scenario)}
                >
                  <span>{scenario.metric}</span>
                  <strong>{scenario.label}</strong>
                  <em>{scenario.detail}</em>
                </button>
              ))}
            </div>
          )}
          {mode === 'plan' && (
            <div className="decision-grid">
              <div className="decision-trace">
                {brief.decisionTrace.map(row => (
                  <div className={`decision-row ${row.tone || 'info'}`} key={row.id}>
                    <span>{row.label}</span>
                    <strong>{row.detail}</strong>
                  </div>
                ))}
              </div>
              <div className="intelligence-actions">
                {brief.recommendedActions.map(action => (
                  <button
                    className={`intelligence-action ${action.tone || 'info'}`}
                    type="button"
                    key={action.id}
                    data-control-id={action.packet ? 'intelligence-stage' : 'command-brain'}
                    data-control-intent={`Run ${action.label}`}
                    onClick={() => runBriefAction(action)}
                  >
                    <strong>{action.label}</strong>
                    <span>{action.detail}</span>
                  </button>
                ))}
                {activeScenario && (
                  <button
                    className={`intelligence-action ${activeScenario.tone || 'info'}`}
                    type="button"
                    data-control-id="intelligence-stage"
                    data-control-intent={`Open ${activeScenario.label} scenario lane`}
                    onClick={() => focusScenario(activeScenario)}
                  >
                    <strong>Open scenario lane</strong>
                    <span>{activeScenario.label}</span>
                  </button>
                )}
              </div>
            </div>
          )}
          {mode === 'evidence' && (
            <div className="evidence-grid">
              <div className="intelligence-signals">
                {brief.signals.map(signal => (
                  <div className={signal.tone} key={signal.label}>
                    <span>{signal.label}</span>
                    <strong>{signal.value}</strong>
                  </div>
                ))}
              </div>
              <div className="command-journal">
                {brief.recentActions.length === 0 ? (
                  <div className="empty-state">No local commands recorded yet.</div>
                ) : (
                  brief.recentActions.map(row => (
                    <div className={`journal-row ${row.tone || 'info'}`} key={row.id}>
                      <span>{formatActionTime(row.time)}</span>
                      <strong>{row.title}</strong>
                      <em>{row.detail}</em>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
          {mode === 'audit' && (
            <div className="control-audit">
              <div className={`control-audit-summary ${controlAudit?.tone || 'info'}`}>
                <div>
                  <span>Control audit</span>
                  <strong>{controlAudit ? `${controlAudit.provenCount}/${controlAudit.controlCount} controls proven` : 'Not run'}</strong>
                  <em>{controlAudit?.headline || 'Run the audit against this dashboard snapshot.'}</em>
                </div>
                {controlAudit && (
                  <div className="control-audit-metrics">
                    <span><strong>{controlAudit.controlCount}</strong> controls</span>
                    <span><strong>{controlAudit.packetCount}</strong> packets</span>
                    <span><strong>{controlAudit.focusCount}</strong> focus</span>
                    <span><strong>{controlAudit.provenCount}</strong> proven</span>
                  </div>
                )}
                <div className="control-audit-actions">
                  <button className="secondary-action" type="button" data-control-id="intelligence-audit" onClick={runControlAudit}>
                    Run Audit
                  </button>
                  <button
                    className="secondary-action"
                    type="button"
                    data-control-id="intelligence-audit"
                    onClick={stageControlAudit}
                    disabled={!controlAudit}
                    data-disabled-reason={!controlAudit ? 'Run Audit before staging a control-audit packet.' : undefined}
                    title={!controlAudit ? 'Run Audit before staging a control-audit packet.' : undefined}
                  >
                    Stage Audit
                  </button>
                  <button
                    className="secondary-action"
                    type="button"
                    data-control-id="intelligence-audit"
                    onClick={stageAuditRisk}
                    disabled={!controlAudit}
                    data-disabled-reason={!controlAudit ? 'Run Audit before staging a selected-risk packet.' : undefined}
                    title={!controlAudit ? 'Run Audit before staging a selected-risk packet.' : undefined}
                  >
                    Stage Risk
                  </button>
                  <button
                    className="secondary-action"
                    type="button"
                    data-control-id="intelligence-audit"
                    onClick={openAuditRisk}
                    disabled={!controlAudit}
                    data-disabled-reason={!controlAudit ? 'Run Audit before opening the highest-risk dashboard lane.' : undefined}
                    title={!controlAudit ? 'Run Audit before opening the highest-risk dashboard lane.' : undefined}
                  >
                    Open Risk
                  </button>
                </div>
              </div>
              {controlAudit && (
                <div className="control-audit-filter filter-cluster">
                  {[
                    ['risks', `Risks ${controlAudit.riskCount}`],
                    ['all', `All ${controlAudit.rows.length}`],
                    ['packets', `Packets ${controlAudit.packetCount}`],
                    ['focus', `Focus ${controlAudit.focusCount}`],
                    ['proof', `Unproven ${controlAudit.unprovenCount}`]
                  ].map(([value, label]) => (
                    <button
                      className={auditFilter === value ? 'active' : ''}
                      type="button"
                      key={value}
                      data-control-id="intelligence-audit"
                      data-control-intent={`Filter audit rows by ${value}`}
                      onClick={() => {
                        setAuditFilter(value);
                        onCommandEvent('Control audit filter changed', value, 'info', { controlId: 'intelligence-audit' });
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              )}
              {controlAudit && (
                <div className={`audit-drill ${controlAudit.unprovenCount > 0 ? 'warn' : 'success'}`}>
                  <div className="audit-drill-head">
                    <div>
                      <span>Proof drill</span>
                      <strong>{controlAudit.provenCount}/{controlAudit.provableCount} controls proven</strong>
                      <em>{drillProgress}% complete; proof only comes from explicit dashboard control events.</em>
                    </div>
                    <div className="audit-drill-meter" aria-label="Control proof drill progress">
                      <span style={{ width: `${drillProgress}%` }} />
                    </div>
                  </div>
                  <div className="audit-drill-target">
                    <div>
                      <span>Current target</span>
                      <strong>{drillTargetRow?.label || 'No unproven target'}</strong>
                      <em>{drillTargetRow ? `${drillTargetRow.state} -> ${drillTargetRow.focus || 'overview'}` : 'All tracked controls have proof in this session.'}</em>
                    </div>
                    <p>{drillTargetRow?.detail || latestProofEvent?.detail || 'Run the audit and start the drill to pick the next surface.'}</p>
                  </div>
                  <div className="audit-drill-guide">
                    {drillGuideRows.map(([label, value]) => (
                      <div key={label}>
                        <span>{label}</span>
                        <strong>{value}</strong>
                      </div>
                    ))}
                  </div>
                  <div className="audit-drill-actions">
                    <button className="secondary-action" type="button" data-control-id="intelligence-audit" onClick={startAuditDrill}>
                      Start Drill
                    </button>
                    <button
                      className="secondary-action"
                      type="button"
                      data-control-id="intelligence-audit"
                      onClick={openDrillTarget}
                      disabled={!drillTargetRow?.focus}
                      data-disabled-reason={!drillTargetRow?.focus ? 'Run Audit or Start Drill before opening a proof target.' : undefined}
                      title={!drillTargetRow?.focus ? 'Run Audit or Start Drill before opening a proof target.' : undefined}
                    >
                      Open Target
                    </button>
                    <button className="secondary-action" type="button" data-control-id="intelligence-audit" onClick={stageAuditDrill}>
                      Stage Drill
                    </button>
                  </div>
                  <div className="audit-drill-queue">
                    {drillQueueRows.length === 0 ? (
                      <span className="empty-state">No queued unproven controls after this target.</span>
                    ) : (
                      drillQueueRows.map(row => (
                        <button
                          className={`drill-queue-row ${row.tone || 'warn'}`}
                          type="button"
                          key={row.id}
                          data-control-id="intelligence-audit"
                          data-control-intent={`Select ${row.label} audit drill target`}
                          onClick={() => selectDrillTarget(row)}
                        >
                          <span>{row.focus || 'overview'}</span>
                          <strong>{row.label}</strong>
                        </button>
                      ))
                    )}
                  </div>
                  <div className="audit-drill-proof">
                    <span>Latest proof</span>
                    <strong>{latestProofEvent ? latestProofEvent.title : 'No explicit proof yet'}</strong>
                    <em>{latestProofEvent ? latestProofEvent.detail : 'Use a real dashboard control to create proof.'}</em>
                  </div>
                  <div className="audit-proof-trail">
                    {proofTrailRows.length === 0 ? (
                      <span>No proof events recorded yet.</span>
                    ) : (
                      proofTrailRows.map(row => (
                        <span key={row.id || `${row.title}-${row.time}`}>
                          <strong>{row.title}</strong>
                          <em>{row.detail}</em>
                        </span>
                      ))
                    )}
                  </div>
                </div>
              )}
              {controlAudit && (
                <div className={`proof-sweep-board ${controlAudit.unprovenCount > 0 ? 'warn' : 'success'}`}>
                  <div className="proof-sweep-head">
                    <div>
                      <span>Proof sweep</span>
                      <strong>{controlAudit.provenCount}/{controlAudit.provableCount} controls proven across {proofCoverageRows.length} groups</strong>
                      <em>{weakestCoverage ? `${weakestCoverage.label}: ${weakestCoverage.proven}/${weakestCoverage.total} proven` : 'Run the audit to build coverage groups.'}</em>
                    </div>
                    <StatusPill tone={controlAudit.unprovenCount > 0 ? 'warn' : 'success'}>
                      {controlAudit.unprovenCount > 0 ? `${controlAudit.unprovenCount} open` : 'covered'}
                    </StatusPill>
                  </div>
                  <div className="proof-sweep-grid">
                    {proofCoverageRows.map(row => (
                      <button
                        className={`proof-sweep-row ${row.tone} ${selectedAuditRow?.id === row.nextRow?.id ? 'selected' : ''}`}
                        type="button"
                        key={row.id}
                        data-control-id="proof-sweep"
                        data-control-intent={`Select ${row.label} proof coverage group`}
                        onClick={() => selectProofCoverage(row)}
                      >
                        <span>{row.label}</span>
                        <strong>{row.proven}/{row.total} proven</strong>
                        <em>{row.unproven} unproven{row.preview ? ` / ${row.preview} preview` : ''}</em>
                        <div className="proof-sweep-meter" aria-label={`${row.label} proof coverage`}>
                          <span className={row.tone} style={{ width: `${row.percent}%` }} />
                        </div>
                      </button>
                    ))}
                  </div>
                  <div className="proof-sweep-target">
                    <div>
                      <span>Weakest group target</span>
                      <strong>{weakestCoverage?.nextRow?.label || 'No target selected'}</strong>
                      <em>{weakestCoverage?.nextRow ? `${weakestCoverage.nextRow.focus || 'overview'} / ${weakestCoverage.nextRow.state}` : 'All groups are covered.'}</em>
                    </div>
                    <p>{weakestCoverage?.nextRow?.target || 'No unproven target remains in the current audit snapshot.'}</p>
                  </div>
                  <div className="proof-sweep-actions">
                    <button
                      className="secondary-action"
                      type="button"
                      data-control-id="proof-sweep"
                      onClick={() => openProofCoverage(weakestCoverage)}
                      disabled={!weakestCoverage?.nextRow}
                      data-disabled-reason={!weakestCoverage?.nextRow ? 'Run Audit before opening a proof coverage group.' : undefined}
                      title={!weakestCoverage?.nextRow ? 'Run Audit before opening a proof coverage group.' : undefined}
                    >
                      Open Group
                    </button>
                    <button className="secondary-action" type="button" data-control-id="proof-sweep" onClick={showUnprovenControls}>
                      Show Unproven
                    </button>
                    <button className="secondary-action" type="button" data-control-id="proof-sweep" onClick={stageProofSweep}>
                      Stage Sweep
                    </button>
                  </div>
                </div>
              )}
              {controlAudit && selectedAuditRow && (
                <div className={`control-risk-triage ${selectedAuditRow.tone || 'info'}`}>
                  <div>
                    <span>Selected risk</span>
                    <strong>{selectedAuditRow.label}</strong>
                    <em>{selectedAuditRow.state} {'->'} {selectedAuditRow.focus || 'overview'}{selectedAuditReviewed ? ' / reviewed' : ''}</em>
                  </div>
                  <p>{selectedAuditRow.detail}</p>
                  <div className="risk-next-action">
                    <span>Next safe action</span>
                    <strong>{selectedRiskRecommendation}</strong>
                  </div>
                  <div className="audit-queue-strip">
                    <span><strong>{reviewedRiskCount}</strong> reviewed</span>
                    <span><strong>{unreviewedRiskRows.length}</strong> open risks</span>
                    <span><strong>{visibleAuditRows.length}</strong> visible rows</span>
                  </div>
                  <div className="audit-queue-actions">
                    <button
                      className="secondary-action"
                      type="button"
                      data-control-ids={selectedAuditRow?.controlId || 'intelligence-audit'}
                      onClick={openSelectedControl}
                      disabled={!selectedAuditRow?.focus}
                      data-disabled-reason={!selectedAuditRow?.focus ? 'Select an audit row with a focus lane before opening it.' : undefined}
                      title={!selectedAuditRow?.focus ? 'Select an audit row with a focus lane before opening it.' : undefined}
                    >
                      {selectedAuditRow?.controlId ? 'Open Control' : 'Open Lane'}
                    </button>
                    <button className="secondary-action" type="button" data-control-id="intelligence-audit" data-control-intent="Mark audit risk reviewed" onClick={markAuditRowReviewed}>
                      Mark Reviewed
                    </button>
                    <button
                      className="secondary-action"
                      type="button"
                      data-control-id="intelligence-audit"
                      data-control-intent="Open next audit risk"
                      onClick={openNextAuditRisk}
                      disabled={!controlAudit?.riskCount}
                      data-disabled-reason={!controlAudit?.riskCount ? 'Run Audit and keep at least one open risk before advancing.' : undefined}
                      title={!controlAudit?.riskCount ? 'Run Audit and keep at least one open risk before advancing.' : undefined}
                    >
                      Next Risk
                    </button>
                  </div>
                </div>
              )}
              <div className="control-audit-grid">
                {!controlAudit ? (
                  <div className="empty-state">Audit has not been run for this snapshot.</div>
                ) : visibleAuditRows.length === 0 ? (
                  <div className="empty-state">No control rows match this audit filter.</div>
                ) : (
                  visibleAuditRows.map(row => (
                    <button
                      className={`control-audit-row ${row.tone || 'info'} ${selectedAuditRow?.id === row.id ? 'selected' : ''} ${reviewedAuditSet.has(row.id) ? 'reviewed' : ''}`}
                      type="button"
                      key={row.id}
                      aria-pressed={selectedAuditRow?.id === row.id}
                      data-control-ids={row.controlId || 'intelligence-audit'}
                      data-control-intent={`Open ${row.label} audit row`}
                      onClick={() => openAuditRow(row)}
                    >
                      <span>{row.state}</span>
                      <strong>{row.label}</strong>
                      <em>{row.detail}</em>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
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

function TelemetryPanel({ sysStatus, cpuHistory, memHistory, activeFocus, onStagePacket, onFocusChange, onCommandEvent }) {
  const [lens, setLens] = useState(sysStatus.mem >= sysStatus.cpu ? 'memory' : 'cpu');
  const maxedOut = String(sysStatus.resourceStatus || '').toLowerCase() === 'maxed_out' || sysStatus.mem >= 90 || sysStatus.cpu >= 90;
  const pressureTone = maxedOut ? 'danger' : sysStatus.mem > 85 || sysStatus.cpu > 85 ? 'warn' : toneForStatus(sysStatus.resourceStatus);
  const lenses = [
    {
      id: 'cpu',
      label: 'CPU',
      value: `${sysStatus.cpu.toFixed(1)}%`,
      tone: sysStatus.cpu >= 90 ? 'danger' : sysStatus.cpu > 85 ? 'warn' : 'info',
      detail: sysStatus.cpu >= 90
        ? 'CPU is saturated; avoid adding local worker load.'
        : sysStatus.cpu > 85
          ? 'CPU is hot; prefer review packets before new execution.'
          : 'CPU headroom is acceptable for local review work.',
      intent: 'Use CPU as the local execution capacity signal.'
    },
    {
      id: 'memory',
      label: 'Memory',
      value: `${sysStatus.mem.toFixed(1)}%`,
      tone: sysStatus.mem >= 90 ? 'danger' : sysStatus.mem > 85 ? 'warn' : 'success',
      detail: sysStatus.mem >= 90
        ? 'Memory pressure is maxed; hold new launches and stage evidence first.'
        : sysStatus.mem > 85
          ? 'Memory is close to the limit; keep work bounded.'
          : 'Memory headroom is acceptable.',
      intent: 'Use memory as the primary launch/no-launch gate.'
    },
    {
      id: 'gate',
      label: 'Gate',
      value: String(sysStatus.resourceStatus || 'unknown').replaceAll('_', ' '),
      tone: pressureTone,
      detail: maxedOut
        ? 'Resource gate is blocking or near blocking; route through Fleet/Sync before dispatch.'
        : 'Resource gate is not reporting a hard block.',
      intent: 'Use this as the operator gate before worker dispatch.'
    }
  ];
  const activeLens = lenses.find(item => item.id === lens) || lenses[0];

  const changeLens = nextLens => {
    setLens(nextLens.id);
    onCommandEvent('Telemetry lens changed', nextLens.label, nextLens.tone, { controlId: 'telemetry-actions' });
  };

  const stageTelemetryBrief = () => {
    const packet = [
      '# Telemetry Pressure Brief',
      '',
      `- status: ${sysStatus.resourceStatus || 'unknown'}`,
      `- cpu_percent: ${sysStatus.cpu.toFixed(1)}`,
      `- memory_percent: ${sysStatus.mem.toFixed(1)}`,
      `- selected_lens: ${activeLens.label}`,
      `- selected_value: ${activeLens.value}`,
      `- maxed_out: ${maxedOut ? 'yes' : 'no'}`,
      `- execution_context: ${sysStatus.executionContext}`,
      `- quantower: ${sysStatus.quantAllowed ? 'enabled' : 'locked'}`,
      '',
      '## Reasons',
      ...(sysStatus.pressureReasons.length
        ? sysStatus.pressureReasons.map(reason => `- ${reason}`)
        : ['- No resource pressure reasons reported.']),
      '',
      '## Selected Lens',
      `- ${activeLens.label}: ${activeLens.detail}`,
      `- intent: ${activeLens.intent}`,
      '',
      '## Operator Intent',
      maxedOut
        ? 'Hold new local worker launches. Review Fleet and Sync state, then stage a bounded packet before dispatch.'
        : 'Proceed with bounded review work, but keep watching pressure before launching more workers.'
    ].join('\n');
    onStagePacket(packet, 'Telemetry pressure brief staged', { controlId: 'telemetry-actions' });
  };

  const openTelemetryLane = focus => {
    onFocusChange(focus);
    onCommandEvent('Telemetry lane opened', focus, activeLens.tone, { controlId: 'telemetry-actions' });
  };

  return (
    <Panel
      title="Telemetry"
      meta={String(sysStatus.resourceStatus).toUpperCase()}
      tone={pressureTone}
      focus="telemetry"
      activeFocus={activeFocus}
      className="telemetry-panel"
      actions={
        <div className="filter-cluster telemetry-modes">
          {lenses.map(item => (
            <button
              className={activeLens.id === item.id ? 'active' : ''}
              type="button"
              key={item.id}
              data-control-id="telemetry-actions"
              data-control-intent={`Select ${item.label} telemetry lens`}
              onClick={() => changeLens(item)}
            >
              {item.label}
            </button>
          ))}
        </div>
      }
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
      <div className={`telemetry-decision ${activeLens.tone}`}>
        <div>
          <span>Selected signal</span>
          <strong>{activeLens.label} {activeLens.value}</strong>
          <em>{activeLens.detail}</em>
        </div>
        <p>{activeLens.intent}</p>
        <div className="telemetry-actions">
          <button className="secondary-action" type="button" data-control-id="telemetry-actions" onClick={stageTelemetryBrief}>
            Stage Pressure
          </button>
          <button className="secondary-action" type="button" data-control-id="telemetry-actions" onClick={() => openTelemetryLane('fleet')}>
            Open Fleet
          </button>
          <button className="secondary-action" type="button" data-control-id="telemetry-actions" onClick={() => openTelemetryLane('sync')}>
            Open Sync
          </button>
        </div>
      </div>
    </Panel>
  );
}

const gateRecommendation = item => {
  if (!item) {
    return {
      label: 'Select a gate',
      detail: 'Choose a checklist row to generate the next review step.',
      tone: 'info'
    };
  }
  const lane = item.focus || 'overview';
  if (item.tone === 'danger') {
    return {
      label: 'Stabilize blocker',
      detail: `Open ${lane}, collect evidence, and keep publish or worker actions blocked until this gate is green.`,
      tone: 'danger'
    };
  }
  if (item.tone === 'warn') {
    return {
      label: 'Review before dispatch',
      detail: `Inspect ${lane}, stage a bounded packet, and keep the action in preview until the warning is explained.`,
      tone: 'warn'
    };
  }
  return {
    label: 'Verify and continue',
    detail: `Use ${lane} as supporting evidence, then move the next safe packet through Comms.`,
    tone: 'success'
  };
};

function OpsChecklist({ items, activeFocus, selectedItem, onItemSelect, onOpenItem, onStageItem, onPlanItem }) {
  const activeItem = selectedItem || items[0];
  const recommendation = gateRecommendation(activeItem);
  return (
    <Panel title="No Slop Checklist" meta="Live gates" tone="info" focus="overview" activeFocus={activeFocus} className="ops-panel">
      <div className="ops-workbench">
        <div className="ops-list">
          {items.map(item => (
            <button
              className={`ops-row ${activeItem?.id === item.id ? 'selected' : ''}`}
              type="button"
              aria-pressed={activeItem?.id === item.id}
              key={item.id}
              data-control-id="ops-plan"
              data-control-intent={`Select ${item.label} checklist gate`}
              onClick={() => onItemSelect(item)}
            >
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
            </button>
          ))}
        </div>
        {activeItem && (
          <div className={`ops-detail ${activeItem.tone || 'info'}`}>
            <div>
              <span>Active gate</span>
              <strong>{activeItem.label}</strong>
              <em>{activeItem.state}</em>
            </div>
            <p>{activeItem.detail}</p>
            <div className={`ops-recommendation ${recommendation.tone}`}>
              <span>Recommended next step</span>
              <strong>{recommendation.label}</strong>
              <p>{recommendation.detail}</p>
            </div>
            <div className="ops-detail-meter">
              <span className={activeItem.tone} style={{ width: `${activeItem.progress}%` }} />
            </div>
            <div className="ops-detail-actions">
              <button className="secondary-action" type="button" data-control-id="ops-plan" data-control-intent={`Open ${activeItem.label} checklist gate`} onClick={() => onOpenItem(activeItem)}>
                Open Gate
              </button>
              <button className="secondary-action" type="button" data-control-id="ops-plan" data-control-intent={`Stage ${activeItem.label} checklist gate`} onClick={() => onStageItem(activeItem)}>
                Stage Gate
              </button>
              <button className="secondary-action" type="button" data-control-id="ops-plan" onClick={() => onPlanItem(activeItem, recommendation)}>
                Plan Step
              </button>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}

function TiuWorkbench({ sysStatus, activeFocus, onStagePacket, onCommandEvent }) {
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
  const resultTone = result ? toneForActionStatus(result) : 'info';
  const blockers = Array.isArray(result?.blockers) ? result.blockers : [];
  const warnings = Array.isArray(result?.warnings) ? result.warnings : [];

  const runLocalPreview = () => {
    const cleanObjective = objective.trim();
    if (!cleanObjective) return;
    const preview = buildLocalTiuPreview({
      objective: cleanObjective,
      scope,
      modelLane,
      mode,
      requireCloudSync,
      includeLiveChecks,
      writePacket,
      sysStatus
    });
    setResult(preview);
    onCommandEvent('TIU local preview generated', preview.plan_state, toneForActionStatus(preview), { controlId: 'tiu-workbench' });
  };

  const runWorkbench = async () => {
    const cleanObjective = objective.trim();
    if (!cleanObjective) return;
    setIsRunning(true);
    onCommandEvent('TIU packet requested', `${scope} / ${modelLane} / ${mode}`, 'info', { controlId: 'tiu-workbench' });
    try {
      if (!TOKEN) {
        const preview = buildLocalTiuPreview({
          objective: cleanObjective,
          scope,
          modelLane,
          mode,
          requireCloudSync,
          includeLiveChecks,
          writePacket,
          sysStatus
        });
        setResult(preview);
        onCommandEvent('TIU preview generated', preview.plan_state, toneForActionStatus(preview), { controlId: 'tiu-workbench' });
        return;
      }
      const response = await fetch(`${BRIDGE}/tiu/workbench`, {
        method: 'POST',
        headers: jsonHeaders(),
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
      onCommandEvent('TIU packet built', data.plan_state || data.status || 'ready', toneForActionStatus(data), { controlId: 'tiu-workbench' });
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
      onCommandEvent('TIU route failed', error.message, 'danger', { controlId: 'tiu-workbench' });
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
        <div className="panel-action-stack">
          <button
            className="primary-action"
            type="button"
            data-control-id="tiu-workbench"
            onClick={runWorkbench}
            disabled={isRunning}
            data-disabled-reason={isRunning ? 'Wait for the current TIU packet build to finish before starting another.' : undefined}
            title={isRunning ? 'Wait for the current TIU packet build to finish before starting another.' : undefined}
          >
            {isRunning ? 'Building' : 'Generate Packet'}
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="tiu-workbench"
            onClick={runLocalPreview}
            disabled={isRunning}
            data-disabled-reason={isRunning ? 'Wait for the current TIU packet build to finish before previewing.' : undefined}
            title={isRunning ? 'Wait for the current TIU packet build to finish before previewing.' : 'Build a safe local TIU preview without calling protected routes.'}
          >
            Local Preview
          </button>
        </div>
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
            <button className="secondary-action" type="button" data-control-id="tiu-workbench" onClick={() => onStagePacket(result.packet, 'TIU packet staged', { controlId: 'tiu-workbench' })}>
              Stage To Comms
            </button>
          )}
        </div>
      )}
    </Panel>
  );
}

function AllianceControl({ sysStatus, activeFocus, onStagePacket, onFocusChange, onCommandEvent }) {
  const [filter, setFilter] = useState('ALL');
  const [selectedLaneId, setSelectedLaneId] = useState('jules');
  const [liveProof, setLiveProof] = useState(null);
  const [proofError, setProofError] = useState('');
  const [isRunningProof, setIsRunningProof] = useState(false);
  const alliance = sysStatus.alliance || DEFAULT_STATUS.alliance;
  const lanes = useMemo(() => buildAllianceLanes(sysStatus), [sysStatus]);
  const visibleLanes = lanes.filter(lane => {
    if (filter === 'READY') return lane.tone === 'success';
    if (filter === 'ATTENTION') return lane.tone !== 'success';
    return true;
  });
  const selectedLane = lanes.find(lane => lane.id === selectedLaneId) || visibleLanes[0] || lanes[0];
  const tone = allianceTone(alliance);
  const activeProof = liveProof ? normalizeCollaborationProof(liveProof) : null;
  const proofTone = proofError
    ? 'danger'
    : activeProof
      ? toneForActionStatus({ ...activeProof, warnings: activeProof.legacy_caveats })
      : 'info';
  const proofGateLabel = activeProof
    ? `${activeProof.required_pass_count}/${activeProof.required_gate_count || activeProof.gate_count}`
    : '--';
  const proofAgents = activeProof?.agents || {};

  useEffect(() => {
    if (lanes.length > 0 && !lanes.some(lane => lane.id === selectedLaneId)) {
      setSelectedLaneId(lanes[0].id);
    }
  }, [lanes, selectedLaneId]);

  const changeFilter = nextFilter => {
    setFilter(nextFilter);
    onCommandEvent('Alliance filter changed', nextFilter, nextFilter === 'ATTENTION' ? 'warn' : 'info', { controlId: 'alliance-actions' });
  };

  const selectLane = lane => {
    setSelectedLaneId(lane.id);
    onCommandEvent('Alliance lane selected', `${lane.label} - ${lane.state}`, lane.tone || 'info', { controlId: 'alliance-actions' });
  };

  const openLaneWorkbench = lane => {
    const targetFocus = lane.id === 'sync' ? 'sync' : 'tiu';
    onFocusChange(targetFocus);
    onCommandEvent('Alliance lane opened', `${lane.label} -> ${targetFocus}`, lane.tone || 'info', { controlId: 'alliance-actions' });
  };

  const stageLaneBrief = lane => {
    const packet = [
      '# Alliance Lane Brief',
      '',
      `- lane: ${lane.label}`,
      `- role: ${lane.role}`,
      `- state: ${lane.state}`,
      `- ready: ${lane.ready ? 'yes' : 'no'}`,
      `- tone: ${lane.tone || 'info'}`,
      `- detail: ${lane.detail}`,
      `- alliance_mode: ${alliance.mode || 'unknown'}`,
      `- creator: ${alliance.creator || 'jules'}`,
      `- implementer: ${alliance.implementer || 'unassigned'}`,
      `- gates: ${alliance.gate_pass_count || 0}/${alliance.gate_total_count || 0}`,
      `- live_work: ${alliance.safe_to_launch_live_work ? 'open' : 'gated'}`,
      '',
      '## Operator Intent',
      lane.id === 'sync'
        ? 'Inspect the Sync lane and build a publish packet before any cloud publish.'
        : 'Use the TIU workbench to prepare a review packet for this alliance lane before live work.'
    ].join('\n');
    onStagePacket(packet, `${lane.label} alliance staged`, { controlId: 'alliance-actions' });
  };

  const agentProofLine = (id, label) => {
    const agent = proofAgents[id] || {};
    if (!Object.keys(agent).length) return `${label}: not returned`;
    if (id === 'jules') {
      return `${label}: ${agent.reachable ? 'reachable' : 'blocked'} / ${agent.mode || 'mode unknown'} / ${agent.skill_count || 0} skills`;
    }
    return `${label}: ${agent.cli_reachable ? 'cli reachable' : 'cli blocked'} / ${agent.model_ready ? 'model ready' : 'model blocked'} / ${agent.skill_count || 0} skills`;
  };

  const runCollaborationProof = async () => {
    setProofError('');
    onCommandEvent('Alliance proof requested', 'POST /proof/collaboration', 'info', { controlId: 'alliance-actions' });
    if (!TOKEN) {
      const tokenGate = normalizeCollaborationProof({
        status: 'blocked',
        summary: 'Bearer token required for POST /proof/collaboration; no proof route was called.',
        blockers: [{ gate: 'dashboard_token', blocker: 'protected_route_token_missing', status: 'blocked' }],
        gates: [],
        proof_policy: {
          live_side_effects: 'none',
          live_read_only_checks: false,
          gemini_smoke_requested: false
        }
      });
      setLiveProof(tokenGate);
      onCommandEvent('Alliance proof token gate', tokenGate.summary, 'warn', { controlId: 'alliance-actions' });
      return;
    }

    setIsRunningProof(true);
    try {
      const response = await fetch(`${BRIDGE}/proof/collaboration`, {
        method: 'POST',
        headers: jsonHeaders(),
        cache: 'no-store',
        body: JSON.stringify({
          include_live_checks: true,
          run_gemini_smoke: false,
          timeout_s: 12,
          write_state: false
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      const normalized = normalizeCollaborationProof(data);
      setLiveProof(normalized);
      onCommandEvent(
        'Alliance proof refreshed',
        `${normalized.required_pass_count}/${normalized.required_gate_count || normalized.gate_count} required gates; blockers ${normalized.blocker_count}; caveats ${normalized.caveat_count}`,
        toneForActionStatus({ ...normalized, warnings: normalized.legacy_caveats }),
        { controlId: 'alliance-actions' }
      );
    } catch (error) {
      const failed = normalizeCollaborationProof({
        status: 'error',
        summary: 'Collaboration proof route failed.',
        blockers: [{ gate: 'proof_route', blocker: error.message, status: 'fail' }],
        proof_policy: {
          live_side_effects: 'none',
          live_read_only_checks: true,
          gemini_smoke_requested: false
        }
      });
      setProofError(error.message);
      setLiveProof(failed);
      onCommandEvent('Alliance proof failed', error.message, 'danger', { controlId: 'alliance-actions' });
    } finally {
      setIsRunningProof(false);
    }
  };

  const stageCollaborationProof = () => {
    if (!activeProof) return;
    const gateRows = activeProof.gates.slice(0, 10).map(gate => (
      `- ${gate.name || gate.id || 'gate'}: ${gate.status || 'unknown'}${gate.required === false ? ' (legacy caveat)' : ''}${gate.summary ? ` - ${gate.summary}` : ''}`
    ));
    const requirementRows = Array.isArray(activeProof.requirement_audit)
      ? activeProof.requirement_audit.slice(0, 8).map(row => `- ${row.id || row.requirement || 'requirement'}: ${row.status || 'unknown'} - ${row.summary || row.evidence || 'no summary'}`)
      : [];
    const packet = [
      '# Alliance Collaboration Proof',
      '',
      '- route: POST /proof/collaboration',
      '- include_live_checks: true',
      '- run_gemini_smoke: false',
      '- write_state: false',
      '- source: live protected bridge route',
      `- generated_at_utc: ${activeProof.generated_at_utc || 'not returned'}`,
      `- status: ${activeProof.status || 'unknown'}`,
      `- summary: ${activeProof.summary || 'no summary'}`,
      `- required_gates: ${proofGateLabel}`,
      `- blockers: ${activeProof.blocker_count}`,
      `- legacy_caveats: ${activeProof.caveat_count}`,
      `- safe_to_mark_goal_complete: ${activeProof.completion_assessment?.safe_to_mark_goal_complete ? 'yes' : 'no'}`,
      '',
      '## Agent Points Of View',
      `- Jules: ${proofAgents.jules?.point_of_view || 'not returned'}`,
      `  - ${agentProofLine('jules', 'Jules')}`,
      `- Gemini: ${proofAgents.gemini?.point_of_view || 'not returned'}`,
      `  - ${agentProofLine('gemini', 'Gemini')}`,
      `- Antigravity: ${proofAgents.antigravity?.point_of_view || 'not returned'}`,
      `  - ${agentProofLine('antigravity', 'Antigravity')}`,
      '',
      '## Gate Evidence',
      ...(gateRows.length ? gateRows : ['- no gates returned']),
      '',
      '## Requirement Audit',
      ...(requirementRows.length ? requirementRows : ['- no requirement audit returned']),
      '',
      '## Operator Guardrail',
      'This proof is read-only. It did not launch Jules sessions, run edit-capable Gemini prompts, save proof JSON, commit, push, or change files.'
    ].join('\n');
    onStagePacket(packet, 'Alliance collaboration proof staged', { controlId: 'alliance-actions' });
    onCommandEvent('Alliance proof staged', `${activeProof.status || 'unknown'} / ${proofGateLabel} gates`, proofTone, { controlId: 'alliance-actions' });
  };

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
              data-control-id="alliance-actions"
              data-control-intent={`Filter alliance lanes by ${item}`}
              onClick={() => changeFilter(item)}
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
      <div className={`alliance-proof-card ${proofTone}`}>
        <div className="alliance-proof-head">
          <div>
            <span>Collaboration Proof</span>
            <strong>{activeProof ? `${proofGateLabel} required gates` : 'Not run this session'}</strong>
          </div>
          <StatusPill tone={proofTone}>{activeProof?.status || (proofError ? 'error' : 'ready')}</StatusPill>
        </div>
        <p>{activeProof?.summary || proofError || 'Run the protected proof route to verify Jules, Gemini, Antigravity, skills, context, HRM, tests, and completion gates.'}</p>
        <div className="alliance-proof-metrics">
          <div>
            <span>Blockers</span>
            <strong>{activeProof?.blocker_count ?? '--'}</strong>
          </div>
          <div>
            <span>Caveats</span>
            <strong>{activeProof?.caveat_count ?? '--'}</strong>
          </div>
          <div>
            <span>Safe Complete</span>
            <strong>{activeProof?.completion_assessment?.safe_to_mark_goal_complete ? 'Yes' : 'No'}</strong>
          </div>
          <div>
            <span>Writes</span>
            <strong>{activeProof ? 'None' : '--'}</strong>
          </div>
        </div>
        {activeProof && (
          <div className="alliance-agent-pov">
            {[
              ['jules', 'Jules'],
              ['gemini', 'Gemini'],
              ['antigravity', 'Antigravity']
            ].map(([id, label]) => (
              <div key={id}>
                <strong>{label}</strong>
                <span>{agentProofLine(id, label)}</span>
                <em>{proofAgents[id]?.point_of_view || 'No point of view returned.'}</em>
              </div>
            ))}
          </div>
        )}
        <div className="alliance-detail-actions">
          <button
            className="primary-action"
            type="button"
            data-control-id="alliance-actions"
            data-control-intent="Run live collaboration proof route"
            onClick={runCollaborationProof}
            disabled={isRunningProof}
            data-disabled-reason={isRunningProof ? 'Wait for the collaboration proof route to finish.' : undefined}
            title={isRunningProof ? 'Wait for the collaboration proof route to finish.' : 'Call POST /proof/collaboration with write_state=false.'}
          >
            {isRunningProof ? 'Running Proof' : 'Run Proof'}
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="alliance-actions"
            data-control-intent="Stage latest collaboration proof"
            onClick={stageCollaborationProof}
            disabled={!activeProof}
            data-disabled-reason={!activeProof ? 'Run proof before staging collaboration evidence.' : undefined}
            title={!activeProof ? 'Run proof before staging collaboration evidence.' : 'Stage the latest collaboration proof into Comms.'}
          >
            Stage Proof
          </button>
        </div>
      </div>
      <div className="alliance-lanes">
        {visibleLanes.map(lane => (
          <button
            className={`alliance-lane ${lane.tone} ${selectedLane?.id === lane.id ? 'selected' : ''}`}
            type="button"
            key={lane.id}
            data-control-id="alliance-actions"
            data-control-intent={`Select ${lane.label} alliance lane`}
            onClick={() => selectLane(lane)}
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
          <div className="alliance-detail-actions">
            <button className="secondary-action" type="button" data-control-id="alliance-actions" onClick={() => openLaneWorkbench(selectedLane)}>
              Open Workbench
            </button>
            <button className="secondary-action" type="button" data-control-id="alliance-actions" onClick={() => stageLaneBrief(selectedLane)}>
              Stage Lane
            </button>
          </div>
        </div>
      )}
    </Panel>
  );
}

function CloudSyncPanel({ cloudSync, activeFocus, onStagePacket, onCommandEvent }) {
  const sync = cloudSync || DEFAULT_STATUS.cloudSync;
  const [writePacket, setWritePacket] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [publishPacket, setPublishPacket] = useState(null);
  const syncGate = buildLocalSyncGate(sync);
  const syncDiagnosis = summarizeCloudSyncGate(sync);
  const blockers = syncGate.blockers;
  const warnings = syncGate.warnings;
  const tone = blockers.length > 0 ? 'danger' : syncGate.publishReady || syncGate.synced ? 'success' : cloudSyncTone(sync);
  const packetTone = publishPacket ? toneForActionStatus(publishPacket) : 'info';
  const packetFamilies = Array.isArray(publishPacket?.change_families) ? publishPacket.change_families : [];
  const packetCommands = Array.isArray(publishPacket?.commands) ? publishPacket.commands : [];
  const canWritePacket = Boolean(TOKEN);
  const effectiveWritePacket = canWritePacket && writePacket;
  const cleanTitle = syncGate.publishReady ? 'Publish ready' : syncGate.synced ? 'Cloud clean' : 'Publish not ready';
  const cleanDetail = syncGate.publishReady
    ? 'Local commits can be pushed intentionally after operator review.'
    : syncGate.synced
      ? 'Local and tracked remote state are clean; no cloud publish is needed.'
      : 'Publish readiness is not proven from the compact status snapshot.';

  const previewPublishPacket = () => {
    const preview = buildLocalPublishPreview(sync, writePacket);
    setPublishPacket(preview);
    onCommandEvent('Publish local preview generated', preview.state, toneForActionStatus(preview), { controlId: 'sync-packet' });
  };

  const buildPublishPacket = async () => {
    setIsBuilding(true);
    onCommandEvent('Publish review requested', `${sync.branch || 'branch'} / ${sync.state || 'unknown'}`, 'info', { controlId: 'sync-packet' });
    try {
      if (!TOKEN) {
        const preview = buildLocalPublishPreview(sync, writePacket);
        const gatedPreview = {
          ...preview,
          warnings: [...new Set([
            ...(Array.isArray(preview.warnings) ? preview.warnings : []),
            writePacket ? 'packet_save_requires_protected_route' : ''
          ].filter(Boolean))]
        };
        setPublishPacket(gatedPreview);
        onCommandEvent('Publish local preview generated', gatedPreview.state || gatedPreview.status || 'preview', toneForActionStatus(gatedPreview), { controlId: 'sync-packet' });
        return;
      }
      const response = effectiveWritePacket
        ? await fetch(`${BRIDGE}/sync/publish-packet`, {
          method: 'POST',
          headers: jsonHeaders(),
          body: JSON.stringify({
            objective: CLOUD_PUBLISH_OBJECTIVE,
            timeout_s: 8,
            use_cache: false,
            write_packet: true
          })
        })
        : await fetch(`${BRIDGE}/sync/publish-preview?${new URLSearchParams({
          objective: CLOUD_PUBLISH_OBJECTIVE,
          timeout_s: '8',
          use_cache: 'false'
        }).toString()}`, {
          headers: jsonHeaders(),
          cache: 'no-store'
        });
      const data = await response.json();
      if (!response.ok && !data.status) {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      setPublishPacket(data);
      onCommandEvent(
        effectiveWritePacket ? 'Publish packet saved' : 'Publish preview built',
        data.state || data.status || 'ready',
        toneForActionStatus(data),
        { controlId: 'sync-packet' }
      );
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
      onCommandEvent('Publish route failed', error.message, 'danger', { controlId: 'sync-packet' });
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
        <div className="panel-action-stack">
          <button
            className="primary-action"
            type="button"
            data-control-id="sync-packet"
            onClick={buildPublishPacket}
            disabled={isBuilding}
            data-disabled-reason={isBuilding ? 'Wait for the current publish review packet to finish building.' : undefined}
            title={isBuilding ? 'Wait for the current publish review packet to finish building.' : undefined}
          >
            {isBuilding ? 'Reviewing' : effectiveWritePacket ? 'Save Publish Packet' : 'Build Publish Preview'}
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="sync-packet"
            onClick={previewPublishPacket}
            disabled={isBuilding}
            data-disabled-reason={isBuilding ? 'Wait for the current publish review packet to finish building before previewing.' : undefined}
            title={isBuilding ? 'Wait for the current publish review packet to finish building before previewing.' : 'Build a safe local publish preview without calling protected routes.'}
          >
            Local Preview
          </button>
        </div>
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
          {syncGate.publishReady
            ? 'Publish gate is ready for operator review'
            : blockers.length > 0
              ? `${blockers.length} sync blocker${blockers.length === 1 ? '' : 's'} require review`
              : sync.github_authenticated
                ? `GitHub ready${sync.github_account ? ` as ${sync.github_account}` : ''}`
                : 'GitHub auth not proven'}
        </span>
      </div>
      <div className={`sync-diagnosis ${syncDiagnosis.tone}`}>
        <strong>{syncDiagnosis.headline}</strong>
        <span>{syncDiagnosis.detail}</span>
        <em>{syncDiagnosis.action}</em>
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
            <strong>{cleanTitle}</strong>
            <span>{cleanDetail}</span>
          </div>
        ) : (
          [...blockers.map(item => ['danger', item]), ...warnings.map(item => ['warn', item])].slice(0, 5).map(([itemTone, item]) => (
            <div className={`finding-row ${itemTone}`} key={`${itemTone}-${item}`}>
              <strong>{cloudSyncIssueLabel(item)}</strong>
              <span>{cloudSyncIssueDetail(item)}</span>
            </div>
          ))
        )}
      </div>
      <label className="sync-save-row">
        <input
          type="checkbox"
          checked={effectiveWritePacket}
          disabled={!canWritePacket}
          onChange={event => setWritePacket(event.target.checked)}
          title={canWritePacket ? undefined : 'Bearer token required for local packet writes'}
        />
        <span>{canWritePacket ? 'Save publish packet locally' : 'Save requires token; preview is read-only'}</span>
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
            <button className="secondary-action" type="button" data-control-id="sync-packet" onClick={() => onStagePacket(publishPacket.packet, 'Publish packet staged', { controlId: 'sync-packet' })}>
              Stage To Comms
            </button>
          )}
        </div>
      )}
    </Panel>
  );
}

function FleetPanel({ fleet, activeFocus, onStagePacket, onFocusChange, onCommandEvent }) {
  const [selectedQueueId, setSelectedQueueId] = useState('pending');
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
  const queueRows = useMemo(() => [
    {
      id: 'complete',
      label: 'Complete',
      count: completed,
      tone: 'success',
      detail: completed > 0 ? 'Completed worker sessions are ready for evidence review.' : 'No completed worker sessions have reported back yet.',
      intent: 'Review completion evidence before closing the fleet loop.'
    },
    {
      id: 'active',
      label: 'Active',
      count: inProgress,
      tone: inProgress > 0 ? 'info' : 'warn',
      detail: inProgress > 0 ? 'Active worker sessions need health monitoring.' : 'No worker sessions are currently in progress.',
      intent: 'Open Workers and inspect live worker health before adding more load.'
    },
    {
      id: 'pending',
      label: 'Pending',
      count: pending,
      tone: pending > 0 ? 'warn' : 'success',
      detail: pending > 0 ? 'Queued sessions need dispatch review before launch.' : 'There is no pending queue pressure.',
      intent: 'Prepare a TIU packet or worker directive before dispatching queued sessions.'
    },
    {
      id: 'failed',
      label: 'Failed',
      count: failed,
      tone: failed > 0 ? 'danger' : 'success',
      detail: failed > 0 ? 'Failed sessions need recovery before new dispatch.' : 'No failed fleet sessions are reported.',
      intent: 'Inspect worker logs and stage a recovery brief before relaunching.'
    }
  ], [completed, failed, inProgress, pending]);
  const selectedQueue = queueRows.find(row => row.id === selectedQueueId) || queueRows[0];
  const fleetTone = failed > 0 ? 'danger' : pending > 0 || inProgress > 0 ? 'warn' : 'success';
  const readinessLabel = failed > 0
    ? 'recovery needed'
    : pending > 0
      ? 'dispatch review'
      : inProgress > 0
        ? 'monitor active'
        : launched > 0
          ? 'complete'
          : 'idle';

  const selectQueue = row => {
    setSelectedQueueId(row.id);
    onCommandEvent('Fleet queue selected', `${row.label}: ${row.count}`, row.tone, { controlId: 'fleet-actions' });
  };

  const stageFleetBrief = () => {
    const packet = [
      '# Fleet Queue Brief',
      '',
      `- launched: ${launched}`,
      `- completed: ${completed}`,
      `- in_progress: ${inProgress}`,
      `- pending: ${pending}`,
      `- failed: ${failed}`,
      `- all_complete: ${fleet.all_complete ? 'yes' : 'no'}`,
      `- sessions_tracked: ${fleet.sessions_tracked || 0}`,
      `- readiness: ${readinessLabel}`,
      '',
      '## Queue State',
      ...queueRows.map(row => `- ${row.label}: ${row.count} (${row.detail})`),
      '',
      '## Selected Lane',
      `- ${selectedQueue.label}: ${selectedQueue.detail}`,
      `- intent: ${selectedQueue.intent}`,
      '',
      '## Operator Intent',
      pending > 0
        ? 'Do not launch queued sessions blindly. Prepare a TIU or worker packet, then verify worker health.'
        : 'Use this packet to decide whether the fleet loop can close or needs monitoring.'
    ].join('\n');
    onStagePacket(packet, 'Fleet queue brief staged', { controlId: 'fleet-actions' });
  };

  const openFleetFocus = focus => {
    onFocusChange(focus);
    onCommandEvent('Fleet focus opened', focus, focus === 'workers' ? selectedQueue.tone : 'info', { controlId: 'fleet-actions' });
  };

  return (
    <Panel
      title="Fleet Queue"
      meta={`${readinessLabel} - ${launched} launches tracked`}
      tone={fleetTone}
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
        <div className="fleet-workbench">
          <div className="fleet-bars">
            {queueRows.map(row => (
              <button
                className={`fleet-bar-row ${selectedQueue.id === row.id ? 'selected' : ''}`}
                type="button"
                key={row.id}
                aria-pressed={selectedQueue.id === row.id}
                data-control-id="fleet-actions"
                data-control-intent={`Select ${row.label} fleet queue`}
                onClick={() => selectQueue(row)}
              >
                <span>{row.label}</span>
                <div className="fleet-bar">
                  <span className={row.tone} style={{ width: `${Math.max((Number(row.count) / Math.max(launched, 1)) * 100, Number(row.count) > 0 ? 8 : 0)}%` }} />
                </div>
                <strong>{row.count}</strong>
              </button>
            ))}
          </div>
          <div className={`fleet-detail ${selectedQueue.tone}`}>
            <div>
              <span>Selected queue</span>
              <strong>{selectedQueue.label}</strong>
              <em>{selectedQueue.detail}</em>
            </div>
            <p>{selectedQueue.intent}</p>
            <div className="fleet-actions">
              <button className="secondary-action" type="button" data-control-id="fleet-actions" onClick={stageFleetBrief}>
                Stage Fleet
              </button>
              <button className="secondary-action" type="button" data-control-id="fleet-actions" onClick={() => openFleetFocus('workers')}>
                Open Workers
              </button>
              <button className="secondary-action" type="button" data-control-id="fleet-actions" onClick={() => openFleetFocus('tiu')}>
                Open TIU
              </button>
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function WorkerDirectory({
  workers,
  cloud,
  selectedWorkerKey,
  setSelectedWorkerKey,
  activeFocus,
  onStagePacket,
  onFocusChange,
  onCommandEvent
}) {
  const selectedWorker = workers.find((worker, index) => workerKey(worker, index) === selectedWorkerKey) || workers[0];
  const [liveVmStatus, setLiveVmStatus] = useState(null);
  const [workerStatusError, setWorkerStatusError] = useState('');
  const [isRefreshingWorker, setIsRefreshingWorker] = useState(false);
  const activeRelayStatus = liveVmStatus ? normalizeVmRelayStatus(liveVmStatus) : null;
  const selectedTone = selectedWorker?.reachable ? 'success' : toneForStatus(selectedWorker?.status);
  const relayTone = activeRelayStatus
    ? activeRelayStatus.online ? 'success' : 'danger'
    : workerStatusError ? 'danger' : 'info';
  const offlineCount = Math.max(Number(cloud.total || 0) - Number(cloud.online || 0), 0);
  const selectedEndpoint = maskEndpoint(selectedWorker?.ip);
  const selectedLabel = selectedWorker?.name || selectedWorker?.provider || 'No worker selected';
  const relayFreshness = activeRelayStatus?.sampled_at_utc
    ? `live VM status ${formatTimestamp(activeRelayStatus.sampled_at_utc)}`
    : workerStatusError || 'live VM status not sampled';

  const refreshWorkerStatus = async () => {
    setIsRefreshingWorker(true);
    setWorkerStatusError('');
    onCommandEvent('Worker status refresh requested', selectedWorker?.name || 'VM relay', 'info', { controlId: 'workers-actions' });
    try {
      const response = await fetch(`${BRIDGE}/vm/status`, { cache: 'no-store' });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      const normalized = normalizeVmRelayStatus({
        ...data,
        sampled_at_utc: new Date().toISOString()
      });
      setLiveVmStatus(normalized);
      onCommandEvent(
        'Worker status refreshed',
        `online=${normalized.online} / completed ${normalized.tasks_completed} / running ${normalized.tasks_running}`,
        normalized.online ? 'success' : 'danger',
        { controlId: 'workers-actions' }
      );
    } catch (error) {
      const message = error.message || 'VM status route failed';
      setWorkerStatusError(message);
      setLiveVmStatus(null);
      onCommandEvent('Worker status refresh failed', message, 'danger', { controlId: 'workers-actions' });
    } finally {
      setIsRefreshingWorker(false);
    }
  };

  const stageWorkerDirectoryBrief = () => {
    if (!selectedWorker) return;
    const packet = [
      '# Worker Directory Brief',
      '',
      `- selected_worker: ${selectedWorker.name || 'unnamed'}`,
      `- provider: ${selectedWorker.provider || 'worker'}`,
      `- zone: ${selectedWorker.zone || 'unknown'}`,
      `- endpoint: ${selectedEndpoint}`,
      `- status: ${selectedWorker.status || 'unknown'}`,
      `- reachable: ${selectedWorker.reachable ? 'yes' : 'no'}`,
      `- fleet_online: ${cloud.online || 0}/${cloud.total || 0}`,
      `- offline_count: ${offlineCount}`,
      `- vm_status_source: ${activeRelayStatus ? 'live GET /vm/status' : 'dashboard/status snapshot'}`,
      `- vm_online: ${activeRelayStatus ? (activeRelayStatus.online ? 'yes' : 'no') : 'not sampled'}`,
      `- vm_tasks_completed: ${activeRelayStatus?.tasks_completed ?? 'not sampled'}`,
      `- vm_tasks_running: ${activeRelayStatus?.tasks_running ?? 'not sampled'}`,
      `- vm_browser_model_loop: ${activeRelayStatus ? (activeRelayStatus.browser_model_loop ? 'configured' : 'not configured') : 'not sampled'}`,
      '',
      '## Operator Intent',
      selectedWorker.reachable
        ? 'Use this worker as evidence context only. Do not launch or mutate worker state from this dashboard brief.'
        : 'Treat this worker as unavailable until a live health check proves otherwise.'
    ].join('\n');
    onStagePacket(packet, `${selectedWorker.name || 'Worker'} directory brief staged`, { controlId: 'workers-actions' });
  };

  const openWorkerFocus = focus => {
    onFocusChange(focus);
    onCommandEvent('Worker directory opened lane', focus, selectedTone || 'info', { controlId: 'workers-actions' });
  };

  return (
    <Panel
      title="Worker Directory"
      meta={`${cloud.online || 0}/${cloud.total || 0} online`}
      tone={(cloud.total || 0) === 0 ? 'warn' : (cloud.online || 0) > 0 ? 'success' : 'danger'}
      focus="workers"
      activeFocus={activeFocus}
      className="workers-panel"
    >
      <div className="worker-workbench">
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
                  data-control-id="workers-actions"
                  data-control-intent={`Select ${vm?.name || vm?.provider || 'worker'} worker`}
                  onClick={() => setSelectedWorkerKey(key)}
                  aria-pressed={selectedWorkerKey === key}
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
        <div className={`worker-detail ${selectedTone || 'info'}`}>
          <div>
            <span>Selected worker</span>
            <strong>{selectedLabel}</strong>
            <em>{selectedWorker ? `${selectedWorker.provider || 'worker'} / ${selectedWorker.zone || 'zone unknown'}` : 'Select a worker row'}</em>
          </div>
          <div className="worker-health-grid">
            <div>
              <span>Reachable</span>
              <strong>{selectedWorker?.reachable ? 'yes' : selectedWorker ? 'no' : '--'}</strong>
            </div>
            <div>
              <span>Endpoint</span>
              <strong>{selectedWorker ? selectedEndpoint : '--'}</strong>
            </div>
            <div>
              <span>Offline</span>
              <strong>{offlineCount}</strong>
            </div>
          </div>
          <div className={`worker-relay-card ${relayTone}`}>
            <div>
              <span>VM Relay</span>
              <strong>{activeRelayStatus ? (activeRelayStatus.online ? 'online' : 'offline') : workerStatusError ? 'failed' : 'not sampled'}</strong>
              <em>{relayFreshness}</em>
            </div>
            <div className="worker-relay-metrics">
              <div>
                <span>Completed</span>
                <strong>{activeRelayStatus?.tasks_completed ?? '--'}</strong>
              </div>
              <div>
                <span>Running</span>
                <strong>{activeRelayStatus?.tasks_running ?? '--'}</strong>
              </div>
              <div>
                <span>Model Loop</span>
                <strong>{activeRelayStatus ? (activeRelayStatus.browser_model_loop ? 'yes' : 'no') : '--'}</strong>
              </div>
            </div>
          </div>
          <p>
            {selectedWorker
              ? selectedWorker.reachable
                ? 'Worker is reachable; use staged evidence before delegating new work.'
                : 'Worker is not proven reachable; hold dispatch and inspect fleet health.'
              : 'No worker is available for triage.'}
          </p>
          <div className="worker-actions">
            <button
              className="primary-action"
              type="button"
              data-control-id="workers-actions"
              data-control-intent="Refresh live VM worker status"
              onClick={refreshWorkerStatus}
              disabled={isRefreshingWorker}
              data-disabled-reason={isRefreshingWorker ? 'Wait for the current VM status refresh to finish.' : undefined}
              title={isRefreshingWorker ? 'Wait for the current VM status refresh to finish.' : 'Sample GET /vm/status without dispatching work.'}
            >
              {isRefreshingWorker ? 'Refreshing' : 'Refresh Worker'}
            </button>
            <button
              className="secondary-action"
              type="button"
              data-control-id="workers-actions"
              onClick={stageWorkerDirectoryBrief}
              disabled={!selectedWorker}
              data-disabled-reason={!selectedWorker ? 'Select a worker row before staging worker evidence.' : undefined}
              title={!selectedWorker ? 'Select a worker row before staging worker evidence.' : undefined}
            >
              Stage Worker
            </button>
            <button className="secondary-action" type="button" data-control-id="workers-actions" onClick={() => openWorkerFocus('fleet')}>
              Open Fleet
            </button>
            <button className="secondary-action" type="button" data-control-id="workers-actions" onClick={() => openWorkerFocus('comms')}>
              Open Comms
            </button>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function RepoGuard({
  repoContext,
  selectedCollisionKey,
  setSelectedCollisionKey,
  activeFocus,
  onStagePacket,
  onFocusChange,
  onCommandEvent
}) {
  const [selectedGuardrailIndex, setSelectedGuardrailIndex] = useState(0);
  const [liveRepoContext, setLiveRepoContext] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState('');
  const cachedRepoContext = useMemo(() => normalizeRepoContext(repoContext), [repoContext]);
  const activeRepoContext = liveRepoContext || cachedRepoContext;
  const summary = activeRepoContext?.summary || {};
  const collisions = Array.isArray(activeRepoContext?.collisions) ? activeRepoContext.collisions : [];
  const guardrails = Array.isArray(activeRepoContext?.guardrails) ? activeRepoContext.guardrails : [];
  const severityCounts = summary.collision_severity_counts || {};
  const tone = (summary.collision_count || 0) > 0 ? 'warn' : toneForStatus(activeRepoContext?.status);
  const activeCollision = collisions.find((collision, index) => collisionKey(collision, index) === selectedCollisionKey) || collisions[0];
  const activeGuardrail = guardrails[selectedGuardrailIndex] || guardrails[0] || 'No repo guardrail reported.';
  const collisionCount = Number(summary.collision_count || 0);
  const warningCount = Number(severityCounts.warning || 0);
  const criticalCount = Number(severityCounts.critical || severityCounts.danger || 0);
  const rootsMissing = Number(summary.roots_missing_count || 0);
  const rootsScanned = Number(summary.roots_scanned_count || 0);
  const repoTone = criticalCount > 0 ? 'danger' : collisionCount > 0 || rootsMissing > 0 ? 'warn' : tone;
  const repoState = criticalCount > 0
    ? 'critical collision review'
    : collisionCount > 0
      ? 'collision review'
      : rootsMissing > 0
        ? 'partial repo map'
        : 'clear matrix';
  const repoFreshness = liveRepoContext
    ? `fresh guard result ${formatTimestamp(liveRepoContext.generated_at_utc)}`
    : `cached guard ${formatTimestamp(activeRepoContext?.generated_at_utc)}`;

  useEffect(() => {
    if (guardrails.length > 0 && selectedGuardrailIndex >= guardrails.length) {
      setSelectedGuardrailIndex(0);
    }
  }, [guardrails.length, selectedGuardrailIndex]);

  const selectGuardrail = index => {
    setSelectedGuardrailIndex(index);
    onCommandEvent('Repo guardrail selected', guardrails[index] || 'guardrail', collisionCount > 0 ? 'warn' : 'info', { controlId: 'repo-actions' });
  };

  const selectCollision = (collision, index) => {
    const key = collisionKey(collision, index);
    setSelectedCollisionKey(key);
  };

  const runRepoGuard = async () => {
    setIsScanning(true);
    setScanError('');
    onCommandEvent('Repo guard refresh requested', `${summary.repo_count || 0} cached repos / ${collisionCount} collisions`, 'info', { controlId: 'repo-actions' });
    try {
      if (!TOKEN) {
        const message = 'Bearer token required for GET /repo/context-guard; cached dashboard snapshot remains visible.';
        setScanError(message);
        onCommandEvent('Repo guard refresh gated', message, 'warn', { controlId: 'repo-actions' });
        return;
      }
      const params = new URLSearchParams({
        max_depth: '4',
        max_repos: '100',
        include_repos: 'false',
        use_cache: 'false'
      });
      const response = await fetch(`${BRIDGE}/repo/context-guard?${params.toString()}`, {
        headers: jsonHeaders(),
        cache: 'no-store'
      });
      const data = await response.json();
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      const normalized = normalizeRepoContext(data);
      const nextSummary = normalized.summary || {};
      const nextSeverity = nextSummary.collision_severity_counts || {};
      const nextCollisionCount = Number(nextSummary.collision_count || 0);
      const nextCriticalCount = Number(nextSeverity.critical || nextSeverity.danger || 0);
      const nextRootsMissing = Number(nextSummary.roots_missing_count || 0);
      const nextTone = nextCriticalCount > 0
        ? 'danger'
        : nextCollisionCount > 0 || nextRootsMissing > 0
          ? 'warn'
          : toneForStatus(normalized.status);
      setLiveRepoContext(normalized);
      setSelectedGuardrailIndex(0);
      setSelectedCollisionKey('');
      onCommandEvent(
        'Repo guard refreshed',
        `${nextSummary.repo_count || 0} repos / ${nextCollisionCount} collisions / ${nextRootsMissing} roots missing`,
        nextTone,
        { controlId: 'repo-actions' }
      );
    } catch (error) {
      const message = error.message || 'Repo context guard route failed';
      setScanError(message);
      onCommandEvent('Repo guard refresh failed', message, 'danger', { controlId: 'repo-actions' });
    } finally {
      setIsScanning(false);
    }
  };

  const stageRepoBrief = () => {
    const packet = [
      '# Repo Guard Brief',
      '',
      `- status: ${activeRepoContext?.status || 'unknown'}`,
      `- source: ${liveRepoContext ? 'live GET /repo/context-guard' : 'cached dashboard/status snapshot'}`,
      `- generated_at_utc: ${activeRepoContext?.generated_at_utc || 'not reported'}`,
      `- repo_count: ${summary.repo_count || 0}`,
      `- roots_scanned: ${rootsScanned}`,
      `- roots_missing: ${rootsMissing}`,
      `- collisions: ${collisionCount}`,
      `- warnings: ${warningCount}`,
      `- critical: ${criticalCount}`,
      `- scan_truncated: ${summary.scan_truncated ? 'yes' : 'no'}`,
      `- cache_age_s: ${activeRepoContext?.cache_age_s ?? 0}`,
      '',
      '## Selected Guardrail',
      `- ${activeGuardrail}`,
      '',
      '## Selected Collision',
      activeCollision
        ? `- ${activeCollision.type || 'collision'} / ${activeCollision.key || 'key hidden'} / ${activeCollision.severity || 'info'} / ${impactedReposLabel(activeCollision)}`
        : '- No collision selected or reported.',
      '',
      '## Operator Intent',
      rootsMissing > 0
        ? 'Treat this as a partial repo map. Review Codebase and Sync before dispatching or publishing work.'
        : collisionCount > 0
          ? 'Resolve collision evidence before worker dispatch or port reuse.'
          : 'No collisions are reported; keep guardrails attached to any worker or publish packet.'
    ].join('\n');
    onStagePacket(packet, 'Repo guard brief staged', { controlId: 'repo-actions' });
  };

  const openRepoLane = focus => {
    onFocusChange(focus, { controlId: 'repo-actions' });
    onCommandEvent('Repo guard opened lane', focus, repoTone, { controlId: 'repo-actions' });
  };

  return (
    <Panel
      title="Repo Collision Matrix"
      meta={`${repoState} - ${summary.repo_count || 0} repos scanned`}
      tone={repoTone}
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
          <strong>{activeRepoContext?.cache_age_s ?? 0}s</strong>
        </div>
      </div>
      <div className="guardrail-grid">
        {guardrails.length === 0 ? (
          <span>No guardrails reported</span>
        ) : (
          guardrails.slice(0, 4).map((rule, index) => (
            <button
              className={`guardrail-entry ${selectedGuardrailIndex === index ? 'selected' : ''}`}
              type="button"
              key={`${rule}-${index}`}
              data-control-id="repo-actions"
              data-control-intent="Select repo guardrail"
              onClick={() => selectGuardrail(index)}
            >
              {rule}
            </button>
          ))
        )}
      </div>
      <div className={`repo-detail ${repoTone}`}>
        <div>
          <span>Selected guardrail</span>
          <strong>{repoState}</strong>
          <em>{activeGuardrail}</em>
        </div>
        <p>{activeCollision ? `${activeCollision.type || 'collision'} - ${activeCollision.key || 'key hidden'}` : 'No active collision; guardrail review is the current repo action.'}</p>
        <div className="repo-actions">
          <button
            className="primary-action"
            type="button"
            data-control-id="repo-actions"
            data-control-intent="Run protected repo context guard"
            onClick={runRepoGuard}
            disabled={isScanning}
            data-disabled-reason={isScanning ? 'Wait for the current repo context scan to finish.' : undefined}
            title={isScanning ? 'Wait for the current repo context scan to finish.' : undefined}
          >
            {isScanning ? 'Scanning' : 'Run Guard'}
          </button>
          <button className="secondary-action" type="button" data-control-id="repo-actions" onClick={stageRepoBrief}>
            Stage Repo
          </button>
          <button className="secondary-action" type="button" data-control-id="repo-actions" onClick={() => openRepoLane('codebase')}>
            Open Codebase
          </button>
          <button className="secondary-action" type="button" data-control-id="repo-actions" onClick={() => openRepoLane('sync')}>
            Open Sync
          </button>
        </div>
        <small className={`repo-live-note ${scanError ? 'warn' : liveRepoContext ? 'success' : 'info'}`}>
          {scanError || repoFreshness}
        </small>
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
                data-control-id="repo-actions"
                data-control-intent={`Select ${collision.type || 'collision'} repo collision`}
                onClick={() => selectCollision(collision, index)}
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

function CodebaseIntelligence({ codebase, activeFocus, onStagePacket, onFocusChange, onCommandEvent }) {
  const [mode, setMode] = useState('SUMMARY');
  const [selectedFindingKey, setSelectedFindingKey] = useState('');
  const [selectedIntegrationId, setSelectedIntegrationId] = useState('');
  const [liveCodebase, setLiveCodebase] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const cachedCodebase = useMemo(() => normalizeCodebaseAnalysis(codebase), [codebase]);
  const activeCodebase = liveCodebase || cachedCodebase;
  const summary = activeCodebase?.summary || {};
  const integrations = useMemo(
    () => (Array.isArray(activeCodebase?.integrations) ? activeCodebase.integrations : []),
    [activeCodebase?.integrations]
  );
  const findings = useMemo(
    () => (Array.isArray(activeCodebase?.findings) ? activeCodebase.findings : []),
    [activeCodebase?.findings]
  );
  const tone = toneForStatus(activeCodebase?.status);
  const findingKey = (item, index = 0) => `${item.title || 'finding'}:${item.detail || ''}:${index}`;
  const selectedFinding = findings.find((item, index) => findingKey(item, index) === selectedFindingKey) || findings[0];
  const selectedIntegration = integrations.find(item => (item.id || item.label) === selectedIntegrationId) || integrations[0];
  const readyIntegrations = integrations.filter(item => item.ready).length;
  const warnFindings = findings.filter(item => item.tone === 'warn').length;
  const dangerFindings = findings.filter(item => item.tone === 'danger').length;
  const codebaseTone = dangerFindings > 0 ? 'danger' : warnFindings > 0 ? 'warn' : tone;
  const routeCount = Number(summary.route_count || 0);
  const moduleCount = Number(summary.module_count || 0);
  const testCount = Number(summary.test_count || 0);
  const routeDensity = moduleCount > 0 ? Math.round(routeCount / moduleCount) : 0;
  const testCoverageSignal = routeCount > 0 ? Math.round((testCount / routeCount) * 100) : 0;
  const activeHeadline = mode === 'INTEGRATIONS'
    ? (selectedIntegration?.label || selectedIntegration?.id || 'No integration selected')
    : selectedFinding?.title || `${routeCount} routes mapped`;
  const activeDetail = mode === 'INTEGRATIONS'
    ? `${selectedIntegration?.ready ? 'Ready' : 'Needs attention'} integration lane`
    : selectedFinding?.detail || `${moduleCount} modules, ${testCount} tests, ${integrations.length} integration lanes`;
  const codebaseFreshness = liveCodebase
    ? `fresh route result ${formatTimestamp(liveCodebase.generated_at_utc)}`
    : `cached status ${formatTimestamp(activeCodebase?.generated_at_utc)}`;

  useEffect(() => {
    if (findings.length > 0 && !findings.some((item, index) => findingKey(item, index) === selectedFindingKey)) {
      setSelectedFindingKey(findingKey(findings[0], 0));
    }
  }, [findings, selectedFindingKey]);

  useEffect(() => {
    if (integrations.length > 0 && !integrations.some(item => (item.id || item.label) === selectedIntegrationId)) {
      setSelectedIntegrationId(integrations[0].id || integrations[0].label);
    }
  }, [integrations, selectedIntegrationId]);

  const changeMode = nextMode => {
    setMode(nextMode);
    onCommandEvent('Codebase lens changed', nextMode, nextMode === 'FINDINGS' && dangerFindings > 0 ? 'danger' : 'info', { controlId: 'codebase-actions' });
  };

  const selectFinding = (item, index) => {
    const key = findingKey(item, index);
    setSelectedFindingKey(key);
    setMode('FINDINGS');
    onCommandEvent('Codebase finding selected', item.title || 'finding', item.tone || 'info', { controlId: 'codebase-actions' });
  };

  const selectIntegration = item => {
    const key = item.id || item.label;
    setSelectedIntegrationId(key);
    setMode('INTEGRATIONS');
    onCommandEvent('Codebase integration selected', item.label || item.id || 'integration', item.ready ? 'success' : 'warn', { controlId: 'codebase-actions' });
  };

  const runLiveAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisError('');
    onCommandEvent('Codebase analysis requested', `${routeCount} cached routes / ${moduleCount} cached modules`, 'info', { controlId: 'codebase-actions' });
    try {
      if (!TOKEN) {
        const message = 'Bearer token required for POST /codebase/analyze; cached dashboard snapshot remains visible.';
        setAnalysisError(message);
        onCommandEvent('Codebase analysis gated', message, 'warn', { controlId: 'codebase-actions' });
        return;
      }
      const response = await fetch(`${BRIDGE}/codebase/analyze`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify({
          max_files: 2500,
          include_files: false
        })
      });
      const data = await response.json();
      if (!response.ok || data.status === 'error') {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      const normalized = normalizeCodebaseAnalysis(data);
      setLiveCodebase(normalized);
      setMode('SUMMARY');
      setSelectedFindingKey('');
      setSelectedIntegrationId('');
      onCommandEvent(
        'Codebase analysis refreshed',
        `${normalized.summary.route_count || 0} routes / ${normalized.summary.module_count || 0} modules / ${normalized.summary.test_count || 0} tests`,
        toneForStatus(normalized.status),
        { controlId: 'codebase-actions' }
      );
    } catch (error) {
      const message = error.message || 'Codebase analyzer route failed';
      setAnalysisError(message);
      onCommandEvent('Codebase analysis failed', message, 'danger', { controlId: 'codebase-actions' });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const stageCodebaseBrief = () => {
    const packet = [
      '# Codebase Intelligence Brief',
      '',
      `- root: ${activeCodebase?.root_name || 'bridge root'}`,
      `- status: ${activeCodebase?.status || 'unknown'}`,
      `- source: ${liveCodebase ? 'live POST /codebase/analyze' : 'cached dashboard/status snapshot'}`,
      `- generated_at_utc: ${activeCodebase?.generated_at_utc || 'not reported'}`,
      `- active_lens: ${mode}`,
      `- files: ${summary.file_count || 0}`,
      `- routes: ${routeCount}`,
      `- modules: ${moduleCount}`,
      `- tests: ${testCount}`,
      `- frontend_dependencies: ${summary.frontend_dependency_count || 0}`,
      `- integrations_ready: ${readyIntegrations}/${integrations.length}`,
      `- findings: ${findings.length}`,
      '',
      '## Selected Finding',
      selectedFinding
        ? `- ${selectedFinding.title}: ${selectedFinding.detail}`
        : '- No analyzer finding selected.',
      '',
      '## Selected Integration',
      selectedIntegration
        ? `- ${selectedIntegration.label || selectedIntegration.id}: ${selectedIntegration.ready ? 'ready' : 'needs attention'}`
        : '- No integration lane selected.',
      '',
      '## Operator Intent',
      mode === 'FINDINGS'
        ? 'Use this finding as the next local code review or refactor target before asking a worker to act.'
        : 'Use this snapshot to decide whether the repo shape supports the next dashboard or bridge action.'
    ].join('\n');
    onStagePacket(packet, 'Codebase intelligence brief staged', { controlId: 'codebase-actions' });
  };

  const openRepoLane = () => {
    onFocusChange('repo', { controlId: 'codebase-actions' });
    onCommandEvent('Codebase opened repo lane', activeHeadline, codebaseTone, { controlId: 'codebase-actions' });
  };

  return (
    <Panel
      title="Codebase Intelligence"
      meta={`${activeCodebase?.root_name || 'bridge root'} local snapshot`}
      tone={codebaseTone}
      focus="codebase"
      activeFocus={activeFocus}
      className="codebase-panel"
      actions={
        <div className="filter-cluster codebase-modes">
          {CODEBASE_MODES.map(item => (
            <button
              className={mode === item ? 'active' : ''}
              type="button"
              key={item}
              data-control-id="codebase-actions"
              data-control-intent={`Switch codebase mode to ${item}`}
              onClick={() => changeMode(item)}
            >
              {item}
            </button>
          ))}
        </div>
      }
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
      <div className="codebase-workbench">
        <div className={`codebase-lens ${codebaseTone}`}>
          <div>
            <span>{mode.toLowerCase()}</span>
            <strong>{activeHeadline}</strong>
            <em>{activeDetail}</em>
          </div>
          <div className="codebase-score-grid">
            <div>
              <span>Route density</span>
              <strong>{routeDensity}</strong>
            </div>
            <div>
              <span>Test signal</span>
              <strong>{testCoverageSignal}%</strong>
            </div>
            <div>
              <span>Warnings</span>
              <strong>{warnFindings + dangerFindings}</strong>
            </div>
          </div>
          <div className="codebase-actions">
            <button
              className="primary-action"
              type="button"
              data-control-id="codebase-actions"
              data-control-intent="Run protected local codebase analyzer"
              onClick={runLiveAnalysis}
              disabled={isAnalyzing}
              data-disabled-reason={isAnalyzing ? 'Wait for the current codebase analysis to finish.' : undefined}
              title={isAnalyzing ? 'Wait for the current codebase analysis to finish.' : undefined}
            >
              {isAnalyzing ? 'Analyzing' : 'Run Analysis'}
            </button>
            <button className="secondary-action" type="button" data-control-id="codebase-actions" onClick={stageCodebaseBrief}>
              Stage Brief
            </button>
            <button className="secondary-action" type="button" data-control-id="codebase-actions" onClick={openRepoLane}>
              Open Repo
            </button>
          </div>
          <small className={`codebase-live-note ${analysisError ? 'warn' : liveCodebase ? 'success' : 'info'}`}>
            {analysisError || codebaseFreshness}
          </small>
        </div>
      </div>
      <div className="integration-grid">
        {integrations.length === 0 ? (
          <span className="empty-state">No integration snapshot reported.</span>
        ) : (
          integrations.slice(0, 8).map(item => (
            <button
              className={`integration-chip ${item.ready ? 'success' : 'warn'} ${(item.id || item.label) === selectedIntegrationId ? 'selected' : ''}`}
              type="button"
              key={item.id || item.label}
              data-control-id="codebase-actions"
              data-control-intent={`Select ${item.label || item.id} integration`}
              onClick={() => selectIntegration(item)}
            >
              <i className={`worker-light ${item.ready ? 'success' : 'warn'}`} />
              {item.label || item.id}
            </button>
          ))
        )}
      </div>
      <div className="finding-list">
        {findings.length === 0 ? (
          <div className="empty-state">Analyzer has not emitted findings.</div>
        ) : (
          findings.slice(0, 4).map((item, index) => (
            <button
              className={`finding-row ${item.tone || 'info'} ${findingKey(item, index) === selectedFindingKey ? 'selected' : ''}`}
              type="button"
              key={findingKey(item, index)}
              data-control-id="codebase-actions"
              data-control-intent={`Select ${item.title} codebase finding`}
              onClick={() => selectFinding(item, index)}
            >
              <strong>{item.title}</strong>
              <span>{item.detail}</span>
            </button>
          ))
        )}
      </div>
    </Panel>
  );
}

function EventConsole({
  rows,
  filter,
  setFilter,
  paused,
  togglePaused,
  activeFocus,
  onStagePacket,
  onFocusChange,
  onCommandEvent
}) {
  const [selectedEventId, setSelectedEventId] = useState('');
  const filteredRows = useMemo(
    () => rows.filter(row => filter === 'ALL' || row.level === filter),
    [filter, rows]
  );
  const visibleRows = useMemo(() => filteredRows.slice(-60), [filteredRows]);
  const visibleRiskRows = useMemo(
    () => visibleRows.filter(row => row.level === 'ERROR' || row.level === 'WARN'),
    [visibleRows]
  );
  const defaultEvent = visibleRiskRows[visibleRiskRows.length - 1] || visibleRows[visibleRows.length - 1];
  const activeEvent = visibleRows.find(row => row.id === selectedEventId) || defaultEvent;
  const evidenceReviewWindow = useMemo(() => buildEvidenceReviewSignature(rows), [rows]);
  const evidenceIssueWindow = useMemo(() => buildEvidenceIssueWindow(rows), [rows]);
  const counts = useMemo(
    () => rows.reduce((acc, row) => {
      acc.total += 1;
      acc[row.level] = (acc[row.level] || 0) + 1;
      return acc;
    }, { total: 0, WARN: 0, ERROR: 0, OK: 0, INFO: 0 }),
    [rows]
  );
  const activeTone = activeEvent?.level === 'ERROR'
    ? 'danger'
    : activeEvent?.level === 'WARN'
      ? 'warn'
      : activeEvent?.level === 'OK'
        ? 'success'
        : 'info';
  const sourceFocus = (() => {
    const source = String(activeEvent?.source || activeEvent?.message || '').toLowerCase();
    if (source.includes('sync') || source.includes('git') || source.includes('publish')) return 'sync';
    if (source.includes('chat') || source.includes('comms') || source.includes('model') || source.includes('llm')) return 'comms';
    if (source.includes('worker') || source.includes('vm')) return 'workers';
    if (source.includes('fleet')) return 'fleet';
    if (source.includes('repo')) return 'repo';
    if (source.includes('code')) return 'codebase';
    if (source.includes('alliance') || source.includes('gemini') || source.includes('antigravity')) return 'alliance';
    if (source.includes('tiu')) return 'tiu';
    return 'overview';
  })();

  useEffect(() => {
    if (visibleRows.length === 0) {
      setSelectedEventId('');
      return;
    }
    if (!visibleRows.some(row => row.id === selectedEventId)) {
      setSelectedEventId(defaultEvent?.id || '');
    }
  }, [defaultEvent, selectedEventId, visibleRows]);

  const selectEvent = row => {
    setSelectedEventId(row.id);
    onCommandEvent('Evidence event selected', `${row.level} / ${row.source}`, row.level === 'ERROR' ? 'danger' : row.level === 'WARN' ? 'warn' : 'info', { controlId: 'evidence-actions' });
  };

  const stageSelectedEvent = () => {
    if (!activeEvent) return;
    const packet = [
      '# Evidence Event Brief',
      '',
      `- level: ${activeEvent.level}`,
      `- source: ${activeEvent.source}`,
      `- timestamp: ${activeEvent.timestamp || 'not provided'}`,
      `- focus: ${sourceFocus}`,
      `- paused: ${paused ? 'yes' : 'no'}`,
      `- filter: ${filter}`,
      '',
      '## Message',
      activeEvent.message || 'No event message.',
      '',
      '## Operator Intent',
      activeEvent.level === 'ERROR'
        ? 'Treat this as a blocker until the related lane is inspected and verified.'
        : activeEvent.level === 'WARN'
          ? 'Review this warning before claiming dashboard or bridge health.'
          : 'Use this as supporting evidence for the current dashboard state.'
    ].join('\n');
    onStagePacket(packet, `${activeEvent.level} evidence staged`, { controlId: 'evidence-actions' });
  };

  const stageEvidenceWindow = () => {
    const windowRows = evidenceIssueWindow.rows;
    const newestIssue = evidenceIssueWindow.newestIssue;
    const packet = [
      '# Evidence Window Brief',
      '',
      `- filter: ${filter}`,
      `- paused: ${paused ? 'yes' : 'no'}`,
      `- total_rows: ${rows.length}`,
      `- visible_rows: ${visibleRows.length}`,
      `- warnings: ${counts.WARN || 0}`,
      `- errors: ${counts.ERROR || 0}`,
      `- window_basis: ${evidenceIssueWindow.basis}`,
      `- issue_rows: ${evidenceIssueWindow.riskCount}`,
      `- selected_focus: ${sourceFocus}`,
      `- evidence_signature: ${evidenceReviewWindow.signature || 'none'}`,
      `- review_window_rows: ${evidenceReviewWindow.windowSize}`,
      newestIssue ? `- newest_issue: ${newestIssue.level} / ${newestIssue.source} / ${newestIssue.timestamp || '--'}` : '- newest_issue: none',
      '',
      '## Issue Window',
      ...(windowRows.length
        ? windowRows.map(row => `- ${row.level} / ${row.source} / ${row.timestamp || '--'} / ${row.message}`)
        : ['- No events visible for this filter.']),
      '',
      '## Operator Intent',
      evidenceIssueWindow.basis === 'risk'
        ? 'Use this packet as the current warning/error issue window for Jules/model review. Do not infer full bridge health until the related lanes are inspected.'
        : 'Use this packet as a bounded evidence tail for Jules/model review. Do not infer full bridge health from this window alone.'
    ].join('\n');
    onStagePacket(packet, evidenceIssueWindow.basis === 'risk' ? 'Evidence issue window staged' : 'Evidence window staged', {
      controlId: 'evidence-actions',
      evidenceKind: 'window',
      evidenceSignature: evidenceReviewWindow.signature,
      evidenceRiskCount: evidenceReviewWindow.riskCount
    });
  };

  const openEventSource = () => {
    onFocusChange(sourceFocus);
    onCommandEvent('Evidence source opened', sourceFocus, activeTone, { controlId: 'evidence-actions' });
  };

  return (
    <Panel
      title="Evidence Stream"
      meta={`${paused ? 'Paused' : 'Live tail'} - ${filter}`}
      tone={counts.ERROR > 0 ? 'danger' : counts.WARN > 0 ? 'warn' : paused ? 'warn' : 'info'}
      focus="evidence"
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
                data-control-id="evidence-actions"
                data-control-intent={`Filter evidence stream by ${item}`}
                onClick={() => setFilter(item)}
              >
                {item}
              </button>
            ))}
          </div>
          <IconButton icon={paused ? 'play' : 'pause'} label={paused ? 'Resume stream' : 'Pause stream'} onClick={togglePaused} pressed={paused} controlId="evidence-actions" />
        </>
      }
    >
      <div className="event-workbench">
        <div className="event-summary-grid">
          <div>
            <span>Total</span>
            <strong>{counts.total}</strong>
          </div>
          <div>
            <span>Warn</span>
            <strong>{counts.WARN || 0}</strong>
          </div>
          <div>
            <span>Error</span>
            <strong>{counts.ERROR || 0}</strong>
          </div>
          <div>
            <span>Selected</span>
            <strong>{activeEvent?.level || '--'}</strong>
          </div>
        </div>
        <div className={`event-issue-window ${evidenceIssueWindow.basis === 'risk' ? 'warn' : 'success'}`}>
          <div>
            <span>{evidenceIssueWindow.basis === 'risk' ? 'Issue window' : 'Review window'}</span>
            <strong>{evidenceIssueWindow.headline}</strong>
            <em>{evidenceIssueWindow.label}</em>
          </div>
          <p>
            {evidenceIssueWindow.newestIssue
              ? `${evidenceIssueWindow.newestIssue.level} / ${evidenceIssueWindow.newestIssue.source}: ${evidenceIssueWindow.newestIssue.message}`
              : 'Stage Window will preserve the current evidence tail for review.'}
          </p>
        </div>
        <div className={`event-detail ${activeTone}`}>
          <div>
            <span>Active event</span>
            <strong>{activeEvent ? `${activeEvent.level} / ${activeEvent.source}` : 'No event selected'}</strong>
            <em>{activeEvent?.timestamp || 'not sampled'}</em>
          </div>
          <p>{activeEvent?.message || 'Awaiting telemetry from the bridge event tail.'}</p>
          <div className="event-actions">
            <button
              className="secondary-action"
              type="button"
              data-control-id="evidence-actions"
              onClick={stageSelectedEvent}
              disabled={!activeEvent}
              data-disabled-reason={!activeEvent ? 'Select an event row before staging an event packet.' : undefined}
              title={!activeEvent ? 'Select an event row before staging an event packet.' : undefined}
            >
              Stage Event
            </button>
            <button
              className="secondary-action"
              type="button"
              data-control-id="evidence-actions"
              onClick={stageEvidenceWindow}
              disabled={visibleRows.length === 0}
              data-disabled-reason={visibleRows.length === 0 ? 'Wait for visible evidence rows before staging an evidence window.' : undefined}
              title={visibleRows.length === 0 ? 'Wait for visible evidence rows before staging an evidence window.' : undefined}
            >
              Stage Window
            </button>
            <button
              className="secondary-action"
              type="button"
              data-control-id="evidence-actions"
              onClick={openEventSource}
              disabled={!activeEvent}
              data-disabled-reason={!activeEvent ? 'Select an event row before opening its inferred source lane.' : undefined}
              title={!activeEvent ? 'Select an event row before opening its inferred source lane.' : undefined}
            >
              Open Source
            </button>
          </div>
        </div>
        <div className="event-console">
          {visibleRows.length === 0 ? (
            <div className="empty-state">Awaiting telemetry.</div>
          ) : (
            visibleRows.map(row => (
              <button
                className={`event-row ${row.level} ${activeEvent?.id === row.id ? 'selected' : ''}`}
                type="button"
                key={row.id}
                aria-pressed={activeEvent?.id === row.id}
                data-control-id="evidence-actions"
                data-control-intent={`Select ${row.level} evidence event`}
                onClick={() => selectEvent(row)}
              >
                <span>{row.timestamp || '--'}</span>
                <strong>{row.level}</strong>
                <em>{row.source}</em>
                <p>{row.message}</p>
              </button>
            ))
          )}
        </div>
      </div>
    </Panel>
  );
}

function Inspector({ sysStatus, worker, collision, onStagePacket, onFocusChange, onCommandEvent }) {
  const workerTone = worker?.reachable ? 'success' : toneForStatus(worker?.status);
  const collisionTone = collision?.severity === 'critical' ? 'danger' : collision?.severity === 'warning' ? 'warn' : 'info';
  const stageWorkerBrief = () => {
    if (!worker) return;
    const packet = [
      '# Worker Inspector Brief',
      '',
      `- name: ${worker.name || 'unnamed'}`,
      `- provider: ${worker.provider || 'worker'}`,
      `- zone: ${worker.zone || 'unknown'}`,
      `- endpoint: ${maskEndpoint(worker.ip)}`,
      `- status: ${worker.status || 'unknown'}`,
      `- reachable: ${worker.reachable ? 'yes' : 'no'}`,
      `- tone: ${workerTone}`,
      '',
      '## Operator Intent',
      'Use this as a masked worker-readiness note. Do not launch, pull, or mutate remote sessions without a protected route and explicit approval.'
    ].join('\n');
    onStagePacket(packet, `${worker.name || 'Worker'} inspector staged`, { controlId: 'inspector-actions' });
  };
  const stageCollisionBrief = () => {
    if (!collision) return;
    const packet = [
      '# Repo Collision Inspector Brief',
      '',
      `- type: ${collision.type || 'collision'}`,
      `- key: ${collision.key || 'hidden'}`,
      `- severity: ${collision.severity || 'info'}`,
      `- impact: ${impactedReposLabel(collision)}`,
      `- tone: ${collisionTone}`,
      '',
      '## Operator Intent',
      'Review this provenance/collision signal before dispatching workers or reusing ports, dependency refs, or repo names.'
    ].join('\n');
    onStagePacket(packet, 'Repo collision inspector staged', { controlId: 'inspector-actions' });
  };
  const stageRuntimeBrief = () => {
    const packet = [
      '# Runtime Inspector Brief',
      '',
      `- execution_context: ${sysStatus.executionContext}`,
      `- quantower: ${sysStatus.quantAllowed ? 'enabled' : 'locked'}`,
      `- bridge_status: ${sysStatus.bridgeStatus || 'unknown'}`,
      `- stream: ${sysStatus.updateMode || 'unknown'} ${sysStatus.streamSequence || 0}`,
      `- contract: ${sysStatus.contractOk ? `v${sysStatus.contract?.version || 0}` : 'waiting'}`,
      `- host: ${sysStatus.hostname || 'unknown'}`,
      '',
      '## Operator Intent',
      'Use this to anchor the current local runtime state before asking Jules or the model loop to act.'
    ].join('\n');
    onStagePacket(packet, 'Runtime inspector staged', { controlId: 'inspector-actions' });
  };
  const openInspectorLane = focus => {
    onFocusChange(focus);
    onCommandEvent('Inspector lane opened', focus, 'info', { controlId: 'inspector-actions' });
  };
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
        <div className="inspector-actions">
          <button className="secondary-action" type="button" data-control-id="inspector-actions" onClick={() => openInspectorLane('workers')}>
            Open Workers
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="inspector-actions"
            onClick={stageWorkerBrief}
            disabled={!worker}
            data-disabled-reason={!worker ? 'Select or load a worker before staging worker evidence.' : undefined}
            title={!worker ? 'Select or load a worker before staging worker evidence.' : undefined}
          >
            Stage Worker
          </button>
        </div>
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
        <div className="inspector-actions">
          <button className="secondary-action" type="button" data-control-id="inspector-actions" onClick={() => openInspectorLane('repo')}>
            Open Repo
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="inspector-actions"
            onClick={stageCollisionBrief}
            disabled={!collision}
            data-disabled-reason={!collision ? 'Select a repo collision before staging collision evidence.' : undefined}
            title={!collision ? 'Select a repo collision before staging collision evidence.' : undefined}
          >
            Stage Collision
          </button>
        </div>
      </div>
      <div className="inspector-section compact">
        <div className="runtime-stack">
          <span>Runtime</span>
          <strong>{sysStatus.executionContext}</strong>
          <em>{sysStatus.quantAllowed ? 'Quantower enabled' : 'Quantower locked'}</em>
        </div>
        <div className="inspector-actions single">
          <button className="secondary-action" type="button" data-control-id="inspector-actions" onClick={stageRuntimeBrief}>
            Stage Runtime
          </button>
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
  stagedPacket,
  setStagedPacket,
  commandJournal,
  activeFocus,
  pendingImage,
  setPendingImage,
  inputValue,
  setInputValue,
  sendChat,
  probeModelLoop,
  onKey,
  onCommandEvent
}) {
  const [mode, setMode] = useState('compose');
  const [packetIntelligence, setPacketIntelligence] = useState(null);
  const draftText = inputValue.trim();
  const activePacketText = draftText || stagedPacket?.content || '';
  const firstHeading = activePacketText.split('\n').find(line => line.trim().startsWith('#'));
  const packetTitle = firstHeading
    ? firstHeading.replace(/^#+\s*/, '').trim()
    : stagedPacket?.title || 'No packet staged';
  const packetLines = activePacketText ? activePacketText.split('\n').length : 0;
  const blockerMatches = activePacketText.match(/\b(blocked|blocker|blockers|dirty_worktree|github_auth_required|no_upstream|no_remote|behind_remote)\b/gi) || [];
  const latestCommand = commandJournal?.[0];
  const hasPacket = !!activePacketText;
  const canSendMessage = draftText.length > 0 || !!pendingImage;
  const activePacketIntelligence = packetIntelligence?.source === activePacketText ? packetIntelligence : null;
  const modes = [
    ['compose', 'Chat'],
    ['packet', 'Packet']
  ];

  useEffect(() => {
    if (stagedPacket?.stagedAt) {
      setMode('packet');
      setPacketIntelligence(null);
    }
  }, [stagedPacket?.stagedAt]);

  const selectMode = nextMode => {
    setMode(nextMode);
    onCommandEvent('Comms mode changed', nextMode, 'info', { controlId: 'comms-actions' });
  };

  const preparePacketPrompt = intent => {
    if (!activePacketText) return;
    const promptMap = {
      review: 'Review this staged dashboard packet. Return blockers, contradictions, and the next safe operator action.',
      verify: 'Verify this staged dashboard packet against the current bridge state. Call out missing evidence before any publish or worker action.',
      handoff: 'Turn this staged dashboard packet into a concise Jules handoff with scope, gates, files, commands, and remaining blockers.'
    };
    setInputValue(`${promptMap[intent]}\n\n${activePacketText}`);
    setMode('compose');
    onCommandEvent('Comms prompt prepared', intent, intent === 'verify' ? 'warn' : 'info', { controlId: 'comms-actions' });
  };

  const runLocalPacketReview = () => {
    if (!activePacketText) return;
    const verdict = buildPacketIntelligence(activePacketText, packetTitle);
    setPacketIntelligence(verdict);
    onCommandEvent('Local packet intelligence', `${verdict.score}% / ${verdict.focus}`, verdict.tone, { controlId: 'comms-actions' });
  };

  const buildPacketVerdictPrompt = () => {
    if (!activePacketText) return;
    const verdict = activePacketIntelligence || buildPacketIntelligence(activePacketText, packetTitle);
    setPacketIntelligence(verdict);
    setInputValue([
      'Verify this staged packet using the local packet intelligence verdict below. Resolve contradictions, missing evidence, and protected-action gates before suggesting any publish or worker step.',
      '',
      verdict.verdictPacket,
      '',
      '## Packet Under Review',
      activePacketText
    ].join('\n'));
    setMode('compose');
    onCommandEvent('Packet intelligence prompt prepared', `${verdict.score}% / ${verdict.focus}`, verdict.tone, { controlId: 'comms-actions' });
  };

  const restorePacket = () => {
    if (!stagedPacket?.content) return;
    setInputValue(stagedPacket.content);
    setMode('packet');
    setPacketIntelligence(null);
    onCommandEvent('Comms packet restored', stagedPacket.title || 'staged packet', 'success', { controlId: 'comms-actions' });
  };

  const clearDraft = () => {
    setInputValue('');
    setPendingImage(null);
    setStagedPacket(null);
    setPacketIntelligence(null);
    setMode('compose');
    onCommandEvent('Comms draft cleared', 'staged packet and attachment cleared', 'warn', { controlId: 'comms-actions' });
  };

  return (
    <Panel
      title="Comm Link"
      meta={stagedPacket ? stagedPacket.title : 'Jules channel'}
      tone="info"
      focus="comms"
      activeFocus={activeFocus}
      className="comm-panel"
      actions={
        <div className="comm-title-actions">
          <div className="filter-cluster comm-modes">
            {modes.map(([value, label]) => (
              <button
                className={mode === value ? 'active' : ''}
                type="button"
                key={value}
                data-control-id="comms-actions"
                data-control-intent={`Switch Comms mode to ${label}`}
                onClick={() => selectMode(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <select className="model-select" value={model} onChange={event => setModel(event.target.value)} title="Select model">
            <option value="fast">flash fast</option>
            <option value="smart">pro smart</option>
          </select>
        </div>
      }
    >
      <div className="comm-workbench">
        <div className="comm-stats">
          <div>
            <span>Draft</span>
            <strong>{draftText.length}</strong>
          </div>
          <div>
            <span>Packet</span>
            <strong>{packetLines}</strong>
          </div>
          <div>
            <span>Risk Words</span>
            <strong>{blockerMatches.length}</strong>
          </div>
          <div>
            <span>Packet IQ</span>
            <strong>{activePacketIntelligence ? activePacketIntelligence.score : '--'}</strong>
          </div>
        </div>
        {latestCommand && (
          <div className={`comm-intent-strip ${latestCommand.tone || 'info'}`}>
            <span>{formatActionTime(latestCommand.time)}</span>
            <strong>{latestCommand.title}</strong>
            <em>{latestCommand.detail}</em>
          </div>
        )}
        {mode === 'packet' ? (
          <div className="packet-review">
            <div className="packet-review-head">
              <span>Staged review</span>
              <strong>{packetTitle}</strong>
              <em>
                {hasPacket
                  ? `${activePacketText.length} chars / ${packetLines} lines`
                  : 'Stage a dashboard brief from any lane.'}
              </em>
            </div>
            <div className="packet-action-grid">
              <button
                className="secondary-action"
                type="button"
                data-control-id="comms-actions"
                onClick={() => preparePacketPrompt('review')}
                disabled={!hasPacket}
                data-disabled-reason={!hasPacket ? 'Stage a dashboard packet before preparing a review prompt.' : undefined}
                title={!hasPacket ? 'Stage a dashboard packet before preparing a review prompt.' : undefined}
              >
                Ask Review
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="comms-actions"
                onClick={() => preparePacketPrompt('verify')}
                disabled={!hasPacket}
                data-disabled-reason={!hasPacket ? 'Stage a dashboard packet before preparing a verification prompt.' : undefined}
                title={!hasPacket ? 'Stage a dashboard packet before preparing a verification prompt.' : undefined}
              >
                Ask Verify
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="comms-actions"
                onClick={() => preparePacketPrompt('handoff')}
                disabled={!hasPacket}
                data-disabled-reason={!hasPacket ? 'Stage a dashboard packet before building a handoff prompt.' : undefined}
                title={!hasPacket ? 'Stage a dashboard packet before building a handoff prompt.' : undefined}
              >
                Build Handoff
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="comms-actions"
                onClick={runLocalPacketReview}
                disabled={!hasPacket}
                data-disabled-reason={!hasPacket ? 'Stage a dashboard packet before running local packet intelligence.' : undefined}
                title={!hasPacket ? 'Stage a dashboard packet before running local packet intelligence.' : undefined}
              >
                Local Review
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="comms-actions"
                onClick={buildPacketVerdictPrompt}
                disabled={!hasPacket}
                data-disabled-reason={!hasPacket ? 'Stage a dashboard packet before building a packet-intelligence verdict.' : undefined}
                title={!hasPacket ? 'Stage a dashboard packet before building a packet-intelligence verdict.' : undefined}
              >
                Build Verdict
              </button>
              <button
                className="secondary-action"
                type="button"
                data-control-id="comms-actions"
                onClick={restorePacket}
                disabled={!stagedPacket?.content}
                data-disabled-reason={!stagedPacket?.content ? 'Stage a packet before restoring it into the draft editor.' : undefined}
                title={!stagedPacket?.content ? 'Stage a packet before restoring it into the draft editor.' : undefined}
              >
                Restore Packet
              </button>
            </div>
            {activePacketIntelligence && (
              <div className={`packet-intelligence ${activePacketIntelligence.tone}`}>
                <div className="packet-intelligence-head">
                  <span>Packet intelligence</span>
                  <strong>{activePacketIntelligence.score}% / {activePacketIntelligence.focus}</strong>
                  <em>{activePacketIntelligence.verdict}</em>
                </div>
                <div className="packet-intelligence-grid">
                  <span><strong>{activePacketIntelligence.blockers.length}</strong> blockers</span>
                  <span><strong>{activePacketIntelligence.evidenceCount}</strong> evidence</span>
                  <span><strong>{activePacketIntelligence.protectedActionCount}</strong> protected</span>
                  <span><strong>{activePacketIntelligence.missingSignals.length}</strong> missing</span>
                </div>
                <p>{activePacketIntelligence.nextAction}</p>
              </div>
            )}
            <pre className="packet-preview">
              {hasPacket ? activePacketText : 'No packet is staged yet.'}
            </pre>
          </div>
        ) : (
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
        )}
      </div>
      <div className="chat-input-area">
        {pendingImage && (
          <div className="img-strip">
            <img src={pendingImage.src} alt="attachment thumbnail" />
            <span className="img-label">Visual attached</span>
            <IconButton icon="close" label="Remove attachment" onClick={() => setPendingImage(null)} controlId="comms-actions" />
          </div>
        )}
        <div className="chat-row">
          <textarea
            className="chat-input"
            placeholder={mode === 'packet' ? 'Review or edit staged packet...' : 'Message Jules...'}
            value={inputValue}
            onChange={event => setInputValue(event.target.value)}
            onKeyDown={onKey}
            rows={mode === 'packet' ? 3 : 1}
            title="Message input"
          />
          <IconButton
            icon="send"
            label="Send message"
            onClick={sendChat}
            disabled={isThinking || !canSendMessage}
            disabledReason={
              isThinking
                ? 'Wait for the current Comms response before sending another message.'
                : !canSendMessage
                  ? 'Type a message or attach an image before sending.'
                  : undefined
            }
            controlId="comms-actions"
          />
        </div>
        <div className="comm-draft-actions">
          <button
            className="secondary-action"
            type="button"
            data-control-id="comms-actions"
            onClick={probeModelLoop}
            disabled={isThinking}
            data-disabled-reason={isThinking ? 'Wait for the current Comms response before probing the model loop.' : undefined}
            title={isThinking ? 'Wait for the current Comms response before probing the model loop.' : undefined}
          >
            Probe Model
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="comms-actions"
            onClick={() => setMode('packet')}
            disabled={!hasPacket}
            data-disabled-reason={!hasPacket ? 'Stage a packet before opening packet review.' : undefined}
            title={!hasPacket ? 'Stage a packet before opening packet review.' : undefined}
          >
            Review Draft
          </button>
          <button
            className="secondary-action"
            type="button"
            data-control-id="comms-actions"
            onClick={clearDraft}
            disabled={!draftText && !pendingImage && !stagedPacket}
            data-disabled-reason={!draftText && !pendingImage && !stagedPacket ? 'Type, attach, or stage content before clearing the draft.' : undefined}
            title={!draftText && !pendingImage && !stagedPacket ? 'Type, attach, or stage content before clearing the draft.' : undefined}
          >
            Clear
          </button>
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
  const [stagedPacket, setStagedPacket] = useState(null);
  const [pendingImage, setPendingImage] = useState(null);
  const [model, setModel] = useState('fast');
  const [isThinking, setIsThinking] = useState(false);
  const [activeFocus, setActiveFocus] = useState('overview');
  const [focusRequestId, setFocusRequestId] = useState(0);
  const [selectedWorkerKey, setSelectedWorkerKey] = useState('');
  const [selectedCollisionKey, setSelectedCollisionKey] = useState('');
  const [selectedTopologyId, setSelectedTopologyId] = useState('sync');
  const [selectedOpsId, setSelectedOpsId] = useState('cloud-sync');
  const [streamPaused, setStreamPaused] = useState(false);
  const [streamSnapshot, setStreamSnapshot] = useState([]);
  const [eventFilter, setEventFilter] = useState('ALL');
  const [commandJournal, setCommandJournal] = useState(loadInitialCommandJournal);
  const [liveBlockerRun, setLiveBlockerRun] = useState(null);
  const [selectedLiveBlockerId, setSelectedLiveBlockerId] = useState('');
  const [lastClickTrace, setLastClickTrace] = useState(null);
  const chatBoxRef = useRef(null);
  const commandSequenceRef = useRef(0);

  const pushCommand = (title, detail, tone = 'info', meta = {}) => {
    commandSequenceRef.current += 1;
    const commandId = `${Date.now()}-${commandSequenceRef.current}`;
    const controlIds = [
      meta?.controlId,
      ...(Array.isArray(meta?.controlIds) ? meta.controlIds : [])
    ].filter(Boolean);
    const evidenceSignature = String(meta?.evidenceSignature || '').trim();
    const evidenceMeta = evidenceSignature
      ? {
        evidenceSignature: evidenceSignature.slice(0, 220),
        evidenceKind: String(meta?.evidenceKind || 'window').slice(0, 40),
        evidenceRiskCount: Number(meta?.evidenceRiskCount || 0)
      }
      : {};
    const nextCommand = {
      id: commandId,
      time: new Date().toISOString(),
      title,
      detail,
      tone,
      ...(controlIds.length > 0 ? { controlId: controlIds[0], controlIds } : {}),
      ...evidenceMeta
    };
    const storedProofs = loadStoredCommandJournalProofs();
    setCommandJournal(previous => mergeCommandJournalRows(
      [nextCommand],
      previous,
      storedProofs
    ).slice(0, COMMAND_JOURNAL_MAX_ROWS));
  };

  const traceControlClick = useCallback(event => {
    try {
      const button = event.target?.closest?.('button');
      if (!button || !event.currentTarget?.contains?.(button)) return;
      const label = compactControlLabel(
        button.getAttribute('aria-label')
        || button.innerText
        || button.textContent
        || button.getAttribute('title')
        || 'button'
      ).slice(0, 120);
      const controlIds = [
        ...normalizeControlIdList(button.getAttribute('data-control-id')),
        ...normalizeControlIdList(button.getAttribute('data-control-ids'))
      ];
      const control = CONTROL_BY_ID.get(controlIds[0]);
      const section = compactControlLabel(
        button.closest('[data-panel-focus]')?.getAttribute('data-panel-focus')
        || button.closest('.command-bar')?.className
        || activeFocus
        || 'dashboard'
      );
      setLastClickTrace({
        tracedAt: new Date().toISOString(),
        label,
        controlId: controlIds[0] || '',
        controlIds,
        section,
        intent: compactControlLabel(button.getAttribute('data-control-intent') || control?.action || button.getAttribute('title') || label).slice(0, 180),
        expected: control?.expected || '',
        focus: control?.focus || section || activeFocus || 'overview'
      });
    } catch (error) {
      // Keep core click wiring alive even if control-trace metadata collection hits an edge case.
      console.warn('Control click trace failed; action still proceeds.', error);
    }
  }, [activeFocus]);

  const applyDashboardStatusPayload = useCallback((payload, fallbackMode = 'poll') => {
    const nextStatus = normalizeDashboardPayload(payload);
    const mode = nextStatus.contractOk ? (nextStatus.updateMode || fallbackMode) : 'contract-drift';
    const statusWithMode = { ...nextStatus, updateMode: mode };
    setSysStatus(statusWithMode);
    setCpuHistory(previous => [...previous.slice(1), nextStatus.cpu]);
    setMemHistory(previous => [...previous.slice(1), nextStatus.mem]);
    return statusWithMode;
  }, []);

  const markDashboardOffline = useCallback(() => {
    let offlineStatus = null;
    setSysStatus(previous => {
      offlineStatus = offlineDashboardStatusSnapshot(previous);
      return offlineStatus;
    });
    return offlineStatus || offlineDashboardStatusSnapshot();
  }, []);

  const refreshDashboardStatus = useCallback(async (mode = 'manual') => {
    try {
      const response = await fetch(`${BRIDGE}/dashboard/status`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`status ${response.status}`);
      const payload = await response.json();
      return applyDashboardStatusPayload(payload, mode);
    } catch {
      return markDashboardOffline();
    }
  }, [applyDashboardStatusPayload, markDashboardOffline]);

  useEffect(() => {
    let mounted = true;
    let pollTimer = null;
    let startupTimer = null;
    let eventSource = null;
    let streamReceived = false;

    const applyStatusPayload = (payload, fallbackMode) => {
      if (!mounted) return;
      applyDashboardStatusPayload(payload, fallbackMode);
    };

    const markOffline = () => {
      if (mounted) {
        markDashboardOffline();
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
  }, [applyDashboardStatusPayload, markDashboardOffline]);

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
  const selectedTopology = topology.find(item => item.id === selectedTopologyId) || topology[0];
  const selectedOpsItem = opsItems.find(item => item.id === selectedOpsId) || opsItems[0];
  const eventRows = useMemo(
    () => buildEventRows(streamPaused ? streamSnapshot : sysStatus.logs),
    [streamPaused, streamSnapshot, sysStatus.logs]
  );
  const liveBlockerQueue = useMemo(
    () => buildLiveBlockerQueue({
      sync: sysStatus.cloudSync || DEFAULT_STATUS.cloudSync,
      eventRows,
      commandJournal
    }),
    [commandJournal, eventRows, sysStatus.cloudSync]
  );

  useEffect(() => {
    if (!selectedLiveBlockerId) return;
    if (!liveBlockerQueue.some(row => row.id === selectedLiveBlockerId)) {
      setSelectedLiveBlockerId('');
    }
  }, [liveBlockerQueue, selectedLiveBlockerId]);

  useEffect(() => {
    if (topology.length > 0 && !topology.some(item => item.id === selectedTopologyId)) {
      setSelectedTopologyId(topology[0].id);
    }
  }, [selectedTopologyId, topology]);

  useEffect(() => {
    if (opsItems.length > 0 && !opsItems.some(item => item.id === selectedOpsId)) {
      setSelectedOpsId(opsItems[0].id);
    }
  }, [opsItems, selectedOpsId]);

  const requestFocus = focus => {
    setActiveFocus(focus);
    setFocusRequestId(previous => previous + 1);
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage?.setItem(
        COMMAND_JOURNAL_STORAGE_KEY,
        JSON.stringify(serializePersistentCommandJournal(commandJournal, DASHBOARD_CONTROL_IDS))
      );
    } catch {
      // Local proof persistence is a convenience layer; the live journal remains authoritative.
    }
  }, [commandJournal]);

  useEffect(() => {
    const target = document.querySelector(`[data-panel-focus="${activeFocus}"]`);
    if (!target) return undefined;
    scrollFocusPanelIntoView(target);
    const settleTimer = window.setTimeout(() => {
      scrollFocusPanelIntoView(target);
    }, 80);
    return () => window.clearTimeout(settleTimer);
  }, [activeFocus, focusRequestId]);

  const changeFocus = (focus, meta = {}) => {
    requestFocus(focus);
    pushCommand('Focus changed', focus, 'info', meta);
  };

  const togglePaused = () => {
    if (streamPaused) {
      setStreamPaused(false);
      setStreamSnapshot([]);
      pushCommand('Evidence stream resumed', 'live log tail restored', 'success', { controlId: 'evidence-actions' });
      return;
    }
    setStreamSnapshot(sysStatus.logs);
    setStreamPaused(true);
    pushCommand('Evidence stream paused', `${sysStatus.logs.length} log rows frozen`, 'warn', { controlId: 'evidence-actions' });
  };

  const changeEventFilter = filter => {
    setEventFilter(filter);
    pushCommand('Evidence filter changed', filter, filter === 'ERROR' ? 'danger' : filter === 'WARN' ? 'warn' : 'info', { controlId: 'evidence-actions' });
  };

  const selectWorker = key => {
    setSelectedWorkerKey(key);
    pushCommand('Worker selected', key, 'success', { controlId: 'workers-actions' });
  };

  const selectCollision = key => {
    setSelectedCollisionKey(key);
    pushCommand('Repo evidence selected', key, 'warn', { controlId: 'repo-actions' });
  };

  const selectTopology = node => {
    setSelectedTopologyId(node.id);
    if (node.focus) {
      requestFocus(node.focus);
    }
    pushCommand('Topology selected', `${node.label} -> ${node.focus || 'overview'}`, node.tone || 'info', { controlId: 'mission-open' });
  };

  const openTopology = node => {
    if (node.focus) {
      changeFocus(node.focus, { controlId: 'mission-open' });
    }
    setSelectedTopologyId(node.id);
    pushCommand('Topology lane opened', node.label, node.tone || 'info', { controlId: 'mission-open' });
  };

  const selectOpsItem = item => {
    setSelectedOpsId(item.id);
    if (item.focus) {
      requestFocus(item.focus);
    }
    pushCommand('Gate selected', `${item.label} -> ${item.state}`, item.tone || 'info', { controlId: 'ops-plan' });
  };

  const openOpsItem = item => {
    if (item.focus) {
      changeFocus(item.focus, { controlId: 'ops-plan' });
    }
    setSelectedOpsId(item.id);
    pushCommand('Gate lane opened', item.label, item.tone || 'info', { controlId: 'ops-plan' });
  };

  const openHeaderStatus = ({ label, focus = 'overview', tone = 'info', topologyId, opsId }) => {
    if (topologyId) setSelectedTopologyId(topologyId);
    if (opsId) setSelectedOpsId(opsId);
    requestFocus(focus);
    pushCommand('Header status opened', `${label} -> ${focus}`, tone, { controlId: 'header-strip' });
  };

  const sendCommsMessage = async ({
    message,
    image = null,
    clearDraft = false,
    userLabel = '',
    successTitle = 'Comms response received'
  }) => {
    const outboundMessage = String(message || '').trim();
    const currentImage = image;
    if (!outboundMessage && !currentImage) {
      setChatHistory(previous => [...previous, { role: 'sys', content: 'COMM LINK WAIT: type a message or attach an image first.' }]);
      pushCommand(
        'Comms blocked',
        'Send was blocked because the draft was empty.',
        'warn',
        { controlId: 'comms-actions' }
      );
      return null;
    }

    if (clearDraft) {
      setInputValue('');
      setPendingImage(null);
    }
    setChatHistory(previous => [
      ...previous,
      { role: 'user', content: userLabel || outboundMessage || '[screenshot]', img: currentImage?.src }
    ]);
    setIsThinking(true);

    try {
      const payload = { message: outboundMessage || 'Analyze this visual data.', model };
      if (currentImage) payload.image_base64 = currentImage.base64;
      const response = await fetch(`${BRIDGE}/chat`, {
        method: 'POST',
        headers: jsonHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || data.error || `status ${response.status}`);
      }
      const reply = data.response || 'No response.';
      const meta = data.model_used ? `${data.model_used} - ${data.elapsed_ms}ms` : '';
      const responseErrors = Array.isArray(data.errors) ? data.errors : [];
      const degradedReason = commsDegradedReason(reply, responseErrors);
      const degraded = data.model_used === 'none' || responseErrors.length > 0 || !!degradedReason;
      setChatHistory(previous => [...previous, { role: 'ai', content: reply, meta }]);
      pushCommand(
        degraded ? 'Comms degraded' : successTitle,
        degraded ? `${meta || 'model loop unavailable'} / ${responseErrors[0] || degradedReason || 'offline fallback'}` : meta || 'model loop returned',
        degraded ? 'warn' : 'success',
        { controlId: 'comms-actions' }
      );
      return data;
    } catch (error) {
      setChatHistory(previous => [...previous, { role: 'sys', content: `COMM LINK FAILED: ${error.message}` }]);
      pushCommand('Comms failed', error.message, 'danger', { controlId: 'comms-actions' });
      return null;
    } finally {
      setIsThinking(false);
    }
  };

  const sendChat = async () => {
    await sendCommsMessage({
      message: inputValue,
      image: pendingImage,
      clearDraft: true
    });
  };

  const probeModelLoop = async () => {
    await sendCommsMessage({
      message: 'Say JULES_COMMS_PROOF_OK and one short sentence describing the live bridge skill you can perform right now.',
      userLabel: '[model loop proof probe]',
      successTitle: 'Comms response received'
    });
  };

  const onKey = event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if ((inputValue || '').trim() || pendingImage) {
        if (isThinking) {
          pushCommand(
            'Comms blocked',
            'Wait for the current Comms response before sending.',
            'warn',
            { controlId: 'comms-actions' }
          );
          return;
        }
        sendChat();
      } else {
        pushCommand(
          'Comms blocked',
          'Press Send blocked because there is no draft content to send.',
          'warn',
          { controlId: 'comms-actions' }
        );
      }
    }
  };

  const stagePacketForComms = (packet, title = 'Packet staged', meta = {}) => {
    const { keepFocus = false, ...commandMeta } = meta || {};
    setInputValue(packet);
    setStagedPacket({
      title,
      content: packet,
      stagedAt: new Date().toISOString()
    });
    if (!keepFocus) requestFocus('comms');
    pushCommand(title, `${packet.length} characters staged to Comms`, 'success', commandMeta);
  };

  const stageTopologyBrief = (node, meta = {}) => {
    const packet = [
      '# Dashboard Topology Brief',
      '',
      `- node: ${node.label}`,
      `- status: ${node.detail}`,
      `- metric: ${node.metric}`,
      `- tone: ${node.tone || 'info'}`,
      `- focus: ${node.focus || 'overview'}`,
      `- active_dashboard_focus: ${activeFocus}`,
      '',
      '## Operator Intent',
      'Open the linked dashboard lane, inspect current evidence, and do not run live worker or publish actions without explicit approval.'
    ].join('\n');
    stagePacketForComms(packet, `${node.label} topology staged`, { controlId: 'mission-stage', ...meta });
  };

  const stageOpsBrief = (item, meta = {}) => {
    const packet = [
      '# Dashboard Gate Brief',
      '',
      `- gate: ${item.label}`,
      `- state: ${item.state}`,
      `- progress: ${item.progress}%`,
      `- tone: ${item.tone || 'info'}`,
      `- focus: ${item.focus || 'overview'}`,
      `- detail: ${item.detail}`,
      '',
      '## Operator Intent',
      'Treat this as a review packet. Use the linked lane to inspect evidence before any protected action route is called.'
    ].join('\n');
    stagePacketForComms(packet, `${item.label} gate staged`, { controlId: 'ops-plan', ...meta });
  };

  const openLiveBlocker = row => {
    if (!row) return;
    setSelectedLiveBlockerId(row.id);
    requestFocus(row.focus || 'overview');
    pushCommand(
      'Live blocker opened',
      `${row.label} -> ${row.focus || 'overview'}`,
      row.tone || 'warn',
      { controlId: 'action-receipt' }
    );
  };

  const runLiveBlocker = async row => {
    if (!row) return;
    setSelectedLiveBlockerId(row.id);
    const selectedBlockerRun = row.id !== liveBlockerQueue[0]?.id;
    const blockerActionLabel = selectedBlockerRun ? 'Selected blocker' : 'Top blocker';
    const actionId = row.safeActionId || row.controlId;
    const action = safeShellActions.find(item => item.id === actionId);
    if (!action) {
      const run = {
        ranAt: new Date().toISOString(),
        blockerId: row.id,
        label: row.label,
        tone: 'warn',
        summary: 'Manual lane inspection required; no safe local checker is mapped for this blocker.',
        exitCriteria: row.exitCriteria || row.action || 'Open the linked lane and rerun Break Test after review.',
        rows: [
          {
            id: `${row.id}-manual`,
            label: 'Manual gate',
            tone: 'warn',
            observed: row.action || 'Open the linked lane and gather evidence.'
          }
        ]
      };
      setLiveBlockerRun(run);
      requestFocus(row.focus || 'overview');
      pushCommand(`${blockerActionLabel} check gated`, `${row.label}: manual review required`, 'warn', { controlId: 'action-receipt' });
      return;
    }

    try {
      const result = await action.run({ keepFocus: true });
      const blockers = Array.isArray(result?.blockers) ? result.blockers : [];
      const warnings = Array.isArray(result?.warnings) ? result.warnings : [];
      const tone = result?.tone || row.tone || 'info';
      const runRows = [
        {
          id: `${row.id}-blocker`,
          label: row.label,
          tone: row.tone || 'warn',
          observed: row.detail || row.headline || 'Blocker sampled.'
        },
        {
          id: `${row.id}-${action.id}`,
          label: action.label,
          tone,
          observed: action.summarize ? action.summarize(result) : result?.detail || 'Safe local checker ran.'
        },
        {
          id: `${row.id}-remaining`,
          label: 'Remaining signals',
          tone: blockers.length > 0 ? 'danger' : warnings.length > 0 ? 'warn' : 'success',
          observed: `${blockers.length} blockers / ${warnings.length} warnings`
        }
      ];
      const run = {
        ranAt: new Date().toISOString(),
        blockerId: row.id,
        label: `${row.label} -> ${action.label}`,
        tone,
        summary: `${result?.detail || row.headline}; ${blockers.length} blockers; ${warnings.length} warnings`,
        exitCriteria: row.exitCriteria || row.action || 'Rerun Break Test after this blocker check is reviewed.',
        rows: runRows
      };
      setLiveBlockerRun(run);
      pushCommand(
        `${blockerActionLabel} check run`,
        `${row.label}: ${result?.detail || action.label}`,
        tone,
        { controlId: 'action-receipt', controlIds: [row.controlId].filter(Boolean) }
      );
    } catch (error) {
      const detail = String(error?.message || error);
      setLiveBlockerRun({
        ranAt: new Date().toISOString(),
        blockerId: row.id,
        label: row.label,
        tone: 'danger',
        summary: detail,
        exitCriteria: row.exitCriteria || row.action || 'Open the linked lane and inspect the failed safe checker.',
        rows: [
          {
            id: `${row.id}-failed`,
            label: 'Safe checker failed',
            tone: 'danger',
            observed: detail
          }
        ]
      });
      pushCommand(`${blockerActionLabel} check failed`, `${row.label}: ${detail}`, 'danger', { controlId: 'action-receipt' });
    }
  };

  const stageLiveBlocker = row => {
    if (!row) return;
    setSelectedLiveBlockerId(row.id);
    const packet = [
      '# Live Dashboard Blocker',
      '',
      `- blocker: ${row.label}`,
      `- headline: ${row.headline}`,
      `- tone: ${row.tone || 'warn'}`,
      `- focus: ${row.focus || 'overview'}`,
      `- control_id: ${row.controlId || 'none'}`,
      `- safe_action_id: ${row.safeActionId || row.controlId || 'none'}`,
      `- active_focus: ${activeFocus || 'overview'}`,
      `- queue_depth: ${liveBlockerQueue.length}`,
      '- protected_routes_called: no',
      '- chat_send_called: no',
      '- publish_or_dispatch_called: no',
      '',
      '## Detail',
      row.detail || 'No detail recorded.',
      '',
      '## Immediate Safe Action',
      row.action || 'Open the linked lane and gather evidence before a ready claim.',
      '',
      '## Exit Criteria',
      row.exitCriteria || 'Rerun Break Test after this blocker is reviewed and resolved.',
      '',
      '## Evidence',
      ...(Array.isArray(row.evidence) && row.evidence.length
        ? row.evidence.map(item => `- ${item}`)
        : ['- No bounded evidence rows attached to this blocker.']),
      '',
      '## Current Queue',
      ...liveBlockerQueue.slice(0, 5).map(item => `- ${String(item.tone || 'warn').toUpperCase()} / ${item.label} / ${item.headline} / focus ${item.focus || 'overview'}`),
      '',
      '## Operator Intent',
      'Use this as a review-only blocker card. Open the linked lane, collect evidence, and rerun Break Test before claiming the dashboard is ready.'
    ].join('\n');
    stagePacketForComms(packet, `${row.label} blocker staged`, { controlId: 'action-receipt' });
  };

  const planOpsStep = (item, recommendation, meta = {}) => {
    if (!item) return;
    const lane = item.focus || 'overview';
    const packet = [
      '# Smart Gate Step',
      '',
      `- gate: ${item.label}`,
      `- state: ${item.state}`,
      `- progress: ${item.progress}%`,
      `- tone: ${item.tone || 'info'}`,
      `- lane: ${lane}`,
      `- recommendation: ${recommendation?.label || 'Review selected gate'}`,
      `- reason: ${recommendation?.detail || item.detail}`,
      '',
      '## Evidence To Inspect',
      `- open_lane: ${lane}`,
      `- current_detail: ${item.detail}`,
      `- active_focus_before_plan: ${activeFocus}`,
      '',
      '## Operator Intent',
      item.tone === 'success'
        ? 'Use this as supporting evidence for the next safe packet or handoff.'
        : 'Do not publish or launch live worker actions until this gate has been inspected and the blocker or warning is explained.'
    ].join('\n');
    setSelectedOpsId(item.id);
    stagePacketForComms(packet, `${item.label} smart step staged`, { controlId: 'ops-plan', ...meta });
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

  const runReceiptBridgeProbe = async () => {
    const rows = await Promise.all(BRIDGE_PROBE_ENDPOINTS.map(async endpoint => {
      const startedAt = performance.now();
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 6000);
      try {
        const response = await fetch(`${BRIDGE}${endpoint.path}`, {
          cache: 'no-store',
          signal: controller.signal
        });
        let data = {};
        try {
          data = await response.json();
        } catch {
          data = {};
        }
        const latencyMs = Math.round(performance.now() - startedAt);
        const passed = response.ok && endpoint.pass(data);
        return {
          id: endpoint.id,
          label: endpoint.label,
          path: endpoint.path,
          status: response.status,
          latencyMs,
          tone: response.ok ? (passed ? 'success' : 'warn') : 'danger',
          detail: response.ok ? endpoint.detail(data) : `HTTP ${response.status}`
        };
      } catch (error) {
        const latencyMs = Math.round(performance.now() - startedAt);
        return {
          id: endpoint.id,
          label: endpoint.label,
          path: endpoint.path,
          status: 0,
          latencyMs,
          tone: 'danger',
          detail: error?.name === 'AbortError' ? 'Timed out after 6000ms' : String(error?.message || error)
        };
      } finally {
        window.clearTimeout(timeoutId);
      }
    }));
    const failCount = rows.filter(row => row.tone === 'danger').length;
    const warnCount = rows.filter(row => row.tone === 'warn').length;
    const passCount = rows.filter(row => row.tone === 'success').length;
    const totalCount = rows.length;
    const averageMs = totalCount
      ? Math.round(rows.reduce((sum, row) => sum + row.latencyMs, 0) / totalCount)
      : 0;
    const tone = failCount > 0 ? 'danger' : warnCount > 0 ? 'warn' : 'success';
    return {
      tone,
      detail: `${passCount}/${totalCount} public routes passed; ${failCount} failed; avg ${averageMs}ms`,
      blockers: rows.filter(row => row.tone === 'danger').map(row => `${row.label}: ${row.detail}`),
      warnings: rows.filter(row => row.tone === 'warn').map(row => `${row.label}: ${row.detail}`),
      rows,
      passCount,
      warnCount,
      failCount,
      totalCount,
      averageMs
    };
  };

  const safeShellActions = [
    {
      id: 'bridge-probe',
      label: 'Run Live Bridge Probe',
      source: 'public-route-probe',
      run: runReceiptBridgeProbe,
      summarize: result => `${result?.passCount || 0}/${result?.totalCount || 0} public routes passed; avg ${result?.averageMs || 0}ms`
    },
    {
      id: 'nav-rail',
      label: 'Open Sync Rail',
      source: 'local-shell-route',
      run: () => {
        changeFocus('sync', { controlId: 'nav-rail' });
        return { tone: 'success', detail: 'sync' };
      },
      summarize: result => `Navigation rail opened ${result?.detail || 'sync'} through the shell focus handler.`
    },
    {
      id: 'mission-open',
      label: 'Open Mission Lane',
      source: 'local-shell-route',
      run: () => {
        if (!selectedTopology) throw new Error('No mission topology route is available.');
        openTopology(selectedTopology);
        return { tone: selectedTopology.tone || 'success', detail: selectedTopology.label };
      },
      summarize: result => `Mission Control opened ${result?.detail || 'the selected topology route'}.`
    },
    {
      id: 'mission-stage',
      label: 'Stage Mission Brief',
      source: 'local-shell-route',
      run: (options = {}) => {
        if (!selectedTopology) throw new Error('No mission topology route is available to stage.');
        stageTopologyBrief(selectedTopology, { keepFocus: options.keepFocus });
        return { tone: selectedTopology.tone || 'success', detail: selectedTopology.label };
      },
      summarize: result => `Mission Control staged ${result?.detail || 'the selected topology route'} into Comms.`
    },
    {
      id: 'ops-plan',
      label: 'Stage Gate Plan',
      source: 'local-shell-route',
      run: (options = {}) => {
        if (!selectedOpsItem) throw new Error('No checklist gate is available to plan.');
        planOpsStep(selectedOpsItem, gateRecommendation(selectedOpsItem), { keepFocus: options.keepFocus });
        return { tone: selectedOpsItem.tone || 'success', detail: selectedOpsItem.label };
      },
      summarize: result => `No Slop checklist staged ${result?.detail || 'the selected gate'} as a Smart Gate Step.`
    },
    {
      id: 'tiu-workbench',
      label: 'Stage TIU Local Preview',
      source: 'local-preview-builder',
      run: (options = {}) => {
        const preview = buildLocalTiuPreview({
          objective: 'Safe Batch local TIU preview for dashboard intelligence proof.',
          scope: 'dashboard',
          modelLane: 'alliance',
          mode: 'design_review',
          requireCloudSync: true,
          includeLiveChecks: false,
          writePacket: false,
          sysStatus
        });
        stagePacketForComms(preview.packet, 'TIU local preview staged', { controlId: 'tiu-workbench', keepFocus: options.keepFocus });
        return {
          tone: toneForActionStatus(preview),
          detail: preview.plan_state || preview.status || 'local_preview',
          blockers: preview.blockers || [],
          warnings: preview.warnings || [],
          packet: preview.packet,
          packetTitle: 'TIU local preview'
        };
      },
      summarize: result => `TIU local preview ${result?.detail || 'built'} staged without protected routes; blockers ${(result?.blockers || []).length}; warnings ${(result?.warnings || []).length}.`
    },
    {
      id: 'sync-packet',
      label: 'Stage Sync Local Preview',
      source: 'local-preview-builder',
      run: (options = {}) => {
        const preview = buildLocalPublishPreview(sysStatus.cloudSync || DEFAULT_STATUS.cloudSync, false);
        stagePacketForComms(preview.packet, 'Publish local preview staged', { controlId: 'sync-packet', keepFocus: options.keepFocus });
        return {
          tone: toneForActionStatus(preview),
          detail: preview.state || preview.status || 'local_preview',
          blockers: preview.blockers || [],
          warnings: preview.warnings || [],
          packet: preview.packet,
          packetTitle: 'Cloud Sync local preview'
        };
      },
      summarize: result => `Cloud Sync local preview ${result?.detail || 'built'} staged without protected routes; blockers ${(result?.blockers || []).length}; warnings ${(result?.warnings || []).length}.`
    },
    {
      id: 'telemetry-actions',
      label: 'Stage Telemetry Pressure',
      source: 'local-panel-action',
      run: (options = {}) => {
        const maxedOut = String(sysStatus.resourceStatus || '').toLowerCase() === 'maxed_out'
          || Number(sysStatus.mem || 0) >= 90
          || Number(sysStatus.cpu || 0) >= 90;
        const pressureTone = maxedOut
          ? 'danger'
          : Number(sysStatus.mem || 0) > 85 || Number(sysStatus.cpu || 0) > 85
            ? 'warn'
            : toneForStatus(sysStatus.resourceStatus);
        const selectedLens = Number(sysStatus.mem || 0) >= Number(sysStatus.cpu || 0) ? 'Memory' : 'CPU';
        const packet = [
          '# Telemetry Pressure Brief',
          '',
          `- status: ${sysStatus.resourceStatus || 'unknown'}`,
          `- cpu_percent: ${Number(sysStatus.cpu || 0).toFixed(1)}`,
          `- memory_percent: ${Number(sysStatus.mem || 0).toFixed(1)}`,
          `- selected_lens: ${selectedLens}`,
          `- maxed_out: ${maxedOut ? 'yes' : 'no'}`,
          `- execution_context: ${sysStatus.executionContext}`,
          `- quantower: ${sysStatus.quantAllowed ? 'enabled' : 'locked'}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Reasons',
          ...(sysStatus.pressureReasons?.length
            ? sysStatus.pressureReasons.map(reason => `- ${reason}`)
            : ['- No resource pressure reasons reported.']),
          '',
          '## Operator Intent',
          maxedOut
            ? 'Hold new local worker launches. Review Fleet and Sync state, then stage a bounded packet before dispatch.'
            : 'Proceed with bounded review work, but keep watching pressure before launching more workers.'
        ].join('\n');
        stagePacketForComms(packet, 'Telemetry pressure brief staged', { controlId: 'telemetry-actions', keepFocus: options.keepFocus });
        return { tone: pressureTone, detail: `${selectedLens} ${maxedOut ? 'maxed' : 'sampled'}` };
      },
      summarize: result => `Telemetry pressure packet staged from local panel state; ${result?.detail || 'pressure sampled'}.`
    },
    {
      id: 'alliance-actions',
      label: 'Stage Alliance Lane',
      source: 'local-panel-action',
      run: (options = {}) => {
        const alliance = sysStatus.alliance || DEFAULT_STATUS.alliance;
        const lanes = buildAllianceLanes(sysStatus);
        const lane = lanes.find(row => row.tone !== 'success') || lanes[0];
        if (!lane) throw new Error('No alliance lane is available.');
        const packet = [
          '# Alliance Lane Brief',
          '',
          `- lane: ${lane.label}`,
          `- role: ${lane.role}`,
          `- state: ${lane.state}`,
          `- ready: ${lane.ready ? 'yes' : 'no'}`,
          `- tone: ${lane.tone || 'info'}`,
          `- detail: ${lane.detail}`,
          `- alliance_mode: ${alliance.mode || 'unknown'}`,
          `- creator: ${alliance.creator || 'jules'}`,
          `- implementer: ${alliance.implementer || 'unassigned'}`,
          `- gates: ${alliance.gate_pass_count || 0}/${alliance.gate_total_count || 0}`,
          `- live_work: ${alliance.safe_to_launch_live_work ? 'open' : 'gated'}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Operator Intent',
          lane.id === 'sync'
            ? 'Inspect the Sync lane and build a publish packet before any cloud publish.'
            : 'Use the TIU workbench to prepare a review packet for this alliance lane before live work.'
        ].join('\n');
        stagePacketForComms(packet, `${lane.label} alliance staged`, { controlId: 'alliance-actions', keepFocus: options.keepFocus });
        return { tone: lane.tone || 'info', detail: `${lane.label} / ${lane.state}`, packet, packetTitle: 'Alliance Lane Brief' };
      },
      summarize: result => `Alliance lane packet staged from local panel state; ${result?.detail || 'lane selected'}.`
    },
    {
      id: 'fleet-actions',
      label: 'Stage Fleet Queue',
      source: 'local-panel-action',
      run: (options = {}) => {
        const fleet = sysStatus.fleet || DEFAULT_STATUS.fleet;
        const launched = Number(fleet.launched || 0);
        const completed = Number(fleet.completed || 0);
        const failed = Number(fleet.failed || 0);
        const inProgress = Number(fleet.in_progress || 0);
        const pending = Number(fleet.pending || 0);
        const readiness = failed > 0 ? 'recovery needed' : pending > 0 ? 'dispatch review' : inProgress > 0 ? 'monitor active' : launched > 0 ? 'complete' : 'idle';
        const tone = failed > 0 ? 'danger' : pending > 0 || inProgress > 0 ? 'warn' : 'success';
        const packet = [
          '# Fleet Queue Brief',
          '',
          `- launched: ${launched}`,
          `- completed: ${completed}`,
          `- in_progress: ${inProgress}`,
          `- pending: ${pending}`,
          `- failed: ${failed}`,
          `- all_complete: ${fleet.all_complete ? 'yes' : 'no'}`,
          `- sessions_tracked: ${fleet.sessions_tracked || 0}`,
          `- readiness: ${readiness}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Queue State',
          `- Complete: ${completed}`,
          `- Active: ${inProgress}`,
          `- Pending: ${pending}`,
          `- Failed: ${failed}`,
          '',
          '## Operator Intent',
          pending > 0
            ? 'Do not launch queued sessions blindly. Prepare a TIU or worker packet, then verify worker health.'
            : 'Use this packet to decide whether the fleet loop can close or needs monitoring.'
        ].join('\n');
        stagePacketForComms(packet, 'Fleet queue brief staged', { controlId: 'fleet-actions', keepFocus: options.keepFocus });
        return { tone, detail: readiness };
      },
      summarize: result => `Fleet queue packet staged from local panel state; readiness ${result?.detail || 'unknown'}.`
    },
    {
      id: 'workers-actions',
      label: 'Stage Worker Directory',
      source: 'local-panel-action',
      run: (options = {}) => {
        const worker = selectedWorker || workers[0];
        const offlineCount = Math.max(Number(cloud.total || 0) - Number(cloud.online || 0), 0);
        const tone = worker ? (worker.reachable ? 'success' : toneForStatus(worker.status)) : 'warn';
        const packet = [
          '# Worker Directory Brief',
          '',
          `- selected_worker: ${worker?.name || 'none'}`,
          `- provider: ${worker?.provider || 'worker'}`,
          `- zone: ${worker?.zone || 'unknown'}`,
          `- endpoint: ${worker ? maskEndpoint(worker.ip) : 'not configured'}`,
          `- status: ${worker?.status || 'unknown'}`,
          `- reachable: ${worker?.reachable ? 'yes' : 'no'}`,
          `- fleet_online: ${cloud.online || 0}/${cloud.total || 0}`,
          `- offline_count: ${offlineCount}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Operator Intent',
          worker?.reachable
            ? 'Use this worker as evidence context only. Do not launch or mutate worker state from this dashboard brief.'
            : 'Treat this worker as unavailable until a live health check proves otherwise.'
        ].join('\n');
        stagePacketForComms(packet, `${worker?.name || 'Worker'} directory brief staged`, { controlId: 'workers-actions', keepFocus: options.keepFocus });
        return { tone, detail: worker?.name || 'no worker selected' };
      },
      summarize: result => `Worker directory packet staged from local panel state; ${result?.detail || 'worker sampled'}.`
    },
    {
      id: 'repo-actions',
      label: 'Stage Repo Guard',
      source: 'local-panel-action',
      run: (options = {}) => {
        const summary = repoContext.summary || {};
        const repoCollisions = Array.isArray(repoContext.collisions) ? repoContext.collisions : [];
        const guardrails = Array.isArray(repoContext.guardrails) ? repoContext.guardrails : [];
        const severityCounts = summary.collision_severity_counts || {};
        const collisionCount = Number(summary.collision_count || 0);
        const criticalCount = Number(severityCounts.critical || severityCounts.danger || 0);
        const rootsMissing = Number(summary.roots_missing_count || 0);
        const tone = criticalCount > 0 ? 'danger' : collisionCount > 0 || rootsMissing > 0 ? 'warn' : toneForStatus(repoContext.status);
        const packet = [
          '# Repo Guard Brief',
          '',
          `- status: ${repoContext.status || 'unknown'}`,
          `- repo_count: ${summary.repo_count || 0}`,
          `- roots_scanned: ${summary.roots_scanned_count || 0}`,
          `- roots_missing: ${rootsMissing}`,
          `- collisions: ${collisionCount}`,
          `- warnings: ${severityCounts.warning || 0}`,
          `- critical: ${criticalCount}`,
          `- scan_truncated: ${summary.scan_truncated ? 'yes' : 'no'}`,
          `- cache_age_s: ${repoContext.cache_age_s ?? 0}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Selected Guardrail',
          `- ${guardrails[0] || 'No repo guardrail reported.'}`,
          '',
          '## Selected Collision',
          repoCollisions[0]
            ? `- ${repoCollisions[0].type || 'collision'} / ${repoCollisions[0].key || 'key hidden'} / ${repoCollisions[0].severity || 'info'} / ${impactedReposLabel(repoCollisions[0])}`
            : '- No collision selected or reported.',
          '',
          '## Operator Intent',
          rootsMissing > 0
            ? 'Treat this as a partial repo map. Review Codebase and Sync before dispatching or publishing work.'
            : collisionCount > 0
              ? 'Resolve collision evidence before worker dispatch or port reuse.'
              : 'No collisions are reported; keep guardrails attached to any worker or publish packet.'
        ].join('\n');
        stagePacketForComms(packet, 'Repo guard brief staged', { controlId: 'repo-actions', keepFocus: options.keepFocus });
        return { tone, detail: `${collisionCount} collisions / ${rootsMissing} roots missing` };
      },
      summarize: result => `Repo guard packet staged from local panel state; ${result?.detail || 'repo sampled'}.`
    },
    {
      id: 'codebase-actions',
      label: 'Stage Codebase Brief',
      source: 'local-panel-action',
      run: (options = {}) => {
        const summary = codebase.summary || {};
        const integrations = Array.isArray(codebase.integrations) ? codebase.integrations : [];
        const findings = Array.isArray(codebase.findings) ? codebase.findings : [];
        const readyIntegrations = integrations.filter(item => item.ready).length;
        const warnFindings = findings.filter(item => item.tone === 'warn').length;
        const dangerFindings = findings.filter(item => item.tone === 'danger').length;
        const tone = dangerFindings > 0 ? 'danger' : warnFindings > 0 ? 'warn' : toneForStatus(codebase.status);
        const selectedFinding = findings[0];
        const selectedIntegration = integrations[0];
        const packet = [
          '# Codebase Intelligence Brief',
          '',
          `- root: ${codebase.root_name || 'bridge root'}`,
          `- status: ${codebase.status || 'unknown'}`,
          '- active_lens: SUMMARY',
          `- files: ${summary.file_count || 0}`,
          `- routes: ${summary.route_count || 0}`,
          `- modules: ${summary.module_count || 0}`,
          `- tests: ${summary.test_count || 0}`,
          `- frontend_dependencies: ${summary.frontend_dependency_count || 0}`,
          `- integrations_ready: ${readyIntegrations}/${integrations.length}`,
          `- findings: ${findings.length}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Selected Finding',
          selectedFinding
            ? `- ${selectedFinding.title}: ${selectedFinding.detail}`
            : '- No analyzer finding selected.',
          '',
          '## Selected Integration',
          selectedIntegration
            ? `- ${selectedIntegration.label || selectedIntegration.id}: ${selectedIntegration.ready ? 'ready' : 'needs attention'}`
            : '- No integration lane selected.',
          '',
          '## Operator Intent',
          'Use this snapshot to decide whether the repo shape supports the next dashboard or bridge action.'
        ].join('\n');
        stagePacketForComms(packet, 'Codebase intelligence brief staged', { controlId: 'codebase-actions', keepFocus: options.keepFocus });
        return { tone, detail: `${summary.route_count || 0} routes / ${summary.module_count || 0} modules` };
      },
      summarize: result => `Codebase intelligence packet staged from local panel state; ${result?.detail || 'codebase sampled'}.`
    },
    {
      id: 'evidence-actions',
      label: 'Stage Evidence Window',
      source: 'local-panel-action',
      run: (options = {}) => {
        const rows = eventRows || [];
        const warnCount = rows.filter(row => row.level === 'WARN').length;
        const errorCount = rows.filter(row => row.level === 'ERROR').length;
        const issueWindow = buildEvidenceIssueWindow(rows);
        const reviewWindow = buildEvidenceReviewSignature(rows);
        const tone = errorCount > 0 ? 'danger' : warnCount > 0 ? 'warn' : rows.length > 0 ? 'success' : 'warn';
        const packet = [
          '# Evidence Window Brief',
          '',
          `- filter: ${eventFilter}`,
          `- paused: ${streamPaused ? 'yes' : 'no'}`,
          `- total_rows: ${rows.length}`,
          `- visible_rows: ${rows.length}`,
          `- warnings: ${warnCount}`,
          `- errors: ${errorCount}`,
          `- window_basis: ${issueWindow.basis}`,
          `- issue_rows: ${issueWindow.riskCount}`,
          `- evidence_signature: ${reviewWindow.signature || 'none'}`,
          `- review_window_rows: ${reviewWindow.windowSize}`,
          issueWindow.newestIssue ? `- newest_issue: ${issueWindow.newestIssue.level} / ${issueWindow.newestIssue.source} / ${issueWindow.newestIssue.timestamp || '--'}` : '- newest_issue: none',
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Issue Window',
          ...(issueWindow.rows.length
            ? issueWindow.rows.map(row => `- ${row.level} / ${row.source} / ${row.timestamp || '--'} / ${row.message}`)
            : ['- No events visible for this filter.']),
          '',
          '## Operator Intent',
          issueWindow.basis === 'risk'
            ? 'Use this packet as the current warning/error issue window for Jules/model review. Do not infer full bridge health until the related lanes are inspected.'
            : 'Use this packet as a bounded evidence tail for Jules/model review. Do not infer full bridge health from this window alone.'
        ].join('\n');
        stagePacketForComms(packet, issueWindow.basis === 'risk' ? 'Evidence issue window staged' : 'Evidence window staged', {
          controlId: 'evidence-actions',
          keepFocus: options.keepFocus,
          evidenceKind: 'window',
          evidenceSignature: reviewWindow.signature,
          evidenceRiskCount: reviewWindow.riskCount
        });
        return { tone, detail: `${rows.length} rows / ${errorCount} errors / ${warnCount} warnings`, packet, packetTitle: 'Evidence Window Brief' };
      },
      summarize: result => `Evidence window packet staged from local panel state; ${result?.detail || 'evidence sampled'}.`
    },
    {
      id: 'inspector-actions',
      label: 'Stage Runtime Inspector',
      source: 'local-panel-action',
      run: (options = {}) => {
        const packet = [
          '# Runtime Inspector Brief',
          '',
          `- execution_context: ${sysStatus.executionContext}`,
          `- quantower: ${sysStatus.quantAllowed ? 'enabled' : 'locked'}`,
          `- bridge_status: ${sysStatus.bridgeStatus || 'unknown'}`,
          `- stream: ${sysStatus.updateMode || 'unknown'} ${sysStatus.streamSequence || 0}`,
          `- contract: ${sysStatus.contractOk ? `v${sysStatus.contract?.version || 0}` : 'waiting'}`,
          `- host: ${sysStatus.hostname || 'unknown'}`,
          `- selected_worker: ${selectedWorker?.name || 'none'}`,
          `- selected_collision: ${selectedCollision?.type || 'none'}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Operator Intent',
          'Use this to anchor the current local runtime state before asking Jules or the model loop to act.'
        ].join('\n');
        stagePacketForComms(packet, 'Runtime inspector staged', { controlId: 'inspector-actions', keepFocus: options.keepFocus });
        return { tone: sysStatus.online ? 'success' : 'warn', detail: sysStatus.executionContext || 'runtime sampled', packet, packetTitle: 'Runtime Inspector Brief' };
      },
      summarize: result => `Inspector runtime packet staged from local panel state; ${result?.detail || 'runtime sampled'}.`
    },
    {
      id: 'comms-model-probe',
      label: 'Probe Comms Model Loop',
      source: 'public-chat-probe',
      run: async () => {
        const data = await sendCommsMessage({
          message: 'Say JULES_COMMS_PROOF_OK and one short sentence describing the live bridge skill you can perform right now.',
          userLabel: '[selected blocker model-loop proof probe]',
          successTitle: 'Comms response received'
        });
        if (!data) {
          return {
            tone: 'danger',
            detail: 'model probe failed; see the Comms journal for the transport error',
            blockers: ['model_probe_failed'],
            warnings: []
          };
        }
        const errors = Array.isArray(data.errors) ? data.errors : [];
        const degradedReason = commsDegradedReason(data.response, errors);
        const degraded = data.model_used === 'none' || errors.length > 0 || !!degradedReason;
        return {
          tone: degraded ? 'warn' : 'success',
          detail: degraded
            ? `${data.model_used || 'none'} / ${errors[0] || degradedReason || 'degraded'}`
            : `${data.model_used || 'model'} responded in ${data.elapsed_ms || 0}ms`,
          blockers: [],
          warnings: degraded ? [errors[0] || degradedReason || 'model_loop_degraded'] : [],
          modelUsed: data.model_used || 'unknown'
        };
      },
      summarize: result => `Comms model loop ${result?.tone === 'success' ? 'responded' : 'reported degraded'}: ${result?.detail || 'no detail'}.`
    },
    {
      id: 'comms-local-review',
      label: 'Stage Comms Local Review',
      source: 'local-comms-review',
      run: (options = {}) => {
        const syncGate = buildLocalSyncGate(sysStatus.cloudSync || DEFAULT_STATUS.cloudSync);
        const sourcePacket = [
          '# Safe Batch Comms Review Seed',
          '',
          '- source: Proof Runner Safe Batch',
          `- active_focus: ${activeFocus || 'overview'}`,
          `- sync_state: ${sysStatus.cloudSync?.state || 'unknown'}`,
          `- dirty_count: ${syncGate.dirty}`,
          `- blockers: ${syncGate.blockers.length ? syncGate.blockers.join(', ') : 'none'}`,
          `- warnings: ${syncGate.warnings.length ? syncGate.warnings.join(', ') : 'none'}`,
          '- evidence: local dashboard state, command journal, and cloud sync snapshot',
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Review Intent',
          'Use local packet intelligence to identify blockers before any publish, worker dispatch, or chat send.'
        ].join('\n');
        const verdict = buildPacketIntelligence(sourcePacket, 'Safe Batch Comms Review Seed');
        const packet = [
          '# Local Comms Packet Review',
          '',
          '- source_packet: Safe Batch Comms Review Seed',
          `- score: ${verdict.score}`,
          `- tone: ${verdict.tone}`,
          `- recommended_focus: ${verdict.focus}`,
          `- blockers_detected: ${verdict.blockers.length}`,
          `- missing_signals: ${verdict.missingSignals.length ? verdict.missingSignals.join(', ') : 'none'}`,
          '- protected_routes_called: no',
          '- chat_send_called: no',
          '',
          '## Verdict',
          verdict.verdict,
          '',
          '## Next Safe Action',
          verdict.nextAction,
          '',
          '## Local Verdict Packet',
          verdict.verdictPacket,
          '',
          '## Packet Under Review',
          sourcePacket
        ].join('\n');
        stagePacketForComms(packet, 'Local Comms review staged', { controlId: 'comms-actions', keepFocus: options.keepFocus });
        return {
          tone: verdict.tone,
          detail: `${verdict.score}% / ${verdict.focus}`,
          blockers: verdict.blockers,
          warnings: verdict.missingSignals,
          packet,
          packetTitle: 'Local Comms Packet Review'
        };
      },
      summarize: result => `Comms local packet intelligence ${result?.detail || 'ran'} without chat send; blockers ${(result?.blockers || []).length}; warnings ${(result?.warnings || []).length}.`
    },
    {
      id: 'header-strip',
      label: 'Open Stream Header',
      source: 'local-shell-route',
      run: () => {
        openHeaderStatus({
          label: streamLabel,
          focus: 'evidence',
          tone: streamTone,
          topologyId: 'bridge'
        });
        return { tone: streamTone, detail: streamLabel };
      },
      summarize: result => `Header status strip opened ${result?.detail || 'the stream evidence lane'}.`
    }
  ];

  return (
    <div className="dashboard-shell" data-focus={activeFocus} onClick={traceControlClick}>
      <header className="command-bar">
        <div className="brand-lockup">
          <span className={`live-dot ${sysStatus.online ? 'online' : 'offline'}`} />
          <div>
            <strong>Jules Bridge</strong>
            <span>{sysStatus.localUrl || BRIDGE}</span>
          </div>
        </div>
        <div className="command-status">
          <StatusPill
            tone={sysStatus.online ? 'success' : 'danger'}
            onClick={() => openHeaderStatus({ label: sysStatus.online ? 'LIVE' : 'OFFLINE', focus: 'overview', tone: sysStatus.online ? 'success' : 'danger', topologyId: 'bridge', opsId: 'bridge' })}
            title="Open bridge overview"
            controlId="header-strip"
          >
            {sysStatus.online ? 'LIVE' : 'OFFLINE'}
          </StatusPill>
          <StatusPill
            tone={streamTone}
            onClick={() => openHeaderStatus({ label: streamLabel, focus: 'evidence', tone: streamTone, topologyId: 'bridge' })}
            title="Open evidence stream"
            controlId="header-strip"
          >
            {streamLabel}
          </StatusPill>
          <StatusPill
            tone={sysStatus.contractOk ? 'success' : 'danger'}
            onClick={() => openHeaderStatus({ label: sysStatus.contractOk ? `CONTRACT V${sysStatus.contract.version}` : 'CONTRACT WAIT', focus: 'evidence', tone: sysStatus.contractOk ? 'success' : 'danger' })}
            title="Open contract evidence"
            controlId="header-strip"
          >
            {sysStatus.contractOk ? `CONTRACT V${sysStatus.contract.version}` : 'CONTRACT WAIT'}
          </StatusPill>
          <StatusPill
            tone={TOKEN ? 'success' : 'warn'}
            onClick={() => openHeaderStatus({ label: TOKEN ? 'ACTIONS ARMED' : 'PREVIEW MODE', focus: 'tiu', tone: TOKEN ? 'success' : 'warn', opsId: 'alliance' })}
            title="Open TIU workbench"
            controlId="header-strip"
          >
            {TOKEN ? 'ACTIONS ARMED' : 'PREVIEW MODE'}
          </StatusPill>
          <StatusPill
            tone={sysStatus.tunnel ? 'success' : 'warn'}
            onClick={() => openHeaderStatus({ label: sysStatus.tunnel ? 'TUNNEL' : 'LOCAL', focus: 'overview', tone: sysStatus.tunnel ? 'success' : 'warn', topologyId: 'bridge', opsId: 'bridge' })}
            title="Open bridge route"
            controlId="header-strip"
          >
            {sysStatus.tunnel ? 'TUNNEL' : 'LOCAL'}
          </StatusPill>
          <StatusPill
            tone={sysStatus.geminiCli?.ready ? 'success' : sysStatus.geminiCli?.installed ? 'warn' : 'danger'}
            onClick={() => openHeaderStatus({ label: sysStatus.geminiCli?.ready ? 'GEMINI READY' : sysStatus.geminiCli?.installed ? 'GEMINI INSTALLED' : 'GEMINI MISSING', focus: 'alliance', tone: sysStatus.geminiCli?.ready ? 'success' : sysStatus.geminiCli?.installed ? 'warn' : 'danger', topologyId: 'gemini', opsId: 'gemini' })}
            title="Open Gemini alliance lane"
            controlId="header-strip"
          >
            {sysStatus.geminiCli?.ready ? 'GEMINI READY' : sysStatus.geminiCli?.installed ? 'GEMINI INSTALLED' : 'GEMINI MISSING'}
          </StatusPill>
          <StatusPill
            tone={sysStatus.antigravityCli?.ready ? 'success' : sysStatus.antigravityCli?.installed ? 'warn' : 'danger'}
            onClick={() => openHeaderStatus({ label: sysStatus.antigravityCli?.ready ? 'AGY READY' : sysStatus.antigravityCli?.installed ? 'AGY INSTALLED' : 'AGY MISSING', focus: 'alliance', tone: sysStatus.antigravityCli?.ready ? 'success' : sysStatus.antigravityCli?.installed ? 'warn' : 'danger', topologyId: 'antigravity', opsId: 'antigravity' })}
            title="Open Antigravity alliance lane"
            controlId="header-strip"
          >
            {sysStatus.antigravityCli?.ready ? 'AGY READY' : sysStatus.antigravityCli?.installed ? 'AGY INSTALLED' : 'AGY MISSING'}
          </StatusPill>
          <StatusPill
            tone={allianceTone(sysStatus.alliance)}
            onClick={() => openHeaderStatus({ label: sysStatus.alliance?.ready_to_execute_alliance ? 'ALLIANCE READY' : 'ALLIANCE WATCH', focus: 'alliance', tone: allianceTone(sysStatus.alliance), topologyId: 'alliance', opsId: 'alliance' })}
            title="Open alliance control"
            controlId="header-strip"
          >
            {sysStatus.alliance?.ready_to_execute_alliance ? 'ALLIANCE READY' : 'ALLIANCE WATCH'}
          </StatusPill>
          <StatusPill
            tone={cloudSyncTone(sysStatus.cloudSync)}
            onClick={() => openHeaderStatus({ label: cloudSyncLabel(sysStatus.cloudSync), focus: 'sync', tone: cloudSyncTone(sysStatus.cloudSync), topologyId: 'sync', opsId: 'cloud-sync' })}
            title="Open cloud sync"
            controlId="header-strip"
          >
            {cloudSyncLabel(sysStatus.cloudSync)}
          </StatusPill>
          <StatusPill
            tone={gateTone(sysStatus)}
            onClick={() => openHeaderStatus({ label: sysStatus.executionContext, focus: 'overview', tone: gateTone(sysStatus), topologyId: 'runtime', opsId: 'context' })}
            title="Open runtime gate"
            controlId="header-strip"
          >
            {sysStatus.executionContext}
          </StatusPill>
          <StatusPill
            tone={sysStatus.quantAllowed ? 'success' : 'warn'}
            onClick={() => openHeaderStatus({ label: sysStatus.quantAllowed ? 'QUANT ON' : 'QUANT LOCKED', focus: 'overview', tone: sysStatus.quantAllowed ? 'success' : 'warn', topologyId: 'runtime', opsId: 'context' })}
            title="Open Quantower gate"
            controlId="header-strip"
          >
            {sysStatus.quantAllowed ? 'QUANT ON' : 'QUANT LOCKED'}
          </StatusPill>
        </div>
        <ActionReceiptDock
          latestCommand={commandJournal[0]}
          commandJournal={commandJournal}
          activeFocus={activeFocus}
          lastClickTrace={lastClickTrace}
          sync={sysStatus.cloudSync || DEFAULT_STATUS.cloudSync}
          eventRows={eventRows}
          blockers={liveBlockerQueue}
          selectedBlockerId={selectedLiveBlockerId}
          blockerRun={liveBlockerRun}
          onOpenFocus={focus => changeFocus(focus, { controlId: 'action-receipt' })}
          onOpenBlocker={openLiveBlocker}
          onRunBlocker={runLiveBlocker}
          onStageBlocker={stageLiveBlocker}
        />
      </header>

      <NavRail activeFocus={activeFocus} onFocusChange={changeFocus} />

      <main className="operations-grid">
        <MissionSummary
          sysStatus={sysStatus}
          topology={topology}
          selectedNode={selectedTopology}
          activeFocus={activeFocus}
          onNodeSelect={selectTopology}
          onOpenNode={openTopology}
          onStageNode={stageTopologyBrief}
        />
        <IntelligencePanel
          sysStatus={sysStatus}
          activeFocus={activeFocus}
          selectedWorker={selectedWorker}
          selectedCollision={selectedCollision}
          eventRows={eventRows}
          commandJournal={commandJournal}
          safeShellActions={safeShellActions}
          onStagePacket={stagePacketForComms}
          onCommandEvent={pushCommand}
          onFocusChange={changeFocus}
          onRefreshStatus={refreshDashboardStatus}
        />
        <TiuWorkbench
          sysStatus={sysStatus}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onCommandEvent={pushCommand}
        />
        <AllianceControl
          sysStatus={sysStatus}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <CloudSyncPanel
          cloudSync={sysStatus.cloudSync || DEFAULT_STATUS.cloudSync}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onCommandEvent={pushCommand}
        />
        <TelemetryPanel
          sysStatus={sysStatus}
          cpuHistory={cpuHistory}
          memHistory={memHistory}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <OpsChecklist
          items={opsItems}
          activeFocus={activeFocus}
          selectedItem={selectedOpsItem}
          onItemSelect={selectOpsItem}
          onOpenItem={openOpsItem}
          onStageItem={stageOpsBrief}
          onPlanItem={planOpsStep}
        />
        <FleetPanel
          fleet={sysStatus.fleet || DEFAULT_STATUS.fleet}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <WorkerDirectory
          workers={workers}
          cloud={cloud}
          selectedWorkerKey={selectedWorkerKey}
          setSelectedWorkerKey={selectWorker}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <RepoGuard
          repoContext={repoContext}
          selectedCollisionKey={selectedCollisionKey}
          setSelectedCollisionKey={selectCollision}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <CodebaseIntelligence
          codebase={codebase}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <EventConsole
          rows={eventRows}
          filter={eventFilter}
          setFilter={changeEventFilter}
          paused={streamPaused}
          togglePaused={togglePaused}
          activeFocus={activeFocus}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
      </main>

      <aside className="side-column">
        <Inspector
          sysStatus={sysStatus}
          worker={selectedWorker}
          collision={selectedCollision}
          onStagePacket={stagePacketForComms}
          onFocusChange={changeFocus}
          onCommandEvent={pushCommand}
        />
        <CommPanel
          chatHistory={chatHistory}
          chatBoxRef={chatBoxRef}
          isThinking={isThinking}
          model={model}
          setModel={setModel}
          stagedPacket={stagedPacket}
          setStagedPacket={setStagedPacket}
          commandJournal={commandJournal}
          activeFocus={activeFocus}
          pendingImage={pendingImage}
          setPendingImage={setPendingImage}
          inputValue={inputValue}
          setInputValue={setInputValue}
          sendChat={sendChat}
          probeModelLoop={probeModelLoop}
          onKey={onKey}
          onCommandEvent={pushCommand}
        />
      </aside>
    </div>
  );
}

export default App;
