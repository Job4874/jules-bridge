import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  buildEvidenceIssueWindow,
  buildEvidenceReviewSignature,
  buildEventRows,
  buildBridgeProbeCommsReceipt,
  buildLiveBlockerQueue,
  buildLocalSyncGate,
  cloudSyncLabel,
  cloudSyncTone,
  ensureUniqueCommandIds,
  isLocalPacketIntelligenceCommand,
  isSuccessfulControlProofCommand,
  mergeCommandJournalRows,
  normalizeCodebaseAnalysis,
  normalizeCollaborationProof,
  normalizeRepoContext,
  normalizeVmRelayStatus,
  offlineDashboardStatusSnapshot,
  PROOF_JOURNAL_MAX_COMMANDS,
  restorePersistentCommandJournal,
  serializePersistentCommandJournal,
  summarizeCloudSyncGate,
  summarizeControlAudit
} from './dashboardModel.js';

const cleanGithubSync = {
  status: 'ready',
  state: 'synced',
  branch: 'master',
  upstream: 'origin/master',
  remote_host: 'github.com',
  ahead: 0,
  behind: 0,
  dirty_count: 0,
  github_authenticated: true,
  publish_ready: false,
  synced: true,
  blockers: [],
  warnings: []
};

test('codebase analysis normalizer accepts raw analyzer route responses', () => {
  const normalized = normalizeCodebaseAnalysis({
    status: 'ready',
    root: { name: 'jules-bridge' },
    generated_at_utc: '2026-07-06T20:20:00Z',
    summary: { route_count: 83, module_count: 31, test_count: 47 },
    integrations: [{ id: 'codebase_analyzer', ready: true }],
    findings: [{ title: 'Route map', tone: 'success' }]
  });

  assert.equal(normalized.root_name, 'jules-bridge');
  assert.equal(normalized.summary.route_count, 83);
  assert.equal(normalized.summary.file_count, 0);
  assert.equal(normalized.integrations.length, 1);
  assert.equal(normalized.findings[0].title, 'Route map');
});

test('repo context normalizer accepts raw context guard route responses', () => {
  const normalized = normalizeRepoContext({
    status: 'ready',
    generated_at_utc: '2026-07-06T20:30:00Z',
    summary: {
      repo_count: 3,
      collision_count: 1,
      roots_scanned_count: 2,
      roots_missing_count: 0,
      collision_severity_counts: { warning: 1 }
    },
    collisions: [{ type: 'port_collision', key: '5000', severity: 'warning' }],
    guardrails: ['Label work by repo path_ref.']
  });

  assert.equal(normalized.status, 'ready');
  assert.equal(normalized.summary.repo_count, 3);
  assert.equal(normalized.summary.scan_truncated, false);
  assert.equal(normalized.summary.collision_severity_counts.warning, 1);
  assert.equal(normalized.collisions[0].key, '5000');
  assert.equal(normalized.guardrails.length, 1);
});

test('VM relay status normalizer accepts live route responses and safe fallbacks', () => {
  const live = normalizeVmRelayStatus({
    online: true,
    uptime_s: '77',
    tasks_completed: '4',
    tasks_running: 1,
    recent: [{ task: 'chat', status: 'done' }],
    browser_model_loop: true,
    sampled_at_utc: '2026-07-06T20:45:00Z'
  });
  const failed = normalizeVmRelayStatus({ online: false, recent: 'not-array' });

  assert.equal(live.online, true);
  assert.equal(live.uptime_s, 77);
  assert.equal(live.tasks_completed, 4);
  assert.equal(live.tasks_running, 1);
  assert.equal(live.browser_model_loop, true);
  assert.equal(live.recent.length, 1);
  assert.equal(live.sampled_at_utc, '2026-07-06T20:45:00Z');
  assert.equal(failed.online, false);
  assert.deepEqual(failed.recent, []);
});

test('collaboration proof normalizer counts required gates blockers and caveats', () => {
  const normalized = normalizeCollaborationProof({
    status: 'blocked',
    gates: [
      { name: 'jules_reachability', status: 'pass', required: true },
      { name: 'legacy_gemini_model', status: 'blocked', required: false },
      { name: 'local_tests', status: 'pass' },
      { name: 'completion', status: 'blocked', required: true }
    ],
    blockers: [{ gate: 'completion', blocker: 'safe_to_mark_goal_complete_false' }],
    legacy_caveats: [{ gate: 'legacy_gemini_model', blocker: 'auth_required' }],
    agents: { jules: { reachable: true, skill_count: 5 } }
  });

  assert.equal(normalized.gate_count, 4);
  assert.equal(normalized.pass_count, 2);
  assert.equal(normalized.required_gate_count, 3);
  assert.equal(normalized.required_pass_count, 2);
  assert.equal(normalized.blocker_count, 1);
  assert.equal(normalized.caveat_count, 1);
  assert.equal(normalized.agents.jules.skill_count, 5);
});

