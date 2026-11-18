/**
 * Net-Proxy-Tool Web Console v3.0
 * Progressive Guided Flow, Dynamic Node & Gateway CRUD, Sandbox Terminal & Zero Pollution.
 */
document.addEventListener("DOMContentLoaded", () => {
  let appConfig = null;
  let activeGateway = null;
  let selectedWizardClient = null;
  let selectedWizardGateway = null;

  // Wizard state flags
  let step1Complete = false;
  let step2Complete = false;
  let step3Complete = false;
  let wizardProbeRevision = 0;

  // Global DOM Elements
  const tabButtons = document.querySelectorAll(".nav-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const globalStatusText = document.getElementById("global-gw-status-text");
  const globalStatusPill = document.getElementById("global-status-pill");
  const footerGwLabel = document.getElementById("footer-gw-label");

  // Wizard Elements
  const pipeStep1 = document.getElementById("pipe-step-1");
  const pipeStep2 = document.getElementById("pipe-step-2");
  const pipeStep3 = document.getElementById("pipe-step-3");
  const pipeStep4 = document.getElementById("pipe-step-4");

  const cardStep2 = document.getElementById("card-step-2");
  const cardStep3 = document.getElementById("card-step-3");
  const cardStep4 = document.getElementById("card-step-4");

  const statusTagStep1 = document.getElementById("status-tag-step-1");
  const statusTagStep2 = document.getElementById("status-tag-step-2");
  const statusTagStep3 = document.getElementById("status-tag-step-3");
  const statusTagStep4 = document.getElementById("status-tag-step-4");

  const wizardGwSelect = document.getElementById("wizard-gw-select");
  const wizardTestUrl = document.getElementById("wizard-test-url");
  const wizardTestGwBtn = document.getElementById("wizard-test-gw-btn");
  const wizardSetDefaultGwBtn = document.getElementById("wizard-set-default-gw-btn");
  const step1Result = document.getElementById("step-1-result");
  const wizardProbeActions = document.getElementById("wizard-probe-actions");
  const readOnlyNode = document.getElementById("wizard-readonly-node");
  const readOnlyTest = document.getElementById("wizard-readonly-test");
  const readOnlyOutput = document.getElementById("wizard-readonly-output");

  const wizardClientSelect = document.getElementById("wizard-client-select");
  const wizardOpenAddClientBtn = document.getElementById("wizard-open-add-client-btn");
  const wizardConfirmClientBtn = document.getElementById("wizard-confirm-client-btn");
  const wMetaHost = document.getElementById("w-meta-host");
  const wMetaOs = document.getElementById("w-meta-os");
  const wMetaGw = document.getElementById("w-meta-gw");
  const wMetaTags = document.getElementById("w-meta-tags");

  const wizardStartDiagBtn = document.getElementById("wizard-start-diag-btn");
  const wizardDiagTime = document.getElementById("wizard-diag-time");
  const wizardTargetGrid = document.getElementById("wizard-target-grid");

  const handoverTargetName = document.getElementById("handover-target-name");
  const handoverGwName = document.getElementById("handover-gw-name");
  const handoverBlocksContainer = document.getElementById("handover-blocks-container");
  const wizardTargetDispName = document.getElementById("wizard-target-disp-name");
  const wizardTargetDispSub = document.getElementById("wizard-target-disp-sub");
  const wizardBtnProxyOn = document.getElementById("wizard-btn-proxy-on");
  const wizardBtnProxyOff = document.getElementById("wizard-btn-proxy-off");
  const wizardBtnNodeTest = document.getElementById("wizard-btn-node-test");
  const wizardSwitchBadge = document.getElementById("wizard-switch-badge");
  const wizardLiveFeedback = document.getElementById("wizard-live-feedback");
  const wizardFeedbackBadge = document.getElementById("wizard-feedback-badge");
  const wizardFeedbackTime = document.getElementById("wizard-feedback-time");
  const wizardFeedbackContent = document.getElementById("wizard-feedback-content");

  // Modal Client extra fields
  const formClientAccessMode = document.getElementById("form-client-access-mode");
  const sectionAccessSsh = document.getElementById("section-access-ssh");
  const sectionAccessDockerHost = document.getElementById("section-access-docker-host");
  const formClientPort = document.getElementById("form-client-port");
  const formClientAuthType = document.getElementById("form-client-auth-type");
  const formGroupClientPass = document.getElementById("form-group-client-pass");
  const formClientSshPass = document.getElementById("form-client-ssh-pass");
  const formClientContainer = document.getElementById("form-client-container");
  const formClientSshUser = document.getElementById("form-client-ssh-user");
  const formClientHostPort = document.getElementById("form-client-host-port");
  const formClientSshHost = document.getElementById("form-client-ssh-host");
  const formClientSshUserHost = document.getElementById("form-client-ssh-user-host");

  // Sandbox Console Elements
  const sbActiveGwVal = document.getElementById("sb-active-gw-val");
  const sbActiveGwSub = document.getElementById("sb-active-gw-sub");
  const sbGwStatusVal = document.getElementById("sb-gw-status-val");
  const sbGwRttSub = document.getElementById("sb-gw-rtt-sub");
  const sbDiagRateVal = document.getElementById("sb-diag-rate-val");
  const sbDiagSummary = document.getElementById("sb-diag-summary");
  const sbQuickDiagBtn = document.getElementById("sb-quick-diag-btn");
  const sbCmdInput = document.getElementById("sb-cmd-input");
  const sbTemplateSelect = document.getElementById("sb-template-select");
  const sbGwOverrideSelect = document.getElementById("sb-gw-override-select");
  const sbRunBtn = document.getElementById("sb-run-btn");
  const sbTerminalOutput = document.getElementById("sb-terminal-output");
  const sbStatusBadge = document.getElementById("sb-status-badge");
  const sbClearTermBtn = document.getElementById("sb-clear-term-btn");

  // Topology Elements
  const topEnableAllBtn = document.getElementById("top-enable-all-btn");
  const topDisableAllBtn = document.getElementById("top-disable-all-btn");
  const topHealthCheckBtn = document.getElementById("top-health-check-btn");
  const topAuditBtn = document.getElementById("top-audit-btn");
  const nodeSearchInput = document.getElementById("node-search-input");
  const nodeFilterType = document.getElementById("node-filter-type");
  const nodeStatsBadge = document.getElementById("node-stats-badge");
  const topAddClientBtn = document.getElementById("top-add-client-btn");
  const topClientsTbody = document.getElementById("top-clients-tbody");
  const topAddGwBtn = document.getElementById("top-add-gw-btn");
  const topGatewaysTbody = document.getElementById("top-gateways-tbody");
  const topNoproxyInput = document.getElementById("top-noproxy-input");
  const topSaveNoproxyBtn = document.getElementById("top-save-noproxy-btn");
  const topNoproxyHint = document.getElementById("top-noproxy-hint");

  // Audit Modal Elements
  const modalAudit = document.getElementById("modal-audit");
  const modalAuditClose = document.getElementById("modal-audit-close");
  const modalAuditCloseBtn = document.getElementById("modal-audit-close-btn");
  const modalAuditRefreshBtn = document.getElementById("modal-audit-refresh-btn");
  const auditTableTbody = document.getElementById("audit-table-tbody");

  // Modals
  const modalClient = document.getElementById("modal-client");
  const modalClientClose = document.getElementById("modal-client-close");
  const modalClientTitle = document.getElementById("modal-client-title");
  const formClientMode = document.getElementById("form-client-mode");
  const formClientId = document.getElementById("form-client-id");
  const formClientName = document.getElementById("form-client-name");
  const formClientHost = document.getElementById("form-client-host");
  const formClientOs = document.getElementById("form-client-os");
  const formClientGw = document.getElementById("form-client-gw");
  const formClientTags = document.getElementById("form-client-tags");
  const formClientDesc = document.getElementById("form-client-desc");
  const formClientHint = document.getElementById("form-client-hint");
  const modalClientTestBtn = document.getElementById("modal-client-test-btn");
  const modalClientSaveBtn = document.getElementById("modal-client-save-btn");

  const modalGateway = document.getElementById("modal-gateway");
  const modalGwClose = document.getElementById("modal-gw-close");
  const modalGwTitle = document.getElementById("modal-gw-title");
  const formGwMode = document.getElementById("form-gw-mode");
  const formGwId = document.getElementById("form-gw-id");
  const formGwName = document.getElementById("form-gw-name");
  const formGwHost = document.getElementById("form-gw-host");
  const formGwPort = document.getElementById("form-gw-port");
  const formGwProtocol = document.getElementById("form-gw-protocol");
  const formGwDesc = document.getElementById("form-gw-desc");
  const formGwHint = document.getElementById("form-gw-hint");
  const modalGwTestBtn = document.getElementById("modal-gw-test-btn");
  const modalGwSaveBtn = document.getElementById("modal-gw-save-btn");

  // ==============================================================
  // 1. Tab 切换与路由
  // ==============================================================
  function switchTab(tabId) {
    tabButtons.forEach(btn => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
    });
    tabPanes.forEach(pane => {
      pane.classList.toggle("active", pane.id === tabId);
    });
  }

  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      switchTab(btn.getAttribute("data-tab"));
    });
  });

  // ==============================================================
  // 2. 初始化与加载配置
  // ==============================================================
  async function loadConfig() {
    try {
      const res = await fetch("/api/config?t=" + Date.now());
      if (!res.ok) throw new Error("加载配置失败: " + res.status);
      appConfig = await res.json();
      renderAll();
      setupReady = true;
      setupControls.disabled = setupBusy;
      setupReload.hidden = true;
      return true;
    } catch (err) {
      if (setupControls.disabled) {
        setupResult.textContent = err.message;
        setupReload.hidden = false;
      }
      console.error(err);
      globalStatusText.textContent = "配置加载失败";
      globalStatusPill.querySelector(".status-indicator-dot").className = "status-indicator-dot offline";
      return false;
    }
  }

  const setupForm = document.getElementById("setup-form");
  const setupResult = document.getElementById("setup-result");
  const setupControls = document.getElementById("setup-controls");
  const setupReload = document.getElementById("setup-reload");
  setupReload.addEventListener("click", loadConfig);
  const setupHost = document.getElementById("setup-host");
  const setupPort = document.getElementById("setup-port");
  const setupName = document.getElementById("setup-name");
  const setupUrl = document.getElementById("setup-url");
  const setupCommand = document.getElementById("setup-command");
  const setupTest = document.getElementById("setup-test");
  const setupCompare = document.getElementById("setup-compare");

  function setupPayload() {
    return {name: setupName.value.trim(), host: setupHost.value.trim(), port: Number(setupPort.value), protocol: "http"};
  }

  async function postJson(path, payload) {
    const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || response.statusText);
    return data;
  }

  const quickTargets = [
    ["Google", "https://www.google.com/"], ["Claude", "https://claude.ai/"],
    ["ChatGPT", "https://chatgpt.com/"], ["YouTube", "https://www.youtube.com/"],
    ["Gemini", "https://gemini.google.com/"], ["Example", "https://example.com/"],
    ["GitHub", "https://github.com/"], ["GitHub Zen API", "https://api.github.com/zen"]
  ];
  const nodeTargetUrl = document.getElementById("node-target-url");
  const gatewayTargetUrl = document.getElementById("gateway-target-url");
  const modalTargetUrl = document.getElementById("modal-target-url");
  const targetSelects = [...document.querySelectorAll("[data-target-input]")];

  function normalTarget(url) {
    try { return new URL(url).href; } catch { return ""; }
  }

  let nodeTargetRevision = 0;
  let activeNodeProbe = 0;
  nodeTargetUrl.addEventListener("input", () => {
    nodeTargetRevision++;
    document.getElementById("node-test-results").hidden = true;
    topClientsTbody.querySelectorAll(".rtt-pill").forEach(pill => { pill.textContent = ""; });
  });

  function refreshTargetOptions() {
    const targets = new Map();
    for (const [name, url] of quickTargets) targets.set(url, name);
    for (const [name, item] of Object.entries(appConfig.diagnostic_targets || {})) {
      const url = normalTarget(typeof item === "string" ? item : item?.url);
      if (url && !targets.has(url)) targets.set(url, name);
    }
    for (const select of targetSelects) {
      const input = document.getElementById(select.dataset.targetInput);
      if (!input.dataset.ready) {
        if (input.value === input.defaultValue) input.value = appConfig.default_test_url || input.defaultValue;
        input.dataset.ready = "true";
      }
      select.replaceChildren(...Array.from(targets, ([url, name]) => new Option(name, url)),
        new Option("自定义 URL", ""));
      select.value = targets.has(normalTarget(input.value)) ? normalTarget(input.value) : "";
    }
  }

  for (const select of targetSelects) {
    const input = document.getElementById(select.dataset.targetInput);
    select.addEventListener("change", () => {
      input.value = select.value;
      input.dispatchEvent(new Event("input", {bubbles: true}));
      if (!input.value) input.focus();
    });
    input.addEventListener("input", () => {
      select.value = [...select.options].some(option => option.value === normalTarget(input.value)) ? normalTarget(input.value) : "";
    });
  }

  const setupSelect = document.getElementById("setup-select");
  const setupSave = document.getElementById("setup-save");
  const setupDefault = document.getElementById("setup-default");
  let setupId = null;
  let setupRevision = 0;
  let setupDirty = false;
  let setupReady = false;
  let setupBusy = false;

  function gatewayAddress(gateway) {
    const host = gateway.host.includes(":") ? "[" + gateway.host + "]" : gateway.host;
    return "http://" + host + ":" + gateway.port;
  }

  function quoteTarget(value, windows) {
    return "'" + value.replaceAll("'", windows ? "''" : "'\\''") + "'";
  }

  function gatewayGetCommand(gateway, target) {
    const windows = navigator.platform.startsWith("Win");
    const quote = value => quoteTarget(value, windows);
    return (windows ? "curl.exe" : "curl") + " --disable --noproxy " + (windows ? "' '" : "''") +
      " --proxy " + quote(gatewayAddress(gateway)) + " --location --max-redirs 5 --max-time 15" +
      " --proto-redir " + quote(target.toLowerCase().startsWith("https:") ? "=https" : "=http,https") + " --url " + quote(target);
  }

  function probeConclusion(result) {
    if (result.http_ok || result.online) return "代理请求成功 · 最终 HTTP " + result.code;
    const phase = {validation: "目标地址校验", proxy_tcp: "网关 TCP 连接", proxy_tunnel: "代理 CONNECT",
      tls: "TLS 握手", http_response: "等待目标响应", response_body: "读取响应内容"};
    const final = result.final_url || result.request_url || result.url;
    if (result.error_type === "timeout") {
      return (phase[result.stage] || "请求") + "超时 · " + (final || "目标") + " 未返回最终 HTTP 响应";
    }
    if (result.stage === "proxy_tunnel" || ["proxy_tunnel", "proxy_auth"].includes(result.error_type)) {
      return "代理" + (result.error_type === "proxy_auth" ? "要求身份验证" : "拒绝建立隧道") +
        (result.code ? "（" + (result.stage === "proxy_tunnel" || result.connect_status === result.code ? "CONNECT " : "HTTP ") + result.code + "）" : "");
    }
    if (result.error_type?.startsWith("redirect_")) return result.error || "重定向未完成";
    if (result.response_received && result.code) return "目标请求未成功 · HTTP " + result.code;
    return (phase[result.stage] || "代理请求") + "失败" + (result.error ? " · " + result.error : "");
  }

  function probeEvidence(result) {
    const rows = [];
    if (result.proxy_url) rows.push("代理网关 · " + result.proxy_url);
    const start = result.request_url || result.url;
    if (start) rows.push("请求 · " + (result.method || "GET") + " " + start);
    for (const attempt of result.attempts || []) {
      const tls = {passed: "TLS 已验证", eof: "TLS 握手 EOF", timeout: "TLS 握手超时",
        certificate_error: "TLS 证书验证失败", failed: "TLS 握手失败"};
      const phases = [attempt.tcp_ok ? "网关 TCP 已连接" : "网关 TCP 未连接"];
      if (attempt.connect_status != null) phases.push("CONNECT " + attempt.connect_status);
      if (tls[attempt.tls]) phases.push(tls[attempt.tls]);
      if (attempt.http_status != null) phases.push("HTTP " + attempt.http_status);
      const redirect = (result.redirects || [])[attempt.hop - 1];
      if (redirect && attempt.http_status === redirect.code) phases.push("跳转至 " + redirect.location);
      rows.push("第 " + attempt.hop + " 跳" + (attempt.attempt > 1 ? "（重试）" : "") +
        " · " + attempt.url + "\n" + phases.join(" · ") + " · " + attempt.elapsed_ms + " ms");
    }
    if (!result.attempts?.length && result.tcp_ok != null) rows.push("网关 TCP " + (result.tcp_ok ? "已连接" : "未连接"));
    if (result.first_status != null || result.final_status != null) {
      rows.push((result.first_status ? "首跳 HTTP " + result.first_status : "首跳状态未知") + " → " +
        (result.final_status == null ? "未收到最终 HTTP 状态" : "最终 HTTP " + result.final_status));
    }
    if (result.tls_retries) rows.push("TLS 握手 EOF 后已重连一次");
    if (result.final_url && result.final_url !== start) rows.push("最后尝试 · " + result.final_url);
    if (result.latency_ms != null) rows.push("耗时 " + result.latency_ms + " ms" +
      (result.budget_ms ? " · 整次请求预算 " + result.budget_ms / 1000 + " 秒" : ""));
    if (result.error_type === "timeout" && result.budget_expired) rows.push("整次请求的时间预算已用完");
    if (result.response_received) rows.push("账户登录与权限未验证");
    return rows;
  }

  function probeSummary(result) {
    return [probeConclusion(result), ...probeEvidence(result)].join("\n");
  }

  function renderProbe(element, result) {
    const title = document.createElement("strong");
    title.textContent = probeConclusion(result);
    const details = document.createElement("details");
    details.className = "probe-evidence";
    const summary = document.createElement("summary");
    summary.textContent = "查看逐跳证据";
    const list = document.createElement("ol");
    for (const row of probeEvidence(result)) {
      const item = document.createElement("li");
      item.textContent = row;
      list.appendChild(item);
    }
    details.append(summary, list);
    element.replaceChildren(title, details);
  }

  function clearSetupResult() {
    setupRevision++;
    setupResult.textContent = "";
    setupCommand.hidden = true;
    setupCompare.hidden = true;
    setupTest.disabled = false;
  }

  function selectSetupGateway(id) {
    const gw = appConfig.gateways.find(item => item.id === id);
    setupId = gw?.id || "";
    setupSelect.value = setupId;
    setupDirty = false;
    setupName.value = gw?.name || "本机代理";
    setupHost.value = gw?.host || "";
    setupPort.value = gw?.port || "";
    setupSave.textContent = gw ? "保存对此网关的修改" : "保存新网关";
    setupDefault.hidden = !gw || gw.id === activeGateway?.id;
    clearSetupResult();
  }

  setupSelect.addEventListener("change", () => selectSetupGateway(setupSelect.value));
  setupForm.addEventListener("input", event => {
    if ([setupName, setupHost, setupPort].includes(event.target)) setupDirty = true;
    clearSetupResult();
  });

  function beginSetupSave(message) {
    clearSetupResult();
    setupBusy = true;
    setupControls.disabled = true;
    setupResult.textContent = message;
  }

  function finishSetupSave() {
    setupBusy = false;
    setupControls.disabled = !setupReady;
  }

  setupDefault.addEventListener("click", async () => {
    beginSetupSave("正在切换默认网关…");
    try {
      await postJson("/api/set-active-gateway", {gateway_id: setupId});
      setupReady = false;
      if (!await loadConfig()) return;
      setupResult.textContent = "已设为默认网关。";
    } catch (error) {
      setupResult.textContent = error.message;
    } finally {
      finishSetupSave();
    }
  });

  setupForm.addEventListener("submit", async event => {
    event.preventDefault();
    beginSetupSave("正在保存并读取网关配置…");
    try {
      const payload = setupPayload();
      if (setupId) payload.id = setupId;
      const data = await postJson(setupId ? "/api/gateways/update" : "/api/gateways/add", payload);
      setupId = data.gateway.id;
      setupDirty = false;
      setupReady = false;
      if (!await loadConfig()) return;
      setupResult.textContent = "已保存网关。点击“发送代理请求”以验证目标站点。";
    } catch (error) {
      setupResult.textContent = error.message;
    } finally {
      finishSetupSave();
    }
  });

  setupTest.addEventListener("click", async () => {
    if (!setupForm.reportValidity()) return;
    clearSetupResult();
    const revision = setupRevision;
    const gateway = setupPayload();
    const target = setupUrl.value.trim();
    setupTest.disabled = true;
    setupResult.textContent = "正在连接代理并请求目标站点…";
    try {
      const data = await postJson("/api/test-gateway", {...gateway, target_url: target});
      if (revision !== setupRevision) return;
      renderProbe(setupResult, data);
      if (data.request_url) {
        setupCommand.textContent = gatewayGetCommand(gateway, data.request_url);
        setupCommand.hidden = false;
        setupCompare.hidden = !setupId || setupDirty;
      }
    } catch (error) {
      if (revision === setupRevision) setupResult.textContent = error.message;
    } finally {
      if (revision === setupRevision) setupTest.disabled = false;
    }
  });

  function renderAll() {
    refreshTargetOptions();
    const gateways = appConfig.gateways || [];
    activeGateway = gateways.find(g => g.id === appConfig.active_gateway_id) || gateways[0] || null;

    setupSelect.replaceChildren(new Option("新增网关", ""));
    gateways.forEach(gw => setupSelect.add(new Option("编辑 " + gw.name + " (" + gw.host + ":" + gw.port + ")", gw.id)));
    if (setupDirty && (!setupId || gateways.some(gw => gw.id === setupId))) {
      setupSelect.value = setupId;
      setupDefault.hidden = !setupId || setupId === activeGateway?.id;
    } else {
      selectSetupGateway(setupId === null ? activeGateway?.id : setupId);
    }

    globalStatusPill.querySelector(".status-indicator-dot").className = "status-indicator-dot";
    globalStatusPill.title = "当前配置的默认网关";
    if (activeGateway) {
      const gwStr = `${activeGateway.host}:${activeGateway.port}`;
      globalStatusText.textContent = `网关: ${gwStr}`;
      footerGwLabel.textContent = `${activeGateway.name} (${gwStr})`;
      sbActiveGwVal.textContent = gwStr;
      sbActiveGwSub.textContent = activeGateway.name;
    }

    renderWizardSelectors();
    renderSandboxSelectors();
    renderTopologyTables();
    topNoproxyInput.value = appConfig.no_proxy || "";
  }

  // ==============================================================
  // 3. TAB 1: 渐进式接入向导 (Progressive Step-by-Step Flow)
  // ==============================================================
  function resetWizard(keepGateway = false) {
    if (!keepGateway) {
      wizardProbeRevision++;
      wizardTestGwBtn.disabled = false;
      wizardTestGwBtn.textContent = "探测该网关连通性";
      wizardProbeActions.hidden = true;
      readOnlyOutput.textContent = "";
      step1Complete = false;
      cardStep2.classList.add("locked-card");
      cardStep2.inert = true;
      pipeStep2.className = "pipeline-step locked";
      pipeStep1.className = "pipeline-step active";
      pipeStep1.querySelector(".pipe-num").textContent = "1";
      pipeStep1.querySelector(".pipe-name").textContent = "校验代理网关";
      statusTagStep1.className = "step-status-tag";
      statusTagStep1.textContent = "待验证";
      step1Result.className = "step-result-banner";
      step1Result.textContent = "验证所选网关后可继续。";
    }
    step2Complete = false;
    step3Complete = false;
    cardStep3.inert = cardStep4.inert = true;
    cardStep3.classList.add("locked-card");
    cardStep4.classList.add("locked-card");
    pipeStep3.className = pipeStep4.className = "pipeline-step locked";
    for (const [step, number] of [[pipeStep2, 2], [pipeStep3, 3], [pipeStep4, 4]]) {
      step.querySelector(".pipe-num").textContent = number;
    }
    statusTagStep2.textContent = "等待保存绑定";
    statusTagStep3.textContent = "等待验证";
    statusTagStep4.textContent = "等待交付";
    wizardTargetGrid.replaceChildren();
    handoverTargetName.textContent = handoverGwName.textContent = wizardTargetDispName.textContent = "未选择";
    handoverBlocksContainer.replaceChildren();
    wizardLiveFeedback.style.display = "none";
  }

  function nodeRequest(client) {
    return {node_id: client.id, node_revision: client.node_revision ?? 0, gateway_id: client.bound_gateway_id || "",
      binding_revision: client.binding_revision || 0};
  }

  function httpJourney(check) {
    const hops = check.redirects || [];
    const initial = check.first_status ?? hops[0]?.code ?? (!check.redirect_count ? check.code : null);
    const final = check.final_status ?? check.code;
    const firstLabel = initial ? "首跳 HTTP " + initial : "首跳状态未知";
    const lastLabel = final ? "最终 HTTP " + final : "未收到最终 HTTP 状态";
    return firstLabel + " → " + lastLabel;
  }

  function formatPeer(ip, port) {
    if (!ip) return "未取得";
    return (ip.includes(":") ? "[" + ip + "]" : ip) + (port ? ":" + port : "");
  }

  function nodeCheckLines(check) {
    if (!check) return ["未执行"];
    const lines = [httpJourney(check)];
    if (check.execution_context) lines.push("执行范围 · " + (check.execution_context === "fresh_login_shell" ? "独立登录 shell（按该账号启动配置）" : "本机控制台进程"));
    const transports = {local: "控制台本机", ssh: "SSH 节点", ssh_docker_exec: "SSH 宿主机上的目标容器"};
    if (transports[check.transport]) lines.push("执行位置 · " + transports[check.transport]);
    if (check.latency_ms != null) lines.push("请求耗时 · " + check.latency_ms + " ms");
    if (check.auth_ok != null) lines.push("SSH 认证 · " + (check.auth_ok ? "通过" : "失败"));
    lines.push("业务身份/权限 · " + (check.business_ok === false ? "目标拒绝访问" :
      (check.business_ok === true ? "已验证" : "未验证登录状态及账户权限")));
    for (const hop of check.redirects || []) {
      lines.push("HTTP " + hop.code + " · " + hop.url + " → " + hop.location);
    }
    if (check.hops?.length > 1) {
      for (const [index, hop] of check.hops.entries()) {
        const peer = hop.peer || {};
        if (peer.ip) lines.push("第 " + (index + 1) + " 跳对端 · " + formatPeer(peer.ip, peer.port));
      }
    }
    if (check.final_url) lines.push("最终地址 · " + check.final_url);
    if (check.proxy_url) lines.push("显式代理 · " + check.proxy_url);
    const ip = check.peer?.ip || check.remote_ip;
    lines.push("TCP 对端 · " + formatPeer(ip, check.peer?.port));
    if (Number(check.connect_status) > 0) lines.push("代理 CONNECT · HTTP " + check.connect_status);
    const route = {selected_proxy: "连接了选定的代理", matches_explicit_peer: "与显式请求的代理对端一致",
      different_peer: "与显式请求的代理对端不同", unknown: "未能确认代理路径"};
    lines.push("代理路径 · " + (route[check.proxy_evidence?.status] || route.unknown));
    const identity = check.execution_identity;
    if (identity && Object.keys(identity).length) {
      lines.push(["执行用户", identity.user, identity.uid != null && ("UID " + identity.uid),
        identity.home && ("HOME=" + identity.home)].filter(Boolean).join(" · "));
      if (identity.curl_config) lines.push("检测到的 curl 配置 · " + identity.curl_config +
        (check.request_mode === "explicit_proxy" ? "（显式请求以 -q 忽略）" : ""));
      if (identity.curl_home) lines.push("CURL_HOME=" + identity.curl_home);
      if (identity.xdg_config_home) lines.push("XDG_CONFIG_HOME=" + identity.xdg_config_home);
    }
    const stages = Object.entries(check.stages || {}).filter(([, state]) => state !== "skipped")
      .map(([stage, state]) => stage + "=" + state);
    if (stages.length) lines.push(stages.join(" · "));
    if (check.exit_code != null) lines.push("命令退出码 " + check.exit_code);
    if (check.error_type || check.error) lines.push([check.error_type, check.error].filter(Boolean).join(" · "));
    return lines;
  }

  function nodeCheckLabel(check) {
    return check?.online ? "成功（HTTP 请求）" : "未成功（HTTP 请求）";
  }

  function nodeCheckPairs(result) {
    return [["显式指定网关", result.explicit_proxy], ["普通 curl（目标当前设置）", result.ordinary_request]];
  }

  const restoredProxyNote = "启用前已有的代理可能继续生效。可用普通 curl 复测当前路径。";

  function restoredEnvironmentNote(verification) {
    const env = verification?.restored_environment;
    if (!env?.observed) return "";
    const gateway = env.matched_gateway;
    const context = verification.verified && verification.verification_scope === "login_and_managed_files"
      ? "原登录环境" : "当前独立登录环境";
    if (gateway) return `${context}仍有代理 · ${formatPeer(gateway.host, gateway.port)}（与已知网关吻合）`;
    return env.proxy_present ? `${context}仍有代理（其他来源，地址未回显）` : `${context}未检测到代理变量（不代表所有应用直连）`;
  }

  function nodeContext(result) {
    const check = result.ordinary_request || result.explicit_proxy || result;
    const enabled = result.is_proxy_enabled ?? check.is_proxy_enabled;
    const recorded = enabled == null ? "未知" : (enabled ? "已开启" : "已关闭");
    const states = {enabled: "已核验开启", disabled: "已核验恢复原基线", unknown: "未核验"};
    const verification = result.verification || {};
    return ["请求目标 · " + (check.target_url || result.target_url || "未知"),
      "托管配置记录 · " + recorded,
      "最近配置核验 · " + (states[result.managed_state] || states.unknown),
      "核验范围 · " + ({login_and_managed_files: "独立登录环境与托管文件", managed_files_only: "原快照文件（不推定直连）", managed_files: "托管文件与执行身份"}[verification.verification_scope] || "尚未核验"),
      restoredEnvironmentNote(verification), "公网出口 IP · 未核验"].filter(Boolean).join("\n");
  }

  function nodeProbeSummary(result) {
    if (!result.explicit_proxy && !result.ordinary_request) return result.error || result.message || "尚无目标请求结果";
    return [nodeContext(result), ...nodeCheckPairs(result).map(([label, check]) =>
      [label + " · " + nodeCheckLabel(check), ...nodeCheckLines(check)].join("\n"))].join("\n\n");
  }

  function showNodeResult(client, result) {
    document.getElementById("node-test-heading").textContent = client.name + " · 外网测试";
    document.getElementById("node-test-record").textContent = nodeContext(result);
    const cards = document.getElementById("node-test-checks");
    cards.replaceChildren();
    for (const [title, check] of nodeCheckPairs(result)) {
      const card = document.createElement("section");
      const heading = document.createElement("h4");
      heading.textContent = title + " · " + nodeCheckLabel(check);
      const details = document.createElement("p");
      details.textContent = nodeCheckLines(check).join("\n");
      card.append(heading, details);
      cards.append(card);
    }
    const panel = document.getElementById("node-test-results");
    panel.hidden = false;
    panel.scrollIntoView({block: "nearest"});
  }

  function renderWizardSelectors() {
    const oldGateway = selectedWizardGateway;
    const oldClient = selectedWizardClient;
    const gateways = appConfig.gateways || [];
    const clients = appConfig.clients || [];

    const gatewayId = gateways.find(g => g.id === oldGateway?.id)?.id || activeGateway?.id;
    // 网关选择器
    wizardGwSelect.innerHTML = "";
    gateways.forEach(gw => {
      const opt = document.createElement("option");
      opt.value = gw.id;
      opt.textContent = `${gw.name} (${gw.host}:${gw.port})` + (gw.id === appConfig.active_gateway_id ? " [默认]" : "");
      if (gw.id === gatewayId) opt.selected = true;
      wizardGwSelect.appendChild(opt);
    });
    selectedWizardGateway = gateways.find(g => g.id === wizardGwSelect.value) || gateways[0];

    // 业务节点选择器
    wizardClientSelect.innerHTML = "";
    clients.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.name} (${c.host}) [${c.os_type || 'linux'}]`;
      wizardClientSelect.appendChild(opt);
    });

    selectedWizardClient = clients.find(c => c.id === oldClient?.id) || clients[0] || null;
    wizardClientSelect.value = selectedWizardClient?.id || "";
    updateWizardClientMeta(selectedWizardClient);
    if (!oldGateway || !selectedWizardGateway || oldGateway.id !== selectedWizardGateway.id ||
        gatewayAddress(oldGateway) !== gatewayAddress(selectedWizardGateway)) resetWizard();
    else if (!oldClient || selectedWizardClient?.id !== oldClient.id ||
        selectedWizardClient.binding_revision !== oldClient.binding_revision) resetWizard(step1Complete);
    if (step3Complete) renderHandoverBlocks();
  }

  function updateWizardClientMeta(client) {
    if (!client) {
      wMetaHost.textContent = wMetaOs.textContent = wMetaGw.textContent = wMetaTags.textContent = "—";
      return;
    }
    wMetaHost.textContent = client.host;
    wMetaOs.textContent = (client.os_type || "linux").toUpperCase();
    const boundGw = (appConfig.gateways || []).find(g => g.id === client.bound_gateway_id);
    wMetaGw.textContent = boundGw ? `${boundGw.name} (${boundGw.host}:${boundGw.port})` : (client.bound_gateway_id || "未指定");
    wMetaTags.textContent = (client.tags && client.tags.length) ? client.tags.join(", ") : "无";
  }

  wizardClientSelect.addEventListener("change", () => {
    const cid = wizardClientSelect.value;
    selectedWizardClient = (appConfig.clients || []).find(c => c.id === cid);
    updateWizardClientMeta(selectedWizardClient);
    resetWizard(step1Complete);
  });

  wizardTestUrl.addEventListener("input", () => resetWizard());
  wizardGwSelect.addEventListener("change", () => {
    const gid = wizardGwSelect.value;
    selectedWizardGateway = (appConfig.gateways || []).find(g => g.id === gid);
    resetWizard();
  });

  // Step 1: 探测网关
  wizardTestGwBtn.addEventListener("click", async () => {
    if (!selectedWizardGateway) { setupHost.focus(); return; }
    if (!wizardTestUrl.reportValidity()) return;
    const gateway = selectedWizardGateway;
    const target = wizardTestUrl.value.trim();
    resetWizard();
    const revision = wizardProbeRevision;
    wizardTestGwBtn.disabled = true;
    wizardTestGwBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在探测网关...';
    step1Result.className = "step-result-banner";
    step1Result.textContent = "正在通过所选网关发送 GET 请求…";

    try {
      const data = await postJson("/api/test-gateway", {...gateway, target_url: target});
      if (revision !== wizardProbeRevision) return;
      renderProbe(step1Result, data);
      wizardProbeActions.hidden = false;
      document.getElementById("wizard-probe-command").textContent = gatewayGetCommand(gateway, target);
      const bound = (appConfig.clients || []).filter(client => client.bound_gateway_id === gateway.id);
      readOnlyNode.replaceChildren(...bound.map(client => new Option(client.name, client.id)));
      if (!bound.length) readOnlyNode.add(new Option("暂无已绑定节点", ""));
      readOnlyNode.disabled = readOnlyTest.disabled = !bound.length;
      if (data.online) {
        step1Result.className = "step-result-banner success";
        statusTagStep1.className = "step-status-tag success";
        statusTagStep1.textContent = "✅ 已就绪";
        pipeStep1.className = "pipeline-step completed";
        pipeStep1.innerHTML = '<span class="pipe-num">✓</span><span class="pipe-name">网关已就绪</span>';

        // 激活 Step 2
        unlockStep2();
      } else {
        step1Result.className = "step-result-banner error";
        statusTagStep1.className = "step-status-tag";
        statusTagStep1.textContent = "目标请求未成功";
      }
    } catch (err) {
      if (revision !== wizardProbeRevision) return;
      step1Result.className = "step-result-banner error";
      step1Result.textContent = "请求异常：" + err.message;
    } finally {
      if (revision === wizardProbeRevision) {
        wizardTestGwBtn.disabled = false;
        wizardTestGwBtn.textContent = "重新测试同一 GET";
      }
    }
  });

  readOnlyNode.addEventListener("change", () => { readOnlyOutput.textContent = ""; });
  readOnlyTest.addEventListener("click", async () => {
    const node = appConfig.clients.find(client => client.id === readOnlyNode.value);
    if (!node || node.bound_gateway_id !== selectedWizardGateway?.id) return;
    const revision = wizardProbeRevision;
    readOnlyNode.disabled = readOnlyTest.disabled = true;
    readOnlyOutput.textContent = "正在从 " + node.name + " 发送只读请求…";
    try {
      const data = await postJson("/api/node-test", {...nodeRequest(node), target_url: wizardTestUrl.value.trim()});
      if (revision === wizardProbeRevision) readOnlyOutput.textContent = node.name + "\n" + nodeProbeSummary(data);
    } catch (error) {
      if (revision === wizardProbeRevision) readOnlyOutput.textContent = error.message;
    } finally {
      if (revision === wizardProbeRevision) readOnlyNode.disabled = readOnlyTest.disabled = false;
    }
  });

  // 设为默认网关
  wizardSetDefaultGwBtn.addEventListener("click", async () => {
    if (!selectedWizardGateway) return;
    try {
      const res = await fetch("/api/set-active-gateway", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gateway_id: selectedWizardGateway.id })
      });
      if (res.ok) {
        await loadConfig();
        alert(`已成功将【${selectedWizardGateway.name}】设为全局默认网关！`);
      }
    } catch (e) {
      alert("设置失败: " + e.message);
    }
  });

  function unlockStep2() {
    step1Complete = true;
    cardStep2.inert = false;
    cardStep2.classList.remove("locked-card");
    pipeStep2.classList.remove("locked");
    pipeStep2.classList.add("active");
    statusTagStep2.textContent = "● 待确认绑定";
    cardStep2.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Step 2: 确认选定节点
  wizardConfirmClientBtn.addEventListener("click", async () => {
    const client = selectedWizardClient;
    const gateway = selectedWizardGateway;
    if (!client || !gateway || !step1Complete) return;
    wizardConfirmClientBtn.disabled = true;
    try {
      const data = await postJson("/api/clients/update", {id: client.id, bound_gateway_id: gateway.id,
        node_revision: client.node_revision ?? 0, binding_revision: client.binding_revision || 0});
      if (data.client?.bound_gateway_id !== gateway.id) throw new Error("服务未确认节点绑定，请重新加载。");
      await loadConfig();
      if (selectedWizardClient?.id !== client.id || selectedWizardGateway?.id !== gateway.id) return;
      if (selectedWizardClient.bound_gateway_id !== gateway.id ||
          (selectedWizardClient.node_revision ?? 0) !== (data.client.node_revision ?? 0) ||
          (selectedWizardClient.binding_revision || 0) !== (data.client.binding_revision || 0)) {
        throw new Error("节点绑定已变化，请重新确认。");
      }
      step2Complete = true;
      statusTagStep2.textContent = "已保存：" + client.name + " → " + gateway.name;
      unlockStep3();
    } catch (error) {
      resetWizard(true);
      statusTagStep2.textContent = error.message;
    } finally {
      wizardConfirmClientBtn.disabled = false;
    }
  });

  function unlockStep3() {
    cardStep3.inert = false;
    cardStep3.classList.remove("locked-card");
    pipeStep3.classList.remove("locked");
    pipeStep3.classList.add("active");
    statusTagStep3.textContent = "● 等待体检";
    initTargetGridPlaceholder();
    cardStep3.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function initTargetGridPlaceholder() {
    wizardTargetGrid.innerHTML = "";
    const targets = appConfig.diagnostic_targets || {};
    if (!Object.keys(targets).length) wizardTargetGrid.textContent = "没有配置多站目标，可继续验证所选节点。";
    Object.keys(targets).forEach(name => {
      const item = targets[name];
      const div = document.createElement("div");
      div.className = "target-card-item";
      div.id = `diag-item-${name}`;
      div.innerHTML = `
        <div class="t-info">
          <span class="t-name">${escapeHtml(name)}</span>
          <span class="t-cat">${escapeHtml(typeof item === 'string' ? item : (item?.desc || item?.category || item?.url || ''))}</span>
        </div>
        <div class="t-status">
          <span class="t-pill waiting">等待测试</span>
          <span class="t-rtt">-- ms</span>
        </div>
      `;
      wizardTargetGrid.appendChild(div);
    });
  }

  // Step 3: 全链路穿透体检
  wizardStartDiagBtn.addEventListener("click", async () => {
    if (!step2Complete) return;
    const client = selectedWizardClient;
    const gateway = selectedWizardGateway;
    wizardStartDiagBtn.disabled = true;
    wizardStartDiagBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在执行全网穿透体检...';
    statusTagStep3.textContent = "⚡ 正在穿透探测...";

    // 状态置为 testing
    const targets = appConfig.diagnostic_targets || {};
    Object.keys(targets).forEach(name => {
      const el = document.getElementById(`diag-item-${name}`);
      if (el) {
        el.querySelector(".t-pill").className = "t-pill testing";
        el.querySelector(".t-pill").textContent = "探测中...";
      }
    });

    try {
      const gid = selectedWizardGateway ? selectedWizardGateway.id : appConfig.active_gateway_id;
      const res = await fetch(`/api/status?gateway_id=${encodeURIComponent(gid)}`);
      const data = await res.json();

      if (!step2Complete || selectedWizardClient?.id !== client.id || selectedWizardGateway?.id !== gateway.id) return;
      wizardDiagTime.textContent = `体检时间: ${data.timestamp}`;
      let onlineCount = 0;
      const results = data.targets || [];

      results.forEach(target => {
        const el = document.getElementById(`diag-item-${target.name}`);
        if (!el) return;
        const pill = el.querySelector(".t-pill");
        const rtt = el.querySelector(".t-rtt");

        if (target.status === "online") {
          onlineCount++;
          pill.className = "t-pill success";
          pill.textContent = `🟢 在线 (HTTP ${target.code})`;
          rtt.textContent = `${target.latency_ms} ms`;
        } else {
          pill.className = "t-pill failed";
          pill.textContent = target.code ? "HTTP " + target.code : "请求未成功";
          rtt.textContent = target.error || "请查看网关与目标地址";
          el.title = probeSummary(target);
        }
      });

      const emptyList = Object.keys(targets).length === 0;
      if (emptyList || (results.length && onlineCount >= Math.min(2, results.length))) {
        step3Complete = true;
        statusTagStep3.className = results.length && onlineCount === results.length ? "step-status-tag success" : "step-status-tag";
        statusTagStep3.textContent = emptyList ? "未配置多站目标" : `已测试，${onlineCount}/${results.length} 个目标请求成功`;
        pipeStep3.className = "pipeline-step completed";
        pipeStep3.querySelector(".pipe-name").textContent = emptyList ? "已跳过多站测试" : "多站测试已完成";

        // 解锁 Step 4
        unlockStep4();
      } else {
        step3Complete = false;
        cardStep4.inert = true;
        cardStep4.classList.add("locked-card");
        statusTagStep3.className = "step-status-tag";
        statusTagStep3.textContent = `⚠️ 穿透异常 (${onlineCount}/${results.length} 在线)`;
        alert("大部分境外目标站点未能通过代理访问，请检查所选网关的节点配置或网络策略。");
      }
    } catch (err) {
      statusTagStep3.textContent = "❌ 诊断请求异常";
      alert("体检请求失败: " + err.message);
    } finally {
      wizardStartDiagBtn.disabled = false;
      wizardStartDiagBtn.innerHTML = '<span class="btn-icon">🚀</span> 重新执行全链路体检';
    }
  });

  function unlockStep4() {
    cardStep4.inert = false;
    cardStep4.classList.remove("locked-card");
    pipeStep4.classList.remove("locked");
    pipeStep4.classList.add("completed");
    pipeStep4.innerHTML = '<span class="pipe-num">✓</span><span class="pipe-name">开箱即用</span>';
    statusTagStep4.textContent = "🎯 交付完成";

    if (wizardSwitchBadge && selectedWizardClient) {
      if (selectedWizardClient.is_proxy_enabled) {
        wizardSwitchBadge.className = "switch-badge on";
        wizardSwitchBadge.textContent = "🟢 托管记录 · 已开启";
      } else {
        wizardSwitchBadge.className = "switch-badge off";
        wizardSwitchBadge.textContent = "⚪ 托管记录 · 已关闭";
      }
    }

    renderHandoverBlocks();
    cardStep4.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderHandoverBlocks() {
    const client = selectedWizardClient;
    if (!client) return;
    const gw = appConfig.gateways.find(g => g.id === client.bound_gateway_id) || activeGateway;
    if (!gw) return;
    const osType = (client.os_type || "linux").toLowerCase();
    const localWindows = isWindowsWorkstation(client);
    wizardBtnProxyOn.textContent = localWindows ? "在本机发送业务请求" : "开启节点代理";
    wizardBtnProxyOff.hidden = localWindows;

    handoverTargetName.textContent = `${client.name} (${osType.toUpperCase()}, ${client.host})`;
    if (handoverGwName) handoverGwName.textContent = `${gw.host}:${gw.port}`;
    if (wizardTargetDispName) wizardTargetDispName.textContent = `${client.name} (${osType.toUpperCase()})`;
    if (wizardTargetDispSub) {
      if (osType === "docker") {
        wizardTargetDispSub.textContent = `目标 IP: ${client.host} | 容器名: ${client.container_name || 'app-container'}`;
      } else {
        wizardTargetDispSub.textContent = `目标 IP: ${client.host} | 绑定网关: ${gw.host}:${gw.port}`;
      }
    }

    const isProxyOn = Boolean(client.is_proxy_enabled);
    if (wizardSwitchBadge) {
      wizardSwitchBadge.className = isProxyOn ? "switch-badge on" : "switch-badge off";
      wizardSwitchBadge.textContent = localWindows ? "单次请求" : (client.applied_gateway_id && client.applied_gateway_id !== gw.id
        ? "已更换绑定，需重新开启以应用" : (isProxyOn ? "托管记录 · 已开启" : "托管记录 · 已关闭"));
    }

    handoverBlocksContainer.innerHTML = "";

    let command;
    let title;
    if (osType === "windows") {
      title = "在 Windows 工具目录中运行单次代理请求";
      command = ".\\bin\\with-proxy.cmd --gateway " + gw.id + " curl.exe --location --url " + quoteTarget(wizardTestUrl.value, true);
    } else {
      title = "开启节点代理后，在目标工作站或容器内验证";
      command = "curl --location --url " + quoteTarget(wizardTestUrl.value, false);
    }
    const card = document.createElement("div");
    card.className = "code-delivery-card";
    card.innerHTML = '<div class="code-delivery-header"><span class="code-delivery-title"></span><button class="btn-copy">复制代码</button></div><pre><code></code></pre>';
    card.querySelector(".code-delivery-title").textContent = title;
    card.querySelector("code").textContent = command;
    card.querySelector(".btn-copy").dataset.copy = command;
    handoverBlocksContainer.appendChild(card);

    // 绑定复制按钮
    attachCopyButtons(handoverBlocksContainer);
  }

  // 步骤 4 Web 自动化一键开通/关闭/复测
  function showWizardFeedback(badgeClass, badgeText, content) {
    if (!wizardLiveFeedback) return;
    wizardLiveFeedback.style.display = "block";
    wizardFeedbackBadge.className = `feedback-badge ${badgeClass}`;
    wizardFeedbackBadge.textContent = badgeText;
    wizardFeedbackTime.textContent = new Date().toLocaleTimeString();
    wizardFeedbackContent.textContent = content;
  }

  function isWindowsWorkstation(client) {
    return client.os_type === "windows" && client.access_mode === "local";
  }

  function openGatewayRequest(gatewayId, target) {
    switchTab("tab-sandbox");
    sbGwOverrideSelect.value = gatewayId;
    if (target) {
      sbCmdInput.value = target;
      sbCmdInput.dispatchEvent(new Event("input", {bubbles: true}));
    }
    resetBusinessMetrics();
    sbCmdInput.focus();
  }

  setupCompare.addEventListener("click", () => openGatewayRequest(setupId, setupUrl.value.trim()));
  document.getElementById("wizard-compare").addEventListener("click", () =>
    openGatewayRequest(selectedWizardGateway.id, wizardTestUrl.value.trim()));

  async function runWizardAction(action) {
    const client = selectedWizardClient;
    const gateway = selectedWizardGateway;
    if (!step3Complete || !client || client.bound_gateway_id !== gateway?.id) return;
    if (action === "on" && isWindowsWorkstation(client)) {
      openGatewayRequest(gateway.id, wizardTestUrl.value.trim());
      return;
    }
    const buttons = [wizardBtnProxyOn, wizardBtnProxyOff, wizardBtnNodeTest];
    buttons.forEach(button => button.disabled = true);
    wizardGwSelect.disabled = wizardClientSelect.disabled = true;
    try {
      showWizardFeedback("warning", "执行中", client.name + " → " + gateway.name);
      if (action === "test") {
        const data = await postJson("/api/node-test", {...nodeRequest(client), target_url: wizardTestUrl.value.trim()});
        showWizardFeedback(data.success ? "success" : "warning", client.name + " · 请求结果", nodeProbeSummary(data));
      } else {
        const data = await postJson("/api/node-switch", {...nodeRequest(client), action});
        await loadConfig();
        showWizardFeedback("success", client.name, action === "off" ? data.message + "\n" + restoredProxyNote : data.message);
      }
    } catch (error) {
      showWizardFeedback("error", "操作未完成", error.message);
    } finally {
      buttons.forEach(button => button.disabled = false);
      wizardGwSelect.disabled = wizardClientSelect.disabled = false;
    }
  }

  wizardBtnProxyOn.addEventListener("click", () => runWizardAction("on"));
  wizardBtnProxyOff.addEventListener("click", () => runWizardAction("off"));
  wizardBtnNodeTest.addEventListener("click", () => runWizardAction("test"));

  // ==============================================================
  // 4. TAB 2: ⚡ 沙箱控制台 (Sandbox Console)
  // ==============================================================
  function renderSandboxSelectors() {
    const previousId = sbGwOverrideSelect.value;
    sbGwOverrideSelect.replaceChildren(new Option("使用默认网关", ""));
    for (const gw of appConfig.gateways) {
      sbGwOverrideSelect.add(new Option(gw.name + " (" + gw.host + ":" + gw.port + ")", gw.id));
    }
    if (appConfig.gateways.some(gw => gw.id === previousId)) sbGwOverrideSelect.value = previousId;
    resetBusinessMetrics();
  }

  function businessGateway() {
    return appConfig?.gateways.find(gw => gw.id === sbGwOverrideSelect.value) || activeGateway;
  }

  function resetBusinessMetrics() {
    const gw = businessGateway();
    sbActiveGwVal.textContent = gw ? gatewayAddress(gw) : "尚未配置";
    sbActiveGwSub.textContent = gw?.name || "请在接入向导保存网关";
    sbGwStatusVal.textContent = sbDiagRateVal.textContent = "尚未检测";
    sbGwRttSub.textContent = sbDiagSummary.textContent = "可发送请求或刷新连通性";
    sbTerminalOutput.textContent = "等待发送请求。";
    sbStatusBadge.textContent = "就绪";
  }

  function showBusinessMetrics(data) {
    sbGwStatusVal.textContent = data.tcp_ok == null ? "尚无结果" : (data.tcp_ok ? "已连接" : "连接失败");
    sbGwRttSub.textContent = data.tcp_latency_ms != null ? data.tcp_latency_ms + " ms" : "";
    const finalCode = data.final_status ?? (data.response_received ? data.code : null);
    sbDiagRateVal.textContent = finalCode ? "HTTP " + finalCode : "未收到最终响应";
    sbDiagSummary.textContent = data.error || data.final_url || data.request_url || "";
  }

  sbGwOverrideSelect.addEventListener("change", resetBusinessMetrics);
  sbCmdInput.addEventListener("input", resetBusinessMetrics);
  sbQuickDiagBtn.addEventListener("click", () => initPrecheck());
  sbClearTermBtn.addEventListener("click", () => { sbTerminalOutput.textContent = ""; });

  sbRunBtn.addEventListener("click", async () => {
    const gw = businessGateway();
    if (!gw) { sbTerminalOutput.textContent = "请在接入向导保存网关。"; return; }
    if (!sbCmdInput.reportValidity()) return;
    const target = sbCmdInput.value.trim();
    const controls = [sbRunBtn, sbQuickDiagBtn, sbCmdInput, sbTemplateSelect, sbGwOverrideSelect];
    controls.forEach(control => control.disabled = true);
    sbStatusBadge.textContent = "请求中";
    sbTerminalOutput.textContent = "GET " + target + "\n" + gatewayAddress(gw);
    try {
      const response = await fetch("/api/run", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({target_url: target, gateway_id: gw.id})});
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || response.statusText);
      }
      const events = (await response.text()).split(/\r?\n/).filter(line => line.startsWith("data: "))
        .map(line => JSON.parse(line.slice(6)));
      const result = events.find(event => event.type === "result");
      if (!result) throw new Error("未收到请求结果，请刷新后重试。");
      showBusinessMetrics(result);
      sbTerminalOutput.textContent = [gatewayAddress(gw) + " → " + target,
        probeSummary(result), result.headers, result.preview].filter(Boolean).join("\n\n");
      sbStatusBadge.textContent = result.success ? "请求成功" : "请求未成功";
    } catch (error) {
      sbStatusBadge.textContent = "请求未完成";
      sbTerminalOutput.textContent = error.message;
    } finally {
      controls.forEach(control => control.disabled = false);
    }
  });

  // ==============================================================
  // 5. TAB 3: 🌐 拓扑与节点管理 (Topology Manager, 完整 CRUD)
  // ==============================================================
  function renderTopologyTables() {
    renderClientsTable();
    renderGatewaysTable();
  }

  // 渲染业务节点表格 (5列紧凑美化布局 + 实时搜索过滤 + 批量管控)
  let cachedClients = [];

  function filterClientsList() {
    if (!cachedClients) return [];
    const query = (nodeSearchInput ? nodeSearchInput.value.trim().toLowerCase() : "");
    const filterType = (nodeFilterType ? nodeFilterType.value : "all");

    return cachedClients.filter(c => {
      if (filterType === "docker" && c.os_type !== "docker") return false;
      if (filterType === "linux" && c.os_type === "docker") return false;
      if (filterType === "proxy_on" && c.managed_state !== "enabled") return false;
      if (filterType === "proxy_off" && c.managed_state !== "disabled") return false;
      if (filterType === "unknown" && ![undefined, "unknown"].includes(c.managed_state)) return false;

      if (!query) return true;
      const matchName = (c.name || "").toLowerCase().includes(query);
      const matchHost = (c.host || "").toLowerCase().includes(query);
      const matchPort = String(c.port || "").includes(query);
      const matchContainer = (c.container_name || "").toLowerCase().includes(query);
      const matchTags = (c.tags || []).some(t => String(t).toLowerCase().includes(query));
      const matchDesc = (c.description || "").toLowerCase().includes(query);
      return matchName || matchHost || matchPort || matchContainer || matchTags || matchDesc;
    });
  }

  function updateNodeStatsBadge() {
    if (!nodeStatsBadge) return;
    const total = cachedClients.length;
    const onCount = cachedClients.filter(c => c.managed_state === "enabled").length;
    const offCount = cachedClients.filter(c => c.managed_state === "disabled").length;
    nodeStatsBadge.textContent = `共 ${total} 个节点 (${onCount} 已核验开启, ${offCount} 已核验恢复, ${total - onCount - offCount} 未核验)`;
  }

  const nodeTargets = new Map();

  function bindRowTarget(row, client) {
    const select = row.querySelector("[data-node-target]");
    const input = row.querySelector("[data-node-custom]");
    const options = document.querySelector('[data-target-input="node-target-url"]').options;
    select.add(new Option("使用节点池目标", "default"));
    for (const option of options) select.add(new Option(option.text, option.value));
    const saved = nodeTargets.get(client.id);
    select.value = saved?.choice ?? "default";
    input.value = saved?.url || "";
    input.hidden = select.value !== "";
    function remember() {
      nodeTargetRevision++;
      if (select.value === "default") nodeTargets.delete(client.id);
      else nodeTargets.set(client.id, {choice: select.value, url: input.value});
      row.querySelector(".rtt-pill").textContent = "";
      document.getElementById("node-test-results").hidden = true;
    }
    select.addEventListener("change", () => {
      input.hidden = select.value !== "";
      if (select.value) input.value = "";
      else input.focus();
      remember();
    });
    input.addEventListener("input", remember);
  }

  function renderClientsTableRows(clientsToRender) {
    topClientsTbody.innerHTML = "";

    if (!clientsToRender || clientsToRender.length === 0) {
      topClientsTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-dim); padding: 24px;">未匹配到符合条件的业务节点</td></tr>`;
      return;
    }

    clientsToRender.forEach(c => {
      const boundGw = (appConfig.gateways || []).find(g => g.id === c.bound_gateway_id);
      const localWindows = isWindowsWorkstation(c);
      const gwName = boundGw ? `${boundGw.name}` : (c.bound_gateway_id || "未绑定（禁止开启）");
      const tagsHtml = (c.tags || []).map(t => `<span class="tag-badge">${escapeHtml(t)}</span>`).join("");
      const isProxyOn = Boolean(c.is_proxy_enabled || c.pending_action);
      const verifiedState = c.managed_state || "unknown";
      const stateLabel = {enabled: "已核验开启", disabled: "已核验恢复", unknown: "未核验"}[verifiedState] || "未核验";
      const isLocal = c.access_mode === "local";

      let addrBadge = '<span class="addr-badge">SSH直连</span>';
      let addrRow = `<code>${escapeHtml(c.ssh_user || 'root')}@${escapeHtml(c.host)}:${c.port || 22}</code>`;

      if (isLocal) {
        addrBadge = '<span class="addr-badge" style="background:rgba(168,85,247,0.15);color:#c084fc;">本机控制台</span>';
        addrRow = `<code>127.0.0.1 (本机执行)</code>`;
      } else if (c.access_mode === "docker_host" || (c.container_name && !c.port)) {
        addrBadge = '<span class="addr-badge" style="background:rgba(234,179,8,0.15);color:#facc15;">Docker穿透</span>';
        addrRow = `<code>${escapeHtml(c.ssh_user || 'ubuntu')}@${escapeHtml(c.ssh_host || c.host)}:${c.port || 22}</code> <span style="font-size:11px;color:var(--text-dim);">&rarr; [${escapeHtml(c.container_name || c.name)}]</span>`;
      } else if (c.port && c.port != 22) {
        addrBadge = `<span class="addr-badge" style="background:rgba(6,182,212,0.15);color:#22d3ee;">端口映射容器 (:${c.port})</span>`;
      }

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>
          <div class="node-title-cell">
            <strong>${escapeHtml(c.name)}</strong>
            <div class="node-tags-inline">${tagsHtml}</div>
            ${c.description ? `<span style="font-size:11px;color:var(--text-muted);">${escapeHtml(c.description)}</span>` : ''}
          </div>
        </td>
        <td>
          <div class="node-addr-cell">
            <div class="addr-row">
              ${addrBadge}
            </div>
            <div style="margin-top:2px;">
              ${addrRow}
            </div>
          </div>
        </td>
        <td>
          <strong>${escapeHtml(gwName)}</strong>
          <div style="font-size:11px;color:var(--text-dim);">${boundGw ? `HTTP 代理 :${boundGw.port}` : ''}</div>
        </td>
        <td>
          <div class="status-capsule ${verifiedState === 'enabled' ? 'on' : verifiedState === 'disabled' ? 'off' : 'unknown'}">
            <span class="capsule-indicator">
              ${escapeHtml(stateLabel)}${c.identity_confirmation_required ? " · 请确认执行位置" : ""}
            </span>
            <button class="capsule-btn ${isProxyOn ? 'btn-turn-off' : 'btn-turn-on'}" data-action="toggle-client" data-id="${escapeHtml(c.id)}" data-action-type="${isProxyOn ? 'off' : 'on'}">
              ${localWindows ? '发送业务请求' : (isProxyOn ? '停止托管' : '⚡ 开启')}
            </button>
          </div>
          ${c.managed_state === "disabled" ? `<div class="restoration-note">${escapeHtml(restoredEnvironmentNote(c.verification))}</div>` : ''}
        </td>
        <td style="text-align: right;">
          <div class="row-target"><select class="form-select" data-node-target aria-label="此节点探测目标"></select>
            <input type="url" class="form-input" data-node-custom required aria-label="此节点自定义 URL" placeholder="https://…" hidden></div>
          <div class="table-actions-modern">
            <button class="btn-speedtest" data-action="test-node-out" data-id="${escapeHtml(c.id)}" title="实测出海延迟与连通状态">
              🔍 测外网 <span class="rtt-pill" id="rtt-${escapeHtml(c.id)}"></span>
            </button>
            <div class="action-dropdown-wrap">
              <button class="btn-dropdown-toggle" title="更多运维操作">•••</button>
              <div class="action-dropdown-menu">
                <button class="dropdown-item" data-action="edit-client" data-id="${escapeHtml(c.id)}">✏️ 编辑参数</button>
                <button class="dropdown-item" data-action="clone-client" data-id="${escapeHtml(c.id)}">📋 克隆节点</button>
                <button class="dropdown-item" data-action="test-client" data-id="${escapeHtml(c.id)}" data-host="${escapeHtml(c.host)}" data-port="${c.port || 22}">⚡ 连通探测</button>
                ${!localWindows ? `<button class="dropdown-item" data-action="restore-client" data-id="${escapeHtml(c.id)}" data-action-type="off">↩ 恢复启用前基线</button>` : ''}
                <button class="dropdown-item danger" data-action="delete-client" data-id="${escapeHtml(c.id)}">🗑️ 删除节点</button>
              </div>
            </div>
          </div>
        </td>
      `;
      bindRowTarget(tr, c);
      topClientsTbody.appendChild(tr);
    });

    // 绑定下拉操作菜单切换
    topClientsTbody.querySelectorAll(".btn-dropdown-toggle").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const wrap = btn.closest(".action-dropdown-wrap");
        document.querySelectorAll(".action-dropdown-wrap.active").forEach(w => {
          if (w !== wrap) w.classList.remove("active");
        });
        if (wrap) wrap.classList.toggle("active");
      });
    });

    // 绑定表格操作按钮
    topClientsTbody.querySelectorAll("[data-action='toggle-client'], [data-action='restore-client']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const cid = btn.getAttribute("data-id");
        const actionType = btn.getAttribute("data-action-type");
        const client = appConfig.clients.find(item => item.id === cid);
        if (isWindowsWorkstation(client)) { openGatewayRequest(client.bound_gateway_id || activeGateway?.id || ""); return; }
        if (actionType === "off" && !confirm(`恢复 ${client.name} 的启用前基线？原有代理可能继续生效。`)) return;
        btn.disabled = true;
        btn.textContent = "⏳...";
        try {
          const res = await fetch("/api/node-switch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...nodeRequest(client),
              action: actionType
            })
          });
          const d = await res.json();
          if (d.success) {
            await loadConfig();
            alert(actionType === "off" ? [d.message, restoredEnvironmentNote(d.verification), restoredProxyNote].filter(Boolean).join("\n") : d.message);
          } else {
            alert("切换失败: " + d.error);
          }
        } catch (e) {
          alert("切换异常: " + e.message);
        } finally {
          await loadConfig();
          btn.disabled = false;
        }
      });
    });

    topClientsTbody.querySelectorAll("[data-action='test-node-out']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const row = btn.closest("tr");
        const choice = row.querySelector("[data-node-target]").value;
        const input = choice === "default" ? nodeTargetUrl : row.querySelector("[data-node-custom]");
        if ((!choice || choice === "default") && !input.reportValidity()) return;
        const target = choice && choice !== "default" ? choice : input.value.trim();
        const revision = nodeTargetRevision;
        const sequence = ++activeNodeProbe;
        const client = appConfig.clients.find(item => item.id === btn.dataset.id);
        const pill = btn.querySelector(".rtt-pill");
        btn.disabled = true;
        pill.textContent = "检测中";
        try {
          const result = await postJson("/api/node-test", {...nodeRequest(client), target_url: target});
          if (revision !== nodeTargetRevision) return;
          pill.textContent = result.success ? "HTTP 成功" : "查看结果";
          pill.style.color = result.success ? "var(--success)" : "var(--warning)";
          if (sequence === activeNodeProbe) showNodeResult(client, result);
        } catch (error) {
          if (revision !== nodeTargetRevision) return;
          pill.textContent = "请求失败";
          alert(error.message);
        } finally {
          btn.disabled = false;
        }
      });
    });

    topClientsTbody.querySelectorAll("[data-action='clone-client']").forEach(btn => {
      btn.addEventListener("click", () => {
        const cid = btn.getAttribute("data-id");
        openClientModal("clone", cid);
      });
    });

    topClientsTbody.querySelectorAll("[data-action='edit-client']").forEach(btn => {
      btn.addEventListener("click", () => {
        const cid = btn.getAttribute("data-id");
        openClientModal("edit", cid);
      });
    });

    topClientsTbody.querySelectorAll("[data-action='delete-client']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const cid = btn.getAttribute("data-id");
        const client = cachedClients.find(item => item.id === cid);
        if (!client) return;
        if (!confirm(`停止托管并删除节点 "${cid}"？\n已有托管先恢复并独立核验，失败将保留登记。删除会移除认证资料，仅保留加回所需非敏感信息。`)) return;
        try {
          const res = await fetch("/api/clients/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: cid, node_revision: client.node_revision ?? 0 })
          });
          const d = await res.json();
          if (d.success) {
            await loadConfig();
          } else {
            await loadConfig();
            alert("删除未完成，登记保留: " + (d.error || d.message));
          }
        } catch (e) {
          alert("删除异常: " + e.message);
        }
      });
    });

    topClientsTbody.querySelectorAll("[data-action='test-client']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const host = btn.getAttribute("data-host");
        const port = parseInt(btn.getAttribute("data-port") || "22", 10);
        btn.textContent = "⏳...";
        try {
          const res = await fetch("/api/test-host", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ host, port })
          });
          const d = await res.json();
          if (d.online) {
            alert(`🟢 主机连通正常 (${host}:${port})，耗时: ${d.latency_ms} ms`);
          } else {
            alert(`⚠️ 主机网络可达性预检未通过 (${host}:${port})`);
          }
        } catch (e) {
          alert("探测异常: " + e.message);
        } finally {
          btn.textContent = "⚡ 连通探测";
        }
      });
    });
  }

  function renderClientsTable() {
    cachedClients = appConfig.clients || [];
    const known = new Set(cachedClients.map(client => client.id));
    for (const id of nodeTargets.keys()) if (!known.has(id)) nodeTargets.delete(id);
    updateNodeStatsBadge();
    renderClientsTableRows(filterClientsList());
  }

  if (nodeSearchInput) {
    nodeSearchInput.addEventListener("input", () => {
      renderClientsTableRows(filterClientsList());
    });
  }
  if (nodeFilterType) {
    nodeFilterType.addEventListener("change", () => {
      renderClientsTableRows(filterClientsList());
    });
  }

  // 一键全部开启出海
  topEnableAllBtn?.addEventListener("click", async () => {
    const selected = filterClientsList();
    if (!selected.length || !confirm(`开启当前显示的 ${selected.length} 个节点？每个节点必须保存自己的网关绑定。`)) return;
    const selections = selected.map(nodeRequest);
    topEnableAllBtn.disabled = true;
    topEnableAllBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在批量下发...';
    try {
      const res = await fetch("/api/nodes/batch-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "on", nodes: selections })
      });
      const d = await res.json();
      await loadConfig();
      alert([d.message || d.error || "操作未完成", ...(d.results || []).filter(item => !item.success).map(item => item.name + " · " + item.error)].join("\n"));
    } catch (e) {
      alert("批量下发异常: " + e.message);
    } finally {
      topEnableAllBtn.disabled = false;
      topEnableAllBtn.innerHTML = '<span class="btn-icon">⚡</span> 开启当前列表';
    }
  });

  // 按各节点的启用前快照批量恢复
  topDisableAllBtn?.addEventListener("click", async () => {
    const selected = filterClientsList();
    if (!selected.length) return;
    const selections = selected.map(nodeRequest);
    if (!confirm(`恢复当前显示的 ${selected.length} 个节点的启用前基线？原有代理可能继续生效；失败节点会保留登记。`)) {
      return;
    }
    topDisableAllBtn.disabled = true;
    topDisableAllBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在逐节点恢复...';
    try {
      const res = await fetch("/api/nodes/batch-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "off", nodes: selections })
      });
      const d = await res.json();
      await loadConfig();
      const failures = (d.results || []).filter(item => !item.success)
        .map(item => item.name + " · " + (item.error || "未恢复"));
      alert([d.message || d.error || "请查看各节点的恢复结果", ...failures, restoredProxyNote].join("\n"));
    } catch (e) {
      alert("切断异常: " + e.message);
    } finally {
      topDisableAllBtn.disabled = false;
      topDisableAllBtn.innerHTML = '<span class="btn-icon">🛑</span> 恢复当前列表';
    }
  });

  // 全网并发健康巡检
  topHealthCheckBtn?.addEventListener("click", async () => {
    if (!nodeTargetUrl.reportValidity()) return;
    const target = nodeTargetUrl.value.trim();
    const revision = nodeTargetRevision;
    topHealthCheckBtn.disabled = true;
    topHealthCheckBtn.textContent = "巡检中…";
    try {
      const data = await postJson("/api/nodes/health-check-all", {target_url: target});
      if (revision !== nodeTargetRevision) return;
      const summary = ["目标 · " + target];
      for (const [id, result] of Object.entries(data.health_map || {})) {
        const count = [result.explicit_proxy, result.ordinary_request].filter(check => check?.online).length;
        const status = result.explicit_proxy ? count + "/2 路 HTTP 成功" : nodeCheckLabel(result);
        const pill = document.getElementById("rtt-" + id);
        if (pill) { pill.textContent = status; pill.style.color = count === 2 ? "var(--success)" : "var(--warning)"; }
        summary.push(id + " · " + status);
      }
      alert(summary.join("\n"));
    } catch (error) {
      alert("巡检异常：" + error.message);
    } finally {
      topHealthCheckBtn.disabled = false;
      topHealthCheckBtn.textContent = "全网巡检";
    }
  });

  // 审计日志抽屉弹窗
  async function loadAuditLogs() {
    if (!auditTableTbody) return;
    auditTableTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:18px;">正在读取审计流水...</td></tr>';
    try {
      const res = await fetch("/api/audit-logs");
      const d = await res.json();
      auditTableTbody.innerHTML = "";
      if (!d.logs || d.logs.length === 0) {
        auditTableTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:18px;">暂无操作审计记录</td></tr>';
        return;
      }
      d.logs.forEach(item => {
        const tr = document.createElement("tr");
        const statusClass = item.status === "success" ? "success" : (item.status === "failed" || item.status === "error" ? "failed" : "info");
        const statusText = item.status === "success" ? "成功" : (item.status === "failed" ? "失败" : item.status);
        tr.innerHTML = `
          <td><code>${item.timestamp}</code></td>
          <td><strong>${escapeHtml(item.action)}</strong></td>
          <td><code>${escapeHtml(item.node_id)}</code></td>
          <td><span class="badge-audit ${statusClass}">${statusText}</span></td>
          <td style="color:var(--text-muted);word-break:break-all;">${escapeHtml(item.details || '-')}</td>
        `;
        auditTableTbody.appendChild(tr);
      });
    } catch (e) {
      auditTableTbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger);">加载失败: ${e.message}</td></tr>`;
    }
  }

  topAuditBtn?.addEventListener("click", () => {
    if (modalAudit) {
      modalAudit.style.display = "flex";
      loadAuditLogs();
    }
  });
  modalAuditClose?.addEventListener("click", () => { if (modalAudit) modalAudit.style.display = "none"; });
  modalAuditCloseBtn?.addEventListener("click", () => { if (modalAudit) modalAudit.style.display = "none"; });
  modalAuditRefreshBtn?.addEventListener("click", loadAuditLogs);



  // 渲染代理网关表格
  function renderGatewaysTable() {
    topGatewaysTbody.innerHTML = "";
    const gateways = appConfig.gateways || [];

    gateways.forEach(g => {
      const isDefault = (g.id === appConfig.active_gateway_id);
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(g.name)}</strong></td>
        <td><code>${escapeHtml(g.host)}</code></td>
        <td>${g.port}</td>
        <td>${(g.protocol || 'http').toUpperCase()}</td>
        <td>${isDefault ? '<span class="t-pill success">默认网关</span>' : '<span style="color:var(--text-dim)">备用</span>'}</td>
        <td style="color:var(--text-muted); font-size:12px;">${escapeHtml(g.description || '-')}</td>
        <td>
          <div class="table-actions">
            ${!isDefault ? `<button class="btn-mini" data-action="set-default-gw" data-id="${escapeHtml(g.id)}">设为默认</button>` : ''}
            <button class="btn-mini" data-action="test-gw" data-host="${escapeHtml(g.host)}" data-port="${escapeHtml(g.port)}">⚡ 测通</button>
            <button class="btn-mini" data-action="edit-gw" data-id="${escapeHtml(g.id)}">✏️ 编辑</button>
            ${!isDefault ? `<button class="btn-mini btn-danger" data-action="delete-gw" data-id="${escapeHtml(g.id)}">🗑️ 删除</button>` : ''}
          </div>
        </td>
      `;
      topGatewaysTbody.appendChild(tr);
    });

    // 绑定网关操作
    topGatewaysTbody.querySelectorAll("[data-action='set-default-gw']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const gid = btn.getAttribute("data-id");
        await fetch("/api/set-active-gateway", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ gateway_id: gid })
        });
        await loadConfig();
      });
    });

    topGatewaysTbody.querySelectorAll("[data-action='test-gw']").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!gatewayTargetUrl.reportValidity()) return;
        const host = btn.getAttribute("data-host");
        const port = btn.getAttribute("data-port");
        btn.textContent = "⏳...";
        try {
          const res = await fetch("/api/test-gateway", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({host, port, target_url: gatewayTargetUrl.value.trim()})
          });
          const d = await res.json();
          alert(probeSummary(d));
        } catch (e) {
          alert("探测异常: " + e.message);
        } finally {
          btn.textContent = "⚡ 测通";
        }
      });
    });

    topGatewaysTbody.querySelectorAll("[data-action='edit-gw']").forEach(btn => {
      btn.addEventListener("click", () => {
        const gid = btn.getAttribute("data-id");
        openGatewayModal("edit", gid);
      });
    });

    topGatewaysTbody.querySelectorAll("[data-action='delete-gw']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const gid = btn.getAttribute("data-id");
        if (!confirm(`确定要删除网关【${gid}】吗？`)) return;
        const res = await fetch("/api/gateways/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: gid })
        });
        const d = await res.json();
        if (d.success) {
          await loadConfig();
        } else {
          alert("删除网关失败: " + d.error);
        }
      });
    });
  }

  // 保存白名单
  topSaveNoproxyBtn.addEventListener("click", async () => {
    const val = topNoproxyInput.value.trim();
    try {
      const res = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ no_proxy: val })
      });
      if (res.ok) {
        topNoproxyHint.textContent = "✅ 直连白名单已保存";
        setTimeout(() => topNoproxyHint.textContent = "", 3000);
      }
    } catch (e) {
      alert("保存失败: " + e.message);
    }
  });

  // ==============================================================
  // 6. 模态弹窗与业务节点增删改 (Client CRUD Modal)
  // ==============================================================
  if (formClientAccessMode) {
    formClientAccessMode.addEventListener("change", () => {
      const mode = formClientAccessMode.value;
      if (mode === "ssh") {
        if (sectionAccessSsh) sectionAccessSsh.style.display = "block";
        if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "none";
      } else {
        if (sectionAccessSsh) sectionAccessSsh.style.display = "none";
        if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = mode === "docker_host" ? "block" : "none";
      }
      if (mode === "local") formClientHint.textContent = "本机模式使用运行控制台的账号；SSH 身份不会用于本机命令。";
    });
  }

  if (formClientAuthType) {
    formClientAuthType.addEventListener("change", () => {
      const auth = formClientAuthType.value;
      if (formGroupClientPass) {
        formGroupClientPass.style.display = (auth === "password") ? "block" : "none";
      }
    });
  }

  if (formClientOs) {
    formClientOs.addEventListener("change", () => {
      const os = formClientOs.value;
      if (os === "docker") {
        if (formClientPort && (!formClientPort.value || formClientPort.value === "22")) {
          formClientPort.value = "6600";
        }
        if (formClientPort) formClientPort.placeholder = "例如: 6600 (容器映射 SSH 端口)";
        if (formClientSshUser && (!formClientSshUser.value || formClientSshUser.value === "ubuntu")) {
          formClientSshUser.value = "root";
        }
        if (formClientHint) {
          formClientHint.style.color = "var(--primary)";
          formClientHint.textContent = "💡 容器有 SSH 服务时填写映射端口；通过宿主机管理时请选择 Docker 穿透模式。";
        }
      } else if (os === "linux") {
        if (formClientPort && formClientPort.value === "6600") {
          formClientPort.value = "22";
        }
        if (formClientPort) formClientPort.placeholder = "标准 SSH 端口 22";
        if (formClientSshUser && formClientSshUser.value === "root") {
          formClientSshUser.value = "ubuntu";
        }
        if (formClientHint) formClientHint.textContent = "";
      }
    });
  }

  function openClientModal(mode, cid = null) {
    const edited = appConfig.clients.find(client => client.id === cid);
    formClientMode.dataset.bindingRevision = edited?.binding_revision || 0;
    formClientMode.dataset.nodeRevision = edited?.node_revision || 0;
    formClientMode.dataset.legacyLocalHost = edited?.identity_confirmation_required ? edited.host : "";
    formClientHint.textContent = "";

    // 填充网关下拉框
    formClientGw.innerHTML = "";
    formClientGw.add(new Option("未绑定（保存后再选择开启）", ""));
    (appConfig.gateways || []).forEach(g => {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = `${g.name} (${g.host}:${g.port})`;
      formClientGw.appendChild(opt);
    });

    if (mode === "add" || mode === "clone") {
      formClientMode.value = "add";
      modalClientTitle.textContent = (mode === "clone") ? "📋 克隆登记新节点" : "➕ 登记新业务节点";

      if (mode === "clone") {
        const target = (appConfig.clients || []).find(c => c.id === cid);
        if (target) {
          formClientId.value = `${target.id}-copy`;
          formClientId.disabled = false;
          formClientName.value = `${target.name} (副本)`;
          formClientHost.value = target.host || "";
          if (formClientPort) formClientPort.value = target.port || 22;
          formClientOs.value = target.os_type || "linux";
          formClientGw.value = target.bound_gateway_id || "";

          const accessMode = target.access_mode || (target.container_name && !target.port ? "docker_host" : "ssh");
          if (formClientAccessMode) formClientAccessMode.value = accessMode;
          if (accessMode === "docker_host") {
            if (sectionAccessSsh) sectionAccessSsh.style.display = "none";
            if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "block";
            if (formClientContainer) formClientContainer.value = target.container_name || "";
            formClientHostPort.value = target.port || 22;
            if (formClientSshHost) formClientSshHost.value = target.ssh_host || target.host || "";
            if (formClientSshUserHost) formClientSshUserHost.value = target.ssh_user || "ubuntu";
          } else {
            if (sectionAccessSsh) sectionAccessSsh.style.display = "block";
            if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "none";
            if (formClientSshUser) formClientSshUser.value = target.ssh_user || (target.os_type === "docker" ? "root" : "ubuntu");
            const authType = target.auth_type || (target.ssh_pass ? "password" : "key");
            if (formClientAuthType) formClientAuthType.value = authType;
            if (formGroupClientPass) formGroupClientPass.style.display = (authType === "password") ? "block" : "none";
            if (formClientSshPass) formClientSshPass.value = target.ssh_pass || "";
          }

          formClientTags.value = (target.tags || []).join(", ");
          formClientDesc.value = target.description || "";
          formClientAccessMode.dispatchEvent(new Event("change"));
          formClientHint.textContent = "请修改执行地址或身份；相同执行身份会保留原登记，密码需重新输入。";
          modalClient.style.display = "flex";
          return;
        }
      }

      formClientId.value = "";
      formClientId.disabled = false;
      formClientName.value = "";
      formClientHost.value = "";
      if (formClientPort) formClientPort.value = "22";
      formClientOs.value = "linux";
      if (formClientAccessMode) formClientAccessMode.value = "ssh";
      if (sectionAccessSsh) sectionAccessSsh.style.display = "block";
      if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "none";
      if (formClientAuthType) formClientAuthType.value = "key";
      if (formGroupClientPass) formGroupClientPass.style.display = "none";
      if (formClientSshPass) formClientSshPass.value = "";
      if (formClientSshUser) formClientSshUser.value = "root";
      if (formClientContainer) formClientContainer.value = "";
      formClientHostPort.value = 22;
      if (formClientSshHost) formClientSshHost.value = "";
      if (formClientSshUserHost) formClientSshUserHost.value = "ubuntu";
      formClientTags.value = "";
      formClientDesc.value = "";
    } else {
      formClientMode.value = "edit";
      modalClientTitle.textContent = "✏️ 编辑业务节点";
      const target = (appConfig.clients || []).find(c => c.id === cid);
      if (!target) return;
      formClientId.value = target.id;
      formClientId.disabled = true; // ID不可改
      formClientName.value = target.name || "";
      formClientHost.value = target.host || "";
      if (formClientPort) formClientPort.value = target.port || 22;
      formClientOs.value = target.os_type || "linux";
      formClientGw.value = target.bound_gateway_id || "";

      const accessMode = target.access_mode || (target.container_name && !target.port ? "docker_host" : "ssh");
      if (formClientAccessMode) formClientAccessMode.value = accessMode;
      if (accessMode === "docker_host") {
        if (sectionAccessSsh) sectionAccessSsh.style.display = "none";
        if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "block";
        if (formClientContainer) formClientContainer.value = target.container_name || "";
        formClientHostPort.value = target.port || 22;
        if (formClientSshHost) formClientSshHost.value = target.ssh_host || target.host || "";
        if (formClientSshUserHost) formClientSshUserHost.value = target.ssh_user || "ubuntu";
      } else {
        if (sectionAccessSsh) sectionAccessSsh.style.display = "block";
        if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "none";
        if (formClientSshUser) formClientSshUser.value = target.ssh_user || (target.os_type === "docker" ? "root" : "ubuntu");
        const authType = target.auth_type || (target.ssh_pass ? "password" : "key");
        if (formClientAuthType) formClientAuthType.value = authType;
        if (formGroupClientPass) formGroupClientPass.style.display = (authType === "password") ? "block" : "none";
        if (formClientSshPass) formClientSshPass.value = target.ssh_pass || "";
      }

      formClientTags.value = (target.tags || []).join(", ");
      formClientDesc.value = target.description || "";
    }

    formClientAccessMode.dispatchEvent(new Event("change"));
    if (edited?.identity_confirmation_required) formClientHint.textContent = "旧记录曾按本机执行。请先选择本机模式保存并恢复基线，再迁移到 SSH。";
    modalClient.style.display = "flex";
  }

  wizardOpenAddClientBtn.addEventListener("click", () => openClientModal("add"));
  topAddClientBtn.addEventListener("click", () => openClientModal("add"));
  modalClientClose.addEventListener("click", () => modalClient.style.display = "none");

  // 深度全链路预检主机
  modalClientTestBtn.addEventListener("click", async () => {
    const accessMode = formClientAccessMode ? formClientAccessMode.value : "ssh";
    const host = accessMode === "local" ? "localhost" : formClientHost.value.trim();
    const port = Number((accessMode === "docker_host" ? formClientHostPort.value : formClientPort.value) || 22);
    const osType = formClientOs ? formClientOs.value : "linux";
    const authType = formClientAuthType ? formClientAuthType.value : "key";
    const sshUser = (accessMode === "docker_host" ? formClientSshUserHost.value : formClientSshUser.value).trim();
    const sshPass = formClientSshPass ? formClientSshPass.value : "";
    const containerName = formClientContainer ? formClientContainer.value.trim() : "";
    const sshHost = formClientSshHost ? formClientSshHost.value.trim() : host;

    if (accessMode === "docker_host") {
      if (!sshHost || !containerName) {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = "❌ 请先填写宿主机 IP 和 Docker 容器内部名称";
        return;
      }
    } else {
      if (!host) {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = "❌ 请先填写目标主机 IP";
        return;
      }
    }

    modalClientTestBtn.disabled = true;
    modalClientTestBtn.innerHTML = '<span class="btn-icon">⏳</span> 深度预检中...';
    formClientHint.style.color = "var(--primary)";
    formClientHint.textContent = "🔍 正在进行三阶深度预检 (TCP握手 -> SSH协议Banner -> 凭据鉴权)...";

    try {
      const res = await fetch("/api/test-node-preflight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          host,
          port,
          node_id: formClientMode.value === "edit" ? formClientId.value : undefined,
          os_type: osType,
          access_mode: accessMode,
          auth_type: authType,
          ssh_user: sshUser,
          ssh_pass: sshPass,
          container_name: containerName,
          ssh_host: sshHost
        })
      });
      const d = await res.json();
      if (d.success) {
        formClientHint.style.color = "var(--success)";
        formClientHint.textContent = d.message || d.error;
      } else {
        formClientHint.style.color = d.tcp_ok ? "var(--warning)" : "var(--danger)";
        formClientHint.textContent = d.message || d.error;
      }
    } catch (e) {
      formClientHint.style.color = "var(--danger)";
      formClientHint.textContent = `探测异常: ${e.message}`;
    } finally {
      modalClientTestBtn.disabled = false;
      modalClientTestBtn.innerHTML = '<span class="btn-icon">⚡</span> 预检主机连通性';
    }
  });

  // 保存业务节点
  modalClientSaveBtn.addEventListener("click", async () => {
    const mode = formClientMode.value;
    const cid = formClientId.value.trim();
    const name = formClientName.value.trim();
    const osType = formClientOs.value;
    const boundGw = formClientGw.value;
    const tags = formClientTags.value.split(",").map(t => t.trim()).filter(Boolean);
    const desc = formClientDesc.value.trim();
    const accessMode = formClientAccessMode ? formClientAccessMode.value : "ssh";

    let host = "";
    let port = 22;
    let sshUser = "";
    let authType = "key";
    let sshPass = "";
    let containerName = undefined;
    let sshHost = undefined;

    if (accessMode === "local") {
      host = formClientMode.dataset.legacyLocalHost || "localhost";
      port = 22;
      sshUser = formClientSshUser.value.trim();
      if (!name) { formClientHint.textContent = "请填写节点名称"; return; }
    } else if (accessMode === "docker_host") {
      host = formClientSshHost ? formClientSshHost.value.trim() : "";
      containerName = formClientContainer ? formClientContainer.value.trim() : "";
      sshHost = host;
      port = Number(formClientHostPort.value || 22);
      sshUser = formClientSshUserHost ? formClientSshUserHost.value.trim() : "ubuntu";
      authType = "key";
      if (!name || !host || !containerName) {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = "❌ 请填写节点名称、宿主机 IP 以及 Docker 容器名称";
        return;
      }
    } else {
      host = formClientHost.value.trim();
      port = parseInt((formClientPort ? formClientPort.value.trim() : "22") || "22", 10);
      sshUser = formClientSshUser ? formClientSshUser.value.trim() : "root";
      authType = formClientAuthType ? formClientAuthType.value : "key";
      sshPass = formClientSshPass ? formClientSshPass.value : "";
      if (!name || !host) {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = "❌ 请填写节点名称和主机 IP";
        return;
      }
    }

    const endpoint = mode === "add" ? "/api/clients/add" : "/api/clients/update";
    const payload = {
      id: cid || undefined,
      name,
      host,
      port,
      os_type: osType,
      bound_gateway_id: boundGw,
      binding_revision: mode === "edit" ? Number(formClientMode.dataset.bindingRevision || 0) : undefined,
      node_revision: mode === "edit" ? Number(formClientMode.dataset.nodeRevision || 0) : undefined,
      confirm_execution_mode: mode === "edit",
      access_mode: accessMode,
      auth_type: authType,
      ssh_user: sshUser,
      ssh_pass: sshPass || undefined,
      container_name: containerName,
      ssh_host: sshHost,
      tags,
      description: desc
    };

    modalClientSaveBtn.disabled = true;
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        modalClient.style.display = "none";
        await loadConfig();
        // 自动选中新加的节点
        if (data.client && mode === "add") {
          wizardClientSelect.value = data.client.id;
          wizardClientSelect.dispatchEvent(new Event("change"));
        }
      } else {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = `❌ ${data.error}${mode === "edit" ? "。请关闭并重新打开编辑，核对最新记录后重试。" : ""}`;
        await loadConfig();
      }
    } catch (e) {
      formClientHint.style.color = "var(--danger)";
      formClientHint.textContent = `保存异常: ${e.message}`;
    } finally {
      modalClientSaveBtn.disabled = false;
    }
  });

  // ==============================================================
  // 7. 网关增删改模态框 (Gateway CRUD Modal)
  // ==============================================================
  function openGatewayModal(mode, gid = null) {
    formGwMode.value = mode;
    formGwHint.textContent = "";

    if (mode === "add") {
      modalGwTitle.textContent = "➕ 添加新代理网关";
      formGwId.value = "";
      formGwId.disabled = false;
      formGwName.value = "";
      formGwHost.value = "";
      formGwPort.value = "7890";
      formGwProtocol.value = "http";
      formGwDesc.value = "";
    } else {
      modalGwTitle.textContent = "✏️ 编辑代理网关";
      const target = (appConfig.gateways || []).find(g => g.id === gid);
      if (!target) return;
      formGwId.value = target.id;
      formGwId.disabled = true;
      formGwName.value = target.name || "";
      formGwHost.value = target.host || "";
      formGwPort.value = target.port || 7890;
      formGwProtocol.value = target.protocol || "http";
      formGwDesc.value = target.description || "";
    }

    modalGateway.style.display = "flex";
  }

  topAddGwBtn.addEventListener("click", () => openGatewayModal("add"));
  modalGwClose.addEventListener("click", () => modalGateway.style.display = "none");

  modalGwTestBtn.addEventListener("click", async () => {
    if (!modalTargetUrl.reportValidity()) return;
    const host = formGwHost.value.trim();
    const port = formGwPort.value.trim();
    if (!host || !port) {
      formGwHint.textContent = "❌ 请填写网关主机与端口";
      return;
    }
    modalGwTestBtn.disabled = true;
    try {
      const res = await fetch("/api/test-gateway", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({host, port, target_url: modalTargetUrl.value.trim()})
      });
      const d = await res.json();
      if (d.online) {
        formGwHint.style.color = "var(--success)";
        formGwHint.textContent = probeSummary(d);
      } else {
        formGwHint.style.color = "var(--danger)";
        formGwHint.textContent = probeSummary(d);
      }
    } catch (e) {
      formGwHint.style.color = "var(--danger)";
      formGwHint.textContent = `测试异常: ${e.message}`;
    } finally {
      modalGwTestBtn.disabled = false;
    }
  });

  modalGwSaveBtn.addEventListener("click", async () => {
    const mode = formGwMode.value;
    const gid = formGwId.value.trim();
    const name = formGwName.value.trim();
    const host = formGwHost.value.trim();
    const port = formGwPort.value.trim();
    const protocol = formGwProtocol.value;
    const desc = formGwDesc.value.trim();

    if (!name || !host || !port) {
      formGwHint.style.color = "var(--danger)";
      formGwHint.textContent = "❌ 请填写网关名称、主机 IP 和端口";
      return;
    }

    const endpoint = mode === "add" ? "/api/gateways/add" : "/api/gateways/update";
    const payload = {
      id: gid || undefined,
      name,
      host,
      port: parseInt(port),
      protocol,
      description: desc
    };

    modalGwSaveBtn.disabled = true;
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        modalGateway.style.display = "none";
        await loadConfig();
      } else {
        formGwHint.style.color = "var(--danger)";
        formGwHint.textContent = `❌ ${data.error}`;
      }
    } catch (e) {
      formGwHint.style.color = "var(--danger)";
      formGwHint.textContent = `保存异常: ${e.message}`;
    } finally {
      modalGwSaveBtn.disabled = false;
    }
  });

  // ==============================================================
  // 8. 辅助功能与全局轻量预检
  // ==============================================================
  async function initPrecheck() {
    const gateway = businessGateway();
    const target = sbCmdInput.value.trim();
    if (!gateway || !sbCmdInput.reportValidity()) return;
    sbQuickDiagBtn.disabled = true;
    try {
      const data = await postJson("/api/test-gateway", {...gateway, target_url: target});
      if (businessGateway()?.id !== gateway.id || sbCmdInput.value.trim() !== target) return;
      showBusinessMetrics(data);
      sbTerminalOutput.textContent = probeSummary(data);
    } catch (error) {
      sbTerminalOutput.textContent = error.message;
    } finally {
      sbQuickDiagBtn.disabled = false;
    }
  }

  function attachCopyButtons(container) {
    container.querySelectorAll(".btn-copy").forEach(btn => {
      btn.addEventListener("click", () => {
        let textToCopy = btn.getAttribute("data-copy");
        if (!textToCopy) {
          const targetId = btn.getAttribute("data-target");
          if (targetId) {
            const el = document.getElementById(targetId);
            if (el) textToCopy = el.innerText;
          }
        }
        if (textToCopy) {
          navigator.clipboard.writeText(textToCopy).then(() => {
            const oldText = btn.textContent;
            btn.textContent = "已复制! ✓";
            btn.classList.add("copied");
            setTimeout(() => {
              btn.textContent = oldText;
              btn.classList.remove("copied");
            }, 2000);
          });
        }
      });
    });
  }

  // 绑定开发者手册中的复制按钮
  attachCopyButtons(document.getElementById("tab-handbook"));
  attachCopyButtons(wizardProbeActions);

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // 启动加载
  loadConfig();
});
