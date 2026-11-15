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

  const cardStep1 = document.getElementById("card-step-1");
  const cardStep2 = document.getElementById("card-step-2");
  const cardStep3 = document.getElementById("card-step-3");
  const cardStep4 = document.getElementById("card-step-4");

  const statusTagStep1 = document.getElementById("status-tag-step-1");
  const statusTagStep2 = document.getElementById("status-tag-step-2");
  const statusTagStep3 = document.getElementById("status-tag-step-3");
  const statusTagStep4 = document.getElementById("status-tag-step-4");

  const wizardGwSelect = document.getElementById("wizard-gw-select");
  const wizardTestGwBtn = document.getElementById("wizard-test-gw-btn");
  const wizardSetDefaultGwBtn = document.getElementById("wizard-set-default-gw-btn");
  const step1Result = document.getElementById("step-1-result");

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
      // 首次加载自动对当前网关做一次轻量级预检
      initPrecheck();
    } catch (err) {
      console.error(err);
      globalStatusText.textContent = "配置加载失败";
      globalStatusPill.querySelector(".status-indicator-dot").className = "status-indicator-dot offline";
    }
  }

  function renderAll() {
    const gateways = appConfig.gateways || [];
    activeGateway = gateways.find(g => g.id === appConfig.active_gateway_id) || gateways[0] || null;

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
  function renderWizardSelectors() {
    const gateways = appConfig.gateways || [];
    const clients = appConfig.clients || [];

    // 网关选择器
    wizardGwSelect.innerHTML = "";
    gateways.forEach(gw => {
      const opt = document.createElement("option");
      opt.value = gw.id;
      opt.textContent = `${gw.name} (${gw.host}:${gw.port})` + (gw.id === appConfig.active_gateway_id ? " [默认]" : "");
      if (gw.id === appConfig.active_gateway_id) opt.selected = true;
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

    if (clients.length > 0) {
      selectedWizardClient = clients[0];
      updateWizardClientMeta(selectedWizardClient);
    }
  }

  function updateWizardClientMeta(client) {
    if (!client) return;
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
  });

  wizardGwSelect.addEventListener("change", () => {
    const gid = wizardGwSelect.value;
    selectedWizardGateway = (appConfig.gateways || []).find(g => g.id === gid);
  });

  // Step 1: 探测网关
  wizardTestGwBtn.addEventListener("click", async () => {
    if (!selectedWizardGateway) return;
    wizardTestGwBtn.disabled = true;
    wizardTestGwBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在探测网关...';
    step1Result.className = "step-result-banner";
    step1Result.innerHTML = '<span class="res-msg">正在测试与网关的端口连通性...</span>';

    try {
      const res = await fetch("/api/test-gateway", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          host: selectedWizardGateway.host,
          port: selectedWizardGateway.port
        })
      });
      const data = await res.json();
      if (data.online) {
        step1Result.className = "step-result-banner success";
        step1Result.innerHTML = `<strong>✅ 连通成功！</strong> 网关 ${selectedWizardGateway.name} (${selectedWizardGateway.host}:${selectedWizardGateway.port}) 响应正常，延迟: <strong>${data.latency_ms} ms</strong>。已自动为您解锁步骤 2。`;
        statusTagStep1.className = "step-status-tag success";
        statusTagStep1.textContent = "✅ 已就绪";
        pipeStep1.className = "pipeline-step completed";
        pipeStep1.innerHTML = '<span class="pipe-num">✓</span><span class="pipe-name">网关已就绪</span>';

        // 激活 Step 2
        unlockStep2();
      } else {
        step1Result.className = "step-result-banner error";
        step1Result.innerHTML = `<strong>❌ 端口不可达:</strong> ${data.error}。请检查网关是否启动 Clash 并配置了 <code>allow-lan: true</code>。`;
        statusTagStep1.className = "step-status-tag";
        statusTagStep1.textContent = "❌ 连通失败";
      }
    } catch (err) {
      step1Result.className = "step-result-banner error";
      step1Result.innerHTML = `<strong>请求异常:</strong> ${err.message}`;
    } finally {
      wizardTestGwBtn.disabled = false;
      wizardTestGwBtn.innerHTML = '<span class="btn-icon">⚡</span> 探测该网关连通性';
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
        appConfig.active_gateway_id = selectedWizardGateway.id;
        renderAll();
        alert(`已成功将【${selectedWizardGateway.name}】设为全局默认网关！`);
      }
    } catch (e) {
      alert("设置失败: " + e.message);
    }
  });

  function unlockStep2() {
    step1Complete = true;
    cardStep2.classList.remove("locked-card");
    pipeStep2.classList.remove("locked");
    pipeStep2.classList.add("active");
    statusTagStep2.textContent = "● 待确认绑定";
    cardStep2.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Step 2: 确认选定节点
  wizardConfirmClientBtn.addEventListener("click", () => {
    if (!selectedWizardClient) {
      alert("请先选择或登记一个业务节点");
      return;
    }
    step2Complete = true;
    statusTagStep2.className = "step-status-tag success";
    statusTagStep2.textContent = `✅ 已绑定: ${selectedWizardClient.name}`;
    pipeStep2.className = "pipeline-step completed";
    pipeStep2.innerHTML = '<span class="pipe-num">✓</span><span class="pipe-name">节点已绑定</span>';

    // 解锁 Step 3
    unlockStep3();
  });

  function unlockStep3() {
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
    Object.keys(targets).forEach(name => {
      const item = targets[name];
      const div = document.createElement("div");
      div.className = "target-card-item";
      div.id = `diag-item-${name.replace(/\s+/g, "_")}`;
      div.innerHTML = `
        <div class="t-info">
          <span class="t-name">${name}</span>
          <span class="t-cat">${item.desc || item.category || '核心服务'}</span>
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
    wizardStartDiagBtn.disabled = true;
    wizardStartDiagBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在执行全网穿透体检...';
    statusTagStep3.textContent = "⚡ 正在穿透探测...";

    // 状态置为 testing
    const targets = appConfig.diagnostic_targets || {};
    Object.keys(targets).forEach(name => {
      const el = document.getElementById(`diag-item-${name.replace(/\s+/g, "_")}`);
      if (el) {
        el.querySelector(".t-pill").className = "t-pill testing";
        el.querySelector(".t-pill").textContent = "探测中...";
      }
    });

    try {
      const gid = selectedWizardGateway ? selectedWizardGateway.id : appConfig.active_gateway_id;
      const res = await fetch(`/api/status?gateway_id=${gid}`);
      const data = await res.json();

      wizardDiagTime.textContent = `体检时间: ${data.timestamp}`;
      let onlineCount = 0;
      const results = data.targets || [];

      results.forEach(target => {
        const el = document.getElementById(`diag-item-${target.name.replace(/\s+/g, "_")}`);
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
          pill.textContent = "🔴 失败";
          rtt.textContent = target.error ? target.error.slice(0, 15) : "超时";
        }
      });

      if (onlineCount >= 2) {
        step3Complete = true;
        statusTagStep3.className = "step-status-tag success";
        statusTagStep3.textContent = `✅ 穿透达标 (${onlineCount}/${results.length} 在线)`;
        pipeStep3.className = "pipeline-step completed";
        pipeStep3.innerHTML = '<span class="pipe-num">✓</span><span class="pipe-name">全网体检通过</span>';

        // 解锁 Step 4
        unlockStep4();
      } else {
        statusTagStep3.className = "step-status-tag";
        statusTagStep3.textContent = `⚠️ 穿透异常 (${onlineCount}/${results.length} 在线)`;
        alert("大部分境外目标站点未能通过代理访问，请检查 183 网关的节点配置或网络策略。");
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
    cardStep4.classList.remove("locked-card");
    pipeStep4.classList.remove("locked");
    pipeStep4.classList.add("completed");
    pipeStep4.innerHTML = '<span class="pipe-num">✓</span><span class="pipe-name">开箱即用</span>';
    statusTagStep4.textContent = "🎯 交付完成";

    if (wizardSwitchBadge && selectedWizardClient) {
      if (selectedWizardClient.is_proxy_enabled) {
        wizardSwitchBadge.className = "switch-badge on";
        wizardSwitchBadge.textContent = "🟢 代理状态: 已开启";
      } else {
        wizardSwitchBadge.className = "switch-badge off";
        wizardSwitchBadge.textContent = "⚪ 代理状态: 已关闭";
      }
    }

    renderHandoverBlocks();
    cardStep4.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderHandoverBlocks() {
    const client = selectedWizardClient || (appConfig && appConfig.clients && appConfig.clients[0]) || { name: "业务计算节点", os_type: "linux", host: "192.168.1.101" };
    const gw = selectedWizardGateway || activeGateway || { host: "192.168.1.100", port: 7890 };
    const osType = (client.os_type || "linux").toLowerCase();

    handoverTargetName.textContent = `${client.name} (${osType.toUpperCase()}, ${client.host})`;
    if (handoverGwName) handoverGwName.textContent = `${gw.host}:${gw.port}`;
    if (wizardTargetDispName) wizardTargetDispName.textContent = `${client.name} (${osType.toUpperCase()})`;
    if (wizardTargetDispSub) {
      if (osType === "docker") {
        wizardTargetDispSub.textContent = `目标 IP: ${client.host} | 容器名: ${client.container_name || 'app-container'} | 隔离性: 宿主机与其他容器 100% 保持直连`;
      } else {
        wizardTargetDispSub.textContent = `目标 IP: ${client.host} | 绑定出口: ${gw.host}:${gw.port} | 进程/会话隔离: 零系统环境残留`;
      }
    }

    const isProxyOn = Boolean(client.is_proxy_enabled);
    if (wizardSwitchBadge) {
      wizardSwitchBadge.className = isProxyOn ? "switch-badge on" : "switch-badge off";
      wizardSwitchBadge.textContent = isProxyOn ? "🟢 出海通道已激活 (全功能就绪)" : "⚪ 当前处于原生直连状态 (未开启出海)";
    }

    handoverBlocksContainer.innerHTML = "";

    const hostUrl = window.location.host || (window.location.hostname ? `${window.location.hostname}:8899` : "127.0.0.1:8899");

    if (osType === "docker") {
      // Docker 容器专属交付指令 (100% 容器内部自主控制，隔离宿主机)
      const cName = client.container_name || (client.id ? client.id.replace("node-", "") : "app-container");
      handoverBlocksContainer.innerHTML = `
        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 1: 在容器内部直接初始化独立代理开关 (最推荐：纯容器内自主操作，宿主机 0 影响)</span>
            <button class="btn-copy" data-copy="curl -s http://${hostUrl}/container-init.sh | bash">复制代码</button>
          </div>
          <pre><code># 1. 直接在【容器内部】运行一次初始化命令 (自动就绪 proxy-on / proxy-off):
curl -s http://${hostUrl}/container-init.sh | bash

# 2. 从此在容器终端中可随时自主开启/关闭出海 (仅在当前容器生效，宿主机完全隔离):
proxy-on           # 开启出海代理 (走 183 网关)
proxy-off          # 关闭出海代理 (恢复直连)
proxy-status       # 查看代理开关状态
with-proxy &lt;命令&gt;  # 单次命令走代理 (如: with-proxy pip install openai)</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 2: 在容器内部临时一键开启/关闭 (零安装，当前 bash 窗口生效)</span>
            <button class="btn-copy" data-copy="source &lt;(curl -s http://${hostUrl}/proxy-on)">复制代码</button>
          </div>
          <pre><code># 在容器内部任何终端中直接执行:
# 开启出海:
source &lt;(curl -s http://${hostUrl}/proxy-on)

# 关闭出海:
source &lt;(curl -s http://${hostUrl}/proxy-off)</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 3: 从 70 宿主机外部开关 (无需进入容器)</span>
            <button class="btn-copy" data-copy="./bin/docker-proxy on ${cName}">复制代码</button>
          </div>
          <pre><code># 若处于 70 宿主机，也可直接外部开关该容器:
./bin/docker-proxy on ${cName}      # 开启该容器代理
./bin/docker-proxy off ${cName}     # 关闭该容器代理
./bin/docker-proxy exec ${cName} /bin/bash  # 单次带代理进入容器终端</code></pre>
        </div>
      `;
    } else if (osType === "windows") {
      // Windows 交互命令
      handoverBlocksContainer.innerHTML = `
        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 1: 单任务进程沙箱包装执行 (执行完毕环境变量即刻销毁，最推荐)</span>
            <button class="btn-copy" data-copy=".\\bin\\with-proxy.ps1 curl.exe -I https://www.google.com">复制代码</button>
          </div>
          <pre><code># PowerShell 执行任何命令 (自动注入 183 代理网关，任务完成即刻彻底清理):
.\\bin\\with-proxy.ps1 curl.exe -I https://www.google.com
.\\bin\\with-proxy.ps1 git clone https://github.com/octocat/Hello-World.git
.\\bin\\with-proxy.ps1 pip install openai

# 经典 CMD 终端执行:
bin\\with-proxy.cmd curl.exe -I https://www.google.com</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 2: 当前 PowerShell 会话临时生效 (关闭终端窗口或注销即还原)</span>
            <button class="btn-copy" data-copy=". .\\bin\\proxy-on.ps1">复制代码</button>
          </div>
          <pre><code># 临时挂载代理:
. .\\bin\\proxy-on.ps1

# 调试完毕后一键注销，恢复纯净环境:
. .\\bin\\proxy-off.ps1</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 3: Python 代码零污染上下文管理器 (纯标准库，退出代码块自动清除)</span>
            <button class="btn-copy" data-copy="from sdk.proxy_session import ProxySession&#10;with ProxySession():&#10;    # 你的业务代码">复制代码</button>
          </div>
          <pre><code>from sdk.proxy_session import ProxySession

with ProxySession():
    import urllib.request
    resp = urllib.request.urlopen("https://www.google.com")
    print("Google Status:", resp.getcode())</code></pre>
        </div>
      `;
    } else {
      // Linux / macOS 交互命令
      handoverBlocksContainer.innerHTML = `
        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 1: 任意路径免进入一键生效 (最推荐：利用控制台端点直接注入，杜绝路径报错)</span>
            <button class="btn-copy" data-copy="source &lt;(curl -s http://${hostUrl}/proxy-on)">复制代码</button>
          </div>
          <pre><code># 在 186 或任意 Linux 机器的【任何目录】下直接执行 (无需先 cd 到工具目录):
# 开启出海代理:
source &lt;(curl -s http://${hostUrl}/proxy-on)

# 关闭出海代理 (恢复直连):
source &lt;(curl -s http://${hostUrl}/proxy-off)</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 2: 本地脚本会话级开关 (明确进入工具目录，杜绝 No such file 报错)</span>
            <button class="btn-copy" data-copy="cd ~/net-proxy-tool && source bin/proxy-on">复制代码</button>
          </div>
          <pre><code># 明确指定目录进入执行:
cd ~/net-proxy-tool && source bin/proxy-on

# 调试完毕后一键注销，恢复纯净环境:
cd ~/net-proxy-tool && source bin/proxy-off

# 提示: 执行一次 ./install-cli.sh 后，在任何目录直接输入 proxy-on 即可全局生效！</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 3: 单任务进程沙箱包装执行 (任务完成即刻彻底清理)</span>
            <button class="btn-copy" data-copy="~/net-proxy-tool/bin/with-proxy curl -I https://www.google.com">复制代码</button>
          </div>
          <pre><code># 使用绝对路径执行单任务 (自动走 ${gw.host}:${gw.port} 网关，任务退出环境自动销毁):
~/net-proxy-tool/bin/with-proxy curl -I https://www.google.com
~/net-proxy-tool/bin/with-proxy git clone https://github.com/octocat/Hello-World.git
~/net-proxy-tool/bin/with-proxy pip install openai httpx</code></pre>
        </div>

        <div class="code-delivery-card">
          <div class="code-delivery-header">
            <span class="code-delivery-title">方式 4: Python 代码零污染上下文管理器 (纯标准库，退出代码块自动清除)</span>
            <button class="btn-copy" data-copy="from sdk.proxy_session import ProxySession&#10;with ProxySession():&#10;    # 业务代码">复制代码</button>
          </div>
          <pre><code>from sdk.proxy_session import ProxySession

with ProxySession():
    import urllib.request
    resp = urllib.request.urlopen("https://www.google.com")
    print("Google Status:", resp.getcode())</code></pre>
        </div>
      `;
    }

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

  wizardBtnProxyOn?.addEventListener("click", async () => {
    if (!selectedWizardClient) return;
    wizardBtnProxyOn.disabled = true;
    showWizardFeedback("warning", "⏳ 自动化下发中...", `正在通过自动化运维通道向目标【${selectedWizardClient.name}】下发代理配置...\n出口网关: ${(selectedWizardGateway || activeGateway).host}:${(selectedWizardGateway || activeGateway).port}`);
    try {
      const res = await fetch("/api/node-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id: selectedWizardClient.id,
          action: "on"
        })
      });
      const data = await res.json();
      if (data.success) {
        selectedWizardClient.is_proxy_enabled = true;
        wizardSwitchBadge.className = "switch-badge on";
        wizardSwitchBadge.textContent = "🟢 出海通道已激活 (全功能就绪)";
        showWizardFeedback("success", "✅ 下发成功", `${data.message}\n目标现已具备原生出海能力！在终端中直接执行 curl https://www.google.com 或 git clone 即可直接访问外网，无需输入任何代理命令。`);
        await loadConfig();
      } else {
        showWizardFeedback("error", "❌ 下发失败", `下发失败: ${data.error || '未知错误'}`);
      }
    } catch (e) {
      showWizardFeedback("error", "❌ 请求异常", `网络请求异常: ${e.message}`);
    } finally {
      wizardBtnProxyOn.disabled = false;
    }
  });

  wizardBtnProxyOff?.addEventListener("click", async () => {
    if (!selectedWizardClient) return;
    wizardBtnProxyOff.disabled = true;
    showWizardFeedback("warning", "⏳ 正在注销...", `正在注销目标【${selectedWizardClient.name}】的代理配置并恢复原生直连...`);
    try {
      const res = await fetch("/api/node-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          node_id: selectedWizardClient.id,
          action: "off"
        })
      });
      const data = await res.json();
      if (data.success) {
        selectedWizardClient.is_proxy_enabled = false;
        wizardSwitchBadge.className = "switch-badge off";
        wizardSwitchBadge.textContent = "⚪ 当前处于原生直连状态 (未开启出海)";
        showWizardFeedback("success", "✅ 已关闭", `${data.message}\n目标网络环境已彻底清理，100% 恢复为原始局域网直连。`);
        await loadConfig();
      } else {
        showWizardFeedback("error", "❌ 关闭失败", `关闭失败: ${data.error || '未知错误'}`);
      }
    } catch (e) {
      showWizardFeedback("error", "❌ 请求异常", `网络请求异常: ${e.message}`);
    } finally {
      wizardBtnProxyOff.disabled = false;
    }
  });

  wizardBtnNodeTest?.addEventListener("click", async () => {
    if (!selectedWizardClient) return;
    wizardBtnNodeTest.disabled = true;
    showWizardFeedback("warning", "🔍 探测中...", `正在连入目标节点【${selectedWizardClient.name}】内部进行外网连通性实测...`);
    try {
      const res = await fetch("/api/node-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node_id: selectedWizardClient.id })
      });
      const data = await res.json();
      if (data.online) {
        showWizardFeedback("success", "🟢 外网畅通", `✅ 外网探测成功！\n响应状态: ${data.status_line || 'HTTP 200 OK'}\n探测耗时: ${data.latency_ms} ms\n节点状态: ${data.message}`);
      } else {
        showWizardFeedback("error", "⚪ 直连未通外网", `⚪ 目标无法直连外网或代理未激活。\n状态: ${data.status_line || '超时'}\n提示: ${data.message}`);
      }
    } catch (e) {
      showWizardFeedback("error", "❌ 探测失败", `探测异常: ${e.message}`);
    } finally {
      wizardBtnNodeTest.disabled = false;
    }
  });

  // ==============================================================
  // 4. TAB 2: ⚡ 沙箱控制台 (Sandbox Console)
  // ==============================================================
  function renderSandboxSelectors() {
    const gateways = appConfig.gateways || [];
    sbGwOverrideSelect.innerHTML = '<option value="">默认当前网关</option>';
    gateways.forEach(gw => {
      const opt = document.createElement("option");
      opt.value = gw.id;
      opt.textContent = `${gw.name} (${gw.host}:${gw.port})`;
      sbGwOverrideSelect.appendChild(opt);
    });
  }

  sbTemplateSelect.addEventListener("change", () => {
    sbCmdInput.value = sbTemplateSelect.value;
  });

  sbQuickDiagBtn.addEventListener("click", () => {
    initPrecheck(true);
  });

  sbClearTermBtn.addEventListener("click", () => {
    sbTerminalOutput.innerHTML = '<span class="t-dim"># 控制台已清屏。等待输入命令...</span>\n';
  });

  // 在线沙箱运行
  sbRunBtn.addEventListener("click", async () => {
    const cmd = sbCmdInput.value.trim();
    if (!cmd) {
      alert("请输入待执行的命令");
      return;
    }

    sbRunBtn.disabled = true;
    sbStatusBadge.className = "badge-status running";
    sbStatusBadge.textContent = "执行中...";
    sbTerminalOutput.innerHTML = `<span class="t-dim">[${new Date().toLocaleTimeString()}] 沙箱环境启动，准备挂载代理通道...</span>\n`;

    try {
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command: cmd,
          gateway_id: sbGwOverrideSelect.value || undefined
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        sbTerminalOutput.innerHTML += `<span style="color:#ef4444;">[错误] HTTP ${response.status}: ${errText}</span>\n`;
        sbStatusBadge.className = "badge-status";
        sbStatusBadge.textContent = "失败";
        sbRunBtn.disabled = false;
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); // 保留未完成部分

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const rawJson = line.slice(6);
            try {
              const event = JSON.parse(rawJson);
              if (event.type === "start") {
                sbTerminalOutput.innerHTML += `<span style="color:#38bdf8;">$ with-proxy ${event.command}</span>\n`;
                sbTerminalOutput.innerHTML += `<span class="t-dim">[网关出海通道: ${event.gateway}]</span>\n`;
              } else if (event.type === "stdout") {
                sbTerminalOutput.innerHTML += `${escapeHtml(event.line)}\n`;
              } else if (event.type === "finish") {
                const color = event.exit_code === 0 ? "#10b981" : "#f59e0b";
                sbTerminalOutput.innerHTML += `\n<span style="color:${color}; font-weight:bold;">${event.msg}</span>\n`;
                if (event.env_clean) {
                  sbTerminalOutput.innerHTML += `<span style="color:#10b981;">🛡️ [零污染安全核验] 任务结束，系统环境变量 HTTP_PROXY 保持为空，宿主机环境 100% 纯净无残留。</span>\n`;
                }
                sbStatusBadge.className = event.exit_code === 0 ? "badge-status success" : "badge-status";
                sbStatusBadge.textContent = event.exit_code === 0 ? "执行完毕" : `退出码: ${event.exit_code}`;
              } else if (event.type === "error") {
                sbTerminalOutput.innerHTML += `<span style="color:#ef4444;">[异常] ${event.msg}</span>\n`;
                sbStatusBadge.className = "badge-status";
                sbStatusBadge.textContent = "异常";
              }
              sbTerminalOutput.scrollTop = sbTerminalOutput.scrollHeight;
            } catch (e) {
              console.error(e);
            }
          }
        }
      }
    } catch (err) {
      sbTerminalOutput.innerHTML += `<span style="color:#ef4444;">[网络异常] ${err.message}</span>\n`;
      sbStatusBadge.className = "badge-status";
      sbStatusBadge.textContent = "请求失败";
    } finally {
      sbRunBtn.disabled = false;
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
      if (filterType === "proxy_on" && !c.is_proxy_enabled) return false;
      if (filterType === "proxy_off" && c.is_proxy_enabled) return false;

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
    const onCount = cachedClients.filter(c => c.is_proxy_enabled).length;
    const offCount = total - onCount;
    nodeStatsBadge.textContent = `共 ${total} 个节点 (${onCount} 出海中, ${offCount} 直连)`;
  }

  function renderClientsTableRows(clientsToRender) {
    topClientsTbody.innerHTML = "";

    if (!clientsToRender || clientsToRender.length === 0) {
      topClientsTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-dim); padding: 24px;">未匹配到符合条件的业务节点</td></tr>`;
      return;
    }

    clientsToRender.forEach(c => {
      const boundGw = (appConfig.gateways || []).find(g => g.id === c.bound_gateway_id);
      const gwName = boundGw ? `${boundGw.name}` : (c.bound_gateway_id || "默认");
      const tagsHtml = (c.tags || []).map(t => `<span class="tag-badge">${escapeHtml(t)}</span>`).join("");
      const isProxyOn = Boolean(c.is_proxy_enabled);
      const isLocal = ["127.0.0.1", "localhost", window.location.hostname].includes(c.host) && (c.port == 22 || !c.port) && !c.container_name;

      let addrBadge = '<span class="addr-badge">SSH直连</span>';
      let addrRow = `<code>${escapeHtml(c.ssh_user || 'root')}@${escapeHtml(c.host)}:${c.port || 22}</code>`;

      if (isLocal) {
        addrBadge = '<span class="addr-badge" style="background:rgba(168,85,247,0.15);color:#c084fc;">本机控制台</span>';
        addrRow = `<code>127.0.0.1 (本机执行)</code>`;
      } else if (c.access_mode === "docker_host" || (c.container_name && !c.port)) {
        addrBadge = '<span class="addr-badge" style="background:rgba(234,179,8,0.15);color:#facc15;">Docker穿透</span>';
        addrRow = `<code>${escapeHtml(c.ssh_user || 'ubuntu')}@${escapeHtml(c.ssh_host || c.host)}</code> <span style="font-size:11px;color:var(--text-dim);">&rarr; [${escapeHtml(c.container_name || c.name)}]</span>`;
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
          <div class="status-capsule ${isProxyOn ? 'on' : 'off'}">
            <span class="capsule-indicator">
              ${isProxyOn ? '<span class="pulse-dot"></span>已出海' : '⚪ 直连'}
            </span>
            <button class="capsule-btn ${isProxyOn ? 'btn-turn-off' : 'btn-turn-on'}" data-action="toggle-client" data-id="${c.id}" data-action-type="${isProxyOn ? 'off' : 'on'}">
              ${isProxyOn ? '🛑 关闭' : '⚡ 开启'}
            </button>
          </div>
        </td>
        <td style="text-align: right;">
          <div class="table-actions-modern">
            <button class="btn-speedtest" data-action="test-node-out" data-id="${c.id}" title="实测出海延迟与连通状态">
              🔍 测外网 <span class="rtt-pill" id="rtt-${c.id}"></span>
            </button>
            <div class="action-dropdown-wrap">
              <button class="btn-dropdown-toggle" title="更多运维操作">•••</button>
              <div class="action-dropdown-menu">
                <button class="dropdown-item" data-action="edit-client" data-id="${c.id}">✏️ 编辑参数</button>
                <button class="dropdown-item" data-action="clone-client" data-id="${c.id}">📋 克隆节点</button>
                <button class="dropdown-item" data-action="test-client" data-id="${c.id}" data-host="${c.host}" data-port="${c.port || 22}">⚡ 连通探测</button>
                <button class="dropdown-item danger" data-action="delete-client" data-id="${c.id}">🗑️ 删除节点</button>
              </div>
            </div>
          </div>
        </td>
      `;
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
    topClientsTbody.querySelectorAll("[data-action='toggle-client']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const cid = btn.getAttribute("data-id");
        const actionType = btn.getAttribute("data-action-type");
        btn.textContent = "⏳...";
        try {
          const res = await fetch("/api/node-switch", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              node_id: cid,
              action: actionType
            })
          });
          const d = await res.json();
          if (d.success) {
            await loadConfig();
            alert(d.message);
          } else {
            alert("切换失败: " + d.error);
          }
        } catch (e) {
          alert("切换异常: " + e.message);
        }
      });
    });

    topClientsTbody.querySelectorAll("[data-action='test-node-out']").forEach(btn => {
      btn.addEventListener("click", async () => {
        const cid = btn.getAttribute("data-id");
        const rttPill = document.getElementById(`rtt-${cid}`);
        btn.disabled = true;
        if (rttPill) rttPill.textContent = "⏳";
        try {
          const res = await fetch("/api/node-test", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ node_id: cid })
          });
          const d = await res.json();
          if (d.online) {
            if (rttPill) {
              rttPill.textContent = `${d.latency_ms}ms`;
              rttPill.style.color = "#4ade80";
            }
            alert(`✅ 节点出海探测正常！\n响应状态: ${d.status_line || 'HTTP 200 OK'}\n实测延迟: ${d.latency_ms} ms\n说明: ${d.message}`);
          } else {
            if (rttPill) {
              rttPill.textContent = "超时";
              rttPill.style.color = "#f87171";
            }
            alert(`⚪ 节点处于直连或无法访问外网:\n状态: ${d.status_line || '超时'}\n说明: ${d.message}`);
          }
        } catch (e) {
          if (rttPill) rttPill.textContent = "ERR";
          alert("探测异常: " + e.message);
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
        if (!confirm(`确定要从拓扑池中删除节点 "${cid}" 吗？`)) return;
        try {
          const res = await fetch("/api/clients/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: cid })
          });
          const d = await res.json();
          if (d.success) {
            await loadConfig();
          } else {
            alert("删除失败: " + d.error);
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
    if (!confirm("⚡ 确定要一键开启列表中所有节点的出海代理吗？")) return;
    topEnableAllBtn.disabled = true;
    topEnableAllBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在批量下发...';
    try {
      const res = await fetch("/api/nodes/batch-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "on" })
      });
      const d = await res.json();
      await loadConfig();
      alert(d.message || "已开通所有节点出海");
    } catch (e) {
      alert("批量下发异常: " + e.message);
    } finally {
      topEnableAllBtn.disabled = false;
      topEnableAllBtn.innerHTML = '<span class="btn-icon">⚡</span> 一键全部出海';
    }
  });

  // 一键全部切断代理恢复直连
  topDisableAllBtn?.addEventListener("click", async () => {
    if (!confirm("⚠️ 确定要一键关闭所有节点的出海通道吗？\n这将彻底清除各节点和容器内的代理配置，全网恢复 100% 原生直连网络。")) {
      return;
    }
    topDisableAllBtn.disabled = true;
    topDisableAllBtn.innerHTML = '<span class="btn-icon">⏳</span> 正在全局切断...';
    try {
      const res = await fetch("/api/nodes/batch-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "off" })
      });
      const d = await res.json();
      await loadConfig();
      alert(d.message || "已恢复全部节点直连");
    } catch (e) {
      alert("切断异常: " + e.message);
    } finally {
      topDisableAllBtn.disabled = false;
      topDisableAllBtn.innerHTML = '<span class="btn-icon">🛑</span> 一键恢复全部直连';
    }
  });

  // 全网并发健康巡检
  topHealthCheckBtn?.addEventListener("click", async () => {
    topHealthCheckBtn.disabled = true;
    topHealthCheckBtn.innerHTML = '<span class="btn-icon">⏳</span> 巡检中...';
    try {
      const res = await fetch("/api/nodes/health-check-all", { method: "POST" });
      const d = await res.json();
      if (d.success && d.health_map) {
        let summary = [];
        Object.keys(d.health_map).forEach(cid => {
          const h = d.health_map[cid];
          const rttPill = document.getElementById(`rtt-${cid}`);
          if (rttPill) {
            if (h.online) {
              rttPill.textContent = `${h.latency_ms}ms`;
              rttPill.style.color = "#4ade80";
            } else {
              rttPill.textContent = h.is_proxy_enabled ? "异常" : "直连";
              rttPill.style.color = h.is_proxy_enabled ? "#f87171" : "var(--text-muted)";
            }
          }
          summary.push(`• [${cid}]: ${h.online ? `🟢 畅通 (${h.latency_ms}ms)` : `⚪ ${h.status_line}`}`);
        });
        alert(`🔄 全网健康巡检报告 (${d.checked_at}):\n\n` + summary.join("\n"));
      }
    } catch (e) {
      alert("巡检异常: " + e.message);
    } finally {
      topHealthCheckBtn.disabled = false;
      topHealthCheckBtn.innerHTML = '<span class="btn-icon">🔄</span> 全网巡检';
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
            ${!isDefault ? `<button class="btn-mini" data-action="set-default-gw" data-id="${g.id}">设为默认</button>` : ''}
            <button class="btn-mini" data-action="test-gw" data-host="${g.host}" data-port="${g.port}">⚡ 测通</button>
            <button class="btn-mini" data-action="edit-gw" data-id="${g.id}">✏️ 编辑</button>
            ${!isDefault ? `<button class="btn-mini btn-danger" data-action="delete-gw" data-id="${g.id}">🗑️ 删除</button>` : ''}
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
        const host = btn.getAttribute("data-host");
        const port = btn.getAttribute("data-port");
        btn.textContent = "⏳...";
        try {
          const res = await fetch("/api/test-gateway", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ host, port })
          });
          const d = await res.json();
          if (d.online) {
            alert(`网关 ${host}:${port} 端口连通正常！延迟: ${d.latency_ms} ms`);
          } else {
            alert(`网关 ${host}:${port} 端口不可达: ${d.error}`);
          }
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
        if (sectionAccessDockerHost) sectionAccessDockerHost.style.display = "block";
      }
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
          formClientHint.textContent = "💡 已切换至 Docker 容器模式：将直接直连容器内部，宿主机与其它容器 100% 保持直连不受影响。";
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
    formClientHint.textContent = "";

    // 填充网关下拉框
    formClientGw.innerHTML = "";
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
            if (formClientSshHost) formClientSshHost.value = target.ssh_host || target.host || "";
            if (formClientSshUserHost) formClientSshUserHost.value = target.ssh_user || "zxy";
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
      if (formClientSshHost) formClientSshHost.value = "";
      if (formClientSshUserHost) formClientSshUserHost.value = "zxy";
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
        if (formClientSshHost) formClientSshHost.value = target.ssh_host || target.host || "";
        if (formClientSshUserHost) formClientSshUserHost.value = target.ssh_user || "zxy";
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

    modalClient.style.display = "flex";
  }

  wizardOpenAddClientBtn.addEventListener("click", () => openClientModal("add"));
  topAddClientBtn.addEventListener("click", () => openClientModal("add"));
  modalClientClose.addEventListener("click", () => modalClient.style.display = "none");

  // 深度全链路预检主机
  modalClientTestBtn.addEventListener("click", async () => {
    const accessMode = formClientAccessMode ? formClientAccessMode.value : "ssh";
    const host = formClientHost.value.trim();
    const port = parseInt((formClientPort ? formClientPort.value.trim() : "22") || "22", 10);
    const osType = formClientOs ? formClientOs.value : "linux";
    const authType = formClientAuthType ? formClientAuthType.value : "key";
    const sshUser = formClientSshUser ? formClientSshUser.value.trim() : "root";
    const sshPass = formClientSshPass ? formClientSshPass.value.trim() : "";
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
        formClientHint.textContent = d.message;
      } else {
        formClientHint.style.color = d.tcp_ok ? "var(--warning)" : "var(--danger)";
        formClientHint.textContent = d.message;
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
    const tags = formClientTags.value.split(",").map(t => t.strip ? t.strip() : t.trim()).filter(Boolean);
    const desc = formClientDesc.value.trim();
    const accessMode = formClientAccessMode ? formClientAccessMode.value : "ssh";

    let host = "";
    let port = 22;
    let sshUser = "";
    let authType = "key";
    let sshPass = "";
    let containerName = undefined;
    let sshHost = undefined;

    if (accessMode === "docker_host") {
      host = formClientSshHost ? formClientSshHost.value.trim() : "";
      containerName = formClientContainer ? formClientContainer.value.trim() : "";
      sshHost = host;
      sshUser = formClientSshUserHost ? formClientSshUserHost.value.trim() : "zxy";
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
      sshPass = formClientSshPass ? formClientSshPass.value.trim() : "";
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
        if (data.client) {
          wizardClientSelect.value = data.client.id;
          selectedWizardClient = data.client;
          updateWizardClientMeta(data.client);
        }
      } else {
        formClientHint.style.color = "var(--danger)";
        formClientHint.textContent = `❌ ${data.error}`;
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
        body: JSON.stringify({ host, port })
      });
      const d = await res.json();
      if (d.online) {
        formGwHint.style.color = "var(--success)";
        formGwHint.textContent = `🟢 端口畅通，响应延迟: ${d.latency_ms} ms`;
      } else {
        formGwHint.style.color = "var(--danger)";
        formGwHint.textContent = `❌ 端口不可达: ${d.error}`;
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
  async function initPrecheck(silent = false) {
    if (!activeGateway) return;
    try {
      const res = await fetch("/api/test-gateway", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ host: activeGateway.host, port: activeGateway.port })
      });
      const d = await res.json();
      if (d.online) {
        globalStatusPill.querySelector(".status-indicator-dot").className = "status-indicator-dot online";
        sbGwStatusVal.textContent = "● 连通正常";
        sbGwStatusVal.className = "m-val green";
        sbGwRttSub.textContent = `TCP 延迟: ${d.latency_ms} ms`;
      } else {
        globalStatusPill.querySelector(".status-indicator-dot").className = "status-indicator-dot offline";
        sbGwStatusVal.textContent = "● 端口异常";
        sbGwStatusVal.className = "m-val";
        sbGwStatusVal.style.color = "var(--danger)";
        sbGwRttSub.textContent = d.error || "无法连接";
      }
    } catch (e) {
      console.error(e);
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
