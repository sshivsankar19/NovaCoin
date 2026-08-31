(() => {
  "use strict";

  const API_BASE = window.MINING_API_BASE || "http://127.0.0.1:5000";
  const PAGE_SIZE = 25;
  const page = document.body.dataset.page;
  const state = {
    chain: null,
    mempool: null,
    poolId: null,
    pool: null,
    monitoring: null,
    miners: [],
    jobs: [],
    shares: [],
    payouts: [],
  };

  const $ = (id) => document.getElementById(id);

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

  async function request(path) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
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
    monitoring: (id) => request(`/pool/${id}/monitoring?limit=${PAGE_SIZE}`),
    miners: (id) => request(`/pool/${id}/miners`),
    jobs: (id) => request(`/pool/${id}/jobs?page=1&page_size=${PAGE_SIZE}`),
    shares: (id) => request(`/pool/${id}/shares?page=1&page_size=${PAGE_SIZE}`),
    payouts: (id) => request(`/pool/${id}/payouts?page=1&page_size=${PAGE_SIZE}`),
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
    ].map(([label, value]) => `<dt>${label}</dt><dd>${escapeHtml(valueOrUnavailable(value))}</dd>`).join("");
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

  function renderPool() {
    if (!state.pool || !state.monitoring) {
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
    $("monitoring-summary").className = "panel-content";
    $("monitoring-summary").innerHTML = `
      <dl class="details">
        <dt>Pool status</dt><dd>${pool.is_active ? "Active" : "Inactive"}</dd>
        <dt>Chain height</dt><dd>${valueOrUnavailable(monitor.current_chain_height)}</dd>
        <dt>Active miners</dt><dd>${valueOrUnavailable(monitor.active_miner_count)}</dd>
        <dt>Active jobs</dt><dd>${valueOrUnavailable(monitor.active_job_count)}</dd>
        <dt>Hashrate</dt><dd>${valueOrUnavailable(monitor.hash_rate)}</dd>
        <dt>Acceptance rate</dt><dd>${stats.acceptance_rate === undefined ? "Not available" : `${(stats.acceptance_rate * 100).toFixed(2)}%`}</dd>
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
      renderDashboard();
      setUpdated();
    } catch (error) {
      if (target) {
        target.textContent = "Blockchain data unavailable.";
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

  async function loadPool() {
    if (!state.poolId) {
      showNotice("Enter a pool ID before loading pool operations.");
      return;
    }
    showNotice("");
    $("pool-identity").textContent = "Loading pool operations…";
    try {
      const [pool, monitoring, miners, jobs, shares, payouts] = await Promise.all([
        api.pool(state.poolId),
        api.monitoring(state.poolId),
        api.miners(state.poolId),
        api.jobs(state.poolId),
        api.shares(state.poolId),
        api.payouts(state.poolId),
      ]);
      state.pool = pool;
      state.monitoring = monitoring;
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
      $("pool-identity").textContent = "Pool data unavailable.";
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
    }
    if (page === "transactions") {
      $("transaction-form").addEventListener("submit", lookupTransaction);
      $("load-mempool").addEventListener("click", loadMempool);
    }
    if (page === "wallet") {
      $("wallet-form").addEventListener("submit", lookupWallet);
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
    } else if (page === "pools") {
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
