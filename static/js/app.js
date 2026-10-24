const state = {
  dashboard: {},
  servers: [],
  alerts: [],
  thresholds: {},
  selectedServerId: null,
  filterStatus: 'All',
  searchTerm: '',
  sortKey: 'health_score',
  charts: {},
  history: {}
};

const currencyFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

document.addEventListener('DOMContentLoaded', () => {
  bindEvents();
  loadDashboard();
  setInterval(loadDashboard, 2000);
});

function bindEvents() {
  document.getElementById('serverSearch').addEventListener('input', (event) => {
    state.searchTerm = event.target.value.trim().toLowerCase();
    renderServerCards();
  });

  document.getElementById('statusFilter').addEventListener('change', (event) => {
    state.filterStatus = event.target.value;
    renderServerCards();
  });

  document.getElementById('refreshBtn').addEventListener('click', loadDashboard);

  document.getElementById('addServerForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      name: document.getElementById('serverName').value.trim(),
      region: document.getElementById('serverRegion').value.trim(),
      operating_system: document.getElementById('serverOS').value.trim(),
      ip_address: document.getElementById('serverIp').value.trim()
    };

    if (!payload.name || !payload.region || !payload.operating_system || !payload.ip_address) {
      return;
    }

    await fetchJSON('/api/servers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    event.target.reset();
    await loadDashboard();
  });

  document.getElementById('thresholdForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {};
    const resourceTypes = ['cpu', 'memory', 'disk', 'network'];
    resourceTypes.forEach((resource) => {
      const warning = document.getElementById(`warning-${resource}`)?.value;
      const critical = document.getElementById(`critical-${resource}`)?.value;
      if (warning && critical) {
        payload[resource] = {
          warning_threshold: Number(warning),
          critical_threshold: Number(critical)
        };
      }
    });

    if (Object.keys(payload).length) {
      await fetchJSON('/api/thresholds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      await loadDashboard();
    }
  });

  document.addEventListener('click', async (event) => {
    const actionTarget = event.target.closest('[data-action]');
    if (!actionTarget) {
      return;
    }

    const serverId = actionTarget.dataset.serverId;
    const action = actionTarget.dataset.action;

    if (action === 'fail-server') {
      await fetchJSON(`/api/servers/${serverId}/fail`, { method: 'POST' });
      await loadDashboard();
    }

    if (action === 'recover-server') {
      await fetchJSON(`/api/servers/${serverId}/recover`, { method: 'POST' });
      await loadDashboard();
    }

    if (action === 'delete-server') {
      if (!window.confirm(`Delete server ${serverId}? This action cannot be undone.`)) {
        return;
      }
      await fetchJSON(`/api/servers/${serverId}`, { method: 'DELETE' });
      await loadDashboard();
    }

    if (action === 'resolve-alert') {
      const alertId = actionTarget.dataset.alertId;
      await fetchJSON(`/api/alerts/${alertId}/resolve`, { method: 'POST' });
      await loadDashboard();
    }
  });

  document.getElementById('historyServerSelect').addEventListener('change', async (event) => {
    state.selectedServerId = event.target.value;
    await loadHistoryForSelectedServer();
  });

  document.querySelectorAll('th[data-sort]').forEach((cell) => {
    cell.addEventListener('click', () => {
      const sortKey = cell.dataset.sort;
      state.sortKey = sortKey;
      renderHealthTable();
    });
  });
}

async function loadDashboard() {
  try {
    const response = await fetchJSON('/api/dashboard');
    state.dashboard = response;
    state.servers = response.servers || [];
    state.alerts = response.alerts || [];
    state.thresholds = response.thresholds || {};

    if (!state.selectedServerId && state.servers.length) {
      state.selectedServerId = state.servers[0].server_id;
    }

    renderDashboardStats();
    renderOverview();
    renderThresholdForm();
    renderServerCards();
    renderAlerts();
    renderHealthTable();
    renderServerOptions();
    await loadHistoryForSelectedServer();
  } catch (error) {
    console.error('Failed to load dashboard', error);
  }
}

async function loadHistoryForSelectedServer() {
  if (!state.selectedServerId) {
    return;
  }

  const data = await fetchJSON(`/api/history/${state.selectedServerId}`);
  state.history[state.selectedServerId] = data.history || [];
  renderCharts();
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Request failed');
  }
  return response.json();
}

function getStatusClass(status) {
  if (status === 'ONLINE') return 'status-online';
  if (status === 'WARNING') return 'status-warning';
  if (status === 'CRITICAL') return 'status-critical';
  return 'status-offline';
}