const extractFunctionCalls = (source, name) => {
  const calls = [];
  for (let start = 0; (start = source.indexOf(`${name}(`, start)) >= 0; start += 1) {
    let cursor = start + name.length + 1;
    let depth = 1;
    let quote = null;
    let escaping = false;
    for (; cursor < source.length; cursor += 1) {
      const char = source[cursor];
      if (quote) {
        if (escaping) {
          escaping = false;
        } else if (char === '\\') {
          escaping = true;
        } else if (char === quote) {
          quote = null;
        }
      } else if (char === "'" || char === '"' || char === '`') {
        quote = char;
      } else if (char === '(') {
        depth += 1;
      } else if (char === ')') {
        depth -= 1;
        if (depth === 0) {
          cursor += 1;
          break;
        }
      }
    }
    calls.push({
      line: source.slice(0, start).split(/\r?\n/).length,
      text: source.slice(start, cursor)
    });
  }
  return calls;
};

const receiptMetadataMissing = call => !/controlId|controlIds|meta|commandMeta/.test(call.text);

test('warning-bearing sync snapshots do not render as clean', () => {
  const staleTracking = {
    ...cleanGithubSync,
    warnings: ['remote_tracking_stale']
  };

  const gate = buildLocalSyncGate(staleTracking);

  assert.equal(gate.synced, false);
  assert.equal(gate.publishReady, false);
  assert.equal(gate.status, 'ready_with_warnings');
  assert.equal(gate.state, 'preview_warning');
  assert.equal(cloudSyncTone(staleTracking), 'warn');
  assert.equal(cloudSyncLabel(staleTracking), 'Needs review');
});

test('count-only snapshots are not inferred as synced without backend proof', () => {
  const compactUnknown = {
    ...cleanGithubSync,
    status: 'unknown',
    state: 'unknown',
    synced: false
  };

  const gate = buildLocalSyncGate(compactUnknown);

  assert.equal(gate.synced, false);
  assert.equal(gate.publishReady, false);
  assert.equal(gate.state, 'preview_waiting');
  assert.equal(cloudSyncTone(compactUnknown), 'info');
  assert.equal(cloudSyncLabel(compactUnknown), 'unknown');
});

test('explicit clean sync without warnings still renders as synced', () => {
  const gate = buildLocalSyncGate(cleanGithubSync);

  assert.equal(gate.synced, true);
  assert.equal(gate.status, 'ready');
  assert.equal(gate.state, 'preview_clean');
  assert.equal(cloudSyncTone(cleanGithubSync), 'success');
  assert.equal(cloudSyncLabel(cleanGithubSync), 'Synced');
});

test('cloud sync diagnosis explains dirty worktree shape and safe next action', () => {
  const diagnosis = summarizeCloudSyncGate({
    ...cleanGithubSync,
    status: 'blocked',
    state: 'blocked',
    dirty_count: 22,
    staged_count: 1,
    unstaged_count: 15,
    untracked_count: 6,
    synced: false,
    blockers: ['dirty_worktree']
  });

  assert.equal(diagnosis.tone, 'danger');
  assert.equal(diagnosis.headline, '22 dirty files block publish');
  assert.ok(diagnosis.detail.includes('22 dirty (1 staged / 15 unstaged / 6 untracked)'));
  assert.ok(diagnosis.detail.includes('0 ahead / 0 behind'));
  assert.ok(diagnosis.detail.includes('GitHub authenticated'));
  assert.ok(diagnosis.action.includes('Build the publish review packet'));
  assert.ok(diagnosis.action.includes('stage and commit only reviewed files'));
  assert.ok(diagnosis.packetLines.includes('worktree: 22 dirty (1 staged / 15 unstaged / 6 untracked)'));
});

test('cloud sync diagnosis keeps clean synced state distinct from publish work', () => {
  const diagnosis = summarizeCloudSyncGate(cleanGithubSync);

  assert.equal(diagnosis.tone, 'success');
  assert.equal(diagnosis.headline, 'Cloud sync is clean');
  assert.ok(diagnosis.detail.includes('clean worktree'));
  assert.equal(diagnosis.gate.synced, true);
  assert.ok(diagnosis.action.includes('Use Sync as supporting readiness evidence'));
});

test('bridge probe model-loop row writes a successful Comms receipt only when clean', () => {
  const receipt = buildBridgeProbeCommsReceipt({
    id: 'chat-test',
    path: '/chat/test',
    state: 'pass',
    tone: 'success',
    detail: 'healthy / openrouter:ok 233ms',
    latencyMs: 244
  });

  assert.equal(receipt.title, 'Comms response received');
  assert.equal(receipt.tone, 'success');
  assert.equal(receipt.controlId, 'comms-actions');
  assert.deepEqual(receipt.controlIds, ['bridge-probe', 'comms-actions']);
  assert.ok(receipt.detail.includes('/chat/test'));
  assert.ok(receipt.detail.includes('healthy'));
});

