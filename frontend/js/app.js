/* ─────────────────────────────────────────────
   Market Intelligence AI - 프론트엔드 앱
   ───────────────────────────────────────────── */

const API = '';  // 같은 서버 사용

let currentSessionId = null;
let ws = null;
let agentSpecs = [];
let elapsedTimer = null;
let startTime = null;

// 에이전트 상태 추적
const agentStates = {};

// ── 초기화 ──
document.addEventListener('DOMContentLoaded', () => {
  checkApiStatus();
  loadAgentSpecs();
  initNavigation();
  initForm();
  initTabs();
  initResultButtons();
});

// ── API 상태 확인 ──
async function checkApiStatus() {
  const badge = document.getElementById('api-status');
  try {
    const res = await fetch(`${API}/api/health`);
    const data = await res.json();
    if (data.api_key_set) {
      badge.textContent = '● API 연결됨';
      badge.className = 'api-badge ok';
    } else {
      badge.textContent = '● API 키 미설정';
      badge.className = 'api-badge error';
    }
  } catch {
    badge.textContent = '● 서버 오프라인';
    badge.className = 'api-badge error';
  }
}

// ── 에이전트 명세 로드 ──
async function loadAgentSpecs() {
  try {
    const res = await fetch(`${API}/api/agents`);
    const data = await res.json();
    agentSpecs = data.agents;
    renderAgentsOverview();
  } catch (e) {
    console.error('에이전트 명세 로드 실패:', e);
  }
}

function renderAgentsOverview() {
  const grid = document.getElementById('agents-grid');
  if (!agentSpecs.length) return;

  const phases = {
    1: { label: 'Phase 1 · 데이터 수집', agents: [] },
    2: { label: 'Phase 2 · 분석', agents: [] },
    3: { label: 'Phase 3 · 종합', agents: [] },
    4: { label: 'Phase 4 · 산출물', agents: [] },
  };

  agentSpecs.forEach(a => phases[a.phase]?.agents.push(a));

  grid.innerHTML = Object.entries(phases).map(([ph, info]) => `
    <div class="phase-column phase-${ph}">
      <div class="phase-header">${info.label}</div>
      ${info.agents.map(a => `
        <div class="agent-chip" title="${a.role}">
          <div class="agent-chip-name">${a.name}</div>
          <div class="agent-chip-role">${a.role}</div>
        </div>
      `).join('')}
    </div>
  `).join('');
}

// ── 네비게이션 ──
function initNavigation() {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      showView(view);
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (view === 'sessions') loadSessions();
    });
  });
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${name}`)?.classList.add('active');
}

// ── 분석 폼 ──
function initForm() {
  document.getElementById('analysis-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    await startAnalysis();
  });
}

async function startAnalysis() {
  const topic = document.getElementById('topic').value.trim();
  if (!topic) return;

  const btn = document.getElementById('start-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">◌</span> 시작 중...';

  const req = {
    topic,
    industries: document.getElementById('industries').value.split(',').map(s => s.trim()).filter(Boolean),
    target_companies: document.getElementById('companies').value.split(',').map(s => s.trim()).filter(Boolean),
    regions: document.getElementById('regions').value.split(',').map(s => s.trim()).filter(Boolean),
    date_range_days: parseInt(document.getElementById('date-range').value) || 90,
    custom_instructions: document.getElementById('instructions').value.trim() || null,
  };

  try {
    // 1. 세션 생성
    const res = await fetch(`${API}/api/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || '세션 생성 실패');
      return;
    }

    const { session_id } = await res.json();
    currentSessionId = session_id;

    // 2. 진행 뷰 초기화
    initProgressView(topic, session_id);
    showView('progress');

    // 3. WebSocket 연결 — open 확인 후 run 호출
    await connectWebSocket(session_id);

    // 4. 분석 실행
    await fetch(`${API}/api/sessions/${session_id}/run`, { method: 'POST' });

  } catch (e) {
    alert('오류: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">▶</span> MI 분석 시작';
  }
}

