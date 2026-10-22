"use strict";

// Keep the former standalone review experience inside the interactive desk.
const reviewPanel = document.querySelector("#review-view");
const workspacePanel = document.querySelector("#workspace-view");
if (reviewPanel && workspacePanel) {
  reviewPanel.hidden = false;
  reviewPanel.classList.remove("view");
  workspacePanel.append(reviewPanel);
}

if ("scrollRestoration" in history) history.scrollRestoration = "manual";

const CASES = {
  chest: {
    title: "夜间突发胸痛",
    note: "82岁男性，夜间突发持续性胸部压榨感，向左臂放射，伴大汗、恶心和呼吸困难。护理员已停止活动并呼叫值班负责人。",
    heartRate: 112, spo2: 91, temperature: 36.8, respiratoryRate: 25, force: true,
  },
  stroke: {
    title: "疑似卒中表现",
    note: "76岁女性，晨间巡视发现突然口角歪斜、言语含糊，右侧上肢无力，症状约20分钟前出现。",
    heartRate: 96, spo2: 95, temperature: 36.6, respiratoryRate: 20, force: true,
  },
  change: {
    title: "慢病状态变化",
    note: "79岁男性，近三日活动后气促加重，双下肢水肿，夜间需垫高枕头入睡，较平日乏力。",
    heartRate: 102, spo2: 93, temperature: 36.7, respiratoryRate: 23, force: false,
  },
  baseline: {
    title: "夜班单次记录",
    note: "合成体征样本 21:00 的单次记录，未附现场主诉或处置描述。此案例用于演示交接信息待补全，不代表真实患者。",
    heartRate: 86, spo2: 96, temperature: 36.7, respiratoryRate: 18, force: false,
    source: "demo_assets/sample_vitals.csv · 21:00",
  },
  recheck: {
    title: "复测语境待核对",
    note: "合成体征样本 21:05 的单次记录。与表中其他时间点不推定属于同一人；需要人工核对测量条件和观察描述。",
    heartRate: 94, spo2: 95, temperature: 36.7, respiratoryRate: 20, force: false,
    source: "demo_assets/sample_vitals.csv · 21:05",
  },
  context: {
    title: "交接信息缺口",
    note: "合成体征样本 21:10 的单次记录，缺少症状、采集条件和已采取措施。请人工补全；单次数值不能给出诊断。",
    heartRate: 103, spo2: 93, temperature: 36.8, respiratoryRate: 23, force: false,
    source: "demo_assets/sample_vitals.csv · 21:10",
  },
};

const CASE_BRIEFS = {
  chest: { number: "001", index: "01 / 06", keyword: "ACUTE", story: "急性线索可能被长篇记录淹没。先核对发生时间、伴随表现和已采取行动，再运行本机筛查。", focus: "突发症状与呼叫动作", human: "优先级与后续处置" },
  stroke: { number: "002", index: "02 / 06", keyword: "SUDDEN", story: "“突然发生”是这段交接的关键上下文。页面保留言语、面部和单侧肢体变化，交由专业人员继续评估。", focus: "变化发生的时间与表现", human: "急性流程与进一步评估" },
  change: { number: "003", index: "03 / 06", keyword: "CHANGE", story: "较平日不同的状态值得明确交接，但当前原型没有已验证的时序恶化概率；请结合后续观察人工判断。", focus: "相对平日的变化", human: "是否补充信息或升级评估" },
  baseline: { number: "004", index: "04 / 06", keyword: "BASE", story: "样本表给出一组单次合成体征，却没有主诉与已采取措施。工作台保留缺口，等待人工补充。", focus: "交接记录是否完整", human: "是否需要补充现场观察" },
  recheck: { number: "005", index: "05 / 06", keyword: "CHECK", story: "时间戳不能证明两行样本属于同一人。本案例训练先核对采集条件，再解释任何数值差异。", focus: "来源、对象与采集条件", human: "是否可比较两条记录" },
  context: { number: "006", index: "06 / 06", keyword: "GAP", story: "没有症状、测量条件和处置动作，就不应从一组体征跳到诊断。先把缺少的信息标出来。", focus: "体征之外的上下文", human: "补录与核验的优先顺序" },
};

CASES.draft = { title: "新建演示案例", note: "", heartRate: "", spo2: "", temperature: "", respiratoryRate: "", force: false, source: "当前浏览器草稿 · 请仅使用合成/脱敏内容" };
CASE_BRIEFS.draft = { number: "NEW", index: "新建 / 10", keyword: "DRAFT", story: "填写合成护理交接记录与体征，完成实际筛查和人工复核后，可选择保存到本机案例库。", focus: "时间、变化与处置", human: "复核决定与来源状态" };
const CASE_LIBRARY_KEY = "careguard.caseLibrary.v1";
const MAX_LIBRARY_ITEMS = 10;
const PRESET_CASE_COUNT = 6;
let savedCases = [];

function readSavedCases() {
  try {
    const raw = JSON.parse(localStorage.getItem(CASE_LIBRARY_KEY) || "[]");
    if (!Array.isArray(raw)) return [];
    return raw.filter((item) => item && /^saved-[a-z0-9-]+$/.test(item.id) &&
      typeof item.title === "string" && item.title.length <= 60 &&
      typeof item.note === "string" && item.note.length <= 2000 &&
      typeof item.observedChange === "string" && item.observedChange.length <= 600 &&
      typeof item.actionTaken === "string" && item.actionTaken.length <= 600 &&
      [[item.heartRate,30,220],[item.spo2,50,100],[item.temperature,32,43],[item.respiratoryRate,5,60]].every(([value,min,max]) => Number.isFinite(Number(value)) && Number(value) >= min && Number(value) <= max)
    ).slice(0, MAX_LIBRARY_ITEMS - PRESET_CASE_COUNT);
  } catch (_error) { return []; }
}

function registerSavedCases() {
  savedCases.forEach((item, index) => {
    CASES[item.id] = item;
    CASE_BRIEFS[item.id] = { number: String(index + 7).padStart(3, "0"), index: `${String(index + 7).padStart(2, "0")} / 10`, keyword: "LOCAL", story: "此案例由当前浏览器保存。记录仅供合成演示；重新载入后必须再次运行筛查，旧结果和复核不沿用。", focus: "保存的交接上下文", human: "本次重新复核", };
  });
}

savedCases = readSavedCases();
registerSavedCases();

const MATERIALS = {
  input: { index: "01 / 06", image: "/assets/diagrams/input-flow.svg", alt: "交接记录到结构化输入的原创流程示意", kind: "PRODUCT DESIGN / 输入流程", overprint: "把观察写清楚，\n再交给系统处理。", title: "结构化交接输入", context: "把观察记录、体征及已采取的措施组织成可核对的输入。示意图对应当前工作台字段，不含患者数据。", can: "输入结构与设计意图", cannot: "实时执行结果或临床效果", origin: "工程对应：site.js / handoff.js · 原创示意" },
  agents: { index: "02 / 06", image: "/assets/diagrams/agent-map.svg", alt: "MAPFM 主链、条件分支与支撑模块示意", kind: "ENGINEERING / 模块协作", overprint: "职责分开，\n过程连起来。", title: "MAPFM 协作链", context: "展示主链模块、TFA 条件分支与隐私、监测、通信支撑；模块不等于十个独立大模型。", can: "工程模块及协作职责", cannot: "每个模块实时在线或临床有效性", origin: "工程对应：mapfm_ecosystem_repaired.py · 原创示意" },
  sources: { index: "03 / 06", image: "/assets/diagrams/source-check.svg", alt: "来源标识、时间与核验原因的示意", kind: "TRACEABILITY / 来源核验", overprint: "有来源，\n也要有适用边界。", title: "来源核验设计", context: "说明候选资料的出处与可追溯信息如何进入核验记录。出处可追溯不等于医学结论正确。", can: "来源核验的检查项", cannot: "资料适用性或诊疗资格", origin: "工程对应：ProvenanceKnowledgeVerificationAgent.verify · 原创示意" },
  review: { index: "04 / 06", image: "/assets/diagrams/review-loop.svg", alt: "系统结果进入人工复核后记录决定的示意", kind: "HUMAN REVIEW / 接管流程", overprint: "自动流程之后，\n决定仍然归于人。", title: "人工复核闭环", context: "结果、来源、复核决定与说明构成可检查的接管流程。示意图不是本次复核回执。", can: "人工接管与复核的设计", cannot: "已完成复核或实际处置结果", origin: "工程对应：careguard_presenter.py / site.js · 原创示意" },
  research: { index: "05 / 06", image: "/assets/diagrams/research-head.svg", alt: "五项基线特征接入 TFA 三年糖尿病研究头的示意", kind: "RESEARCH / 条件计算", overprint: "先检查输入，\n再讨论研究估计。", title: "TFA 研究计算分支", context: "仅在任务和基线条件符合时运行现有三年糖尿病研究头；缺失或冲突时停止输出。", can: "研究计算的输入与门控关系", cannot: "外部临床校准或任意疾病概率", origin: "工程对应：mapfm_prospective_neural.py · 原创示意" },
  audit: { index: "06 / 06", image: "/assets/diagrams/audit-trail.svg", alt: "请求、运行、来源与人工说明连接的审计示意", kind: "AUDIT DESIGN / 可追溯记录", overprint: "留下结果，\n更要留下过程。", title: "审计记录结构", context: "说明本次请求、运行状态、来源与人工说明的关系。真实记录需要进入工作台主动运行后生成。", can: "可追溯记录的组织方式", cannot: "已经生成的运行回执", origin: "工程对应：careguard_presenter.py / handoff.js · 原创示意" },
};

