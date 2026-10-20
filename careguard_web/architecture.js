/* Source-grounded module explorer. Highlights describe call paths, never live telemetry. */
(() => {
  "use strict";
  const root = document.getElementById("mapfm-architecture");
  if (!root) return;
  const agents = {
    Perception: { number: "01", name: "感知编码", role: "输入层", mark: "P", description: "把文本与已提供的多模态数据整理为后续模块可读取的表示。", input: "交接文本、预处理体征和可选多模态输入", output: "文本向量、上下文表示与输入模态记录", code: "RealPerceptionAgent.encode", method: "当前默认类是 RealPerceptionAgent：从实际输入构建确定性特征，可接收外部预计算图像特征。旧的模拟感知类仍保留在工程中。", handover: "输入编码；单次体征由预处理器解析后编入临床文本。" },
    RAA: { number: "02", name: "检索增强", role: "证据层", mark: "R", description: "围绕当前问题检索资料，比较不同检索策略，为推理提供可追溯的候选上下文。", input: "问题文本、知识索引与检索策略", output: "候选文档、检索元数据与来源标记", code: "RetrievalAugmentedAgent.retrieve", method: "包含 mixed、rerank、adaptive 策略，并在协作任务中进行策略选择。知识索引支持词面检索和 FAISS；具体启用情况取决于配置与依赖。", handover: "提供候选资料，交给 Fusion 与 Verification 继续处理。" },
    Fusion: { number: "03", name: "知识融合", role: "证据层", mark: "F", description: "把多路候选资料合并、去重，并保留来源与潜在冲突，让下游读取同一份上下文。", input: "多路检索批次与三源融合资料", output: "去重文档、融合摘要与冲突记录", code: "KnowledgeFusionAgent.fuse", method: "融合阶段使用 SimHash 去重与冲突检查；时序分支可用时，还提供 fuse_with_tfa 汇总入口。", handover: "整理候选资料；来源通过与否由下一步核验记录。" },
    Verification: { number: "04", name: "来源核验", role: "核验层", mark: "V", description: "检查资料出处、可追溯标识、时间信息和基础风险信号，记录接受或拒绝的原因。", input: "融合文档、来源标识与融合摘要", output: "通过核验的文档、拒绝记录与核验摘要", code: "ProvenanceKnowledgeVerificationAgent.verify", method: "当前默认实现检查 PMID、DOI、来源网址、检索时间等信息。来源核验衡量可追溯性，医学结论的适用性仍需专业复核。", handover: "为 DMA 准备已核验资料，并把核验摘要交给共识模块。" },
    DMA: { number: "05", name: "决策推理", role: "推理层", mark: "D", description: "结合当前记录与核验后的上下文调用推理后端，输出本次回答以及实际生成或降级状态。", input: "问题、核验资料、感知上下文与蒸馏信息", output: "推理结果、后端状态与人工复核标记", code: "DecisionMakingAgent.infer", method: "配置优先使用本地 Ollama llama3:8b；后端失败时允许旧路径降级，并显式记录状态。内部评分不解释为疾病概率。", handover: "生成本次推理结果；展示层进一步组织为交接线索。" },
    TFA: { number: "06", name: "时序研究预测", role: "预测层", mark: "T", description: "承载时序预测接口，以及新增的三年新发糖尿病研究头。不同任务对应各自的数据和权重。", input: "任务匹配的时序数据，或糖尿病基线五项指标", output: "可用性状态，或通过校验的三年研究风险估计", code: "TemporalForeseeingAgent.forecast / forecast_prospective", method: "糖尿病路径通过 attach_to_tfa 接入 mapfm_prospective_neural.research_predict。checkpoint 与训练报告校验后，forecast_prospective 才执行对应任务权重。", handover: "条件分支：未验证的旧时序概率不进入护理交接风险展示。", diabetes: "本路径的核心计算模块：使用公开 NAGALA 随访队列训练的新增研究权重。" },
    Consensus: { number: "07", name: "共识与接管", role: "门控层", mark: "C", description: "汇总推理、核验与风险信号，执行分层门控，并把需要处理的情况交给人工复核。", input: "DMA 结果、核验摘要与可用风险信号", output: "门控状态、升级原因与人工接管要求", code: "ConsensusModule.hierarchical_vote", method: "包含强制人工接管、DMA 否决和常规投票三个层次。最终输出还经过 readiness gate；网页复核由使用者填写并导出。", handover: "把本次自动流程接到人工复核；高风险演示不能自动放行。" },
    Privacy: { number: "08", name: "隐私与传输", role: "支撑层", mark: "P", description: "为智能体间消息提供加密与解密，并在反馈更新路径中处理裁剪和噪声。", input: "模块间消息与可选反馈梯度", output: "认证加密消息与处理后的反馈梯度", code: "RealPrivacyAgent.encrypt_message / decrypt_message", method: "当前默认实现使用 AES-GCM 认证加密。原始代码同时保留旧的模拟类。梯度加噪尚未配备隐私预算核算，不宣称形式化差分隐私保证。", handover: "支撑模块间消息传输；页面输入另有个人标识预检。" },
    Maintenance: { number: "09", name: "运行监测", role: "支撑层", mark: "M", description: "观察模块心跳、执行异常与异常输出，给协作引擎留下可检查的运行状态。", input: "注册模块、心跳与本次执行输出", output: "模块健康状态与异常标记", code: "MaintenanceAgent.monitor / detect_abnormal_output", method: "协作任务开始时检查注册模块，DMA 推理后检查异常输出。异常监测与 DegradationManager 的降级机制共同服务工程运行。", handover: "运行开始时监测模块，并检查推理输出异常。" },
    Topology: { number: "10", name: "通信拓扑", role: "支撑层", mark: "N", description: "管理模块之间的消息路由、邻居关系与重试队列，连接完整协作流程。", input: "发送者、接收者、消息内容与拓扑配置", output: "路由路径、投递结果与通信统计", code: "CommunicationTopologyManager.route_message", method: "支持 star 与 mesh。星型经配置的中心节点转发，网状允许节点直连；通过隐私模块处理消息，并记录投递失败。", handover: "串接感知、检索、融合、推理和人工接管消息。" }
  };
  const paths = {
    handover: { title: "护理交接协作链", copy: "文本与单次体征进入原始协作引擎，经过检索、融合、核验与推理，再进入共识门控和人工复核。TFA 的时序分支按配置与任务适用性处理。", link: "/?view=workspace#input-title", cta: "去工作台实际运行 ↗", selected: "Perception", active: ["Perception", "RAA", "Fusion", "Verification", "DMA", "Consensus", "Privacy", "Maintenance", "Topology"], conditional: ["TFA"] },
    diabetes: { title: "TFA · 3 年新发糖尿病研究头", copy: "自然语言先提取年龄、BMI、空腹血糖、收缩压、甘油三酯及基线状态，核对完整性后调用 TFA 的 forecast_prospective。此路径使用独立的纵向队列研究权重。", link: "/?view=workspace#medical-language-studio", cta: "输入自然语言并计算 ↗", selected: "TFA", active: ["TFA"], conditional: [] },
    knowledge: { title: "MedQuAD · 独立来源检索", copy: "英文问题进入 medquad_qa.py，由词面与预训练语义检索联合匹配来源答案。这条路径直接调用检索服务；医学盲评在同一工作台核查回答质量。", link: "/?view=workspace#medquad-studio", cta: "现场检索来源答案 ↗", selected: "RAA", active: [], conditional: [] }
  };
  const $ = id => document.getElementById(`architecture-${id}`);
  const detailContent = window.CareGuardArchitectureDetails || {};
  let selectedPath = "handover";
  let selectedAgent = "Perception";
  let selectedDetail = "mechanism";
  const agentOrder = Object.keys(agents);
  const element = (tag, className, text) => {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text) item.textContent = text;
    return item;
  };
  function renderDetail() {
    const detail = detailContent[selectedAgent];
    const panel = $("handbook-panel");
    if (!detail || !panel) return;
    panel.replaceChildren();
    root.querySelectorAll("[data-architecture-detail]").forEach(button => {
      const selected = button.dataset.architectureDetail === selectedDetail;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    const columns = element("div", "architecture-detail-columns");
    if (selectedDetail === "mechanism") {
      detail.steps.forEach(([title, copy], index) => {
        const card = element("article", "architecture-detail-step");
        card.append(element("span", "architecture-detail-index", `0${index + 1}`), element("h5", "", title), element("p", "", copy));
        columns.append(card);
      });
      panel.append(columns);
    } else if (selectedDetail === "collaboration") {
      const flow = element("div", "architecture-relation-flow");
      const parts = [
        ["上游 / 接收", detail.before[0], detail.before[1]],
        ["当前 / 处理", selectedAgent, agents[selectedAgent].description],
        ["下游 / 交付", detail.after[0], detail.after[1]]
      ];
      parts.forEach(([label, title, copy]) => {
        const card = element("article", "architecture-relation-node");
        card.append(element("span", "", label), element("h5", "", title), element("p", "", copy));
        flow.append(card);
      });
      panel.append(flow, element("p", "architecture-relation-note", detail.cooperation));
    } else {
      panel.append(element("p", "architecture-example-context", `合成示例 · ${detail.example.context}`));
      [["INPUT / 输入", detail.example.input], ["PROCESS / 处理", detail.example.processing], ["OUTPUT / 产出", detail.example.output]].forEach(([title, copy]) => {
        const card = element("article", "architecture-detail-example");
        card.append(element("h5", "", title), element("p", "", copy));
        columns.append(card);
      });
      panel.append(columns);
    }
  }
  function renderHandbook() {
    const detail = detailContent[selectedAgent];
    if (!detail || !$("handbook-title")) return;
    const agent = agents[selectedAgent];
    $("handbook-number").textContent = `${agent.number} / 10`;
    $("handbook-title").replaceChildren(document.createTextNode(selectedAgent), element("em", "", agent.name));
    $("handbook-tagline").textContent = detail.title;
    $("handbook-purpose").textContent = detail.purpose;
    $("handbook-scope").textContent = detail.scope;
    const index = agentOrder.indexOf(selectedAgent);
    $("agent-prev").setAttribute("aria-label", `上一个智能体：${agentOrder[(index + agentOrder.length - 1) % agentOrder.length]}`);
    $("agent-next").setAttribute("aria-label", `下一个智能体：${agentOrder[(index + 1) % agentOrder.length]}`);
    renderDetail();
  }
  function renderAgent(name) {
    if (!agents[name]) return;
    selectedAgent = name;
    const agent = agents[name];
    root.querySelectorAll("[data-architecture-agent]").forEach(button => {
      const selected = button.dataset.architectureAgent === name;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    $("agent-number").textContent = `${agent.number} / 10`;
    $("agent-role").textContent = agent.role;
    $("agent-mark").replaceChildren(document.createTextNode(agent.mark));
    const number = document.createElement("span"); number.textContent = agent.number;
    $("agent-mark").append(number);
    $("agent-title").replaceChildren(document.createTextNode(name));
    const chinese = document.createElement("em"); chinese.textContent = agent.name;
    $("agent-title").append(chinese);
    $("agent-description").textContent = agent.description;
    $("agent-input").textContent = agent.input;
    $("agent-output").textContent = agent.output;
    $("agent-code").replaceChildren(document.createTextNode("mapfm_ecosystem_repaired.py"), document.createElement("br"), document.createTextNode(agent.code));
    $("agent-method").textContent = agent.method;
    $("agent-context").textContent = selectedPath === "handover" ? `本路径：${agent.handover}`
      : selectedPath === "diabetes" && name === "TFA" ? agent.diabetes
      : selectedPath === "knowledge" && name === "RAA" ? "本路径使用 medquad_qa.py 的独立问答索引；这里的 RAA 属于原始协作引擎，二者应分别核查。"
      : "本路径不经过此模块；仍可点选了解其在原始 MAPFM 工程中的职责。";
    renderHandbook();
  }
  function selectPath(name) {
    if (!paths[name]) return;
    selectedPath = name;
    const path = paths[name];
    root.dataset.path = name;
    root.querySelectorAll("[data-architecture-path]").forEach(button => {
      const selected = button.dataset.architecturePath === name;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    root.querySelectorAll("[data-architecture-agent]").forEach(button => {
      const agent = button.dataset.architectureAgent;
      button.classList.toggle("is-muted", !path.active.includes(agent) && !path.conditional.includes(agent));
      button.classList.toggle("is-conditional", path.conditional.includes(agent));
    });
    root.querySelector(".architecture-human").classList.toggle("is-muted", name !== "handover");
    $("route-title").textContent = path.title;
    $("route-copy").textContent = path.copy;
    $("run-link").href = path.link;
    $("run-link").textContent = path.cta;
    renderAgent(path.selected);
  }
  root.addEventListener("click", event => {
    const detailTab = event.target.closest("[data-architecture-detail]");
    if (detailTab) {
      selectedDetail = detailTab.dataset.architectureDetail;
      renderDetail();
      return;
    }
    const pager = event.target.closest("#architecture-agent-prev, #architecture-agent-next");
    if (pager) {
      const offset = pager.id === "architecture-agent-next" ? 1 : -1;
      renderAgent(agentOrder[(agentOrder.indexOf(selectedAgent) + offset + agentOrder.length) % agentOrder.length]);
      return;
    }
    const path = event.target.closest("[data-architecture-path]");
    if (path) { selectPath(path.dataset.architecturePath); return; }
    const agent = event.target.closest("[data-architecture-agent]");
    if (agent) {
      renderAgent(agent.dataset.architectureAgent);
      if (window.matchMedia("(max-width: 1100px)").matches) {
        requestAnimationFrame(() => root.querySelector(".architecture-inspector").scrollIntoView({
          block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"
        }));
      }
    }
  });
  if ($("handbook-title")) {
    const link = element("a", "architecture-handbook-jump", "阅读执行机制、协作关系与示例 ↓");
    link.href = "#architecture-handbook";
    root.querySelector(".architecture-inspector").append(link);
  }
  const header = document.querySelector(".engineering-bridge-head > div");
  if (header) {
    const link = document.createElement("a");
    link.className = "architecture-source-jump";
    link.href = "/?view=home#mapfm-architecture";
    link.textContent = "查看 MAPFM 十智能体技术架构 ↗";
    header.append(link);
  }
  selectPath(selectedPath);
})();
