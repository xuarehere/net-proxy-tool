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

  // Local observation gateway Elements
  const localGatewayStartBtn = document.getElementById("local-gateway-start");
  const localGatewayDemoBtn = document.getElementById("local-gateway-demo");
  const localGatewayStopBtn = document.getElementById("local-gateway-stop");
  const localGatewayState = document.getElementById("local-gateway-state");

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
      if (!res.ok) throw new Error(t("loadConfig") + res.status);
      appConfig = await res.json();
      renderAll();
      loadLocalGatewayState();
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
      globalStatusText.textContent = t("loadConfig-2");
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
  // Each node keeps its own test number and its own result, so two nodes can be
  // tested at the same time without one result replacing the other.
  const nodeProbeSequences = new Map();
  const nodeProbeResults = new Map();
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
        new Option(t("refreshTargetOptions"), ""));
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
    if (result.http_ok || result.online) return t("probeConclusion") + result.code;
    const phase = {validation: t("probeConclusion-2"), proxy_tcp: t("probeConclusion-3"), proxy_tunnel: t("probeConclusion-4"),
      tls: t("probeConclusion-5"), http_response: t("probeConclusion-6"), response_body: t("probeConclusion-7")};
    const final = result.final_url || result.request_url || result.url;
    if (result.error_type === "timeout") {
      return (phase[result.stage] || t("probeConclusion-8")) + t("probeConclusion-9") + (final || t("probeConclusion-10")) + t("probeConclusion-11");
    }
    if (result.stage === "proxy_tunnel" || ["proxy_tunnel", "proxy_auth"].includes(result.error_type)) {
      return t("probeConclusion-12") + (result.error_type === "proxy_auth" ? t("probeConclusion-13") : t("probeConclusion-14")) +
        (result.code ? "（" + (result.stage === "proxy_tunnel" || result.connect_status === result.code ? "CONNECT " : "HTTP ") + result.code + "）" : "");
    }
    if (result.error_type?.startsWith("redirect_")) return result.error || t("probeConclusion-15");
    if (result.response_received && result.code) return t("probeConclusion-16") + result.code;
    return (phase[result.stage] || t("probeConclusion-17")) + t("probeConclusion-18") + (result.error ? " · " + result.error : "");
  }

  function probeEvidence(result) {
    const rows = [];
    if (result.proxy_url) rows.push(t("probeEvidence") + result.proxy_url);
    const start = result.request_url || result.url;
    if (start) rows.push(t("probeEvidence-2") + (result.method || "GET") + " " + start);
    for (const attempt of result.attempts || []) {
      const tls = {passed: t("probeEvidence-3"), eof: t("probeEvidence-4"), timeout: t("probeEvidence-5"),
        certificate_error: t("probeEvidence-6"), failed: t("probeEvidence-7")};
      const phases = [attempt.tcp_ok ? t("probeEvidence-8") : t("probeEvidence-9")];
      if (attempt.connect_status != null) phases.push("CONNECT " + attempt.connect_status);
      if (tls[attempt.tls]) phases.push(tls[attempt.tls]);
      if (attempt.http_status != null) phases.push("HTTP " + attempt.http_status);
      const redirect = (result.redirects || [])[attempt.hop - 1];
      if (redirect && attempt.http_status === redirect.code) phases.push(t("probeEvidence-10") + redirect.location);
      rows.push(t("probeEvidence-11") + attempt.hop + t("probeEvidence-12") + (attempt.attempt > 1 ? t("probeEvidence-13") : "") +
        " · " + attempt.url + "\n" + phases.join(" · ") + " · " + attempt.elapsed_ms + " ms");
    }
    if (!result.attempts?.length && result.tcp_ok != null) rows.push(t("probeEvidence-14") + (result.tcp_ok ? t("probeEvidence-15") : t("probeEvidence-16")));
    if (result.first_status != null || result.final_status != null) {
      rows.push((result.first_status ? t("probeEvidence-17") + result.first_status : t("probeEvidence-18")) + " → " +
        (result.final_status == null ? t("probeEvidence-19") : t("probeEvidence-20") + result.final_status));
    }
    if (result.tls_retries) rows.push(t("probeEvidence-21"));
    if (result.final_url && result.final_url !== start) rows.push(t("probeEvidence-22") + result.final_url);
    if (result.latency_ms != null) rows.push(t("probeEvidence-23") + result.latency_ms + " ms" +
      (result.budget_ms ? t("probeEvidence-24") + result.budget_ms / 1000 + t("probeEvidence-25") : ""));
    if (result.error_type === "timeout" && result.budget_expired) rows.push(t("probeEvidence-26"));
    if (result.response_received) rows.push(t("probeEvidence-27"));
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
    summary.textContent = t("renderProbe");
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
    setupName.value = gw?.name || t("selectSetupGateway");
    setupHost.value = gw?.host || "";
    setupPort.value = gw?.port || "";
    setupSave.textContent = gw ? t("selectSetupGateway-2") : t("selectSetupGateway-3");
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
    beginSetupSave(t("finishSetupSave"));
    try {
      await postJson("/api/set-active-gateway", {gateway_id: setupId});
      setupReady = false;
      if (!await loadConfig()) return;
      setupResult.textContent = t("finishSetupSave-2");
    } catch (error) {
      setupResult.textContent = error.message;
    } finally {
      finishSetupSave();
    }
  });

  setupForm.addEventListener("submit", async event => {
    event.preventDefault();
    beginSetupSave(t("finishSetupSave-3"));
    try {
      const payload = setupPayload();
      if (setupId) payload.id = setupId;
      const data = await postJson(setupId ? "/api/gateways/update" : "/api/gateways/add", payload);
      setupId = data.gateway.id;
      setupDirty = false;
      setupReady = false;
      if (!await loadConfig()) return;
      setupResult.textContent = t("finishSetupSave-4");
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
    setupResult.textContent = t("finishSetupSave-5");
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

  async function renderLocalGatewayState(state) {
    if (!state || !state.running) {
      localGatewayStopBtn.hidden = true;
      localGatewayStartBtn.hidden = false;
      localGatewayDemoBtn.hidden = false;
      localGatewayState.textContent = "";
      return state;
    }
    localGatewayStopBtn.hidden = false;
    localGatewayStartBtn.hidden = true;
    localGatewayDemoBtn.hidden = true;
    const seen = [...new Set((state.records || []).map(record => record.host + ":" + record.port))];
    localGatewayState.textContent = t("renderLocalGatewayState") + state.address +
      (seen.length ? "\n已访问：" + seen.join(", ") : "\n尚未收到请求。");
    return state;
  }

  async function loadLocalGatewayState() {
    try {
      const res = await fetch("/api/local-gateway");
      if (!res.ok) throw new Error(t("loadLocalGatewayState"));
      return await renderLocalGatewayState(await res.json());
    } catch (error) {
      localGatewayState.textContent = error.message;
      return null;
    }
  }

  async function localGatewayAction(action) {
    [localGatewayStartBtn, localGatewayDemoBtn, localGatewayStopBtn].forEach(btn => { btn.disabled = true; });
    try {
      const res = await fetch("/api/local-gateway", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || t("localGatewayAction"));
      await renderLocalGatewayState(data);
      await loadConfig();
      return data;
    } catch (error) {
      localGatewayState.textContent = error.message;
      return null;
    } finally {
      [localGatewayStartBtn, localGatewayDemoBtn, localGatewayStopBtn].forEach(btn => { btn.disabled = false; });
    }
  }

  localGatewayStartBtn.addEventListener("click", () => localGatewayAction("start"));
  localGatewayStopBtn.addEventListener("click", () => localGatewayAction("stop"));
  localGatewayDemoBtn.addEventListener("click", async () => {
    const state = await localGatewayAction("start");
    if (!state || !state.gateway) return;
    setupName.value = state.gateway.name || t("localGatewayAction-2");
    setupHost.value = state.gateway.host || "127.0.0.1";
    setupPort.value = String(state.gateway.port || "");
    setupUrl.value = "https://example.com/";
    setupTest.click();
  });

  // A language change re-renders the tables, so that the dynamic text follows it.
  document.addEventListener("npt-language", () => {
    if (appConfig) renderAll();
  });

  function renderAll() {
    refreshTargetOptions();
    const gateways = appConfig.gateways || [];
    activeGateway = gateways.find(g => g.id === appConfig.active_gateway_id) || gateways[0] || null;

    setupSelect.replaceChildren(new Option(t("renderAll"), ""));
    gateways.forEach(gw => setupSelect.add(new Option(t("renderAll-2") + gw.name + " (" + gw.host + ":" + gw.port + ")", gw.id)));
    if (setupDirty && (!setupId || gateways.some(gw => gw.id === setupId))) {
      setupSelect.value = setupId;
      setupDefault.hidden = !setupId || setupId === activeGateway?.id;
    } else {
      selectSetupGateway(setupId === null ? activeGateway?.id : setupId);
    }

    globalStatusPill.querySelector(".status-indicator-dot").className = "status-indicator-dot";
    globalStatusPill.title = t("renderAll-3");
    if (activeGateway) {
      const gwStr = `${activeGateway.host}:${activeGateway.port}`;
      globalStatusText.textContent = t("renderAll-4", {gwStr});
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
      wizardTestGwBtn.textContent = t("resetWizard");
      wizardProbeActions.hidden = true;
      readOnlyOutput.textContent = "";
      step1Complete = false;
      cardStep2.classList.add("locked-card");
      cardStep2.inert = true;
      pipeStep2.className = "pipeline-step locked";
      pipeStep1.className = "pipeline-step active";
      pipeStep1.querySelector(".pipe-num").textContent = "1";
      pipeStep1.querySelector(".pipe-name").textContent = t("resetWizard-2");
      statusTagStep1.className = "step-status-tag";
      statusTagStep1.textContent = t("resetWizard-3");
      step1Result.className = "step-result-banner";
      step1Result.textContent = t("resetWizard-4");
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
    statusTagStep2.textContent = t("resetWizard-5");
    statusTagStep3.textContent = t("resetWizard-6");
    statusTagStep4.textContent = t("resetWizard-7");
    wizardTargetGrid.replaceChildren();
    handoverTargetName.textContent = handoverGwName.textContent = wizardTargetDispName.textContent = t("resetWizard-8");
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
    const firstLabel = initial ? t("httpJourney") + initial : t("httpJourney-2");
    const lastLabel = final ? t("httpJourney-3") + final : t("httpJourney-4");
    return firstLabel + " → " + lastLabel;
  }

  function formatPeer(ip, port) {
    if (!ip) return t("formatPeer");
    return (ip.includes(":") ? "[" + ip + "]" : ip) + (port ? ":" + port : "");
  }

  function nodeCheckLines(check) {
    if (!check) return [t("nodeCheckLines")];
    const lines = [httpJourney(check)];
    if (check.execution_context) lines.push(t("nodeCheckLines-2") + (check.execution_context === "fresh_login_shell" ? t("nodeCheckLines-3") : t("nodeCheckLines-4")));
    const transports = {local: t("nodeCheckLines-5"), ssh: t("nodeCheckLines-6"), ssh_docker_exec: t("nodeCheckLines-7")};
    if (transports[check.transport]) lines.push(t("nodeCheckLines-8") + transports[check.transport]);
    if (check.latency_ms != null) lines.push(t("nodeCheckLines-9") + check.latency_ms + " ms");
    if (check.auth_ok != null) lines.push(t("nodeCheckLines-10") + (check.auth_ok ? t("nodeCheckLines-11") : t("nodeCheckLines-12")));
    lines.push(t("nodeCheckLines-13") + (check.business_ok === false ? t("nodeCheckLines-14") :
      (check.business_ok === true ? t("nodeCheckLines-15") : t("nodeCheckLines-16"))));
    for (const hop of check.redirects || []) {
      lines.push("HTTP " + hop.code + " · " + hop.url + " → " + hop.location);
    }
    if (check.hops?.length > 1) {
      for (const [index, hop] of check.hops.entries()) {
        const peer = hop.peer || {};
        if (peer.ip) lines.push(t("nodeCheckLines-17") + (index + 1) + t("nodeCheckLines-18") + formatPeer(peer.ip, peer.port));
      }
    }
    if (check.final_url) lines.push(t("nodeCheckLines-19") + check.final_url);
    if (check.proxy_url) lines.push(t("nodeCheckLines-20") + check.proxy_url);
    const ip = check.peer?.ip || check.remote_ip;
    lines.push(t("nodeCheckLines-21") + formatPeer(ip, check.peer?.port));
    if (Number(check.connect_status) > 0) lines.push(t("nodeCheckLines-22") + check.connect_status);
    const route = {selected_proxy: t("nodeCheckLines-23"), matches_explicit_peer: t("nodeCheckLines-24"),
      different_peer: t("nodeCheckLines-25"), unknown: t("nodeCheckLines-26")};
    lines.push(t("nodeCheckLines-27") + (route[check.proxy_evidence?.status] || route.unknown));
    const identity = check.execution_identity;
    if (identity && Object.keys(identity).length) {
      lines.push([t("nodeCheckLines-28"), identity.user, identity.uid != null && ("UID " + identity.uid),
        identity.home && ("HOME=" + identity.home)].filter(Boolean).join(" · "));
      if (identity.curl_config) lines.push(t("nodeCheckLines-29") + identity.curl_config +
        (check.request_mode === "explicit_proxy" ? t("nodeCheckLines-30") : ""));
      if (identity.curl_home) lines.push("CURL_HOME=" + identity.curl_home);
      if (identity.xdg_config_home) lines.push("XDG_CONFIG_HOME=" + identity.xdg_config_home);
    }
    const stages = Object.entries(check.stages || {}).filter(([, state]) => state !== "skipped")
      .map(([stage, state]) => stage + "=" + state);
    if (stages.length) lines.push(stages.join(" · "));
    if (check.exit_code != null) lines.push(t("nodeCheckLines-31") + check.exit_code);
    if (check.error_type || check.error) lines.push([check.error_type, check.error].filter(Boolean).join(" · "));
    return lines;
  }

  function nodeCheckLabel(check) {
    return check?.online ? t("nodeCheckLabel") : t("nodeCheckLabel-2");
  }

  function nodeCheckPairs(result) {
    return [[t("nodeCheckPairs"), result.explicit_proxy], [t("nodeCheckPairs-2"), result.ordinary_request]];
  }

  const restoredProxyNote = t("nodeCheckPairs-3");

  function restoredEnvironmentNote(verification) {
    const env = verification?.restored_environment;
    if (!env?.observed) return "";
    const gateway = env.matched_gateway;
    const context = verification.verified && verification.verification_scope === "login_and_managed_files"
      ? t("restoredEnvironmentNote") : t("restoredEnvironmentNote-2");
    if (gateway) return t("restoredEnvironmentNote-3", {context, port_});
    return env.proxy_present ? t("restoredEnvironmentNote-4", {context}) : t("restoredEnvironmentNote-5", {context});
  }

  function nodeContext(result) {
    const check = result.ordinary_request || result.explicit_proxy || result;
    const enabled = result.is_proxy_enabled ?? check.is_proxy_enabled;
    const recorded = enabled == null ? t("nodeContext") : (enabled ? t("nodeContext-2") : t("nodeContext-3"));
    const states = {enabled: t("nodeContext-4"), disabled: t("nodeContext-5"), unknown: t("nodeContext-6")};
    const verification = result.verification || {};
    return [t("nodeContext-7") + (check.target_url || result.target_url || t("nodeContext-8")),
      t("nodeContext-9") + recorded,
      t("nodeContext-10") + (states[result.managed_state] || states.unknown),
      t("nodeContext-11") + ({login_and_managed_files: t("nodeContext-12"), managed_files_only: t("nodeContext-13"), managed_files: t("nodeContext-14")}[verification.verification_scope] || t("nodeContext-15")),
      restoredEnvironmentNote(verification), t("nodeContext-16")].filter(Boolean).join("\n");
  }

  function nodeProbeSummary(result) {
    if (!result.explicit_proxy && !result.ordinary_request) return result.error || result.message || t("nodeProbeSummary");
    return [nodeContext(result), ...nodeCheckPairs(result).map(([label, check]) =>
      [label + " · " + nodeCheckLabel(check), ...nodeCheckLines(check)].join("\n"))].join("\n\n");
  }

  function showNodeResult(client, result) {
    // Remember the result for this node, so a redraw keeps it and another
    // node's result never replaces it.
    nodeProbeResults.set(client.id, result);
    document.getElementById("node-test-heading").textContent = client.name + t("showNodeResult");
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
      opt.textContent = `${gw.name} (${gw.host}:${gw.port})` + (gw.id === appConfig.active_gateway_id ? t("renderWizardSelectors") : "");
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
    wMetaGw.textContent = boundGw ? `${boundGw.name} (${boundGw.host}:${boundGw.port})` : (client.bound_gateway_id || t("updateWizardClientMeta"));
    wMetaTags.textContent = (client.tags && client.tags.length) ? client.tags.join(", ") : t("updateWizardClientMeta-2");
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
    wizardTestGwBtn.innerHTML = t("updateWizardClientMeta-3");
    step1Result.className = "step-result-banner";
    step1Result.textContent = t("updateWizardClientMeta-4");

    try {
      const data = await postJson("/api/test-gateway", {...gateway, target_url: target});
      if (revision !== wizardProbeRevision) return;
      renderProbe(step1Result, data);
      wizardProbeActions.hidden = false;
      document.getElementById("wizard-probe-command").textContent = gatewayGetCommand(gateway, target);
      const bound = (appConfig.clients || []).filter(client => client.bound_gateway_id === gateway.id);
      readOnlyNode.replaceChildren(...bound.map(client => new Option(client.name, client.id)));
      if (!bound.length) readOnlyNode.add(new Option(t("updateWizardClientMeta-5"), ""));
      readOnlyNode.disabled = readOnlyTest.disabled = !bound.length;
      if (data.online) {
        step1Result.className = "step-result-banner success";
        statusTagStep1.className = "step-status-tag success";
        statusTagStep1.textContent = t("updateWizardClientMeta-6");
        pipeStep1.className = "pipeline-step completed";
        pipeStep1.innerHTML = t("updateWizardClientMeta-7");

        // 激活 Step 2
        unlockStep2();
      } else {
        step1Result.className = "step-result-banner error";
        statusTagStep1.className = "step-status-tag";
        statusTagStep1.textContent = t("updateWizardClientMeta-8");
      }
    } catch (err) {
      if (revision !== wizardProbeRevision) return;
      step1Result.className = "step-result-banner error";
      step1Result.textContent = t("updateWizardClientMeta-9") + err.message;
    } finally {
      if (revision === wizardProbeRevision) {
        wizardTestGwBtn.disabled = false;
        wizardTestGwBtn.textContent = t("updateWizardClientMeta-10");
      }
    }
  });

  readOnlyNode.addEventListener("change", () => { readOnlyOutput.textContent = ""; });
  readOnlyTest.addEventListener("click", async () => {
    const node = appConfig.clients.find(client => client.id === readOnlyNode.value);
    if (!node || node.bound_gateway_id !== selectedWizardGateway?.id) return;
    const revision = wizardProbeRevision;
    readOnlyNode.disabled = readOnlyTest.disabled = true;
    readOnlyOutput.textContent = t("updateWizardClientMeta-11") + node.name + t("updateWizardClientMeta-12");
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
        alert(t("updateWizardClientMeta-13", {name}));
      }
    } catch (e) {
      alert(t("updateWizardClientMeta-14") + e.message);
    }
  });

  function unlockStep2() {
    step1Complete = true;
    cardStep2.inert = false;
    cardStep2.classList.remove("locked-card");
    pipeStep2.classList.remove("locked");
    pipeStep2.classList.add("active");
    statusTagStep2.textContent = t("unlockStep2");
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
      if (data.client?.bound_gateway_id !== gateway.id) throw new Error(t("unlockStep2-2"));
      await loadConfig();
      if (selectedWizardClient?.id !== client.id || selectedWizardGateway?.id !== gateway.id) return;
      if (selectedWizardClient.bound_gateway_id !== gateway.id ||
          (selectedWizardClient.node_revision ?? 0) !== (data.client.node_revision ?? 0) ||
          (selectedWizardClient.binding_revision || 0) !== (data.client.binding_revision || 0)) {
        throw new Error(t("unlockStep2-3"));
      }
      step2Complete = true;
      statusTagStep2.textContent = t("unlockStep2-4") + client.name + " → " + gateway.name;
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
    statusTagStep3.textContent = t("unlockStep3");
    initTargetGridPlaceholder();
    cardStep3.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function initTargetGridPlaceholder() {
    wizardTargetGrid.innerHTML = "";
    const targets = appConfig.diagnostic_targets || {};
    if (!Object.keys(targets).length) wizardTargetGrid.textContent = t("initTargetGridPlaceholder");
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
    wizardStartDiagBtn.innerHTML = t("initTargetGridPlaceholder-2");
    statusTagStep3.textContent = t("initTargetGridPlaceholder-3");

    // 状态置为 testing
    const targets = appConfig.diagnostic_targets || {};
    Object.keys(targets).forEach(name => {
      const el = document.getElementById(`diag-item-${name}`);
      if (el) {
        el.querySelector(".t-pill").className = "t-pill testing";
        el.querySelector(".t-pill").textContent = t("initTargetGridPlaceholder-4");
      }
    });

    try {
      const gid = selectedWizardGateway ? selectedWizardGateway.id : appConfig.active_gateway_id;
      const res = await fetch(`/api/status?gateway_id=${encodeURIComponent(gid)}`);
      const data = await res.json();

      if (!step2Complete || selectedWizardClient?.id !== client.id || selectedWizardGateway?.id !== gateway.id) return;
      wizardDiagTime.textContent = t("initTargetGridPlaceholder-5", {timestamp});
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
          pill.textContent = t("initTargetGridPlaceholder-6", {code});
          rtt.textContent = `${target.latency_ms} ms`;
        } else {
          pill.className = "t-pill failed";
          pill.textContent = target.code ? "HTTP " + target.code : t("initTargetGridPlaceholder-7");
          rtt.textContent = target.error || t("initTargetGridPlaceholder-8");
          el.title = probeSummary(target);
        }
      });

      const emptyList = Object.keys(targets).length === 0;
      if (emptyList || (results.length && onlineCount >= Math.min(2, results.length))) {
        step3Complete = true;
        statusTagStep3.className = results.length && onlineCount === results.length ? "step-status-tag success" : "step-status-tag";
        statusTagStep3.textContent = emptyList ? t("initTargetGridPlaceholder-10") : t("initTargetGridPlaceholder-9", {onlineCount, length});
        pipeStep3.className = "pipeline-step completed";
        pipeStep3.querySelector(".pipe-name").textContent = emptyList ? t("initTargetGridPlaceholder-11") : t("initTargetGridPlaceholder-12");

        // 解锁 Step 4
        unlockStep4();
      } else {
        step3Complete = false;
        cardStep4.inert = true;
        cardStep4.classList.add("locked-card");
        statusTagStep3.className = "step-status-tag";
        statusTagStep3.textContent = t("initTargetGridPlaceholder-13", {onlineCount, length});
        alert(t("initTargetGridPlaceholder-14"));
      }
    } catch (err) {
      statusTagStep3.textContent = t("initTargetGridPlaceholder-15");
      alert(t("initTargetGridPlaceholder-16") + err.message);
    } finally {
      wizardStartDiagBtn.disabled = false;
      wizardStartDiagBtn.innerHTML = t("initTargetGridPlaceholder-17");
    }
  });

  function unlockStep4() {
    cardStep4.inert = false;
    cardStep4.classList.remove("locked-card");
    pipeStep4.classList.remove("locked");
    pipeStep4.classList.add("completed");
    pipeStep4.innerHTML = t("unlockStep4");
    statusTagStep4.textContent = t("unlockStep4-2");

    if (wizardSwitchBadge && selectedWizardClient) {
      if (selectedWizardClient.is_proxy_enabled) {
        wizardSwitchBadge.className = "switch-badge on";
        wizardSwitchBadge.textContent = t("unlockStep4-3");
      } else {
        wizardSwitchBadge.className = "switch-badge off";
        wizardSwitchBadge.textContent = t("unlockStep4-4");
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
    wizardBtnProxyOn.textContent = localWindows ? t("renderHandoverBlocks") : t("renderHandoverBlocks-2");
    wizardBtnProxyOff.hidden = localWindows;

    handoverTargetName.textContent = `${client.name} (${osType.toUpperCase()}, ${client.host})`;
    if (handoverGwName) handoverGwName.textContent = `${gw.host}:${gw.port}`;
    if (wizardTargetDispName) wizardTargetDispName.textContent = `${client.name} (${osType.toUpperCase()})`;
    if (wizardTargetDispSub) {
      if (osType === "docker") {
        wizardTargetDispSub.textContent = t("renderHandoverBlocks-3", {host, container_name_____app_container_});
      } else {
        wizardTargetDispSub.textContent = t("renderHandoverBlocks-4", {host, host_2, port});
      }
    }

    const isProxyOn = Boolean(client.is_proxy_enabled);
    if (wizardSwitchBadge) {
      wizardSwitchBadge.className = isProxyOn ? "switch-badge on" : "switch-badge off";
      wizardSwitchBadge.textContent = localWindows ? t("renderHandoverBlocks-5") : (client.applied_gateway_id && client.applied_gateway_id !== gw.id
        ? t("renderHandoverBlocks-6") : (isProxyOn ? t("renderHandoverBlocks-7") : t("renderHandoverBlocks-8")));
    }

    handoverBlocksContainer.innerHTML = "";

    let command;
    let title;
    if (osType === "windows") {
      title = t("renderHandoverBlocks-9");
      command = ".\\bin\\with-proxy.cmd --gateway " + gw.id + " curl.exe --location --url " + quoteTarget(wizardTestUrl.value, true);
    } else {
      title = t("renderHandoverBlocks-10");
      command = "curl --location --url " + quoteTarget(wizardTestUrl.value, false);
    }
    const card = document.createElement("div");
    card.className = "code-delivery-card";
    card.innerHTML = t("renderHandoverBlocks-11");
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

  function isLoopbackHost(host) {
    const name = String(host || "").trim().toLowerCase();
    if (!name) return false;
    if (name === "localhost") return true;
    if (name === "::1" || name === "0:0:0:0:0:0:0:1") return true;
    if (name.startsWith("::ffff:")) return isLoopbackHost(name.slice(7));
    return /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(name);
  }

  function positionDropdownMenu(wrap) {
    const menu = wrap && wrap.querySelector(".action-dropdown-menu");
    const toggle = wrap && wrap.querySelector(".btn-dropdown-toggle");
    if (!menu || !toggle) return;
    const rect = toggle.getBoundingClientRect();
    const width = menu.offsetWidth || 140;
    const height = menu.offsetHeight || 160;
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8));
    const top = Math.max(8, Math.min(rect.bottom + 4, window.innerHeight - height - 8));
    menu.style.left = left + "px";
    menu.style.top = top + "px";
  }

  function repositionOpenDropdown() {
    const wrap = document.querySelector(".action-dropdown-wrap.active");
    if (wrap) positionDropdownMenu(wrap);
  }

  window.addEventListener("scroll", repositionOpenDropdown, true);
  window.addEventListener("resize", repositionOpenDropdown);

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
      showWizardFeedback("warning", t("runWizardAction"), client.name + " → " + gateway.name);
      if (action === "test") {
        const data = await postJson("/api/node-test", {...nodeRequest(client), target_url: wizardTestUrl.value.trim()});
        showWizardFeedback(data.success ? "success" : "warning", client.name + t("runWizardAction-2"), nodeProbeSummary(data));
      } else {
        const data = await postJson("/api/node-switch", {...nodeRequest(client), action});
        await loadConfig();
        showWizardFeedback("success", client.name, action === "off" ? data.message + "\n" + restoredProxyNote : data.message);
      }
    } catch (error) {
      showWizardFeedback("error", t("runWizardAction-3"), error.message);
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
    sbGwOverrideSelect.replaceChildren(new Option(t("renderSandboxSelectors"), ""));
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
    sbActiveGwVal.textContent = gw ? gatewayAddress(gw) : t("resetBusinessMetrics");
    sbActiveGwSub.textContent = gw?.name || t("resetBusinessMetrics-2");
    sbGwStatusVal.textContent = sbDiagRateVal.textContent = t("resetBusinessMetrics-3");
    sbGwRttSub.textContent = sbDiagSummary.textContent = t("resetBusinessMetrics-4");
    sbTerminalOutput.textContent = t("resetBusinessMetrics-5");
    sbStatusBadge.textContent = t("resetBusinessMetrics-6");
  }

  function showBusinessMetrics(data) {
    sbGwStatusVal.textContent = data.tcp_ok == null ? t("showBusinessMetrics") : (data.tcp_ok ? t("showBusinessMetrics-2") : t("showBusinessMetrics-3"));
    sbGwRttSub.textContent = data.tcp_latency_ms != null ? data.tcp_latency_ms + " ms" : "";
    const finalCode = data.final_status ?? (data.response_received ? data.code : null);
    sbDiagRateVal.textContent = finalCode ? "HTTP " + finalCode : t("showBusinessMetrics-4");
    sbDiagSummary.textContent = data.error || data.final_url || data.request_url || "";
  }

  sbGwOverrideSelect.addEventListener("change", resetBusinessMetrics);
  sbCmdInput.addEventListener("input", resetBusinessMetrics);
  sbQuickDiagBtn.addEventListener("click", () => initPrecheck());
  sbClearTermBtn.addEventListener("click", () => { sbTerminalOutput.textContent = ""; });

  sbRunBtn.addEventListener("click", async () => {
    const gw = businessGateway();
    if (!gw) { sbTerminalOutput.textContent = t("showBusinessMetrics-5"); return; }
    if (!sbCmdInput.reportValidity()) return;
    const target = sbCmdInput.value.trim();
    const controls = [sbRunBtn, sbQuickDiagBtn, sbCmdInput, sbTemplateSelect, sbGwOverrideSelect];
    controls.forEach(control => control.disabled = true);
    sbStatusBadge.textContent = t("showBusinessMetrics-6");
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
      if (!result) throw new Error(t("showBusinessMetrics-7"));
      showBusinessMetrics(result);
      sbTerminalOutput.textContent = [gatewayAddress(gw) + " → " + target,
        probeSummary(result), result.headers, result.preview].filter(Boolean).join("\n\n");
      sbStatusBadge.textContent = result.success ? t("showBusinessMetrics-8") : t("showBusinessMetrics-9");
    } catch (error) {
      sbStatusBadge.textContent = t("showBusinessMetrics-10");
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
    nodeStatsBadge.textContent = t("updateNodeStatsBadge", {total, onCount, offCount, total___onCount___offCount});
  }

  const nodeTargets = new Map();

  function bindRowTarget(row, client) {
    const select = row.querySelector("[data-node-target]");
    const input = row.querySelector("[data-node-custom]");
    const options = document.querySelector('[data-target-input="node-target-url"]').options;
    select.add(new Option(t("bindRowTarget"), "default"));
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
      topClientsTbody.innerHTML = t("renderClientsTableRows");
      return;
    }

    clientsToRender.forEach(c => {
      const boundGw = (appConfig.gateways || []).find(g => g.id === c.bound_gateway_id);
      const localWindows = isWindowsWorkstation(c);
      const gwName = boundGw ? `${boundGw.name}` : (c.bound_gateway_id || t("renderClientsTableRows-2"));
      const tagsHtml = (c.tags || []).map(t => `<span class="tag-badge">${escapeHtml(t)}</span>`).join("");
      const isProxyOn = Boolean(c.is_proxy_enabled || c.pending_action);
      const verifiedState = c.managed_state || "unknown";
      const stateLabel = {enabled: t("renderClientsTableRows-3"), disabled: t("renderClientsTableRows-4"), unknown: t("renderClientsTableRows-5")}[verifiedState] || t("renderClientsTableRows-6");
      const isLocal = c.access_mode === "local";

      let addrBadge = t("renderClientsTableRows-7");
      let addrRow = `<code>${escapeHtml(c.ssh_user || 'root')}@${escapeHtml(c.host)}:${c.port || 22}</code>`;

      if (isLocal) {
        addrBadge = t("renderClientsTableRows-8");
        addrRow = t("renderClientsTableRows-9");
      } else if (c.access_mode === "docker_host" || (c.container_name && !c.port)) {
        addrBadge = t("renderClientsTableRows-10");
        addrRow = `<code>${escapeHtml(c.ssh_user || 'ubuntu')}@${escapeHtml(c.ssh_host || c.host)}:${c.port || 22}</code> <span style="font-size:11px;color:var(--text-dim);">&rarr; [${escapeHtml(c.container_name || c.name)}]</span>`;
      } else if (c.port && c.port != 22) {
        addrBadge = t("renderClientsTableRows-11", {port});
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
          <div style="font-size:11px;color:var(--text-dim);">${boundGw ? t("renderClientsTableRows-12", {port}) : ''}</div>
        </td>
        <td>
          <div class="status-capsule ${verifiedState === 'enabled' ? 'on' : verifiedState === 'disabled' ? 'off' : 'unknown'}">
            <span class="capsule-indicator">
              ${escapeHtml(stateLabel)}${c.identity_confirmation_required ? t("renderClientsTableRows-13") : ""}
            </span>
            <button class="capsule-btn ${isProxyOn ? 'btn-turn-off' : 'btn-turn-on'}" data-action="toggle-client" data-id="${escapeHtml(c.id)}" data-action-type="${isProxyOn ? 'off' : 'on'}">
              ${localWindows ? t("renderClientsTableRows-14") : (isProxyOn ? t("renderClientsTableRows-15") : t("renderClientsTableRows-16"))}
            </button>
          </div>
          ${c.managed_state === "disabled" ? `<div class="restoration-note">${escapeHtml(restoredEnvironmentNote(c.verification))}</div>` : ''}
        </td>
        <td style="text-align: right;">
          <div class="row-target"><select class="form-select" data-node-target aria-label=t("renderClientsTableRows-17")></select>
            <input type="url" class="form-input" data-node-custom required aria-label=t("renderClientsTableRows-18") placeholder="https://…" hidden></div>
          <div class="table-actions-modern">
            <button class="btn-speedtest" data-action="test-node-out" data-id="${escapeHtml(c.id)}" title=t("renderClientsTableRows-19")>
              🔍 测外网 <span class="rtt-pill" id="rtt-${escapeHtml(c.id)}"></span>
            </button>
            <div class="action-dropdown-wrap">
              <button class="btn-dropdown-toggle" title=t("renderClientsTableRows-20")>•••</button>
              <div class="action-dropdown-menu">
                <button class="dropdown-item" data-action="edit-client" data-id="${escapeHtml(c.id)}">✏️ 编辑参数</button>
                <button class="dropdown-item" data-action="clone-client" data-id="${escapeHtml(c.id)}">📋 克隆节点</button>
                <button class="dropdown-item" data-action="test-client" data-id="${escapeHtml(c.id)}" data-host="${escapeHtml(c.host)}" data-port="${c.port || 22}">⚡ 连通探测</button>
                ${!localWindows ? t("renderClientsTableRows-21", {id_}) : ''}
                <button class="dropdown-item danger" data-action="delete-client" data-id="${escapeHtml(c.id)}">🗑️ 删除节点</button>
              </div>
            </div>
          </div>
        </td>
      `;
      bindRowTarget(tr, c);
      topClientsTbody.appendChild(tr);
      const stored = nodeProbeResults.get(c.id);
      if (stored) {
        const pill = tr.querySelector(".rtt-pill");
        if (pill) {
          pill.textContent = stored.success ? t("renderClientsTableRows-22") : t("renderClientsTableRows-23");
          pill.style.color = stored.success ? "var(--success)" : "var(--warning)";
        }
      }
    });

    // 绑定下拉操作菜单切换
    topClientsTbody.querySelectorAll(".btn-dropdown-toggle").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const wrap = btn.closest(".action-dropdown-wrap");
        document.querySelectorAll(".action-dropdown-wrap.active").forEach(w => {
          if (w !== wrap) w.classList.remove("active");
        });
        if (wrap) {
          const opening = !wrap.classList.contains("active");
          wrap.classList.toggle("active");
          if (opening) positionDropdownMenu(wrap);
        }
      });
    });

    // 悬停打开的菜单也要跟随按钮，否则会被表格裁掉
    topClientsTbody.querySelectorAll(".action-dropdown-wrap").forEach(wrap => {
      wrap.addEventListener("mouseenter", () => positionDropdownMenu(wrap));
    });

    // 绑定表格操作按钮
    topClientsTbody.querySelectorAll("[data-action='toggle-client'], [data-action='restore-client']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const cid = btn.getAttribute("data-id");
        const actionType = btn.getAttribute("data-action-type");
        const client = appConfig.clients.find(item => item.id === cid);
        if (isWindowsWorkstation(client)) { openGatewayRequest(client.bound_gateway_id || activeGateway?.id || ""); return; }
        if (actionType === "off" && !confirm(t("renderClientsTableRows-24", {name}))) return;
        if (actionType === "on" && client.access_mode !== "local") {
          const boundGw = (appConfig.gateways || []).find(g => g.id === client.bound_gateway_id);
          if (boundGw && isLoopbackHost(boundGw.host)) {
            const ok = confirm(`节点【${client.name}】绑定的网关 ${boundGw.host}:${boundGw.port} 是本机回环地址，远程节点无法访问它。\n仍要开启吗？`);
            if (!ok) return;
          }
        }
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
            alert(t("renderClientsTableRows-25") + d.error);
          }
        } catch (e) {
          alert(t("renderClientsTableRows-26") + e.message);
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
        const client = appConfig.clients.find(item => item.id === btn.dataset.id);
        const sequence = (nodeProbeSequences.get(client.id) || 0) + 1;
        nodeProbeSequences.set(client.id, sequence);
        const pill = btn.querySelector(".rtt-pill");
        btn.disabled = true;
        pill.textContent = t("renderClientsTableRows-27");
        try {
          const result = await postJson("/api/node-test", {...nodeRequest(client), target_url: target});
          if (revision !== nodeTargetRevision) return;
          pill.textContent = result.success ? t("renderClientsTableRows-28") : t("renderClientsTableRows-29");
          pill.style.color = result.success ? "var(--success)" : "var(--warning)";
          if (nodeProbeSequences.get(client.id) === sequence) showNodeResult(client, result);
        } catch (error) {
          if (revision !== nodeTargetRevision) return;
          pill.textContent = t("renderClientsTableRows-30");
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
            alert(t("renderClientsTableRows-31") + (d.error || d.message));
          }
        } catch (e) {
          alert(t("renderClientsTableRows-32") + e.message);
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
            alert(t("renderClientsTableRows-33", {host, port, latency_ms}));
          } else {
            alert(t("renderClientsTableRows-34", {host, port}));
          }
        } catch (e) {
          alert(t("renderClientsTableRows-35") + e.message);
        } finally {
          btn.textContent = t("renderClientsTableRows-36");
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
    if (!selected.length || !confirm(t("renderClientsTable", {length}))) return;
    const selections = selected.map(nodeRequest);
    topEnableAllBtn.disabled = true;
    topEnableAllBtn.innerHTML = t("renderClientsTable-2");
    try {
      const res = await fetch("/api/nodes/batch-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "on", nodes: selections })
      });
      const d = await res.json();
      await loadConfig();
      alert([d.message || d.error || t("renderClientsTable-3"), ...(d.results || []).filter(item => !item.success).map(item => item.name + " · " + item.error)].join("\n"));
    } catch (e) {
      alert(t("renderClientsTable-4") + e.message);
    } finally {
      topEnableAllBtn.disabled = false;
      topEnableAllBtn.innerHTML = t("renderClientsTable-5");
    }
  });

  // 按各节点的启用前快照批量恢复
  topDisableAllBtn?.addEventListener("click", async () => {
    const selected = filterClientsList();
    if (!selected.length) return;
    const selections = selected.map(nodeRequest);
    if (!confirm(t("renderClientsTable-6", {length}))) {
      return;
    }
    topDisableAllBtn.disabled = true;
    topDisableAllBtn.innerHTML = t("renderClientsTable-7");
    try {
      const res = await fetch("/api/nodes/batch-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "off", nodes: selections })
      });
      const d = await res.json();
      await loadConfig();
      const failures = (d.results || []).filter(item => !item.success)
        .map(item => item.name + " · " + (item.error || t("renderClientsTable-8")));
      alert([d.message || d.error || t("renderClientsTable-9"), ...failures, restoredProxyNote].join("\n"));
    } catch (e) {
      alert(t("renderClientsTable-10") + e.message);
    } finally {
      topDisableAllBtn.disabled = false;
      topDisableAllBtn.innerHTML = t("renderClientsTable-11");
    }
  });

  // 全网并发健康巡检
  topHealthCheckBtn?.addEventListener("click", async () => {
    if (!nodeTargetUrl.reportValidity()) return;
    const target = nodeTargetUrl.value.trim();
    const revision = nodeTargetRevision;
    topHealthCheckBtn.disabled = true;
    topHealthCheckBtn.textContent = t("renderClientsTable-12");
    try {
      const data = await postJson("/api/nodes/health-check-all", {target_url: target});
      if (revision !== nodeTargetRevision) return;
      const summary = [t("renderClientsTable-13") + target];
      for (const [id, result] of Object.entries(data.health_map || {})) {
        const count = [result.explicit_proxy, result.ordinary_request].filter(check => check?.online).length;
        const status = result.explicit_proxy ? count + t("renderClientsTable-14") : nodeCheckLabel(result);
        const pill = document.getElementById("rtt-" + id);
        if (pill) { pill.textContent = status; pill.style.color = count === 2 ? "var(--success)" : "var(--warning)"; }
        summary.push(id + " · " + status);
      }
      alert(summary.join("\n"));
    } catch (error) {
      alert(t("renderClientsTable-15") + error.message);
    } finally {
      topHealthCheckBtn.disabled = false;
      topHealthCheckBtn.textContent = t("renderClientsTable-16");
    }
  });

  // 审计日志抽屉弹窗
  async function loadAuditLogs() {
    if (!auditTableTbody) return;
    auditTableTbody.innerHTML = t("loadAuditLogs");
    try {
      const res = await fetch("/api/audit-logs");
      const d = await res.json();
      auditTableTbody.innerHTML = "";
      if (!d.logs || d.logs.length === 0) {
        auditTableTbody.innerHTML = t("loadAuditLogs-2");
        return;
      }
      d.logs.forEach(item => {
        const tr = document.createElement("tr");
        const statusClass = item.status === "success" ? "success" : (item.status === "failed" || item.status === "error" ? "failed" : "info");
        const statusText = item.status === "success" ? t("loadAuditLogs-3") : (item.status === "failed" ? t("loadAuditLogs-4") : item.status);
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
      auditTableTbody.innerHTML = t("loadAuditLogs-5", {message});
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
        <td>${isDefault ? t("renderGatewaysTable") : t("renderGatewaysTable-2")}</td>
        <td style="color:var(--text-muted); font-size:12px;">${escapeHtml(g.description || '-')}</td>
        <td>
          <div class="table-actions">
            ${!isDefault ? t("renderGatewaysTable-3", {id_}) : ''}
            <button class="btn-mini" data-action="test-gw" data-host="${escapeHtml(g.host)}" data-port="${escapeHtml(g.port)}">⚡ 测通</button>
            <button class="btn-mini" data-action="edit-gw" data-id="${escapeHtml(g.id)}">✏️ 编辑</button>
            ${!isDefault ? t("renderGatewaysTable-4", {id_}) : ''}
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
          alert(t("renderGatewaysTable-5") + e.message);
        } finally {
          btn.textContent = t("renderGatewaysTable-6");
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
        if (!confirm(t("renderGatewaysTable-7", {gid}))) return;
        const res = await fetch("/api/gateways/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: gid })
        });
        const d = await res.json();
        if (d.success) {
          await loadConfig();
        } else {
          alert(t("renderGatewaysTable-8") + d.error);
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
        topNoproxyHint.textContent = t("renderGatewaysTable-9");
        setTimeout(() => topNoproxyHint.textContent = "", 3000);
      }
    } catch (e) {
      alert(t("renderGatewaysTable-10") + e.message);
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
      if (mode === "local") formClientHint.textContent = t("renderGatewaysTable-11");
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
        if (formClientPort) formClientPort.placeholder = t("renderGatewaysTable-12");
        if (formClientSshUser && (!formClientSshUser.value || formClientSshUser.value === "ubuntu")) {
          formClientSshUser.value = "root";
        }
        if (formClientHint) {
          formClientHint.style.color = "var(--primary)";
          formClientHint.textContent = t("renderGatewaysTable-13");
        }
      } else if (os === "linux") {
        if (formClientPort && formClientPort.value === "6600") {
          formClientPort.value = "22";
        }
        if (formClientPort) formClientPort.placeholder = t("renderGatewaysTable-14");
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
    formClientGw.add(new Option(t("openClientModal"), ""));
    (appConfig.gateways || []).forEach(g => {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = `${g.name} (${g.host}:${g.port})`;
      formClientGw.appendChild(opt);
    });

    if (mode === "add" || mode === "clone") {
      formClientMode.value = "add";
      modalClientTitle.textContent = (mode === "clone") ? t("openClientModal-2") : t("openClientModal-3");

      if (mode === "clone") {
        const target = (appConfig.clients || []).find(c => c.id === cid);
        if (target) {
          formClientId.value = `${target.id}-copy`;
          formClientId.disabled = false;
          formClientName.value = t("openClientModal-4", {name});
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
          formClientHint.textContent = t("openClientModal-5");
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
      modalClientTitle.textContent = t("openClientModal-6");
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
    if (edited?.identity_confirmation_required) formClientHint.textContent = t("openClientModal-7");
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
        formClientHint.textContent = t("openClientModal-8");
        return;
      }
    } else {
      if (!host) {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = t("openClientModal-9");
        return;
      }
    }

    modalClientTestBtn.disabled = true;
    modalClientTestBtn.innerHTML = t("openClientModal-10");
    formClientHint.style.color = "var(--primary)";
    formClientHint.textContent = t("openClientModal-11");

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
      formClientHint.textContent = t("openClientModal-12", {message});
    } finally {
      modalClientTestBtn.disabled = false;
      modalClientTestBtn.innerHTML = t("openClientModal-13");
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
      if (!name) { formClientHint.textContent = t("openClientModal-14"); return; }
    } else if (accessMode === "docker_host") {
      host = formClientSshHost ? formClientSshHost.value.trim() : "";
      containerName = formClientContainer ? formClientContainer.value.trim() : "";
      sshHost = host;
      port = Number(formClientHostPort.value || 22);
      sshUser = formClientSshUserHost ? formClientSshUserHost.value.trim() : "ubuntu";
      authType = "key";
      if (!name || !host || !containerName) {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = t("openClientModal-15");
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
        formClientHint.textContent = t("openClientModal-16");
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
        formClientHint.textContent = t("openClientModal-17", {error, mode______edit_________________________________});
        await loadConfig();
      }
    } catch (e) {
      formClientHint.style.color = "var(--danger)";
      formClientHint.textContent = t("openClientModal-18", {message});
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
      modalGwTitle.textContent = t("openGatewayModal");
      formGwId.value = "";
      formGwId.disabled = false;
      formGwName.value = "";
      formGwHost.value = "";
      formGwPort.value = "7890";
      formGwProtocol.value = "http";
      formGwDesc.value = "";
    } else {
      modalGwTitle.textContent = t("openGatewayModal-2");
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
      formGwHint.textContent = t("openGatewayModal-3");
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
      formGwHint.textContent = t("openGatewayModal-4", {message});
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
      formGwHint.textContent = t("openGatewayModal-5");
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
      formGwHint.textContent = t("openGatewayModal-6", {message});
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
            btn.textContent = t("attachCopyButtons");
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