const FEATURES = {
  observe: {
    overline: "01 / OBSERVE THE WHOLE PICTURE",
    title: "先看见人记录了什么。",
    description: "自由文本与生命体征并置。时间、伴随表现和已采取行动不会被一个预测标签盖住。",
    eyebrow: "SYNTHETIC INPUT / 交接记录",
    badge: "原始观察保留",
    content: '<div class="feature-note">夜间突发持续性胸部压榨感，伴大汗、恶心与呼吸困难。护理员已停止活动并呼叫值班负责人。</div><div class="feature-chip-row"><span>心率 112 次/分</span><span>血氧 91%</span><span>呼吸 25 次/分</span></div>',
  },
  verify: {
    overline: "02 / SHOW THE SOURCE STATE",
    title: "资料从哪里来，要说清楚。",
    description: "动态检索证据与人工整理的离线公共信息卡分开展示。没有通过来源核验的动态资料，不被补成引用。",
    eyebrow: "EVIDENCE / SOURCE LABELS",
    badge: "示意：状态可为空",
    content: '<div class="feature-evidence-row"><span>动态检索资料</span><b>可能为空 · 不补造</b></div><div class="feature-evidence-row"><span>离线公共信息卡</span><b>人工整理 · 单列</b></div><div class="feature-evidence-row"><span>医学结论</span><b>不自动证明</b></div>',
  },
  review: {
    overline: "03 / KEEP THE HUMAN IN THE LOOP",
    title: "AI 不拥有最后决定权。",
    description: "高风险案例进入人工优先复核；复核说明和决定可导出为审计摘要。输入一旦改变，旧结果失效。",
    eyebrow: "DECISION GATE / HUMAN REVIEW",
    badge: "演示门控示意",
    content: '<div class="feature-review-row"><strong>P1</strong><span>立即人工复核<br>系统不自动放行</span><i>↗</i></div><div class="feature-chip-row"><span>复核人</span><span>判断依据</span><span>审计导出</span></div>',
  },
};

const ATLAS_NUMBERS = { chest: "001", stroke: "002", change: "003" };

const AUDIENCES = {
  recorder: { number: "01", overline: "OBSERVATION / RECORD", title: "先把现场讲清楚。", description: "记录人员保留发生时间、变化与已采取措施，并把生命体征放在同一上下文。系统不把一条记录自动变成诊断。", primary: "原始观察", secondary: "体征并置", sample: "夜间突发持续性胸部压榨感，伴大汗与呼吸困难；已呼叫值班负责人。", meta: "SYNTHETIC CASE / 001", steps: ["输入事实", "补全体征", "交给复核"], action: "载入合成案例", destination: "workspace" },
  reviewer: { number: "02", overline: "DECISION / HUMAN GATE", title: "看见线索，也看见刹车。", description: "复核人员核对本次推理状态、动态来源与离线信息卡，填写自己的决定。高风险演示案例不能由系统自动放行。", primary: "P1 需人工复核", secondary: "审计摘要", sample: "优先级只是本次演示线索；复核决定、说明和责任人由人工记录。", meta: "REVIEW FLOW / HUMAN OWNED", steps: ["检查过程", "辨清来源", "记录决定"], action: "进入复核工作台", destination: "workspace" },
  evaluator: { number: "03", overline: "PROOF / CLAIM LEDGER", title: "知道已经做到哪一步。", description: "评审与研究者可以逐项检查实现、历史快照和未验证边界。代码测试证明软件行为，不被包装成临床有效性。", primary: "8 项主张档案", secondary: "未验证显式标记", sample: "本机可运行 ≠ 临床有效；历史自检成功 ≠ 此刻服务在线。", meta: "EVIDENCE / NO CLINICAL CLAIM", steps: ["查看快照", "选择主张", "复现路径"], action: "打开证据档案", destination: "evidence" },
};

const CLAIM_FILES = [
  { status: "已实现", check: "在工作台以合成案例调用 /screening/engineering：原始 MAPFM 预处理解析单次体征，随后运行多智能体引擎；查看本次后端、优先级线索和人工门控。", boundary: "单次体征以文本进入模型，不是时序预测；可调用不等于诊断准确。", paths: ["api.py", "mapfm_utils/multimodal_utils.py", "tests/test_engineering_bridge.py"] },
  { status: "最近快照", check: "检查最近合成案例自检 JSON 中的时间、Ollama 生成标记和降级标记；工作台本次运行另行显示实时结果。", boundary: "历史自检不能证明当前服务在线，也不承诺固定延迟。", paths: ["artifacts/competition/careguard_live_smoke_latest.json", "careguard_smoke.py"] },
  { status: "有限证据", check: "在本次结果的“证据”标签中分别查看通过核验的动态资料与人工整理的离线公共信息卡；零条动态资料如实显示零条。", boundary: "有资料来源不意味着相关医学结论已获验证，离线卡不能当作本次实时检索。", paths: ["careguard_presenter.py", "tests/test_competition_evidence.py"] },
  { status: "已实现", check: "运行 P1 合成案例，检查没有“常规观察”选项、说明必填；完成复核后导出审计 JSON，再修改输入验证旧结果作废。", boundary: "审计摘要证明界面流程留痕，不证明复核决定的临床正确性。", paths: ["careguard_presenter.py", "tests/test_careguard_presenter.py"] },
  { status: "未启用", check: "检查展示层隔离逻辑及就绪性测试：时序概率和旧诊断标签不进入本版风险分流展示。", boundary: "不能把被隔离的旧模型输出写成已验证的养老场景能力。", paths: ["careguard_presenter.py", "tests/test_competition_readiness.py"] },
  { status: "未验证", check: "本页明确标注尚无独立外部临床验证；目前仅能核查软件行为和合成案例链路。", boundary: "不得宣称诊断准确率、治疗效果、临床可用或医疗使用资格。", paths: ["EVIDENCE_MATRIX.md", "COMPETITION_UPGRADE.md"] },
  { status: "不属于成果", check: "参赛范围和证据矩阵将本次交付界定为软件应用原型。", boundary: "不宣称已交付护理机器人、床头硬件或真实机构降本结果。", paths: ["COMPETITION_UPGRADE.md", "EVIDENCE_MATRIX.md"] },
  { status: "已实现 / 待外部验证", check: "在工作台输入基线血压、BMI、空腹血糖和血脂，调用 /risk/diabetes-8y；逐项对照 Wilson 等 2007 年论文 Table 6，修改输入确认评分改变。", boundary: "这是发表的美国队列 8 年新发糖尿病评分，不是本项目训练的中国人群预测模型；未验证临床适用性。", paths: ["diabetes_risk.py", "api.py", "tests/test_diabetes_risk.py"] },
];

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const state = { view: "home", caseId: "chest", launchCaseId: "chest", screening: null, audit: null, engineering: null, resultTab: "steps", running: false, inputEdited: false, savedRequestId: null, loadedSignature: null };

function renderCaseLibrary() {
  const list = $("#custom-case-list");
  list.replaceChildren();
  $("#case-library-count").textContent = `${String(PRESET_CASE_COUNT + savedCases.length).padStart(2, "0")} / 10`;
  savedCases.forEach((item, index) => {
    const row = node("div", "custom-case-row");
    const picker = node("button", "case-picker" + (state.caseId === item.id ? " is-active" : ""));
    picker.type = "button"; picker.dataset.case = item.id;
    picker.append(node("small", "", `${String(index + 7).padStart(2, "0")} / LOCAL`), node("strong", "", item.title), node("span", "", "本机保存 · 重新筛查"));
    const remove = node("button", "custom-case-remove", "移除");
    remove.type = "button"; remove.dataset.removeCase = item.id;
    remove.setAttribute("aria-label", `从本机案例库移除 ${item.title}`);
    row.append(picker, remove); list.append(row);
  });
  $("#new-case-button").disabled = savedCases.length >= MAX_LIBRARY_ITEMS - PRESET_CASE_COUNT;
}

