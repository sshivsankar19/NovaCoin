(() => {
  "use strict";

  const isLocalHost = (
    window.location.hostname === "localhost"
    || window.location.hostname === "127.0.0.1"
  );
  const API_BASE = window.MINING_API_BASE || (
    isLocalHost
      ? "http://127.0.0.1:5000"
      : "https://novacoin-backend.onrender.com"
  );
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
    signedTransaction: null,
    miningPoolId: null,
    miningPool: null,
    miningMiners: [],
    miningJobs: null,
    miningShares: null,
    miningPayouts: null,
    miningPoolQueryInvalid: false,
    miningStatus: "idle",
    lastMinedBlock: null,
    web3Provider: null,
    web3Address: null,
    web3ChainId: null,
    web3Balance: null,
    web3Signature: null,
    hederaAnchor: null,
    selectedAnchorBlock: null,
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

  function getWeb3Provider() {
    return window.ethereum && typeof window.ethereum.request === "function"
      ? window.ethereum
      : null;
  }

  function web3NetworkLabel(chainId) {
    if (!chainId) {
      return "Not available";
    }
    const labels = {
      "0x1": "Ethereum Mainnet",
      "0x5": "Goerli",
      "0xaa36a7": "Sepolia",
      "0x89": "Polygon",
      "0x13881": "Polygon Mumbai",
      "0x128": "Hedera Testnet",
    };
    return `${labels[chainId.toLowerCase()] || "Unknown EVM network"} (${chainId})`;
  }

  function renderWeb3Wallet() {
    const status = $("web3-status");
    const details = $("web3-wallet-result");
    const connectButton = $("connect-metamask");
    const signButton = $("sign-web3-message");
    const switchButton = $("switch-hedera-network");
    if (!status || !details || !connectButton || !signButton) {
      const switchButton = $("switch-hedera-network");
      if (switchButton) {
        switchButton.disabled = !state.web3Address || state.web3ChainId?.toLowerCase() === "0x128";
      }
      renderHederaWalletStatus();
      return;
    }
    if (!state.web3Provider) {
      status.textContent = "MetaMask not detected. Install MetaMask to use the optional Web3 connection.";
      details.className = "result empty";
      details.textContent = "No MetaMask account connected.";
      connectButton.disabled = true;
      signButton.disabled = true;
      if (switchButton) switchButton.disabled = true;
      renderHederaWalletStatus();
      return;
    }
    connectButton.disabled = false;
    if (!state.web3Address) {
      status.textContent = "MetaMask available. Not connected.";
      details.className = "result empty";
      details.textContent = "Connect an EVM account to continue.";
      signButton.disabled = true;
      if (switchButton) switchButton.disabled = true;
      renderHederaWalletStatus();
      return;
    }
    status.textContent = "MetaMask connected. NovaCoin remains a separate native blockchain.";
    details.className = "result";
    details.innerHTML = `
      <dl class="details">
        <dt>EVM address</dt><dd>${copyButton(state.web3Address, "Copy MetaMask address")}</dd>
        <dt>EVM network</dt><dd>${escapeHtml(web3NetworkLabel(state.web3ChainId))}</dd>
        <dt>Chain ID</dt><dd>${escapeHtml(state.web3ChainId || "Not available")}</dd>
        ${state.web3Balance !== null ? `<dt>HBAR balance</dt><dd>${escapeHtml(state.web3Balance)} HBAR</dd>` : ""}
        <dt>Account use</dt><dd>Web3 message signing only</dd>
      </dl>
      ${state.web3Signature ? `
        <dl class="details">
          <dt>Test message</dt><dd>${escapeHtml(state.web3Signature.message)}</dd>
          <dt>Signature</dt><dd>${copyButton(state.web3Signature.signature, "Copy Web3 signature")}</dd>
        </dl>
      ` : ""}
    `;
    signButton.disabled = false;
    if (switchButton) switchButton.disabled = state.web3ChainId === "0x128";
    renderHederaWalletStatus();
  }

  function renderHederaWalletStatus() {
    const target = $("hedera-wallet-status");
    if (!target) return;
    const ready = Boolean(state.web3Address && state.web3ChainId?.toLowerCase() === "0x128" && hederaContractAddress());
    target.className = `result${ready ? "" : " empty"}`;
    target.innerHTML = ready
      ? `<strong>Hedera Testnet ready</strong><br>✓ Wallet connected<br>✓ Hedera Testnet selected<br>✓ NovaCoin Anchor contract configured${state.web3Balance !== null ? `<br>HBAR balance: ${escapeHtml(state.web3Balance)} HBAR` : ""}`
      : "Connect MetaMask and select Hedera Testnet to use the external NovaCoin anchor.";
  }

  async function refreshWeb3Account() {
    const accounts = await state.web3Provider.request({ method: "eth_accounts" });
    state.web3Address = accounts[0] || null;
    state.web3Signature = null;
    state.web3ChainId = state.web3Address
      ? await state.web3Provider.request({ method: "eth_chainId" })
      : null;
    state.web3Balance = null;
    if (state.web3Address && state.web3ChainId?.toLowerCase() === "0x128") {
      const raw = await state.web3Provider.request({ method: "eth_getBalance", params: [state.web3Address, "latest"] });
      state.web3Balance = Number(window.ethers?.formatEther(raw) || (Number(BigInt(raw)) / 1e18).toFixed(4)).toFixed(4);
    }
    renderWeb3Wallet();
  }

  async function switchToHedera() {
    if (!state.web3Provider) return;
    try {
      await state.web3Provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: "0x128" }] });
    } catch (error) {
      if (error.code !== 4902) {
        showNotice(error?.message || "Hedera network switch was not completed.");
        return;
      }
      try {
        await state.web3Provider.request({
          method: "wallet_addEthereumChain",
          params: [{
            chainId: "0x128",
            chainName: "Hedera Testnet",
            nativeCurrency: { name: "HBAR", symbol: "HBAR", decimals: 18 },
            rpcUrls: ["https://testnet.hashio.io/api"],
            blockExplorerUrls: ["https://hashscan.io/testnet"],
          }],
        });
      } catch (addError) {
        showNotice(addError?.message || "Hedera Testnet was not added.");
      }
    }
  }

  async function connectMetaMask() {
    if (!state.web3Provider) {
      renderWeb3Wallet();
      return;
    }
    $("web3-status").textContent = "Requesting MetaMask account access...";
    $("connect-metamask").disabled = true;
    try {
      const accounts = await state.web3Provider.request({ method: "eth_requestAccounts" });
      state.web3Address = accounts[0] || null;
      state.web3ChainId = await state.web3Provider.request({ method: "eth_chainId" });
      state.web3Balance = null;
      state.web3Signature = null;
      renderWeb3Wallet();
      if (!state.web3Address) {
        showNotice("MetaMask did not return an account.");
      }
    } catch (error) {
      renderWeb3Wallet();
      showNotice(error?.message || "MetaMask connection was not completed.");
    }
  }

  async function signWeb3TestMessage() {
    if (!state.web3Provider || !state.web3Address) {
      showNotice("Connect MetaMask before signing the Web3 test message.");
      return;
    }

    const message = "NovaCoin Web3 Integration Test";
    $("web3-signature-result").textContent = "Waiting for MetaMask signature approval...";
    $("sign-web3-message").disabled = true;
    try {
      const signature = await state.web3Provider.request({
        method: "personal_sign",
        params: [message, state.web3Address],
      });
      state.web3Signature = { message, signature };
      renderWeb3Wallet();
      $("web3-signature-result").textContent = "Message signed locally by MetaMask. It was not sent to NovaCoin.";
    } catch (error) {
      $("web3-signature-result").textContent = "Message was not signed.";
      showNotice(error?.message || "MetaMask message signing was not completed.");
      renderWeb3Wallet();
    }
  }

  function initializeWeb3Wallet() {
    state.web3Provider = getWeb3Provider();
    renderWeb3Wallet();
    if (!state.web3Provider) {
      return;
    }
    state.web3Provider.on?.("accountsChanged", (accounts) => {
      state.web3Address = accounts[0] || null;
      state.web3Signature = null;
      refreshWeb3Account().catch((error) => showNotice(error.message));
    });
    state.web3Provider.on?.("chainChanged", (chainId) => {
      state.web3ChainId = chainId;
      state.web3Signature = null;
      refreshWeb3Account().catch((error) => showNotice(error.message));
    });
    refreshWeb3Account().catch((error) => showNotice(error.message));
  }

  const HEDERA_ANCHOR_ABI = [
    "function anchorBlock(uint256 novaBlockIndex, bytes32 blockHash)",
    "function getAnchor(uint256 novaBlockIndex) view returns (uint256, bytes32, uint256, address)",
  ];

  function hederaContractAddress() {
    return window.NOVACOIN_HEDERA_CONTRACT_ADDRESS || "";
  }

  function validBlockHash(blockHash) {
    return typeof blockHash === "string" && /^[0-9a-fA-F]{64}$/.test(blockHash);
  }

  function renderHederaAnchor() {
    const target = $("hedera-anchor-result");
    const button = $("anchor-block");
    const verifyButton = $("verify-anchor");
    if (!target || !button || !verifyButton) {
      return;
    }
    if ($("hedera-contract-display")) {
      $("hedera-contract-display").textContent = hederaContractAddress() || "Not configured";
    }
    const block = state.selectedAnchorBlock || state.lastMinedBlock;
    button.disabled = !block || !validBlockHash(block.hash) || !state.web3Address || state.web3ChainId?.toLowerCase() !== "0x128";
    verifyButton.disabled = !block || !validBlockHash(block.hash) || !state.web3Address || state.web3ChainId?.toLowerCase() !== "0x128";
    if (!state.hederaAnchor) {
      target.className = "result empty";
      target.textContent = block
        ? "Not anchored. Connect MetaMask on Hedera Testnet to anchor the selected block."
        : "Select a real NovaCoin block before anchoring its hash.";
      return;
    }
    target.className = "result";
    target.innerHTML = state.hederaAnchor.html || escapeHtml(state.hederaAnchor.message);
  }

  function requireHederaRuntime() {
    if (!state.web3Provider) {
      throw new Error("Connect MetaMask on Hedera Testnet to anchor this block.");
    }
    if (state.web3ChainId?.toLowerCase() !== "0x128") {
      throw new Error("Switch MetaMask to Hedera Testnet.");
    }
    if (!window.ethers) {
      throw new Error("Hedera Web3 support is unavailable because the ethers library did not load.");
    }
    if (!hederaContractAddress()) {
      throw new Error("Hedera contract is not configured. Deploy NovaCoinAnchor and set the contract address.");
    }
    if (!(state.selectedAnchorBlock || state.lastMinedBlock) || !validBlockHash((state.selectedAnchorBlock || state.lastMinedBlock).hash)) {
      throw new Error("The selected NovaCoin block hash is not available or is invalid.");
    }
  }

  async function anchorBlockOnHedera() {
    const button = $("anchor-block");
    button.disabled = true;
    state.hederaAnchor = { message: "Submitting to Hedera Testnet..." };
    renderHederaAnchor();
    try {
      requireHederaRuntime();
      const provider = new window.ethers.BrowserProvider(state.web3Provider);
      const network = await provider.getNetwork();
      if (network.chainId !== 296n) {
        throw new Error("Switch MetaMask to Hedera Testnet.");
      }
      const signer = await provider.getSigner();
      const contract = new window.ethers.Contract(hederaContractAddress(), HEDERA_ANCHOR_ABI, signer);
      const block = state.selectedAnchorBlock || state.lastMinedBlock;
      const transaction = await contract.anchorBlock(block.index, `0x${block.hash}`);
      const receipt = await transaction.wait();
      const txHash = receipt.hash || transaction.hash;
      state.hederaAnchor = {
        message: "Anchored on Hedera Testnet.",
        html: `
          <dl class="details">
            <dt>NovaCoin block index</dt><dd>${escapeHtml(block.index)}</dd>
            <dt>NovaCoin block hash</dt><dd>${copyButton(block.hash, "Copy NovaCoin block hash")}</dd>
            <dt>Hedera transaction</dt><dd>${copyButton(txHash, "Copy Hedera transaction hash")}</dd>
            <dt>Contract</dt><dd>${copyButton(hederaContractAddress(), "Copy Hedera contract address")}</dd>
            <dt>Confirmation</dt><dd>Confirmed on Hedera Testnet</dd>
            <dt>Network</dt><dd>Hedera Testnet (chain ID 296)</dd>
          </dl>
          <a href="https://hashscan.io/testnet/transaction/${encodeURIComponent(txHash)}" target="_blank" rel="noopener">View transaction on HashScan</a>
        `,
      };
      showNotice("NovaCoin block hash anchored on Hedera Testnet.", false);
    } catch (error) {
      state.hederaAnchor = {
        message: error?.code === 4001 || error?.message?.toLowerCase().includes("user rejected")
          ? "Transaction rejected by user."
          : error?.message || "Hedera anchoring was not completed.",
      };
      showNotice(state.hederaAnchor.message);
    } finally {
      renderHederaAnchor();
    }
  }

  async function verifyAnchorOnHedera() {
    const target = $("hedera-verification-result");
    try {
      requireHederaRuntime();
      const provider = new window.ethers.BrowserProvider(state.web3Provider);
      const contract = new window.ethers.Contract(hederaContractAddress(), HEDERA_ANCHOR_ABI, provider);
      const block = state.selectedAnchorBlock || state.lastMinedBlock;
      const anchor = await contract.getAnchor(block.index);
      const nativeHash = `0x${block.hash}`.toLowerCase();
      const anchoredHash = String(anchor[1]).toLowerCase();
      const match = Number(anchor[0]) === Number(block.index) && nativeHash === anchoredHash;
      target.className = `result${match ? "" : " empty"}`;
      target.innerHTML = `
        <dl class="details">
          <dt>NovaCoin hash</dt><dd>${copyButton(nativeHash, "Copy NovaCoin hash")}</dd>
          <dt>Hedera anchored hash</dt><dd>${copyButton(anchoredHash, "Copy Hedera anchored hash")}</dd>
          <dt>Stored block index</dt><dd>${escapeHtml(anchor[0].toString())}</dd>
          <dt>Stored timestamp</dt><dd>${escapeHtml(new Date(Number(anchor[2]) * 1000).toLocaleString())}</dd>
          <dt>Submitter</dt><dd>${copyButton(String(anchor[3]), "Copy Hedera submitter")}</dd>
          <dt>Verification</dt><dd>${match ? "MATCH" : "MISMATCH"}</dd>
        </dl>
      `;
    } catch (error) {
      target.className = "result empty";
      target.textContent = error?.message || "Anchor verification was not completed.";
      showNotice(target.textContent);
    }
  }

  function renderAnchorBlockSelection() {
      const select = $("hedera-block-select");
      const target = $("hedera-selected-block");
      if (!select || !target) return;
      const blocks = state.chain?.chain || [];
      const minedBlocks = blocks.filter((block) => block.index > 0);
      select.innerHTML = minedBlocks.map((block) => `<option value="${block.index}">#${block.index} · ${shortHash(block.hash)}</option>`).join("") || "<option>No mined blocks available</option>";
      select.disabled = !minedBlocks.length;
      if (state.lastMinedBlock && minedBlocks.some((block) => block.index === state.lastMinedBlock.index)) {
        select.value = String(state.lastMinedBlock.index);
      }
      const selectedIndex = Number(select.value);
      state.selectedAnchorBlock = blocks.find((block) => block.index === selectedIndex) || state.lastMinedBlock || null;
      const block = state.selectedAnchorBlock;
      target.className = block ? "result" : "result empty";
      target.innerHTML = block ? `<dl class="details"><dt>Block index</dt><dd>${block.index}</dd><dt>Block hash</dt><dd>${copyButton(block.hash, "Copy selected NovaCoin block hash")}</dd><dt>Previous hash</dt><dd>${copyButton(block.previous_hash, "Copy previous hash")}</dd><dt>Timestamp</dt><dd>${escapeHtml(formatTime(block.timestamp))}</dd><dt>Transactions</dt><dd>${Array.isArray(block.transactions) ? block.transactions.length : "Not available"}</dd></dl>` : "Select a real block from the NovaCoin chain.";
      renderHederaAnchor();
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
    mine: (miner, signal) => request("/mine", {
      method: "POST",
      signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ miner }),
    }),
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
    createWallet: () => request("/wallet/new"),
    createTransaction: (payload) => request("/transaction/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    submitTransaction: (payload) => request("/transaction", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
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

  function renderMiningOperation() {
    const status = $("mine-status");
    const result = $("mine-result");
    if (!status || !result) {
      return;
    }
    if (state.miningStatus === "mining") {
      status.className = "result";
      status.textContent = "Mining… The real backend Proof-of-Work loop is running.";
      return;
    }
    if (state.miningStatus === "error") {
      status.className = "result empty";
      return;
    }
    if (state.miningStatus === "success" && state.lastMinedBlock) {
      const block = state.lastMinedBlock;
      status.className = "result";
      status.textContent = "Block mined successfully and persisted by the backend.";
      result.className = "result";
      result.innerHTML = `
        <dl class="details">
          <dt>Block index</dt><dd>${valueOrUnavailable(block.index)}</dd>
          <dt>Hash</dt><dd>${copyButton(block.hash, "Copy mined block hash")}</dd>
          <dt>Nonce</dt><dd>${valueOrUnavailable(block.nonce)}</dd>
          <dt>Previous hash</dt><dd>${copyButton(block.previous_hash, "Copy previous hash")}</dd>
          <dt>Transactions</dt><dd>${Array.isArray(block.transactions) ? block.transactions.length : "Not available"}</dd>
          <dt>Reward</dt><dd>${escapeHtml(valueOrUnavailable(block.transactions?.find((tx) => tx.sender === "SYSTEM")?.amount))} NVC</dd>
          <dt>Duration</dt><dd>${valueOrUnavailable(state.miningDuration)} ms</dd>
          <dt>Pending after mining</dt><dd>${valueOrUnavailable(state.mempool?.count)}</dd>
        </dl>
      `;
      return;
    }
    status.className = "result empty";
    status.textContent = "No mining request made.";
  }

  async function mineBlock(event) {
    event.preventDefault();
    const address = $("mine-address").value.trim();
    if (!address) {
      showNotice("Enter or generate a miner wallet address.");
      return;
    }
    const button = $("mine-button");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 120000);
    state.miningStatus = "mining";
    state.lastMinedBlock = null;
    renderMiningOperation();
    button.disabled = true;
    const startedAt = performance.now();
    try {
      const response = await api.mine(address, controller.signal);
      state.lastMinedBlock = response.block;
      state.hederaAnchor = null;
      state.miningDuration = Math.round(performance.now() - startedAt);
      state.miningStatus = "success";
      await loadChain();
      await loadMempool();
      renderMiningOperation();
      renderHederaAnchor();
      showNotice("Real backend mining completed.", false);
    } catch (error) {
      state.miningStatus = "error";
      renderMiningOperation();
      showNotice(error.name === "AbortError"
        ? "Mining timed out while waiting for the backend."
        : error.message);
    } finally {
      window.clearTimeout(timeout);
      button.disabled = false;
    }
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
      ${state.mempool.transactions?.length ? `
        <div class="table-wrap"><table>
          <thead><tr><th>TXID</th><th>Sender</th><th>Receiver</th><th>Amount</th><th>Status</th><th>Timestamp</th></tr></thead>
          <tbody>${state.mempool.transactions.map((transaction) => tableRow(
            [copyButton(transaction.txid, "Copy transaction ID"),
              copyButton(transaction.sender, "Copy sender address"),
              copyButton(transaction.receiver, "Copy receiver address"),
              escapeHtml(valueOrUnavailable(transaction.amount)),
              badge(transaction.status || "pending"),
              escapeHtml(formatTime(transaction.timestamp))],
            `${transaction.txid} ${transaction.sender} ${transaction.receiver} ${transaction.status || ""}`,
            transaction.status || "pending",
          )).join("")}</tbody>
        </table></div>` : ""}
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

  function renderPoolMetrics() {
    const target = $("pool-metrics");
    if (!target || !state.pool) {
      return;
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
      renderAnchorBlockSelection();
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
      renderMiningOperation();
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
      const pool = await api.pool(state.poolId);
      const monitoring = await api.monitoring(state.poolId);
      const analytics = await api.analytics(state.poolId);
      const miners = await api.miners(state.poolId);
      const jobs = await api.jobs(state.poolId);
      const shares = await api.shares(state.poolId);
      const payouts = await api.payouts(state.poolId);
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

  async function createWallet() {
    $("wallet-create-result").textContent = "Generating development wallet…";
    try {
      const wallet = await api.createWallet();
      $("wallet-address").value = wallet.address;
      window.sessionStorage.setItem("novacoin-development-address", wallet.address);
      $("wallet-create-result").className = "result";
      $("wallet-create-result").innerHTML = `
        <dl class="details">
          <dt>Address</dt><dd>${copyButton(wallet.address, "Copy wallet address")}</dd>
          <dt>Private key</dt><dd>Not returned by this API</dd>
        </dl>
      `;
      await lookupWallet({ preventDefault() {} });
    } catch (error) {
      $("wallet-create-result").textContent = "Wallet was not created.";
      showNotice(error.message);
    }
  }

  async function createSignedTransaction(event) {
    event.preventDefault();
    const sender = $("transaction-sender").value.trim();
    const receiver = $("transaction-receiver").value.trim();
    const amount = Number($("transaction-amount").value);
    if (!sender || !receiver) {
      showNotice("Sender and receiver addresses are required.");
      return;
    }
    if (!Number.isFinite(amount) || amount <= 0) {
      showNotice("Transaction amount must be positive.");
      return;
    }
    $("signed-transaction-result").textContent = "Signing transaction…";
    $("submit-transaction").disabled = true;
    try {
      state.signedTransaction = await api.createTransaction({ sender, receiver, amount });
      $("signed-transaction-result").className = "result";
      $("signed-transaction-result").innerHTML = `
        <dl class="details">
          <dt>Transaction ID</dt><dd>${copyButton(state.signedTransaction.txid, "Copy transaction ID")}</dd>
          <dt>Sender</dt><dd>${copyButton(state.signedTransaction.sender, "Copy sender address")}</dd>
          <dt>Receiver</dt><dd>${copyButton(state.signedTransaction.receiver, "Copy receiver address")}</dd>
          <dt>Amount</dt><dd>${escapeHtml(valueOrUnavailable(state.signedTransaction.amount))}</dd>
          <dt>Signature</dt><dd>Created by backend</dd>
        </dl>
      `;
      $("submit-transaction").disabled = false;
      showNotice("Transaction signed by the backend. Submit it to the real mempool.", false);
    } catch (error) {
      state.signedTransaction = null;
      $("signed-transaction-result").textContent = "Transaction was not signed.";
      showNotice(error.message);
    }
  }

  async function submitSignedTransaction() {
    if (!state.signedTransaction) {
      showNotice("Create and sign a transaction first.");
      return;
    }
    $("submit-transaction").disabled = true;
    try {
      const response = await api.submitTransaction(state.signedTransaction);
      $("submit-transaction-result").textContent = response.message || "Transaction submitted.";
      $("signed-transaction-result").textContent = "No unsigned transaction ready.";
      state.signedTransaction = null;
      await loadMempool();
      showNotice("Transaction submitted to the real backend mempool.", false);
    } catch (error) {
      $("submit-transaction-result").textContent = "Transaction was not submitted.";
      $("submit-transaction").disabled = false;
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
      const savedAddress = window.sessionStorage.getItem("novacoin-development-address");
      if (savedAddress) {
        $("transaction-sender").value = savedAddress;
      }
      $("transaction-form").addEventListener("submit", lookupTransaction);
      $("load-mempool").addEventListener("click", loadMempool);
      $("create-transaction-form").addEventListener("submit", createSignedTransaction);
      $("submit-transaction").addEventListener("click", submitSignedTransaction);
    }
    if (page === "wallet") {
      $("wallet-form").addEventListener("submit", lookupWallet);
      $("create-wallet").addEventListener("click", createWallet);
      $("connect-metamask").addEventListener("click", connectMetaMask);
      $("switch-hedera-network")?.addEventListener("click", switchToHedera);
      $("sign-web3-message").addEventListener("click", signWeb3TestMessage);
      initializeWeb3Wallet();
    }
    if (page === "mining") {
      initializeWeb3Wallet();
      const savedAddress = window.sessionStorage.getItem("novacoin-development-address");
      if (savedAddress) {
        $("mine-address").value = savedAddress;
      }
      $("mine-form").addEventListener("submit", mineBlock);
      $("anchor-block").addEventListener("click", anchorBlockOnHedera);
      $("verify-anchor").addEventListener("click", verifyAnchorOnHedera);
      $("hedera-block-select").addEventListener("change", renderAnchorBlockSelection);
      $("switch-hedera-network")?.addEventListener("click", switchToHedera);
      $("refresh-mining").addEventListener("click", () => {
        loadChain();
        loadMempool();
        loadMiningPoolRecords();
      });
      renderMiningOperation();
      renderHederaAnchor();
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
      loadMempool();
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
