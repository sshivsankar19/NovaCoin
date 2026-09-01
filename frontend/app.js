(() => {
  "use strict";

  const API_BASE = window.MINING_API_BASE || "http://127.0.0.1:5000";
  const PAGE_SIZE = 25;
  const page = document.body.dataset.page;
  const state = {
    chain: null,
    mempool: null,
    pools: [],
    poolId: null,
    pool: null,
    monitoring: null,
    analytics: null,
    miners: [],
    jobs: [],
    shares: [],
    payouts: [],
    miningPoolId: null,
    miningPool: null,
    miningMiners: [],
    miningJobs: null,
    miningShares: null,
    miningPayouts: null,
    miningPoolQueryInvalid: false,
  };

  const $ = (id) => document.getElementById(id);

  if (page === "mining") {
    const queryValue = new URLSearchParams(window.location.search).get("pool_id");
    if (queryValue !== null) {
      const parsedPoolId = Number(queryValue);
      if (Number.isInteger(parsedPoolId) && parsedPoolId > 0) {
        state.miningPoolId = parsedPoolId;
      } else {
        state.miningPoolQueryInvalid = true;
      }
    }
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[character]));
  }

  function valueOrUnavailable(value) {
    return value === null || value === undefined || value === ""
      ? "Not available"
      : value;
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === "") {
      return "Not available";
    }
    return new Intl.NumberFormat().format(value);
  }

  function formatTime(value) {
    if (!value) {
      return "Not available";
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  function shortHash(value) {
    if (!value) {
      return "Not available";
    }
    const text = String(value);
    return text.length > 22 ? `${text.slice(0, 10)}…${text.slice(-8)}` : text;
  }

  function copyButton(value, label) {
    if (!value) {
      return "Not available";
    }
    return `
      <span class="hash">
        <code title="${escapeHtml(value)}">${escapeHtml(shortHash(value))}</code>
        <button class="copy-button" type="button" data-copy="${escapeHtml(value)}"
          aria-label="${escapeHtml(label)}">copy</button>
      </span>
    `;
  }

  function badge(value) {
    const className = String(value || "unknown").toLowerCase();
    return `<span class="badge ${escapeHtml(className)}">${escapeHtml(valueOrUnavailable(value))}</span>`;
  }

  function showNotice(message) {
    if (!$("notice")) {
      return;
    }
    $("notice").textContent = message || "";
    $("notice").hidden = !message;
  }

  function setUpdated() {
    if ($("last-updated")) {
      $("last-updated").textContent = `Updated ${new Date().toLocaleTimeString()}`;
    }
  }

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });
    let body = null;
    try {
      body = await response.json();
    } catch (error) {
      if (response.ok) {
        throw new Error("API returned invalid JSON.");
      }
    }
    if (!response.ok) {
      throw new Error(body?.error || `API request failed (${response.status})`);
    }
    return body;
  }

  const api = {
    health: () => request("/health"),
    chain: () => request("/chain"),
    mempool: () => request("/mempool"),
    pool: (id) => request(`/pool/${id}`),
    pools: () => request("/pools"),
    monitoring: (id) => request(`/pool/${id}/monitoring?limit=${PAGE_SIZE}`),
    analytics: (id) => request(`/pool/${id}/analytics?page=1&page_size=${PAGE_SIZE}`),
    miners: (id) => request(`/pool/${id}/miners`),
    jobs: (id) => request(`/pool/${id}/jobs?page=1&page_size=${PAGE_SIZE}`),
    shares: (id) => request(`/pool/${id}/shares?page=1&page_size=${PAGE_SIZE}`),
    payouts: (id) => request(`/pool/${id}/payouts?page=1&page_size=${PAGE_SIZE}`),
    createPool: (payload) => request("/pool", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    wallet: (address) => request(`/wallet/${encodeURIComponent(address)}`),
    transaction: (txid) => request(`/transaction/${encodeURIComponent(txid)}`),
  };

  function tableRow(cells, searchText, status = "") {
    return `
      <tr data-search="${escapeHtml(searchText)}" data-status="${escapeHtml(status)}">
        ${cells.map((cell) => `<td>${cell === null || cell === undefined ? "Not available" : cell}</td>`).join("")}
      </tr>
    `;
  }

  function renderTable(containerId, items, headers, renderRow) {
    const container = $(containerId);
    if (!container) {
      return;
    }
    if (!items || items.length === 0) {
      container.innerHTML = `<p class="empty">No persisted records available.</p>`;
      return;
    }
    container.innerHTML = `
      <div class="table-wrap">
        <table>
          <thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead>
          <tbody>${items.map(renderRow).join("")}</tbody>
        </table>
      </div>
    `;
  }

  function renderBlockTable(blocks) {
    renderTable(
      "chain-blocks-table",
      blocks,
      ["Height", "Hash", "Previous hash", "Nonce", "Difficulty", "Transactions", "Timestamp"],
      (block) => {
        const height = block.index ?? block.height;
        const count = Array.isArray(block.transactions)
          ? block.transactions.length
          : "Not exposed by current API";
        return tableRow(
          [height, copyButton(block.hash, "Copy block hash"),
            copyButton(block.previous_hash, "Copy previous hash"), block.nonce,
            block.difficulty, count, formatTime(block.timestamp)],
          `${height} ${block.hash || ""} ${block.previous_hash || ""}`,
        );
      },
    );
  }

  function renderChainSummary() {
    const blocks = state.chain?.chain || [];
    const latest = blocks[blocks.length - 1] || {};
    const target = $("chain-summary");
    if (!target || !state.chain) {
      return;
    }
    target.className = "summary-strip";
    target.innerHTML = `
      <div class="summary-details">
        <div><strong>${escapeHtml(valueOrUnavailable(state.chain.name))}</strong><span>Network</span></div>
        <div><strong>${escapeHtml(valueOrUnavailable(state.chain.symbol))}</strong><span>Asset symbol</span></div>
        <div><strong>${escapeHtml(valueOrUnavailable(state.chain.algorithm))}</strong><span>Algorithm</span></div>
        <div><strong>${formatNumber(blocks.length)}</strong><span>Chain length</span></div>
      </div>
      <dl class="details summary-details-secondary">
        <dt>Latest block height</dt><dd>${valueOrUnavailable(latest.index)}</dd>
        <dt>Latest block hash</dt><dd>${copyButton(latest.hash, "Copy latest block hash")}</dd>
        <dt>Previous hash</dt><dd>${copyButton(latest.previous_hash, "Copy previous hash")}</dd>
        <dt>Nonce</dt><dd>${valueOrUnavailable(latest.nonce)}</dd>
        <dt>Timestamp</dt><dd>${escapeHtml(formatTime(latest.timestamp))}</dd>
        <dt>Chain status</dt><dd>Loaded from API</dd>
      </dl>
    `;
    renderBlockTable(blocks);
  }

  function renderDashboard() {
    const blocks = state.chain?.chain || [];
    const latest = blocks[blocks.length - 1] || {};
    const poolStats = state.pool?.statistics || {};
    const monitor = state.monitoring || {};
    const metrics = [
      ["Chain height", latest.index],
      ["Algorithm", state.chain?.algorithm],
      ["Difficulty", state.chain?.difficulty],
      ["Pending transactions", state.mempool?.count],
      ["Chain status", state.chain ? "Available" : "Not available"],
      ["Mempool status", state.mempool ? "Available" : "Not available"],
      ["Active miners", monitor.active_miner_count],
      ["Active jobs", monitor.active_job_count],
      ["Pool hashrate", monitor.hash_rate],
    ];
    if ($("dashboard-metrics")) {
      $("dashboard-metrics").innerHTML = metrics.map(([label, value]) => `
        <div class="metric"><span class="metric-label">${escapeHtml(label)}</span><strong class="metric-value">${escapeHtml(valueOrUnavailable(value))}</strong></div>
      `).join("");
    }
    if ($("dashboard-chain") && state.chain) {
      $("dashboard-chain").className = "panel-content";
      $("dashboard-chain-status").textContent = "Available";
      $("dashboard-chain").innerHTML = `
        <dl class="details">
          <dt>Latest height</dt><dd>${valueOrUnavailable(latest.index)}</dd>
          <dt>Latest hash</dt><dd>${copyButton(latest.hash, "Copy latest block hash")}</dd>
          <dt>Difficulty</dt><dd>${valueOrUnavailable(state.chain.difficulty)}</dd>
        </dl>
      `;
    }
    if ($("dashboard-mempool") && state.mempool) {
      $("dashboard-mempool").className = "panel-content";
      $("dashboard-mempool-status").textContent = "Available";
      $("dashboard-mempool").innerHTML = `
        <dl class="details">
          <dt>Pending transactions</dt><dd>${formatNumber(state.mempool.count)}</dd>
          <dt>Queue status</dt><dd>${state.mempool.count ? "Transactions waiting" : "Empty"}</dd>
        </dl>
      `;
    }
    if ($("dashboard-pool") && state.pool) {
      $("dashboard-pool").className = "panel-content";
      $("dashboard-pool").innerHTML = `
        <dl class="details">
          <dt>Pool</dt><dd>${escapeHtml(valueOrUnavailable(state.pool.pool?.name))}</dd>
          <dt>Active miners</dt><dd>${valueOrUnavailable(poolStats.online_miner_count)}</dd>
          <dt>Active jobs</dt><dd>${valueOrUnavailable(monitor.active_job_count)}</dd>
        </dl>
      `;
    }
  }

  function renderMiningProtocol() {
    const target = $("mining-protocol");
    if (!target) {
      return;
    }
    if (!state.chain) {
      target.innerHTML = "<dt>Status</dt><dd>Not available</dd>";
      return;
    }
    $("mining-protocol-title").textContent = `${state.chain.algorithm || "Proof-of-Work"} protocol`;
    target.innerHTML = [
      ["Algorithm", state.chain.algorithm],
      ["Difficulty", state.chain.difficulty],
      ["Block reward", state.chain.block_reward],
      ["Block time", state.chain.block_time],
      ["Current height", state.chain.chain?.[state.chain.chain.length - 1]?.index],
      ["Pending transactions", state.chain.pending_transactions?.length],
    ].map(([label, value]) => `<dt>${label}</dt><dd>${escapeHtml(valueOrUnavailable(value))}</dd>`).join("");
  }

  function renderMiningBlock() {
    const target = $("mining-block-state");
    const blocks = state.chain?.chain || [];
    const latest = blocks[blocks.length - 1];
    if (!target) {
      return;
    }
    if (!latest) {
      target.className = "panel-content empty";
      target.textContent = "No block data is available from the current API.";
      return;
    }
    const prefix = Number.isInteger(latest.difficulty)
      ? "0".repeat(Math.max(0, latest.difficulty))
      : null;
    target.className = "panel-content";
    target.innerHTML = `
      <dl class="details">
        <dt>Block height</dt><dd>${valueOrUnavailable(latest.index)}</dd>
        <dt>Block data</dt><dd>${Array.isArray(latest.transactions) ? `${latest.transactions.length} transaction(s)` : "Not exposed by current API"}</dd>
        <dt>Previous hash</dt><dd>${copyButton(latest.previous_hash, "Copy previous block hash")}</dd>
        <dt>Timestamp</dt><dd>${escapeHtml(formatTime(latest.timestamp))}</dd>
        <dt>Nonce</dt><dd>${valueOrUnavailable(latest.nonce)}</dd>
        <dt>Difficulty</dt><dd>${valueOrUnavailable(latest.difficulty)}</dd>
        <dt>Required hash prefix</dt><dd><code>${escapeHtml(valueOrUnavailable(prefix))}</code></dd>
        <dt>Resulting hash</dt><dd>${copyButton(latest.hash, "Copy resulting block hash")}</dd>
      </dl>
      <details class="raw-data">
        <summary>View serialized block data</summary>
        <pre>${escapeHtml(JSON.stringify(latest, null, 2))}</pre>
      </details>
    `;
  }

  function renderMiningWorkerStatus() {
    const target = $("mining-worker-status");
    if (!target) {
      return;
    }
    if (!state.miningPoolId) {
      target.className = "panel-content empty";
      target.textContent = "Worker status is pool-scoped. Supply a pool context to inspect persisted worker status.";
      return;
    }
    if (!state.miningMiners.length) {
      target.className = "panel-content empty";
      target.textContent = "No persisted workers are available for this pool.";
      return;
    }
    renderTable(
      "mining-worker-status",
      state.miningMiners,
      ["Miner", "Worker", "Status", "Hashrate", "Shares", "Last seen"],
      (miner) => tableRow(
        [miner.id, escapeHtml(valueOrUnavailable(miner.worker_name)),
          badge(miner.status), valueOrUnavailable(miner.hash_rate),
          formatNumber(miner.total_shares), escapeHtml(formatTime(miner.last_seen))],
        `${miner.id} ${miner.worker_name || ""} ${miner.status || ""}`,
        miner.status,
      ),
    );
  }

  function renderMiningHistory() {
    const poolId = state.miningPoolId;
    const context = $("mining-pool-context");
    if (!poolId) {
      if (context) {
        context.className = "panel-content empty";
        context.innerHTML = 'No pool context supplied. Open the <a href="pools.html">Pools page</a> to select a pool, then load Mining with <code>?pool_id=&lt;id&gt;</code> to inspect its records.';
      }
      return;
    }
    if (context && state.miningPool) {
      context.className = "panel-content";
      context.innerHTML = `
        <dl class="details">
          <dt>Pool</dt><dd>${escapeHtml(valueOrUnavailable(state.miningPool.pool?.name))}</dd>
          <dt>Pool ID</dt><dd>${valueOrUnavailable(state.miningPool.pool?.id)}</dd>
          <dt>Algorithm</dt><dd>${escapeHtml(valueOrUnavailable(state.miningPool.pool?.algorithm))}</dd>
        </dl>
      `;
    }
    renderMiningWorkerStatus();
    const datasets = [
      ["mining-jobs-table", state.miningJobs, "jobs", ["Job ID", "Miner / worker", "Block height", "Status", "Created", "Expires", "Completed"], (job) => {
        const miner = state.miningMiners.find((item) => item.id === job.miner_id);
        return tableRow(
          [job.id, `${job.miner_id} / ${escapeHtml(valueOrUnavailable(miner?.worker_name))}`,
            job.block_height, badge(job.status), formatTime(job.created_at),
            formatTime(job.expires_at), formatTime(job.completed_at)],
          `${job.id} ${job.miner_id} ${miner?.worker_name || ""} ${job.block_height} ${job.status || ""}`,
          job.status,
        );
      }],
      ["mining-shares-table", state.miningShares, "shares", ["Share ID", "Miner", "Job", "Nonce", "Difficulty", "Status", "Timestamp"], (share) => tableRow(
        [share.id, share.miner_id, share.mining_job_id, share.nonce, share.difficulty,
          badge(share.status), formatTime(share.submitted_at)],
        `${share.id} ${share.miner_id} ${share.mining_job_id} ${share.nonce} ${share.status || ""}`,
        share.status,
      )],
      ["mining-payouts-table", state.miningPayouts, "payouts", ["Payout ID", "Miner", "Block", "Gross reward", "Pool fee", "Miner reward", "Status", "Timestamp"], (payout) => tableRow(
        [payout.id, payout.miner_id, payout.block_id, payout.gross_reward,
          payout.pool_fee, payout.miner_reward, badge(payout.status), formatTime(payout.created_at)],
        `${payout.id} ${payout.miner_id} ${payout.block_id} ${payout.status || ""}`,
        payout.status,
      )],
    ];
    datasets.forEach(([containerId, payload, key, headers, renderRow]) => {
      renderTable(containerId, payload?.[key] || [], headers, renderRow);
    });
  }

  async function loadMiningPoolRecords() {
    if (state.miningPoolQueryInvalid) {
      showNotice("The mining pool context must be a positive integer.");
      renderMiningHistory();
      return;
    }
    if (!state.miningPoolId) {
      renderMiningHistory();
      return;
    }
    const context = $("mining-pool-context");
    if (context) {
      context.textContent = "Loading pool-scoped mining records…";
    }
    try {
      state.miningPool = await api.pool(state.miningPoolId);
      const [miners, jobs, shares, payouts] = await Promise.all([
        api.miners(state.miningPoolId),
        api.jobs(state.miningPoolId),
        api.shares(state.miningPoolId),
        api.payouts(state.miningPoolId),
      ]);
      state.miningMiners = miners.miners || [];
      state.miningJobs = jobs;
      state.miningShares = shares;
      state.miningPayouts = payouts;
      renderMiningHistory();
      setUpdated();
    } catch (error) {
      state.miningPool = null;
      state.miningMiners = [];
      state.miningJobs = null;
      state.miningShares = null;
      state.miningPayouts = null;
      if (context) {
        context.className = "panel-content empty";
        context.textContent = "Pool-scoped mining records are unavailable.";
      }
      showNotice(error.message);
    }
  }

  function renderMempool() {
    const target = $("mempool-result");
    if (!target || !state.mempool) {
      return;
    }
    target.className = "panel";
    target.innerHTML = `
      <dl class="details">
        <dt>Pending count</dt><dd>${formatNumber(state.mempool.count)}</dd>
        <dt>Transactions</dt><dd>${state.mempool.transactions?.length ? "Available" : "None"}</dd>
      </dl>
      ${state.mempool.transactions?.length ? `<pre>${escapeHtml(JSON.stringify(state.mempool.transactions, null, 2))}</pre>` : ""}
    `;
  }

  function renderWorkers() {
    renderTable("workers-table", state.miners,
      ["Miner ID", "Worker", "Wallet", "Status", "Hashrate", "Shares", "Accepted", "Rejected", "Blocks", "Earned", "Last seen"],
      (miner) => tableRow(
        [miner.id, escapeHtml(valueOrUnavailable(miner.worker_name)),
          copyButton(miner.wallet_address, "Copy wallet address"), badge(miner.status),
          valueOrUnavailable(miner.hash_rate), formatNumber(miner.total_shares),
          formatNumber(miner.accepted_shares), formatNumber(miner.rejected_shares),
          formatNumber(miner.blocks_found), valueOrUnavailable(miner.total_earned),
          escapeHtml(formatTime(miner.last_seen))],
        `${miner.id} ${miner.worker_name || ""} ${miner.wallet_address || ""} ${miner.status || ""}`,
        miner.status,
      ),
    );
  }

  function renderJobs() {
    renderTable("jobs-table", state.jobs,
      ["Job ID", "Miner", "Height", "Difficulty", "Share difficulty", "Share target", "Network target", "Status", "Created", "Expires", "Completed"],
      (job) => tableRow(
        [job.id, job.miner_id, job.block_height, job.difficulty, job.share_difficulty,
          copyButton(job.share_target, "Copy share target"), copyButton(job.target, "Copy network target"),
          badge(job.status), formatTime(job.created_at), formatTime(job.expires_at), formatTime(job.completed_at)],
        `${job.id} ${job.miner_id} ${job.status || ""} ${job.share_target || ""}`,
        job.status,
      ),
    );
  }

  function renderShares() {
    renderTable("shares-table", state.shares,
      ["Share ID", "Miner", "Job", "Nonce", "Hash", "Difficulty", "Status", "Timestamp"],
      (share) => tableRow(
        [share.id, share.miner_id, share.mining_job_id, share.nonce,
          copyButton(share.hash, "Copy share hash"), share.difficulty, badge(share.status),
          formatTime(share.submitted_at)],
        `${share.id} ${share.miner_id} ${share.mining_job_id} ${share.status || ""} ${share.hash || ""}`,
        share.status,
      ),
    );
  }

  function renderPayouts() {
    renderTable("payouts-table", state.payouts,
      ["Payout ID", "Miner", "Block", "Gross reward", "Pool fee", "Miner reward", "Status", "Timestamp"],
      (payout) => tableRow(
        [payout.id, payout.miner_id, payout.block_id, payout.gross_reward,
          payout.pool_fee, payout.miner_reward, badge(payout.status), formatTime(payout.created_at)],
        `${payout.id} ${payout.miner_id} ${payout.block_id} ${payout.status || ""}`,
        payout.status,
      ),
    );
  }

  function formatPercent(value) {
    return value === null || value === undefined
      ? "Not available"
      : `${(Number(value) * 100).toFixed(2)}%`;
  }

  function renderPoolMetrics() {
    const target = $("pool-metrics");
    if (!target || !state.pool) {
      return;
    }

    function renderPoolDirectory() {
      const target = $("pool-directory");
      if (!target) {
        return;
      }
      if (!state.pools.length) {
        target.innerHTML = `
          <p class="empty">No mining pools have been created yet.</p>
          <p class="muted">Create a pool below to make it available here.</p>
        `;
        return;
      }
      target.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Name</th><th>Blockchain</th><th>Algorithm</th><th>Fee</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>
              ${state.pools.map((pool) => `
                <tr>
                  <td>${escapeHtml(pool.id)}</td>
                  <td>${escapeHtml(valueOrUnavailable(pool.name))}</td>
                  <td>${escapeHtml(valueOrUnavailable(pool.blockchain_id))}</td>
                  <td>${escapeHtml(valueOrUnavailable(pool.algorithm))}</td>
                  <td>${escapeHtml(valueOrUnavailable(pool.fee_percent))}%</td>
                  <td>${badge(pool.is_active ? "active" : "inactive")}</td>
                  <td><button class="text-button" type="button" data-pool-select="${escapeHtml(pool.id)}">Select</button></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      `;
    }
    const stats = state.pool.statistics || {};
    const analytics = state.analytics?.statistics || {};
    const jobs = stats.job_counts || analytics.job_counts || {};
    const metrics = [
      ["Total miners", stats.miner_count],
      ["Online miners", stats.online_miner_count],
      ["Offline miners", stats.offline_miner_count],
      ["Hashrate", stats.total_hash_rate ?? stats.hash_rate],
      ["Active jobs", stats.active_job_count ?? jobs.active],
      ["Completed jobs", stats.completed_job_count ?? jobs.completed],
      ["Stale jobs", stats.stale_job_count ?? jobs.stale],
      ["Expired jobs", stats.expired_job_count ?? jobs.expired],
      ["Total shares", stats.total_shares],
      ["Accepted shares", stats.accepted_shares],
      ["Rejected shares", stats.rejected_shares],
      ["Acceptance rate", formatPercent(stats.acceptance_rate)],
      ["Blocks found", stats.blocks_found],
      ["Gross rewards", stats.total_gross_rewards],
      ["Pool fees", stats.total_pool_fees],
      ["Miner rewards", stats.total_miner_rewards],
    ];
    target.innerHTML = metrics.map(([label, value]) => `
      <div class="metric">
        <span class="metric-label">${escapeHtml(label)}</span>
        <strong class="metric-value">${escapeHtml(valueOrUnavailable(value))}</strong>
      </div>
    `).join("");
  }

  function renderRecentBlocks() {
    const blocks = state.monitoring?.recent_blocks || [];
    renderTable(
      "recent-blocks-table",
      blocks,
      ["Block ID", "Height", "Hash", "Previous hash", "Nonce", "Difficulty", "Timestamp"],
      (block) => tableRow(
        [block.id, block.height, copyButton(block.hash, "Copy block hash"),
          copyButton(block.previous_hash, "Copy previous hash"), block.nonce,
          block.difficulty, formatTime(block.timestamp)],
        `${block.id} ${block.height} ${block.hash || ""} ${block.previous_hash || ""}`,
      ),
    );
  }

  function renderAnalyticsSummary() {
    const target = $("analytics-summary");
    if (!target || !state.analytics) {
      return;
    }
    const stats = state.analytics.statistics || {};
    const jobs = stats.job_counts || {};
    target.className = "panel-content";
    target.innerHTML = `
      <dl class="details">
        <dt>Samples</dt><dd>${valueOrUnavailable(stats.sample_count)}</dd>
        <dt>Average hashrate</dt><dd>${valueOrUnavailable(stats.average_hash_rate)}</dd>
        <dt>Acceptance rate</dt><dd>${formatPercent(stats.share_acceptance_rate ?? stats.acceptance_rate)}</dd>
        <dt>Online / offline</dt><dd>${valueOrUnavailable(stats.online_miner_count)} / ${valueOrUnavailable(stats.offline_miner_count)}</dd>
        <dt>Active / completed jobs</dt><dd>${valueOrUnavailable(jobs.active)} / ${valueOrUnavailable(jobs.completed)}</dd>
        <dt>Stale / expired jobs</dt><dd>${valueOrUnavailable(jobs.stale)} / ${valueOrUnavailable(jobs.expired)}</dd>
      </dl>
    `;
  }

  function renderAnalyticsHistory() {
    const history = state.analytics?.history || [];
    renderTable(
      "analytics-history-table",
      history,
      ["Recorded", "Miners", "Online", "Hashrate", "Shares", "Accepted", "Rate", "Active jobs", "Blocks"],
      (snapshot) => tableRow(
        [formatTime(snapshot.recorded_at), snapshot.miner_count,
          snapshot.online_miner_count, snapshot.total_hash_rate,
          snapshot.total_shares, snapshot.accepted_shares,
          formatPercent(snapshot.acceptance_rate), snapshot.active_job_count,
          snapshot.blocks_found],
        `${snapshot.recorded_at} ${snapshot.miner_count} ${snapshot.active_job_count}`,
      ),
    );
  }

  function renderPool() {
    if (!state.pool || !state.monitoring || !state.analytics) {
      return;
    }
    const pool = state.pool.pool;
    const stats = state.pool.statistics || {};
    const monitor = state.monitoring;
    const totals = monitor.payout_totals || {};
    $("pool-identity").className = "summary-strip";
    $("pool-identity").innerHTML = `
      <div class="summary-details">
        <div><strong>${escapeHtml(valueOrUnavailable(pool.name))}</strong><span>Pool</span></div>
        <div><strong>#${escapeHtml(valueOrUnavailable(pool.id))}</strong><span>Pool ID</span></div>
        <div><strong>${escapeHtml(valueOrUnavailable(pool.symbol))}</strong><span>Asset</span></div>
        <div><strong>${escapeHtml(valueOrUnavailable(pool.algorithm))}</strong><span>Algorithm</span></div>
      </div>
    `;
    renderPoolMetrics();
    renderAnalyticsSummary();
    $("monitoring-summary").className = "panel-content";
    $("monitoring-summary").innerHTML = `
      <dl class="details">
        <dt>Pool status</dt><dd>${pool.is_active ? "Active" : "Inactive"}</dd>
        <dt>Blockchain ID</dt><dd>${valueOrUnavailable(pool.blockchain_id)}</dd>
        <dt>Fee</dt><dd>${escapeHtml(valueOrUnavailable(pool.fee_percent))}%</dd>
        <dt>Created</dt><dd>${escapeHtml(formatTime(pool.created_at))}</dd>
        <dt>Chain height</dt><dd>${valueOrUnavailable(monitor.current_chain_height ?? monitor.chain_height)}</dd>
        <dt>Active miners</dt><dd>${valueOrUnavailable(monitor.active_miner_count)}</dd>
        <dt>Active jobs</dt><dd>${valueOrUnavailable(monitor.active_job_count)}</dd>
        <dt>Estimated hashrate</dt><dd>${valueOrUnavailable(monitor.hash_rate ?? monitor.hashrate)}</dd>
        <dt>Recent shares</dt><dd>${formatNumber((monitor.recent_shares || []).length)}</dd>
        <dt>Recent blocks</dt><dd>${formatNumber((monitor.recent_blocks || []).length)}</dd>
      </dl>
    `;
    $("payout-summary").className = "panel-content";
    $("payout-summary").innerHTML = `
      <dl class="details">
        <dt>Blocks found</dt><dd>${valueOrUnavailable(totals.blocks_found)}</dd>
        <dt>Gross rewards</dt><dd>${valueOrUnavailable(totals.gross_rewards)}</dd>
        <dt>Pool fees</dt><dd>${valueOrUnavailable(totals.pool_fees)}</dd>
        <dt>Miner rewards</dt><dd>${valueOrUnavailable(totals.miner_rewards)}</dd>
        <dt>Total shares</dt><dd>${valueOrUnavailable(stats.total_shares)}</dd>
        <dt>Accepted / rejected</dt><dd>${valueOrUnavailable(stats.accepted_shares)} / ${valueOrUnavailable(stats.rejected_shares)}</dd>
      </dl>
    `;
    renderRecentBlocks();
    renderAnalyticsHistory();
    renderWorkers();
    renderJobs();
    renderShares();
    renderPayouts();
  }

  async function loadChain() {
    const target = $("chain-summary");
    if (target) {
      target.textContent = "Loading blockchain state…";
    }
    try {
      state.chain = await api.chain();
      renderChainSummary();
      renderMiningProtocol();
      renderMiningBlock();
      renderDashboard();
      setUpdated();
    } catch (error) {
      if (target) {
        target.textContent = "Blockchain data unavailable.";
      }
      if ($("mining-protocol")) {
        $("mining-protocol-title").textContent = "Protocol unavailable";
        $("mining-protocol").innerHTML = "<dt>Status</dt><dd>Not available</dd>";
      }
      if ($("mining-block-state")) {
        $("mining-block-state").textContent = "Latest block data unavailable.";
      }
      showNotice(error.message);
    }
  }

  async function loadMempool() {
    const target = $("mempool-result");
    if (target) {
      target.textContent = "Loading mempool state…";
    }
    try {
      state.mempool = await api.mempool();
      renderMempool();
      renderDashboard();
    } catch (error) {
      if (target) {
        target.textContent = "Mempool data unavailable.";
      }
      showNotice(error.message);
    }
  }

  async function loadPools() {
    const target = $("pool-directory");
    if (target) {
      target.innerHTML = '<p class="empty">Loading available pools…</p>';
    }
    try {
      const response = await api.pools();
      state.pools = response.pools || [];
      renderPoolDirectory();
    } catch (error) {
      state.pools = [];
      if (target) {
        target.innerHTML = `<p class="empty">Pool directory unavailable.</p>`;
      }
      showNotice(error.message);
    }
  }

  async function loadPool() {
    if (!state.poolId) {
      showNotice("Enter a pool ID before loading pool operations.");
      return;
    }
    showNotice("");
    $("pool-identity").textContent = "Loading pool operations…";
    try {
      const [pool, monitoring, analytics, miners, jobs, shares, payouts] = await Promise.all([
        api.pool(state.poolId),
        api.monitoring(state.poolId),
        api.analytics(state.poolId),
        api.miners(state.poolId),
        api.jobs(state.poolId),
        api.shares(state.poolId),
        api.payouts(state.poolId),
      ]);
      state.pool = pool;
      state.monitoring = monitoring;
      state.analytics = analytics;
      state.miners = miners.miners || [];
      state.jobs = jobs.jobs || [];
      state.shares = shares.shares || [];
      state.payouts = payouts.payouts || [];
      renderPool();
      renderDashboard();
      setUpdated();
    } catch (error) {
      state.pool = null;
      state.monitoring = null;
      state.analytics = null;
      state.miners = [];
      state.jobs = [];
      state.shares = [];
      state.payouts = [];
      $("pool-identity").textContent = "Pool data unavailable.";
      $("pool-metrics").innerHTML = '<p class="empty">No pool statistics available.</p>';
      $("monitoring-summary").innerHTML = '<p class="empty">No monitoring data available.</p>';
      $("analytics-summary").innerHTML = '<p class="empty">No analytics data available.</p>';
      $("payout-summary").innerHTML = '<p class="empty">No payout data available.</p>';
      renderRecentBlocks();
      renderAnalyticsHistory();
      renderWorkers();
      renderJobs();
      renderShares();
      renderPayouts();
      showNotice(error.message);
    }
  }

  async function createPool(event) {
    event.preventDefault();
    const blockchainId = Number($("pool-blockchain-id").value);
    const name = $("pool-name").value.trim();
    const fee = Number($("pool-fee").value);
    if (!Number.isInteger(blockchainId) || blockchainId <= 0) {
      showNotice("Blockchain ID must be a positive integer.");
      return;
    }
    if (!Number.isFinite(fee) || fee < 0 || fee > 100) {
      showNotice("Pool fee must be between 0 and 100.");
      return;
    }
    showNotice("");
    $("create-pool-result").textContent = "Creating pool…";
    try {
      const response = await api.createPool({
        blockchain_id: blockchainId,
        ...(name ? { name } : {}),
        fee_percent: fee,
      });
      const pool = response.pool;
      $("create-pool-result").textContent = `Created pool #${pool.id}.`;
      $("pool-id").value = pool.id;
      state.poolId = pool.id;
      await loadPools();
      await loadPool();
    } catch (error) {
      $("create-pool-result").textContent = "Pool was not created.";
      showNotice(error.message);
    }
  }

  async function lookupWallet(event) {
    event.preventDefault();
    const address = $("wallet-address").value.trim();
    if (!address) {
      showNotice("Enter a wallet address.");
      return;
    }
    $("wallet-result").textContent = "Loading wallet…";
    try {
      const wallet = await api.wallet(address);
      $("wallet-result").className = "result";
      $("wallet-result").innerHTML = `
        <dl class="details">
          <dt>Address</dt><dd>${copyButton(wallet.address, "Copy wallet address")}</dd>
          <dt>Balance</dt><dd>${escapeHtml(valueOrUnavailable(wallet.balance))}</dd>
        </dl>
      `;
    } catch (error) {
      $("wallet-result").textContent = "Wallet data unavailable.";
      showNotice(error.message);
    }
  }

  async function lookupTransaction(event) {
    event.preventDefault();
    const txid = $("txid").value.trim();
    if (!txid) {
      showNotice("Enter a transaction ID.");
      return;
    }
    $("transaction-result").textContent = "Loading transaction…";
    try {
      const transaction = await api.transaction(txid);
      $("transaction-result").className = "result";
      $("transaction-result").innerHTML = `
        <dl class="details">
          <dt>Transaction ID</dt><dd>${copyButton(transaction.txid, "Copy transaction ID")}</dd>
          <dt>Sender</dt><dd>${copyButton(transaction.sender, "Copy sender address")}</dd>
          <dt>Receiver</dt><dd>${copyButton(transaction.receiver, "Copy receiver address")}</dd>
          <dt>Amount</dt><dd>${escapeHtml(valueOrUnavailable(transaction.amount))}</dd>
          <dt>Timestamp</dt><dd>${escapeHtml(formatTime(transaction.timestamp))}</dd>
          <dt>Status</dt><dd>${transaction.confirmed === true ? "Confirmed" : transaction.confirmed === false ? "Pending" : "Not exposed by current API"}</dd>
        </dl>
        <details class="raw-data"><summary>View API response</summary><pre>${escapeHtml(JSON.stringify(transaction, null, 2))}</pre></details>
      `;
    } catch (error) {
      $("transaction-result").textContent = "Transaction data unavailable.";
      showNotice(error.message);
    }
  }

  function applyTableFilters() {
    document.querySelectorAll("[data-table-filter], [data-table-status]").forEach((control) => {
      const containerId = control.dataset.tableFilter || control.dataset.tableStatus;
      const table = document.getElementById(containerId)?.querySelector("table");
      if (!table) {
        return;
      }
      const filter = document.querySelector(`[data-table-filter="${containerId}"]`);
      const status = document.querySelector(`[data-table-status="${containerId}"]`);
      const search = (filter?.value || "").toLowerCase();
      const selectedStatus = (status?.value || "").toLowerCase();
      table.querySelectorAll("tbody tr").forEach((row) => {
        row.hidden = Boolean(
          (search && !row.dataset.search.toLowerCase().includes(search))
          || (selectedStatus && row.dataset.status !== selectedStatus),
        );
      });
    });
  }

  function bindCommonEvents() {
    $("menu-button").addEventListener("click", () => {
      const open = $("main-navigation").classList.toggle("open");
      $("menu-button").setAttribute("aria-expanded", String(open));
    });
    $("main-navigation").addEventListener("click", (event) => {
      if (event.target.matches("a")) {
        $("main-navigation").classList.remove("open");
        $("menu-button").setAttribute("aria-expanded", "false");
      }
    });
    document.addEventListener("input", (event) => {
      if (event.target.matches("[data-table-filter]")) {
        applyTableFilters();
      }
    });
    document.addEventListener("change", (event) => {
      if (event.target.matches("[data-table-status]")) {
        applyTableFilters();
      }
    });
    document.addEventListener("click", async (event) => {
      const poolButton = event.target.closest("[data-pool-select]");
      if (poolButton) {
        state.poolId = Number(poolButton.dataset.poolSelect);
        $("pool-id").value = state.poolId;
        await loadPool();
        return;
      }
      const button = event.target.closest("[data-copy]");
      if (!button) {
        return;
      }
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        button.textContent = "copied";
        window.setTimeout(() => {
          button.textContent = "copy";
        }, 1200);
      } catch (error) {
        showNotice("Clipboard access is unavailable.");
      }
    });
  }

  function bindPageEvents() {
    if (page === "dashboard") {
      $("refresh-dashboard").addEventListener("click", () => {
        loadChain();
        loadMempool();
      });
    }
    if (page === "blockchain") {
      $("load-chain").addEventListener("click", loadChain);
      $("load-mempool").addEventListener("click", loadMempool);
    }
    if (page === "pools") {
      $("pool-form").addEventListener("submit", (event) => {
        event.preventDefault();
        const id = Number($("pool-id").value);
        if (!Number.isInteger(id) || id <= 0) {
          showNotice("Pool ID must be a positive integer.");
          return;
        }
        state.poolId = id;
        loadPool();
      });
      $("refresh-pool").addEventListener("click", loadPool);
      $("create-pool-form").addEventListener("submit", createPool);
    }
    if (page === "transactions") {
      $("transaction-form").addEventListener("submit", lookupTransaction);
      $("load-mempool").addEventListener("click", loadMempool);
    }
    if (page === "wallet") {
      $("wallet-form").addEventListener("submit", lookupWallet);
    }
    if (page === "mining") {
      $("refresh-mining").addEventListener("click", () => {
        loadChain();
        loadMiningPoolRecords();
      });
    }
  }

  function loadPageData() {
    if (page === "dashboard") {
      loadChain();
      loadMempool();
    } else if (page === "blockchain") {
      loadChain();
      loadMempool();
    } else if (page === "mining") {
      loadChain();
      loadMiningPoolRecords();
    } else if (page === "pools") {
      loadPools();
      renderPoolDirectory();
      renderWorkers();
      renderJobs();
      renderShares();
      renderPayouts();
    } else if (page === "transactions") {
      loadMempool();
    }
  }

  document.querySelector(`[data-page-link="${page}"]`)?.classList.add("active");
  if ($("api-endpoint")) {
    $("api-endpoint").textContent = API_BASE;
  }
  bindCommonEvents();
  bindPageEvents();
  loadPageData();
  api.health().then(() => {
    $("health-indicator").className = "ok";
    $("health-label").textContent = "API healthy";
  }).catch(() => {
    $("health-indicator").className = "error";
    $("health-label").textContent = "API unavailable";
  });
})();