// ── 진행 뷰 초기화 ──
function initProgressView(topic, sessionId) {
  document.getElementById('progress-topic').textContent = topic;
  document.getElementById('progress-session-id').textContent = `세션: ${sessionId.substring(0, 8)}...`;
  document.getElementById('overall-bar').style.width = '0%';
  document.getElementById('overall-pct').textContent = '0%';
  document.getElementById('log-output').innerHTML = '';

  // 에이전트 상태 초기화
  Object.keys(agentStates).forEach(k => delete agentStates[k]);

  // 에이전트 카드 렌더링
  renderAgentCards();

  // 타이머 시작
  startTime = Date.now();
  clearInterval(elapsedTimer);
  elapsedTimer = setInterval(() => {
    const sec = Math.floor((Date.now() - startTime) / 1000);
    const m = Math.floor(sec / 60), s = sec % 60;
    document.getElementById('progress-elapsed').textContent =
      `경과: ${m}분 ${s}초`;
  }, 1000);

  // 로그 지우기 버튼
  document.getElementById('clear-log').onclick = () => {
    document.getElementById('log-output').innerHTML = '';
  };

  // 분석 중지 버튼
  const cancelBtn = document.getElementById('cancel-btn');
  cancelBtn.disabled = false;
  cancelBtn.onclick = async () => {
    if (!currentSessionId) return;
    if (!confirm('분석을 중지하시겠습니까?')) return;
    cancelBtn.disabled = true;
    cancelBtn.textContent = '중지 중...';
    try {
      await fetch(`${API}/api/sessions/${currentSessionId}/cancel`, { method: 'POST' });
    } catch (e) {
      console.error('취소 요청 실패:', e);
    }
  };
}

function renderAgentCards() {
  const container = document.getElementById('agent-cards');
  container.innerHTML = agentSpecs.map(a => `
    <div class="agent-card pending" id="ac-${a.id}">
      <div class="ac-phase" style="color: var(--phase${a.phase})">Phase ${a.phase}</div>
      <div class="ac-name">${a.name}</div>
      <div class="ac-status">
        <span class="ac-dot"></span>
        <span class="ac-status-text">대기 중</span>
      </div>
      <div class="ac-progress"><div class="ac-progress-bar" style="width:0%"></div></div>
    </div>
  `).join('');
}

function updateAgentCard(agentId, state, message, progress) {
  const card = document.getElementById(`ac-${agentId}`);
  if (!card) return;
  card.className = `agent-card ${state}`;
  card.querySelector('.ac-status-text').textContent = message || state;
  if (progress !== undefined) {
    card.querySelector('.ac-progress-bar').style.width = `${progress}%`;
  }
}

// ── WebSocket — 연결 완료(open)를 기다리는 Promise 반환 ──
function connectWebSocket(sessionId) {
  return new Promise((resolve) => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${proto}://${location.host}/ws/${sessionId}`;

    if (ws) ws.close();
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      addLog('info', 'WebSocket', '연결됨');
      resolve();
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleWSMessage(msg);
    };

    ws.onerror = () => {
      addLog('error', 'WebSocket', '연결 오류');
      resolve(); // 오류여도 run은 진행
    };

    ws.onclose = () => addLog('warn', 'WebSocket', '연결 종료');
  });
}

function handleWSMessage(msg) {
  const { type, agent_id, agent_name, phase, progress_pct, message, data } = msg;

  switch (type) {
    case 'agent_start':
      agentStates[agent_id] = 'running';
      updateAgentCard(agent_id, 'running', '실행 중', 5);
      addLog('info', agent_name, '시작');
      break;

    case 'agent_progress':
      updateAgentCard(agent_id, 'running', message, progress_pct);
      addLog('info', agent_name, message);
      break;

    case 'agent_complete':
      agentStates[agent_id] = 'completed';
      const quality = data?.quality || '';
      updateAgentCard(agent_id, 'completed', `완료 (${quality})`, 100);
      addLog('success', agent_name, `완료 - ${data?.data_points || 0}개 데이터, ${data?.duration?.toFixed(1) || 0}초`);
      break;

    case 'agent_error':
      agentStates[agent_id] = 'failed';
      updateAgentCard(agent_id, 'failed', '오류', 0);
      addLog('error', agent_name, message);
      break;

    case 'phase_complete':
      addLog('success', `Phase ${phase}`, `완료 (${progress_pct?.toFixed(0)}%)`);
      break;

    case 'session_complete':
      clearInterval(elapsedTimer);
      updateOverallProgress(100);
      addLog('success', '시스템', 'MI 분석 완료!');
      document.getElementById('cancel-btn').disabled = true;
      setTimeout(() => loadAndShowResults(), 1500);
      break;

    case 'session_cancelled':
      clearInterval(elapsedTimer);
      addLog('warn', '시스템', '분석이 중지되었습니다.');
      document.getElementById('cancel-btn').textContent = '분석 중지됨';
      document.getElementById('cancel-btn').disabled = true;
      break;

    case 'qa_retry':
      addLog('warn', 'QA Agent',
        `품질 기준 미충족 (${(data?.qa_score * 100).toFixed(0)}%) — Phase ${data?.retry_phases?.join(', ')} 재실행 중... (${data?.attempt}/${data?.max_retries})`
      );
      break;

    case 'log':
      addLog('info', '시스템', message);
      break;
  }

  if (progress_pct !== undefined && progress_pct !== null) {
    updateOverallProgress(progress_pct);
  }
}