function addSessionEvent(stage, title, description, reset = false) {
  const list = $("#session-events");
  if (!list) return;
  if (reset) list.replaceChildren();
  const item = node("li");
  const icon = node("span", "session-event-icon", String(list.children.length + 1).padStart(2, "0"));
  const copy = node("div", "session-event-copy");
  copy.append(node("span", "", stage), node("strong", "", title), node("p", "", description));
  const time = node("time", "", new Date().toLocaleTimeString("zh-CN", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }));
  item.append(icon, copy, time);
  list.append(item);
  while (list.children.length > 8) list.firstElementChild.remove();
}

function setCaseBrief(caseId) {
  const brief = CASE_BRIEFS[caseId];
  if (!brief) return;
  $("#brief-number").textContent = brief.number;
  $("#brief-index").textContent = brief.index;
  $("#brief-keyword").textContent = brief.keyword;
  $("#case-brief-title").textContent = CASES[caseId].title;
  $("#brief-story").textContent = brief.story;
  $("#brief-focus").textContent = brief.focus;
  $("#brief-human").textContent = brief.human;
  $("#brief-source").textContent = CASES[caseId].source || "项目预置合成情境 · 非真实患者";
}

function setMaterial(key) {
  const item = MATERIALS[key];
  if (!item) return;
  const preview = $("#material-image");
  preview.src = item.image;
  preview.alt = item.alt;
  $("#material-current").textContent = item.index;
  $("#material-kind").textContent = item.kind;
  $("#material-overprint").textContent = item.overprint;
  $("#material-title-detail").textContent = item.title;
  $("#material-context").textContent = item.context;
  $("#material-can").textContent = item.can;
  $("#material-cannot").textContent = item.cannot;
  $("#material-origin").textContent = item.origin;
  $("#material-open").href = item.image;
  $$('[data-material]').forEach((tab) => {
    const active = tab.dataset.material === key;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
}

function node(tag, className, value) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (value !== undefined && value !== null) element.textContent = String(value);
  return element;
}

function mountInteractiveDepth() {
  $(".case-brief-art>small").id = "case-origin-label";
  const preflight = node("div", "input-preflight");
  preflight.id = "input-preflight";
  preflight.setAttribute("role", "status");
  preflight.setAttribute("aria-live", "polite");
  preflight.innerHTML = '<div class="preflight-mark" aria-hidden="true">✳</div><div><span>INPUT / PRIVACY PREFLIGHT</span><strong id="preflight-title">预置合成案例 · 可用于演示</strong><p id="preflight-message">提交前检查常见身份标识。检测不能替代人工脱敏；请勿输入真实患者资料。</p></div>';
  $(".field-caption").insertAdjacentElement("afterend", preflight);

  const proof = node("section", "live-proof");
  proof.setAttribute("aria-labelledby", "live-proof-title");
  proof.innerHTML = '<div class="live-proof-head"><div><span>LIVE SESSION / NOT A HISTORICAL SNAPSHOT</span><h2 id="live-proof-title">这一刻的运行，<br><em>单独留一页。</em></h2><p>这里仅映射当前浏览器会话中工作台返回的状态，不使用历史自检充当实时结果；刷新后重置。</p></div><b id="live-proof-state">尚未运行</b></div><div class="live-proof-path" aria-label="当前会话核验路径"><div><small>01 / REQUEST</small><strong id="proof-request">等待发起</strong><span>仅显示请求编号，不显示交接原文</span></div><div><small>02 / ENGINE</small><strong id="proof-engine">尚未运行</strong><span>实际运行状态，不借用历史快照</span></div><div><small>03 / SOURCES</small><strong id="proof-sources">尚未核验</strong><span>动态来源与离线卡分列</span></div><div><small>04 / HUMAN GATE</small><strong id="proof-human">等待结果</strong><span>最终决定必须由人确认</span></div></div><div class="live-proof-foot"><p id="proof-boundary">先在工作台运行一个合成案例。这里不会预填结果，也不显示临床有效性主张。</p><button type="button" data-nav="workspace">前往现场运行 <span>↗</span></button></div>';
  $(".source-chain").before(proof);
  const researchLink = node("button", "research-lab-link", "进入三维研究图谱 ↗");
  researchLink.type = "button"; researchLink.dataset.nav = "lab";
  $(".research-source-note").after(researchLink);
  const journalLink = node("button", "journal-lab-link", "在三维图谱中检查输入与门控 ↗");
  journalLink.type = "button"; journalLink.dataset.nav = "lab";
  $(".journal-contract").append(journalLink);
}

function sensitiveInputReason(value) {
  if (/(?:^|\D)1[3-9]\d{9}(?!\d)/.test(value)) return "疑似手机号码";
  if (/(?:^|\D)\d{17}[\dXx](?!\d)/.test(value)) return "疑似身份证号码";
  if (/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.test(value)) return "疑似电子邮箱";
  if (/(?:姓名|患者姓名)\s*[:：]\s*[\u4e00-\u9fa5]{2,4}/.test(value)) return "明确标注的姓名";
  if (/(?:病历号|住院号)\s*[:：]?\s*[A-Za-z0-9-]{5,}/.test(value)) return "疑似病历或住院编号";
  return "";
}

function updateInputPreflight() {
  const reason = sensitiveInputReason(["#handover-title", "#case-note", "#observed-change", "#action-taken"].map((id) => $(id).value).join("\n"));
  const preflight = $("#input-preflight");
  preflight.classList.toggle("is-alert", Boolean(reason));
  preflight.classList.toggle("is-edited", state.inputEdited && !reason);
  $("#preflight-title").textContent = reason ? `检测到${reason} · 已暂停提交` : state.inputEdited ? "交接内容已编辑 · 请人工确认脱敏" : "合成案例 · 可用于演示";
  $("#preflight-message").textContent = reason
    ? "请删除身份标识后再运行。此检查只识别常见格式，不能保证发现全部个人信息。"
    : "未发现常见格式的身份标识；仍需人工确认没有真实姓名、病历或其他可识别信息。";
  $("#run-button").disabled = state.running || Boolean(reason);
  $("#case-origin-label").textContent = state.inputEdited ? "模板已编辑 · 内容未核验" : "合成情境 · 非真实患者";
  $(".hero-card-bottom span:first-child").textContent = state.inputEdited ? "已编辑模板" : "合成案例";
  return reason;
}

function renderSessionProof(phase = "idle") {
  const view = state.screening;
  const status = $("#live-proof-state");
  if (!view) {
    status.textContent = phase === "running" ? "正在运行" : phase === "error" ? "本次失败" : "尚未运行";
    $("#proof-request").textContent = phase === "running" ? "等待返回" : "等待发起";
    $("#proof-engine").textContent = phase === "running" ? "正在运行" : phase === "error" ? "本次失败" : "尚未运行";
    $("#proof-sources").textContent = phase === "running" ? "等待核验" : "尚未核验";
    $("#proof-human").textContent = "等待结果";
    $("#proof-boundary").textContent = phase === "error" ? "本次请求没有可用结果，不用历史自检填补；请检查本机服务后重试。" : "先在工作台运行一个合成案例。这里不会预填结果，也不显示临床有效性主张。";
    return;
  }
  const reviewed = state.audit?.human_review?.status === "completed";
  status.textContent = reviewed ? "人工决定已记录" : "本次结果 · 待人工复核";
  $("#proof-request").textContent = String(view.request_id || "编号未提供");
  $("#proof-engine").textContent = view.engine_label || "状态未确认";
  $("#proof-sources").textContent = `${view.evidence_count || 0} 动态 / ${view.reference_count || 0} 离线`;
  $("#proof-human").textContent = reviewed ? "人工决定已记录" : `${view.priority?.code || "—"} · 等待复核`;
  $("#proof-boundary").textContent = "以上仅为当前浏览器会话的演示链路状态；来源数量和运行成功均不能证明临床有效性。";
}

function routeFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const view = params.get("view");
  return {
    view: view === "review" ? "workspace" : ["home", "workspace", "evidence", "lab", "join"].includes(view) ? view : "home",
    caseId: CASES[params.get("case")] ? params.get("case") : "chest",
  };
}

function navigate(view, caseId = state.caseId, push = true) {
  if (CASES[caseId] && caseId !== state.caseId && !loadCase(caseId)) {
    if (!push) history.replaceState({ view: state.view, caseId: state.caseId }, "", state.view === "home" ? "/" : `/?view=${state.view}${state.view === "workspace" ? `&case=${state.caseId}` : ""}`);
    return;
  }
  state.view = view;
  document.body.dataset.view = view;
  for (const item of ["home", "workspace", "evidence", "lab", "join"]) {
    $("#" + item + "-view").hidden = item !== view;
  }
  $$('[data-nav]').forEach((button) => {
    if (button.classList.contains("nav-link")) button.classList.toggle("is-active", button.dataset.nav === view);
  });
  document.title = ({ home: "安护智链 CareLink — 让照护风险被看见", workspace: "交互工作台 — CareLink", evidence: "证据与边界 — CareLink", lab: "三维研究图谱 — CareLink", join: "加入我们 — CareLink" })[view];
  if (push) {
    const url = view === "home" ? "/" : `/?view=${view}${view === "workspace" ? `&case=${state.caseId}` : ""}`;
    history.pushState({ view, caseId: state.caseId }, "", url);
  }
  if (!push && new URLSearchParams(window.location.search).get("view") === "review") {
    history.replaceState({ view: "workspace", caseId: state.caseId }, "", "/?view=workspace#review-desk");
  }
  const hashTarget = !push && window.location.hash
    ? document.getElementById(window.location.hash.slice(1)) : null;
  if (hashTarget) requestAnimationFrame(() => hashTarget.scrollIntoView({ block: "start", behavior: "instant" }));
  else window.scrollTo({ top: 0, behavior: "instant" });
  document.dispatchEvent(new Event("careguard:viewchange"));
  requestAnimationFrame(updateReadingProgress);
  loadStatus();
}