test('bridge probe model-loop row writes honest degraded or failed Comms receipts', () => {
  const degraded = buildBridgeProbeCommsReceipt({
    id: 'chat-test',
    path: '/chat/test',
    state: 'review',
    tone: 'warn',
    detail: 'degraded / no providers ready',
    latencyMs: 510
  });
  const failed = buildBridgeProbeCommsReceipt({
    id: 'chat-test',
    path: '/chat/test',
    state: 'fail',
    tone: 'danger',
    detail: 'HTTP 503',
    latencyMs: 6000
  });

  assert.equal(degraded.title, 'Comms degraded');
  assert.equal(degraded.tone, 'warn');
  assert.equal(failed.title, 'Comms failed');
  assert.equal(failed.tone, 'danger');
  assert.equal(buildBridgeProbeCommsReceipt({ id: 'health', tone: 'success' }), null);
});

test('persistent command journal stores only current contract proof rows', () => {
  const controlIds = ['nav-rail', 'break-test-lab'];
  const payload = serializePersistentCommandJournal([
    { id: 'boot', title: 'Dashboard booted', detail: 'no proof', tone: 'info' },
    { id: 'one', time: '2026-07-06T08:00:00.000Z', title: 'Focus changed', detail: 'sync', tone: 'success', controlId: 'nav-rail' },
    { id: 'two', time: '2026-07-06T08:00:01.000Z', title: 'Unknown control', detail: 'ignored', tone: 'success', controlId: 'missing-control' },
    { id: 'three', time: '2026-07-06T08:00:02.000Z', title: 'Break test run', detail: '51%', tone: 'danger', controlIds: ['break-test-lab', 'missing-control'] }
  ], controlIds, { now: '2026-07-06T08:01:00.000Z' });

  assert.equal(payload.commands.length, 2);
  assert.deepEqual(payload.commands.map(row => row.controlId), ['nav-rail', 'break-test-lab']);
  assert.deepEqual(payload.commands[1].controlIds, ['break-test-lab']);
});

test('persistent command journal restores within age and contract bounds', () => {
  const controlIds = ['nav-rail', 'break-test-lab'];
  const payload = serializePersistentCommandJournal([
    { id: 'one', time: '2026-07-06T08:00:00.000Z', title: 'Focus changed', detail: 'sync', tone: 'success', controlId: 'nav-rail' },
    { id: 'two', time: '2026-07-06T08:00:01.000Z', title: 'Break test run', detail: '51%', tone: 'danger', controlId: 'break-test-lab' }
  ], controlIds, { now: '2026-07-06T08:01:00.000Z' });

  const restored = restorePersistentCommandJournal(JSON.stringify(payload), controlIds, {
    now: '2026-07-06T09:00:00.000Z'
  });
  const mismatched = restorePersistentCommandJournal(JSON.stringify(payload), ['nav-rail'], {
    now: '2026-07-06T09:00:00.000Z'
  });
  const stale = restorePersistentCommandJournal(JSON.stringify(payload), controlIds, {
    now: '2026-07-07T09:00:00.000Z'
  });

  assert.equal(restored.length, 2);
  assert.equal(mismatched.length, 0);
  assert.equal(stale.length, 0);
});

test('persistent command journal expires proof rows by their own event time', () => {
  const controlIds = ['comms-actions'];
  const payload = serializePersistentCommandJournal([
    {
      id: 'old-model-proof',
      time: '2026-07-01T08:00:00.000Z',
      title: 'Comms response received',
      detail: 'old model proof',
      tone: 'success',
      controlId: 'comms-actions'
    }
  ], controlIds, {
    now: '2026-07-06T08:01:00.000Z'
  });

  assert.equal(payload.commands.length, 0);
});

test('persistent command journal cannot refresh stale proof by resaving the envelope', () => {
  const controlIds = ['comms-actions'];
  const freshOnOriginalDay = serializePersistentCommandJournal([
    {
      id: 'model-proof',
      time: '2026-07-01T08:00:00.000Z',
      title: 'Comms response received',
      detail: 'vm/jules-worker - 100ms',
      tone: 'success',
      controlId: 'comms-actions'
    }
  ], controlIds, {
    now: '2026-07-01T08:01:00.000Z'
  });
  const restoredSameDay = restorePersistentCommandJournal(JSON.stringify(freshOnOriginalDay), controlIds, {
    now: '2026-07-01T09:00:00.000Z'
  });
  const resavedDaysLater = serializePersistentCommandJournal(restoredSameDay, controlIds, {
    now: '2026-07-06T08:00:00.000Z'
  });
  const restoredDaysLater = restorePersistentCommandJournal(JSON.stringify(resavedDaysLater), controlIds, {
    now: '2026-07-06T09:00:00.000Z'
  });

  assert.equal(restoredSameDay.length, 1);
  assert.equal(resavedDaysLater.commands.length, 0);
  assert.equal(restoredDaysLater.length, 0);
});