function updateOverallProgress(pct) {
  document.getElementById('overall-bar').style.width = `${pct}%`;
  document.getElementById('overall-pct').textContent = `${pct.toFixed(0)}%`;
}

function addLog(level, agent, message) {
  const output = document.getElementById('log-output');
  const now = new Date().toLocaleTimeString('ko-KR', { hour12: false });
  const line = document.createElement('div');
  line.className = `log-line log-${level === 'success' ? 'success' : level === 'error' ? 'error' : level === 'warn' ? 'warn' : ''}`;
  line.innerHTML = `<span class="log-time">${now}</span><span class="log-agent">[${agent}]</span><span class="log-msg">${message}</span>`;
  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}

// ── 결과 로드 ──
async function loadAndShowResults() {
  if (!currentSessionId) return;

  try {
    const [sessionRes, reportRes] = await Promise.all([
      fetch(`${API}/api/sessions/${currentSessionId}`),
      fetch(`${API}/api/sessions/${currentSessionId}/report`),
    ]);

    const session = await sessionRes.json();
    const report = await reportRes.json();

    renderResults(session, report);
    showView('result');
  } catch (e) {
    addLog('error', '시스템', '결과 로드 실패: ' + e.message);
  }
}

function renderResults(session, report) {
  // 헤더
  document.getElementById('result-topic').textContent = session.scope?.topic || '분석 결과';

  const created = new Date(session.created_at);
  const completed = session.completed_at ? new Date(session.completed_at) : new Date();
  const duration = Math.floor((completed - created) / 1000);
  const m = Math.floor(duration / 60), s = duration % 60;

  document.getElementById('result-duration').textContent = `소요 시간: ${m}분 ${s}초`;
  document.getElementById('result-agents').textContent = `에이전트: ${session.agents_completed || 0}/14`;
  document.getElementById('result-tokens').textContent = `토큰: ${(session.total_tokens_used || 0).toLocaleString()}`;

  // Executive Summary
  const execEl = document.getElementById('exec-summary-content');
  execEl.innerHTML = markdownToHtml(report.executive_summary || '분석 중...');

  // 상세 리포트
  const reportEl = document.getElementById('report-content');
  reportEl.innerHTML = markdownToHtml(report.final_report || '리포트 생성 중...');

  // 대시보드
  if (report.dashboard_data) {
    renderDashboard(report.dashboard_data);
  }

  // 에이전트별 결과 (비동기 로드)
  loadAgentResults();
}