const WORKFLOW_STATES = {
  idle: ["current", "pending", "pending", "pending", "pending"],
  running: ["complete", "current", "pending", "pending", "pending"],
  result: ["complete", "complete", "complete", "current", "pending"],
  reviewed: ["complete", "complete", "complete", "complete", "complete"],
  error: ["complete", "error", "pending", "pending", "pending"],
};

function updateWorkflow(phase) {
  const stages = WORKFLOW_STATES[phase] || WORKFLOW_STATES.idle;
  const labels = { current: "当前", complete: "已完成", pending: "待处理", error: "失败" };
  $$('[data-workflow-stage]').forEach((step, index) => {
    step.classList.remove("is-current", "is-complete", "is-pending", "is-error");
    step.classList.add(`is-${stages[index]}`);
    step.querySelector("b").textContent = labels[stages[index]];
  });
  $("#workspace-phase").textContent = {
    idle: "等待输入", running: "正在本机运行", result: "等待人工复核",
    reviewed: "人工复核已记录", error: "本次运行失败",
  }[phase] || "等待输入";
  $("#run-phase").textContent = $("#workspace-phase").textContent;
  const checkpoints = {
    idle: ["尚未运行", "尚未核验", "等待结果"],
    running: ["正在运行", "等待结果", "等待结果"],
    result: ["本次已生成", "来源已呈现", "待人工复核"],
    reviewed: ["本次已生成", "来源已呈现", "人工决定已记录"],
    error: ["本次失败", "未能核验", "无法复核"],
  }[phase] || ["尚未运行", "尚未核验", "等待结果"];
  ["run", "source", "human"].forEach((key, index) => {
    $("#checkpoint-" + key).textContent = checkpoints[index];
  });
}

