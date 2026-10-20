/* Separate, research-only inference from the actually trained MAPFM TFA head. */
(() => {
  const after = document.querySelector("#diabetes-studio");
  if (!after) return;
  const section = document.createElement("section");
  section.className = "prospective-neural";
  section.id = "prospective-neural-lab";
  section.innerHTML = `
    <header><span>MAPFM TFA / TRAINED RESEARCH PATH</span><h2>神经预测，<em>有权重才计算。</em></h2><p>这一栏与上方 8 年 Framingham 评分和下方 MedQuAD 问答完全独立。研究权重来自公开 NAGALA 纵向队列；输入仅用于本机即时推断，不写入案例库。</p></header>
    <div class="prospective-neural-grid"><form id="prospective-neural-form"><div class="prospective-neural-top"><b>01 / 三年新发糖尿病研究演示</b><span id="prospective-neural-status">核对权重…</span></div><div class="prospective-neural-fields">
      <label>年龄 / 岁<input name="age_years" type="number" min="18" max="110" step="1" value="50" required></label>
      <label>BMI / kg/m²<input name="bmi" type="number" min="15" max="55" step="0.1" value="25" required></label>
      <label>基线空腹血糖 / mmol/L<input name="fasting_glucose_mmol_l" type="number" min="0.1" max="6.99" step="0.01" value="5.3" required></label>
      <label>收缩压 / mmHg<input name="systolic_bp_mmhg" type="number" min="70" max="250" step="1" value="125" required></label>
      <label>甘油三酯 / mmol/L<input name="triglyceride_mmol_l" type="number" min="0.2" max="20" step="0.01" value="1.2" required></label>
    </div><button type="submit" disabled>运行 MAPFM 研究推断 ↗</button><p>示例数字可改；仅适用于基线无糖尿病人群。超出训练队列的基线观察范围会拒绝输出；它不是个人诊断概率，不能作为治疗或分诊依据。</p><div class="prospective-neural-validation" id="prospective-neural-validation">内部验证资料核对中…</div></form>
    <div class="prospective-neural-output" id="prospective-neural-output" role="status" aria-live="polite"><span>02 / VERIFIED INFERENCE</span><strong>等待研究输入。</strong><p>只有检查点 SHA-256 与训练报告一致、训练任务已登记时，后端才会输出神经模型计算结果。</p></div></div>
    <footer><div><b>11,113</b><small>3 年结局可判定样本</small></div><div><b>101</b><small>3 年内观察事件</small></div><div><b>15</b><small>内部测试集事件数</small></div><p>上述数字来自已验证公开数据，但内部留出集不是外部验证。日本队列未经中国目标人群验证。MedQuAD 问答不参与此预测。<a href="https://datadryad.org/dataset/doi:10.5061/dryad.8q0p192" target="_blank" rel="noopener noreferrer">数据来源 ↗</a></p></footer>`;
  after.insertAdjacentElement("afterend", section);
  const flags = document.querySelector("#workspace-view .workspace-hero-flags");
  if (flags) {
    const jump = document.createElement("a");
    jump.className = "prospective-neural-jump";
    jump.href = "#prospective-neural-lab";
    jump.textContent = "独立模块 · MAPFM 神经研究推断 ↘";
    flags.append(jump);
  }
  if (window.location.hash === "#prospective-neural-lab")
    requestAnimationFrame(() => section.scrollIntoView({block: "start", behavior: "instant"}));
  const form = section.querySelector("form");
  const button = form.querySelector("button");
  const status = section.querySelector("#prospective-neural-status");
  const output = section.querySelector("#prospective-neural-output");
  const validation = section.querySelector("#prospective-neural-validation");
  fetch("/mapfm/prospective-neural/status", {cache: "no-store"})
    .then(response => response.json())
    .then(data => {
      const ready = data.trained_tasks?.includes("diabetes_onset") === true;
      status.textContent = ready ? "权重校验通过 · 糖尿病研究头" : "未安装糖尿病研究权重";
      button.disabled = !ready;
      const metrics = data.internal_validation?.diabetes_onset;
      validation.textContent = metrics
        ? `内部测试 ${metrics.test_rows} 人 / ${metrics.test_events} 事件；AUROC ${metrics.auroc.toFixed(2)}，重抽样 95% 区间 ${metrics.auroc_95ci[0].toFixed(2)}–${metrics.auroc_95ci[1].toFixed(2)}。非外部验证。`
        : "没有可核验的内部验证报告。";
      if (!ready) output.querySelector("p").textContent = "本机没有通过校验的糖尿病神经权重；不会生成估计。请安装含权重的完整交付包。";
    })
    .catch(() => { status.textContent = "本机服务不可用"; validation.textContent = "暂无法读取验证资料。"; });
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (!form.reportValidity() || button.disabled) return;
    const fields = new FormData(form);
    const baseline_values = {known_diabetes_at_baseline: 0};
    for (const name of ["age_years", "bmi", "fasting_glucose_mmol_l", "systolic_bp_mmhg", "triglyceride_mmol_l"])
      baseline_values[name] = Number(fields.get(name));
    button.disabled = true;
    output.innerHTML = "<span>02 / VERIFIED INFERENCE</span><strong>本机计算中…</strong>";
    try {
      const response = await fetch("/mapfm/prospective-neural/research-predict", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({task: "diabetes_onset", baseline_values}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "研究推断失败");
      if (result.model !== "mapfm_tfa_prospective_neural_v2" || result.task !== "diabetes_onset" ||
          result.horizon_days !== 1095 || result.clinical_use_allowed !== false ||
          result.execution_path !== "original_mapfm_tfa.forecast_prospective")
        throw new Error("模型版本或用途标识不匹配，拒绝展示结果。");
      output.replaceChildren();
      const label = document.createElement("span"); label.textContent = "02 / RESEARCH ESTIMATE ONLY";
      const value = document.createElement("strong"); value.textContent = `${(result.research_probability * 100).toFixed(2)}%`;
      const note = document.createElement("p"); note.textContent = "MAPFM TFA 扩展真实权重计算的三年研究估计；只做内部留出集验证，未完成外部验证，不能用于个人诊断、分诊或治疗。";
      const hash = document.createElement("small"); hash.textContent = `SHA-256 ${result.checkpoint_sha256.slice(0, 16)}…`;
      output.append(label, value, note, hash);
    } catch (error) {
      output.replaceChildren();
      const label = document.createElement("span"); label.textContent = "INFERENCE STOPPED";
      const note = document.createElement("p"); note.textContent = error.message || "无法连接本机服务";
      output.append(label, note);
    } finally { button.disabled = false; }
  });
})();
