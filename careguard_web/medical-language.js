/* One question, two honest paths: source QA or the fixed 3-year diabetes head. */
(() => {
  "use strict";
  const hero = document.querySelector("#workspace-view .workspace-hero");
  if (!hero) return;
  const section = document.createElement("section");
  section.id = "medical-language-studio";
  section.className = "medical-language-studio";
  section.innerHTML = `
    <div class="wrap language-wrap">
      <div class="language-heading"><div><span>UNIFIED MEDICAL INPUT / RESEARCH ONLY</span><h2>一个问题，<br><em>两条诚实的路径。</em></h2></div><p>英文医学知识问题进入 MedQuAD 来源检索；只有明确给出完整基线信息的未来糖尿病问题，才调用 MAPFM TFA 的 3 年研究模型。普通问答、其他疾病和缺失指标不会被编造成疾病概率。</p></div>
      <div class="language-grid"><form id="language-form"><div class="language-panel-top"><span>01 / 自然语言输入</span><b>LOCAL COMPUTE · NO DIAGNOSIS</b></div><label for="language-question">用自然语言描述你的问题</label><textarea id="language-question" minlength="5" maxlength="1500" required spellcheck="false" placeholder="例如：未患糖尿病，50 岁，BMI 25，空腹血糖 5.3 mmol/L，收缩压 125 mmHg，甘油三酯 1.2 mmol/L。未来 3 年新发糖尿病的研究风险是多少？"></textarea><div class="language-examples"><button type="button" data-language-example="risk">填入合成风险示例</button><button type="button" data-language-example="qa">填入英文知识问答</button></div><div class="language-submit"><small>请勿输入姓名、电话、病历号或真实患者记录。输入只发送至本机 127.0.0.1 服务。</small><button type="submit">分析这段问题 ↗</button></div></form>
      <div class="language-result" id="language-result" role="status" aria-live="polite"><div class="language-panel-top"><span>02 / SOURCE OR RESEARCH ESTIMATE</span><b>等待输入</b></div><div class="language-empty"><strong>不会为每个问题<br>生成一个百分比。</strong><p>先判定问题能否由有来源的资料回答，或是否具备三年新发糖尿病模型所需的完整基线特征。</p></div></div></div>
      <div class="language-bottom"><div><b>已训练结局</b><span>未来 3 年新发糖尿病</span></div><div><b>研究权重</b><span>MAPFM TFA 扩展 · 非 MedQuAD</span></div><div><b>泛化状态</b><span>仅内部验证 · 无外部临床验证</span></div><div><b>人工核查</b><a href="#review-desk">继续到本工作台的盲评区 ↗</a></div></div>
    </div>`;
  const guidance = document.querySelector("#workspace-guidance");
  (guidance || hero).insertAdjacentElement("afterend", section);
  const flags = hero.querySelector(".workspace-hero-flags");
  if (flags) {
    const link = document.createElement("a");
    link.href = "#medical-language-studio";
    link.className = "language-hero-jump";
    link.textContent = "自然语言问答 × 3 年糖尿病研究估计 ↘";
    flags.append(link);
  }
  const form = section.querySelector("#language-form");
  const input = section.querySelector("#language-question");
  const result = section.querySelector("#language-result");
  const submit = form.querySelector('button[type="submit"]');
  const exampleRisk = "未患糖尿病，50岁，BMI 25，空腹血糖5.3 mmol/L，收缩压125 mmHg，甘油三酯1.2 mmol/L。未来3年新发糖尿病的研究风险是多少？";
  const exampleQa = "What are the symptoms of type 2 diabetes?";
  section.querySelectorAll("[data-language-example]").forEach(button => button.addEventListener("click", () => {
    input.value = button.dataset.languageExample === "risk" ? exampleRisk : exampleQa;
    input.focus();
  }));

  const resetResult = (eyebrow, title) => {
    result.replaceChildren();
    const top = document.createElement("div");
    top.className = "language-panel-top";
    const label = document.createElement("span"); label.textContent = eyebrow;
    const state = document.createElement("b"); state.textContent = title;
    top.append(label, state); result.append(top);
  };
  const paragraph = text => {
    const item = document.createElement("p");
    item.textContent = text;
    result.append(item);
  };
  const extracted = values => {
    if (!values) return;
    const labels = [
      ["age_years", "年龄", "岁"], ["bmi", "BMI", "kg/m²"],
      ["fasting_glucose_mmol_l", "空腹血糖", "mmol/L"],
      ["systolic_bp_mmhg", "收缩压", "mmHg"],
      ["triglyceride_mmol_l", "甘油三酯", "mmol/L"],
      ["known_diabetes_at_baseline", "基线糖尿病", ""],
    ];
    const grid = document.createElement("div"); grid.className = "language-extracted";
    labels.forEach(([key, label, unit]) => {
      if (values[key] == null) return;
      const cell = document.createElement("div");
      const name = document.createElement("small"); name.textContent = label;
      const value = document.createElement("strong");
      value.textContent = key === "known_diabetes_at_baseline" ? "明确否认" : `${Number(values[key]).toFixed(key === "age_years" || key === "systolic_bp_mmhg" ? 0 : 2)} ${unit}`;
      cell.append(name, value); grid.append(cell);
    });
    if (grid.childElementCount) result.append(grid);
  };
  const show = data => {
    if (data.kind === "diabetes_3y_result") {
      const estimate = data.estimate;
      if (estimate?.model !== "mapfm_tfa_prospective_neural_v2" || estimate.task !== "diabetes_onset" ||
          estimate.horizon_days !== 1095 || estimate.clinical_use_allowed !== false ||
          estimate.external_validation_completed !== false ||
          estimate.execution_path !== "original_mapfm_tfa.forecast_prospective" ||
          !Number.isFinite(estimate.research_probability)) throw new Error("研究模型来源或边界标识不匹配，拒绝展示百分比。");
      resetResult("02 / MAPFM TFA · RESEARCH ESTIMATE", "仅内部验证");
      const number = document.createElement("strong"); number.className = "language-probability";
      number.textContent = `${(estimate.research_probability * 100).toFixed(2)}%`;
      result.append(number);
      paragraph("未来 3 年新发糖尿病的模型研究估计。只在公开纵向队列内部测试过，未在中国目标人群外部校准；不是个人诊断概率，不用于临床决策。");
      extracted(data.extracted);
      const source = document.createElement("small"); source.className = "language-model-id";
      source.textContent = `MAPFM TFA · SHA-256 ${estimate.checkpoint_sha256.slice(0, 16)}…`;
      result.append(source);
      return;
    }
    if (data.kind === "source_qa") {
      resetResult("02 / MEDQUAD · ATTRIBUTED SOURCE", `${data.qa?.matches?.length || 0} 条来源`);
      paragraph("这是一条医学知识来源检索，不提供未来患病概率。原始资料可能不是现行指南。");
      if (!data.qa?.matches?.length) { paragraph("没有达到检索阈值的来源答案，系统拒答。请调整英文问题，不能据此推断疾病风险。"); return; }
      data.qa.matches.forEach((match, index) => {
        const card = document.createElement("article"); card.className = "language-source-card";
        const top = document.createElement("small"); top.textContent = `${String(index + 1).padStart(2, "0")} / ${match.source || "来源未标注"}`;
        const title = document.createElement("h3"); title.textContent = match.question || "原始问题";
        const answer = document.createElement("p"); answer.textContent = match.answer || "";
        card.append(top, title, answer);
        if (/^https:\/\//i.test(match.source_url || "")) {
          const link = document.createElement("a"); link.href = match.source_url; link.target = "_blank";
          link.rel = "noopener noreferrer"; link.textContent = "查看原始来源 ↗"; card.append(link);
        }
        result.append(card);
      });
      return;
    }
    resetResult("02 / BOUNDARY CHECK", "不输出概率");
    paragraph(data.message || "当前问题不能可靠计算未来疾病概率。");
    extracted(data.extracted);
    if (data.missing?.length) paragraph(`仍需明确：${data.missing.join("、")}。`);
    if (data.issues?.length) paragraph(`需要核对：${data.issues.join("；")}。`);
  };
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    resetResult("02 / PROCESSING", "本机分析中");
    paragraph("正在区分来源问答与固定结局预测，并核对能否运行现有研究权重…");
    try {
      const response = await fetch("/mapfm/medical-language/evaluate", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question: input.value.trim()})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "本机请求失败。");
      show(data);
    } catch (error) {
      resetResult("02 / REQUEST STOPPED", "没有可用结果");
      paragraph(error.message || "无法连接本机服务。");
    } finally { submit.disabled = false; }
  });
})();