test('persistent command journal keeps proof rows beyond the old dense-session cap', () => {
  const controlIds = Array.from({ length: 45 }, (_, index) => `control-${index}`);
  const commands = controlIds.map((controlId, index) => ({
    id: `cmd-${index}`,
    time: `2026-07-06T08:${String(index).padStart(2, '0')}:00.000Z`,
    title: `Proof ${index}`,
    detail: controlId,
    tone: 'success',
    controlId
  }));

  const payload = serializePersistentCommandJournal(commands, controlIds, {
    now: '2026-07-06T09:00:00.000Z'
  });
  const restored = restorePersistentCommandJournal(JSON.stringify(payload), controlIds, {
    now: '2026-07-06T09:30:00.000Z'
  });

  assert.equal(payload.commands.length, 45);
  assert.equal(restored.length, 45);
  assert.ok(PROOF_JOURNAL_MAX_COMMANDS > 40);
  assert.equal(new Set(restored.map(row => row.controlId)).size, 45);
});

test('evidence review signatures are stable until the event window changes', () => {
  const rows = [
    { timestamp: '[2026-07-06 01:00:00,000]', level: 'INFO', source: 'bridge', message: 'online' },
    { timestamp: '[2026-07-06 01:01:00,000]', level: 'WARN', source: 'sync', message: 'dirty_worktree' },
    { timestamp: '[2026-07-06 01:02:00,000]', level: 'ERROR', source: 'chat', message: 'No LLM available' }
  ];

  const first = buildEvidenceReviewSignature(rows);
  const same = buildEvidenceReviewSignature([...rows]);
  const changed = buildEvidenceReviewSignature([
    ...rows,
    { timestamp: '[2026-07-06 01:03:00,000]', level: 'OK', source: 'bridge', message: 'heartbeat' }
  ]);

  assert.equal(first.signature, same.signature);
  assert.notEqual(first.signature, changed.signature);
  assert.equal(first.warningCount, 1);
  assert.equal(first.errorCount, 1);
  assert.equal(first.riskCount, 2);
});

test('evidence issue window prefers warning and error rows over newer info rows', () => {
  const rows = [
    { timestamp: '2026-07-06T01:00:00Z', level: 'INFO', source: 'bridge', message: 'online' },
    { timestamp: '2026-07-06T01:01:00Z', level: 'WARN', source: 'sync', message: 'dirty_worktree' },
    { timestamp: '2026-07-06T01:02:00Z', level: 'INFO', source: 'bridge', message: 'poll ok' },
    { timestamp: '2026-07-06T01:03:00Z', level: 'ERROR', source: 'chat', message: 'No LLM available' },
    { timestamp: '2026-07-06T01:04:00Z', level: 'INFO', source: 'bridge', message: 'status ok' }
  ];

  const window = buildEvidenceIssueWindow(rows);

  assert.equal(window.basis, 'risk');
  assert.equal(window.windowSize, 2);
  assert.deepEqual(window.rows.map(row => row.level), ['WARN', 'ERROR']);
  assert.equal(window.newestIssue.message, 'No LLM available');
  assert.equal(window.label, '2 risk rows / 1 errors / 1 warnings');
});

test('evidence issue window falls back to recent rows when there are no risks', () => {
  const rows = [
    { timestamp: '2026-07-06T01:00:00Z', level: 'INFO', source: 'bridge', message: 'online' },
    { timestamp: '2026-07-06T01:01:00Z', level: 'OK', source: 'bridge', message: 'healthy' },
    { timestamp: '2026-07-06T01:02:00Z', level: 'INFO', source: 'bridge', message: 'poll ok' }
  ];

  const window = buildEvidenceIssueWindow(rows, { maxRows: 2 });

  assert.equal(window.basis, 'recent');
  assert.equal(window.windowSize, 2);
  assert.deepEqual(window.rows.map(row => row.message), ['healthy', 'poll ok']);
  assert.equal(window.newestIssue, null);
  assert.equal(window.label, '2 recent rows / 0 errors / 0 warnings');
});