function renderDashboardStats() {
  const stats = state.dashboard;
  const cart = [
    { label: 'Total Servers', value: stats.total_servers || 0, delta: 'All simulated nodes' },
    { label: 'Online Servers', value: stats.online_servers || 0, delta: 'Healthy and active' },
    { label: 'Offline Servers', value: stats.offline_servers || 0, delta: 'Unavailable nodes' },
    { label: 'Warning Servers', value: stats.warning_servers || 0, delta: 'Monitoring attention' },
    { label: 'Critical Servers', value: stats.critical_servers || 0, delta: 'Immediate action' },
    { label: 'Avg CPU', value: `${stats.average_cpu_usage || 0}%`, delta: 'Processing load' },
    { label: 'Avg Memory', value: `${stats.average_memory_usage || 0}%`, delta: 'Memory footprint' },
    { label: 'Avg Disk', value: `${stats.average_disk_usage || 0}%`, delta: 'Storage saturation' },
    { label: 'Infrastructure Health', value: `${stats.overall_infrastructure_health || 0}%`, delta: 'Composite health score' }
  ];

  document.getElementById('dashboardStats').innerHTML = cart.map((item) => `
    <div class="stat-card">
      <div class="label">${item.label}</div>
      <span class="value">${item.value}</span>
      <div class="delta">${item.delta}</div>
    </div>
  `).join('');
}

function renderOverview() {
  const stats = state.dashboard;
  const items = [
    { label: 'Healthy Servers', value: stats.healthy_servers || 0 },
    { label: 'Warning Servers', value: stats.warning_servers || 0 },
    { label: 'Critical Servers', value: stats.critical_servers || 0 },
    { label: 'Offline Servers', value: stats.offline_servers || 0 },
    { label: 'Average CPU', value: `${stats.average_cpu_usage || 0}%` },
    { label: 'Average Memory', value: `${stats.average_memory_usage || 0}%` },
    { label: 'Average Disk', value: `${stats.average_disk_usage || 0}%` },
    { label: 'Average Network', value: `${stats.average_network_usage || 0}%` }
  ];

  document.getElementById('overviewMetrics').innerHTML = items.map((item) => `
    <div class="overview-item">
      <div>${item.label}</div>
      <strong>${item.value}</strong>
    </div>
  `).join('');
}

function renderThresholdForm() {
  const mapping = {
    cpu: 'CPU',
    memory: 'Memory',
    disk: 'Disk',
    network: 'Network'
  };

  const element = document.getElementById('thresholdFields');
  element.innerHTML = Object.entries(mapping).map(([resource, label]) => {
    const item = state.thresholds[resource] || { warning_threshold: 0, critical_threshold: 0 };
    return `
      <div class="threshold-row">
        <div>
          <label>${label}</label>
          <input id="warning-${resource}" type="number" min="0" max="100" value="${item.warning_threshold ?? 0}" />
        </div>
        <div>
          <label>Critical</label>
          <input id="critical-${resource}" type="number" min="0" max="100" value="${item.critical_threshold ?? 0}" />
        </div>
        <div>
          <label>Resource</label>
          <div class="status-pill">${label}</div>
        </div>
      </div>
    `;
  }).join('');
}

function filterServers() {
  return state.servers.filter((server) => {
    const matchesSearch = !state.searchTerm || [
      server.name,
      server.server_id,
      server.region,
      server.ip_address
    ].join(' ').toLowerCase().includes(state.searchTerm);

    const matchesStatus = state.filterStatus === 'All' || server.status === state.filterStatus;
    return matchesSearch && matchesStatus;
  });
}

function renderServerCards() {
  const filtered = filterServers();
  const cards = document.getElementById('serverCards');
  cards.innerHTML = filtered.map((server) => `
    <article class="server-card ${server.status.toLowerCase()}">
      <div class="card-top">
        <div>
          <h3>${server.name}</h3>
          <div class="server-subtitle">${server.server_id}</div>
        </div>
        <span class="status-badge ${getStatusClass(server.status)}">${server.status}</span>
      </div>

      <div class="server-subtitle">${server.region} • ${server.operating_system}</div>
      <div class="server-subtitle">IP: ${server.ip_address}</div>

      <div class="metrics-grid">
        <div class="metric"><span class="metric-label">CPU</span><strong>${currencyFormat.format(server.cpu_usage)}%</strong></div>
        <div class="metric"><span class="metric-label">Memory</span><strong>${currencyFormat.format(server.memory_usage)}%</strong></div>
        <div class="metric"><span class="metric-label">Disk</span><strong>${currencyFormat.format(server.disk_usage)}%</strong></div>
        <div class="metric"><span class="metric-label">Network</span><strong>${currencyFormat.format(server.network_usage)}%</strong></div>
      </div>

      <div class="health-score">
        <span>Health Score</span>
        <strong>${server.health_score}</strong>
      </div>

      <div class="server-subtitle">Last Checked: ${server.last_checked}</div>

      <div class="card-actions">
        <button class="action-btn fail" data-action="fail-server" data-server-id="${server.server_id}">Simulate Failure</button>
        <button class="action-btn recover" data-action="recover-server" data-server-id="${server.server_id}">Recover</button>
        <button class="delete-btn" data-action="delete-server" data-server-id="${server.server_id}">Remove</button>
      </div>
    </article>
  `).join('') || '<div class="panel">No matching servers found.</div>';
}