function setAudience(key) {
  const item = AUDIENCES[key];
  if (!item) return;
  $$('[role="tab"][data-audience]').forEach((tab) => {
    const active = tab.dataset.audience === key;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  const panel = $("#audience-panel");
  // The audience copy is fixed product copy, never model or user-provided HTML.
  panel.innerHTML = `<div class="audience-story"><span class="audience-overline">${item.overline}</span><h3>${item.title}</h3><p>${item.description}</p><div class="audience-step-list">${item.steps.map((step, index) => `<div><b>0${index + 1}</b><span>${step}</span></div>`).join("")}</div><button type="button" class="audience-cta" data-nav="${item.destination}">${item.action} <span>↗</span></button></div><div class="audience-preview"><div class="audience-preview-top"><span class="console-dots"><i></i><i></i><i></i></span><b>CARELINK / ${item.number}</b><small>LOCAL DEMO</small></div><div class="audience-preview-main"><div class="audience-preview-overline">${item.meta}</div><div class="audience-preview-card"><span>ACTIVE VIEW</span><strong>${item.primary}</strong><p>${item.sample}</p><div class="audience-preview-tags"><b>${item.secondary}</b><b>非临床决策</b></div></div><div class="audience-preview-progress"><span>观察</span><i></i><span>核验</span><i></i><span>人工决定</span></div></div></div>`;
  panel.dataset.audience = key;
}

function selectClaim(row) {
  if (!row) return;
  const rows = $$('[data-claim-state]');
  const index = rows.indexOf(row);
  const file = CLAIM_FILES[index];
  if (!file) return;
  rows.forEach((item) => item.setAttribute("aria-pressed", String(item === row)));
  rows.forEach((item) => item.classList.toggle("is-selected", item === row));
  $("#claim-file-number").textContent = String(index + 1).padStart(2, "0");
  $("#claim-file-status").textContent = file.status;
  $("#claim-file-title").textContent = row.querySelector("h3").textContent;
  $("#claim-file-summary").textContent = row.querySelector("p").textContent;
  $("#claim-file-check").textContent = file.check;
  $("#claim-file-boundary").textContent = file.boundary;
  $("#claim-file-paths").replaceChildren(...file.paths.map((path) => node("code", "", path)));
}

function setClaimFilter(filter) {
  const allowed = ["all", "implemented", "limited", "unverified"];
  if (!allowed.includes(filter)) return;
  const rows = $$("[data-claim-state]");
  let visible = 0;
  rows.forEach((row) => {
    row.hidden = filter !== "all" && row.dataset.claimState !== filter;
    if (!row.hidden) visible += 1;
  });
  $$("[data-claim-filter]").forEach((button) => {
    const active = button.dataset.claimFilter === filter;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
    const count = button.dataset.claimFilter === "all" ? rows.length
      : rows.filter((row) => row.dataset.claimState === button.dataset.claimFilter).length;
    button.querySelector("span").textContent = String(count).padStart(2, "0");
  });
  $("#evidence-claim-count").textContent = `显示 ${visible} 项主张`;
  if (rows.find((row) => row.classList.contains("is-selected"))?.hidden) selectClaim(rows.find((row) => !row.hidden));
}

function updateReadingProgress() {
  const distance = document.documentElement.scrollHeight - window.innerHeight;
  const amount = distance > 0 ? Math.min(1, Math.max(0, window.scrollY / distance)) : 0;
  $("#reading-progress").style.transform = `scaleX(${amount})`;
}

function setAtlasCase(caseId) {
  const selected = CASES[caseId];
  if (!selected) return;
  $(".atlas-shell").dataset.caseId = caseId;
  $("#atlas-number").textContent = `OBSERVATION / ${ATLAS_NUMBERS[caseId]}`;
  $("#atlas-case-title").textContent = selected.title;
  $("#atlas-case-note").textContent = selected.note;
  $("#atlas-heart").textContent = String(selected.heartRate);
  $("#atlas-spo2").textContent = `${selected.spo2}%`;
  $("#atlas-breath").textContent = String(selected.respiratoryRate);
  $$('[data-atlas-case]').forEach((button) => {
    const active = button.dataset.atlasCase === caseId;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
}

function setLaunchCase(caseId) {
  const selected = CASES[caseId];
  if (!selected) return;
  state.launchCaseId = caseId;
  $("#launch-case-title").textContent = selected.title;
  $("#launch-case-note").textContent = selected.note;
  $("#launch-heart").textContent = String(selected.heartRate);
  $("#launch-spo2").textContent = `${selected.spo2}%`;
  $("#launch-breath").textContent = String(selected.respiratoryRate);
  $("#medical-case-title").textContent = selected.title;
  $(".medical-monitor-title small").textContent = `CASE ${CASE_BRIEFS[caseId].number} / SYNTHETIC`;
  $("#medical-heart").textContent = String(selected.heartRate);
  $("#medical-spo2").textContent = `${selected.spo2}%`;
  $("#medical-breath").textContent = String(selected.respiratoryRate);
  $("#home-medical-wave").dataset.medicalRate = selected.heartRate;
  $$('[data-launch-case]').forEach((tab) => {
    const active = tab.dataset.launchCase === caseId;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
}

function setFeature(key) {
  const feature = FEATURES[key];
  if (!feature) return;
  $$("[data-feature]").forEach((tab) => {
    const active = tab.dataset.feature === key;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  const canvas = $("#feature-canvas");
  // Feature content is fixed, authored UI copy; no model or user data is interpolated here.
  canvas.innerHTML = `<div class="feature-content"><span class="feature-overline">${feature.overline}</span><h3>${feature.title}</h3><p>${feature.description}</p><div class="feature-visual"><div class="feature-visual-head"><span>${feature.eyebrow}</span><b>${feature.badge}</b></div><div class="feature-visual-body">${feature.content}</div></div></div>`;
}

function updateCharacterCount() {
  $("#char-count").textContent = `${$("#case-note").value.length} / 2000`;
}

function currentInputSignature() {
  return JSON.stringify([
    $("#handover-title").value.trim(), $("#event-time").value,
    $("#case-note").value.trim(), $("#observed-change").value.trim(), $("#action-taken").value.trim(),
    $("#heart-rate").value, $("#spo2").value,
    $("#temperature").value, $("#respiratory-rate").value,
    $("#force-high-risk").checked,
  ]);
}

function renderEngineeringBridge(phase = "idle") {
  const data = state.engineering;
  if (data) {
    $("#engineering-parse").textContent = `${data.parsed_observation_count || 0} 条已解析`;
    $("#engineering-source").textContent = data.core_source_match ? `原始包一致 · ${String(data.core_sha256 || "").slice(0, 12)}` : "源码指纹有差异";
    $("#engineering-run").textContent = data.ollama_generation_verified ? "Ollama 本次已生成" : data.dma_backend === "legacy_fallback" ? "本次已降级" : "本次后端待核实";
    $("#engineering-route-state").textContent = `请求 ${state.screening?.request_id || "—"} · 工程计算已返回`;
    $("#engineering-feed").textContent = `单次体征→原工程预处理→${data.active_model_input === "clinical_text_from_parsed_single_observation" ? "实际文本输入" : "输入状态待核实"}；未进行时序预测。`;
    return;
  }
  $("#engineering-parse").textContent = phase === "running" ? "正在解析" : "等待输入";
  $("#engineering-source").textContent = phase === "running" ? "核对中" : "待读取";
  $("#engineering-run").textContent = phase === "running" ? "正在运行" : phase === "error" ? "本次失败" : "尚未运行";
  $("#engineering-route-state").textContent = phase === "running" ? "已发起真实工程请求" : phase === "error" ? "本次工程计算未成功" : "尚未发起工程计算";
  $("#engineering-feed").textContent = phase === "error" ? "失败不会显示旧结果；请检查本机服务后重试。" : "运行后显示本次输入通道与请求状态；源码一致不代表临床有效。";
}

function showIdle(message) {
  state.engineering = null;
  renderEngineeringBridge("idle");
  $("#handover-packet").hidden = true;
  const output = $("#screening-output");
  output.replaceChildren();
  const idle = node("div", "output-idle");
  idle.append(node("div", "idle-symbol", "✳"), node("strong", "", message || "等待一次安全的演示输入"));
  idle.append(node("p", "", "载入案例并开始筛查。真实运行后的线索、证据状态与人工复核入口会在这里出现。"));
  const progress = node("div", "idle-progress");
  progress.append(node("span", "", "输入"), node("i"), node("span", "", "核验"), node("i"), node("span", "", "复核"));
  idle.append(progress);
  output.append(idle);
  $("#result-state").textContent = "WAITING FOR INPUT";
  $("#run-engine").textContent = "尚未运行";
  $("#run-sources").textContent = "尚未核验";
  $("#run-review").textContent = "等待运行";
  updateWorkflow("idle");
  renderSessionProof();
}

function invalidateResult() {
  if (state.running || !state.screening) return;
  state.screening = null;
  state.audit = null;
  state.savedRequestId = null;
  showIdle("输入已变化，旧结果和复核记录已作废");
  addSessionEvent("INPUT CHANGED", "旧结果已作废", "输入更改后不沿用之前的筛查结果与人工复核记录。请重新运行。");
}

function caseInputSignature() {
  return JSON.stringify([
    $("#handover-title").value, $("#event-time").value, $("#case-note").value,
    $("#observed-change").value, $("#action-taken").value, $("#heart-rate").value,
    $("#spo2").value, $("#temperature").value, $("#respiratory-rate").value,
    $("#force-high-risk").checked,
  ]);
}

function loadCase(caseId, discardConfirmed = false) {
  const selected = CASES[caseId];
  if (!selected) return false;
  if (!discardConfirmed && state.inputEdited && state.loadedSignature !== null &&
      caseInputSignature() !== state.loadedSignature &&
      !window.confirm("当前交接内容尚未保存。切换案例会丢失这次编辑，确定继续吗？")) return false;
  state.caseId = caseId;
  setCaseBrief(caseId);
  $("#workspace-case-label").textContent = selected.title;
  $("#workspace-monitor-hr").textContent = String(selected.heartRate);
  $("#workspace-monitor-spo2").textContent = `${selected.spo2}%`;
  $("#workspace-monitor-rr").textContent = String(selected.respiratoryRate);
  $("#workspace-medical-wave").dataset.medicalRate = selected.heartRate;
  $("#run-case").textContent = selected.title;
  $("#handover-title").value = caseId === "draft" ? "" : selected.title;
  $("#event-time").value = selected.eventTime || "";
  $("#case-note").value = selected.note;
  $("#observed-change").value = selected.observedChange || "";
  $("#action-taken").value = selected.actionTaken || "";
  $("#heart-rate").value = selected.heartRate;
  $("#spo2").value = selected.spo2;
  $("#temperature").value = selected.temperature;
  $("#respiratory-rate").value = selected.respiratoryRate;
  $("#force-high-risk").checked = selected.force;
  state.inputEdited = false;
  state.loadedSignature = caseInputSignature();
  $$("[data-case]").forEach((button) => button.classList.toggle("is-active", button.dataset.case === caseId));
  updateCharacterCount();
  updateInputPreflight();
  state.screening = null;
  state.audit = null;
  state.savedRequestId = null;
  showIdle();
  addSessionEvent("CASE LOADED", `${selected.title} · 已载入`, "合成交接记录与生命体征已填入；尚未生成本次筛查结论。", true);
  if (state.view === "workspace") history.replaceState({ view: "workspace", caseId }, "", `/?view=workspace&case=${caseId}`);
  return true;
}

function addFact(container, label, value) {
  const fact = node("div");
  fact.append(node("small", "", label), node("strong", "", value));
  container.append(fact);
}

function renderResult() {
  const view = state.screening;
  if (!view) return;
  const output = $("#screening-output");
  output.replaceChildren();
  $("#result-state").textContent = "REVIEW REQUIRED";
  $("#run-engine").textContent = view.engine_label || "状态未确认";
  $("#run-sources").textContent = `${view.evidence_count || 0} 条动态 / ${view.reference_count || 0} 条离线`;
  $("#run-review").textContent = "等待人工复核";
  const banner = node("div", "result-banner");
  banner.append(node("div", "result-code", view.priority?.code || "—"));
  const message = node("div");
  message.append(node("strong", "", view.priority?.label || "人工复核"), node("p", "", view.priority?.reason || "系统输出需专业人员确认。"));
  banner.append(message);
  output.append(banner);

  output.append(node("div", "result-heading", "SCREENING / TRACEABLE FACTS"));
  const facts = node("div", "result-facts");
  addFact(facts, "观察到的线索", view.observed_clue || "未能可靠归类");
  addFact(facts, "线索类别", view.candidate_risk_domain || "未能可靠归类");
  addFact(facts, "本次推理链路", view.engine_label || "状态未确认");
  addFact(facts, "来源状态", `${view.evidence_count || 0} 动态 / ${view.reference_count || 0} 离线`);
  addFact(facts, "潜在冲突", `${view.conflict_count || 0} 处`);
  addFact(facts, "本次耗时", `${view.runtime_seconds ?? "—"} 秒`);
  output.append(facts);
  output.append(node("div", "result-caution", "这只是演示线索，不是诊断或临床分诊。未经验证的诊断标签不会参与风险分流。"));

  const tabs = node("div", "result-tabs");
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", "筛查结果详情");
  for (const [key, label] of [["steps", "过程"], ["evidence", "证据"], ["review", "人工复核"]]) {
    const button = node("button", "result-tab" + (state.resultTab === key ? " is-active" : ""), label);
    button.type = "button";
    button.dataset.resultTab = key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(state.resultTab === key));
    tabs.append(button);
  }
  const detail = node("div", "result-detail");
  detail.setAttribute("role", "tabpanel");
  output.append(tabs, detail);
  updateWorkflow("result");
  renderSessionProof();
  renderResultDetail();
}

function renderResultDetail() {
  const view = state.screening;
  if (!view) return;
  $$("[data-result-tab]").forEach((tab) => {
    const active = tab.dataset.resultTab === state.resultTab;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  const detail = $(".result-detail");
  detail.replaceChildren();
  if (state.resultTab === "steps") {
    const traceHead = node("div", "trace-head");
    const traceTitle = node("div");
    traceTitle.append(node("span", "", "EXECUTION TRACE / THIS REQUEST"), node("strong", "", String(view.request_id || "请求编号未提供")));
    const traceTime = node("div", "trace-time");
    traceTime.append(node("small", "", "本次耗时"), node("b", "", `${view.runtime_seconds ?? "—"} s`));
    traceHead.append(traceTitle, traceTime);
    detail.append(traceHead);
    const pipeline = node("ol", "trace-pipeline");
    (view.pipeline || []).forEach((step, index) => {
      const item = node("li", "trace-stage" + (String(step.status || "").includes("待") ? " is-pending" : ""));
      const number = node("span", "trace-stage-number", String(index + 1).padStart(2, "0"));
      const copy = node("div", "trace-stage-copy");
      const top = node("div", "trace-stage-top");
      top.append(node("strong", "", step.name || "未命名阶段"), node("b", "", step.status || "状态未标注"));
      copy.append(top, node("p", "", step.detail || "未提供过程说明"));
      item.append(number, copy); pipeline.append(item);
    });
    if (!pipeline.children.length) pipeline.append(node("li", "detail-empty", "本次响应没有提供执行阶段；不能据此确认完整链路。"));
    detail.append(pipeline);
    const traceBoundary = node("div", "trace-boundary");
    const engine = node("div");
    engine.append(node("span", "", "LOCAL ENGINE / 实际状态"), node("strong", "", view.engine_label || "状态未确认"), node("p", "", view.engine_status || "本机推理状态未确认。"));
    const temporal = view.temporal_assessment || {};
    const temporalPanel = node("div");
    temporalPanel.append(node("span", "", "MODEL BOUNDARY / 未自动推断"), node("strong", "", temporal.label || "时序风险未提供"), node("p", "", temporal.reason || "没有已验证的检查点。"));
    traceBoundary.append(engine, temporalPanel);
    detail.append(traceBoundary);
  } else if (state.resultTab === "evidence") {
    const summary = node("div", "source-summary");
    addFact(summary, "动态检索 / 通过来源核验", `${view.evidence_count || 0} 条`);
    addFact(summary, "离线公共信息卡 / 人工整理", `${view.reference_count || 0} 条`);
    detail.append(summary);
    if (!(view.evidence || []).length) detail.append(node("p", "detail-empty", "本次动态检索没有通过来源核验的资料。离线资料不冒充实时证据。"));
    (view.evidence || []).forEach((row) => {
      const item = node("div", "evidence-item");
      item.append(node("strong", "", row.title || "未命名资料"), node("small", "", `${row.source || "来源未标注"} · ${row.updated || "日期未标注"} · 来源与时效核验`));
      if (typeof row.url === "string" && row.url.startsWith("https://")) {
        const link = node("a", "", "查看来源 ↗"); link.href = row.url; link.target = "_blank"; link.rel = "noopener noreferrer"; item.append(link);
      }
      detail.append(item);
    });
    detail.append(node("div", "result-heading", "离线公共信息卡 / 非实时检索"));
    (view.reference_cards || []).forEach((row) => {
      const item = node("div", "evidence-item");
      item.append(node("strong", "", row.title || "公共信息"), node("small", "", `${row.summary || ""} · 人工核对 ${row.checked_on || ""}`));
      if (typeof row.url === "string" && row.url.startsWith("https://")) {
        const link = node("a", "", "查看原始网页 ↗"); link.href = row.url; link.target = "_blank"; link.rel = "noopener noreferrer"; item.append(link);
      }
      detail.append(item);
    });
  } else {
    renderReview(detail, view);
  }
}

function reviewField(form, labelText, element) {
  const label = node("label", "", labelText);
  label.append(element);
  form.append(label);
  return element;
}

function renderReview(detail, view) {
  detail.append(node("div", "review-policy", view.priority?.code === "P1"
    ? "P1 人工门控：不能选择常规观察，且必须填写复核说明。最终决定由专业人员负责。"
    : "所有演示输出都需要人工确认；复核说明请勿填写可识别个人信息。"));
  const form = node("form", "review-form");
  form.id = "review-form";
  const reviewer = node("input"); reviewer.id = "reviewer"; reviewer.required = true; reviewer.maxLength = 80; reviewer.value = state.audit?.human_review?.reviewer || "竞赛演示复核员";
  reviewField(form, "复核人（演示）", reviewer);
  const decision = node("select"); decision.id = "review-decision";
  const options = view.priority?.code === "P1" ? ["立即转专业人员评估", "已按机构急救流程升级", "退回重新筛查（人工继续接管）"] : ["转专业人员评估", "补充信息后复核", "维持常规观察", "退回重新筛查"];
  options.forEach((value) => { const option = node("option", "", value); option.value = value; decision.append(option); });
  if (options.includes(state.audit?.human_review?.decision)) decision.value = state.audit.human_review.decision;
  reviewField(form, "复核决定", decision);
  const notes = node("textarea"); notes.id = "review-notes"; notes.maxLength = 1000; notes.placeholder = "填写判断依据。请勿粘贴交接原文或个人身份信息。"; notes.value = state.audit?.human_review?.notes || "";
  reviewField(form, "复核说明" + (view.priority?.code === "P1" ? "（P1 必填）" : ""), notes);
  const save = node("button", "", "确认复核并生成审计记录"); save.type = "submit"; form.append(save);
  detail.append(form);
  const status = node("p", "review-message", state.audit?.human_review?.status === "completed" ? "人工复核已记录。最终决定归属于复核人员。" : "等待人工复核。审计文件不会自动包含交接原文，复核说明按填写内容导出。");
  status.id = "review-message";
  detail.append(status);
  const download = node("button", "download-button", state.audit?.human_review?.status === "completed" ? "下载审计摘要 JSON ↓" : "完成人工复核后可下载审计摘要");
  download.type = "button"; download.id = "download-audit";
  download.disabled = state.audit?.human_review?.status !== "completed";
  detail.append(download);
  const library = node("div", "case-save-panel");
  library.append(node("span", "", "CASE LIBRARY / 当前浏览器"), node("p", "", "复核后可明确保存本次合成/脱敏输入；不保存模型结论、复核人姓名或审计原文。重载案例必须重新筛查。"));
  const consent = node("label", "case-save-consent");
  const checkbox = node("input"); checkbox.id = "case-save-consent"; checkbox.type = "checkbox";
  consent.append(checkbox, node("span", "", "我确认仅使用合成或充分脱敏的演示内容，并同意在此浏览器本地保存。"));
  library.append(consent);
  const saveCase = node("button", "save-case-button", state.savedRequestId === String(view.request_id) ? "本次案例已存入 Case Library" : "将本次案例存入 Case Library ↗");
  saveCase.type = "button"; saveCase.id = "save-case-button";
  saveCase.disabled = state.audit?.human_review?.status !== "completed" || state.savedRequestId === String(view.request_id) || savedCases.length >= MAX_LIBRARY_ITEMS - PRESET_CASE_COUNT;
  library.append(saveCase);
  const count = node("small", "", `已存 ${PRESET_CASE_COUNT + savedCases.length} / ${MAX_LIBRARY_ITEMS} · 满额后可从左侧移除自建案例。`);
  count.id = "case-save-count"; library.append(count);
  const saveMessage = node("p", "case-save-message", "案例库只保存在此浏览器，不会上传服务器；请勿录入真实患者信息。");
  saveMessage.id = "case-save-message"; library.append(saveMessage);
  detail.append(library);
}

function currentHandoverRecord() {
  return {
    title: $("#handover-title").value, eventTime: $("#event-time").value,
    note: $("#case-note").value, observedChange: $("#observed-change").value,
    actionTaken: $("#action-taken").value, heartRate: $("#heart-rate").value,
    spo2: $("#spo2").value, temperature: $("#temperature").value,
    respiratoryRate: $("#respiratory-rate").value,
  };
}

function reviewedHandoverPacket() {
  return window.CareGuardHandoff.build(currentHandoverRecord(), state.screening, state.audit?.human_review);
}

function renderHandoverPacket() {
  const packet = reviewedHandoverPacket();
  $("#handover-packet-title").textContent = packet.title;
  $("#handover-packet-note").textContent = packet.note;
  $("#handover-packet-time").textContent = packet.eventTime;
  $("#handover-packet-change").textContent = packet.observedChange;
  $("#handover-packet-action").textContent = packet.actionTaken;
  $("#handover-packet-vitals").textContent = `HR ${packet.vitals.heartRate} · SpO₂ ${packet.vitals.spo2}% · T ${packet.vitals.temperature}℃ · RR ${packet.vitals.respiratoryRate}`;
  $("#handover-packet-priority").textContent = `${packet.priority} / 演示优先级线索`;
  $("#handover-packet-clue").textContent = packet.clue;
  $("#handover-packet-sources").textContent = `动态核验 ${packet.dynamicEvidence} 条 / 人工整理离线参考 ${packet.offlineReferences} 条`;
  $("#handover-packet-engine").textContent = `实际链路：${packet.engine}`;
  $("#handover-packet-decision").textContent = packet.decision;
  $("#handover-packet-review").textContent = `${packet.reviewer} · ${packet.reviewNotes}`;
  $("#handover-packet-id").textContent = `REQUEST ${packet.requestId} / ${packet.reviewedAt}`;
  $("#handover-packet").hidden = false;
}

function downloadHandover() {
  if (!state.screening || state.audit?.human_review?.status !== "completed") return;
  const summary = window.CareGuardHandoff.toText(reviewedHandoverPacket());
  const blob = new Blob(["\uFEFF", summary], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = node("a"); link.href = url;
  link.download = `carelink_handover_${String(state.screening.request_id || "demo").replace(/[^a-zA-Z0-9_-]/g, "_")}.txt`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function runScreening(event) {
  event.preventDefault();
  if (state.running) return;
  if (updateInputPreflight()) { $("#case-note").focus(); return; }
  const form = $("#screening-form");
  if (!form.reportValidity()) return;
  const note = $("#case-note").value.trim();
  if (!note) return;
  const handoverText = [
    `案例标题：${$("#handover-title").value.trim()}`,
    $("#event-time").value ? `发生时间：${$("#event-time").value}` : "",
    `护理交接记录：${note}`,
    $("#observed-change").value.trim() ? `观察到的变化：${$("#observed-change").value.trim()}` : "",
    $("#action-taken").value.trim() ? `已采取措施与待交接事项：${$("#action-taken").value.trim()}` : "",
  ].filter(Boolean).join("\n");
  const heart = Number($("#heart-rate").value), spo2 = Number($("#spo2").value), temp = Number($("#temperature").value), rr = Number($("#respiratory-rate").value);
  const submittedInput = currentInputSignature();
  state.running = true; state.screening = null; state.audit = null; state.engineering = null; state.savedRequestId = null; state.resultTab = "steps";
  renderEngineeringBridge("running");
  $("#handover-packet").hidden = true;
  renderSessionProof("running");
  addSessionEvent("SCREENING STARTED", "本地筛查已发起", "正在等待本机实际响应；旧结果不会在运行中显示。");
  updateWorkflow("running");
  const runButton = $("#run-button"); runButton.disabled = true; runButton.firstChild.textContent = "本地多智能体正在运行 ";
  $("#result-state").textContent = "RUNNING LOCALLY";
  $("#run-engine").textContent = "正在运行";
  $("#run-sources").textContent = "等待核验";
  $("#run-review").textContent = "等待筛查";
  const output = $("#screening-output"); output.replaceChildren();
  const idle = node("div", "output-idle"); idle.append(node("div", "idle-symbol loading-dot", "✳"), node("strong", "", "正在整理线索与来源状态"), node("p", "", "本机模型可能需要一些时间。结果生成前不会显示历史案例的旧结论。"), node("div", "running-bar")); output.append(idle);
  try {
    const response = await fetch("/screening/engineering", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ patient_query: handoverText, observation: { heart_rate: heart, spo2, temperature: temp, respiratory_rate: rr }, force_high_risk: $("#force-high-risk").checked }) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (!payload.screening || !payload.audit || !payload.engineering) throw new Error("响应缺少工程筛查结果");
    if (currentInputSignature() !== submittedInput) {
      showIdle("输入已变化，运行中的旧结果已作废");
      addSessionEvent("INPUT CHANGED", "运行中输入已变化", "返回结果与当前输入不一致，已丢弃；请重新运行筛查。");
      return;
    }
    state.screening = payload.screening;
    state.audit = payload.audit;
    state.engineering = payload.engineering;
    renderResult();
    renderEngineeringBridge("complete");
    addSessionEvent("RESULT RETURNED", "本次筛查已返回", `优先级 ${payload.screening.priority?.code || "未确认"}；动态来源 ${payload.screening.evidence_count || 0} 条、离线卡 ${payload.screening.reference_count || 0} 条。等待人工复核。`);
  } catch (_error) {
    state.engineering = null;
    renderEngineeringBridge("error");
    output.replaceChildren(node("div", "output-error", "本次筛查未生成结果。请检查本地推理服务和项目数据后重试；页面不会保留旧结论。"));
    $("#result-state").textContent = "RUN FAILED";
    $("#run-engine").textContent = "本次运行失败";
    $("#run-sources").textContent = "未生成结果";
    $("#run-review").textContent = "无法复核";
    updateWorkflow("error");
    renderSessionProof("error");
    addSessionEvent("RUN FAILED", "本次运行未生成结果", "请检查本地服务并重试；此次失败不记作已验证的筛查。");
  } finally {
    state.running = false; updateInputPreflight(); runButton.firstChild.textContent = "开始风险筛查 ";
  }
}

function saveReview(event) {
  event.preventDefault();
  if (!state.audit || !state.screening) return;
  const reviewer = $("#reviewer").value.trim();
  const decision = $("#review-decision").value;
  const notes = $("#review-notes").value.trim();
  const message = $("#review-message");
  if (!reviewer) { message.textContent = "请填写复核人。"; return; }
  if (state.screening.priority?.code === "P1" && !notes) { message.textContent = "P1 案例必须填写复核说明。"; return; }
  state.audit.human_review = { status: "completed", reviewer, decision, notes, reviewed_at: new Date().toISOString() };
  renderHandoverPacket();
  message.textContent = "人工复核已记录。最终决定归属于复核人员。";
  const download = $("#download-audit");
  download.disabled = false;
  download.textContent = "下载审计摘要 JSON ↓";
  $("#save-case-button").disabled = savedCases.length >= MAX_LIBRARY_ITEMS - PRESET_CASE_COUNT || state.savedRequestId === String(state.screening.request_id);
  updateWorkflow("reviewed");
  $("#run-review").textContent = "人工决定已记录";
  renderSessionProof();
  addSessionEvent("HUMAN REVIEW", "人工决定已记录", "审计摘要可导出；这里不展示复核人姓名、说明或交接原文。");
}

function saveCurrentCase() {
  const message = $("#case-save-message");
  if (!state.screening || state.audit?.human_review?.status !== "completed") { message.textContent = "请先完成本次筛查与人工复核。"; return; }
  if (state.savedRequestId === String(state.screening.request_id)) { message.textContent = "本次案例已经保存，请修改输入并重新筛查后再保存。"; return; }
  if (savedCases.length >= MAX_LIBRARY_ITEMS - PRESET_CASE_COUNT) { message.textContent = "案例库已满：请先移除一个自建案例。"; return; }
  if (!$("#case-save-consent").checked) { message.textContent = "请先确认内容仅为合成或充分脱敏的演示数据。"; return; }
  if (updateInputPreflight()) { message.textContent = "发现疑似身份标识；本次内容不能保存。"; return; }
  const item = {
    id: `saved-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    title: $("#handover-title").value.trim(), eventTime: $("#event-time").value,
    note: $("#case-note").value.trim(), observedChange: $("#observed-change").value.trim(), actionTaken: $("#action-taken").value.trim(),
    heartRate: Number($("#heart-rate").value), spo2: Number($("#spo2").value), temperature: Number($("#temperature").value), respiratoryRate: Number($("#respiratory-rate").value),
    force: $("#force-high-risk").checked, savedAt: new Date().toISOString(), source: "当前浏览器保存 · 合成/脱敏演示",
  };
  if (!item.title || !item.note || !$("#screening-form").reportValidity()) { message.textContent = "请补全案例标题、交接记录和有效体征。"; return; }
  try { localStorage.setItem(CASE_LIBRARY_KEY, JSON.stringify([...savedCases, item])); }
  catch (_error) { message.textContent = "当前浏览器无法保存本地案例；请检查存储权限或空间。"; return; }
  savedCases.push(item); registerSavedCases(); renderCaseLibrary();
  $("#case-save-count").textContent = `已存 ${PRESET_CASE_COUNT + savedCases.length} / ${MAX_LIBRARY_ITEMS} · 满额后可从左侧移除自建案例。`;
  state.savedRequestId = String(state.screening.request_id);
  state.loadedSignature = caseInputSignature();
  $("#save-case-button").disabled = true;
  $("#save-case-button").textContent = "本次案例已存入 Case Library";
  message.textContent = "保存成功。左侧 Case Library 已新增案例；再次打开时需重新筛查。";
  addSessionEvent("CASE SAVED", "本机案例已存入", "本次合成/脱敏输入存入当前浏览器；筛查结果与审计内容不持久化。" );
}

function removeSavedCase(caseId) {
  const item = savedCases.find((entry) => entry.id === caseId);
  if (!item || !window.confirm(`仅从此浏览器移除「${item.title}」？移除后无法恢复。`)) return;
  const next = savedCases.filter((entry) => entry.id !== caseId);
  try { localStorage.setItem(CASE_LIBRARY_KEY, JSON.stringify(next)); }
  catch (_error) { window.alert("本地存储更新失败，案例未移除。"); return; }
  savedCases = next; delete CASES[caseId]; delete CASE_BRIEFS[caseId]; registerSavedCases();
  if (state.caseId === caseId) loadCase("draft", true);
  renderCaseLibrary();
}

function downloadAudit() {
  if (!state.audit || !state.screening || state.audit.human_review?.status !== "completed") return;
  const blob = new Blob([JSON.stringify(state.audit, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = node("a"); link.href = url; link.download = `carelink_audit_${String(state.screening.request_id || "demo").replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function loadStatus() {
  const metrics = $("#evidence-metrics").querySelectorAll("strong");
  const timestamp = $("#evidence-timestamp");
  const workspaceSnapshot = $("#workspace-snapshot");
  const dynamicCount = $("#evidence-dynamic-count");
  const globalTestCount = $("#global-test-count");
  try {
    const response = await fetch("/site/status", { cache: "no-store" });
    if (!response.ok) throw new Error("status unavailable");
    const data = await response.json();
    const tests = data.tests || {}, smoke = data.smoke || {};
    const passed = (tests.total || 0) - (tests.failures || 0) - (tests.errors || 0) - (tests.skipped || 0);
    metrics[0].textContent = tests.total ? `${passed} / ${tests.total} 通过` : "待复测";
    globalTestCount.textContent = tests.total ? `${passed} / ${tests.total} 通过` : "待复测";
    metrics[1].textContent = smoke.ollama_generation_verified && !smoke.fallback_used ? "最近自检已验证" : "待复测";
    metrics[2].textContent = "未获准";
    metrics[3].textContent = smoke.latency_seconds == null ? "待复测" : `${smoke.latency_seconds} 秒`;
    timestamp.textContent = smoke.checked_at_local ? `最近合成案例自检：${smoke.checked_at_local}（本地时间） · 动态证据 ${smoke.dynamic_evidence_count ?? "—"} 条。以上均为历史快照，不代表当前持续在线。` : "未找到带时间戳的本机自检记录；以上指标不代表当前持续在线。";
    dynamicCount.textContent = `最近自检动态证据：${smoke.dynamic_evidence_count ?? "—"} 条`;
    workspaceSnapshot.textContent = smoke.checked_at_local
      ? `最近本机自检：${smoke.checked_at_local} · ${smoke.ollama_generation_verified && !smoke.fallback_used ? "Ollama 曾验证" : "生成状态待复核"}。历史快照，不代表此刻在线。`
      : "暂无带时间戳的本机自检快照；请以本次运行状态为准。";
    $("#diag-tests").textContent = tests.total ? `${tests.total} / ${tests.failures || 0} / ${tests.errors || 0} / ${tests.skipped || 0}` : "无测试报告";
    $("#diag-generation").textContent = smoke.checked_at_local ? (smoke.ollama_generation_verified ? "历史已验证" : "未验证") : "无自检记录";
    $("#diag-fallback").textContent = smoke.checked_at_local ? (smoke.fallback_used ? "发生降级" : "未发生降级") : "无自检记录";
    $("#diag-retrieval").textContent = smoke.dynamic_evidence_count == null ? "未记录" : `${smoke.dynamic_evidence_count} 条`;
  } catch (_error) {
    metrics[0].textContent = "状态不可读"; metrics[1].textContent = "状态不可读"; metrics[3].textContent = "状态不可读";
    globalTestCount.textContent = "状态不可读";
    timestamp.textContent = "本机证据快照暂不可读取；请检查服务后重试。";
    dynamicCount.textContent = "最近自检动态证据：状态不可读";
    workspaceSnapshot.textContent = "最近本机自检快照不可读；请以本次实际运行状态为准。";
    for (const id of ["diag-tests", "diag-generation", "diag-fallback", "diag-retrieval"]) $("#" + id).textContent = "不可读";
  }
}

document.addEventListener("click", (event) => {
  const nav = event.target.closest("[data-nav]");
  if (nav) { event.preventDefault(); navigate(nav.dataset.nav); return; }
  const claimFilter = event.target.closest("[data-claim-filter]");
  if (claimFilter) { setClaimFilter(claimFilter.dataset.claimFilter); return; }
  const material = event.target.closest("[data-material]");
  if (material) { setMaterial(material.dataset.material); return; }
  if (event.target.closest("#brief-start")) { $("#screening-form").scrollIntoView({ block: "start", behavior: "smooth" }); return; }
  const claimRow = event.target.closest("[data-claim-state]");
  if (claimRow) {
    selectClaim(claimRow);
    if (window.innerWidth <= 850) $("#claim-inspector").scrollIntoView({ block: "start", behavior: "smooth" });
    return;
  }
  const audience = event.target.closest('[role="tab"][data-audience]');
  if (audience) { setAudience(audience.dataset.audience); return; }
  const launchCase = event.target.closest("[data-launch-case]");
  if (launchCase) { setLaunchCase(launchCase.dataset.launchCase); return; }
  if (event.target.closest("#launch-open-case, #medical-open-case")) {
    if (loadCase(state.launchCaseId)) navigate("workspace", state.launchCaseId); return;
  }
  const atlasCase = event.target.closest("[data-atlas-case]");
  if (atlasCase) { setAtlasCase(atlasCase.dataset.atlasCase); return; }
  if (event.target.closest("#atlas-open-case")) {
    const caseId = $(".atlas-shell").dataset.caseId || "chest";
    if (loadCase(caseId)) navigate("workspace", caseId); return;
  }
  const caseCard = event.target.closest("[data-open-case]");
  if (caseCard) { if (loadCase(caseCard.dataset.openCase)) navigate("workspace", caseCard.dataset.openCase); return; }
  const removeCase = event.target.closest("[data-remove-case]");
  if (removeCase) { removeSavedCase(removeCase.dataset.removeCase); return; }
  if (event.target.closest("#new-case-button")) { if (loadCase("draft")) { $("#screening-form").scrollIntoView({ block: "start", behavior: "smooth" }); $("#handover-title").focus(); } return; }
  const picker = event.target.closest("[data-case]");
  if (picker) { loadCase(picker.dataset.case); return; }
  const feature = event.target.closest("[data-feature]");
  if (feature) { setFeature(feature.dataset.feature); return; }
  const resultTab = event.target.closest("[data-result-tab]");
  if (resultTab) { state.resultTab = resultTab.dataset.resultTab; renderResultDetail(); return; }
  if (event.target.closest("#save-case-button")) { saveCurrentCase(); return; }
  if (event.target.closest("#download-audit")) { downloadAudit(); return; }
  if (event.target.closest("#download-handover")) downloadHandover();
});

document.addEventListener("submit", (event) => {
  if (event.target.id === "screening-form") runScreening(event);
  if (event.target.id === "review-form") saveReview(event);
});

$("#screening-form").addEventListener("input", (event) => {
  if (event.target.id === "case-note") updateCharacterCount();
  if (event.target.id === "handover-title" && state.caseId === "draft") {
    const title = event.target.value.trim() || "新建演示案例";
    $("#workspace-case-label").textContent = title;
    $("#case-brief-title").textContent = title;
    $("#run-case").textContent = title;
  }
  state.inputEdited = true;
  updateInputPreflight();
  invalidateResult();
});
window.addEventListener("popstate", () => { const route = routeFromUrl(); navigate(route.view, route.caseId, false); });
window.addEventListener("scroll", updateReadingProgress, { passive: true });
window.addEventListener("resize", updateReadingProgress, { passive: true });

$$('[data-claim-state]').forEach((row) => {
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-pressed", "false");
  row.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectClaim(row); }
  });
});

setFeature("observe");
mountInteractiveDepth();
renderCaseLibrary();
setAudience("recorder");
setAtlasCase("chest");
setLaunchCase("chest");
setMaterial("input");
setClaimFilter("all");
selectClaim($('[data-claim-state]'));
window.CareGuardSite = {
  getSessionSummary() {
    if (!state.screening) return null;
    return { requestId: String(state.screening.request_id || "—"), engine: state.screening.engine_label || "状态未确认", priority: state.screening.priority?.code || "—", evidenceCount: state.screening.evidence_count || 0, reviewed: state.audit?.human_review?.status === "completed" };
  },
  loadLabVariant(point) {
    if (!point || !CASES[point.caseId]) return;
    const values = [point.heartRate, point.spo2, point.respiratoryRate];
    if (values.some((value) => !Number.isFinite(value))) return;
    if (!loadCase(point.caseId)) return;
    $("#heart-rate").value = point.heartRate;
    $("#spo2").value = point.spo2;
    $("#respiratory-rate").value = point.respiratoryRate;
    state.inputEdited = !point.central;
    updateInputPreflight();
    navigate("workspace", point.caseId);
    addSessionEvent("SYNTHETIC VARIANT", "三维图谱变体已载入", "只改变合成案例的三项体征输入；尚未运行筛查，也不代表真实患者。", true);
    requestAnimationFrame(() => $("#screening-form").scrollIntoView({ block: "start", behavior: "smooth" }));
  },
  openClaim(index) {
    const rows = $$('[data-claim-state]');
    if (!Number.isInteger(index) || !rows[index]) return;
    setClaimFilter("all"); selectClaim(rows[index]); navigate("evidence");
    requestAnimationFrame(() => $("#claim-inspector").scrollIntoView({ block: "start", behavior: "smooth" }));
  },
  openMaterial(key) {
    if (!MATERIALS[key]) return;
    setMaterial(key); navigate("evidence");
    requestAnimationFrame(() => $(".material-archive").scrollIntoView({ block: "start", behavior: "smooth" }));
  },
  openSession() {
    if (state.screening) {
      navigate("evidence");
      requestAnimationFrame(() => $(".live-proof").scrollIntoView({ block: "start", behavior: "smooth" }));
    } else navigate("workspace");
  },
};
const initial = routeFromUrl();
loadCase(initial.caseId);
navigate(initial.view, initial.caseId, false);