test('live blocker queue ranks sync evidence and comms blockers into operator actions', () => {
  const queue = buildLiveBlockerQueue({
    sync: {
      ...cleanGithubSync,
      status: 'blocked',
      state: 'blocked',
      dirty_count: 3,
      staged_count: 1,
      unstaged_count: 1,
      untracked_count: 1,
      synced: false,
      blockers: ['dirty_worktree']
    },
    eventRows: [
      { timestamp: '2026-07-06T01:00:00Z', level: 'WARN', source: 'sync', message: 'dirty worktree' },
      { timestamp: '2026-07-06T01:01:00Z', level: 'ERROR', source: 'chat', message: 'No LLM available' }
    ],
    commandJournal: [
      { title: 'Comms degraded', detail: 'model loop unavailable', tone: 'warn', controlId: 'comms-actions' }
    ]
  });

  assert.deepEqual(queue.map(row => row.id), [
    'sync-gate',
    'evidence-health',
    'comms-loop',
    'local-packet-intelligence'
  ]);
  assert.deepEqual(queue.map(row => row.focus), ['sync', 'evidence', 'comms', 'comms']);
  assert.equal(queue[0].tone, 'danger');
  assert.equal(queue[0].action, 'Open Sync and build or stage the publish review packet.');
  assert.match(queue[0].exitCriteria, /publish packet/i);
  assert.match(queue[1].exitCriteria, /issue window/i);
  assert.match(queue[2].exitCriteria, /Probe Model/i);
  assert.equal(queue[2].safeActionId, 'comms-model-probe');
  assert.ok(queue[2].detail.includes('Comms degraded'));
  assert.equal(queue[3].controlId, 'comms-actions');
  assert.equal(queue[3].safeActionId, 'comms-local-review');
  assert.match(queue[3].exitCriteria, /local packet intelligence/i);
});

test('live blocker queue promotes tunnel failures to the bridge probe action', () => {
  const queue = buildLiveBlockerQueue({
    sync: cleanGithubSync,
    eventRows: [
      { timestamp: '2026-07-06T01:00:00Z', level: 'INFO', source: 'bridge', message: 'status ok' },
      { timestamp: '2026-07-06T01:01:00Z', level: 'ERROR', source: 'jules_bridge_start', message: 'FATAL: Tunnel cannot self-heal' }
    ],
    commandJournal: [
      { title: 'Local Comms review staged', detail: '88% / sync', tone: 'warn', controlId: 'comms-actions' },
      { title: 'Comms response received', detail: 'vm/jules-worker - 100ms', tone: 'success', controlId: 'comms-actions' }
    ]
  });

  assert.deepEqual(queue.map(row => row.id), ['evidence-health', 'tunnel-health']);
  assert.equal(queue[1].label, 'Tunnel Health');
  assert.equal(queue[1].tone, 'danger');
  assert.equal(queue[1].focus, 'overview');
  assert.equal(queue[1].controlId, 'bridge-probe');
  assert.match(queue[1].action, /Live Bridge Probe/i);
  assert.match(queue[1].exitCriteria, /local-only mode/i);
});

test('live blocker queue exposes local packet intelligence when model proof is clean', () => {
  const queue = buildLiveBlockerQueue({
    sync: cleanGithubSync,
    eventRows: [
      { timestamp: '2026-07-06T01:00:00Z', level: 'INFO', source: 'bridge', message: 'online' },
      { timestamp: '2026-07-06T01:01:00Z', level: 'OK', source: 'bridge', message: 'healthy' }
    ],
    commandJournal: [
      { title: 'Comms response received', detail: 'vm/jules-worker - 100ms', tone: 'success', controlId: 'comms-actions' }
    ]
  });

  assert.deepEqual(queue.map(row => row.id), ['local-packet-intelligence']);
  assert.equal(queue[0].focus, 'comms');
  assert.equal(queue[0].controlId, 'comms-actions');
  assert.equal(queue[0].safeActionId, 'comms-local-review');
  assert.match(queue[0].action, /Local Review/i);
});

test('live blocker queue is empty for clean sync evidence comms and local packet proof', () => {
  const queue = buildLiveBlockerQueue({
    sync: cleanGithubSync,
    eventRows: [
      { timestamp: '2026-07-06T01:00:00Z', level: 'INFO', source: 'bridge', message: 'online' },
      { timestamp: '2026-07-06T01:01:00Z', level: 'OK', source: 'bridge', message: 'healthy' }
    ],
    commandJournal: [
      { title: 'Local Comms review staged', detail: '88% / sync', tone: 'warn', controlId: 'comms-actions' },
      { title: 'Comms response received', detail: 'vm/jules-worker - 100ms', tone: 'success', controlId: 'comms-actions' }
    ]
  });

  assert.equal(queue.length, 0);
});

test('fatal log rows classify as evidence errors', () => {
  const [row] = buildEventRows(['[2026-07-06 01:01:00,000] [JULES_BRIDGE_START]: FATAL: Tunnel cannot self-heal']);

  assert.equal(row.level, 'ERROR');
  assert.equal(row.source, 'JULES_BRIDGE_START');
  assert.match(row.message, /FATAL/);
});