function renderAlerts() {
  const alertSummary = document.getElementById('alertSummary');
  const summary = {
    active: state.alerts.filter((alert) => alert.status === 'ACTIVE').length,
    critical: state.alerts.filter((alert) => alert.status === 'ACTIVE' && alert.severity === 'CRITICAL').length,
    warning: state.alerts.filter((alert) => alert.status === 'ACTIVE' && alert.severity === 'WARNING').length,
    resolved: state.alerts.filter((alert) => alert.status === 'RESOLVED').length
  };

  alertSummary.innerHTML = `
    <div class="alert-pill"><span>Active Alerts</span><strong>${summary.active}</strong></div>
    <div class="alert-pill"><span>Critical Alerts</span><strong>${summary.critical}</strong></div>
    <div class="alert-pill"><span>Warning Alerts</span><strong>${summary.warning}</strong></div>
    <div class="alert-pill"><span>Resolved Alerts</span><strong>${summary.resolved}</strong></div>
  `;

  const list = document.getElementById('alertList');
  list.innerHTML = (state.alerts || []).slice(0, 10).map((alert) => `
    <div class="alert-item">
      <div class="alert-meta">
        <strong>${alert.server_id} • ${alert.resource_type}</strong>
        <span>${alert.message}</span>
        <span>Threshold: ${alert.threshold}% / Current: ${alert.current_value}%</span>
        <span class="alert-severity ${alert.severity.toLowerCase()}">${alert.severity}</span>
        <span>Status: ${alert.status}</span>
      </div>
      ${alert.status === 'ACTIVE' ? `<div class="alert-actions"><button class="secondary-btn" data-action="resolve-alert" data-alert-id="${alert.id}">Resolve</button></div>` : ''}
    </div>
  `).join('') || '<div>No alerts recorded.</div>';
}

function renderHealthTable() {
  const rows = [...state.servers].sort((a, b) => {
    const direction = 1;
    const left = Number(a[state.sortKey] ?? 0);
    const right = Number(b[state.sortKey] ?? 0);
    if (left === right) return 0;
    return left > right ? direction : -direction;
  });

  document.getElementById('healthTableBody').innerHTML = rows.map((server) => `
    <tr>
      <td>${server.name}</td>
      <td>${server.region}</td>
      <td><span class="status-badge ${getStatusClass(server.status)}">${server.status}</span></td>
      <td>${server.cpu_usage}%</td>
      <td>${server.memory_usage}%</td>
      <td>${server.disk_usage}%</td>
      <td>${server.network_usage}%</td>
      <td>${server.health_score}</td>
      <td>${server.last_checked}</td>
    </tr>
  `).join('');
}

function renderServerOptions() {
  const select = document.getElementById('historyServerSelect');
  if (!state.servers.length) {
    select.innerHTML = '<option value="">No servers</option>';
    return;
  }

  const selected = state.servers.some((server) => server.server_id === state.selectedServerId)
    ? state.selectedServerId
    : state.servers[0].server_id;
  state.selectedServerId = selected;

  select.innerHTML = state.servers.map((server) => `
    <option value="${server.server_id}" ${server.server_id === selected ? 'selected' : ''}>${server.name}</option>
  `).join('');
}

function renderCharts() {
  const serverId = state.selectedServerId;
  const history = state.history[serverId] || [];
  const labels = history.map((entry) => new Date(entry.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));

  const configs = [
    { id: 'cpuChart', key: 'cpu_usage', label: 'CPU Usage (%)', color: '#4f9cff' },
    { id: 'memoryChart', key: 'memory_usage', label: 'Memory Usage (%)', color: '#4ade80' },
    { id: 'diskChart', key: 'disk_usage', label: 'Disk Usage (%)', color: '#fbbf24' },
    { id: 'networkChart', key: 'network_usage', label: 'Network Usage (%)', color: '#f472b6' },
    { id: 'healthChart', key: 'health_score', label: 'Health Score', color: '#a78bfa' }
  ];

  configs.forEach(({ id, key, label, color }) => {
    const canvas = document.getElementById(id);
    const dataset = history.map((entry) => Number(entry[key] || 0));

    if (state.charts[id]) {
      state.charts[id].data.labels = labels;
      state.charts[id].data.datasets[0].data = dataset;
      state.charts[id].data.datasets[0].label = label;
      state.charts[id].data.datasets[0].borderColor = color;
      state.charts[id].data.datasets[0].backgroundColor = color + '33';
      state.charts[id].update();
      return;
    }

    state.charts[id] = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label,
          data: dataset,
          borderColor: color,
          backgroundColor: color + '33',
          pointRadius: 2,
          tension: 0.25,
          fill: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: false,
            suggestedMin: 0,
            suggestedMax: 100
          }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  });
}