async function loadAgentResults() {
  const container = document.getElementById('agent-results-list');
  container.innerHTML = '<p class="empty-msg">결과 로딩 중...</p>';

  const results = [];
  for (const spec of agentSpecs) {
    try {
      const res = await fetch(`${API}/api/sessions/${currentSessionId}/agents/${spec.id}`);
      if (res.ok) results.push(await res.json());
    } catch {}
  }

  container.innerHTML = results.map(r => `
    <div class="agent-result-item">
      <div class="agent-result-header" onclick="toggleAgentResult('${r.agent_id}')">
        <span class="ari-phase" style="background: rgba(79,142,247,0.15); color: var(--phase${r.phase})">
          Phase ${r.phase}
        </span>
        <span class="ari-name">${r.agent_name}</span>
        <span class="ari-quality ${r.quality?.overall || ''}">${
          r.quality?.overall === 'pass' ? '✓ 통과' :
          r.quality?.overall === 'warning' ? '⚠ 주의' : '✗ 실패'
        }</span>
        <div class="ari-actions" onclick="event.stopPropagation()">
          <button class="ari-btn" onclick="openAgentPrint('${r.agent_id}')" title="PDF로 저장">🖨️</button>
          <button class="ari-btn" onclick="downloadAgentMd('${r.agent_id}', '${r.agent_name}')" title="Markdown 다운로드">⬇ MD</button>
        </div>
        <span class="ari-toggle">▼</span>
      </div>
      <div class="agent-result-body" id="arb-${r.agent_id}">
        <div class="ari-meta-row">
          <span>데이터 ${r.data_points_collected || 0}건</span>
          <span>${r.duration_seconds ? r.duration_seconds.toFixed(1) + '초' : ''}</span>
          <span>${(r.sources_used || []).slice(0,3).join(' · ')}</span>
        </div>
        <p class="ari-summary">${r.summary || ''}</p>
        <div class="ari-analysis markdown-body">${markdownToHtml(r.analysis || '분석 내용 없음')}</div>
        ${r.quality?.checks ? `
        <details class="quality-details">
          <summary>품질 검증 상세 (${r.quality.checks.filter(c => c.level === 'pass').length}/${r.quality.checks.length} 통과)</summary>
          <table class="quality-table">
            <thead><tr><th>항목</th><th>목표</th><th>실제</th><th>결과</th></tr></thead>
            <tbody>
              ${r.quality.checks.map(c => `
                <tr>
                  <td>${c.criterion}</td>
                  <td>${c.target}</td>
                  <td>${c.actual}</td>
                  <td style="color:${c.level === 'pass' ? '#22c55e' : c.level === 'warning' ? '#f59e0b' : '#ef4444'};font-weight:700">
                    ${c.level === 'pass' ? '✓' : c.level === 'warning' ? '⚠' : '✗'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </details>` : ''}
      </div>
    </div>
  `).join('');
}

function toggleAgentResult(agentId) {
  const body = document.getElementById(`arb-${agentId}`);
  body?.classList.toggle('open');
}

// ── 대시보드 렌더링 ──
function renderDashboard(data) {
  const { metrics, charts, alerts } = data;

  // 메트릭
  const marketMetrics = metrics?.market || {};
  const metricsEl = document.getElementById('dashboard-metrics');
  metricsEl.innerHTML = [
    { label: '총 시가총액', value: `$${((marketMetrics.total_market_cap_usd || 0) / 1e9).toFixed(0)}B`, change: marketMetrics.market_cap_change_24h_pct },
    { label: '24h 거래량', value: `$${((marketMetrics.total_volume_24h_usd || 0) / 1e9).toFixed(0)}B`, change: null },
    { label: 'BTC 도미넌스', value: `${(marketMetrics.btc_dominance_pct || 0).toFixed(1)}%`, change: null },
    { label: '완료 에이전트', value: `${metrics?.session?.completed || 0}/14`, change: null },
  ].map(m => `
    <div class="metric-card">
      <div class="metric-label">${m.label}</div>
      <div class="metric-value">${m.value}</div>
      ${m.change !== null && m.change !== undefined ? `
        <div class="metric-change ${m.change >= 0 ? 'up' : 'down'}">
          ${m.change >= 0 ? '▲' : '▼'} ${Math.abs(m.change).toFixed(2)}%
        </div>` : ''}
    </div>
  `).join('');

  // 알림
  const alertsEl = document.getElementById('dashboard-alerts');
  alertsEl.innerHTML = (alerts || []).map(a => `
    <div class="alert-item ${a.type}">
      <span>${a.type === 'warning' ? '⚠' : 'ℹ'}</span>
      <span>${a.message}</span>
    </div>
  `).join('') || '';

  // 차트
  const chartsEl = document.getElementById('dashboard-charts');
  chartsEl.innerHTML = (charts || []).map(c => renderBarChart(c)).join('');
}

function renderBarChart(chart) {
  const items = chart.data || [];
  const maxVal = Math.max(...items.map(i => Math.abs(i.value)), 1);

  return `
    <div class="chart-card">
      <div class="chart-title">${chart.title}</div>
      <div class="bar-chart">
        ${items.map(item => `
          <div class="bar-row">
            <div class="bar-label" title="${item.label}">${item.label}</div>
            <div class="bar-track">
              <div class="bar-fill" style="width: ${(Math.abs(item.value) / maxVal * 100).toFixed(1)}%;
                background: ${item.color === 'red' ? 'var(--error)' : item.color === 'green' ? 'var(--success)' : 'var(--accent)'}">
                <span class="bar-value">${typeof item.value === 'number' ? item.value.toFixed(1) : item.value}${item.unit || ''}</span>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// ── 탭 ──
function initTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const tabName = tab.dataset.tab;
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(`tab-${tabName}`)?.classList.add('active');
    });
  });
}

// ── 결과 버튼 ──
function initResultButtons() {
  document.getElementById('new-analysis-btn')?.addEventListener('click', () => {
    showView('home');
    document.querySelector('.nav-btn[data-view="home"]')?.click();
  });

  document.getElementById('print-report-btn')?.addEventListener('click', () => {
    if (!currentSessionId) return;
    window.open(`${API}/api/sessions/${currentSessionId}/report/print`, '_blank');
  });

  document.getElementById('download-md-btn')?.addEventListener('click', () => {
    if (!currentSessionId) return;
    const a = document.createElement('a');
    a.href = `${API}/api/sessions/${currentSessionId}/report/markdown`;
    a.download = `MI_Report_${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
  });
}

// ── 에이전트별 PDF/MD 다운로드 ──
function openAgentPrint(agentId) {
  if (!currentSessionId) return;
  window.open(`${API}/api/sessions/${currentSessionId}/agents/${agentId}/print`, '_blank');
}

function downloadAgentMd(agentId, agentName) {
  if (!currentSessionId) return;
  const a = document.createElement('a');
  a.href = `${API}/api/sessions/${currentSessionId}/agents/${agentId}/markdown`;
  a.download = `${agentId}_${agentName.replace(/\s+/g, '_')}.md`;
  a.click();
}

// ── 세션 이력 ──
async function loadSessions() {
  const container = document.getElementById('sessions-list');
  try {
    const res = await fetch(`${API}/api/sessions`);
    const { sessions } = await res.json();

    if (!sessions.length) {
      container.innerHTML = '<p class="empty-msg">분석 이력이 없습니다.</p>';
      return;
    }

    container.innerHTML = sessions.reverse().map(s => `
      <div class="session-item" onclick="loadSession('${s.session_id}')">
        <div class="si-topic">${s.topic}</div>
        <div class="si-meta">
          <span>${new Date(s.created_at).toLocaleString('ko-KR')}</span>
          <span>${s.progress_pct?.toFixed(0)}% 완료</span>
        </div>
        <span class="si-status ${s.status}">${
          s.status === 'completed' ? '완료' :
          s.status === 'running' ? '진행 중' : s.status
        }</span>
      </div>
    `).join('');
  } catch {
    container.innerHTML = '<p class="empty-msg">이력 로드 실패</p>';
  }
}

async function loadSession(sessionId) {
  currentSessionId = sessionId;
  await loadAndShowResults();
  document.querySelector('.nav-btn[data-view="home"]')?.classList.remove('active');
}

// ── Markdown 변환 (경량) ──
function markdownToHtml(md) {
  if (!md) return '';
  return md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 헤딩
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // 굵게/기울임
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 코드
    .replace(/`(.+?)`/g, '<code>$1</code>')
    // 수평선
    .replace(/^---+$/gm, '<hr>')
    // 테이블 (간단)
    .replace(/^\|(.+)\|$/gm, (match) => {
      const isSeparator = match.replace(/[\|\s\-:]/g, '') === '';
      if (isSeparator) return '';
      const cells = match.slice(1, -1).split('|').map(c => c.trim());
      const isHeader = false;
      return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    })
    // 리스트
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // 인용
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // 단락
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<)(.+)$/gm, (m) => m.startsWith('<') ? m : m)
    // 테이블 래핑
    .replace(/(<tr>[\s\S]+?<\/tr>)+/g, (m) => `<table>${m}</table>`)
    // 리스트 래핑
    .replace(/(<li>[\s\S]+?<\/li>)+/g, (m) => `<ul>${m}</ul>`)
    // 줄바꿈
    .replace(/\n/g, '<br>');
}