test('persistent command journal preserves evidence review metadata for current controls', () => {
  const controlIds = ['evidence-actions'];
  const review = buildEvidenceReviewSignature([
    { timestamp: '[2026-07-06 01:02:00,000]', level: 'ERROR', source: 'chat', message: 'No LLM available' }
  ]);
  const payload = serializePersistentCommandJournal([
    {
      id: 'evidence',
      time: '2026-07-06T08:00:00.000Z',
      title: 'Evidence window staged',
      detail: '1 rows / 1 errors / 0 warnings',
      tone: 'success',
      controlId: 'evidence-actions',
      evidenceKind: 'window',
      evidenceSignature: review.signature,
      evidenceRiskCount: review.riskCount
    }
  ], controlIds, { now: '2026-07-06T08:01:00.000Z' });

  const restored = restorePersistentCommandJournal(JSON.stringify(payload), controlIds, {
    now: '2026-07-06T09:00:00.000Z'
  });

  assert.equal(restored.length, 1);
  assert.equal(restored[0].evidenceKind, 'window');
  assert.equal(restored[0].evidenceSignature, review.signature);
  assert.equal(restored[0].evidenceRiskCount, 1);
});

test('local packet intelligence proof stays separate from model-loop proof', () => {
  const localProofRows = [
    { title: 'Local packet intelligence', detail: '88% / comms', controlId: 'comms-actions' },
    { title: 'Packet intelligence prompt prepared', detail: 'verify packet', controlId: 'comms-actions' },
    { title: 'Local Comms review staged', detail: 'review packet', controlId: 'comms-actions' },
    { title: 'Stage Sync Local Preview packet intelligence staged', detail: 'safe step', controlId: 'break-test-lab' }
  ];
  const modelLoopRows = [
    { title: 'Comms response received', detail: 'vm/jules-worker - 4406ms', controlId: 'comms-actions' },
    { title: 'Comms degraded', detail: 'model loop unavailable', controlId: 'comms-actions' },
    { title: 'Comms failed', detail: 'offline fallback', controlId: 'comms-actions' }
  ];

  assert.deepEqual(localProofRows.map(isLocalPacketIntelligenceCommand), [true, true, true, true]);
  assert.deepEqual(modelLoopRows.map(isLocalPacketIntelligenceCommand), [false, false, false]);
});

test('control proof only accepts successful control events', () => {
  const rows = [
    { title: 'Comms response received', detail: 'vm/jules-worker - 4406ms', tone: 'success', controlId: 'comms-actions' },
    { title: 'Comms degraded', detail: 'model loop unavailable', tone: 'warn', controlId: 'comms-actions' },
    { title: 'Comms failed', detail: 'offline fallback', tone: 'danger', controlId: 'comms-actions' },
    { title: 'Publish packet built', detail: 'preview_blocked', tone: 'warn', controlId: 'sync-packet' },
    { title: 'Dashboard booted', detail: 'no control id', tone: 'success' }
  ];

  assert.deepEqual(rows.map(isSuccessfulControlProofCommand), [true, false, false, false, false]);
});

test('command journal ids are made unique for restored or burst events', () => {
  const rows = ensureUniqueCommandIds([
    { id: 'duplicate', title: 'First', controlId: 'nav-rail' },
    { id: 'duplicate', title: 'Second', controlId: 'nav-rail' },
    { title: 'Missing id', time: '2026-07-06T08:00:00.000Z', controlId: 'sync-packet' },
    { title: 'Missing id', time: '2026-07-06T08:00:00.000Z', controlId: 'sync-packet' }
  ]);

  assert.equal(rows.length, 4);
  assert.equal(new Set(rows.map(row => row.id)).size, 4);
  assert.equal(rows[0].id, 'duplicate');
  assert.notEqual(rows[1].id, 'duplicate');
});

test('new command receipts preserve restored proof rows during journal merge', () => {
  const restoredProofs = [
    { id: 'restored-nav', time: '2026-07-06T08:00:00.000Z', title: 'Focus changed', detail: 'sync', tone: 'success', controlId: 'nav-rail' },
    { id: 'restored-break', time: '2026-07-06T08:00:01.000Z', title: 'Break test run', detail: '70%', tone: 'success', controlId: 'break-test-lab' }
  ];
  const currentRows = [
    { id: 'boot', title: 'Proof ledger restored', detail: '2/29 persistent control proofs loaded', tone: 'success' }
  ];
  const merged = mergeCommandJournalRows([
    { id: 'new-receipt', time: '2026-07-06T09:00:00.000Z', title: 'Focus changed', detail: 'evidence', tone: 'info', controlId: 'action-receipt' }
  ], currentRows, restoredProofs);

  assert.deepEqual(merged.map(row => row.id), ['new-receipt', 'boot', 'restored-nav', 'restored-break']);
  assert.equal(new Set(merged.map(row => row.id)).size, 4);
  assert.deepEqual(merged.filter(row => row.tone === 'success' && row.controlId).map(row => row.controlId), ['nav-rail', 'break-test-lab']);
});

test('control audit summary separates proven controls from runtime risks', () => {
  const summary = summarizeControlAudit({
    controlCount: 29,
    provenCount: 29,
    unprovenCount: 0,
    riskCount: 2,
    riskRows: [
      { id: 'system-sync', label: 'Sync gate', tone: 'danger' },
      { id: 'system-evidence', label: 'Evidence tail', tone: 'warn' }
    ],
    score: 94
  });

  assert.equal(summary.controlCoveragePercent, 100);
  assert.equal(summary.controlRiskCount, 0);
  assert.equal(summary.nonControlRiskCount, 2);
  assert.equal(summary.headline, 'Controls proven; 2 system/runtime risks remain');
  assert.ok(summary.summary.includes('29/29 controls proven'));
  assert.ok(summary.summary.includes('button proof is clear'));
});

test('control audit summary keeps unproven controls distinct from other risks', () => {
  const summary = summarizeControlAudit({
    controlCount: 29,
    provenCount: 24,
    unprovenCount: 5,
    riskCount: 6,
    riskRows: [
      { id: 'control-comms-actions', controlId: 'comms-actions', provable: true },
      { id: 'system-sync', label: 'Sync gate', tone: 'danger' }
    ],
    score: 88
  });

  assert.equal(summary.controlCoveragePercent, 83);
  assert.equal(summary.controlRiskCount, 1);
  assert.equal(summary.nonControlRiskCount, 5);
  assert.equal(summary.headline, '5 controls still need proof');
  assert.ok(summary.summary.includes('1 control risk'));
  assert.ok(summary.summary.includes('5 system/runtime risks'));
});

test('dashboard command and packet receipt writers keep control metadata', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');
  const missing = [
    ...extractFunctionCalls(source, 'onCommandEvent').filter(receiptMetadataMissing),
    ...extractFunctionCalls(source, 'pushCommand').filter(receiptMetadataMissing),
    ...extractFunctionCalls(source, 'onStagePacket').filter(receiptMetadataMissing),
    ...extractFunctionCalls(source, 'stagePacketForComms').filter(receiptMetadataMissing)
  ];

  assert.deepEqual(
    missing.map(call => `${call.line}: ${call.text.replace(/\s+/g, ' ').slice(0, 140)}`),
    []
  );
});

test('action receipt dock exposes a five-row blocker queue', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /blockers\.slice\(0, 5\)\.map\(row =>/);
  assert.doesNotMatch(source, /blockers\.slice\(0, 3\)\.map\(row =>/);
});

test('action receipt dock runs the selected blocker instead of only the first blocker', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /selectedBlockerId = ''/);
  assert.match(source, /const activeBlocker = blockers\.find\(row => row\.id === selectedBlockerId\) \|\| topBlocker/);
  assert.match(source, /onClick=\{\(\) => onRunBlocker\(activeBlocker\)\}/);
  assert.match(source, /onClick=\{\(\) => onStageBlocker\(activeBlocker\)\}/);
  assert.match(source, /aria-pressed=\{row\.id === activeBlocker\?\.id\}/);
  assert.match(source, /setSelectedLiveBlockerId\(row\.id\)/);
  assert.match(source, /const actionId = row\.safeActionId \|\| row\.controlId/);
  assert.match(source, /id: 'comms-model-probe'/);
  assert.match(source, /id: 'comms-local-review'/);
});

test('cloud sync build uses local preview when the dashboard has no bearer token', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /CLOUD_PUBLISH_OBJECTIVE/);
  assert.match(source, /const \[writePacket, setWritePacket\] = useState\(false\);/);
  assert.match(source, /if \(!TOKEN\) \{\s+const preview = buildLocalPublishPreview\(sync, writePacket\);/);
  assert.match(source, /onCommandEvent\('Publish local preview generated'/);
  assert.match(source, /const effectiveWritePacket = canWritePacket && writePacket/);
  assert.match(source, /disabled=\{!canWritePacket\}/);
  assert.match(source, /Save requires token; preview is read-only/);
});

test('cloud sync build uses authenticated read-only preview unless save is explicit', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /effectiveWritePacket\s+\?\s+await fetch\(`\$\{BRIDGE\}\/sync\/publish-packet`/);
  assert.match(source, /write_packet: true/);
  assert.match(source, /:\s+await fetch\(`\$\{BRIDGE\}\/sync\/publish-preview\?\$\{new URLSearchParams/);
  assert.match(source, /cache: 'no-store'/);
  assert.match(source, /effectiveWritePacket \? 'Publish packet saved' : 'Publish preview built'/);
  assert.match(source, /effectiveWritePacket \? 'Save Publish Packet' : 'Build Publish Preview'/);
});

test('codebase intelligence can run the protected local analyzer route', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /const runLiveAnalysis = async \(\) =>/);
  assert.match(source, /fetch\(`\$\{BRIDGE\}\/codebase\/analyze`/);
  assert.match(source, /headers: jsonHeaders\(\)/);
  assert.match(source, /max_files: 2500/);
  assert.match(source, /normalizeCodebaseAnalysis\(data\)/);
  assert.match(source, /onCommandEvent\(\s+'Codebase analysis refreshed'/);
  assert.match(source, /Bearer token required for POST \/codebase\/analyze/);
});

test('repo guard can run the protected local context guard route', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /const runRepoGuard = async \(\) =>/);
  assert.match(source, /fetch\(`\$\{BRIDGE\}\/repo\/context-guard\?\$\{params\.toString\(\)\}`/);
  assert.match(source, /headers: jsonHeaders\(\)/);
  assert.match(source, /include_repos: 'false'/);
  assert.match(source, /normalizeRepoContext\(data\)/);
  assert.match(source, /<strong>{activeRepoContext\?\.cache_age_s \?\? 0}s<\/strong>/);
  assert.match(source, /onCommandEvent\(\s+'Repo guard refreshed'/);
  assert.match(source, /Bearer token required for GET \/repo\/context-guard/);
});

test('worker directory can refresh the live VM relay status route', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /const refreshWorkerStatus = async \(\) =>/);
  assert.match(source, /fetch\(`\$\{BRIDGE\}\/vm\/status`, \{ cache: 'no-store' \}\)/);
  assert.match(source, /normalizeVmRelayStatus\(\{\s+\.\.\.data,\s+sampled_at_utc: new Date\(\)\.toISOString\(\)/);
  assert.match(source, /onCommandEvent\(\s+'Worker status refreshed'/);
  assert.match(source, /data-control-intent="Refresh live VM worker status"/);
  assert.match(source, /Refresh Worker/);
  assert.match(source, /vm_status_source: \$\{activeRelayStatus \? 'live GET \/vm\/status' : 'dashboard\/status snapshot'\}/);
});

test('alliance control can run and stage the protected collaboration proof route', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /const runCollaborationProof = async \(\) =>/);
  assert.match(source, /fetch\(`\$\{BRIDGE\}\/proof\/collaboration`/);
  assert.match(source, /include_live_checks: true/);
  assert.match(source, /run_gemini_smoke: false/);
  assert.match(source, /write_state: false/);
  assert.match(source, /normalizeCollaborationProof\(data\)/);
  assert.match(source, /onCommandEvent\(\s+'Alliance proof refreshed'/);
  assert.match(source, /data-control-intent="Run live collaboration proof route"/);
  assert.match(source, /Run Proof/);
  assert.match(source, /Stage Proof/);
  assert.match(source, /Bearer token required for POST \/proof\/collaboration/);
  assert.match(source, /# Alliance Collaboration Proof/);
  assert.match(source, /## Agent Points Of View/);
});

test('offline dashboard snapshot preserves context while marking the bridge offline', () => {
  const previous = {
    online: true,
    uptime: '3m',
    bridgeStatus: 'running',
    updateMode: 'connecting',
    statusTimestamp: '',
    cloudSync: { state: 'blocked', dirty_count: 4 }
  };

  const offline = offlineDashboardStatusSnapshot(previous);

  assert.notEqual(offline, previous);
  assert.equal(offline.online, false);
  assert.equal(offline.uptime, 'OFFLINE');
  assert.equal(offline.bridgeStatus, 'offline');
  assert.equal(offline.updateMode, 'offline');
  assert.equal(offline.cloudSync.dirty_count, 4);
});

test('break test refreshes dashboard status before scoring startup placeholders', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /const runBreakTest = async \(\) =>/);
  assert.match(source, /const statusForReport = await ensureFreshBreakTestStatus\(\)/);
  assert.match(source, /const refreshedStatus = await onRefreshStatus\('break-test'\)/);
  assert.match(source, /const report = buildBreakTestReport\(statusForReport\)/);
  assert.match(source, /onRefreshStatus=\{refreshDashboardStatus\}/);
});

test('break test status refresh failure returns an offline snapshot for scoring', () => {
  const source = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8');

  assert.match(source, /const markDashboardOffline = useCallback\(\(\) => \{/);
  assert.match(source, /offlineStatus = offlineDashboardStatusSnapshot\(previous\)/);
  assert.match(source, /return offlineStatus \|\| offlineDashboardStatusSnapshot\(\)/);
  assert.match(source, /catch \{\s+return markDashboardOffline\(\);\s+\}/);
  assert.doesNotMatch(source, /catch \{\s+markDashboardOffline\(\);\s+return null;\s+\}/);
});
